"""
Capa de acceso al modelo de lenguaje.

El modulo abstrae el proveedor concreto (Google, Anthropic u OpenAI) detras
de una interfaz unica, y provee ademas un modo de operacion sin conexion.

Sobre el modo sin conexion
--------------------------
Cuando no hay clave de API configurada o la llamada de red falla, el sistema
no se interrumpe: genera el resumen mediante reglas deterministas sobre los
fragmentos recuperados (ver `core/perfil_molecular.py` y las funciones de
extraccion de este modulo).

Esta decision persigue dos objetivos:

  1. Disponibilidad. La herramienta sigue siendo utilizable ante una caida
     del proveedor o una interrupcion de conectividad, situacion esperable
     en un entorno hospitalario.
  2. Verificabilidad. La salida determinista es reproducible y auditable, lo
     que permite contrastar contra ella la salida del modelo generativo.

En ambos modos rige la misma regla: ningun dato se afirma si no puede
atribuirse a un fragmento concreto de la documentacion aportada.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.config import (
    CLAVE_API_LLM,
    MODELO_LLM,
    PROVEEDOR_LLM,
    TEXTO_SIN_DATO,
    TIMEOUT_RED,
)


MODO_CONECTADO = "conectado"
MODO_SIN_CONEXION = "sin_conexion"

# Modelo utilizado cuando no se especifica uno en la configuracion.
#
# Los proveedores renuevan su linea de modelos con frecuencia y retiran los
# identificadores antiguos, de modo que un valor fijo en el codigo queda
# desactualizado y la llamada falla con un error 404. Por ese motivo el
# sistema provee `listar_modelos_disponibles`, que consulta al proveedor que
# modelos admite la clave configurada, y el script de verificacion del
# entorno informa el resultado.
MODELOS_POR_DEFECTO = {
    "google": "gemini-3.5-flash-lite",
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "cerebras": "llama-3.3-70b",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
}

# Modelos a los que el sistema recurre cuando el configurado no resulta
# accesible, ordenados de mayor a menor disponibilidad.
#
# Los proveedores retiran los identificadores ANTIGUOS para las cuentas
# nuevas y derivan su uso hacia las generaciones recientes, de modo que un
# modelo estable de hace varios meses puede resultar inaccesible mientras
# uno posterior si lo esta. La lista refleja ese orden.
#
# Cuando el proveedor indica en el mensaje de error que identificador debe
# utilizarse en reemplazo, el sistema lo antepone a esta lista: una
# indicacion explicita del proveedor es mas confiable que cualquier orden
# fijado de antemano, que envejece con cada renovacion de la linea.
MODELOS_ALTERNATIVOS = {
    "google": [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
    ],
    "anthropic": ["claude-sonnet-4-5", "claude-haiku-4-5"],
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant",
             "qwen-2.5-32b"],
    "cerebras": ["llama-3.3-70b", "llama3.1-8b"],
    "openrouter": ["meta-llama/llama-3.3-70b-instruct:free"],
}

# Los proveedores suelen consignar en el mensaje de error el identificador
# que corresponde utilizar en reemplazo del retirado.
PATRON_MODELO_SUGERIDO = re.compile(
    "use .{0,24}models/([a-z0-9][a-z0-9.-]+)", re.IGNORECASE)


def _modelo_sugerido(exc: Exception) -> Optional[str]:
    """Extrae el identificador que el proveedor propone en reemplazo."""
    hallazgo = PATRON_MODELO_SUGERIDO.search(str(exc))
    return hallazgo.group(1) if hallazgo else None


@dataclass
class RespuestaLLM:
    texto: str
    modelo: str
    modo: str
    error: str = ""

    @property
    def exitosa(self) -> bool:
        return not self.error


# ---------------------------------------------------------------------------
# Deteccion del proveedor
# ---------------------------------------------------------------------------

def detectar_proveedor() -> Tuple[str, str]:
    """
    Devuelve (proveedor, modelo) segun la configuracion disponible.

    Si no hay clave de API configurada, devuelve el proveedor 'offline'.
    """
    if not CLAVE_API_LLM:
        return "offline", "reglas-deterministas"

    proveedor = PROVEEDOR_LLM
    if proveedor in ("", "auto"):
        proveedor = "google"

    if proveedor == "offline":
        return "offline", "reglas-deterministas"

    modelo = MODELO_LLM or MODELOS_POR_DEFECTO.get(proveedor, "")
    return proveedor, modelo


# ---------------------------------------------------------------------------
# Llamada al proveedor
# ---------------------------------------------------------------------------

def _detalle_del_error(respuesta) -> str:
    """
    Extrae el motivo que el proveedor consigna en el cuerpo de la respuesta.

    Ante un rechazo, los proveedores devuelven el codigo de estado en la
    cabecera y la explicacion en el cuerpo. Descartar el cuerpo deja al
    usuario frente a un numero sin indicacion de la causa, cuando es
    precisamente alli donde se informa si la interfaz no esta habilitada, si
    la clave tiene restricciones o si el modelo requiere otro nivel de acceso.
    """
    try:
        datos = respuesta.json()
    except Exception:
        texto = (respuesta.text or "").strip()
        return texto[:300] if texto else ""

    error = datos.get("error", datos)
    partes = []
    if isinstance(error, dict):
        if error.get("message"):
            partes.append(str(error["message"]))
        if error.get("status"):
            partes.append(f"[{error['status']}]")
    return " ".join(partes)[:400]


def _verificar_respuesta(respuesta) -> None:
    """Eleva el error del proveedor incorporando el motivo que lo acompania."""
    if respuesta.status_code < 400:
        return
    detalle = _detalle_del_error(respuesta)
    mensaje = f"{respuesta.status_code} {respuesta.reason}"
    if detalle:
        mensaje += f". {detalle}"
    raise RuntimeError(mensaje)


def _llamar_google(prompt: str, modelo: str) -> str:
    import requests

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{modelo}:generateContent")
    respuesta = requests.post(
        url,
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": CLAVE_API_LLM},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}},
        timeout=TIMEOUT_RED,
    )
    _verificar_respuesta(respuesta)
    datos = respuesta.json()
    return datos["candidates"][0]["content"]["parts"][0]["text"]


def _llamar_anthropic(prompt: str, modelo: str) -> str:
    import requests

    respuesta = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json",
                 "x-api-key": CLAVE_API_LLM,
                 "anthropic-version": "2023-06-01"},
        json={"model": modelo, "max_tokens": 2048, "temperature": 0.1,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT_RED,
    )
    _verificar_respuesta(respuesta)
    datos = respuesta.json()
    return "".join(b.get("text", "") for b in datos.get("content", []))


# Varios proveedores exponen una interfaz compatible con el formato de
# OpenAI, de modo que una misma implementacion los cubre a todos. Se
# distinguen unicamente por su direccion base.
#
# Los niveles gratuitos que no requieren medio de pago se financian, segun
# los propios proveedores, mediante el aprovechamiento de las consultas
# recibidas. Esta circunstancia resulta relevante en un dominio clinico: no
# corresponde dirigir documentacion de pacientes a un servicio que la
# incorpore a sus procesos de entrenamiento, aun cuando el sistema solo
# transmita fragmentos. Para los casos sinteticos de demostracion no
# presenta inconveniente, pero debe considerarse antes de cualquier uso con
# documentacion real.
DIRECCIONES_COMPATIBLES = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


def _llamar_compatible(prompt: str, modelo: str, proveedor: str) -> str:
    """Invoca un proveedor que expone la interfaz de formato OpenAI."""
    import requests

    base = DIRECCIONES_COMPATIBLES.get(proveedor,
                                       DIRECCIONES_COMPATIBLES["openai"])
    respuesta = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {CLAVE_API_LLM}"},
        json={"model": modelo, "temperature": 0.1,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT_RED,
    )
    _verificar_respuesta(respuesta)
    datos = respuesta.json()
    return datos["choices"][0]["message"]["content"]


def _llamar_groq(prompt: str, modelo: str) -> str:
    return _llamar_compatible(prompt, modelo, "groq")


def _llamar_cerebras(prompt: str, modelo: str) -> str:
    return _llamar_compatible(prompt, modelo, "cerebras")


def _llamar_openrouter(prompt: str, modelo: str) -> str:
    return _llamar_compatible(prompt, modelo, "openrouter")


def _llamar_openai(prompt: str, modelo: str) -> str:
    import requests

    respuesta = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {CLAVE_API_LLM}"},
        json={"model": modelo, "temperature": 0.1,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT_RED,
    )
    _verificar_respuesta(respuesta)
    datos = respuesta.json()
    return datos["choices"][0]["message"]["content"]


PROVEEDORES = {
    "google": _llamar_google,
    "anthropic": _llamar_anthropic,
    "openai": _llamar_openai,
    "groq": _llamar_groq,
    "cerebras": _llamar_cerebras,
    "openrouter": _llamar_openrouter,
}


def consultar(prompt: str) -> RespuestaLLM:
    """
    Envia un prompt al proveedor configurado.

    Ante cualquier error de red, autenticacion o formato, devuelve una
    RespuestaLLM con el error registrado y modo sin conexion, de modo que la
    capa superior pueda aplicar el procedimiento determinista de respaldo.
    """
    proveedor, modelo = detectar_proveedor()

    if proveedor == "offline":
        return RespuestaLLM("", modelo, MODO_SIN_CONEXION,
                            error="Sin clave de API configurada.")

    funcion = PROVEEDORES.get(proveedor)
    if funcion is None:
        return RespuestaLLM("", modelo, MODO_SIN_CONEXION,
                            error=f"Proveedor no reconocido: {proveedor}")

    # Si en esta sesion ya se identifico un modelo operativo distinto del
    # configurado, se utiliza directamente en lugar de repetir la busqueda.
    if not MODELO_LLM and proveedor in _MODELO_EFECTIVO:
        modelo = _MODELO_EFECTIVO[proveedor]

    pendientes = [modelo] + [m for m in MODELOS_ALTERNATIVOS.get(proveedor, [])
                             if m != modelo]

    primer_error = None
    intentados = set()

    while pendientes:
        candidato = pendientes.pop(0)
        if candidato in intentados:
            continue
        intentados.add(candidato)

        try:
            texto = funcion(prompt, candidato)
            if not (texto or "").strip():
                raise RuntimeError("El proveedor devolvio una respuesta vacia.")

            if candidato != modelo:
                _MODELO_EFECTIVO[proveedor] = candidato
            return RespuestaLLM(texto, candidato, MODO_CONECTADO)

        except Exception as exc:
            if primer_error is None:
                primer_error = (exc, candidato)
            if not _conviene_reintentar(exc):
                break

            # El proveedor puede indicar el identificador de reemplazo en el
            # propio mensaje de error. Esa indicacion es mas confiable que el
            # orden fijado de antemano, por lo que se antepone.
            sugerido = _modelo_sugerido(exc)
            if sugerido and sugerido not in intentados:
                pendientes.insert(0, sugerido)

    exc, fallido = primer_error
    return RespuestaLLM("", fallido, MODO_SIN_CONEXION,
                        error=_describir_error(exc, proveedor, fallido))


# Modelo que efectivamente respondio, por proveedor. Permite evitar la
# busqueda de alternativas en las solicitudes siguientes de la misma sesion.
_MODELO_EFECTIVO: Dict[str, str] = {}


def _conviene_reintentar(exc: Exception) -> bool:
    """
    Indica si corresponde probar con otro modelo.

    Solo se reintenta ante un rechazo atribuible al modelo, es decir cuando
    no existe o cuando el nivel de acceso no lo alcanza. Un fallo de red, una
    credencial invalida o un limite de uso alcanzado afectan por igual a
    cualquier modelo, de modo que reintentar unicamente demoraria la
    respuesta sin posibilidad de exito.
    """
    texto = str(exc).lower()
    if "401" in texto or "api key" in texto or "unauthorized" in texto:
        return False
    if "429" in texto or "quota" in texto or "rate limit" in texto:
        return False
    return ("404" in texto or "not found" in texto
            or "403" in texto or "permission" in texto or "forbidden" in texto)


def _describir_error(exc: Exception, proveedor: str, modelo: str) -> str:
    """
    Traduce el error del proveedor a un mensaje accionable.

    Un codigo 404 sobre el endpoint de generacion indica, casi siempre, que
    el identificador del modelo no existe o no se encuentra habilitado para
    la clave configurada, y no que el servicio no este disponible. Informarlo
    como un fallo generico de conexion deja al usuario sin saber que el
    problema se resuelve cambiando una linea de configuracion.
    """
    texto = str(exc)
    minusculas = texto.lower()

    if "404" in texto or "not found" in minusculas:
        return (f"El modelo '{modelo}' no esta disponible para la clave "
                f"configurada. Los proveedores retiran identificadores de "
                f"modelo con frecuencia. Ejecute "
                f"'python scripts/verificar_entorno.py --modelos' para "
                f"conocer los modelos habilitados y consigne uno de ellos en "
                f"MODELO_LLM dentro del archivo .env")

    if "403" in texto or "permission" in minusculas or "forbidden" in minusculas:
        return (f"El proveedor {proveedor} rechazo la solicitud sobre el "
                f"modelo '{modelo}' por falta de permisos. Motivo informado: "
                f"{texto}. Verifique que la interfaz de programacion se "
                f"encuentre habilitada en el proyecto, que la clave no tenga "
                f"restricciones y que el modelo este disponible para su nivel "
                f"de acceso. Ejecute "
                f"'python scripts/verificar_entorno.py --modelos' para "
                f"conocer los modelos efectivamente habilitados.")

    if "401" in texto or "api key" in minusculas or "unauthorized" in minusculas:
        return (f"La clave de API configurada para {proveedor} fue rechazada. "
                f"Motivo informado: {texto}. Verifique su validez en el "
                f"archivo .env")

    if "429" in texto or "quota" in minusculas or "rate limit" in minusculas:
        return (f"Se alcanzo el limite de uso del proveedor {proveedor}. "
                f"Reintente en unos minutos.")

    return texto


def verificar_modelo_operativo(modelo: str) -> Tuple[bool, str]:
    """
    Comprueba que el modelo responda efectivamente a una solicitud.

    La enumeracion de modelos que ofrece el proveedor no constituye garantia
    de acceso: un modelo puede figurar en el listado y rechazar la solicitud
    por falta de permisos. La unica verificacion concluyente consiste en
    emitir una solicitud minima y observar el resultado.
    """
    proveedor, _ = detectar_proveedor()
    if proveedor == "offline":
        return False, "No hay clave de API configurada."

    funcion = PROVEEDORES.get(proveedor)
    if funcion is None:
        return False, f"Proveedor no reconocido: {proveedor}"

    try:
        respuesta = funcion("Responde unicamente: ok", modelo)
        if (respuesta or "").strip():
            return True, "operativo"
        return False, "El proveedor devolvio una respuesta vacia."
    except Exception as exc:
        return False, str(exc)[:160]


def listar_modelos_disponibles() -> Tuple[List[str], str]:
    """
    Consulta al proveedor configurado que modelos admite la clave en uso.

    Devuelve (lista de identificadores, mensaje). La lista se encuentra vacia
    cuando el proveedor no admite la consulta o cuando esta no puede
    completarse; en ese caso el mensaje explica el motivo.

    Solo el proveedor Google expone un endpoint publico de enumeracion de
    modelos. Para los restantes se remite a su documentacion.
    """
    proveedor, _modelo = detectar_proveedor()

    if proveedor == "offline":
        return [], "No hay clave de API configurada en el archivo .env"

    if proveedor != "google":
        return [], (f"El proveedor {proveedor} no expone un listado publico "
                    f"de modelos. Consulte su documentacion oficial.")

    try:
        import requests
        respuesta = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": CLAVE_API_LLM},
            timeout=TIMEOUT_RED,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except Exception as exc:
        return [], f"No fue posible consultar los modelos disponibles: {exc}"

    modelos = []
    for entrada in datos.get("models", []):
        nombre = entrada.get("name", "").replace("models/", "")
        metodos = entrada.get("supportedGenerationMethods", [])
        if nombre and (not metodos or "generateContent" in metodos):
            modelos.append(nombre)

    if not modelos:
        return [], ("El proveedor no informo modelos habilitados para "
                    "generacion de contenido.")

    return sorted(modelos), f"{len(modelos)} modelos habilitados."


# ---------------------------------------------------------------------------
# Utilidades de parseo
# ---------------------------------------------------------------------------

def extraer_json(texto: str) -> Optional[Dict]:
    """
    Extrae el primer objeto JSON valido presente en la respuesta del modelo.

    Los modelos suelen envolver el JSON en delimitadores de bloque de codigo
    o precederlo de texto explicativo, por lo que no puede asumirse que la
    respuesta sea JSON puro.
    """
    if not texto:
        return None

    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
    limpio = re.sub(r"\s*```$", "", limpio)

    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass

    # Busqueda del primer objeto balanceado
    inicio = limpio.find("{")
    if inicio == -1:
        return None
    profundidad = 0
    for i in range(inicio, len(limpio)):
        if limpio[i] == "{":
            profundidad += 1
        elif limpio[i] == "}":
            profundidad -= 1
            if profundidad == 0:
                try:
                    return json.loads(limpio[inicio:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
