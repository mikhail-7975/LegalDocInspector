import io
import json
import os
import re
import tempfile
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from configs.config import AppConfig, load_yaml_config
from .llm_functions import parse_contract, parse_zip, parse_claim
from legal_doc_inspector.doc_parser.table_parser import TableParser 
from legal_doc_inspector.penalty_calculator.penalty_calculator import Penalty_calculator
from legal_doc_inspector.doc_creator.penalty_table_creator import PenaltyTableCreator
from legal_doc_inspector.doc_creator.lawsuit_creator import LawsuitCreator
from legal_doc_inspector.doc_parser.contract_parser import ContractParser
from legal_doc_inspector.doc_parser.zip_parser import ZipParser
from legal_doc_inspector.doc_parser.claim_parser import ClaimParser

from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, g, jsonify, render_template, request, send_file
from flask import current_app as app
from transformers import (
    AutoModel,
    AutoTokenizer,
    Qwen2_5OmniForConditionalGeneration,
    Qwen2_5OmniProcessor,
)
from werkzeug.utils import secure_filename

from configs.config import AppConfig, load_yaml_config
from legal_doc_inspector.doc_creator.lawsuit_creator import LawsuitCreator
from legal_doc_inspector.doc_creator.penalty_table_creator import PenaltyTableCreator
from legal_doc_inspector.doc_parser.claim_parser import ClaimParser
from legal_doc_inspector.doc_parser.contract_parser import ContractParser
from legal_doc_inspector.doc_parser.html_parser import parse_html
from legal_doc_inspector.app.utils.parse_info_by_inn import parse_html

from legal_doc_inspector.doc_parser.table_parser import TableParser
from legal_doc_inspector.doc_parser.zip_parser import ZipParser
from legal_doc_inspector.penalty_calculator.penalty_calculator import Penalty_calculator

model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2.5-Omni-3B",
    torch_dtype="auto",
    device_map="auto",
    enable_audio_output=False,
)
processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")
emb_tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased")
emb_model = AutoModel.from_pretrained("DeepPavlov/rubert-base-cased")

zip_parser = ZipParser(model, processor, emb_model, emb_tokenizer)
contract_parser = ContractParser(model, processor)
claim_parser = ClaimParser(model, processor)

# model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen2.5-Omni-3B",
#     torch_dtype="auto",
#     device_map="auto",
#     enable_audio_output=False,
# )
# processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")
# zip_parser = ZipParser(model, processor)
# contract_parser = ContractParser(model, processor)
# claim_parser = ClaimParser(model, processor)

