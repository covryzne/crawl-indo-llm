def normalize_whitespace(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def first_non_empty(*values):
    for value in values:
        normalized = normalize_whitespace(value)
        if normalized:
            return normalized
    return ""
