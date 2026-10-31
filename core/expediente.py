# -*- coding: utf-8 -*-
"""
Expediente documental completo del caso.

Destino y alcance, que conviene declarar antes que el codigo.

Un financiador de salud que evalua la cobertura de un tratamiento oncologico
requiere constancia documental: que estudios se realizaron, que arrojaron,
quien los interpreto y sobre que base se adoptó la conducta. Reunir esa
documentacion es un trabajo administrativo considerable, y el sistema ya
dispone de todas las piezas.

**Este expediente no avala ni recomienda tratamiento alguno.** El sistema es
una herramienta de apoyo documental y tiene prohibido sugerir conductas
terapeuticas; esa prohibicion no admite excepcion por el destinatario del
documento. Lo que el expediente aporta es el legajo: lo que consta, con su
respaldo documental, las guias aplicables al cuadro y el registro de que
profesionales revisaron el caso y que dictaminaron. La indicacion terapeutica
la formula y la suscribe el medico tratante.

La distincion no es formal. Un documento emitido por un programa que
afirmara que corresponde cubrir determinada terapia constituiria un acto
medico sin medico, y su eventual error no tendria responsable.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.config import DIR_SALIDAS, TEXTO_SIN_DATO


ADVERTENCIA_ALCANCE = (
    "Este expediente reune la documentacion registrada en el sistema y el "
    "respaldo de cada dato consignado. No constituye indicacion, "
    "prescripcion ni aval de tratamiento, ni reemplaza el criterio del "
    "medico tratante, a quien corresponde formular y suscribir la "
    "indicacion terapeutica."
)

MARCO_NORMATIVO = [
    ("Clasificacion de tumores del sistema nervioso central",
     "Organizacion Mundial de la Salud, 5.a edicion (WHO CNS5, 2021). "
     "Define las entidades diagnosticas y la asignacion de grado a partir "
     "de la combinacion de criterios histologicos y moleculares."),
    ("Determinacion de biomarcadores en gliomas difusos",
     "College of American Pathologists, en conjunto con la American "
     "Association of Neuropathologists, la Association for Molecular "
     "Pathology y la Society for Neuro-Oncology (Brat et al., Arch Pathol "
     "Lab Med, 2022). Establece que biomarcadores corresponde determinar y "
     "mediante que tecnicas."),
    ("Diagnostico y tratamiento de gliomas difusos del adulto",
     "European Association of Neuro-Oncology (Weller et al., Nat Rev Clin "
     "Oncol, 2021). Esquemas terapeuticos y pautas de seguimiento."),
    ("Informe anatomopatologico estructurado",
     "International Collaboration on Cancer Reporting (ICCR), conjunto de "
     "datos de "
     "tumores del sistema nervioso central. Informe en capas: diagnostico "
     "integrado, apariencia histologica, parametros moleculares y grado."),
    ("Evaluacion de respuesta",
     "Response Assessment in Neuro-Oncology (RANO). Medicion bidimensional "
     "y criterios de respuesta, con ventana de doce semanas para la "
     "distincion entre progresion y pseudoprogresion."),
]


# ---------------------------------------------------------------------------
# Composicion del contenido
# ---------------------------------------------------------------------------

def _fecha_legible() -> str:
    return datetime.now().strftime("%d/%m/%Y a las %H:%M")


def componer_indice(secciones: List[str]) -> List[str]:
    return [f"{i}. {titulo}" for i, titulo in enumerate(secciones, 1)]


def reunir(identificador: str, resumen: Dict,
           ensayos: Optional[List[Dict]] = None,
           consultas: Optional[List[Dict]] = None,
           informes_lectura: Optional[List[Dict]] = None,
           emitido_por: str = "",
           institucion: str = "") -> Dict:
    """
    Reune en una estructura unica todo lo que integrara el expediente.

    Se separa la reunion del material de su presentacion: el mismo contenido
    alimenta el PDF, el indice del paquete y la constancia de integridad, y
    no deben poder divergir entre si.
    """
    campos = resumen.get("campos", []) or []
    documentados = [c for c in campos
                    if (c.get("contenido") or "").strip() != TEXTO_SIN_DATO]

    consultas = consultas or []
    respondidas = [c for c in consultas if c.get("estado") != "pendiente"]
    conformes = [c for c in consultas if c.get("estado") == "conforme"]
    observadas = [c for c in consultas
                  if c.get("estado") == "con_observaciones"]

    return {
        "identificador": identificador,
        "emitido_el": _fecha_legible(),
        "emitido_por": emitido_por,
        "institucion": institucion,
        "resumen": resumen,
        "campos": campos,
        "campos_documentados": len(documentados),
        "campos_totales": len(campos),
        "perfil_molecular": resumen.get("perfil_molecular") or {},
        "ensayos": ensayos or [],
        "consultas": consultas,
        "consultas_respondidas": len(respondidas),
        "consultas_conformes": len(conformes),
        "consultas_observadas": len(observadas),
        "informes_lectura": informes_lectura or [],
        "advertencias": resumen.get("advertencias") or [],
        "marco_normativo": MARCO_NORMATIVO,
        "modo": resumen.get("modo", ""),
        "modelo": resumen.get("modelo", ""),
    }


# ---------------------------------------------------------------------------
# Version en texto
# ---------------------------------------------------------------------------

def generar_texto(datos: Dict) -> str:
    """Version en texto plano del expediente, apta para copiar o adjuntar."""
    L: List[str] = []
    ancho = 78

    def regla(caracter="=") -> None:
        L.append(caracter * ancho)

    def titulo(texto: str) -> None:
        L.append("")
        regla("-")
        L.append(texto.upper())
        regla("-")

    regla()
    L.append("EXPEDIENTE DOCUMENTAL DEL CASO")
    L.append(f"Caso: {datos['identificador']}")
    regla()
    L.append(f"Emitido el {datos['emitido_el']}")
    if datos.get("emitido_por"):
        L.append(f"Emitido por: {datos['emitido_por']}")
    if datos.get("institucion"):
        L.append(f"Institucion: {datos['institucion']}")

    L.append("")
    L.append("ALCANCE DE ESTE DOCUMENTO")
    for linea in _envolver(ADVERTENCIA_ALCANCE, ancho):
        L.append(linea)

    titulo("1. Resumen estructurado del caso")
    for campo in datos["campos"]:
        L.append("")
        L.append(f"{campo.get('etiqueta', campo.get('clave', ''))}:")
        for linea in _envolver(campo.get("contenido", ""), ancho - 2):
            L.append(f"  {linea}")
        fuentes = campo.get("fuentes") or []
        if fuentes:
            etiquetas = ", ".join(
                sorted({f.get("etiqueta", "") for f in fuentes if f.get("etiqueta")}))
            L.append(f"  [Respaldo documental: {etiquetas}]")
        else:
            L.append("  [Sin fragmento documental de respaldo]")

    titulo("2. Perfil molecular")
    perfil = datos["perfil_molecular"]
    if not perfil:
        L.append("No se consignaron determinaciones moleculares.")
    for nombre, detalle in perfil.items():
        valor = detalle.get("valor", "") if isinstance(detalle, dict) else detalle
        L.append(f"  {nombre}: {valor}")

    titulo("3. Documentacion analizada")
    if not datos["informes_lectura"]:
        L.append("No se registro el detalle de los documentos procesados.")
    for informe in datos["informes_lectura"]:
        L.append(f"  {informe.get('nombre_documento', '')} "
                 f"({informe.get('metodo', '')}) - "
                 f"{informe.get('fragmentos', 0)} fragmento(s)")
        for advertencia in informe.get("advertencias", []):
            for linea in _envolver(advertencia, ancho - 6):
                L.append(f"      {linea}")

    titulo("4. Revision por especialidad")
    if not datos["consultas"]:
        L.append("El caso no fue sometido a revision por especialidad.")
        L.append("La ausencia de objeciones no equivale a conformidad.")
    for consulta in datos["consultas"]:
        L.append(f"  {consulta.get('nombre', '')} "
                 f"({consulta.get('especialidad', '')}): "
                 f"{consulta.get('estado', '')}")
        if consulta.get("observacion"):
            for linea in _envolver(consulta["observacion"], ancho - 6):
                L.append(f"      {linea}")

    titulo("5. Estudios clinicos identificados")
    if not datos["ensayos"]:
        L.append("No se incorporaron estudios clinicos al expediente.")
    for ensayo in datos["ensayos"]:
        L.append(f"  {ensayo.get('identificador', '')} - "
                 f"{ensayo.get('titulo', '')}")

    titulo("6. Marco normativo y de referencia")
    for nombre, descripcion in datos["marco_normativo"]:
        L.append(f"  {nombre}")
        for linea in _envolver(descripcion, ancho - 6):
            L.append(f"      {linea}")

    titulo("7. Observaciones del sistema")
    if not datos["advertencias"]:
        L.append("Sin observaciones.")
    for advertencia in datos["advertencias"]:
        for linea in _envolver(f"- {advertencia}", ancho):
            L.append(linea)

    L.append("")
    regla()
    for linea in _envolver(ADVERTENCIA_ALCANCE, ancho):
        L.append(linea)
    regla()

    return "\n".join(L)


def _envolver(texto: str, ancho: int) -> List[str]:
    import textwrap

    if not texto:
        return [""]
    lineas: List[str] = []
    for parrafo in str(texto).split("\n"):
        lineas.extend(textwrap.wrap(parrafo, ancho) or [""])
    return lineas


# ---------------------------------------------------------------------------
# Version en PDF
# ---------------------------------------------------------------------------

def generar_pdf(datos: Dict, destino: Optional[Path] = None) -> Path:
    """
    Compone el expediente en PDF, con caratula, indice y numeracion.

    El formato es deliberadamente sobrio y previsible. El destinatario es un
    area de auditoria que revisa muchos legajos: la claridad de la estructura
    y la constancia del respaldo de cada dato pesan mas que el diseno.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                        SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
    except ImportError as exc:
        raise RuntimeError(
            "La generacion del expediente en PDF requiere reportlab. "
            "Instalela con: pip install reportlab") from exc

    destino = Path(destino) if destino else (
        DIR_SALIDAS / f"expediente_{datos['identificador']}_"
                      f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)

    hoja = getSampleStyleSheet()
    normal = ParagraphStyle("cuerpo", parent=hoja["Normal"],
                            fontName="Helvetica", fontSize=9.5, leading=13,
                            alignment=TA_JUSTIFY)
    menor = ParagraphStyle("menor", parent=normal, fontSize=8, leading=10.5,
                           textColor=colors.HexColor("#555555"))
    h1 = ParagraphStyle("h1", parent=hoja["Normal"],
                        fontName="Helvetica-Bold", fontSize=16, leading=20,
                        spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=hoja["Normal"],
                        fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                        spaceBefore=14, spaceAfter=5)
    h3 = ParagraphStyle("h3", parent=hoja["Normal"],
                        fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                        spaceBefore=7, spaceAfter=2)
    centrado = ParagraphStyle("centrado", parent=normal, alignment=TA_CENTER)

    def recuadro(texto: str, estilo=None):
        tabla = Table([[Paragraph(texto, estilo or normal)]],
                      colWidths=[170 * mm])
        tabla.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#333333")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F2F2")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return tabla

    def tabla_datos(filas, anchos=(58 * mm, 112 * mm)):
        tabla = Table(
            [[Paragraph(f"<b>{a}</b>", normal), Paragraph(str(b), normal)]
             for a, b in filas], colWidths=list(anchos))
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tabla

    E: List = []

    # --- Caratula ----------------------------------------------------------
    E.append(Spacer(1, 22 * mm))
    E.append(Paragraph("Expediente documental del caso", h1))
    E.append(Paragraph(
        "Compilacion de la documentacion registrada y de su respaldo",
        menor))
    E.append(Spacer(1, 10 * mm))

    encabezado = [("Caso", _escapar(datos["identificador"])),
                  ("Fecha de emision", datos["emitido_el"])]
    if datos.get("emitido_por"):
        encabezado.append(("Emitido por", _escapar(datos["emitido_por"])))
    if datos.get("institucion"):
        encabezado.append(("Institucion", _escapar(datos["institucion"])))
    encabezado.append(
        ("Campos documentados",
         f"{datos['campos_documentados']} de {datos['campos_totales']}"))
    encabezado.append(
        ("Revision por especialidad",
         f"{datos['consultas_respondidas']} de {len(datos['consultas'])} "
         f"consulta(s) respondida(s)" if datos["consultas"]
         else "Sin consultas registradas"))
    E.append(tabla_datos(encabezado))

    E.append(Spacer(1, 10 * mm))
    E.append(recuadro("<b>Alcance de este documento.</b> "
                      + ADVERTENCIA_ALCANCE))

    E.append(Spacer(1, 8 * mm))
    E.append(Paragraph("Contenido", h3))
    for linea in componer_indice([
            "Resumen estructurado del caso, con respaldo documental",
            "Perfil molecular",
            "Documentacion analizada",
            "Revision por especialidad",
            "Estudios clinicos identificados",
            "Marco normativo y de referencia",
            "Observaciones del sistema"]):
        E.append(Paragraph(_escapar(linea), normal))

    E.append(PageBreak())

    # --- 1. Resumen --------------------------------------------------------
    E.append(Paragraph("1. Resumen estructurado del caso", h2))
    E.append(Paragraph(
        "Cada campo se acompana del documento del que proviene. Un campo sin "
        "respaldo documental se senala como tal.", menor))

    for campo in datos["campos"]:
        bloque = [Paragraph(
            _escapar(campo.get("etiqueta", campo.get("clave", ""))), h3)]
        bloque.append(Paragraph(_escapar(campo.get("contenido", "")), normal))
        fuentes = campo.get("fuentes") or []
        if fuentes:
            etiquetas = ", ".join(sorted(
                {f.get("etiqueta", "") for f in fuentes if f.get("etiqueta")}))
            bloque.append(Paragraph(
                f"Respaldo documental: {_escapar(etiquetas)}", menor))
        else:
            bloque.append(Paragraph(
                "Sin fragmento documental de respaldo asociado.", menor))
        E.append(KeepTogether(bloque))

    # --- 2. Perfil molecular ----------------------------------------------
    E.append(Paragraph("2. Perfil molecular", h2))
    perfil = datos["perfil_molecular"]
    if perfil:
        filas = []
        for nombre, detalle in perfil.items():
            valor = (detalle.get("valor", "") if isinstance(detalle, dict)
                     else str(detalle))
            filas.append((_escapar(nombre), _escapar(valor)))
        E.append(tabla_datos(filas, anchos=(58 * mm, 112 * mm)))
        E.append(Spacer(1, 2 * mm))
        E.append(Paragraph(
            "Determinaciones extraidas de la documentacion mediante reglas "
            "explicitas y verificables, no mediante un modelo de lenguaje.",
            menor))
    else:
        E.append(Paragraph("No se consignaron determinaciones moleculares.",
                           normal))

    # --- 3. Documentacion analizada ---------------------------------------
    E.append(Paragraph("3. Documentacion analizada", h2))
    if datos["informes_lectura"]:
        filas = [("Documento", "Lectura")]
        datos_tabla = [[Paragraph("<b>Documento</b>", normal),
                        Paragraph("<b>Metodo de lectura</b>", normal),
                        Paragraph("<b>Fragmentos</b>", normal)]]
        for informe in datos["informes_lectura"]:
            datos_tabla.append([
                Paragraph(_escapar(informe.get("nombre_documento", "")), normal),
                Paragraph(_escapar(informe.get("metodo", "")), normal),
                Paragraph(str(informe.get("fragmentos", 0)), normal)])
        tabla = Table(datos_tabla, colWidths=[70 * mm, 75 * mm, 25 * mm])
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        E.append(tabla)

        observaciones = [(i.get("nombre_documento", ""), a)
                         for i in datos["informes_lectura"]
                         for a in i.get("advertencias", [])]
        if observaciones:
            E.append(Spacer(1, 3 * mm))
            E.append(Paragraph("Observaciones sobre la lectura", h3))
            for nombre, advertencia in observaciones:
                E.append(Paragraph(
                    f"{_escapar(nombre)}: {_escapar(advertencia)}", menor))
    else:
        E.append(Paragraph(
            "No se registro el detalle de los documentos procesados.", normal))

    # --- 4. Revision por especialidad -------------------------------------
    E.append(Paragraph("4. Revision por especialidad", h2))
    if datos["consultas"]:
        for consulta in datos["consultas"]:
            bloque = [Paragraph(
                f"{_escapar(consulta.get('nombre', ''))} "
                f"- {_escapar(consulta.get('especialidad', ''))}", h3)]
            bloque.append(Paragraph(
                f"Dictamen: {_escapar(consulta.get('estado', ''))}. "
                f"Consultado el {_escapar(str(consulta.get('fecha_creacion', ''))[:10])}.",
                normal))
            if consulta.get("observacion"):
                bloque.append(Paragraph(
                    f"Observacion: {_escapar(consulta['observacion'])}", normal))
            E.append(KeepTogether(bloque))
    else:
        E.append(recuadro(
            "El caso no fue sometido a revision por especialidad. La "
            "ausencia de objeciones no equivale a conformidad."))

    # --- 5. Estudios clinicos ---------------------------------------------
    E.append(Paragraph("5. Estudios clinicos identificados", h2))
    if datos["ensayos"]:
        E.append(Paragraph(
            "Estudios cuya poblacion resulta compatible con las "
            "caracteristicas documentadas del caso. Su mencion no supone "
            "indicacion de participar en ellos.", menor))
        for ensayo in datos["ensayos"]:
            bloque = [Paragraph(
                _escapar(f"{ensayo.get('identificador', '')} "
                         f"- {ensayo.get('titulo', '')}"), h3)]
            if ensayo.get("estado"):
                bloque.append(Paragraph(
                    f"Estado: {_escapar(ensayo['estado'])}", menor))
            E.append(KeepTogether(bloque))
    else:
        E.append(Paragraph(
            "No se incorporaron estudios clinicos al expediente.", normal))

    # --- 6. Marco normativo ------------------------------------------------
    E.append(Paragraph("6. Marco normativo y de referencia", h2))
    E.append(Paragraph(
        "Guias y clasificaciones conforme a las cuales se estructuro el "
        "analisis documental.", menor))
    for nombre, descripcion in datos["marco_normativo"]:
        E.append(KeepTogether([Paragraph(_escapar(nombre), h3),
                               Paragraph(_escapar(descripcion), normal)]))

    # --- 7. Observaciones --------------------------------------------------
    E.append(Paragraph("7. Observaciones del sistema", h2))
    if datos["advertencias"]:
        E.append(Paragraph(
            "Discrepancias y faltantes detectados durante el analisis. Se "
            "consignan por transparencia: su presencia no invalida el "
            "expediente, pero corresponde que el profesional las evalue.",
            menor))
        for advertencia in datos["advertencias"]:
            E.append(Paragraph(f"- {_escapar(advertencia)}", normal))
    else:
        E.append(Paragraph("Sin observaciones.", normal))

    E.append(Spacer(1, 8 * mm))
    E.append(recuadro(ADVERTENCIA_ALCANCE, menor))

    def pie(lienzo, documento):
        lienzo.saveState()
        lienzo.setFont("Helvetica", 7.5)
        lienzo.setFillColor(colors.HexColor("#666666"))
        lienzo.drawString(
            20 * mm, 12 * mm,
            f"Expediente {datos['identificador']} - emitido el "
            f"{datos['emitido_el']} - documento de apoyo, no constituye "
            f"indicacion terapeutica")
        lienzo.drawRightString(190 * mm, 12 * mm, f"Pagina {documento.page}")
        lienzo.restoreState()

    documento = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Expediente documental - {datos['identificador']}",
        author=datos.get("emitido_por") or "Sistema de preparacion de casos")
    documento.build(E, onFirstPage=pie, onLaterPages=pie)
    return destino


