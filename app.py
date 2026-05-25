"""
Colmena PDF Service
Microservicio Flask que recibe HTML base64 y devuelve PDF base64
usando WeasyPrint para generación perfecta con CSS completo.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from weasyprint import HTML
import base64
import os

app = Flask(__name__)
CORS(app)  # Permite peticiones desde cualquier origen (Hostinger)

@app.route('/', methods=['GET'])
def health():
    return jsonify({'ok': True, 'service': 'Colmena PDF Service v1', 'status': 'running'})

@app.route('/pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        if not data or 'html' not in data:
            return jsonify({'ok': False, 'error': 'Falta el campo html'}), 400

        # Decodificar HTML base64
        html_bytes = base64.b64decode(data['html'])
        html_str   = html_bytes.decode('utf-8')

        # Generar PDF con WeasyPrint
        pdf_bytes = HTML(string=html_str).write_pdf()

        # Devolver PDF como base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        return jsonify({'ok': True, 'pdf': pdf_b64})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
