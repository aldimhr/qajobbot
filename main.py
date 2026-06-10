import asyncio
import logging
from config import settings
from database import init_db
from bot import setup_bot
from scheduler import setup_scheduler
from proxy_pool import proxy_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    # Init database
    await init_db()
    logger.info("Database initialized")

    # Setup bot
    app = setup_bot(settings.BOT_TOKEN)
    logger.info("Bot handlers registered")

    # Refresh proxy pool
    logger.info("Refreshing proxy pool...")
    await proxy_pool.refresh()
    logger.info(f"Proxy pool ready: {proxy_pool.count} proxies")

    # Setup scheduler
    scheduler = setup_scheduler(app.bot)
    scheduler.start()
    logger.info("Scheduler started")

    # Run bot in polling mode
    logger.info("Bot starting in polling mode...")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Bot is running! Press Ctrl+C to stop.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
