import shutil
from pathlib import Path
import json

from TableParser import TableParser


def copy_part(root_dirname, dst_dirname):
    # Определяем пути
    ROOT_DIR = Path(root_dirname)  # папка docs
    CLAIMS_DIR = ROOT_DIR / "claims"
    PART1_DIR = Path(dst_dirname)  # Теперь part1 — отдельная папка на уровне выше docs

    # Создаём part1 в текущей директории (рядом с docs)
    PART1_DIR.mkdir(exist_ok=True)

    print(f"Копирование папок из {CLAIMS_DIR} в {PART1_DIR}\n")

    for claim_folder in CLAIMS_DIR.iterdir():
        if claim_folder.is_dir():  # claim_001, claim_002 и т.д.
            print(f"📁 Вход в: {claim_folder.name}")
            for level1_folder in claim_folder.iterdir():
                if level1_folder.is_dir():  # например, some_subdir
                    print(f"  🔍 Проверка подпапки: {level1_folder.name}")
                    for doc_folder in level1_folder.iterdir():
                        if doc_folder.is_dir():  # нужные папки с документами
                            dest = PART1_DIR / doc_folder.name

                            # Обработка конфликта имён
                            counter = 1
                            original_dest = dest
                            while dest.exists():
                                counter += 1
                                dest = PART1_DIR / f"{original_dest.name}_{counter}"

                            # Копируем
                            shutil.copytree(doc_folder, dest)
                            if counter == 1:
                                print(f"    ✅ {doc_folder.name} → {dest}")
                            else:
                                print(f"    ✅ {doc_folder.name} → {dest} (переименовано)")
                        else:
                            print(f"    ⚠️ Пропущен файл: {doc_folder.name}")
                else:
                    print(f"  ⚠️ Пропущен файл: {level1_folder.name}")

    print(f"\n✅ Готово! Все папки скопированы в: {PART1_DIR.absolute()}")


def answer_pdf(filename: str, location: str):
    data = {
        "contract_number": f"{location.split('/')[-1]}",   # Номер договора
        "plaintiff_INN": "",   # ИНН истца
        "defendant_INN": "",   # ИНН ответчика
        "settlement_date": "",   # Дата совершения расчётов по договору
        "clause_of_the_contract": "",   # Номер пункта договора с информацией о дате платежа
        "type_of_contract": "",   # Тип договора
        "number_of_claim": "",   # Номер претензии
        "claim_date": "",   # Дата составления претензии
        "plaintiff_full_name": "",   # Дата составления претензии
        "defendant_full_name": "",   # Дата составления претензии
        "plaintiff_short_name": "",   # Дата составления претензии
        "defendant_short_name": "",   # Дата составления претензии
    }

    path = str(location) + "/" + filename
    with open(path, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def copy_all_documents():
    for src, dst in zip(["docs", "docs2", "docs3"], ["part1", "part2", "part3"]):
        copy_part(src, dst)


def answer_excel(config_filename: str, excel_filename: str, location: str):
    xls_path = excel_filename
    # print(f"Парсим excel: {excel_filename}")
    periods = parse_excel_data(xls_path)

    data = {
        "contract_number": f"{location.split('/')[-1]}",   # Номер договора
        "periods": []
    }

    for month in periods.keys():
        data["periods"].append({
            "period": month,
            "main_accrual": {
                "accruals": [accrual for accrual in periods[month]["accrual"]["accruals"]],
                "payments": [payment for payment in periods[month]["accrual"]["payments"]],
                "additionals": [additional for additional in periods[month]["accrual"]["additionals"]],
                "total_amount_of_accruals": periods[month]["accrual"]["total_amount_of_accruals"],
                "total_amount_of_payments": periods[month]["accrual"]["total_amount_of_payments"],
                "debt": periods[month]["accrual"]["debt"]
            }, 
            "adjustment": {
                "accruals": [accrual for accrual in periods[month]["adjustment"]["accruals"]],
                "payments": [payment for payment in periods[month]["adjustment"]["payments"]],
                "additionals": [additional for additional in periods[month]["adjustment"]["additionals"]],
                "total_amount_of_accruals": periods[month]["adjustment"]["total_amount_of_accruals"],
                "total_amount_of_payments": periods[month]["adjustment"]["total_amount_of_payments"],
                "debt": periods[month]["adjustment"]["debt"]
            }
        })

    cfg_path = str(location) + "/" + config_filename
    with open(cfg_path, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def make_answers():
    excel_answers_filename = "excel_true_answers.json"
    pdf_answer_filename = "pdf_true_answers.json"
    start_directory_src = "../test_data"
    start_directory = Path(start_directory_src)
    for part in start_directory.iterdir():
        if part.is_dir():
            for document_folder in part.iterdir():
                # print(f"document_folder: {document_folder}")
                excel_filename = find_excel_in_folder(str(document_folder))
                answer_excel(excel_answers_filename, excel_filename, str(document_folder))
                # answer_pdf(pdf_answer_filename, str(document_folder))


def parse_excel_data(file_fullpath):
    table_parser = TableParser()
    table_parser.open(file_fullpath)
    return table_parser.parse()


def find_excel_in_folder(folder_path):
    # Поддерживаемые расширения
    supported_suffixes = ['.xlsx', '.xlsm', '.xls']

    folder = Path(folder_path)

    # Ищем все Excel-файлы (включая .xls), но не временные
    excel_files = [
        f for f in folder.iterdir()
        if f.is_file() and
            f.suffix.lower() in supported_suffixes and
            not f.name.startswith('~$')
    ]

    if len(excel_files) == 0:
        print(f"⚠️ Excel-файл не найден в: {folder}")
    elif len(excel_files) > 1:
        print(f"ℹ️ Несколько Excel-файлов в: {folder}, берём первый")

    return str(excel_files[0].resolve())


def main():
    # copy_all_documents()
    make_answers()


if __name__ == "__main__":
    main()
