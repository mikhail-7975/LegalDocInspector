import json

from TableParser import TableParser
from PenaltyCalculator import calculate_penalty

from CalculationClaimGenerator import CalculationClaimGenerator


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

    # with open("temp.json", "w") as file:
    #     json.dump(convert_data_from_calculator(None, calculated_data), file, ensure_ascii=False, indent=4)

    # 3. Гененрируем расчет к иску
    calc_claim_gen = CalculationClaimGenerator()
    calculated_data_list = []
    calculated_data_list.append(calculated_data)
    calc_claim_gen.make_instance(calculated_data_list, HARD_PATH_TO_CALCULATION_CLAIM_TEMPLATE, "output/calculation_claim.docx")

    # 4. Генерируем иск


def convert_data_from_calculator(self, data):
    # print(data)
    converted_data = {
        "contract_number": data["contract_number"],
        "delay_start": data["start_of_table"]["start"],
        "delay_end": data["start_of_table"]["end"],
        "total_debt": data["end_of_table1"]["money"],
        "total_peny": data["end_of_table2"]["money"],
        "periods": [],
    }

    for period in data.keys():
        if period not in ["contract_number", "start_of_table", "end_of_table1", "end_of_table2"]:
            new_period = {}
            new_period["period"] = period

            for item in data[period]:
                print(item)
                if item["text"] == "Итого:":
                    new_period["total"] = item["penalty"]

            new_period["rows"] = []
            for item in data[period]:
                if item["text"] != "Итого:":
                    new_period["rows"].append(item)

            converted_data["periods"].append(new_period)

    return converted_data


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
