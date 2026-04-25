"""
Scrape LinkedIn company profiles via Google Search (Dorks) on Apify.
This is 100% free, avoids LinkedIn login blocks, and finds highly relevant
companies based on targeted keywords for Jordan.
"""

import os
import logging
from typing import List
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path

from ..models import Company
from ..utils.parse import normalize_company_name, extract_city

logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def _get_client() -> ApifyClient:
    return ApifyClient(APIFY_TOKEN)

def scrape_linkedin_via_google() -> List[Company]:
    client = _get_client()
    
    # Comprehensive keyword list for tech/marketing companies in Jordan
    keywords = [
        "Software Development",
        "Web Development",
        "Mobile App Development",
        "IT Services",
        "Digital Marketing",
        "SEO Agency",
        "Cybersecurity",
        "Artificial Intelligence",
        "Data Analytics",
        "Cloud Computing"
    ]
    
    # Construct Google Dorks
    # e.g. site:linkedin.com/company "Amman" "Software Development"
    queries = ""
    for kw in keywords:
        queries += f'site:linkedin.com/company "Amman" OR "Jordan" "{kw}"\n'
        
    logger.info(f"[Apify/LinkedIn] Launching Google Search scraper for {len(keywords)} keywords...")
    
    run_input = {
        "queries": queries.strip(),
        "maxPagesPerQuery": 2, # Top 20 results per keyword
        "resultsPerPage": 10,
        "countryCode": "jo", # Jordan
        "languageCode": "en",
    }
    
    run = client.actor("apify/google-search-scraper").call(
        run_input=run_input,
        timeout_secs=600,
        memory_mbytes=1024
    )
    
    if run.get("status") != "SUCCEEDED":
        logger.warning(f"[Apify/LinkedIn] Google Search run failed (status={run.get('status')})")
        return []
        
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    companies = []
    seen_urls = set()
    
    for item in items:
        # Organic results contain the actual search hits
        organic = item.get("organicResults", [])
        for res in organic:
            url = res.get("url", "")
            title = res.get("title", "")
            desc = res.get("description", "")
            
            # Ensure it's a company page
            if "linkedin.com/company/" not in url:
                continue
                
            # Clean up title (e.g. "Company Name | LinkedIn")
            name = title.split(" | ")[0].split(" - ")[0].strip()
            
            # Try to guess city from description
            city = extract_city(desc) or "Amman"
            
            if url not in seen_urls and len(name) > 2:
                seen_urls.add(url)
                
                c = Company(
                    company_name=name,
                    source_url=url,
                    source_name="LinkedIn (via Google)",
                    company_profile_url=url,
                    description=desc[:500],
                    city=city,
                    country="Jordan"
                )
                c.name_normalized = normalize_company_name(name)
                companies.append(c)

    logger.info(f"[Apify/LinkedIn] Extracted {len(companies)} unique LinkedIn companies via Google Search.")
    return companies

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    comps = scrape_linkedin_via_google()
    for c in comps[:10]:
        print(f"{c.company_name} | {c.company_profile_url}")
