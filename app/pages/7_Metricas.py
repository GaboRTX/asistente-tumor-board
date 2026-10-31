"""
Pantalla de metricas.

Presenta la evidencia cuantitativa asociada a la hipotesis del proyecto.

Toda comparacion de tiempos se acompania de la aclaracion de su procedencia:
el tiempo automatico lo mide el sistema, mientras que el tiempo manual
proviene de un relevamiento con profesionales. Presentar ambos como si
tuvieran el mismo respaldo metodologico sobreestimaria la evidencia
disponible.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import streamlit as st

from app.comun import barra_lateral, configurar_pagina, encabezado, estado
from core import db, metricas


configurar_pagina("Metricas")
encabezado(
    "Metricas del sistema",
    "Tiempos de procesamiento, calidad de las salidas y evolucion de la tasa "
    "de correccion.",
)
barra_lateral()

datos = metricas.resumen_general()
procesamiento = datos["procesamiento"]
comparacion = datos["comparacion"]
calidad = datos["calidad"]
tendencia = datos["tendencia"]

# ---------------------------------------------------------------------------
# Procesamiento
# ---------------------------------------------------------------------------

st.markdown("## Procesamiento automatico")

if procesamiento["casos_procesados"] == 0:
    st.info("Todavia no se proceso ningun caso.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Casos procesados", procesamiento["casos_procesados"])
c2.metric("Tiempo promedio", f"{procesamiento['segundos_promedio']} s")
c3.metric("Tiempo mediano", f"{procesamiento['segundos_mediana']} s")
c4.metric("Generaciones", procesamiento.get("generaciones_totales", 0))

st.caption(
    f"Rango observado: entre {procesamiento['segundos_minimo']} y "
    f"{procesamiento['segundos_maximo']} segundos por caso."
)

if procesamiento["por_modo"]:
    modos = ", ".join(
        f"{'modelo de lenguaje' if k == 'conectado' else 'reglas deterministas'}: {v}"
        for k, v in procesamiento["por_modo"].items()
    )
    st.caption(f"Distribucion por modo de generacion: {modos}.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Comparacion con la preparacion manual
# ---------------------------------------------------------------------------

st.markdown("## Comparacion con la preparacion manual")

if not comparacion["disponible"]:
    st.warning(comparacion["motivo"])
    with st.form("alta_tiempo"):
        st.markdown("**Registrar un tiempo de preparacion manual de referencia**")
        c1, c2 = st.columns(2)
        with c1:
            minutos = st.number_input("Minutos", min_value=1.0, max_value=480.0,
                                      value=45.0, step=5.0)
        with c2:
            fuente = st.text_input(
                "Fuente del dato",
                placeholder="Relevamiento con profesionales del servicio",
            )
        descripcion = st.text_input(
            "Descripcion",
            value="Preparacion manual de un caso para junta multidisciplinaria",
        )
        if st.form_submit_button("Registrar", type="primary"):
            if not fuente.strip():
                st.error("Indique la fuente del dato relevado.")
            else:
                db.registrar_tiempo_manual(descripcion, minutos, fuente.strip())
                st.success("Tiempo de referencia registrado.")
                st.rerun()
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Preparacion manual",
              f"{comparacion['manual_minutos_promedio']} min",
              help="Valor relevado con profesionales, no medido por el sistema.")
    c2.metric("Procesamiento automatico",
              f"{comparacion['automatico_minutos_promedio']} min")
    c3.metric("Diferencia", f"{comparacion['ahorro_minutos']} min",
              delta=f"{comparacion['ahorro_porcentaje']}%")

    st.warning(comparacion["advertencia"])
    st.caption(
        f"Basado en {comparacion['manual_relevamientos']} relevamiento(s). "
        f"Fuentes: {', '.join(comparacion['manual_fuentes'])}."
    )

    with st.expander("Registrar un nuevo relevamiento"):
        c1, c2 = st.columns(2)
        with c1:
            minutos = st.number_input("Minutos", min_value=1.0, max_value=480.0,
                                      value=45.0, step=5.0, key="m2")
        with c2:
            fuente = st.text_input("Fuente del dato", key="f2")
        if st.button("Registrar relevamiento"):
            if not fuente.strip():
                st.error("Indique la fuente del dato relevado.")
            else:
                db.registrar_tiempo_manual(
                    "Preparacion manual de un caso", minutos, fuente.strip())
                st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# Calidad y aprendizaje
# ---------------------------------------------------------------------------

st.markdown("## Calidad de las salidas y evolucion")

c1, c2 = st.columns(2)
c1.metric("Correcciones registradas", calidad["total_correcciones"])
c2.metric("Promedio por caso", calidad["promedio_correcciones"])

serie = calidad["correcciones_por_caso"]
if len(serie) >= 2:
    tabla = pd.DataFrame([
        {"Caso": d["identificador"], "Correcciones": d["correcciones"]}
        for d in serie
    ]).set_index("Caso")
    st.bar_chart(tabla)
    st.caption(
        "Correcciones registradas por caso, en orden cronologico de carga. "
        "Una tendencia descendente sugiere que las correcciones incorporadas "
        "reducen los errores en casos posteriores."
    )
else:
    st.info(
        "Se requieren al menos dos casos procesados para representar la "
        "evolucion."
    )

if tendencia["concluyente"]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Primera mitad", tendencia["promedio_primera_mitad"])
    c2.metric("Segunda mitad", tendencia["promedio_segunda_mitad"])
    c3.metric("Variacion", tendencia["variacion"],
              delta="mejora" if tendencia["mejora"] else "sin mejora")
    st.caption(tendencia["advertencia"])
else:
    st.info(tendencia["motivo"])

if calidad["campos_mas_corregidos"]:
    st.markdown("### Campos con mayor cantidad de correcciones")
    tabla_campos = pd.DataFrame(
        [{"Campo": k, "Correcciones": v}
         for k, v in calidad["campos_mas_corregidos"].items()]
    ).set_index("Campo")
    st.bar_chart(tabla_campos)
    st.caption(
        "Concentra la atencion sobre los campos que requieren revision mas "
        "frecuente, lo que orienta las mejoras del sistema."
    )

st.markdown("---")

retro = datos["retroalimentacion"]
st.markdown("## Estado del ciclo de retroalimentacion")
c1, c2, c3 = st.columns(3)
c1.metric("Pendientes", retro["correcciones_pendientes"])
c2.metric("Activas", retro["correcciones_activas"])
c3.metric("Desactivadas", retro["correcciones_desactivadas"])

if retro["por_tipo_error"]:
    st.markdown("### Distribucion por tipo de error")
    from core.feedback import TIPOS_ERROR
    tabla_tipos = pd.DataFrame([
        {"Tipo": TIPOS_ERROR.get(k, k), "Cantidad": v}
        for k, v in sorted(retro["por_tipo_error"].items(), key=lambda kv: -kv[1])
    ]).set_index("Tipo")
    st.bar_chart(tabla_tipos)
