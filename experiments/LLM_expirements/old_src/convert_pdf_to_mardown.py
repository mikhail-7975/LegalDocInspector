import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import time
import io
import os
from paddleocr import PaddleOCR

def pdf_to_text_with_paddleocr(pdf_path, output_text_path="output.txt", lang='ru', use_gpu=True):
    # Открываем PDF
    pdf_document = fitz.open(pdf_path)
    print(f"Найдено страниц: {len(pdf_document)}")

    # Инициализируем PaddleOCR
    ocr = PaddleOCR(
        use_angle_cls=True,  # опционально: распознавание угла текста
        lang=lang,
        use_gpu=use_gpu
        # Не передаём det, rec, cls здесь!
    )

    full_text = ""

    for page_num in range(len(pdf_document)):
        print(f"Обработка страницы {page_num + 1}/{len(pdf_document)}...")

        page = pdf_document.load_page(page_num)
        
        # Преобразуем страницу в изображение (высокое разрешение)
        mat = fitz.Matrix(2, 2)  # масштаб 2x = ~144 DPI, можно больше (3x = 216 DPI)
        pix = page.get_pixmap(matrix=mat, dpi=144)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        # Временно сохраняем изображение в памяти (PaddleOCR работает с путями или массивами)
        # Можно передать напрямую как numpy array
        img_np = np.array(image)

        # Запускаем OCR
        result = ocr.ocr(img_np, det=True, rec=True)

        # Извлекаем текст
        page_text = ""
        if result[0] is not None:
            for line in result[0]:
                text = line[1][0]  # текст
                page_text += text + " "
        else:
            page_text = "[На этой странице не удалось распознать текст]"

        full_text += f"--- Страница {page_num + 1} ---\n"
        full_text += page_text.strip() + "\n\n"

    pdf_document.close()

    # Сохраняем результат в файл
    with open(output_text_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"✅ Текст сохранён в {output_text_path}")
    return full_text

# === ЗАПУСК ===
pdf_path = "docs3/contract.pdf"  # ← замени на путь к твоему PDF
t1 = time.time()
text = pdf_to_text_with_paddleocr(pdf_path, lang='ru', use_gpu=True)  # если нет GPU — use_gpu=False
t2 = time.time()
print(f"Чтение документа - {round(t2-t1, 3)} секунд.")
print(text)
