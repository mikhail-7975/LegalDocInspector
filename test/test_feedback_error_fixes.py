"""Узкие регрессии по фидбэку из data/errors (error1–error3)."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from docx import Document

from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator
from LegalDocInspector.legal_doc_inspector.doc_creator.docx_editor import DocxRedactor
from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import PDFClaimParser
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (
    get_ogrn_info,
    get_table_info,
    parse_egrul_certificate,
    parse_md_table,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/templates/calculation_claim_new_version_new.docx"
CLAIM_TEMPLATE = ROOT / "data/templates/claim.docx"
NON_EXCEL_CERTIFICATE = (
    ROOT
    / "test/data/documents_from_request_2026-07-22_113440.916885/complect_1/pdf.html"
)
ERROR3_ZIP = ROOT / "data/errors/error3/для программы (ООО УК Меридиан).zip"

_FOTE_LEGAL_STARTS = (
    "В силу п. 25",
    "Согласно п. 3 Информационного письма",
    "Как следует из содержания п. 2 ст. 421",
)
_FOTE_LEFTOVER_TAILS = (
    "в указанном в настоящем Иске количестве",
    "исполнил надлежащим образом",
)


def test_replace_text_spanning_split_runs(tmp_path):
    path = tmp_path / "split.docx"
    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run(" /*кол-во дней ")
    paragraph.add_run("начисления*/")
    doc.save(path)

    redactor = DocxRedactor()
    redactor.open(str(path))
    ok = redactor.replace_text_in_paragraph(
        redactor.doc.paragraphs[0],
        "/*кол-во дней начисления*/",
        "60",
    )
    redactor.save()
    redactor.close()

    assert ok is True
    text = Document(str(path)).paragraphs[0].text
    assert "кол-во дней" not in text
    assert "60" in text


@pytest.mark.skipif(not TEMPLATE.exists(), reason="нет шаблона расчёта")
def test_replace_days_placeholder_in_template_table_5(tmp_path):
    path = tmp_path / "calc.docx"
    shutil.copy(TEMPLATE, path)

    redactor = DocxRedactor()
    redactor.open(str(path))
    table = redactor.get_table(5)
    target = None
    for cell in table.rows[5].cells:
        if "кол-во дней" in cell.text:
            target = cell.paragraphs[0]
            break
    assert target is not None
    assert "/*кол-во дней начисления*/" in target.text

    ok = redactor.replace_text_in_paragraph(target, "/*кол-во дней начисления*/", "60")
    redactor.save()
    redactor.close()

    assert ok is True
    cell_text = Document(str(path)).tables[5].rows[5].cells
    joined = " ".join(c.text for c in cell_text)
    assert "кол-во дней" not in joined
    assert "60" in joined


def test_contract_cards_keep_duplicate_numbers_by_complect_index():
    table_parser_result = [
        ({}, "№ 09.800653кТЭ от 05.04.2024", "ТЭ", "-", "18", "text1", []),
        ({}, "№ 09.800653кТЭ от 05.04.2024", "ТЭ", "-", "18", "text2", []),
        ({}, "№ 04.517059кТЭ от 04.02.2026", "ТЭ", "-", "18", "text3", []),
    ]
    contracts = {}
    for complect_idx, contract_info in enumerate(table_parser_result):
        contracts[complect_idx] = {
            "contract_number": contract_info[1],
            "contract_text_parsed": contract_info[5],
        }
    assert len(contracts) == 3
    assert contracts[0]["contract_number"] == contracts[1]["contract_number"]
    assert contracts[0]["contract_text_parsed"] != contracts[1]["contract_text_parsed"]


def test_claim_parser_requires_header_and_local_pair():
    parser = object.__new__(PDFClaimParser)

    # Строгий режим: номер и дата в длинных разных блоках без «№»/«претенз» — пусто
    false_pos = [
        (1, "номер счёта 123456 в длинной строке оплаты по договору"),
        (1, "дата оплаты 01.01.2026 тоже в длинной строке без заголовка"),
    ]
    assert PDFClaimParser._parse_claim_number_and_date_strict(parser, false_pos) == []
    assert PDFClaimParser._parse_claim_number_and_date(parser, false_pos) == []

    same_block = [(1, "Претензия № 632341 от 11.08.2026")]
    assert PDFClaimParser._parse_claim_number_and_date(parser, same_block) == [
        ("632341", "11.08.2026")
    ]

    adjacent = [
        (1, "Претензия № 632341"),
        (1, "от 11.08.2026"),
    ]
    assert PDFClaimParser._parse_claim_number_and_date(parser, adjacent) == [
        ("632341", "11.08.2026")
    ]

    # OCR letterhead: дата / № / номер в трёх соседних блоках
    letterhead = [
        (1, "14.07.2026"),
        (1, "№"),
        (1, "629633"),
        (1, "на №"),
        (1, "от"),
    ]
    assert PDFClaimParser._parse_claim_number_and_date(parser, letterhead) == [
        ("629633", "14.07.2026")
    ]

    # Почтовый индекс 111524 рядом с датой и «№» не должен стать номером претензии
    with_index = [
        (1, "г. Москва, 111524 телефон"),
        (1, "14.07.2026"),
        (1, "№"),
        (1, "629633"),
    ]
    assert PDFClaimParser._parse_claim_number_and_date(parser, with_index) == [
        ("629633", "14.07.2026")
    ]

    # Строгий режим отсекает индекс+тело; legacy может взять фрагмент договора — проверяем strict
    body_false = [
        (1, "125009, город Москва, Малый Кисловский пер, д. 8"),
        (1, "Претензия на сумму 100 рублей"),
        (1, "заключен договор от 04.02.2026 №04.517059кТЭ"),
    ]
    assert PDFClaimParser._parse_claim_number_and_date_strict(parser, body_false) == []

    multi = [
        (1, "Претензия № 632341 от 11.08.2026"),
        (2, "123456"),
        (2, "02.02.2026"),
        (3, "Претензия № 631196 от 16.07.2026"),
        (4, "Претензия № 632341 от 11.08.2026"),
    ]
    # Основной путь — legacy: первая пара на каждой странице, без отсечения шапки.
    assert PDFClaimParser._parse_claim_number_and_date(parser, multi) == [
        ("632341", "11.08.2026"),
        ("123456", "02.02.2026"),
        ("631196", "16.07.2026"),
        ("632341", "11.08.2026"),
    ]


def test_claim_parser_falls_back_to_legacy_same_block_without_number_sign():
    """Как No560045: дата и номер в одном абзаце без «№» — срабатывает legacy."""
    parser = object.__new__(PDFClaimParser)
    blocks = [(1, "16.06.2025                        560045")]
    assert PDFClaimParser._parse_claim_number_and_date_strict(parser, blocks) == []
    assert PDFClaimParser._parse_claim_number_and_date(parser, blocks) == [
        ("560045", "16.06.2025")
    ]

def test_analyse_claim_stub_when_empty():
    parser = object.__new__(PDFClaimParser)
    # Аргумент self.doc_converter вычисляется до вызова _collect_claim_text_pairs
    parser.doc_converter = object()
    parser._collect_claim_text_pairs = lambda *a, **k: []  # type: ignore[method-assign]
    parser._parse_doc_with_ocr = lambda *a, **k: []  # type: ignore[method-assign]
    claims = PDFClaimParser.analyse_claim(parser, Path("missing.pdf"))
    assert claims == [
        {
            "claim_date": "Не удалось распознать дату",
            "claim_number": "Не удалось распознать номер",
        }
    ]


def test_ogrn_from_markdown_pipe_table():
    text = (
        "| 8 | ОГРН                                                                                   | 1147746934037                 |\n"
        "| 9 | Дата регистрации | 18.08.2014 |\n"
    )
    assert get_ogrn_info(text) == "1147746934037"


def test_ogrn_from_spaced_digits():
    text = "Выписка\nОГРН 1 1 4 7 7 4 6 9 3 4 0 3 7\nИНН 7721842711\n"
    assert get_ogrn_info(text) == "1147746934037"


def test_get_table_info_when_ogrn_row_became_header():
    import pandas as pd

    df = pd.DataFrame(columns=["8", "ОГРН", "1147746934037"], data=[["9", "Дата регистрации", "18.08.2014"]])
    assert get_table_info([df], "ОГРН") == "1147746934037"


def test_ogrn_fallback_from_text_when_tables_empty():
    text = (
        "Выписка из ЕГРЮЛ\n"
        "ОГРН 1147746934037                      Страница 1 из 22\n"
        "ИНН 7721842711\n"
    )
    assert get_table_info([], "ОГРН") == ""
    assert get_ogrn_info(text) == "1147746934037"


def test_parse_md_table_tolerates_extra_pipe():
    table = (
        "| № | Наименование | Значение |\n"
        "|---|---|---|\n"
        "| 1 | Полное наименование | ООО «А» |\n"
        "| 8 | ОГРН | 1147746934037 |\n"
        "| 9 | Адрес | Москва | дом 1 | корпус 2 |\n"
    )
    df = parse_md_table(table)
    assert df is not None
    assert not df.empty
    values = " ".join(df.astype(str).to_numpy().ravel())
    assert "ОГРН" in values
    assert "1147746934037" in values


@pytest.mark.integration
@pytest.mark.skipif(not ERROR3_ZIP.exists(), reason="нет архива error3")
def test_error3_egrul_pdf_yields_ogrn(tmp_path):
    import zipfile

    with zipfile.ZipFile(ERROR3_ZIP) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".pdf") and "ul-" in n.lower()]
        assert names
        pdf_path = tmp_path / Path(names[0]).name
        pdf_path.write_bytes(zf.read(names[0]))

    _full, _short, _address, _kpp, ogrn, _text = parse_egrul_certificate(pdf_path)
    assert ogrn == "1147746934037"


def _minimal_fote_config(service_type: str, n_contracts: int) -> dict:
    return {
        "company_type": "УК",
        "contracts_info": [{} for _ in range(n_contracts)],
        "responsitive_name": "Иванов И.И.",
        "plaintiff_info": {
            "full_name": "ПАО «МОЭК»",
            "short_name": "ПАО «МОЭК»",
            "ogrn": "1047796974092",
            "inn": "7720518494",
        },
        "defendant_info": {
            "full_name": "ООО «Тест»",
            "short_name": "ООО «Тест»",
            "ogrn": "1234567890123",
            "inn": "7700000000",
        },
        "table_info": {"all_debt": "100,00"},
        "lawsuit_info": {
            "service_type": service_type,
            "cost": "100,00",
            "tax": "10,00",
            "claims": ["№ 1 от 01.01.2026"],
        },
    }


@pytest.mark.skipif(not CLAIM_TEMPLATE.exists(), reason="нет шаблона иска")
@pytest.mark.parametrize(
    ("service_type", "n_contracts"),
    [("ФОТЭ", 1), ("ТЭ и ФОТЭ", 2)],
)
def test_fote_legal_inserts_do_not_keep_source_paragraph_tail(
    tmp_path, service_type, n_contracts
):
    """Вставки по акту ФОТЭ — отдельные абзацы, без хвоста клонированного абзаца шаблона."""
    out = tmp_path / "claim.docx"
    generator = ClaimGenerator()
    generator.config = _minimal_fote_config(service_type, n_contracts)
    generator.redactor.clone_file(str(CLAIM_TEMPLATE), str(out))
    generator.doc = generator.redactor.open(str(out))
    generator.prepare_data()
    generator.fill_other_parts()

    paragraphs = [p.text for p in generator.doc.paragraphs]
    fact_supply = [text for text in paragraphs if "Факт поставки" in text]
    assert len(fact_supply) == 1
    assert fact_supply[0].strip().startswith("Факт поставки")

    for start in _FOTE_LEGAL_STARTS:
        matched = [text for text in paragraphs if text.strip().startswith(start)]
        assert len(matched) == 1, start
        for tail in _FOTE_LEFTOVER_TAILS:
            assert tail not in matched[0], start


def test_parse_returns_body_for_non_excel_certificate(monkeypatch, tmp_path):
    """Справка не в Excel не должна превращать /parse в пустой HTML 500."""
    assert NON_EXCEL_CERTIFICATE.is_file()

    class _DummyParser:
        def __init__(self, *args, **kwargs):
            pass

    import LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models as parser_models
    from configs.config import load_yaml_config
    from dataclasses import replace

    monkeypatch.setattr(parser_models, "PDFClaimParser", _DummyParser)
    monkeypatch.setattr(parser_models, "PDFContractParser", _DummyParser)

    config = replace(
        load_yaml_config(str(ROOT / "configs/debug_config.yaml")),
        save_data_folder=str(tmp_path),
    )

    from LegalDocInspector.backend import create_app

    monkeypatch.setattr(
        "LegalDocInspector.backend.load_yaml_config", lambda _filename: config
    )
    app = create_app()
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False

    payload = NON_EXCEL_CERTIFICATE.read_bytes()
    name = NON_EXCEL_CERTIFICATE.name

    def _file():
        return (io.BytesIO(payload), name)

    response = app.test_client().post(
        "/parse",
        data={
            "date": "2026-11-11",
            "complects_count": "1",
            "1_certificates_count": "1",
            "egrul_certificate_file": _file(),
            "complect_1_claim_file": _file(),
            "complect_1_contract_file": _file(),
            "complect_1_certificate_file_0": _file(),
        },
        content_type="multipart/form-data",
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert name in body
    assert "не является файлом Excel" in body
    assert "Internal Server Error" not in body
    assert "did not return a valid response" not in body
