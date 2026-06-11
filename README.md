# 🧪 QA Jobs ID Bot

A Telegram bot that automatically scrapes QA/testing job listings from multiple Indonesian and international job boards, enriches them with skill extraction and AI summaries, and dispatches matching jobs to subscribers via instant alerts and daily digest.

**Bot:** [@QAJobsID_bot](https://t.me/QAJobsID_bot)

## ✨ Features

- **Multi-source scraping** — 8 job sources (Indonesian + international)
- **Smart filtering** — QA-only jobs, Indonesia-relevant
- **Skill extraction** — Auto-detects Selenium, Cypress, Playwright, Postman, etc.
- **Experience level inference** — Entry / Mid / Senior from job descriptions
- **AI summaries** — Optional Claude API for human-readable summaries
- **Cross-source deduplication** — Same job from multiple sources = 1 alert
- **Instant alerts** — New QA jobs pushed to subscribers in real-time
- **Daily digest** — 08:00 WIB summary of past 24h jobs
- **User preferences** — Filter by work type (remote/onsite/hybrid) and experience level
- **Full-text search** — FTS5-powered search across all jobs
- **Admin dashboard** — Stats, error logs, broadcast, proxy management
- **Anti-detection** — UA rotation, per-domain rate limiting, proxy pool

## 📡 Job Sources

| Source | Method | Interval | Status |
|--------|--------|----------|--------|
| LinkedIn Jobs | Guest API + HTML | 15 min | ✅ Working |
| LinkedIn Posts | Brave Search | 30 min | ✅ Working |
| Glints | httpx + proxy + `__NEXT_DATA__` | 15 min | ⚠️ Needs proxies |
| Kalibrr | Playwright (JS-rendered) | 20 min | ✅ Working |
| JobStreet | Playwright + proxy | 20 min | ⚠️ Cloudflare blocks |
| Remote OK | JSON API | 60 min | ✅ Working |
| Remotive | JSON API | 60 min | ✅ Working |
| We Work Remotely | RSS feed | 60 min | ✅ Working |

## 🛠️ Tech Stack

- **Python 3.11** — Single async process
- **python-telegram-bot v21** — Telegram Bot API (polling mode)
- **SQLite + FTS5 + WAL** — Lightweight DB with full-text search
- **APScheduler** — Interval-based scraping
- **httpx** — Async HTTP client with proxy support
- **Playwright** — Headless browser for JS-rendered pages
- **BeautifulSoup + lxml** — HTML parsing
- **Claude API** (optional) — AI job summaries

## 🚀 Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Install

```bash
git clone https://github.com/aldimhr/qajobbot.git
cd qajobbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright browsers (for Kalibrr/JobStreet)
playwright install chromium
```

### Configure

Create `.env` file:

```env
TELEGRAM_BOT_KEY=your_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_id
ANTHROPIC_API_KEY=sk-ant-...  # optional, for AI summaries
```

### Run

```bash
python main.py
```

### Systemd Service (Linux)

```bash
sudo cp qajobbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qajobbot
```

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | 🤖 Mulai menggunakan bot |
| `/subscribe` | ✅ Berlangganan notifikasi |
| `/unsubscribe` | 🔕 Berhenti berlangganan |
| `/preferences` | ⚙️ Atur filter preferensi |
| `/jobs` | 📋 Lihat 10 lowongan terbaru |
| `/search <query>` | 🔍 Cari lowongan |
| `/help` | 📖 Daftar perintah |
| `/about` | ℹ️ Info tentang bot ini |
| `/deletedata` | 🗑️ Hapus data kamu |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Admin panel with inline keyboard |
| `/stats` | Bot statistics |
| `/errors` | Recent error log |
| `/broadcast <msg>` | Send message to all users |

## 📁 Project Structure

```
qajobbot/
├── main.py              # Entry point
├── bot.py               # Telegram bot handlers
├── config.py            # Settings from .env
├── constants.py         # QA keywords, patterns, search queries
├── database.py          # SQLite + FTS5 + dedup
├── models.py            # Data models
├── formatter.py         # Telegram message builder
├── dispatcher.py        # Job matching & delivery
├── scheduler.py         # APScheduler scraper orchestration
├── admin.py             # Admin panel & notifications
├── proxy_pool.py        # Auto-fetch & rotate free proxies
├── requirements.txt
├── scrapers/
│   ├── base.py          # Base scraper (rate limiting, UA rotation)
│   ├── linkedin.py      # LinkedIn Jobs (guest API)
│   ├── linkedin_posts.py # LinkedIn Posts (Brave Search)
│   ├── glints.py        # Glints (httpx + proxy)
│   ├── kalibrr.py       # Kalibrr (Playwright)
│   ├── jobstreet.py     # JobStreet (Playwright + proxy)
│   ├── remoteok.py      # Remote OK (JSON API)
│   ├── remotive.py      # Remotive (JSON API)
│   └── weworkremotely.py # WWR (RSS)
├── enrichment/
│   ├── keywords.py      # QA relevance & Indonesia filter
│   ├── skills.py        # Skill extraction
│   ├── level.py         # Experience level inference
│   ├── summarizer.py    # AI/Claude summary
│   └── post_parser.py   # LinkedIn post text extraction
└── plans/               # Implementation plans
```

## ⚙️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  8 Scrapers │────▶│  QA Filter   │────▶│  Enrichment   │
│  (interval) │     │  + ID Filter │     │  skills/level │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                                                  ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Telegram   │◀────│  Dispatcher  │◀────│   SQLite DB   │
│  Subscribers│     │  (5 min)     │     │   + FTS5      │
└─────────────┘     └──────────────┘     └───────────────┘
```

## 📝 License

MIT

## 🙋‍♂️ Author

**Dirikuin** — [aldimhr.dev](https://aldimhr.dev) · [GitHub](https://github.com/aldimhr)
