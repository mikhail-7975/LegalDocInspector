from .utils import create_prompt, split_by_points, retrieve_relevant_chunks, get_conversation_for_contract

import torch
from sentence_transformers import SentenceTransformer, util
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

class contract_parser:
    def __init__(self):
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-Omni-3B",
            torch_dtype="auto",
            device_map="auto",
            enable_audio_output=False,
        )

        self.processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")

    def  pdf_to_text(self, pdf_path):
        '''
        Принимает путь до pdf файла, возвращает разделенный на фрагменты текст
        '''
        pdf_text = create_prompt(pdf_path)
        chunks = split_by_points(pdf_text)
        return chunks
    
    def parse(self, chunks, question):
        chunk_embeddings = self.embedding_model.encode(chunks, convert_to_tensor=True)
        relevant_chunks = retrieve_relevant_chunks(question, self.embedding_model, chunk_embeddings, chunks)

        conversation = get_conversation_for_contract(relevant_chunks, question)
        inputs = self.rocessor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            padding=True,
        ).to(self.model.device)

        text_ids = self.model.generate(**inputs)
        text = self.processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        response = text[0].split("assistant", 1)[-1].strip()
        return response



        



