"""
Pantalla de borrado del historico.

Existe por una necesidad concreta: dejar el sistema en condiciones de una
demostracion limpia, sin arrastrar los casos de las pruebas previas.

El borrado es irreversible y no admite deshacer, de modo que la pantalla
exhibe primero que se va a borrar y exige una confirmacion escrita. Un boton
de borrado total sin constancia previa invita al accidente.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (barra_lateral, configurar_pagina, dato, encabezado,
                       estado, limpiar_caso, requerir_sesion)
from core import db


configurar_pagina("Administracion del historico")

# Streamlit admite dirigirse a cualquier pantalla por su direccion, de modo
# que proteger unicamente la inicial dejaria el resto accesible.
requerir_sesion()
encabezado(
    "Administracion del historico",
    "Eliminacion de casos registrados. Las operaciones de esta pantalla son "
    "irreversibles.",
)
barra_lateral()

CONFIRMACION = "BORRAR TODO"

casos = db.listar_casos()
conteo = db.contar_historico()

c1, c2, c3 = st.columns(3)
c1.metric("Casos registrados", conteo["casos"])
c2.metric("Generaciones", conteo["generaciones"])
c3.metric("Correcciones", conteo["feedback"])

st.markdown("---")

# ---------------------------------------------------------------------------
# Borrado de un caso
# ---------------------------------------------------------------------------

st.markdown("### Eliminar un caso")

if not casos:
    st.caption("No hay casos registrados.")
else:
    etiquetas = {f"{c['identificador']} - cargado el {c['fecha_carga'][:10]}":
                 c for c in casos}
    seleccion = st.selectbox("Caso", list(etiquetas.keys()))
    caso = etiquetas[seleccion]

    st.caption(
        "Se eliminaran tambien sus generaciones, consultas y correcciones "
        "asociadas."
    )

    if st.button(f"Eliminar {caso['identificador']}",
                 key="eliminar_caso_individual"):
        db.eliminar_caso(caso["id"])
        if estado().get("caso_id") == caso["id"]:
            limpiar_caso()
        st.success(f"Caso {caso['identificador']} eliminado.")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# Borrado total
# ---------------------------------------------------------------------------

st.markdown("### Borrar la totalidad del historico")

total = sum(conteo.values())

if total == 0:
    st.success("El historico ya se encuentra vacio.")
else:
    st.warning(
        "Esta operacion elimina todos los casos, generaciones, consultas, "
        "correcciones y mediciones registradas. **No puede deshacerse.**"
    )

    st.markdown("**Se eliminaran los siguientes registros**")
    for tabla, cantidad in conteo.items():
        if cantidad:
            st.markdown(f"- {tabla}: {cantidad}")

    st.caption(
        "No se ven afectados el padron de usuarios, la configuracion ni los "
        "documentos de los casos que conserve en sus carpetas."
    )

    escrito = st.text_input(
        f"Para confirmar, escriba {CONFIRMACION}",
        key="confirmacion_borrado",
        placeholder=CONFIRMACION,
    )

    habilitado = escrito.strip().upper() == CONFIRMACION

    if st.button("Borrar todo el historico", type="primary",
                 disabled=not habilitado, use_container_width=True):
        borrados = db.borrar_historico()
        limpiar_caso()
        st.success(
            "Historico eliminado: "
            + ", ".join(f"{t} ({c})" for t, c in borrados.items() if c)
            + "."
        )
        st.rerun()
