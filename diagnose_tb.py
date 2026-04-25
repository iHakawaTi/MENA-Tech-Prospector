"""
Diagnostic script: visit TechBehemoths and dump ALL network requests made.
This tells us the exact API URL the page calls to load company data.
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time, json

sys.path.insert(0, '.')
from src.utils.stealth import apply_stealth, get_stealth_context_options

all_requests = []
all_responses = []

def on_request(req):
    all_requests.append({
        "url": req.url,
        "method": req.method,
        "resource_type": req.resource_type,
    })

def on_response(resp):
    ct = resp.headers.get("content-type", "")
    if "json" in ct or "javascript" in ct:
        all_responses.append({
            "url": resp.url,
            "status": resp.status,
            "content_type": ct,
        })

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    ctx = browser.new_context(**get_stealth_context_options())
    ctx.on("request", on_request)
    ctx.on("response", on_response)
    page = ctx.new_page()
    apply_stealth(page)
    
    print("Loading homepage...")
    page.goto("https://techbehemoths.com", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    print("Loading companies/jordan...")
    page.goto("https://techbehemoths.com/companies/jordan", wait_until="domcontentloaded", timeout=30000)
    
    # Wait for content selector
    try:
        page.wait_for_selector("a[href*='/company/'], h3", timeout=15000)
    except:
        pass
    time.sleep(4)
    
    # Print content sample
    content = page.content()
    print(f"\nPage content length: {len(content)} chars")
    # Look for company links in rendered HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, "lxml")
    company_links = soup.select("a[href*='/company/']")
    print(f"Company links found in DOM: {len(company_links)}")
    for lnk in company_links[:10]:
        print(f"  {lnk.get_text(strip=True)[:50]} -> {lnk.get('href','')[:80]}")
    
    browser.close()

print("\n\n=== ALL JSON/JS RESPONSES ===")
for r in all_responses:
    if r["status"] == 200:
        print(f"  [{r['status']}] {r['url'][:120]}")

print("\n\n=== FETCH/XHR REQUESTS ===")
for r in all_requests:
    if r["resource_type"] in ["fetch", "xhr"]:
        print(f"  [{r['method']}] {r['url'][:120]}")
