import os
import csv
import logging
from typing import List, Dict
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
import sys

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

def continue_scraping(input_csv: str, output_csv: str):
    client = _get_client()
    
    # Get previously processed domains from the crashed run
    logger.info("Fetching previously processed domains to avoid re-scraping...")
    crashed_run_id = "kE7m997DgObifL6oD"
    processed_domains = set()
    try:
        dataset = client.run(crashed_run_id).dataset()
        for item in dataset.iterate_items():
            url = item.get("originalStartUrl", "")
            if url:
                processed_domains.add(get_domain(url))
    except Exception as e:
        logger.warning(f"Could not fetch crashed dataset: {e}")

    logger.info(f"Found {len(processed_domains)} already processed domains.")

    # Load companies
    companies = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
            
    # Filter URLs
    start_urls = []
    domain_to_company = {}
    
    for c in companies:
        website = c.get("website", "")
        if website and "http" in website:
            domain = get_domain(website)
            if domain not in processed_domains:
                start_urls.append({"url": website})
                domain_to_company[domain] = c
                
    if not start_urls:
        logger.warning("No remaining websites found to scrape contacts from.")
        return
        
    logger.info(f"Found {len(start_urls)} REMAINING websites to scrape for contacts.")
    
    # We will limit maxPagesPerDomain to 3 to prevent timeouts on large sites
    run_input = {
        "startUrls": start_urls,
        "maxDepth": 1,
        "maxPagesPerDomain": 3,
        "proxyConfiguration": {"useApifyProxy": True}
    }
    
    logger.info("Starting Apify contact-info-scraper actor. This will visit their websites...")
    
    run = client.actor("vdrmota/contact-info-scraper").call(
        run_input=run_input,
        timeout_secs=2400, # 40 mins max
        memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.error(f"Apify run failed again: {run.get('status')}")
        # We can salvage again if needed, but for now we'll just stop
        return
        
    logger.info("Apify run succeeded. Fetching results...")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    # Process results
    enriched_count = 0
    email_count = 0
    
    for item in items:
        url = item.get("originalStartUrl", "")
        domain = get_domain(url)
        
        emails = item.get("emails", [])
        phones = item.get("phones", [])
        linkedins = item.get("linkedIns", [])
        twitters = item.get("twitters", [])
        facebooks = item.get("facebooks", [])
        
        c = domain_to_company.get(domain)
        if c:
            existing_emails = c.get("scraped_real_emails", "").split(", ") if c.get("scraped_real_emails") else []
            new_emails = [e["value"] if isinstance(e, dict) else e for e in emails]
            combined_emails = list(set(existing_emails + new_emails))
            if combined_emails:
                c["scraped_real_emails"] = ", ".join(combined_emails)
                email_count += len(new_emails)
                if not existing_emails: enriched_count += 1
                
            existing_phones = c.get("scraped_phones", "").split(", ") if c.get("scraped_phones") else []
            new_phones = [p["value"] if isinstance(p, dict) else p for p in phones]
            if existing_phones or new_phones:
                 c["scraped_phones"] = ", ".join(list(set(existing_phones + new_phones)))
            
            existing_linkedins = c.get("scraped_linkedins", "").split(", ") if c.get("scraped_linkedins") else []
            new_linkedins = [l["value"] if isinstance(l, dict) else l for l in linkedins]
            if existing_linkedins or new_linkedins:
                c["scraped_linkedins"] = ", ".join(list(set(existing_linkedins + new_linkedins)))

    # Write to output
    fieldnames = list(companies[0].keys())
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
        
    logger.info(f"Successfully extracted {email_count} NEW real emails!")
    logger.info(f"Enriched {enriched_count} NEW companies with verified contact details!")
    logger.info(f"Saved to {output_csv}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_ultimate_contacts.csv"
    output_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_ultimate_contacts_final.csv"
    
    continue_scraping(str(input_file), str(output_file))
