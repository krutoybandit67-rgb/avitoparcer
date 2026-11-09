import aiohttp
from app.config import settings

QUERIES = [
    ("смартфон", "rossiya"),
    ("телефон", "rossiya"),
    ("смартфон", "ryazan"),
    ("телефон", "ryazan"),
]

async def search_avito():
    """Search provider adapter. API.SH charges 5 credits per search call (see provider docs)."""
    if not settings.apish_key:
        raise RuntimeError("APISH_KEY is missing. Configure an API.SH key to enable listing search.")
    headers = {"x-api-key": settings.apish_key}
    results = []
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for query, location in QUERIES:
            for page in range(1, max(1, settings.pages_per_query) + 1):
                params = {
                    "q": query,
                    "location": location,
                    "category": "telefony",
                    "price_max": settings.max_price,
                    "with_photos": "true",
                    "sort": "newest",
                    "page": page,
                }
                async with session.get(settings.apish_url, params=params, headers=headers) as resp:
                    if resp.status == 404:
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                for item in data.get("listings", []):
                    item["_search_location"] = location
                    results.append(item)
                if not data.get("next_page"):
                    break
    # De-duplicate items returned by overlapping searches.
    unique = {}
    for item in results:
        unique[str(item.get("id") or item.get("url"))] = item
    return list(unique.values())
