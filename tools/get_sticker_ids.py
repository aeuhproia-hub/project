"""
Вспомогательный скрипт: получает file_id стикеров из стикерпака
https://t.me/addstickers/Akemi_Homura и выводит готовую строку
для вставки в переменную QUESTION_STICKERS в файле .env.

Запуск (из корня проекта, после установки зависимостей):

    python tools/get_sticker_ids.py

Скрипт спросит токен бота, если он не найден в переменной окружения
BOT_TOKEN / файле .env.
"""

from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot
from dotenv import load_dotenv

STICKER_SET_NAME = "Akemi_Homura"


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        token = input("Введите BOT_TOKEN вашего бота: ").strip()

    bot = Bot(token=token)
    try:
        sticker_set = await bot.get_sticker_set(STICKER_SET_NAME)
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось получить стикерпак '{STICKER_SET_NAME}': {exc}")
        sys.exit(1)
    finally:
        await bot.session.close()

    print(f"\nНайдено стикеров в наборе: {len(sticker_set.stickers)}\n")
    for i, sticker in enumerate(sticker_set.stickers, start=1):
        print(f"{i}. {sticker.emoji or ''}  file_id: {sticker.file_id}")

    needed = 8
    ids = [s.file_id for s in sticker_set.stickers[:needed]]
    if len(ids) < needed:
        print(
            f"\n⚠️ В наборе всего {len(ids)} стикеров, а вопросов в анкете {needed}. "
            "Можно повторно использовать одни и те же file_id — просто скопируйте "
            "нужное количество вручную из списка выше."
        )

    print("\nГотовая строка для .env (при необходимости отредактируйте порядок):\n")
    print("QUESTION_STICKERS=" + ",".join(ids))


if __name__ == "__main__":
    asyncio.run(main())
