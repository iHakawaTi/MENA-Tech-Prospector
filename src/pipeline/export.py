import csv
import logging
from pathlib import Path
from typing import List
from datetime import datetime
from ..models import Company, DATABASE_FIELDS

logger = logging.getLogger(__name__)


def export_to_csv(companies: List[Company], output_path: str, include_internal: bool = False) -> None:
    logger.info(f"Exporting {len(companies)} companies to {output_path}")
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = DATABASE_FIELDS.copy()
    
    if include_internal:
        fieldnames.extend([
            "domain_normalized",
            "name_normalized",
            "merged_sources",
            "confidence_score"
        ])
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for company in companies:
            row = company.to_dict()
            
            filtered_row = {
                k: v for k, v in row.items() 
                if k in fieldnames
            }
            
            filtered_row = clean_values(filtered_row)
            
            writer.writerow(filtered_row)
    
    logger.info(f"Successfully exported to {output_path}")


def clean_values(row: dict) -> dict:
    cleaned = {}
    
    for key, value in row.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, str):
            value = value.strip()
            
            value = value.replace("\n", " ")
            value = value.replace("\r", " ")
            value = value.replace("\t", " ")
            
            value = " ".join(value.split())
            
            cleaned[key] = value
        else:
            cleaned[key] = value
    
    return cleaned


def generate_report(
    raw_count: int,
    cleaned_count: int,
    deduped_count: int,
    sources_stats: dict,
    failed_sources: list,
    output_path: str
) -> None:
    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_content = f"""# Jordan Companies Scraper Report
Generated: {timestamp}

## Summary
- Total raw companies: {raw_count}
- After cleaning: {cleaned_count}
- After deduplication: {deduped_count}

## Sources Used
"""
    
    for source, count in sorted(sources_stats.items(), key=lambda x: x[1], reverse=True):
        report_content += f"- {source}: {count} companies\n"
    
    if failed_sources:
        report_content += "\n## Failed/Blocked Sources\n"
        for source in failed_sources:
            report_content += f"- {source}\n"
    
    report_content += """
## Assumptions & Limitations

1. Data quality depends on source availability and page structure
2. Some fields may be empty due to source limitations
3. Deduplication uses domain + fuzzy name matching
4. Filtered out irrelevant business types (restaurants, retail, etc.)
5. Rate limiting applied to respect source servers

## Fields Captured
- company_name, website, source_url, source_name
- city, country, full_location
- category_primary, category_secondary, services
- description, phone, email
- founded_year, company_size, hourly_rate
- rating, review_count, verified_status

## Notes
- Companies filtered to IT/software/digital/marketing/consulting sectors
- Confidence score calculated based on data completeness
- Merged sources track provenance for deduplicated records
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info(f"Report generated: {output_path}")


def load_from_csv(filepath: str) -> List[Company]:
    companies = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            company = Company(**row)
            companies.append(company)
    
    logger.info(f"Loaded {len(companies)} companies from {filepath}")
    return companies