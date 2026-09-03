"""
Файловое хранилище состояний aiogram FSM.

По умолчанию aiogram хранит состояние анкеты (на каком вопросе находится
пользователь, какие ответы уже даны) в оперативной памяти. При перезапуске
бота (например, при редеплое на Railway) это всё терялось бы.

Этот класс сохраняет состояние и данные каждого диалога в JSON-файл,
поэтому после перезапуска пользователь, находящийся в процессе заполнения
анкеты, не теряет прогресс.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey


def _key_str(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or 0}:{key.destiny}"


class JSONFileStorage(BaseStorage):
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_sync({})

    def _read_sync(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return {}

    def _write_sync(self, data: Dict[str, Any]) -> None:
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".fsm.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    async def set_state(self, key: StorageKey, state: Optional[str | State] = None) -> None:
        async with self._lock:
            data = self._read_sync()
            entry = data.get(_key_str(key), {})
            state_value = state.state if isinstance(state, State) else state
            if state_value is None:
                entry.pop("state", None)
            else:
                entry["state"] = state_value
            data[_key_str(key)] = entry
            self._write_sync(data)

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with self._lock:
            data = self._read_sync()
            entry = data.get(_key_str(key))
            return entry.get("state") if entry else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        async with self._lock:
            all_data = self._read_sync()
            entry = all_data.get(_key_str(key), {})
            entry["data"] = data
            all_data[_key_str(key)] = entry
            self._write_sync(all_data)

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        async with self._lock:
            all_data = self._read_sync()
            entry = all_data.get(_key_str(key))
            return dict(entry.get("data", {})) if entry else {}

    async def close(self) -> None:
        return None
