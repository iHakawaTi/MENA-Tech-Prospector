"""
Step 2: CEO Enrichment
Reads companies_master.csv, searches Google for their CEO/Founder profiles, and updates the file.
"""
import os
import csv
import logging
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def main():
    base_dir = Path(__file__).parent.parent.parent
    master_csv = base_dir / "data" / "processed" / "companies_master.csv"
    
    if not master_csv.exists():
        logger.error(f"{master_csv} not found. Run 1_discovery.py first.")
        return

    with open(master_csv, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))

    client = ApifyClient(APIFY_TOKEN)
    queries = [f'site:linkedin.com/in ("CEO" OR "Founder" OR "Managing Director" OR "CTO") "{c["company_name"].replace(chr(34),"")}" "{c.get("country", "")}"' for c in companies]
    
    logger.info(f"Prepared {len(queries)} Google Search queries for Apify.")
    run = client.actor("apify/google-search-scraper").call(
        run_input={"queries": "\n".join(queries), "maxPagesPerQuery": 1, "resultsPerPage": 2, "countryCode": "us"},
        timeout_secs=3600, memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.error("Apify run failed.")
        return
        
    query_results = {item.get("searchQuery", {}).get("term", ""): item.get("organicResults", [{}])[0] for item in client.dataset(run["defaultDatasetId"]).iterate_items() if item.get("organicResults")}

    for c in companies:
        query = f'site:linkedin.com/in ("CEO" OR "Founder" OR "Managing Director" OR "CTO") "{c["company_name"].replace(chr(34),"")}" "{c.get("country", "")}"'
        res = query_results.get(query)
        if res:
            title_full = res.get("title", "")
            parts = [p.strip() for p in title_full.replace("| LinkedIn", "").split("-")]
            if "LinkedIn" not in title_full and "profiles" in res.get("url", "").lower(): continue
            c["ceo_name"] = parts[0] if len(parts) > 0 else ""
            c["ceo_title"] = parts[1] if len(parts) > 1 else "CEO/Founder"
            c["ceo_linkedin"] = res.get("url", "")

    with open(master_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(companies[0].keys()))
        writer.writeheader()
        writer.writerows(companies)
    logger.info("Master file updated with CEO details.")

if __name__ == "__main__":
    main()
