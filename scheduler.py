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
