"""
Ciclo de retroalimentacion y aprendizaje del sistema.

El sistema no reentrena el modelo de lenguaje. Incorpora el conocimiento
aportado por los profesionales modificando aquello que el modelo observa en
el momento de generar, no sus parametros internos.

Justificacion de este enfoque
-----------------------------
El ajuste fino (fine-tuning) del modelo fue evaluado y descartado por tres
razones. Primero, requiere un volumen de ejemplos muy superior al que un
servicio asistencial produce en el plazo de este proyecto. Segundo, el
conocimiento incorporado por ajuste fino no es trazable: el modelo aplica lo
aprendido sin que pueda identificarse el caso de origen. Tercero, y de mayor
peso en un dominio clinico, un error incorporado por ajuste fino no puede
revertirse sin reentrenar.

El mecanismo implementado aqui conserva, en cambio, la trazabilidad completa:
cada correccion tiene un autor, una fecha y un caso de origen, puede
desactivarse en cualquier momento con efecto inmediato, y el sistema informa
que correcciones influyeron sobre cada salida generada.

Curacion previa
---------------
Ninguna correccion influye sobre casos futuros hasta que es validada. Una
correccion erronea aplicada automaticamente se propagaria a todos los casos
siguientes, por lo que la validacion humana no es un tramite administrativo
sino un control de seguridad del propio mecanismo de aprendizaje.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core import db
from core.config import CAMPOS_RESUMEN
from core.vectorizacion import IndiceVectorial


TIPOS_ERROR = {
    "dato_faltante": "Dato presente en la documentacion que el sistema omitio",
    "dato_incorrecto": "Dato consignado con un valor distinto al documentado",
    "interpretacion_erronea": "Lectura incorrecta del contenido documental",
    "dato_no_documentado": "Dato afirmado sin respaldo en la documentacion",
    "redaccion": "Contenido correcto con redaccion inadecuada",
}

ETIQUETAS_CAMPO = dict(CAMPOS_RESUMEN)


def redactar_regla(campo: str, valor_generado: str, valor_corregido: str,
                   tipo_error: str, comentario: str = "") -> str:
    """
    Convierte una correccion puntual en una regla textual reutilizable.

    La regla se redacta en terminos generales, de modo que pueda recuperarse
    ante casos distintos del que la origino, pero sin afirmar datos clinicos
    del caso original, que no son trasladables a otro paciente.
    """
    etiqueta = ETIQUETAS_CAMPO.get(campo, campo)
    generado = (valor_generado or "").strip()
    corregido = (valor_corregido or "").strip()

    if tipo_error == "dato_faltante":
        return (f"En el campo '{etiqueta}', el sistema omitio informacion que "
                f"constaba en la documentacion. Debe consignarse el dato cuando "
                f"este presente, con el nivel de detalle del ejemplo corregido: "
                f"\"{corregido}\".")

    if tipo_error == "dato_incorrecto":
        return (f"En el campo '{etiqueta}', el sistema consigno \"{generado}\" "
                f"cuando correspondia \"{corregido}\". Verificar la lectura de "
                f"este dato contra la fuente documental antes de consignarlo.")

    if tipo_error == "interpretacion_erronea":
        return (f"En el campo '{etiqueta}', la expresion documental fue "
                f"interpretada erroneamente como \"{generado}\", cuando su "
                f"lectura correcta es \"{corregido}\". Atender a esta "
                f"distincion de redaccion.")

    if tipo_error == "dato_no_documentado":
        return (f"En el campo '{etiqueta}', el sistema afirmo \"{generado}\" sin "
                f"respaldo documental. No debe completarse este campo por "
                f"inferencia: si el dato no consta, declararlo como no "
                f"documentado.")

    if tipo_error == "redaccion":
        return (f"En el campo '{etiqueta}', ajustar la redaccion al estilo del "
                f"ejemplo corregido: \"{corregido}\".")

    base = (f"En el campo '{etiqueta}', corregir \"{generado}\" por "
            f"\"{corregido}\".")
    return base + (f" Observacion del profesional: {comentario}" if comentario else "")


def registrar_correccion(generacion_id: int, caso_id: int, campo: str,
                         valor_generado: str, valor_corregido: str,
                         tipo_error: str, comentario: str = "",
                         autor: str = "", ruta=None) -> Dict[str, int]:
    """
    Registra una correccion del profesional y crea la regla asociada.

    La regla queda en estado pendiente: no influye sobre ninguna generacion
    hasta que sea validada explicitamente.
    """
    if tipo_error not in TIPOS_ERROR:
        raise ValueError(f"Tipo de error no reconocido: {tipo_error}")

    feedback_id = db.registrar_feedback(
        generacion_id=generacion_id, caso_id=caso_id, campo=campo,
        valor_generado=valor_generado, valor_corregido=valor_corregido,
        tipo_error=tipo_error, comentario=comentario, autor=autor, ruta=ruta,
    )

    regla = redactar_regla(campo, valor_generado, valor_corregido,
                           tipo_error, comentario)
    correccion_id = db.crear_correccion(feedback_id, campo, regla, ruta=ruta)

    return {"feedback_id": feedback_id, "correccion_id": correccion_id}


def validar_correccion(correccion_id: int, autor: str, ruta=None) -> None:
    """Activa una correccion, habilitandola para influir en casos futuros."""
    db.cambiar_estado_correccion(correccion_id, "activa", autor, ruta=ruta)


def desactivar_correccion(correccion_id: int, autor: str, ruta=None) -> None:
    """
    Desactiva una correccion con efecto inmediato.

    No se requiere reprocesar ningun caso: la correccion deja de recuperarse
    en la siguiente generacion.
    """
    db.cambiar_estado_correccion(correccion_id, "desactivada", autor, ruta=ruta)


def construir_indice_correcciones(ruta=None,
                                  motor: Optional[str] = None
                                  ) -> IndiceVectorial:
    """
    Construye el indice vectorial de las correcciones activas.

    Este indice se mantiene separado del indice documental del caso: las
    correcciones son conocimiento acumulado del servicio, mientras que los
    fragmentos documentales pertenecen a un paciente concreto. Mezclarlos
    permitiria que el contenido de un caso influyera sobre otro, lo que no
    es admisible.
    """
    activas = db.listar_correcciones("activa", ruta=ruta)
    indice = IndiceVectorial(motor=motor)

    textos = [c["regla"] for c in activas]
    metadatos = [
        {
            "id": c["id"],
            "campo": c["campo"],
            "regla": c["regla"],
            "autor_validacion": c.get("autor_validacion", ""),
            "fecha_validacion": c.get("fecha_validacion", ""),
        }
        for c in activas
    ]

    indice.indexar(textos, metadatos)
    return indice


def estadisticas(ruta=None) -> Dict:
    """Resumen del estado del ciclo de retroalimentacion."""
    todas = db.listar_correcciones(ruta=ruta)
    feedback = db.listar_feedback(ruta=ruta)

    por_tipo: Dict[str, int] = {}
    por_campo: Dict[str, int] = {}
    for f in feedback:
        por_tipo[f["tipo_error"]] = por_tipo.get(f["tipo_error"], 0) + 1
        etiqueta = ETIQUETAS_CAMPO.get(f["campo"], f["campo"])
        por_campo[etiqueta] = por_campo.get(etiqueta, 0) + 1

    return {
        "total_feedback": len(feedback),
        "correcciones_pendientes": sum(1 for c in todas if c["estado"] == "pendiente"),
        "correcciones_activas": sum(1 for c in todas if c["estado"] == "activa"),
        "correcciones_desactivadas": sum(1 for c in todas if c["estado"] == "desactivada"),
        "por_tipo_error": por_tipo,
        "por_campo": por_campo,
    }
