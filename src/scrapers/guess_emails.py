import csv
from pathlib import Path
import re

def clean_domain(url: str) -> str:
    if not url: return ""
    url = url.lower().replace("http://", "").replace("https://", "").replace("www.", "")
    return url.split("/")[0]

def guess_ceo_emails(name: str, domain: str) -> str:
    if not name or not domain or "linkedin" in domain:
        return ""
        
    # Clean name (remove titles, emojis, etc)
    name = re.sub(r'[^a-zA-Z\s]', '', name).strip().lower()
    parts = name.split()
    if len(parts) < 1:
        return ""
        
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    
    emails = []
    emails.append(f"{first}@{domain}")
    if last:
        emails.append(f"{first}.{last}@{domain}")
        emails.append(f"{first[0]}{last}@{domain}")
        
    return ", ".join(emails)

def main():
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_ceos.csv"
    output_file = base_dir / "data" / "processed" / "companies_it_jordan_ksa_final_enriched.csv"
    
    companies = []
    with open(input_file, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))
        
    if not companies: return
    
    fieldnames = list(companies[0].keys())
    if "guessed_emails" not in fieldnames:
        fieldnames.append("guessed_emails")
        fieldnames.append("general_email")
        
    email_count = 0
    for c in companies:
        website = c.get("website", "")
        domain = clean_domain(website)
        ceo_name = c.get("ceo_name", "")
        
        c["guessed_emails"] = ""
        c["general_email"] = ""
        
        if domain:
            c["general_email"] = f"info@{domain}"
            guessed = guess_ceo_emails(ceo_name, domain)
            if guessed:
                c["guessed_emails"] = guessed
                email_count += 1
                
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
        
    print(f"Generated email guesses for {email_count} companies based on CEO names and domains.")
    print(f"File saved to {output_file}")

if __name__ == "__main__":
    main()
