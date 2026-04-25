"""
Expansion Scraper: Jordan/KSA Schools and KSA IT Companies.
Uses Apify Google Search (LinkedIn Dorks) to fetch new data without re-running old scripts.
"""

import os
import csv
import logging
from typing import List
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path

# Fix Windows encoding for prints
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def _get_client() -> ApifyClient:
    return ApifyClient(APIFY_TOKEN)

def scrape_linkedin_dorks(queries: str, country_code: str, max_pages: int = 2) -> List[dict]:
    client = _get_client()
    run_input = {
        "queries": queries.strip(),
        "maxPagesPerQuery": max_pages,
        "resultsPerPage": 10,
        "countryCode": country_code,
        "languageCode": "en",
    }
    
    logger.info(f"Launching Apify Google Search scraper. Max pages/query: {max_pages}")
    run = client.actor("apify/google-search-scraper").call(
        run_input=run_input,
        timeout_secs=600,
        memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.warning(f"Apify run failed (status={run.get('status')})")
        return []
        
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    results = []
    seen_urls = set()
    
    for item in items:
        for res in item.get("organicResults", []):
            url = res.get("url", "")
            title = res.get("title", "")
            desc = res.get("description", "")
            
            if "linkedin.com/school/" not in url and "linkedin.com/company/" not in url:
                continue
                
            name = title.split(" | ")[0].split(" - ")[0].strip()
            
            if url not in seen_urls and len(name) > 2:
                seen_urls.add(url)
                results.append({
                    "name": name,
                    "linkedin_url": url,
                    "description": desc[:500],
                })
    return results

def save_to_csv(data: List[dict], filename: str):
    filepath = Path("data/processed") / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        logger.warning(f"No data to save for {filename}")
        return
        
    keys = ["name", "linkedin_url", "description"]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved {len(data)} records to {filepath}")

def main():
    # 1. Schools in Jordan
    logger.info("=== SCRAPING SCHOOLS IN JORDAN ===")
    jo_school_queries = (
        'site:linkedin.com/school "Amman" OR "Jordan"\n'
        'site:linkedin.com/company "Amman" OR "Jordan" "School" OR "Academy" OR "Education"\n'
    )
    jo_schools = scrape_linkedin_dorks(jo_school_queries, country_code="jo", max_pages=3)
    save_to_csv(jo_schools, "schools_jordan.csv")
    
    # 2. Schools in KSA
    logger.info("=== SCRAPING SCHOOLS IN KSA ===")
    ksa_school_queries = (
        'site:linkedin.com/school "Saudi Arabia" OR "Riyadh" OR "Jeddah"\n'
        'site:linkedin.com/company "Saudi Arabia" "School" OR "Academy" OR "Education"\n'
    )
    ksa_schools = scrape_linkedin_dorks(ksa_school_queries, country_code="sa", max_pages=3)
    save_to_csv(ksa_schools, "schools_ksa.csv")
    
    # 3. IT Companies in KSA
    logger.info("=== SCRAPING IT COMPANIES IN KSA ===")
    keywords = ["Software Development", "Web Development", "Mobile App", "IT Services", "Cybersecurity", "Artificial Intelligence"]
    ksa_it_queries = ""
    for kw in keywords:
        ksa_it_queries += f'site:linkedin.com/company "Saudi Arabia" OR "Riyadh" "{kw}"\n'
        
    ksa_companies = scrape_linkedin_dorks(ksa_it_queries, country_code="sa", max_pages=2)
    
    # Format KSA companies to match existing CSV structure
    ksa_formatted = []
    for c in ksa_companies:
        ksa_formatted.append({
            "company_name": c["name"],
            "website": "",
            "company_profile_url": c["linkedin_url"],
            "city": "Riyadh", # Default assumption, could parse from desc
            "country": "Saudi Arabia",
            "services": "IT & Software",
            "description": c["description"],
            "source_name": "LinkedIn (via Google)"
        })
        
    # Save standalone KSA companies just in case
    filepath_ksa = Path("data/processed") / "companies_ksa.csv"
    if ksa_formatted:
        with open(filepath_ksa, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ksa_formatted[0].keys())
            writer.writeheader()
            writer.writerows(ksa_formatted)
        logger.info(f"Saved {len(ksa_formatted)} KSA companies to {filepath_ksa}")
    
    # 4. Combine Jordan and KSA IT companies
    logger.info("=== COMBINING JORDAN AND KSA IT COMPANIES ===")
    combined_list = []
    seen_urls = set()
    
    # Load Jordan data
    jo_path = Path("data/processed/companies_jordan_deduplicated.csv")
    if jo_path.exists():
        with open(jo_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("company_profile_url", "")
                if url: seen_urls.add(url)
                combined_list.append(row)
        logger.info(f"Loaded {len(combined_list)} Jordan companies from existing CSV.")
        
    # Append KSA data
    added_ksa = 0
    for row in ksa_formatted:
        if row["company_profile_url"] not in seen_urls:
            seen_urls.add(row["company_profile_url"])
            combined_list.append(row)
            added_ksa += 1
            
    # Save combined
    combined_path = Path("data/processed/companies_it_jordan_ksa_combined.csv")
    if combined_list:
        keys = combined_list[0].keys()
        with open(combined_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(combined_list)
        logger.info(f"Saved COMBINED {len(combined_list)} companies (Jordan + KSA) to {combined_path}")

if __name__ == "__main__":
    main()
