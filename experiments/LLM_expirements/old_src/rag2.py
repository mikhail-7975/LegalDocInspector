from llama_index.core import VectorStoreIndex, Document
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from pdf2image import convert_from_path
import pytesseract
import os
import time


# -----------------------------------------------
# 🧩 ФУНКЦИЯ: ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ PDF С ПОМОЩЬЮ OCR
# -----------------------------------------------
def extract_text_with_ocr(pdf_path):
    print(f"🔍 Обрабатываю PDF с OCR: {pdf_path}")
    # Конвертируем PDF в изображения (по одной странице)
    images = convert_from_path(pdf_path, dpi=200)

    full_text = ""
    for i, image in enumerate(images):
        # Распознаём текст с поддержкой русского языка
        text = pytesseract.image_to_string(image, lang='rus+eng')
        full_text += f"\n\nСтраница {i+1}:\n{text}"
        print(f"  Обработана страница {i+1}...")
    
    return full_text

# -----------------------------------------------
# 📂 ЗАГРУЗКА ДОКУМЕНТОВ С ПОДДЕРЖКОЙ OCR
# -----------------------------------------------
print("🔍 Загружаю и обрабатываю документы из папки 'docs'...")

documents = []

# Проходим по всем файлам в папке docs
dirname = "docs3"
for filename in os.listdir(dirname):
    t1 = time.time()
    filepath = os.path.join(dirname, filename)

    if filename.lower().endswith(".pdf"):
        # Обрабатываем PDF через OCR
        text = extract_text_with_ocr(filepath)
        documents.append(Document(text=text, metadata={"file_name": filename}))
    elif filename.lower().endswith((".txt", ".md")):
        # Просто читаем текстовые файлы
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        documents.append(Document(text=text, metadata={"file_name": filename}))
    else:
        print(f"⚠️ Формат {filename} пока не поддерживается")
    t2 = time.time()
    print(f"Обработка файла заняла {round(t2-t1, 3)} секунд")

print(f"✅ Подготовлено {len(documents)} документов для индексации")

# Показываем пример текста
for i, doc in enumerate(documents):
    print(f"\n📄 Документ {i+1}: {doc.metadata['file_name']}")
    print(f"Текст (первые 500 символов):\n{doc.text[:1000]}...")
    print("-" * 50)

# -----------------------------------------------
# 🚀 ОСНОВНАЯ RAG-ЛОГИКА (без изменений)
# -----------------------------------------------
embed_model = OllamaEmbedding(model_name="llama3")
llm = Ollama(model="llama3", request_timeout=360.0)

# Создаём индекс из документов с OCR-текстом
index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

# Создаём движок запросов
query_engine = index.as_query_engine(llm=llm)

searching_info = [
    "ИНН исца", 
    # "ИНН ответчика",
    # "номер Договора",
    # "дату совершения расчётов по договору",
    # "номер пункта договора с информацией о дате платежа",
    # "тип Договора (ТЭ, ГВС или СОИ)",
    "номер претензии",
    "дату составления претензии",
    # "полное название компании исца",
    # "полное название компании ответчика",
    # "сокращенное название компании исца",
    # "сокращенное название компании ответчика",
]

for query_item in searching_info:
    # query = f"Найди {query_item}, и скажи, в каком файле и на какой странице найдена информация"
    query = f"Найди {query_item}"
    print(f"\n❓ Вопрос: {query}")
    response = query_engine.query(query)
    print(f"📝 Ответ: {response}")
    
"""
# Задаём вопрос
query = "Найди ИНН исца, ИНН ответчика, номер договора, дату совершения расчётов по Договору, номер пункта Договора с информацией о дате платежа, тип Договора(ТЭ, ГВС или СОИ), номер претензии, дату составления претензии"
print(f"\n❓ Вопрос: {query}")
response = query_engine.query(query)
print(f"📝 Ответ: {response}")
"""
