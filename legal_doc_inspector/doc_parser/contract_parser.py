from .utils import create_prompt, split_by_points, retrieve_relevant_chunks

import torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForCausalLM

class contract_parser:
    def __init__(self):
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
        self.model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

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
        context = "\n".join(relevant_chunks)

        input_text = f"Контекст: {context}\n\nВопрос: {question}"
        inputs = self.tokenizer(input_text, return_tensors="pt")
        generate_ids = self.model.generate(inputs.input_ids)
        response = self.tokenizer.batch_decode(generate_ids)[0]

        return response



        



