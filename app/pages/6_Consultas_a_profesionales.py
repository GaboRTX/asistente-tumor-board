"""
Pantalla de circulacion del caso a los profesionales de la junta.

Antes de que la junta delibere, cada seccion del resumen se somete a la
revision del especialista que corresponde. El circuito deja constancia de a
quien se consulto, que se le exhibio y que respondio.

El aviso por correo no transporta documentacion clinica. El sistema se
sostiene sobre la premisa de que la documentacion no abandona el equipo, y un
mensaje de correo queda depositado de manera persistente en casillas ajenas al
control institucional. El aviso anuncia la consulta; el contenido se consulta
aqui.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (barra_lateral, configurar_pagina, dato, encabezado, enlace_pagina, estado, requerir_resumen, requerir_sesion)
from core import consultas, correo, db


configurar_pagina("Consultas a profesionales")

# Streamlit admite dirigirse a cualquier pantalla por su direccion, de modo
# que proteger unicamente la inicial dejaria el resto accesible.
requerir_sesion()
encabezado(
    "Consultas a profesionales",
    "Circulacion del caso para revision por especialidad, previa a la "
    "deliberacion de la junta.",
)
barra_lateral()

e = requerir_resumen()
if e is None:
    st.stop()

caso_id = e["caso_id"]
identificador = e["identificador"]
resumen = e["resumen"]

circuito = consultas.estado_del_circuito(caso_id)

# ---------------------------------------------------------------------------
# Estado del circuito
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric("Consultas", circuito["total"])
c2.metric("Pendientes", circuito["pendientes"])
c3.metric("Conformes", circuito["conformes"])
c4.metric("Con observaciones", circuito["con_observaciones"])

if circuito["total"] == 0:
    st.info(
        "Todavia no se registraron consultas para este caso. La ausencia de "
        "objeciones no equivale a conformidad: mientras no haya consultas, el "
        "caso no puede presentarse como revisado."
    )
elif circuito["habilitado_para_decision"]:
    st.success(
        "No restan respuestas pendientes ni observaciones sin atender. La "
        "decision corresponde a la junta; el sistema unicamente constata el "
        "estado del circuito."
    )
else:
    faltantes = []
    if circuito["pendientes"]:
        faltantes.append(f"{circuito['pendientes']} respuesta(s) pendiente(s)")
    if circuito["con_observaciones"]:
        faltantes.append(
            f"{circuito['con_observaciones']} observacion(es) sin atender")
    st.warning("Circuito incompleto: " + "; ".join(faltantes) + ".")

if not correo.configurado():
    st.caption(
        "Sin servidor de correo configurado. Las consultas se registran "
        "igualmente y el aviso queda disponible para su envio por el medio "
        "que el servicio disponga."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Alta de una consulta
# ---------------------------------------------------------------------------

st.markdown("### Nueva consulta")
st.caption(
    "Cada consulta se dirige a un unico profesional. Para consultar a varios, "
    "registre una consulta por cada uno."
)

opciones = list(consultas.ESPECIALIDADES.keys()) + ["otra"]

with st.form("alta_consulta", clear_on_submit=True):
    col1, col2 = st.columns(2)
    nombre = col1.text_input("Nombre del profesional", key="consulta_nombre")
    correo_destino = col2.text_input(
        "Correo electronico", key="consulta_correo",
        help="Una unica direccion. No se admiten copias.")

    col3, col4 = st.columns(2)
    clave_especialidad = col3.selectbox(
        "Especialidad", opciones,
        format_func=lambda k: ("Otra (revision integral)" if k == "otra"
                               else consultas.ESPECIALIDADES[k][0]),
        key="consulta_especialidad")
    especialidad_libre = col4.text_input(
        "Especificar especialidad", key="consulta_especialidad_libre",
        disabled=clave_especialidad != "otra",
        help="Se habilita al seleccionar 'Otra'.")

    instrucciones = st.text_area(
        "Indicaciones para el profesional (opcional)",
        key="consulta_instrucciones",
        help="Se incorpora al aviso. No consigne aqui datos clinicos.")

    enviado = st.form_submit_button("Registrar consulta y enviar aviso",
                                    type="primary")

if enviado:
    especialidad = (especialidad_libre if clave_especialidad == "otra"
                    else clave_especialidad)
    try:
        consulta = consultas.crear_consulta(
            caso_id=caso_id, identificador_caso=identificador,
            resumen=resumen, nombre=nombre, especialidad=especialidad,
            correo=correo_destino,
            generacion_id=(e.get("generacion_id")),
        )
    except consultas.DestinatarioInvalido as exc:
        st.error(str(exc))
    except ValueError as exc:
        st.error(str(exc))
    else:
        resultado = correo.enviar_aviso(consulta, instrucciones)
        db.registrar_envio_consulta(consulta["id"], resultado.enviado,
                                    resultado.detalle)
        if resultado.enviado:
            st.success(f"Consulta registrada. {resultado.detalle}")
        else:
            st.warning(
                f"Consulta registrada bajo el codigo {consulta['token']}, "
                f"pero el aviso no pudo enviarse. {resultado.detalle}")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# Consultas registradas
# ---------------------------------------------------------------------------

st.markdown("### Consultas registradas")

if not circuito["consultas"]:
    st.caption("Sin consultas registradas para este caso.")

ICONOS = {
    consultas.PENDIENTE: "Pendiente",
    consultas.CONFORME: "Conforme",
    consultas.CON_OBSERVACIONES: "Con observaciones",
}

for consulta in circuito["consultas"]:
    etiqueta_estado = consultas.ETIQUETAS_ESTADO.get(consulta["estado"],
                                                     consulta["estado"])
    titulo = (f"{consulta['nombre']} "
              f"({consultas.etiqueta_de_especialidad(consulta['especialidad'])}) "
              f"- {etiqueta_estado}")

    with st.expander(titulo, expanded=consulta["estado"] == consultas.PENDIENTE):
        col1, col2 = st.columns(2)
        with col1:
            dato("Correo", consulta["correo"])
            dato("Codigo de la consulta", consulta["token"])
        with col2:
            dato("Estado", etiqueta_estado)
            dato("Consultada el", consulta["fecha_creacion"])

        if not consulta["aviso_enviado"]:
            st.warning(f"Aviso no enviado. {consulta['detalle_envio']}")
            if st.button("Reintentar el envio del aviso",
                         key=f"reenviar_{consulta['id']}"):
                resultado = correo.enviar_aviso(consulta)
                db.registrar_envio_consulta(consulta["id"], resultado.enviado,
                                            resultado.detalle)
                st.rerun()

        # --- Vista exhibida al profesional ---------------------------------
        st.markdown("#### Caso exhibido al profesional")
        st.caption(
            "Se conserva lo efectivamente exhibido al momento de la consulta. "
            "Una respuesta solo significa algo respecto del contenido sobre el "
            "cual se emitio, y el resumen puede regenerarse despues."
        )

        instantanea = consulta["instantanea"]
        for campo in instantanea.get("campos", []):
            if campo.get("resaltado"):
                st.markdown(
                    f"**{campo['etiqueta']}** &nbsp; "
                    f"<span style='font-size:0.75rem;padding:0.1rem 0.45rem;"
                    f"border:1px solid currentColor;border-radius:0.6rem;"
                    f"opacity:0.8'>seccion a revisar</span>",
                    unsafe_allow_html=True)
                st.info(campo["contenido"])
            else:
                st.markdown(f"**{campo['etiqueta']}**")
                st.write(campo["contenido"])

        # --- Respuesta ------------------------------------------------------
        st.markdown("#### Respuesta del profesional")

        if consulta["estado"] == consultas.PENDIENTE:
            with st.form(f"respuesta_{consulta['id']}"):
                decision = st.radio(
                    "Dictamen", consultas.ESTADOS_RESPUESTA,
                    format_func=lambda v: consultas.ETIQUETAS_ESTADO[v],
                    key=f"decision_{consulta['id']}", horizontal=True)
                observacion = st.text_area(
                    "Observacion",
                    key=f"observacion_{consulta['id']}",
                    help="Obligatoria cuando el dictamen consigna "
                         "observaciones.")
                if st.form_submit_button("Registrar respuesta"):
                    try:
                        consultas.registrar_respuesta(
                            consulta["id"], decision, observacion)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
        else:
            dato("Dictamen", etiqueta_estado)
            dato("Respondida el", consulta["fecha_respuesta"] or "")
            if consulta["observacion"]:
                st.markdown("**Observacion**")
                st.warning(consulta["observacion"])


st.markdown("---")
enlace_pagina("pages/4_Reporte_final.py", "Continuar al reporte final")