@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods=["POST"])
def parse():
    # для дебага без использования видеокарты
    # json_example = {}
    # with open(str('data/response_json_example.json')) as json_file:
    #     json_example = json.load(json_file)
    #     # print(type(data))

    
    current_config = g.config
    save_data_folder = Path(current_config.save_data_folder)

    date_request = request.form.get("date")
    date_request = date.fromisoformat(date_request)
    company_type = request.form.get("company_type")
    day_of_penalty = request.form.get("day_of_penalty")
    allowed_keys = {
        "zip_file": r"zip_file$",
        "claim_file": r"claim_file*",
        "contract_file": r"contract_file*",
        "certificate_file": r"certificate_file*",
    }
    uploaded_files = defaultdict(lambda: [])

    folder = Path(
        save_data_folder, secure_filename(f"documents_from_request_{datetime.now()}")
    )
    folder.mkdir(exist_ok=True, parents=True)

    uploaded_files = get_request_files(
        allowed_keys=allowed_keys, path_to_folder=folder, uploaded_files=uploaded_files
    )

    data = dict()
    with open(str(Path(folder, "index.json")), "w") as json_file:
        json.dump(uploaded_files, json_file)

    with open(str(Path(folder, "index.json"))) as json_file:
        data["results_of_data_saving"] = json.load(json_file)

    pdf_pars_dict = dict()

    # Договор
    for i, contract_file in enumerate(uploaded_files["contract_file"]):
        
        contract_number, service_type, overdue_date = parse_contract(contract_file, contract_parser)
        pdf_pars_dict[f"contract_{contract_number}"] = {}
        pdf_pars_dict[f"contract_{contract_number}"]["service_type"] = service_type
        pdf_pars_dict[f"contract_{contract_number}"]["overdue_date"] = overdue_date

    # Zip архив
    for i, folder in enumerate(uploaded_files["zip_file"]):
        zip_names = parse_zip(folder, zip_parser)
        pdf_pars_dict[f"zip_{i}"] = zip_names

    # Претензия
    for i, claim_file in enumerate(uploaded_files["claim_file"]):
        plaintiff_inn, claim_number, claim_date = parse_claim(claim_file, claim_parser)
        
        #plaintiff_inn = '7720518494'
        # print(f"parsed inn - {plaintiff_inn}")
        plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(
            plaintiff_inn
        )

        pdf_pars_dict[f"claim_{i}"] = {}
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"] = {}
        pdf_pars_dict[f"claim_{i}"]["claim_number"] = claim_number
        pdf_pars_dict[f"claim_{i}"]["claim_date"] = claim_date
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_full_name"] = plaintiff_full_name
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_short_name"] = plaintiff_short_name
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_address"] = plaintiff_address
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_inn"] = plaintiff_inn
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_kpp"] = plaintiff_kpp
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_ogrn"] = plaintiff_ogrn
        

    # парсинг таблиц и создание документа с расчётом к иску
    table_creator = PenaltyTableCreator()
    table_parser = TableParser()
    penalty_calculator = Penalty_calculator()

    list_of_tables_info = []

    result_dict_json = []

    parsing_table_results = []

    for table_path in data["results_of_data_saving"]["certificate_file"]:

        parsing_table_result = table_parser.parse_excel_table(table_path)
        defendant_inn = parsing_table_result['ИНН']
        result_dict = penalty_calculator.calculate_penalty_from_doc(data=parsing_table_result,
                                                                        company_type=company_type,
                                                                        current_date=date_request,
                                                                        day_of_penalty=day_of_penalty)

        result_dict_json.append(table_creator.convert_datetime_keys(table_creator.group_by_month(result_dict)))
        
        claim_number = parsing_table_result['номер договора']
        contract_number, start_date, end_date, all_debt, all_penalty = table_creator.create_penalty_table_from_json(
                name = Path(folder,'расчёт к иску.docx') ,
                data=result_dict,
                start_date=result_dict[0]['start'].strftime("%d.%m.%Y"),
                end_date=date_request.strftime('%d.%m.%Y'),
                contract_number=f'№ {claim_number}',
            )
        
        
        list_of_tables_info.append((contract_number, start_date, end_date, all_debt, all_penalty))
    



    table_name, contracts_info = table_creator.create_result_table(list_of_tables_info,Path(folder,'расчёт к иску.docx'))

    bio = io.BytesIO()
    table_creator.doc.save(bio)
    bio.seek(0)

    uploaded_files['lawsuit_calculating'] = table_name


    result_json = dict()

    result_json['files_table']  = uploaded_files
    result_json['result_of_penalty_calculator'] = result_dict_json

    # result_json['result_of_llm_parsers'] = json_example['result_of_llm_parsers']

    result_json['results_of_name_parser'] = {}
    result_json['results_of_name_parser']['defendant_info'] = {}
    result_json['results_of_name_parser']['defendant_info']['inn'] = f'{defendant_inn}'
    full_name, short_name, address, kpp, ogrn = parse_html(int(defendant_inn))
    result_json['results_of_name_parser']['defendant_info']['full_name'] = full_name
    result_json['results_of_name_parser']['defendant_info']['short_name'] = short_name
    result_json['results_of_name_parser']['defendant_info']['address'] = address
    result_json['results_of_name_parser']['defendant_info']['kpp'] = kpp
    result_json['results_of_name_parser']['defendant_info']['ogrn'] = ogrn

    result_json['contracts_info'] = contracts_info 
    # result_json['result_of_penalty_calculator'] = result_dict_json
    result_json['result_of_llm_parsers'] = pdf_pars_dict
    
    with open(str(Path(folder, "index.json")),"w") as json_file:
        json.dump(uploaded_files, json_file)

    return jsonify(result_json), 200


@app.route("/create_doc", methods=["POST"])
def create_doc():
    request_json = request.json
    lawsuit_creator = LawsuitCreator(dict())
    path_to_save = find_parent_dir_with_name(Path(request_json['files_info']['lawsuit_calculating']),'documents_from_request')
    file = lawsuit_creator.create_lawsuit(request_json, Path(path_to_save,'ИСК.docx'))
    print(file)
    return send_file(file, as_attachment=True), 200


@app.route("/create_calculating_table", methods=["POST"])
def create_table():
    request_json = request.json
    path_to_table = request_json['lawsuit_calculating']

    if not os.path.exists(path_to_table):
        return jsonify({"error": "Файл не найден"}), 404
    
    return send_file(path_to_table, as_attachment=True), 200


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

def safe_decode_filename(filename_bytes: str):
    try:
        return filename_bytes.encode('cp437').decode('utf-8')
    except UnicodeDecodeError:
        pass

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