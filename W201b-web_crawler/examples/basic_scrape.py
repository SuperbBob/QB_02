#!/usr/bin/env python3
"""
Basic Amazon Review Scraper Example

This example demonstrates how to use the Amazon scraper programmatically
to scrape reviews for wireless headphones with specific criteria.
"""

import asyncio
from datetime import datetime, timedelta

from src.models import SearchCriteria, ScrapingConfig
from src.scraper import AmazonScraper
from src.utils import export_to_json, create_summary_report


async def main():
    """Main example function"""
    
    # Define search criteria
    search_criteria = SearchCriteria(
        keywords=["wireless headphones", "bluetooth"],
        min_rating=4,  # Only 4+ star reviews
        verified_purchase_only=True,  # Only verified purchases
        min_review_length=100,  # At least 100 characters
        max_results=50,  # Limit to 50 reviews
        sort_by="helpful",
        sort_order="desc"
    )
    
    # Configure scraper
    config = ScrapingConfig(
        search_criteria=search_criteria,
        output_format="json"
    )
    
    print("Starting Amazon review scrape...")
    print(f"Keywords: {', '.join(search_criteria.keywords)}")
    print(f"Criteria: {search_criteria.min_rating}+ stars, verified purchases only")
    print()
    
    # Run scraper
    async with AmazonScraper(config) as scraper:
        result = await scraper.scrape_reviews(search_criteria)
    
    # Export results
    await export_to_json(result, "wireless_headphones_reviews.json")
    
    # Print summary
    print(f"\\nScraping completed!")
    print(f"Found {len(result.reviews)} reviews")
    print(f"Average rating: {result.stats.average_rating:.2f}/5.0")
    print(f"Execution time: {result.execution_time:.2f} seconds")
    
    # Print some example reviews
    print(f"\\nExample reviews:")
    for i, review in enumerate(result.reviews[:3]):
        print(f"\\n{i+1}. {review.title}")
        print(f"   Rating: {review.rating}/5 | Verified: {review.verified_purchase}")
        print(f"   Date: {review.date.strftime('%Y-%m-%d')}")
        print(f"   Text: {review.text[:200]}...")
    
    # Save summary report
    summary = create_summary_report(result)
    with open("scraping_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"\\nDetailed results saved to:")
    print(f"  - wireless_headphones_reviews.json")
    print(f"  - scraping_summary.txt")


if __name__ == "__main__":
    asyncio.run(main())
