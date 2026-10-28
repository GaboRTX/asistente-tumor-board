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

MODELOS_POR_DEFECTO = {
    "google": "gemini-2.0-flash",
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
        return RespuestaLLM("", modelo, MODO_SIN_CONEXION, error=str(exc))


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
