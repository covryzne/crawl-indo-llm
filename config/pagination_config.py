"""Central pagination configuration for different pipelines.

Keep pipeline-specific defaults here so teams can change page limits
and related pagination tuning in a single place.
"""

# Keyword pipeline pagination defaults
KEYWORD_PAGINATION = {
    # how many results per Google page (usually 10)
    "search_page_size": 10,
    # how many pages to iterate when performing a keyword search
    "search_max_pages": 3,
    # delay window (seconds) before each search request to appear human-like
    "search_pre_request_delay_min": 10.0,
    "search_pre_request_delay_max": 25.0,
    # retry/backoff defaults for failed search requests
    "search_retry_base_delay": 30.0,
    "search_max_retries": 3,
    # limits for downstream crawling after discovery
    "max_seed_results": 15,
    "max_links_to_crawl": 10,
}


# Government pipeline pagination / scraper tuning defaults
GOVERNMENT_PAGINATION = {
    # maximum pages to follow for site list pages (can be overridden per-site)
    "max_pages": 1,
    # stop after this many consecutive pages that yield no results
    "max_consecutive_empty": 1,
    # concurrency limit for link/detail fetching
    "concurrency_limit": 5,
    # polite delay between requests
    "polite_delay": 0.5,
    # default wait timeout (ms) when waiting for selectors
    "wait_timeout": 30000,
}


def get_keyword_pagination(overrides: dict | None = None) -> dict:
    cfg = KEYWORD_PAGINATION.copy()
    if overrides:
        cfg.update(overrides)
    return cfg


def get_government_pagination(overrides: dict | None = None) -> dict:
    cfg = GOVERNMENT_PAGINATION.copy()
    if overrides:
        cfg.update(overrides)
    return cfg
