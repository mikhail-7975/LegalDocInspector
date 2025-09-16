import io # работа с zip
import json # работа с json документами
import os
import re # работа с текстом
import tempfile
import zipfile # рабоат с архивами
from collections import defaultdict # словари
from datetime import date, datetime # работа с датой
from pathlib import Path

# from configs.config import AppConfig, load_yaml_config # конфиги

# from ___legal_doc_inspector.doc_parser.table_parser_new import TableParser
from LegalDocInspector.legal_doc_inspector.utils.calculator_adapter import convert_data
from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import calculate_penalty

from configs.config import AppConfig
# import pandas as pd # работа с датафреймами
import requests # запросы
from bs4 import BeautifulSoup # раьота с html
from flask import Flask, Response, g, jsonify, render_template, request, send_file # бекэнд
from flask import current_app as app
from flask import session

from werkzeug.utils import secure_filename

from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import parse_html # класс

from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import CalculationClaimGenerator
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator

# from .llm_functions import parse_claim, parse_contract
# app.secret_key = os.urandom(30).hex()
@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods=["POST"])
def parse():

    table_parser = g.table_parser

    current_config:AppConfig = g.config
    # save_data_folder = Path("/tmp/doc_inspector_data")
    save_data_folder = current_config.save_data_folder

    date_request = request.form.get("date")
    date_request = date.fromisoformat(date_request).strftime("%d.%m.%Y")
    complects_count = int(request.form.get('complects_count'))

    folder = Path(
        save_data_folder, secure_filename(f"documents_from_request_{datetime.now()}")
    )
    # session['path_to_save'] = str(folder)
    request.files

    folder.mkdir(exist_ok=True, parents=True)

    result_json = dict()
    parsing_table_results = []
    uploaded_files = defaultdict(lambda : [])
    for complect_id in range(1, complects_count+1):
        complect_folder = Path(folder, f'complect_{complect_id}')
        complect_folder.mkdir(exist_ok=True, parents=True)

        complect_claim_file = request.files[f"complect_{complect_id}_claim_file"]
        complect_contract_file = request.files[f'complect_{complect_id}_contract_file']
        complect_certificate_file = request.files[f'complect_{complect_id}_certificate_file']

        # договор
        contract_file_path = Path(complect_folder, secure_filename(complect_contract_file.filename))
        complect_contract_file.save(contract_file_path)
        uploaded_files['contract_file'].append(str(contract_file_path))

        # претензия
        claim_file_path = Path(complect_folder, secure_filename(complect_claim_file.filename))
        complect_claim_file.save(claim_file_path)
        uploaded_files['claim_file'].append(str(claim_file_path))

        # справка
        certificate_file_path = Path(complect_folder, secure_filename(complect_certificate_file.filename))
        complect_certificate_file.save(certificate_file_path)
        uploaded_files['certificate_file'].append(str(certificate_file_path))


        table_parser.open(str(certificate_file_path))
        result = table_parser.parse()
        defendant_inn = table_parser.parse_defendant_inn()
        contract_number = table_parser.parse_contract_number()
        # print(contract_number)
        table_parser.close()

        # LLM parser

        # llm_contract_number, service_type_info, overdue_date_info = parse_contract(contract_file_path)
        # # print("contract parser done!")
        # plaintiff_inn, claim_number, claim_date = parse_claim(claim_file_path)
        # claim_info = {"claim_date": str(claim_date), "claim_number": str(claim_number)}
        # # print("claim parser done!")

        overdue_date_info  = "(заглушка) В следующем фрагменте указан срок, в течение которого Исполнитель должен произвести оплату:\n\n\"5. 5. Исполнитель в срок до 18-го числа месяца, следующего за расчетным, производит оплату стоимости тепловой энергии, теплоносителя, указанной в счете. Датой оплаты считается дата поступления денежных средств на расчетный счет Теплоснабжающей организации.\""
        service_type_info = "(заглушка) тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))"
        claim_info = {"claim_date": '01.01.2000', "claim_number": '123456'}

        parsing_table_results.append((result, contract_number, overdue_date_info, service_type_info, claim_info))

    result_json['table_parser_result'] = parsing_table_results

    result_json['results_of_name_parser'] = {}
    result_json['results_of_name_parser']['defendant_info'] = {}
    result_json['results_of_name_parser']['defendant_info']['inn'] = f'{defendant_inn}'

    # Получение данных ответчика по его инн
    full_name, short_name, address, kpp, ogrn = parse_html(int(defendant_inn))
    result_json['results_of_name_parser']['defendant_info']['full_name'] = full_name
    result_json['results_of_name_parser']['defendant_info']['short_name'] = short_name
    result_json['results_of_name_parser']['defendant_info']['address'] = address
    result_json['results_of_name_parser']['defendant_info']['kpp'] = kpp
    result_json['results_of_name_parser']['defendant_info']['ogrn'] = ogrn
    result_json['path_to_save'] = str(folder.resolve())

    # result_json['result_of_llm_parsers'] = pdf_pars_dict

    with open(str(Path(folder, "result_parser.json")),"w") as json_file:
        # json.dump(result_json, json_file)
        json.dump(result_json, json_file, indent=4, ensure_ascii=False)

    return jsonify(result_json), 200

