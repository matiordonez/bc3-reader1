# -*- coding: utf-8 -*-
"""BC3 Reader - Aplicación web Flask para Vercel."""

import io
import zipfile
from flask import Flask, request, send_file, jsonify, Response

from bc3_reader import BC3Parser, export_to_xlsx_bytes, export_to_pdf_bytes

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB límite

# HTML de la página principal (embebido para que funcione en Vercel sin depender de public/)
INDEX_HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BC3 Reader - Convertidor de presupuestos</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #0f0f12; --surface: #1a1a1f; --border: #2a2a32; --text: #f0f0f5; --text-muted: #8888a0; --accent: #6366f1; --accent-hover: #818cf8; --success: #22c55e; --error: #ef4444; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; }
    .container { max-width: 480px; width: 100%; }
    h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .subtitle { color: var(--text-muted); font-size: 1rem; margin-bottom: 2rem; }
    .upload-zone { background: var(--surface); border: 2px dashed var(--border); border-radius: 16px; padding: 3rem 2rem; text-align: center; transition: all 0.2s ease; cursor: pointer; position: relative; }
    .upload-zone:hover, .upload-zone.dragover { border-color: var(--accent); background: rgba(99, 102, 241, 0.05); }
    .upload-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .upload-icon { font-size: 3rem; margin-bottom: 1rem; opacity: 0.6; }
    .upload-text { font-size: 1.1rem; margin-bottom: 0.5rem; }
    .upload-hint { font-size: 0.875rem; color: var(--text-muted); }
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 1rem 2rem; font-size: 1rem; font-weight: 600; font-family: inherit; border: none; border-radius: 12px; cursor: pointer; margin-top: 1.5rem; background: var(--accent); color: white; width: 100%; }
    .btn:hover:not(:disabled) { background: var(--accent-hover); transform: translateY(-1px); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
    .file-name { margin-top: 1rem; font-size: 0.9rem; color: var(--success); display: none; }
    .file-name.visible { display: block; }
    .message { margin-top: 1rem; padding: 1rem; border-radius: 8px; font-size: 0.9rem; display: none; }
    .message.visible { display: block; }
    .message.error { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .message.success { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
    .footer { margin-top: 3rem; font-size: 0.8rem; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <h1>BC3 Reader</h1>
    <p class="subtitle">Sube tu archivo BC3 (FIEBDC) y descarga Excel y PDF</p>
    <form id="uploadForm">
      <div class="upload-zone" id="dropZone">
        <input type="file" id="fileInput" name="file" accept=".bc3" required>
        <div class="upload-icon">📄</div>
        <div class="upload-text">Arrastra tu archivo aquí o haz clic para seleccionar</div>
        <div class="upload-hint">Solo archivos .bc3 (máx. 5 MB)</div>
      </div>
      <div class="file-name" id="fileName"></div>
      <button type="submit" class="btn" id="submitBtn" disabled>Convertir y descargar</button>
    </form>
    <div class="message" id="message"></div>
  </div>
  <p class="footer">Formato FIEBDC • Presupuestos de construcción</p>
  <script>
    const dropZone=document.getElementById('dropZone'), fileInput=document.getElementById('fileInput'), fileName=document.getElementById('fileName'), submitBtn=document.getElementById('submitBtn'), form=document.getElementById('uploadForm'), message=document.getElementById('message');
    function showMessage(text,type){ message.textContent=text; message.className='message visible '+type; }
    function hideMessage(){ message.className='message'; }
    function updateFile(files){ if(files&&files.length){ fileInput.files=files; fileName.textContent='✓ '+files[0].name; fileName.classList.add('visible'); submitBtn.disabled=false; } }
    dropZone.onclick=()=>fileInput.click();
    dropZone.ondragover=e=>{ e.preventDefault(); dropZone.classList.add('dragover'); };
    dropZone.ondragleave=()=>dropZone.classList.remove('dragover');
    dropZone.ondrop=e=>{ e.preventDefault(); dropZone.classList.remove('dragover'); if(e.dataTransfer.files.length&&e.dataTransfer.files[0].name.toLowerCase().endsWith('.bc3')) updateFile(e.dataTransfer.files); else showMessage('Solo se aceptan archivos .bc3','error'); };
    fileInput.onchange=e=>updateFile(e.target.files);
    form.onsubmit=async e=>{ e.preventDefault(); if(!fileInput.files.length) return; submitBtn.disabled=true; submitBtn.textContent='Procesando...'; hideMessage(); try { const res=await fetch('/api/convert',{method:'POST',body:new FormData(form)}); if(!res.ok){ const err=await res.json().catch(()=>({})); throw new Error(err.error||'Error '+res.status); } const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=fileInput.files[0].name.replace(/\\.bc3$/i,'')+'_bc3_export.zip'; a.click(); URL.revokeObjectURL(url); showMessage('¡Descarga completada! El ZIP contiene Excel y PDF.','success'); } catch(err){ showMessage(err.message||'Error al procesar','error'); } finally { submitBtn.disabled=false; submitBtn.textContent='Convertir y descargar'; } };
  </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Sirve la página principal (embebida para Vercel)."""
    return Response(INDEX_HTML, mimetype='text/html; charset=utf-8')


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
