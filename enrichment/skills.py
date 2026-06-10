import re
from constants import SKILL_PATTERNS


def extract_skills(text: str) -> list[str]:
    """Extract matching tech skills from job text."""
    text = text.lower()
    return [name for name, pat in SKILL_PATTERNS.items() if re.search(pat, text)]
