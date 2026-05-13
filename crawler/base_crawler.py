from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig


def build_browser_config(headless=True, verbose=False):
    return BrowserConfig(headless=headless, verbose=verbose)


def build_run_config(
    extraction_strategy,
    wait_for=None,
    session_id=None,
    js_code=None,
    js_only=False,
    wait_for_timeout=None,
):
    return CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS,
        wait_for=wait_for,
        session_id=session_id,
        js_code=js_code,
        js_only=js_only,
        wait_for_timeout=wait_for_timeout,
    )
