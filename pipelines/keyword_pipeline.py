# pipelines/keyword_pipeline.py

import asyncio
import hashlib
import logging
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

from config.browser_config import REALISTIC_HEADERS
from config.government_config import OUTPUT_DIR
from config.keyword_config import (
    GOOGLE_SEARCH_BASE,
    SEARCH_MAX_PAGES,
    SEARCH_MAX_RETRIES,
    SEARCH_PAGE_SIZE,
    SEARCH_PRE_REQUEST_DELAY_MAX,
    SEARCH_PRE_REQUEST_DELAY_MIN,
    SEARCH_RETRY_BASE_DELAY,
    get_keyword_browser_config,
)
from extractor.page_router import classify_page_type  # <--- IMPORT BARU
from extractor.pdf_discovery import extract_pdf_urls_from_html
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

# Set zona waktu ke WIB (GMT+7)
WIB = timezone(timedelta(hours=7))


class _GoogleLinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._current_href = None
        self._current_text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        attributes = dict(attrs)
        href = attributes.get("href")
        if not href:
            return

        self._current_href = href
        self._current_text_parts = []

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self._current_href is None:
            return

        text = " ".join(
            part.strip() for part in self._current_text_parts if part.strip()
        )
        self.links.append({"href": self._current_href, "text": text})
        self._current_href = None
        self._current_text_parts = []


class _PageTextCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = " ".join(str(data).split())
            if text:
                self.parts.append(text)


