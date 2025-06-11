def parse_contract (file, parser):
    contract_text_chunks = parser.pdf_to_text(file)
    service_type = parser.find_info(contract_text_chunks, 'Какой тип услуги указан в договоре? Выбери: вода, отопление или оба, ответь одним словом?', service_flag = True)
    overdue_date = parser.find_info(contract_text_chunks, 'В какой срок исполнитель должен произвести оплату?', service_flag = False) 
    if (service_type == "Оба." or service_type == "Оба"): service_type = 'тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))'
    if (service_type == "Вода." or service_type == "Вода"): service_type = 'горячую воду (ГВС))'
    if (service_type == "Отопление." or service_type == "Отопление"): service_type = 'тепловую энергию/теплоноситель (ТЭ)'

    return service_type, overdue_date

def parse_zip (archive_folder, zip_parser):
    zip_docs_texts = zip_parser.get_texts(archive_folder)
    zip_names = zip_parser.find_names(zip_docs_texts)
    return zip_names


def parse_claim (file, parser):
    claim_text = parser.pdf_to_text(file)
    res = parser.find_info (claim_text)
    lines = res.split('\n')
    parsed_lines = [line.split(':', 1)[1].strip() if ':' in line else line for line in lines]

    defendant_inn = parsed_lines[1]
    plaintiff_inn = parsed_lines[0]
    claim_number = parsed_lines[3]
    claim_date = parsed_lines[2]
    return defendant_inn, plaintiff_inn, claim_number, claim_date