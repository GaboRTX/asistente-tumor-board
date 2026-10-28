# -*- coding: utf-8 -*-
"""
Pruebas del ciclo de retroalimentacion.

Se concentran en la propiedad que hace admisible el mecanismo de aprendizaje
en un dominio clinico: ninguna correccion influye sobre casos futuros hasta
ser validada, y su desactivacion surte efecto de inmediato.
"""

import pytest

from core import db, feedback


@pytest.fixture
def caso_con_generacion(base_temporal):
    caso_id = db.crear_caso("CASO-PRUEBA", {"genomica": "g.txt"},
                            ruta=base_temporal)
    generacion_id = db.registrar_generacion(
        caso_id, "resumen", {"campos": []}, [], "prueba", "sin_conexion", 1.0,
        ruta=base_temporal)
    return base_temporal, caso_id, generacion_id


def registrar(ruta, caso_id, generacion_id, **extra):
    datos = dict(
        generacion_id=generacion_id, caso_id=caso_id, campo="perfil_molecular",
        valor_generado="MGMT: metilado",
        valor_corregido="MGMT: promotor metilado (42%)",
        tipo_error="dato_faltante", autor="Dra. Prueba", ruta=ruta)
    datos.update(extra)
    return feedback.registrar_correccion(**datos)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

def test_registrar_correccion_crea_feedback_y_regla(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    assert ids["feedback_id"] and ids["correccion_id"]
    assert len(db.listar_feedback(ruta=ruta)) == 1
    assert len(db.listar_correcciones(ruta=ruta)) == 1


def test_la_correccion_nace_pendiente(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    registrar(ruta, caso_id, generacion_id)
    assert db.listar_correcciones(ruta=ruta)[0]["estado"] == "pendiente"


def test_tipo_de_error_invalido_es_rechazado(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    with pytest.raises(ValueError):
        registrar(ruta, caso_id, generacion_id, tipo_error="inexistente")


def test_la_regla_no_reproduce_datos_del_paciente(caso_con_generacion):
    """
    La regla debe ser trasladable a otros casos, por lo que no puede afirmar
    datos clinicos del caso que la origino.
    """
    ruta, caso_id, generacion_id = caso_con_generacion
    registrar(ruta, caso_id, generacion_id)
    regla = db.listar_correcciones(ruta=ruta)[0]["regla"]
    assert "Perfil molecular" in regla
    assert "CASO-PRUEBA" not in regla


@pytest.mark.parametrize("tipo", list(feedback.TIPOS_ERROR.keys()))
def test_todos_los_tipos_de_error_producen_una_regla(caso_con_generacion, tipo):
    ruta, caso_id, generacion_id = caso_con_generacion
    registrar(ruta, caso_id, generacion_id, tipo_error=tipo)
    regla = db.listar_correcciones(ruta=ruta)[0]["regla"]
    assert isinstance(regla, str) and len(regla) > 40


# ---------------------------------------------------------------------------
# Curacion: la propiedad central del mecanismo
# ---------------------------------------------------------------------------

def test_una_correccion_pendiente_no_influye(caso_con_generacion, monkeypatch):
    ruta, caso_id, generacion_id = caso_con_generacion
    registrar(ruta, caso_id, generacion_id)
    monkeypatch.setattr(db, "RUTA_BASE_DATOS", ruta)
    assert len(feedback.construir_indice_correcciones(ruta=ruta)) == 0


def test_una_correccion_validada_si_influye(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    feedback.validar_correccion(ids["correccion_id"], "Dr. Validador", ruta=ruta)
    assert len(feedback.construir_indice_correcciones(ruta=ruta)) == 1


def test_la_desactivacion_surte_efecto_inmediato(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    feedback.validar_correccion(ids["correccion_id"], "Dr. Validador", ruta=ruta)
    assert len(feedback.construir_indice_correcciones(ruta=ruta)) == 1

    feedback.desactivar_correccion(ids["correccion_id"], "Dr. Validador",
                                   ruta=ruta)
    assert len(feedback.construir_indice_correcciones(ruta=ruta)) == 0


def test_una_correccion_desactivada_puede_reactivarse(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    feedback.validar_correccion(ids["correccion_id"], "A", ruta=ruta)
    feedback.desactivar_correccion(ids["correccion_id"], "A", ruta=ruta)
    feedback.validar_correccion(ids["correccion_id"], "B", ruta=ruta)
    assert len(feedback.construir_indice_correcciones(ruta=ruta)) == 1


def test_la_validacion_registra_autor_y_fecha(caso_con_generacion):
    """La trazabilidad de quien incorporo cada regla debe quedar asentada."""
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    feedback.validar_correccion(ids["correccion_id"], "Dr. Validador", ruta=ruta)
    correccion = db.listar_correcciones("activa", ruta=ruta)[0]
    assert correccion["autor_validacion"] == "Dr. Validador"
    assert correccion["fecha_validacion"]


def test_estado_invalido_es_rechazado(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    ids = registrar(ruta, caso_id, generacion_id)
    with pytest.raises(ValueError):
        db.cambiar_estado_correccion(ids["correccion_id"], "aprobada",
                                     ruta=ruta)


# ---------------------------------------------------------------------------
# Estadisticas
# ---------------------------------------------------------------------------

def test_estadisticas_sobre_un_almacen_vacio(base_temporal):
    est = feedback.estadisticas(ruta=base_temporal)
    assert est["total_feedback"] == 0
    assert est["correcciones_activas"] == 0


def test_estadisticas_reflejan_los_estados(caso_con_generacion):
    ruta, caso_id, generacion_id = caso_con_generacion
    a = registrar(ruta, caso_id, generacion_id)
    b = registrar(ruta, caso_id, generacion_id, campo="antecedentes")
    feedback.validar_correccion(a["correccion_id"], "V", ruta=ruta)

    est = feedback.estadisticas(ruta=ruta)
    assert est["total_feedback"] == 2
    assert est["correcciones_activas"] == 1
    assert est["correcciones_pendientes"] == 1
