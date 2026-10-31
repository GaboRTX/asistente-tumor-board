# -*- coding: utf-8 -*-
"""
Verificacion de que el formato del documento no altera el analisis.

Es la propiedad que justifica admitir formatos heterogeneos: si el mismo
informe arrojara un perfil distinto por estar en Word en lugar de en texto
plano, la ampliacion de formatos seria una fuente de error y no una
facilidad.

La comparacion se realiza contra el mismo contenido en texto plano, que es
la referencia sobre la que se construyeron los detectores.
"""

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from core.config import DIR_CASOS_DEMO
from core.ingesta import cargar_caso_demo, procesar_documentos_detallado
from core.perfil_molecular import extraer_perfil


def _casos():
    from generar_casos_demo import CASOS
    return CASOS


def _perfil_de(caso: str, documentos) -> dict:
    fragmentos, _informes = procesar_documentos_detallado(caso, documentos)
    perfil = extraer_perfil(fragmentos)
    return {nombre: marcador.valor
            for nombre, marcador in perfil.informados.items()}


@pytest.fixture(scope="module")
def referencia(tmp_path_factory):
    """Los mismos casos escritos integramente en texto plano."""
    base = tmp_path_factory.mktemp("texto_plano")
    for caso, documentos in _casos().items():
        directorio = base / caso
        directorio.mkdir(parents=True)
        for tipo, contenido in documentos.items():
            (directorio / f"{tipo}.txt").write_text(contenido,
                                                    encoding="utf-8")
    return base


@pytest.mark.parametrize("caso", sorted(_casos()))
def test_el_formato_no_altera_el_perfil_molecular(caso, referencia):
    esperado = _perfil_de(caso, cargar_caso_demo(referencia / caso))
    obtenido = _perfil_de(caso, cargar_caso_demo(DIR_CASOS_DEMO / caso))

    assert obtenido == esperado, (
        f"{caso}: el perfil difiere segun el formato del documento")


@pytest.mark.parametrize("caso", sorted(_casos()))
def test_todo_documento_del_caso_aporta_texto(caso):
    """
    Un documento que no aporta fragmentos indica que su formato no se leyo.
    Los casos de demostracion no contienen imagenes ni escaneos, de modo que
    todos deben aportar texto.
    """
    _fragmentos, informes = procesar_documentos_detallado(
        caso, cargar_caso_demo(DIR_CASOS_DEMO / caso))

    assert informes, f"{caso}: no se hallaron documentos"
    sin_texto = [i["nombre_documento"] for i in informes
                 if not i["tiene_texto"]]
    assert not sin_texto, f"{caso}: documentos sin texto extraido: {sin_texto}"


def test_el_conjunto_ejercita_formatos_variados():
    """
    El conjunto debe cubrir los lectores. Si todos los casos quedaran en
    texto plano, las pruebas anteriores serian vacuas.
    """
    extensiones = set()
    for directorio in DIR_CASOS_DEMO.glob("CASO-*"):
        for ruta in directorio.glob("*.*"):
            extensiones.add(ruta.suffix.lower())

    esperadas = {".docx", ".pdf", ".xlsx", ".odt", ".csv", ".html", ".rtf",
                 ".md", ".txt"}
    faltantes = esperadas - extensiones
    assert not faltantes, f"formatos no ejercitados por el conjunto: {faltantes}"


def test_los_documentos_de_word_incorporan_figuras():
    """
    Al menos un caso debe incluir figuras embebidas, de modo que la via de
    deteccion y declaracion de imagenes quede ejercitada.
    """
    from core import lectores

    con_figuras = []
    for ruta in DIR_CASOS_DEMO.glob("CASO-*/*.docx"):
        if lectores.leer(ruta).imagenes:
            con_figuras.append(ruta.name)

    assert con_figuras, "ningun documento de Word incorpora figuras"
