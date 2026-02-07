#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BC3 Reader - Convierte archivos BC3 (FIEBDC) a PDF o XLSX.

Uso:
    python main.py archivo.bc3 -o salida.xlsx
    python main.py archivo.bc3 -o presupuesto.pdf
    python main.py archivo.bc3 -o salida.xlsx -o salida.pdf  # Exporta a ambos
"""

import argparse
import sys
from pathlib import Path

from bc3_reader import BC3Parser, export_to_xlsx, export_to_pdf


def main():
    parser = argparse.ArgumentParser(
        description='Convierte archivos BC3 (FIEBDC) a PDF o XLSX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py presupuesto.bc3 -o resultado.xlsx
  python main.py presupuesto.bc3 -o resultado.pdf
  python main.py presupuesto.bc3 -x resultado.xlsx -p resultado.pdf
  python main.py presupuesto.bc3 -x salida.xlsx -p salida.pdf -t "Mi Presupuesto"
        """
    )
    
    parser.add_argument(
        'archivo_bc3',
        help='Ruta al archivo .bc3 a convertir'
    )
    parser.add_argument(
        '-o', '--output',
        help='Archivo de salida (detecta formato por extensión .xlsx o .pdf)'
    )
    parser.add_argument(
        '-x', '--xlsx',
        help='Exportar a archivo Excel (.xlsx)'
    )
    parser.add_argument(
        '-p', '--pdf',
        help='Exportar a archivo PDF'
    )
    parser.add_argument(
        '-t', '--titulo',
        default='Presupuesto BC3',
        help='Título del documento (default: Presupuesto BC3)'
    )
    
    args = parser.parse_args()
    
    # Validar archivo de entrada
    archivo = Path(args.archivo_bc3)
    if not archivo.exists():
        print(f"Error: El archivo '{archivo}' no existe.", file=sys.stderr)
        sys.exit(1)
    
    if archivo.suffix.lower() != '.bc3':
        print("Advertencia: El archivo no tiene extensión .bc3", file=sys.stderr)
    
    # Determinar salidas
    salidas_xlsx = []
    salidas_pdf = []
    
    if args.output:
        ext = Path(args.output).suffix.lower()
        if ext == '.xlsx':
            salidas_xlsx.append(args.output)
        elif ext == '.pdf':
            salidas_pdf.append(args.output)
        else:
            # Por defecto exportar a ambos si extensión no reconocida
            salidas_xlsx.append(str(Path(args.output).with_suffix('.xlsx')))
            salidas_pdf.append(str(Path(args.output).with_suffix('.pdf')))
    
    if args.xlsx:
        salidas_xlsx.append(args.xlsx)
    if args.pdf:
        salidas_pdf.append(args.pdf)
    
    if not salidas_xlsx and not salidas_pdf:
        # Si no se especificó nada, exportar a ambos con nombre base
        base = archivo.stem
        salidas_xlsx.append(str(archivo.parent / f"{base}.xlsx"))
        salidas_pdf.append(str(archivo.parent / f"{base}.pdf"))
    
    try:
        # Parsear BC3
        bc3_parser = BC3Parser()
        presupuesto = bc3_parser.parse(str(archivo))
        partidas = bc3_parser.get_partidas_con_detalles(presupuesto)
        
        titulo = args.titulo
        if presupuesto.version.get('empresa'):
            titulo = f"{titulo} - {presupuesto.version['empresa']}"
        
        # Exportar
        for path in salidas_xlsx:
            result = export_to_xlsx(partidas, path, titulo)
            print(f"✓ Exportado a Excel: {result}")
        
        for path in salidas_pdf:
            result = export_to_pdf(partidas, path, titulo)
            print(f"✓ Exportado a PDF: {result}")
        
    except Exception as e:
        print(f"Error al procesar el archivo: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
