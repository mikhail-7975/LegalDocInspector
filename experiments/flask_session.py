from flask import Flask, session, request, jsonify
from flask_session import Session  # For server-side sessions

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure server-side session (optional but recommended for production)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/endpoint1', methods=['POST'])
def endpoint1():
    data = request.get_json()
    session['data1'] = data  # Store data in session
    return jsonify({"status": "saved in endpoint1"})

@app.route('/endpoint2', methods=['POST'])
def endpoint2():
    data = request.get_json()
    session['data2'] = data  # Store data in session
    return jsonify({"status": "saved in endpoint2"})

@app.route('/endpoint3', methods=['POST'])
def endpoint3():
    data = request.get_json()
    session['data3'] = data  # Store data in session
    
    # Access all stored data
    all_data = {
        'data1': session.get('data1'),
        'data2': session.get('data2'),
        'data3': session.get('data3')
    }
    
    return jsonify({"all_data": all_data})