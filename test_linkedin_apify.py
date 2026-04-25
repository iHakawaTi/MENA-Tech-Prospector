import os, sys
from pathlib import Path
from dotenv import load_dotenv
from apify_client import ApifyClient

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
load_dotenv(Path('.env'))
client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

actors = [
    "sotura/linkedin-company-scraper",
    "voyager/linkedin-company-scraper", 
    "epctex/linkedin-company-scraper",
    "steams/linkedin-company-url-scraper"
]

print("=== Checking LinkedIn Actors ===")
for a in actors:
    try:
        info = client.actor(a).get()
        if info:
            print(f"[FOUND] {a} - Free: {info.get('pricing', {}).get('pricingModel')}")
    except Exception as e:
        print(f"[ERROR] {a}: {e}")

# Try testing google search for LinkedIn as a fallback
print("\n=== Testing Google Search Dork (100% Free & Reliable) ===")
try:
    run = client.actor("apify/google-search-scraper").call(
        run_input={
            "queries": ["site:linkedin.com/company \"Amman\" OR \"Jordan\" \"Software Development\""],
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10
        },
        timeout_secs=60
    )
    items = list(client.dataset(run['defaultDatasetId']).iterate_items())
    print(f"Google Search returned {len(items)} pages.")
    if items and 'organicResults' in items[0]:
        print(f"Found {len(items[0]['organicResults'])} organic results.")
        for res in items[0]['organicResults'][:3]:
            print(f" - {res['title'][:40]} | {res['url']}")
except Exception as e:
    print(f"Google Search failed: {e}")
