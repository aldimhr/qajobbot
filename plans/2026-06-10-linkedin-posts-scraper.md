# LinkedIn Posts Scraper — Job Announcements from Feed

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a scraper that finds QA job announcements from LinkedIn user/company posts (e.g. "We're hiring!", "Looking for QA Engineer"), not just the official Jobs section.

**Architecture:** New scraper class `LinkedInPostsScraper` that uses Playwright to search LinkedIn's content/posts search for QA-related hiring keywords. Parses post text for job details (title, company, location) using regex/heuristics since posts are unstructured. Stores as jobs with `source='linkedin_posts'`.

**Tech Stack:** Playwright (already installed), existing scraper base class, existing enrichment pipeline.

---

## Context

### Why this matters
Many Indonesian recruiters and companies post job openings directly on their LinkedIn feed rather than (or in addition to) creating formal job listings. These posts often:
- Get more engagement than formal listings
- Include direct contact info (DM, WhatsApp, email)
- Are posted earlier than the formal listing
- Include insider info about team/role

### Current state
- `scrapers/linkedin.py` scrapes `linkedin.com/jobs/search` — official job board only
- `source='linkedin'` in database
- Playwright is already installed and working

### Challenge
LinkedIn posts are unstructured text. A post might say:
- "Tim QA kami butuh 2 orang, DM me!"
- "Hiring: Senior QA Engineer at Tokopedia. Apply here: [link]"
- "My company is looking for a test automation engineer..."

We need to extract structured data (title, company, location, URL) from free-form text.

---

## Tasks

### Task 1: Create LinkedIn Posts Scraper

**Objective:** New scraper that searches LinkedIn content/posts for QA hiring keywords

**Files:**
- Create: `scrapers/linkedin_posts.py`

**Approach:**
- Use Playwright to navigate to LinkedIn's post search: `https://www.linkedin.com/search/results/content/?keywords=qa+hiring+indonesia&origin=SWITCH_SEARCH_VERTICAL`
- LinkedIn guest search for posts is accessible without login (limited results but works)
- Parse post cards: extract author (company/person name), post text, post URL, timestamp
- Filter posts that contain QA-related keywords AND hiring signals
- Extract job details from post text using patterns

**Search queries to rotate:**
```
"qa engineer hiring"
"qa engineer indonesia"  
"test engineer hiring"
"quality assurance hiring"
"qa automation hiring"
"selenium hiring"
"tester hiring indonesia"
"lowongan qa"
"lowongan tester"
"dicari qa"
"mencari qa engineer"
```

**Post parsing heuristics:**
```python
# Extract company from post author name
# Extract job title from post text patterns:
#   - "Hiring: {title}"
#   - "Looking for {title}"
#   - "Mencari {title}"
#   - "{title} position"
#   - "Kami butuh {title}"
# Extract location from text:
#   - "Jakarta", "Bandung", "Remote", "WFH", etc.
# Extract apply link from post:
#   - URLs in post text
#   - "Apply here:", "Link:", "bit.ly/..."
```

**Verification:**
```bash
cd /opt/hermes/qajobbot && source venv/bin/activate
python3 -c "
import asyncio
from scrapers.linkedin_posts import LinkedInPostsScraper
from database import Database
async def test():
    db = Database()
    s = LinkedInPostsScraper(db)
    jobs = await s.scrape()
    print(f'Found {len(jobs)} jobs from LinkedIn posts')
    for j in jobs[:5]:
        print(f'  {j.title} @ {j.company} ({j.source_url})')
asyncio.run(test())
"
```

### Task 2: Add Post Keyword Patterns

**Objective:** Define Indonesian + English hiring signal patterns for post classification

**Files:**
- Modify: `constants.py`

**Add constants:**
```python
HIRING_SIGNALS_ID = [
    "dicari", "mencari", "butuh", "dibutuhkan", "kami butuh",
    "lowongan", "loker", "hiring", "recruiting", "we're hiring",
    "looking for", "cari", "sedang cari", "rekrut", "open position",
    "info loker", "info lowongan", "join our team", "join my team",
]

HIRING_SIGNALS_EN = [
    "hiring", "we're hiring", "looking for", "seeking",
    "open position", "job opening", "join our team",
    "now hiring", "is hiring", "are hiring",
]

# Minimum QA relevance score for a post to be considered
POST_QA_RELEVANCE_THRESHOLD = 2  # must match at least 2 QA keywords
```

### Task 3: Add Post Text Parser Utility

**Objective:** Extract structured job data from unstructured post text

**Files:**
- Create: `enrichment/post_parser.py`

**Functions:**
```python
def extract_job_title(text: str) -> str | None:
    """Extract job title from post text using patterns."""
    # Pattern: "Hiring: {title}", "Looking for {title}", etc.
    # Returns best guess or None

def extract_company(text: str, author: str) -> str:
    """Extract company name — prefer author name, fallback to text patterns."""

def extract_location(text: str) -> str | None:
    """Extract location from post text."""
    # Look for Indonesian cities, "Remote", "WFH", "WFO", "Hybrid"

def extract_apply_url(text: str) -> str | None:
    """Extract application URL from post text."""
    # Look for URLs after "apply", "link", "daftar", "lamar"

def is_qa_relevant(text: str) -> bool:
    """Check if post is about QA/testing jobs."""
    # Count QA keyword matches, return True if >= POST_QA_RELEVANCE_THRESHOLD

def score_post(text: str) -> float:
    """Score 0-1 how relevant a post is for QA jobs."""
    # Higher score = more confident it's a QA job post
```

### Task 4: Register Scraper in Scheduler

**Objective:** Add LinkedIn posts scraper to the periodic scrape schedule

**Files:**
- Modify: `scheduler.py`

**Changes:**
- Import `LinkedInPostsScraper`
- Add schedule: every 30 minutes (posts are less time-sensitive than formal listings)
- Add to scraper list

### Task 5: Update Source Constants

**Objective:** Register `linkedin_posts` as a valid source

**Files:**
- Modify: `constants.py` — add `"linkedin_posts"` to SOURCES
- Modify: `config.py` — add `SCRAPE_INTERVAL_LINKEDIN_POSTS = 1800`

### Task 6: Test & Deploy

**Objective:** Verify scraper finds real posts, restart service

**Steps:**
1. Run scraper manually, check output
2. Verify posts are stored in DB with `source='linkedin_posts'`
3. Restart service: `sudo systemctl restart qajobbot`
4. Wait for first scheduled run, check logs

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LinkedIn blocks post search without login | Use Playwright with stealth; fallback to Google `site:linkedin.com/posts/` search |
| Posts are noisy — many non-job posts | Strict keyword filtering + relevance scoring |
| Post text parsing is unreliable | Store raw text, mark confidence score, let users see full post |
| Rate limiting from LinkedIn | Rotate search queries, 30min interval, random delays |
| Duplicate posts from same recruiter | Dedup by post URL |

## Fallback: Google Search for LinkedIn Posts

If LinkedIn's own search blocks us, use Google:
```
site:linkedin.com/posts "qa engineer" hiring indonesia
site:linkedin.com/posts "tester" hiring
```
Parse Google results → visit each LinkedIn post URL → extract content.

---

## Files Changed Summary
- `scrapers/linkedin_posts.py` — NEW: main scraper
- `enrichment/post_parser.py` — NEW: text parsing utilities
- `constants.py` — MODIFIED: add hiring signals, source
- `config.py` — MODIFIED: add scrape interval
- `scheduler.py` — MODIFIED: register new scraper
