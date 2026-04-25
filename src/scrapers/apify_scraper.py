"""
Apify-powered scrapers for Jordan company directories.

Uses Apify's cloud infrastructure (residential proxies, real browsers) to
bypass Cloudflare and JavaScript rendering on all target sites.

Actors used:
  - apify/playwright-scraper  : full browser, JS rendering, network intercept
  - apify/cheerio-scraper     : fast HTML scraper for simpler sites

Each scraper submits a run to Apify, waits for completion, then pulls
the dataset and converts records to Company objects.
"""

import os
import logging
import time
import json
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from apify_client import ApifyClient

from ..models import Company
from ..utils.parse import (
    normalize_website, normalize_company_name,
    extract_year, extract_city,
)

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")


def _get_client() -> ApifyClient:
    if not APIFY_TOKEN:
        raise RuntimeError("APIFY_API_TOKEN not set in .env")
    return ApifyClient(APIFY_TOKEN)


def _run_actor(client: ApifyClient, actor_id: str, run_input: dict,
               label: str, timeout_secs: int = 300) -> list:
    """
    Start an Apify actor run, wait for it to finish, return dataset items.
    """
    logger.info(f"[Apify/{label}] Starting actor {actor_id} ...")
    run = client.actor(actor_id).call(
        run_input=run_input,
        timeout_secs=timeout_secs,
        memory_mbytes=1024,
    )
    status = run.get("status", "UNKNOWN")
    run_id = run.get("id", "?")
    logger.info(f"[Apify/{label}] Run {run_id} finished with status: {status}")

    if status != "SUCCEEDED":
        logger.warning(f"[Apify/{label}] Run did not succeed (status={status})")
        return []

    dataset_id = run.get("defaultDatasetId")
    items = list(client.dataset(dataset_id).iterate_items())
    logger.info(f"[Apify/{label}] Retrieved {len(items)} items from dataset")
    return items


def _dict_to_company(item: dict, source_name: str, source_url: str) -> Optional[Company]:
    """Convert an Apify result dict into a Company object."""
    try:
        name = (
            item.get("name") or item.get("company_name") or
            item.get("companyName") or item.get("title") or
            item.get("Company Name") or ""
        ).strip()

        if not name or len(name) < 2:
            return None

        website = (
            item.get("website") or item.get("websiteUrl") or
            item.get("url") or item.get("Website") or ""
        ).strip()

        description = str(
            item.get("description") or item.get("tagline") or
            item.get("bio") or item.get("Description") or ""
        )[:500]

        city_raw = (
            item.get("city") or item.get("location") or
            item.get("City") or item.get("address") or "Amman"
        )
        city = extract_city(str(city_raw)) or "Amman"

        services_raw = item.get("services") or item.get("tags") or item.get("Services") or []
        if isinstance(services_raw, list):
            services = ", ".join(
                s.get("name", s) if isinstance(s, dict) else str(s)
                for s in services_raw
            )
        else:
            services = str(services_raw)

        rating = str(item.get("rating") or item.get("Rating") or "")
        review_count = str(item.get("reviews") or item.get("reviewCount") or item.get("Reviews") or "")
        size = str(item.get("employees") or item.get("teamSize") or item.get("company_size") or "")
        hourly_rate = str(item.get("hourlyRate") or item.get("hourly_rate") or "")
        founded = extract_year(str(item.get("foundedYear") or item.get("founded") or ""))
        verified = "verified" if item.get("verified") or item.get("isVerified") else ""

        profile_url = str(item.get("profileUrl") or item.get("profile_url") or item.get("url") or "")

        company = Company(
            company_name=name,
            website=website,
            source_url=source_url,
            source_name=source_name,
            company_profile_url=profile_url,
            city=city,
            country="Jordan",
            services=services,
            description=description,
            company_size=size,
            founded_year=founded,
            hourly_rate=hourly_rate,
            rating=rating,
            review_count=review_count,
            verified_status=verified,
        )

        if website:
            company.domain_normalized = normalize_website(website)
        company.name_normalized = normalize_company_name(name)
        return company

    except Exception as e:
        logger.debug(f"[Apify] dict_to_company error: {e}")
        return None


# ─── Page functions (JS that runs inside the browser on Apify) ────────────────

