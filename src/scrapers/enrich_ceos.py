import os
import csv
import re
import logging
from typing import List, Dict
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
import sys

# Fix Windows encoding for prints
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def _get_client() -> ApifyClient:
    return ApifyClient(APIFY_TOKEN)

def extract_email(text: str) -> str:
    """Extracts first valid email from text using regex."""
    if not text:
        return ""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""

def enrich_companies_with_ceo_data(input_csv: str, output_csv: str):
    logger.info(f"Loading companies from {input_csv}")
    companies = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
            
    if not companies:
        logger.warning("No companies found to enrich.")
        return

    client = _get_client()
    
    # Due to Apify limits on single run, we batch queries if necessary.
    # 410 queries in one run might take a while, but google-search-scraper handles arrays.
    # To be safe and quick, we will only take the first 100 for this run as a proof of concept,
    # or we can do all 410. Let's do all 410 but set resultsPerPage to 1.
    
    queries = []
    for c in companies:
        name = c.get("company_name", "").replace('"', '')
        country = c.get("country", "")
        # Google Dork to find the CEO/Founder profile
        query = f'site:linkedin.com/in ("CEO" OR "Founder" OR "Managing Director" OR "CTO") "{name}" "{country}"'
        queries.append(query)
        
    logger.info(f"Prepared {len(queries)} Google Search queries for Apify.")
    
    # Prepare Apify Run Input
    run_input = {
        "queries": "\n".join(queries),
        "maxPagesPerQuery": 1,
        "resultsPerPage": 2, # Just need the top 1 or 2 hits
        "countryCode": "us",
        "languageCode": "en",
    }
    
    logger.info("Starting Apify google-search-scraper actor. This may take a few minutes...")
    run = client.actor("apify/google-search-scraper").call(
        run_input=run_input,
        timeout_secs=3600, # 1 hour max
        memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.error(f"Apify run failed: {run.get('status')}")
        return
        
    logger.info("Apify run succeeded. Fetching results...")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    # Map query to result
    # The dataset returns items where each item corresponds to a query
    query_results = {}
    for item in items:
        sq = item.get("searchQuery", {}).get("term", "")
        org_res = item.get("organicResults", [])
        if org_res:
            query_results[sq] = org_res[0] # Take the top result
            
    # Update companies
    logger.info("Parsing results and extracting CEO details & emails...")
    
    fieldnames = list(companies[0].keys())
    new_fields = ["ceo_name", "ceo_title", "ceo_linkedin", "scraped_email"]
    for f in new_fields:
        if f not in fieldnames:
            fieldnames.append(f)
            
    enriched_count = 0
    email_count = 0
    
    for c in companies:
        name = c.get("company_name", "").replace('"', '')
        country = c.get("country", "")
        query = f'site:linkedin.com/in ("CEO" OR "Founder" OR "Managing Director" OR "CTO") "{name}" "{country}"'
        
        c["ceo_name"] = ""
        c["ceo_title"] = ""
        c["ceo_linkedin"] = ""
        c["scraped_email"] = ""
        
        res = query_results.get(query)
        if res:
            title_full = res.get("title", "")
            desc = res.get("description", "")
            url = res.get("url", "")
            
            # Extract Email from description snippet (Google often surfaces emails in the snippet)
            email = extract_email(desc)
            if not email and "email" in c and c["email"]:
                 email = c["email"] # fallback to existing
                 
            # Parse Title string: "Ahmad K. - CEO - Company Name | LinkedIn"
            parts = [p.strip() for p in title_full.replace("| LinkedIn", "").split("-")]
            ceo_name = parts[0] if len(parts) > 0 else ""
            ceo_title = parts[1] if len(parts) > 1 else "CEO/Founder"
            
            # Filter out generic garbage if the search was bad
            if "LinkedIn" not in title_full and "profiles" in url.lower():
                pass # sometimes it returns a directory instead of a person
            else:
                c["ceo_name"] = ceo_name
                c["ceo_title"] = ceo_title
                c["ceo_linkedin"] = url
                enriched_count += 1
                
            if email:
                c["scraped_email"] = email
                email_count += 1
                
    # Write to output
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
        
    logger.info(f"Successfully enriched {enriched_count} companies with CEO profiles!")
    logger.info(f"Successfully extracted {email_count} emails!")
    logger.info(f"Saved to {output_csv}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_combined.csv"
    output_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_ceos.csv"
    
    enrich_companies_with_ceo_data(str(input_file), str(output_file))
