# pipelines/sitemap_pipeline.py

import asyncio
import gzip
import hashlib
import io
import logging
import random
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup

WIB = timezone(timedelta(hours=7))

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

from config.browser_config import GLOBAL_HEADLESS, get_browser_config
from config.government_config import OUTPUT_DIR, SCRAPER_CONFIG
from storage.json_storage import save_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def get_urls_from_sitemap(sitemap_url):
    # 1. AUTO-FIX MISSING HTTPS (Biar requests gak crash)
    if not sitemap_url.startswith("http://") and not sitemap_url.startswith("https://"):
        sitemap_url = "https://" + sitemap_url

    logger.info(f"Mencoba narik sitemap dari: {sitemap_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Connection": "keep-alive",
    }

    # 2. AUTO-ROOT DOMAIN EXTRACTOR (Buang sub-folder kayak /nasional, /berita, dll)
    parsed_url = urllib.parse.urlparse(sitemap_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    sitemap_targets = []

    # 3. AUTO-DISCOVERY
    if not sitemap_url.lower().endswith(".xml") and not sitemap_url.lower().endswith(
        ".xml.gz"
    ):
        logger.info(f"Mencari lokasi sitemap via robots.txt di {base_url}...")
        try:
            r_robots = requests.get(
                f"{base_url}/robots.txt", headers=headers, timeout=10
            )
            if r_robots.status_code == 200:
                for line in r_robots.text.split("\n"):
                    if line.lower().startswith("sitemap:"):
                        found_sitemap = line.split(":", 1)[1].strip()
                        sitemap_targets.append(found_sitemap)
                        logger.info(f"Ketemu sitemap di robots.txt: {found_sitemap}")
        except Exception:
            pass

        if not sitemap_targets:
            sitemap_targets = [
                f"{base_url}/sitemap.xml",
                f"{base_url}/sitemap_index.xml",
                f"{base_url}/sitemap.xml.gz",
                f"{base_url}/sitemap/sitemap.xml",
                f"{base_url}/sitemap/sitemap_index.xml",
                f"{base_url}/sitemap-news.xml",
                f"{base_url}/wp-sitemap.xml",
                f"{base_url}/post-sitemap.xml",
                f"{base_url}/sitemap.php",
            ]
    else:
        sitemap_targets.append(sitemap_url)

    # 4. LOOPING TEBAKAN
    for target_url in sitemap_targets:
        logger.info(f"Mencoba jalur sitemap: {target_url}")
        try:
            response = requests.get(target_url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.content

                if target_url.endswith(".gz"):
                    try:
                        content = gzip.GzipFile(fileobj=io.BytesIO(content)).read()
                    except Exception as e:
                        logger.debug(f"Gagal ekstrak gzip: {e}")

                text_content = content.decode("utf-8", errors="ignore")

                if (
                    "xml" in text_content[:150].lower()
                    or "<urlset" in text_content[:150].lower()
                    or "<sitemapindex" in text_content[:150].lower()
                ):
                    soup = BeautifulSoup(content, "xml")
                    urls = [
                        loc.text.strip()
                        for loc in soup.find_all("loc")
                        if loc.text.strip()
                    ]

                    xml_urls = [
                        u
                        for u in urls
                        if u.lower().endswith(".xml") or u.lower().endswith(".xml.gz")
                    ]
                    if xml_urls:
                        logger.info(
                            f"Ini Sitemap Index! Nyelam ke sub-sitemap: {xml_urls[0]}"
                        )
                        return get_urls_from_sitemap(xml_urls[0])

                    valid_urls = [
                        u
                        for u in urls
                        if not u.lower().endswith((".jpg", ".png", ".pdf", ".mp4"))
                    ]
                    if valid_urls:
                        logger.info(
                            f"Berhasil menemukan {len(valid_urls)} link valid dari {target_url}!"
                        )
                        return valid_urls
                else:
                    logger.debug(
                        f"Jalur {target_url} merespons 200 tapi isinya bukan XML/Sitemap."
                    )
            else:
                logger.debug(
                    f"Jalur {target_url} merespons error {response.status_code}"
                )

        except Exception as e:
            logger.debug(f"Gagal di {target_url}: {e}")
            continue

    logger.error(
        "Semua tebakan sitemap gagal. Web ini menyembunyikan sitemap-nya atau memblokir bot."
    )
    return []


async def scrape_sitemap_article(
    url, index, total, source_name, crawler, run_config, errors_list
):
    try:
        result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            raise RuntimeError(result.error_message or "Gagal load halaman")

        # PAKE TRAFILATURA (bare_extraction buat narik Teks, Judul, Tanggal sekaligus)
        extracted = trafilatura.bare_extraction(result.html, include_comments=False)

        if not extracted:
            raise ValueError("Trafilatura gagal menemukan teks utama di halaman ini")

        # FIX: Kompatibilitas Trafilatura Versi Lama (Dict) vs Versi Baru (Object)
        if isinstance(extracted, dict):
            text = extracted.get("text", "")
            title = extracted.get("title", "Tanpa Judul")
            date = extracted.get("date", "")
        else:
            text = getattr(extracted, "text", "")
            title = getattr(extracted, "title", "Tanpa Judul")
            date = getattr(extracted, "date", "")

        if not text:
            raise ValueError("Teks artikel kosong atau tidak terdeteksi")

        # -- INJEKSI METADATA ENTERPRISE --
        crawled_at = datetime.now(WIB).isoformat()
        word_count = len(text.split())
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]

        item = {
            "title": title,
            "link": url,
            "date": date,
            "source": source_name,
            "text": text,
            "source_pdf": [],  # Kosongin aja karena ini fokus ke teks artikel
            "document_id": f"{source_name.lower()}-doc-{url_hash}",
            "content_hash": content_hash,
            "word_count": word_count,
            "crawled_at": crawled_at,
        }

        logger.info(
            f"[{source_name}] [{index+1}/{total}] Sukses => {url} (Words: {word_count})"
        )
        return item

    except Exception as exc:
        logger.warning(f"[{source_name}] [{index+1}/{total}] Gagal => {url} : {exc}")
        errors_list.append(
            {"url": url, "error_type": type(exc).__name__, "message": str(exc)}
        )
        return None


async def run_sitemap_pipeline(sitemap_url, source_name, limit_urls=None):
    start_time_dt = datetime.now(WIB)
    logger.info(f"=== START SITEMAP CRAWL [{source_name}] ===")

    all_urls = get_urls_from_sitemap(sitemap_url)
    if not all_urls:
        logger.error("Tidak ada URL yang bisa dicrawl. Aborting.")
        return None

    # Batasi URL kalau user minta
    if limit_urls and limit_urls > 0:
        target_urls = all_urls[:limit_urls]
        logger.info(f"Membatasi crawl hanya untuk {limit_urls} URL pertama.")
    else:
        target_urls = all_urls

    total_seeds = len(target_urls)
    valid_results = []
    errors = []

    browser_config = get_browser_config(site_name="DEFAULT", headless=GLOBAL_HEADLESS)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    concurrency_limit = SCRAPER_CONFIG.get("concurrency_limit", 5)
    semaphore = asyncio.Semaphore(concurrency_limit)

    async with AsyncWebCrawler(config=browser_config) as crawler:

        async def bounded_scrape(url, index):
            async with semaphore:
                delay = SCRAPER_CONFIG.get("polite_delay", 2) + random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
                return await scrape_sitemap_article(
                    url, index, total_seeds, source_name, crawler, run_config, errors
                )

        tasks = [bounded_scrape(url, index) for index, url in enumerate(target_urls)]
        results = await asyncio.gather(*tasks)

        valid_results = [res for res in results if res is not None]

    # -- BUNGKUS PAYLOAD AKHIR ENTERPRISE --
    end_time_dt = datetime.now(WIB)
    duration_seconds = (end_time_dt - start_time_dt).total_seconds()
    success_rate = (
        f"{(len(valid_results) / total_seeds * 100):.1f}%" if total_seeds else "0.0%"
    )

    final_payload = {
        "metadata": {
            "schema_version": "1.0.0",
            "job_context": {
                "job_id": f"sitemap-{source_name.lower()}-{start_time_dt.strftime('%Y%m%d-%H%M')}",
                "crawler_name": "indo-llm-engine",
                "crawler_version": "v1.0.0",
                "run_mode": "SITEMAP_CRAWL",
                "target_source": source_name,
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

    output_file = BASE_DIR / OUTPUT_DIR / f"sitemap_{source_name.lower()}.json"
    save_json(output_file, final_payload)

    logger.info(f"[{source_name}] Content saved successfully => {output_file}")
    logger.info(f"=== FINISHED SITEMAP CRAWL [{source_name}] ===")

    return final_payload