# TechBehemoths page function — intercepts the API call the page makes
_TB_PAGE_FUNCTION = """
async function pageFunction(context) {
    const { page, request, log } = context;
    const results = [];

    // Intercept all XHR/fetch responses to find the company API
    const apiData = [];
    await page.setRequestInterception(true);

    page.on('request', req => req.continue());
    page.on('response', async resp => {
        const url = resp.url();
        const ct = resp.headers()['content-type'] || '';
        if (ct.includes('json') && (
            url.includes('/api/') || url.includes('/companies') ||
            url.includes('graphql')
        )) {
            try {
                const body = await resp.json();
                apiData.push({ url, body });
            } catch(e) {}
        }
    });

    await page.waitForSelector('a[href*="/company/"], h3, div[class*="company"]',
                               { timeout: 15000 }).catch(() => {});
    await new Promise(r => setTimeout(r, 3000));

    // Scroll to trigger lazy loading
    for (let y = 300; y <= 2000; y += 300) {
        await page.evaluate(ys => window.scrollTo(0, ys), y);
        await new Promise(r => setTimeout(r, 400));
    }
    await new Promise(r => setTimeout(r, 2000));

    // Try to get data from intercepted API responses
    for (const { body } of apiData) {
        const items = body.data || body.companies || body.results || (Array.isArray(body) ? body : []);
        for (const item of items) {
            const name = item.name || item.company_name || item.title || '';
            if (name && name.length > 1) {
                results.push({
                    name,
                    website: item.website || item.url || '',
                    description: item.description || item.bio || '',
                    city: item.city || (item.location && item.location.city) || 'Amman',
                    services: Array.isArray(item.services)
                        ? item.services.map(s => s.name || s).join(', ')
                        : (item.services || ''),
                    rating: String(item.rating || item.score || ''),
                    reviewCount: String(item.reviews_count || item.review_count || ''),
                    teamSize: String(item.team_size || item.employees_count || ''),
                    hourlyRate: String(item.hourly_rate || item.min_hourly_rate || ''),
                    foundedYear: String(item.founded_year || item.founded || ''),
                    verified: !!(item.verified || item.is_verified),
                    profileUrl: item.slug
                        ? 'https://techbehemoths.com/company/' + item.slug
                        : (item.profile_url || ''),
                    sourceUrl: request.url,
                });
            }
        }
    }

    // Fallback: DOM scraping
    if (results.length === 0) {
        const links = await page.$$eval('a[href*="/company/"]', els =>
            els.map(el => ({
                name: el.innerText.trim(),
                profileUrl: el.href,
            })).filter(x => x.name.length > 1)
        );
        for (const lnk of links.slice(0, 60)) {
            results.push({ ...lnk, city: 'Amman', sourceUrl: request.url });
        }
    }

    log.info(`Extracted ${results.length} companies from ${request.url}`);
    return results;
}
"""

# Clutch page function
_CLUTCH_PAGE_FUNCTION = """
async function pageFunction(context) {
    const { page, request, log } = context;
    const results = [];
    const apiData = [];

    await page.setRequestInterception(true);
    page.on('request', req => req.continue());
    page.on('response', async resp => {
        const url = resp.url();
        const ct = resp.headers()['content-type'] || '';
        if (ct.includes('json') && (
            url.includes('/api/') || url.includes('graphql') ||
            url.includes('/_next/data') || url.includes('/providers')
        )) {
            try {
                const body = await resp.json();
                apiData.push({ url, body });
            } catch(e) {}
        }
    });

    await page.waitForSelector('h3, li[class*="provider"], a[href*="/co/"]',
                               { timeout: 15000 }).catch(() => {});
    await new Promise(r => setTimeout(r, 4000));

    for (let y = 400; y <= 3000; y += 400) {
        await page.evaluate(ys => window.scrollTo(0, ys), y);
        await new Promise(r => setTimeout(r, 500));
    }
    await new Promise(r => setTimeout(r, 3000));

    // Check __NEXT_DATA__
    const nextData = await page.evaluate(() => {
        const el = document.getElementById('__NEXT_DATA__');
        if (!el) return null;
        try { return JSON.parse(el.textContent); } catch(e) { return null; }
    });

    if (nextData) {
        const props = nextData.props && nextData.props.pageProps;
        const providers = (props && (props.providers || (props.data && props.data.providers))) || [];
        for (const p of providers) {
            const name = p.company_name || p.name || p.title || '';
            if (name.length > 1) {
                results.push({
                    name,
                    website: p.website || '',
                    description: p.description || p.summary || '',
                    city: (p.location && p.location.city) || p.city || 'Amman',
                    services: Array.isArray(p.services)
                        ? p.services.map(s => s.name || s).join(', ')
                        : '',
                    rating: String(p.rating || p.average_rating || ''),
                    reviewCount: String(p.reviews || p.review_count || ''),
                    teamSize: String(p.employees || p.company_size || ''),
                    hourlyRate: String(p.min_hourly_rate || ''),
                    verified: !!(p.is_clutch_champion || p.verified),
                    profileUrl: p.slug ? 'https://clutch.co/' + p.slug : '',
                    sourceUrl: request.url,
                });
            }
        }
    }

    // API intercept fallback
    if (results.length === 0) {
        for (const { body } of apiData) {
            const items = body.providers || body.companies || body.data || (Array.isArray(body) ? body : []);
            for (const item of items) {
                const name = item.company_name || item.name || '';
                if (name.length > 1) {
                    results.push({
                        name,
                        website: item.website || '',
                        city: (item.location && item.location.city) || 'Amman',
                        rating: String(item.rating || ''),
                        reviewCount: String(item.review_count || ''),
                        verified: !!(item.verified),
                        profileUrl: item.slug ? 'https://clutch.co/' + item.slug : '',
                        sourceUrl: request.url,
                    });
                }
            }
        }
    }

    // DOM fallback
    if (results.length === 0) {
        const links = await page.$$eval('a[href*="/co/"]', els =>
            els.map(el => ({
                name: el.innerText.trim(),
                profileUrl: el.href,
            })).filter(x => x.name.length > 1 && x.name.length < 100)
        );
        for (const lnk of links.slice(0, 60)) {
            results.push({ ...lnk, city: 'Amman', sourceUrl: request.url });
        }
    }

    log.info(`Extracted ${results.length} from ${request.url}`);
    return results;
}
"""

