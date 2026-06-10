# QA Job Bot — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a Telegram bot that scrapes Indonesian QA job boards, deduplicates, enriches, and delivers alerts to subscribed users.

**Architecture:** Single async Python process (APScheduler + python-telegram-bot polling). SQLite via aiosqlite. httpx + BS4 + feedparser for scraping. Optional Playwright for JS-heavy sites.

**Tech Stack:** Python 3.11, python-telegram-bot v21, httpx, aiosqlite, BeautifulSoup4, lxml, feedparser, APScheduler, python-dotenv

**Working Directory:** `/opt/hermes/qajobbot`

**Bot Token:** Already in `.env` (BOT_TOKEN)

---

## Phase 1: Project Foundation

### Task 1: Create requirements.txt and install dependencies

**Objective:** Set up the Python environment with all needed packages.

**Files:**
- Create: `requirements.txt`

**Step 1: Write requirements.txt**

```
python-telegram-bot[job-queue]==21.*
httpx==0.27.*
aiosqlite==0.20.*
beautifulsoup4==4.12.*
lxml==5.*
feedparser==6.*
apscheduler==3.*
python-dotenv==1.*
```

**Step 2: Create venv and install**

```bash
cd /opt/hermes/qajobbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 3: Verify**

```bash
python -c "import telegram, httpx, aiosqlite, bs4, feedparser, apscheduler; print('All imports OK')"
```

**Step 4: Commit**

```bash
git init && git add requirements.txt && git commit -m "chore: initial requirements.txt"
```

---

### Task 2: Create config.py

**Objective:** Load settings from .env into a typed dataclass.

**Files:**
- Create: `config.py`

**Step 1: Write config.py**

```python
from dataclasses import dataclass, field
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    PROXY_URL: str = os.getenv("PROXY_URL", "")
    DB_PATH: str = "bot.db"
    LOG_PATH: str = "bot.log"

settings = Settings()
```

**Step 2: Verify**

```bash
python -c "from config import settings; print(f'Token loaded: {bool(settings.BOT_TOKEN)}')"
```

Expected: `Token loaded: True`

**Step 3: Commit**

```bash
git add config.py && git commit -m "feat: add config module"
```

---

### Task 3: Create models.py (dataclasses)

**Objective:** Define Job, User, and Preferences dataclasses.

**Files:**
- Create: `models.py`

**Step 1: Write models.py**

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Job:
    external_id: str
    source: str
    source_url: str
    title: str
    company_name: str
    location: str = ""
    is_remote: bool = False
    is_hybrid: bool = False
    work_type: str = ""
    experience_level: str = "unknown"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description_summary: str = ""
    skills: list[str] = field(default_factory=list)
    posted_at: str = ""

@dataclass
class Preferences:
    work_type: str = "any"        # any, remote, onsite, hybrid
    experience_level: str = "any"  # any, entry, mid, senior
    job_type: str = "any"          # any, fulltime, parttime, contract, freelance, internship
    notification_mode: str = "instant"  # instant, daily, weekly

@dataclass
class User:
    telegram_id: int
    username: str = ""
    first_name: str = ""
    is_subscribed: bool = False
    notification_mode: str = "instant"
    preferences: Preferences = field(default_factory=Preferences)
```

**Step 2: Verify**

```bash
python -c "from models import Job, User, Preferences; j = Job(external_id='1', source='test', source_url='http://x', title='QA', company_name='ACME'); print(f'Job: {j.title}')"
```

**Step 3: Commit**

```bash
git add models.py && git commit -m "feat: add data models"
```

---

### Task 4: Create constants.py

**Objective:** Centralize keyword lists, city names, and exclusion patterns.

**Files:**
- Create: `constants.py`

**Step 1: Write constants.py**

```python
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
```

**Step 2: Verify**

```bash
python -c "from constants import QA_PATTERNS, ID_CITIES, SKILL_PATTERNS; print(f'{len(QA_PATTERNS)} QA patterns, {len(ID_CITIES)} cities, {len(SKILL_PATTERNS)} skills')"
```

**Step 3: Commit**

```bash
git add constants.py && git commit -m "feat: add keyword and location constants"
```

---

## Phase 2: Database Layer

### Task 5: Create database.py (schema + init)

**Objective:** SQLite setup with WAL mode, all tables, indexes, and FTS5.

**Files:**
- Create: `database.py`

**Step 1: Write database.py**

