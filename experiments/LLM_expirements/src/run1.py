import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import ollama

# --- Настройки ---
PDF_PATH = "docs2/claim.pdf"     # ← Укажи путь к твоему PDF
OLLAMA_MODEL = "llama3"               # ← Модель в Ollama
NOT_PROMPT = """
Проанализируй текст документа и найди:
- номер № Договора
- дату совершения расчётов по договору
- тип Договора (ТЭ, ГВС или СОИ)
- В каком фрагменте указан срок исполнитель должен произвести оплату?

Верни ответ в понятной форме.
"""


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

# --- Проверка Tesseract ---
try:
    pytesseract.get_tesseract_version()
except OSError:
    print("❌ Tesseract не найден. Убедись, что установлен: sudo apt install tesseract-ocr")
    exit(1)

# --- Функция: OCR по PDF ---
def ocr_pdf(pdf_path):
    print("Конвертируем PDF в изображения...")
    # Конвертируем PDF в список изображений (по одной на страницу)
    images = convert_from_path(pdf_path, dpi=300)

    full_text = ""
    print(f"Обработка {len(images)} страниц...")

    for i, image in enumerate(images):
        print(f"  Распознавание страницы {i+1}...")
        # Улучшение качества (опционально)
        image = image.convert("L")  # В оттенки серого
        # image = image.point(lambda x: 0 if x < 140 else 255, mode='1')  # Бинаризация (если нужно)

        # OCR с русским и английским
        text = pytesseract.image_to_string(image, lang='rus+eng')
        full_text += f"\n\n--- Страница {i+1} ---\n"
        full_text += text.strip()

    return full_text.strip()

# --- Функция: запрос к Ollama ---
def ask_ollama(prompt, text, model=OLLAMA_MODEL):
    print("Отправляем запрос в Ollama...")
    full_prompt = f"{prompt}\n\n--- Текст документа ---\n{text}"

    try:
        response = ollama.generate(
            model=model,
            prompt=full_prompt,
            stream=False
        )
        return response['response']
    except Exception as e:
        return f"Ошибка при обращении к Ollama: {e}"

# --- Основная логика ---
if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ Файл не найден: {PDF_PATH}")
        exit(1)

    print("🚀 Запуск обработки PDF через pytesseract и Ollama...")

    # Шаг 1: Извлечение текста
    extracted_text = ocr_pdf(PDF_PATH)
    print(f"\n✅ OCR завершён. Извлечено ~{len(extracted_text)} символов.")

    # Сохранить текст (опционально)
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(extracted_text)
    print("📄 Текст сохранён в 'extracted_text.txt'")

    # Шаг 2: Запрос к модели
    answer = ask_ollama(CLAIM_PROMPT, extracted_text, OLLAMA_MODEL)
    print("\n\n💡 Ответ модели:")
    print("=" * 60)
    print(answer)
    print("=" * 60)
