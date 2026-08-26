def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_lines(value):
    if not value:
        return []
    return [line.strip() for line in value.replace("；", "\n").replace(";", "\n").splitlines() if line.strip()]


def contains_any_text(text_value, keywords):
    text_value = (text_value or "").lower()
    return any(keyword.lower() in text_value for keyword in keywords)
