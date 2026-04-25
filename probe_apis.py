"""
Probe TechBehemoths and Clutch for accessible API endpoints.
These sites load data via XHR — let's find the raw API URL.
"""
import sys, requests, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://techbehemoths.com/",
    "Origin": "https://techbehemoths.com",
}

# Known TechBehemoths API endpoints to probe
tb_candidates = [
    "https://techbehemoths.com/api/v2/companies?filters[country]=jordan&page=1&per_page=24",
    "https://techbehemoths.com/api/companies?country=jordan&page=1",
    "https://api.techbehemoths.com/companies?country=jordan",
    "https://techbehemoths.com/api/v1/companies?location=jordan",
    "https://techbehemoths.com/api/v2/companies?location=jordan",
]

print("=== TechBehemoths API probes ===")
for url in tb_candidates:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  [{r.status_code}] {url[:80]}")
        if r.status_code == 200 and 'json' in r.headers.get('content-type',''):
            data = r.json()
            print(f"           -> JSON keys: {list(data.keys()) if isinstance(data, dict) else 'list['+str(len(data))+']'}")
    except Exception as e:
        print(f"  [ERR] {url[:60]} -> {e}")

# Clutch API probes
clutch_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0",
    "Accept": "application/json",
    "Referer": "https://clutch.co/",
    "x-requested-with": "XMLHttpRequest",
}
clutch_candidates = [
    "https://clutch.co/api/v1/providers?location=jordan&page=1",
    "https://clutch.co/api/providers?country=jordan&page=1",
    "https://clutch.co/api/v2/providers/search?country=JO",
    "https://clutch.co/api/directory/providers?location=jordan",
]

print("\n=== Clutch API probes ===")
for url in clutch_candidates:
    try:
        r = requests.get(url, headers=clutch_headers, timeout=10)
        print(f"  [{r.status_code}] {url[:80]}")
        if r.status_code == 200 and 'json' in r.headers.get('content-type',''):
            data = r.json()
            print(f"           -> JSON keys: {list(data.keys()) if isinstance(data, dict) else 'list['+str(len(data))+']'}")
    except Exception as e:
        print(f"  [ERR] {url[:60]} -> {e}")
