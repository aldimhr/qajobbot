"""Extract structured job data from unstructured LinkedIn post text."""

import re
from constants import (
    QA_PATTERNS, EXCLUDE_PATTERNS, ID_CITIES,
    HIRING_SIGNALS_ID, HIRING_SIGNALS_EN, QA_SEARCH_QUERIES,
)

# Job title extraction patterns
_TITLE_PATTERNS = [
    # "Hiring: Senior QA Engineer" / "Hiring - QA Automation"
    r"(?:hiring|looking for|seeking|cari|mencari|butuh|dibutuhkan)[:\s\-–—]+(?:a\s+)?(.+?)(?:\.|!|\n|$)",
    # "We're hiring a QA Engineer"
    r"(?:we'?re|we are|kami)\s+(?:hiring|looking for|seeking|cari|mencari|butuh)\s+(?:a\s+)?(.+?)(?:\.|!|\n|$)",
    # "Open position: QA Engineer"
    r"(?:open position|posisi|lowongan|loker)[:\s\-–—]+(.+?)(?:\.|!|\n|$)",
    # "QA Engineer position available"
    r"(.+?)\s+(?:position|posisi)\s+(?:available|open|tersedia)",
    # "Dicari: QA Engineer"
    r"(?:dicari|dibutuhkan)[:\s\-–—]+(.+?)(?:\.|!|\n|$)",
]

# Location extraction
_LOCATION_PATTERN = re.compile(
    r"\b(" + "|".join(ID_CITIES) + r"|remote|wfh|work from home|hybrid|wfo)\b",
    re.IGNORECASE,
)

# URL extraction
_URL_PATTERN = re.compile(
    r"https?://[^\s\)\]\"'>]+",
    re.IGNORECASE,
)

# Apply link indicators
_APPLY_INDICATORS = [
    "apply", "apply here", "apply at", "apply now",
    "lamar", "daftar", "link", "link apply", "link lamar",
    "klik", "click here", "registration", "registrasi",
]

_TITLE_RE = re.compile("|".join(_TITLE_PATTERNS), re.IGNORECASE)


def is_qa_post(text: str) -> bool:
    """Check if a post is about QA/testing jobs. Must have both QA keywords AND hiring signals."""
    text_lower = text.lower()

    # Check for QA relevance
    qa_score = 0
    for pat in QA_PATTERNS:
        if re.search(pat, text_lower):
            qa_score += 1

    # Exclude non-software QA
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, text_lower):
            return False

    # Must have at least 1 QA keyword
    if qa_score < 1:
        return False

    # Must have hiring signals
    all_signals = HIRING_SIGNALS_ID + HIRING_SIGNALS_EN
    has_signal = any(sig in text_lower for sig in all_signals)

    return has_signal


def extract_job_title(text: str) -> str:
    """Extract job title from post text using patterns. Returns best guess or generic fallback."""
    for pattern in _TITLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            # Clean up: remove trailing punctuation, links, etc.
            title = re.sub(r"https?://\S+", "", title).strip()
            title = re.sub(r"[.!?]+$", "", title).strip()
            # Limit length
            if len(title) > 100:
                title = title[:100].rsplit(" ", 1)[0] + "..."
            if len(title) > 3:  # must be meaningful
                return title

    # Fallback: look for QA-related terms in text
    text_lower = text.lower()
    for query in QA_SEARCH_QUERIES:
        if query.lower() in text_lower:
            return query

    return "QA Engineer"


def extract_company(text: str, author: str = "") -> str:
    """Extract company name — prefer author name, fallback to text patterns."""
    if author and author.strip():
        company = author.strip()
        # Remove common suffixes like " | HR", " | Recruiter"
        company = re.sub(r"\s*[\|–-]\s*(HR|Recruiter|Hiring Manager|Talent Acquisition).*$",
                         "", company, flags=re.IGNORECASE)
        if len(company) > 2:
            return company

    # Try to find company in text: "at {Company}", "di {Company}"
    match = re.search(r"(?:at|@|di|di\s+)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[.,!]|\s+is\s+|\s+sedang|\s+we|\s+kami|\n)", text)
    if match:
        return match.group(1).strip()

    return ""


def extract_location(text: str) -> str:
    """Extract location from post text."""
    matches = _LOCATION_PATTERN.findall(text)
    if matches:
        # Return first match, capitalize
        loc = matches[0].strip().title()
        return loc
    return ""


def extract_apply_url(text: str) -> str:
    """Extract application URL from post text."""
    urls = _URL_PATTERN.findall(text)

    # Filter out LinkedIn's own URLs and common non-apply links
    skip_domains = ["linkedin.com", "instagram.com", "facebook.com", "twitter.com", "x.com"]
    apply_urls = []
    for url in urls:
        if not any(d in url.lower() for d in skip_domains):
            apply_urls.append(url)

    if apply_urls:
        return apply_urls[0]

    # If only LinkedIn URLs, return the post URL itself
    if urls:
        return urls[0]

    return ""


def extract_description(text: str) -> str:
    """Clean post text for use as description (remove URLs, excessive whitespace)."""
    # Remove URLs
    desc = re.sub(r"https?://\S+", "", text)
    # Remove excessive whitespace
    desc = re.sub(r"\s+", " ", desc).strip()
    # Truncate for summary
    if len(desc) > 500:
        desc = desc[:500].rsplit(" ", 1)[0] + "..."
    return desc
