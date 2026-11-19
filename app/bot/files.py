import io

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest


class DownloadError(Exception):
    pass


async def download_photo(bot: Bot, file_id: str, max_bytes: int) -> bytes:
    try:
        file = await bot.get_file(file_id)
    except TelegramBadRequest as exc:
        raise DownloadError(exc.message) from None
    if file.file_size and file.file_size > max_bytes:
        raise DownloadError("too large")
    if not file.file_path:
        raise DownloadError("no path")
    buffer = io.BytesIO()
    try:
        await bot.download_file(file.file_path, buffer)
    except TelegramBadRequest as exc:
        raise DownloadError(exc.message) from None
    data = buffer.getvalue()
    if not data or len(data) > max_bytes:
        raise DownloadError("too large")
    return data
