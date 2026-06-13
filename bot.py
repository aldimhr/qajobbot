import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from telegram.constants import ParseMode
import database as db
from formatter import format_job_alert, format_digest
from formatter import format_jobs_page
from admin import is_admin, format_stats, format_errors, format_scraper_status
from constants import SKILL_PATTERNS

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(
        "👋 Hey there! I'm the QA Job Alert Bot.\n\n"
        "Use /subscribe to start receiving QA job alerts.\n"
        "Use /help to see all available commands."
    )


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.first_name or "")
    await db.set_subscribed(user.id, True)
    await update.message.reply_text(
        "✅ You're subscribed! You'll get notified when new QA jobs drop.\n\n"
        "Use /preferences to set your filters."
    )


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.set_subscribed(user.id, False)
    await update.message.reply_text(
        "🔕 You've unsubscribed. Use /subscribe to start again."
    )


PAGE_SIZE = 5


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs, total = await db.get_recent_jobs_page(offset=0, limit=PAGE_SIZE)
    if not jobs:
        await update.message.reply_text("📭 No jobs saved yet. Check back later.")
        return
    text = format_jobs_page(jobs, 0, total)
    keyboard = _build_page_keyboard("jobs", "", 0, total)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args or [])
    if not query:
        await update.message.reply_text("🔍 Usage: /search selenium jakarta")
        return
    jobs, total = await db.search_jobs_page(query, offset=0, limit=PAGE_SIZE)
    if not jobs:
        await update.message.reply_text(f"🔍 No jobs found for: {query}")
        return
    text = f"🔍 *Results for:* {query}\n\n" + format_jobs_page(jobs, 0, total)
    keyboard = _build_page_keyboard("search", query, 0, total)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


