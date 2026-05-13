from .link_discovery import classify_link, discover_internal_links, is_internal_link
from .page_router import classify_page_type, classify_source_domain
from .pdf_discovery import (
    discover_attachment_candidates_from_html,
    discover_attachment_candidates_from_record,
    extract_pdf_urls_from_html,
    extract_pdf_urls_from_record,
    is_attachment_candidate,
    is_pdf_url,
    normalize_url,
)