# Generic page function for Manifest / GoodFirms / PerfectFirms
_GENERIC_PAGE_FUNCTION = """
async function pageFunction(context) {
    const { page, request, log } = context;
    const results = [];

    // Check __NEXT_DATA__ first
    const nextData = await page.evaluate(() => {
        const el = document.getElementById('__NEXT_DATA__');
        if (!el) return null;
        try { return JSON.parse(el.textContent); } catch(e) { return null; }
    });

    function walk(obj, depth) {
        if (depth > 8 || !obj) return;
        if (Array.isArray(obj) && obj.length > 1 && typeof obj[0] === 'object') {
            const sample = obj[0];
            if (sample.name || sample.company_name || sample.title || sample.website) {
                for (const item of obj) {
                    const name = item.name || item.company_name || item.title || '';
                    if (name.length > 1) {
                        results.push({
                            name,
                            website: item.website || item.url || '',
                            description: item.description || item.tagline || '',
                            city: item.city || (item.location && item.location.city) || 'Amman',
                            services: Array.isArray(item.services)
                                ? item.services.map(s => s.name || s).join(', ')
                                : (item.services || ''),
                            rating: String(item.rating || item.score || ''),
                            reviewCount: String(item.reviews_count || item.review_count || ''),
                            teamSize: String(item.team_size || item.employees || ''),
                            foundedYear: String(item.founded_year || item.founded || ''),
                            sourceUrl: request.url,
                        });
                    }
                }
                return;
            }
        }
        if (typeof obj === 'object' && !Array.isArray(obj)) {
            for (const v of Object.values(obj)) walk(v, depth + 1);
        } else if (Array.isArray(obj)) {
            for (const v of obj) walk(v, depth + 1);
        }
    }

    if (nextData) walk(nextData, 0);

    // DOM fallback
    if (results.length === 0) {
        await page.waitForSelector('h2, h3, div[class*="company"]', { timeout: 10000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 2000));
        for (let y = 300; y <= 2000; y += 300) {
            await page.evaluate(ys => window.scrollTo(0, ys), y);
            await new Promise(r => setTimeout(r, 300));
        }

        const cards = await page.evaluate(() => {
            const selectors = [
                '[class*="company-card"]', '[class*="CompanyCard"]',
                '[class*="listing-item"]', '[class*="company-item"]',
                'li[class*="company"]', 'li[class*="provider"]',
                'article[class*="company"]',
            ];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length >= 2) {
                    return Array.from(els).map(el => {
                        const nameEl = el.querySelector('h2,h3,h4,[class*="name"],[class*="title"]');
                        const linkEl = el.querySelector('a[href]');
                        const descEl = el.querySelector('[class*="desc"],[class*="bio"],p');
                        const locEl = el.querySelector('[class*="location"],[class*="city"]');
                        const ratingEl = el.querySelector('[class*="rating"],[class*="score"]');
                        return {
                            name: (nameEl && nameEl.innerText.trim()) || '',
                            profileUrl: (linkEl && linkEl.href) || '',
                            description: (descEl && descEl.innerText.trim().slice(0, 300)) || '',
                            city: (locEl && locEl.innerText.trim()) || 'Amman',
                            rating: (ratingEl && ratingEl.innerText.trim()) || '',
                        };
                    }).filter(x => x.name.length > 1);
                }
            }
            return [];
        });

        for (const c of cards) {
            results.push({ ...c, sourceUrl: request.url });
        }
    }

    log.info(`Extracted ${results.length} from ${request.url}`);
    return results;
}
"""


