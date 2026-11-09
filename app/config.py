import os
from dataclasses import dataclass

@dataclass
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    apish_key: str = os.getenv("APISH_KEY", "")
    max_price: int = int(os.getenv("MAX_PRICE", "1000"))
    poll_minutes: int = int(os.getenv("POLL_MINUTES", "45"))
    pages_per_query: int = int(os.getenv("PAGES_PER_QUERY", "1"))
    max_images_for_ai: int = int(os.getenv("MAX_IMAGES_FOR_AI", "3"))
    database_url: str = os.getenv("DATABASE_URL", "")
    admin_chat_id: str = os.getenv("ADMIN_CHAT_ID", "")
    # API.SH search is a third-party paid data provider, not an official Avito API.
    apish_url: str = "https://api.api.sh/avito/v1/search"

settings = Settings()
