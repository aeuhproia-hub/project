"""
Простое, но надёжное JSON-хранилище.

Особенности:
- Атомарная запись (запись во временный файл + os.replace), поэтому файл
  никогда не остаётся "битым" при падении процесса посреди записи.
- asyncio.Lock на файл, чтобы параллельные обработчики (например, два админа,
  одновременно нажавшие "Взять на рассмотрение") не могли повредить данные
  или получить рассинхронизацию.
- Метод `update()` — атомарное чтение-изменение-запись одной операцией,
  это основной способ безопасно менять данные.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict

_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(path: Path) -> asyncio.Lock:
    key = str(path.resolve())
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


class JSONStore:
    """Обёртка над одним JSON-файлом с безопасным доступом."""

    def __init__(self, path: Path, default: Any):
        self.path = Path(path)
        self._default = default
        self._lock = _lock_for(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_sync(self._default_copy())

    def _default_copy(self) -> Any:
        if isinstance(self._default, dict):
            return dict(self._default)
        if isinstance(self._default, list):
            return list(self._default)
        return self._default

    def _read_sync(self) -> Any:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return self._default_copy()

    def _write_sync(self, data: Any) -> None:
        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
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

    async def read(self) -> Any:
        async with self._lock:
            return self._read_sync()

    async def write(self, data: Any) -> None:
        async with self._lock:
            self._write_sync(data)

    async def update(self, mutator: Callable[[Any], Any]) -> Any:
        """
        Атомарно читает файл, применяет `mutator(data) -> data_or_None`
        и сохраняет результат. Если mutator возвращает None, считается,
        что он изменил структуру in-place (актуально для dict/list).
        Возвращает итоговые данные.
        """
        async with self._lock:
            data = self._read_sync()
            result = mutator(data)
            final_data = data if result is None else result
            self._write_sync(final_data)
            return final_data
