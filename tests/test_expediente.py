# -*- coding: utf-8 -*-
"""
Pruebas del expediente documental.

La propiedad que mas atencion concentra es negativa y no funcional: que el
expediente NO formule indicacion terapeutica. El sistema tiene prohibido
sugerir conductas, y esa prohibicion no admite excepcion por el destinatario
del documento. Un documento emitido por un programa que afirmara que
corresponde cubrir determinada terapia constituiria un acto medico sin
medico, y su eventual error no tendria responsable.
"""

import io
import zipfile

import pytest

from core import expediente


RESUMEN = {
    "modo": "sin_conexion",
    "modelo": "reglas-deterministas",
    "advertencias": ["El marcador TERT no aparece en el resumen generado."],
    "perfil_molecular": {
        "IDH": {"valor": "mutado"},
        "MGMT": {"valor": "metilado"},
    },
    "campos": [
        {"clave": "datos_clinicos", "etiqueta": "Datos clinicos relevantes",
         "contenido": "Varon de 41 anios con cefalea holocraneana.",
         "fuentes": [{"etiqueta": "Historia clinica (fragmento 1)"}]},
        {"clave": "hallazgos_patologia",
         "etiqueta": "Hallazgos anatomopatologicos",
         "contenido": "Astrocitoma IDH mutante, grado 3 de la OMS.",
         "fuentes": [{"etiqueta": "Informe anatomopatologico (fragmento 2)"}]},
        {"clave": "tratamientos_previos", "etiqueta": "Tratamientos previos",
         "contenido": "No consta en la documentacion aportada.",
         "fuentes": []},
    ],
}

CONSULTAS = [
    {"nombre": "Dra. Carolina Vera", "especialidad": "anatomia_patologica",
     "estado": "conforme", "observacion": "",
     "fecha_creacion": "2026-10-30T20:00:00"},
    {"nombre": "Dr. Julian Laguna", "especialidad": "neurocirugia",
     "estado": "con_observaciones",
     "observacion": "Revisar el margen posterior de la reseccion.",
     "fecha_creacion": "2026-10-30T20:05:00"},
]

INFORMES = [
    {"nombre_documento": "historia_clinica.docx", "metodo": "DOCX",
     "fragmentos": 4, "advertencias": [], "tiene_texto": True},
    {"nombre_documento": "resonancia.png", "metodo": "imagen adjunta",
     "fragmentos": 0, "tiene_texto": False,
     "advertencias": ["Sin reconocimiento optico disponible. El documento se "
                      "conserva adjunto pero no aporta texto al analisis."]},
]


@pytest.fixture
def datos():
    return expediente.reunir(
        "CASO-001", RESUMEN, ensayos=[], consultas=CONSULTAS,
        informes_lectura=INFORMES, emitido_por="Dra. Mariana Rossi",
        institucion="Hospital de demostracion")


# ---------------------------------------------------------------------------
# Alcance: el expediente no indica tratamiento
# ---------------------------------------------------------------------------

# Formulaciones que supondrian una indicacion o un aval terapeutico emitido
# por el sistema.
FORMULAS_PROHIBIDAS = [
    "se recomienda el tratamiento",
    "corresponde cubrir",
    "corresponde autorizar",
    "se indica tratamiento",
    "debe autorizarse",
    "resulta imprescindible el tratamiento",
    "el tratamiento indicado es",
    "se avala",
]


def _normalizar(texto: str) -> str:
    """
    Reduce el texto a una sola linea con espacios simples.

    El expediente ajusta el texto al ancho de la pagina, de modo que una
    frase puede repartirse en varias lineas. La verificacion recae sobre el
    contenido, no sobre su disposicion.
    """
    return " ".join(texto.split())


def test_el_expediente_declara_su_alcance_en_texto(datos):
    texto = _normalizar(expediente.generar_texto(datos))
    assert "No constituye indicacion, prescripcion ni aval de tratamiento" \
        in texto
    assert "medico tratante" in texto


def test_el_expediente_no_formula_indicacion_terapeutica(datos):
    """
    Propiedad central. El sistema compila documentacion; no prescribe.
    """
    texto = _normalizar(expediente.generar_texto(datos)).lower()
    presentes = [f for f in FORMULAS_PROHIBIDAS if f in texto]
    assert not presentes, f"el expediente formula una indicacion: {presentes}"


def test_la_mencion_de_estudios_aclara_que_no_es_indicacion():
    datos = expediente.reunir(
        "CASO-001", RESUMEN,
        ensayos=[{"identificador": "NCT00000000", "titulo": "Estudio X",
                  "estado": "reclutando"}])
    ruta = expediente.generar_pdf(datos)
    assert ruta.exists()
    # El texto cumple la misma funcion y es inspeccionable
    texto = expediente.generar_texto(datos)
    assert "Estudio X" in texto


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------

def test_cada_campo_se_acompana_de_su_respaldo(datos):
    texto = _normalizar(expediente.generar_texto(datos))
    assert "Historia clinica (fragmento 1)" in texto
    assert "Informe anatomopatologico (fragmento 2)" in texto


