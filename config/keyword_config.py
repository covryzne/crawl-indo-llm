import json
import logging
import random
import urllib.request
from pathlib import Path

from crawl4ai import BrowserConfig

from config.browser_config import GLOBAL_HEADLESS, REALISTIC_HEADERS, SEARCH_USER_AGENT
from config.pagination_config import get_keyword_pagination

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_BASE = "https://www.google.com/search"

# load defaults from central pagination config (can pass overrides when needed)
_KP = get_keyword_pagination()
SEARCH_PAGE_SIZE = _KP["search_page_size"]
SEARCH_MAX_PAGES = _KP["search_max_pages"]
SEARCH_PRE_REQUEST_DELAY_MIN = _KP["search_pre_request_delay_min"]
SEARCH_PRE_REQUEST_DELAY_MAX = _KP["search_pre_request_delay_max"]
SEARCH_RETRY_BASE_DELAY = _KP["search_retry_base_delay"]
SEARCH_MAX_RETRIES = _KP["search_max_retries"]

MAX_SEED_RESULTS = _KP["max_seed_results"]
MAX_LINKS_TO_CRAWL = _KP["max_links_to_crawl"]

PROFILE_DIR = Path("./playwright_profile_keyword")
PROFILE_DIR.mkdir(exist_ok=True)


def resolve_google_ipv4():
    doh_endpoints = [
        "https://cloudflare-dns.com/dns-query?name=www.google.com&type=A",
        "https://dns.google/resolve?name=www.google.com&type=A",
        "https://dns.quad9.net:5053/dns-query?name=www.google.com&type=A",
    ]

    for endpoint in doh_endpoints:
        try:
            req = urllib.request.Request(
                endpoint, headers={"accept": "application/dns-json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                dns_data = json.loads(response.read().decode())

            ipv4 = next(
                ans["data"] for ans in dns_data.get("Answer", []) if ans["type"] == 1
            )
            provider = endpoint.split("/")[2]
            logger.info(f"Using DoH provider {provider}: {ipv4}")

            # Format string persis seperti crawler.py lama
            return f"MAP www.google.com {ipv4}, MAP google.com {ipv4}"
        except Exception as e:
            continue

    logger.warning("All DoH providers failed.")
    return ""


def get_keyword_browser_config(headless: bool | None = None):
    effective_headless = GLOBAL_HEADLESS if headless is None else headless
    resolver_rules = resolve_google_ipv4()

    extra_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US,en",
        "--start-maximized",
    ]

    if resolver_rules:
        extra_args.append(f"--host-resolver-rules={resolver_rules}")

    return BrowserConfig(
        headless=effective_headless,
        verbose=False,
        use_persistent_context=True,
        user_data_dir=str(PROFILE_DIR),
        user_agent=SEARCH_USER_AGENT,
        viewport_width=random.choice([1366, 1920]),
        viewport_height=random.choice([768, 1080]),
        headers=REALISTIC_HEADERS,
        ignore_https_errors=True,
        extra_args=extra_args,
    )
