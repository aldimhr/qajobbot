import re

# --- QA keyword patterns (regex, case-insensitive) ---
QA_PATTERNS = [
    r"\bqa\b", r"quality assurance", r"quality analyst",
    r"software tester", r"test engineer", r"automation engineer",
    r"\bsdet\b", r"qa engineer", r"qa lead", r"qa manager",
    r"manual tester", r"performance tester", r"mobile tester",
    r"game tester", r"penguji perangkat lunak", r"analis kualitas",
    r"insinyur qa", r"insinyur pengujian", r"staf qa",
]

EXCLUDE_PATTERNS = [
    r"supplier quality", r"food quality", r"quality control food",
    r"manufacturing quality", r"iso auditor",
]

# --- Indonesian locations ---
ID_CITIES = [
    "indonesia", "jakarta", "bandung", "surabaya", "yogyakarta", "bali",
    "medan", "makassar", "semarang", "bekasi", "tangerang", "depok",
    "palembang", "pekanbaru", "malang", "bogor", "batam",
]

NON_ID_RESTRICTIONS = [
    r"must be (in|based in|located in) (us|uk|eu|europe|australia|canada|germany)",
    r"(us|uk|eu|us-based|uk-based) only",
    r"authorized to work in (us|uk|eu|europe)",
]

# --- Skill extraction patterns ---
SKILL_PATTERNS = {
    "selenium": r"\bselenium\b",
    "cypress": r"\bcypress\b",
    "playwright": r"\bplaywright\b",
    "postman": r"\bpostman\b",
    "jira": r"\bjira\b",
    "pytest": r"\bpytest\b",
    "robot framework": r"robot framework",
    "appium": r"\bappium\b",
    "k6": r"\bk6\b",
    "jmeter": r"\bjmeter\b",
    "sql": r"\bsql\b",
    "api testing": r"api test",
    "mobile testing": r"mobile test",
    "rest assured": r"rest.?assured",
}

# --- Scraping config ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

QA_SEARCH_QUERIES = [
    "QA Engineer", "Quality Assurance", "Software Tester",
    "Test Automation", "SDET", "QA Analyst", "Manual Tester",
]

# --- Hiring signals (for post scanning) ---
HIRING_SIGNALS_ID = [
    "dicari", "mencari", "butuh", "dibutuhkan", "kami butuh",
    "lowongan", "loker", "hiring", "recruiting", "we're hiring",
    "looking for", "cari", "sedang cari", "rekrut", "open position",
    "info loker", "info lowongan", "join our team", "join my team",
    "dibuka", "tersedia", "kesempatan", "peluang",
]

HIRING_SIGNALS_EN = [
    "hiring", "we're hiring", "looking for", "seeking",
    "open position", "job opening", "join our team",
    "now hiring", "is hiring", "are hiring",
    "we are looking", "my team is looking",
]

# LinkedIn posts search queries (rotate to avoid rate limits)
LINKEDIN_POST_QUERIES = [
    "qa engineer hiring",
    "test engineer hiring",
    "quality assurance hiring",
    "qa automation hiring",
    "selenium hiring",
    "tester hiring",
    "lowongan qa",
    "lowongan tester",
    "dicari qa",
    "mencari qa engineer",
    "qa engineer indonesia",
]
