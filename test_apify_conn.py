import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from src.scrapers.apify_scraper import _get_client

c = _get_client()
me = c.user('me').get()
username = me.get('username', '?')
plan = me.get('plan', {}).get('name', '?')
print(f"Apify connected OK - User: {username} | Plan: {plan}")
