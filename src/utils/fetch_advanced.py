import logging
import time
import random
import requests
from typing import Optional, Tuple, Dict, Any, Callable
from urllib.parse import urljoin
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

from ..config import RETRY_CONFIG, RATE_LIMIT, HEADERS


@dataclass
class FetchResult:
    success: bool
    content: Optional[str] = None
    mode_used: str = ""
    response_time: float = 0.0
    error: str = ""
    attempts: int = 0


@dataclass
class SourceDiagnostics:
    source_name: str = ""
    mode_used: str = "skip"
    homepage_reachable: bool = False
    listing_reachable: bool = False
    pagination_works: bool = False
    avg_response_time: float = 0.0
    records_extracted: int = 0
    failure_reason: str = ""
    started_at: str = ""
    completed_at: str = ""


class SessionFetcher:
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.request_count = 0
        self.total_response_time = 0.0
        self.last_request_time = 0.0
        
    def _get_domain_delay(self, url: str) -> float:
        base_delay = RATE_LIMIT["delay_seconds"]
        jitter = random.uniform(0.5, 1.5)
        return base_delay + jitter
    
    def _should_retry(self, status_code: int, attempt: int) -> bool:
        if status_code in [403, 429]:
            return True
        if status_code >= 500:
            return True
        if attempt < RETRY_CONFIG["max_retries"]:
            return True
        return False
    
    def _get_backoff_delay(self, attempt: int, status_code: int = None) -> float:
        base = RETRY_CONFIG["retry_delay"]
        factor = RETRY_CONFIG["backoff_factor"]
        delay = base * (factor ** attempt)
        
        if status_code in [403, 429]:
            delay *= 2
            
        return delay + random.uniform(0.5, 2.0)
    
    def fetch(
        self, 
        url: str, 
        timeout: int = RETRY_CONFIG["timeout"],
        warmup_url: Optional[str] = None
    ) -> FetchResult:
        
        start_time = time.time()
        attempts = 0
        last_error = ""
        
        if warmup_url:
            try:
                self.session.get(warmup_url, timeout=10)
                time.sleep(1)
            except Exception:
                pass
        
        for attempt in range(RETRY_CONFIG["max_retries"]):
            attempts = attempt + 1
            
            elapsed = time.time() - self.last_request_time
            if elapsed < self._get_domain_delay(url):
                time.sleep(self._get_domain_delay(url) - elapsed)
            
            try:
                req_start = time.time()
                response = self.session.get(
                    url,
                    timeout=timeout,
                    allow_redirects=True
                )
                req_time = time.time() - req_start
                self.request_count += 1
                self.total_response_time += req_time
                self.last_request_time = time.time()
                
                if response.status_code == 200:
                    return FetchResult(
                        success=True,
                        content=response.text,
                        mode_used="session_http",
                        response_time=req_time,
                        attempts=attempts
                    )
                elif self._should_retry(response.status_code, attempt):
                    backoff = self._get_backoff_delay(attempt, response.status_code)
                    logger.warning(
                        f"[{self.source_name}] HTTP {response.status_code} on attempt {attempts}, "
                        f"backing off {backoff:.1f}s"
                    )
                    time.sleep(backoff)
                    last_error = f"HTTP {response.status_code}"
                    continue
                else:
                    return FetchResult(
                        success=False,
                        mode_used="session_http",
                        error=f"HTTP {response.status_code}",
                        attempts=attempts,
                        response_time=req_time
                    )
                    
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                logger.warning(f"[{self.source_name}] Timeout on attempt {attempts}")
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                logger.warning(f"[{self.source_name}] Request error on attempt {attempts}: {e}")
            
            if attempt < RETRY_CONFIG["max_retries"] - 1:
                backoff = self._get_backoff_delay(attempt)
                logger.info(f"[{self.source_name}] Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
        
        return FetchResult(
            success=False,
            mode_used="session_http",
            error=last_error or "Max retries exceeded",
            attempts=attempts,
            response_time=time.time() - start_time
        )
    
    def get_stats(self) -> Dict[str, Any]:
        avg_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
        return {
            "request_count": self.request_count,
            "total_response_time": self.total_response_time,
            "avg_response_time": avg_time
        }


class MultiModeFetcher:
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session_fetcher = SessionFetcher(source_name)
        self.diagnostics = SourceDiagnostics()
        self.diagnostics.source_name = source_name
        self.diagnostics.started_at = datetime.now().isoformat()
        
    def try_session_http(self, url: str, warmup_url: str = None) -> FetchResult:
        logger.info(f"[{self.source_name}] Trying session_http mode")
        result = self.session_fetcher.fetch(url, warmup_url=warmup_url)
        
        if result.success:
            self.diagnostics.mode_used = "session_http"
            self.diagnostics.homepage_reachable = True
            
        return result
    
    def try_playwright(self, url: str) -> FetchResult:
        logger.info(f"[{self.source_name}] Trying playwright mode")
        try:
            from playwright.sync_api import sync_playwright
            
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={'width': 1280, 'height': 720},
                locale='en-US',
                timezone_id='Asia/Amman'
            )
            
            page = context.new_page()
            page.set_default_timeout(30000)
            
            start_time = time.time()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            response_time = time.time() - start_time
            
            content = page.content()
            
            browser.close()
            playwright.stop()
            
            self.diagnostics.mode_used = "playwright"
            self.diagnostics.homepage_reachable = True
            
            return FetchResult(
                success=True,
                content=content,
                mode_used="playwright",
                response_time=response_time,
                attempts=1
            )
            
        except Exception as e:
            logger.error(f"[{self.source_name}] Playwright failed: {e}")
            return FetchResult(
                success=False,
                mode_used="playwright",
                error=str(e)
            )
    
    def fetch_with_fallback(self, url: str, warmup_url: str = None) -> FetchResult:
        result = self.try_session_http(url, warmup_url)
        
        if not result.success:
            logger.info(f"[{self.source_name}] Session HTTP failed, trying Playwright")
            result = self.try_playwright(url)
        
        return result
    
    def finalize_diagnostics(self, records_extracted: int = 0, failure_reason: str = ""):
        self.diagnostics.records_extracted = records_extracted
        self.diagnostics.completed_at = datetime.now().isoformat()
        
        if self.session_fetcher.request_count > 0:
            stats = self.session_fetcher.get_stats()
            self.diagnostics.avg_response_time = stats["avg_response_time"]
        
        if failure_reason:
            self.diagnostics.failure_reason = failure_reason
            
        return self.diagnostics


def create_fetcher(source_name: str) -> Tuple[MultiModeFetcher, SourceDiagnostics]:
    fetcher = MultiModeFetcher(source_name)
    return fetcher, fetcher.diagnostics