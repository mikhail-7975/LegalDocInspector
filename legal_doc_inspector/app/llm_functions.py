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
    defendant_adress = parser.find_info(claim_text, "найди адрес ответчика и адрес истца?")
    defendant_adress = defendant_adress.split("адрес:")[-1].strip()
    plaintiff_data = parser.find_info(claim_text, 'найди все данные истца?')
    claim_date = parser.find_info(claim_text, 'найди дату претензии? напиши только дату в формате дата:')
    claim_number = parser.find_info(claim_text, 'найди номер претензии? напиши только номер в формате номер:')
    claim_number = ''.join(filter(str.isdigit, claim_number))
    return defendant_adress, plaintiff_data, claim_number, claim_date