# -*- coding: utf-8 -*-
"""
Pruebas de la extraccion determinista del perfil molecular.

Este modulo concentra la mayor cantidad de pruebas del proyecto porque de su
correccion dependen dos funciones criticas: la busqueda de estudios clinicos
y la verificacion de la salida generada por el modelo de lenguaje.

Varios de los casos incluidos corresponden a defectos efectivamente
detectados durante el desarrollo y se conservan como prueba de regresion.
"""

import pytest

from core.perfil_molecular import extraer_perfil


def perfil_de(texto, tipo_documento="genomica"):
    return extraer_perfil([{"texto": texto, "tipo_documento": tipo_documento}])


# ---------------------------------------------------------------------------
# IDH
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Se detecta mutacion IDH1 R132H por secuenciacion.", "mutado"),
    ("IDH1: mutacion p.R132H detectada.", "mutado"),
    ("Inmunohistoquimica para IDH1 R132H positiva.", "mutado"),
    ("Tumor IDH wildtype confirmado.", "no mutado"),
    ("IDH1/2 wild-type.", "no mutado"),
    ("No se detecta mutacion en IDH1 ni IDH2.", "no mutado"),
    ("IDH1 no mutado.", "no mutado"),
])
def test_idh(texto, esperado):
    assert perfil_de(texto).valor("IDH") == esperado


# ---------------------------------------------------------------------------
# Codelecion 1p/19q
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Se observa codelecion 1p/19q.", "codelecion presente"),
    ("Codelecion 1p/19q presente por FISH.", "codelecion presente"),
    ("Ausencia de codelecion 1p/19q.", "codelecion ausente"),
    ("No se evidencia codelecion 1p/19q.", "codelecion ausente"),
    ("1p/19q conservados.", "codelecion ausente"),
    ("1p/19q: ausente.", "codelecion ausente"),
])
def test_codelecion(texto, esperado):
    assert perfil_de(texto).valor("1p/19q") == esperado


# ---------------------------------------------------------------------------
# MGMT
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Promotor de MGMT metilado.", "metilado"),
    ("MGMT hipermetilado (45%).", "metilado"),
    ("Promotor de MGMT no metilado.", "no metilado"),
    ("Metilacion del promotor de MGMT: ausente.", "no metilado"),
    ("Ausencia de metilacion del promotor MGMT.", "no metilado"),
])
def test_mgmt(texto, esperado):
    assert perfil_de(texto).valor("MGMT") == esperado


def test_mgmt_descripcion_de_tecnica_no_es_resultado():
    """
    Regresion. Una linea que describe unicamente la tecnica empleada no
    informa un resultado y no debe interpretarse como metilacion positiva.
    """
    assert perfil_de("Metilacion de MGMT por pirosecuenciacion.").valor("MGMT") == \
        "no informado"


def test_mgmt_estudio_no_valorable():
    """
    Regresion. Un estudio no valorable por material insuficiente debe
    declararse como no informado, nunca como un resultado negativo.
    """
    texto = ("El estudio de metilacion del promotor de MGMT no resulta "
             "valorable por material insuficiente.")
    assert perfil_de(texto, "anatomia_patologica").valor("MGMT") == "no informado"


# ---------------------------------------------------------------------------
# Otros marcadores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto,marcador,esperado", [
    ("Perdida de expresion nuclear de ATRX.", "ATRX", "perdido"),
    ("ATRX conservado.", "ATRX", "conservado"),
    ("Mutacion del promotor de TERT C228T.", "TERT", "mutado"),
    ("Amplificacion de EGFR presente.", "EGFR", "amplificado"),
    ("Sin amplificacion de EGFR.", "EGFR", "no amplificado"),
    ("Mutacion de TP53 detectada.", "TP53", "mutado"),
])
def test_otros_marcadores(texto, marcador, esperado):
    assert perfil_de(texto).valor(marcador) == esperado


# ---------------------------------------------------------------------------
# Enumeraciones y negaciones cruzadas
# ---------------------------------------------------------------------------

def test_enumeracion_de_inmunohistoquimica():
    """
    Regresion. En una enumeracion separada por comas, el estado informado de
    un marcador no debe atribuirse a otro. El defecto original asignaba a
    ATRX el termino 'negativo' que correspondia a IDH1.
    """
    texto = "IHQ: GFAP +, IDH1 R132H negativo, ATRX conservado, Ki67 30%."
    perfil = perfil_de(texto, "anatomia_patologica")
    assert perfil.valor("ATRX") == "conservado"
    assert perfil.valor("IDH") == "no mutado"


def test_negacion_posterior_al_marcador():
    """Regresion. La negacion puede seguir al marcador: 'TP53 sin mutacion'."""
    perfil = perfil_de("ATRX conservado y TP53 sin mutacion.")
    assert perfil.valor("TP53") == "no mutado"
    assert perfil.valor("ATRX") == "conservado"


def test_varios_marcadores_en_una_oracion():
    texto = ("Tumor IDH wild-type, sin codelecion 1p/19q, promotor de MGMT "
             "no metilado.")
    perfil = perfil_de(texto)
    assert perfil.valor("IDH") == "no mutado"
    assert perfil.valor("1p/19q") == "codelecion ausente"
    assert perfil.valor("MGMT") == "no metilado"


def test_negacion_no_se_propaga_entre_clausulas():
    texto = ("No se detecta amplificacion de EGFR, aunque si se observa "
             "mutacion del promotor de TERT.")
    perfil = perfil_de(texto)
    assert perfil.valor("EGFR") == "no amplificado"
    assert perfil.valor("TERT") == "mutado"


# ---------------------------------------------------------------------------
# Prioridad entre documentos
# ---------------------------------------------------------------------------

def test_informe_genomico_prevalece_sobre_patologia():
    """
    Ante resultados discrepantes, prevalece el informe de secuenciacion por
    ser la tecnica de mayor especificidad.
    """
    fragmentos = [
        {"texto": "IDH1 R132H negativo por inmunohistoquimica.",
         "tipo_documento": "anatomia_patologica"},
        {"texto": "IDH1: mutacion p.R132H detectada.",
         "tipo_documento": "genomica"},
    ]
    assert extraer_perfil(fragmentos).valor("IDH") == "mutado"


# ---------------------------------------------------------------------------
# Casos limite
# ---------------------------------------------------------------------------

def test_texto_vacio():
    assert extraer_perfil([]).informados == {}
    assert perfil_de("").informados == {}


def test_texto_sin_marcadores():
    texto = "El paciente presenta cefalea de tres meses de evolucion."
    assert perfil_de(texto, "historia_clinica").informados == {}


def test_marcador_no_informado_devuelve_valor_por_defecto():
    perfil = perfil_de("Promotor de MGMT metilado.")
    assert perfil.valor("IDH") == "no informado"
    assert not perfil.obtener("IDH").informado


def test_representacion_textual_del_perfil():
    perfil = perfil_de("IDH1 R132H detectada. Promotor de MGMT metilado.")
    texto = perfil.como_texto()
    assert "IDH" in texto and "MGMT" in texto
    assert texto.endswith(".")


def test_perfil_conserva_la_evidencia_textual():
    """Cada marcador debe conservar la oracion que lo respalda."""
    oracion = "Promotor de MGMT metilado."
    marcador = perfil_de(oracion).obtener("MGMT")
    assert marcador.evidencia.strip() == oracion
    assert marcador.tipo_documento == "genomica"
