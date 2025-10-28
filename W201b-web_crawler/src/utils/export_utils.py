import json
import csv
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import aiofiles

from ..models import Review, ScrapingResult


async def export_to_json(result: ScrapingResult, file_path: str) -> None:
    """
    Export scraping results to JSON format
    
    Args:
        result: ScrapingResult object to export
        file_path: Path to save the JSON file
    """
    # Convert to dictionary with proper serialization
    data = result.model_dump(mode='json')
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))


async def export_to_csv(reviews: List[Review], file_path: str) -> None:
    """
    Export reviews to CSV format
    
    Args:
        reviews: List of Review objects to export
        file_path: Path to save the CSV file
    """
    if not reviews:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write('No reviews found\\n')
        return
    
    # Convert reviews to dictionaries
    data = [review.model_dump() for review in reviews]
    df = pd.DataFrame(data)
    
    # Convert datetime columns to string
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if it's a datetime column
            if any(isinstance(val, datetime) for val in df[col].dropna()):
                df[col] = df[col].apply(lambda x: x.isoformat() if isinstance(x, datetime) else x)
    
    df.to_csv(file_path, index=False, encoding='utf-8')


async def export_to_xlsx(result: ScrapingResult, file_path: str) -> None:
    """
    Export scraping results to Excel format with multiple sheets
    
    Args:
        result: ScrapingResult object to export
        file_path: Path to save the Excel file
    """
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # Reviews sheet
        if result.reviews:
            reviews_data = [review.model_dump() for review in result.reviews]
            reviews_df = pd.DataFrame(reviews_data)
            
            # Convert datetime columns
            for col in reviews_df.columns:
                if reviews_df[col].dtype == 'object':
                    if any(isinstance(val, datetime) for val in reviews_df[col].dropna()):
                        reviews_df[col] = reviews_df[col].apply(
                            lambda x: x.isoformat() if isinstance(x, datetime) else x
                        )
            
            reviews_df.to_excel(writer, sheet_name='Reviews', index=False)
        
        # Statistics sheet
        stats_data = {
            'Metric': ['Total Reviews', 'Average Rating', 'Verified Purchases', 'Date Range'],
            'Value': [
                result.stats.total_reviews,
                f"{result.stats.average_rating:.2f}",
                result.stats.verified_purchase_count,
                f"{result.stats.date_range['earliest'].date()} to {result.stats.date_range['latest'].date()}" 
                if result.stats.date_range else "N/A"
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        
        # Rating distribution sheet
        if result.stats.rating_distribution:
            rating_data = {
                'Rating': list(result.stats.rating_distribution.keys()),
                'Count': list(result.stats.rating_distribution.values())
            }
            rating_df = pd.DataFrame(rating_data).sort_values('Rating')
            rating_df.to_excel(writer, sheet_name='Rating Distribution', index=False)


def generate_filename(prefix: str, extension: str) -> str:
    """
    Generate a filename with timestamp
    
    Args:
        prefix: Filename prefix
        extension: File extension (without dot)
        
    Returns:
        Generated filename with timestamp
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}.{extension}"


def create_summary_report(result: ScrapingResult) -> str:
    """
    Create a text summary report of scraping results
    
    Args:
        result: ScrapingResult object
        
    Returns:
        Formatted summary report as string
    """
    report_lines = [
        "Amazon Review Scraping Report",
        "=" * 40,
        "",
        f"Scraped At: {result.scraped_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Keywords: {', '.join(result.search_criteria.keywords)}",
        f"Total Reviews Found: {len(result.reviews)}",
        f"Total Products Processed: {result.total_processed}",
        ""
    ]
    
    if result.execution_time:
        report_lines.append(f"Execution Time: {result.execution_time:.2f} seconds")
        report_lines.append("")
    
    # Review Statistics
    stats = result.stats
    report_lines.extend([
        "Review Statistics:",
        f"- Average Rating: {stats.average_rating:.2f}/5.0",
        f"- Total Reviews: {stats.total_reviews}",
        f"- Verified Purchases: {stats.verified_purchase_count}",
        ""
    ])
    
    # Rating Distribution
    if stats.rating_distribution:
        report_lines.append("Rating Distribution:")
        for rating in sorted(stats.rating_distribution.keys(), reverse=True):
            count = stats.rating_distribution[rating]
            percentage = (count / stats.total_reviews * 100) if stats.total_reviews > 0 else 0
            report_lines.append(f"  {rating} stars: {count} reviews ({percentage:.1f}%)")
        report_lines.append("")
    
    # Date Range
    if stats.date_range:
        report_lines.extend([
            "Date Range:",
            f"- Earliest: {stats.date_range['earliest'].strftime('%Y-%m-%d')}",
            f"- Latest: {stats.date_range['latest'].strftime('%Y-%m-%d')}",
            ""
        ])
    
    # Search Criteria
    criteria = result.search_criteria
    report_lines.extend([
        "Search Criteria:",
        f"- Keywords: {', '.join(criteria.keywords)}",
        f"- Min Rating: {criteria.min_rating or 'No limit'}",
        f"- Max Rating: {criteria.max_rating or 'No limit'}",
        f"- Verified Purchase Only: {'Yes' if criteria.verified_purchase_only else 'No'}",
        f"- Min Review Length: {criteria.min_review_length or 'No limit'} characters",
        f"- Max Results: {criteria.max_results or 'No limit'}",
        f"- Sort By: {criteria.sort_by} ({criteria.sort_order})",
        ""
    ])
    
    # Errors
    if result.errors:
        report_lines.extend([
            f"Errors Encountered ({len(result.errors)}):",
            *[f"- {error}" for error in result.errors],
            ""
        ])
    else:
        report_lines.append("No errors encountered.")
    
    return "\\n".join(report_lines)
