"""
Flask приложение для веб-интерфейса LegalDocInspector
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import sys
import os

# Добавляем путь к корню проекта для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import parse_html
    from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    # Заглушки для разработки
    def parse_html(inn):
        raise Exception("parse_html not available")
    def calculate_state_duty(cost):
        return "0"

app = Flask(__name__)
CORS(app)

BACKEND_URL = "http://localhost:5001"

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/parse-inn/<inn>')
def parse_inn(inn):
    """Получение данных по ИНН"""
    try:
        full_name, short_name, address, kpp, ogrn = parse_html(inn)
        return jsonify({
            'full_name': full_name,
            'short_name': short_name,
            'address': address,
            'kpp': kpp,
            'ogrn': ogrn
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate-duty', methods=['POST'])
def calculate_duty():
    """Расчёт госпошлины"""
    try:
        data = request.get_json()
        cost = data.get('cost')
        if cost is None:
            return jsonify({'error': 'Cost parameter is required'}), 400
        
        duty = calculate_state_duty(cost)
        return jsonify({'duty': duty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/proxy/parse', methods=['POST'])
def proxy_parse():
    """Проксирование запроса к основному серверу для парсинга документов"""
    files = {}
    data = {}
    
    # Обработка файлов из FormData
    print(f"DEBUG: Received files keys: {list(request.files.keys())}")  # Отладка
    for key, file in request.files.items():
        files[key] = (file.filename, file.stream, file.content_type)
        print(f"DEBUG: Added file {key}: {file.filename}")  # Отладка
    
    # Обработка данных
    for key, value in request.form.items():
        data[key] = value
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/parse",
            files=files,
            data=data,
            # timeout=300
        )
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/calculate-penalty', methods=['POST'])
def proxy_calculate_penalty():
    """Проксирование запроса для расчёта пени"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{BACKEND_URL}/calculate_penalty",
            json=data,
            timeout=300
        )
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/create-doc', methods=['POST'])
def proxy_create_doc():
    """Проксирование запроса для создания иска"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{BACKEND_URL}/create_doc",
            json=data,
            timeout=300
        )
        response.raise_for_status()
        return response.content, response.status_code, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/create-calculating-table', methods=['POST'])
def proxy_create_calculating_table():
    """Проксирование запроса для создания расчёта к иску"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{BACKEND_URL}/create_calculating_table",
            json=data,
            timeout=300
        )
        response.raise_for_status()
        return response.content, response.status_code, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

