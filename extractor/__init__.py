from .page_router import classify_page_type
from .pdf_discovery import (
    discover_attachment_candidates_from_html,
    discover_attachment_candidates_from_record,
    extract_pdf_urls_from_html,
    extract_pdf_urls_from_record,
    is_attachment_candidate,
    is_pdf_url,
    normalize_url,
)