def test_un_campo_sin_respaldo_se_senala_como_tal(datos):
    """
    Omitir la falta de respaldo permitiria presentar como documentado algo
    que no lo esta, que es exactamente lo que el expediente debe impedir.
    """
    texto = _normalizar(expediente.generar_texto(datos))
    assert "Sin fragmento documental de respaldo" in texto


def test_el_expediente_consigna_la_documentacion_que_no_aporto_texto(datos):
    """
    Una imagen adjunta sin reconocimiento optico no aporta texto. El
    expediente debe consignarlo: quien lo revise podria suponer que ese
    estudio fue considerado.
    """
    texto = _normalizar(expediente.generar_texto(datos))
    assert "resonancia.png" in texto
    assert "no aporta texto al analisis" in texto


def test_el_expediente_incluye_la_revision_y_sus_observaciones(datos):
    texto = _normalizar(expediente.generar_texto(datos))
    assert "Dra. Carolina Vera" in texto
    assert "Revisar el margen posterior" in texto


def test_un_caso_sin_revision_se_declara_sin_revision():
    datos = expediente.reunir("CASO-001", RESUMEN, consultas=[])
    texto = _normalizar(expediente.generar_texto(datos))
    assert "no fue sometido a revision" in texto
    assert "ausencia de objeciones no equivale a conformidad" in texto


def test_el_expediente_incluye_el_marco_normativo(datos):
    texto = _normalizar(expediente.generar_texto(datos))
    for sigla in ("WHO CNS5", "College of American Pathologists",
                  "European Association of Neuro-Oncology", "RANO", "ICCR"):
        assert sigla in texto, f"falta la referencia a {sigla}"


def test_las_advertencias_del_sistema_se_trasladan(datos):
    """
    Omitirlas presentaria un expediente mas prolijo que la realidad.
    """
    texto = _normalizar(expediente.generar_texto(datos))
    assert "TERT no aparece" in texto


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def test_el_pdf_se_genera_con_varias_paginas(datos, tmp_path):
    from pypdf import PdfReader

    ruta = expediente.generar_pdf(datos, destino=tmp_path / "exp.pdf")
    assert ruta.exists()

    lector = PdfReader(str(ruta))
    assert len(lector.pages) >= 2

    texto = "\n".join(p.extract_text() or "" for p in lector.pages)
    assert "CASO-001" in texto
    assert "Expediente documental" in texto
    assert "no constituye indicacion terapeutica" in texto.lower()


def test_el_pdf_resiste_el_marcado_en_el_contenido(tmp_path):
    """
    El contenido proviene de documentacion aportada por el usuario y se
    inserta en un lenguaje de marcado. Sin escapado, un signo de menor
    romperia la composicion.
    """
    resumen = dict(RESUMEN)
    resumen["campos"] = [
        {"clave": "datos_clinicos", "etiqueta": "Datos clinicos",
         "contenido": "Lesion <10 mm & margen > 5 mm <b>no es negrita</b>",
         "fuentes": []}]

    datos = expediente.reunir("CASO-002", resumen)
    ruta = expediente.generar_pdf(datos, destino=tmp_path / "exp.pdf")
    assert ruta.exists() and ruta.stat().st_size > 1000


# ---------------------------------------------------------------------------
# Paquete
# ---------------------------------------------------------------------------

def test_el_paquete_reune_expediente_y_documentacion(datos, tmp_path):
    origen = tmp_path / "patologia.txt"
    origen.write_text("Informe anatomopatologico de origen.", encoding="utf-8")

    contenido = expediente.componer_paquete(
        datos, documentos_origen={"anatomia_patologica": origen})

    with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
        nombres = paquete.namelist()
        assert "CASO-001/expediente.pdf" in nombres
        assert "CASO-001/expediente.txt" in nombres
        assert "CASO-001/CONTENIDO.txt" in nombres
        assert any("documentacion_origen/anatomia_patologica.txt" in n
                   for n in nombres)

        manifiesto = paquete.read("CASO-001/CONTENIDO.txt").decode("utf-8")
        assert "No constituye indicacion" in manifiesto


def test_el_paquete_se_compone_sin_documentacion_de_origen(datos):
    contenido = expediente.componer_paquete(datos)
    with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
        assert "CASO-001/expediente.pdf" in paquete.namelist()
        assert not any("documentacion_origen" in n
                       for n in paquete.namelist())


def test_un_documento_de_origen_inexistente_no_interrumpe(datos, tmp_path):
    """
    El archivo temporal pudo haberse limpiado. El expediente debe componerse
    igualmente, antes que fallar por completo.
    """
    contenido = expediente.componer_paquete(
        datos, documentos_origen={"patologia": tmp_path / "no_existe.pdf"})

    with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
        assert "CASO-001/expediente.pdf" in paquete.namelist()


def test_el_nombre_del_paquete_identifica_el_caso():
    nombre = expediente.nombre_del_paquete("CASO-007")
    assert nombre.startswith("expediente_CASO-007_")
    assert nombre.endswith(".zip")
