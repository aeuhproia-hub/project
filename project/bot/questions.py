"""Список вопросов анкеты. Порядок важен — он же определяет порядок стикеров."""

from __future__ import annotations

from typing import Any, Dict, List

QUESTIONS: List[Dict[str, Any]] = [
    {"key": "name", "text": "❀🌟 Ваше имя | псевдоним:", "type": "text"},
    {"key": "age", "text": "❀🌟 Ваш возраст в РЖ:", "type": "age"},
    {"key": "nickname", "text": "❀🌟 Ваш ник в Roblox:", "type": "text"},
    {"key": "experience", "text": "❀🌟 Сколько вы в сфере РП:", "type": "text"},
    {"key": "conflict", "text": "❀🌟 Конфликтный ли вы человек:", "type": "text"},
    {"key": "frequency", "text": "❀🌟 Как часто сможете приходить на РП:", "type": "text"},
    {"key": "source", "text": "❀🌟 Откуда узнали о проекте:", "type": "text"},
    {"key": "photos", "text": "❀🌟 Фото вашего скина (можно 1 или 2 фото):", "type": "photos"},
]

QUESTION_LABELS: Dict[str, str] = {
    "name": "Имя | псевдоним",
    "age": "Возраст",
    "nickname": "Ник в Roblox",
    "experience": "Опыт в РП",
    "conflict": "Конфликтность",
    "frequency": "Частота посещений",
    "source": "Откуда узнал(а)",
}

AGE_OPTIONS = ["12", "13", "14", "15", "16", "17", "18+"]

TOTAL_STEPS = len(QUESTIONS)
