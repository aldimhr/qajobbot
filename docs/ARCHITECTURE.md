# QA Job Bot — Architecture Document

## 1. System Overview

The bot is a **single Python process** — no Docker, no Redis, no PostgreSQL. Everything runs in one script with APScheduler driving the scrape loops and python-telegram-bot handling user interaction. State is persisted in a single SQLite file on disk.

```
┌──────────────────────────────────────────────────────────┐
│                    main.py  (one process)                │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Scheduler  │──▶│   Scrapers   │──▶│  Enrichment  │  │
│  │ APScheduler │   │ httpx/BS4/   │   │  (keyword,   │  │
│  │  (async)    │   │  feedparser  │   │  skills, lvl)│  │
│  └─────────────┘   └──────┬───────┘   └──────┬───────┘  │
│                           │                  │           │
│                           ▼                  ▼           │
│                    ┌─────────────────────────────┐       │
│                    │       SQLite  (bot.db)       │       │
│                    │  jobs · users · sent_jobs    │       │
│                    └──────────────┬──────────────┘       │
│                                  │                       │
│  ┌───────────────────────────────▼──────────────────┐   │
│  │              Dispatcher  (async loop)             │   │
│  │  matches new jobs → user prefs → sends via        │   │
│  │  Telegram Bot API                                 │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │              Bot Handler (polling)                │   │
│  │  /commands · inline keyboards · preferences       │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

Everything is async (`asyncio`). The scheduler, scrapers, dispatcher, and bot handler all share the same event loop.

---

## 2. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Best scraping + bot ecosystem |
| Bot framework | python-telegram-bot v21 (async) | Mature, full Bot API, polling mode |
| HTTP client | httpx (async) | Fast, supports proxies, async-native |
| HTML parsing | BeautifulSoup4 + lxml | Reliable, fast |
| JS-heavy sites | playwright (async) | For React-rendered job boards |
| RSS parsing | feedparser | LinkedIn / remote boards |
| Scheduler | APScheduler (AsyncIOScheduler) | In-process cron, no external service |
| Database | SQLite (via aiosqlite) | Zero-config, single file, persistent |
| Config | python-dotenv + dataclass | Simple `.env` file |
| Logging | Python `logging` → `bot.log` | Plain file log, no infra needed |
| AI enrichment | Anthropic Claude API (optional) | Summary generation if key present |

---

## 3. Project Structure

```
qa-job-bot/
├── main.py                  # Entry point — wires everything, starts event loop
├── config.py                # Settings loaded from .env
├── database.py              # SQLite setup, all DB queries (aiosqlite)
├── scheduler.py             # APScheduler setup, registers all scraper jobs
├── dispatcher.py            # Matches new jobs to users, sends Telegram messages
├── formatter.py             # Builds Telegram message text from Job objects
├── bot.py                   # Telegram command handlers, inline keyboards
│
├── scrapers/
│   ├── base.py              # BaseScaper: httpx session, UA rotation, delays
│   ├── linkedin.py          # RSS feed + HTML detail fetch
│   ├── glints.py            # GraphQL/JSON API
│   ├── kalibrr.py           # JSON API
│   ├── jobstreet.py         # JSON API
│   ├── indeed_id.py         # HTML scrape (Playwright)
│   ├── techinasia.py        # HTML scrape (Playwright)
│   ├── lokerid.py           # HTML scrape (httpx + BS4)
│   ├── topkarir.py          # HTML scrape (httpx + BS4)
│   ├── ekrut.py             # HTML scrape (httpx + BS4)
│   ├── remotive.py          # JSON API
│   ├── remoteok.py          # JSON API
│   └── weworkremotely.py    # RSS feed
│
├── enrichment/
│   ├── keywords.py          # QA keyword regex patterns + location filter
│   ├── skills.py            # Tech skill tag extraction
│   ├── level.py             # Experience level inference
│   └── summarizer.py        # Plain-text summary (+ optional Claude API)
│
├── models.py                # Python dataclasses: Job, User, Preferences
├── constants.py             # Keyword lists, Indonesian cities, enums
│
├── .env                     # BOT_TOKEN, optional ANTHROPIC_API_KEY
├── requirements.txt
├── bot.db                   # SQLite file (auto-created on first run)
└── bot.log                  # Rolling log file
```

---

## 4. Database (SQLite)

### Setup

```python
# database.py
import aiosqlite

