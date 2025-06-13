import io
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from datetime import date, datetime
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
from legal_doc_inspector.doc_creator.penalty_table_creator import PenaltyTableCreator
from legal_doc_inspector.doc_parser.claim_parser import ClaimParser
from legal_doc_inspector.doc_parser.contract_parser import ContractParser
from legal_doc_inspector.doc_parser.html_parser import parse_html

# from .llm_functions import parse_contract, parse_zip, parse_claim
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


@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods=["POST"])
def parse():
    # для дебага без использования видеокарты
    with open(str("data/response_json_example.json")) as json_file:
        data = json.load(json_file)
        # print(type(data))
        data["results_of_name_parser"] = {}
        data["results_of_name_parser"]["defendant_info"] = {}
        data["results_of_name_parser"]["defendant_info"]["inn"] = "7721064162"
        name, address, kpp, ogrn = parse_html(7721064162)
        data["results_of_name_parser"]["defendant_info"]["name"] = name
        data["results_of_name_parser"]["defendant_info"]["address"] = address
        data["results_of_name_parser"]["defendant_info"]["kpp"] = kpp
        data["results_of_name_parser"]["defendant_info"]["ogrn"] = ogrn
        return jsonify(data), 200

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
        service_type, overdue_date = parse_contract(contract_file, contract_parser)
        pdf_pars_dict[f"contract_{i}"] = {}
        pdf_pars_dict[f"contract_{i}"]["service_type"] = service_type
        pdf_pars_dict[f"contract_{i}"]["overdue_date"] = overdue_date

    # Zip архив
    for i, folder in enumerate(uploaded_files["zip_file"]):
        zip_names = parse_zip(folder, zip_parser)
        pdf_pars_dict[f"zip_{i}"] = zip_names

    # Претензия
    for i, claim_file in enumerate(uploaded_files["claim_file"]):
        plaintiff_inn, claim_number, claim_date = parse_claim(claim_file, claim_parser)
        plaintiff_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(
            plaintiff_inn
        )

        pdf_pars_dict[f"claim_{i}"] = {}
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"] = {}
        pdf_pars_dict[f"claim_{i}"]["claim_number"] = claim_number
        pdf_pars_dict[f"claim_{i}"]["claim_date"] = claim_date
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_name"] = plaintiff_name
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"][
            "plaintiff_address"
        ] = plaintiff_address
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_inn"] = plaintiff_inn
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_kpp"] = plaintiff_kpp
        pdf_pars_dict[f"claim_{i}"]["plaintiff_info"]["plaintiff_ogrn"] = plaintiff_ogrn
        # TODO   <- КАЙТЕН ЕБАТЬ:
        # Получить все данные истца из API по инну

    # парсинг таблиц и создание документа с расчётом к иску
    table_creator = PenaltyTableCreator()
    table_parser = TableParser()
    penalty_calculator = Penalty_calculator()

    list_of_tables_info = []

    result_dict_json = []

    parsing_table_results = []

    for table_path in data["results_of_data_saving"]["certificate_file"]:

        parsing_table_result = table_parser.parse_excel_table(table_path)
        result_dict = penalty_calculator.calculate_penalty_from_doc(
            data=parsing_table_result,
            company_type=company_type,
            current_date=date_request,
            day_of_penalty=day_of_penalty,
        )

        result_dict_json.append(
            table_creator.convert_datetime_keys(
                table_creator.group_by_month(result_dict)
            )
        )

        contract_number, start_date, end_date, all_debt, all_penalty = (
            table_creator.create_penalty_table_from_json(
                name=Path(folder, "расчёт к иску.docx"),
                data=result_dict,
                start_date=result_dict[0]["start"].strftime("%d.%m.%Y"),
                end_date=date_request.strftime("%d.%m.%Y"),
                contract_number=parsing_table_result["номер договора"],
            )
        )

        list_of_tables_info.append(
            (contract_number, start_date, end_date, all_debt, all_penalty)
        )

    table_creator.create_result_table(
        list_of_tables_info, Path(folder, "расчёт к иску.docx")
    )

    bio = io.BytesIO()
    table_creator.doc.save(bio)
    bio.seek(0)

    uploaded_files["lawsuit_calculating"] = str(Path(folder, "расчёт к иску.docx"))

    result_json = dict()
    result_json["files_table"] = uploaded_files
    result_json["result_of_penalty_calculator"] = result_dict_json
    result_json["result_of_llm_parsers"] = pdf_pars_dict

    with open(str(Path(folder, "index.json")), "w") as json_file:
        json.dump(uploaded_files, json_file)

    return jsonify(result_json), 200


@app.route("/create_doc", methods=["POST"])
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"


@app.route("/create_calculating_table", methods=["POST"])
def create_table():
    return 200


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
                                try:
                                    file_name = zip_info.filename.encode(
                                        "cp437"
                                    ).decode("utf-8")
                                except UnicodeDecodeError:
                                    file_name = zip_info.filename.encode(
                                        "cp437"
                                    ).decode("cp866")
                                zip_info.filename = file_name
                                zip_ref.extract(zip_info, archive_folder)
                    uploaded_files[dest_key].append(str(archive_folder))

    return uploaded_files
