from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

router = Router()


@router.message(StateFilter(None), F.text)
async def fallback(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        await message.answer("Не знаю такую команду. Пришлите фото еды или откройте /today.")
        return
    await message.answer("Пришлите фото еды — я оценю состав. /today показывает дневник за сегодня.")
