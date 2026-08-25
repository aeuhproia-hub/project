from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.keyboards import main_menu_kb
from bot.services.settings import get_total_submitted
from bot.texts import HELP_TEXT

logger = logging.getLogger(__name__)
router = Router(name="user_start")


async def _greeting_text() -> str:
    total = await get_total_submitted()
    return (
        "Приветствую в боте-анкетнице!\n\n"
        f"Анкет подано: {total}\n\n"
        f"Связь с администрацией: {config.admin_contact}"
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = await _greeting_text()
    kb = main_menu_kb()
    if config.banner:
        try:
            await message.answer_photo(photo=config.banner, caption=text, reply_markup=kb)
            return
        except Exception:
            logger.exception("Не удалось отправить баннер, отправляю только текст")
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "show_help")
async def cb_show_help(callback: CallbackQuery) -> None:
    await callback.answer()
    if config.help_gif:
        try:
            await callback.message.answer_animation(animation=config.help_gif, caption=HELP_TEXT)
        except Exception:
            logger.exception("Не удалось отправить GIF помощи, отправляю только текст")
            await callback.message.answer(HELP_TEXT)
    else:
        await callback.message.answer(HELP_TEXT)
