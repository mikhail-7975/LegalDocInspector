import datetime
import logging
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
import pymorphy2
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

_log = logging.getLogger(__name__)

KEYWORDS = ['публичное', 'пао', 'акционерное', 'общество']
SKIP_PHRASES = [r'справка.*прохождении.*документа']
SKIP_LINES_AFTER_MATCH = 5

logging.getLogger("docling").setLevel(logging.WARNING)
_log.setLevel(logging.INFO)

class PDFClaimParser:
    def __init__(self) -> None:
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

        
    def _parse_claim_text(self, path_to_file: str | Path) -> DoclingDocument:
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
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
        return claims

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

    def __init__(self) -> None:
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
        self.morph = pymorphy2.MorphAnalyzer(lang='ru')

        _log.info(f"Pipeline initialized in {init_runtime:.2f} seconds.")

    def _parse_contract_text(self, path_to_file: str| Path) -> DoclingDocument:
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        start_time = time.time()
        _log.info(f"Starting conversion of document: {path_to_file}")
        conv_result = self.doc_converter.convert(path_to_file, page_range=(1,30))
        if conv_result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Conversion failed for {path_to_file}")
        _log.info(f"Document converted in {time.time() - start_time:.2f} seconds.")
        return conv_result.document
    
    def analyse_contract(self, path_to_file: str | Path):
        conv_result = self._parse_contract_text(path_to_file)
        conv_result_html = conv_result.export_to_html()
        print(conv_result_html)
        response = self._find_point_of_overdue_date(conv_result_html)
        return response

    def _find_point_of_overdue_date(self, parsed_html_text:str):
        service_type_key_words_list_weighted = {"срок":2, "числа":2, "месяца":2, "производится":1,"оплата":3, "расчётным":2, "период":2 , "следующего":2, "оплачивает":3}
        exclude_words = ["оформляет", "регулирует", "помещения", "дубликатов", "льгот", "распределяются", "Ресурсоснабжающая", "ОДПУ", "указания"]
        finded_text = self._find_top5_elements_weighted(parsed_html_text, service_type_key_words_list_weighted, exclude_words)
        print(finded_text)
        return finded_text[0][0]
    


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

        for elem in candidates:
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
                scored.append((self._strip_html(str(elem)), total_weight))

        # Топ-5 по весу
        top5 = sorted(scored, key=lambda x: x[1], reverse=True)[:5]
        return top5
    

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