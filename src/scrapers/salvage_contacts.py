import os
import csv
import logging
from apify_client import ApifyClient
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

def get_domain(url: str) -> str:
    if not url: return ""
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "").lower()

def salvage_contact_details():
    input_csv = Path("data/processed/companies_it_jordan_ksa_ultimate_contacts.csv")
    output_csv = Path("data/processed/companies_it_jordan_ksa_ultimate_contacts_final.csv")
    
    companies = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))
        
    domain_to_company = {}
    for c in companies:
        website = c.get("website", "")
        if website:
            domain_to_company[get_domain(website)] = c

    client = ApifyClient(APIFY_TOKEN)
    run_id = "b3FQEoKpME3tBY8p9"
    
    logger.info(f"Fetching salvaged data from crashed run: {run_id}")
    try:
        dataset = client.run(run_id).dataset()
        items = list(dataset.iterate_items())
    except Exception as e:
        logger.error(f"Could not fetch dataset: {e}")
        return

    logger.info(f"Recovered {len(items)} scraped pages from the dataset.")
    
    fieldnames = list(companies[0].keys())
    new_fields = ["scraped_real_emails", "scraped_phones", "scraped_linkedins", "scraped_twitters", "scraped_facebooks"]
    for f in new_fields:
        if f not in fieldnames: fieldnames.append(f)
            
    for c in companies:
        for f in new_fields:
            c[f] = ""

    enriched_count = 0
    email_count = 0
    
    for item in items:
        url = item.get("originalStartUrl", "")
        domain = get_domain(url)
        
        emails = item.get("emails", [])
        phones = item.get("phones", [])
        linkedins = item.get("linkedIns", [])
        twitters = item.get("twitters", [])
        facebooks = item.get("facebooks", [])
        
        c = domain_to_company.get(domain)
        if c:
            existing_emails = c["scraped_real_emails"].split(", ") if c["scraped_real_emails"] else []
            new_emails = [e["value"] if isinstance(e, dict) else e for e in emails]
            combined_emails = list(set(existing_emails + new_emails))
            if combined_emails:
                c["scraped_real_emails"] = ", ".join(combined_emails)
                email_count += len(new_emails)
                
            existing_phones = c["scraped_phones"].split(", ") if c["scraped_phones"] else []
            new_phones = [p["value"] if isinstance(p, dict) else p for p in phones]
            c["scraped_phones"] = ", ".join(list(set(existing_phones + new_phones)))
            
            c["scraped_linkedins"] = ", ".join(list(set((c["scraped_linkedins"].split(", ") if c["scraped_linkedins"] else []) + [l["value"] if isinstance(l, dict) else l for l in linkedins])))
            
            # Count if this is the first time we added an email to this company
            if not existing_emails and combined_emails:
                enriched_count += 1

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
        
    logger.info(f"Successfully recovered {email_count} real emails!")
    logger.info(f"Enriched {enriched_count} companies with verified contact details!")
    logger.info(f"Saved to {output_csv}")

if __name__ == "__main__":
    salvage_contact_details()
