from typing import Dict
from ..models import ScrapingConfig, SearchCriteria, BrowserConfig, RateLimitingConfig, ErrorHandlingConfig

# CSS selectors for Amazon elements
AMAZON_SELECTORS = {
    # Search page selectors
    'search_box': '#twotabsearchtextbox',
    'search_button': '#nav-search-submit-button',
    'product_links': '[data-component-type="s-search-result"] h2 a, [data-cy="title-recipe-title"] a, .s-link-style a',
    'product_titles': '[data-component-type="s-search-result"] h2 a span, [data-cy="title-recipe-title"] span, .s-link-style .a-text-base',
    'product_ratings': '[data-component-type="s-search-result"] .a-icon-alt, .a-icon-star .a-icon-alt',
    'product_prices': '[data-component-type="s-search-result"] .a-price-whole, .a-price .a-offscreen',
    
    # Product page selectors
    'see_all_reviews': '[data-hook="see-all-reviews-link-foot"]',
    'customer_reviews_link': '#reviewsMedley a[href*="customer-reviews"]',
    
    # Reviews page selectors
    'review_containers': '[data-hook="review"]',
    'review_title': '[data-hook="review-title"] > span',
    'review_text': '[data-hook="review-body"] span',
    'review_rating': '[data-hook="review-star-rating"] span.a-icon-alt',
    'review_date': '[data-hook="review-date"]',
    'reviewer_name': '.a-profile-name',
    'verified_purchase': '[data-hook="avp-badge"]',
    'helpful_votes': '[data-hook="helpful-vote-statement"]',
    'review_images': '[data-hook="review-image-tile"] img',
    
    # Pagination
    'next_page_button': 'li.a-last a',
    'pagination_current': '.a-pagination .a-selected',
    
    # Anti-bot detection
    'captcha_image': '.cvf-widget-input-captcha img',
    'captcha_input': '#captchacharacters',
    'robot_checkbox': '#captcha-form input[type="checkbox"]',
    
    # Product info
    'product_title_detail': '#productTitle',
    'product_image': '#landingImage',
    'product_category': '#wayfinding-breadcrumbs_feature_div',
    
    # Review stats
    'total_reviews': '[data-hook="total-review-count"]',
    'average_rating': '[data-hook="rating-out-of-text"]',
}

# Amazon domains for different regions
AMAZON_DOMAINS = {
    'US': 'https://www.amazon.com',
    'UK': 'https://www.amazon.co.uk',
    'DE': 'https://www.amazon.de',
    'FR': 'https://www.amazon.fr',
    'IT': 'https://www.amazon.it',
    'ES': 'https://www.amazon.es',
    'JP': 'https://www.amazon.co.jp',
    'CA': 'https://www.amazon.ca',
    'AU': 'https://www.amazon.com.au',
    'IN': 'https://www.amazon.in',
    'BR': 'https://www.amazon.com.br',
    'MX': 'https://www.amazon.com.mx',
}

# Default scraping configuration
DEFAULT_CONFIG = ScrapingConfig(
    search_criteria=SearchCriteria(
        keywords=["example"],  # Placeholder keyword
        max_results=100,
        sort_by='helpful',
        sort_order='desc'
    ),
    output_format='json',
    browser=BrowserConfig(
        headless=True,
        viewport={'width': 1920, 'height': 1080},
        timeout=30000
    ),
    rate_limiting=RateLimitingConfig(
        delay_between_requests=3000,  # 3 seconds
        max_concurrent_pages=2,
        respect_robots_txt=True,
        random_delay_variation=0.25
    ),
    error_handling=ErrorHandlingConfig(
        max_retries=3,
        retry_delay=5000,  # 5 seconds
        continue_on_error=True,
        captcha_timeout=30000
    ),
    amazon_domain=AMAZON_DOMAINS['US']
)

# Common search filters and sorting options
SORT_OPTIONS = {
    'helpful': 'helpful',
    'recent': 'recent',  
    'top_rated': 'top_rated',
    'lowest_rated': 'lowest_rated'
}

# Review quality indicators
REVIEW_QUALITY_THRESHOLDS = {
    'min_review_length': 50,  # Minimum characters for meaningful review
    'max_review_length': 5000,  # Maximum reasonable review length
    'spam_keywords': [
        'fake', 'bot', 'spam', 'advertisement', 'promotion'
    ]
}
