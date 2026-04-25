import logging
import time
import random
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup

from ..models import Company
from ..utils.fetch_advanced import SessionFetcher

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    company_name: str
    page_title: str = ""
    meta_description: str = ""
    about_text: str = ""
    contact_page: str = ""
    email: str = ""
    linkedin: str = ""
    facebook: str = ""
    instagram: str = ""
    location: str = ""
    phone: str = ""
    enrichment_status: str = "failed"


class WebsiteEnricher:
    def __init__(self, max_visits: int = 50):
        self.max_visits = max_visits
        self.visit_count = 0
        self.results: List[EnrichmentResult] = []
        
    def _extract_email(self, text: str) -> Optional[str]:
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        patterns = [
            r'\+962\d{8,9}',
            r'0\d{9}',
            r'\(\+962\)\s*\d{8,9}',
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    def _extract_social(self, soup: BeautifulSoup) -> Dict[str, str]:
        socials = {"linkedin": "", "facebook": "", "instagram": ""}
        
        links = soup.select("a[href]")
        for link in links:
            href = link.get("href", "")
            href_lower = href.lower()
            if "linkedin.com" in href_lower and not socials["linkedin"]:
                socials["linkedin"] = href
            elif "facebook.com" in href_lower and not socials["facebook"]:
                socials["facebook"] = href
            elif "instagram.com" in href_lower and not socials["instagram"]:
                socials["instagram"] = href
        
        return socials
    
    def _extract_location(self, text: str) -> Optional[str]:
        jordan_cities = ["amman", "irbid", "zarqa", "aqaba", "mafraq", "madaba", "karak"]
        text_lower = text.lower()
        for city in jordan_cities:
            if city in text_lower:
                return city.title()
        return None
    
    def enrich_company(self, company: Company) -> EnrichmentResult:
        if not company.website or not company.website.startswith("http"):
            return EnrichmentResult(company_name=company.company_name, enrichment_status="no website")
        
        if self.visit_count >= self.max_visits:
            return EnrichmentResult(company_name=company.company_name, enrichment_status="max visits reached")
        
        fetcher = SessionFetcher(f"Enrichment-{company.company_name}")
        result = fetcher.fetch(company.website, timeout=15)
        
        self.visit_count += 1
        
        if not result.success:
            return EnrichmentResult(
                company_name=company.company_name,
                enrichment_status="fetch failed"
            )
        
        soup = BeautifulSoup(result.content, "lxml")
        
        page_title = soup.title.get_text(strip=True) if soup.title else ""
        
        meta_desc = ""
        desc_tag = soup.find("meta", {"name": "description"})
        if desc_tag:
            meta_desc = desc_tag.get("content", "")
        
        about_text = ""
        about_candidates = soup.select("div#about, div.about, section#about, section.about, div[data-tab='about']")
        for candidate in about_candidates[:3]:
            text = candidate.get_text(strip=True)[:500]
            if text:
                about_text = text
                break
        
        contact_page = ""
        contact_links = soup.select("a[href*='contact']")
        for link in contact_links[:2]:
            href = link.get("href", "")
            if href and not href.startswith("#"):
                contact_page = href
                break
        
        email = self._extract_email(result.content)
        phone = self._extract_phone(result.content)
        
        socials = self._extract_social(soup)
        
        location = self._extract_location(result.content)
        
        return EnrichmentResult(
            company_name=company.company_name,
            page_title=page_title,
            meta_description=meta_desc,
            about_text=about_text,
            contact_page=contact_page,
            email=email or "",
            linkedin=socials["linkedin"],
            facebook=socials["facebook"],
            instagram=socials["instagram"],
            location=location or "",
            phone=phone or "",
            enrichment_status="success"
        )
    
    def enrich_batch(self, companies: List[Company]) -> List[EnrichmentResult]:
        results = []
        
        for i, company in enumerate(companies[:self.max_visits]):
            logger.info(f"Enriching {i+1}/{min(len(companies), self.max_visits)}: {company.company_name}")
            
            result = self.enrich_company(company)
            results.append(result)
            
            if i < len(companies) - 1 and result.enrichment_status == "success":
                delay = random.uniform(2, 4)
                time.sleep(delay)
        
        self.results = results
        return results
    
    def apply_enrichment(self, companies: List[Company]) -> List[Company]:
        results = self.enrich_batch(companies)
        
        for company, result in zip(companies, results):
            if result.enrichment_status == "success":
                if result.meta_description and not company.description:
                    company.description = result.meta_description[:500]
                elif result.about_text and not company.description:
                    company.description = result.about_text[:500]
                
                if result.email and not company.email:
                    company.email = result.email
                
                if result.phone and not company.phone:
                    company.phone = result.phone
                
                if result.linkedin:
                    company.linkedin = result.linkedin
                
                if result.facebook:
                    company.facebook = result.facebook
                
                if result.location and not company.city:
                    company.city = result.location
        
        return companies
    
    def get_summary(self) -> Dict:
        success_count = sum(1 for r in self.results if r.enrichment_status == "success")
        return {
            "total_attempted": len(self.results),
            "successful": success_count,
            "failed": len(self.results) - success_count,
            "success_rate": success_count / len(self.results) * 100 if self.results else 0
        }


def enrich_companies(companies: List[Company], max_visits: int = 30) -> Tuple[List[Company], Dict]:
    logger.info(f"Starting enrichment for {len(companies)} companies (max {max_visits})")
    
    enricher = WebsiteEnricher(max_visits=max_visits)
    enriched_companies = enricher.apply_enrichment(companies)
    summary = enricher.get_summary()
    
    logger.info(f"Enrichment complete: {summary}")
    
    return enriched_companies, summary