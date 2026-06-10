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
