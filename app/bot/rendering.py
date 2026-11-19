from datetime import date, datetime
from decimal import Decimal

from app.application.results import DailyDiary
from app.domain.entry import FoodEntry
from app.domain.food_item import FoodItem
from app.domain.nutrition import Nutrition, quantize_amount
from app.domain.states import NutritionSource
from app.domain.time import resolve_zone

ESTIMATE_FOOTER = "Цифры приблизительные. Это не точное измерение."

_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_SOURCE = {
    NutritionSource.CATALOG: "каталог",
    NutritionSource.ESTIMATED: "оценка",
    NutritionSource.MANUAL: "вручную",
}

_FAILURE = {
    "not_configured": "Распознавание не настроено. Нужен ключ vision-сервиса в окружении бота.",
    "timeout": "Сервис распознавания не ответил вовремя.",
    "unavailable": "Сервис распознавания сейчас недоступен.",
    "invalid": "Не удалось прочитать ответ распознавания.",
    "empty": "На фото не получилось выделить еду. Снимите тарелку ближе и при свете.",
    "download_failed": "Не удалось скачать фото из Telegram.",
    "unexpected": "Не получилось разобрать фото.",
}


def format_amount(value: Decimal) -> str:
    quantized = quantize_amount(value)
    if quantized == quantized.to_integral():
        return str(int(quantized))
    return f"{quantized:.1f}".replace(".", ",")


def format_day(day: date) -> str:
    return f"{day.day} {_MONTHS[day.month - 1]}"


def format_local_stamp(moment: datetime, timezone_name: str) -> str:
    local = moment.astimezone(resolve_zone(timezone_name))
    return f"{format_day(local.date())}, {local.strftime('%H:%M')}"


def format_local_time(moment: datetime, timezone_name: str) -> str:
    return moment.astimezone(resolve_zone(timezone_name)).strftime("%H:%M")


def render_draft(entry: FoodEntry, timezone_name: str) -> str:
    lines = [
        f"Черновик · {format_local_stamp(entry.eaten_at, timezone_name)}",
        "Проверьте позиции и веса. В дневник запись попадёт только после «Сохранить».",
        "",
        _items_block(entry) or "Позиции не распознаны.",
        "",
        _totals_line("Итого", entry.totals),
        "",
        ESTIMATE_FOOTER,
    ]
    return "\n".join(lines)


def render_confirmed(entry: FoodEntry, timezone_name: str) -> str:
    lines = [
        f"Сохранено в дневник · {format_local_stamp(entry.eaten_at, timezone_name)}",
        "Состав и расчёт зафиксированы на момент сохранения.",
        "",
        _items_block(entry),
        "",
        _totals_line("Итого", entry.totals),
        "",
        ESTIMATE_FOOTER,
    ]
    return "\n".join(lines)


def render_cancelled() -> str:
    return "Черновик отменён. В дневник ничего не записано."


def render_failure(code: str) -> str:
    reason = _FAILURE.get(code, _FAILURE["unexpected"])
    return "\n".join(
        [
            "Не получилось разобрать фото.",
            reason,
            "",
            "Можно повторить анализ или отменить черновик. В дневник ничего не записано.",
            "",
            ESTIMATE_FOOTER,
        ]
    )


def render_edit_menu(entry: FoodEntry) -> str:
    if not entry.items:
        return "В черновике нет позиций. Повторите анализ или отмените его."
    return "Выберите позицию: нажмите название, чтобы изменить вес, или ✕, чтобы убрать её."


def render_weight_prompt(item: FoodItem) -> str:
    return "\n".join(
        [
            f"Новый вес для «{item.name}»",
            f"Сейчас: {format_amount(item.weight_g)} г",
            "",
            "Отправьте число в граммах, от 1 до 5000.",
            "/cancel — вернуться без изменений",
        ]
    )


def render_diary(diary: DailyDiary) -> str:
    title = f"Дневник · {format_day(diary.day)}"
    if not diary.entries:
        return "\n".join(
            [
                title,
                "",
                "Пока нет сохранённых записей. Пришлите фото еды.",
                "",
                ESTIMATE_FOOTER,
            ]
        )
    blocks = []
    for entry in diary.entries:
        names = ", ".join(f"{item.name} {format_amount(item.weight_g)} г" for item in entry.items)
        blocks.append(
            f"{format_local_time(entry.eaten_at, diary.timezone)} · {format_amount(entry.totals.calories)} ккал\n{names}"
        )
    return "\n\n".join(
        [
            title,
            *blocks,
            _totals_line("Итого за день", diary.totals),
            ESTIMATE_FOOTER,
        ]
    )


def render_analyzing() -> str:
    return "Анализирую фото…"


def item_button_label(item: FoodItem) -> str:
    name = item.name if len(item.name) <= 28 else item.name[:27] + "…"
    return f"{name} · {format_amount(item.weight_g)} г"


def _items_block(entry: FoodEntry) -> str:
    lines: list[str] = []
    for index, item in enumerate(entry.items, start=1):
        nutrition = item.nutrition
        source = _SOURCE.get(item.nutrition_source, "оценка")
        lines.append(f"{index}. {item.name} — {format_amount(item.weight_g)} г")
        lines.append(
            "   "
            f"{format_amount(nutrition.calories)} ккал · "
            f"Б {format_amount(nutrition.protein)} · "
            f"Ж {format_amount(nutrition.fat)} · "
            f"У {format_amount(nutrition.carbohydrates)} · "
            f"{source}"
        )
    return "\n".join(lines)


def _totals_line(label: str, totals: Nutrition) -> str:
    return (
        f"{label}: {format_amount(totals.calories)} ккал · "
        f"Б {format_amount(totals.protein)} · "
        f"Ж {format_amount(totals.fat)} · "
        f"У {format_amount(totals.carbohydrates)}"
    )
