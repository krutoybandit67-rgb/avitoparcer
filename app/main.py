import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config import settings
from app.db import init_db, already_seen, remember, close_db
from app.search import search_avito
from app.analyzer import analyze_listing
from app.formatting import format_listing

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Я Avito Smart Finder 📱\n"
        "Ищу смартфоны до 1 000 ₽, с приоритетом Рязани.\n\n"
        "/status — состояние бота\n"
        "/scan — запустить поиск вручную"
    )

@dp.message(Command("id"))
async def show_id(message: Message):
    await message.answer(f"Твой Telegram chat ID: <code>{message.chat.id}</code>")

@dp.message(Command("status"))
async def status(message: Message):
    await message.answer(
        f"Поиск: {'настроен' if settings.apish_key else 'нет APISH_KEY'}\n"
        f"Gemini: {'подключён' if settings.gemini_api_key else 'не подключён'}\n"
        f"Лимит цены: {settings.max_price} ₽\n"
        f"Интервал: {settings.poll_minutes} мин."
    )

async def send_listing(bot: Bot, chat_id: int, item, analysis=None):
    listing_id = str(item.get("id") or item.get("url") or "")
    if not listing_id or await already_seen(listing_id):
        return
    if analysis is None:
        analysis = await analyze_listing(item)
    # Skip only obvious low-potential/high-risk results? User asked to see all, sorted by score.
    caption = format_listing(item, analysis)
    images = item.get("images") or []
    if isinstance(images, str):
        images = [images]
    first_image = images[0] if images else None
    if first_image:
        try:
            await bot.send_photo(chat_id, first_image, caption=caption, parse_mode=ParseMode.HTML)
        except Exception:
            await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    else:
        await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    # Send remaining photos as an album; Telegram accepts up to 10 media items.
    if len(images) > 1:
        from aiogram.types import InputMediaPhoto
        try:
            await bot.send_media_group(chat_id, [InputMediaPhoto(media=u) for u in images[1:10]])
        except Exception:
            pass
    await remember(listing_id, item.get("url") or item.get("link") or "")

async def scan_once(bot: Bot, chat_id: int):
    items = await search_avito()
    # Ryazan first, then other regions; score ordering is done after analysis in send stage.
    items.sort(key=lambda x: 0 if "ryazan" in str(x.get("_search_location","")).lower() or "рязан" in str(x.get("location","")).lower() else 1)
    # Анализируем новые объявления заранее и сортируем по оценке Gemini.
    prepared = []
    for item in items:
        listing_id = str(item.get("id") or item.get("url") or "")
        if not listing_id or await already_seen(listing_id):
            continue
        try:
            analysis = await analyze_listing(item)
            prepared.append((item, analysis))
        except Exception:
            logging.exception("AI analysis failed")
            prepared.append((item, {
                "model": "Не определена", "faults": ["Не удалось выполнить ИИ-анализ"],
                "visual_condition": "Не проверено", "repair_difficulty": "неизвестно",
                "risk": "неизвестно", "repair_cost_rub": {"min": 0, "max": 0},
                "fair_value_rub": None, "score": 0, "confidence": "низкая",
                "reason": "Проверьте доступность Gemini API.", "red_flags": []
            }))
    prepared.sort(key=lambda pair: (
        int(pair[1].get("score", 0) or 0),
        1 if "ryazan" in str(pair[0].get("_search_location", "")).lower()
             or "рязан" in str(pair[0].get("location", "")).lower() else 0
    ), reverse=True)
    sent = 0
    for item, analysis in prepared:
        try:
            await send_listing(bot, chat_id, item, analysis)
            sent += 1
            await asyncio.sleep(1.2)
        except Exception:
            logging.exception("Failed to send listing")
    await bot.send_message(chat_id, f"Поиск завершён. Новых объявлений отправлено: {sent}.")

@dp.message(Command("scan"))
async def manual_scan(message: Message, bot: Bot):
    if settings.admin_chat_id and str(message.chat.id) != settings.admin_chat_id:
        await message.answer("Нет доступа.")
        return
    await message.answer("Запускаю поиск. Это может занять несколько минут…")
    try:
        await scan_once(bot, message.chat.id)
    except Exception as e:
        logging.exception("Manual scan failed")
        await message.answer(f"Ошибка поиска: {str(e)[:500]}")

async def polling_loop(bot: Bot):
    chat_id = int(settings.admin_chat_id) if settings.admin_chat_id else None
    if not chat_id:
        logging.warning("ADMIN_CHAT_ID is empty: automatic notifications disabled; use /scan.")
        return
    while True:
        try:
            await scan_once(bot, chat_id)
        except Exception:
            logging.exception("Scheduled scan failed")
        await asyncio.sleep(max(10, settings.poll_minutes) * 60)

async def main():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing")
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    task = asyncio.create_task(polling_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
