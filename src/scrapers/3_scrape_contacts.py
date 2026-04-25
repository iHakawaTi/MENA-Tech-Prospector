"""
Step 3: Contact Extraction
Reads companies_master.csv, extracts their websites, crawls them for emails/phones using Apify.
"""
import os
import csv
import logging
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

def get_domain(url: str) -> str:
    if not url: return ""
    if not url.startswith("http"): url = "https://" + url
    return urlparse(url).netloc.replace("www.", "").lower()

def main():
    base_dir = Path(__file__).parent.parent.parent
    master_csv = base_dir / "data" / "processed" / "companies_master.csv"
    
    if not master_csv.exists(): return
    with open(master_csv, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))

    start_urls, domain_to_company = [], {}
    for c in companies:
        website = c.get("website", "")
        if website and "http" in website:
            domain = get_domain(website)
            start_urls.append({"url": website})
            domain_to_company[domain] = c
            
    if not start_urls: return
    
    client = ApifyClient(APIFY_TOKEN)
    logger.info("Starting Apify contact-info-scraper...")
    run = client.actor("vdrmota/contact-info-scraper").call(
        run_input={"startUrls": start_urls, "maxDepth": 1, "maxPagesPerDomain": 3, "proxyConfiguration": {"useApifyProxy": True}},
        timeout_secs=2400, memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.error(f"Apify run failed: {run.get('status')}")
        # Note: If it fails, users can use a salvage script, but for standard flow we stop here.
        return
        
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        domain = get_domain(item.get("originalStartUrl", ""))
        c = domain_to_company.get(domain)
        if c:
            new_emails = [e["value"] if isinstance(e, dict) else e for e in item.get("emails", [])]
            if new_emails: c["scraped_real_emails"] = ", ".join(list(set(new_emails)))
            new_phones = [p["value"] if isinstance(p, dict) else p for p in item.get("phones", [])]
            if new_phones: c["scraped_phones"] = ", ".join(list(set(new_phones)))
            new_linkedins = [l["value"] if isinstance(l, dict) else l for l in item.get("linkedIns", [])]
            if new_linkedins: c["scraped_linkedins"] = ", ".join(list(set(new_linkedins)))

    with open(master_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(companies[0].keys()))
        writer.writeheader()
        writer.writerows(companies)
    logger.info("Master file updated with scraped contact details.")

if __name__ == "__main__":
    main()
