"""Быстрые unit-тесты эвристик PDFContractParser без Docling/PDF."""

from __future__ import annotations

import pymorphy3
import pytest

from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import (
    PDFContractParser,
)


@pytest.fixture(scope="module")
def contract_heuristics() -> PDFContractParser:
    """Лёгкий экземпляр: только morph, без инициализации Docling."""
    parser = object.__new__(PDFContractParser)
    parser.morph = pymorphy3.MorphAnalyzer(lang="ru")
    return parser


def _html(*parts: str) -> str:
    body = "\n".join(parts)
    return f"<html><head></head><body>{body}</body></html>"


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            _html("<h2>ДОГОВОР ТЕПЛОСНАБЖЕНИЯ</h2><p>Стороны заключили договор</p>"),
            "ТЭ",
        ),
        (
            _html("<p>Договор № 04.515629-ТЭ от 01.01.2020</p>"),
            "ТЭ",
        ),
        (
            _html("<div>ДОГОВОР ГОРЯЧЕГО ВОДОСНАБЖЕНИЯ № 03.208064ГВС</div>"),
            "ГВС",
        ),
        (
            _html(
                "<p>по акту от 01.08.2019 №224-13/01-19-ФОТЭ образовалась задолженность</p>"
            ),
            "ФОТЭ",
        ),
        (
            _html(
                "<p>Договор на цели содержания общего имущества (СОИ) многоквартирного дома</p>"
            ),
            "СОИ",
        ),
        # Тип только в div (не h1/h2/p) — раньше не находился.
        (
            _html("<div>ДОГОВОР ТЕПЛОСНАБЖЕНИЯ № 09.801882-ТЭ</div>"),
            "ТЭ",
        ),
        # OCR: латиница в коде типа.
        (
            _html("<p>Договор № 06.501123-TE от 29.10.2025</p>"),
            "ТЭ",
        ),
        (
            _html("<p>Акт проверки № 667-09/09/24-FOTE</p>"),
            "ФОТЭ",
        ),
    ],
)
def test_find_type_of_contract_from_html(
    contract_heuristics: PDFContractParser, html: str, expected: str
):
    assert contract_heuristics._find_type_of_contract(html) == expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("No_04.515629-ТЭ.pdf", "ТЭ"),
        ("contract-ГВС.pdf", "ГВС"),
        ("akt-19-ФОТЭ.pdf", "ФОТЭ"),
        ("dogovor_СОИ_2024.pdf", "СОИ"),
        ("contract-TE.pdf", "ТЭ"),
        ("scan-FOTE.pdf", "ФОТЭ"),
    ],
)
def test_find_type_of_contract_from_filename(
    contract_heuristics: PDFContractParser, filename: str, expected: str
):
    # Пустой HTML: сигнал только из имени файла.
    empty = _html("<div></div>")
    assert (
        contract_heuristics._find_type_of_contract(empty, path_to_file=filename)
        == expected
    )


def test_find_type_of_contract_unknown_without_signals(
    contract_heuristics: PDFContractParser,
):
    html = _html("<p>Стороны согласовали порядок расчётов и срок оплаты.</p>")
    assert (
        contract_heuristics._find_type_of_contract(html, path_to_file="scan_001.pdf")
        == PDFContractParser._TYPE_UNKNOWN
    )


def test_find_type_prefers_contract_number_over_body_gvs_mention(
    contract_heuristics: PDFContractParser,
):
    """В договоре ТЭ часто есть разделы про ГВС — тип берём из номера/титула."""
    html = _html(
        "<h2>ДОГОВОР ТЕПЛОСНАБЖЕНИЯ № 04.515629-ТЭ</h2>",
        "<p>3.5. Определение объема тепловой энергии на горячее водоснабжение.</p>",
        "<li>измеряющего количество тепловой энергии 1-й ступенью ВВП ГВС, и измеряющего</li>",
    )
    assert contract_heuristics._find_type_of_contract(html) == "ТЭ"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("до 18 числа месяца, следующего за расчетным, производит оплату", "18"),
        ("оплата производится в срок до 20-го числа месяца", "20"),
        ("5.5. Исполнитель в срок до 18-го числа месяца производит оплату", "18"),
        ("просто текст без дня", None),
        ("пункт 7.2 без дня оплаты", None),  # не брать 7/2 как день
    ],
)
def test_find_day_overdue_suggestions(
    contract_heuristics: PDFContractParser, text: str, expected: str | None
):
    assert contract_heuristics._find_day_overdue_suggestions(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("7.2. Оплата производится до 18 числа", "7.2"),
        ("7,2 Оплата производится до 18 числа", "7.2"),
        ("Согласно п. 5.5 договора оплата до 18 числа", "5.5"),
        ("в пункте 4.5 указано, что оплата до 15 числа", "4.5"),
    ],
)
def test_extract_contract_point(
    contract_heuristics: PDFContractParser, text: str, expected: str
):
    assert contract_heuristics._extract_contract_point(text) == expected


def test_find_point_of_overdue_prefers_payment_over_invoice(
    contract_heuristics: PDFContractParser,
):
    """Платёжный срок (оплата до N), а не выставление счёта."""
    from configs.config import load_yaml_config
    from pathlib import Path

    config = load_yaml_config(
        str(Path(__file__).resolve().parent.parent / "configs" / "debug_config.yaml")
    )
    html = _html(
        "<p>3.3. Снятие показаний производится ежемесячно по состоянию на 00:00 часов "
        "первого числа месяца, следующего за расчетным.</p>",
        "<p>7.1. Оплата поставляемой в расчетном периоде тепловой энергии производится "
        "Потребителем в срок до 20 числа месяца, следующего за расчетным.</p>",
        "<p>7.2. Теплоснабжающая организация выставляет Потребителю до 10 числа месяца, "
        "следующего за расчетным, счет на весь объем.</p>",
    )
    point, day, _ = contract_heuristics._find_point_of_overdue_date(
        html,
        keywords=config.point_overdue_keywords,
        excluded_words=config.point_overdue_excluded,
    )
    assert point == "7.1"
    assert day == "20"


def test_find_point_mid_sentence_punkt(
    contract_heuristics: PDFContractParser,
):
    from configs.config import load_yaml_config
    from pathlib import Path

    config = load_yaml_config(
        str(Path(__file__).resolve().parent.parent / "configs" / "debug_config.yaml")
    )
    html = _html(
        "<p>Исполнитель в соответствии с пунктом 5.5 договора в срок до 18-го числа "
        "месяца, следующего за расчетным, производит оплату стоимости тепловой энергии.</p>",
    )
    point, day, _ = contract_heuristics._find_point_of_overdue_date(
        html,
        keywords=config.point_overdue_keywords,
        excluded_words=config.point_overdue_excluded,
    )
    assert point == "5.5"
    assert day == "18"
