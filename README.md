# MENA Tech Prospector 🦅

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)
![Apify](https://img.shields.io/badge/Powered%20By-Apify-yellow)
![License](https://img.shields.io/badge/license-MIT-purple)

**MENA Tech Prospector** is an automated, cloud-native scraping and data enrichment pipeline designed to build high-quality B2B directories of Technology, IT, and Marketing companies across **Jordan** and **Saudi Arabia (KSA)**. 

Bypassing aggressive anti-bot protections (like Cloudflare Enterprise) and LinkedIn login walls, this pipeline utilizes Google Search Dorking via Apify to map the ecosystem, identify key decision-makers (CEOs/Founders), extract verified contact details, and generate high-probability email permutations for cold outreach.

---

## 🎯 Objectives & Capabilities

*   **Ecosystem Mapping:** Scrapes leading directories to aggregate IT/Software companies and educational institutions in Jordan and KSA.
*   **Anti-Bot Bypass:** Uses Apify's Google Search integrations to completely bypass LinkedIn login walls and Cloudflare checks that block standard Playwright scrapers.
*   **CEO Discovery:** Programmatically identifies the exact CEO, Founder, or Managing Director of each company along with their personal LinkedIn URL.
*   **Contact Verification:** Deep-crawls target company websites to extract 100% verified public emails (e.g., `info@`, `sales@`), phone numbers, and social media handles.
*   **Email Heuristics:** Generates highly probable direct emails for decision-makers (e.g., `first.last@domain.com`) to facilitate direct, personalized cold outreach.

---

## 🏗️ Architecture & Pipeline

The pipeline is entirely modular and relies on [Apify](https://apify.com/) for cloud execution, residential proxies, and stealth scraping. 

### 1. Discovery (`expand_scrape.py`)
Uses Google Dorks (e.g., `site:linkedin.com/company/ ... "Software Development" "Jordan"`) to discover companies. It dedupes the results and outputs pristine CSVs.

### 2. CEO Enrichment (`enrich_ceos.py`)
Reads the discovered companies and runs a secondary Google Search Dork targeting individuals (e.g., `site:linkedin.com/in "CEO" "Company Name"`). It extracts the exact name, title, and profile URL.

### 3. Contact Extraction (`scrape_contacts.py` & `continue_scrape_contacts.py`)
Feeds the company websites into the Apify Contact Info Scraper (`vdrmota/contact-info-scraper`). It crawls their homepages and contact pages to harvest real emails, phones, and social links.

### 4. Email Generation (`guess_emails.py`)
A local heuristic script that combines the extracted CEO names and normalized domain names to generate standard corporate email permutations.

### 5. Memory Salvage (`salvage_contacts.py`)
A fail-safe utility. If the Apify Contact Scraper crashes due to memory limits when hitting massive/broken websites, this script extracts all successfully scraped data directly from the dead actor's dataset.

---

## 📂 Repository Structure

```text
📦 MENA-Tech-Prospector
├── 📁 data/
│   └── 📁 processed/
│       ├── companies_master.csv        # The ultimate enriched database!
│       ├── companies_ksa.csv           # KSA specific slice
│       ├── schools_jordan.csv          # Jordanian educational institutions
│       └── schools_ksa.csv             # KSA educational institutions
├── 📁 src/
│   ├── 📁 scrapers/
│   │   ├── expand_scrape.py            # Primary discovery script
│   │   ├── enrich_ceos.py              # CEO/Founder identification
│   │   ├── guess_emails.py             # Email permutation generator
│   │   ├── scrape_contacts.py          # Deep website crawler for contacts
│   │   ├── continue_scrape_contacts.py # Resumes crawling on failure
│   │   ├── salvage_contacts.py         # Recovers data from crashed runs
│   │   ├── linkedin_apify.py           # Apify Google Search logic
│   │   └── apify_scraper.py            # Core Apify client wrappers
│   └── 📁 models/                      # Pydantic/Dataclass definitions
├── .env.example                        # API keys template
├── requirements.txt                    # Python dependencies
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
1. Python 3.10+
2. An [Apify](https://apify.com/) account and API Token.

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/MENA-Tech-Prospector.git
cd MENA-Tech-Prospector

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup your environment variables
cp .env.example .env
# Edit .env and add your APIFY_API_TOKEN
```

---

## ⚙️ Usage Workflow

If you wish to re-run the pipeline from scratch or expand to new countries (e.g., UAE, Egypt), follow this sequence:

1. **Discover Companies:**
   ```bash
   python src/scrapers/expand_scrape.py
   ```
2. **Find Decision Makers:**
   ```bash
   python src/scrapers/enrich_ceos.py
   ```
3. **Extract Real Contact Details:**
   ```bash
   python src/scrapers/scrape_contacts.py
   ```
4. **Generate Direct Emails:**
   ```bash
   python src/scrapers/guess_emails.py
   ```

*(Note: If `scrape_contacts.py` crashes due to Apify memory limits on large sites, run `continue_scrape_contacts.py` and then use `salvage_contacts.py` to merge the data).*

---

## 📊 Final Dataset Specs

The resulting `companies_master.csv` contains highly structured data:
*   `company_name`, `website`, `domain_normalized`
*   `description`, `city`, `country`, `services`
*   `ceo_name`, `ceo_title`, `ceo_linkedin_url`
*   `scraped_real_emails`, `scraped_phones`, `scraped_linkedins`
*   `guessed_emails`, `general_email`

---

## ⚠️ Disclaimer

This tool is designed for B2B research and professional networking. Ensure your outreach complies with local anti-spam regulations (e.g., CAN-SPAM, GDPR) and always verify generated emails before initiating bulk campaigns.

---
*Built for precision and scale. No more manual data entry.*