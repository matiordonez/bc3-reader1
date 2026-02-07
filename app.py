# -*- coding: utf-8 -*-
"""BC3 Reader - Aplicación web Flask para Vercel."""

import io
import zipfile
from flask import Flask, request, send_file, jsonify, send_from_directory

from bc3_reader import BC3Parser, export_to_xlsx_bytes, export_to_pdf_bytes

app = Flask(__name__, static_folder='public', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB límite


@app.route('/')
def index():
    """Sirve la página principal."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/convert', methods=['POST'])
def convert():
    """
    Recibe un archivo BC3 y retorna un ZIP con Excel y PDF.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    if not file.filename.lower().endswith('.bc3'):
        return jsonify({'error': 'El archivo debe tener extensión .bc3'}), 400
    
    try:
        content = file.read()
        
        # Parsear BC3
        parser = BC3Parser()
        presupuesto = parser.parse_from_bytes(content, file.filename)
        partidas = parser.get_partidas_con_detalles(presupuesto)
        
        if not partidas:
            return jsonify({'error': 'El archivo BC3 no contiene partidas válidas'}), 400
        
        titulo = "Presupuesto BC3"
        if presupuesto.version.get('empresa'):
            titulo = f"{titulo} - {presupuesto.version['empresa']}"
        
        base_name = file.filename.rsplit('.', 1)[0]
        
        # Generar Excel y PDF en memoria
        xlsx_bytes = export_to_xlsx_bytes(partidas, titulo)
        pdf_bytes = export_to_pdf_bytes(partidas, titulo)
        
        # Crear ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{base_name}.xlsx", xlsx_bytes)
            zf.writestr(f"{base_name}.pdf", pdf_bytes)
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{base_name}_bc3_export.zip"
        )
    
    except Exception as e:
        return jsonify({'error': f'Error al procesar: {str(e)}'}), 500


@app.route('/api/health')
def health():
    """Health check para Vercel."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
