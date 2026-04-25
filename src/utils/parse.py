import re
from urllib.parse import urlparse, parse_qs
from typing import Optional


def normalize_website(url: str) -> str:
    if not url:
        return ""
    
    url = url.strip().lower()
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        domain = domain.replace("www.", "")
        domain = domain.rstrip("/")
        
        return domain
    except Exception:
        return url


def extract_domain(url: str) -> str:
    if not url:
        return ""
    
    url = url.strip()
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        domain = domain.replace("www.", "")
        
        return domain.lower()
    except Exception:
        return ""


def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    
    name = name.strip().lower()
    
    suffixes_to_remove = [
        r'\s+llc$',
        r'\s+llc\.?$',
        r'\s+inc\.?$',
        r'\s+corp\.?$',
        r'\s+corporation$',
        r'\s+co\.?$',
        r'\s+company$',
        r'\s+ltd\.?$',
        r'\s+limited$',
        r'\s+llp$',
        r'\s+group$',
        r'\s+solutions$',
        r'\s+agency$',
        r'\s+technologies$',
        r'\s+tech$',
        r'\s+services$',
        r'\s+systems$',
    ]
    
    for pattern in suffixes_to_remove:
        name = re.sub(pattern, "", name)
    
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()


def extract_year(text: str) -> Optional[str]:
    if not text:
        return None
    
    patterns = [
        r'\b(19[89]\d|20[0-2]\d)\b',
        r'founded[:\s]+(\d{4})',
        r'established[:\s]+(\d{4})',
        r'since[:\s]+(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_size(text: str) -> Optional[str]:
    if not text:
        return None
    
    text = text.lower()
    
    patterns = [
        (r'(\d{3,4})\s*[-–]\s*(\d{3,4})', lambda m: f"{m.group(1)}-{m.group(2)} employees"),
        (r'(\d+)\s*-\s*(\d+)\s*employees', lambda m: f"{m.group(1)}-{m.group(2)} employees"),
        (r'(\d+)\+?\s*employees', lambda m: f"{m.group(1)} employees"),
        (r'(\d{3,})\s*[-–]\s*(\d{3,})', lambda m: f"{m.group(1)}-{m.group(2)}"),
        (r'1,\d{3}\+', lambda m: m.group(0)),
        (r'10[-\s]?49', lambda m: "10-49"),
        (r'50[-\s]?99', lambda m: "50-99"),
        (r'100[-\s]?249', lambda m: "100-249"),
        (r'250[-\s]?499', lambda m: "250-499"),
        (r'500[-\s]?999', lambda m: "500-999"),
        (r'1000[+]', lambda m: "1000+"),
        (r'[\d,]+', lambda m: m.group(0)),
    ]
    
    for pattern, formatter in patterns:
        match = re.search(pattern, text)
        if match:
            return formatter(match)
    
    return None


def extract_rating(text: str) -> Optional[str]:
    if not text:
        return None
    
    patterns = [
        r'(\d+\.?\d*)\s*/\s*5',
        r'rating[:\s]*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s+stars?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = float(match.group(1))
            if 0 <= rating <= 5:
                return str(rating)
    
    return None


def extract_phone(text: str) -> Optional[str]:
    if not text:
        return None
    
    patterns = [
        r'\+962\d{8,9}',
        r'0\d{9}',
        r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',
        r'\(\+962\)\s*\d{8,9}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def extract_email(text: str) -> Optional[str]:
    if not text:
        return None
    
    pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    match = re.search(pattern, text)
    
    if match:
        return match.group(0)
    
    return None


def extract_city(text: str) -> Optional[str]:
    if not text:
        return None
    
    text = text.lower()
    
    cities = [
        "amman", "zarqa", "irbid", "mafraq", "ma'an", "aqaba", 
        "jadara", "tafilah", "karak", "madaba", "rushdia", 
        "sahab", "naour", "wadi as sir", "jerash", "ajloun",
        "balqa", "allenby", "shuna"
    ]
    
    for city in cities:
        if city.lower() in text:
            return city.title()
    
    return None


def normalize_location(location: str) -> str:
    if not location:
        return ""
    
    location = location.strip()
    
    location = re.sub(r',?\s*jordan$', '', location, flags=re.IGNORECASE)
    
    location = location.strip(', ')
    
    return location


def is_irrelevant_company(name: str, description: str = "") -> bool:
    from ..config import IRRELEVANT_KEYWORDS
    
    text = f"{name} {description}".lower()
    
    for keyword in IRRELEVANT_KEYWORDS:
        if keyword.lower() in text:
            return True
    
    return False