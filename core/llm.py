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
}


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
    respuesta.raise_for_status()
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
    respuesta.raise_for_status()
    datos = respuesta.json()
    return "".join(b.get("text", "") for b in datos.get("content", []))


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
    respuesta.raise_for_status()
    datos = respuesta.json()
    return datos["choices"][0]["message"]["content"]


PROVEEDORES = {
    "google": _llamar_google,
    "anthropic": _llamar_anthropic,
    "openai": _llamar_openai,
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

    try:
        texto = funcion(prompt, modelo)
        if not (texto or "").strip():
            return RespuestaLLM("", modelo, MODO_SIN_CONEXION,
                                error="El proveedor devolvio una respuesta vacia.")
        return RespuestaLLM(texto, modelo, MODO_CONECTADO)
    except Exception as exc:
        return RespuestaLLM("", modelo, MODO_SIN_CONEXION,
                            error=_describir_error(exc, proveedor, modelo))


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

    if "401" in texto or "403" in texto or "api key" in minusculas or "unauthorized" in minusculas:
        return (f"La clave de API configurada para {proveedor} fue rechazada. "
                f"Verifique su validez en el archivo .env")

    if "429" in texto or "quota" in minusculas or "rate limit" in minusculas:
        return (f"Se alcanzo el limite de uso del proveedor {proveedor}. "
                f"Reintente en unos minutos.")

    return texto


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
