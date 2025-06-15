import re
import pytesseract  
from .utils import get_conversation_for_claim
from pdf2image import convert_from_path  

class ClaimParser:
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor

    def pdf_to_text(self, pdf_path):
        '''
        Принимает путь до pdf файла, возвращает строку
        '''
        images = convert_from_path(pdf_path, dpi=200)  
        ocr_text = ""
        if images:
            for i, image in enumerate (images):
                if i == 0:
                    width, height = image.size
                    center_x = width // 2
                    center_y = height // 3
                    left_upper = image.crop((0, 0, center_x, center_y))
                    right_upper = image.crop((center_x, 0, width, center_y))
                    bottom_part = image.crop((0, center_y, width, height))
                    ocr_text += pytesseract.image_to_string(left_upper, lang="rus+eng") + "\n"
                    ocr_text += pytesseract.image_to_string(right_upper, lang="rus+eng") + "\n"
                    ocr_text += pytesseract.image_to_string(bottom_part, lang="rus+eng") + "\n"
                else:
                    ocr_text += pytesseract.image_to_string(image, lang="rus+eng") + "\n"
        return ocr_text.strip()
    
    def find_info(self, pdf_text):
        '''
        Принимает строку, возвращает ответ нейросети (str)
        '''
        conversation = get_conversation_for_claim(pdf_text)
        
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
        return(text[0].split("assistant", 1)[-1].strip())