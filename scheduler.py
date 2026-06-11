import time
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from enrichment import is_qa_job, is_indonesia_relevant, extract_skills, infer_level, summarize
import database as db
from dispatcher import dispatch_new_jobs, send_daily_digest
from admin import notify_scraper_error, notify_scraper_warning
from proxy_pool import proxy_pool
from scrapers.remoteok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.weworkremotely import WWRScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.linkedin_posts import LinkedInPostsScraper
from scrapers.glints import GlintsScraper
from scrapers.kalibrr import KalibrrScraper
from scrapers.jobstreet import JobStreetScraper

logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))

# ── Scraper definitions (name → (scraper_factory, interval_minutes)) ──
SCRAPER_DEFS: dict[str, tuple] = {}
_SCRAPER_FACTORIES = {
    "remoteok": (lambda: RemoteOKScraper(), 60),
    "remotive": (lambda: RemotiveScraper(), 60),
    "weworkremotely": (lambda: WWRScraper(), 60),
    "linkedin": (lambda: LinkedInScraper(), 15),
    "linkedin_posts": (lambda: LinkedInPostsScraper(), 30),
    "glints": (lambda: GlintsScraper(), 15),
    "kalibrr": (lambda: KalibrrScraper(), 20),
    "jobstreet": (lambda: JobStreetScraper(), 20),
}

# Track consecutive errors per source for alerting
_error_counts: dict[str, int] = {}

# ── Live scraper state (updated in run_scraper) ──
_scraper_state: dict[str, dict] = {}
_scheduler_ref: AsyncIOScheduler | None = None


def _get_state(source: str) -> dict:
    if source not in _scraper_state:
        _scraper_state[source] = {
            "is_running": False,
            "last_run": None,      # ISO string
            "last_duration": None,  # seconds
            "last_result": None,   # "ok" | "error"
            "last_scraped": 0,
            "last_saved": 0,
            "last_error": None,
            "consecutive_errors": 0,
        }
    return _scraper_state[source]


async def run_scraper(scraper, source_name: str, bot: Bot = None):
    """Run a single scraper, filter, enrich, and save jobs."""
    state = _get_state(source_name)
    state["is_running"] = True
    start = time.monotonic()

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
            if not isinstance(job.get("skills"), list) or not job["skills"]:
                job["skills"] = extract_skills(desc)
            if isinstance(job.get("skills"), str):
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

        # Update state
        state["last_result"] = "ok"
        state["last_scraped"] = len(raw_jobs)
        state["last_saved"] = saved
        state["last_error"] = None
        state["consecutive_errors"] = 0
        _error_counts[source_name] = 0

        await scraper.close()
    except Exception as e:
        logger.error(f"[{source_name}] scraper error: {e}")
        _error_counts[source_name] = _error_counts.get(source_name, 0) + 1

        state["last_result"] = "error"
        state["last_error"] = str(e)[:200]
        state["consecutive_errors"] = _error_counts[source_name]
        state["last_scraped"] = 0
        state["last_saved"] = 0

        # Notify admin on first error or every 3rd consecutive error
        if bot and (_error_counts[source_name] == 1 or _error_counts[source_name] % 3 == 0):
            await notify_scraper_error(
                bot, source_name,
                f"{e}\n(Consecutive errors: {_error_counts[source_name]})"
            )
    finally:
        state["is_running"] = False
        state["last_run"] = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
        state["last_duration"] = round(time.monotonic() - start, 1)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _scheduler_ref
    sched = AsyncIOScheduler(timezone="Asia/Jakarta")
    _scheduler_ref = sched

    # Scrapers — each gets its own job
    scrapers = [
        (RemoteOKScraper(), "remoteok", 60),
        (RemotiveScraper(), "remotive", 60),
        (WWRScraper(), "weworkremotely", 60),
        (LinkedInScraper(), "linkedin", 15),
        (LinkedInPostsScraper(), "linkedin_posts", 30),
        (GlintsScraper(), "glints", 15),
        (KalibrrScraper(), "kalibrr", 20),
        (JobStreetScraper(), "jobstreet", 20),
    ]

    for scraper, name, minutes in scrapers:
        sched.add_job(
            run_scraper, "interval", minutes=minutes,
            args=[scraper, name, bot], id=f"scraper_{name}",
            max_instances=1, coalesce=True,
        )
        # Initialize state with interval info
        _get_state(name)["interval_minutes"] = minutes

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

    # Refresh proxy pool every 2 hours
    sched.add_job(
        proxy_pool.refresh, "interval", hours=2,
        id="proxy_refresh",
    )

    # Cleanup old jobs at 02:00
    sched.add_job(
        db.purge_old_jobs, "cron", hour=2, minute=0,
        id="cleanup",
    )

    return sched


def get_scraper_status() -> dict:
    """Return full scraper status dict (for admin views)."""
    result = {}
    for name in _SCRAPER_FACTORIES:
        state = _get_state(name)
        entry = dict(state)
        # Compute next_run from scheduler if available
        if _scheduler_ref:
            job = _scheduler_ref.get_job(f"scraper_{name}")
            if job and job.next_run_time:
                entry["next_run"] = job.next_run_time.astimezone(WIB).strftime(
                    "%Y-%m-%d %H:%M:%S WIB"
                )
            else:
                entry["next_run"] = None
        result[name] = entry
    return result


async def trigger_scraper_now(source_name: str, bot: Bot) -> str:
    """Manually trigger a scraper. Returns status message."""
    if source_name not in _SCRAPER_FACTORIES:
        return f"❌ Unknown source: {source_name}"

    state = _get_state(source_name)
    if state["is_running"]:
        return f"⏳ {source_name} is already running, please wait."

    factory, _ = _SCRAPER_FACTORIES[source_name]
    scraper = factory()
    await run_scraper(scraper, source_name, bot)

    s = _get_state(source_name)
    if s["last_result"] == "ok":
        return (
            f"✅ {source_name} done!\n"
            f"Scraped: {s['last_scraped']} | Saved: {s['last_saved']}\n"
            f"Duration: {s['last_duration']}s"
        )
    else:
        return f"❌ {source_name} failed: {s['last_error']}"
