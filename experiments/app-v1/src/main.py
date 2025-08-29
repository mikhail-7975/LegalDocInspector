import json
from datetime import datetime

from TableParser import TableParser
from PenaltyCalculator import calculate_penalty
from CalculationClaimGenerator import CalculationClaimGenerator
from ClaimGenerator import ClaimGenerator
from calculator_adapter import convert_data


HARD_PATH_TO_EXCEL = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/documents/docs1/claims/комплект 1 (с долей кор-ки 2024)/Документы для иска/07.300558-ТЭ/справка о задолженности по договору 07.300358.XLSM"
HARD_PATH_TO_CLAIM_TEMPLATE = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/templates/claim.docx"
HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE = "/home/artyomtrifautsan/IT/python/Work2/LegalDocInspector/experiments/app-v1/templates/calculation_claim.docx"


def generate_claim(config):
    # 1. Парсим данные из эксельной таблицы
    table_parser = TableParser()
    table_parser.open(config["excel_filename"])
    excel_data = table_parser.parse()

    # 2. Скармливаем данные калькулятору
    calculated_data = calculate_penalty(
        parsed_data = excel_data,
        day_of_penalty = config["last_date_for_payment"],
        company_type = config["company_type"],
        end_date = config["end_date"]
    )
    calculated_data["contract_number"] = table_parser.parse_contract_number()

    table_parser.close()

    # 3. Гененрируем расчет к иску
    calc_claim_gen = CalculationClaimGenerator()
    calculated_data_list = []
    # Для теста запускаем два одинаковых контракта
    calculated_data_list.append(calculated_data)
    calculated_data_list.append(calculated_data)
    calc_claim_gen.make_instance(calculated_data_list, HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE, "output/calculation_claim.docx")

    # 4. Генерируем иск
    calculated_data_list = []
    calculated_data_list.append(calculated_data)
    calculated_data_list.append(calculated_data)
    last_days_of_penalty = [20, 19]
    contract_points = ["4.5", "5.7"]
    company_type = "ТСЖ"
    current_date = datetime.now().strftime("%d.%m.%Y")
    converted_data = convert_data(calculated_data_list, last_days_of_penalty, contract_points, company_type, current_date)

    converted_data["plaintiff_info"] = {
        "inn": "11111111",
        "full_name": "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «ИСТЕЦ»",
        "short_name": "ПАО «МОЭК»",
        "addres": "119526, Москва, пр-кт Вернадского",
        "correspondency_addres": "121596, г. Мосфильмовская",
        "ogrn": "22222222"
    }
    converted_data["lawsuit_info"] = {
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

    claim_gen = ClaimGenerator()
    claim_gen.make_instance(converted_data, HARD_PATH_TO_CLAIM_TEMPLATE, "output/claim.docx")


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
        "excel_filename": HARD_PATH_TO_EXCEL,

        # Последний день срока оплаты
        "last_date_for_payment": 20,

        # Тип компании
        "company_type": "ТСЖ",

        # Некий end_date
        "end_date": "27.08.2025"
    }
    generate_claim(config)


if __name__ == "__main__":
    main()
