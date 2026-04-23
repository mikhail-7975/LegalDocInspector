import datetime
import logging
import time
from pathlib import Path
import torch
import numpy as np
from pydantic import TypeAdapter
from typing import Any, Optional, List, Tuple
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
    TesseractOcrOptions,
    TesseractCliOcrOptions,
    EasyOcrOptions,
    OcrMacOptions,
    RapidOcrOptions,
    OcrAutoOptions
)
from rapidfuzz import fuzz

from bs4 import BeautifulSoup
import re
import gc

from configs.config import AppConfig

_log = logging.getLogger(__name__)

KEYWORDS = ['публичное', 'пао', 'акционерное', 'общество']
SKIP_PHRASES = [r'справка.*прохождении.*документа']
SKIP_LINES_AFTER_MATCH = 5

logging.getLogger("docling").setLevel(logging.WARNING)
_log.setLevel(logging.INFO)

class PDFClaimParser:
    def __init__(self, ocr_engine: Any | None = None) -> None:
        """
        :param ocr_engine: опционально движок из LegalDocInspectorV2 (legaldoc_v2.ocr.OcrEngine);
            иначе встроенный Docling-пайплайн в этом модуле.
        """
        self._ocr_engine = ocr_engine
        if ocr_engine is not None:
            self.doc_converter = None
            return

        pipeline_options = ThreadedPdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU,
                num_threads=64

            ),
            ocr_batch_size=4,
            layout_batch_size=16,
            table_batch_size=4,
            do_ocr=True,
            do_table_structure= True
        )

        # pipeline_options.ocr_options = EasyOcrOptions(lang=['ru'], force_full_page_ocr=True) # лучший вариант
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

    def _parse_doc_with_ocr(self, path_to_file: str | Path) -> DoclingDocument:
        if self._ocr_engine is not None:
            from legaldoc_v2.ocr.engine import PdfOcrMode

            p = Path(path_to_file)
            return self._ocr_engine.convert_pdf(p, mode=PdfOcrMode.EASYOCR_FULL_PAGE)

        pipeline_options = ThreadedPdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU,
                num_threads=64

            ),
            ocr_batch_size=4,
            layout_batch_size=16,
            table_batch_size=4,
            do_ocr=True,
            do_table_structure= True
        )

        pipeline_options.ocr_options = EasyOcrOptions(lang=['ru'], force_full_page_ocr=True) # лучший вариант
        # pipeline_options.ocr_options = PdfPipelineOptions()

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
        _log.info(f"Starting conversion of document - ocr attempt: {path_to_file}")
        conv_result = doc_converter_ocr.convert(path_to_file)
        if conv_result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Conversion failed for {path_to_file}")
        _log.info(f"Document converted in {time.time() - start_time:.2f} seconds.")

        del doc_converter_ocr
        return conv_result.document




    def _parse_claim_text(self, path_to_file: str | Path) -> DoclingDocument:
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        if self._ocr_engine is not None:
            from legaldoc_v2.ocr.engine import PdfOcrMode

            return self._ocr_engine.convert_pdf(path_to_file, mode=PdfOcrMode.DEFAULT)

        start_time = time.time()
        _log.info(f"Starting conversion of document: {path_to_file}")
        conv_result = self.doc_converter.convert(path_to_file)
        if conv_result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Conversion failed for {path_to_file}")
        _log.info(f"Document converted in {time.time() - start_time:.2f} seconds.")
        return conv_result.document

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
        document = self._parse_claim_text(path_to_file)
        data = list(document.export_to_dict().values())

        text_pairs = self._extract_text_with_page(data)
        claims = self._parse_claim_number_and_date(text_pairs)
        if len(claims)==0 :
            document = self._parse_doc_with_ocr(path_to_file)
            data = list(document.export_to_dict().values())
            text_pairs = self._extract_text_with_page(data)
            claims = self._parse_claim_number_and_date(text_pairs)
        torch.cuda.empty_cache()
        claims = self._standartize_claims(claims)
        if len(claims) == 0:
            claims = [{"claim-date": "Не удалось распознать дату", "claim_number" : "Не удалось распознать номер"}]
        return claims

    def _standartize_claims(self, claims:list[tuple[str | None, str | None]]):
        response = []
        for number, date in claims:
            claim_dict = {"claim_date": str(date), "claim_number": str(number)}
            response.append(claim_dict)
        return response

    def _parse_claim_number_and_date(self, texts_with_pages: List[Tuple[int, str]]) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Принимает список пар [(страница, текст), ...].
        Возвращает (номер_претензии, дата_претензии).
        """
        date_pattern = re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b')
        number_pattern = re.compile(r'\b\d{6}\b')
        skip_pages = set()
        for page, text in texts_with_pages:
            if re.search(r'справка.*прохождении', text, re.IGNORECASE):
                skip_pages.add(page)

        # Сгруппируем тексты по страницам
        from collections import defaultdict
        pages_dict = defaultdict(list)
        for page, text in texts_with_pages:
            if page not in skip_pages:
                pages_dict[page].append(text)
        response = []
        for page in list(pages_dict.keys()):
            date_flag = False
            num_flag = False
            number = None
            date = None
            for string in pages_dict[page]:
                match1 = number_pattern.search(string)
                match2 = date_pattern.search(string)

                # print(match1, match2)

                if match1 and match2:
                    # print(string)
                    # print(match2.group())
                    # print(match1.group())
                    number = match1.group()
                    date = match2.group()
                    date_flag = True
                    num_flag = True

                if match2 and len(string)<11:
                    # print(string)
                    # print(match2.group())
                    date = match2.group()

                    date_flag = True
                if match1 and len(string)<7:
                    # print(string)
                    # print(match1.group())
                    number = match1.group()

                    num_flag = True

                if num_flag and date_flag:
                    response.append((number, date ))
                    break

        return response


class PDFContractParser:

    def __init__(self, device='cuda', ocr_engine: Any | None = None) -> None:
        """
        :param ocr_engine: опционально движок LegalDocInspectorV2; иначе встроенный Docling+EasyOCR.
        """
        self._ocr_engine = ocr_engine
        if ocr_engine is not None:
            self.doc_converter = None
            self.morph = pymorphy3.MorphAnalyzer(lang='ru')
            return

        pipeline_options = ThreadedPdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=AcceleratorDevice.CUDA if (torch.cuda.is_available() and device=='cuda') else AcceleratorDevice.CPU,
                num_threads=64
            ),
            ocr_batch_size=4,
            layout_batch_size=16,
            table_batch_size=4,
            do_ocr=True,
            do_table_structure= True
        )

        pipeline_options.ocr_options = EasyOcrOptions(lang=['ru'], force_full_page_ocr=True) # лучший вариант

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
        conv_result = self._parse_contract_text(path_to_file)
        conv_result_html = conv_result.export_to_html()
        # print(conv_result_html)
        type_of_service = self._find_type_of_contract(conv_result_html)
        if type_of_service not in ['ФОТЭ', 'не удалось определить тип договора']:
            point_of_contract, overdue_day, result_text = self._find_point_of_overdue_date(conv_result_html,
                                                                keywords=config.point_overdue_keywords,
                                                                excluded_words=config.point_overdue_excluded)
        elif type_of_service == 'ФОТЭ':
            return type_of_service, '-', '15', 'Данный тип договора является актом ФОТЭ, согласно закону базовый день начала просрочки - 15-е число месяца'


        else:
            return type_of_service, '-', '18', type_of_service
        # type_of_service = self._find_point_of_service_type(conv_result_html,
        #                                                    keywords=config.service_type_keywords,
        #                                                    excluded_words=config.service_type_excluded)
        torch.cuda.empty_cache()
        return type_of_service, point_of_contract, overdue_day, result_text

    def _find_type_of_contract(self, parsed_html):
        soup = BeautifulSoup(parsed_html, 'lxml')
        candidates = soup.find_all(['h1','h2','p'])
        valid_values_keywords = ['акт','договор', 'контракт', 'гвс', 'тэ', 'фотэ', 'сои']

        valid_values_keywords_lemmatized = {self._lemmatize_word(elem) for elem in valid_values_keywords}
        valid_values = []

        for text_elem in [elem.get_text() for elem in candidates]:
            if len(text_elem)>2:
                text_elem_lemmatized = self._lemmatize_words(text_elem)
                if valid_values_keywords_lemmatized & text_elem_lemmatized:
                    valid_values.append(text_elem.lower())

        soi_keywords = ['целей содержания общего имущества', 'сои', 'cои']
        te_keywords = ['договор теплоснабжения', 'на снабжение тепловой']
        gvs_keywords = ['договор поставки горячей воды', 'горячей воды', 'гвс', 'горячего водоснабжения']
        fote_keywords = ['акт проверки', 'фотэ']
        for valid_elem in valid_values[:20]:
            for keyword in soi_keywords:
                if keyword in valid_elem:
                    return 'СОИ'
            for keyword in te_keywords:
                if keyword in valid_elem:
                    return 'ТЭ'
            for keyword in gvs_keywords:
                if keyword in valid_elem:
                    return 'ГВС'
            for keyword in fote_keywords:
                if keyword in valid_elem:
                    return 'ФОТЭ'

        return "не удалось определить тип договора"

    def _parse_contract_text(self, path_to_file: str| Path) -> DoclingDocument:
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        if self._ocr_engine is not None:
            from legaldoc_v2.ocr.engine import PdfOcrMode

            return self._ocr_engine.convert_pdf(
                path_to_file,
                mode=PdfOcrMode.EASYOCR_FULL_PAGE,
                page_range=(1, 30),
            )

        start_time = time.time()
        _log.info(f"Starting conversion of document: {path_to_file}")
        conv_result = self.doc_converter.convert(path_to_file, page_range=(1,30))
        if conv_result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Conversion failed for {path_to_file}")
        _log.info(f"Document converted in {time.time() - start_time:.2f} seconds.")
        return conv_result.document


    def _find_point_of_overdue_date(self, parsed_html_text:str, keywords:dict, excluded_words:list):
        point_overdue_key_words_list_weighted = keywords
        exclude_words = excluded_words
        finded_text, candidates = self._find_top5_elements_weighted(parsed_html_text, point_overdue_key_words_list_weighted, exclude_words)
        # print(finded_text)
        if len(finded_text) > 0:
            contract_point, result_text = self._find_point_overdue_suggestions(finded_text, candidates)
            overdue_day = self._find_day_overdue_suggestions(result_text)
            return contract_point, overdue_day, result_text
        else:
            return "К сожалению, не удалось распознать часть текста", None, None
    #FIXME нужно брать информацию из шапки договора
    def _find_point_of_service_type(self, parsed_html_text:str, keywords:dict, excluded_words:list):
        service_type_key_words_list_weighted = keywords
        finded_text, candidates = self._find_top5_elements_weighted(parsed_html_text, service_type_key_words_list_weighted, excluded_words)

        # print(finded_text)
        if len(finded_text) > 0:
            return finded_text[0][0]
        else:
            return "К сожалению, не удалось распознать часть текста"

    def _find_point_overdue_suggestions(self, perspective_elems:list[tuple[str, int, int]], candidates):
        pattern = r'^\d+(?:[.,]\d+)*'
        for perspective_elem in perspective_elems:
            elem_text, _ , current_index = perspective_elem
            # print(elem_text)

            matches = re.match(pattern, elem_text)
            if matches is not None:
                return matches.group(0), elem_text
            zone_of_interest = [elem.get_text() for elem in candidates[current_index-5:current_index]]
            # print(zone_of_interest)
            for elem in zone_of_interest[::-1]:
                matches = re.match(pattern, elem)
                # print(matches)
                if matches is not None:
                    flag = self._check_contract_point(elem)
                    if flag:
                        return matches.group(0), elem + '\n' + elem_text
                    else :
                        continue
            if not flag:
                continue

    def _find_day_overdue_suggestions(self, result_text: str):
    # Удаляем число из начала
        cleaned = re.sub(r'^\d+(?:[.,]\d+)*', '', result_text).lstrip()

        # Находим все элементы
        matches = re.findall(r'\d+|\n|числа', cleaned, flags=re.IGNORECASE)

        if '\n' in matches:
            # Ищем число между \n и "числа"
            for i in range(len(matches)):
                if matches[i] == '\n':
                    # Ищем число после \n
                    for j in range(i + 1, len(matches)):
                        if matches[j].isdigit():
                            # Проверяем, есть ли "числа" после этого числа
                            if 'числа' in [m.lower() for m in matches[j+1:]]:
                                return matches[j]
        else:
            # Ищем число перед "числа"
            for i in range(len(matches) - 1):
                if matches[i].isdigit() and matches[i+1].lower() == 'числа':
                    return matches[i]

        # Если не нашли по правилам, возвращаем первое число
        for elem in matches:
            if elem.isdigit():
                return elem

        return None

    def _check_contract_point(self, elem:str) -> bool:
        keywords = ["производит", "оплату", "сроки"]
        excl_word = ["энергоснабжающая", "передает", "выставляет"]
        keywords_lemmatized = {self._lemmatize_word(w) for w in keywords}
        excl_word_lemmatized = {self._lemmatize_word(w) for w in excl_word}
        elem_lemmatized = self._lemmatize_words(elem)

        if excl_word_lemmatized & elem_lemmatized:
            return False

        if keywords_lemmatized & elem_lemmatized:
            return True

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

        soup = BeautifulSoup(html, 'lxml')
        candidates = soup.find_all(['p', 'li'])

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