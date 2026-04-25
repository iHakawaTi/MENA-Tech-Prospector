# MENA Tech Prospector

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square)
![Apify](https://img.shields.io/badge/integration-Apify-yellow.svg?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-purple.svg?style=flat-square)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg?style=flat-square)

MENA Tech Prospector is an automated, cloud-native scraping and data enrichment pipeline designed to build high-quality B2B directories of Technology, IT, and Marketing companies across Jordan and Saudi Arabia (KSA). 

Bypassing aggressive anti-bot protections (like Cloudflare Enterprise) and LinkedIn login walls, this pipeline utilizes Google Search Dorking via Apify to map the ecosystem, identify key decision-makers (CEOs/Founders), extract verified contact details, and generate high-probability email permutations for cold outreach.

---

## Objectives & Capabilities

- **Ecosystem Mapping:** Scrapes leading directories to aggregate IT/Software companies and educational institutions in Jordan and KSA.
- **Anti-Bot Bypass:** Uses Apify's Google Search integrations to completely bypass LinkedIn login walls and Cloudflare checks that block standard Playwright scrapers.
- **CEO Discovery:** Programmatically identifies the exact CEO, Founder, or Managing Director of each company along with their personal LinkedIn URL.
- **Contact Verification:** Deep-crawls target company websites to extract 100% verified public emails, phone numbers, and social media handles.
- **Email Heuristics:** Generates highly probable direct emails for decision-makers (e.g., `first.last@domain.com`) to facilitate direct, personalized cold outreach.

---

## Architecture & Pipeline

The pipeline is entirely modular and relies on [Apify](https://apify.com/) for cloud execution, residential proxies, and stealth scraping. All scripts read from and write to a centralized `companies_master.csv` file, making the pipeline fully sequential and idempotent.

### 1. Discovery (`1_discovery.py`)
Uses Google Dorks (e.g., `site:linkedin.com/company/ ... "Software Development" "Jordan"`) to discover companies. It deduplicates the results and initializes the master database.

### 2. CEO Enrichment (`2_enrich_ceos.py`)
Reads the discovered companies and runs a secondary Google Search Dork targeting individuals. It extracts the exact name, title, and profile URL.

### 3. Contact Extraction (`3_scrape_contacts.py`)
Feeds the company websites into the Apify Contact Info Scraper. It crawls their homepages and contact pages to harvest real emails, phones, and social links.

### 4. Email Generation (`4_guess_emails.py`)
A local heuristic script that combines the extracted CEO names and normalized domain names to generate standard corporate email permutations.

---

## Repository Structure

```text
MENA-Tech-Prospector/
├── data/
│   └── processed/
│       ├── companies_master.csv
│       ├── schools_jordan.csv
│       └── schools_ksa.csv
├── src/
│   ├── scrapers/
│   │   ├── 1_discovery.py
│   │   ├── 2_enrich_ceos.py
│   │   ├── 3_scrape_contacts.py
│   │   └── 4_guess_emails.py
│   └── models/
├── .env.example
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
1. Python 3.10+
2. An [Apify](https://apify.com/) account and API Token.

### Installation

```bash
git clone https://github.com/iHakawaTi/MENA-Tech-Prospector.git
cd MENA-Tech-Prospector

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your APIFY_API_TOKEN
```

---

## Usage Workflow

If you wish to re-run the pipeline from scratch or expand to new countries, follow this exact sequence:

1. **Discover Companies:**
   ```bash
   python src/scrapers/1_discovery.py
   ```
2. **Find Decision Makers:**
   ```bash
   python src/scrapers/2_enrich_ceos.py
   ```
3. **Extract Real Contact Details:**
   ```bash
   python src/scrapers/3_scrape_contacts.py
   ```
4. **Generate Direct Emails:**
   ```bash
   python src/scrapers/4_guess_emails.py
   ```

*(Note: Data is saved iteratively to `data/processed/companies_master.csv` after each step).*

---

## Final Dataset Specs

The resulting `companies_master.csv` contains highly structured data:
- `company_name`, `website`, `domain_normalized`
- `description`, `city`, `country`, `services`
- `ceo_name`, `ceo_title`, `ceo_linkedin_url`
- `scraped_real_emails`, `scraped_phones`, `scraped_linkedins`
- `guessed_emails`, `general_email`

---

## Disclaimer

This tool is designed for B2B research and professional networking. Ensure your outreach complies with local anti-spam regulations (e.g., CAN-SPAM, GDPR) and always verify generated emails before initiating bulk campaigns.