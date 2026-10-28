"""
Generacion del reporte final del caso.

Produce el documento que se pone a disposicion del equipo tratante antes de
la junta multidisciplinaria, en formato PDF y en texto plano.

El reporte incluye de manera obligatoria, y en lugar visible, la aclaracion
de que se trata de un documento de apoyo elaborado por un sistema automatico,
que requiere validacion profesional y que no constituye indicacion
terapeutica. La aclaracion no es configurable: un documento de este tipo
circulando sin esa constancia podria ser interpretado como una conclusion
clinica, que es precisamente lo que el sistema no produce.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.config import DIR_SALIDAS, TEXTO_SIN_DATO


ADVERTENCIA = (
    "Documento de apoyo generado por un sistema automatico de sintesis "
    "documental. Requiere validacion por parte del profesional tratante. "
    "No constituye diagnostico ni indicacion terapeutica. La decision "
    "clinica corresponde exclusivamente al equipo medico."
)

ADVERTENCIA_ENSAYOS = (
    "Los estudios listados se proponen unicamente como referencia a partir de "
    "los marcadores moleculares documentados. La elegibilidad definitiva debe "
    "evaluarse contra el protocolo completo de cada estudio."
)


# ---------------------------------------------------------------------------
# Reporte en texto plano
# ---------------------------------------------------------------------------

def generar_texto(identificador: str, resumen: Dict,
                  ensayos: Optional[List[Dict]] = None,
                  origen_ensayos: str = "",
                  motor_recuperacion: str = "") -> str:
    """Construye el reporte en texto plano."""
    lineas: List[str] = []
    ancho = 78

    lineas.append("=" * ancho)
    lineas.append("RESUMEN DE CASO PARA JUNTA MULTIDISCIPLINARIA DE NEURO-ONCOLOGIA")
    lineas.append("=" * ancho)
    lineas.append("")
    lineas.append(f"Identificador del caso : {identificador}")
    lineas.append(f"Fecha de generacion    : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    modo = resumen.get("modo", "")
    modelo = resumen.get("modelo", "")
    lineas.append(f"Modo de generacion     : {_describir_modo(modo)}")
    lineas.append(f"Modelo utilizado       : {modelo}")
    if motor_recuperacion:
        lineas.append(f"Motor de recuperacion  : {motor_recuperacion}")
    lineas.append("")

    lineas.append("-" * ancho)
    lineas.append("ADVERTENCIA")
    lineas.append("-" * ancho)
    for linea in _envolver(ADVERTENCIA, ancho):
        lineas.append(linea)
    lineas.append("")

    advertencias = resumen.get("advertencias") or []
    if advertencias:
        lineas.append("-" * ancho)
        lineas.append("OBSERVACIONES DEL SISTEMA")
        lineas.append("-" * ancho)
        for a in advertencias:
            for i, linea in enumerate(_envolver(a, ancho - 3)):
                lineas.append((" - " if i == 0 else "   ") + linea)
        lineas.append("")

    lineas.append("-" * ancho)
    lineas.append("RESUMEN ESTRUCTURADO")
    lineas.append("-" * ancho)
    lineas.append("")

    for campo in resumen.get("campos", []):
        lineas.append(campo.get("etiqueta", "").upper())
        contenido = campo.get("contenido", TEXTO_SIN_DATO)
        for linea in _envolver(contenido, ancho - 2):
            lineas.append("  " + linea)

        fuentes = campo.get("fuentes") or []
        if fuentes:
            etiquetas = sorted({f.get("etiqueta", "") for f in fuentes if f.get("etiqueta")})
            if etiquetas:
                for linea in _envolver("Fuente: " + "; ".join(etiquetas), ancho - 2):
                    lineas.append("  " + linea)
        elif contenido != TEXTO_SIN_DATO:
            lineas.append("  Fuente: sin fragmento de respaldo asociado.")

        correcciones = campo.get("correcciones_aplicadas") or []
        if correcciones:
            lineas.append(f"  Correcciones previas aplicadas: {len(correcciones)}")
        lineas.append("")

    if ensayos:
        lineas.append("-" * ancho)
        lineas.append("ESTUDIOS CLINICOS A CONSIDERAR")
        lineas.append("-" * ancho)
        if origen_ensayos:
            lineas.append(f"Origen de los datos: {origen_ensayos}")
        lineas.append("")
        for linea in _envolver(ADVERTENCIA_ENSAYOS, ancho):
            lineas.append(linea)
        lineas.append("")

        for e in ensayos:
            lineas.append(f"{e.get('nct', '')} | {e.get('fase', '')} | {e.get('estado', '')}")
            for linea in _envolver(e.get("titulo", ""), ancho - 2):
                lineas.append("  " + linea)
            coincidencias = e.get("coincidencias") or []
            if coincidencias:
                for linea in _envolver("Coincide por: " + "; ".join(coincidencias), ancho - 2):
                    lineas.append("  " + linea)
            compat = e.get("compatibilidades") or []
            if compat:
                for linea in _envolver("Compatibilidad: " + "; ".join(compat), ancho - 2):
                    lineas.append("  " + linea)
            lineas.append(f"  {e.get('url', '')}")
            lineas.append("")

    lineas.append("=" * ancho)
    lineas.append("Fin del documento")
    lineas.append("=" * ancho)

    return "\n".join(lineas)


def _describir_modo(modo: str) -> str:
    if modo == "conectado":
        return "Generacion asistida por modelo de lenguaje"
    return "Generacion determinista por reglas (sin conexion)"


def _envolver(texto: str, ancho: int) -> List[str]:
    import textwrap
    if not texto:
        return [""]
    return textwrap.wrap(texto, width=ancho) or [""]


# ---------------------------------------------------------------------------
# Reporte en PDF
# ---------------------------------------------------------------------------

def generar_pdf(identificador: str, resumen: Dict,
                ensayos: Optional[List[Dict]] = None,
                origen_ensayos: str = "",
                motor_recuperacion: str = "",
                destino: Optional[Path] = None) -> Path:
    """
    Genera el reporte en PDF.

    Requiere reportlab. Ante su ausencia se informa el error, sin degradar de
    manera silenciosa: la exportacion a PDF es una funcionalidad solicitada
    explicitamente por el usuario y su fallo debe ser visible.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_JUSTIFY
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                        Table, TableStyle)
        from reportlab.lib import colors
    except ImportError as exc:
        raise RuntimeError(
            "La exportacion a PDF requiere la biblioteca reportlab. "
            "Instalela con: pip install reportlab"
        ) from exc

    destino = Path(destino) if destino else (
        DIR_SALIDAS / f"reporte_{identificador}_"
                      f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)

    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("cuerpo", parent=estilos["Normal"],
                            fontName="Helvetica", fontSize=9.5, leading=13,
                            alignment=TA_JUSTIFY)
    titulo = ParagraphStyle("titulo", parent=estilos["Normal"],
                            fontName="Helvetica-Bold", fontSize=14, leading=18,
                            spaceAfter=6)
    seccion = ParagraphStyle("seccion", parent=estilos["Normal"],
                             fontName="Helvetica-Bold", fontSize=11, leading=14,
                             spaceBefore=10, spaceAfter=4)
    campo_titulo = ParagraphStyle("campo", parent=estilos["Normal"],
                                  fontName="Helvetica-Bold", fontSize=9.5,
                                  leading=12, spaceBefore=7, spaceAfter=2)
    fuente = ParagraphStyle("fuente", parent=estilos["Normal"],
                            fontName="Helvetica-Oblique", fontSize=8,
                            leading=10, textColor=colors.HexColor("#555555"))
    aviso = ParagraphStyle("aviso", parent=normal, fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#333333"))

    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Resumen de caso {identificador}",
    )

    elementos = []
    elementos.append(Paragraph(
        "Resumen de caso para junta multidisciplinaria de neuro-oncologia",
        titulo))

    datos_cabecera = [
        ["Identificador del caso", identificador],
        ["Fecha de generacion", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Modo de generacion", _describir_modo(resumen.get("modo", ""))],
        ["Modelo utilizado", resumen.get("modelo", "")],
    ]
    if motor_recuperacion:
        datos_cabecera.append(["Motor de recuperacion", motor_recuperacion])

    tabla = Table(datos_cabecera, colWidths=[45 * mm, 125 * mm])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 8))

    # Advertencia obligatoria, destacada
    caja = Table([[Paragraph(f"<b>ADVERTENCIA.</b> {ADVERTENCIA}", aviso)]],
                 colWidths=[170 * mm])
    caja.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#888888")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F2F2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(caja)

    advertencias = resumen.get("advertencias") or []
    if advertencias:
        elementos.append(Paragraph("Observaciones del sistema", seccion))
        for a in advertencias:
            elementos.append(Paragraph(f"&bull; {_escapar(a)}", normal))

    elementos.append(Paragraph("Resumen estructurado", seccion))

    for campo in resumen.get("campos", []):
        elementos.append(Paragraph(_escapar(campo.get("etiqueta", "")), campo_titulo))
        elementos.append(Paragraph(
            _escapar(campo.get("contenido", TEXTO_SIN_DATO)), normal))

        fuentes = campo.get("fuentes") or []
        etiquetas = sorted({f.get("etiqueta", "") for f in fuentes if f.get("etiqueta")})
        if etiquetas:
            elementos.append(Paragraph(
                "Fuente: " + _escapar("; ".join(etiquetas)), fuente))
        elif campo.get("contenido") != TEXTO_SIN_DATO:
            elementos.append(Paragraph(
                "Fuente: sin fragmento de respaldo asociado.", fuente))

        correcciones = campo.get("correcciones_aplicadas") or []
        if correcciones:
            elementos.append(Paragraph(
                f"Correcciones previas aplicadas: {len(correcciones)}", fuente))

    if ensayos:
        elementos.append(Paragraph("Estudios clinicos a considerar", seccion))
        if origen_ensayos:
            elementos.append(Paragraph(
                f"Origen de los datos: {_escapar(origen_ensayos)}", fuente))
        elementos.append(Paragraph(_escapar(ADVERTENCIA_ENSAYOS), aviso))
        elementos.append(Spacer(1, 4))

        filas = [["Identificador", "Fase", "Estado", "Criterio de correspondencia"]]
        for e in ensayos:
            criterio = "; ".join(e.get("coincidencias") or []) or \
                       "; ".join(e.get("compatibilidades") or []) or \
                       "Sin criterio molecular especifico"
            filas.append([
                e.get("nct", ""),
                e.get("fase", ""),
                e.get("estado", ""),
                Paragraph(_escapar(criterio), fuente),
            ])

        tabla_e = Table(filas, colWidths=[28 * mm, 22 * mm, 30 * mm, 90 * mm])
        tabla_e.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elementos.append(tabla_e)

        elementos.append(Spacer(1, 4))
        for e in ensayos:
            elementos.append(Paragraph(
                f"<b>{_escapar(e.get('nct', ''))}</b>: "
                f"{_escapar(e.get('titulo', ''))} &mdash; "
                f"{_escapar(e.get('url', ''))}", fuente))

    doc.build(elementos)
    return destino


def _escapar(texto: str) -> str:
    """Escapa los caracteres con significado en el marcado de reportlab."""
    return (str(texto or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def guardar_texto(identificador: str, contenido: str,
                  destino: Optional[Path] = None) -> Path:
    destino = Path(destino) if destino else (
        DIR_SALIDAS / f"reporte_{identificador}_"
                      f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")
    return destino
