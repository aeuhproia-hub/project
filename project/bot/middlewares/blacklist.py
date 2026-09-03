from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import config
from bot.services.blacklist import is_blocked
from bot.texts import BLACKLISTED

logger = logging.getLogger(__name__)


class BlacklistMiddleware(BaseMiddleware):
    """Полностью блокирует взаимодействие для пользователей из чёрного списка.

    Не применяется в админ-группе — блокировка касается только личных
    сообщений пользователей боту.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        # В группах (админ-чат) блокировку не применяем
        if chat is not None and chat.type != "private":
            return await handler(event, data)

        if user is None or user.id == config.owner_id:
            return await handler(event, data)

        if await is_blocked(user.id):
            try:
                if isinstance(event, Message):
                    await event.answer(BLACKLISTED)
                elif isinstance(event, CallbackQuery):
                    await event.answer(BLACKLISTED, show_alert=True)
            except Exception:
                logger.exception("Не удалось уведомить заблокированного пользователя")
            return None

        return await handler(event, data)
