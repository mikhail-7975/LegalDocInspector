"""
Заглушка парсера претензии: совместима с ``PDFClaimParser.analyse_claim`` (список dict с ключами
``claim_date``, ``claim_number``).
"""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


class ClaimParserStub:
    """Возвращает одну «пустую» запись для ручного ввода (как крайний случай в легаси)."""

    MANUAL_PROMPT: str = "заглушка претензии, введите данные вручную"

    def analyse_claim(self, path_to_file: str | Path) -> list[dict[str, str]]:
        path = Path(path_to_file)
        _log.info("ClaimParserStub: без OCR, файл=%s", path)
        return [{"claim_date": self.MANUAL_PROMPT, "claim_number": self.MANUAL_PROMPT}]