async def cmd_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🌐 Remote Only", callback_data="pref_work_remote"),
            InlineKeyboardButton("🏢 On-site", callback_data="pref_work_onsite"),
        ],
        [
            InlineKeyboardButton("🏠 Hybrid", callback_data="pref_work_hybrid"),
            InlineKeyboardButton("✅ All", callback_data="pref_work_any"),
        ],
        [
            InlineKeyboardButton("🟢 Entry", callback_data="pref_level_entry"),
            InlineKeyboardButton("🟡 Mid", callback_data="pref_level_mid"),
        ],
        [
            InlineKeyboardButton("🔴 Senior", callback_data="pref_level_senior"),
            InlineKeyboardButton("✅ Any Level", callback_data="pref_level_any"),
        ],
        [
            InlineKeyboardButton("⚡ Instant", callback_data="pref_notif_instant"),
            InlineKeyboardButton("📅 Daily (08:00)", callback_data="pref_notif_daily"),
        ],
    ]
    await update.message.reply_text(
        "⚙️ Set your preferences:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cb_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    user = await db.get_user(user_id)
    prefs = json.loads(user.get("preferences", "{}")) if user else {}

    if data.startswith("pref_work_"):
        work_type = data.replace("pref_work_", "")
        prefs["work_type"] = work_type
        await db.update_user_preferences(user_id, prefs)
        labels = {
            "remote": "🌐 Remote Only",
            "onsite": "🏢 On-site",
            "hybrid": "🏠 Hybrid",
            "any": "✅ All",
        }
        await query.edit_message_text(
            f"✅ Work type updated: {labels.get(work_type, work_type)}"
        )

    elif data.startswith("pref_notif_"):
        mode = data.replace("pref_notif_", "")
        prefs["notification_mode"] = mode
        await db.update_user_preferences(user_id, prefs)
        labels = {"instant": "⚡ Instant", "daily": "📅 Daily (08:00 WIB)"}
        await query.edit_message_text(f"✅ Notification mode: {labels.get(mode, mode)}")

    elif data.startswith("pref_level_"):
        level = data.replace("pref_level_", "")
        prefs["experience_level"] = level
        await db.update_user_preferences(user_id, prefs)
        labels = {
            "entry": "🟢 Entry",
            "mid": "🟡 Mid",
            "senior": "🔴 Senior",
            "any": "✅ Any Level",
        }
        await query.edit_message_text(
            f"✅ Experience level: {labels.get(level, level)}"
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Available Commands:*\n\n"
        "/start — Get started\n"
        "/subscribe — Subscribe to job alerts\n"
        "/unsubscribe — Stop receiving alerts\n"
        "/preferences — Set your filters\n"
        "/skills — Set skill-based filters\n"
        "/jobs — View 10 latest jobs\n"
        "/search <query> — Search jobs\n"
        "/deletedata — Delete your data\n"
        "/help — Show this message\n"
        "/about — About this bot"
    )
    if is_admin(update.effective_user.id):
        text += (
            "\n\n🔧 *Admin Commands:*"
            "\n/admin — Admin panel"
            "\n/stats — Bot statistics"
            "\n/errors — Recent errors"
            "\n/scrapestatus — Scraper status & run now"
            "\n/broadcast <msg> — Send to all subscribers"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧪 *QA Job Alert Bot*\n\n"
        "I monitor QA/Testing jobs from top job boards in Indonesia "
        "and send alerts straight to your Telegram.\n\n"
        "*Data sources:*\n"
        "• LinkedIn (RSS)\n"
        "• Glints\n"
        "• Kalibrr\n"
        "• JobStreet\n"
        "• Remote OK\n"
        "• Remotive\n"
        "• We Work Remotely\n\n"
        "Made with ❤️ for the Indonesian QA community.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set skill-based filters for job alerts."""
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    prefs = json.loads(user.get("preferences", "{}")) if user else {}
    current_skills = prefs.get("preferred_skills", [])

    if not context.args:
        if current_skills:
            skill_list = ", ".join(current_skills)
            text = (
                f"🎯 *Your skill filters:* {skill_list}\n\n"
                "Usage: /skills selenium,playwright,cypress\n"
                "Send /skills clear to remove all filters."
            )
        else:
            text = (
                "🎯 *No skill filters set.* You'll receive all QA jobs.\n\n"
                "Usage: /skills selenium,playwright,cypress\n"
                f"Available: {', '.join(sorted(SKILL_PATTERNS.keys()))}"
            )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    raw = " ".join(context.args)
    if raw.lower() == "clear":
        prefs["preferred_skills"] = []
        await db.update_user_preferences(user_id, prefs)
        await update.message.reply_text("🗑️ Skill filters cleared. You'll receive all QA jobs.")
        return

    requested = [s.strip().lower() for s in raw.split(",") if s.strip()]
    known = set(SKILL_PATTERNS.keys())
    unknown = [s for s in requested if s not in known]
    valid = [s for s in requested if s in known]
    if not valid:
        await update.message.reply_text(
            f"❌ None of those match known skills.\n\n"
            f"Available: {', '.join(sorted(known))}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    prefs["preferred_skills"] = valid
    await db.update_user_preferences(user_id, prefs)

    msg = f"✅ Skill filters updated: *{', '.join(valid)}*"
    if unknown:
        msg += f"\n⚠️ Skipped unknown: {', '.join(unknown)}"
    msg += "\n\nYou'll only receive jobs matching at least one of these skills."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_deletedata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await db.delete_user(user_id)
    await update.message.reply_text(
        "🗑️ Your data has been deleted. Use /start to begin again."
    )


# ─── Admin Commands ───────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("🚨 Errors", callback_data="admin_errors"),
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("📂 Sources", callback_data="admin_sources"),
        ],
        [
            InlineKeyboardButton("🔍 Scrape Status", callback_data="admin_scrape_status"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Proxies", callback_data="admin_refresh_proxy"),
            InlineKeyboardButton("🗑 Clear Errors", callback_data="admin_clear_errors"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        ],
    ]
    await update.message.reply_text(
        "🔧 *Admin Panel*\n\nChoose an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    stats = await db.get_stats()
    await update.message.reply_text(
        format_stats(stats), parse_mode=ParseMode.MARKDOWN
    )


async def cmd_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    errors = await db.get_recent_errors(10)
    await update.message.reply_text(
        format_errors(errors), parse_mode=ParseMode.MARKDOWN
    )


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    subscribers = await db.get_subscribers()
    sent = 0
    failed = 0
    for user in subscribers:
        try:
            await context.bot.send_message(
                chat_id=user["telegram_id"],
                text=f"📢 *Admin Broadcast*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN,
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {user['telegram_id']}: {e}")

    await update.message.reply_text(
        f"📢 Broadcast complete: {sent} sent, {failed} failed"
    )


async def cmd_scrapestatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    from scheduler import get_scraper_status
    status = get_scraper_status()
    keyboard = _build_run_now_keyboard(status)
    await update.message.reply_text(
        format_scraper_status(status),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )



def _build_page_keyboard(kind: str, query: str, offset: int, total: int) -> list:
    """Build pagination keyboard for /jobs and /search results."""
    buttons = []
    if offset > 0:
        prev_off = max(0, offset - PAGE_SIZE)
        buttons.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"pg_{kind}:{prev_off}:{query[:20]}")
        )
    if offset + PAGE_SIZE < total:
        next_off = offset + PAGE_SIZE
        buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"pg_{kind}:{next_off}:{query[:20]}")
        )
    return [buttons] if buttons else []


async def cb_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination callbacks for /jobs and /search."""
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g. "pg_jobs:5:" or "pg_search:10:selenium"

    parts = data.split(":", 2)
    kind = parts[0].replace("pg_", "")
    offset = int(parts[1])
    search_term = parts[2] if len(parts) > 2 else ""

    if kind == "jobs":
        jobs, total = await db.get_recent_jobs_page(offset=offset, limit=PAGE_SIZE)
        text = format_jobs_page(jobs, offset, total)
        keyboard = _build_page_keyboard("jobs", "", offset, total)
    elif kind == "search" and search_term:
        jobs, total = await db.search_jobs_page(search_term, offset=offset, limit=PAGE_SIZE)
        text = f"🔍 *Results for:* {search_term}\n\n" + format_jobs_page(jobs, offset, total)
        keyboard = _build_page_keyboard("search", search_term, offset, total)
    else:
        await query.edit_message_text("❌ Invalid page request.")
        return

    if not jobs:
        await query.edit_message_text("📭 No jobs on this page.")
        return

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


def _build_run_now_keyboard(scraper_status: dict = None) -> list:
    """Build inline keyboard with 'Run Now' or 'Enable' buttons per source."""
    sources = ["linkedin", "glints", "kalibrr", "jobstreet",
               "linkedin_posts", "remoteok", "remotive", "weworkremotely"]
    row = []
    keyboard = []
    for src in sources:
        is_disabled = (scraper_status or {}).get(src, {}).get("is_disabled", False)
        if is_disabled:
            row.append(InlineKeyboardButton(f"🔴 Enable {src}", callback_data=f"admin_enable_{src}"))
        else:
            row.append(InlineKeyboardButton(f"▶️ {src}", callback_data=f"admin_run_{src}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_scrape_status")])
    return keyboard


async def cb_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Not authorized")
        return

    await query.answer()
    data = query.data

    if data == "admin_stats":
        stats = await db.get_stats()
        await query.edit_message_text(
            format_stats(stats), parse_mode=ParseMode.MARKDOWN
        )

    elif data == "admin_errors":
        errors = await db.get_recent_errors(10)
        await query.edit_message_text(
            format_errors(errors), parse_mode=ParseMode.MARKDOWN
        )

    elif data == "admin_users":
        subscribers = await db.get_subscribers()
        users_text = f"👥 *Subscribers:* {len(subscribers)}\n\n"
        for u in subscribers[:20]:
            name = u.get("first_name", "") or u.get("username", "")
            mode = u.get("notification_mode", "instant")
            users_text += f"• {name} ({u['telegram_id']}) — {mode}\n"
        await query.edit_message_text(
            users_text, parse_mode=ParseMode.MARKDOWN
        )

    elif data == "admin_sources":
        stats = await db.get_stats()
        sources = stats.get("jobs_by_source", {})
        text = "📂 *Jobs by Source:*\n\n"
        for src, cnt in sources.items():
            text += f"• {src}: {cnt}\n"
        if not sources:
            text += "No jobs yet."
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_refresh_proxy":
        from proxy_pool import proxy_pool
        await query.edit_message_text("🔄 Refreshing proxy pool...")
        await proxy_pool.refresh()
        await query.edit_message_text(
            f"✅ Proxy pool refreshed: {proxy_pool.count} proxies"
        )

    elif data == "admin_clear_errors":
        await db.clear_errors()
        await query.edit_message_text("🗑 Error log cleared.")

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 Use /broadcast <message> to send to all subscribers."
        )

    elif data == "admin_scrape_status":
        from scheduler import get_scraper_status
        status = get_scraper_status()
        keyboard = _build_run_now_keyboard(status)
        await query.edit_message_text(
            format_scraper_status(status),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("admin_run_"):
        source_name = data.replace("admin_run_", "")
        from scheduler import trigger_scraper_now
        await query.edit_message_text(f"🔄 Running *{source_name}* scraper now...",
                                      parse_mode=ParseMode.MARKDOWN)
        result = await trigger_scraper_now(source_name, context.bot)
        # Show result with back button
        keyboard = [[InlineKeyboardButton("◀️ Back to Status",
                                          callback_data="admin_scrape_status")]]
        await query.edit_message_text(
            result, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("admin_enable_"):
        source_name = data.replace("admin_enable_", "")
        from scheduler import enable_scraper
        result = enable_scraper(source_name)
        keyboard = [[InlineKeyboardButton("◀️ Back to Status",
                                          callback_data="admin_scrape_status")]]
        await query.edit_message_text(
            result, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


from telegram import BotCommand


async def register_commands(app: Application):
    """Register bot commands in the Telegram menu."""
    commands = [
        BotCommand("start", "🤖 Get started"),
        BotCommand("subscribe", "✅ Subscribe to job alerts"),
        BotCommand("unsubscribe", "🔕 Stop receiving alerts"),
        BotCommand("preferences", "⚙️ Set your filters"),
        BotCommand("skills", "🎯 Set skill-based filters"),
        BotCommand("jobs", "📋 View 10 latest jobs"),
        BotCommand("search", "🔍 Search jobs"),
        BotCommand("help", "📖 List all commands"),
        BotCommand("about", "ℹ️ About this bot"),
        BotCommand("deletedata", "🗑️ Delete your data"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("Bot commands registered in menu")


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
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("deletedata", cmd_deletedata))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("scrapestatus", cmd_scrapestatus))
    app.add_handler(CallbackQueryHandler(cb_preferences, pattern="^pref_"))
    app.add_handler(CallbackQueryHandler(cb_page, pattern="^pg_"))
    app.add_handler(CallbackQueryHandler(cb_admin, pattern="^admin_"))
    return app
