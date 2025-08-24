import os
import logging
from datetime import datetime
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
import pytesseract


# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler("ocr.log", encoding="utf-8"),
        logging.StreamHandler()  # вывод в консоль
    ]
)


class OCR:
    """
    Универсальный класс для извлечения текста из отсканированных PDF.
    Поддерживает разные OCR-движки. Сохраняет результат в Markdown.
    """

    def __init__(self, engine='tesseract', log_level=logging.INFO):
        self.engine = engine.lower()
        self.logger = logging.getLogger(f"OCR[{self.engine}]")
        self.logger.setLevel(log_level)

        supported_engines = ['tesseract', 'easyocr']
        if self.engine not in supported_engines:
            raise ValueError(f"OCR-движок '{self.engine}' не поддерживается. "
                             f"Доступные: {supported_engines}")

        if self.engine == 'tesseract':
            self._validate_tesseract()
        elif self.engine == 'easyocr':
            self.logger.warning("Режим 'easyocr' активирован. Реализация пока не добавлена.")


    def _validate_tesseract(self):
        """Проверка наличия Tesseract."""
        try:
            pytesseract.get_tesseract_version()
            self.logger.info("Tesseract найден: %s", pytesseract.get_tesseract_version())
        except (OSError, pytesseract.TesseractNotFoundError):
            self.logger.critical("Tesseract не установлен!")
            raise RuntimeError(
                "Tesseract не найден. Установите: sudo apt install tesseract-ocr tesseract-ocr-rus"
            )


    def extract_text(self, pdf_path):
        """
        Извлекает текст из PDF с помощью выбранного OCR-движка.

        :param pdf_path: Путь к PDF-файлу
        :return: Строка с текстом
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            self.logger.error("Файл не найден: %s", pdf_path)
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")

        self.logger.info("Начало обработки PDF: %s", pdf_path.name)

        if self.engine == 'tesseract':
            text = self._tesseract_ocr(pdf_path)
        elif self.engine == 'easyocr':
            text = self._easyocr_ocr(pdf_path)
        else:
            self.logger.error("Неизвестный OCR-движок: %s", self.engine)
            raise RuntimeError(f"Неизвестный движок: {self.engine}")

        self.logger.info("OCR завершён. Извлечено ~%d символов.", len(text))
        return text


    def _tesseract_ocr(self, pdf_path):
        """OCR через Tesseract."""
        self.logger.debug("Конвертируем PDF в изображения (dpi=300)...")
        images = convert_from_path(str(pdf_path), dpi=300)

        full_text = ""
        self.logger.info("Обработка %d страниц...", len(images))

        for i, image in enumerate(images):
            self.logger.debug("Распознавание страницы %d...", i + 1)

            # Предобработка
            image = image.convert("L")  # в оттенки серого

            # OCR
            text = pytesseract.image_to_string(image, lang='rus+eng')
            page_header = f"\n\n### Страница {i + 1}\n\n"
            full_text += page_header
            full_text += "```\n" + text.strip() + "\n```\n"

        return full_text.strip()


    def _easyocr_ocr(self, pdf_path):
        """Заглушка для EasyOCR."""
        self.logger.warning("EasyOCR пока не реализован.")
        raise NotImplementedError("Поддержка EasyOCR ещё не добавлена.")


    def save_as_markdown(self, text, output_path):
        """
        Сохраняет текст в формате Markdown.

        :param text: Текст для сохранения
        :param output_path: Путь к файлу .md
        """
        output_path = Path(output_path)

        # Автоматически добавим расширение .md, если его нет
        if output_path.suffix.lower() != '.md':
            output_path = output_path.with_suffix('.md')

        # Добавим заголовок и метаданные
        header = f"""# Извлечённый текст из PDF
> Обработано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> OCR-движок: {self.engine}

---

"""
        content = header + text

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info("Текст сохранён в Markdown: %s", output_path)
        except Exception as e:
            self.logger.error("Не удалось сохранить файл: %s", e)
            raise


    def extract_and_save(self, pdf_path, output_path=None):
        """
        Полный цикл: извлечь текст и сохранить в .md

        :param pdf_path: Путь к PDF
        :param output_path: Путь к .md файлу (опционально)
        :return: Путь к сохранённому файлу
        """
        text = self.extract_text(pdf_path)

        if output_path is None:
            # Автоимя: имя_файла_ocr_2025-04-05.md
            pdf_name = Path(pdf_path).stem
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            output_path = f"{pdf_name}_ocr_{timestamp}.md"

        self.save_as_markdown(text, output_path)
        return output_path
