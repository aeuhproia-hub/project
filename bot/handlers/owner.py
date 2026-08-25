from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import config
from bot.services.blacklist import add_to_blacklist, remove_from_blacklist
from bot.services.settings import get_total_submitted

router = Router(name="owner")


def _is_owner(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id == config.owner_id


@router.message(Command("setanket"))
async def cmd_setanket(message: Message) -> None:
    if not _is_owner(message):
        return
    total = await get_total_submitted()
    await message.reply(f"📊 Всего подано анкет: {total}")


def _parse_user_id(text: str) -> int | None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    try:
        return int(parts[1].strip())
    except ValueError:
        return None


# Telegram не распознаёт кириллические команды как "bot command entity",
# поэтому фильтруем вручную по началу текста сообщения.
@router.message(F.text.func(lambda t: t is not None and t.startswith("/чс")))
async def cmd_blacklist_add(message: Message) -> None:
    if not _is_owner(message):
        return
    user_id = _parse_user_id(message.text)
    if user_id is None:
        await message.reply("Использование: /чс USER_ID")
        return
    added = await add_to_blacklist(user_id)
    if added:
        await message.reply(f"⛔ Пользователь {user_id} добавлен в чёрный список.")
    else:
        await message.reply(f"Пользователь {user_id} уже находится в чёрном списке.")


@router.message(F.text.func(lambda t: t is not None and t.startswith("/разблокировать")))
async def cmd_blacklist_remove(message: Message) -> None:
    if not _is_owner(message):
        return
    user_id = _parse_user_id(message.text)
    if user_id is None:
        await message.reply("Использование: /разблокировать USER_ID")
        return
    removed = await remove_from_blacklist(user_id)
    if removed:
        await message.reply(f"✅ Пользователь {user_id} удалён из чёрного списка.")
    else:
        await message.reply(f"Пользователь {user_id} не найден в чёрном списке.")
