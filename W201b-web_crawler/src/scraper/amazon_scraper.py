import re
import asyncio
import time
from urllib.parse import urlencode, quote_plus
from typing import List, Optional, Dict, Any
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..models import Review, Product, ScrapingResult, ReviewStats, SearchCriteria, ScrapingConfig
from ..config import AMAZON_SELECTORS, AMAZON_DOMAINS, get_random_user_agent
from ..utils import human_delay, RateLimiter
from .review_extractor import ReviewExtractor


class AmazonScraper:
    """Main Amazon review scraper class"""
    
    def __init__(self, config: ScrapingConfig):
        """
        Initialize the Amazon scraper
        
        Args:
            config: Scraping configuration
        """
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.review_extractor = ReviewExtractor()
        self.rate_limiter = RateLimiter(
            max_requests=60,  # 60 requests per minute
            time_window=60.0
        )
        self.errors: List[str] = []
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self) -> None:
        """Initialize browser and context"""
        try:
            playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=self.config.browser.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            # Create context
            self.context = await self.browser.new_context(
                user_agent=self.config.browser.user_agent or get_random_user_agent(),
                viewport=self.config.browser.viewport,
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                }
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.config.browser.timeout)
            
            # Block unnecessary resources to improve performance
            await self.context.route('**/*', self._route_handler)
            
        except Exception as e:
            error_msg = f"Failed to initialize browser: {e}"
            self.errors.append(error_msg)
            raise RuntimeError(error_msg)
    
    async def _route_handler(self, route, request):
        """Handle routing to block unnecessary resources"""
        resource_type = request.resource_type
        
        # Block images, stylesheets, fonts, and media to speed up scraping
        if resource_type in ['image', 'stylesheet', 'font', 'media']:
            await route.abort()
        else:
            await route.continue_()
    
    async def scrape_reviews(self, search_criteria: SearchCriteria) -> ScrapingResult:
        """
        Main method to scrape Amazon reviews
        
        Args:
            search_criteria: Search and filtering criteria
            
        Returns:
            ScrapingResult with scraped reviews and statistics
        """
        start_time = time.time()
        all_reviews: List[Review] = []
        total_processed = 0
        
        try:
            print(f"Starting scrape for keywords: {', '.join(search_criteria.keywords)}")
            
            # Step 1: Search for products
            products = await self._search_products(search_criteria.keywords)
            print(f"Found {len(products)} products")
            
            # Step 2: Scrape reviews from each product
            for i, product in enumerate(products):
                if search_criteria.max_results and len(all_reviews) >= search_criteria.max_results:
                    break
                
                print(f"Processing product {i + 1}/{len(products)}: {product.title}")
                
                try:
                    # Rate limiting
                    await self.rate_limiter.acquire()
                    
                    product_reviews = await self._scrape_product_reviews(product, search_criteria)
                    all_reviews.extend(product_reviews)
                    total_processed += 1
                    
                    # Add delay between products
                    await human_delay(
                        self.config.rate_limiting.delay_between_requests / 1000.0,
                        self.config.rate_limiting.random_delay_variation * 100
                    )
                    
                except Exception as e:
                    error_msg = f"Error scraping reviews for {product.title}: {e}"
                    self.errors.append(error_msg)
                    print(error_msg)
                    
                    if not self.config.error_handling.continue_on_error:
                        raise
            
            # Step 3: Apply final filtering and generate stats
            filtered_reviews = self._apply_filters(all_reviews, search_criteria)
            stats = self._generate_stats(filtered_reviews)
            
            execution_time = time.time() - start_time
            
            result = ScrapingResult(
                reviews=filtered_reviews,
                stats=stats,
                search_criteria=search_criteria,
                total_processed=total_processed,
                errors=self.errors,
                execution_time=execution_time
            )
            
            print(f"Scraping completed in {execution_time:.2f}s. Found {len(filtered_reviews)} reviews.")
            return result
            
        except Exception as e:
            error_msg = f"Scraping failed: {e}"
            self.errors.append(error_msg)
            raise RuntimeError(error_msg)
    
    async def _search_products(self, keywords: List[str]) -> List[Product]:
        """Search for products on Amazon"""
        page = await self.context.new_page()
        products: List[Product] = []
        
        try:
            # Construct search URL
            search_query = ' '.join(keywords)
            search_params = {'k': search_query}
            search_url = f"{self.config.amazon_domain}/s?{urlencode(search_params)}"
            
            print(f"Searching: {search_url}")
            await page.goto(search_url, wait_until='networkidle')
            
            # Handle anti-bot measures
            if await self._handle_anti_bot(page):
                await page.wait_for_load_state('networkidle')
            
            # Extract product links
            product_elements = await page.query_selector_all(AMAZON_SELECTORS['product_links'])
            
            for element in product_elements[:20]:  # Limit to first 20 products
                try:
                    href = await element.get_attribute('href')
                    title_element = await element.query_selector('span')
                    title = await title_element.inner_text() if title_element else "Unknown Product"
                    
                    if href and title:
                        full_url = href if href.startswith('http') else f"{self.config.amazon_domain}{href}"
                        asin = self._extract_asin_from_url(full_url)
                        
                        if asin:
                            products.append(Product(
                                title=title.strip(),
                                asin=asin,
                                url=full_url,
                                average_rating=0.0,
                                total_reviews=0
                            ))
                
                except Exception as e:
                    print(f"Error extracting product: {e}")
                    continue
            
            return products
            
        finally:
            await page.close()
    
    async def _scrape_product_reviews(self, product: Product, criteria: SearchCriteria) -> List[Review]:
        """Scrape reviews for a specific product"""
        page = await self.context.new_page()
        reviews: List[Review] = []
        
        try:
            # Navigate to reviews page
            reviews_url = f"{self.config.amazon_domain}/product-reviews/{product.asin}"
            
            # Add sorting parameter
            sort_param = self._get_sort_parameter(criteria.sort_by)
            if sort_param:
                reviews_url += f"?sortBy={sort_param}"
            
            await page.goto(reviews_url, wait_until='networkidle')
            
            # Handle anti-bot measures
            await self._handle_anti_bot(page)
            
            # Extract product information if not already available
            if not product.average_rating:
                product_info = await self.review_extractor.extract_product_info(page, product.asin)
                if product_info:
                    product.average_rating = product_info.average_rating
                    product.total_reviews = product_info.total_reviews
            
            # Scrape reviews from multiple pages
            current_page = 1
            max_pages = 10  # Reasonable limit
            
            while current_page <= max_pages and len(reviews) < (criteria.max_results or float('inf')):
                print(f"  Scraping reviews page {current_page}")
                
                # Extract reviews from current page
                page_reviews = await self.review_extractor.extract_reviews_from_page(page, product)
                
                # Apply criteria filtering
                filtered_reviews = [r for r in page_reviews if self._matches_criteria(r, criteria)]
                reviews.extend(filtered_reviews)
                
                # Check for next page
                if not await self._goto_next_page(page):
                    break
                
                current_page += 1
                
                # Rate limiting between pages
                await human_delay(
                    self.config.rate_limiting.delay_between_requests / 2000.0,  # Half delay for pages
                    self.config.rate_limiting.random_delay_variation * 100
                )
            
            return reviews
            
        finally:
            await page.close()
    
    async def _handle_anti_bot(self, page: Page) -> bool:
        """Handle anti-bot detection measures"""
        try:
            # Check for CAPTCHA
            captcha = await page.query_selector(AMAZON_SELECTORS['captcha_image'])
            if captcha:
                print("CAPTCHA detected - waiting for manual resolution...")
                await asyncio.sleep(self.config.error_handling.captcha_timeout / 1000.0)
                return True
            
            # Check for access denied using text content
            try:
                access_denied = await page.query_selector('text=Access Denied')
                sorry_page = await page.query_selector('text=Sorry, we just need to make sure you')
                blocked_page = await page.query_selector('text=Robot Check')
                
                if access_denied or sorry_page or blocked_page:
                    print("Access denied or robot check detected")
                    await asyncio.sleep(10)  # Wait 10 seconds
                    return True
            except:
                # If text selectors fail, check page content directly
                page_content = await page.content()
                if any(phrase in page_content.lower() for phrase in [
                    'access denied', 'robot check', 'sorry, we just need to make sure',
                    'unusual traffic', 'automated requests'
                ]):
                    print("Access denied or robot check detected in page content")
                    await asyncio.sleep(10)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error handling anti-bot measures: {e}")
            return False
    
    def _extract_asin_from_url(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL"""
        # Pattern for ASIN in URL (10 character alphanumeric)
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product-reviews/([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:/|\\?|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_sort_parameter(self, sort_by: str) -> Optional[str]:
        """Get Amazon sort parameter for review sorting"""
        sort_mapping = {
            'helpful': 'helpful',
            'recent': 'recent',
            'rating': None,  # Default sort
            'date': 'recent'
        }
        return sort_mapping.get(sort_by)
    
    def _matches_criteria(self, review: Review, criteria: SearchCriteria) -> bool:
        """Check if review matches filtering criteria"""
        # Rating filter
        if criteria.min_rating and review.rating < criteria.min_rating:
            return False
        if criteria.max_rating and review.rating > criteria.max_rating:
            return False
        
        # Date filter
        if criteria.date_range:
            start_date = criteria.date_range.get('start_date')
            end_date = criteria.date_range.get('end_date')
            
            if start_date and review.date < start_date:
                return False
            if end_date and review.date > end_date:
                return False
        
        # Verified purchase filter
        if criteria.verified_purchase_only and not review.verified_purchase:
            return False
        
        # Review length filter
        if criteria.min_review_length and len(review.text) < criteria.min_review_length:
            return False
        if criteria.max_review_length and len(review.text) > criteria.max_review_length:
            return False
        
        # Helpful votes filter
        if criteria.min_helpful_votes and review.helpful_votes < criteria.min_helpful_votes:
            return False
        
        return True
    
    def _apply_filters(self, reviews: List[Review], criteria: SearchCriteria) -> List[Review]:
        """Apply final filtering and sorting to reviews"""
        # Filter reviews
        filtered = [r for r in reviews if self._matches_criteria(r, criteria)]
        
        # Sort reviews
        sort_key_map = {
            'date': lambda r: r.date,
            'helpful': lambda r: r.helpful_votes,
            'rating': lambda r: r.rating
        }
        
        if criteria.sort_by in sort_key_map:
            reverse = criteria.sort_order == 'desc'
            filtered.sort(key=sort_key_map[criteria.sort_by], reverse=reverse)
        
        # Limit results
        if criteria.max_results:
            filtered = filtered[:criteria.max_results]
        
        return filtered
    
    def _generate_stats(self, reviews: List[Review]) -> ReviewStats:
        """Generate statistics from reviews"""
        stats = ReviewStats()
        
        for review in reviews:
            stats.add_review(review)
        
        return stats
    
    async def _goto_next_page(self, page: Page) -> bool:
        """Navigate to next page of reviews"""
        try:
            next_button = await page.query_selector(AMAZON_SELECTORS['next_page_button'])
            if next_button:
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                return True
            return False
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            return False
    
    async def close(self) -> None:
        """Clean up browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
