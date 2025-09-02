import json
from datetime import datetime

from legal_doc_inspector.exel_parser import TableParser
from legal_doc_inspector.calculator.penalty_calculator import calculate_penalty
from legal_doc_inspector.doc_creator.calculation_claim_generator import CalculationClaimGenerator
from legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator
from legal_doc_inspector.utils.calculator_adapter import convert_data


PATH_TO_CLAIM_TEMPLATE = "data/templates/claim.docx"
PATH_TO_CALCULATION_CLAIM_TEMPLATE = "data/templates/calculation_claim.docx"

# Тут у ТЭ есть годовая корректировка, у ГВС нет
OUTPUT_CLAIM = "data/input_examples/комплект 1/claim.docx"
OUTPUT_CALCULATION_CLAIM = "data/input_examples/комплект 1/calculation_claim.docx"

LAST_DAY_OF_PENALTY_1 = 20
LAST_DAY_OF_PENALTY_2 = 20

COMPANY_TYPE = "ТСЖ"

CURRENT_DATE = "25.07.2025"#datetime.now().strftime("%d.%m.%Y")

CONTRACT_POINT_1 = "4.5"
CONTRACT_POINT_2 = "4.6"

def generate_claim():
    excel_files = [
        "data/input_examples/комплект 1/Документы для иска/04.303360-ТЭ/04.303360-ТЭ_справка.XLSM",
        "data/input_examples/комплект 1/Документы для иска/04.303360ГВС/04.303360ГВС_справка (2).XLS"
    ]
    last_days_of_penalty = [LAST_DAY_OF_PENALTY_1, LAST_DAY_OF_PENALTY_2]
    contract_points = [CONTRACT_POINT_1, CONTRACT_POINT_2]
    number_of_contracts = len(excel_files)

    # 1. Парсим данные из эксельной таблицы (или из нескольких)
    excel_data_list = []
    contract_numbers = []
    table_parser = TableParser()
    for i in range(number_of_contracts):
        table_parser.open(excel_files[i])
        excel_data_list.append(table_parser.parse())
        contract_numbers.append(table_parser.parse_contract_number())
        table_parser.close()

    # 2. Скармливаем данные калькулятору
    calculator_list = []
    for i in range(number_of_contracts):
        calculator_list.append(
            calculate_penalty(
                parsed_data = excel_data_list[i],
                day_of_penalty = last_days_of_penalty[i],
                company_type = COMPANY_TYPE,
                end_date = CURRENT_DATE
            )
        )

    # 3. Подготавливаем данные
    for i in range(number_of_contracts):
        calculator_list[i]["contract_number"] = contract_numbers[i]

    claim_data = convert_data(calculator_list, last_days_of_penalty, contract_points, COMPANY_TYPE, CURRENT_DATE)
    claim_data["plaintiff_info"] = {
        "inn": "Истец ИНН 1",
        "full_name": "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «ИСТЕЦ»",
        "short_name": "ПАО «ИСТЕЦ»",
        "addres": "119526, Москва, пр-кт Истец",
        "correspondency_addres": "121596, г. Мосфильмовская",   # это че за херь
        "ogrn": "Истец ОГРН 1"
    }
    claim_data["defendant_info"] = {
        "inn": "Ответчик ИНН 2",
        "full_name": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «ОТВЕТЧИК»",
        "short_name": "ООО «ОТВЕТЧИК»",
        "addres": "119285, Москва, Муниципальный Округ Ответчика",
        "ogrn": "Ответчик ОГРН 2"
    }
    claim_data["lawsuit_info"] = {
        "cost": "546 167,56 руб.",
        "tax": "32 308,00 руб.",
        "service_type": "ТЭ",
        "claims": [
            "№ 553106 от 28.04.2025",
            "№ 111111 от 11.11.1111",
        ]
    }

    filename = "data/input_examples/комплект 1/claim_data.json"
    with open(filename, 'w') as file:
        json.dump(claim_data, file, ensure_ascii=False, indent=4)


    # 4. Гененрируем расчет к иску
    calc_claim_gen = CalculationClaimGenerator()
    calc_claim_gen.make_instance(calculator_list, claim_data, PATH_TO_CALCULATION_CLAIM_TEMPLATE, OUTPUT_CALCULATION_CLAIM)

    # 5. Генерируем иск
    claim_gen = ClaimGenerator()
    claim_gen.make_instance(claim_data, PATH_TO_CLAIM_TEMPLATE, OUTPUT_CLAIM)


def main():

    generate_claim()


if __name__ == "__main__":
    main()
