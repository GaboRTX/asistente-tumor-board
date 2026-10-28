# -*- coding: utf-8 -*-
"""
Pruebas del pipeline de recuperacion aumentada por generacion.

Verifican la restriccion central del sistema: ningun campo puede afirmar un
dato que no este respaldado por la documentacion aportada, y toda afirmacion
debe poder atribuirse a un fragmento concreto.
"""

from core.config import TEXTO_SIN_DATO
from core.rag import (generar_resumen, construir_prompt, verificar_consistencia,
                      CampoResumen)
from core.perfil_molecular import extraer_perfil
from core.vectorizacion import construir_indice


# ---------------------------------------------------------------------------
# Generacion determinista
# ---------------------------------------------------------------------------

def test_el_resumen_contiene_todos_los_campos(fragmentos_caso):
    resultado = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    claves = {c.clave for c in resultado.campos}
    assert {"datos_clinicos", "antecedentes", "hallazgos_patologia",
            "perfil_molecular", "hallazgos_imagenes",
            "tratamientos_previos"} <= claves


def test_los_campos_documentados_citan_su_fuente(fragmentos_caso):
    """Toda afirmacion debe poder atribuirse a un fragmento documental."""
    resultado = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    for campo in resultado.campos:
        if campo.tiene_dato:
            assert campo.fuentes, f"El campo {campo.clave} no cita su fuente"


def test_el_perfil_molecular_se_refleja_en_el_resumen(fragmentos_caso):
    resultado = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    campo = resultado.campo("perfil_molecular")
    assert "IDH" in campo.contenido
    assert "MGMT" in campo.contenido


def test_un_dato_ausente_se_declara_explicitamente():
    """
    El sistema no debe completar por inferencia: si el dato no consta, debe
    declararlo.
    """
    fragmentos = [{"id": "x", "texto": "Resonancia magnetica sin hallazgos.",
                   "tipo_documento": "imagenes", "etiqueta_fuente": "Imagenes"}]
    resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
    campo = resultado.campo("perfil_molecular")
    assert campo.contenido == TEXTO_SIN_DATO
    assert not campo.tiene_dato


def test_el_modo_sin_conexion_queda_registrado(fragmentos_caso):
    resultado = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    assert resultado.modo == "sin_conexion"
    assert resultado.modelo == "reglas-deterministas"


def test_se_registra_el_tiempo_de_procesamiento(fragmentos_caso):
    """El tiempo alimenta la metrica asociada a la hipotesis del proyecto."""
    resultado = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    assert resultado.segundos > 0


def test_la_generacion_es_reproducible(fragmentos_caso):
    """
    En modo determinista, dos ejecuciones sobre la misma entrada deben
    producir el mismo resultado. Esta propiedad es la que hace auditable el
    modo de respaldo.
    """
    a = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    b = generar_resumen(fragmentos_caso, forzar_sin_conexion=True)
    assert [c.contenido for c in a.campos] == [c.contenido for c in b.campos]


def test_entrada_vacia_no_produce_error():
    resultado = generar_resumen([], forzar_sin_conexion=True)
    assert all(c.contenido == TEXTO_SIN_DATO for c in resultado.campos)


# ---------------------------------------------------------------------------
# Construccion del prompt
# ---------------------------------------------------------------------------

def test_el_prompt_prohibe_afirmar_datos_ausentes(fragmentos_caso):
    indice = construir_indice(fragmentos_caso)
    recuperados = indice.buscar("perfil molecular", k=3)
    prompt = construir_prompt([("perfil_molecular", "Perfil molecular")],
                              recuperados)
    assert TEXTO_SIN_DATO in prompt
    assert "No afirmes" in prompt or "no afirmes" in prompt.lower()


def test_el_prompt_numera_los_fragmentos(fragmentos_caso):
    indice = construir_indice(fragmentos_caso)
    recuperados = indice.buscar("perfil molecular", k=2)
    prompt = construir_prompt([("perfil_molecular", "Perfil molecular")],
                              recuperados)
    assert "[Fragmento 1]" in prompt


def test_las_correcciones_se_incorporan_al_prompt(fragmentos_caso):
    indice = construir_indice(fragmentos_caso)
    recuperados = indice.buscar("perfil molecular", k=2)
    correcciones = [{"id": 1, "regla": "Consignar el porcentaje de metilacion."}]
    prompt = construir_prompt([("perfil_molecular", "Perfil molecular")],
                              recuperados, correcciones)
    assert "CORRECCIONES PREVIAS" in prompt
    assert "porcentaje de metilacion" in prompt


def test_las_correcciones_no_habilitan_a_inventar(fragmentos_caso):
    """
    Las reglas incorporadas no deben interpretarse como permiso para afirmar
    datos ausentes en el caso en curso.
    """
    indice = construir_indice(fragmentos_caso)
    recuperados = indice.buscar("perfil molecular", k=2)
    prompt = construir_prompt([("perfil_molecular", "Perfil molecular")],
                              recuperados, [{"id": 1, "regla": "Regla."}])
    assert "NO habilitan" in prompt


# ---------------------------------------------------------------------------
# Verificacion de consistencia
# ---------------------------------------------------------------------------

def test_se_detecta_un_marcador_omitido(fragmentos_caso):
    """
    Si la extraccion determinista halla un marcador que el resumen no
    menciona, debe emitirse una advertencia.
    """
    perfil = extraer_perfil(fragmentos_caso)
    campos = [CampoResumen("perfil_molecular", "Perfil molecular",
                           "Sin particularidades.", fuentes=[{"etiqueta": "x"}])]
    advertencias = verificar_consistencia(campos, perfil)
    assert any("IDH" in a for a in advertencias)


