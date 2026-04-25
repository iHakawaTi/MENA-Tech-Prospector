from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Company:
    company_name: str = ""
    website: str = ""
    source_url: str = ""
    source_name: str = ""
    company_profile_url: str = ""
    city: str = ""
    country: str = "Jordan"
    full_location: str = ""
    category_primary: str = ""
    category_secondary: str = ""
    services: str = ""
    description: str = ""
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    facebook: str = ""
    instagram: str = ""
    founded_year: str = ""
    company_size: str = ""
    pricing_info: str = ""
    hourly_rate: str = ""
    minimum_project_size: str = ""
    technologies: str = ""
    industries_served: str = ""
    rating: str = ""
    review_count: str = ""
    verified_status: str = ""
    last_seen: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    domain_normalized: str = ""
    name_normalized: str = ""
    merged_sources: str = ""
    confidence_score: float = 0.0
    source_priority: str = ""
    source_count: int = 0
    duplicate_confidence: str = ""

    def to_dict(self):
        return asdict(self)

    def to_dict_clean(self):
        d = asdict(self)
        keys_to_remove = [
            "domain_normalized", 
            "name_normalized", 
            "merged_sources", 
            "confidence_score"
        ]
        for k in keys_to_remove:
            d.pop(k, None)
        return d

    def has_minimal_data(self) -> bool:
        return bool(self.company_name and self.company_name.strip())


DATABASE_FIELDS = [
    "company_name",
    "website",
    "source_url",
    "source_name",
    "company_profile_url",
    "city",
    "country",
    "full_location",
    "category_primary",
    "category_secondary",
    "services",
    "description",
    "phone",
    "email",
    "linkedin",
    "facebook",
    "instagram",
    "founded_year",
    "company_size",
    "pricing_info",
    "hourly_rate",
    "minimum_project_size",
    "technologies",
    "industries_served",
    "rating",
    "review_count",
    "verified_status",
    "last_seen",
    "scraped_at",
    "source_priority",
    "source_count",
    "duplicate_confidence",
]