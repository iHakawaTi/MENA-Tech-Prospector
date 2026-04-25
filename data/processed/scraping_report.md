# Jordan Companies Scraper Report
Generated: 2026-04-26 00:47:27

## Summary
- Total raw companies: 170
- After cleaning: 169
- After deduplication: 169

## Sources Used
- Clutch: 37 companies
- TechBehemoths: 30 companies
- The Manifest: 16 companies
- Jordan Directory: 13 companies
- Digital Agency: 12 companies
- Google Search: 9 companies
- F6S: 8 companies
- GoodFirms: 7 companies
- Cybersecurity: 5 companies
- Startup: 5 companies
- AI: 5 companies
- Regional: 5 companies
- Entasher: 4 companies
- Jordan ICT: 4 companies
- Cloud: 3 companies
- Consulting: 3 companies
- University: 2 companies
- Hosting: 1 companies

## Assumptions & Limitations

1. Data quality depends on source availability and page structure
2. Some fields may be empty due to source limitations
3. Deduplication uses domain + fuzzy name matching
4. Filtered out irrelevant business types (restaurants, retail, etc.)
5. Rate limiting applied to respect source servers

## Fields Captured
- company_name, website, source_url, source_name
- city, country, full_location
- category_primary, category_secondary, services
- description, phone, email
- founded_year, company_size, hourly_rate
- rating, review_count, verified_status

## Notes
- Companies filtered to IT/software/digital/marketing/consulting sectors
- Confidence score calculated based on data completeness
- Merged sources track provenance for deduplicated records
