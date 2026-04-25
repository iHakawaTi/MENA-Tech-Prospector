"""
Test specific Clutch actor.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from apify_client import ApifyClient
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path('.env'))
client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

print("\n=== Testing curious_coder/clutch-scraper ===")
run = client.actor("curious_coder/clutch-scraper").call(
    run_input={
        "startUrls": [{"url": "https://clutch.co/jo/developers"}],
        "maxPagesPerUrl": 1,
    },
    memory_mbytes=1024,
    timeout_secs=300
)

print(f"Status: {run.get('status')}")
if run.get('status') == 'SUCCEEDED':
    items = list(client.dataset(run['defaultDatasetId']).iterate_items())
    print(f"Found {len(items)} items")
    if items:
        print(f"Keys in first item: {list(items[0].keys())}")
        for item in items[:3]:
            print(f"  {item.get('name', item.get('companyName', '?'))[:40]} | {item.get('website', '')}")
