# -*- coding: utf-8 -*-
"""
Control de acceso al sistema.

Alcance y limites, que conviene declarar antes que el codigo.

Este modulo resuelve quien opera el sistema durante una sesion y deja esa
identidad asentada en cada correccion y en cada validacion. No constituye un
sistema de identidad institucional: no contempla altas y bajas delegadas,
politicas de vencimiento, segundo factor ni auditoria centralizada. Un
despliegue asistencial real debe integrarse al directorio de la institucion.

Lo que si se respeta es el minimo exigible a cualquier manejo de
credenciales: la contrasenia no se almacena ni se compara en texto plano. Se
guarda su derivacion mediante PBKDF2 con sal por usuario, y la comparacion se
realiza en tiempo constante para no filtrar informacion por la duracion de la
respuesta.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.config import RUTA_BASE_DATOS


ITERACIONES = 240_000
ALGORITMO = "sha256"
LONGITUD_SAL = 16

# Perfil de uso. No existe una figura administrativa: el sistema es una
# herramienta de apoyo documental y todos sus usuarios operan sobre los
# mismos casos. La distincion de perfiles corresponderia a un despliegue
# institucional, donde la define el directorio de la organizacion.
PERFIL = "lider_tumor_board"
ETIQUETA_PERFIL = "Lider de tumor board"


@dataclass(frozen=True)
class Usuario:
    """Identidad con la que se opera el sistema."""
    usuario: str
    nombre: str
    especialidad: str

    @property
    def etiqueta(self) -> str:
        return f"{self.nombre} ({self.especialidad})"


# ---------------------------------------------------------------------------
# Padron inicial
# ---------------------------------------------------------------------------

# Credenciales de puesta en marcha. Existen para que el sistema sea operable
# desde la primera ejecucion y para la demostracion del proyecto. En un
# despliegue real deben reemplazarse: su publicacion en el repositorio las
# vuelve inservibles como secreto, y asi debe entenderse.
PADRON_INICIAL = [
    {
        "usuario": "mrossi",
        "nombre": "Dra. Mariana Rossi",
        "especialidad": "Neuro-oncologia clinica",
        "clave": "tumorboard.2026",
    },
    {
        "usuario": "jlaguna",
        "nombre": "Dr. Julian Laguna",
        "especialidad": "Neurocirugia",
        "clave": "tumorboard.2026",
    },
    {
        "usuario": "cvera",
        "nombre": "Dra. Carolina Vera",
        "especialidad": "Anatomia patologica",
        "clave": "tumorboard.2026",
    },
]


def ruta_padron(ruta_base=None) -> Path:
    """Ubicacion del padron, junto a la base de datos del sistema."""
    base = Path(ruta_base) if ruta_base else RUTA_BASE_DATOS
    return base.parent / "usuarios.json"


# ---------------------------------------------------------------------------
# Derivacion y verificacion de la clave
# ---------------------------------------------------------------------------

def derivar(clave: str, sal: bytes, iteraciones: int = ITERACIONES) -> str:
    derivada = hashlib.pbkdf2_hmac(ALGORITMO, clave.encode("utf-8"), sal,
                                   iteraciones)
    return derivada.hex()


def componer_registro(usuario: str, nombre: str, especialidad: str,
                      clave: str) -> Dict:
    sal = os.urandom(LONGITUD_SAL)
    return {
        "usuario": usuario,
        "nombre": nombre,
        "especialidad": especialidad,
        "perfil": PERFIL,
        "algoritmo": ALGORITMO,
        "iteraciones": ITERACIONES,
        "sal": sal.hex(),
        "derivada": derivar(clave, sal),
    }


def verificar_clave(registro: Dict, clave: str) -> bool:
    """
    Compara la clave ofrecida contra la derivacion almacenada.

    La comparacion se realiza en tiempo constante: una comparacion corriente
    termina en el primer caracter discrepante, y la diferencia de duracion
    permite deducir el valor almacenado caracter por caracter.
    """
    try:
        sal = bytes.fromhex(registro["sal"])
        iteraciones = int(registro.get("iteraciones", ITERACIONES))
    except (KeyError, ValueError, TypeError):
        return False

    candidata = derivar(clave or "", sal, iteraciones)
    return hmac.compare_digest(candidata, registro.get("derivada", ""))


# ---------------------------------------------------------------------------
# Padron
# ---------------------------------------------------------------------------

def inicializar_padron(ruta_base=None) -> Path:
    """Crea el padron con las credenciales de puesta en marcha. Idempotente."""
    ruta = ruta_padron(ruta_base)
    if ruta.exists():
        return ruta

    ruta.parent.mkdir(parents=True, exist_ok=True)
    registros = [componer_registro(u["usuario"], u["nombre"],
                                   u["especialidad"], u["clave"])
                 for u in PADRON_INICIAL]
    ruta.write_text(json.dumps(registros, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


def leer_padron(ruta_base=None) -> List[Dict]:
    ruta = inicializar_padron(ruta_base)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return datos if isinstance(datos, list) else []


def listar_usuarios(ruta_base=None) -> List[Usuario]:
    return [Usuario(r["usuario"], r.get("nombre", r["usuario"]),
                    r.get("especialidad", ""))
            for r in leer_padron(ruta_base) if r.get("usuario")]


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------

# Derivacion de descarte, empleada cuando el usuario no existe. Sin ella el
# sistema responderia de inmediato ante un usuario inexistente y tras el
# calculo completo ante uno existente, revelando cuales son validos.
_SAL_DE_DESCARTE = os.urandom(LONGITUD_SAL)


def autenticar(usuario: str, clave: str, ruta_base=None) -> Optional[Usuario]:
    """
    Verifica las credenciales y devuelve el usuario, o None.

    No se informa cual de los dos datos resulto incorrecto: distinguirlos
    permitiria enumerar los usuarios validos del sistema.
    """
    nombre_usuario = (usuario or "").strip().lower()
    registro = next((r for r in leer_padron(ruta_base)
                     if r.get("usuario", "").lower() == nombre_usuario), None)

    if registro is None:
        derivar(clave or "", _SAL_DE_DESCARTE)
        return None

    if not verificar_clave(registro, clave):
        return None

    return Usuario(registro["usuario"], registro.get("nombre", ""),
                   registro.get("especialidad", ""))


def cambiar_clave(usuario: str, clave_actual: str, clave_nueva: str,
                  ruta_base=None) -> None:
    """Sustituye la clave de un usuario, previa verificacion de la vigente."""
    if len((clave_nueva or "").strip()) < 8:
        raise ValueError("La clave nueva debe tener al menos 8 caracteres.")

    registros = leer_padron(ruta_base)
    nombre_usuario = (usuario or "").strip().lower()

    for i, registro in enumerate(registros):
        if registro.get("usuario", "").lower() != nombre_usuario:
            continue
        if not verificar_clave(registro, clave_actual):
            raise ValueError("La clave actual no es correcta.")
        registros[i] = componer_registro(
            registro["usuario"], registro.get("nombre", ""),
            registro.get("especialidad", ""), clave_nueva)
        ruta_padron(ruta_base).write_text(
            json.dumps(registros, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return

    raise ValueError("El usuario no existe.")
