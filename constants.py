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
    # Test automation frameworks
    "selenium": r"\bselenium\b",
    "cypress": r"\bcypress\b",
    "playwright": r"\bplaywright\b",
    "appium": r"\bappium\b",
    "robot framework": r"robot framework",
    "rest assured": r"rest.?assured",
    "testng": r"\btestng\b",
    "junit": r"\bjunit\b",
    "cucumber": r"\bcucumber\b",
    "behave": r"\bbehave\b",
    "detox": r"\bdetox\b",
    "xcuitest": r"\bxcuitest\b",
    "espresso": r"\bespresso\b",
    "webdriverio": r"\bwebdriverio\b",
    "puppeteer": r"\bpuppeteer\b",
    "taiko": r"\btaiko\b",
    # API & performance testing
    "postman": r"\bpostman\b",
    "k6": r"\bk6\b",
    "jmeter": r"\bjmeter\b",
    "gatling": r"\bgatling\b",
    "locust": r"\blocust\b",
    "artillery": r"\bartillery\b",
    "api testing": r"api test",
    "mobile testing": r"mobile test",
    # Languages & scripting
    "python": r"\bpython\b",
    "java": r"\bjava\b",
    "javascript": r"\bjavascript\b",
    "typescript": r"\btypescript\b",
    "groovy": r"\bgroovy\b",
    "sql": r"\bsql\b",
    # DevOps & CI/CD
    "docker": r"\bdocker\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "jenkins": r"\bjenkins\b",
    "gitlab ci": r"\bgitlab.?ci\b",
    "github actions": r"github.?actions",
    "aws": r"\baws\b",
    "azure": r"\bazure\b",
    "terraform": r"\bterraform\b",
    # Project management & reporting
    "jira": r"\bjira\b",
    "testrail": r"\btestrail\b",
    "zephyr": r"\bzephyr\b",
    "xray": r"\bxray\b",
    "qase": r"\bqase\b",
    "allure": r"\ballure\b",
    # QA concepts
    "bdd": r"\bbdd\b",
    "tdd": r"\btdd\b",
    "ci/cd": r"\bci.?cd\b",
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
