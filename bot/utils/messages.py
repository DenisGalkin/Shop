from __future__ import annotations

from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message


_BANNER_PATH = Path(__file__).resolve().parents[2] / "image.png"


async def _answer_with_banner(message: Message, text: str, reply_markup=None) -> None:
    await message.answer_photo(
        FSInputFile(_BANNER_PATH),
        caption=text,
        reply_markup=reply_markup,
    )


async def render_message(
    source: Message | CallbackQuery,
    text: str,
    reply_markup=None,
) -> None:
    if isinstance(source, CallbackQuery):
        try:
            if source.message.photo:
                await source.message.edit_caption(caption=text, reply_markup=reply_markup)
            else:
                await source.message.delete()
                await _answer_with_banner(source.message, text, reply_markup=reply_markup)
        except TelegramBadRequest:
            await _answer_with_banner(source.message, text, reply_markup=reply_markup)
        await source.answer()
    else:
        await _answer_with_banner(source, text, reply_markup=reply_markup)
