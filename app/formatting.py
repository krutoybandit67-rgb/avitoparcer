from html import escape

def format_listing(item, analysis):
    title = escape(str(item.get("title") or "Смартфон"))
    price = item.get("price_text") or (f"{item.get('price')} ₽" if item.get("price") is not None else "Цена не указана")
    city = item.get("location") or item.get("address") or item.get("_search_location") or "Не указан"
    url = item.get("url") or item.get("link") or ""
    model = escape(str(analysis.get("model", "Не определена")))
    faults = analysis.get("faults") or ["Не удалось определить"]
    faults_text = "\n".join("• " + escape(str(x)) for x in faults[:5])
    repair = analysis.get("repair_cost_rub") or {}
    repair_text = f"{repair.get('min', '?')}–{repair.get('max', '?')} ₽"
    fair = analysis.get("fair_value_rub")
    fair_text = f"{fair} ₽" if isinstance(fair, (int, float)) else "недостаточно данных"
    score = analysis.get("score", 0)
    risk = escape(str(analysis.get("risk", "неизвестно")))
    confidence = escape(str(analysis.get("confidence", "низкая")))
    reason = escape(str(analysis.get("reason", "")))
    red_flags = analysis.get("red_flags") or []
    flags = "\n⚠️ Риски: " + escape("; ".join(map(str, red_flags[:4]))) if red_flags else ""
    link = f'<a href="{escape(url, quote=True)}">Открыть оригинальное объявление</a>' if url else "Ссылка не предоставлена"
    return (
        f"📱 <b>{title}</b>\n"
        f"Модель по ИИ: {model}\n"
        f"💰 Цена: <b>{escape(str(price))}</b>\n"
        f"📍 Место: {escape(str(city))}\n\n"
        f"🔧 <b>Предполагаемые проблемы:</b>\n{faults_text}\n"
        f"🛠 Ремонт (оценка ИИ): {repair_text}\n"
        f"🏷 Ориентир цены исправного: {fair_text}\n"
        f"⭐ Оценка: {score}/10 | Риск: {risk}\n"
        f"Уверенность анализа: {confidence}\n"
        f"{reason}{flags}\n\n{link}\n"
        "<i>Это предварительная оценка по объявлению и фото. Перед покупкой нужна личная диагностика.</i>"
    )