@app.route("/calculate_penalty", methods=["POST"])
def calc_penalty():
    data = request.json
    calculated_results = []
    last_days_of_penalty = []
    contract_points = []
    response = {}
    for parsing_result in data['parsing_results']:
        calculated_data = calculate_penalty(
            parsed_data=parsing_result['parsed_info'],
            day_of_penalty=parsing_result['day_of_penalty'],
            company_type=data['company_type'],
            end_date=data['end_date'],
        )
        calculated_data['contract_number'] = parsing_result['contract_number']
        last_days_of_penalty.append(parsing_result['day_of_penalty'])
        contract_points.append(parsing_result['contract_point'])
        calculated_results.append(sort_data_structure(calculated_data))

    converted_data = convert_data(
        calculated_data_list=calculated_results,
        last_days_of_penalty=last_days_of_penalty,
        contract_points=contract_points,
        company_type=data['company_type'],
        current_date=data['end_date']
    )
    # print(converted_data , '\n' , calculated_results)
    response['claim_data'] = converted_data
    response['calculator_list']  = calculated_results
    return jsonify(response), 200

@app.route("/create_doc", methods=["POST"])
def create_doc():

    request_json = request.json
    calculator_list, claim_data, path_to_save = request_json['calculator_list'], request_json['claim_data'], request_json['path_to_save']
    claim_gen:ClaimGenerator = g.claim_generator
    # path_to_save = str(Path('/tmp', 'doc_inspector_data', 'ИСК.docx'))
    path_to_save = str(Path(path_to_save, 'ИСК.docx'))
    # path_to_template = str(Path("/home/mkalinichenko/projects/LegalDocInspector/data/templates/claim.docx"))
    config:AppConfig = g.config
    path_to_template = config.claim_template_path
    claim_gen.make_instance(config=claim_data,
                            template_filename=path_to_template,
                            output_filename=path_to_save)
    
    return send_file(path_to_save, as_attachment=True), 200


@app.route("/create_calculating_table", methods=["POST"])
def create_table():
    calc_claim_generator:CalculationClaimGenerator = g.calc_claim_generator
    request_json = request.json
    calculator_list, claim_data, path_to_save = request_json['calculator_list'], request_json['claim_data'], request_json['path_to_save']
    calculator_list_sorted = [sort_data_structure(calculator_list[i]) for i in range(len(calculator_list))]
    # path_to_save = str(Path('/tmp', 'doc_inspector_data', 'расчёт к иску.docx'))
    path_to_save = str(Path(path_to_save, 'расчёт к иску.docx'))

    config:AppConfig = g.config
    path_to_template = config.calculation_claim_template_path

    # path_to_template = str(Path("/home/mkalinichenko/projects/LegalDocInspector/data/templates/calculation_claim.docx"))
    calc_claim_generator.make_instance(config=calculator_list_sorted,
                                       config2=claim_data,
                                       template_filename=path_to_template,
                                       output_filename=path_to_save)
    # if not os.path.exists(path_to_table):
    #     return jsonify({"error": "Файл не найден"}), 404

    return send_file(path_to_save, as_attachment=True), 200


