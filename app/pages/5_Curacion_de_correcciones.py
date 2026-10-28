"""
Pantalla de curacion de correcciones.

Constituye el control de seguridad del mecanismo de aprendizaje. Una
correccion incorporada de manera automatica se aplicaria a todos los casos
posteriores, de modo que un error de registro se propagaria sin que nadie lo
advirtiera. La validacion previa no es un tramite administrativo sino la
condicion que hace admisible el ciclo de retroalimentacion en un dominio
clinico.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (barra_lateral, configurar_pagina, encabezado, estado)
from core import db, feedback


configurar_pagina("Curacion de correcciones")
encabezado(
    "Curacion de correcciones",
    "Las correcciones influyen sobre casos futuros unicamente despues de ser "
    "validadas.",
)
barra_lateral()

e = estado()
est = feedback.estadisticas()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Correcciones registradas", est["total_feedback"])
c2.metric("Pendientes", est["correcciones_pendientes"])
c3.metric("Activas", est["correcciones_activas"])
c4.metric("Desactivadas", est["correcciones_desactivadas"])

st.info(
    "Una correccion activa se recupera durante la generacion de casos "
    "posteriores y se incorpora al contexto del modelo. Desactivarla surte "
    "efecto de inmediato, sin necesidad de reprocesar caso alguno."
)

autor = e.get("autor", "").strip()
if not autor:
    st.warning(
        "Indique su nombre en el panel lateral para poder validar o "
        "desactivar correcciones. La autoria queda registrada."
    )

pendientes, activas, desactivadas = st.tabs(
    ["Pendientes de validacion", "Activas", "Desactivadas"]
)


def _mostrar(correccion, acciones):
    """Presenta una correccion junto con su contexto de origen."""
    detalle = next(
        (f for f in db.listar_feedback()
         if f["id"] == correccion["feedback_id"]), None
    )

    with st.container(border=True):
        st.markdown(f"**Correccion {correccion['id']}** "
                    f"&nbsp; campo: `{correccion['campo']}`")
        st.write(correccion["regla"])

        if detalle:
            with st.expander("Ver el caso y la correccion de origen"):
                caso = db.obtener_caso(detalle["caso_id"])
                st.caption(
                    f"Caso: {caso['identificador'] if caso else detalle['caso_id']} | "
                    f"Registrada por: {detalle.get('autor') or 'no indicado'} | "
                    f"Fecha: {detalle['fecha'][:16]}"
                )
                st.caption(
                    f"Tipo de error: "
                    f"{feedback.TIPOS_ERROR.get(detalle['tipo_error'], detalle['tipo_error'])}"
                )
                izquierda, derecha = st.columns(2)
                with izquierda:
                    st.markdown("**Contenido generado**")
                    st.text(detalle["valor_generado"][:600] or "(vacio)")
                with derecha:
                    st.markdown("**Contenido corregido**")
                    st.text(detalle["valor_corregido"][:600])
                if detalle.get("comentario"):
                    st.caption(f"Observacion: {detalle['comentario']}")

        if correccion.get("autor_validacion"):
            st.caption(
                f"Ultima accion: {correccion['autor_validacion']} | "
                f"{(correccion.get('fecha_validacion') or '')[:16]}"
            )

        acciones(correccion)


with pendientes:
    lista = db.listar_correcciones("pendiente")
    if not lista:
        st.success("No hay correcciones pendientes de validacion.")
    else:
        st.caption(
            f"{len(lista)} correccion(es) a la espera de revision. Ninguna "
            f"influye sobre las generaciones actuales."
        )

    def acciones_pendiente(c):
        a, b = st.columns(2)
        with a:
            if st.button("Validar e incorporar", key=f"val_{c['id']}",
                         type="primary", disabled=not autor,
                         use_container_width=True):
                feedback.validar_correccion(c["id"], autor)
                st.rerun()
        with b:
            if st.button("Desestimar", key=f"des_{c['id']}",
                         disabled=not autor, use_container_width=True):
                feedback.desactivar_correccion(c["id"], autor)
                st.rerun()

    for c in lista:
        _mostrar(c, acciones_pendiente)


with activas:
    lista = db.listar_correcciones("activa")
    if not lista:
        st.info(
            "No hay correcciones activas. El sistema genera los resumenes sin "
            "incorporar conocimiento previo del servicio."
        )
    else:
        st.caption(
            f"{len(lista)} correccion(es) influyen actualmente sobre la "
            f"generacion de nuevos casos."
        )

    def acciones_activa(c):
        if st.button("Desactivar", key=f"off_{c['id']}", disabled=not autor):
            feedback.desactivar_correccion(c["id"], autor)
            st.rerun()

    for c in lista:
        _mostrar(c, acciones_activa)


with desactivadas:
    lista = db.listar_correcciones("desactivada")
    if not lista:
        st.info("No hay correcciones desactivadas.")
    else:
        st.caption(
            f"{len(lista)} correccion(es) fuera de uso. Se conservan como "
            f"registro y pueden reactivarse."
        )

    def acciones_desactivada(c):
        if st.button("Reactivar", key=f"on_{c['id']}", disabled=not autor):
            feedback.validar_correccion(c["id"], autor)
            st.rerun()

    for c in lista:
        _mostrar(c, acciones_desactivada)
