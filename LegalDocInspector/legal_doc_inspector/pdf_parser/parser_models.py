import datetime
import logging
import os
import shutil
import time
from pathlib import Path
import torch
import numpy as np
from pydantic import TypeAdapter
from typing import Optional, List, Tuple
from docling.datamodel.settings import settings
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import (
    ThreadedPdfPipelineOptions,
)
import pymorphy3
import html as html_parser
from docling_core.types.doc.document import DoclingDocument
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline
from docling.utils.profiling import ProfilingItem
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
    OcrMacOptions,
    RapidOcrOptions,
    OcrAutoOptions,
)
from rapidfuzz import fuzz

from bs4 import BeautifulSoup
import re
import gc

from configs.config import AppConfig
from LegalDocInspector.legal_doc_inspector.docling_artifacts import (
    resolve_docling_artifacts_path,
)
from LegalDocInspector.legal_doc_inspector.pdf_parser.docling_safe_convert import (
    concatenate_documents,
    convert_pdf_pages,
    documents_export_to_html,
    documents_have_text,
    extract_text_pairs_from_documents,
    get_pdf_page_count,
    is_allocation_error,
    release_memory,
    write_pdf_sidecar_html,
)

_DOCLING_ACCEL_THREADS = min(4, os.cpu_count() or 4)
_CONTRACT_MAX_PAGES = 15
torch.set_num_threads(_DOCLING_ACCEL_THREADS)

_log = logging.getLogger(__name__)

KEYWORDS = ['публичное', 'пао', 'акционерное', 'общество']
SKIP_PHRASES = [r'справка.*прохождении.*документа']
SKIP_LINES_AFTER_MATCH = 5

logging.getLogger("docling").setLevel(logging.WARNING)
_log.setLevel(logging.INFO)


def _docling_pipeline_options_low_memory(*, use_cuda: bool) -> ThreadedPdfPipelineOptions:
    """Меньше RAM: layout без таблиц, батчи по 1, мало потоков, images_scale=0.5."""
    options = ThreadedPdfPipelineOptions(
        accelerator_options=AcceleratorOptions(
            device=AcceleratorDevice.CUDA if use_cuda else AcceleratorDevice.CPU,
            num_threads=_DOCLING_ACCEL_THREADS,
        ),
        images_scale=0.5,
        ocr_batch_size=1,
        layout_batch_size=1,
        table_batch_size=1,
        do_ocr=True,
        do_table_structure=False,
        do_picture_description=False,
    )
    artifacts_path = resolve_docling_artifacts_path()
    if artifacts_path is not None:
        options.artifacts_path = str(artifacts_path)
        _log.debug("Docling artifacts_path=%s", artifacts_path)
    return options


def _resolve_tesseract_cmd() -> str:
    """
    Path or name of the tesseract executable for TesseractCliOcrOptions.
    Set TESSERACT_CMD to an absolute path if tesseract is not on PATH (typical on Windows).
    """
    explicit = (os.environ.get("TESSERACT_CMD") or "").strip()
    if explicit:
        return explicit
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        p = Path(candidate)
        if p.is_file():
            return str(p.resolve())
    return "tesseract"


_get_pdf_page_count = get_pdf_page_count


def _get_contract_page_count(pdf_path: Path) -> int:
    """Число страниц договора для извлечения (не более _CONTRACT_MAX_PAGES)."""
    total_pages = _get_pdf_page_count(pdf_path)
    if total_pages > _CONTRACT_MAX_PAGES:
        _log.info(
            "Contract PDF has %s page(s), limiting extraction to first %s: %s",
            total_pages,
            _CONTRACT_MAX_PAGES,
            pdf_path,
        )
        return _CONTRACT_MAX_PAGES
    return total_pages


def _tesseract_cli_ocr_options() -> TesseractCliOcrOptions:
    cmd = _resolve_tesseract_cmd()
    if not (Path(cmd).is_file() or shutil.which(cmd)):
        raise RuntimeError(
            "Tesseract executable not found. Install Tesseract for Windows (e.g. UB Mannheim build), "
            "add its folder to PATH, or set the environment variable TESSERACT_CMD to the full path "
            r'of tesseract.exe (for example C:\Program Files\Tesseract-OCR\tesseract.exe).'
        )
    _log.debug("Using Tesseract CLI: %s", cmd)
    return TesseractCliOcrOptions(
        lang=["rus"],
        force_full_page_ocr=False,
        tesseract_cmd=cmd,
    )


