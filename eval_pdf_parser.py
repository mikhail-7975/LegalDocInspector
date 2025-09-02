from transformers import (
    AutoModel,
    AutoTokenizer,
    Qwen2_5OmniForConditionalGeneration,
    Qwen2_5OmniProcessor,
) # библиотека для llm


from legal_doc_inspector.pdf_parser.contract_parser import ContractParser # Парсе догоора
from legal_doc_inspector.pdf_parser.claim_parser import ClaimParser # парсер претензии

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
contract_text_chunks = contract_parser.pdf_to_text("data/input_examples/комплект 1/Документы для иска/04.303360-ТЭ/04.303360-ТЭ договор и допик. на 24 л..pdf")
# определяем тип услуги
service_type = contract_parser.find_info(contract_text_chunks, 'Какой тип услуги указан в договоре? Выбери: вода, отопление или оба, ответь одним словом?', service_flag = True)
# определяем фрагмент с датой начала просрочки
overdue_date = contract_parser.find_info(contract_text_chunks, 'В какой срок исполнитель должен произвести оплату?', service_flag = False)
# опредляем номер договора
contract_number = contract_parser.find_info(contract_text_chunks, 'номер договора №', service_flag = True)

print("contract_number", contract_number)
print("service_type", service_type)
print("overdue_date", overdue_date)

claim_text = claim_parser.pdf_to_text("data/input_examples/комплект 1/Документы для иска/04.303360-ТЭ/Претензия №560045 ДЗ+ГК на 1л.pdf")
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

print("plaintiff_inn", plaintiff_inn)
print("claim_number", claim_number)
print("claim_date", claim_date)