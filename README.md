# BC3 Reader

Software para leer archivos BC3 (formato FIEBDC - Formato de Intercambio de Bases de Datos de Construcción) y exportarlos a **PDF** o **Excel (XLSX)**.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Desde línea de comandos

```bash
# Exportar a Excel (por defecto genera .xlsx y .pdf)
python main.py tu_archivo.bc3

# Especificar archivo de salida
python main.py presupuesto.bc3 -o resultado.xlsx
python main.py presupuesto.bc3 -o resultado.pdf

# Exportar a ambos formatos
python main.py presupuesto.bc3 -x salida.xlsx -p salida.pdf

# Con título personalizado
python main.py presupuesto.bc3 -o salida.xlsx -t "Presupuesto Obra 2024"
```

### Desde Python

```python
from bc3_reader import BC3Parser, export_to_xlsx, export_to_pdf

# Parsear archivo BC3
parser = BC3Parser()
presupuesto = parser.parse("mi_presupuesto.bc3")
partidas = parser.get_partidas_con_detalles(presupuesto)

# Exportar a Excel
export_to_xlsx(partidas, "salida.xlsx", titulo="Mi Presupuesto")

# Exportar a PDF
export_to_pdf(partidas, "salida.pdf", titulo="Mi Presupuesto")
```

## Formato BC3 (FIEBDC)

Los archivos BC3 son archivos de texto con estructura específica:
- **Registros** separados por `~` (tilde)
- **Campos** separados por `|` (pipe)
- **Subcampos** separados por `\` (backslash)

Tipos de registro principales:
- **V**: Versión y metadatos
- **C**: Conceptos (código, unidad, descripción, precio...)
- **D**: Descomposiciones
- **M**: Mediciones (cantidades)
- **T**: Textos descriptivos largos

## Versión web (Vercel)

Puedes desplegar la app en la nube en Vercel para usarla desde el navegador:

1. **Conectar el repositorio** a [Vercel](https://vercel.com)
2. **Desplegar** (Vercel detecta Flask automáticamente)
3. **Usar** la web: sube un .bc3 y descarga un ZIP con Excel y PDF

### Despliegue local con Vercel CLI

```bash
npm i -g vercel
vercel
```

La interfaz web está en `public/index.html`. La API recibe POST en `/api/convert` con el archivo y retorna un ZIP.

## Requisitos

- Python 3.8+
- flask, openpyxl, reportlab
