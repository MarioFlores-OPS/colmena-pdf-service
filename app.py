from flask import Flask, request, jsonify
from flask_cors import CORS
from weasyprint import HTML
import base64, os, json, urllib.request, urllib.error

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/', methods=['GET'])
def health():
    return jsonify({'ok': True, 'service': 'Colmena PDF + IA Service v4'})

# ── PDF visual (páginas 1–4) ────────────────────────────────────────────────
@app.route('/pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
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

# ── Reporte completo: visual + narrativo IA en un solo PDF ──────────────────
@app.route('/reporte', methods=['POST', 'OPTIONS'])
def generate_reporte_completo():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    try:
        data = request.get_json(force=True)
        if not data or 'html' not in data or 'prompt' not in data:
            return jsonify({'ok': False, 'error': 'Faltan campos html o prompt'}), 400

        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return jsonify({'ok': False, 'error': 'ANTHROPIC_API_KEY no configurada'}), 500

        # 1. Generar reporte narrativo con Claude
        payload = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 4000,
            'messages': [{'role': 'user', 'content': data['prompt']}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        html_narrativo = result.get('content', [{}])[0].get('text', '')
        if not html_narrativo:
            return jsonify({'ok': False, 'error': 'Respuesta vacía de Claude'}), 500

        # 2. Decodificar HTML visual (páginas 1–4)
        html_visual_bytes = base64.b64decode(data['html'])
        html_visual = html_visual_bytes.decode('utf-8')

        # 3. Combinar: visual + separador + narrativo en un solo HTML
        html_combinado = html_visual.replace(
            '</body></html>',
            f'''
            <div style="page-break-before:always"></div>
            <div style="font-family:Arial,sans-serif;max-width:210mm;margin:0;padding:25mm 30mm;color:#1e293b;line-height:1.7">
              {html_narrativo}
            </div>
            </body></html>'''
        )

        # 4. Generar PDF combinado con WeasyPrint
        pdf_bytes = HTML(string=html_combinado).write_pdf()
        pdf_b64   = base64.b64encode(pdf_bytes).decode('utf-8')
        return jsonify({'ok': True, 'pdf': pdf_b64})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        return jsonify({'ok': False, 'error': f'API Claude error {e.code}: {body}'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
