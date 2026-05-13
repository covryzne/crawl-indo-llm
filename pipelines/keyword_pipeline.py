import asyncio
import json
import logging
import os
import random
import socket
import ssl
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from config.government_config import GENERAL_SITES_CONFIG
from extractor.link_discovery import discover_internal_links
from extractor.page_router import classify_page_type, classify_source_domain
from extractor.pdf_discovery import discover_attachment_candidates_from_html
from extractor.structured_extractor import parse_crawl4ai_json
from storage.json_storage import save_json
from storage.output_formatter import (
    build_debug_payload,
    build_final_payload,
    current_utc_timestamp,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)
_DUCKDUCKGO_TEMPLATES = (
    "https://html.duckduckgo.com/html/?q={query}",
    "https://lite.duckduckgo.com/lite/?q={query}",
    "https://duckduckgo.com/html/?q={query}",
)

_GOOGLE_TEMPLATES = (
    "https://www.google.com/search?q={query}",
    "https://www.google.com/search?q={query}+site:go.id",
)

# Default to Google templates; override with USE_GOOGLE_SEARCH=0 to force DuckDuckGo
if os.getenv("USE_GOOGLE_SEARCH", "1") == "1":
    SEARCH_URL_TEMPLATES = _GOOGLE_TEMPLATES
    logger.warning(
        "Defaulting to Google HTML search templates. This may trigger CAPTCHA or blocking."
    )
else:
    SEARCH_URL_TEMPLATES = _DUCKDUCKGO_TEMPLATES

REALISTIC_HEADERS = {
    "User-Agent": SEARCH_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Google Chrome";v="135", "Chromium";v="135", "Not:A-Brand";v="8"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def _is_captcha_page(html: str) -> bool:
    """Detect captcha pages from search results."""
    if not html:
        return False
    lower = html.lower()
    signals = [
        "recaptcha",
        "captcha",
        "not a robot",
        "unusual traffic",
        "automated queries",
        "g-recaptcha",
        "detected unusual traffic",
        "please verify",
    ]
    return any(sig in lower for sig in signals)


def _resolve_doh_ipv4(hostname):
    """Resolve hostname to IPv4 via DoH (DNS over HTTPS) to bypass DNS interception."""
    doh_endpoints = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
        f"https://dns.quad9.net:5053/dns-query?name={hostname}&type=A",
    ]

    for endpoint in doh_endpoints:
        try:
            req = Request(
                endpoint,
                headers={
                    "accept": "application/dns-json",
                    "User-Agent": SEARCH_USER_AGENT,
                },
            )
            with urlopen(req, timeout=8) as response:
                dns_data = json.loads(response.read().decode())
            ipv4 = next(
                ans["data"] for ans in dns_data.get("Answer", []) if ans["type"] == 1
            )
            logger.info("DoH resolved %s to %s via %s", hostname, ipv4, endpoint)
            return ipv4
        except Exception as e:
            logger.debug("DoH failed for %s on %s: %s", hostname, endpoint, e)
    return None


def generate_search_urls(keyword: str):
    encoded = quote_plus(keyword)

    return [
        f"https://www.google.com/search?q={encoded}",
        f"https://www.google.com/search?q={encoded}+site:go.id",
    ]


def extract_google_result_links(html: str):
    soup = BeautifulSoup(html, "html.parser")

    discovered = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Case 1: Google redirect links like /url?q=<target>&...
        if "/url?q=" in href:
            try:
                clean = href.split("/url?q=")[1].split("&")[0]
                clean = unquote(clean)
                parsed = urlparse(clean)
                if parsed.scheme in ("http", "https"):
                    discovered.append(clean)
                    continue
            except Exception:
                pass

        # Case 2: Links that include url= param (older patterns)
        if "url=" in href and ("/url?" in href or "&url=" in href):
            try:
                # split on 'url=' and take first param value
                clean = href.split("url=")[1].split("&")[0]
                clean = unquote(clean)
                parsed = urlparse(clean)
                if parsed.scheme in ("http", "https"):
                    discovered.append(clean)
                    continue
            except Exception:
                pass

        # Case 3: Direct absolute links in href (some SERP renderings)
        if href.startswith("http://") or href.startswith("https://"):
            parsed = urlparse(href)
            # skip internal google links
            if parsed.netloc and "google" in parsed.netloc:
                continue
            discovered.append(href)

    # dedupe while preserving order
    return list(dict.fromkeys(discovered))


