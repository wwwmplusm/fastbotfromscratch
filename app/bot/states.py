from aiogram.fsm.state import State, StatesGroup


class DraftEdit(StatesGroup):
    waiting_weight = State()
