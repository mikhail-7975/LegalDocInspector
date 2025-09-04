from .utils import split_by_points, retrieve_relevant_chunks, get_conversation_for_contract

import pytesseract
import re
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path

class ContractParser:
    def __init__(self, llm_model, processor):
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.llm_model = llm_model

        self.processor = processor

    def pdf_to_text(self, pdf_path):
        '''
        Принимает путь до pdf файла, возвращает список строк (текст разделяется на пункты, после чего возвращается их список)
        '''
        # Получаем изображения из пдфа
        images = convert_from_path(pdf_path)
        pdf_text = ""
        for image in images:
            # сканируем текст изобраений при помощи ocr и конкатинируем его
            pdf_text += pytesseract.image_to_string(image, lang="rus")
        # удаляем лишние символы
        pdf_text = re.sub(r"\x0c", "", pdf_text)
        # разделяем на пункты
        chunks = split_by_points(pdf_text)
        return chunks

    def find_info(self, chunks, question, service_flag):
        '''
        Принимает список строк (разделенный текст), список строк (наиболее подходящие отрывки текста)
        '''
        # переделываем запрос и части текста в вектора
        chunk_embeddings = self.embedding_model.encode(chunks, convert_to_tensor=True, device='cpu')
        question_embedding = self.embedding_model.encode([question], convert_to_tensor=True, device='cpu')

        # RAG- поиск наиболее подходящих фрагментов при помощи близости векторов
        relevant_chunks = retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks)

        # в случае если мы ищем пункт договора нужен другой запрос
        if service_flag == False:
            question = "В каком фрагменте указан срок исполнитель должен произвести оплату?"

        # Обращение к llm, в качестве контекста - релевантные части текста, в качестве вопроса - запрос пользователя
        conversation = get_conversation_for_contract(relevant_chunks, question)
        inputs = self.processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            padding=True,
        ).to(self.llm_model.device)
        text_ids = self.llm_model.generate(**inputs)
        # преобразование ответа llm в текст
        text = self.processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        response = text[0].split("assistant", 1)[-1].strip()
        return response







