from __future__ import annotations

import logging

from bot.keyboards import moderation_kb
from bot.rendering import render_admin_card
from bot.services import anketas as anketas_service

logger = logging.getLogger(__name__)


async def update_group_card(bot, entry: dict) -> None:
    """Карточка в теме группы: без кнопок решения — только статус.
    Кнопка «Взять на рассмотрение» есть только пока анкета свободна."""
    if not entry.get("admin_chat_id") or not entry.get("admin_message_id"):
        return
    kb = moderation_kb(entry["id"]) if entry["status"] == anketas_service.STATUS_NEW else None
    try:
        await bot.edit_message_text(
            chat_id=entry["admin_chat_id"],
            message_id=entry["admin_message_id"],
            text=render_admin_card(entry),
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Не удалось обновить групповую карточку анкеты #%s", entry["id"])


async def update_dm_card(bot, entry: dict, kb=None) -> None:
    """Карточка в личке админа: тут живут все кнопки принятия решения."""
    if not entry.get("dm_admin_id") or not entry.get("dm_message_id"):
        return
    try:
        await bot.edit_message_text(
            chat_id=entry["dm_admin_id"],
            message_id=entry["dm_message_id"],
            text=render_admin_card(entry),
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Не удалось обновить карточку анкеты #%s в личке", entry["id"])


async def sync_cards(bot, entry: dict, dm_kb=None) -> None:
    await update_group_card(bot, entry)
    await update_dm_card(bot, entry, dm_kb)
