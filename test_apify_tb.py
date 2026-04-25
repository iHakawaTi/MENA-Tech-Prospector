"""Quick test: scrape just the first TechBehemoths page via Apify."""
import sys, logging
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s", stream=sys.stdout)

from src.scrapers.apify_scraper import _get_client, _playwright_scrape, _TB_PAGE_FUNCTION

companies = _playwright_scrape(
    label="TechBehemoths-TEST",
    source_name="TechBehemoths",
    urls=["https://techbehemoths.com/companies/jordan"],
    page_function=_TB_PAGE_FUNCTION,
    timeout_secs=180,
)

print(f"\n=== RESULT: {len(companies)} companies ===")
for c in companies[:10]:
    print(f"  {c.company_name:<40} | {c.city:<15} | {c.website[:40] if c.website else '-'}")
