from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import config
from bot.services.anketas import is_active_reviewer
from bot.texts import SPAM_BLOCKED


class AntiSpamMiddleware(BaseMiddleware):
    """Простой антиспам на основе скользящего окна.

    Если пользователь отправляет больше `antispam_limit` сообщений/нажатий
    за `antispam_window` секунд — временно блокируется на
    `antispam_block_minutes` минут. Случайный двойной клик не считается
    спамом благодаря отдельной защите от дребезга (см. debounce ниже).
    """

    def __init__(self) -> None:
        self._events: Dict[int, Deque[float]] = defaultdict(deque)
        self._blocked_until: Dict[int, float] = {}
        self._notified: set[int] = set()

    def force_unblock(self, user_id: int) -> None:
        """Снимает временную блокировку немедленно — используется кнопкой
        «У меня спамблок!»."""
        self._blocked_until.pop(user_id, None)
        self._notified.discard(user_id)
        self._events.pop(user_id, None)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Кнопка "У меня спамблок!" всегда должна быть нажимаема
        if isinstance(event, CallbackQuery) and event.data == "spam_help":
            return await handler(event, data)

        user = data.get("event_from_user")
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        # В группах (админ-чат) антиспам не применяем
        if chat is not None and chat.type != "private":
            return await handler(event, data)

        if user is None or user.id == config.owner_id:
            return await handler(event, data)

        # Админа, который сейчас что-то рассматривает, не блокируем —
        # иначе живая переписка с заявителем может оборваться на середине
        if await is_active_reviewer(user.id):
            return await handler(event, data)

        now = time.monotonic()
        user_id = user.id

        blocked_until = self._blocked_until.get(user_id)
        if blocked_until and now < blocked_until:
            if user_id not in self._notified:
                self._notified.add(user_id)
                try:
                    if isinstance(event, Message):
                        await event.answer(SPAM_BLOCKED)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(SPAM_BLOCKED, show_alert=True)
                except Exception:
                    pass
            return None
        if blocked_until and now >= blocked_until:
            self._blocked_until.pop(user_id, None)
            self._notified.discard(user_id)

        window = self._events[user_id]
        window.append(now)
        cutoff = now - config.antispam_window
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) > config.antispam_limit:
            self._blocked_until[user_id] = now + config.antispam_block_minutes * 60
            self._notified.add(user_id)
            try:
                if isinstance(event, Message):
                    await event.answer(SPAM_BLOCKED)
                elif isinstance(event, CallbackQuery):
                    await event.answer(SPAM_BLOCKED, show_alert=True)
            except Exception:
                pass
            return None

        return await handler(event, data)


class DebounceMiddleware(BaseMiddleware):
    """Игнорирует повторное нажатие той же inline-кнопки в течение короткого
    интервала — защита от случайного двойного клика и от гонки при
    одновременных действиях нескольких админов."""

    def __init__(self, interval_seconds: float = 1.2) -> None:
        self._interval = interval_seconds
        self._last_seen: Dict[tuple, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery) or not event.message:
            return await handler(event, data)

        key = (event.from_user.id, event.message.chat.id, event.message.message_id, event.data)
        now = time.monotonic()
        last = self._last_seen.get(key)
        if last is not None and now - last < self._interval:
            try:
                await event.answer()
            except Exception:
                pass
            return None
        self._last_seen[key] = now
        return await handler(event, data)