def get_request_files(
    allowed_keys: dict, path_to_folder: Path, uploaded_files: defaultdict
):
    for file_key in request.files:
        for dest_key, pattern in allowed_keys.items():
            if re.match(pattern, file_key):
                file = request.files[file_key]
                filename = secure_filename(file.filename)
                if filename and dest_key != "zip_file":
                    file.save(Path(path_to_folder, filename))
                    uploaded_files[dest_key].append(str(Path(path_to_folder, filename)))

                if filename and dest_key == "zip_file":
                    archive_folder = Path(path_to_folder, "archive")
                    archive_folder.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory() as temp_dir:
                        path_to_archive = Path(temp_dir, secure_filename(file.filename))
                        file.save(path_to_archive)
                        with zipfile.ZipFile(path_to_archive, "r") as zip_ref:
                            for zip_info in zip_ref.infolist():
                                raw_filename = zip_info.orig_filename
                                decoded_name = safe_decode_filename(raw_filename)
                                zip_info.filename = decoded_name
                                zip_ref.extract(zip_info, archive_folder)
                    uploaded_files[dest_key].append(str(archive_folder))

    return uploaded_files


def find_parent_dir_with_name(start_path: Path, target_name: str) -> Path | None:
    """
    Поднимается по родительским директориям,
    пока не найдёт папку с нужным именем.
    Возвращает её путь или None, если не найдено.
    """
    for parent in [start_path, *start_path.parents]:
        if target_name in parent.name:
            return parent
    return None

def safe_decode_filename_linux(filename_bytes: str): # Linux
    try:
        return filename_bytes.encode('utf-8').decode('utf-8')
    except UnicodeDecodeError:
        pass
    except UnicodeEncodeError:
        pass
    try:
        return filename_bytes.encode('utf-8').decode('cp866')
    except UnicodeDecodeError:
        pass

    except UnicodeEncodeError:
        pass

    try:
        return filename_bytes.encode('utf-8').decode('cp437')
    except UnicodeDecodeError:
        pass
    except UnicodeEncodeError:
        pass

    try:
        return filename_bytes.encode('utf-8').decode('cp1251')
    except UnicodeDecodeError:
        pass
    except UnicodeEncodeError:
        pass

    return filename_bytes.encode('utf-8').decode('utf-8', errors='replace')

def safe_decode_filename(filename_bytes: str): # Windows
    try:
        return filename_bytes.encode('cp437').decode('utf-8')
    except UnicodeDecodeError:
        pass
    except UnicodeEncodeError:
        return safe_decode_filename_linux(filename_bytes)

    try:
        return filename_bytes.encode('cp437').decode('cp866')
    except UnicodeDecodeError:
        pass

    try:
        return filename_bytes.encode('cp437').decode('cp437')
    except UnicodeDecodeError:
        pass

    try:
        return filename_bytes.encode('cp437').decode('cp1251')
    except UnicodeDecodeError:
        pass

    return filename_bytes.encode('cp437').decode('utf-8', errors='replace')


def sort_data_structure(data:dict) -> dict:
    """
    Сортирует структуру данных в нужном порядке:
    1. start_of_table
    2. Месяцы в хронологическом порядке
    3. end_of_table1
    4. end_of_table2
    5. debt_info
    6. contract_number
    """

    # Создаем новый упорядоченный словарь
    sorted_data = {}

    # 1. Добавляем start_of_table первым
    if 'start_of_table' in data:
        sorted_data['start_of_table'] = data['start_of_table']

    # 2. Собираем и сортируем месяцы
    months = []
    for key in data.keys():
        # Проверяем, что ключ соответствует формату "Месяц ГГГГ"
        if isinstance(key, str) and len(key.split()) == 2:
            try:
                # Пробуем разобрать месяц и год
                month_name, year_str = key.split()
                year = int(year_str)
                months.append((key, year, month_name))
            except (ValueError, IndexError):
                # Если не получается разобрать, пропускаем
                continue

    # Сортируем месяцы: сначала по году, потом по названию месяца
    month_order = {
        'Январь': 1, 'Февраль': 2, 'Март': 3, 'Апрель': 4,
        'Май': 5, 'Июнь': 6, 'Июль': 7, 'Август': 8,
        'Сентябрь': 9, 'Октябрь': 10, 'Ноябрь': 11, 'Декабрь': 12
    }

    def month_sort_key(item):
        key, year, month_name = item
        return (year, month_order.get(month_name, 99))

    sorted_months = sorted(months, key=month_sort_key)

    # Добавляем отсортированные месяцы
    for month_key, _, _ in sorted_months:
        sorted_data[month_key] = data[month_key]

    # 3-6. Добавляем остальные элементы в нужном порядке
    elements_order = ['end_of_table1', 'end_of_table2', 'debt_info', 'contract_number']

    for element in elements_order:
        if element in data:
            sorted_data[element] = data[element]

    return sorted_data