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

from ___legal_doc_inspector.doc_parser.table_parser_new import TableParser
from ___legal_doc_inspector.doc_parser.calculator_adapter import convert_data
from ___legal_doc_inspector.penalty_calculator.penalty_calculator_new import calculate_penalty

from pathlib import Path

# import pandas as pd # работа с датафреймами
import requests # запросы
from bs4 import BeautifulSoup # раьота с html
from flask import Flask, Response, g, jsonify, render_template, request, send_file # бекэнд
from flask import current_app as app

from werkzeug.utils import secure_filename

from ___legal_doc_inspector.doc_parser.html_parser import parse_html # функция для парсинга html
from ___legal_doc_inspector.app.utils.parse_info_by_inn import parse_html # класс

from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import CalculationClaimGenerator
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator

@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods=["POST"])
def parse():

    table_parser:TableParser = g.table_parser

    # current_config = g.config
    save_data_folder = Path("/tmp/doc_inspector_data")

    date_request = request.form.get("date")
    date_request = date.fromisoformat(date_request).strftime("%d.%m.%Y")
    complects_count = int(request.form.get('complects_count'))

    folder = Path(
        save_data_folder, secure_filename(f"documents_from_request_{datetime.now()}")
    )
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
        print(contract_number)
        table_parser.close()


        parsing_table_results.append((result, contract_number))

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


    # result_json['result_of_llm_parsers'] = pdf_pars_dict

    # with open(str(Path(folder, "index.json")),"w") as json_file:
    #     json.dump(uploaded_files, json_file)

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
        calculated_results.append(calculated_data)

    converted_data = convert_data(
        calculated_data_list=calculated_results,
        last_days_of_penalty=last_days_of_penalty,
        contract_points=contract_points,
        company_type=data['company_type'],
        current_date=data['end_date']
    )
    print(calculated_results)
    response['claim_data'] = converted_data
    response['calculator_list']  = calculated_results
    return jsonify(response), 200

@app.route("/create_doc", methods=["POST"])
def create_doc():
    
    request_json = request.json
    # lawsuit_creator = LawsuitCreator(dict())
    # path_to_save = find_parent_dir_with_name(Path(request_json['files_info']['lawsuit_calculating']),'documents_from_request')
    # with open(Path(path_to_save,'lawsuit_create.json'), "w", encoding='utf-8') as f:
    #     json.dump(request_json, f , indent=4, ensure_ascii=False)
    # file = lawsuit_creator.create_lawsuit(request_json, Path(path_to_save,'ИСК.docx'))
    # # print(file)
    # return send_file(file, as_attachment=True), 200


@app.route("/create_calculating_table", methods=["POST"])
def create_table():
    pass
    # request_json = request.json
    # path_to_table = request_json['lawsuit_calculating']

    # if not os.path.exists(path_to_table):
    #     return jsonify({"error": "Файл не найден"}), 404

    # return send_file(path_to_table, as_attachment=True), 200


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
