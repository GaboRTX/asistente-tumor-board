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


def test_sin_clave_no_se_verifica_el_modelo():
    from core.llm import verificar_modelo_operativo

    operativo, detalle = verificar_modelo_operativo("cualquiera")
    assert operativo is False
    assert "clave" in detalle.lower()


def test_se_extrae_el_modelo_que_el_proveedor_sugiere():
    """
    Ante un identificador retirado, el proveedor indica en el mensaje de
    error cual corresponde utilizar. Aprovechar esa indicacion resulta mas
    confiable que cualquier orden de preferencia fijado de antemano, que
    envejece con cada renovacion de la linea de modelos.
    """
    from core.llm import _modelo_sugerido

    mensaje = ("404 Not Found. This model models/gemini-2.5-flash-lite is no "
               "longer available to new users. Please update your code to use "
               "models/gemini-3.5-flash-lite for the new version.")

    assert _modelo_sugerido(Exception(mensaje)) == "gemini-3.5-flash-lite"
    assert _modelo_sugerido(Exception("403 Forbidden")) is None


def test_la_lista_de_respaldo_prioriza_las_generaciones_recientes():
    """
    Regresion. Una version preliminar ordenaba la lista de respaldo
    comenzando por los modelos mas antiguos, bajo el supuesto de que serian
    los mas accesibles. Los proveedores retiran precisamente esos
    identificadores para las cuentas nuevas.
    """
    from core.llm import MODELOS_ALTERNATIVOS

    candidatos = MODELOS_ALTERNATIVOS["google"]
    assert not candidatos[0].startswith("gemini-2."), (
        "la lista no debe encabezarse con una generacion retirada")


def test_los_proveedores_compatibles_comparten_implementacion():
    """
    Varios proveedores exponen la interfaz de formato OpenAI y se distinguen
    unicamente por su direccion base, de modo que una misma implementacion
    los cubre.
    """
    from core.llm import DIRECCIONES_COMPATIBLES, PROVEEDORES

    for proveedor in ("groq", "cerebras", "openrouter"):
        assert proveedor in PROVEEDORES
        assert proveedor in DIRECCIONES_COMPATIBLES
        assert DIRECCIONES_COMPATIBLES[proveedor].startswith("https://")


def test_cada_proveedor_declara_su_modelo_por_defecto():
    from core.llm import MODELOS_POR_DEFECTO, PROVEEDORES

    for proveedor in PROVEEDORES:
        assert MODELOS_POR_DEFECTO.get(proveedor), (
            f"{proveedor} no declara modelo por defecto")


def test_el_proveedor_local_no_exige_credencial():
    """
    La ejecucion local corre en el propio equipo y no media autenticacion, de
    modo que la ausencia de clave no debe degradar el sistema al modo
    determinista cuando se selecciono ese proveedor.
    """
    import importlib
    import core.llm as llm

    original_proveedor = llm.PROVEEDOR_LLM
    original_clave = llm.CLAVE_API_LLM
    try:
        llm.PROVEEDOR_LLM = "ollama"
        llm.CLAVE_API_LLM = ""
        proveedor, modelo = llm.detectar_proveedor()
        assert proveedor == "ollama", (
            "sin clave, el proveedor local debe seguir seleccionado")
        assert modelo, "debe resolverse un modelo por defecto"
    finally:
        llm.PROVEEDOR_LLM = original_proveedor
        llm.CLAVE_API_LLM = original_clave
        importlib.reload(llm)


def test_el_proveedor_local_apunta_al_propio_equipo():
    """
    La direccion del proveedor local debe resolver en el equipo donde corre el
    sistema. De ello depende el argumento de confidencialidad: la
    documentacion no abandona la institucion.
    """
    from core.llm import DIRECCIONES_COMPATIBLES, PROVEEDORES

    assert "ollama" in PROVEEDORES
    direccion = DIRECCIONES_COMPATIBLES["ollama"]
    assert "127.0.0.1" in direccion or "localhost" in direccion


def test_la_ausencia_de_clave_no_emite_cabecera_de_autorizacion(monkeypatch):
    """
    Al operar contra el servicio local no corresponde enviar una cabecera de
    autorizacion vacia, que algunos servidores rechazan.
    """
    import requests

    import core.llm as llm

    capturadas = {}

    class RespuestaFalsa:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "resumen"}}]}

        text = ""

    def post_falso(url, headers=None, json=None, timeout=None):
        capturadas["headers"] = headers or {}
        capturadas["url"] = url
        return RespuestaFalsa()

    monkeypatch.setattr(llm, "CLAVE_API_LLM", "")
    monkeypatch.setattr(requests, "post", post_falso)

    llm._llamar_compatible("prompt de prueba", "llama3.2:3b", "ollama")

    assert "Authorization" not in capturadas["headers"]
    assert "127.0.0.1" in capturadas["url"]


