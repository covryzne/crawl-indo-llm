# pipelines/government_pipeline.py

import asyncio
import hashlib
import logging
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

WIB = timezone(timedelta(hours=7))

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Import config baru kita di sini
from config.browser_config import GLOBAL_HEADLESS, get_browser_config
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
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


async def crawl_links(site_name, headless=None):
    site_config = GOVERNMENT_SITES_CONFIG[site_name]
    pagination_config = site_config["pagination"]
    pagination_type = pagination_config["type"]
    links_config = site_config["links"]

    effective_headless = GLOBAL_HEADLESS if headless is None else headless
    browser_config = get_browser_config(
        site_name=site_name, headless=effective_headless
    )

    extraction_strategy = JsonCssExtractionStrategy(links_config["schema"])

    all_news_items = []
    consecutive_empty_pages = 0
    max_pages = SCRAPER_CONFIG["max_pages"]
    max_empty = SCRAPER_CONFIG["max_consecutive_empty"]

    async with AsyncWebCrawler(config=browser_config) as crawler:
        session_id = f"session_{site_name.lower()}"

        for page_num in range(1, max_pages + 1):
            logger.info("[%s] Crawling page %s", site_name, page_num)

            url = links_config["url"]
            js_code = None
            js_only = False

            if pagination_type == "url":
                url = build_url(links_config["url"], page_num)
            elif pagination_type == "js_click":
                js_config = get_js_click_config(pagination_config, page_num)
                js_code = js_config["js_code"]
                js_only = js_config["js_only"]

            run_config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                cache_mode=CacheMode.BYPASS,
                wait_for=(f"css:{links_config['wait_for']}"),
                session_id=session_id,
                js_code=js_code,
                js_only=js_only,
                wait_for_timeout=SCRAPER_CONFIG["wait_timeout"],
                magic=(True if site_name == "KOMDIGI" else False),
            )

            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                logger.error(
                    "[%s] Failed page %s => %s",
                    site_name,
                    page_num,
                    result.error_message,
                )
                break

            page_data = parse_crawl4ai_json(result.extracted_content)
            page_items = _extract_news_items(page_data)

            if not page_items:
                consecutive_empty_pages += 1
                logger.warning(
                    "[%s] Empty items on page %s (Consecutive: %s)",
                    site_name,
                    page_num,
                    consecutive_empty_pages,
                )
                if consecutive_empty_pages >= max_empty:
                    logger.info("[%s] Stopping due to empty pages", site_name)
                    break
                continue

            consecutive_empty_pages = 0
            processed = _process_items(
                page_items, links_config["url"], site_name, page_num
            )
            all_news_items.extend(processed)

            if pagination_type == "js_click" and is_last_page(
                result.html, pagination_config
            ):
                logger.info("[%s] Last page marker found via JS", site_name)
                break

            # Jeda polite sebelum lanjut narik halaman link (Randomize dikit biar aman)
            delay = SCRAPER_CONFIG["polite_delay"] + random.uniform(0.5, 1.5)
            await asyncio.sleep(delay)

    return all_news_items


