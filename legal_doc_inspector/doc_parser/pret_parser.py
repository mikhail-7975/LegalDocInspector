import re
import pytesseract  

from pdf2image import convert_from_path  

class PretParser:
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor

    def pdf_to_text(self, pdf_path):
        '''
        Принимает путь до pdf файла, возвращает строку
        '''
        images = convert_from_path(pdf_path)
        pdf_text = ""
        for image in images:
            pdf_text += pytesseract.image_to_string(image, lang="rus")  
        pdf_text = re.sub(r"\x0c", "", pdf_text)  
        return pdf_text
    
    def find_info(self, pdf_text):
        '''
        Принимает строку, возвращает словарь ответ нейросети (str)
        '''
        conversation = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": f"Ты - ассистент для обработка документов. Вот фрагменты документа: {pdf_text}. Тебе нужно точно ответить на вопросы пользовтаеля по его содержанию"}
                ],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "Какие в документе есть данные истца?"},
                            {"type": "text", "text": "Какой номер претензии?"},
                            {"type": "text", "text": "Какая дата претензии?"},
                            {"type": "text", "text": "Какой адрес ответчика?"}]
            }
        ]
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