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
        # Чтение Excel файла
        import pandas as pd
        print(type(file))
        df = pd.read_excel(file)
        
        # # Пример обработки: подсчёт строк и столбцов
        # result = {
        #     "rows": len(df),
        #     "columns": len(df.columns),
        #     "preview": df.head().to_dict()
        # }
        return jsonify({"response": "OK"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500




    return "parse endpoint"


@app.route("/create_doc")
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"
