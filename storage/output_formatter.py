from copy import deepcopy
from datetime import datetime, timezone


def clean_empty_fields(value):
    """Recursively remove empty strings, empty lists, empty dicts, and null values."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            normalized = clean_empty_fields(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned[key] = normalized
        return cleaned

    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            normalized = clean_empty_fields(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned_list.append(normalized)
        return cleaned_list

    return value


def normalize_attachment_output(attachments):
    """Keep attachment payload compact: url + type only, deduped by URL."""
    normalized = []
    seen = set()

    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            continue

        url = attachment.get("url")
        if not url or url in seen:
            continue

        attachment_type = attachment.get("type") or attachment.get("kind") or "pdf"
        normalized.append({"url": url, "type": attachment_type})
        seen.add(url)

    return normalized


def reduce_candidate_links(candidate_links, limit=5, high_priority_only=True):
    """Reduce noisy internal links to a small, readable subset.

    Accepts either string links or dict records from link discovery.
    """
    reduced = []
    seen = set()

    for item in candidate_links or []:
        if isinstance(item, str):
            url = item
            priority = "normal"
            text = None
        elif isinstance(item, dict):
            url = item.get("url")
            priority = item.get("priority", "normal")
            text = item.get("text")
        else:
            continue

        if not url or url in seen:
            continue
        if high_priority_only and priority != "high_priority":
            continue

        reduced.append(
            clean_empty_fields({"url": url, "text": text, "priority": priority})
        )
        seen.add(url)

        if len(reduced) >= limit:
            break

    return reduced


def _normalize_result_item(result_item):
    normalized = {
        "url": result_item.get("url"),
        "title": result_item.get("title"),
        "page_type": result_item.get("page_type"),
        "attachments": normalize_attachment_output(result_item.get("attachments", [])),
    }
    return clean_empty_fields(normalized)


def build_final_payload(keyword, generated_at, stats, results):
    """Build the final consumable JSON payload for downstream teams."""
    normalized_results = []
    for result in results or []:
        normalized = _normalize_result_item(result)
        if normalized.get("url"):
            normalized_results.append(normalized)

    payload = {
        "keyword": keyword,
        "generated_at": generated_at,
        "stats": stats or {},
        "results": normalized_results,
    }
    return clean_empty_fields(payload)


def build_debug_payload(raw_payload, candidate_link_limit=5):
    """Build a debug-oriented payload with reduced internal crawler metadata."""
    debug_payload = deepcopy(raw_payload or {})

    if "seeds" in debug_payload:
        for seed in debug_payload["seeds"]:
            if not isinstance(seed, dict):
                continue
            seed["candidate_links"] = reduce_candidate_links(
                seed.get("candidate_links", []),
                limit=candidate_link_limit,
                high_priority_only=True,
            )
            seed["attachments"] = normalize_attachment_output(
                seed.get("attachments", [])
            )

    return clean_empty_fields(debug_payload)


def current_utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
