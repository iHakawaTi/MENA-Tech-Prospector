"""
Step 4: Guess Emails
Reads companies_master.csv, generates probable CEO emails and general info@ emails based on domain.
"""
import csv
import re
import logging
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def clean_domain(url: str) -> str:
    if not url: return ""
    if not url.startswith("http"): url = "http://" + url
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain.split('/')[0]

def guess_ceo_emails(name: str, domain: str) -> str:
    if not name or not domain: return ""
    name = re.sub(r'[^a-zA-Z\s]', '', name).strip().lower()
    parts = name.split()
    if len(parts) < 1: return ""
        
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    
    emails = [f"{first}@{domain}"]
    if last:
        emails.extend([f"{first}.{last}@{domain}", f"{first[0]}{last}@{domain}"])
        
    return ", ".join(emails)

def main():
    base_dir = Path(__file__).parent.parent.parent
    master_csv = base_dir / "data" / "processed" / "companies_master.csv"
    
    if not master_csv.exists(): return
    with open(master_csv, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))

    for c in companies:
        domain = clean_domain(c.get("website", ""))
        ceo_name = c.get("ceo_name", "")
        if domain:
            c["general_email"] = f"info@{domain}"
            guessed = guess_ceo_emails(ceo_name, domain)
            if guessed: c["guessed_emails"] = guessed

    with open(master_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(companies[0].keys()))
        writer.writeheader()
        writer.writerows(companies)
        
    logger.info("Master file updated with generated/guessed emails.")

if __name__ == "__main__":
    main()
