from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.anketa_form import resolve_fix
from bot.services import anketas as anketas_service
from bot.texts import FIX_CONFIRM_SENT

logger = logging.getLogger(__name__)
router = Router(name="dm_bridge")


async def _forward_content(message: Message, target_chat_id: int, prefix: str) -> bool:
    try:
        if message.text:
            await message.bot.send_message(target_chat_id, f"{prefix}\n{message.text}")
        elif message.photo:
            await message.bot.send_photo(target_chat_id, message.photo[-1].file_id, caption=prefix)
        elif message.video:
            await message.bot.send_video(target_chat_id, message.video.file_id, caption=prefix)
        elif message.document:
            await message.bot.send_document(target_chat_id, message.document.file_id, caption=prefix)
        elif message.voice:
            await message.bot.send_voice(target_chat_id, message.voice.file_id, caption=prefix)
        elif message.animation:
            await message.bot.send_animation(target_chat_id, message.animation.file_id, caption=prefix)
        elif message.sticker:
            await message.bot.send_message(target_chat_id, prefix)
            await message.bot.send_sticker(target_chat_id, message.sticker.file_id)
        else:
            return False
        return True
    except Exception:
        logger.exception("Не удалось переслать сообщение в чат %s", target_chat_id)
        try:
            await message.reply("⚠️ Не удалось доставить сообщение собеседнику.")
        except Exception:
            pass
        return False


async def _route_admin_message(message: Message) -> bool:
    reviews = await anketas_service.get_active_reviews_for_admin(message.from_user.id)
    if not reviews:
        return False

    target_entry = None
    if len(reviews) == 1:
        target_entry = reviews[0]
    else:
        reply_to_id = message.reply_to_message.message_id if message.reply_to_message else None
        if reply_to_id:
            for entry in reviews:
                if entry.get("dm_message_id") == reply_to_id:
                    target_entry = entry
                    break
        if target_entry is None:
            names = ", ".join(f"#{e['id']}" for e in reviews)
            await message.reply(
                f"У вас сейчас несколько анкет на рассмотрении ({names}). "
                "Ответьте (через «Ответить») на карточку нужной анкеты, чтобы отправить "
                "сообщение именно по ней."
            )
            return True

    admin = message.from_user
    prefix = f"👮 Администратор (@{admin.username})" if admin.username else f"👮 Администратор (id{admin.id})"
    await _forward_content(message, target_entry["user_id"], prefix)
    return True


async def _route_applicant_message(message: Message) -> bool:
    entry = await anketas_service.get_active_for_user(message.from_user.id)
    if not entry or not entry.get("reviewer_id"):
        return False
    if entry["status"] not in (anketas_service.STATUS_REVIEW, anketas_service.STATUS_FIX_REQUIRED):
        return False

    user = message.from_user
    prefix = f"👤 Заявитель (@{user.username})" if user.username else f"👤 Заявитель (id{user.id})"
    delivered = await _forward_content(message, entry["reviewer_id"], prefix)
    if not delivered:
        return True

    if entry["status"] == anketas_service.STATUS_FIX_REQUIRED:
        ok = await resolve_fix(message.bot, entry["id"])
        if ok:
            await message.answer(FIX_CONFIRM_SENT)
    return True


@router.message(F.chat.type == "private")
async def bridge_catch_all(message: Message, state: FSMContext) -> None:
    if message.text and message.text.startswith("/"):
        return

    # Если пользователь сейчас в каком-то другом сценарии (заполняет анкету,
    # пишет причину отказа и т.п.) — не вмешиваемся, тот хендлер уже сработал
    # раньше нас по порядку регистрации роутеров.
    current_state = await state.get_state()
    if current_state is not None:
        return

    if await _route_admin_message(message):
        return
    await _route_applicant_message(message)
