import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from telegram.constants import ParseMode
import database as db
from formatter import format_job_alert, format_digest

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
    await update.message.reply_text(
        "📖 *Perintah yang tersedia:*\n\n"
        "/start — Mulai menggunakan bot\n"
        "/subscribe — Berlangganan notifikasi\n"
        "/unsubscribe — Berhenti berlangganan\n"
        "/preferences — Atur filter preferensi\n"
        "/jobs — Lihat 10 lowongan terbaru\n"
        "/search <query> — Cari lowongan\n"
        "/deletedata — Hapus data kamu\n"
        "/help — Tampilkan pesan ini\n"
        "/about — Info tentang bot ini",
        parse_mode=ParseMode.MARKDOWN,
    )


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
    app.add_handler(CallbackQueryHandler(cb_preferences, pattern="^pref_"))
    return app
