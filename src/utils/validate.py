import re
from typing import Optional


def validate_email(email: str) -> bool:
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_url(url: str) -> bool:
    if not url:
        return False
    
    url = url.strip().lower()
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))


def validate_phone(phone: str) -> bool:
    if not phone:
        return False
    
    jordan_pattern = r'^(\+962|0)[0-9]{9}$'
    return bool(re.match(jordan_pattern, phone.replace(" ", "").replace("-", "")))


def validate_rating(rating: str) -> bool:
    if not rating:
        return False
    
    try:
        r = float(rating)
        return 0 <= r <= 5
    except (ValueError, TypeError):
        return False


def validate_year(year: str) -> bool:
    if not year:
        return False
    
    try:
        y = int(year)
        return 1900 <= y <= 2030
    except (ValueError, TypeError):
        return False


def validate_company_size(size: str) -> bool:
    if not size:
        return False
    
    return True


def validate_city(city: Optional[str]) -> bool:
    if not city:
        return True
    
    valid_cities = [
        "Amman", "Zarqa", "Irbid", "Mafraq", "Ma'an", "Aqaba",
        "Jadara", "Tafilah", "Karak", "Madaba", "Rushdia",
        "Sahab", "Naour", "Wadi As Sir", "Jerash", "Ajloun",
        "Balqa"
    ]
    
    return city.title() in valid_cities


def has_valid_data(company_dict: dict) -> bool:
    name = company_dict.get("company_name", "").strip()
    return bool(name)


def get_confidence_score(company_dict: dict) -> float:
    score = 0.0
    
    if company_dict.get("company_name"):
        score += 0.3
    
    if company_dict.get("website"):
        score += 0.25
    
    if company_dict.get("description"):
        score += 0.15
    
    if company_dict.get("category_primary"):
        score += 0.1
    
    if company_dict.get("services"):
        score += 0.1
    
    if company_dict.get("city"):
        score += 0.05
    
    if company_dict.get("phone") or company_dict.get("email"):
        score += 0.05
    
    return min(score, 1.0)