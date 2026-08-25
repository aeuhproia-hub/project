from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import fix_ack_kb, moderation_kb, review_kb
from bot.rendering import render_admin_card
from bot.services import anketas as anketas_service
from bot.services import users as users_service
from bot.services.settings import set_admin_topic
from bot.states import FixForm, RejectForm
from bot.config import config
from bot.texts import NOT_IN_TOPIC, TOPIC_SET

logger = logging.getLogger(__name__)
router = Router(name="moderation")


def _is_owner(user_id: int) -> bool:
    return user_id == config.owner_id


@router.message(Command("settopic"))
async def cmd_settopic(message: Message) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    if not _is_owner(message.from_user.id):
        await message.reply("⚠️ Эту команду может использовать только владелец бота.")
        return

    if not message.is_topic_message or not message.message_thread_id:
        await message.reply(NOT_IN_TOPIC)
        return

    await set_admin_topic(message.chat.id, message.message_thread_id)
    await message.reply(TOPIC_SET)


async def _update_admin_card(bot, entry: dict, kb=None) -> None:
    if not entry.get("admin_chat_id") or not entry.get("admin_message_id"):
        return
    try:
        await bot.edit_message_text(
            chat_id=entry["admin_chat_id"],
            message_id=entry["admin_message_id"],
            text=render_admin_card(entry),
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Не удалось обновить карточку анкеты #%s", entry["id"])


@router.callback_query(F.data.startswith("take:"))
async def cb_take(callback: CallbackQuery) -> None:
    anketa_id = callback.data.split(":", 1)[1]
    admin = callback.from_user
    result = await anketas_service.take_for_review(anketa_id, admin.id, admin.username)

    if not result["ok"]:
        if result["reason"] == "already_taken":
            reviewer = result["entry"].get("reviewer_username")
            hint = f"@{reviewer}" if reviewer else "другим администратором"
            await callback.answer(f"Анкета уже взята на рассмотрение ({hint}).", show_alert=True)
        elif result["reason"] == "not_found":
            await callback.answer("Анкета не найдена.", show_alert=True)
        else:
            await callback.answer("Не удалось взять анкету на рассмотрение.", show_alert=True)
        return

    entry = result["entry"]
    await callback.answer("Анкета взята на рассмотрение.")
    await _update_admin_card(callback.bot, entry, review_kb(anketa_id))

    try:
        await callback.bot.send_message(
            entry["user_id"],
            f"👮 Вашу анкету рассматривает @{admin.username or admin.id}.",
        )
    except Exception:
        logger.warning("Не удалось уведомить пользователя %s о взятии анкеты", entry["user_id"])


@router.callback_query(F.data.startswith("release:"))
async def cb_release(callback: CallbackQuery) -> None:
    anketa_id = callback.data.split(":", 1)[1]
    admin = callback.from_user
    result = await anketas_service.release(anketa_id, admin.id)

    if not result["ok"]:
        reasons = {
            "not_found": "Анкета не найдена.",
            "not_in_review": "Анкета не находится на рассмотрении.",
            "not_your_review": "Вы не рассматриваете эту анкету.",
        }
        await callback.answer(reasons.get(result["reason"], "Не удалось освободить анкету."), show_alert=True)
        return

    entry = result["entry"]
    await callback.answer("Анкета освобождена.")
    await _update_admin_card(callback.bot, entry, moderation_kb(anketa_id))


@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(callback: CallbackQuery) -> None:
    anketa_id = callback.data.split(":", 1)[1]
    admin = callback.from_user
    result = await anketas_service.approve(anketa_id, admin.id)

    if not result["ok"]:
        reasons = {
            "not_found": "Анкета не найдена.",
            "already_decided": "По анкете уже принято решение.",
            "not_your_review": "Вы не рассматриваете эту анкету.",
        }
        await callback.answer(reasons.get(result["reason"], "Не удалось одобрить анкету."), show_alert=True)
        return

    entry = result["entry"]
    await callback.answer("Анкета одобрена.")
    await _update_admin_card(callback.bot, entry, None)
    await users_service.start_cooldown(entry["user_id"], config.cooldown_days)

    try:
        await callback.bot.send_message(entry["user_id"], "✅ Ваша анкета одобрена! Добро пожаловать.")
    except Exception:
        logger.warning("Не удалось уведомить пользователя %s об одобрении", entry["user_id"])


@router.callback_query(F.data.startswith("reject:"))
async def cb_reject_start(callback: CallbackQuery, state: FSMContext) -> None:
    anketa_id = callback.data.split(":", 1)[1]
    entry = await anketas_service.get_anketa(anketa_id)
    if not entry:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return
    if entry.get("reviewer_id") != callback.from_user.id:
        await callback.answer("Вы не рассматриваете эту анкету.", show_alert=True)
        return
    if entry["status"] in (anketas_service.STATUS_APPROVED, anketas_service.STATUS_REJECTED):
        await callback.answer("По анкете уже принято решение.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(RejectForm.waiting_reason)
    await state.update_data(anketa_id=anketa_id)
    await callback.message.reply("✍️ Напишите причину отказа отдельным сообщением в этом чате.")


@router.message(RejectForm.waiting_reason, F.text)
async def process_reject_reason(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    anketa_id = data.get("anketa_id")
    await state.clear()

    result = await anketas_service.reject(anketa_id, message.from_user.id, message.text.strip())
    if not result["ok"]:
        await message.reply("Не удалось отклонить анкету (возможно, решение уже принято).")
        return

    entry = result["entry"]
    await _update_admin_card(message.bot, entry, None)
    await users_service.start_cooldown(entry["user_id"], config.cooldown_days)
    await message.reply(f"Анкета #{anketa_id} отклонена.")

    try:
        await message.bot.send_message(
            entry["user_id"],
            f"❌ Ваша анкета отклонена.\n💬 Причина: {entry['reject_reason']}",
        )
    except Exception:
        logger.warning("Не удалось уведомить пользователя %s об отказе", entry["user_id"])


@router.callback_query(F.data.startswith("fixreq:"))
async def cb_fixreq_start(callback: CallbackQuery, state: FSMContext) -> None:
    anketa_id = callback.data.split(":", 1)[1]
    entry = await anketas_service.get_anketa(anketa_id)
    if not entry:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return
    if entry.get("reviewer_id") != callback.from_user.id:
        await callback.answer("Вы не рассматриваете эту анкету.", show_alert=True)
        return
    if entry["status"] in (anketas_service.STATUS_APPROVED, anketas_service.STATUS_REJECTED):
        await callback.answer("По анкете уже принято решение.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(FixForm.waiting_comment)
    await state.update_data(anketa_id=anketa_id)
    await callback.message.reply(
        "✍️ Напишите комментарий с тем, что нужно исправить, отдельным сообщением."
    )


@router.message(FixForm.waiting_comment, F.text)
async def process_fix_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    anketa_id = data.get("anketa_id")
    await state.clear()

    result = await anketas_service.request_fix(anketa_id, message.from_user.id, message.text.strip())
    if not result["ok"]:
        await message.reply("Не удалось запросить исправление (возможно, решение уже принято).")
        return

    entry = result["entry"]
    await _update_admin_card(message.bot, entry, review_kb(anketa_id))
    await message.reply(f"Запрошено исправление по анкете #{anketa_id}.")

    try:
        await message.bot.send_message(
            entry["user_id"],
            "⚠️ По вашей анкете требуется исправление.\n"
            f"💬 Комментарий: {entry['fix_comment']}",
            reply_markup=fix_ack_kb(),
        )
    except Exception:
        logger.warning("Не удалось уведомить пользователя %s о необходимости исправления", entry["user_id"])
