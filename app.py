"""
Colmena PDF Service v2
Microservicio Flask con WeasyPrint y CORS abierto
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from weasyprint import HTML
import base64, os

app = Flask(__name__)

# CORS completamente abierto — acepta peticiones desde cualquier origen
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/', methods=['GET'])
def health():
    return jsonify({'ok': True, 'service': 'Colmena PDF Service v2'})

@app.route('/pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
    # Responder preflight CORS
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    try:
        data = request.get_json(force=True)
        if not data or 'html' not in data:
            return jsonify({'ok': False, 'error': 'Falta el campo html'}), 400
        html_bytes = base64.b64decode(data['html'])
        html_str   = html_bytes.decode('utf-8')
        pdf_bytes  = HTML(string=html_str).write_pdf()
        pdf_b64    = base64.b64encode(pdf_bytes).decode('utf-8')
        return jsonify({'ok': True, 'pdf': pdf_b64})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
