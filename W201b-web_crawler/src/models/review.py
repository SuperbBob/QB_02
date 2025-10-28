from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator


class Review(BaseModel):
    """Model representing an Amazon product review"""
    
    id: str = Field(..., description="Unique review ID")
    title: str = Field(..., description="Review title")
    text: str = Field(..., description="Review content/text")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    date: datetime = Field(..., description="Review date")
    reviewer_name: str = Field(..., description="Name of the reviewer")
    verified_purchase: bool = Field(default=False, description="Whether this is a verified purchase")
    helpful_votes: int = Field(default=0, ge=0, description="Number of helpful votes")
    product_asin: str = Field(..., description="Amazon Standard Identification Number")
    product_title: str = Field(..., description="Product title")
    review_url: Optional[str] = Field(None, description="Direct URL to the review")
    images: Optional[List[str]] = Field(default_factory=list, description="Review image URLs")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Product(BaseModel):
    """Model representing an Amazon product"""
    
    title: str = Field(..., description="Product title")
    asin: str = Field(..., description="Amazon Standard Identification Number")
    url: str = Field(..., description="Product URL")
    average_rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average product rating")
    total_reviews: int = Field(default=0, ge=0, description="Total number of reviews")
    price: Optional[str] = Field(None, description="Current product price")
    image_url: Optional[str] = Field(None, description="Main product image URL")
    category: Optional[str] = Field(None, description="Product category")
    
    @validator('asin')
    def validate_asin(cls, v):
        """Validate ASIN format (10 characters, alphanumeric)"""
        if not v or len(v) != 10 or not v.isalnum():
            raise ValueError('ASIN must be 10 alphanumeric characters')
        return v.upper()


class ReviewStats(BaseModel):
    """Statistics about scraped reviews"""
    
    total_reviews: int = Field(default=0, ge=0, description="Total number of reviews")
    average_rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average rating")
    rating_distribution: Dict[int, int] = Field(
        default_factory=dict, 
        description="Distribution of ratings (rating -> count)"
    )
    verified_purchase_count: int = Field(default=0, ge=0, description="Number of verified purchases")
    date_range: Optional[Dict[str, datetime]] = Field(
        None, 
        description="Date range of reviews (earliest and latest)"
    )
    
    def add_review(self, review: Review) -> None:
        """Add a review to the statistics"""
        self.total_reviews += 1
        
        # Update rating distribution
        if review.rating not in self.rating_distribution:
            self.rating_distribution[review.rating] = 0
        self.rating_distribution[review.rating] += 1
        
        # Update verified purchase count
        if review.verified_purchase:
            self.verified_purchase_count += 1
            
        # Update date range
        if self.date_range is None:
            self.date_range = {
                'earliest': review.date,
                'latest': review.date
            }
        else:
            if review.date < self.date_range['earliest']:
                self.date_range['earliest'] = review.date
            if review.date > self.date_range['latest']:
                self.date_range['latest'] = review.date
                
        # Recalculate average rating
        total_rating = sum(rating * count for rating, count in self.rating_distribution.items())
        self.average_rating = total_rating / self.total_reviews
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
