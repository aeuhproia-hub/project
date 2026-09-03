from __future__ import annotations

from bot.config import config
from bot.json_store import JSONStore

_store = JSONStore(config.blacklist_file, {"blocked": []})


async def is_blocked(user_id: int) -> bool:
    data = await _store.read()
    return user_id in data.get("blocked", [])


async def add_to_blacklist(user_id: int) -> bool:
    """Возвращает True, если пользователь был добавлен (не находился там ранее)."""
    added_holder = {"added": False}

    def mutate(data: dict) -> dict:
        blocked = data.setdefault("blocked", [])
        if user_id not in blocked:
            blocked.append(user_id)
            added_holder["added"] = True
        return data

    await _store.update(mutate)
    return added_holder["added"]


async def remove_from_blacklist(user_id: int) -> bool:
    """Возвращает True, если пользователь был удалён (находился в списке)."""
    removed_holder = {"removed": False}

    def mutate(data: dict) -> dict:
        blocked = data.setdefault("blocked", [])
        if user_id in blocked:
            blocked.remove(user_id)
            removed_holder["removed"] = True
        return data

    await _store.update(mutate)
    return removed_holder["removed"]
