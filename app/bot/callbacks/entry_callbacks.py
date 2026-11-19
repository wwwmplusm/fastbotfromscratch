from aiogram.filters import Filter
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery


class EntryCB(CallbackData, prefix="e"):
    a: str
    eid: str


class ItemCB(CallbackData, prefix="i"):
    a: str
    iid: str


class DiaryCB(CallbackData, prefix="d"):
    a: str


class EntryAction(Filter):
    def __init__(self, *actions: str) -> None:
        self.actions = set(actions)

    async def __call__(self, callback: CallbackQuery) -> bool:
        parts = (callback.data or "").split(":")
        return len(parts) == 3 and parts[0] == "e" and parts[1] in self.actions


class ItemAction(Filter):
    def __init__(self, *actions: str) -> None:
        self.actions = set(actions)

    async def __call__(self, callback: CallbackQuery) -> bool:
        parts = (callback.data or "").split(":")
        return len(parts) == 3 and parts[0] == "i" and parts[1] in self.actions
