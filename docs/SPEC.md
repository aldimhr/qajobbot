# QA Job Bot — Product Specification

## 1. Overview

**Product Name:** QA Job Bot (`@QAJobsID_bot`)
**Platform:** Telegram (Bot API)
**Purpose:** Automatically scrape and broadcast Indonesian-relevant Software QA / Quality Assurance job openings to subscribed users, in near real-time.
**Philosophy:** Single-process, run-it-anywhere. No Docker, no heavy infra. Just Python + SQLite on any VPS or even a Raspberry Pi.

---

## 2. Goals & Non-Goals

### Goals
- Monitor multiple job boards continuously for new QA-related postings
- Deliver job alerts to subscribed Telegram users and group chats
- Filter to Indonesia-based positions OR remote positions open to Indonesian applicants
- Deduplicate jobs so the same listing is never sent twice
- Allow users to configure preferences (role keywords, experience level, work type)
- Provide a searchable history of recent jobs via bot commands
- Run as a single Python process with zero external services

### Non-Goals
- Full-featured ATS or application tracker
- Resume/CV storage or submission
- Non-QA job categories
- Real-time chat with recruiters
- Monitoring dashboards or metrics pipelines
- Containerization or orchestration

---

## 3. Target Users

| Persona | Description |
|---|---|
| Job seeker | Indonesian QA engineer actively looking for work |
| Passive browser | Employed QA professional monitoring the market |
| Group admin | Runs a QA/tech community Telegram group and wants auto job feed |

---

## 4. Job Keyword Taxonomy

The bot matches jobs whose **title or description** contains any of the following (case-insensitive):

### Primary Titles
- Quality Assurance Engineer / QA Engineer
- Software Tester / Software QA
- QA Analyst / Quality Analyst
- Test Engineer / Test Automation Engineer
- SDET (Software Development Engineer in Test)
- QA Lead / QA Manager / Quality Lead
- Automation Engineer (in QA context)
- Performance Tester / Load Tester
- Mobile Tester / Web Tester
- Game Tester / Game QA
- Manual Tester / Manual QA

### Indonesian Equivalents
- Penguji Perangkat Lunak
- Analis Kualitas
- Insinyur QA / Insinyur Pengujian
- Staf QA / Tim QA

### Exclusion Keywords (reduce false positives)
- "Supplier Quality" (manufacturing, not software)
- "Food Quality" / "Quality Control Food"
- "ISO Auditor" (unless paired with software context)

---

## 5. Location Filter Rules

A job is included if **any** of the following are true:

1. **Location field** contains Indonesia or an Indonesian city (Jakarta, Bandung, Surabaya, Yogyakarta, Bali, Medan, Makassar, Semarang, Bekasi, Tangerang, Depok, etc.)
2. **Work type** is `Remote` AND the posting does NOT explicitly restrict to a non-Indonesian country (e.g. "US only", "must be in EU")
3. **Work type** is `Hybrid` and location is in Indonesia
4. **Salary currency** is IDR — strong signal of an Indonesian role

---

## 6. Bot Features

### 6.1 User Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + subscription prompt |
| `/subscribe` | Subscribe to new job alerts |
| `/unsubscribe` | Stop receiving alerts |
| `/preferences` | Configure filters via inline keyboard |
| `/jobs` | Browse last 20 jobs (paginated) |
| `/search <query>` | Search the job database |
| `/help` | Show command list |
| `/about` | Bot info and data sources |

### 6.2 Preference Filters (per user)

- **Experience level:** Any / Junior (0–2 yr) / Mid (2–5 yr) / Senior (5+ yr)
- **Work type:** Any / Remote only / On-site only / Hybrid
- **Job type:** Any / Full-time / Part-time / Contract / Freelance / Internship
- **Notification frequency:** Instant / Daily digest (08:00 WIB) / Weekly (Monday 08:00 WIB)

### 6.3 Job Alert Message Format

```
🧪 *QA Engineer — PT. Tokopedia*

📍 Jakarta, Indonesia (Hybrid)
💼 Full-time · Mid-level
💰 IDR 8,000,000 – 12,000,000 / month

📝 Bertanggung jawab melakukan pengujian manual dan otomatis
   pada alur checkout dan sistem pembayaran...

🔧 *Skills:* Selenium, Postman, JIRA, SQL

🔗 [Lamar Sekarang](https://...)
📅 Diposting: 2 jam lalu · Sumber: LinkedIn
```

### 6.4 Daily Digest Format

Sent as a single message at 08:00 WIB with up to 10 new jobs, one-liner per job, with apply links.

