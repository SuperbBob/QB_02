#!/usr/bin/env python3
"""
Amazon Review Scraper using Requests + BeautifulSoup
Based on successful techniques from amazoncrawler repository

This approach often works better than Playwright for Amazon scraping.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, urljoin
import json
import logging

from ..models import Review, Product, ScrapingResult, ReviewStats, SearchCriteria
from ..utils import human_delay


class RequestsAmazonScraper:
    """Amazon scraper using requests + BeautifulSoup approach"""
    
    def __init__(self, delay_range=(2.0, 4.0)):
        """
        Initialize scraper with session and configuration
        
        Args:
            delay_range: Tuple of (min_delay, max_delay) in seconds
        """
        self.session = requests.Session()
        self.delay_range = delay_range
        self.errors = []
        self.authenticated = False
        self.auth_email = None
        
        # User agents that work well with Amazon
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]
        
        self._setup_session()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _setup_session(self):
        """Configure session with headers and settings"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        # Configure session
        self.session.max_redirects = 3
        
        # Add some cookies to look more legitimate
        self.session.cookies.update({
            'session-id': f'session_{random.randint(100000, 999999)}',
            'ubid-main': f'ubid_{random.randint(100000, 999999)}',
        })
    
    def _random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(*self.delay_range)
        self.logger.info(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)
    
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Get and parse a web page with retries
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(retries):
            try:
                self.logger.info(f"Fetching: {url}")
                
                # Rotate user agent occasionally
                if attempt > 0:
                    self.session.headers['User-Agent'] = random.choice(self.user_agents)
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                # Check if we got blocked
                if self._is_blocked_response(response):
                    self.logger.warning("Detected blocked response, retrying...")
                    if attempt < retries - 1:
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        return None
                
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
                
            except requests.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    self.errors.append(f"Failed to fetch {url}: {e}")
        
        return None
    
    def _is_blocked_response(self, response: requests.Response) -> bool:
        """Check if response indicates we're blocked"""
        content = response.text.lower()
        blocked_indicators = [
            'access denied', 'robot check', 'captcha', 
            'unusual traffic', 'automated requests',
            'sorry, we just need to make sure you',
            'enter the characters you see below'
        ]
        
        for indicator in blocked_indicators:
            if indicator in content:
                return True
        
        # Check for specific blocked page titles
        if response.status_code == 503 or 'Service Unavailable' in response.text:
            return True
            
        return False
    
    def search_products(self, keywords: List[str], max_products: int = 20) -> List[Product]:
        """
        Search for products on Amazon
        
        Args:
            keywords: Search keywords
            max_products: Maximum number of products to find
            
        Returns:
            List of Product objects
        """
        products = []
        search_query = ' '.join(keywords)
        
        # Build search URL
        params = {
            'k': search_query,
            'ref': 'sr_pg_1'
        }
        search_url = f"https://www.amazon.com/s?{urlencode(params)}"
        
        self.logger.info(f"Searching for: {search_query}")
        soup = self._get_page(search_url)
        
        if not soup:
            self.logger.error("Failed to get search results page")
            return products
        
        # Multiple selector strategies for product links
        product_selectors = [
            'div[data-component-type="s-search-result"] h2.a-size-mini a',
            'div[data-component-type="s-search-result"] h2 a',
            '.s-result-item h2 a',
            'h2.a-size-mini a',
            'a[href*="/dp/"]'
        ]
        
        found_links = []
        for selector in product_selectors:
            links = soup.select(selector)
            if links:
                self.logger.info(f"Found {len(links)} products using selector: {selector}")
                found_links = links
                break
        
        if not found_links:
            self.logger.warning("No product links found")
            return products
        
        # Extract product information with ASIN deduplication
        seen_asins = set()
        for link in found_links[:max_products * 2]:  # Process more to find unique ASINs
            try:
                href = link.get('href')
                if not href:
                    continue
                
                # Debug: Log first few hrefs to understand the format  
                # (Remove debug logging to reduce noise)
                
                # Extract ASIN from various URL formats
                asin = None
                
                # Method 1: Direct Amazon URLs
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', href)
                if asin_match:
                    asin = asin_match.group(1)
                
                # Method 2: Alternative Amazon URL patterns
                if not asin:
                    asin_match = re.search(r'/gp/product/([A-Z0-9]{10})', href)
                    if asin_match:
                        asin = asin_match.group(1)
                
                # Method 3: ASIN in query parameters
                if not asin:
                    asin_match = re.search(r'[?&]ASIN=([A-Z0-9]{10})', href)
                    if asin_match:
                        asin = asin_match.group(1)
                
                # Method 4: Extract from Amazon tracking URLs 
                if not asin:
                    # Look for embedded amazon.com/dp/ URLs in tracking links
                    embedded_match = re.search(r'amazon\.com/dp/([A-Z0-9]{10})', href)
                    if embedded_match:
                        asin = embedded_match.group(1)
                
                # Method 5: ASIN in pd_rd_i parameter (common in tracking URLs)
                if not asin:
                    asin_match = re.search(r'pd_rd_i=([A-Z0-9]{10})', href)
                    if asin_match:
                        asin = asin_match.group(1)
                    
                if not asin:
                    if len(products) < 2:
                        self.logger.info(f"No ASIN found in: {href[:100]}...")
                    continue
                
                # Skip if we've already seen this ASIN (deduplication)
                if asin in seen_asins:
                    if len(products) < 2:
                        self.logger.info(f"Duplicate ASIN {asin} skipped")
                    continue
                    
                seen_asins.add(asin)
                title = link.get_text(strip=True)
                
                # If title is empty, try to find it in nearby elements or use ASIN as fallback
                if not title:
                    # Try to find title in parent or sibling elements
                    parent = link.parent
                    if parent:
                        # Look for common Amazon title selectors
                        title_selectors = [
                            'h2', '.s-size-mini', '.s-size-base-plus', 
                            'span[data-component-type="s-product-image"]', 
                            '.a-text-base', '.s-link-style'
                        ]
                        
                        for selector in title_selectors:
                            title_elem = parent.select_one(selector)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                if title:
                                    break
                
                # Final fallback: use a placeholder title with ASIN
                if not title or len(title.strip()) == 0:
                    title = f"Amazon Product {asin}"
                
                # Debug: Show what we got for title 
                # (Remove debug logging to reduce noise)
                
                # Create the product (we should have a title now)
                full_url = f"https://www.amazon.com/dp/{asin}"  # Use clean direct URL
                product = Product(
                    title=title,
                    asin=asin,
                    url=full_url,
                    average_rating=0.0,
                    total_reviews=0
                )
                products.append(product)
                self.logger.info(f"✅ Added product: {title[:50]}... (ASIN: {asin})")
                
                # Stop when we have enough unique products
                if len(products) >= max_products:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error extracting product: {e}")
                continue
        
        self.logger.info(f"Found {len(products)} products total")
        return products
    
    def get_product_reviews(self, product: Product, max_reviews: int = 50) -> List[Review]:
        """
        Get reviews for a specific product from the main product page
        
        Args:
            product: Product object
            max_reviews: Maximum number of reviews to get
            
        Returns:
            List of Review objects
        """
        reviews = []
        
        # Build product page URL (not dedicated reviews page)
        product_url = f"https://www.amazon.com/dp/{product.asin}"
        
        self.logger.info(f"Getting reviews from product page: {product.title[:50]}...")
        
        # Add delay before requesting
        self._random_delay()
        
        soup = self._get_page(product_url)
        if not soup:
            self.logger.error(f"Failed to get product page for {product.asin}")
            return reviews
        
        # Debug: Check what we actually got from Amazon
        page_title = soup.find('title')
        if page_title:
            self.logger.info(f"Page title: {page_title.get_text()[:100]}...")
        
        # Look for review summary data first (this is what Amazon actually shows)
        try:
            # Get overall rating
            rating_elem = soup.select_one('[data-hook="average-star-rating"]')
            overall_rating = 0
            if rating_elem:
                rating_text = rating_elem.get('class', [])
                for cls in rating_text:
                    if 'a-star-medium-' in cls:
                        rating_str = cls.split('a-star-medium-')[-1].replace('-', '.')
                        try:
                            overall_rating = float(rating_str)
                        except:
                            pass
            
            # Get total review count
            total_reviews = 0
            review_count_elem = soup.select_one('[data-hook="total-review-count"]')
            if review_count_elem:
                count_text = review_count_elem.get_text()
                count_match = re.search(r'([\d,]+)', count_text.replace(',', ''))
                if count_match:
                    total_reviews = int(count_match.group(1))
                    
            self.logger.info(f"Found review summary: {overall_rating}/5.0 stars, {total_reviews} total reviews")
            
        except Exception as e:
            self.logger.error(f"Error extracting review summary: {e}")
            
        # Check if we got blocked or redirected (less aggressive check)
        page_text = soup.get_text().lower()
        if 'robot check' in page_text or 'captcha' in page_text:
            self.logger.warning(f"Blocking detected on {product_url}")
        elif 'customer reviews' in page_text:
            self.logger.info(f"✅ Found customer reviews section!")
        
        # Save HTML for debugging (first product only)
        if hasattr(self, '_debug_saved') is False:
            with open(f'debug_amazon_page_{product.asin}.html', 'w', encoding='utf-8') as f:
                f.write(str(soup))
            self.logger.info(f"Saved debug HTML to debug_amazon_page_{product.asin}.html")
            self._debug_saved = True
        
        # Look for actual review elements on the product page
        review_containers = []
        
        # Amazon shows different types of reviews on product pages
        review_selectors = [
            # Main review containers
            'div[data-hook="review"]',
            '[data-hook="review-body"]', 
            '.cr-original-review-text',
            # Featured/highlight reviews
            '.cr-widget-FeaturedReviews .review',
            '[data-hook="cmps-review-body"]',
            # Any review-like containers
            '.review-item',
            '.customer-review',
            # Text content that looks like reviews
            'span[data-hook="review-body"] span'
        ]
        
        for selector in review_selectors:
            try:
                containers = soup.select(selector)
                if containers:
                    self.logger.info(f"Found {len(containers)} elements with selector: {selector}")
                    review_containers.extend(containers)
                    break  # Use first successful selector
            except Exception as e:
                continue
        
        # If no containers found, look for review-like text content
        if not review_containers:
            self.logger.info("No specific review containers found, searching for review-like content")
            
            # Look for customer review section and extract text
            review_section = soup.find(id="customer-reviews")
            if not review_section:
                review_section = soup.find("h2", string=re.compile("Customer reviews", re.I))
                if review_section:
                    review_section = review_section.find_parent()
            
            if review_section:
                # Find all text elements in the review section
                text_elements = review_section.find_all(['div', 'span', 'p'], 
                                                      string=re.compile(r'.{30,}'))
                review_containers = text_elements[:5]  # Limit to 5 elements
                self.logger.info(f"Found {len(review_containers)} text elements in review section")
        
        self.logger.info(f"Processing {len(review_containers)} potential review elements")
        
        # Initialize reviews list before processing
        reviews = []
        
        for container in review_containers:
            try:
                review = self._extract_review_from_container(container, product)
                if review:
                    reviews.append(review)
                    # Stop when we have enough successful reviews
                    if len(reviews) >= max_reviews:
                        break
            except Exception as e:
                self.logger.error(f"Error extracting review data: {e}")
                continue
        
        self.logger.info(f"Successfully extracted {len(reviews)} reviews")
        return reviews
    
    def get_product_reviews_paginated(self, product: Product, max_reviews: int = 50, max_pages: int = 1) -> List[Review]:
        """
        Get reviews for a specific product using dedicated review pages with pagination
        
        Args:
            product: Product object
            max_reviews: Maximum number of reviews to get
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of Review objects
        """
        reviews = []
        
        self.logger.info(f"Getting reviews from {max_pages} page(s): {product.title[:50]}...")
        
        for page_num in range(1, max_pages + 1):
            # Stop if we have enough reviews
            if len(reviews) >= max_reviews:
                break
            
            # Build dedicated review page URL with pagination
            reviews_url = f"https://www.amazon.com/product-reviews/{product.asin}/ref=cm_cr_dp_d_show_all_btm"
            if page_num > 1:
                reviews_url += f"?pageNumber={page_num}"
            
            self.logger.info(f"Scraping page {page_num}/{max_pages}: {reviews_url}")
            
            # Add delay before requesting
            self._random_delay()
            
            try:
                soup = self._get_page(reviews_url)
                if not soup:
                    self.logger.warning(f"Failed to get page {page_num}")
                    continue
                
                # Check if we got blocked or redirected
                page_title = soup.find('title')
                if page_title and any(blocked in page_title.get_text().lower() for blocked in ['robot', 'captcha', 'access denied', 'sign in']):
                    self.logger.warning(f"Possible blocking detected on page {page_num}")
                    break
                
                # Extract reviews from this page
                page_reviews = self._extract_reviews_from_review_page(soup, product, max_reviews - len(reviews))
                
                if not page_reviews:
                    self.logger.info(f"No reviews found on page {page_num}, stopping pagination")
                    break
                    
                reviews.extend(page_reviews)
                self.logger.info(f"Page {page_num}: Found {len(page_reviews)} reviews (total: {len(reviews)})")
                
                # Check if there's a next page
                if page_num < max_pages:
                    next_page_link = soup.select_one('li.a-last a, .a-pagination .a-last a')
                    if not next_page_link or 'a-disabled' in next_page_link.get('class', []):
                        self.logger.info(f"No more pages available after page {page_num}")
                        break
                
            except Exception as e:
                self.logger.error(f"Error scraping page {page_num}: {e}")
                break
        
        self.logger.info(f"Successfully extracted {len(reviews)} reviews from {page_num} pages")
        return reviews[:max_reviews]  # Ensure we don't exceed the limit

    def _extract_reviews_from_review_page(self, soup: BeautifulSoup, product: Product, max_reviews: int) -> List[Review]:
        """Extract reviews from a dedicated review page"""
        reviews = []
        
        # Selectors for review page elements (different from product page)
        review_selectors = [
            '[data-hook="review"]',  # Main review containers
            '.cr-original-review-text',  # Review text containers
            '.review-item',  # Alternative review containers
        ]
        
        review_containers = []
        for selector in review_selectors:
            try:
                containers = soup.select(selector)
                if containers:
                    self.logger.info(f"Found {len(containers)} review containers with selector: {selector}")
                    review_containers = containers
                    break
            except Exception as e:
                continue
        
        if not review_containers:
            self.logger.warning("No review containers found on review page")
            return reviews
        
        # Extract reviews from containers
        for container in review_containers:
            try:
                review = self._extract_review_from_review_container(container, product)
                if review:
                    reviews.append(review)
                    if len(reviews) >= max_reviews:
                        break
            except Exception as e:
                self.logger.error(f"Error extracting review: {e}")
                continue
                
        return reviews

    def _extract_review_from_review_container(self, container: BeautifulSoup, product: Product) -> Optional[Review]:
        """Extract review data from a review page container (different selectors than product page)"""
        try:
            from datetime import datetime
            import random
            import re
            
            # Extract title (review page has different structure)
            title_elem = container.select_one('[data-hook="review-title"] span:not([class*="a-icon"])')
            if not title_elem:
                title_elem = container.select_one('.cr-original-review-text')
            title = title_elem.get_text(strip=True) if title_elem else "Customer Review"
            
            # Remove common prefixes
            title = re.sub(r'^(Verified Purchase\\s*)?(.+)', r'\\2', title).strip()
            
            # Extract review text (review page has cleaner text)
            text_elem = container.select_one('[data-hook="review-body"] span')
            if not text_elem:
                text_elem = container.select_one('.cr-original-review-text')
            text = text_elem.get_text(strip=True) if text_elem else ""
            
            # Extract rating
            rating = 5  # Default rating
            rating_elem = container.select_one('[data-hook="review-star-rating"], .cr-original-review-text .a-icon-star')
            if rating_elem:
                rating_text = rating_elem.get('class', [])
                for cls in rating_text:
                    if 'a-star-' in cls:
                        rating_match = re.search(r'a-star-(\\d+)', cls)
                        if rating_match:
                            extracted_rating = int(rating_match.group(1))
                            if 1 <= extracted_rating <= 5:
                                rating = extracted_rating
                                break
            
            # Extract reviewer name
            reviewer_elem = container.select_one('[data-hook="review-author"] span')
            reviewer_name = reviewer_elem.get_text(strip=True) if reviewer_elem else "Amazon Customer"
            
            # Extract date
            date_elem = container.select_one('[data-hook="review-date"]')
            review_date = datetime.now()
            if date_elem:
                try:
                    date_text = date_elem.get_text(strip=True)
                    # Parse "Reviewed in the United States on March 15, 2024"
                    date_match = re.search(r'on (.+)', date_text)
                    if date_match:
                        date_str = date_match.group(1)
                        review_date = datetime.strptime(date_str, '%B %d, %Y')
                except:
                    pass  # Use default date if parsing fails
            
            # Extract helpful votes
            helpful_elem = container.select_one('[data-hook="helpful-vote-statement"]')
            helpful_votes = 0
            if helpful_elem:
                helpful_text = helpful_elem.get_text()
                helpful_match = re.search(r'(\\d+)', helpful_text)
                if helpful_match:
                    helpful_votes = int(helpful_match.group(1))
            
            # Only return review if we have substantial content
            if text and len(text.strip()) > 20:
                return Review(
                    id=f"R{random.randint(10000, 99999)}",
                    title=title,
                    text=text,
                    rating=rating,
                    date=review_date,
                    reviewer_name=reviewer_name,
                    verified_purchase=True,  # Most reviews on review pages are verified
                    helpful_votes=helpful_votes,
                    product_asin=product.asin,
                    product_title=product.title
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error in _extract_review_from_review_container: {e}")
            return None
    
    def authenticate_amazon(self, email: str, password: str) -> bool:
        """
        Authenticate with Amazon to access review pages
        
        ⚠️  WARNING: This may violate Amazon's Terms of Service
        Use at your own risk and ensure compliance with applicable laws
        
        Args:
            email: Amazon account email
            password: Amazon account password
            
        Returns:
            bool: True if authentication successful
        """
        try:
            self.logger.info("🔐 Attempting Amazon authentication...")
            self.logger.warning("⚠️  WARNING: Automated login may violate Amazon's Terms of Service")
            
            # Step 1: Get login page
            login_url = "https://www.amazon.com/ap/signin"
            self.logger.info(f"Fetching login page: {login_url}")
            
            response = self.session.get(login_url, timeout=self.timeout)
            if response.status_code != 200:
                self.logger.error(f"Failed to access login page: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Step 2: Extract form parameters
            form = soup.find('form', {'name': 'signIn'})
            if not form:
                self.logger.error("Login form not found")
                return False
            
            # Extract hidden form fields
            form_data = {}
            for input_field in form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    form_data[name] = value
            
            # Set credentials
            form_data['email'] = email
            form_data['password'] = password
            
            # Step 3: Submit login form
            login_action = form.get('action', '/ap/signin')
            if not login_action.startswith('http'):
                login_action = 'https://www.amazon.com' + login_action
            
            self.logger.info("Submitting login credentials...")
            login_response = self.session.post(
                login_action,
                data=form_data,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Step 4: Check authentication status
            if self._check_authentication_status():
                self.authenticated = True
                self.auth_email = email
                self.logger.info("✅ Amazon authentication successful!")
                return True
            else:
                self.logger.error("❌ Amazon authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def _check_authentication_status(self) -> bool:
        """Check if we're successfully authenticated with Amazon"""
        try:
            # Test authentication by accessing account page
            test_url = "https://www.amazon.com/gp/css/homepage.html"
            response = self.session.get(test_url, timeout=self.timeout)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for account indicators
                account_indicators = [
                    'nav-link-accountList',
                    'nav-line-1-container',
                    'Hello,'
                ]
                
                page_text = soup.get_text()
                for indicator in account_indicators:
                    if indicator in str(soup) or 'Hello,' in page_text:
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking authentication: {e}")
            return False
    
    def get_authenticated_reviews(self, product: Product, max_reviews: int = 50) -> List[Review]:
        """
        Get reviews using authenticated session (can access more reviews)
        
        Args:
            product: Product object
            max_reviews: Maximum number of reviews to get
            
        Returns:
            List of Review objects
        """
        if not self.authenticated:
            self.logger.warning("Not authenticated - falling back to standard review extraction")
            return self.get_product_reviews(product, max_reviews)
        
        reviews = []
        
        # Try accessing the full reviews page (requires authentication)
        reviews_url = f"https://www.amazon.com/product-reviews/{product.asin}/ref=cm_cr_dp_d_show_all_btm"
        
        self.logger.info(f"Getting authenticated reviews for: {product.title[:50]}...")
        
        # Add delay before requesting reviews
        self._random_delay()
        
        soup = self._get_page(reviews_url)
        if not soup:
            self.logger.error(f"Failed to get reviews page for {product.asin}")
            return reviews
        
        # Check if we got the reviews page or were redirected to login
        if 'ap/signin' in soup.find('title', string=True) or 'Sign in' in soup.get_text():
            self.logger.warning("Authentication may have expired - got login page")
            return self.get_product_reviews(product, max_reviews)  # Fallback
        
        # Extract reviews from the dedicated reviews page
        review_containers = soup.select('[data-hook="review"]')
        
        if not review_containers:
            # Try alternative selectors for authenticated review pages
            review_containers = soup.select('.review')
        
        self.logger.info(f"Found {len(review_containers)} review containers on authenticated page")
        
        # Initialize reviews list before processing
        reviews = []
        
        for container in review_containers:
            try:
                review = self._extract_authenticated_review(container, product)
                if review:
                    reviews.append(review)
                    # Stop when we have enough successful reviews
                    if len(reviews) >= max_reviews:
                        break
            except Exception as e:
                self.logger.error(f"Error extracting authenticated review: {e}")
                continue
        
        self.logger.info(f"Successfully extracted {len(reviews)} authenticated reviews")
        return reviews
    
    def _extract_authenticated_review(self, container: BeautifulSoup, product: Product) -> Optional[Review]:
        """Extract review data from authenticated review page"""
        try:
            # Extract title
            title_elem = container.select_one('[data-hook="review-title"] span')
            title = title_elem.get_text(strip=True) if title_elem else "Customer Review"
            
            # Extract review text
            text_elem = container.select_one('[data-hook="review-body"] span')
            review_text = text_elem.get_text(strip=True) if text_elem else ""
            
            # Extract rating
            rating_elem = container.select_one('[data-hook="review-star-rating"] .a-icon-alt')
            rating = 5  # Default
            if rating_elem:
                rating_text = rating_elem.get_text() or rating_elem.get('alt', '')
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    rating = int(float(rating_match.group(1)))
            
            # Extract reviewer name
            name_elem = container.select_one('[data-hook="review-author"] .a-profile-name')
            reviewer_name = name_elem.get_text(strip=True) if name_elem else "Amazon Customer"
            
            # Extract date
            date_elem = container.select_one('[data-hook="review-date"]')
            review_date = datetime.now()
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Parse "Reviewed in the United States on January 1, 2024"
                date_match = re.search(r'(\w+ \d+, \d{4})', date_text)
                if date_match:
                    try:
                        review_date = datetime.strptime(date_match.group(1), '%B %d, %Y')
                    except:
                        pass
            
            # Extract helpful votes
            helpful_elem = container.select_one('[data-hook="helpful-vote-statement"]')
            helpful_votes = 0
            if helpful_elem:
                helpful_text = helpful_elem.get_text(strip=True)
                helpful_match = re.search(r'(\d+)', helpful_text)
                if helpful_match:
                    helpful_votes = int(helpful_match.group(1))
            
            # Check verified purchase
            verified_elem = container.select_one('[data-hook="avp-badge"]')
            verified = verified_elem is not None
            
            # Only return review if we have substantial text
            if review_text and len(review_text.strip()) > 20:
                return Review(
                    id=f"R{random.randint(10000, 99999)}",
                    title=title,
                    text=review_text,
                    rating=rating,
                    date=review_date,
                    reviewer_name=reviewer_name,
                    verified_purchase=verified,
                    helpful_votes=helpful_votes,
                    product_asin=product.asin,
                    product_title=product.title
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in _extract_authenticated_review: {e}")
            return None
    
    def _extract_review_from_container(self, container: BeautifulSoup, product: Product) -> Optional[Review]:
        """Extract review data from a review container"""
        try:
            # Extract title
            title_elem = container.select_one('[data-hook="review-title"] span')
            if not title_elem:
                title_elem = container.select_one('.review-title')
            title = title_elem.get_text(strip=True) if title_elem else "No Title"
            
            # Extract review text
            text_elem = container.select_one('[data-hook="review-body"] span')
            if not text_elem:
                text_elem = container.select_one('.review-text')
            text = text_elem.get_text(strip=True) if text_elem else ""
            
            # Extract rating
            rating_elem = container.select_one('[data-hook="review-star-rating"] span')
            if not rating_elem:
                rating_elem = container.select_one('.a-icon-star')
            
            rating = 5  # Default rating (must be 1-5 for Pydantic validation)
            if rating_elem:
                rating_text = rating_elem.get('title') or rating_elem.get_text()
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    extracted_rating = int(float(rating_match.group(1)))
                    if 1 <= extracted_rating <= 5:  # Ensure valid rating range
                        rating = extracted_rating
            
            # Extract date
            date_elem = container.select_one('[data-hook="review-date"]')
            review_date = datetime.now()
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                date_match = re.search(r'(\w+ \d+, \d{4})', date_text)
                if date_match:
                    try:
                        review_date = datetime.strptime(date_match.group(1), '%B %d, %Y')
                    except:
                        pass
            
            # Extract reviewer name
            reviewer_elem = container.select_one('[data-hook="review-author"]')
            if not reviewer_elem:
                reviewer_elem = container.select_one('.a-profile-name')
            reviewer_name = reviewer_elem.get_text(strip=True) if reviewer_elem else "Anonymous"
            
            # Check verified purchase
            verified_elem = container.select_one('[data-hook="avp-badge"]')
            verified_purchase = verified_elem is not None
            
            # Extract helpful votes
            helpful_elem = container.select_one('[data-hook="helpful-vote-statement"]')
            helpful_votes = 0
            if helpful_elem:
                helpful_text = helpful_elem.get_text(strip=True)
                helpful_match = re.search(r'(\d+)', helpful_text)
                if helpful_match:
                    helpful_votes = int(helpful_match.group(1))
            
            # Create review object
            review = Review(
                id=f"R{random.randint(10000, 99999)}",
                title=title,
                text=text,
                rating=rating,
                date=review_date,
                reviewer_name=reviewer_name,
                verified_purchase=verified_purchase,
                helpful_votes=helpful_votes,
                product_asin=product.asin,
                product_title=product.title
            )
            
            return review
            
        except Exception as e:
            self.logger.error(f"Error extracting review data: {e}")
            return None
    
    def scrape_reviews(self, criteria: SearchCriteria) -> ScrapingResult:
        """
        Main method to scrape reviews based on criteria
        
        Args:
            criteria: Search criteria
            
        Returns:
            ScrapingResult object
        """
        start_time = time.time()
        all_reviews = []
        
        self.logger.info(f"Starting scrape for keywords: {criteria.keywords}")
        
        try:
            # Step 1: Search for products  
            products = self.search_products(criteria.keywords, max_products=5)
            
            if not products:
                self.logger.warning("No products found")
                return self._create_empty_result(criteria, time.time() - start_time)
            
            # Step 2: Get reviews from products (with proper max_results handling)
            remaining_reviews = criteria.max_results or 50
            for i, product in enumerate(products):
                if remaining_reviews <= 0:
                    self.logger.info(f"Reached max_results limit ({criteria.max_results}), stopping")
                    break
                
                self.logger.info(f"Processing product {i+1}/{len(products)}: {product.title[:50]}...")
                
                try:
                    # Calculate how many reviews to get from this product
                    reviews_to_get = min(remaining_reviews, 10)  # Max 10 per product
                    
                    # Use paginated scraping if max_pages > 1
                    if criteria.max_pages and criteria.max_pages > 1:
                        product_reviews = self.get_product_reviews_paginated(product, reviews_to_get, criteria.max_pages)
                    else:
                        product_reviews = self.get_product_reviews(product, reviews_to_get)
                    
                    # Apply filtering
                    filtered_reviews = self._apply_criteria_filter(product_reviews, criteria)
                    
                    # Only take what we need to reach max_results
                    reviews_to_add = filtered_reviews[:remaining_reviews]
                    all_reviews.extend(reviews_to_add)
                    remaining_reviews -= len(reviews_to_add)
                    
                    self.logger.info(f"Added {len(reviews_to_add)} reviews from this product (remaining: {remaining_reviews})")
                    
                    # Stop if we have enough reviews
                    if remaining_reviews <= 0:
                        break
                    
                    # Delay between products
                    if i < len(products) - 1:  # Don't delay after last product
                        self._random_delay()
                        
                except Exception as e:
                    error_msg = f"Error processing product {product.title}: {e}"
                    self.logger.error(error_msg)
                    self.errors.append(error_msg)
                    continue
            
            # Step 3: Final filtering and sorting
            final_reviews = self._apply_final_processing(all_reviews, criteria)
            
            # Step 4: Generate statistics
            stats = self._generate_stats(final_reviews)
            
            execution_time = time.time() - start_time
            
            result = ScrapingResult(
                reviews=final_reviews,
                stats=stats,
                search_criteria=criteria,
                total_processed=len(products),
                errors=self.errors,
                execution_time=execution_time
            )
            
            self.logger.info(f"Scraping completed! Found {len(final_reviews)} reviews in {execution_time:.1f}s")
            return result
            
        except Exception as e:
            error_msg = f"Scraping failed: {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return self._create_empty_result(criteria, time.time() - start_time)
    
    def _apply_criteria_filter(self, reviews: List[Review], criteria: SearchCriteria) -> List[Review]:
        """Apply search criteria filtering to reviews"""
        filtered = []
        
        for review in reviews:
            # Rating filter
            if criteria.min_rating and review.rating < criteria.min_rating:
                continue
            if criteria.max_rating and review.rating > criteria.max_rating:
                continue
            
            # Date filter
            if criteria.date_range:
                start_date = criteria.date_range.get('start_date')
                end_date = criteria.date_range.get('end_date')
                
                if start_date and review.date < start_date:
                    continue
                if end_date and review.date > end_date:
                    continue
            
            # Verified purchase filter
            if criteria.verified_purchase_only and not review.verified_purchase:
                continue
            
            # Review length filter
            if criteria.min_review_length and len(review.text) < criteria.min_review_length:
                continue
            if criteria.max_review_length and len(review.text) > criteria.max_review_length:
                continue
            
            # Helpful votes filter
            if criteria.min_helpful_votes and review.helpful_votes < criteria.min_helpful_votes:
                continue
            
            filtered.append(review)
        
        return filtered
    
    def _apply_final_processing(self, reviews: List[Review], criteria: SearchCriteria) -> List[Review]:
        """Apply final sorting and limiting"""
        # Sort reviews
        if criteria.sort_by == 'date':
            reviews.sort(key=lambda r: r.date, reverse=(criteria.sort_order == 'desc'))
        elif criteria.sort_by == 'helpful':
            reviews.sort(key=lambda r: r.helpful_votes, reverse=(criteria.sort_order == 'desc'))
        elif criteria.sort_by == 'rating':
            reviews.sort(key=lambda r: r.rating, reverse=(criteria.sort_order == 'desc'))
        
        # Limit results
        if criteria.max_results:
            reviews = reviews[:criteria.max_results]
        
        return reviews
    
    def _generate_stats(self, reviews: List[Review]) -> ReviewStats:
        """Generate statistics from reviews"""
        stats = ReviewStats()
        for review in reviews:
            stats.add_review(review)
        return stats
    
    def _create_empty_result(self, criteria: SearchCriteria, execution_time: float) -> ScrapingResult:
        """Create empty result for failed scrapes"""
        return ScrapingResult(
            reviews=[],
            stats=ReviewStats(),
            search_criteria=criteria,
            total_processed=0,
            errors=self.errors,
            execution_time=execution_time
        )
