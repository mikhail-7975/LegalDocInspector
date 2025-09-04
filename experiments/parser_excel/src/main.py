from pathlib import Path

from TableParser import TableParser

from new_penalty_calculator import calculate_penalty


def collect_contracts_and_files(claims_folder):
    """
    Находит все папки в 'claims', ищет в них Excel-файлы (.xlsx, .xlsm, .xls)
    и сохраняет пути + названия договоров.

    :param claims_folder: Путь к папке 'claims'
    :return: (список путей, список названий договоров)
    """
    file_paths = []
    contract_names = []

    claims_path = Path(claims_folder)

    if not claims_path.exists():
        raise FileNotFoundError(f"Папка claims не найдена: {claims_path}")

    # Все подпапки в claims
    claim_folders = [f for f in claims_path.iterdir() if f.is_dir()]

    if not claim_folders:
        print("В папке claims не найдено подпапок.")
        return file_paths, contract_names

    # Поддерживаемые расширения
    supported_suffixes = ['.xlsx', '.xlsm', '.xls']

    for base_folder in claim_folders:
        docs_folder = base_folder / "Документы для иска"
        if not docs_folder.exists() or not docs_folder.is_dir():
            print(f"Пропущено: папка 'Документы для иска' не найдена в {base_folder.name}")
            continue

        # Перебираем папки-договоры
        for contract_folder in docs_folder.iterdir():
            if not contract_folder.is_dir():
                continue

            contract_name = contract_folder.name

            # Ищем все Excel-файлы (включая .xls), но не временные
            excel_files = [
                f for f in contract_folder.iterdir()
                if f.is_file() and
                   f.suffix.lower() in supported_suffixes and
                   not f.name.startswith('~$')
            ]

            if len(excel_files) == 0:
                print(f"⚠️ Excel-файл не найден в: {contract_folder}")
                continue
            elif len(excel_files) > 1:
                print(f"ℹ️ Несколько Excel-файлов в: {contract_folder}, берём первый")

            excel_file = excel_files[0]
            file_paths.append(str(excel_file.resolve()))
            contract_names.append(contract_name)

    return file_paths, contract_names





def print_periods(periods: dict):
    for month in periods.keys():
        # print(f"{period}: {periods[period]}")
        print(f"{month}")

        # Основной блок
        # print("Основной долг. Начисления:")
        # for accrual in periods[month]["accrual"]["accruals"]:
        #     print(accrual)
        # if len(periods[month]["accrual"]["accruals"]) == 0:
        #     print("-")

        # print("Основной долг. Платежи:")
        # for accrual in periods[month]["accrual"]["payments"]:
        #     print(accrual)
        # if len(periods[month]["accrual"]["payments"]) == 0:
        #     print("-")

        # print("Основной долг. Доборы:")
        # for accrual in periods[month]["accrual"]["additionals"]:
        #     print(accrual)
        # if len(periods[month]["accrual"]["additionals"]) == 0:
        #     print("-")

        print("Основной долг. Общая сумма начислений:")
        print(periods[month]["accrual"]["total_amount_of_accruals"])

        print("Основной долг. Общая сумма оплаты:")
        print(periods[month]["accrual"]["total_amount_of_payments"])

        print("Основной долг. Задолженность:")
        print(periods[month]["accrual"]["debt"])

        print("Основной долг. Вычисленная задолженность:")
        print(calculate_debt(periods[month], "accrual"))

        # Блок корректировки обязательств
        # print("Корректировка обязательств. Начисления:")
        # for accrual in periods[month]["adjustment"]["accruals"]:
        #     print(accrual)
        # if len(periods[month]["adjustment"]["accruals"]) == 0:
        #     print("-")

        # print("Корректировка обязательств. Платежи:")
        # for accrual in periods[month]["adjustment"]["payments"]:
        #     print(accrual)
        # if len(periods[month]["adjustment"]["payments"]) == 0:
        #     print("-")

        # print("Корректировка обязательств. Доборы:")
        # for accrual in periods[month]["adjustment"]["additionals"]:
        #     print(accrual)
        # if len(periods[month]["adjustment"]["additionals"]) == 0:
        #     print("-")

        print("Корректировка обязательств. Общая сумма начислений:")
        print(periods[month]["adjustment"]["total_amount_of_accruals"])

        print("Корректировка обязательств. Общая сумма оплаты:")
        print(periods[month]["adjustment"]["total_amount_of_payments"])

        print("Корректировка обязательств. Задолженность:")
        print(periods[month]["adjustment"]["debt"])

        print("Корректировка обязательств. Вычисленная задолженность:")
        print(calculate_debt(periods[month], "adjustment"))

        print()


def calculate_debt(period, block_type):
    debt = 0.0

    for accrual in period[block_type]["accruals"]:
        debt += accrual["accrual"]

    for payment in period[block_type]["payments"]:
        debt -= payment["payment"]

    for additional in period[block_type]["additionals"]:
        debt += additional["accrual"]

    return debt


def parse_first_complect(base_folder: str):
    file_list, contract_list = collect_contracts_and_files(base_folder)
    # print(f"\nНайдено {len(file_list)} Excel-файлов:\n")
    # for contract, file_path in zip(contract_list, file_list):
    #     print(f"Договор: {contract}")
    #     print(f"Файл:     {file_path}\n")

    for file_path in file_list:
        table_parser = TableParser()
        table_parser.open(file_path)

        # text = table_parser.cell(12, 0)
        # print(f"text = {text}")
        print()
        print(f"Файл:     {file_path}")
        periods = table_parser.parse()
        # print_periods(periods)

        result = calculate_with_calculator(periods)
        print(f"Вывод:\n{result}")
        break


def calculate_with_calculator(data):
    day_of_penalty = 20
    company_type = 'ТСЖ'
    end_date = '27.08.2025'
    res = calculate_penalty(
        parsed_data= data,
        day_of_penalty=day_of_penalty,
        company_type=company_type,
        end_date=end_date
    )
    return res


def main():
    parse_first_complect("../docs3/claims")



if __name__ == "__main__":
    main()
