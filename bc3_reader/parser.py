# -*- coding: utf-8 -*-
"""
Parser para archivos BC3 (FIEBDC-3 - Formato de Intercambio Estándar de Bases de Datos
de la Construcción). Implementación conforme a la especificación oficial:
https://www.fiebdc.es/formato-fiebdc/
https://fiebdc.es/web2/datos/uploads/Formato-FIEBDC-3-2020.pdf

Estructura según especificación FIEBDC-3:
- Registros separados por ~ (ASCII-126)
- Campos separados por | (ASCII-124)
- Subcampos separados por \ (ASCII-92)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


def _primer_subcampo(valor: str) -> str:
    """Extrae el primer subcampo de un campo (separador \). FIEBDC-3."""
    if not valor or not str(valor).strip():
        return ''
    partes = str(valor).strip().split('\\')
    return partes[0].strip() if partes else ''


def _todos_subcampos(valor: str) -> List[str]:
    """Extrae todos los subcampos de un campo (separador \)."""
    if not valor or not str(valor).strip():
        return []
    return [p.strip() for p in str(valor).strip().split('\\') if p.strip()]


@dataclass
class Concepto:
    """Representa un concepto según registro ~C FIEBDC-3."""

    codigo: str
    unidad: str
    resumen: str
    precio: str
    fecha: str
    tipo: str
    raw_fields: List[str] = field(default_factory=list)


@dataclass
class PresupuestoBC3:
    """Objeto que contiene todo el presupuesto parseado según FIEBDC-3."""

    version: Dict[str, str] = field(default_factory=dict)
    coeficientes: Dict[str, Any] = field(default_factory=dict)  # Registro ~K
    conceptos: Dict[str, List[str]] = field(default_factory=dict)
    descomposiciones: Dict[str, List[str]] = field(default_factory=dict)
    mediciones: Dict[str, List[str]] = field(default_factory=dict)
    textos: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Registros adicionales para compatibilidad
    otros_registros: Dict[str, List[List[str]]] = field(default_factory=dict)


class BC3Parser:
    """Parser para archivos BC3 conforme a especificación FIEBDC-3/2020."""

    def __init__(self, encoding: str = "latin-1"):
        """
        Args:
            encoding: Codificación por defecto (latin-1 para BC3 clásicos, utf-8 para UTF-8).
        """
        self.encoding = encoding

    def _detect_encoding(self, raw_bytes: bytes) -> str:
        """Detecta codificación según especificación (850, 437, ANSI)."""
        try:
            raw_bytes.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "latin-1"

    def parse_from_bytes(
        self, raw: bytes, filename: str = ""
    ) -> PresupuestoBC3:
        """
        Parsea contenido BC3 desde bytes (uploads web).

        Args:
            raw: Contenido binario del archivo BC3
            filename: Nombre del archivo (opcional)

        Returns:
            PresupuestoBC3 con todos los datos parseados
        """
        encoding = self._detect_encoding(raw)
        contenido = raw.decode(encoding, errors="replace")

        presupuesto = PresupuestoBC3()
        presupuesto.metadata["encoding"] = encoding
        presupuesto.metadata["filepath"] = filename or "upload.bc3"

        return self._parse_content(contenido, presupuesto)

    def parse(self, filepath: str) -> PresupuestoBC3:
        """
        Parsea un archivo BC3.

        Args:
            filepath: Ruta al archivo .bc3

        Returns:
            PresupuestoBC3 con todos los datos parseados
        """
        with open(filepath, "rb") as f:
            raw = f.read()

        encoding = self._detect_encoding(raw)
        contenido = raw.decode(encoding, errors="replace")

        presupuesto = PresupuestoBC3()
        presupuesto.metadata["encoding"] = encoding
        presupuesto.metadata["filepath"] = filepath

        return self._parse_content(contenido, presupuesto)

    def _parse_content(
        self, contenido: str, presupuesto: PresupuestoBC3
    ) -> PresupuestoBC3:
        """Parse interno según especificación FIEBDC-3."""
        contenido = contenido.replace("\r\n", "\n").replace("\r", "\n")

        # Eliminar carácter EOF (ASCII-26) si existe
        if "\x1a" in contenido:
            contenido = contenido.split("\x1a")[0]

        # Registros entre ~
        registros_raw = contenido.split("~")

        for reg_raw in registros_raw:
            reg_raw = reg_raw.strip()
            if not reg_raw:
                continue

            campos = self._split_campos(reg_raw)
            if not campos:
                continue

            tipo = campos[0].strip().upper()

            if tipo == "V":
                self._parse_registro_v(campos, presupuesto)
            elif tipo == "K":
                self._parse_registro_k(campos, presupuesto)
            elif tipo == "C":
                self._parse_registro_c(campos, presupuesto)
            elif tipo == "D":
                self._parse_registro_d(campos, presupuesto)
            elif tipo == "Y":
                self._parse_registro_y(campos, presupuesto)
            elif tipo == "M":
                self._parse_registro_m(campos, presupuesto)
            elif tipo == "T":
                self._parse_registro_t(campos, presupuesto)
            elif tipo == "R":
                self._guardar_otro(tipo, campos, presupuesto)
            elif tipo in ("F", "G", "L", "O", "X", "Z"):
                self._guardar_otro(tipo, campos, presupuesto)

        return presupuesto

    def _parse_registro_v(self, campos: List[str], presupuesto: PresupuestoBC3):
        """
        ~V | PROPIEDAD_ARCHIVO | VERSION_FORMATO \ DDMMAAAA | PROGRAMA_EMISION |
        CABECERA \ { ROTULO_IDENTIFICACION \ } | JUEGO_CARACTERES | COMENTARIO |
        TIPO INFORMACIÓN | NÚMERO CERTIFICACIÓN | FECHA CERTIFICACIÓN | URL_BASE |
        """
        presupuesto.version = dict(
            zip(
                [
                    "propiedad",
                    "version_formato",
                    "programa_emision",
                    "cabecera",
                    "charset",
                    "comentario",
                    "tipo_info",
                    "num_certificacion",
                    "fecha_certificacion",
                    "url_base",
                ],
                (campos[1:11] if len(campos) > 11 else campos[1:] + [""] * 10),
            )
        )

    def _parse_registro_k(self, campos: List[str], presupuesto: PresupuestoBC3):
        """~K | Decimales y coeficientes. Almacenamos raw para futuras mejoras."""
        if len(campos) > 1:
            presupuesto.coeficientes["raw"] = campos[1:]

    def _parse_registro_c(self, campos: List[str], presupuesto: PresupuestoBC3):
        """
        ~C | CODIGO { \ CODIGO } | [ UNIDAD ] | [ RESUMEN ] | { PRECIO \ } | { FECHA \ } | [ TIPO ] |
        Subcampos con \\: primer valor es el principal.
        """
        if len(campos) < 4:
            return
        codigo_raw = campos[1]
        codigo = _primer_subcampo(codigo_raw) or codigo_raw.strip()
        codigo = self._limpiar_codigo(codigo)
        if not codigo:
            return

        # Campos según especificación: UNIDAD, RESUMEN, PRECIO, FECHA, TIPO
        unidad = _primer_subcampo(campos[2]) if len(campos) > 2 else ""
        resumen = _primer_subcampo(campos[3]) if len(campos) > 3 else ""
        precio_raw = campos[4] if len(campos) > 4 else ""
        precio = _primer_subcampo(precio_raw) or precio_raw.strip()
        fecha_raw = campos[5] if len(campos) > 5 else ""
        fecha = _primer_subcampo(fecha_raw) or fecha_raw.strip()
        tipo = _primer_subcampo(campos[6]) if len(campos) > 6 else ""

        # Guardamos [unidad, resumen, precio, fecha, tipo, ...] para compatibilidad
        presupuesto.conceptos[codigo] = [unidad, resumen, precio, fecha, tipo]

    def _parse_registro_d(self, campos: List[str], presupuesto: PresupuestoBC3):
        """
        ~D | CODIGO_PADRE | < CODIGO_HIJO \ FACTOR \ RENDIMIENTO \ > | ...
        Cada línea: CODIGO_HIJO\\FACTOR\\RENDIMIENTO
        """
        if len(campos) < 3:
            return
        codigo_padre = self._limpiar_codigo(campos[1])
        if not codigo_padre:
            return
        lineas = []
        for campo in campos[2:]:
            sub = _todos_subcampos(campo)
            if not sub:
                continue
            codigo_hijo = sub[0]
            factor = sub[1] if len(sub) > 1 else "1"
            rendimiento = sub[2] if len(sub) > 2 else "1"
            f_ok = factor and self._parse_numero(factor) != 1.0
            r_ok = rendimiento and self._parse_numero(rendimiento) != 1.0
            if r_ok:
                lineas.append(f"{codigo_hijo} x {factor} (r: {rendimiento})")
            elif f_ok:
                lineas.append(f"{codigo_hijo} x {factor}")
            else:
                lineas.append(codigo_hijo)
        presupuesto.descomposiciones[codigo_padre] = lineas

    def _parse_registro_y(self, campos: List[str], presupuesto: PresupuestoBC3):
        """~Y | Añadir descomposición. Igual que ~D pero se añade en lugar de reemplazar."""
        if len(campos) < 3:
            return
        codigo_padre = self._limpiar_codigo(campos[1])
        if not codigo_padre:
            return
        lineas = presupuesto.descomposiciones.get(codigo_padre, [])
        for campo in campos[2:]:
            sub = _todos_subcampos(campo)
            if not sub:
                continue
            codigo_hijo = sub[0]
            factor = sub[1] if len(sub) > 1 else "1"
            rendimiento = sub[2] if len(sub) > 2 else "1"
            f_ok = factor and self._parse_numero(factor) != 1.0
            r_ok = rendimiento and self._parse_numero(rendimiento) != 1.0
            if r_ok:
                lineas.append(f"{codigo_hijo} x {factor} (r: {rendimiento})")
            elif f_ok:
                lineas.append(f"{codigo_hijo} x {factor}")
            else:
                lineas.append(codigo_hijo)
        presupuesto.descomposiciones[codigo_padre] = lineas

    def _parse_registro_m(self, campos: List[str], presupuesto: PresupuestoBC3):
        """
        ~M | CODIGO | Mediciones (cantidad directa o fórmula con subcampos).
        Ejemplo simple: ~M|01.1.001|150|
        Con dimensiones: valor puede ser \dim1\dim2\dim3\ o cantidad directa.
        """
        if len(campos) < 3:
            return
        codigo = self._limpiar_codigo(campos[1])
        if not codigo:
            return
        valor_raw = campos[2]
        sub = _todos_subcampos(valor_raw)
        if sub:
            presupuesto.mediciones[codigo] = sub
        else:
            presupuesto.mediciones[codigo] = [valor_raw.strip()] if valor_raw.strip() else []

    def _parse_registro_t(self, campos: List[str], presupuesto: PresupuestoBC3):
        """~T | CODIGO | TEXTO |"""
        if len(campos) >= 3:
            codigo = self._limpiar_codigo(campos[1])
            if codigo:
                presupuesto.textos[codigo] = campos[2].strip() if campos[2] else ""

    def _guardar_otro(
        self, tipo: str, campos: List[str], presupuesto: PresupuestoBC3
    ):
        """Guarda registros adicionales (R, F, G, L, O, X, Z) para integridad."""
        if tipo not in presupuesto.otros_registros:
            presupuesto.otros_registros[tipo] = []
        presupuesto.otros_registros[tipo].append(campos[1:])

    def _split_campos(self, registro: str) -> List[str]:
        """Divide por | según especificación FIEBDC-3."""
        campos = re.split(r"\|", registro)
        return [c.strip() for c in campos]

    def _limpiar_codigo(self, codigo: str) -> str:
        """Limpia código. ## = raíz, # = capítulo (FIEBDC-3)."""
        return codigo.strip() if codigo else ""

    def _extraer_cantidad_medicion(self, med: List[str]) -> str:
        """
        Extrae cantidad de medición.
        - Si es número directo: ese valor.
        - Si tiene subcampos (fórmula LxAx): primer valor numérico o "dim1 x dim2 x dim3".
        """
        if not med:
            return ""
        if len(med) == 1:
            return med[0]
        # Fórmula tipo dimensiones: \10\5\3\ -> "10 x 5 x 3" o calcular
        numeros = []
        for m in med:
            n = self._parse_numero(m)
            if n is not None:
                numeros.append(str(n))
            else:
                numeros.append(m)
        return " x ".join(numeros) if numeros else med[0]

    def _parse_numero(self, s: str) -> Optional[float]:
        """Parsea número español (coma decimal) o inglés según FIEBDC-3."""
        if not s or not str(s).strip():
            return None
        s = str(s).strip().replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def get_partidas_con_detalles(self, presupuesto: PresupuestoBC3) -> List[Dict]:
        """
        Genera lista de partidas con todos los detalles para exportar.
        Conforme a estructura FIEBDC-3: conceptos (~C), mediciones (~M), textos (~T), descomposiciones (~D).
        """
        partidas = []
        codigos_procesados = set()

        def orden_codigo(c: str) -> tuple:
            """Ordenación jerárquica de códigos (##, #, 01.1.001)."""
            base = str(c).replace("##", "").replace("#", "")
            partes = re.split(r"[.#]", base)
            result = []
            for p in partes[:8]:
                if p.isdigit():
                    result.append(int(p))
                else:
                    result.append(p or "0")
            return tuple(result)

        todos_codigos = set(presupuesto.conceptos.keys()) | set(
            presupuesto.mediciones.keys()
        )
        codigos_ordenados = sorted(todos_codigos, key=orden_codigo)

        for codigo in codigos_ordenados:
            if codigo in codigos_procesados:
                continue

            partida = {
                "codigo": codigo,
                "descripcion": "",
                "unidad": "",
                "cantidad": "",
                "precio_unitario": "",
                "importe": "",
                "texto_largo": "",
                "descomposicion": "",
            }

            if codigo in presupuesto.conceptos:
                campos = presupuesto.conceptos[codigo]
                partida["unidad"] = campos[0] if len(campos) > 0 else ""
                partida["descripcion"] = campos[1] if len(campos) > 1 else ""
                partida["precio_unitario"] = campos[2] if len(campos) > 2 else ""

            if codigo in presupuesto.textos:
                partida["texto_largo"] = presupuesto.textos[codigo]

            if codigo in presupuesto.mediciones:
                med = presupuesto.mediciones[codigo]
                partida["cantidad"] = self._extraer_cantidad_medicion(med)

            if codigo in presupuesto.descomposiciones:
                partida["descomposicion"] = " | ".join(
                    presupuesto.descomposiciones[codigo]
                )

            try:
                cant = self._parse_numero(partida["cantidad"])
                precio = self._parse_numero(partida["precio_unitario"])
                if cant is not None and precio is not None:
                    partida["importe"] = (
                        f"{cant * precio:,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
            except (ValueError, TypeError):
                pass

            partidas.append(partida)
            codigos_procesados.add(codigo)

        return partidas
