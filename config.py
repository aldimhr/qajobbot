from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_KEY", "") or os.getenv("BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    PROXY_URL: str = os.getenv("PROXY_URL", "")
    DB_PATH: str = "bot.db"
    LOG_PATH: str = "bot.log"


settings = Settings()
