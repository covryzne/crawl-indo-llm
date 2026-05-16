import json
import logging
import random
import urllib.request
from pathlib import Path

from crawl4ai import BrowserConfig

from config.browser_config import REALISTIC_HEADERS, SEARCH_USER_AGENT

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_BASE = "https://www.google.com/search"
SEARCH_PAGE_SIZE = 10
SEARCH_MAX_PAGES = 3
SEARCH_PRE_REQUEST_DELAY_MIN = 10.0
SEARCH_PRE_REQUEST_DELAY_MAX = 25.0
SEARCH_RETRY_BASE_DELAY = 30.0
SEARCH_MAX_RETRIES = 3

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


def get_keyword_browser_config():
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
        headless=False,
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
