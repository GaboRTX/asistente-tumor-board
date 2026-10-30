"""
Pantalla de inicio: panel de casos y estado del sistema.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (aviso_clinico, barra_lateral, configurar_pagina, dato, encabezado, estado, fijar)
from core import db, feedback, metricas
from core.llm import detectar_proveedor
from core.vectorizacion import motor_disponible, MOTOR_EMBEDDINGS


configurar_pagina("Inicio")
encabezado(
    "Asistente de preparacion de casos para junta de neuro-oncologia",
    "Sintesis documental asistida con trazabilidad de fuentes y busqueda de "
    "estudios clinicos segun perfil molecular.",
)
barra_lateral()
aviso_clinico()

# ---------------------------------------------------------------------------
# Estado del sistema
# ---------------------------------------------------------------------------

st.markdown("## Estado del sistema")

col1, col2, col3 = st.columns(3)

proveedor, modelo = detectar_proveedor()
with col1:
    if proveedor == "offline":
        dato("Generacion", "Reglas deterministas")
        st.caption(
            "Sin clave de API configurada. El sistema opera en modo "
            "determinista, que es reproducible y auditable pero produce "
            "resumenes menos fluidos."
        )
    else:
        dato("Generacion", "Modelo de lenguaje")
        st.caption(f"Proveedor: {proveedor} | Modelo: {modelo}")

with col2:
    motor = motor_disponible()
    if motor == MOTOR_EMBEDDINGS:
        dato("Recuperacion", "Embeddings")
        st.caption(
            "Biblioteca de embeddings disponible. La primera ejecucion "
            "requiere descargar el modelo."
        )
    else:
        dato("Recuperacion", "TF-IDF")
        st.caption(
            "Modo de respaldo sin dependencias externas. Instale "
            "sentence-transformers para habilitar recuperacion semantica."
        )

with col3:
    casos = db.listar_casos()
    st.metric("Casos registrados", len(casos))
    est = feedback.estadisticas()
    st.caption(
        f"{est['correcciones_activas']} correcciones activas | "
        f"{est['correcciones_pendientes']} pendientes de validacion"
    )

with st.expander("Verificar el modelo de embeddings antes de una presentacion"):
    st.markdown(
        "La primera carga del modelo de embeddings requiere conexion a "
        "internet. Una vez descargado queda almacenado localmente y el "
        "sistema opera sin conexion. Conviene ejecutar esta verificacion "
        "con anticipacion si el sistema se utilizara en un entorno sin "
        "conectividad garantizada."
    )
    if st.button("Verificar ahora"):
        with st.spinner("Cargando el modelo de embeddings..."):
            from core.vectorizacion import verificar_modelo
            disponible, mensaje = verificar_modelo()
        if disponible:
            st.success(mensaje)
        else:
            st.warning(mensaje)
            st.caption(
                "El sistema sigue siendo operativo con el motor TF-IDF."
            )

st.markdown("---")

def _cargar_caso_existente(caso):
    """Restablece en la sesion un caso previamente procesado."""
    from core.ingesta import cargar_caso_demo, procesar_documentos
    from core.config import DIR_CASOS_DEMO

    generacion = db.ultima_generacion(caso["id"], "resumen")
    directorio = DIR_CASOS_DEMO / caso["identificador"]

    fragmentos = None
    if directorio.exists():
        documentos = cargar_caso_demo(directorio)
        if documentos:
            fragmentos = procesar_documentos(caso["identificador"], documentos)

    fijar(
        caso_id=caso["id"],
        identificador=caso["identificador"],
        fragmentos=fragmentos,
        resumen=generacion["contenido"] if generacion else None,
        generacion_id=generacion["id"] if generacion else None,
        ensayos=None, origen_ensayos="", resumen_ensayos=None,
    )
    st.rerun()


# ---------------------------------------------------------------------------
# Panel de casos
# ---------------------------------------------------------------------------

st.markdown("## Casos registrados")

if not casos:
    st.info(
        "Todavia no hay casos registrados. Comience en la pantalla "
        "**Carga de caso** del menu lateral."
    )
else:
    calidad = metricas.metricas_calidad()
    correcciones_por_caso = {d["caso_id"]: d["correcciones"]
                             for d in calidad["correcciones_por_caso"]}

    for caso in casos:
        generacion = db.ultima_generacion(caso["id"], "resumen")
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])

            with c1:
                st.markdown(f"**{caso['identificador']}**")
                st.caption(f"Cargado el {caso['fecha_carga'][:10]}")

            with c2:
                documentos = caso.get("documentos", {})
                st.caption(f"{len(documentos)} documentos")
                if generacion:
                    etiqueta = ("Modelo de lenguaje"
                                if generacion["modo"] == "conectado"
                                else "Reglas deterministas")
                    st.caption(etiqueta)

            with c3:
                if generacion:
                    st.caption(f"Procesado en {generacion['segundos']} s")
                else:
                    st.caption("Sin procesar")
                n = correcciones_por_caso.get(caso["id"], 0)
                st.caption(f"{n} correcciones registradas")

            with c4:
                if st.button("Abrir", key=f"abrir_{caso['id']}",
                             use_container_width=True):
                    _cargar_caso_existente(caso)


st.markdown("---")
with st.expander("Como utilizar la herramienta"):
    st.markdown(
        """
1. **Carga de caso**: seleccione un caso de demostracion o cargue los
   documentos de un caso propio. El sistema los normaliza, los fragmenta y
   construye el indice de recuperacion.
2. **Resumen del caso**: revise el resumen estructurado. Cada campo indica el
   fragmento documental que lo respalda. Corrija los campos que lo requieran.
3. **Estudios clinicos**: consulte los estudios propuestos segun el perfil
   molecular documentado, con el criterio de correspondencia explicito.
4. **Reporte final**: exporte el documento consolidado para la junta.
5. **Curacion de correcciones**: valide o desestime las correcciones
   registradas. Solo las correcciones validadas influyen sobre casos futuros.
6. **Metricas**: consulte los tiempos de procesamiento y la evolucion de la
   tasa de correccion.
        """
    )
