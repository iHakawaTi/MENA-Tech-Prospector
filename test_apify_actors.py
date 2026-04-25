"""
Test: use Apify's web-scraper (Cheerio-based) on TechBehemoths
with a longer navigation timeout and 'load' wait (not 'networkidle').
Also tests the dedicated Clutch actor from the marketplace.
"""
import sys, logging
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s", stream=sys.stdout)

from apify_client import ApifyClient
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path('.env'))
client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

# Test: can we reach TechBehemoths with apify/web-scraper (uses Cheerio + browser-like headers)?
print("\n=== Testing apify/web-scraper on TechBehemoths ===")
run = client.actor("apify/web-scraper").call(
    run_input={
        "startUrls": [{"url": "https://techbehemoths.com/companies/jordan"}],
        "pageFunction": """
async function pageFunction(context) {
    const { $, request, log } = context;
    const links = [];
    $('a[href*="/company/"]').each((i, el) => {
        const name = $(el).text().trim();
        if (name.length > 1) links.push({ name, href: $(el).attr('href') });
    });
    log.info('Found ' + links.length + ' company links');
    return { url: request.url, companyLinks: links.slice(0, 30) };
}
""",
        "proxyConfiguration": {"useApifyProxy": True},
        "maxConcurrency": 1,
    },
    timeout_secs=120,
    memory_mbytes=512,
)
print(f"Status: {run.get('status')}")
items = list(client.dataset(run['defaultDatasetId']).iterate_items())
for item in items:
    links = item.get('companyLinks', [])
    print(f"  Found {len(links)} company links on {item.get('url','')[:60]}")
    for lnk in links[:5]:
        print(f"    {lnk['name'][:50]} -> {lnk['href'][:60]}")

# Check if curious_coder/clutch-scraper actor exists
print("\n=== Checking Clutch marketplace actors ===")
actors_to_check = [
    "curious_coder/clutch-scraper",
    "epctex/clutch-scraper",
    "apify/clutch-scraper",
    "maxcopell/clutch-companies-scraper",
]
for actor_id in actors_to_check:
    try:
        info = client.actor(actor_id).get()
        if info:
            print(f"  [FOUND] {actor_id} - {info.get('name','?')}")
        else:
            print(f"  [NOT FOUND] {actor_id}")
    except Exception as e:
        print(f"  [ERROR] {actor_id}: {e}")
