import re
from constants import QA_PATTERNS, EXCLUDE_PATTERNS, ID_CITIES, NON_ID_RESTRICTIONS


def is_qa_job(title: str, description: str = "") -> bool:
    """Check if a job title/description matches QA roles."""
    t = title.lower()
    # Check exclusions first
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, t):
            return False
    # Check title for QA patterns
    for pat in QA_PATTERNS:
        if re.search(pat, t):
            return True
    # Weak signal: description needs 2+ matches
    d = description.lower()
    return sum(1 for p in QA_PATTERNS if re.search(p, d)) >= 2


def is_indonesia_relevant(location: str, is_remote: bool, description: str = "") -> bool:
    """Check if job is relevant to Indonesian applicants."""
    loc = location.lower()
    desc = description.lower()
    # Direct location match
    if any(city in loc for city in ID_CITIES):
        return True
    # Remote but not restricted to non-ID countries
    if is_remote:
        return not any(re.search(p, desc) for p in NON_ID_RESTRICTIONS)
    return False
