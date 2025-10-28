from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
from .review import Review, ReviewStats


class SearchCriteria(BaseModel):
    """Search and filtering criteria for Amazon reviews"""
    
    keywords: List[str] = Field(..., min_items=1, description="Search keywords")
    category: Optional[str] = Field(None, description="Product category to search in")
    min_rating: Optional[int] = Field(None, ge=1, le=5, description="Minimum star rating")
    max_rating: Optional[int] = Field(None, ge=1, le=5, description="Maximum star rating")
    date_range: Optional[Dict[str, datetime]] = Field(
        None, 
        description="Date range for reviews (start_date and end_date)"
    )
    verified_purchase_only: bool = Field(default=False, description="Only include verified purchases")
    min_review_length: Optional[int] = Field(None, ge=0, description="Minimum review text length")
    max_review_length: Optional[int] = Field(None, ge=0, description="Maximum review text length")
    min_helpful_votes: Optional[int] = Field(None, ge=0, description="Minimum helpful votes")
    max_results: Optional[int] = Field(None, ge=1, description="Maximum number of reviews to scrape")
    max_pages: Optional[int] = Field(default=1, ge=1, le=10, description="Maximum review pages to scrape per product")
    sort_by: Literal['date', 'helpful', 'rating'] = Field(default='helpful', description="Sort criteria")
    sort_order: Literal['asc', 'desc'] = Field(default='desc', description="Sort order")
    
    @validator('max_rating')
    def validate_rating_range(cls, v, values):
        """Ensure max_rating is greater than min_rating"""
        min_rating = values.get('min_rating')
        if min_rating is not None and v is not None and v < min_rating:
            raise ValueError('max_rating must be greater than or equal to min_rating')
        return v
    
    @validator('max_review_length')
    def validate_review_length_range(cls, v, values):
        """Ensure max_review_length is greater than min_review_length"""
        min_length = values.get('min_review_length')
        if min_length is not None and v is not None and v < min_length:
            raise ValueError('max_review_length must be greater than or equal to min_review_length')
        return v


class BrowserConfig(BaseModel):
    """Browser configuration for scraping"""
    
    headless: bool = Field(default=True, description="Run browser in headless mode")
    user_agent: Optional[str] = Field(None, description="Custom user agent string")
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {'width': 1920, 'height': 1080},
        description="Browser viewport size"
    )
    timeout: int = Field(default=30000, ge=1000, description="Page timeout in milliseconds")


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration"""
    
    delay_between_requests: int = Field(
        default=3000, 
        ge=1000, 
        description="Delay between requests in milliseconds"
    )
    max_concurrent_pages: int = Field(
        default=2, 
        ge=1, 
        le=5, 
        description="Maximum concurrent pages"
    )
    respect_robots_txt: bool = Field(
        default=True, 
        description="Respect robots.txt directives"
    )
    random_delay_variation: float = Field(
        default=0.25, 
        ge=0.0, 
        le=1.0, 
        description="Random delay variation (0-1)"
    )


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration"""
    
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=5000, ge=1000, description="Delay between retries in milliseconds")
    continue_on_error: bool = Field(default=True, description="Continue scraping on individual errors")
    captcha_timeout: int = Field(default=30000, ge=5000, description="Timeout for CAPTCHA resolution")


class ScrapingConfig(BaseModel):
    """Complete scraping configuration"""
    
    search_criteria: SearchCriteria
    output_format: Literal['json', 'csv', 'xlsx'] = Field(default='json', description="Output format")
    output_path: Optional[str] = Field(None, description="Custom output file path")
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)
    amazon_domain: str = Field(default='https://www.amazon.com', description="Amazon domain to scrape")


class ScrapingResult(BaseModel):
    """Result of a scraping operation"""
    
    reviews: List[Review] = Field(default_factory=list, description="Scraped reviews")
    stats: ReviewStats = Field(default_factory=ReviewStats, description="Statistics about the reviews")
    search_criteria: SearchCriteria
    scraped_at: datetime = Field(default_factory=datetime.now, description="When the scraping was performed")
    total_processed: int = Field(default=0, ge=0, description="Total number of products processed")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during scraping")
    execution_time: Optional[float] = Field(None, ge=0.0, description="Total execution time in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