def _keyword_tokens(keyword):
    return [token for token in keyword.lower().split() if len(token) >= 3]


def _build_local_seed_catalog():
    catalog = []
    for site_name, site_conf in GENERAL_SITES_CONFIG.items():
        links_conf = site_conf.get("links", {})
        url_template = links_conf.get("url_template")
        if not url_template:
            continue

        base_url = url_template.replace("{page}", "1")
        base_url = base_url.replace("?page=1", "")
        base_url = base_url.replace("&page=1", "")
        catalog.append(
            {
                "name": site_name,
                "url": base_url,
            }
        )

    catalog.extend(
        [
            {"name": "PERATURAN", "url": "https://peraturan.go.id/"},
            {"name": "KOMDIGI", "url": "https://www.komdigi.go.id/"},
            {"name": "INDONESIA", "url": "https://www.indonesia.go.id/"},
        ]
    )

    deduped = []
    seen = set()
    for item in catalog:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


LOCAL_SEED_CATALOG = _build_local_seed_catalog()


def _discover_seed_urls_local(keyword, max_results=10, require_go_id=False):
    tokens = _keyword_tokens(keyword)
    seeds = []
    seen = set()

    for item in LOCAL_SEED_CATALOG:
        url = item["url"]
        name = item["name"].lower()
        haystack = f"{name} {url.lower()}"

        parsed = urlparse(url)
        if require_go_id and "go.id" not in parsed.netloc.lower():
            continue

        if tokens and not any(token in haystack for token in tokens):
            continue

        if url in seen:
            continue

        seen.add(url)
        seeds.append(url)
        if len(seeds) >= max_results:
            break

    if seeds:
        return seeds

    for item in LOCAL_SEED_CATALOG:
        url = item["url"]
        parsed = urlparse(url)
        if require_go_id and "go.id" not in parsed.netloc.lower():
            continue
        if url in seen:
            continue
        seen.add(url)
        seeds.append(url)
        if len(seeds) >= max_results:
            break

    return seeds


class _SearchResultCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_anchor = False
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        attributes = dict(attrs)
        href = attributes.get("href")
        if not href:
            return

        self._in_anchor = True
        self._current_href = href

    def handle_endtag(self, tag):
        if tag.lower() == "a":
            self._in_anchor = False
            self._current_href = None

    def handle_data(self, data):
        if self._in_anchor and self._current_href:
            self.links.append(self._current_href)


def _resolve_search_result_url(raw_url):
    if not raw_url:
        return None

    parsed = urlparse(raw_url)

    if parsed.path.startswith("/l/") and parsed.query:
        query_params = parse_qs(parsed.query)
        uddg = query_params.get("uddg")
        if uddg:
            return unquote(uddg[0])

    if parsed.scheme in {"http", "https"}:
        return raw_url

    return None


async def discover_seed_urls_by_keyword(
    crawler,
    keyword: str,
    only_go_id: bool = False,
):
    logger.info("Keyword discovery: %s", keyword)

    search_urls = generate_search_urls(keyword)

    discovered = []

    for search_url in search_urls:
        logger.info("Searching: %s", search_url)

        try:
            result = await crawler.arun(url=search_url)

            if not result.success:
                logger.warning(
                    "Failed search crawl: %s",
                    result.error_message,
                )
                continue

            html = getattr(result, "html", "") or ""

            links = extract_google_result_links(html)

            logger.info("Discovered %s raw links", len(links))

            for link in links:
                if only_go_id and ".go.id" not in link:
                    continue

                discovered.append(link)

        except Exception as exc:
            logger.error("Keyword discovery error: %s", exc)

    unique = list(dict.fromkeys(discovered))

    logger.info("Final discovered URLs: %s", len(unique))

    return unique


def _slugify(url):
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/").replace("/", "_")
    path = path or "root"
    host = parsed.netloc.replace(":", "_").replace(".", "_")
    return f"{host}__{path}"[:180]


def _build_pdf_queue_items(result):
    queue_items = []
    source_page = result.get("url")
    source_domain = result.get("source_domain")
    page_type = result.get("page_type")

    for attachment in result.get("attachments", []):
        pdf_url = attachment.get("url")
        if not pdf_url:
            continue

        queue_items.append(
            {
                "pdf_url": pdf_url,
                "source_page": source_page,
                "source_domain": source_domain,
                "page_type": page_type,
                "priority": (
                    "high_priority"
                    if attachment.get("kind") == "pdf"
                    else "medium_priority"
                ),
                "link_text": attachment.get("text"),
            }
        )

    return queue_items


