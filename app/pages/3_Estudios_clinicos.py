"""
Pantalla de estudios clinicos.

Presenta los estudios propuestos junto con el criterio que origino cada
correspondencia. Exhibir el criterio es un requisito del disenio: una lista
de estudios sin fundamento visible obligaria al profesional a verificar cada
uno contra su protocolo, con lo que la herramienta no aportaria ahorro alguno.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (aviso_clinico, barra_lateral, configurar_pagina, dato, encabezado, enlace_pagina, estado, fijar, requerir_resumen, requerir_sesion)
from core.ensayos import ORIGEN_CACHE, buscar_para_perfil


configurar_pagina("Estudios clinicos")

# Streamlit admite dirigirse a cualquier pantalla por su direccion, de modo
# que proteger unicamente la inicial dejaria el resto accesible.
requerir_sesion()
encabezado(
    "Estudios clinicos a considerar",
    "Propuestos segun los marcadores moleculares documentados en el caso.",
)
barra_lateral()

e = requerir_resumen()

st.warning(
    "Los estudios listados se presentan unicamente como referencia. La "
    "elegibilidad definitiva debe evaluarse contra el protocolo completo de "
    "cada estudio. Esta pantalla no constituye una recomendacion terapeutica."
)

perfil = e["resumen"].get("perfil_molecular", {})
marcadores = [(k, v["valor"]) for k, v in perfil.items()
              if v.get("valor") and v["valor"] != "no informado"]

if not marcadores:
    st.error(
        "No se detectaron marcadores moleculares en la documentacion del caso, "
        "por lo que no es posible aplicar criterios moleculares de "
        "correspondencia."
    )
    st.stop()

st.markdown("**Marcadores utilizados como criterio de busqueda**")
columnas = st.columns(min(len(marcadores), 4))
for i, (nombre, valor) in enumerate(marcadores):
    with columnas[i % len(columnas)]:
        dato(nombre, valor)

st.markdown("---")

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    termino = st.text_input("Condicion a buscar", value="glioma")
with c2:
    maximo = st.slider("Maximo de resultados", 3, 20, 8)
with c3:
    st.write("")
    sin_conexion = st.toggle(
        "Usar copia local",
        help="Utiliza la copia local de estudios en lugar de consultar "
             "ClinicalTrials.gov. Util para operar sin conexion.",
    )

if st.button("Buscar estudios", type="primary", use_container_width=True):
    with st.spinner("Consultando estudios clinicos..."):
        try:
            resultados, origen, resumen_busqueda = buscar_para_perfil(
                marcadores, termino=termino, maximo_resultados=maximo,
                preferir_cache=sin_conexion,
            )
            fijar(ensayos=[c.como_dict() for c in resultados],
                  origen_ensayos=origen, resumen_ensayos=resumen_busqueda)
        except Exception as exc:
            st.error(f"La busqueda no pudo completarse: {exc}")

ensayos = e.get("ensayos")
resumen_busqueda = e.get("resumen_ensayos")

if ensayos is None:
    st.info("Ejecute la busqueda para obtener los estudios aplicables al caso.")
    st.stop()

origen = e.get("origen_ensayos", "")
if origen == ORIGEN_CACHE:
    st.warning(
        f"**Origen de los datos: {origen}.** La copia local puede no reflejar "
        "el estado actual del registro. Para obtener datos vigentes ejecute "
        "`python scripts/construir_cache_ensayos.py --regenerar` con conexion "
        "disponible."
    )
else:
    st.success(f"Origen de los datos: {origen}")

if resumen_busqueda:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evaluados", resumen_busqueda["total_evaluados"])
    c2.metric("Con correspondencia", resumen_busqueda["con_coincidencia"])
    c3.metric("Descartados", resumen_busqueda["descartados_por_exclusion"])
    c4.metric("Sin criterio molecular",
              resumen_busqueda["sin_criterio_molecular"])
    st.caption(
        "Los estudios descartados presentan criterios de elegibilidad "
        "incompatibles con el perfil molecular documentado en este caso."
    )

st.markdown("---")

if not ensayos:
    st.info(
        "No se hallaron estudios aplicables. Puede ampliar la busqueda "
        "modificando la condicion consultada."
    )

for ensayo in ensayos:
    with st.container(border=True):
        cabecera, enlace = st.columns([5, 1])
        with cabecera:
            st.markdown(f"**{ensayo.get('nct', '')}** &nbsp; "
                        f"{ensayo.get('fase', '')} &nbsp; "
                        f"{ensayo.get('estado', '')}")
            st.write(ensayo.get("titulo", ""))
        with enlace:
            st.link_button("Ver ficha", ensayo.get("url", ""),
                           use_container_width=True)

        coincidencias = ensayo.get("coincidencias") or []
        compatibilidades = ensayo.get("compatibilidades") or []

        if coincidencias:
            st.success("Correspondencia por: " + "; ".join(coincidencias))
        if compatibilidades:
            st.info("Compatibilidad: " + "; ".join(compatibilidades))
        if not coincidencias and not compatibilidades:
            st.caption(
                "El estudio no especifica criterios moleculares que puedan "
                "contrastarse con el perfil del caso."
            )

        paises = ensayo.get("paises") or []
        if paises:
            st.caption("Paises: " + ", ".join(paises[:8]))

st.markdown("---")
enlace_pagina("pages/6_Consultas_a_profesionales.py",
              "Continuar a consultas a profesionales")
