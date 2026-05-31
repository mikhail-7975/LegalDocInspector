"""Единая настройка логирования в консоль для точек входа приложения."""

from __future__ import annotations

import logging
import sys


def configure_console_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    logging.getLogger("docling").setLevel(logging.WARNING)
