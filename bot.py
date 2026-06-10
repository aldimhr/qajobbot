import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from telegram.constants import ParseMode
import database as db
from formatter import format_job_alert, format_digest
from admin import is_admin, format_stats, format_errors

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
    await update.message.reply_text(
        "🔕 Kamu sudah berhenti berlangganan. Gunakan /subscribe untuk mulai lagi."
    )


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
            "any": "✅ Semua",
        }
        await query.edit_message_text(
            f"✅ Preferensi diperbarui: {labels.get(work_type, work_type)}"
        )

    elif data.startswith("pref_notif_"):
        mode = data.replace("pref_notif_", "")
        prefs["notification_mode"] = mode
        await db.update_user_preferences(user_id, prefs)
        labels = {"instant": "⚡ Langsung", "daily": "📅 Harian (08:00)"}
        await query.edit_message_text(f"✅ Notifikasi: {labels.get(mode, mode)}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Perintah yang tersedia:*\n\n"
        "/start — Mulai menggunakan bot\n"
        "/subscribe — Berlangganan notifikasi\n"
        "/unsubscribe — Berhenti berlangganan\n"
        "/preferences — Atur filter preferensi\n"
        "/jobs — Lihat 10 lowongan terbaru\n"
        "/search <query> — Cari lowongan\n"
        "/deletedata — Hapus data kamu\n"
        "/help — Tampilkan pesan ini\n"
        "/about — Info tentang bot ini"
    )
    if is_admin(update.effective_user.id):
        text += (
            "\n\n🔧 *Admin Commands:*\n"
            "/admin — Admin panel\n"
            "/stats — Bot statistics\n"
            "/errors — Recent errors\n"
            "/broadcast <msg> — Send to all subscribers"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


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
    await update.message.reply_text(
        "🗑️ Data kamu sudah dihapus. Gunakan /start untuk mulai lagi."
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
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(cb_preferences, pattern="^pref_"))
    app.add_handler(CallbackQueryHandler(cb_admin, pattern="^admin_"))
    return app