```python
import aiosqlite
import json
from config import settings

DB_PATH = settings.DB_PATH

CREATE_JOBS = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT NOT NULL,
    source          TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    title           TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    location        TEXT,
    is_remote       INTEGER DEFAULT 0,
    is_hybrid       INTEGER DEFAULT 0,
    work_type       TEXT,
    experience_level TEXT DEFAULT 'unknown',
    salary_min      INTEGER,
    salary_max      INTEGER,
    description_summary TEXT,
    skills          TEXT,
    posted_at       TEXT,
    scraped_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_active       INTEGER DEFAULT 1,
    UNIQUE(source, external_id)
);
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id     INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    is_subscribed   INTEGER DEFAULT 0,
    notification_mode TEXT DEFAULT 'instant',
    preferences     TEXT DEFAULT '{}',
    subscribed_at   TEXT,
    last_active_at  TEXT DEFAULT (datetime('now'))
);
"""

CREATE_SENT_JOBS = """
CREATE TABLE IF NOT EXISTS sent_jobs (
    user_id  INTEGER NOT NULL,
    job_id   INTEGER NOT NULL,
    sent_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, job_id)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_active  ON jobs(is_active) WHERE is_active=1;",
    "CREATE INDEX IF NOT EXISTS idx_jobs_source  ON jobs(source);",
]

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, company_name, location, description_summary, skills,
    content=jobs, content_rowid=id
);
"""

CREATE_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, company_name, location, description_summary, skills)
    VALUES (new.id, new.title, new.company_name, new.location, new.description_summary, new.skills);
END;
CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, description_summary, skills)
    VALUES ('delete', old.id, old.title, old.company_name, old.location, old.description_summary, old.skills);
END;
CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, description_summary, skills)
    VALUES ('delete', old.id, old.title, old.company_name, old.location, old.description_summary, old.skills);
    INSERT INTO jobs_fts(rowid, title, company_name, location, description_summary, skills)
    VALUES (new.id, new.title, new.company_name, new.location, new.description_summary, new.skills);
END;
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute(CREATE_JOBS)
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_SENT_JOBS)
        for idx in CREATE_INDEXES:
            await db.execute(idx)
        await db.execute(CREATE_FTS)
        # Triggers require raw execution (multiple statements)
        for stmt in CREATE_FTS_TRIGGERS.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()


async def save_job(job: dict) -> bool:
    """Insert job, ignore if duplicate. Returns True if newly inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        skills_str = ",".join(job.get("skills", [])) if isinstance(job.get("skills"), list) else job.get("skills", "")
        try:
            cursor = await db.execute("""
                INSERT OR IGNORE INTO jobs
                    (external_id, source, source_url, title, company_name, location,
                     is_remote, is_hybrid, work_type, experience_level,
                     salary_min, salary_max, description_summary, skills, posted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job["external_id"], job["source"], job["source_url"],
                job["title"], job["company_name"], job.get("location", ""),
                int(job.get("is_remote", False)), int(job.get("is_hybrid", False)),
                job.get("work_type", ""), job.get("experience_level", "unknown"),
                job.get("salary_min"), job.get("salary_max"),
                job.get("description_summary", ""), skills_str,
                job.get("posted_at", ""),
            ))
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.IntegrityError:
            return False


async def get_new_jobs(since_minutes: int = 16) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM jobs
            WHERE scraped_at > datetime('now', ? || ' minutes')
              AND is_active = 1
            ORDER BY scraped_at DESC
        """, (f"-{since_minutes}",))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_unsent_jobs(user_id: int, since_minutes: int = 60) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT j.* FROM jobs j
            WHERE j.scraped_at > datetime('now', ? || ' minutes')
              AND j.is_active = 1
              AND j.id NOT IN (SELECT job_id FROM sent_jobs WHERE user_id = ?)
            ORDER BY j.scraped_at DESC
        """, (f"-{since_minutes}", user_id))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_sent(user_id: int, job_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_jobs (user_id, job_id) VALUES (?, ?)",
            (user_id, job_id),
        )
        await db.commit()


async def upsert_user(telegram_id: int, username: str = "", first_name: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_active_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active_at = datetime('now')
        """, (telegram_id, username, first_name))
        await db.commit()


async def set_subscribed(telegram_id: int, subscribed: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        if subscribed:
            await db.execute("""
                UPDATE users SET is_subscribed = 1, subscribed_at = datetime('now')
                WHERE telegram_id = ?
            """, (telegram_id,))
        else:
            await db.execute("""
                UPDATE users SET is_subscribed = 0 WHERE telegram_id = ?
            """, (telegram_id,))
        await db.commit()


async def get_subscribers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_subscribed = 1"
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_recent_jobs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE is_active = 1 ORDER BY scraped_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def search_jobs(query: str, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT j.* FROM jobs j
            JOIN jobs_fts fts ON j.id = fts.rowid
            WHERE jobs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        return [dict(r) for r in await cursor.fetchall()]


async def update_user_preferences(telegram_id: int, prefs: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET preferences = ? WHERE telegram_id = ?",
            (json.dumps(prefs), telegram_id),
        )
        await db.commit()


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sent_jobs WHERE user_id = ?", (telegram_id,))
        await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await db.commit()


async def purge_old_jobs(days: int = 90):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM jobs WHERE scraped_at < datetime('now', ? || ' days')",
            (f"-{days}",),
        )
        await db.commit()


async def get_digest_jobs(since_hours: int = 24) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM jobs
            WHERE scraped_at > datetime('now', ? || ' hours')
              AND is_active = 1
            ORDER BY scraped_at DESC
            LIMIT 10
        """, (f"-{since_hours}",))
        return [dict(r) for r in await cursor.fetchall()]
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from database import init_db
asyncio.run(init_db())
print('DB initialized successfully')
"
```

Expected: `DB initialized successfully` and `bot.db` created.

**Step 3: Commit**

```bash
git add database.py && git commit -m "feat: add database layer with FTS5"
```

---

## Phase 3: Enrichment Pipeline

### Task 6: Create enrichment package (keywords, skills, level, summarizer)

**Objective:** Build the filtering and enrichment modules.

**Files:**
- Create: `enrichment/__init__.py`
- Create: `enrichment/keywords.py`
- Create: `enrichment/skills.py`
- Create: `enrichment/level.py`
- Create: `enrichment/summarizer.py`

**Step 1: Create enrichment/__init__.py**

```python
from .keywords import is_qa_job, is_indonesia_relevant
from .skills import extract_skills
from .level import infer_level
from .summarizer import summarize
```

**Step 2: Create enrichment/keywords.py**

```python
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
```

**Step 3: Create enrichment/skills.py**

```python
import re
from constants import SKILL_PATTERNS


def extract_skills(text: str) -> list[str]:
    """Extract matching tech skills from job text."""
    text = text.lower()
    return [name for name, pat in SKILL_PATTERNS.items() if re.search(pat, text)]
```

**Step 4: Create enrichment/level.py**

```python
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
```

**Step 5: Create enrichment/summarizer.py**

