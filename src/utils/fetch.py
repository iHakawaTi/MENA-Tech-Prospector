import logging
import time
import requests
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import random

from ..config import RETRY_CONFIG, RATE_LIMIT, HEADERS

logger = logging.getLogger(__name__)


def fetch_html(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = RETRY_CONFIG["timeout"],
    use_cache: bool = False
) -> Tuple[Optional[str], requests.Response]:
    merged_headers = {**HEADERS}
    if headers:
        merged_headers.update(headers)

    last_error = None
    
    for attempt in range(RETRY_CONFIG["max_retries"]):
        try:
            response = requests.get(
                url,
                headers=merged_headers,
                timeout=timeout
            )
            response.raise_for_status()
            time.sleep(RATE_LIMIT["delay_seconds"] + random.uniform(0.5, 1.5))
            return response.text, response
            
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout: {e}"
            logger.warning(f"Timeout on attempt {attempt + 1}/{RETRY_CONFIG['max_retries']} for {url}")
            
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {e.response.status_code}: {e}"
            logger.warning(f"HTTP error on attempt {attempt + 1}/{RETRY_CONFIG['max_retries']} for {url}: {e.response.status_code}")
            if e.response.status_code in [403, 429]:
                backoff = RETRY_CONFIG["retry_delay"] * (RETRY_CONFIG["backoff_factor"] ** attempt)
                logger.info(f"Rate limited, backing off for {backoff}s")
                time.sleep(backoff)
                
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {e}"
            logger.warning(f"Request error on attempt {attempt + 1}/{RETRY_CONFIG['max_retries']} for {url}: {e}")
        
        if attempt < RETRY_CONFIG["max_retries"] - 1:
            backoff = RETRY_CONFIG["retry_delay"] * (RETRY_CONFIG["backoff_factor"] ** attempt)
            logger.info(f"Retrying in {backoff}s...")
            time.sleep(backoff)
    
    logger.error(f"Failed to fetch {url} after {RETRY_CONFIG['max_retries']} attempts: {last_error}")
    return None, None


def parse_html(html: str, parser: str = "lxml") -> BeautifulSoup:
    return BeautifulSoup(html, parser)


def find_in_soup(soup: BeautifulSoup, selector: str) -> Optional[str]:
    try:
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
    except Exception:
        pass
    return None


def find_all_in_soup(soup: BeautifulSoup, selector: str) -> list:
    try:
        return soup.select(selector)
    except Exception:
        return []


def extract_text_safe(element, strip: bool = True) -> str:
    if element:
        return element.get_text(strip=strip)
    return ""


def extract_attr_safe(element, attr: str) -> str:
    if element and element.has_attr(attr):
        return element[attr]
    return ""


def normalize_url(base: str, path: str) -> str:
    return urljoin(base, path)