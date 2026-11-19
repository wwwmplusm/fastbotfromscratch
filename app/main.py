import asyncio
import logging

import httpx
from aiogram import Bot
from sqlalchemy import text

from app.bot.context import AppContext
from app.bot.factory import build_dispatcher
from app.config import get_settings
from app.health import serve_health
from app.infrastructure.ai.openai_vision import build_recognizer
from app.infrastructure.database.session import create_db_engine, create_session_factory
from app.logging_config import setup_logging
from app.services.food_catalog import FoodCatalog
from app.services.nutrition_calculator import NutritionCalculator

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    if not settings.bot_token.strip():
        raise SystemExit("BOT_TOKEN is not set")
    setup_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    logger.info("database connection ok")

    client = None
    if settings.openai_api_key.strip():
        client = httpx.AsyncClient(timeout=httpx.Timeout(settings.openai_timeout_seconds, connect=10.0))
    recognizer = build_recognizer(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        json_mode=settings.openai_json_mode,
        client=client,
    )
    app = AppContext(
        settings=settings,
        recognizer=recognizer,
        calculator=NutritionCalculator(FoodCatalog()),
    )
    bot = Bot(token=settings.bot_token)
    dispatcher = build_dispatcher(app, session_factory)
    health = await serve_health(session_factory, settings.health_host, settings.health_port)
    try:
        await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        if health is not None:
            health.close()
            await health.wait_closed()
        await bot.session.close()
        if client is not None:
            await client.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(run())
