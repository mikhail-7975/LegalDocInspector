import re
import pytesseract
import numpy as np
import os
from pdf2image import convert_from_path  
from sentence_transformers import util

def split_by_points(text):
    '''
    Функция принимает текст и разделяет его по пунктам, возвращает список текстов
    '''
    pattern = r'(\n\d+[\.)]?|\n[а-я]\)|\n[А-Я]\.)'    
    parts = re.split(pattern, text)
    result = []
    for i in range(1, len(parts), 2):
        point_number = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        result.append(
            f"{point_number} {content}"
        )
    return result

def retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks, top_k=5):
    '''
    Функция принимает вопрос, модель, список фрагментов текста в виде эмбеддингов и простой список фрагментов. 
    возвращает top-k ближайших к вопросу фрагментов
    '''
    cos_scores = util.cos_sim(question_embedding, chunk_embeddings)[0]
    cos_scores = cos_scores.numpy().tolist()
    top_indices = np.argsort(cos_scores)[-top_k:][::-1]
    return [chunks[i] for i in top_indices]


def get_conversation_for_contract(chunks, question):
    '''
    Функция для создания запроса для модели
    '''
    conversation = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": f"Ты - ассистент для обработки документов. Вот фрагменты документа: {chunks}. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию"}
            ],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": f"{question}"}],
        }
    ]
    return conversation


def get_text_for_zip(pdf_path):
    images = convert_from_path(pdf_path)
    ocr_text = ""
    if images:
        ocr_text += pytesseract.image_to_string(images[0], lang="rus")  
    text = ocr_text.strip()
    clean_text = re.sub(r"\x0c", "", text)
    return clean_text

def get_pdf_files(directory):
    files = os.listdir(directory)
    pdf_files = [
        os.path.abspath(os.path.join(directory, f)) 
        for f in files 
        if f.lower().endswith('.pdf')
    ]
    return pdf_files

def get_conversation_for_zip(value):
    '''
    Функция для создания запроса для llm
    '''
    conversation = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": f"Ты - ассистент для обработка документов. Вот фрагменты документа: {value}. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию"}
            ],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "Напиши название документа которое ты нашел в его фрагментах"}],
        }
    ]
    return conversation
