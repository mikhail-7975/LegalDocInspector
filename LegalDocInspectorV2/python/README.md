# legaldoc-v2 (OCR engine)

Абстракция OCR-движка с подменой реализации через конфиг (`LegalDocInspectorV2/config/ocr_engine.yaml`).

## Установка

```bash
cd LegalDocInspectorV2/python
pip install -e ".[docling]"
```

Без `[docling]` пакет ставится без тяжёлых зависимостей; класс `DoclingOcrEngine` импортируется только при `backend: docling`.

## Конфиг

См. `../config/ocr_engine.yaml`. Поле `backend`: `docling` (реализация, эквивалентная текущему пайплайну в `parser_models.py`: Docling + при необходимости EasyOCR).

## Использование

### OCR

```python
from pathlib import Path
from legaldoc_v2.ocr import load_ocr_engine_from_config, PdfOcrMode

engine = load_ocr_engine_from_config()
doc = engine.convert_pdf(Path("sample.pdf"), mode=PdfOcrMode.EASYOCR_FULL_PAGE, page_range=(1, 30))
engine.close()
```

### Заглушка парсера договора

Ждёт 10 секунд и возвращает четырёхэлементный кортеж, где все значения — «введите данные вручную» (как у ``PDFContractParser.analyse_contract``):

```python
from legaldoc_v2.parsers import ContractParserStub

stub = ContractParserStub()
t = stub.analyse_contract("dogovor.pdf", config=None)  # (str, str, str, str)
```
