from transformers import (
    AutoModel,
    AutoTokenizer,
    Qwen2_5OmniForConditionalGeneration,
    Qwen2_5OmniProcessor,
) # библиотека для llm


from LegalDocInspector.legal_doc_inspector.pdf_parser.contract_parser import ContractParser # Парсе догоора
from LegalDocInspector.legal_doc_inspector.pdf_parser.claim_parser import ClaimParser # парсер претензии

def extract_first_10_digits(text: str) -> str:
    result = ''
    for char in text:
        if char.isdigit():
            result += char
            if len(result) == 10:
                break
    return result

model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2.5-Omni-3B",
    torch_dtype="auto",
    device_map="auto",
    enable_audio_output=False,
)
processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")

contract_parser = ContractParser(model, processor)
claim_parser = ClaimParser(model, processor)


def extract_first_10_digits(text: str) -> str:
    result = ''
    for char in text:
        if char.isdigit():
            result += char
            if len(result) == 10:
                break
    return result

def parse_contract (file):
    # получаем фрагменты документа
    contract_text_chunks = contract_parser.pdf_to_text(file)
    # определяем тип услуги
    service_type = contract_parser.find_info(contract_text_chunks, 'Какой тип услуги указан в договоре? Выбери: вода, отопление или оба, ответь одним словом?', service_flag = True)
    # определяем фрагмент с датой начала просрочки
    overdue_date = contract_parser.find_info(contract_text_chunks, 'В какой срок исполнитель должен произвести оплату?', service_flag = False)
    # опредляем номер договора
    contract_number = contract_parser.find_info(contract_text_chunks, 'номер договора №', service_flag = True)
    contract_number = contract_number.split(":", 1)[-1].strip()
    # определяем тип услуги по ответу сети
    if (service_type == "Оба." or service_type == "Оба"): service_type = 'тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))'
    if (service_type == "Вода." or service_type == "Вода"): service_type = 'горячую воду (ГВС))'
    if (service_type == "Отопление." or service_type == "Отопление"): service_type = 'тепловую энергию/теплоноситель (ТЭ)'

    return contract_number, service_type, overdue_date


def parse_claim (file):
    # получаем текст претензии в виде строки
    claim_text = claim_parser.pdf_to_text(file)
    res = claim_parser.find_info (claim_text)
    # делим на абзацы
    lines = res.split('\n')
    parsed_lines = [line.split(':', 1)[1].strip() if ':' in line else line for line in lines]
    # получаем инн истца
    plaintiff_inn = extract_first_10_digits(parsed_lines[0])
    # получаем дату претензии
    claim_date = parsed_lines[1]
    # получаем номер претензии
    claim_number = parsed_lines[2]
    return plaintiff_inn, claim_number, claim_date

