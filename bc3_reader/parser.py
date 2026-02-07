# -*- coding: utf-8 -*-
"""
Parser para archivos BC3 (FIEBDC - Formato de Intercambio de Bases de Datos de Construcción).
Estructura: registros separados por ~, campos por |, subcampos por \\
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Concepto:
    """Representa un concepto/capítulo del presupuesto."""
    codigo: str
    unidad: str
    resumen: str
    precio: str
    fecha: str
    tipo: str
    raw_fields: List[str] = field(default_factory=list)


@dataclass 
class PresupuestoBC3:
    """Objeto que contiene todo el presupuesto parseado."""
    version: Dict[str, str] = field(default_factory=dict)
    conceptos: Dict[str, List[str]] = field(default_factory=dict)
    descomposiciones: Dict[str, List[str]] = field(default_factory=dict)
    mediciones: Dict[str, List[str]] = field(default_factory=dict)
    textos: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BC3Parser:
    """Parser para archivos BC3."""
    
    def __init__(self, encoding: str = 'latin-1'):
        """
        Args:
            encoding: Codificación del archivo (latin-1 para BC3 antiguos, utf-8 para UTF-8)
        """
        self.encoding = encoding
    
    def _detect_encoding(self, raw_bytes: bytes) -> str:
        """Detecta la codificación del archivo."""
        try:
            raw_bytes.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            return 'latin-1'
    
    def parse_from_bytes(self, raw: bytes, filename: str = '') -> PresupuestoBC3:
        """
        Parsea contenido BC3 desde bytes (útil para uploads web).
        
        Args:
            raw: Contenido binario del archivo BC3
            filename: Nombre del archivo (opcional, para metadata)
            
        Returns:
            PresupuestoBC3 con todos los datos parseados
        """
        encoding = self._detect_encoding(raw)
        contenido = raw.decode(encoding, errors='replace')
        
        presupuesto = PresupuestoBC3()
        presupuesto.metadata['encoding'] = encoding
        presupuesto.metadata['filepath'] = filename or 'upload.bc3'
        
        return self._parse_content(contenido, presupuesto)
    
    def parse(self, filepath: str) -> PresupuestoBC3:
        """
        Parsea un archivo BC3 y retorna un objeto PresupuestoBC3.
        
        Args:
            filepath: Ruta al archivo .bc3
            
        Returns:
            PresupuestoBC3 con todos los datos parseados
        """
        with open(filepath, 'rb') as f:
            raw = f.read()
        
        encoding = self._detect_encoding(raw)
        contenido = raw.decode(encoding, errors='replace')
        
        presupuesto = PresupuestoBC3()
        presupuesto.metadata['encoding'] = encoding
        presupuesto.metadata['filepath'] = filepath
        
        return self._parse_content(contenido, presupuesto)
    
    def _parse_content(self, contenido: str, presupuesto: PresupuestoBC3) -> PresupuestoBC3:
        """Parse interno del contenido de texto."""
        contenido = contenido.replace('\r\n', '\n').replace('\r', '\n')
        
        # Dividir por registros (~)
        registros_raw = contenido.split('~')
        
        for reg_raw in registros_raw:
            reg_raw = reg_raw.strip()
            if not reg_raw:
                continue
            
            # Dividir campos por |
            campos = self._split_campos(reg_raw)
            if not campos:
                continue
            
            tipo = campos[0].strip()
            
            if tipo == 'V':
                # Registro de versión: ~V|EMPRESA|FIEBDC-3/2002|APLICACION|...
                presupuesto.version = dict(zip(
                    ['empresa', 'estandar', 'aplicacion', 'version_app', 'charset'],
                    campos[1:6] if len(campos) > 5 else campos[1:] + [''] * (5 - len(campos))
                ))
            elif tipo == 'C':
                # Concepto: ~C|codigo|unidad|resumen|precio|fecha|tipo|...
                if len(campos) >= 4:
                    codigo = self._limpiar_codigo(campos[1])
                    presupuesto.conceptos[codigo] = campos[2:]
            elif tipo == 'D':
                # Descomposición
                if len(campos) >= 3:
                    codigo = self._limpiar_codigo(campos[1])
                    presupuesto.descomposiciones[codigo] = campos[2:]
            elif tipo == 'M':
                # Mediciones
                if len(campos) >= 3:
                    codigo = self._limpiar_codigo(campos[1])
                    presupuesto.mediciones[codigo] = campos[2:]
            elif tipo == 'T':
                # Textos (descripción larga)
                if len(campos) >= 3:
                    codigo = self._limpiar_codigo(campos[1])
                    presupuesto.textos[codigo] = campos[2] if campos[2] else ''
            # K y otros se ignoran
        
        return presupuesto
    
    def _split_campos(self, registro: str) -> List[str]:
        """Divide un registro en campos. En BC3 los campos se separan por |."""
        campos = re.split(r'\|', registro)
        return [c.strip() for c in campos]
    
    def _limpiar_codigo(self, codigo: str) -> str:
        """Limpia el código (# = capítulo, ## = raíz en FIEBDC)."""
        return codigo.strip() if codigo else ''
    
    def get_partidas_con_detalles(self, presupuesto: PresupuestoBC3) -> List[Dict]:
        """
        Genera lista de partidas con todos los detalles para exportar.
        Combina conceptos, mediciones, textos y descomposiciones.
        """
        partidas = []
        codigos_procesados = set()
        
        # Ordenar códigos para mantener estructura jerárquica
        def orden_codigo(c):
            partes = re.split(r'[.#]', str(c).replace('##', '').replace('#', ''))
            return tuple(int(p) if p.isdigit() else 0 for p in partes[:5])
        
        todos_codigos = set(presupuesto.conceptos.keys()) | set(presupuesto.mediciones.keys())
        codigos_ordenados = sorted(todos_codigos, key=orden_codigo)
        
        for codigo in codigos_ordenados:
            if codigo in codigos_procesados:
                continue
            
            partida = {
                'codigo': codigo,
                'descripcion': '',
                'unidad': '',
                'cantidad': '',
                'precio_unitario': '',
                'importe': '',
                'texto_largo': '',
                'descomposicion': ''
            }
            
            # Datos del concepto: [unidad, resumen, precio, fecha, tipo, ...]
            if codigo in presupuesto.conceptos:
                campos = presupuesto.conceptos[codigo]
                partida['unidad'] = campos[0] if len(campos) > 0 else ''
                partida['descripcion'] = campos[1] if len(campos) > 1 else ''
                partida['precio_unitario'] = campos[2] if len(campos) > 2 else ''
            
            # Texto largo
            if codigo in presupuesto.textos:
                partida['texto_largo'] = presupuesto.textos[codigo]
            
            # Mediciones (cantidad)
            if codigo in presupuesto.mediciones:
                med = presupuesto.mediciones[codigo]
                if med:
                    # Formato medición: puede ser cantidad directa o fórmula
                    partida['cantidad'] = med[0] if isinstance(med[0], str) else str(med[0])
            
            # Descomposición
            if codigo in presupuesto.descomposiciones:
                partida['descomposicion'] = ' | '.join(str(x) for x in presupuesto.descomposiciones[codigo])
            
            # Calcular importe si hay cantidad y precio
            try:
                cant = self._parse_numero(partida['cantidad'])
                precio = self._parse_numero(partida['precio_unitario'])
                if cant is not None and precio is not None:
                    partida['importe'] = f"{cant * precio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except (ValueError, TypeError):
                pass
            
            partidas.append(partida)
            codigos_procesados.add(codigo)
        
        return partidas
    
    def _parse_numero(self, s: str) -> Optional[float]:
        """Parsea número español (coma decimal) o inglés."""
        if not s or not str(s).strip():
            return None
        s = str(s).strip().replace(' ', '')
        s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return None
