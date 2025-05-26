from .utils import split_by_points, retrieve_relevant_chunks

import pytesseract
import re
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path  

class ContractParser:
    def __init__(self):
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        # self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
        #     "Qwen/Qwen2.5-Omni-3B",
        #     torch_dtype="auto",
        #     device_map="auto",
        #     enable_audio_output=False,
        # )

        # self.processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")

    def pdf_to_text(self, pdf_path):
        '''
        Принимает путь до pdf файла, возвращает список строк
        '''
        images = convert_from_path(pdf_path)
        pdf_text = ""
        for image in images:
            pdf_text += pytesseract.image_to_string(image, lang="rus")  
        pdf_text = re.sub(r"\x0c", "", pdf_text)  
        chunks = split_by_points(pdf_text)
        return chunks
    
    def find_info(self, chunks, question):
        '''
        Принимает список строк (разделенный текст), список строк (наиболее подходящие отрывки текста) 
        '''
        chunk_embeddings = self.embedding_model.encode(chunks, convert_to_tensor=True)
        question_embedding = self.embedding_model.encode([question], convert_to_tensor=True)
        relevant_chunks = retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks)


        # ToDo:
        # на будущее
        # conversation = get_conversation_for_contract(relevant_chunks, question)
        # inputs = self.rocessor.apply_chat_template(
        #     conversation,
        #     add_generation_prompt=True,
        #     tokenize=True,
        #     return_dict=True,
        #     return_tensors="pt",
        #     padding=True,
        # ).to(self.model.device)
        # text_ids = self.model.generate(**inputs)
        # text = self.processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        # response = text[0].split("assistant", 1)[-1].strip()        
        # return response

        return relevant_chunks



        



