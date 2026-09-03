"""Единая настройка логирования для всего проекта."""

import logging
import sys


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Библиотека aiogram довольно многословна на DEBUG — оставляем INFO
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