def _normalize_whitespace(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def _slugify(value):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    slug = slug.strip("_")
    return slug or "keyword"


def _source_from_url(url):
    host = urlparse(url).netloc.lower().replace("www.", "")
    if not host:
        return "KEYWORD"

    parts = host.split(".")
    if len(parts) >= 3 and parts[-2:] == ["go", "id"]:
        return parts[0].upper()

    return parts[0].upper()


def _is_go_id_url(url):
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host.endswith(".go.id") or host == "go.id"


def _is_google_domain(url):
    host = urlparse(url).netloc.lower()
    return (
        "google." in host
        or host.endswith("google.com")
        or host.endswith("google.co.id")
    )


def _extract_target_url(href):
    if not href:
        return None

    cleaned = str(href).strip()
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None

    parsed = urlparse(cleaned)
    if parsed.netloc and _is_google_domain(cleaned) and parsed.path.startswith("/url"):
        query = parse_qs(parsed.query)
        for key in ("q", "url", "u"):
            if query.get(key):
                target = unquote(query[key][0]).strip()
                if target.startswith("http"):
                    return target
        return None

    if cleaned.startswith("/url?"):
        query = parse_qs(urlparse(cleaned).query)
        for key in ("q", "url", "u"):
            if query.get(key):
                target = unquote(query[key][0]).strip()
                if target.startswith("http"):
                    return target
        return None

    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned

    return None


def _dedupe_urls(urls):
    seen = set()
    unique = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return unique


def _build_search_url(keyword, start=0, require_go_id=False):
    query = keyword.strip()
    if require_go_id:
        query = f"{query} site:go.id"

    return (
        f"{GOOGLE_SEARCH_BASE}?q={quote_plus(query)}"
        f"&num={SEARCH_PAGE_SIZE}&hl=id&gl=id&start={start}"
    )


def _build_browser_config():
    return get_keyword_browser_config()


def _fetch_google_html(search_url):
    request = Request(search_url, headers=REALISTIC_HEADERS)
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


async def _fetch_google_html_with_browser(search_url):
    browser_config = _build_browser_config()

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        simulate_user=True,
        magic=True,
        delay_before_return_html=random.uniform(5, 12),
        page_timeout=90000,
        scan_full_page=True,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        sleep_time = random.uniform(10, 25)
        logger.info(
            f"Stealth delay: tidur dulu {sleep_time:.1f} detik sebelum hit Google..."
        )
        await asyncio.sleep(sleep_time)

        result = await crawler.arun(url=search_url, config=run_config)
        if not result.success:
            raise RuntimeError(result.error_message or "Google search fetch failed")
        return result.html or ""


def _looks_blocked(html):
    if not html:
        return True

    lower = html.lower()

    signals = [
        "recaptcha",
        "captcha",
        "not a robot",
        "unusual traffic",
        "automated queries",
        "/sorry/index",
        "g-recaptcha",
        "detected unusual traffic",
    ]

    return any(signal in lower for signal in signals)


async def _get_google_search_html(search_url):
    try:
        html = await _fetch_google_html_with_browser(search_url)
        if html and not _looks_blocked(html):
            return html
        logger.warning("Google browser fetch looks blocked, switching to requests mode")
    except Exception as exc:
        logger.warning(
            "Google browser fetch failed, switching to requests mode: %s", exc
        )

    try:
        html = await asyncio.to_thread(_fetch_google_html, search_url)
        if html and not _looks_blocked(html):
            return html
        logger.warning("Google HTML fetch looks blocked after requests fallback")
    except Exception as exc:
        logger.warning("Google HTML fetch failed after requests fallback: %s", exc)

    return ""


def _extract_google_result_urls(html, require_go_id=False):
    if not html:
        return []

    collector = _GoogleLinkCollector()
    collector.feed(html)

    candidate_urls = []
    for item in collector.links:
        target = _extract_target_url(item.get("href"))
        if not target:
            continue
        if _is_google_domain(target):
            continue
        if require_go_id and not _is_go_id_url(target):
            continue
        candidate_urls.append(target)

    return _dedupe_urls(candidate_urls)


async def discover_seed_urls_by_keyword(
    keyword, max_seed_results=10, require_go_id=False
):
    keyword = _normalize_whitespace(keyword)
    if not keyword:
        return [], {
            "seed_discovery_source": "google",
            "seed_discovery_error": "Keyword cannot be empty.",
        }

    discovered = []
    discovery_error = None

    for page_index in range(SEARCH_MAX_PAGES):
        if len(discovered) >= max_seed_results:
            break

        search_url = _build_search_url(
            keyword,
            start=page_index * SEARCH_PAGE_SIZE,
            require_go_id=require_go_id,
        )

        logger.info("Google search page %s => %s", page_index + 1, search_url)

        page_discovered = False

        for attempt in range(1, SEARCH_MAX_RETRIES + 1):
            try:
                await asyncio.sleep(
                    random.uniform(
                        SEARCH_PRE_REQUEST_DELAY_MIN,
                        SEARCH_PRE_REQUEST_DELAY_MAX,
                    )
                )

                html = await _get_google_search_html(search_url)

                if _looks_blocked(html):
                    discovery_error = "Google returned a blocked or captcha page."
                    logger.warning(discovery_error)

                    if attempt < SEARCH_MAX_RETRIES:
                        wait = SEARCH_RETRY_BASE_DELAY * (
                            2 ** (attempt - 1)
                        ) + random.uniform(15, 40)
                        logger.warning(
                            "Kena CAPTCHA! Exponential retry nunggu %.1fs", wait
                        )
                        await asyncio.sleep(wait)
                        continue

                    break

                urls = _extract_google_result_urls(html, require_go_id=require_go_id)
                for url in urls:
                    if url not in discovered:
                        discovered.append(url)
                    if len(discovered) >= max_seed_results:
                        break

                page_discovered = True
                break

            except Exception as exc:
                discovery_error = str(exc)
                logger.warning("Google discovery error: %s", exc)

                if attempt < SEARCH_MAX_RETRIES:
                    wait = SEARCH_RETRY_BASE_DELAY * attempt + random.uniform(10, 25)
                    logger.warning("Retrying Google search in %.1fs", wait)
                    await asyncio.sleep(wait)

        if page_discovered:
            await asyncio.sleep(random.uniform(1.5, 3.5))

    return discovered[:max_seed_results], {
        "seed_discovery_source": "google",
        "seed_discovery_error": discovery_error,
    }


def _extract_meta_content(html, meta_names):
    if not html:
        return ""

    for meta_name in meta_names:
        pattern = re.compile(
            r'<meta[^>]+(?:name|property)=["\']%s["\'][^>]+content=["\']([^"\']+)["\']'
            % re.escape(meta_name),
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return _normalize_whitespace(match.group(1))

    return ""


def _extract_tag_content(html, tag_name):
    if not html:
        return ""

    pattern = re.compile(
        rf"<{tag_name}\b[^>]*>(.*?)</{tag_name}>", re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(html)
    if not match:
        return ""

    content = re.sub(r"<[^>]+>", " ", match.group(1))
    return _normalize_whitespace(content)


def _extract_text_from_html(html):
    if not html:
        return ""

    container_patterns = [
        r"<article\b[^>]*>(.*?)</article>",
        r"<main\b[^>]*>(.*?)</main>",
        r"<body\b[^>]*>(.*?)</body>",
    ]

    source_html = html
    for pattern in container_patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            source_html = match.group(1)
            break

    extractor = _PageTextCollector()
    extractor.feed(source_html)
    return _normalize_whitespace(" ".join(extractor.parts))


def _extract_page_record(url, html):
    title = _normalize_whitespace(
        _extract_meta_content(html, ["og:title", "twitter:title"])
        or _extract_tag_content(html, "title")
    )

    if not title:
        h1_match = re.search(
            r"<h1\b[^>]*>(.*?)</h1>", html or "", re.IGNORECASE | re.DOTALL
        )
        if h1_match:
            title = _normalize_whitespace(re.sub(r"<[^>]+>", " ", h1_match.group(1)))

    date = _normalize_whitespace(
        _extract_meta_content(
            html,
            [
                "article:published_time",
                "datePublished",
                "pubdate",
                "publishdate",
                "DC.date.issued",
                "date",
            ],
        )
    )

    if not date:
        time_match = re.search(
            r"<time\b[^>]*(?:datetime=[\"']([^\"']+)[\"'])?[^>]*>(.*?)</time>",
            html or "",
            re.IGNORECASE | re.DOTALL,
        )
        if time_match:
            date = _normalize_whitespace(time_match.group(1) or time_match.group(2))

    text = _extract_text_from_html(html)
    pdfs = extract_pdf_urls_from_html(html, base_url=url)

    # -- METADATA ENTERPRISE & SCORING INJECTION --
    crawled_at = datetime.now(WIB).isoformat()
    word_count = len(text.split()) if text else 0

    # Menentukan klasifikasi tipe halaman pakai router pintar yang baru
    page_type = classify_page_type(url, title=title, text=text, attachments=pdfs)

    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    source_name = _source_from_url(url)
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    document_id = f"{source_name.lower()}-doc-{url_hash}"

    return {
        "document_id": document_id,
        "content_hash": content_hash,
        "page_type": page_type,  # <-- Posisi page_type
        "title": title,
        "link": url,
        "source": source_name,
        "published_date": date,
        "text": text,
        "word_count": word_count,
        "source_pdf": pdfs if pdfs else None,
        "crawled_at": crawled_at,
    }


async def crawl_url(url):
    browser_config = _build_browser_config()
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        simulate_user=True,
        magic=True,
        delay_before_return_html=random.uniform(3, 6),
        page_timeout=90000,
        scan_full_page=True,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        await asyncio.sleep(random.uniform(1.0, 2.5))
        result = await crawler.arun(url=url, config=run_config)
        if not result.success:
            raise RuntimeError(result.error_message or f"Failed to crawl {url}")
        return result.html or ""


async def run_by_keyword_async(
    keyword,
    max_seed_results=10,
    max_links=20,
    output_prefix="dynamic_keyword",
    require_go_id=False,
):
    keyword = _normalize_whitespace(keyword)
    start_time_dt = datetime.now(WIB)

    if not keyword:
        return {
            "keyword": keyword,
            "seed_discovery_source": "google",
            "seed_discovery_error": "Keyword cannot be empty.",
            "seed_urls": [],
            "combined_output_path": None,
            "results": [],
            "stats": {"pages_crawled": 0, "documents_found": 0, "attachments_found": 0},
        }

    seed_urls, discovery_info = await discover_seed_urls_by_keyword(
        keyword,
        max_seed_results=max_seed_results,
        require_go_id=require_go_id,
    )

    if max_links is not None:
        seed_urls = seed_urls[:max_links]

    logger.info(
        "Keyword [%s] discovered %s seed URL(s)",
        keyword,
        len(seed_urls),
    )

    results = []
    errors = []
    attachments_found = 0
    documents_found = 0

    for index, url in enumerate(seed_urls, start=1):
        logger.info("[%s/%s] Crawling %s", index, len(seed_urls), url)

        try:
            html = await crawl_url(url)
            record = _extract_page_record(url, html)
            results.append(record)

            if record.get("source_pdf"):
                attachments_found += len(record["source_pdf"])
                documents_found += 1

            await asyncio.sleep(random.uniform(1.0, 2.0))

        except Exception as exc:
            logger.warning("Failed to crawl %s: %s", url, exc)
            errors.append(
                {"url": url, "error_type": type(exc).__name__, "message": str(exc)}
            )

    end_time_dt = datetime.now(WIB)
    duration_seconds = (end_time_dt - start_time_dt).total_seconds()
    success_rate = f"{(len(results)/len(seed_urls)*100):.1f}%" if seed_urls else "0.0%"

    # BUNGKUS PAYLOAD AKHIR
    final_payload = {
        "metadata": {
            "schema_version": "1.0.0",
            "job_context": {
                "job_id": f"crawl-{_slugify(keyword)}-{start_time_dt.strftime('%Y%m%d-%H%M')}",
                "crawler_name": "indo-llm-engine",
                "crawler_version": "v1.0.0",
                "run_mode": "KEYWORD_CRAWL",
                "target_keyword": keyword,
            },
            "execution_metrics": {
                "started_at": start_time_dt.isoformat(),
                "completed_at": end_time_dt.isoformat(),
                "duration_seconds": round(duration_seconds, 2),
                "total_seed_urls": len(seed_urls),
                "total_extracted": len(results),
                "total_failed": len(errors),
                "success_rate": success_rate,
            },
            "errors": errors,
        },
        "data": results,
    }

    output_file = BASE_DIR / OUTPUT_DIR / f"{output_prefix}_{_slugify(keyword)}.json"

    # Save the new enterprise metadata format
    save_json(output_file, final_payload)

    logger.info("Keyword crawl saved => %s", output_file)

    # Return kombinasi untuk jaga kompatibilitas sama cli_pipeline.py
    return {
        "keyword": keyword,
        "seed_discovery_source": discovery_info.get("seed_discovery_source", "google"),
        "seed_discovery_error": discovery_info.get("seed_discovery_error"),
        "seed_urls": seed_urls,
        "combined_output_path": str(output_file),
        **final_payload,
    }


def run_by_keyword(
    keyword,
    max_seed_results=10,
    max_links=20,
    output_prefix="dynamic_keyword",
    require_go_id=False,
):
    return asyncio.run(
        run_by_keyword_async(
            keyword,
            max_seed_results=max_seed_results,
            max_links=max_links,
            output_prefix=output_prefix,
            require_go_id=require_go_id,
        )
    )
