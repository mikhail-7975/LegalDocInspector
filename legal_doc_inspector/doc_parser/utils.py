import re
import torch
from sentence_transformers import util

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

def retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks, top_k=3):
    '''
    Функция принимает вопрос, модель, список фрагментов текста в виде эмбеддингов и простой список фрагментов. 
    возвращает top-k ближайших к вопросу фрагментов
    '''
    cos_scores = util.cos_sim(question_embedding, chunk_embeddings)[0]
    top_indices = torch.topk(cos_scores, k=top_k).indices.tolist()
    return [chunks[i] for i in top_indices]


def get_conversation_for_contract(chunks, question):
    '''
    Функция для создания запроса для модели
    '''
    conversation = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": f"Ты - ассистент для обработка документов. Вот фрагменты документа: {chunks}. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию"}
            ],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": f"{question}"}],
        }
    ]
    return conversation
