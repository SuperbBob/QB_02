#!/usr/bin/env python3
"""
Advanced Amazon Review Scraper Example

This example demonstrates advanced usage including:
- Date range filtering
- Multiple export formats
- Custom browser configuration
- Error handling
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from src.models import (
    SearchCriteria, ScrapingConfig, 
    BrowserConfig, RateLimitingConfig, ErrorHandlingConfig
)
from src.scraper import AmazonScraper
from src.utils import export_to_json, export_to_csv, export_to_xlsx, create_summary_report


async def scrape_with_date_filter():
    """Example: Scrape reviews from the last 6 months only"""
    
    # Date range: last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    search_criteria = SearchCriteria(
        keywords=["gaming laptop", "rtx"],
        min_rating=3,
        date_range={
            'start_date': start_date,
            'end_date': end_date
        },
        max_results=75,
        sort_by="recent",
        sort_order="desc"
    )
    
    config = ScrapingConfig(
        search_criteria=search_criteria,
        output_format="xlsx"
    )
    
    print("Scraping gaming laptop reviews from last 6 months...")
    
    async with AmazonScraper(config) as scraper:
        result = await scraper.scrape_reviews(search_criteria)
    
    # Export to multiple formats
    await export_to_json(result, "gaming_laptops.json")
    await export_to_csv(result.reviews, "gaming_laptops.csv")
    await export_to_xlsx(result, "gaming_laptops.xlsx")
    
    print(f"Found {len(result.reviews)} recent reviews")
    return result


async def scrape_with_custom_config():
    """Example: Custom browser and rate limiting configuration"""
    
    search_criteria = SearchCriteria(
        keywords=["coffee maker"],
        min_rating=4,
        verified_purchase_only=True,
        min_helpful_votes=5,  # Reviews with at least 5 helpful votes
        max_results=30
    )
    
    # Custom browser configuration
    browser_config = BrowserConfig(
        headless=False,  # Run with GUI for debugging
        viewport={'width': 1366, 'height': 768},
        timeout=45000  # 45 second timeout
    )
    
    # Conservative rate limiting
    rate_config = RateLimitingConfig(
        delay_between_requests=5000,  # 5 seconds between requests
        max_concurrent_pages=1,  # Single page at a time
        random_delay_variation=0.5  # 50% variation
    )
    
    # Robust error handling
    error_config = ErrorHandlingConfig(
        max_retries=5,
        retry_delay=10000,  # 10 second retry delay
        continue_on_error=True,
        captcha_timeout=60000  # 1 minute for CAPTCHA
    )
    
    config = ScrapingConfig(
        search_criteria=search_criteria,
        output_format="json",
        browser=browser_config,
        rate_limiting=rate_config,
        error_handling=error_config
    )
    
    print("Scraping with conservative rate limiting...")
    
    async with AmazonScraper(config) as scraper:
        result = await scraper.scrape_reviews(search_criteria)
    
    await export_to_json(result, "coffee_makers_conservative.json")
    
    print(f"Found {len(result.reviews)} high-quality reviews")
    return result


async def scrape_multiple_products():
    """Example: Scrape reviews for multiple product categories"""
    
    product_categories = [
        {
            "name": "smartphones",
            "keywords": ["smartphone", "iPhone", "Samsung Galaxy"],
            "min_rating": 4
        },
        {
            "name": "tablets", 
            "keywords": ["tablet", "iPad", "Android tablet"],
            "min_rating": 3
        },
        {
            "name": "smartwatches",
            "keywords": ["smartwatch", "Apple Watch", "fitness tracker"],
            "min_rating": 4
        }
    ]
    
    all_results = []
    
    for category in product_categories:
        print(f"\\nScraping {category['name']}...")
        
        search_criteria = SearchCriteria(
            keywords=category["keywords"],
            min_rating=category["min_rating"],
            verified_purchase_only=True,
            max_results=25  # Smaller batch per category
        )
        
        config = ScrapingConfig(
            search_criteria=search_criteria,
            output_format="json"
        )
        
        async with AmazonScraper(config) as scraper:
            result = await scraper.scrape_reviews(search_criteria)
        
        # Export individual category results
        await export_to_json(result, f"{category['name']}_reviews.json")
        all_results.append((category['name'], result))
        
        print(f"  Found {len(result.reviews)} reviews for {category['name']}")
        
        # Small delay between categories
        await asyncio.sleep(2)
    
    # Create combined summary
    print(f"\\nSummary across all categories:")
    for name, result in all_results:
        print(f"  {name}: {len(result.reviews)} reviews, avg rating {result.stats.average_rating:.2f}")
    
    return all_results


async def main():
    """Run all advanced examples"""
    
    print("Amazon Review Scraper - Advanced Examples")
    print("=" * 50)
    
    try:
        # Example 1: Date filtering
        print("\\n1. Scraping with date filter...")
        result1 = await scrape_with_date_filter()
        
        # Example 2: Custom configuration  
        print("\\n2. Scraping with custom configuration...")
        result2 = await scrape_with_custom_config()
        
        # Example 3: Multiple products
        print("\\n3. Scraping multiple product categories...")
        results3 = await scrape_multiple_products()
        
        print("\\nAll examples completed successfully!")
        
        # Create overall summary
        total_reviews = len(result1.reviews) + len(result2.reviews) + sum(len(r[1].reviews) for r in results3)
        print(f"Total reviews scraped: {total_reviews}")
        
    except Exception as e:
        print(f"Error in advanced examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