def test_se_detecta_una_contradiccion_de_polaridad(fragmentos_caso):
    """
    El caso documenta IDH mutado; un resumen que consigne lo contrario debe
    generar una advertencia de discrepancia.
    """
    perfil = extraer_perfil(fragmentos_caso)
    campos = [CampoResumen("perfil_molecular", "Perfil molecular",
                           "IDH: no mutado. MGMT: metilado. 1p/19q: codelecion ausente.",
                           fuentes=[{"etiqueta": "x"}])]
    advertencias = verificar_consistencia(campos, perfil)
    assert any("Discrepancia" in a and "IDH" in a for a in advertencias)


def test_se_detecta_contenido_sin_respaldo(fragmentos_caso):
    perfil = extraer_perfil(fragmentos_caso)
    campos = [CampoResumen("antecedentes", "Antecedentes",
                           "Hipertension arterial.", fuentes=[])]
    advertencias = verificar_consistencia(campos, perfil)
    assert any("sin fragmento de respaldo" in a for a in advertencias)


def test_un_resumen_consistente_no_genera_advertencias(fragmentos_caso):
    perfil = extraer_perfil(fragmentos_caso)
    campos = [CampoResumen("perfil_molecular", "Perfil molecular",
                           perfil.como_texto(), fuentes=[{"etiqueta": "x"}])]
    assert verificar_consistencia(campos, perfil) == []


# ---------------------------------------------------------------------------
# Diagnostico de la configuracion del modelo de lenguaje
# ---------------------------------------------------------------------------

def test_el_error_de_modelo_inexistente_es_accionable():
    """
    Un codigo 404 indica que el identificador del modelo no esta habilitado,
    no que el servicio este caido. El mensaje debe orientar sobre como
    resolverlo en lugar de reproducir el error del proveedor.
    """
    from core.llm import _describir_error

    mensaje = _describir_error(
        Exception("404 Client Error: Not Found for url: https://ejemplo"),
        "google", "modelo-inexistente")

    assert "modelo-inexistente" in mensaje
    assert "MODELO_LLM" in mensaje
    assert "verificar_entorno" in mensaje


def test_el_error_de_credencial_se_distingue_del_de_modelo():
    from core.llm import _describir_error

    mensaje = _describir_error(Exception("401 Unauthorized"), "google", "m")
    assert "clave" in mensaje.lower()
    assert "MODELO_LLM" not in mensaje


def test_el_error_de_cuota_se_identifica():
    from core.llm import _describir_error

    mensaje = _describir_error(Exception("429 Too Many Requests"), "google", "m")
    assert "limite" in mensaje.lower()


def test_sin_clave_no_se_consultan_modelos():
    """Sin credencial configurada no corresponde intentar la consulta."""
    from core.llm import listar_modelos_disponibles

    modelos, mensaje = listar_modelos_disponibles()
    assert modelos == []
    assert ".env" in mensaje


def test_el_motivo_informado_por_el_proveedor_se_conserva():
    """
    Regresion. El codigo de estado por si solo no indica la causa: el motivo
    se consigna en el cuerpo de la respuesta. Descartarlo deja al usuario sin
    saber si debe habilitar la interfaz, revisar las restricciones de la
    clave o cambiar de modelo.
    """
    from core.llm import _describir_error

    mensaje = _describir_error(
        RuntimeError("403 Forbidden. Generative Language API has not been "
                     "used in project 123 before or it is disabled. "
                     "[PERMISSION_DENIED]"),
        "google", "gemini-3.8-flash")

    assert "has not been used" in mensaje or "disabled" in mensaje
    assert "gemini-3.8-flash" in mensaje


def test_el_cuerpo_del_error_se_extrae_del_json():
    from core.llm import _detalle_del_error

    class RespuestaSimulada:
        def json(self):
            return {"error": {"message": "API key not valid",
                              "status": "INVALID_ARGUMENT"}}

    detalle = _detalle_del_error(RespuestaSimulada())
    assert "API key not valid" in detalle
    assert "INVALID_ARGUMENT" in detalle


def test_solo_se_reintenta_ante_un_rechazo_del_modelo():
    """
    El respaldo automatico debe activarse unicamente cuando el rechazo es
    atribuible al modelo. Una credencial invalida, un limite de uso alcanzado
    o un fallo de red afectan por igual a cualquier modelo, de modo que
    reintentar solo demoraria la respuesta.
    """
    from core.llm import _conviene_reintentar

    assert _conviene_reintentar(Exception("404 Not Found"))
    assert _conviene_reintentar(Exception("403 Forbidden"))
    assert not _conviene_reintentar(Exception("401 Unauthorized"))
    assert not _conviene_reintentar(Exception("429 quota exceeded"))
    assert not _conviene_reintentar(Exception("Connection timeout"))


def test_la_lista_de_respaldo_encabeza_con_versiones_estables():
    """
    Figurar en el listado del proveedor no implica acceso efectivo: los
    modelos mas recientes suelen requerir un nivel superior. La lista de
    respaldo comienza por versiones estables de generaciones anteriores.
    """
    from core.llm import MODELOS_ALTERNATIVOS

    candidatos = MODELOS_ALTERNATIVOS["google"]
    assert candidatos
    assert candidatos[0].startswith("gemini-2.5")


def test_sin_clave_no_se_verifica_el_modelo():
    from core.llm import verificar_modelo_operativo

    operativo, detalle = verificar_modelo_operativo("cualquiera")
    assert operativo is False
    assert "clave" in detalle.lower()