class PDFClaimParser:
    def __init__(self) -> None:
        pipeline_options = _docling_pipeline_options_low_memory(
            use_cuda=torch.cuda.is_available()
        )

        pipeline_options.ocr_options = _tesseract_cli_ocr_options()
        # pipeline_options.ocr_options = PdfPipelineOptions()

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )

        start_time = time.time()
        self.doc_converter.initialize_pipeline(InputFormat.PDF)
        init_runtime = time.time() - start_time
        _log.info(f"Pipeline initialized in {init_runtime:.2f} seconds.")

    def _collect_claim_text_pairs(
        self,
        path_to_file: Path,
        doc_converter: DocumentConverter,
        *,
        log_prefix: str,
    ) -> list[tuple[int, str]]:
        documents, pages_ok, last_error = convert_pdf_pages(
            doc_converter,
            path_to_file,
            log_prefix=log_prefix,
        )
        if last_error and not documents:
            if is_allocation_error(last_error):
                return []
            raise RuntimeError(
                f"Conversion failed for {path_to_file}: {last_error}"
            ) from last_error
        write_pdf_sidecar_html(path_to_file, documents_export_to_html(documents))
        pairs = extract_text_pairs_from_documents(
            documents,
            extract_text_with_page=self._extract_text_with_page,
        )
        _log.info(
            "Claim text pairs from %s page(s): %s blocks (%s)",
            pages_ok,
            len(pairs),
            path_to_file,
        )
        return pairs

    def _parse_doc_with_ocr(self, path_to_file: str | Path) -> list[tuple[int, str]]:
        pipeline_options = _docling_pipeline_options_low_memory(
            use_cuda=torch.cuda.is_available()
        )
        pipeline_options.ocr_options = _tesseract_cli_ocr_options()

        doc_converter_ocr = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )

        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        start_time = time.time()
        _log.info("Starting conversion of document - ocr attempt: %s", path_to_file)
        pairs = self._collect_claim_text_pairs(
            path_to_file,
            doc_converter_ocr,
            log_prefix="claim-OCR",
        )
        _log.info(
            "Document converted (ocr) in %.2f seconds.",
            time.time() - start_time,
        )
        del doc_converter_ocr
        return pairs

    def _extract_text_with_page(self, data: list) -> list[tuple[int, str]]:
        """
        Принимает список, полученный как list(doc.as_dict().values()),
        и возвращает список кортежей (page_number, text).
        """
        if len(data) < 9:
            raise ValueError("Ожидался список длиной >= 9 (текстовые блоки в data[7])")

        text_blocks = data[7]  # это список словарей с текстом
        # print(text_blocks)
        result = []
        for block in text_blocks:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            prov = block.get("prov")
            if not text or not prov:
                continue
            # Берём номер первой страницы из prov (обычно один элемент)
            page_no = prov[0].get("page_no")
            if page_no is not None:
                result.append((int(page_no), str(text)))
        return result

    def analyse_claim(self, path_to_file: str|Path):
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        start_time = time.time()
        _log.info("Starting conversion of document: %s", path_to_file)

        text_pairs = self._collect_claim_text_pairs(
            path_to_file,
            self.doc_converter,
            log_prefix="claim",
        )
        _log.info(
            "Document converted in %.2f seconds.",
            time.time() - start_time,
        )

        claims = self._parse_claim_number_and_date(text_pairs)
        if len(claims) == 0:
            text_pairs = self._parse_doc_with_ocr(path_to_file)
            claims = self._parse_claim_number_and_date(text_pairs)
        release_memory()
        claims = self._standartize_claims(claims)
        if len(claims) == 0:
            claims = [{"claim_date": "Не удалось распознать дату", "claim_number": "Не удалось распознать номер"}]
        return claims

    def _standartize_claims(self, claims:list[tuple[str | None, str | None]]):
        response = []
        for number, date in claims:
            claim_dict = {"claim_date": str(date), "claim_number": str(number)}
            response.append(claim_dict)
        return response

    _CLAIM_HEADER_HINT = re.compile(
        r"(претенз|исх(?:\.|од)|№|No\.?)",
        re.IGNORECASE,
    )
    _CLAIM_DATE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b")
    _CLAIM_NUMBER = re.compile(r"\b\d{6}\b")

    def _parse_claim_number_and_date(self, texts_with_pages: List[Tuple[int, str]]) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Сначала прежняя эвристика по страницам (первая пара «6 цифр + дата»).
        Строгие правила — только если эвристика ничего не нашла
        (дата и номер разрезаны OCR и не попали в короткие блоки).
        """
        claims = self._parse_claim_number_and_date_legacy(texts_with_pages)
        if claims:
            return claims
        return self._parse_claim_number_and_date_strict(texts_with_pages)

    def _claim_skip_pages(self, texts_with_pages: List[Tuple[int, str]]) -> set:
        skip_pages = set()
        for page, text in texts_with_pages:
            if re.search(r"справка.*прохождении", text, re.IGNORECASE):
                skip_pages.add(page)
        return skip_pages

    def _parse_claim_number_and_date_strict(
        self, texts_with_pages: List[Tuple[int, str]]
    ) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Пара засчитывается только если номер и дата лежат в одном блоке или в окне
        из 2–3 соседних блоков (типичный OCR-разрез «дата / № / номер»), и рядом
        есть признак заголовка претензии.
        """
        from collections import defaultdict

        skip_pages = self._claim_skip_pages(texts_with_pages)
        pages_dict = defaultdict(list)
        for page, text in texts_with_pages:
            if page not in skip_pages:
                pages_dict[page].append(text)

        response: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for page in pages_dict:
            blocks = pages_dict[page]
            for i in range(len(blocks)):
                # 1–3 соседних блока: дата и номер часто разрезаны OCR по отдельным run/абзацам
                for width in (1, 2, 3):
                    if i + width > len(blocks):
                        break
                    window_blocks = blocks[i : i + width]
                    window = " ".join(window_blocks)
                    dates = self._CLAIM_DATE.findall(window)
                    if not dates:
                        continue
                    if not self._CLAIM_HEADER_HINT.search(window):
                        continue
                    numbers = self._claim_numbers_in_header_window(window_blocks, window)
                    if not numbers:
                        continue
                    # В коротком заголовочном окне берём первую пару номер+дата
                    pair = (numbers[0], dates[0])
                    if pair in seen:
                        continue
                    seen.add(pair)
                    response.append(pair)

        return response

    def _parse_claim_number_and_date_legacy(
        self, texts_with_pages: List[Tuple[int, str]]
    ) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Старые правила: на странице ищем 6 цифр и дату в одном блоке либо
        в коротких отдельных блоках (номер len<7, дата len<11); по странице — первая пара.
        """
        from collections import defaultdict

        skip_pages = self._claim_skip_pages(texts_with_pages)
        pages_dict = defaultdict(list)
        for page, text in texts_with_pages:
            if page not in skip_pages:
                pages_dict[page].append(text)

        response: list[tuple[str, str]] = []
        for page in pages_dict:
            date_flag = False
            num_flag = False
            number = None
            date = None
            for string in pages_dict[page]:
                match1 = self._CLAIM_NUMBER.search(string)
                match2 = self._CLAIM_DATE.search(string)

                if match1 and match2:
                    number = match1.group()
                    date = match2.group()
                    date_flag = True
                    num_flag = True

                if match2 and len(string) < 11:
                    date = match2.group()
                    date_flag = True
                if match1 and len(string) < 7:
                    number = match1.group()
                    num_flag = True

                if num_flag and date_flag:
                    response.append((number, date))
                    break

        return response

    def _claim_numbers_in_header_window(self, window_blocks: List[str], window: str) -> List[str]:
        """Номера, привязанные к «№»/заголовку; почтовый индекс рядом с датой не берём."""
        postal_nums = set()
        for block in window_blocks:
            m = re.match(r"^(\d{6})\s*,", block.strip())
            if m:
                postal_nums.add(m.group(1))

        numbers: list[str] = []
        numbers.extend(re.findall(r"№\s*(\d{6})", window, flags=re.IGNORECASE))
        numbers.extend(re.findall(r"\bNo\.?\s*(\d{6})", window, flags=re.IGNORECASE))
        for j in range(len(window_blocks) - 1):
            left = window_blocks[j].strip()
            right = window_blocks[j + 1].strip()
            if left in {"№", "No", "No."} or re.fullmatch(r"№\s*", left):
                if re.fullmatch(r"\d{6}", right):
                    numbers.append(right)
        # Заголовок «Претензия…»/«исх.»: только целый блок из 6 цифр (как после «№»),
        # а не фрагменты номера договора «07.663212-ТЭ» и не индекс «125009, город…».
        if re.search(r"претенз|исх(?:\.|од)", window, flags=re.IGNORECASE):
            for block in window_blocks:
                if re.fullmatch(r"\d{6}", block.strip()):
                    numbers.append(block.strip())
        numbers = [n for n in numbers if n not in postal_nums]
        # уникальные с сохранением порядка
        return list(dict.fromkeys(numbers))


def _html_fragments(html: str) -> list[str]:
    """Делит склейку постраничных HTML-документов Docling на отдельные документы.

    lxml останавливается на первом ``</html>``, поэтому страница с пунктом об оплате
    иначе не попадает в поиск.
    """
    if not html or not str(html).strip():
        return []
    html = str(html)
    doctype_starts = [
        match.start() for match in re.finditer(r"(?i)<!DOCTYPE\s+html\b", html)
    ]
    if len(doctype_starts) > 1 or (len(doctype_starts) == 1 and doctype_starts[0] > 0):
        starts = doctype_starts
    else:
        starts = [match.start() for match in re.finditer(r"(?i)<html\b", html)]
    if len(starts) <= 1:
        return [html]
    fragments: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html)
        fragment = html[start:end].strip()
        if fragment:
            fragments.append(fragment)
    return fragments or [html]


def _find_html_tags(html: str, tags: list[str]):
    found = []
    for fragment in _html_fragments(html):
        soup = BeautifulSoup(fragment, "lxml")
        found.extend(soup.find_all(tags))
    return found


class PDFContractParser:

    def __init__(self, device='cuda') -> None:
        pipeline_options = _docling_pipeline_options_low_memory(
            use_cuda=torch.cuda.is_available() and device == "cuda"
        )

        pipeline_options.ocr_options = _tesseract_cli_ocr_options()

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )

        start_time = time.time()
        self.doc_converter.initialize_pipeline(InputFormat.PDF)

        init_runtime = time.time() - start_time
        self.morph = pymorphy3.MorphAnalyzer(lang='ru')

        _log.info(f"Pipeline initialized in {init_runtime:.2f} seconds.")

    def analyse_contract(self, path_to_file: str | Path, config:AppConfig):
        """
        Docstring для analyse_contract

        :param self: Описание
        :param path_to_file: Описание
        :type path_to_file: str | Path
        :param config: Описание
        :type config: AppConfig

        returns
        tuple (тип договора, пункт договора, день, текст)

        """
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        contract_documents = self._parse_contract_documents(path_to_file)
        conv_result_html = documents_export_to_html(contract_documents)
        write_pdf_sidecar_html(path_to_file, conv_result_html)
        # print(conv_result_html)
        type_of_service = self._find_type_of_contract(conv_result_html, path_to_file)
        if type_of_service not in ['ФОТЭ', 'не удалось определить тип договора']:
            point_of_contract, overdue_day, result_text = self._find_point_of_overdue_date(conv_result_html,
                                                                keywords=config.point_overdue_keywords,
                                                                excluded_words=config.point_overdue_excluded)
        elif type_of_service == 'ФОТЭ':
            return type_of_service, '-', '15', 'Данный тип договора является актом ФОТЭ, согласно закону базовый день начала просрочки - 15-е число месяца'


        else:
            _log.warning(
                "Contract type not determined for %s; returning defaults without payment clause",
                path_to_file,
            )
            return type_of_service, '-', '18', type_of_service
        # type_of_service = self._find_point_of_service_type(conv_result_html,
        #                                                    keywords=config.service_type_keywords,
        #                                                    excluded_words=config.service_type_excluded)
        release_memory()
        return type_of_service, point_of_contract, overdue_day, result_text

    _TYPE_UNKNOWN = "не удалось определить тип договора"

    # Латиница, визуально похожая на кириллицу (частый OCR-шум в шапке договора).
    _OCR_LATIN_LOOKALIKES = str.maketrans({
        "A": "А", "a": "а",
        "B": "В",
        "C": "С", "c": "с",
        "E": "Е", "e": "е",
        "H": "Н",
        "K": "К", "k": "к",
        "M": "М",
        "O": "О", "o": "о",
        "P": "Р", "p": "р",
        "T": "Т", "t": "т",
        "X": "Х", "x": "х",
        "Y": "У", "y": "у",
    })

    def _normalize_ocr_contract_text(self, text: str) -> str:
        """Нормализует OCR-текст шапки/номера договора для поиска типа."""
        if not text:
            return ""
        # Сначала латинские коды типов на исходном тексте (до lookalike-замен).
        normalized = text
        for pattern, repl in (
            (r"(?i)\bfote\b", "ФОТЭ"),
            (r"(?i)\bgvs\b", "ГВС"),
            (r"(?i)\bsoi\b", "СОИ"),
            (r"(?i)(?<![A-Za-zА-Яа-яЁё])te(?![A-Za-zА-Яа-яЁё])", "ТЭ"),
            (r"(?i)-\s*te(?![A-Za-zА-Яа-яЁё])", "-ТЭ"),
        ):
            normalized = re.sub(pattern, repl, normalized)
        normalized = normalized.translate(self._OCR_LATIN_LOOKALIKES)
        # После lookalike: «ТЕ»/«ФОТЕ» как кириллические токены → канонические коды.
        normalized = re.sub(r"(?i)\bфоте\b", "ФОТЭ", normalized)
        normalized = re.sub(r"(?i)\bте\b", "ТЭ", normalized)
        # OCR «ТтЭ» / «Т-Э» в номере договора.
        normalized = re.sub(r"(?i)Т\s*т\s*Э", "ТЭ", normalized)
        normalized = re.sub(r"(?i)Т\s*-\s*Э", "ТЭ", normalized)
        return normalized

    def _type_from_type_code(
        self, text: str, *, require_number_context: bool = False
    ) -> str | None:
        """Тип по коду в имени файла / номере договора (ФОТЭ раньше ТЭ)."""
        normalized = self._normalize_ocr_contract_text(text)
        if not normalized:
            return None
        # Суффиксы номера (…-ТЭ, …064ГВС) — высокий приоритет, меньше ложных «ВВП ГВС».
        number_suffix_patterns: list[tuple[str, str]] = [
            (r"(?i)\d\s*[-_/]?\s*ФОТЭ(?:[^А-Яа-яЁё]|$)", "ФОТЭ"),
            (r"(?i)\dГВС(?:[^А-Яа-яЁё]|$)", "ГВС"),
            (r"(?i)\d\s*[-_/]\s*ТЭ(?:[^А-Яа-яЁё]|$)", "ТЭ"),
            (r"(?i)[-_/]\s*ТЭ(?:[^А-Яа-яЁё]|$)", "ТЭ"),
            (r"(?i)(?:№|No\.?)\s*[^\n]{0,40}?ФОТЭ", "ФОТЭ"),
            (r"(?i)(?:№|No\.?)\s*[^\n]{0,40}?ГВС", "ГВС"),
            (r"(?i)(?:№|No\.?)\s*[^\n]{0,40}?ТЭ", "ТЭ"),
            (r"(?i)(?:№|No\.?)\s*[^\n]{0,40}?СОИ", "СОИ"),
        ]
        for pattern, contract_type in number_suffix_patterns:
            if re.search(pattern, normalized):
                return contract_type
        if require_number_context:
            return None
        # Отдельный токен (имя файла / короткая шапка).
        token_patterns: list[tuple[str, str]] = [
            (r"(?i)(?:^|[^А-Яа-яЁё])ФОТЭ(?:[^А-Яа-яЁё]|$)", "ФОТЭ"),
            (r"(?i)(?:^|[^А-Яа-яЁё])СОИ(?:[^А-Яа-яЁё]|$)", "СОИ"),
            (r"(?i)(?:^|[^А-Яа-яЁё])ГВС(?:[^А-Яа-яЁё]|$)", "ГВС"),
            (r"(?i)(?:^|[^А-Яа-яЁё])ТЭ(?:[^А-Яа-яЁё]|$)", "ТЭ"),
        ]
        for pattern, contract_type in token_patterns:
            if re.search(pattern, normalized):
                return contract_type
        return None

    def _type_from_title_keywords(self, text_lower: str) -> str | None:
        """Тип по формулировкам заголовка (без широкого скана всего договора)."""
        soi_keywords = (
            "целей содержания общего имущества",
            "цели содержания общего имущества",
            "содержание общего имущества",
        )
        te_keywords = (
            "договор теплоснабжения",
            "контракт теплоснабжения",
            "на снабжение тепловой",
            "снабжение тепловой энергией",
            "поставка тепловой энергии",
        )
        # Без голых «горячего водоснабжения» / «ГВС»: они часто встречаются в договорах ТЭ.
        gvs_keywords = (
            "договор горячего водоснабжения",
            "договор поставки горячей воды",
            "контракт горячего водоснабжения",
        )
        fote_keywords = (
            "акт проверки",
            "акта проверки",
            "фотэ",
        )
        for keyword in soi_keywords:
            if keyword in text_lower:
                return "СОИ"
        for keyword in te_keywords:
            if keyword in text_lower:
                return "ТЭ"
        for keyword in gvs_keywords:
            if keyword in text_lower:
                return "ГВС"
        for keyword in fote_keywords:
            if keyword in text_lower:
                return "ФОТЭ"
        return None

    def _find_type_of_contract(
        self,
        parsed_html: str,
        path_to_file: str | Path | None = None,
    ) -> str:
        """
        Определяет тип договора (ТЭ / ГВС / ФОТЭ / СОИ).

        Источники сигнала (по приоритету): имя файла, строки с «Договор №» / титул,
        коды типа в первых блоках HTML, затем keyword-эвристика по кандидатам.
        """
        if path_to_file is not None:
            from_name = self._type_from_type_code(Path(path_to_file).name)
            if from_name:
                return from_name

        # Короткие/заголовочные блоки — для кодов типа; длинные div/li дают ложные «ГВС».
        heading_tags = ("title", "h1", "h2", "h3")
        body_tags = ("p", "div", "li", "td")
        max_code_block_len = 280

        heading_blocks: list[str] = []
        short_blocks: list[str] = []
        legacy_blocks: list[str] = []  # как раньше: в основном h1/h2/p

        for elem in _find_html_tags(
            parsed_html or "", list(heading_tags) + list(body_tags)
        ):
            text_elem = elem.get_text(" ", strip=True)
            if len(text_elem) <= 2:
                continue
            tag = elem.name
            if tag in heading_tags:
                heading_blocks.append(text_elem)
            if len(text_elem) <= max_code_block_len:
                short_blocks.append(text_elem)
            if tag in ("h1", "h2", "h3", "p"):
                legacy_blocks.append(text_elem)

        contract_line_re = re.compile(
            r"договор.{0,80}?№|контракт.{0,40}?№|акт\s+проверки|акта\s+проверки",
            re.IGNORECASE | re.DOTALL,
        )

        # 1) Строки с «Договор … №» / актом — код типа и титульные фразы.
        for text_elem in heading_blocks + short_blocks[:50]:
            normalized = self._normalize_ocr_contract_text(text_elem)
            low = normalized.lower()
            if not contract_line_re.search(low):
                continue
            from_code = self._type_from_type_code(normalized)
            if from_code:
                return from_code
            from_title = self._type_from_title_keywords(low)
            if from_title:
                return from_title

        # 2) Титульные фразы в заголовках — раньше голых кодов («ВВП ГВС»).
        for text_elem in heading_blocks:
            from_title = self._type_from_title_keywords(
                self._normalize_ocr_contract_text(text_elem).lower()
            )
            if from_title:
                return from_title

        # 3) Коды в заголовках; в коротких блоках — только рядом с номером.
        for text_elem in heading_blocks:
            from_code = self._type_from_type_code(
                self._normalize_ocr_contract_text(text_elem)
            )
            if from_code:
                return from_code
        for text_elem in short_blocks[:50]:
            from_code = self._type_from_type_code(
                self._normalize_ocr_contract_text(text_elem),
                require_number_context=True,
            )
            if from_code:
                return from_code

        # 4) Титульные фразы в коротких блоках.
        for text_elem in short_blocks[:50]:
            from_title = self._type_from_title_keywords(
                self._normalize_ocr_contract_text(text_elem).lower()
            )
            if from_title:
                return from_title

        # 5) Legacy: леммы по h1/h2/h3/p (без длинных div).
        valid_values_keywords = ["акт", "договор", "контракт", "гвс", "тэ", "фотэ", "сои"]
        valid_values_keywords_lemmatized = {
            self._lemmatize_word(elem) for elem in valid_values_keywords
        }
        valid_values: list[str] = []
        for text_elem in legacy_blocks:
            text_elem_lemmatized = self._lemmatize_words(text_elem)
            if valid_values_keywords_lemmatized & text_elem_lemmatized:
                valid_values.append(
                    self._normalize_ocr_contract_text(text_elem).lower()
                )

        for valid_elem in valid_values[:20]:
            if len(valid_elem) <= max_code_block_len:
                from_code = self._type_from_type_code(
                    valid_elem, require_number_context=True
                )
                if from_code:
                    return from_code
            from_title = self._type_from_title_keywords(valid_elem)
            if from_title:
                return from_title

        return self._TYPE_UNKNOWN

    def _convert_contract_pdf_chunked(self, path_to_file: Path) -> list[DoclingDocument]:
        """OCR: постранично; при OOM возвращает обработанные страницы."""
        page_count = _get_contract_page_count(path_to_file)
        _log.info(
            "Contract PDF has %s page(s), converting with OCR one-by-one: %s",
            page_count,
            path_to_file,
        )
        documents, pages_ok, last_error = convert_pdf_pages(
            self.doc_converter,
            path_to_file,
            page_count=page_count,
            log_prefix="contract-OCR",
        )
        if last_error and not documents:
            if is_allocation_error(last_error):
                return []
            raise RuntimeError(
                f"Conversion failed for {path_to_file}: {last_error}"
            ) from last_error
        _log.info(
            "Contract OCR: %s/%s page(s) converted: %s",
            pages_ok,
            page_count,
            path_to_file,
        )
        return documents

    def _convert_contract_pdf_chunked_no_ocr(
        self, path_to_file: Path
    ) -> list[DoclingDocument]:
        """Без OCR: постранично; пустой список, если текста нет."""
        page_count = _get_contract_page_count(path_to_file)
        _log.info(
            "Starting conversion (text layer, no OCR), %s page(s): %s",
            page_count,
            path_to_file,
        )

        pipeline_options = _docling_pipeline_options_low_memory(
            use_cuda=torch.cuda.is_available()
        )
        pipeline_options.do_ocr = False

        doc_converter_no_ocr = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        doc_converter_no_ocr.initialize_pipeline(InputFormat.PDF)

        documents, pages_ok, last_error = convert_pdf_pages(
            doc_converter_no_ocr,
            path_to_file,
            page_count=page_count,
            log_prefix="contract-no-OCR",
        )
        del doc_converter_no_ocr

        if last_error and not documents:
            if is_allocation_error(last_error):
                return []
            _log.warning(
                "Contract no-OCR stopped at page %s/%s: %s",
                pages_ok + 1,
                page_count,
                last_error,
            )

        if not documents:
            return []

        if documents_have_text(documents):
            return documents

        return []

    def _parse_contract_documents(self, path_to_file: Path) -> list[DoclingDocument]:
        start_time = time.time()

        documents = self._convert_contract_pdf_chunked_no_ocr(path_to_file)
        if documents:
            _log.info(
                "Document converted without OCR in %.2f seconds (%s page chunk(s)).",
                time.time() - start_time,
                len(documents),
            )
            return documents

        _log.info(
            "Text layer not found or empty, falling back to OCR (chunked conversion)."
        )
        documents = self._convert_contract_pdf_chunked(path_to_file)
        if not documents:
            raise RuntimeError(f"No pages converted for contract PDF: {path_to_file}")
        _log.info(
            "Document converted in %.2f seconds (%s page chunk(s)).",
            time.time() - start_time,
            len(documents),
        )
        return documents

    def _parse_contract_text(self, path_to_file: str | Path) -> DoclingDocument:
        """Совместимость с тестами: объединённый DoclingDocument или первый фрагмент."""
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        documents = self._parse_contract_documents(path_to_file)
        merged, _ = concatenate_documents(documents)
        if merged is not None:
            return merged
        if documents:
            return documents[0]
        raise RuntimeError(f"No pages converted for contract PDF: {path_to_file}")

    _PAYMENT_DEADLINE_RE = re.compile(
        r"(?is)(?:оплат\w*|оплачива\w*).{0,120}?до\s+(\d{1,2})(?:-?\s*го)?\s+числ"
        r"|до\s+(\d{1,2})(?:-?\s*го)?\s+числ\w*.{0,80}?(?:оплат\w*|оплачива\w*)"
    )
    _POINT_AT_START_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)*)")
    _POINT_EXPLICIT_RE = re.compile(
        r"(?i)(?:пункт\w*|п)\s*\.?\s*(\d+(?:[.,]\d+)*)"
    )
    _DAY_UNTIL_RE = re.compile(
        r"(?i)до\s+(\d{1,2})(?:-?\s*го)?\s+числ"
    )

    @staticmethod
    def _normalize_contract_point(raw: str | None) -> str | None:
        """Нормализует пункт к виду 7.2 (точка вместо запятой)."""
        if not raw:
            return None
        return raw.strip().replace(",", ".")

    def _extract_contract_point(self, text: str) -> str | None:
        """Ищет номер пункта в начале строки, «п. 7.2» / «пункт 5.5»."""
        if not text:
            return None
        m = self._POINT_AT_START_RE.match(text)
        if m:
            return self._normalize_contract_point(m.group(1))
        m = self._POINT_EXPLICIT_RE.search(text)
        if m:
            return self._normalize_contract_point(m.group(1))
        return None

    def _is_payment_deadline_clause(self, text: str) -> bool:
        return bool(text and self._PAYMENT_DEADLINE_RE.search(text))

    def _text_with_following_deadline(self, text: str, candidates, index: int) -> str:
        """Добавляет соседние строки, если «до N числа» вынесено из пункта в список."""
        if self._find_day_overdue_suggestions(text):
            return text
        parts = [text]
        for elem in candidates[index + 1 : index + 8]:
            following = elem.get_text(" ", strip=True)
            if not following:
                continue
            if self._POINT_AT_START_RE.match(following):
                break
            parts.append(following)
            joined = "\n".join(parts)
            if self._find_day_overdue_suggestions(joined):
                return joined
        return text

    def _find_point_of_overdue_date(
        self, parsed_html_text: str, keywords: dict, excluded_words: list
    ):
        finded_text, candidates = self._find_top5_elements_weighted(
            parsed_html_text, keywords, excluded_words
        )
        # Предпочитаем абзацы «оплата … до N числа» среди top-N.
        if finded_text:
            payment_first = [
                item
                for item in finded_text
                if self._is_payment_deadline_clause(item[0])
            ]
            ordered = payment_first + [
                item for item in finded_text if item not in payment_first
            ]
            contract_point, result_text = self._find_point_overdue_suggestions(
                ordered, candidates
            )
            if result_text:
                overdue_day = self._find_day_overdue_suggestions(result_text)
                point_out = (
                    contract_point
                    if contract_point and "не удалось" not in contract_point.lower()
                    else "Не удалось найти пункт"
                )
                return point_out, overdue_day, result_text

        # Fallback: прямой поиск платёжной оговорки по всем страницам.
        elements = _find_html_tags(parsed_html_text or "", ["p", "li"])
        for index, elem in enumerate(elements):
            text = elem.get_text(" ", strip=True)
            point = self._extract_contract_point(text)
            window = text
            if point and self._check_contract_point(text):
                window = self._text_with_following_deadline(text, elements, index)
            if not self._is_payment_deadline_clause(window):
                continue
            day = self._find_day_overdue_suggestions(window)
            resolved_point = point or self._extract_contract_point(window)
            if resolved_point or day:
                return (
                    resolved_point or "Не удалось найти пункт",
                    day,
                    window,
                )

        return "Не удалось найти пункт", None, None

    #FIXME нужно брать информацию из шапки договора
    def _find_point_of_service_type(self, parsed_html_text:str, keywords:dict, excluded_words:list):
        service_type_key_words_list_weighted = keywords
        finded_text, candidates = self._find_top5_elements_weighted(parsed_html_text, service_type_key_words_list_weighted, excluded_words)

        # print(finded_text)
        if len(finded_text) > 0:
            return finded_text[0][0]
        else:
            return "К сожалению, не удалось распознать часть текста"

    def _find_point_overdue_suggestions(
        self, perspective_elems: list[tuple[str, int, int]], candidates
    ):
        for perspective_elem in perspective_elems:
            elem_text, _, current_index = perspective_elem
            point = self._extract_contract_point(elem_text)
            if point and (
                self._is_payment_deadline_clause(elem_text)
                or self._check_contract_point(elem_text)
            ):
                return point, self._text_with_following_deadline(
                    elem_text, candidates, current_index
                )
            if point and self._find_day_overdue_suggestions(elem_text):
                return point, self._text_with_following_deadline(
                    elem_text, candidates, current_index
                )

            zone_of_interest = [
                elem.get_text()
                for elem in candidates[max(0, current_index - 5) : current_index]
            ]
            flag = False
            for elem in zone_of_interest[::-1]:
                point = self._extract_contract_point(elem)
                if point is None:
                    continue
                flag = bool(self._check_contract_point(elem))
                if flag:
                    return point, self._text_with_following_deadline(
                        elem + "\n" + elem_text, candidates, current_index
                    )
            if not flag:
                continue

            # Последний шанс по текущему абзацу: пункт в середине («п. 7.2»).
            point = self._extract_contract_point(elem_text)
            if point:
                return point, self._text_with_following_deadline(
                    elem_text, candidates, current_index
                )

        return "Не удалось найти пункт", None

    def _find_day_overdue_suggestions(self, result_text: str):
        """День оплаты: приоритет «до N числа», диапазон 1–28."""
        if not result_text:
            return None

        # Убираем номер пункта в начале, чтобы не спутать с днём.
        cleaned = re.sub(r"^\s*\d+(?:[.,]\d+)*\s*[.]?\s*", "", result_text).lstrip()

        m = self._DAY_UNTIL_RE.search(cleaned)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 28:
                return str(day)

        # «N числа» без «до», но рядом с оплатой.
        m = re.search(r"(?i)(\d{1,2})(?:-?\s*го)?\s+числ", cleaned)
        if m and self._is_payment_deadline_clause(result_text):
            day = int(m.group(1))
            if 1 <= day <= 28:
                return str(day)

        return None

    def _check_contract_point(self, elem: str) -> bool:
        keywords = ["производит", "оплату", "сроки", "оплачивает", "оплата"]
        excl_word = [
            "энергоснабжающая",
            "передает",
            "выставляет",
            "показаний",
            "снимаются",
        ]
        keywords_lemmatized = {self._lemmatize_word(w) for w in keywords}
        excl_word_lemmatized = {self._lemmatize_word(w) for w in excl_word}
        elem_lemmatized = self._lemmatize_words(elem)

        if excl_word_lemmatized & elem_lemmatized:
            return False

        if keywords_lemmatized & elem_lemmatized:
            return True
        return False

    def _find_top5_elements_weighted(self,
        html: str,
        keyword_weights: dict[str, int],
        exclude_words: list[str] | None = None
    ):
        if not keyword_weights:
            return []

        # Лемматизация ключевых слов и исключений
        query_weights = {
            self._lemmatize_word(word): weight
            for word, weight in keyword_weights.items()
        }

        exclude_lemmas = set()
        if exclude_words:
            exclude_lemmas = {self._lemmatize_word(w) for w in exclude_words}

        candidates = _find_html_tags(html, ["p", "li"])

        scored = []

        for i, elem in enumerate(candidates):
            text = elem.get_text()
            if not text.strip():
                continue

            elem_lemmas = self._lemmatize_words(text)

            # Отбрасываем, если есть исключения
            if exclude_lemmas & elem_lemmas:
                continue

            # Считаем взвешенную сумму
            total_weight = sum(
                query_weights[lemma]
                for lemma in elem_lemmas
                if lemma in query_weights
            )

            if total_weight > 0:
                scored.append((self._strip_html(str(elem)), total_weight, i))

        top5 = sorted(scored, key=lambda x: x[1], reverse=True)[:5]
        return top5, candidates


    def _lemmatize_words(self, text: str) -> set[str]:
        """Извлекает слова и возвращает множество лемм (в нижнем регистре)."""
        # Извлекаем только буквы (игнорируем цифры, пунктуацию)
        words = re.findall(r'[а-яё]+', text.lower())  # только кириллица
        lemmas = {self.morph.parse(w)[0].normal_form for w in words if w}
        return lemmas

    def _lemmatize_word(self, word: str) -> str:
        """Лемматизирует одно слово."""
        return self.morph.parse(word.lower())[0].normal_form

    def _strip_html(self, html: str) -> str:
        """
        Удаляет HTML-теги с помощью регулярных выражений и декодирует HTML-сущности.
        """
        if not html:
            return ""
        # Удаляем теги
        text = re.sub(r'<[^>]+>', '', html)
        # Декодируем сущности: &amp; → &, &lt; → < и т.д.
        text = html_parser.unescape(text)
        # Убираем лишние пробелы (опционально)
        text = re.sub(r'\s+', ' ', text).strip()
        return text