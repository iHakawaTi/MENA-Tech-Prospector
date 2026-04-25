import os
import csv
import logging
from typing import List, Dict
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
import sys

# Fix Windows encoding for prints
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def _get_client() -> ApifyClient:
    return ApifyClient(APIFY_TOKEN)

def get_domain(url: str) -> str:
    if not url: return ""
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "").lower()

def scrape_contact_details(input_csv: str, output_csv: str):
    logger.info(f"Loading companies from {input_csv}")
    companies = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
            
    if not companies:
        logger.warning("No companies found.")
        return

    # Extract all valid URLs
    start_urls = []
    domain_to_company = {}
    
    for c in companies:
        website = c.get("website", "")
        if website and "http" in website:
            start_urls.append({"url": website})
            domain_to_company[get_domain(website)] = c
            
    if not start_urls:
        logger.warning("No valid websites found to scrape contacts from.")
        return
        
    logger.info(f"Found {len(start_urls)} websites to scrape for contacts.")
    
    client = _get_client()
    
    run_input = {
        "startUrls": start_urls,
        "maxDepth": 1, # Crawl homepage and 1 click deep (like /contact)
        "maxPagesPerDomain": 5,
        "proxyConfiguration": {"useApifyProxy": True}
    }
    
    logger.info("Starting Apify contact-info-scraper actor. This will visit their websites...")
    # Using the standard contact-info-scraper
    run = client.actor("vdrmota/contact-info-scraper").call(
        run_input=run_input,
        timeout_secs=1200, # 20 mins max
        memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.error(f"Apify run failed: {run.get('status')}")
        return
        
    logger.info("Apify run succeeded. Fetching results...")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    # Initialize new columns
    fieldnames = list(companies[0].keys())
    new_fields = ["scraped_real_emails", "scraped_phones", "scraped_linkedins", "scraped_twitters", "scraped_facebooks"]
    for f in new_fields:
        if f not in fieldnames:
            fieldnames.append(f)
            
    for c in companies:
        for f in new_fields:
            c[f] = ""
            
    # Process results
    enriched_count = 0
    email_count = 0
    
    for item in items:
        # vdrmota/contact-info-scraper returns objects with lists
        url = item.get("url", "")
        domain = get_domain(url)
        
        emails = item.get("emails", [])
        phones = item.get("phones", [])
        linkedins = item.get("linkedIns", [])
        twitters = item.get("twitters", [])
        facebooks = item.get("facebooks", [])
        
        # In case the actor uses a different format, e.g., nested
        if not emails and "contactDetails" in item:
             cd = item["contactDetails"]
             emails = cd.get("emails", [])
             phones = cd.get("phones", [])
        
        c = domain_to_company.get(domain)
        if c:
            if emails:
                c["scraped_real_emails"] = ", ".join(list(set(e["value"] if isinstance(e, dict) else e for e in emails)))
                email_count += len(emails)
                enriched_count += 1
            if phones:
                c["scraped_phones"] = ", ".join(list(set(p["value"] if isinstance(p, dict) else p for p in phones)))
            if linkedins:
                 c["scraped_linkedins"] = ", ".join(list(set(l["value"] if isinstance(l, dict) else l for l in linkedins)))
            if twitters:
                 c["scraped_twitters"] = ", ".join(list(set(t["value"] if isinstance(t, dict) else t for t in twitters)))
            if facebooks:
                 c["scraped_facebooks"] = ", ".join(list(set(f["value"] if isinstance(f, dict) else f for f in facebooks)))

    # Write to output
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
        
    logger.info(f"Successfully extracted {email_count} real emails!")
    logger.info(f"Enriched {enriched_count} companies with verified contact details!")
    logger.info(f"Saved to {output_csv}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_final_enriched.csv"
    output_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_ultimate_contacts.csv"
    
    scrape_contact_details(str(input_file), str(output_file))
