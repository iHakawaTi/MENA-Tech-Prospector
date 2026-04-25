import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "companies_scraper"))

from src.models import Company
from src.utils.parse import (
    normalize_company_name,
    normalize_website,
    extract_year,
    extract_size,
    extract_phone,
    extract_email,
    extract_city,
)
from src.utils.validate import (
    validate_email,
    validate_url,
    validate_rating,
    get_confidence_score,
)


class TestNormalization:
    def test_normalize_company_name_basic(self):
        assert normalize_company_name("Tech Corp LLC") == "tech corp"
        assert normalize_company_name("Example Inc.") == "example"
        assert normalize_company_name("My Company Ltd") == "my company"
    
    def test_normalize_company_name_strips_suffixes(self):
        assert normalize_company_name("Test Solutions LLC") == "test"
        assert normalize_company_name("Dev Agency Inc") == "dev"
        assert normalize_company_name("Data Systems Ltd") == "data"
    
    def test_normalize_website(self):
        assert normalize_website("https://example.com") == "example.com"
        assert normalize_website("www.example.com") == "example.com"
        assert normalize_website("https://www.test.net/") == "test.net"
        assert normalize_website("HTTP://EXAMPLE.COM/PATH") == "example.com"


class TestExtraction:
    def test_extract_year(self):
        assert extract_year("Founded in 2015") == "2015"
        assert extract_year("since 2010") == "2010"
        assert extract_year("Established: 2008") == "2008"
        assert extract_year("2020") == "2020"
    
    def test_extract_size(self):
        assert extract_size("10-49 employees") == "10-49 employees"
        assert extract_size("100-250") == "100-250"
        assert extract_size("500+ employees") is not None
    
    def test_extract_phone(self):
        assert extract_phone("+96265512345") == "+96265512345"
        assert extract_phone("0621234567") == "0621234567"
    
    def test_extract_email(self):
        assert extract_email("contact@example.com") == "contact@example.com"
        assert extract_email("info@company.co.uk") == "info@company.co.uk"
    
    def test_extract_city(self):
        assert extract_city("Amman, Jordan") == "Amman"
        assert extract_city("Irbid") == "Irbid"


class TestValidation:
    def test_validate_email(self):
        assert validate_email("test@example.com") == True
        assert validate_email("invalid") == False
        assert validate_email("") == False
    
    def test_validate_url(self):
        assert validate_url("https://example.com") == True
        assert validate_url("http://test.net") == True
        assert validate_url("not-a-url") == False
    
    def test_validate_rating(self):
        assert validate_rating("4.5") == True
        assert validate_rating("5") == True
        assert validate_rating("0") == True
        assert validate_rating("6") == False
    
    def test_confidence_score(self):
        company = Company(
            company_name="Test Company",
            website="https://test.com",
            description="A test company",
            services="Web development",
            city="Amman",
        )
        score = get_confidence_score(company.to_dict())
        assert score >= 0.5


class TestDeduplication:
    def test_company_schema(self):
        company = Company(
            company_name="Test Company",
            website="https://test.com",
            source_url="https://source.com",
            source_name="Test Source",
        )
        company.domain_normalized = normalize_company_name(company.company_name)
        company.name_normalized = normalize_company_name(company.company_name)
        
        assert company.has_minimal_data() == True
        assert company.company_name == "Test Company"
    
    def test_company_empty_name(self):
        company = Company()
        assert company.has_minimal_data() == False
    
    def test_company_to_dict(self):
        company = Company(
            company_name="Test",
            description="Description",
        )
        data = company.to_dict()
        assert "company_name" in data
        assert data["company_name"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])