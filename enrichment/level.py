import re


def infer_level(title: str, description: str) -> str:
    """Infer experience level from job title and description."""
    text = (title + " " + description).lower()
    if any(w in text for w in ["senior", "sr.", "lead", "principal", "staff"]):
        return "senior"
    if any(w in text for w in ["junior", "jr.", "fresh", "entry", "magang", "intern"]):
        return "entry"
    years = re.findall(r"(\d+)\+?\s*(?:years?|tahun)", text)
    if years:
        max_yr = max(int(y) for y in years)
        if max_yr >= 5:
            return "senior"
        if max_yr >= 2:
            return "mid"
        return "entry"
    return "mid"