async def crawl_url(url, max_links=20):
    """Crawl one URL and emit normalized discovery JSON."""
    browser_config = BrowserConfig(headless=True, verbose=False)

    schema = {
        "name": "Dynamic Page",
        "baseSelector": "body",
        "fields": [
            {"name": "title", "selector": "title", "type": "text"},
            {"name": "text", "selector": "body", "type": "text"},
        ],
    }

    async with AsyncWebCrawler(config=browser_config) as crawler:
        run_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(schema),
            cache_mode=CacheMode.BYPASS,
            wait_for_timeout=30000,
        )

        result = await crawler.arun(url=url, config=run_config)
        if not result.success:
            return {
                "url": url,
                "source_domain": classify_source_domain(url),
                "page_type": "other",
                "attachments": [],
                "candidate_links": [],
                "crawl_metadata": {
                    "status": "error",
                    "error_message": result.error_message,
                },
            }

        parsed = parse_crawl4ai_json(result.extracted_content)
        extracted = parsed[0] if parsed else {}
        html = getattr(result, "html", "") or ""
        candidate_links = discover_internal_links(
            html, base_url=url, current_url=url, max_links=max_links
        )
        attachments = discover_attachment_candidates_from_html(html, base_url=url)
        page_type = classify_page_type(
            url,
            title=extracted.get("title", ""),
            text=extracted.get("text", ""),
            attachments=attachments,
            candidate_links=candidate_links,
        )

        return {
            "title": extracted.get("title", ""),
            "url": url,
            "source_domain": classify_source_domain(url),
            "page_type": page_type,
            "date": extracted.get("date"),
            "text": extracted.get("text", ""),
            "attachments": attachments,
            "candidate_links": candidate_links,
            "crawl_metadata": {
                "status": "ok",
                "attachments_found": len(attachments),
                "candidate_links_found": len(candidate_links),
            },
        }


async def crawl_urls(urls, max_links=20):
    """Crawl multiple seed URLs and emit normalized web + PDF queue data."""
    web_results = []
    pdf_queue = []

    for url in urls:
        result = await crawl_url(url, max_links=max_links)
        web_results.append(result)
        pdf_queue.extend(_build_pdf_queue_items(result))

    return web_results, pdf_queue


