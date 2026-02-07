# -*- coding: utf-8 -*-
"""Exportador de presupuestos BC3 a PDF."""

import io
from pathlib import Path
from typing import List, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


def export_to_pdf(partidas: List[Dict], output_path: str, titulo: str = "Presupuesto BC3") -> str:
    """
    Exporta las partidas del presupuesto a un archivo PDF.
    
    Args:
        partidas: Lista de diccionarios con los datos de cada partida
        output_path: Ruta del archivo de salida .pdf
        titulo: Título del documento
        
    Returns:
        Ruta del archivo generado
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != '.pdf':
        output_path = output_path.with_suffix('.pdf')
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = []
    
    # Título
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # Center
    )
    elements.append(Paragraph(titulo, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Tabla principal (sin descripción larga para evitar páginas gigantes)
    # Usamos columnas: Código, Descripción, Ud, Cantidad, Precio, Importe
    data = [['Código', 'Descripción', 'Ud', 'Cantidad', 'Precio Unit.', 'Importe']]
    
    for partida in partidas:
        row = [
            str(partida.get('codigo', ''))[:20],
            str(partida.get('descripcion', ''))[:60],
            str(partida.get('unidad', '')),
            str(partida.get('cantidad', '')),
            str(partida.get('precio_unitario', '')),
            str(partida.get('importe', ''))
        ]
        data.append(row)
    
    # Crear tabla con ancho fijo para caber en A4
    col_widths = [3*cm, 8*cm, 1.5*cm, 2*cm, 2.5*cm, 2.5*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (5, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return str(output_path)


def export_to_pdf_bytes(partidas: List[Dict], titulo: str = "Presupuesto BC3") -> bytes:
    """Exporta a PDF y retorna los bytes (para respuestas HTTP)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=20, alignment=1)
    elements.append(Paragraph(titulo, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    data = [['Código', 'Descripción', 'Ud', 'Cantidad', 'Precio Unit.', 'Importe']]
    for partida in partidas:
        data.append([
            str(partida.get('codigo', ''))[:20],
            str(partida.get('descripcion', ''))[:60],
            str(partida.get('unidad', '')),
            str(partida.get('cantidad', '')),
            str(partida.get('precio_unitario', '')),
            str(partida.get('importe', ''))
        ])
    
    col_widths = [3*cm, 8*cm, 1.5*cm, 2*cm, 2.5*cm, 2.5*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (5, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