def test_se_descartan_los_remanentes_de_oracion():
    """
    Regresion. El solapamiento entre fragmentos deja el comienzo de algunos
    fragmentos en el interior de una oracion. Ese remanente llegaba al
    resumen: CASO-001 exhibia "de gadolinio se observa realce heterogeneo".

    La oracion completa esta disponible en el fragmento contiguo, de modo que
    descartar el remanente no implica perdida de informacion.
    """
    from core.rag import _es_oracion_truncada

    assert _es_oracion_truncada("de gadolinio se observa realce heterogeneo.")
    assert _es_oracion_truncada("tracion de gadolinio.")
    assert not _es_oracion_truncada(
        "Tras la administracion de gadolinio se observa realce.")
    assert not _es_oracion_truncada("42 x 31 mm en el corte axial.")


def test_ningun_caso_de_demostracion_exhibe_remanentes():
    """
    Verificacion de extremo a extremo sobre el conjunto completo: ninguna
    oracion del resumen determinista debe comenzar en minuscula.
    """
    from pathlib import Path

    from core.ingesta import cargar_caso_demo, procesar_documentos
    from core.rag import generar_resumen

    directorios = sorted(Path("data/casos_demo").glob("CASO-*"))
    assert directorios, "no se hallaron casos de demostracion"

    for directorio in directorios:
        documentos = cargar_caso_demo(directorio)
        fragmentos = procesar_documentos(directorio.name, documentos)
        resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
        for campo in resultado.campos:
            for oracion in campo.contenido.split(". "):
                oracion = oracion.strip()
                if not oracion:
                    continue
                assert oracion[0].isupper() or oracion[0].isdigit(), (
                    f"{directorio.name} / {campo.clave}: la oracion "
                    f"'{oracion[:60]}' comienza en minuscula")


def test_el_servicio_local_detenido_se_informa_como_tal():
    """
    El modo de falla mas probable en ejecucion local es que Ollama no se
    encuentre corriendo. Informarlo como un fallo generico de conexion
    obligaria a diagnosticar lo que el sistema ya sabe.
    """
    from core.llm import _describir_error

    error = Exception(
        "HTTPConnectionPool(host='localhost', port=11434): Max retries "
        "exceeded with url: /v1/chat/completions (Caused by "
        "NewConnectionError('Connection refused'))")
    mensaje = _describir_error(error, "ollama", "llama3.2:3b")

    assert "ollama" in mensaje.lower()
    assert "11434" in mensaje or "ejecucion" in mensaje.lower()


def test_el_modelo_no_descargado_indica_el_comando_de_descarga():
    from core.llm import _describir_error

    mensaje = _describir_error(
        Exception("404 Client Error: Not Found"), "ollama", "qwen2.5:7b")

    assert "ollama pull qwen2.5:7b" in mensaje


def test_la_ejecucion_local_no_encadena_modelos_ausentes():
    """
    Ante un modelo no descargado no corresponde probar otros identificadores:
    tampoco estarian descargados, y el encadenamiento solo demoraria el
    mensaje que indica la descarga necesaria.
    """
    from core.llm import _conviene_reintentar

    assert not _conviene_reintentar(
        Exception("404 Not Found: http://localhost:11434/v1/chat/completions"))
    # El comportamiento remoto se conserva
    assert _conviene_reintentar(
        Exception("404 models/gemini-x is not found for API version v1beta"))


def test_el_agotamiento_de_la_espera_no_se_confunde_con_servicio_caido():
    """
    Regresion. El texto de la excepcion por espera agotada contiene
    "HTTPConnectionPool", de modo que satisfacia la condicion de fallo de
    conexion y el sistema informaba que Ollama no estaba corriendo cuando en
    realidad estaba respondiendo, solo que con lentitud.

    El diagnostico equivocado es peor que la ausencia de diagnostico: envia a
    reiniciar un servicio que funciona.
    """
    from core.llm import _describir_error

    mensaje = _describir_error(
        Exception("HTTPConnectionPool(host='127.0.0.1', port=11434): "
                  "Read timed out. (read timeout=300)"),
        "ollama", "llama3.2:3b")

    assert "no respondio dentro" in mensaje
    assert "ejecucion" not in mensaje.lower() or "memoria" in mensaje


def test_la_ejecucion_local_admite_una_espera_mayor():
    """
    La generacion corre sobre el procesador del equipo, de modo que la espera
    admisible excede holgadamente la de un proveedor remoto.
    """
    from core.config import TIMEOUT_LOCAL, TIMEOUT_RED
    from core.llm import _timeout_de

    assert _timeout_de("ollama") == TIMEOUT_LOCAL
    assert _timeout_de("groq") == TIMEOUT_RED
    assert TIMEOUT_LOCAL >= 10 * TIMEOUT_RED


def test_la_direccion_local_no_depende_de_la_resolucion_de_localhost():
    """
    En Windows 'localhost' puede resolver primero a IPv6, donde el servicio no
    escucha. Consignar la direccion IPv4 evita esa clase de fallo.
    """
    from core.llm import DIRECCIONES_COMPATIBLES

    assert DIRECCIONES_COMPATIBLES["ollama"].startswith("http://127.0.0.1:")
