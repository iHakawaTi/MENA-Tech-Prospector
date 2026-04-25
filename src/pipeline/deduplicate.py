import logging
from typing import List, Dict, Tuple, Set
from rapidfuzz import fuzz
from collections import defaultdict
from ..models import Company

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85
NAME_SIMILARITY_THRESHOLD = 90


def deduplicate_companies(companies: List[Company]) -> List[Company]:
    if not companies:
        return []
    
    logger.info(f"Starting deduplication of {len(companies)} companies")
    
    grouped = group_by_domain(companies)
    logger.info(f"Grouped into {len(grouped)} domain groups")
    
    merged = merge_groups(grouped)
    logger.info(f"After deduplication: {len(merged)} unique companies")
    
    return merged


def group_by_domain(companies: List[Company]) -> Dict[str, List[Company]]:
    domain_groups = defaultdict(list)
    
    for company in companies:
        domain = company.domain_normalized
        
        if domain:
            domain_groups[domain].append(company)
        else:
            key = company.name_normalized if company.name_normalized else company.company_name.lower().strip()
            domain_groups[key].append(company)
    
    return domain_groups


def group_by_name_similarity(companies: List[Company]) -> Dict[str, List[Company]]:
    name_groups = defaultdict(list)
    processed: Set[str] = set()
    
    for company in companies:
        name_key = company.name_normalized if company.name_normalized else company.company_name.lower().strip()
        
        found_group = None
        for existing_key in name_groups.keys():
            if existing_key in processed:
                continue
            
            try:
                similarity = fuzz.ratio(name_key, existing_key)
            except Exception:
                similarity = 0
            
            if similarity >= NAME_SIMILARITY_THRESHOLD:
                found_group = existing_key
                break
        
        if found_group:
            name_groups[found_group].append(company)
        else:
            name_groups[name_key].append(company)
            processed.add(name_key)
    
    return name_groups


def merge_groups(domain_groups: Dict[str, List[Company]]) -> List[Company]:
    merged_companies = []
    seen_names: Set[str] = set()
    
    for domain, group in domain_groups.items():
        candidates = []
        
        for company in group:
            name_key = company.name_normalized if company.name_normalized else company.company_name.lower().strip()
            
            is_duplicate = False
            for seen_name in seen_names:
                try:
                    similarity = fuzz.ratio(name_key, seen_name)
                except Exception:
                    similarity = 0
                
                if similarity >= NAME_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                candidates.append(company)
                seen_names.add(name_key)
        
        if candidates:
            best = select_best_company(candidates)
            best.domain_normalized = domain
            best.merged_sources = ", ".join([
                f"{c.source_name} ({c.source_url})" for c in group
            ])
            merged_companies.append(best)
    
    return merged_companies


def select_best_company(companies: List[Company]) -> Company:
    if len(companies) == 1:
        return companies[0]
    
    candidates = sorted(
        companies,
        key=lambda c: (
            bool(c.domain_normalized),
            c.confidence_score if c.confidence_score else 0,
            len(c.description or ""),
            len(c.services or ""),
            len(c.website or "")
        ),
        reverse=True
    )
    
    primary = candidates[0]
    all_sources = []
    
    for c in companies:
        source = f"{c.source_name}"
        if c.source_url and c.source_url not in all_sources:
            all_sources.append(source)
    
    if len(all_sources) > 1:
        primary.merged_sources = " | ".join(set(all_sources))
    
    return primary


def fuzzy_match_merge(companies: List[Company], threshold: int = FUZZY_THRESHOLD) -> List[Company]:
    merged: List[Company] = []
    merged_names: Set[str] = set()
    
    for company in companies:
        name = company.name_normalized if company.name_normalized else company.company_name.lower().strip()
        
        best_match = None
        best_score = 0
        
        for existing in merged:
            existing_name = existing.name_normalized if existing.name_normalized else existing.company_name.lower().strip()
            
            try:
                score = fuzz.ratio(name, existing_name)
            except Exception:
                score = 0
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = existing
        
        if best_match:
            merge_companies(best_match, company)
        else:
            merged.append(company)
            merged_names.add(name)
    
    return merged


def merge_companies(primary: Company, secondary: Company) -> None:
    if not primary.domain_normalized and secondary.domain_normalized:
        primary.domain_normalized = secondary.domain_normalized
    
    if not primary.website and secondary.website:
        primary.website = secondary.website
    
    if not primary.description and secondary.description:
        primary.description = secondary.description
    
    if not primary.services and secondary.services:
        primary.services = secondary.services
    
    if not primary.city and secondary.city:
        primary.city = secondary.city
    
    if not primary.phone and secondary.phone:
        primary.phone = secondary.phone
    
    if not primary.email and secondary.email:
        primary.email = secondary.email
    
    if not primary.rating and secondary.rating:
        primary.rating = secondary.rating
    
    if not primary.review_count and secondary.review_count:
        primary.review_count = secondary.review_count
    
    if not primary.verified_status and secondary.verified_status:
        primary.verified_status = secondary.verified_status
    
    if not primary.company_size and secondary.company_size:
        primary.company_size = secondary.company_size
    
    if not primary.hourly_rate and secondary.hourly_rate:
        primary.hourly_rate = secondary.hourly_rate
    
    if primary.confidence_score and secondary.confidence_score:
        primary.confidence_score = max(primary.confidence_score, secondary.confidence_score)
    elif secondary.confidence_score:
        primary.confidence_score = secondary.confidence_score
    
    source_entry = f"{secondary.source_name}"
    if primary.merged_sources:
        if source_entry not in primary.merged_sources:
            primary.merged_sources += f", {source_entry}"
    else:
        primary.merged_sources = source_entry