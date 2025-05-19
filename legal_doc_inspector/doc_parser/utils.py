import pdfplumber  
import pytesseract
import re
import torch
from sentence_transformers import util
from pdf2image import convert_from_path  

def extract_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text.strip()

def extract_images(pdf_path):
    images = convert_from_path(pdf_path)
    ocr_text = ""
    for image in images:
        ocr_text += pytesseract.image_to_string(image, lang="rus")  
    return ocr_text.strip()

def create_prompt(pdf_path):
    '''
    Функция принимает путь до документа формата pdf, возвращает текст
    '''
    text = extract_text(pdf_path)
    images_text = extract_images(pdf_path)
    
    prompt = "Документ содержит следующую информацию:\n\n"
    if text:
        prompt += f"Основной текст:\n{text}\n\n"
    if images_text:
        prompt += f"Текст с изображений:\n{images_text}\n\n"
    return prompt
import re

def split_by_points(text):
    '''
    Функция принимает текст и разделяет его по пунктам, возвращает список текстов
    '''
    text = re.sub(r'\s+', ' ', text).strip()
    pattern = r'(\n\d+[\.]?\d*[\.\)]?\s|' \
              r'\n[а-я][\)\.]|\n[А-Я][\)\.]|\n[ivx]+\.[\d\.]+)'
    parts = re.split(pattern, text)
    print(parts)
    result = []
    for i in range(1, len(parts), 2):
        point_number = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        result.append(
            f"{point_number} {content}"
        )
    return result

def retrieve_relevant_chunks(query, embedding_model, chunk_embeddings, chunks, top_k=3):
    '''
    Функция принимает вопрос, модель, список фрагментов текста в виде эмбеддингов и простой список фрагментов. 
    возвращает top-k ближайших к вопросу фрагментов
    '''
    query_embedding = embedding_model.encode([query], convert_to_tensor=True)
    cos_scores = util.cos_sim(query_embedding, chunk_embeddings)[0]
    top_indices = torch.topk(cos_scores, k=top_k).indices.tolist()
    return [chunks[i] for i in top_indices]
