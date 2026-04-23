"""
Заглушка парсера договора: имитирует долгий разбор (10 с) и возвращает признак
ручного ввода по всем полям (совместимо с ``PDFContractParser.analyse_contract``).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


class ContractParserStub:
    """
    Совместимость с легаси:
    ``analyse_contract(path, config) -> (тип, пункт, день_просрочки, текст)``.

    Третий элемент — та же строка «введите данные вручную»; в BFF нецифровое
    значение даёт fallback на 18 (см. ``form_helpers``).
    """

    DELAY_SECONDS: float = 1.0
    MANUAL_PROMPT: str = "отработала заглушка, введите данные вручную"

    def analyse_contract(
        self,
        path_to_file: str | Path,
        config: Any,
    ) -> tuple[str, str, str, str]:
        path = Path(path_to_file)
        _log.info(
            "ContractParserStub: ожидание %s с (заглушка), файл=%s",
            self.DELAY_SECONDS,
            path,
        )
        # time.sleep(self.DELAY_SECONDS)
        m = self.MANUAL_PROMPT
        return (m, m, m, m)
