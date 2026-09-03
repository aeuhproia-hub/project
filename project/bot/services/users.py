from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from bot.config import config
from bot.json_store import JSONStore

_store = JSONStore(config.users_file, {})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_user() -> dict:
    return {
        "active_anketa_id": None,
        "cooldown_until": None,
        "cooldown_notice_sent": False,
    }


async def get_user(user_id: int) -> dict:
    data = await _store.read()
    entry = data.get(str(user_id), _empty_user())
    for k, v in _empty_user().items():
        entry.setdefault(k, v)
    return entry


async def set_active_anketa(user_id: int, anketa_id: Optional[str]) -> None:
    def mutate(data: dict) -> dict:
        entry = data.get(str(user_id), _empty_user())
        entry["active_anketa_id"] = anketa_id
        data[str(user_id)] = entry
        return data

    await _store.update(mutate)


async def start_cooldown(user_id: int, days: int) -> None:
    until = (_now() + timedelta(days=days)).isoformat()

    def mutate(data: dict) -> dict:
        entry = data.get(str(user_id), _empty_user())
        entry["active_anketa_id"] = None
        entry["cooldown_until"] = until
        entry["cooldown_notice_sent"] = False
        data[str(user_id)] = entry
        return data

    await _store.update(mutate)


async def clear_cooldown(user_id: int) -> None:
    """Досрочно снимает cooldown, позволяя подать анкету заново."""

    def mutate(data: dict) -> dict:
        entry = data.get(str(user_id), _empty_user())
        entry["cooldown_until"] = None
        entry["cooldown_notice_sent"] = False
        data[str(user_id)] = entry
        return data

    await _store.update(mutate)


async def was_cooldown_notice_sent(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user.get("cooldown_notice_sent"))


async def mark_cooldown_notice_sent(user_id: int) -> None:
    def mutate(data: dict) -> dict:
        entry = data.get(str(user_id), _empty_user())
        entry["cooldown_notice_sent"] = True
        data[str(user_id)] = entry
        return data

    await _store.update(mutate)


async def cooldown_remaining(user_id: int) -> Optional[timedelta]:
    """Возвращает оставшееся время cooldown, либо None если его нет."""
    user = await get_user(user_id)
    until_raw = user.get("cooldown_until")
    if not until_raw:
        return None
    until = datetime.fromisoformat(until_raw)
    remaining = until - _now()
    if remaining.total_seconds() <= 0:
        return None
    return remaining


def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days} д.")
    if hours:
        parts.append(f"{hours} ч.")
    if minutes and not days:
        parts.append(f"{minutes} мин.")
    if not parts:
        parts.append("менее минуты")
    return " ".join(parts)
