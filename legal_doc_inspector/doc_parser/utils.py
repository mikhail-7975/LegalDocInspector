from pathlib import Path
import re  # нужна для очистки и разделения текста

import numpy as np
from pdf2image import convert_from_path  # нужна для сканирования текста из pdf
import pytesseract  # нужна для сканирования текста из pdf
from sentence_transformers import util  # нужна для rag поиска через близость векторов


def split_by_points(text):
    """
    Функция принимает текст и разделяет его по пунктам, возвращает список текстов (для договора)
    """
    pattern = r"(\n\d+[\.)]?|\n[а-я]\)|\n[А-Я]\.)"
    parts = re.split(pattern, text)
    result = []
    for i in range(1, len(parts), 2):
        point_number = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        result.append(f"{point_number} {content}")
    return result


def retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks, top_k=5):
    """
    Функция принимает вопрос, модель, список фрагментов текста в виде эмбеддингов и простой список фрагментов.
    возвращает top-k ближайших к вопросу фрагментов (функция для rag - поиска по договору)
    """
    cos_scores = util.cos_sim(question_embedding, chunk_embeddings)[0]
    cos_scores = cos_scores.numpy().tolist()
    top_indices = np.argsort(cos_scores)[-top_k:][::-1]
    return [chunks[i] for i in top_indices]


def get_conversation_for_contract(chunks, question):
    """
    Функция для создания запроса для модели (для договора)
    """
    conversation = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"Ты - ассистент для обработки документов. Вот фрагменты документа: {chunks}. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию",
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": f"{question}"}],
        },
    ]
    return conversation


def get_text_for_zip(pdf_path):
    """принимает путь до документа, возвращает текст документа в виде строки (для zip архива)"""
    images = convert_from_path(pdf_path)
    ocr_text = ""
    if images:
        ocr_text += pytesseract.image_to_string(images[0], lang="rus")
    text = ocr_text.strip()
    clean_text = re.sub(r"\x0c", "", text)
    return clean_text


def get_pdf_files(directory):
    """Принимает путь до директории, возвращает абсолютные пути до файлов в них в виде списка (для zip архива)"""
    path = Path(directory)
    return [
        str(file.resolve())  # Преобразуем Path в строку с абсолютным путем
        for file in path.iterdir()  # Итерация по элементам директории [[3]]
        if file.is_file()
        and file.suffix.lower() == ".pdf"  # Проверка типа файла и расширения
    ]


def get_conversation_for_zip(rev_chunks, pdf_text):
    """
    Функция для создания запроса для llm (для zip архива)
    """
    conversation = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"Ты - ассистент для обработка документов. Вот содержание документа: {pdf_text} Вот примеры названия документов: {rev_chunks}. Ответь на запрос пользователя",
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "Напиши название документа"}],
        },
    ]
    return conversation


def get_conversation_for_claim(pdf_text):
    """
    Функция для создания запроса для llm (для претензии)
    """
    conversation = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"Ты - ассистент для обработки документов. Вот текст документа: {pdf_text}. Он представляет из себя претензию. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию\
                    для инн используй формат истец: инн",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Какой инн у истца?"},
                {"type": "text", "text": "Какая дата претензии?"},
                {"type": "text", "text": "Какой номер № претензии?"},
            ],
        },
    ]
    return conversation


# примеры названий документов для парсера архива
examples = """
Расчет суммы неустойки (пеней) и общей цены иска.
Соглашение о порядке урегулирования задолженности о признании ООО «КОНДОР-ГРУПП» задолженности перед ПАО «МОЭК» по Договору № 07.300418-ТЭ от 01.01.2019 за период 12.2022.
Методика расчета тепловой энергии на нужды отопления за 2022 год.
Методика расчета тепловой энергии на нужды отопления за периоды 2024 года.
Расчет долга по иску.
Методика расчета тепловой энергии на нужды отопления за периоды 2024 года.
Отчет по фактическим начислениям за период 02.2024-03.2024.
Претензия № 489722 от 03.05.2024 (вместе со справкой СБИС о прохождении документа).
Отчет по начислениям за период 12.2023, 02.2024-03.2024.
Посуточные ведомости показаний прибора учета ГВС за период 12.2023, 02.2024-03.2024.
Акт приемки-передачи энергоресурсов, счет на оплату, счет-фактура за период 12.2023 (вместе со справкой СБИС о прохождении документа).
Отчет по начислениям за период 12.2023.
Месячные ведомости учета тепловой энергии и теплоносителя за период 12.2023 на ГВС.
Договор № 07.663944-ТЭ от 01.11.2021 (с приложениями и дополнительными соглашениями).
Справка о задолженности по выставленному счету с учетом начислений по 1/12.
Акты приемки-передачи энергоресурсов, счеты на оплату, счет-фактуры за период 11.2023-12.2023 (вместе со справками СБИС о прохождении документов).
Методика расчета количества среднемесячного объема потребления.
Выписка из ЕГРЮЛ Ответчика.
Выписка из ЕГРЮЛ Истца.
Свидетельство о государственной регистрации Истца.
Платежное поручение об оплате государственной пошлины.
Почтовая квитанция об отправке иска Ответчику.
Копия диплома представителя ПАО «МОЭК».
Копия доверенности представителя ПАО «МОЭК» на подписание искового заявления.
АКТ № 314-02/01-21-УУТЭ проверки узла учета тепловой энергии и теплоносителя у потребителя 
"""


def calculate_state_duty(amount_str: str):
    rubles, kopecks = amount_str.split()
    total_rubles = int(rubles) + int(kopecks) / 100

    if total_rubles <= 100_000:
        duty = 10_000.0
    elif total_rubles <= 1_000_000:
        excess = total_rubles - 100_000
        duty = 10_000.0 + excess * 0.05
    elif total_rubles <= 10_000_000:
        excess = total_rubles - 1_000_000
        duty = 55_000.0 + excess * 0.03
    elif total_rubles <= 50_000_000:
        excess = total_rubles - 10_000_000
        duty = 325_000.0 + excess * 0.01
    else:
        excess = total_rubles - 50_000_000
        duty = 725_000.0 + excess * 0.005
        if duty > 10_000_000:
            duty = 10_000_000.0

    value = round(duty, 2)
    rubbles = int(value)
    kopecks = int(round(value - rubbles, 2) * 100)

    rubbles_str = str(rubbles)
    formatted = ""
    for i, digit in enumerate(rubbles_str[::-1]):
        if i % 3 == 0 and i != 0:
            formatted = " " + formatted
        formatted = digit + formatted

    return f"{formatted},{kopecks:02d}"
