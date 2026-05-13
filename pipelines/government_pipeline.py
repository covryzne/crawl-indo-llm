# pipelines/government_pipeline.py

import asyncio
import logging
import sys
from pathlib import Path
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from config.government_config import GOVERNMENT_SITES_CONFIG, OUTPUT_DIR, SCRAPER_CONFIG
from crawler.pagination.js_click_pagination import get_js_click_config, is_last_page
from crawler.pagination.url_pagination import build_url
from extractor.structured_extractor import parse_crawl4ai_json
from storage.json_storage import save_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s - " "%(levelname)s - " "%(message)s"),
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

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


async def crawl_links(site_name):
    site_config = GOVERNMENT_SITES_CONFIG[site_name]
    pagination_config = site_config["pagination"]
    pagination_type = pagination_config["type"]
    links_config = site_config["links"]
    base_url = links_config["url"]
    schema = links_config["schema"]

    browser_config = BrowserConfig(
        headless=True,  # Tetep False dulu biar kelihatan kalau udah sukses
        verbose=True,
        headers=REALISTIC_HEADERS,
        ignore_https_errors=True,  # Abaikan error SSL yang sering kejadian di web pemerintah
        extra_args=[
            "--disable-web-security",  # Ini jurus pamungkas buat ngelewatin error CORS
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--ignore-certificate-errors",
        ],
    )

    all_results = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        page_num = 1
        consecutive_empty = 0

        logger.info(
            "=== START LINK CRAWL [%s] ===",
            site_name,
        )

        while page_num <= SCRAPER_CONFIG["max_pages"]:

            if pagination_type == "url":
                url = build_url(
                    base_url,
                    page_num,
                )
            else:
                url = base_url

            logger.info(
                "[%s] Crawling page %s => %s",
                site_name,
                page_num,
                url,
            )

            js_config = {
                "js_code": None,
                "js_only": False,
            }

            if pagination_type == "js_click":
                js_config = get_js_click_config(
                    pagination_config,
                    page_num,
                )

            js_code = js_config["js_code"]
            js_only = js_config["js_only"]

            run_config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(schema),
                cache_mode=(CacheMode.BYPASS),
                wait_for=(f"css:{links_config['wait_for']}"),
                wait_for_timeout=(SCRAPER_CONFIG["wait_timeout"]),
                session_id=(f"{site_name.lower()}_session"),
                js_code=js_code,
                js_only=js_only,
            )

            try:
                result = await crawler.arun(
                    url=url,
                    config=run_config,
                )

                if not result.success:
                    logger.error(
                        ("[%s] Failed " "page %s => %s"),
                        site_name,
                        page_num,
                        result.error_message,
                    )
                    break

                data = parse_crawl4ai_json(result.extracted_content)
                news_items = _extract_news_items(data)

                if not news_items:
                    logger.warning(
                        ("[%s] " "Empty page %s"),
                        site_name,
                        page_num,
                    )

                    consecutive_empty += 1

                    if consecutive_empty >= SCRAPER_CONFIG["max_consecutive_empty"]:
                        break

                else:
                    consecutive_empty = 0

                    processed_items = _process_items(
                        items=news_items,
                        base_url=url,
                        source_name=site_name,
                        page_num=page_num,
                    )

                    all_results.extend(processed_items)

                    logger.info(
                        ("[%s] " "Found %s items"),
                        site_name,
                        len(processed_items),
                    )

                if pagination_type == "js_click" and is_last_page(
                    result.html,
                    pagination_config,
                ):
                    logger.info(
                        ("[%s] " "Last page detected"),
                        site_name,
                    )
                    break

                page_num += 1

                await asyncio.sleep(SCRAPER_CONFIG["polite_delay"])

            except Exception as exc:
                logger.error(
                    ("[%s] Error " "page %s => %s"),
                    site_name,
                    page_num,
                    exc,
                )
                break

    return all_results