async def scrape_article(item, index, total, site_name, errors_list, headless=None):
    url = item.get("link")
    if not url:
        return None

    site_config = GOVERNMENT_SITES_CONFIG[site_name]
    detail_config = site_config.get("detail")

    if not detail_config:
        # Fallback kalau ga ada config detail (inject metadata dasar)
        crawled_at = datetime.now(WIB).isoformat()
        item["document_id"] = (
            f"{site_name.lower()}-doc-{hashlib.md5(url.encode('utf-8')).hexdigest()[:8]}"
        )
        item["content_hash"] = ""
        item["word_count"] = 0
        item["crawled_at"] = crawled_at
        return item

    effective_headless = GLOBAL_HEADLESS if headless is None else headless
    browser_config = get_browser_config(
        site_name=site_name, headless=effective_headless
    )
    extraction_strategy = JsonCssExtractionStrategy(detail_config["schema"])

    run_config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS,
        wait_for=("css:" f"{detail_config['wait_for']}"),
        wait_for_timeout=SCRAPER_CONFIG["wait_timeout"],
        magic=(True if site_name == "KOMDIGI" else False),
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                raise RuntimeError(result.error_message or "Extraction failed")

            detail_data = parse_crawl4ai_json(result.extracted_content)
            if detail_data and isinstance(detail_data, list):
                detail_dict = detail_data[0]
                item.update(detail_dict)

            # ==========================================
            # --- LOGIKA KUSTOM, TABEL & REGEX PDF ---
            # ==========================================
            soup = BeautifulSoup(result.html, "html.parser")

            # 1. KHUSUS BRIN JDIH: Bedah tabel manual buat nyari Tanggal & Judul
            if site_name == "BRIN_JDIH":
                tds = soup.find_all("td")
                for i, td in enumerate(tds):
                    label = td.get_text(strip=True).lower()
                    if label == "tanggal penetapan" and i + 1 < len(tds):
                        item["date"] = tds[i + 1].get_text(strip=True)
                    elif label == "judul" and i + 1 < len(tds):
                        item["text"] = tds[i + 1].get_text(strip=True)

            # --- JURUS PAMUNGKAS NANGKEP PDF (ANTI ACCESS-DENIED) ---
            bs4_pdfs = []
            doc_id = url.split("/")[-1] if "/" in url else ""

            # Cari SEMUA tag <a> di halaman
            for a in soup.find_all("a", href=True):
                href = a["href"]
                href_lower = href.lower()
                text_lower = a.get_text(strip=True).lower()

                # JANGAN nangkep miniox karena itu private S3 bucket!
                if "miniox.brin.go.id" in href_lower:
                    continue

                # Nangkep URL Proxy/Download resmi JDIH
                if any(
                    kw in href_lower for kw in [".pdf", "/download", "/unduh", "api/"]
                ):
                    bs4_pdfs.append(href)
                # Nangkep dari teks tombolnya
                elif any(
                    kw in text_lower
                    for kw in ["salinan", "lampiran", "unduh", "download"]
                ):
                    bs4_pdfs.append(href)
                # Nangkep URL yang bawa ID dokumen, tapi bukan halaman 'view' saat ini
                elif doc_id and doc_id in href_lower and "view" not in href_lower:
                    bs4_pdfs.append(href)

            # Cari dari iframe / embed (Biasanya tab "Preview Dokumen" naruh PDF di sini)
            for iframe in soup.find_all(["iframe", "embed", "object"]):
                src = iframe.get("src") or iframe.get("data") or ""
                if src and "miniox" not in src.lower() and len(src) > 5:
                    bs4_pdfs.append(src)

            # Cari via Regex (Filter ketat, skip miniox)
            all_hrefs = re.findall(r'href="([^"]+)"', result.html, re.IGNORECASE)
            valid_regex_pdfs = []
            for h in all_hrefs:
                hl = h.lower()
                if "miniox.brin.go.id" in hl:
                    continue
                if any(kw in hl for kw in [".pdf", "download", "unduh"]) or (
                    doc_id and doc_id in hl and "view" not in hl
                ):
                    valid_regex_pdfs.append(h)

            # Tangkapan dari Schema Config
            schema_pdfs = item.get("source_pdf", [])
            if isinstance(schema_pdfs, str):
                schema_pdfs = [schema_pdfs]
            elif isinstance(schema_pdfs, list):
                schema_pdfs = [
                    p.get("url", "") if isinstance(p, dict) else str(p)
                    for p in schema_pdfs
                ]
            else:
                schema_pdfs = []

            # Gabungin semua hasil tangkapan, hapus duplikat (GUA UDAH BUANG miniox_urls DARI SINI BIAR GA ERROR)
            raw_pdfs = list(set(bs4_pdfs + valid_regex_pdfs + schema_pdfs))

            final_pdfs = []
            for p_url in raw_pdfs:
                p_url = p_url.strip()
                if (
                    not p_url
                    or p_url == "None"
                    or len(p_url) < 5
                    or p_url.startswith("#")
                    or "miniox.brin.go.id" in p_url.lower()
                ):
                    continue
                if "{" in p_url or "<" in p_url or ">" in p_url or " " in p_url:
                    continue

                full_pdf_url = (
                    p_url if p_url.startswith("http") else urljoin(url, p_url)
                )

                if full_pdf_url not in final_pdfs:
                    final_pdfs.append(full_pdf_url)

            # ============================================================
            # 🔥 INJEKSI PAKSA API DOWNLOAD BRIN JDIH (SALINAN & LAMPIRAN)
            # ============================================================
            if site_name == "BRIN_JDIH":
                # Cari SEMUA wujud UUID di seluruh kode HTML tanpa ampun!
                all_uuids = re.findall(
                    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                    result.html,
                )

                for file_uuid in set(all_uuids):
                    api_link = f"https://e-regulasi.brin.go.id/api/v1/file/download/{file_uuid}"
                    if api_link not in final_pdfs:
                        final_pdfs.append(api_link)
            # ============================================================

            item["source_pdf"] = final_pdfs if final_pdfs else []
            item["date"] = str(item.get("date", "")).strip()

            # BUANG TABLE DATA BIAR JSON RAPI
            item.pop("table_data", None)
            # ==========================================

            # -- INJEKSI METADATA ENTERPRISE --
            text = item.get("text", "")
            # ============================================================

            item["source_pdf"] = final_pdfs if final_pdfs else []
            item["date"] = str(item.get("date", "")).strip()
            # ==========================================

            # -- INJEKSI METADATA ENTERPRISE --
            text = item.get("text", "")
            crawled_at = datetime.now(WIB).isoformat()
            word_count = len(text.split()) if text else 0
            content_hash = (
                hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
            )
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]

            item["document_id"] = f"{site_name.lower()}-doc-{url_hash}"
            item["content_hash"] = content_hash
            item["word_count"] = word_count
            item["source"] = site_name
            item["crawled_at"] = crawled_at

            logger.info(
                "[%s] [%s/%s] Success => %s (Words: %s)",
                site_name,
                index + 1,
                total,
                url,
                word_count,
            )
            return item

    except Exception as exc:
        logger.warning(
            "[%s] [%s/%s] Failed => %s: %s", site_name, index + 1, total, url, exc
        )
        errors_list.append(
            {"url": url, "error_type": type(exc).__name__, "message": str(exc)}
        )
        return None


