import json
from datetime import datetime

from TableParser import TableParser
from PenaltyCalculator import calculate_penalty
from CalculationClaimGenerator import CalculationClaimGenerator
from ClaimGenerator import ClaimGenerator
from calculator_adapter import convert_data


# HARD_PATH_TO_EXCEL = "/home/artyomtrifautsan/Загрузки/04.303360-ТЭ_справка.XLSM"
# HARD_PATH_TO_EXCEL = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 1 (с долей кор-ки 2024)/Документы для иска/07.300558-ТЭ/справка о задолженности по договору 07.300358.XLSM"
HARD_PATH_TO_CLAIM_TEMPLATE = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/templates/claim.docx"
HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/templates/calculation_claim.docx"

# Тут у ТЭ есть годовая корректировка, у ГВС нет
HARD_PATH_TO_EXCEL_1 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 3 (с оплаченной долей кор-ки 2024)/Документы для иска/07.620008ГВС/008ГВС 01.25-02.25.XLS"
HARD_PATH_TO_EXCEL_2 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 3 (с оплаченной долей кор-ки 2024)/Документы для иска/07.620008-ТЭ/008-ТЭ 11.24-02.25.XLSM"

HARD_PATH_TO_EXCEL_3 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 2 (с долей кор-ки 2024)/Документы для иска/05.414435-ТЭ/05.414435-ТЭ.XLSM"

HARD_PATH_TO_EXCEL_4 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 4 (с долей кор-ки 2024)/Документы для иска/07.659095ГВС/07.659095ГВС 12.2024-03.2025.XLS"
HARD_PATH_TO_EXCEL_5 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 4 (с долей кор-ки 2024)/Документы для иска/07.659095-ТЭ/07.659095-ТЭ 12.2024-03.2025.XLSM"

HARD_PATH_TO_EXCEL_6 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/new_docs/05.413208ГВС/05.413208ГВС.XLS"
HARD_PATH_TO_EXCEL_7 = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/new_docs/05.413208-ТЭ/05.413208-ТЭ.XLSM"

OUTPUT_CLAIM = "output/claim.docx"
OUTPUT_CALCULATION_CLAIM = "output/calculation_claim.docx"

LAST_DAY_OF_PENALTY_1 = 20
LAST_DAY_OF_PENALTY_2 = 20

COMPANY_TYPE = "ТСЖ"

CURRENT_DATE = datetime.now().strftime("%d.%m.%Y")

CONTRACT_POINT_1 = "4.5"
CONTRACT_POINT_2 = "4.6"

def generate_claim():
    excel_files = [HARD_PATH_TO_EXCEL_6, HARD_PATH_TO_EXCEL_7]
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
            "№ 222222 от 28.04.2025",
            "№ 333333 от 28.04.2025",
            "№ 444444 от 28.04.2025",
            "№ 555555 от 28.04.2025",
            "№ 666666 от 28.04.2025",
            "№ 777777 от 28.04.2025" 
        ]
    }

    filename = "claim_data.json"
    with open(filename, 'w') as file:
        json.dump(claim_data, file, ensure_ascii=False, indent=4)


    # 4. Гененрируем расчет к иску
    calc_claim_gen = CalculationClaimGenerator()
    calc_claim_gen.make_instance(calculator_list, claim_data, HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE, OUTPUT_CALCULATION_CLAIM)

    # 5. Генерируем иск
    claim_gen = ClaimGenerator()
    claim_gen.make_instance(claim_data, HARD_PATH_TO_CLAIM_TEMPLATE, OUTPUT_CLAIM)


def main():
    config = {
        # Генерируемый файл с иском
        "output_claim_filename": "output/claim.docx",

        # Шаблон файла для иска
        "claim_template_filename": HARD_PATH_TO_CLAIM_TEMPLATE,

        # Генерируемый файл с расчётом для иска
        "output_calculation_claim_filename": "output/calculation_claim.docx",

        # Шаблон файла для расчета для иска
        "calculation_claim_template_filename": HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE,

        # Файл ексель с табличкой
        # "excel_filename": HARD_PATH_TO_EXCEL,

        # Последний день срока оплаты
        "last_date_for_payment": 20,

        # Тип компании
        "company_type": "ТСЖ",

        # Некий end_date
        "end_date": "27.08.2025"
    }
    generate_claim()


if __name__ == "__main__":
    main()
