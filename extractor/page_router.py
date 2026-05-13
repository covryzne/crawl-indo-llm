"""Lightweight page classification helpers for generic government/news crawling."""

from extractor.generic_content import first_non_empty, normalize_whitespace

GOVERNMENT_KEYWORDS = (
    "go.id",
    "kemdikbud",
    "kemen",
    "setneg",
    "bappenas",
    "komdigi",
    "bgn",
    "esdm",
    "pemda",
    "pemerintah",
)

NEWS_KEYWORDS = (
    "news",
    "berita",
    "siaran-pers",
    "siaran pers",
    "press",
    "article",
)

PUBLICATION_KEYWORDS = (
    "publikasi",
    "publication",
    "laporan",
    "report",
    "dokumen",
    "document",
    "makalah",
    "ebook",
)

DOCUMENT_KEYWORDS = (
    "pdf",
    "download",
    "unduh",
    "lampiran",
    "attachment",
    "file",
)


def _lower_join(*values):
    return " ".join(normalize_whitespace(value).lower() for value in values if value)


def classify_page_type(url, title="", text="", attachments=None, candidate_links=None):
    """Classify a page into government/news/publication/document/other."""
    attachments = attachments or []
    candidate_links = candidate_links or []

    combined = _lower_join(url, title, text)
    attachment_text = _lower_join(
        *(attachment.get("url", "") for attachment in attachments),
        *(attachment.get("text", "") for attachment in attachments),
    )

    if attachments and any(keyword in attachment_text for keyword in DOCUMENT_KEYWORDS):
        return "document"

    if any(keyword in combined for keyword in DOCUMENT_KEYWORDS):
        return "document"

    if any(keyword in combined for keyword in PUBLICATION_KEYWORDS):
        return "publication"

    if any(keyword in combined for keyword in NEWS_KEYWORDS):
        return "news"

    if any(keyword in combined for keyword in GOVERNMENT_KEYWORDS):
        return "government"

    if candidate_links:
        high_priority_count = sum(
            1
            for link in candidate_links
            if link.get("priority") in {"high_priority", "medium_priority"}
        )
        if high_priority_count >= 3:
            return "news"

    return "other"


def classify_source_domain(url):
    """Best-effort domain label from URL."""
    lowered = (url or "").lower()
    if any(keyword in lowered for keyword in GOVERNMENT_KEYWORDS):
        return "government"
    if any(keyword in lowered for keyword in NEWS_KEYWORDS):
        return "news"
    if any(keyword in lowered for keyword in PUBLICATION_KEYWORDS):
        return "publication"
    if any(keyword in lowered for keyword in DOCUMENT_KEYWORDS):
        return "document"
    return "other"
