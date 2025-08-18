from pathlib import Path

from TableParser import TableParser


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


def main():
    base_folder = "../docs/claims"
    file_list, contract_list = collect_contracts_and_files(base_folder)
    # print(f"\nНайдено {len(file_list)} Excel-файлов:\n")
    # for contract, file_path in zip(contract_list, file_list):
    #     print(f"Договор: {contract}")
    #     print(f"Файл:     {file_path}\n")

    file_path = file_list[2]
    table_parser = TableParser()
    table_parser.open(file_path)

    # text = table_parser.cell(12, 0)
    # print(f"text = {text}")
    periods = table_parser.parse()
    print(f"Файл:     {file_path}\n")
    print(f"Результат помесячно.")
    for period in periods.keys():
        print(f"{period}: {periods[period]}")


if __name__ == "__main__":
    main()
