"""
Step 1: Discovery Scraper
Uses Apify Google Search (LinkedIn Dorks) to fetch new IT companies and schools in Jordan/KSA.
"""
import os
import csv
import logging
from typing import List
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def scrape_linkedin_dorks(queries: str, country_code: str, max_pages: int = 2) -> List[dict]:
    client = ApifyClient(APIFY_TOKEN)
    run_input = {
        "queries": queries.strip(),
        "maxPagesPerQuery": max_pages,
        "resultsPerPage": 10,
        "countryCode": country_code,
        "languageCode": "en",
    }
    
    logger.info(f"Launching Apify Google Search scraper. Max pages/query: {max_pages}")
    run = client.actor("apify/google-search-scraper").call(
        run_input=run_input, timeout_secs=600, memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.warning(f"Apify run failed (status={run.get('status')})")
        return []
        
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    results, seen_urls = [], set()
    
    for item in items:
        for res in item.get("organicResults", []):
            url = res.get("url", "")
            title = res.get("title", "")
            desc = res.get("description", "")
            if "linkedin.com/school/" not in url and "linkedin.com/company/" not in url: continue
            name = title.split(" | ")[0].split(" - ")[0].strip()
            if url not in seen_urls and len(name) > 2:
                seen_urls.add(url)
                results.append({"name": name, "linkedin_url": url, "description": desc[:500]})
    return results

def save_to_csv(data: List[dict], filepath: Path, keys: list = None):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not data:
        logger.warning(f"No data to save for {filepath.name}")
        return
    keys = keys or list(data[0].keys())
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved {len(data)} records to {filepath}")

def format_company(c: dict, country: str, city: str) -> dict:
    return {
        "company_name": c["name"],
        "website": "",
        "company_profile_url": c["linkedin_url"],
        "city": city,
        "country": country,
        "services": "IT & Software",
        "description": c["description"],
        "source_name": "LinkedIn (via Google)",
        "ceo_name": "", "ceo_title": "", "ceo_linkedin": "", "scraped_real_emails": "",
        "scraped_phones": "", "scraped_linkedins": "", "guessed_emails": "", "general_email": ""
    }

def main():
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data" / "processed"
    
    # Jordan Schools
    logger.info("=== SCRAPING SCHOOLS IN JORDAN ===")
    jo_schools = scrape_linkedin_dorks('site:linkedin.com/school "Amman" OR "Jordan"', "jo", 3)
    save_to_csv(jo_schools, data_dir / "schools_jordan.csv")
    
    # KSA Schools
    logger.info("=== SCRAPING SCHOOLS IN KSA ===")
    ksa_schools = scrape_linkedin_dorks('site:linkedin.com/school "Saudi Arabia" OR "Riyadh"', "sa", 3)
    save_to_csv(ksa_schools, data_dir / "schools_ksa.csv")
    
    # Jordan IT Companies
    logger.info("=== SCRAPING IT COMPANIES IN JORDAN ===")
    jo_it = scrape_linkedin_dorks('site:linkedin.com/company "Jordan" "Software Development"', "jo", 3)
    
    # KSA IT Companies
    logger.info("=== SCRAPING IT COMPANIES IN KSA ===")
    ksa_it = scrape_linkedin_dorks('site:linkedin.com/company "Saudi Arabia" "Software Development"', "sa", 3)
    
    combined = [format_company(c, "Jordan", "Amman") for c in jo_it] + [format_company(c, "Saudi Arabia", "Riyadh") for c in ksa_it]
    
    master_path = data_dir / "companies_master.csv"
    save_to_csv(combined, master_path)

if __name__ == "__main__":
    main()
