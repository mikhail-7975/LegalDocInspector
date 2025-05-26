import tempfile
import zipfile
import json
from configs.config import AppConfig, load_yaml_config
from legal_doc_inspector.doc_parser.table_parser import TableParser 
from legal_doc_inspector.penalty_calculator.penalty_calculator import Penalty_calculator

from pathlib import Path
from datetime import datetime,date
from werkzeug.utils import secure_filename

import pandas as pd
from flask import Flask,Response,jsonify
from flask import current_app as app
from flask import g, render_template, request




@app.route("/")
def home():
    return "server is working"


@app.route("/parse", methods = ['POST'])
def parse():
    current_config = load_yaml_config(Path('/home/kirill/neurolumber/LegalDocInspector/configs/debug_config.yaml'))
    save_data_folder = Path(current_config.save_data_folder)
# try:
    date_request = request.form.get('date')
    date_request = date.fromisoformat(date_request)
    company_type = request.form.get('company_type')

    allowed_keys = ['zip_file', 'claim_file', 'contract_file', 'certificate_file']
    uploaded_files = {}

    folder = Path(save_data_folder,secure_filename(f"{datetime.now()}"))
    folder.mkdir(exist_ok=True,parents=True)

    for key in allowed_keys:
        if key in request.files:
            file = request.files[key]
            filename = secure_filename(file.filename)
            if filename and key != 'zip_file':

                file.save(Path(folder, filename))
                uploaded_files[key] = str(Path(folder,filename))
            
            if filename and key == "zip_file":
                archive_folder = Path(folder,"archive")
                archive_folder.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory() as temp_dir:
                    path_to_archive = Path(temp_dir,secure_filename(file.filename)) 
                    file.save(path_to_archive)
                    with zipfile.ZipFile(path_to_archive, 'r') as zip_ref:
                        zip_ref.extractall(archive_folder)
                uploaded_files[key] = str(archive_folder)

    
    with open(str(Path(folder,"index.json")),"w") as json_file:
        json.dump(uploaded_files, json_file)

    
    with open(str(Path(folder,"index.json"))) as json_file:
        data = json.load(json_file)

    # result_dict = TableParser().parse_excel_table()
    # result_dict = Penalty_calculator().calculate_penalty_from_doc(data=result_dict,
    #                                                                 company_type=company_type,
    #                                                                 current_date=date_request)
    return jsonify(data) , 200

    # except Exception as e:
    #     print(e)
    #     return jsonify({"error": str(e)}), 500

@app.route("/create_doc", methods = ['POST'])
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"
