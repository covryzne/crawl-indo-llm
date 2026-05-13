"""Lightweight attachment and PDF discovery helpers."""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

ATTACHMENT_KEYWORDS = (
    "attachment",
    "attachments",
    "lampiran",
    "download",
    "unduh",
    "dokumen",
    "file",
    "pdf",
)

FILE_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
)

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "#")


def normalize_url(url, base_url=None):
    """Normalizes a URL and resolves it against an optional base URL."""
    if not url:
        return None

    cleaned = " ".join(str(url).strip().split())
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered.startswith(SKIP_SCHEMES):
        return None

    resolved = urljoin(base_url, cleaned) if base_url else cleaned
    parsed = urlparse(resolved)

    if parsed.scheme and parsed.netloc:
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
        )

    return resolved


def is_pdf_url(url):
    """Returns True when the URL points to a PDF file."""
    if not url:
        return False

    parsed = urlparse(url)
    return parsed.path.lower().endswith(".pdf")


def is_attachment_candidate(url, link_text=""):
    """Returns True for URLs that look like attachments."""
    if not url:
        return False

    normalized = normalize_url(url)
    if not normalized:
        return False

    if is_pdf_url(normalized):
        return True

    parsed = urlparse(normalized)
    path = parsed.path.lower()
    query = parsed.query.lower()
    text = (link_text or "").lower()

    if any(keyword in path for keyword in ATTACHMENT_KEYWORDS):
        return True

    if any(keyword in query for keyword in ATTACHMENT_KEYWORDS):
        return True

    if any(keyword in text for keyword in ATTACHMENT_KEYWORDS):
        return True

    return path.endswith(FILE_EXTENSIONS)


def _unique_candidates(candidates):
    seen = set()
    unique_candidates = []

    for candidate in candidates:
        url = candidate["url"]
        if url in seen:
            continue
        seen.add(url)
        unique_candidates.append(candidate)

    return unique_candidates


def discover_attachment_candidates_from_record(record, base_url=None, fields=None):
    """Extracts attachment-like URLs from a structured record."""
    if not isinstance(record, dict):
        return []

    fields = fields or ("dokumen_peraturan", "attachment", "link", "href", "url")
    text_hint = " ".join(
        str(record.get(key, "")).strip()
        for key in ("judul", "title", "name", "text")
        if record.get(key)
    )

    candidates = []
    for field in fields:
        raw_url = record.get(field)
        if not isinstance(raw_url, str):
            continue

        normalized = normalize_url(raw_url, base_url=base_url)
        if not normalized:
            continue

        if is_attachment_candidate(normalized, text_hint):
            candidates.append(
                {
                    "url": normalized,
                    "source_field": field,
                    "kind": "pdf" if is_pdf_url(normalized) else "attachment",
                    "text": text_hint or None,
                }
            )

    return _unique_candidates(candidates)


def extract_pdf_urls_from_record(record, base_url=None, fields=None):
    """Returns normalized PDF URLs from a structured record."""
    pdf_urls = []
    for candidate in discover_attachment_candidates_from_record(
        record, base_url=base_url, fields=fields
    ):
        if candidate["kind"] == "pdf":
            pdf_urls.append(candidate["url"])
    return pdf_urls


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.candidates = []
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
        self.candidates.append(
            {
                "href": anchor["href"],
                "text": anchor_text,
                "title": anchor["title"],
                "aria_label": anchor["aria_label"],
            }
        )


def discover_attachment_candidates_from_html(html, base_url=None):
    """Extracts attachment-like URLs from HTML anchor tags."""
    if not html:
        return []

    parser = _AnchorCollector()
    parser.feed(html)

    candidates = []
    for anchor in parser.candidates:
        label = " ".join(
            part
            for part in (anchor["text"], anchor["title"], anchor["aria_label"])
            if part
        )
        normalized = normalize_url(anchor["href"], base_url=base_url)
        if not normalized:
            continue

        if is_attachment_candidate(normalized, label):
            candidates.append(
                {
                    "url": normalized,
                    "kind": "pdf" if is_pdf_url(normalized) else "attachment",
                    "text": label or None,
                }
            )

    return _unique_candidates(candidates)


def extract_pdf_urls_from_html(html, base_url=None):
    """Returns normalized PDF URLs found in HTML."""
    return [
        candidate["url"]
        for candidate in discover_attachment_candidates_from_html(
            html, base_url=base_url
        )
        if candidate["kind"] == "pdf"
    ]
