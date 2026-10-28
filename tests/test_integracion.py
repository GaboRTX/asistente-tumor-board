# -*- coding: utf-8 -*-
"""
Pruebas de integracion sobre los casos de demostracion.

Verifican el recorrido completo del sistema, desde la lectura de los
documentos hasta la generacion del reporte, sobre los casos sinteticos
incluidos en el proyecto. Los perfiles esperados se derivan de la
construccion documentada de cada caso.
"""

import pytest

from core.config import DIR_CASOS_DEMO
from core.ingesta import cargar_caso_demo, procesar_documentos
from core.perfil_molecular import extraer_perfil, resumir_para_busqueda
from core.rag import generar_resumen
from core.ensayos import buscar_para_perfil
from core import reporte


PERFILES_ESPERADOS = {
    "CASO-001": {"IDH": "mutado", "1p/19q": "codelecion ausente",
                 "MGMT": "metilado", "ATRX": "perdido", "TP53": "mutado",
                 "EGFR": "no amplificado", "TERT": "no mutado",
                 "CDKN2A/B": "delecion homocigota ausente"},
    "CASO-002": {"IDH": "no mutado", "1p/19q": "codelecion ausente",
                 "MGMT": "no metilado", "ATRX": "conservado",
                 "TERT": "mutado", "EGFR": "amplificado",
                 "CDKN2A/B": "delecion homocigota presente",
                 "Cromosomas 7/10": "alterado"},
    "CASO-003": {"IDH": "mutado", "1p/19q": "codelecion presente",
                 "MGMT": "metilado", "ATRX": "conservado",
                 "TERT": "mutado", "TP53": "no mutado",
                 "CDKN2A/B": "delecion homocigota ausente"},
    "CASO-004": {"IDH": "no mutado", "ATRX": "conservado",
                 "MGMT": "no informado"},
    "CASO-005": {"IDH": "no mutado", "1p/19q": "codelecion ausente",
                 "MGMT": "no metilado", "ATRX": "conservado",
                 "TERT": "mutado", "EGFR": "no amplificado",
                 "TP53": "no mutado",
                 "CDKN2A/B": "delecion homocigota presente"},
    "CASO-006": {"IDH": "no mutado", "H3": "alterado", "ATRX": "perdido",
                 "TP53": "mutado", "MGMT": "no metilado",
                 "1p/19q": "codelecion ausente", "TERT": "no mutado",
                 "CDKN2A/B": "delecion homocigota ausente"},
    "CASO-007": {"IDH": "mutado", "1p/19q": "codelecion ausente",
                 "MGMT": "metilado", "ATRX": "perdido", "TP53": "mutado",
                 "TERT": "no mutado",
                 "CDKN2A/B": "delecion homocigota ausente"},
    "CASO-008": {"IDH": "no mutado", "1p/19q": "codelecion ausente",
                 "MGMT": "metilado", "ATRX": "conservado",
                 "TERT": "mutado", "EGFR": "no amplificado",
                 "CDKN2A/B": "delecion homocigota presente",
                 "Cromosomas 7/10": "alterado"},
}


def fragmentos_de(caso):
    directorio = DIR_CASOS_DEMO / caso
    if not directorio.exists():
        pytest.skip(f"El caso {caso} no esta disponible. Ejecute "
                    f"scripts/generar_casos_demo.py")
    return procesar_documentos(caso, cargar_caso_demo(directorio))


@pytest.mark.parametrize("caso", sorted(PERFILES_ESPERADOS))
def test_perfil_molecular_de_cada_caso(caso):
    perfil = extraer_perfil(fragmentos_de(caso))
    for marcador, esperado in PERFILES_ESPERADOS[caso].items():
        assert perfil.valor(marcador) == esperado, (
            f"{caso}: se esperaba {marcador}={esperado}, "
            f"se obtuvo {perfil.valor(marcador)}")


@pytest.mark.parametrize("caso", sorted(PERFILES_ESPERADOS))
def test_el_pipeline_completo_no_falla(caso):
    resultado = generar_resumen(fragmentos_de(caso), forzar_sin_conexion=True)
    assert resultado.campos
    assert resultado.segundos > 0


def test_caso_con_documentacion_incompleta():
    """
    CASO-004 carece de informe genomico y su estudio de MGMT no es valorable.
    El sistema debe procesarlo sin fallar y declarar lo no documentado en
    lugar de completarlo por inferencia.
    """
    fragmentos = fragmentos_de("CASO-004")
    perfil = extraer_perfil(fragmentos)
    assert perfil.valor("MGMT") == "no informado"

    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    assert resultado.campos