```python
import re
from config import settings


async def summarize(title: str, company: str, description: str) -> str:
    """Generate a 2-sentence summary. Uses Claude if ANTHROPIC_API_KEY set, else truncates."""
    clean = re.sub(r"<[^>]+>", "", description).strip()
    summary = clean[:200].rsplit(" ", 1)[0] + "..." if len(clean) > 200 else clean

    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic()
            msg = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Buat ringkasan 1-2 kalimat dalam Bahasa Indonesia untuk lowongan ini:\n"
                        f"Posisi: {title} di {company}\n{clean[:1000]}"
                    ),
                }],
            )
            summary = msg.content[0].text.strip()
        except Exception:
            pass  # fall through to plain summary

    return summary
```

**Step 6: Verify**

```bash
python -c "
from enrichment import is_qa_job, is_indonesia_relevant, extract_skills, infer_level
assert is_qa_job('QA Engineer') == True
assert is_qa_job('Supplier Quality Manager') == False
assert is_indonesia_relevant('Jakarta, Indonesia', False) == True
assert is_indonesia_relevant('Berlin', True, 'must be in EU') == False
assert 'selenium' in extract_skills('Experience with Selenium and Cypress')
assert infer_level('Senior QA Engineer', '') == 'senior'
print('All enrichment checks passed')
"
```

**Step 7: Commit**

```bash
git add enrichment/ && git commit -m "feat: add enrichment pipeline (keywords, skills, level, summarizer)"
```

---

## Phase 4: Scrapers

### Task 7: Create scrapers package with base scraper

**Objective:** Build the base HTTP client with rate limiting and UA rotation.

**Files:**
- Create: `scrapers/__init__.py`
- Create: `scrapers/base.py`

**Step 1: Create scrapers/__init__.py**

```python
```

(empty)

**Step 2: Create scrapers/base.py**

```python
import httpx
import random
import asyncio
import logging
from constants import USER_AGENTS

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all job scrapers with rate limiting and UA rotation."""

    SOURCE: str = "unknown"

    def __init__(self, proxy_url: str = ""):
        headers = {
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json",
        }
        kwargs = {"timeout": 20, "headers": headers, "follow_redirects": True}
        if proxy_url:
            kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**kwargs)
        self._last_request: dict[str, float] = {}

    async def get(self, url: str, **kwargs) -> httpx.Response:
        domain = httpx.URL(url).host
        elapsed = asyncio.get_event_loop().time() - self._last_request.get(domain, 0)
        if elapsed < 3:
            await asyncio.sleep(3 - elapsed + random.uniform(0, 2))

        self.client.headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            resp = await self.client.get(url, **kwargs)
            resp.raise_for_status()
            self._last_request[domain] = asyncio.get_event_loop().time()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"[{self.SOURCE}] Rate limited, backing off 60s")
                await asyncio.sleep(60)
            raise

    async def post(self, url: str, **kwargs) -> httpx.Response:
        domain = httpx.URL(url).host
        elapsed = asyncio.get_event_loop().time() - self._last_request.get(domain, 0)
        if elapsed < 3:
            await asyncio.sleep(3 - elapsed + random.uniform(0, 2))

        self.client.headers["User-Agent"] = random.choice(USER_AGENTS)
        resp = await self.client.post(url, **kwargs)
        resp.raise_for_status()
        self._last_request[domain] = asyncio.get_event_loop().time()
        return resp

    async def scrape(self) -> list[dict]:
        """Override in subclasses. Returns list of raw job dicts."""
        raise NotImplementedError

    async def close(self):
        await self.client.aclose()
```

**Step 3: Verify**

```bash
python -c "from scrapers.base import BaseScraper; print('BaseScraper OK')"
```

**Step 4: Commit**

```bash
git add scrapers/ && git commit -m "feat: add base scraper with rate limiting"
```

---

### Task 8: Add Remote OK scraper (easiest — JSON API, no auth)

**Objective:** First working scraper to validate the full pipeline.

**Files:**
- Create: `scrapers/remoteok.py`

**Step 1: Create scrapers/remoteok.py**

```python
import logging
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    SOURCE = "remoteok"
    API_URL = "https://remoteok.com/api?tags=qa,testing,quality-assurance"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.API_URL)
            data = resp.json()
            # First element is metadata, skip it
            if isinstance(data, list) and len(data) > 1:
                jobs = []
                for item in data[1:]:
                    if not isinstance(item, dict):
                        continue
                    jobs.append({
                        "external_id": str(item.get("id", "")),
                        "source": self.SOURCE,
                        "source_url": item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id', '')}"),
                        "title": item.get("position", ""),
                        "company_name": item.get("company", ""),
                        "location": item.get("location", "Remote"),
                        "is_remote": True,
                        "salary_min": item.get("salary_min"),
                        "salary_max": item.get("salary_max"),
                        "description_summary": (item.get("description", "") or "")[:200],
                        "skills": item.get("tags", []),
                        "posted_at": item.get("date", ""),
                    })
                logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
                return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from scrapers.remoteok import RemoteOKScraper

async def test():
    s = RemoteOKScraper()
    jobs = await s.scrape()
    print(f'Got {len(jobs)} jobs')
    if jobs:
        print(f'Sample: {jobs[0][\"title\"]} @ {jobs[0][\"company_name\"]}')
    await s.close()

asyncio.run(test())
"
```

Expected: `Got N jobs` with a sample title.

**Step 3: Commit**

```bash
git add scrapers/remoteok.py && git commit -m "feat: add Remote OK scraper"
```

---

### Task 9: Add Remotive scraper (JSON API, no auth)

**Objective:** Second scraper — tests multi-source pipeline.

**Files:**
- Create: `scrapers/remotive.py`

**Step 1: Create scrapers/remotive.py**