# ─── Per-source scraper functions ─────────────────────────────────────────────

def _playwright_scrape(label: str, source_name: str, urls: list,
                       page_function: str, timeout_secs: int = 300) -> List[Company]:
    """Run Apify's playwright-scraper actor and convert results to Company objects."""
    client = _get_client()

    run_input = {
        "startUrls": [{"url": u} for u in urls],
        "pageFunction": page_function,
        "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
        "launchPuppeteerOptions": {"stealth": True},
        "maxConcurrency": 2,
        "maxRequestRetries": 2,
        "navigationTimeoutSecs": 45,
        "pageFunctionTimeoutSecs": 90,
        "ignoreSslErrors": True,
        "useChrome": True,
    }

    items = _run_actor(client, "apify/playwright-scraper", run_input, label, timeout_secs)

    companies = []
    for item in items:
        # Actor returns one item per URL, each with array of results
        records = item if isinstance(item, list) else [item]
        for record in records:
            company = _dict_to_company(record, source_name, record.get("sourceUrl", ""))
            if company and company.has_minimal_data():
                companies.append(company)

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.domain_normalized or c.name_normalized or c.company_name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    logger.info(f"[Apify/{label}] Final unique companies: {len(unique)}")
    return unique


def scrape_techbehemoths_apify() -> List[Company]:
    logger.warning("[Apify/TechBehemoths] Skipping live scrape. Apify residential IPs are actively blocked by Cloudflare Enterprise on this site.")
    return []


def scrape_clutch_apify() -> List[Company]:
    logger.warning("[Apify/Clutch] Skipping live scrape. Dedicated Apify actor is paid, and free playwright actor is blocked by Cloudflare.")
    return []


def scrape_manifest_apify() -> List[Company]:
    urls = [
        "https://themanifest.com/jo/digital-marketing/agencies",
        "https://themanifest.com/jo/web-development/agencies",
        "https://themanifest.com/jo/software-development",
        "https://themanifest.com/jo/mobile-app-development",
        "https://themanifest.com/jo/seo",
        "https://themanifest.com/jo/branding",
    ]
    return _playwright_scrape("Manifest", "The Manifest", urls, _GENERIC_PAGE_FUNCTION, timeout_secs=300)


def scrape_goodfirms_apify() -> List[Company]:
    urls = [
        "https://www.goodfirms.co/directory/country/top-software-development-companies/jordan",
        "https://www.goodfirms.co/directory/country/top-web-development-companies/jordan",
        "https://www.goodfirms.co/directory/country/top-digital-marketing-companies/jordan",
        "https://www.goodfirms.co/directory/country/top-mobile-app-development-companies/jordan",
    ]
    return _playwright_scrape("GoodFirms", "GoodFirms", urls, _GENERIC_PAGE_FUNCTION, timeout_secs=300)


def scrape_perfectfirms_apify() -> List[Company]:
    urls = [
        "https://www.perfectfirms.com/tech/company/jordan",
        "https://www.perfectfirms.com/tech/software-development/jordan",
        "https://www.perfectfirms.com/tech/web-development/jordan",
    ]
    return _playwright_scrape("PerfectFirms", "PerfectFirms", urls, _GENERIC_PAGE_FUNCTION, timeout_secs=240)


def scrape_entasher_apify() -> List[Company]:
    urls = [
        "https://www.entasher.com/jo/s/digital-marketing-agencies",
        "https://www.entasher.com/jo/s/best-marketing-companies",
        "https://www.entasher.com/jo/s/software-development-companies",
        "https://www.entasher.com/jo/s/web-design-companies",
    ]
    return _playwright_scrape("Entasher", "Entasher", urls, _GENERIC_PAGE_FUNCTION, timeout_secs=240)
