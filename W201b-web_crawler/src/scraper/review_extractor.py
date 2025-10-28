import re
from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page, ElementHandle
from bs4 import BeautifulSoup

from ..models import Review, Product
from ..config import AMAZON_SELECTORS


class ReviewExtractor:
    """Extracts review information from Amazon pages"""
    
    def __init__(self):
        self.selectors = AMAZON_SELECTORS
    
    async def extract_reviews_from_page(self, page: Page, product: Product) -> List[Review]:
        """
        Extract all reviews from the current reviews page
        
        Args:
            page: Playwright page object
            product: Product information
            
        Returns:
            List of extracted Review objects
        """
        reviews = []
        
        try:
            # Wait for reviews to load
            await page.wait_for_selector(self.selectors['review_containers'], timeout=10000)
            
            # Get all review containers
            review_elements = await page.query_selector_all(self.selectors['review_containers'])
            
            for element in review_elements:
                try:
                    review = await self._extract_single_review(element, product, page)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    print(f"Error extracting individual review: {e}")
                    continue
            
        except Exception as e:
            print(f"Error extracting reviews from page: {e}")
        
        return reviews
    
    async def _extract_single_review(self, element: ElementHandle, product: Product, page: Page) -> Optional[Review]:
        """
        Extract a single review from a review element
        
        Args:
            element: Review container element
            product: Product information
            page: Playwright page for URL generation
            
        Returns:
            Review object or None if extraction fails
        """
        try:
            # Extract review ID from data attributes
            review_id = await element.get_attribute('data-hook')
            if not review_id or review_id == 'review':
                # Try to get a unique identifier
                review_id = await element.get_attribute('id') or f"review_{hash(str(element))}"
            
            # Extract title
            title_element = await element.query_selector(self.selectors['review_title'])
            title = await title_element.inner_text() if title_element else "No Title"
            title = title.strip()
            
            # Extract text content
            text_element = await element.query_selector(self.selectors['review_text'])
            text = await text_element.inner_text() if text_element else ""
            text = self._clean_review_text(text)
            
            # Extract rating
            rating_element = await element.query_selector(self.selectors['review_rating'])
            rating = await self._extract_rating(rating_element)
            
            # Extract date
            date_element = await element.query_selector(self.selectors['review_date'])
            date = await self._extract_date(date_element)
            
            # Extract reviewer name
            name_element = await element.query_selector(self.selectors['reviewer_name'])
            reviewer_name = await name_element.inner_text() if name_element else "Anonymous"
            reviewer_name = reviewer_name.strip()
            
            # Check if verified purchase
            verified_element = await element.query_selector(self.selectors['verified_purchase'])
            verified_purchase = verified_element is not None
            
            # Extract helpful votes
            helpful_element = await element.query_selector(self.selectors['helpful_votes'])
            helpful_votes = await self._extract_helpful_votes(helpful_element)
            
            # Extract review images
            image_elements = await element.query_selector_all(self.selectors['review_images'])
            images = []
            for img_element in image_elements:
                src = await img_element.get_attribute('src')
                if src:
                    images.append(src)
            
            # Generate review URL (approximate)
            current_url = page.url
            review_url = f"{current_url}#review_{review_id}" if current_url else None
            
            return Review(
                id=review_id,
                title=title,
                text=text,
                rating=rating,
                date=date,
                reviewer_name=reviewer_name,
                verified_purchase=verified_purchase,
                helpful_votes=helpful_votes,
                product_asin=product.asin,
                product_title=product.title,
                review_url=review_url,
                images=images if images else None
            )
            
        except Exception as e:
            print(f"Error extracting single review: {e}")
            return None
    
    async def _extract_rating(self, rating_element: Optional[ElementHandle]) -> int:
        """Extract rating from rating element"""
        if not rating_element:
            return 0
        
        try:
            # Get the alt text or title which usually contains the rating
            alt_text = await rating_element.get_attribute('title') or await rating_element.get_attribute('alt') or ""
            
            # Look for patterns like "4.0 out of 5 stars" or "4 stars"
            rating_match = re.search(r'(\\d+(?:\\.\\d+)?)\\s*(?:out of 5|stars?)', alt_text.lower())
            if rating_match:
                return int(float(rating_match.group(1)))
            
            # Fallback: look for just a number
            number_match = re.search(r'(\\d+)', alt_text)
            if number_match:
                rating = int(number_match.group(1))
                return min(max(rating, 1), 5)  # Clamp between 1 and 5
            
        except Exception as e:
            print(f"Error extracting rating: {e}")
        
        return 0
    
    async def _extract_date(self, date_element: Optional[ElementHandle]) -> datetime:
        """Extract date from date element"""
        if not date_element:
            return datetime.now()
        
        try:
            date_text = await date_element.inner_text()
            date_text = date_text.strip()
            
            # Remove common prefixes
            date_text = re.sub(r'^(Reviewed in|Reviewed on|on)\\s+', '', date_text, flags=re.IGNORECASE)
            
            # Try different date formats
            date_patterns = [
                r'(\\w+\\s+\\d{1,2},\\s+\\d{4})',  # "January 15, 2023"
                r'(\\d{1,2}\\s+\\w+\\s+\\d{4})',    # "15 January 2023"
                r'(\\d{1,2}/\\d{1,2}/\\d{4})',      # "01/15/2023"
                r'(\\d{4}-\\d{2}-\\d{2})',          # "2023-01-15"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_text)
                if match:
                    date_str = match.group(1)
                    return self._parse_date_string(date_str)
            
        except Exception as e:
            print(f"Error extracting date: {e}")
        
        return datetime.now()
    
    def _parse_date_string(self, date_str: str) -> datetime:
        """Parse various date string formats"""
        date_formats = [
            '%B %d, %Y',      # "January 15, 2023"
            '%b %d, %Y',      # "Jan 15, 2023"
            '%d %B %Y',       # "15 January 2023"
            '%d %b %Y',       # "15 Jan 2023"
            '%m/%d/%Y',       # "01/15/2023"
            '%d/%m/%Y',       # "15/01/2023"
            '%Y-%m-%d',       # "2023-01-15"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If no format matches, return current date
        return datetime.now()
    
    async def _extract_helpful_votes(self, helpful_element: Optional[ElementHandle]) -> int:
        """Extract number of helpful votes"""
        if not helpful_element:
            return 0
        
        try:
            text = await helpful_element.inner_text()
            
            # Look for patterns like "5 people found this helpful"
            match = re.search(r'(\\d+)\\s+people found this helpful', text.lower())
            if match:
                return int(match.group(1))
            
            # Look for just "Helpful" or "One person found this helpful"
            if 'one person' in text.lower():
                return 1
            
        except Exception as e:
            print(f"Error extracting helpful votes: {e}")
        
        return 0
    
    def _clean_review_text(self, text: str) -> str:
        """Clean and normalize review text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\\s+', ' ', text.strip())
        
        # Remove "Read more" links and similar artifacts
        text = re.sub(r'\\s*Read more\\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\\s*Show more\\s*$', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    async def extract_product_info(self, page: Page, asin: str) -> Optional[Product]:
        """
        Extract product information from product detail page
        
        Args:
            page: Playwright page object
            asin: Product ASIN
            
        Returns:
            Product object or None if extraction fails
        """
        try:
            # Extract title
            title_element = await page.query_selector(self.selectors['product_title_detail'])
            title = await title_element.inner_text() if title_element else "Unknown Product"
            title = title.strip()
            
            # Extract image
            image_element = await page.query_selector(self.selectors['product_image'])
            image_url = await image_element.get_attribute('src') if image_element else None
            
            # Extract category
            category_element = await page.query_selector(self.selectors['product_category'])
            category = await category_element.inner_text() if category_element else None
            
            # Extract review stats
            total_reviews_element = await page.query_selector(self.selectors['total_reviews'])
            total_reviews = 0
            if total_reviews_element:
                total_text = await total_reviews_element.inner_text()
                match = re.search(r'([\\d,]+)', total_text.replace(',', ''))
                if match:
                    total_reviews = int(match.group(1))
            
            rating_element = await page.query_selector(self.selectors['average_rating'])
            average_rating = 0.0
            if rating_element:
                rating_text = await rating_element.inner_text()
                match = re.search(r'(\\d+\\.\\d+)', rating_text)
                if match:
                    average_rating = float(match.group(1))
            
            return Product(
                title=title,
                asin=asin,
                url=page.url,
                average_rating=average_rating,
                total_reviews=total_reviews,
                image_url=image_url,
                category=category.strip() if category else None
            )
            
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None
