import asyncpg
from app.config import settings

_pool = None

async def init_db():
    global _pool
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is missing. Add a Railway PostgreSQL database.")
    dsn = settings.database_url.replace("postgres://", "postgresql://", 1)
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                listing_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

async def already_seen(listing_id: str) -> bool:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM seen_listings WHERE listing_id=$1", str(listing_id))
        return row is not None

async def remember(listing_id: str, url: str):
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO seen_listings(listing_id,url) VALUES($1,$2) ON CONFLICT DO NOTHING",
            str(listing_id), url
        )

async def close_db():
    if _pool:
        await _pool.close()