### 6.5 Group Chat Mode

When added to a group, the bot broadcasts all jobs matching default filters. Group admins can run `/preferences` to configure group-wide filters. Individual users in the group are not tracked.

---

## 7. Data Model (SQLite)

### jobs table
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `external_id` | TEXT | Source-specific ID |
| `source` | TEXT | linkedin, glints, kalibrr, etc. |
| `source_url` | TEXT | Original job URL |
| `title` | TEXT | Raw title |
| `company_name` | TEXT | |
| `location` | TEXT | Raw location string |
| `is_remote` | INTEGER | 0/1 |
| `is_hybrid` | INTEGER | 0/1 |
| `work_type` | TEXT | full-time, contract, etc. |
| `experience_level` | TEXT | entry, mid, senior, lead |
| `salary_min` | INTEGER | IDR |
| `salary_max` | INTEGER | IDR |
| `description_summary` | TEXT | Short plain-text summary |
| `skills` | TEXT | Comma-separated skill tags |
| `posted_at` | TEXT | ISO timestamp |
| `scraped_at` | TEXT | ISO timestamp |
| `is_active` | INTEGER | 1 = active |
| UNIQUE | `(source, external_id)` | Dedup key |

### users table
| Field | Type |
|---|---|
| `telegram_id` | INTEGER PK |
| `username` | TEXT |
| `first_name` | TEXT |
| `is_subscribed` | INTEGER |
| `notification_mode` | TEXT |
| `preferences` | TEXT (JSON) |
| `subscribed_at` | TEXT |
| `last_active_at` | TEXT |

### sent_jobs table
| Field | Type |
|---|---|
| `user_id` | INTEGER |
| `job_id` | INTEGER |
| `sent_at` | TEXT |
| PRIMARY KEY | `(user_id, job_id)` |

---

## 8. Scraping Cadence

| Source | Method | Frequency |
|---|---|---|
| LinkedIn | RSS + HTML | Every 15 min |
| Glints | JSON API | Every 15 min |
| Kalibrr | JSON API | Every 20 min |
| JobStreet | JSON API | Every 20 min |
| Indeed Indonesia | HTML scrape | Every 30 min |
| Tech in Asia Jobs | HTML scrape | Every 30 min |
| Loker.id | HTML scrape | Every 30 min |
| Topkarir | HTML scrape | Every 30 min |
| Ekrut | HTML scrape | Every 30 min |
| We Work Remotely | RSS | Every 60 min |
| Remotive.io | JSON API | Every 60 min |
| Remote OK | JSON API | Every 60 min |

---

## 9. Anti-Detection & Ethical Scraping

- Respect `robots.txt` where applicable
- Rotate User-Agent strings from a pool
- Randomize delays between requests (2–8 seconds)
- Set `Accept-Language: id-ID` headers
- Max 1 request per 3 seconds per domain
- Exponential backoff on 429/503 responses

---

## 10. Enrichment Pipeline

Each new job is processed before storage:

1. **Title normalization** — Map raw title to canonical QA role category
2. **Experience level inference** — Parse from years/keywords in description
3. **Skills extraction** — Regex-based detection of tech stack (Selenium, Cypress, Postman, etc.)
4. **Description summarization** — Generate a 2-sentence summary (regex + truncation; optional Claude API if key is set)
5. **Remote eligibility check** — Confirm remote applies to Indonesian applicants

AI enrichment via Claude API is **optional** — the bot works fully without it.

---

## 11. Notification Logic

```
FOR each new job scraped:
  IF job passes location filter:
    store in SQLite (skip if duplicate)
    FOR each subscribed user:
      IF job matches user preferences:
        IF (user_id, job_id) NOT in sent_jobs:
          IF user.notification_mode == instant:
            send immediately via Telegram
          ELSE:
            add to in-memory digest queue
```

---

## 12. Error Handling

- Scraper failure → log to `bot.log`, skip source, retry next cycle
- Telegram rate limit → sleep + retry with backoff, no message lost
- Enrichment failure → store job with raw data, skip summary
- SQLite locked → retry with 3-second wait (WAL mode enabled)

---

## 13. Privacy & Compliance

- Only Telegram user ID and first name stored
- Users can `/deletedata` to remove their record
- Scraped job data purged after 90 days (nightly cleanup job)
- No data sold or shared
- Complies with Telegram Bot ToS

---

## 14. Out-of-Scope (Future)

- CV/resume upload and auto-match
- Salary benchmarking
- WhatsApp / Discord versions
- Recruiter-side posting
