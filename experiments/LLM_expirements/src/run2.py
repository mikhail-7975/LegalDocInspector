import os
import logging
from datetime import datetime
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import ollama

from OCR import OCR
from LLM import LLM

# --- Настройки ---
PDF_PATH = "docs2/claim.pdf"           # Путь к PDF
OLLAMA_MODEL = "llama3"                # Модель Ollama
USE_EXISTING_MARKDOWN = True  # поставь False, чтобы перезапустить OCR

CLAIM_PROMPT = """
Вы являетесь ведущим в мире экспертом по извлечению данных из юридических документов, особенно из претензий.

### Задача
Ваша задача - проанализировать текст данной претензии и извлечь конкретную информацию в формате JSON
для другого сервиса, а не для человека.
Приведенный ниже текст является текстом претензии. Извлеките из него информацию о том, какой номер № Договора,
тип Договора (ТЭ, ГВС или СОИ), в каком фрагменте указан срок, за который исполнитель должен произвести оплату. Если
в доверенности указана дата совершения расчётов по договору, то какая именно?

### Формат вывода
1. "Proxy" - это единственный объект-массив в результирующем JSON, и в массиве "Proxy" есть только один объект.
2. Номер № Договора должен быть в формате **.******-** или **.******-***.
3. Тип договора (принимает одно из трёх значений: ТЭ, ГВС или СОИ)
4. Текст фрагмента, где указан срок, за который исполнитель должен произвести оплату. 
5. Если вы нашли дату совершения расчётов по договору, то запишите её в формате "ДД.ММ.ГГГГ"
6. В вашем ответе не должно быть никакой другой информации, кроме текста в формате JSON.
7. Нет необходимости включать в свой ответ объяснения или рекомендации.
"""


# --- Основная логика ---
if __name__ == "__main__":
    # 1. Создаём OCR-движок
    ocr = OCR(engine='tesseract')
    llm = LLM(model="llama3", temperature=0.0)
    markdown_file = "claim_extracted.md"

    try:
        if USE_EXISTING_MARKDOWN and os.path.exists(markdown_file):
            print("📖 Используем существующий файл...")
            with open(markdown_file, "r", encoding="utf-8") as f:
                text_from_file = f.read()
        else:
            print("🔄 Перезапускаем OCR...")
            extracted_text = ocr.extract_text(PDF_PATH)
            ocr.save_as_markdown(extracted_text, markdown_file)
            with open(markdown_file, "r", encoding="utf-8") as f:
                text_from_file = f.read()

        # 4. Отправляем в Ollama
        answer = llm.ask_with_context(CLAIM_PROMPT, text_from_file)

        # 5. Выводим ответ
        print("\n\n💡 Ответ модели (JSON):")
        print("=" * 60)
        print(answer.strip())
        print("=" * 60)

    except Exception as e:
        logging.critical("Произошла ошибка: %s", e)
        print(f"❌ Критическая ошибка: {e}")
