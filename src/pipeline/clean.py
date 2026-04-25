import logging
from typing import List
from ..models import Company
from ..utils.parse import (
    normalize_company_name,
    normalize_website,
    extract_city,
    normalize_location,
    is_irrelevant_company
)
from ..utils.validate import get_confidence_score

logger = logging.getLogger(__name__)


def clean_companies(companies: List[Company]) -> List[Company]:
    cleaned = []
    
    for company in companies:
        try:
            cleaned_company = clean_single_company(company)
            
            if cleaned_company and cleaned_company.has_minimal_data():
                if not is_irrelevant_company(
                    cleaned_company.company_name,
                    cleaned_company.description
                ):
                    cleaned.append(cleaned_company)
        except Exception as e:
            logger.debug(f"Error cleaning company {company.company_name}: {e}")
            continue
    
    logger.info(f"Cleaned {len(cleaned)} companies from {len(companies)} raw")
    return cleaned


def clean_single_company(company: Company) -> Company:
    company.company_name = company.company_name.strip()
    company.company_name = company.company_name[:200]
    
    if company.website:
        company.website = company.website.strip()
        
        company.domain_normalized = normalize_website(company.website)
    else:
        company.domain_normalized = ""
    
    company.name_normalized = normalize_company_name(company.company_name)
    
    if company.full_location:
        company.full_location = normalize_location(company.full_location)
    
    if company.city:
        company.city = company.city.strip().title()
    else:
        company.city = extract_city(company.full_location) if company.full_location else ""
    
    if company.description:
        company.description = company.description[:1000]
    
    if company.services:
        company.services = company.services[:500]
    
    company.confidence_score = get_confidence_score(company.to_dict())
    
    return company


def filter_by_relevance(companies: List[Company], min_confidence: float = 0.1) -> List[Company]:
    relevant = []
    
    for company in companies:
        if company.confidence_score >= min_confidence:
            relevant.append(company)
        else:
            logger.debug(f"Filtered out low confidence: {company.company_name} ({company.confidence_score})")
    
    logger.info(f"Filtered to {len(relevant)} relevant companies (min confidence: {min_confidence})")
    return relevant


def normalize_categories(companies: List[Company]) -> List[Company]:
    from ..config import CATEGORY_MAPPING
    
    for company in companies:
        services_text = (company.services or "").lower()
        category = company.category_primary
        
        for keyword, mapped_category in CATEGORY_MAPPING.items():
            if keyword in services_text:
                if not category:
                    category = mapped_category
                break
        
        if category and category not in ["", "Other"]:
            company.category_primary = category.capitalize()
    
    return companies