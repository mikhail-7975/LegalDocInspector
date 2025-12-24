import datetime
import logging
import time
from pathlib import Path
import torch
import numpy as np
from pydantic import TypeAdapter
from docling.datamodel.settings import settings
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import (
    ThreadedPdfPipelineOptions,
)
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
from bs4 import BeautifulSoup
import re

_log = logging.getLogger(__name__)


logging.getLogger("docling").setLevel(logging.WARNING)
_log.setLevel(logging.INFO)

class PDFParserOCR:
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
            do_table_structure= False
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
        _log.info(f"Pipeline initialized in {init_runtime:.2f} seconds.")

        
    def _parse_claim_text(self, path_to_file: str | Path) -> str:
        if isinstance(path_to_file, str):
            path_to_file = Path(path_to_file)
        start_time = time.time()
        _log.info(f"Start cobverting document.")
        conv_result = self.doc_converter.convert(path_to_file)
        if conv_result.status == ConversionStatus.SUCCESS:
            pass
        else:
            raise RuntimeError()
        pipeline_runtime = time.time() - start_time
        _log.info(f"Document converted in {pipeline_runtime:.2f} seconds.")

        html_text = conv_result.document.export_to_html()
        return html_text
    
    def analyse_claim(self, path_to_file: str | Path):
        """
        Анализирует html-text претензии
        возвращает (claim_number, claim_date)
        
        :param self: Description
        :param html_text: Description
        """

        html_text = self._parse_claim_text(path_to_file)

        claim_number = self._find_claim_number(html_text)
        claim_date = self._find_claim_date(html_text)

        return claim_number, claim_date


    def _find_claim_number(self, html_text:str) -> str | None:
        candidates = []
        number_pattern = r'\b\d{6}\b'
        claim_element = None

        soup =  BeautifulSoup(html_text, "html.parser")
        start_parcing = False
        for elem in soup.find_all(['p', 'h1', 'h2']): 
            if elem.string:
                text = elem.get_text()
            else:
                text = elem.get_text(strip=True)
            if not start_parcing and re.search('публичное', text.lower()):
                start_parcing = True
            if start_parcing:
                candidates.append(text.lower())
            else:
                continue
            if re.search('претензия', text.lower(), re.IGNORECASE):
                claim_element = elem
                break
        if not claim_element:
            raise ValueError("Элемент не найден")

        for candidat in candidates:
            # print(candidat)
            # if not ['ул', 'телефон',]
            excluded_words = ['ул', 'телефон']
            if not any(word in candidat.lower() for word in excluded_words):

                if re.search(number_pattern, candidat) :
                    return re.search(number_pattern, candidat).group()
        
        return None
    

    def _find_claim_date(self, html_text:str):
            candidates = []
            claim_element = None
            date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
            start_parcing = False
            soup =  BeautifulSoup(html_text, "html.parser")
            for elem in soup.find_all(['p', 'h1', 'h2']): 
                if elem.string:
                    text = elem.get_text()
                else:
                    text = elem.get_text(strip=True)
                if not start_parcing and re.search('публичное', text.lower()):
                    start_parcing = True
                if start_parcing:
                    candidates.append(text.lower())
                else:
                    continue
                if re.search('претензия', text.lower(), re.IGNORECASE):
                    claim_element = elem
                    break
            if not claim_element:
                raise ValueError("Элемент не найден")
            print(candidates)
            for candidat in candidates:
                
                excluded_words = ['ул', 'телефон']
                if not any(word in candidat.lower() for word in excluded_words):
                    if re.search(date_pattern, candidat):
                        return re.search(date_pattern, candidat).group()
                        
            # вторая попытка
            for elem in soup.find_all(['p', 'h1', 'h2']):
                if re.search('по состоянию', elem.get_text().lower()):
                    return re.search(date_pattern, elem.get_text().lower()).group()
            
            
    