```python
import logging
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RemotiveScraper(BaseScraper):
    SOURCE = "remotive"
    API_URL = "https://remotive.com/api/remote-jobs?category=qa&limit=50"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.API_URL)
            data = resp.json()
            jobs = []
            for item in data.get("jobs", []):
                jobs.append({
                    "external_id": str(item.get("id", "")),
                    "source": self.SOURCE,
                    "source_url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "company_name": item.get("company_name", ""),
                    "location": item.get("candidate_required_location", "Remote"),
                    "is_remote": True,
                    "salary_min": None,
                    "salary_max": None,
                    "description_summary": (item.get("description", "") or "")[:200],
                    "skills": item.get("tags", []),
                    "posted_at": item.get("publication_date", ""),
                })
            logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from scrapers.remotive import RemotiveScraper
async def test():
    s = RemotiveScraper()
    jobs = await s.scrape()
    print(f'Got {len(jobs)} jobs')
    await s.close()
asyncio.run(test())
"
```

**Step 3: Commit**

```bash
git add scrapers/remotive.py && git commit -m "feat: add Remotive scraper"
```

---

### Task 10: Add We Work Remotely scraper (RSS feed)

**Objective:** Test RSS-based scraping path.

**Files:**
- Create: `scrapers/weworkremotely.py`

**Step 1: Create scrapers/weworkremotely.py**

```python
import logging
import feedparser
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class WWRScraper(BaseScraper):
    SOURCE = "weworkremotely"
    RSS_URL = "https://weworkremotely.com/categories/remote-testing-qa-jobs.rss"

    async def scrape(self) -> list[dict]:
        try:
            resp = await self.get(self.RSS_URL)
            feed = feedparser.parse(resp.text)
            jobs = []
            for entry in feed.entries:
                jobs.append({
                    "external_id": entry.get("id", entry.get("link", "")),
                    "source": self.SOURCE,
                    "source_url": entry.get("link", ""),
                    "title": entry.get("title", ""),
                    "company_name": entry.get("author", ""),
                    "location": "Remote",
                    "is_remote": True,
                    "description_summary": (entry.get("summary", "") or "")[:200],
                    "posted_at": entry.get("published", ""),
                })
            logger.info(f"[{self.SOURCE}] scraped {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE}] scrape error: {e}")
        return []
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from scrapers.weworkremotely import WWRScraper
async def test():
    s = WWRScraper()
    jobs = await s.scrape()
    print(f'Got {len(jobs)} jobs')
    await s.close()
asyncio.run(test())
"
```

**Step 3: Commit**

```bash
git add scrapers/weworkremotely.py && git commit -m "feat: add We Work Remotely scraper"
```

---

### Task 11: Add LinkedIn scraper (RSS + HTML detail)

**Objective:** Highest-volume source — RSS feed + detail page fetch.

**Files:**
- Create: `scrapers/linkedin.py`

**Step 1: Create scrapers/linkedin.py**

```python
import logging
import feedparser
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    SOURCE = "linkedin"
    RSS_TEMPLATE = "https://www.linkedin.com/jobs/search/?keywords={query}&location=Indonesia&f_TPR=r86400&format=rss"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES:
            try:
                url = self.RSS_TEMPLATE.format(query=query.replace(" ", "+"))
                resp = await self.get(url)
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    ext_id = entry.get("urn", entry.get("link", ""))
                    if ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)
                    company = ""
                    if hasattr(entry, "source") and isinstance(entry.source, dict):
                        company = entry.source.get("title", "")
                    all_jobs.append({
                        "external_id": ext_id,
                        "source": self.SOURCE,
                        "source_url": entry.get("link", ""),
                        "title": entry.get("title", ""),
                        "company_name": company,
                        "location": entry.get("location", "Indonesia"),
                        "posted_at": entry.get("published", ""),
                        "description_raw": entry.get("summary", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for query '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from scrapers.linkedin import LinkedInScraper
async def test():
    s = LinkedInScraper()
    jobs = await s.scrape()
    print(f'Got {len(jobs)} jobs')
    if jobs:
        print(f'Sample: {jobs[0][\"title\"]}')
    await s.close()
asyncio.run(test())
"
```

**Step 3: Commit**

```bash
git add scrapers/linkedin.py && git commit -m "feat: add LinkedIn RSS scraper"
```

---

### Task 12: Add Glints scraper (GraphQL API, no auth)

**Objective:** Major Indonesian job board — structured JSON API.

**Files:**
- Create: `scrapers/glints.py`

**Step 1: Create scrapers/glints.py**

```python
import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)

ENDPOINT = "https://glints.com/api/graphql"

QUERY = """
query Jobs($keyword: String, $page: Int) {
  searchJobs(keyword: $keyword, locationName: "Indonesia", pageNumber: $page, pageSize: 20) {
    jobResult {
      jobs {
        id title createdAt workArrangementOption
        salary { minAmount maxAmount currencyCode }
        location { cityName countryCode }
        company { name }
        descriptionHtml
        skills { name }
        minYearsOfExperience maxYearsOfExperience
      }
    }
  }
}
"""


class GlintsScraper(BaseScraper):
    SOURCE = "glints"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for keyword in QA_SEARCH_QUERIES:
            try:
                resp = await self.post(
                    ENDPOINT,
                    json={"query": QUERY, "variables": {"keyword": keyword, "page": 1}},
                    headers={"Content-Type": "application/json"},
                )
                data = resp.json()
                jobs_data = data.get("data", {}).get("searchJobs", {}).get("jobResult", {}).get("jobs", [])
                for job in jobs_data:
                    jid = str(job.get("id", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    salary = job.get("salary") or {}
                    location = job.get("location") or {}
                    company = job.get("company") or {}
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://glints.com/id/opportunities/jobs/{jid}",
                        "title": job.get("title", ""),
                        "company_name": company.get("name", ""),
                        "location": location.get("cityName", "Indonesia"),
                        "is_remote": job.get("workArrangementOption") == "REMOTE",
                        "salary_min": salary.get("minAmount"),
                        "salary_max": salary.get("maxAmount"),
                        "skills": [s["name"] for s in job.get("skills", [])],
                        "posted_at": job.get("createdAt", ""),
                        "description_raw": job.get("descriptionHtml", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{keyword}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
```