async def run(site_name, headless=None):
    start_time_dt = datetime.now(WIB)
    logger.info("=== START LINK CRAWL [%s] ===", site_name)

    news_items = await crawl_links(site_name, headless=headless)
    logger.info("[%s] Found %s total link items", site_name, len(news_items))

    valid_results = []
    errors = []

    if news_items:
        limit = SCRAPER_CONFIG["concurrency_limit"]
        semaphore = asyncio.Semaphore(limit)

        async def bounded_scrape(item, index, total):
            async with semaphore:
                # Tambahin Random Jitter Biar Bot Kelihatan Natural pas narik Detail
                delay = SCRAPER_CONFIG["polite_delay"] + random.uniform(0.5, 2.0)
                await asyncio.sleep(delay)
                return await scrape_article(
                    item,
                    index,
                    total,
                    site_name,
                    errors,
                    headless=headless,
                )

        tasks = [
            bounded_scrape(item, index, len(news_items))
            for index, item in enumerate(news_items)
        ]

        results = await asyncio.gather(*tasks)
        valid_results = [item for item in results if item is not None]

    # -- BUNGKUS PAYLOAD AKHIR ENTERPRISE --
    end_time_dt = datetime.now(WIB)
    duration_seconds = (end_time_dt - start_time_dt).total_seconds()
    total_seeds = len(news_items)
    success_rate = (
        f"{(len(valid_results) / total_seeds * 100):.1f}%" if total_seeds else "0.0%"
    )

    final_payload = {
        "metadata": {
            "schema_version": "1.0.0",
            "job_context": {
                "job_id": f"crawl-{site_name.lower()}-{start_time_dt.strftime('%Y%m%d-%H%M')}",
                "crawler_name": "indo-llm-engine",
                "crawler_version": "v1.0.0",
                "run_mode": "GOVERNMENT_WEBSITE",
                "target_source": site_name,
            },
            "execution_metrics": {
                "started_at": start_time_dt.isoformat(),
                "completed_at": end_time_dt.isoformat(),
                "duration_seconds": round(duration_seconds, 2),
                "total_seed_urls": total_seeds,
                "total_extracted": len(valid_results),
                "total_failed": len(errors),
                "success_rate": success_rate,
            },
            "errors": errors,
        },
        "data": valid_results,
    }

    output_file = BASE_DIR / OUTPUT_DIR / f"siaran_pers_{site_name.lower()}.json"

    # Save dengan format wrapper baru
    save_json(output_file, final_payload)

    logger.info(
        "[%s] Content saved successfully => %s",
        site_name,
        output_file,
    )
    logger.info("=== FINISHED [%s] ===", site_name)

    return final_payload


def _extract_news_items(data):
    if isinstance(data, list):
        if data and "title" in data[0]:
            return data
        if data and "news_items" in data[0]:
            return data[0].get("news_items", [])

    if isinstance(data, dict):
        return data.get("news_items", [])

    return []


def _process_items(items, base_url, source_name, page_num):
    for item in items:
        link = item.get("link", "")
        if link and not link.startswith("http"):
            item["link"] = urljoin(base_url, link)
        item["source"] = source_name
        item["page"] = page_num
    return items
