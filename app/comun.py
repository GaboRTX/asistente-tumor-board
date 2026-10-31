"""
Utilidades compartidas por las pantallas de la interfaz.

El estado de la sesion se concentra en un unico diccionario, de acuerdo con
el modelo de ejecucion de Streamlit, que reejecuta el script completo ante
cada interaccion. Dispersar el estado en claves independientes es la
principal fuente de inconsistencias en aplicaciones de este tipo.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from core import acceso, db
from core.config import TIPOS_DOCUMENTO


CLAVE_ESTADO = "estado_app"


def inicializar_app() -> None:
    """Inicializa la base de datos y el estado de sesion. Es idempotente."""
    db.inicializar()
    if CLAVE_ESTADO not in st.session_state:
        st.session_state[CLAVE_ESTADO] = {
            "caso_id": None,
            "identificador": None,
            "documentos_origen": {},
            "informes_lectura": [],
            "fragmentos": None,
            "resumen": None,
            "generacion_id": None,
            "ensayos": None,
            "origen_ensayos": "",
            "resumen_ensayos": None,
            "motor_recuperacion": "",
            "degradacion": "",
            "autor": "",
        }


def estado() -> Dict[str, Any]:
    inicializar_app()
    return st.session_state[CLAVE_ESTADO]


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------

CLAVE_SESION = "usuario_sesion"


def usuario_actual():
    """Devuelve el usuario de la sesion, o None."""
    return st.session_state.get(CLAVE_SESION)


def cerrar_sesion() -> None:
    st.session_state.pop(CLAVE_SESION, None)
    st.session_state.pop(CLAVE_ESTADO, None)


def requerir_sesion():
    """
    Exige una sesion iniciada. Presenta el formulario de ingreso y detiene la
    ejecucion de la pantalla mientras no haya usuario autenticado.

    Se invoca desde todas las pantallas: Streamlit permite dirigirse a
    cualquiera por su direccion, de modo que proteger unicamente la inicial
    dejaria el resto accesible.
    """
    inicializar_app()
    acceso.inicializar_padron()

    usuario = usuario_actual()
    if usuario is not None:
        return usuario

    _formulario_de_ingreso()
    st.stop()


def _formulario_de_ingreso() -> None:
    st.markdown("## Ingreso al sistema")
    st.caption(
        "Asistente de preparacion de casos para junta de neuro-oncologia. "
        "La identidad con la que ingrese quedara asentada en las "
        "correcciones y validaciones que registre."
    )

    with st.form("ingreso"):
        nombre_usuario = st.text_input("Usuario")
        clave = st.text_input("Clave", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            usuario = acceso.autenticar(nombre_usuario, clave)
            if usuario is None:
                # No se distingue cual de los dos datos fallo: hacerlo
                # permitiria enumerar los usuarios validos.
                st.error("Usuario o clave incorrectos.")
            else:
                st.session_state[CLAVE_SESION] = usuario
                estado()["autor"] = usuario.etiqueta
                st.rerun()

    with st.expander("Credenciales de demostracion"):
        st.caption(
            "El sistema se distribuye con tres credenciales de puesta en "
            "marcha, publicadas en el repositorio. Por esa razon no "
            "constituyen un secreto y deben sustituirse en cualquier "
            "despliegue real."
        )
        for registro in acceso.PADRON_INICIAL:
            st.markdown(
                f"- **{registro['usuario']}** / `{registro['clave']}` "
                f"- {registro['nombre']}, {registro['especialidad']}")


def fijar(**valores) -> None:
    estado().update(valores)


def limpiar_caso() -> None:
    """Descarta el caso en curso, conservando las preferencias de sesion."""
    autor = estado().get("autor", "")
    st.session_state[CLAVE_ESTADO] = {
        "caso_id": None, "identificador": None, "documentos_origen": {},
        "informes_lectura": [], "fragmentos": None,
        "resumen": None, "generacion_id": None, "ensayos": None,
        "origen_ensayos": "", "resumen_ensayos": None,
        "motor_recuperacion": "", "degradacion": "", "autor": autor,
    }


def configurar_pagina(titulo: str, icono: str = "") -> None:
    st.set_page_config(page_title=f"{titulo} | Asistente de junta",
                       layout="wide", initial_sidebar_state="expanded")
    inicializar_app()


def encabezado(titulo: str, descripcion: str = "") -> None:
    st.title(titulo)
    if descripcion:
        st.caption(descripcion)


def aviso_clinico() -> None:
    """Aviso permanente sobre el alcance de la herramienta."""
    st.info(
        "Esta herramienta asiste en la preparacion documental del caso. "
        "No emite diagnosticos ni indicaciones terapeuticas. La decision "
        "clinica corresponde al equipo medico tratante."
    )


def barra_lateral() -> None:
    """Informacion de contexto comun a todas las pantallas."""
    e = estado()
    with st.sidebar:
        st.markdown("### Caso en curso")
        if e.get("identificador"):
            st.success(f"**{e['identificador']}**")
            if e.get("fragmentos") is not None:
                st.caption(f"{len(e['fragmentos'])} fragmentos documentales")
            if e.get("resumen"):
                modo = e["resumen"].get("modo", "")
                etiqueta = ("Modelo de lenguaje" if modo == "conectado"
                            else "Reglas deterministas")
                st.caption(f"Resumen generado: {etiqueta}")
        else:
            st.warning("Ningun caso cargado")
            st.caption("Comience en la pantalla de carga de caso.")

        if e.get("motor_recuperacion"):
            st.markdown("### Motor de recuperacion")
            st.caption(e["motor_recuperacion"])

        if e.get("degradacion"):
            st.markdown("### Estado del sistema")
            st.warning(e["degradacion"])

        st.markdown("---")
        st.markdown("### Profesional")
        usuario = usuario_actual()
        if usuario is not None:
            st.markdown(f"**{usuario.nombre}**")
            st.caption(usuario.especialidad)
            st.caption(f"Usuario: {usuario.usuario}")
            if e.get("autor") != usuario.etiqueta:
                fijar(autor=usuario.etiqueta)
        else:
            st.caption("Sin sesion iniciada.")

        st.markdown("---")
        if e.get("identificador") and st.button("Cerrar caso en curso",
                                                use_container_width=True):
            limpiar_caso()
            st.rerun()

        if usuario is not None and st.button("Cerrar sesion",
                                             use_container_width=True):
            cerrar_sesion()
            st.rerun()


def requerir_caso() -> Optional[Dict[str, Any]]:
    """
    Verifica que haya un caso cargado. Devuelve el estado o detiene la
    ejecucion de la pantalla con un mensaje orientativo.
    """
    e = estado()
    if not e.get("identificador"):
        st.warning(
            "No hay ningun caso cargado. Dirijase a la pantalla "
            "**Carga de caso** para comenzar."
        )
        st.stop()
    return e


def requerir_resumen() -> Optional[Dict[str, Any]]:
    e = requerir_caso()
    if not e.get("resumen"):
        st.warning(
            "El caso aun no fue procesado. Dirijase a la pantalla "
            "**Carga de caso** y ejecute el procesamiento."
        )
        st.stop()
    return e


def etiqueta_documento(tipo: str) -> str:
    return TIPOS_DOCUMENTO.get(tipo, tipo)


def enlace_pagina(ruta: str, etiqueta: str) -> None:
    """
    Enlace a otra pantalla, tolerante al modo de ejecucion.

    La resolucion de rutas de `st.page_link` depende del archivo utilizado
    como punto de entrada, por lo que puede fallar segun como se inicie la
    aplicacion. Ante ese caso se presenta una indicacion textual equivalente,
    de modo que la navegacion nunca quede interrumpida por un error.
    """
    try:
        st.page_link(ruta, label=etiqueta, icon=":material/arrow_forward:")
    except Exception:
        nombre = Path(ruta).stem
        partes = nombre.split("_", 1)
        legible = (partes[1] if len(partes) > 1 else nombre).replace("_", " ")
        st.caption(f"{etiqueta}: seleccione **{legible}** en el menu lateral.")


def dato(etiqueta: str, valor: Any) -> None:
    """
    Muestra un par etiqueta-valor con el texto integro.

    Reemplaza a st.metric, que recorta el valor con puntos suspensivos cuando
    excede el ancho de la columna. En un contexto clinico el recorte es
    inadmisible: "delecion hom..." no permite distinguir una delecion presente
    de una ausente, que es precisamente el dato que determina la conducta.
    """
    texto = "" if valor is None else str(valor)
    st.markdown(
        f"""<div style="margin-bottom:0.85rem">
  <div style="font-size:0.78rem;opacity:0.65;line-height:1.3">{_escapar(etiqueta)}</div>
  <div style="font-size:1.45rem;line-height:1.25;overflow-wrap:anywhere">{_escapar(texto)}</div>
</div>""",
        unsafe_allow_html=True,
    )


def _escapar(texto: str) -> str:
    """Neutraliza el marcado HTML presente en el contenido documental."""
    import html

    return html.escape(str(texto))