**Step 2: Verify**

```bash
python -c "
import asyncio
from scrapers.glints import GlintsScraper
async def test():
    s = GlintsScraper()
    jobs = await s.scrape()
    print(f'Got {len(jobs)} jobs')
    await s.close()
asyncio.run(test())
"
```

**Step 3: Commit**

```bash
git add scrapers/glints.py && git commit -m "feat: add Glints GraphQL scraper"
```

---

### Task 13: Add Kalibrr + JobStreet scrapers

**Objective:** Two more Indonesian boards with JSON APIs.

**Files:**
- Create: `scrapers/kalibrr.py`
- Create: `scrapers/jobstreet.py`

**Step 1: Create scrapers/kalibrr.py**

```python
import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class KalibrrScraper(BaseScraper):
    SOURCE = "kalibrr"
    API_URL = "https://www.kalibrr.com/api/jobs?search={query}&location=Indonesia&sort=date&limit=20&offset=0"

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES[:4]:  # Top 4 queries to avoid rate limits
            try:
                url = self.API_URL.format(query=query.replace(" ", "+"))
                resp = await self.get(url)
                data = resp.json()
                for job in data.get("data", []):
                    jid = str(job.get("id", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    company = job.get("company", {})
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://www.kalibrr.com/job/{jid}",
                        "title": job.get("title", ""),
                        "company_name": company.get("name", "") if isinstance(company, dict) else str(company),
                        "location": job.get("location", {}).get("name", "") if isinstance(job.get("location"), dict) else job.get("location", ""),
                        "work_type": job.get("job_type", ""),
                        "salary_min": job.get("min_salary"),
                        "salary_max": job.get("max_salary"),
                        "posted_at": job.get("published_at", ""),
                        "description_raw": job.get("description", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
```

**Step 2: Create scrapers/jobstreet.py**

```python
import logging
from scrapers.base import BaseScraper
from constants import QA_SEARCH_QUERIES

logger = logging.getLogger(__name__)


class JobStreetScraper(BaseScraper):
    SOURCE = "jobstreet"
    API_URL = (
        "https://id.jobstreet.com/api/jobsearch/v5/jobs?"
        "where=Indonesia&keywords={query}&dateRange=1&pageSize=20&pageNum=1"
    )

    async def scrape(self) -> list[dict]:
        all_jobs = []
        seen_ids = set()
        for query in QA_SEARCH_QUERIES[:4]:
            try:
                url = self.API_URL.format(query=query.replace(" ", "+"))
                resp = await self.get(url, headers={"Accept": "application/json"})
                data = resp.json()
                for job in data.get("results", []):
                    jid = str(job.get("jobId", ""))
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    loc = job.get("location", {}) if isinstance(job.get("location"), dict) else {}
                    all_jobs.append({
                        "external_id": jid,
                        "source": self.SOURCE,
                        "source_url": f"https://id.jobstreet.com/job/{jid}",
                        "title": job.get("jobTitle", ""),
                        "company_name": job.get("companyName", ""),
                        "location": loc.get("label", job.get("jobLocation", "")),
                        "work_type": job.get("workType", ""),
                        "posted_at": job.get("listingDate", ""),
                    })
            except Exception as e:
                logger.error(f"[{self.SOURCE}] error for '{query}': {e}")
        logger.info(f"[{self.SOURCE}] scraped {len(all_jobs)} jobs")
        return all_jobs
```

**Step 3: Verify**

```bash
python -c "
import asyncio
from scrapers.kalibrr import KalibrrScraper
from scrapers.jobstreet import JobStreetScraper
async def test():
    for scraper_cls in [KalibrrScraper, JobStreetScraper]:
        s = scraper_cls()
        jobs = await s.scrape()
        print(f'{s.SOURCE}: {len(jobs)} jobs')
        await s.close()
asyncio.run(test())
"
```

**Step 4: Commit**

```bash
git add scrapers/kalibrr.py scrapers/jobstreet.py && git commit -m "feat: add Kalibrr and JobStreet scrapers"
```

---

## Phase 5: Message Formatting

### Task 14: Create formatter.py

**Objective:** Build Telegram-formatted job alert messages.

**Files:**
- Create: `formatter.py`

**Step 1: Write formatter.py**

