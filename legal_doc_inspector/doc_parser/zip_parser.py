from sentence_splitter import SentenceSplitter
from .utils import get_text_for_zip, get_pdf_files, get_conversation_for_zip

class ZipParser:
    def __init__(self, model, processor):
        self.model = model

        self.processor = processor
        self.splitter = SentenceSplitter(language='ru')

    def get_texts (self, docs_path):
        '''
        Принимает путь до папки с документами, возвращает словарь {документ: [предложения]}
        '''
        pdf_paths = get_pdf_files (docs_path)
        pdf_chunks = {}
        for path in pdf_paths:
            pdf_text = get_text_for_zip(path)
            sentences = self.splitter.split(pdf_text)
            sentences = list(filter(None, sentences))  
            pdf_chunks[path] = sentences
        return pdf_chunks
    
    def find_names(self, docs_json):
        '''
        Принимает словарь {документ: [предложения]}, возвращает словарь {документ: название}
        '''
        result = {}
        for key, value in docs_json.items():

            conversation = get_conversation_for_zip(value)
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
        
