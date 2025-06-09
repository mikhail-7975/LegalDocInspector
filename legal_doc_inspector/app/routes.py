import tempfile
import zipfile
import json
import re
import io
from collections import defaultdict

from configs.config import AppConfig, load_yaml_config
from legal_doc_inspector.doc_parser.table_parser import TableParser 
from legal_doc_inspector.penalty_calculator.penalty_calculator import Penalty_calculator
from legal_doc_inspector.doc_creator.penalty_table_creator import PenaltyTableCreator

from legal_doc_inspector.doc_parser.contract_parser import ContractParser
from legal_doc_inspector.doc_parser.zip_parser import ZipParser
from legal_doc_inspector.doc_parser.pret_parser import PretParser

from pathlib import Path
from datetime import datetime,date
from werkzeug.utils import secure_filename

import pandas as pd
from flask import Flask, Response, jsonify, send_file
from flask import current_app as app
from flask import g, render_template, request
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2.5-Omni-3B",
    torch_dtype="auto",
    device_map="auto",
    enable_audio_output=False,
)
processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-3B")
zip_parser = ZipParser(model, processor)
contract_parser = ContractParser(model, processor)
pret_patser = PretParser(model, processor)

@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods = ['POST'])
def parse():
    current_config = g.config
    save_data_folder = Path(current_config.save_data_folder)

    date_request = request.form.get('date')
    date_request = date.fromisoformat(date_request)
    company_type = request.form.get('company_type')
    day_of_penalty = request.form.get('day_of_penalty')
    allowed_keys = {'zip_file':r'zip_file$', 'claim_file':r'claim_file*', 'contract_file':r'contract_file*', 'certificate_file':r'certificate_file*'}
    uploaded_files = defaultdict(lambda: [])

    folder = Path(save_data_folder, secure_filename(f"documents_from_request_{datetime.now()}"))
    folder.mkdir(exist_ok=True, parents=True)

    uploaded_files = get_request_files(allowed_keys=allowed_keys,
                      path_to_folder=folder,
                      uploaded_files=uploaded_files)

    data = dict()
    with open(str(Path(folder, "index.json")),"w") as json_file:
        json.dump(uploaded_files, json_file)

    
    with open(str(Path(folder, "index.json"))) as json_file:
        data['results_of_data_saving'] = json.load(json_file)

    result_dict = TableParser().parse_excel_table(data['results_of_data_saving']['certificate_file'])
    result_dict = Penalty_calculator().calculate_penalty_from_doc(data=result_dict,
                                                                    company_type=company_type,
                                                                    current_date=date_request)
    # Договор
    contract_text_chunks = contract_parser.pdf_to_text(uploaded_files['contract_file'])
    usluga_type = contract_parser.find_info(contract_text_chunks, 'Какой тип услуги указан в договоре? Выбери: вода, отопление или оба, ответь одним словом?', Usluga = True)
    prosrochka_date = contract_parser.find_info(contract_text_chunks, 'В какой срок исполнитель должен произвести оплату?', Usluga = False) 

    if (usluga_type == "Оба." or usluga_type == "Оба"): usluga_type = 'тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))'
    if (usluga_type == "Вода." or usluga_type == "Вода"): usluga_type = 'горячую воду (ГВС))'
    if (usluga_type == "Отопление." or usluga_type == "Отопление"): usluga_type = 'тепловую энергию/теплоноситель (ТЭ)'

    # Zip архив
    zip_docs_texts = zip_parser.get_texts(archive_folder)
    zip_names = zip_parser.find_names(zip_docs_texts)

    # Претензия
    
    claim_text = pret_patser.pdf_to_text(uploaded_files['claim_file'])
    otv_adress = pret_patser.find_info(claim_text, "найди адрес ответчика?")
    ist_data = pret_patser.find_info(claim_text, 'найди все данные истца?')
    claim_date = pret_patser.find_info(claim_text, 'найди дату претензии? напиши только дату в формате дата:')
    claim_number = pret_patser.find_info(claim_text, 'найди номер претензии? напиши только номер в формате номер:')
    claim_number = ''.join(filter(str.isdigit, claim_number))
    
    data['results_of_table_parsing'] = PenaltyTableCreator().create_penalty_table_from_json(
            name = Path(folder,'расчёт к иску.docx') ,
            data=result_dict,
            start_date='тут должна быть дата',
            end_date='тут должна была быть дата',
            contract_number="тут должно было быть номер контракта"
        )
    
    data['contract_info'] = {}
    data['contract_info']['usluga_type'] = usluga_type
    data['contract_info']['prosrochka_date'] = prosrochka_date 

    # парсинг таблиц и создание документа с расчётом к иску
    table_creator = PenaltyTableCreator()
    list_of_tables_info = []

    for table_path in data['results_of_data_saving']['certificate_file']:


        parsing_table_result = TableParser().parse_excel_table(table_path)
        result_dict = Penalty_calculator().calculate_penalty_from_doc(data=parsing_table_result,
                                                                        company_type=company_type,
                                                                        current_date=date_request,
                                                                        day_of_penalty=day_of_penalty)
    
        contract_number, start_date, end_date, all_debt, all_penalty = table_creator.create_penalty_table_from_json(
                name = Path(folder,'расчёт к иску.docx') ,
                data=result_dict,
                start_date=result_dict[0]['start'].strftime("%d.%m.%Y"),
                end_date=date_request.strftime('%d.%m.%Y'),
                contract_number=parsing_table_result['номер договора'],
            )
        
        
        list_of_tables_info.append((contract_number, start_date, end_date, all_debt, all_penalty))
    
    table_creator.create_result_table(list_of_tables_info,Path(folder,'расчёт к иску.docx'))

    bio = io.BytesIO()
    table_creator.doc.save(bio)
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name='расчёт_к_иску.docx'
    ) , 200
    data['zip_names'] = zip_names

    data['claim_info'] = {}
    data['claim_info']["otv_adress"] = otv_adress.split("адрес:")[-1].strip()
    data['claim_info']["ist_data"] = ist_data
    data['claim_info']["claim_date"] = claim_date
    data['claim_info']["claim_number"] = claim_number.split()
    return jsonify(data) , 200

    # except Exception as e:
    #     print(e)
    #     return jsonify({"error": str(e)}), 500

@app.route("/create_doc", methods = ['POST'])
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"



def get_request_files(allowed_keys:dict, path_to_folder:Path, uploaded_files:defaultdict):
    for file_key in request.files:
        for dest_key, pattern in allowed_keys.items():
            if re.match(pattern,file_key):
                file = request.files[file_key]
                filename = secure_filename(file.filename)
                if filename and dest_key != 'zip_file':
                    file.save(Path(path_to_folder, filename))
                    uploaded_files[dest_key].append(str(Path(path_to_folder, filename)))
                
                if filename and dest_key == "zip_file":
                    archive_folder = Path(path_to_folder, "archive")
                    archive_folder.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory() as temp_dir:
                        path_to_archive = Path(temp_dir, secure_filename(file.filename)) 
                        file.save(path_to_archive)
                        with zipfile.ZipFile(path_to_archive, 'r') as zip_ref:
                            zip_ref.extractall(archive_folder)
                    uploaded_files[dest_key].append(str(archive_folder))
    
    return uploaded_files