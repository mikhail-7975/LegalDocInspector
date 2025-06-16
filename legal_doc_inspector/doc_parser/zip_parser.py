from .utils import get_text_for_zip, get_pdf_files, get_conversation_for_zip, examples
import torch
import re
from sentence_transformers import util

class ZipParser:
    def __init__(self, model, processor, emb_model, emb_tokenizer):
        self.model = model
        self.processor = processor

        self.emb_model = emb_model
        self.emb_tokenizer = emb_tokenizer

    def get_texts (self, docs_path):
        '''
        Принимает путь до папки с документами, возвращает словарь {документ: текст}
        '''
        pdf_paths = get_pdf_files (docs_path)
        pdf_chunks = {}
        for path in pdf_paths:
            pdf_text = get_text_for_zip(path)
            pdf_chunks[path] = pdf_text
        return pdf_chunks
    
    def find_names(self, docs_json):
        '''
        Принимает словарь {документ: текст}, возвращает словарь {документ: название}
        '''
        result = {}

        for key, value in docs_json.items():
            # эмбеддинги примеров
            name_examples = re.split(r'(?<=[.!?])\s+', examples.strip())
            # inputs = self.emb_tokenizer(
            #     name_examples,
            #     padding=True,        
            #     truncation=True,       
            #     max_length=1024,        
            #     return_tensors="pt"    
            # )
            # outputs = self.emb_model(**inputs)
            # cls_embeddings = outputs.last_hidden_state[:, 0, :].detach().numpy()
            # mean_embeddings = outputs.last_hidden_state.mean(dim=1).detach().numpy()

            # # Эмбеддинг документа 
            # inputs = self.emb_tokenizer(
            #     value,
            #     return_tensors="pt",
            #     truncation=True,      
            #     max_length=512        
            # )
            # outputs = self.emb_model(**inputs)
            # cls_query_embedding = outputs.last_hidden_state[:, 0, :].detach().numpy()
            # mean_query_embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()

            # mean_similarities = util.cos_sim(mean_query_embedding, mean_embeddings)[0]  
            # cls_similarities = util.cos_sim(cls_query_embedding, cls_embeddings)[0]  
            # average_similarities = (mean_similarities + cls_similarities) / 2

            # top_indices = torch.topk(average_similarities, k=10).indices.tolist()

            # rev_chunks = []

            # for i in top_indices:
            #     rev_chunks.append(examples[i])

            # conversation = get_conversation_for_zip(rev_chunks, value)
            
            conversation = get_conversation_for_zip(name_examples, value)
            inputs = self.processor.apply_chat_template(
                conversation,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                padding=True,
            ).to(self.model.device)

            text_ids = self.model.generate(**inputs)
            text = self.processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            clean_text = text[0].split("assistant", 1)[-1].strip()
            result[key] = clean_text
        return result
        