async def crawl_content(
    site_name,
    news_items,
):
    logger.info(
        "[%s] Total articles => %s",
        site_name,
        len(news_items),
    )

    site_config = GOVERNMENT_SITES_CONFIG[site_name]
    detail_config = site_config["detail"]

    browser_config = BrowserConfig(
        headless=True,  # Tetep False dulu biar kelihatan kalau udah sukses
        verbose=True,
        headers=REALISTIC_HEADERS,
        ignore_https_errors=True,  # Abaikan error SSL yang sering kejadian di web pemerintah
        extra_args=[
            "--disable-web-security",  # Ini jurus pamungkas buat ngelewatin error CORS
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--ignore-certificate-errors",
        ],
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        semaphore = asyncio.Semaphore(SCRAPER_CONFIG["concurrency_limit"])

        async def scrape_article(
            item,
            index,
            total,
        ):
            async with semaphore:
                url = item["link"]

                logger.info(
                    "[%s] [%s/%s] %s",
                    site_name,
                    index + 1,
                    total,
                    url,
                )

                run_config = CrawlerRunConfig(
                    extraction_strategy=JsonCssExtractionStrategy(
                        detail_config["schema"]
                    ),
                    cache_mode=(CacheMode.BYPASS),
                    wait_for=("css:" f"{detail_config['wait_for']}"),
                    wait_for_timeout=(SCRAPER_CONFIG["wait_timeout"]),
                )

                try:
                    result = await crawler.arun(
                        url=url,
                        config=run_config,
                    )

                    if not result.success:
                        logger.error(
                            ("[%s] " "Failed => %s"),
                            site_name,
                            url,
                        )
                        return None

                    data = parse_crawl4ai_json(result.extracted_content)
                    detail = data[0] if data else {}

                    # ========================================================
                    # LOGIKA BARU PENANGANAN PDF MENGGUNAKAN REGEX (UNIVERSAL)
                    # ========================================================
                    import re

                    # Langsung scan HTML mentah buat nyari semua href berakhiran .pdf (Case Insensitive)
                    # Ini jauh lebih aman dan ga peduli webnya pake slick-carousel atau bukan
                    raw_pdfs = re.findall(
                        r'href="([^"]+\.pdf)"', result.html, re.IGNORECASE
                    )

                    final_pdfs = []
                    for p_url in raw_pdfs:
                        p_url = p_url.strip()
                        if not p_url:
                            continue

                        # Resolve relative URL (/docs/file.pdf) jadi Full URL
                        full_pdf_url = (
                            p_url if p_url.startswith("http") else urljoin(url, p_url)
                        )

                        # Deduplikasi (buang link PDF kembar efek dari elemen yang di-clone)
                        if full_pdf_url not in final_pdfs:
                            final_pdfs.append(full_pdf_url)

                    # Pastikan cuma ada SATU blok return ini di bagian akhir try!
                    return {
                        "title": (item["title"]),
                        "link": (item["link"]),
                        "source": (site_name),
                        "date": (str(detail.get("date", "")).strip()),
                        "text": (" ".join(str(detail.get("text", "")).split())),
                        # Output berupa list ["url1.pdf", "url2.pdf"] atau None jika kosong
                        "source_pdf": final_pdfs if final_pdfs else None,
                    }

                except Exception as exc:
                    logger.error(
                        ("[%s] Error " "=> %s | %s"),
                        site_name,
                        url,
                        exc,
                    )
                    return None

                finally:
                    await asyncio.sleep(SCRAPER_CONFIG["polite_delay"])

        tasks = [
            scrape_article(
                item,
                index,
                len(news_items),
            )
            for index, item in enumerate(news_items)
        ]

        results = await asyncio.gather(*tasks)

    valid_results = [item for item in results if item is not None]

    output_file = BASE_DIR / OUTPUT_DIR / f"siaran_pers_{site_name.lower()}.json"

    save_json(
        output_file,
        valid_results,
    )

    logger.info(
        "[%s] Content saved => %s",
        site_name,
        output_file,
    )


def _extract_news_items(data):
    if isinstance(data, list):
        if data and "title" in data[0]:
            return data
        if data and "news_items" in data[0]:
            return data[0].get("news_items", [])

    if isinstance(data, dict):
        return data.get("news_items", [])

    return []


def _process_items(
    items,
    base_url,
    source_name,
    page_num,
):
    for item in items:
        link = item.get("link", "")
        if link and not link.startswith("http"):
            item["link"] = urljoin(base_url, link)
        item["source"] = source_name
        item["scraped_at_page"] = page_num

    return items


async def run_async(site_name):
    news_items = await crawl_links(site_name)
    await crawl_content(
        site_name=site_name,
        news_items=news_items,
    )


def run(site_name):
    asyncio.run(run_async(site_name))
