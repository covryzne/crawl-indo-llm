import json


def parse_crawl4ai_json(extracted_content):
    if not extracted_content:
        return []

    parsed = json.loads(extracted_content)
    if isinstance(parsed, list):
        return parsed
    return [parsed]