def _escapar(texto) -> str:
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# Paquete
# ---------------------------------------------------------------------------

def nombre_del_paquete(identificador: str) -> str:
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"expediente_{identificador}_{marca}.zip"


def componer_paquete(datos: Dict,
                     documentos_origen: Optional[Dict[str, Path]] = None
                     ) -> bytes:
    """
    Empaqueta el expediente y la documentacion de origen.

    Se incluyen los documentos tal como fueron aportados. El expediente
    afirma lo que consta en ellos, de modo que quien lo revise debe poder
    contrastarlo contra la fuente sin tener que solicitarla por separado.

    Devuelve el contenido del archivo comprimido en memoria, apto para
    entregarlo por descarga sin dejar copia en el servidor.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr(
            f"{datos['identificador']}/expediente.txt",
            generar_texto(datos))

        try:
            ruta_pdf = generar_pdf(datos)
            paquete.write(ruta_pdf,
                          f"{datos['identificador']}/expediente.pdf")
        except RuntimeError as exc:
            # La ausencia de reportlab no debe impedir la entrega del
            # expediente: se informa dentro del propio paquete.
            paquete.writestr(
                f"{datos['identificador']}/LEEME_expediente_pdf.txt",
                f"No fue posible generar la version en PDF.\n\n{exc}\n\n"
                f"La version en texto plano se incluye completa.")

        incluidos = []
        for tipo, ruta in (documentos_origen or {}).items():
            ruta = Path(ruta)
            if not ruta.exists():
                continue
            destino = (f"{datos['identificador']}/documentacion_origen/"
                       f"{tipo}{ruta.suffix}")
            paquete.write(ruta, destino)
            incluidos.append(destino)

        paquete.writestr(f"{datos['identificador']}/CONTENIDO.txt",
                         _manifiesto(datos, incluidos))

    buffer.seek(0)
    return buffer.read()


def _manifiesto(datos: Dict, documentos_incluidos: List[str]) -> str:
    L = [
        f"EXPEDIENTE DOCUMENTAL - {datos['identificador']}",
        f"Emitido el {datos['emitido_el']}",
        "",
        "CONTENIDO DEL PAQUETE",
        "  expediente.pdf   Expediente completo, version para presentar.",
        "  expediente.txt   El mismo contenido en texto plano.",
    ]
    if documentos_incluidos:
        L.append("  documentacion_origen/   Documentos tal como fueron "
                 "aportados al sistema.")
        for ruta in sorted(documentos_incluidos):
            L.append(f"      {Path(ruta).name}")
    else:
        L.append("  (No se incorporo la documentacion de origen.)")

    L += ["", "ALCANCE"]
    L.extend(_envolver(ADVERTENCIA_ALCANCE, 76))
    return "\n".join(L)
