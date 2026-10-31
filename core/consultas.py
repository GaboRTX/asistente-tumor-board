"""
Circulacion de un caso a un profesional y registro de su respuesta.

Antes de que la junta adopte una decision, el caso se somete a la revision de
los profesionales cuya especialidad corresponde a cada seccion del resumen: el
patologo revisa los hallazgos anatomopatologicos, el imagenologo los
imagenologicos. El circuito deja constancia de a quien se consulto, que se le
exhibio y que respondio.

Dos decisiones de disenio gobiernan este modulo.

La primera: el aviso por correo no transporta contenido clinico. El sistema se
sostiene sobre la premisa de que la documentacion no abandona el equipo, y un
mensaje de correo atraviesa servidores de terceros y queda depositado en las
casillas de emisor y destinatario. El aviso anuncia la consulta; el contenido
se consulta en el sistema.

La segunda: cada consulta tiene un unico destinatario, el profesional
registrado. No se admiten copias ni destinatarios adicionales. Una revision
responde a una persona identificada, y la difusion a terceros no declarados
carece de justificacion asistencial.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core import db
from core.config import CAMPOS_RESUMEN


# ---------------------------------------------------------------------------
# Estados del circuito
# ---------------------------------------------------------------------------

PENDIENTE = "pendiente"
CONFORME = "conforme"
CON_OBSERVACIONES = "con_observaciones"

ESTADOS_RESPUESTA = (CONFORME, CON_OBSERVACIONES)
ESTADOS = (PENDIENTE,) + ESTADOS_RESPUESTA

ETIQUETAS_ESTADO = {
    PENDIENTE: "Pendiente de respuesta",
    CONFORME: "Conforme",
    CON_OBSERVACIONES: "Con observaciones",
}


# ---------------------------------------------------------------------------
# Especialidades y su campo de revision
# ---------------------------------------------------------------------------

# La especialidad determina que seccion del resumen se resalta. El profesional
# recibe el caso completo, dado que una seccion aislada no admite lectura
# clinica, pero se le senala aquella sobre la cual se requiere su dictamen.
ESPECIALIDADES = {
    "anatomia_patologica": ("Anatomia patologica", "hallazgos_patologia"),
    "diagnostico_por_imagenes": ("Diagnostico por imagenes", "hallazgos_imagenes"),
    "neurocirugia": ("Neurocirugia", "tratamientos_previos"),
    "oncologia_clinica": ("Oncologia clinica", "tratamientos_previos"),
    "biologia_molecular": ("Biologia molecular", "perfil_molecular"),
    "neurologia": ("Neurologia", "datos_clinicos"),
}


def campo_de_especialidad(especialidad: str) -> str:
    """Devuelve la clave del campo que revisa una especialidad."""
    entrada = ESPECIALIDADES.get(especialidad)
    if entrada:
        return entrada[1]
    # Una especialidad no contemplada revisa el caso en su conjunto. No
    # corresponde rechazar la consulta por ello: la nomina de especialidades
    # no puede anticiparse por completo.
    return ""


def etiqueta_de_especialidad(especialidad: str) -> str:
    entrada = ESPECIALIDADES.get(especialidad)
    return entrada[0] if entrada else especialidad


# ---------------------------------------------------------------------------
# Validacion del destinatario
# ---------------------------------------------------------------------------

# Deliberadamente restrictivo. No pretende abarcar la totalidad de la norma
# sino rechazar lo que con certeza no es una direccion utilizable, y en
# particular lo que encubre mas de un destinatario.
PATRON_CORREO = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")

# Caracteres que permiten inyectar cabeceras adicionales en un mensaje de
# correo. Una direccion que los contenga se rechaza sin excepcion.
CARACTERES_PROHIBIDOS = ("\n", "\r", "\t", "\0")

SEPARADORES_DE_DESTINATARIOS = (",", ";", "<", ">")


class DestinatarioInvalido(ValueError):
    """La direccion no es utilizable o encubre mas de un destinatario."""


def validar_destinatario(correo: str) -> str:
    """
    Valida que la direccion corresponda a un unico destinatario.

    Devuelve la direccion normalizada. Lanza DestinatarioInvalido en caso
    contrario.
    """
    if not isinstance(correo, str):
        raise DestinatarioInvalido("La direccion de correo es obligatoria.")

    bruto = correo.strip()
    if not bruto:
        raise DestinatarioInvalido("La direccion de correo es obligatoria.")

    for caracter in CARACTERES_PROHIBIDOS:
        if caracter in bruto:
            raise DestinatarioInvalido(
                "La direccion contiene caracteres de control, que permitirian "
                "incorporar destinatarios no declarados al mensaje.")

    for separador in SEPARADORES_DE_DESTINATARIOS:
        if separador in bruto:
            raise DestinatarioInvalido(
                "Cada consulta admite un unico destinatario. Registre una "
                "consulta por profesional.")

    if not PATRON_CORREO.match(bruto):
        raise DestinatarioInvalido(
            f"La direccion '{bruto}' no tiene un formato valido.")

    return bruto


def _texto_obligatorio(valor: str, campo: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        raise ValueError(f"El campo '{campo}' es obligatorio.")
    for caracter in CARACTERES_PROHIBIDOS:
        if caracter in texto:
            raise ValueError(
                f"El campo '{campo}' contiene caracteres de control.")
    return texto


# ---------------------------------------------------------------------------
# Token de la consulta
# ---------------------------------------------------------------------------

def generar_token(identificador_caso: str, especialidad: str) -> str:
    """
    Compone un identificador legible y unico para la consulta.

    Se incorpora un sufijo aleatorio para que dos consultas a la misma
    especialidad sobre el mismo caso no colisionen.
    """
    caso = _simplificar(identificador_caso) or "CASO"
    area = _simplificar(especialidad)[:12] or "GENERAL"
    return f"TB-{caso}-{area}-{secrets.token_hex(3)}"


def _simplificar(texto: str) -> str:
    """Reduce el texto a mayusculas sin acentos ni separadores."""
    normalizado = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in normalizado if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]", "", sin_acentos).upper()


# ---------------------------------------------------------------------------
# Vista entregada al profesional
# ---------------------------------------------------------------------------

@dataclass
class VistaProfesional:
    """Lo que se exhibe al profesional consultado."""
    identificador_caso: str
    nombre: str
    especialidad: str
    campo_interes: str
    campos: List[Dict[str, Any]] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    @property
    def campo_resaltado(self) -> Optional[Dict[str, Any]]:
        return next((c for c in self.campos if c.get("resaltado")), None)

    def como_dict(self) -> Dict[str, Any]:
        return {
            "identificador_caso": self.identificador_caso,
            "nombre": self.nombre,
            "especialidad": self.especialidad,
            "campo_interes": self.campo_interes,
            "campos": self.campos,
            "advertencias": self.advertencias,
        }


def armar_vista(resumen: Dict[str, Any], identificador_caso: str,
                nombre: str, especialidad: str,
                campo_interes: Optional[str] = None) -> VistaProfesional:
    """
    Arma el caso completo con la seccion de interes senalada.

    El profesional recibe la totalidad del resumen: una seccion aislada no
    admite lectura clinica. Lo que distingue a su vista es el senalamiento de
    aquella sobre la cual se requiere su dictamen.
    """
    clave_interes = campo_interes
    if clave_interes is None:
        clave_interes = campo_de_especialidad(especialidad)

    etiquetas = dict(CAMPOS_RESUMEN)

    campos = []
    for campo in resumen.get("campos", []):
        clave = campo.get("clave", "")
        campos.append({
            "clave": clave,
            "etiqueta": campo.get("etiqueta") or etiquetas.get(clave, clave),
            "contenido": campo.get("contenido", ""),
            "fuentes": campo.get("fuentes", []),
            "resaltado": bool(clave_interes) and clave == clave_interes,
        })

    return VistaProfesional(
        identificador_caso=identificador_caso,
        nombre=nombre,
        especialidad=especialidad,
        campo_interes=clave_interes,
        campos=campos,
        advertencias=list(resumen.get("advertencias") or []),
    )


# ---------------------------------------------------------------------------
# Alta y respuesta
# ---------------------------------------------------------------------------

def crear_consulta(caso_id: int, identificador_caso: str, resumen: Dict[str, Any],
                   nombre: str, especialidad: str, correo: str,
                   campo_interes: Optional[str] = None,
                   generacion_id: Optional[int] = None,
                   ruta=None) -> Dict[str, Any]:
    """
    Registra una consulta y devuelve el registro creado.

    No envia el aviso: el envio es una operacion separada que puede fallar sin
    que la consulta deje de existir. Una consulta registrada y no notificada
    es un estado legitimo y visible; una consulta perdida por un fallo de
    correo, no.
    """
    nombre = _texto_obligatorio(nombre, "nombre del profesional")
    especialidad = _texto_obligatorio(especialidad, "especialidad")
    correo = validar_destinatario(correo)

    vista = armar_vista(resumen, identificador_caso, nombre, especialidad,
                        campo_interes)
    token = generar_token(identificador_caso, especialidad)

    consulta_id = db.crear_consulta(
        caso_id=caso_id, token=token, nombre=nombre, especialidad=especialidad,
        correo=correo, campo_interes=vista.campo_interes,
        instantanea=vista.como_dict(), generacion_id=generacion_id, ruta=ruta)

    return db.obtener_consulta(consulta_id, ruta=ruta)


def registrar_respuesta(consulta_id: int, estado: str, observacion: str = "",
                        ruta=None) -> Dict[str, Any]:
    """
    Asienta la respuesta del profesional.

    Una respuesta con observaciones exige texto. Admitir una observacion vacia
    produciria un caso marcado como objetado sin constancia de la objecion, y
    la junta no tendria sobre que deliberar.
    """
    if estado not in ESTADOS_RESPUESTA:
        raise ValueError(
            f"Estado de respuesta no valido: '{estado}'. "
            f"Valores admitidos: {', '.join(ESTADOS_RESPUESTA)}.")

    observacion = (observacion or "").strip()
    if estado == CON_OBSERVACIONES and not observacion:
        raise ValueError(
            "Una respuesta con observaciones requiere el detalle de la "
            "observacion.")

    existente = db.obtener_consulta(consulta_id, ruta=ruta)
    if existente is None:
        raise ValueError(f"No existe la consulta {consulta_id}.")

    db.registrar_respuesta_consulta(consulta_id, estado, observacion, ruta=ruta)
    return db.obtener_consulta(consulta_id, ruta=ruta)


# ---------------------------------------------------------------------------
# Estado del circuito
# ---------------------------------------------------------------------------

def estado_del_circuito(caso_id: int, ruta=None) -> Dict[str, Any]:
    """
    Resume la situacion de las consultas de un caso.

    'habilitado_para_decision' no constituye una autorizacion sino la
    constatacion de que no restan respuestas pendientes ni observaciones sin
    atender. La decision corresponde a la junta.
    """
    consultas = db.listar_consultas(caso_id, ruta=ruta)
    pendientes = [c for c in consultas if c["estado"] == PENDIENTE]
    observadas = [c for c in consultas if c["estado"] == CON_OBSERVACIONES]
    conformes = [c for c in consultas if c["estado"] == CONFORME]

    return {
        "total": len(consultas),
        "pendientes": len(pendientes),
        "conformes": len(conformes),
        "con_observaciones": len(observadas),
        "sin_aviso": len([c for c in consultas if not c["aviso_enviado"]]),
        "habilitado_para_decision": bool(consultas) and not pendientes
                                    and not observadas,
        "consultas": consultas,
    }
