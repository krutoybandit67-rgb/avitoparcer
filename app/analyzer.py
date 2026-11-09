import asyncio, json, re
import aiohttp
from google import genai
from google.genai import types
from app.config import settings

PROMPT = """
Ты помогаешь предварительно оценивать объявления о продаже подержанных смартфонов.
Проанализируй описание и приложенные фото. Не утверждай, что скрытая неисправность точно отсутствует.
Различай явно заявленную проблему и то, что только видно на фото. Если данных мало — так и напиши.
Нас интересуют простые дефекты: стекло/экран, разъём зарядки, кнопки, аккумулятор.
Серьёзные/неясные риски: не включается, следы жидкости, плата, блокировка аккаунта, неизвестное происхождение.
Верни ТОЛЬКО JSON:
{
 "model": "модель или Не определена",
 "faults": ["..."],
 "visual_condition": "...",
 "repair_difficulty": "низкая|средняя|высокая|неизвестно",
 "risk": "низкий|средний|высокий",
 "repair_cost_rub": {"min": 0, "max": 0},
 "fair_value_rub": null,
 "score": 0,
 "confidence": "низкая|средняя|высокая",
 "reason": "краткое объяснение",
 "red_flags": ["..."]
}
Оценка fair_value_rub должна быть null, если модель/состояние/рынок недостаточно ясны. Не выдумывай точные цены.
"""

def _extract_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.I|re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("Gemini did not return JSON")
    return json.loads(text[start:end+1])

async def analyze_listing(listing):
    if not settings.gemini_api_key:
        return {
            "model": "Не определена", "faults": ["ИИ-анализ отключён: нет GEMINI_API_KEY"],
            "visual_condition": "Не проверено", "repair_difficulty": "неизвестно",
            "risk": "неизвестно", "repair_cost_rub": {"min": 0, "max": 0},
            "fair_value_rub": None, "score": 0, "confidence": "низкая",
            "reason": "Добавьте Gemini API key в Railway Variables.", "red_flags": []
        }

    client = genai.Client(api_key=settings.gemini_api_key)
    parts = [PROMPT, f"""
Заголовок: {listing.get('title','')}
Цена: {listing.get('price','')}
Описание: {listing.get('description','')}
Параметры: {listing.get('params','')}
Город: {listing.get('location') or listing.get('_search_location','')}
"""]
    image_urls = listing.get("images") or []
    if isinstance(image_urls, str):
        image_urls = [image_urls]
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in image_urls[:settings.max_images_for_ai]:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        raw = await resp.read()
                        ctype = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
                        if ctype.startswith("image/") and len(raw) < 8_000_000:
                            parts.append(types.Part.from_bytes(data=raw, mime_type=ctype))
            except Exception:
                continue

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_model,
        contents=parts,
        config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json")
    )
    return _extract_json(response.text or "{}")
