# -*- coding: utf-8 -*-
"""BC3 Reader - Aplicación web Flask para Vercel."""

import io
import os
import zipfile
from flask import Flask, request, send_file, jsonify, Response

from bc3_reader import BC3Parser, export_to_xlsx_bytes, export_to_pdf_bytes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB límite

# HTML de la página principal - Diseño oficial Plancraft (plancraft.com/de-de)
# Paleta: fondo #000, superficie #111, acento #00D4AA, tipografía Inter
INDEX_HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BC3 Reader | plancraft</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    /* Plancraft design system - plancraft.com/de-de */
    :root {
      --plancraft-bg: #000000;
      --plancraft-surface: #111111;
      --plancraft-border: #262626;
      --plancraft-text: #ffffff;
      --plancraft-muted: #737373;
      --plancraft-accent: #00D4AA;
      --plancraft-accent-hover: #00E5B8;
      --plancraft-success: #00D4AA;
      --plancraft-error: #ef4444;
      --radius: 8px;
      --radius-lg: 12px;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--plancraft-bg);
      color: var(--plancraft-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 24px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 48px;
    }
    .header img {
      height: 36px;
      width: auto;
    }
    .header-brand { font-size: 1.125rem; font-weight: 600; color: var(--plancraft-text); }
    .header-divider { color: var(--plancraft-border); font-weight: 300; }
    .header-product { color: var(--plancraft-accent); font-weight: 600; }
    .container {
      max-width: 440px;
      width: 100%;
    }
    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      margin-bottom: 8px;
      color: var(--plancraft-text);
      letter-spacing: -0.02em;
    }
    h1 .accent { color: var(--plancraft-accent); }
    .subtitle {
      color: var(--plancraft-muted);
      font-size: 0.9375rem;
      margin-bottom: 32px;
      font-weight: 400;
    }
    .upload-zone {
      background: var(--plancraft-surface);
      border: 2px dashed var(--plancraft-border);
      border-radius: var(--radius-lg);
      padding: 40px 32px;
      text-align: center;
      transition: all 0.2s ease;
      cursor: pointer;
      position: relative;
      margin-bottom: 24px;
    }
    .upload-zone:hover, .upload-zone.dragover {
      border-color: var(--plancraft-accent);
      background: rgba(0, 212, 170, 0.06);
    }
    .upload-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .upload-icon { font-size: 2.5rem; margin-bottom: 16px; opacity: 0.7; }
    .upload-text { font-size: 1rem; font-weight: 500; margin-bottom: 4px; }
    .upload-hint { font-size: 0.8125rem; color: var(--plancraft-muted); }
    .file-name { margin-bottom: 20px; font-size: 0.875rem; color: var(--plancraft-success); display: none; }
    .file-name.visible { display: block; }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 14px 24px;
      font-size: 1rem;
      font-weight: 600;
      font-family: inherit;
      border: none;
      border-radius: var(--radius);
      cursor: pointer;
      width: 100%;
      background: var(--plancraft-accent);
      color: #000000;
      transition: all 0.2s ease;
    }
    .btn:hover:not(:disabled) {
      background: var(--plancraft-accent-hover);
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn.loading { pointer-events: none; }
    .btn .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid rgba(0,0,0,0.2);
      border-top-color: #000;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .message {
      margin-top: 24px;
      padding: 16px;
      border-radius: var(--radius);
      font-size: 0.875rem;
      display: none;
    }
    .message.visible { display: block; }
    .message.error { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .message.success { background: rgba(0, 212, 170, 0.12); color: var(--plancraft-accent-hover); }
    .footer {
      margin-top: 48px;
      font-size: 0.75rem;
      color: var(--plancraft-muted);
      text-align: center;
    }
    .footer a { color: var(--plancraft-accent); text-decoration: none; }
    .footer a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="header">
    <img src="https://cdn.prod.website-files.com/6721edec2a463887e742a101/6721edec2a463887e742a172_plancraft%20logo.svg" alt="plancraft" onerror="this.src='/plancraft-logo.png'">
    <span class="header-brand">plancraft</span>
    <span class="header-divider">|</span>
    <span class="header-product">BC3 Reader</span>
  </div>
  <div class="container">
    <h1>Convertidor <span class="accent">BC3</span></h1>
    <p class="subtitle">Sube tu archivo BC3 (FIEBDC) y descarga Excel y PDF</p>
    <form id="uploadForm">
      <div class="upload-zone" id="dropZone">
        <input type="file" id="fileInput" name="file" accept=".bc3" required>
        <div class="upload-icon">📄</div>
        <div class="upload-text">Arrastra tu archivo aquí o haz clic para seleccionar</div>
        <div class="upload-hint">Solo archivos .bc3 (máx. 5 MB)</div>
      </div>
      <div class="file-name" id="fileName"></div>
      <button type="submit" class="btn" id="submitBtn" disabled>
        <span class="btn-text">Convertir y descargar</span>
      </button>
    </form>
    <div class="message" id="message"></div>
  </div>
  <p class="footer">Formato FIEBDC • <a href="https://plancraft.com" target="_blank" rel="noopener">plancraft.com</a></p>
  <script>
    const dropZone=document.getElementById('dropZone'), fileInput=document.getElementById('fileInput'),
      fileName=document.getElementById('fileName'), submitBtn=document.getElementById('submitBtn'),
      btnText=submitBtn.querySelector('.btn-text'), form=document.getElementById('uploadForm'),
      message=document.getElementById('message');
    function showMessage(text,type){ message.textContent=text; message.className='message visible '+type; }
    function hideMessage(){ message.className='message'; }
    function setLoading(loading){
      submitBtn.disabled=loading;
      submitBtn.classList.toggle('loading',loading);
      if(loading){
        btnText.innerHTML='<span class="spinner"></span> Procesando...';
      }else{
        btnText.textContent='Convertir y descargar';
      }
    }
    function updateFile(files){
      if(files&&files.length){
        fileInput.files=files;
        fileName.textContent='✓ '+files[0].name;
        fileName.classList.add('visible');
        submitBtn.disabled=false;
      }
    }
    dropZone.onclick=()=>fileInput.click();
    dropZone.ondragover=e=>{ e.preventDefault(); dropZone.classList.add('dragover'); };
    dropZone.ondragleave=()=>dropZone.classList.remove('dragover');
    dropZone.ondrop=e=>{
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if(e.dataTransfer.files.length&&e.dataTransfer.files[0].name.toLowerCase().endsWith('.bc3')){
        updateFile(e.dataTransfer.files);
      }else{
        showMessage('Solo se aceptan archivos .bc3','error');
      }
    };
    fileInput.onchange=e=>updateFile(e.target.files);
    form.onsubmit=async e=>{
      e.preventDefault();
      if(!fileInput.files.length) return;
      setLoading(true);
      hideMessage();
      try{
        const res=await fetch('/api/convert',{method:'POST',body:new FormData(form)});
        if(!res.ok){
          const err=await res.json().catch(()=>({}));
          throw new Error(err.error||'Error '+res.status);
        }
        const blob=await res.blob();
        const url=URL.createObjectURL(blob);
        const a=document.createElement('a');
        a.href=url;
        a.download=fileInput.files[0].name.replace(/\\.bc3$/i,'')+'_bc3_export.zip';
        a.click();
        URL.revokeObjectURL(url);
        showMessage('¡Listo! El ZIP con Excel y PDF se ha descargado.','success');
      }catch(err){
        showMessage(err.message||'Error al procesar el archivo','error');
      }finally{
        setLoading(false);
      }
    };
  </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Sirve la página principal (embebida para Vercel)."""
    return Response(INDEX_HTML, mimetype='text/html; charset=utf-8')


@app.route('/plancraft-logo.png')
def logo():
    """Sirve el logo de Plancraft."""
    logo_path = os.path.join(BASE_DIR, 'assets', 'plancraft-logo.png')
    return send_file(logo_path, mimetype='image/png')


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
