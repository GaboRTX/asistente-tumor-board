"""
Pantalla del resumen estructurado del caso.

Es la pantalla central del sistema. Cada campo se presenta junto con el
fragmento documental que lo respalda, de modo que el profesional pueda
verificar la procedencia de cada dato sin recurrir al documento original.

La captura de correcciones se resuelve en pocos pasos deliberadamente: un
mecanismo de retroalimentacion que exija demasiado esfuerzo no se utiliza, y
un ciclo de aprendizaje sin datos de entrada no aporta valor alguno.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (aviso_clinico, barra_lateral, configurar_pagina, dato, encabezado, enlace_pagina, estado, fijar, requerir_resumen)
from core import db, feedback
from core.config import TEXTO_SIN_DATO


configurar_pagina("Resumen del caso")
encabezado(
    "Resumen estructurado del caso",
    "Cada campo indica el fragmento documental que lo respalda.",
)
barra_lateral()

e = requerir_resumen()
resumen = e["resumen"]
aviso_clinico()


# ---------------------------------------------------------------------------
# Encabezado informativo
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
with col1:
    dato("Caso", e["identificador"])
with col2:
    modo = resumen.get("modo", "")
    dato("Generacion",
               "Modelo de lenguaje" if modo == "conectado" else "Reglas")
with col3:
    dato("Tiempo", f"{resumen.get('segundos', 0)} s")
with col4:
    completos = sum(1 for c in resumen.get("campos", [])
                    if c.get("contenido") != TEXTO_SIN_DATO)
    st.metric("Campos documentados", f"{completos} de {len(resumen.get('campos', []))}")

if resumen.get("modo") != "conectado":
    st.caption(
        "El resumen fue generado por reglas deterministas. Este modo es "
        "reproducible y auditable, pero produce una redaccion menos fluida "
        "que la generacion asistida por modelo de lenguaje."
    )

advertencias = resumen.get("advertencias") or []
if advertencias:
    with st.expander(f"Observaciones del sistema ({len(advertencias)})",
                     expanded=True):
        for a in advertencias:
            st.warning(a)
        st.caption(
            "Las observaciones surgen de contrastar el resumen generado con "
            "la extraccion determinista realizada sobre los mismos "
            "documentos. Corresponde al profesional resolver cada discrepancia."
        )

st.markdown("---")


# ---------------------------------------------------------------------------
# Campos del resumen
# ---------------------------------------------------------------------------

correcciones_previas = {
    f["campo"] for f in db.listar_feedback(e["caso_id"])
}

for campo in resumen.get("campos", []):
    clave = campo.get("clave", "")
    etiqueta = campo.get("etiqueta", clave)
    contenido = campo.get("contenido", TEXTO_SIN_DATO)
    fuentes = campo.get("fuentes") or []
    aplicadas = campo.get("correcciones_aplicadas") or []
    documentado = contenido != TEXTO_SIN_DATO

    with st.container(border=True):
        cabecera, acciones = st.columns([5, 1])

        with cabecera:
            marca = " ✎" if clave in correcciones_previas else ""
            st.markdown(f"#### {etiqueta}{marca}")
            if documentado:
                st.write(contenido)
            else:
                st.caption(TEXTO_SIN_DATO)

        with acciones:
            corregir = st.toggle("Corregir", key=f"toggle_{clave}")

        # -- trazabilidad ---------------------------------------------------
        if fuentes:
            with st.expander(f"Ver las {len(fuentes)} fuentes de este campo"):
                for i, f in enumerate(fuentes, 1):
                    st.markdown(f"**{i}. {f.get('etiqueta', 'Documento')}**")
                    st.text(f.get("texto", "")[:900])
        elif documentado:
            st.caption(
                "Este campo no tiene fragmento de respaldo asociado. "
                "Verifique su contenido contra la documentacion original."
            )

        if aplicadas:
            with st.expander(
                f"Correcciones previas aplicadas a este campo ({len(aplicadas)})"
            ):
                for c in aplicadas:
                    st.caption(f"Regla {c.get('id', '')}: {c.get('regla', '')}")

        # -- correccion -----------------------------------------------------
        if corregir:
            st.markdown("---")
            valor = st.text_area(
                "Contenido corregido",
                value=contenido if documentado else "",
                key=f"valor_{clave}",
                height=110,
            )
            c1, c2 = st.columns(2)
            with c1:
                tipo = st.selectbox(
                    "Tipo de error",
                    options=list(feedback.TIPOS_ERROR.keys()),
                    format_func=lambda t: feedback.TIPOS_ERROR[t],
                    key=f"tipo_{clave}",
                )
            with c2:
                comentario = st.text_input(
                    "Observacion (opcional)", key=f"comentario_{clave}"
                )

            autor = e.get("autor", "").strip()
            if not autor:
                st.caption(
                    "Indique su nombre en el panel lateral para registrar "
                    "la correccion."
                )

            if st.button("Registrar correccion", key=f"guardar_{clave}",
                         type="primary", disabled=not autor):
                if not valor.strip():
                    st.error("El contenido corregido no puede quedar vacio.")
                elif valor.strip() == contenido.strip():
                    st.warning(
                        "El contenido corregido coincide con el generado. "
                        "No se registro ninguna correccion."
                    )
                else:
                    try:
                        feedback.registrar_correccion(
                            generacion_id=e["generacion_id"],
                            caso_id=e["caso_id"],
                            campo=clave,
                            valor_generado=contenido,
                            valor_corregido=valor.strip(),
                            tipo_error=tipo,
                            comentario=comentario.strip(),
                            autor=autor,
                        )
                        st.success(
                            "Correccion registrada. Quedara pendiente de "
                            "validacion y no influira sobre casos futuros "
                            "hasta ser aprobada en la pantalla de curacion."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No fue posible registrar la correccion: {exc}")


# ---------------------------------------------------------------------------
# Perfil molecular
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("## Perfil molecular detectado")
st.caption(
    "Extraido de manera determinista mediante reglas sobre la documentacion. "
    "Se utiliza como criterio para la busqueda de estudios clinicos y como "
    "verificacion de la salida generada."
)

perfil = resumen.get("perfil_molecular", {})
informados = {k: v for k, v in perfil.items()
              if v.get("valor") and v["valor"] != "no informado"}

if not informados:
    st.warning(
        "No se detectaron marcadores moleculares en la documentacion aportada."
    )
else:
    columnas = st.columns(min(len(informados), 4))
    for i, (nombre, datos) in enumerate(informados.items()):
        with columnas[i % len(columnas)]:
            dato(nombre, datos.get("valor", ""))
            if datos.get("detalle"):
                st.caption(datos["detalle"])

    with st.expander("Ver la evidencia textual de cada marcador"):
        for nombre, datos in informados.items():
            st.markdown(f"**{nombre}: {datos.get('valor', '')}**")
            st.caption(
                f"Documento: {datos.get('tipo_documento', 'no especificado')}"
            )
            if datos.get("evidencia"):
                st.text(datos["evidencia"])

st.markdown("---")
enlace_pagina("pages/3_Estudios_clinicos.py", "Continuar a estudios clinicos")
