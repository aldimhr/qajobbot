"""Admin notifications and dashboard helpers."""
import logging
from telegram import Bot
from config import settings
import database as db

logger = logging.getLogger(__name__)


async def notify_admin(bot: Bot, message: str, level: str = "info"):
    """Send a notification to the admin via Telegram."""
    if not settings.ADMIN_TELEGRAM_ID:
        return

    emoji = {"error": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
    text = f"{emoji} *Admin Notification*\n\n{message}"

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_TELEGRAM_ID,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")


async def notify_scraper_error(bot: Bot, source: str, error: str):
    """Log error to DB and notify admin."""
    await db.log_error(source, "error", error)
    await notify_admin(bot, f"*Scraper Error* [{source}]\n{error[:500]}", "error")


async def notify_scraper_warning(bot: Bot, source: str, warning: str):
    """Log warning to DB and notify admin."""
    await db.log_error(source, "warning", warning)
    await notify_admin(bot, f"*Scraper Warning* [{source}]\n{warning[:500]}", "warning")


def is_admin(user_id: int) -> bool:
    """Check if user is the admin."""
    return settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID


def format_stats(stats: dict) -> str:
    """Format stats dict into a readable admin message."""
    lines = ["📊 *QA Job Bot — Dashboard*\n"]

    lines.append(f"📦 *Jobs:* {stats['total_jobs']} total ({stats['jobs_24h']} in 24h)")
    lines.append(f"👥 *Users:* {stats['total_users']} ({stats['subscribers']} subscribed)")
    lines.append(f"📨 *Sent:* {stats['total_sent']} alerts")
    lines.append(f"❌ *Errors:* {stats['total_errors']} ({stats['errors_24h']} in 24h)")

    if stats.get("jobs_by_source"):
        lines.append("\n📂 *Jobs by Source:*")
        for source, count in stats["jobs_by_source"].items():
            lines.append(f"  • {source}: {count}")

    if stats.get("latest_job"):
        j = stats["latest_job"]
        lines.append(f"\n🕐 *Latest Job:* {j['title']} @ {j['company']}")
        lines.append(f"  Scraped: {j['time']}")

    return "\n".join(lines)


def format_errors(errors: list[dict]) -> str:
    """Format error list into a readable message."""
    if not errors:
        return "✅ No errors logged."

    lines = [f"🚨 *Recent Errors* ({len(errors)}):\n"]
    for e in errors[:10]:
        level_emoji = "🚨" if e["level"] == "error" else "⚠️"
        lines.append(f"{level_emoji} [{e['source']}] {e['message'][:100]}")
        lines.append(f"  📅 {e['created_at']}")
        lines.append("")

    return "\n".join(lines)
