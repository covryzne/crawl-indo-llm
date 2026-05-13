"""Lightweight internal link discovery helpers for government/news pages."""

from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse

from extractor.pdf_discovery import normalize_url as _normalize_url

HIGH_PRIORITY_KEYWORDS = (
    "pdf",
    "download",
    "unduh",
    "lampiran",
    "dokumen",
    "publikasi",
    "laporan",
    "media-center",
    "media center",
    "berita",
    "news",
)

MEDIUM_PRIORITY_KEYWORDS = (
    "siaran-pers",
    "siaran pers",
    "berita",
    "news",
    "publikasi",
    "laporan",
    "dokumen",
    "media-center",
    "media center",
)

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "#")


def normalize_url(url, base_url=None):
    """Normalizes and resolves a URL against an optional base URL."""
    return _normalize_url(url, base_url=base_url)


def _normalize_netloc(netloc):
    return netloc.lower().lstrip("www.")


def is_internal_link(url, base_url=None):
    """Returns True when a URL stays within the same website/domain."""
    if not url:
        return False

    normalized = normalize_url(url, base_url=base_url)
    if not normalized:
        return False

    if any(normalized.lower().startswith(prefix) for prefix in SKIP_SCHEMES):
        return False

    if not base_url:
        return True

    base_parsed = urlparse(base_url)
    target_parsed = urlparse(normalized)

    if not base_parsed.netloc or not target_parsed.netloc:
        return False

    base_host = _normalize_netloc(base_parsed.netloc)
    target_host = _normalize_netloc(target_parsed.netloc)

    return target_host == base_host or target_host.endswith(f".{base_host}")


def classify_link(url, link_text="", base_url=None, current_url=None):
    """Classifies a link with lightweight heuristics."""
    normalized = normalize_url(url, base_url=base_url)
    if not normalized or not is_internal_link(normalized, base_url=base_url):
        return None

    if current_url:
        current_normalized = normalize_url(current_url)
        if current_normalized:
            current_clean = urlunparse(
                urlparse(current_normalized)._replace(query="", fragment="")
            )
            target_clean = urlunparse(
                urlparse(normalized)._replace(query="", fragment="")
            )
            if target_clean == current_clean:
                return None

    parsed = urlparse(normalized)
    path = f"{parsed.path} {parsed.query}".lower()
    text = (link_text or "").lower()
    combined = f"{path} {text}"

    if any(keyword in combined for keyword in HIGH_PRIORITY_KEYWORDS):
        priority = "high_priority"
    elif any(keyword in combined for keyword in MEDIUM_PRIORITY_KEYWORDS):
        priority = "medium_priority"
    else:
        priority = "normal"

    return {"url": normalized, "priority": priority, "text": link_text or None}


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self._current_anchor = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        attributes = dict(attrs)
        href = attributes.get("href")
        if not href:
            return

        self._current_anchor = {
            "href": href,
            "title": attributes.get("title", ""),
            "aria_label": attributes.get("aria-label", ""),
            "text_parts": [],
        }

    def handle_data(self, data):
        if self._current_anchor is not None:
            self._current_anchor["text_parts"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self._current_anchor is None:
            return

        anchor = self._current_anchor
        self._current_anchor = None
        anchor_text = " ".join(
            part.strip() for part in anchor["text_parts"] if part.strip()
        )
        self.anchors.append(
            {
                "href": anchor["href"],
                "text": anchor_text,
                "title": anchor["title"],
                "aria_label": anchor["aria_label"],
            }
        )


def discover_internal_links(html, base_url=None, current_url=None, max_links=None):
    """Extracts and ranks internal links from HTML."""
    if not html:
        return []

    parser = _AnchorCollector()
    parser.feed(html)

    seen = set()
    candidates = []

    for anchor in parser.anchors:
        label = " ".join(
            part
            for part in (anchor["text"], anchor["title"], anchor["aria_label"])
            if part
        )
        classified = classify_link(
            anchor["href"], link_text=label, base_url=base_url, current_url=current_url
        )
        if not classified:
            continue

        url = classified["url"]
        if url in seen:
            continue

        seen.add(url)
        candidates.append(classified)

    candidates.sort(
        key=lambda item: (
            (
                0
                if item["priority"] == "high_priority"
                else 1 if item["priority"] == "medium_priority" else 2
            ),
            item["url"],
        )
    )

    if max_links is not None:
        return candidates[:max_links]

    return candidates
