"""
Envio del aviso de consulta a un profesional.

El aviso NO transporta contenido clinico. El sistema se sostiene sobre la
premisa de que la documentacion no abandona el equipo, y un mensaje de correo
atraviesa servidores de terceros y queda depositado de manera persistente en
las casillas de emisor y destinatario, fuera de todo control institucional.
Incorporar alli el estudio anularia esa premisa.

El mensaje anuncia que hay una consulta, identifica el caso por su codigo
interno y remite al sistema. El contenido se consulta donde reside.

Cada mensaje admite un unico destinatario, el profesional registrado. No se
contemplan copias.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Dict, Optional

from core.config import (
    SMTP_CLAVE,
    SMTP_INSTITUCION,
    SMTP_PUERTO,
    SMTP_REMITENTE,
    SMTP_SERVIDOR,
    SMTP_USUARIO,
    TIMEOUT_SMTP,
)
from core.consultas import (
    CARACTERES_PROHIBIDOS,
    etiqueta_de_especialidad,
    validar_destinatario,
)


@dataclass
class ResultadoEnvio:
    enviado: bool
    detalle: str


def configurado() -> bool:
    """Indica si hay servidor de correo configurado."""
    return bool(SMTP_SERVIDOR and SMTP_REMITENTE)


def motivo_no_configurado() -> str:
    faltantes = []
    if not SMTP_SERVIDOR:
        faltantes.append("SMTP_SERVIDOR")
    if not SMTP_REMITENTE:
        faltantes.append("SMTP_REMITENTE o SMTP_USUARIO")
    return ("Sin servidor de correo configurado. Complete "
            + " y ".join(faltantes) + " en el archivo .env. "
            "El circuito de consulta funciona igualmente: el aviso puede "
            "entregarse por el medio que el servicio disponga.")


# ---------------------------------------------------------------------------
# Composicion del aviso
# ---------------------------------------------------------------------------

def componer_asunto(consulta: Dict) -> str:
    return (f"[{consulta['token']}] Consulta de revision "
            f"- caso {consulta['instantanea'].get('identificador_caso', '')}")


def componer_cuerpo(consulta: Dict, instrucciones: str = "") -> str:
    """
    Redacta el aviso.

    Deliberadamente no se incorpora ningun dato del paciente ni del resumen:
    ni edad, ni diagnostico, ni marcadores. Unicamente el codigo interno del
    caso, que fuera del sistema no identifica a nadie.
    """
    especialidad = etiqueta_de_especialidad(consulta["especialidad"])
    identificador = consulta["instantanea"].get("identificador_caso", "")

    lineas = [
        f"Estimado/a {consulta['nombre']}:",
        "",
        f"Se solicita su revision, en calidad de {especialidad}, del caso "
        f"registrado bajo el codigo {identificador} en el sistema de "
        f"preparacion de casos para junta de neuro-oncologia.",
        "",
        "Por razones de confidencialidad este mensaje no incluye "
        "documentacion clinica. El caso se encuentra disponible en el "
        "sistema, donde podra consultarlo y dejar asentada su conformidad o "
        "las observaciones que estime corresponder.",
        "",
        f"Codigo de la consulta: {consulta['token']}",
    ]

    if instrucciones.strip():
        lineas += ["", instrucciones.strip()]

    if SMTP_INSTITUCION:
        lineas += ["", "--", SMTP_INSTITUCION]

    lineas += [
        "",
        "Mensaje generado automaticamente. El sistema constituye una "
        "herramienta de apoyo documental y no emite recomendaciones "
        "terapeuticas.",
    ]
    return "\n".join(lineas)


def _verificar_sin_caracteres_de_control(valor: str, campo: str) -> None:
    for caracter in CARACTERES_PROHIBIDOS:
        if caracter in valor:
            raise ValueError(
                f"El campo '{campo}' contiene caracteres de control, que "
                f"permitirian incorporar cabeceras al mensaje.")


def construir_mensaje(consulta: Dict, instrucciones: str = "") -> EmailMessage:
    """
    Arma el mensaje con un unico destinatario.

    El asunto se depura de caracteres de control antes de asignarse: el token
    y el identificador del caso se componen en el sistema, pero la verificacion
    no depende de ese supuesto.
    """
    destinatario = validar_destinatario(consulta["correo"])

    asunto = componer_asunto(consulta).replace("\n", " ").replace("\r", " ")
    _verificar_sin_caracteres_de_control(asunto, "asunto")

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = SMTP_REMITENTE
    mensaje["To"] = destinatario
    mensaje.set_content(componer_cuerpo(consulta, instrucciones))
    return mensaje


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------

def enviar_aviso(consulta: Dict, instrucciones: str = "",
                 transporte=None) -> ResultadoEnvio:
    """
    Envia el aviso al profesional registrado.

    'transporte' permite sustituir el cliente SMTP durante las pruebas. El
    fallo no se propaga: la consulta ya esta registrada y el circuito debe
    poder continuar informando el problema, no interrumpirse.
    """
    try:
        mensaje = construir_mensaje(consulta, instrucciones)
    except ValueError as exc:
        return ResultadoEnvio(False, str(exc))

    if transporte is None and not configurado():
        return ResultadoEnvio(False, motivo_no_configurado())

    try:
        if transporte is not None:
            transporte(mensaje)
        else:
            contexto = ssl.create_default_context()
            with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PUERTO,
                              timeout=TIMEOUT_SMTP) as servidor:
                servidor.ehlo()
                servidor.starttls(context=contexto)
                servidor.ehlo()
                if SMTP_USUARIO:
                    servidor.login(SMTP_USUARIO, SMTP_CLAVE)
                servidor.send_message(mensaje)
    except smtplib.SMTPAuthenticationError:
        return ResultadoEnvio(
            False, "El servidor de correo rechazo las credenciales. Si utiliza "
                   "Gmail, SMTP_CLAVE debe ser una contrasenia de aplicacion y "
                   "no la contrasenia de la cuenta.")
    except smtplib.SMTPRecipientsRefused:
        return ResultadoEnvio(
            False, f"El servidor rechazo la direccion {consulta['correo']}.")
    except (smtplib.SMTPException, OSError) as exc:
        return ResultadoEnvio(
            False, f"No fue posible enviar el aviso: {type(exc).__name__}: {exc}")

    return ResultadoEnvio(True, f"Aviso enviado a {consulta['correo']}.")