```python
def format_job_alert(job: dict) -> str:
    """Format a job dict into a Telegram markdown message."""
    # Emoji based on experience level
    level_emoji = {"entry": "🟢", "mid": "🟡", "senior": "🔴"}.get(
        job.get("experience_level", "mid"), "⚪"
    )

    # Title line
    title = job.get("title", "Unknown Position")
    company = job.get("company_name", "Unknown Company")
    lines = [f"🧪 *{_escape_md(title)}* — {_escape_md(company)}"]

    # Location
    location = job.get("location", "")
    remote_tag = ""
    if job.get("is_remote"):
        remote_tag = " (Remote)"
    elif job.get("is_hybrid"):
        remote_tag = " (Hybrid)"
    if location:
        lines.append(f"\n📍 {_escape_md(location)}{remote_tag}")

    # Work type + level
    work_type = job.get("work_type", "")
    level = job.get("experience_level", "")
    parts = []
    if work_type:
        parts.append(_escape_md(work_type))
    if level and level != "unknown":
        parts.append(f"{level_emoji} {level.capitalize()}")
    if parts:
        lines.append(f"💼 {' · '.join(parts)}")

    # Salary
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if salary_min or salary_max:
        salary_str = _format_salary(salary_min, salary_max)
        lines.append(f"💰 {salary_str}")

    # Skills
    skills = job.get("skills", "")
    if isinstance(skills, str) and skills:
        skills_list = skills
    elif isinstance(skills, list) and skills:
        skills_list = ", ".join(skills)
    else:
        skills_list = ""
    if skills_list:
        lines.append(f"\n🔧 *Skills:* {_escape_md(skills_list)}")

    # Description summary
    desc = job.get("description_summary", "")
    if desc:
        lines.append(f"\n📝 {_escape_md(desc[:200])}")

    # Apply link
    source_url = job.get("source_url", "")
    if source_url:
        lines.append(f"\n🔗 [Lamar Sekarang]({source_url})")

    # Source + posted
    source = job.get("source", "")
    posted = job.get("posted_at", "")
    meta_parts = []
    if posted:
        meta_parts.append(f"📅 {_escape_md(posted[:10])}")
    if source:
        meta_parts.append(f"Sumber: {_escape_md(source)}")
    if meta_parts:
        lines.append(f"{' · '.join(meta_parts)}")

    return "\n".join(lines)


def format_digest(jobs: list[dict]) -> str:
    """Format a daily/weekly digest of jobs as a compact list."""
    if not jobs:
        return "📭 Tidak ada lowongan baru dalam 24 jam terakhir."

    lines = [f"📋 *Lowongan QA Terbaru* ({len(jobs)} lowongan)\n"]
    for i, job in enumerate(jobs, 1):
        title = job.get("title", "")
        company = job.get("company_name", "")
        source_url = job.get("source_url", "")
        link = f"[Lamar]({source_url})" if source_url else ""
        lines.append(f"{i}. {_escape_md(title)} — {_escape_md(company)} {link}")

    return "\n".join(lines)


def _escape_md(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    # For Markdown (v1) we only need to escape _ * [ ] `
    for char in ["_", "*", "[", "]", "`"]:
        text = text.replace(char, f"\\{char}")
    return text


def _format_salary(min_val, max_val) -> str:
    """Format salary range in IDR."""
    if min_val and max_val:
        return f"IDR {min_val:,.0f} – {max_val:,.0f}".replace(",", ".")
    elif min_val:
        return f"IDR {min_val:,.0f}+".replace(",", ".")
    elif max_val:
        return f"Up to IDR {max_val:,.0f}".replace(",", ".")
    return ""