async def run_async(
    url,
    output_name=None,
    max_links=20,
    output_prefix=None,
    seed_discovery=None,
    keyword=None,
):
    """Run a dynamic crawl and save normalized web output plus PDF queue."""
    urls = [url] if isinstance(url, str) else list(url)
    web_results, pdf_queue = await crawl_urls(urls, max_links=max_links)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        web_output_path = OUTPUT_DIR / output_name
    else:
        web_output_path = OUTPUT_DIR / f"keyword_web_{_slugify(urls[0])}.json"

    pdf_output_path = OUTPUT_DIR / f"keyword_pdf_queue_{_slugify(urls[0])}.json"

    save_json(web_output_path, web_results if len(web_results) > 1 else web_results[0])
    save_json(pdf_output_path, pdf_queue)

    logger.info("Saved keyword web output to %s", web_output_path)
    logger.info("Saved keyword PDF queue to %s", pdf_output_path)

    # Build combined per-seed grouped output (Option B) for internal use.
    prefix = output_prefix
    if not prefix:
        # derive prefix from output_name if possible
        if output_name and output_name.endswith(".json"):
            prefix = Path(output_name).stem.replace("_web", "")
        else:
            prefix = f"keyword_{_slugify(urls[0])}"

    combined_output_path = OUTPUT_DIR / f"combined_keyword_{prefix}.json"

    seeds = []
    seed_map = {}
    for idx, res in enumerate(web_results, start=1):
        seed_id = f"seed-{idx}"
        seed_obj = {
            "id": seed_id,
            "url": res.get("url"),
            "title": res.get("title"),
            "text": res.get("text"),
            "source_domain": res.get("source_domain"),
            "page_type": res.get("page_type"),
            "attachments": res.get("attachments", []),
            "candidate_links": res.get("candidate_links", []),
            "crawl_metadata": res.get("crawl_metadata", {}),
        }
        seeds.append(seed_obj)
        seed_map[res.get("url")] = seed_id

    pdf_index = []
    for item in pdf_queue:
        pdf_url = item.get("pdf_url")
        source_page = item.get("source_page")
        seed_id = seed_map.get(source_page)
        pdf_index.append(
            {
                "pdf_url": pdf_url,
                "seed_id": seed_id,
                "priority": item.get("priority"),
                "link_text": item.get("link_text"),
            }
        )

    raw_combined = {
        "keyword": None,
        "seed_discovery": seed_discovery or {},
        "generated_at": current_utc_timestamp(),
        "stats": {
            "seeds": len(seeds),
            "web_results": len(web_results),
            "pdf_index_count": len(pdf_index),
        },
        "seeds": seeds,
        "pdf_index": pdf_index,
    }

    final_payload = build_final_payload(
        keyword=keyword,
        generated_at=raw_combined["generated_at"],
        stats={
            "pages_crawled": len(web_results),
            "documents_found": sum(
                1
                for item in web_results
                if item.get("page_type") in {"document", "pdf", "publication"}
                or item.get("attachments")
            ),
            "attachments_found": sum(
                len(item.get("attachments", [])) for item in web_results
            ),
        },
        results=web_results,
    )

    save_json(combined_output_path, final_payload)

    debug_output_path = None
    if os.getenv("SAVE_KEYWORD_DEBUG_OUTPUT", "1") == "1":
        debug_output_path = OUTPUT_DIR / f"debug_keyword_{prefix}.json"
        save_json(debug_output_path, build_debug_payload(raw_combined))
        logger.info("Saved debug keyword output to %s", debug_output_path)

    logger.info("Saved combined keyword output to %s", combined_output_path)

    return {
        "web_output_path": str(web_output_path),
        "pdf_queue_path": str(pdf_output_path),
        "combined_output_path": str(combined_output_path),
        "debug_output_path": str(debug_output_path) if debug_output_path else None,
        "web_results": web_results,
        "pdf_queue": pdf_queue,
        "combined": final_payload,
        "debug_payload": raw_combined,
    }


async def run_keyword_async(
    keyword,
    max_seed_results=10,
    max_links=20,
    output_prefix="keyword",
    require_go_id=False,
):
    """Discover seed URLs by keyword, then run dynamic crawl on discovered seeds."""
    # Use an AsyncWebCrawler instance to perform search-based discovery
    seed_urls = []
    discovery_source = "none"
    discovery_error = None

    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            discovered = await discover_seed_urls_by_keyword(
                crawler, keyword, only_go_id=require_go_id
            )

        if discovered:
            seed_urls = discovered[:max_seed_results]
            discovery_source = "search"
        else:
            discovery_source = "search"
            discovery_error = "search returned no URLs"
    except Exception as exc:
        logger.warning("Search-based keyword discovery failed: %s", exc)
        discovery_error = str(exc)

    # If search returned nothing, fall back to local seed catalog
    if not seed_urls:
        local_fallback = _discover_seed_urls_local(
            keyword, max_results=max_seed_results, require_go_id=require_go_id
        )
        if local_fallback:
            seed_urls = local_fallback
            discovery_source = "local_fallback"
            if discovery_error is None:
                discovery_error = "search returned no URLs"

    if not seed_urls:
        return {
            "keyword": keyword,
            "seed_urls": [],
            "seed_discovery_source": discovery_source,
            "seed_discovery_error": discovery_error,
            "web_output_path": None,
            "pdf_queue_path": None,
            "web_results": [],
            "pdf_queue": [],
        }

    output_name = f"{output_prefix}_web.json"
    result = await run_async(
        seed_urls,
        output_name=output_name,
        max_links=max_links,
        output_prefix=output_prefix,
        seed_discovery={"source": discovery_source, "note": discovery_error},
        keyword=keyword,
    )
    result["seed_urls"] = seed_urls
    result["seed_discovery_source"] = discovery_source
    result["seed_discovery_error"] = discovery_error
    return result


def run(url, output_name=None, max_links=20):
    return asyncio.run(run_async(url, output_name=output_name, max_links=max_links))


def run_keyword(
    keyword,
    max_seed_results=10,
    max_links=20,
    output_prefix="keyword",
    require_go_id=False,
):
    return asyncio.run(
        run_keyword_async(
            keyword,
            max_seed_results=max_seed_results,
            max_links=max_links,
            output_prefix=output_prefix,
            require_go_id=require_go_id,
        )
    )
