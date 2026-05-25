from flask import Flask, request, jsonify
from flask_cors import CORS
from weasyprint import HTML
import base64, os, json, urllib.request, urllib.error, re

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
    return jsonify({'ok': True, 'service': 'Colmena PDF Service v5'})

# ── PDF visual (páginas 1-4) ─────────────────────────────────────────────────
@app.route('/pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    try:
        data = request.get_json(force=True)
        if not data or 'html' not in data:
            return jsonify({'ok': False, 'error': 'Falta el campo html'}), 400
        html_str  = base64.b64decode(data['html']).decode('utf-8')
        pdf_bytes = HTML(string=html_str).write_pdf()
        return jsonify({'ok': True, 'pdf': base64.b64encode(pdf_bytes).decode('utf-8')})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ── CSS del reporte narrativo ─────────────────────────────────────────────────
REPORTE_CSS = """
<style>
@page { size: A4; margin: 20mm 25mm; }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; color: #1e293b; font-size: 10.5pt; line-height: 1.75; background: #fff; }
h1 { font-size: 20pt; font-weight: 900; color: #1e293b; border-bottom: 4px solid #f59e0b; padding-bottom: 10px; margin-bottom: 6px; margin-top: 0; }
.subtitulo { color: #64748b; font-size: 9pt; margin-bottom: 28px; }
h2 { font-size: 13pt; font-weight: 800; color: #1d4ed8; margin-top: 28px; margin-bottom: 8px; padding-left: 12px; border-left: 4px solid #1d4ed8; }
h3 { font-size: 10.5pt; font-weight: 700; color: #475569; margin-top: 16px; margin-bottom: 6px; }
p { margin-bottom: 12px; }
ul, ol { margin: 10px 0 14px 20px; padding: 0; }
li { margin-bottom: 7px; }
strong { color: #1e293b; }
.destaca { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; }
.alerta { background: #fef2f2; border-left: 4px solid #dc2626; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; }
.exito { background: #f0fdf4; border-left: 4px solid #16a34a; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 16px 0; }
.paso { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin: 10px 0; }
.paso-num { display: inline-block; background: #1d4ed8; color: #fff; font-weight: 800; font-size: 9pt; padding: 2px 8px; border-radius: 4px; margin-bottom: 6px; }
.firma { background: #1e293b; color: #fff; padding: 20px 24px; border-radius: 10px; margin-top: 32px; }
.firma strong { color: #f59e0b; font-size: 12pt; display: block; margin-bottom: 6px; }
.firma p { color: #94a3b8; font-size: 9pt; margin: 0; }
</style>
"""

# ── Limpiar respuesta de Claude ───────────────────────────────────────────────
def limpiar_html(texto):
    # Quitar bloques markdown ```html ... ```
    texto = re.sub(r'^```html?\s*', '', texto.strip(), flags=re.IGNORECASE)
    texto = re.sub(r'```\s*$', '', texto.strip())
    # Si no tiene <html>, envolverlo
    if '<html' not in texto.lower():
        # Quitar <style> que venga del prompt (ya lo inyectamos nosotros)
        texto = re.sub(r'<style>.*?</style>', '', texto, flags=re.DOTALL)
        return f"<div>{texto}</div>"
    return texto

# ── Reporte completo: visual + narrativo IA en un solo PDF ───────────────────
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

        # 1. Llamar a Claude
        payload = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 4000,
            'system': 'Eres una mentora de negocios. Devuelve UNICAMENTE el contenido HTML del reporte, sin markdown, sin bloques de codigo, sin explicaciones. Empieza directamente con las etiquetas HTML del contenido.',
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

        html_raw = result.get('content', [{}])[0].get('text', '')
        if not html_raw:
            return jsonify({'ok': False, 'error': 'Respuesta vacia de Claude'}), 500

        # 2. Limpiar y preparar HTML narrativo
        html_narrativo = limpiar_html(html_raw)

        # 3. Página de portada del reporte narrativo con diseño Colmena
        portada_narrativo = f"""
        <div style="page-break-before:always; background:#1e293b; color:#fff;
                    padding:40mm 30mm; min-height:100vh; display:flex;
                    flex-direction:column; justify-content:center;">
          <div style="color:#f59e0b;font-size:11pt;font-weight:700;
                      text-transform:uppercase;letter-spacing:3px;margin-bottom:16px;">
            Negocio Colmena
          </div>
          <div style="font-size:28pt;font-weight:900;line-height:1.2;margin-bottom:12px;">
            Reporte Narrativo<br/>de Diagnóstico
          </div>
          <div style="color:#94a3b8;font-size:11pt;margin-bottom:32px;">
            Análisis personalizado generado con Inteligencia Artificial
          </div>
          <div style="background:#334155;border-radius:10px;padding:20px 24px;">
            <div style="color:#f59e0b;font-size:9pt;text-transform:uppercase;
                        letter-spacing:2px;margin-bottom:8px;">Elaborado para</div>
            <div style="font-size:14pt;font-weight:800;">{data.get('negocio','')}</div>
            <div style="color:#94a3b8;font-size:9pt;margin-top:4px;">
              {data.get('fecha','')} &nbsp;·&nbsp; {data.get('ciudad','')} &nbsp;·&nbsp; {data.get('etapa','')}
            </div>
          </div>
        </div>
        """

        # 4. Contenido narrativo con CSS propio
        cuerpo_narrativo = f"""
        <div style="page-break-before:always;">
          <!DOCTYPE html><html><head><meta charset="UTF-8"/>{REPORTE_CSS}</head>
          <body>{html_narrativo}</body></html>
        </div>
        """

        # 5. HTML visual (páginas 1-4)
        html_visual = base64.b64decode(data['html']).decode('utf-8')

        # 6. Combinar todo en un solo HTML
        html_combinado = html_visual.replace(
            '</body></html>',
            portada_narrativo + cuerpo_narrativo + '</body></html>'
        )

        # 7. Generar PDF con WeasyPrint
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