def test_caso_con_redaccion_abreviada():
    """
    CASO-005 emplea una redaccion telegrafica, habitual en la practica. La
    extraccion debe ser igualmente correcta.
    """
    perfil = extraer_perfil(fragmentos_de("CASO-005"))
    assert perfil.valor("IDH") == "no mutado"
    assert perfil.valor("MGMT") == "no metilado"


def test_un_glioblastoma_no_recibe_estudios_de_idh_mutado():
    """
    Prueba de regresion sobre el defecto mas grave detectado: un caso IDH
    wild-type no debe recibir estudios que exigen mutacion de IDH.
    """
    perfil = extraer_perfil(fragmentos_de("CASO-002"))
    resultados, _origen, _resumen = buscar_para_perfil(
        resumir_para_busqueda(perfil), preferir_cache=True,
        maximo_resultados=10)

    for correspondencia in resultados:
        criterios = " ".join(correspondencia.coincidencias)
        assert "IDH: mutado" not in criterios


def test_un_caso_sin_codelecion_no_recibe_estudios_de_codelecionados():
    perfil = extraer_perfil(fragmentos_de("CASO-001"))
    resultados, _o, _r = buscar_para_perfil(
        resumir_para_busqueda(perfil), preferir_cache=True,
        maximo_resultados=10)

    for correspondencia in resultados:
        criterios = " ".join(correspondencia.coincidencias)
        assert "codelecion presente" not in criterios


def test_generacion_del_reporte_en_texto():
    fragmentos = fragmentos_de("CASO-001")
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    texto = reporte.generar_texto("CASO-001", resultado.como_dict())

    assert "CASO-001" in texto
    assert "ADVERTENCIA" in texto
    assert "no constituye" in texto.lower()


def test_el_reporte_incluye_siempre_la_advertencia_clinica():
    """
    La constancia de que el documento requiere validacion profesional no es
    configurable: debe estar presente en todo reporte generado.
    """
    fragmentos = fragmentos_de("CASO-003")
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    texto = reporte.generar_texto("CASO-003", resultado.como_dict())
    assert reporte.ADVERTENCIA.split(".")[0] in texto


def test_generacion_del_reporte_en_pdf(tmp_path):
    fragmentos = fragmentos_de("CASO-001")
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    destino = tmp_path / "reporte.pdf"

    try:
        ruta = reporte.generar_pdf("CASO-001", resultado.como_dict(),
                                   destino=destino)
    except RuntimeError:
        pytest.skip("reportlab no esta instalado")

    assert ruta.exists()
    assert ruta.stat().st_size > 1000


# ---------------------------------------------------------------------------
# Casos clinicos incorporados
# ---------------------------------------------------------------------------

def test_glioma_de_linea_media_recibe_su_estudio_especifico():
    """
    Regresion. Un glioma difuso de la linea media con alteracion de H3 debe
    recibir el estudio dirigido a esa entidad. El defecto original atribuia a
    H3 el estado wild-type informado para IDH en la misma enumeracion de
    criterios, y descartaba el estudio.
    """
    perfil = extraer_perfil(fragmentos_de("CASO-006"))
    assert perfil.valor("H3") == "alterado"

    resultados, _o, _r = buscar_para_perfil(
        resumir_para_busqueda(perfil), preferir_cache=True,
        maximo_resultados=10)

    criterios = " ".join(
        c for correspondencia in resultados
        for c in correspondencia.coincidencias
    )
    assert "H3: alterado" in criterios


def test_caso_de_seguimiento_con_evaluacion_de_respuesta():
    """El caso de seguimiento debe procesarse y consignar el tratamiento
    recibido."""
    fragmentos = fragmentos_de("CASO-007")
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    campo = resultado.campo("tratamientos_previos")
    assert campo is not None and campo.tiene_dato


def test_caso_de_pseudoprogresion_se_procesa_sin_error():
    """
    El caso de pseudoprogresion presenta un incremento del realce que no
    constituye progresion. El sistema debe procesarlo y recuperar los
    hallazgos imagenologicos, sin emitir juicio sobre la progresion, que
    corresponde al equipo tratante.
    """
    fragmentos = fragmentos_de("CASO-008")
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    campo = resultado.campo("hallazgos_imagenes")
    assert campo is not None and campo.tiene_dato