```

**Step 2: Verify**

```bash
python -c "
from formatter import format_job_alert
job = {
    'title': 'QA Engineer', 'company_name': 'Tokopedia',
    'location': 'Jakarta', 'is_remote': False, 'is_hybrid': True,
    'work_type': 'Full-time', 'experience_level': 'mid',
    'salary_min': 8000000, 'salary_max': 12000000,
    'skills': 'Selenium,Postman,JIRA',
    'description_summary': 'Bertanggung jawab melakukan pengujian',
    'source_url': 'https://example.com', 'source': 'linkedin',
    'posted_at': '2026-06-01',
}
print(format_job_alert(job))
"
```

**Step 3: Commit**

```bash
git add formatter.py && git commit -m "feat: add message formatter"
```

---

## Phase 6: Bot Handlers

### Task 15: Create bot.py (command handlers + inline keyboards)

**Objective:** All Telegram bot commands.

**Files:**
- Create: `bot.py`

**Step 1: Write bot.py**

```python
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from telegram.constants import ParseMode
import database as db
from formatter import format_job_alert, format_digest

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(
        "👋 Halo! Saya bot lowongan QA Indonesia.\n\n"
        "Gunakan /subscribe untuk mulai menerima notifikasi lowongan QA terbaru.\n"
        "Gunakan /help untuk melihat semua perintah."
    )


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.first_name or "")
    await db.set_subscribed(user.id, True)
    await update.message.reply_text(
        "✅ Kamu sudah berlangganan! Kamu akan dapat notifikasi saat ada lowongan QA baru.\n\n"
        "Gunakan /preferences untuk mengatur filter."
    )


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.set_subscribed(user.id, False)
    await update.message.reply_text("🔕 Kamu sudah berhenti berlangganan. Gunakan /subscribe untuk mulai lagi.")


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = await db.get_recent_jobs(limit=10)
    if not jobs:
        await update.message.reply_text("📭 Belum ada lowongan tersimpan. Coba lagi nanti.")
        return
    for job in jobs:
        await update.message.reply_text(
            format_job_alert(job),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("🔍 Contoh: /search selenium jakarta")
        return
    jobs = await db.search_jobs(query, limit=5)
    if not jobs:
        await update.message.reply_text(f"🔍 Tidak ditemukan lowongan untuk: {query}")
        return
    for job in jobs:
        await update.message.reply_text(
            format_job_alert(job),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )


async def cmd_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🌐 Remote Only", callback_data="pref_work_remote"),
            InlineKeyboardButton("🏢 On-site", callback_data="pref_work_onsite"),
        ],
        [
            InlineKeyboardButton("🏠 Hybrid", callback_data="pref_work_hybrid"),
            InlineKeyboardButton("✅ Semua", callback_data="pref_work_any"),
        ],
        [
            InlineKeyboardButton("⚡ Langsung", callback_data="pref_notif_instant"),
            InlineKeyboardButton("📅 Harian (08:00)", callback_data="pref_notif_daily"),
        ],
    ]
    await update.message.reply_text(
        "⚙️ Pilih preferensi kamu:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cb_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Get current preferences
    user = await db.get_user(user_id)
    prefs = json.loads(user.get("preferences", "{}")) if user else {}

    if data.startswith("pref_work_"):
        work_type = data.replace("pref_work_", "")
        prefs["work_type"] = work_type
        await db.update_user_preferences(user_id, prefs)
        labels = {"remote": "🌐 Remote Only", "onsite": "🏢 On-site", "hybrid": "🏠 Hybrid", "any": "✅ Semua"}
        await query.edit_message_text(f"✅ Preferensi diperbarui: {labels.get(work_type, work_type)}")

    elif data.startswith("pref_notif_"):
        mode = data.replace("pref_notif_", "")
        prefs["notification_mode"] = mode
        await db.update_user_preferences(user_id, prefs)
        labels = {"instant": "⚡ Langsung", "daily": "📅 Harian (08:00)"}
        await query.edit_message_text(f"✅ Notifikasi: {labels.get(mode, mode)}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Perintah yang tersedia:*\n\n"
        "/start — Mulai menggunakan bot\n"
        "/subscribe — Berlangganan notifikasi\n"
        "/unsubscribe — Berhenti berlangganan\n"
        "/preferences — Atur filter preferensi\n"
        "/jobs — Lihat 10 lowongan terbaru\n"
        "/search <query> — Cari lowongan\n"
        "/deletedata — Hapus data kamu\n"
        "/help — Tampilkan pesan ini\n"
        "/about — Info tentang bot ini",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧪 *QA Job Bot*\n\n"
        "Bot ini memantau lowongan kerja QA/Testing dari berbagai job board Indonesia "
        "dan mengirimkan notifikasi langsung ke Telegram kamu.\n\n"
        "*Sumber data:*\n"
        "• LinkedIn (RSS)\n"
        "• Glints\n"
        "• Kalibrr\n"
        "• JobStreet\n"
        "• Remote OK\n"
        "• Remotive\n"
        "• We Work Remotely\n\n"
        "Dibuat dengan ❤️ untuk komunitas QA Indonesia.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_deletedata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.delete_user(user_id)
    await update.message.reply_text("🗑️ Data kamu sudah dihapus. Gunakan /start untuk mulai lagi.")


def setup_bot(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("preferences", cmd_preferences))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("deletedata", cmd_deletedata))
    app.add_handler(CallbackQueryHandler(cb_preferences, pattern="^pref_"))
    return app
```

**Step 2: Verify**

```bash
python -c "from bot import setup_bot; print('Bot handlers OK')"
```

**Step 3: Commit**

```bash
git add bot.py && git commit -m "feat: add bot command handlers"
```

---

## Phase 7: Dispatcher + Scheduler

### Task 16: Create dispatcher.py

**Objective:** Match new jobs to subscribed users and send alerts.

**Files:**
- Create: `dispatcher.py`

**Step 1: Write dispatcher.py**

```python
import json
import asyncio
import logging
from telegram import Bot
import database as db
from formatter import format_job_alert, format_digest

logger = logging.getLogger(__name__)


def matches_prefs(job: dict, prefs: dict) -> bool:
    """Check if a job matches user preferences."""
    work_type = prefs.get("work_type", "any")
    if work_type and work_type != "any":
        if work_type == "remote" and not job.get("is_remote"):
            return False
        if work_type == "onsite" and job.get("is_remote"):
            return False
        if work_type == "hybrid" and not job.get("is_hybrid"):
            return False

    level = prefs.get("experience_level", "any")
    if level and level != "any":
        if job.get("experience_level", "unknown") != level:
            return False

    return True


async def dispatch_new_jobs(bot: Bot):
    """Send new unsent jobs to subscribed users."""
    jobs = await db.get_new_jobs(since_minutes=16)
    if not jobs:
        return

    subscribers = await db.get_subscribers()
    if not subscribers:
        return

    sent_count = 0
    for user in subscribers:
        prefs = json.loads(user.get("preferences", "{}"))
        for job in jobs:
            if not matches_prefs(job, prefs):
                continue
            # Check if already sent
            if user["telegram_id"] and job["id"]:
                try:
                    await bot.send_message(
                        chat_id=user["telegram_id"],
                        text=format_job_alert(job),
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    await db.mark_sent(user["telegram_id"], job["id"])
                    sent_count += 1
                    await asyncio.sleep(0.05)  # Telegram rate limit
                except Exception as e:
                    logger.warning(f"Send failed for user {user['telegram_id']}: {e}")

    if sent_count:
        logger.info(f"Dispatched {sent_count} job alerts")


async def send_daily_digest(bot: Bot):
    """Send daily digest to users with daily notification mode."""
    jobs = await db.get_digest_jobs(since_hours=24)
    if not jobs:
        return

    subscribers = await db.get_subscribers()
    digest_text = format_digest(jobs)

    for user in subscribers:
        mode = user.get("notification_mode", "instant")
        if mode == "daily":
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=digest_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Daily digest failed for {user['telegram_id']}: {e}")
```

**Step 2: Verify**

```bash
python -c "from dispatcher import dispatch_new_jobs, send_daily_digest; print('Dispatcher OK')"
```

**Step 3: Commit**

```bash
git add dispatcher.py && git commit -m "feat: add job dispatcher and digest sender"
```

---

### Task 17: Create scheduler.py

**Objective:** APScheduler setup — register all scraper jobs, dispatch, digest, cleanup.

**Files:**
- Create: `scheduler.py`

**Step 1: Write scheduler.py**

```python
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from enrichment import is_qa_job, is_indonesia_relevant, extract_skills, infer_level, summarize
import database as db
from dispatcher import dispatch_new_jobs, send_daily_digest
from scrapers.remoteok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.weworkremotely import WWRScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.glints import GlintsScraper
from scrapers.kalibrr import KalibrrScraper
from scrapers.jobstreet import JobStreetScraper

logger = logging.getLogger(__name__)


async def run_scraper(scraper, source_name: str):
    """Run a single scraper, filter, enrich, and save jobs."""
    try:
        raw_jobs = await scraper.scrape()
        saved = 0
        for job in raw_jobs:
            title = job.get("title", "")
            desc = job.get("description_raw", "")
            location = job.get("location", "")
            is_remote = job.get("is_remote", False)

            # Filter: must be QA and Indonesia-relevant
            if not is_qa_job(title, desc):
                continue
            if not is_indonesia_relevant(location, is_remote, desc):
                continue

            # Enrich
            job["skills"] = extract_skills(desc) if isinstance(job.get("skills"), list) == False else job.get("skills", [])
            if isinstance(job["skills"], str):
                job["skills"] = [s.strip() for s in job["skills"].split(",") if s.strip()]
            job["experience_level"] = infer_level(title, desc)
            job["description_summary"] = await summarize(
                title, job.get("company_name", ""), desc
            )

            # Remove raw description before saving
            job.pop("description_raw", None)

            is_new = await db.save_job(job)
            if is_new:
                saved += 1

        logger.info(f"[{source_name}] scraped={len(raw_jobs)} saved={saved}")
        await scraper.close()
    except Exception as e:
        logger.error(f"[{source_name}] scraper error: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="Asia/Jakarta")

    # Scrapers — each gets its own job
    scrapers = [
        (RemoteOKScraper(), "remoteok", 60),
        (RemotiveScraper(), "remotive", 60),
        (WWRScraper(), "weworkremotely", 60),
        (LinkedInScraper(), "linkedin", 15),
        (GlintsScraper(), "glints", 15),
        (KalibrrScraper(), "kalibrr", 20),
        (JobStreetScraper(), "jobstreet", 20),
    ]

    for scraper, name, minutes in scrapers:
        sched.add_job(
            run_scraper, "interval", minutes=minutes,
            args=[scraper, name], id=f"scraper_{name}",
            max_instances=1, coalesce=True,
        )

    # Dispatch new jobs every 5 minutes
    sched.add_job(
        dispatch_new_jobs, "interval", minutes=5,
        args=[bot], id="dispatcher",
    )

    # Daily digest at 08:00 WIB
    sched.add_job(
        send_daily_digest, "cron", hour=8, minute=0,
        args=[bot], id="daily_digest",
    )

    # Cleanup old jobs at 02:00
    sched.add_job(
        db.purge_old_jobs, "cron", hour=2, minute=0,
        id="cleanup",
    )

    return sched
```

**Step 2: Verify**

```bash
python -c "from scheduler import setup_scheduler; print('Scheduler OK')"
```

**Step 3: Commit**

```bash
git add scheduler.py && git commit -m "feat: add scheduler with all scrapers"
```

---

## Phase 8: Entry Point + Run

### Task 18: Create main.py

**Objective:** Wire everything together and start the bot.

**Files:**
- Create: `main.py`

**Step 1: Write main.py**

```python
import asyncio
import logging
from config import settings
from database import init_db
from bot import setup_bot
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    # Init database
    await init_db()
    logger.info("Database initialized")

    # Setup bot
    app = setup_bot(settings.BOT_TOKEN)
    logger.info("Bot handlers registered")

    # Setup scheduler
    scheduler = setup_scheduler(app.bot)
    scheduler.start()
    logger.info("Scheduler started")

    # Run bot in polling mode
    logger.info("Bot starting in polling mode...")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Bot is running! Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
```

**Step 2: Verify**

```bash
python -c "from main import main; print('Main OK')"
```

**Step 3: Commit**

```bash
git add main.py && git commit -m "feat: add main entry point"
```

---

### Task 19: Create .gitignore

**Objective:** Keep repo clean.

**Files:**
- Create: `.gitignore`

**Step 1: Write .gitignore**

```
venv/
__pycache__/
*.pyc
.env
*.db
*.log
playwright/
```

**Step 2: Commit**

```bash
git add .gitignore && git commit -m "chore: add .gitignore"
```

---

### Task 20: Run the bot and test

**Objective:** Start the bot, verify it connects, test /start command.

**Step 1: Start the bot**

```bash
cd /opt/hermes/qajobbot
source venv/bin/activate
python main.py
```

Expected: Bot starts, logs show "Bot is running!"

**Step 2: Test on Telegram**

Send `/start` to `@QAJobsID_bot` — should get welcome message.

**Step 3: Test /subscribe**

Send `/subscribe` — should confirm subscription.

**Step 4: Wait for first scrape cycle**

After ~15 minutes, Remote OK scraper should have run. Send `/jobs` to see results.

**Step 5: Set up systemd service**

```bash
sudo tee /etc/systemd/system/qajobbot.service << 'EOF'
[Unit]
Description=QA Job Bot
After=network.target

[Service]
WorkingDirectory=/opt/hermes/qajobbot
ExecStart=/opt/hermes/qajobbot/venv/bin/python main.py
Restart=on-failure
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable qajobbot
sudo systemctl start qajobbot
sudo journalctl -u qajobbot -f
```

**Step 6: Final commit**

```bash
git add -A && git commit -m "chore: final cleanup"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1. Foundation | 1–4 | deps, config, models, constants |
| 2. Database | 5 | SQLite schema + queries |
| 3. Enrichment | 6 | keywords, skills, level, summarizer |
| 4. Scrapers | 7–13 | base + 7 scrapers (Remote OK, Remotive, WWR, LinkedIn, Glints, Kalibrr, JobStreet) |
| 5. Formatting | 14 | Telegram message builder |
| 6. Bot | 15 | Command handlers |
| 7. Dispatch | 16–17 | Dispatcher + Scheduler |
| 8. Run | 18–20 | main.py, .gitignore, deploy |

**Total: 20 tasks, ~60 files touched**
