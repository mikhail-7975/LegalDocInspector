#!/usr/bin/env python3
"""
Конвертация справки о задолженности из «узкого» 5-колоночного формата (УПД/выгрузка)
в 8-колоночный формат, который корректно читает TableParser
(см. data/input_examples/.../04.303360-ТЭ_справка.XLSM).

Важно:
- все значения столбца «Задолженность» сохраняются без изменений;
- строки «оплата без даты» (типичный артефакт выгрузки с суммой 0) отбрасываются —
  иначе парсер падает на Invalid row.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from openpyxl import Workbook

PERIOD_RE = re.compile(r"^(0?[1-9]|1[0-2])\.\d{4}$")
MONTH_RE = re.compile(
    r"(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)\s+\d{4}",
    re.IGNORECASE,
)
END_MARKERS = ("итого по периоду", "итого по договору")


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _cell(row: list[Any], idx: int) -> Any:
    if idx >= len(row):
        return None
    value = row[idx]
    if isinstance(value, str):
        value = value.strip()
        return value if value != "" else None
    return value


def _as_text_period(value: Any) -> Any:
    """Нормализует период MM.YYYY (в т.ч. после чтения Excel-дат как float)."""
    if _is_empty(value):
        return value
    if isinstance(value, float) and value == int(value):
        # не ожидаем float-период; оставляем как есть
        return value
    text = str(value).strip()
    if text.startswith("="):
        # ="01.2026" или =\"01.2026\"
        m = re.search(r"(\d{1,2}\.\d{4})", text)
        return m.group(1) if m else text
    return text


def read_sheet_rows(path: Path) -> list[list[Any]]:
    suffix = path.suffix.lower()
    if suffix == ".xls":
        import xlrd

        wb = xlrd.open_workbook(str(path))
        sh = wb.sheet_by_index(0)
        rows: list[list[Any]] = []
        for r in range(sh.nrows):
            rows.append([sh.cell(r, c).value for c in range(sh.ncols)])
        return rows

    if suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook

        wb = load_workbook(str(path), data_only=True, read_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
        wb.close()
        return rows

    raise ValueError(f"Неподдерживаемый формат файла: {path.suffix}")


def classify_data_row(row: list[Any]) -> str:
    """
    Классификация строк тела таблицы (после заголовков).

    Возвращает один из:
      month_header, end, accrual, payment, debt, totals, advances, other, skip
    """
    c0 = _cell(row, 0)
    c1 = _cell(row, 1)
    c2 = _cell(row, 2)
    c3 = _cell(row, 3)
    # В исходнике задолженность в col 4; в уже 8-колоночном — в col 6
    c_debt = _cell(row, 6)
    if _is_empty(c_debt):
        c_debt = _cell(row, 4)

    if not _is_empty(c0) and isinstance(c0, str):
        low = c0.lower()
        if MONTH_RE.search(low):
            return "month_header"
        if any(marker in low for marker in END_MARKERS):
            return "end"
        if low.startswith("аванс"):
            return "advances"
        if PERIOD_RE.match(str(c0).strip()) and not _is_empty(c1):
            return "accrual"

    if _is_empty(c0):
        # Оплата: есть дата и сумма
        if not _is_empty(c2) and not _is_empty(c3):
            return "payment"
        # Артефакт выгрузки: сумма оплаты без даты (часто 0) — ломает парсер
        if _is_empty(c2) and not _is_empty(c3) and _is_empty(c1) and _is_empty(c_debt):
            return "skip"
        # Строка задолженности: только долг
        if _is_empty(c1) and _is_empty(c2) and _is_empty(c3) and not _is_empty(c_debt):
            return "debt"
        # Итоги блока: суммы начислений и оплат (опционально с долгом в той же строке)
        if not _is_empty(c1) and _is_empty(c2) and not _is_empty(c3):
            return "totals"

    return "other"


def convert_rows(src_rows: list[list[Any]]) -> list[list[Any]]:
    """Преобразует строки исходной справки в 8-колоночный формат парсера."""
    out: list[list[Any]] = []
    in_table = False
    finished = False

    for row in src_rows:
        # Нормализуем длину
        cells = list(row) + [None] * max(0, 5 - len(row))
        c0 = _cell(cells, 0)

        # Заголовок «Выставленный счет» — начало таблицы
        if not in_table and isinstance(c0, str) and "выставленный счет" in c0.lower():
            in_table = True
            out.append(
                [
                    "Выставленный счет",
                    None,
                    "Оплата",
                    None,
                    "Банковский\n документ",
                    "Расчетный\n счет",
                    "Задолженность",
                    "Назначение платежа",
                ]
            )
            continue

        if not in_table:
            # Шапка документа: ККС: → ККС, расширяем до 8 колонок
            header = [_cell(cells, i) for i in range(5)]
            if isinstance(header[0], str) and header[0].strip().upper().startswith("ККС"):
                header[0] = "ККС"
            out.append(header + [None, None, None])
            continue

        if finished:
            # После ИТОГО можно сохранить блок АВАНСЫ в совместимом виде
            kind = classify_data_row(cells)
            if kind == "advances":
                out.append([c0, None, None, None, None, None, None, None])
            elif kind == "skip":
                continue
            elif kind == "debt":
                debt = _cell(cells, 6)
                if _is_empty(debt):
                    debt = _cell(cells, 4)
                out.append([None, None, None, None, None, None, debt, None])
            elif kind == "totals":
                debt = _cell(cells, 6)
                if _is_empty(debt):
                    debt = _cell(cells, 4)
                out.append(
                    [
                        None,
                        _cell(cells, 1),
                        None,
                        _cell(cells, 3),
                        None,
                        None,
                        debt if not _is_empty(debt) else None,
                        None,
                    ]
                )
            elif kind == "other":
                # Строка вида «оплата 0 + задолженность 0» в блоке АВАНСЫ
                debt = _cell(cells, 6)
                if _is_empty(debt):
                    debt = _cell(cells, 4)
                pay = _cell(cells, 3)
                if _is_empty(_cell(cells, 0)) and _is_empty(_cell(cells, 1)) and _is_empty(_cell(cells, 2)):
                    if not _is_empty(debt) and _is_empty(pay):
                        out.append([None, None, None, None, None, None, debt, None])
                    elif not _is_empty(debt) and not _is_empty(pay):
                        # Сохраняем задолженность; сумму без даты не пишем как оплату
                        out.append([None, None, None, None, None, None, debt, None])
                elif all(_is_empty(_cell(cells, i)) for i in range(5)):
                    out.append([None] * 8)
            continue

        # Подзаголовки колонок сразу после «Выставленный счет»
        if isinstance(c0, str) and c0.strip().lower().startswith("месяц"):
            out.append(["Месяц, год", "Сумма", "Дата ", "Сумма", None, None, None, None])
            continue

        # Нумерация колонок 1..5 → 1..8
        if c0 in (1, 1.0) and _cell(cells, 1) in (2, 2.0):
            out.append([1, 2, 3, 4, 5, 6, 7, 8])
            continue

        kind = classify_data_row(cells)

        if kind == "skip":
            continue

        if kind == "month_header":
            out.append([c0, None, None, None, None, None, None, None])
            continue

        if kind == "end":
            # Унифицируем маркер конца как в эталонной справке
            out.append(["ИТОГО ПО ДОГОВОРУ", None, None, None, None, None, None, None])
            finished = True
            continue

        if kind == "accrual":
            period = _as_text_period(c0)
            out.append([period, _cell(cells, 1), None, None, None, None, None, None])
            continue

        if kind == "payment":
            out.append(
                [None, None, _cell(cells, 2), _cell(cells, 3), None, None, None, None]
            )
            continue

        if kind == "debt":
            debt = _cell(cells, 6)
            if _is_empty(debt):
                debt = _cell(cells, 4)
            # Сохраняем значение задолженности как есть (включая 0)
            out.append([None, None, None, None, None, None, debt, None])
            continue

        if kind == "totals":
            debt = _cell(cells, 6)
            if _is_empty(debt):
                debt = _cell(cells, 4)
            out.append(
                [
                    None,
                    _cell(cells, 1),
                    None,
                    _cell(cells, 3),
                    None,
                    None,
                    debt if not _is_empty(debt) else None,
                    None,
                ]
            )
            continue

        if kind == "advances":
            out.append([c0, None, None, None, None, None, None, None])
            finished = True
            continue

        # Пустая строка или нераспознанное — переносим «как есть» в 8 колонок,
        # но задолженность из col4 → col6
        debt = _cell(cells, 4)
        mapped = [
            _cell(cells, 0),
            _cell(cells, 1),
            _cell(cells, 2),
            _cell(cells, 3),
            None,
            None,
            debt,
            None,
        ]
        # Если это была «оплата без даты», уже отфильтровали через skip;
        # для прочих артефактов с суммой в col3 без даты — не пишем col3 без даты
        if _is_empty(mapped[0]) and _is_empty(mapped[1]) and _is_empty(mapped[2]) and not _is_empty(mapped[3]) and _is_empty(mapped[6]):
            continue
        out.append(mapped)

    return out


def write_xlsx(rows: list[list[Any]], dest: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Лист1"
    for r_idx, row in enumerate(rows, start=1):
        for c_idx, value in enumerate(row, start=1):
            if value is not None:
                ws.cell(r_idx, c_idx, value)
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(dest))


def convert_upd_to_certificate(src: Path, dest: Path) -> Path:
    src = Path(src)
    dest = Path(dest)
    src_rows = read_sheet_rows(src)
    out_rows = convert_rows(src_rows)
    write_xlsx(out_rows, dest)
    return dest


def _verify_with_parser(path: Path) -> dict:
    from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser

    parser = TableParser()
    parser.open(str(path))
    try:
        return parser.parse()
    finally:
        parser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Конвертация 5-колоночной справки УПД в формат TableParser (8 колонок)."
    )
    parser.add_argument("src", type=Path, help="Исходный .xls/.xlsx")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Путь к результату .xlsx (по умолчанию: <src_stem>_справка.xlsx)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Прогнать результат через TableParser и вывести долги по месяцам",
    )
    args = parser.parse_args()

    src = args.src
    if not src.is_file():
        raise SystemExit(f"Файл не найден: {src}")

    dest = args.output
    if dest is None:
        dest = src.with_name(f"{src.stem}_справка.xlsx")

    out = convert_upd_to_certificate(src, dest)
    print(f"Сохранено: {out}")

    if args.verify:
        import json

        result = _verify_with_parser(out)
        debts = {
            month: {
                "accrual_debt": data["accrual"]["debt"],
                "adjustment_debt": data["adjustment"]["debt"],
            }
            for month, data in result.items()
        }
        print(json.dumps(debts, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
