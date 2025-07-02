def extract_first_10_digits(text: str) -> str:
    result = ''
    for char in text:
        if char.isdigit():
            result += char
            if len(result) == 10:
                break
    return result

def parse_contract (file, parser):
    # получаем фрагменты документа
    contract_text_chunks = parser.pdf_to_text(file)
    # определяем тип услуги
    service_type = parser.find_info(contract_text_chunks, 'Какой тип услуги указан в договоре? Выбери: вода, отопление или оба, ответь одним словом?', service_flag = True)
    # определяем фрагмент с датой начала просрочки
    overdue_date = parser.find_info(contract_text_chunks, 'В какой срок исполнитель должен произвести оплату?', service_flag = False) 
    # опредляем номер договора
    contract_number = parser.find_info(contract_text_chunks, 'номер договора №', service_flag = True) 
    contract_number = contract_number.split(":", 1)[-1].strip()
    # определяем тип услуги по ответу сети
    if (service_type == "Оба." or service_type == "Оба"): service_type = 'тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))'
    if (service_type == "Вода." or service_type == "Вода"): service_type = 'горячую воду (ГВС))'
    if (service_type == "Отопление." or service_type == "Отопление"): service_type = 'тепловую энергию/теплоноситель (ТЭ)'

    return contract_number, service_type, overdue_date

def parse_zip (archive_folder, zip_parser):
    # получаем словарь документов типа {путь: текст}
    zip_docs_texts = zip_parser.get_texts(archive_folder)
    # получаем названия документов 
    zip_names = zip_parser.find_names(zip_docs_texts)
    return zip_names


def parse_claim (file, parser):
    # получаем текст претензии в виде строки
    claim_text = parser.pdf_to_text(file)
    res = parser.find_info (claim_text)
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

