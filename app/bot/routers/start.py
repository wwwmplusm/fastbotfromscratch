from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.application.ports import UnitOfWork
from app.bot.context import AppContext
from app.bot.keyboards.draft_keyboard import draft_keyboard
from app.bot.ui import parse_uuid, show_draft
from app.domain.states import EntryStatus

router = Router()

START_TEXT = (
    "Fastbot — дневник питания.\n\n"
    "Пришлите фото еды. Я предложу состав и примерный вес, "
    "посчитаю калории, белки, жиры и углеводы.\n\n"
    "Это оценка, не точное измерение. "
    "Запись попадёт в дневник только после «Сохранить».\n\n"
    "/today — дневник за сегодня"
)

HELP_TEXT = (
    "Пришлите фото блюда.\n"
    "На карточке можно изменить вес, убрать позицию, сохранить или отменить.\n"
    "Пока вы не нажали «Сохранить», записи в дневнике нет.\n"
    "Изменение веса пересчитывает нутриенты без нового распознавания.\n\n"
    "/today — дневник за сегодня\n"
    "/cancel — выйти из ввода веса"
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cancel_input(message: Message, state: FSMContext, bot: Bot, uow: UnitOfWork, app: AppContext) -> None:
    current = await state.get_state()
    data = await state.get_data()
    await state.clear()
    if current is None:
        await message.answer("Нечего отменять. Черновик закрывается кнопкой «Отмена» на карточке.")
        return
    if message.from_user is None:
        return
    entry_id = parse_uuid(str(data.get("entry_id", "")))
    user = await uow.users.get_or_create(message.from_user.id, app.settings.default_timezone)
    entry = await uow.entries.get(entry_id, user.id) if entry_id is not None else None
    await uow.commit()
    if entry is None or entry.status != EntryStatus.DRAFT:
        await message.answer("Ввод веса отменён.")
        return
    await show_draft(bot, uow, user, entry, draft_keyboard(entry))
    await message.answer("Ввод веса отменён. Карточка черновика обновлена.")
