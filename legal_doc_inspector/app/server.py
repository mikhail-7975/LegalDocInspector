import tempfile
import zipfile

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
    return "main page"


@app.route("/parse", methods = ['POST'])
def parse():
    # TODO
    # add pdf, exel and zip file receiving from post request
    # after navigating to endpoint:
    # - create folder with date and time in folder name
    # - save files to the folder
    # path to the folder must be loaded from config. Now it can be global variable
    if 'file' not in request.files:
        return jsonify({"error": "Файл не загружен"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Файл не выбран"}), 400

    try:
        date_request = request.form.get('date')
        date_request = date.fromisoformat(date_request)
        company_type = request.form.get('company_type')
        # Чтение Excel файла его обработка и отправка результата обработки
        if 'xls' in Path(file.filename).suffix.lower():

            folder = Path("data",secure_filename(f"{datetime.now()}"))
            folder.mkdir(exist_ok=True,parents=True)
            file.save(Path(folder,f'{file.filename}'))


        if 'zip' in Path(file.filename).suffix.lower():
            folder = Path("data",secure_filename(f"{datetime.now()}"))
            folder.mkdir(exist_ok=True,parents=True)
            with tempfile.TemporaryDirectory() as temp_dir:
                path_to_archive = Path(temp_dir,secure_filename(file.filename)) 
                file.save(path_to_archive)
                with zipfile.ZipFile(path_to_archive, 'r') as zip_ref:
                    zip_ref.extractall(folder)
            
        tables = folder.rglob('*.XLS')
        for table in tables:

            result_dict = TableParser().parse_excel_table(table)
            result_dict = Penalty_calculator().calculate_penalty_from_doc(data=result_dict,
                                                                          company_type=company_type,
                                                                          current_date=date_request)
            return jsonify(result_dict) , 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route("/create_doc", methods = ['POST'])
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"