DB_PATH = "bot.db"

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
    skills          TEXT,       -- comma-separated
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
    "CREATE INDEX IF NOT EXISTS idx_jobs_remote  ON jobs(is_remote) WHERE is_remote=1;",
]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")  # concurrent reads + writes
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute(CREATE_JOBS)
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_SENT_JOBS)
        for idx in CREATE_INDEXES:
            await db.execute(idx)
        await db.commit()
```

### Key Queries

```python
# Insert job (ignore if duplicate)
await db.execute("""
    INSERT OR IGNORE INTO jobs
        (external_id, source, source_url, title, company_name, location,
         is_remote, is_hybrid, work_type, experience_level,
         salary_min, salary_max, description_summary, skills, posted_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (...))

# Get new jobs not yet dispatched to a specific user
await db.execute("""
    SELECT j.* FROM jobs j
    WHERE j.scraped_at > datetime('now', '-1 hour')
      AND j.is_active = 1
      AND j.id NOT IN (
          SELECT job_id FROM sent_jobs WHERE user_id = ?
      )
    ORDER BY j.scraped_at DESC
""", (user_id,))

# Full-text search (SQLite FTS5, configured at init)
await db.execute("""
    SELECT j.* FROM jobs j
    JOIN jobs_fts fts ON j.id = fts.rowid
    WHERE jobs_fts MATCH ?
    ORDER BY rank
    LIMIT 20
""", (query,))

# Purge old jobs (90-day cleanup)
await db.execute("""
    DELETE FROM jobs
    WHERE scraped_at < datetime('now', '-90 days')
""")
```

---

## 5. Scraper Architecture

### 5.1 Base Scraper

```python
# scrapers/base.py
import httpx, random, asyncio

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
]

class BaseScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=20,
            headers={
                "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/json",
            },
            follow_redirects=True,
        )
        self._last_request: dict[str, float] = {}

    async def get(self, url: str, **kwargs) -> httpx.Response:
        domain = httpx.URL(url).host
        # Per-domain rate limit: min 3 seconds between requests
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
                await asyncio.sleep(60)   # back off 1 min on rate limit
                raise
            raise

    async def close(self):
        await self.client.aclose()
```

### 5.2 How Each Source is Scraped

#### LinkedIn (RSS + HTML detail)

No API key needed. LinkedIn exposes a job search RSS feed:

```
https://www.linkedin.com/jobs/search/?keywords=QA+Engineer&location=Indonesia&f_TPR=r86400&format=rss
```

Parameters: `keywords` (rotated through ~10 QA variants), `location=Indonesia`, `f_TPR=r86400` (last 24h).

```python
# scrapers/linkedin.py
import feedparser

RSS_QUERIES = [
    "QA Engineer", "Quality Assurance", "Software Tester",
    "Test Automation", "SDET", "QA Analyst", "Manual Tester",
]

async def scrape(db) -> list[dict]:
    jobs = []
    for query in RSS_QUERIES:
        url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '+')}&location=Indonesia&f_TPR=r86400&format=rss"
        resp = await self.get(url)
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            jobs.append({
                "external_id": entry.get("urn", entry.link),
                "source": "linkedin",
                "source_url": entry.link,
                "title": entry.title,
                "company_name": entry.get("source", {}).get("title", ""),
                "location": entry.get("location", ""),
                "posted_at": entry.get("published", ""),
                "description_raw": entry.get("summary", ""),
            })
    return deduplicate(jobs)  # by external_id
```

For full description, fetch the detail page HTML and parse:
```
Selector: div.show-more-less-html__markup
```

---

#### Glints (GraphQL JSON API — no auth)

```python
# scrapers/glints.py
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

async def scrape() -> list[dict]:
    results = []
    for keyword in QA_KEYWORDS:
        resp = await self.client.post(
            ENDPOINT,
            json={"query": QUERY, "variables": {"keyword": keyword, "page": 1}},
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        for job in data["data"]["searchJobs"]["jobResult"]["jobs"]:
            results.append({
                "external_id": job["id"],
                "source": "glints",
                "title": job["title"],
                "company_name": job["company"]["name"],
                "location": job["location"]["cityName"],
                "is_remote": job["workArrangementOption"] == "REMOTE",
                "salary_min": job["salary"]["minAmount"] if job.get("salary") else None,
                "salary_max": job["salary"]["maxAmount"] if job.get("salary") else None,
                "skills": [s["name"] for s in job.get("skills", [])],
                "posted_at": job["createdAt"],
            })
    return results
```

---

#### Kalibrr (JSON API — no auth)

```
GET https://www.kalibrr.com/api/jobs?search=QA+Engineer&location=Indonesia&sort=date&limit=20&offset=0
```

Returns structured JSON. Paginate via `offset`. Key response fields: `id`, `job_function`, `title`, `company.name`, `location`, `job_type`, `min_salary`, `max_salary`, `description`, `published_at`.

---

#### JobStreet Indonesia (JSON API — no auth)

```
GET https://id.jobstreet.com/api/jobsearch/v5/jobs?
    where=Indonesia
    &keywords=quality+assurance
    &dateRange=1
    &pageSize=20
    &pageNum=1
```

Set `Accept: application/json`. Returns `jobId`, `jobTitle`, `companyName`, `jobLocation`, `workingArrangements`, `salary`, `listingDate`.

---

#### Indeed Indonesia (Playwright — HTML)

Indeed renders job cards with JS, so we use Playwright:

```python
# scrapers/indeed_id.py
from playwright.async_api import async_playwright

URL = "https://id.indeed.com/jobs?q={query}&l=Indonesia&fromage=1&sort=date"

async def scrape() -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL.format(query="QA+Engineer"))
        await page.wait_for_selector("div.job_seen_beacon", timeout=10000)
        
        cards = await page.query_selector_all("div.job_seen_beacon")
        jobs = []
        for card in cards:
            jobs.append({
                "external_id": await card.get_attribute("data-jk"),
                "source": "indeed_id",
                "title": await card.query_selector("h2.jobTitle") and ...,
                "company_name": ...,
                "location": ...,
                "source_url": f"https://id.indeed.com/viewjob?jk={jk}",
            })
        await browser.close()
        return jobs
```

Note: Playwright adds ~200MB to install but is only needed for Indeed and Tech in Asia. All other scrapers use plain httpx. To skip Playwright entirely, just omit those two spiders from the scheduler.

---

#### Tech in Asia (Playwright — HTML)

```
https://www.techinasia.com/jobs?job_category=engineering&search=QA&country=indonesia
```

React-rendered. Same Playwright approach as Indeed. Selector: `div[data-testid='job-card']`.

---

#### Loker.id / Topkarir / Ekrut (httpx + BeautifulSoup4)

These are simpler WordPress or server-rendered sites, no JS needed:

```python
# scrapers/lokerid.py
from bs4 import BeautifulSoup

URL = "https://www.loker.id/?s=QA+Engineer&post_type=loker"

async def scrape() -> list[dict]:
    resp = await self.get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []
    for article in soup.select("article.loker-item"):
        jobs.append({
            "external_id": article.get("id", ""),
            "source": "lokerid",
            "title": article.select_one("h2.entry-title a").text.strip(),
            "source_url": article.select_one("h2.entry-title a")["href"],
            "company_name": article.select_one("span.company-name").text.strip(),
            "location": article.select_one("span.location").text.strip(),
            "posted_at": article.select_one("time")["datetime"],
        })
    return jobs
```

---

#### Remote Job Boards (JSON API / RSS — simplest)

**Remote OK** (free, no auth):
```
GET https://remoteok.com/api?tags=qa,testing,quality-assurance
```
Returns JSON array. Filter out "US residents only" or "EU only" entries by checking the `description` field.

**Remotive** (free, no auth):
```
GET https://remotive.com/api/remote-jobs?category=qa&limit=50
```

**We Work Remotely** (RSS):
```
https://weworkremotely.com/categories/remote-testing-qa-jobs.rss
```
Parse with `feedparser`. Filter description for geographic restrictions.

---

### 5.3 Keyword & Location Filtering

```python
# enrichment/keywords.py
import re

QA_PATTERNS = [
    r"\bqa\b", r"quality assurance", r"quality analyst",
    r"software tester", r"test engineer", r"automation engineer",
    r"\bsdet\b", r"qa engineer", r"qa lead", r"qa manager",
    r"manual tester", r"performance tester", r"mobile tester",
    r"game tester", r"penguji perangkat lunak", r"analis kualitas",
]

EXCLUDE_PATTERNS = [
    r"supplier quality", r"food quality", r"quality control food",
    r"manufacturing quality",
]

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

def is_qa_job(title: str, description: str = "") -> bool:
    t = title.lower()
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, t):
            return False
    for pat in QA_PATTERNS:
        if re.search(pat, t):
            return True
    # Weak signal: check description for 2+ matches
    d = description.lower()
    return sum(1 for p in QA_PATTERNS if re.search(p, d)) >= 2

def is_indonesia_relevant(location: str, is_remote: bool, description: str = "") -> bool:
    loc = location.lower()
    desc = description.lower()
    if any(city in loc for city in ID_CITIES):
        return True
    if is_remote:
        return not any(re.search(p, desc) for p in NON_ID_RESTRICTIONS)
    return False
```

---

## 6. Enrichment Pipeline

After a raw job is scraped and passes keyword + location filters:

```python
# enrichment/skills.py
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

def extract_skills(text: str) -> list[str]:
    text = text.lower()
    return [name for name, pat in SKILL_PATTERNS.items() if re.search(pat, text)]
```

```python
# enrichment/level.py
def infer_level(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    if any(w in text for w in ["senior", "sr.", "lead", "principal", "staff"]):
        return "senior"
    if any(w in text for w in ["junior", "jr.", "fresh", "entry", "magang", "intern"]):
        return "entry"
    years = re.findall(r"(\d+)\+?\s*(?:years?|tahun)", text)
    if years:
        max_yr = max(int(y) for y in years)
        if max_yr >= 5:   return "senior"
        if max_yr >= 2:   return "mid"
        return "entry"
    return "mid"  # default assumption
```

```python
# enrichment/summarizer.py
async def summarize(title: str, company: str, description: str) -> str:
    # Fallback: first 200 chars of cleaned description
    clean = re.sub(r"<[^>]+>", "", description).strip()
    summary = clean[:200].rsplit(" ", 1)[0] + "..."

    # Optional: if ANTHROPIC_API_KEY set, use Claude haiku
    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic()
            msg = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content":
                    f"Buat ringkasan 1-2 kalimat dalam Bahasa Indonesia untuk lowongan ini:\n"
                    f"Posisi: {title} di {company}\n{clean[:1000]}"
                }]
            )
            summary = msg.content[0].text.strip()
        except Exception:
            pass  # fall through to plain summary

    return summary
```

---

## 7. Dispatcher

```python
# dispatcher.py
import json
from database import get_new_jobs, get_subscribers, mark_sent, get_digest_users
from formatter import format_job_alert, format_digest

async def dispatch_new_jobs(bot):
    jobs = await get_new_jobs(since_minutes=16)  # slightly overlaps scrape interval
    if not jobs:
        return

    users = await get_subscribers()
    for user in users:
        prefs = json.loads(user["preferences"] or "{}")
        for job in jobs:
            if not matches_prefs(job, prefs):
                continue
            if user["notification_mode"] == "instant":
                try:
                    await bot.send_message(
                        chat_id=user["telegram_id"],
                        text=format_job_alert(job),
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    await mark_sent(user["telegram_id"], job["id"])
                    await asyncio.sleep(0.05)  # respect Telegram 30msg/sec limit
                except Exception as e:
                    logging.warning(f"Send failed for user {user['telegram_id']}: {e}")

def matches_prefs(job: dict, prefs: dict) -> bool:
    if prefs.get("work_type") and prefs["work_type"] != "any":
        if prefs["work_type"] == "remote" and not job["is_remote"]:
            return False
        if prefs["work_type"] == "onsite" and job["is_remote"]:
            return False
    if prefs.get("level") and prefs["level"] != "any":
        if job["experience_level"] != prefs["level"]:
            return False
    return True
```

---

## 8. Scheduler

```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scrapers import linkedin, glints, kalibrr, jobstreet, indeed_id, \
                    techinasia, lokerid, topkarir, ekrut, remotive, remoteok, wwr

def setup_scheduler(bot, db):
    sched = AsyncIOScheduler(timezone="Asia/Jakarta")

    async def run_scraper(scraper_fn, source_name):
        try:
            jobs = await scraper_fn()
            saved = 0
            for job in jobs:
                if is_qa_job(job["title"], job.get("description_raw", "")):
                    if is_indonesia_relevant(job.get("location",""), job.get("is_remote", False)):
                        job["skills"] = ",".join(extract_skills(job.get("description_raw","")))
                        job["experience_level"] = infer_level(job["title"], job.get("description_raw",""))
                        job["description_summary"] = await summarize(...)
                        await db.save_job(job)
                        saved += 1
            logging.info(f"[{source_name}] scraped={len(jobs)} saved={saved}")
        except Exception as e:
            logging.error(f"[{source_name}] scraper error: {e}")

    async def dispatch():
        await dispatch_new_jobs(bot)

    # Scrape jobs
    sched.add_job(lambda: run_scraper(linkedin.scrape, "linkedin"),    "interval", minutes=15)
    sched.add_job(lambda: run_scraper(glints.scrape,   "glints"),      "interval", minutes=15)
    sched.add_job(lambda: run_scraper(kalibrr.scrape,  "kalibrr"),     "interval", minutes=20)
    sched.add_job(lambda: run_scraper(jobstreet.scrape,"jobstreet"),   "interval", minutes=20)
    sched.add_job(lambda: run_scraper(indeed_id.scrape,"indeed_id"),   "interval", minutes=30)
    sched.add_job(lambda: run_scraper(techinasia.scrape,"techinasia"), "interval", minutes=30)
    sched.add_job(lambda: run_scraper(lokerid.scrape,  "lokerid"),     "interval", minutes=30)
    sched.add_job(lambda: run_scraper(topkarir.scrape, "topkarir"),    "interval", minutes=30)
    sched.add_job(lambda: run_scraper(ekrut.scrape,    "ekrut"),       "interval", minutes=30)
    sched.add_job(lambda: run_scraper(remotive.scrape, "remotive"),    "interval", minutes=60)
    sched.add_job(lambda: run_scraper(remoteok.scrape, "remoteok"),    "interval", minutes=60)
    sched.add_job(lambda: run_scraper(wwr.scrape,      "wwr"),         "interval", minutes=60)

    # Dispatch alerts every 5 minutes
    sched.add_job(dispatch, "interval", minutes=5)

    # Daily digest at 08:00 WIB
    sched.add_job(send_daily_digest, "cron", hour=8, minute=0)

    # Weekly digest on Monday 08:00 WIB
    sched.add_job(send_weekly_digest, "cron", day_of_week="mon", hour=8, minute=0)

    # Cleanup old jobs at 02:00 every day
    sched.add_job(db.purge_old_jobs, "cron", hour=2, minute=0)

    return sched
```

---

## 9. Bot Handlers

```python
# bot.py
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

async def cmd_start(update, context):
    await update.message.reply_text(
        "👋 Halo! Saya bot lowongan QA Indonesia.\n\n"
        "Gunakan /subscribe untuk mulai menerima notifikasi lowongan QA terbaru.\n"
        "Gunakan /help untuk melihat semua perintah."
    )

async def cmd_subscribe(update, context):
    uid = update.effective_user.id
    await db.upsert_user(uid, update.effective_user.username, update.effective_user.first_name)
    await db.set_subscribed(uid, True)
    await update.message.reply_text("✅ Kamu sudah berlangganan! Kamu akan dapat notifikasi saat ada lowongan QA baru.")

async def cmd_jobs(update, context):
    jobs = await db.get_recent_jobs(limit=10)
    if not jobs:
        await update.message.reply_text("Belum ada lowongan tersimpan. Coba lagi nanti.")
        return
    for job in jobs:
        await update.message.reply_text(format_job_alert(job), parse_mode="Markdown", disable_web_page_preview=True)

async def cmd_search(update, context):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Contoh: /search selenium jakarta")
        return
    jobs = await db.search_jobs(query, limit=5)
    for job in jobs:
        await update.message.reply_text(format_job_alert(job), parse_mode="Markdown", disable_web_page_preview=True)

async def cmd_preferences(update, context):
    keyboard = [
        [InlineKeyboardButton("🌐 Remote Only", callback_data="pref_work_remote"),
         InlineKeyboardButton("🏢 On-site", callback_data="pref_work_onsite")],
        [InlineKeyboardButton("🏠 Hybrid", callback_data="pref_work_hybrid"),
         InlineKeyboardButton("✅ Semua", callback_data="pref_work_any")],
        [InlineKeyboardButton("📅 Harian (08:00)", callback_data="pref_notif_daily"),
         InlineKeyboardButton("⚡ Langsung", callback_data="pref_notif_instant")],
    ]
    await update.message.reply_text("Pilih preferensi kamu:", reply_markup=InlineKeyboardMarkup(keyboard))

def setup_bot(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("subscribe",   cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("preferences", cmd_preferences))
    app.add_handler(CommandHandler("jobs",        cmd_jobs))
    app.add_handler(CommandHandler("search",      cmd_search))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("deletedata",  cmd_deletedata))
    app.add_handler(CallbackQueryHandler(cb_preferences, pattern="^pref_"))
    return app
```

---

## 10. Entry Point

```python
# main.py
import asyncio, logging
from config import settings
from database import init_db
from bot import setup_bot
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)

async def main():
    await init_db()
    app = setup_bot(settings.BOT_TOKEN)
    scheduler = setup_scheduler(app.bot)
    scheduler.start()

    logging.info("Bot started. Running in polling mode.")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Run forever
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 11. Configuration

```bash
# .env
BOT_TOKEN=123456:ABC-DEF...
ADMIN_TELEGRAM_ID=123456789

# Optional — bot works fine without these
ANTHROPIC_API_KEY=sk-ant-...   # enables AI summaries
PROXY_URL=http://user:pass@proxy.webshare.io:80  # for protected sites
```

```python
# config.py
from dataclasses import dataclass
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

---

## 12. Requirements

```
# requirements.txt
python-telegram-bot[job-queue]==21.*
httpx==0.27.*
aiosqlite==0.20.*
beautifulsoup4==4.12.*
lxml==5.*
feedparser==6.*
apscheduler==3.*
python-dotenv==1.*
playwright==1.*          # optional, for Indeed + Tech in Asia
anthropic==0.28.*        # optional, for AI summaries
```

Install:
```bash
pip install -r requirements.txt
playwright install chromium   # only if using Indeed/Tech in Asia scrapers
```

---

## 13. Running the Bot

```bash
# First run
git clone https://github.com/yourorg/qa-job-bot
cd qa-job-bot
cp .env.example .env
# Fill in BOT_TOKEN in .env

pip install -r requirements.txt
python main.py
```

To keep it running on a VPS using `systemd`:

```ini
# /etc/systemd/system/qajobbot.service
[Unit]
Description=QA Job Bot
After=network.target

[Service]
WorkingDirectory=/opt/qa-job-bot
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10
User=ubuntu
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable qajobbot
sudo systemctl start qajobbot
sudo journalctl -u qajobbot -f   # tail logs
```

Or with `tmux` / `screen` for a quick test:
```bash
tmux new -s bot
python main.py
# Ctrl+B, D to detach
```

---

## 14. Minimum Server Requirement

| Resource | Minimum |
|---|---|
| CPU | 1 vCPU |
| RAM | 512 MB (without Playwright) / 1 GB (with Playwright) |
| Disk | 2 GB |
| OS | Any Linux, Python 3.11+ |
| Estimated cost | ~$4/month (Hetzner CX11, Contabo, or even a Raspberry Pi 4) |

SQLite handles hundreds of concurrent reads fine in WAL mode. The bot will comfortably run on the smallest available VPS.

---

## 15. Scaling Notes (when needed later)

The single-process design handles thousands of subscribers easily. If you outgrow it:

- Swap `aiosqlite` for `asyncpg` + PostgreSQL with minimal code changes (all queries are in `database.py`)
- Split scrapers into separate processes using `multiprocessing` if scraping becomes slow
- Add a simple Redis pub/sub if you need multiple bot instances (unlikely until 50k+ subscribers)

There is intentionally no migration path to Docker in scope — keep it simple.
