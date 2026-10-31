"""
Pantalla del reporte final consolidado.

Reune el resumen estructurado y los estudios propuestos en un unico documento
apto para su distribucion previa a la junta.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (barra_lateral, configurar_pagina, encabezado,
                       requerir_resumen)
from core import consultas, reporte
from core.config import TEXTO_SIN_DATO


configurar_pagina("Reporte final")
encabezado(
    "Reporte final del caso",
    "Documento consolidado para su distribucion previa a la junta.",
)
barra_lateral()

e = requerir_resumen()
resumen = e["resumen"]
ensayos = e.get("ensayos") or []

st.warning(
    "El reporte incluye de manera obligatoria la constancia de que se trata "
    "de un documento de apoyo generado automaticamente, que requiere "
    "validacion profesional y no constituye indicacion terapeutica."
)

if not ensayos:
    st.info(
        "El reporte se generara sin la seccion de estudios clinicos. Para "
        "incluirla, ejecute previamente la busqueda en la pantalla "
        "**Estudios clinicos**."
    )

texto = reporte.generar_texto(
    identificador=e["identificador"],
    resumen=resumen,
    ensayos=ensayos,
    origen_ensayos=e.get("origen_ensayos", ""),
    motor_recuperacion=e.get("motor_recuperacion", ""),
)

c1, c2, c3 = st.columns(3)
with c1:
    completos = sum(1 for c in resumen.get("campos", [])
                    if c.get("contenido") != TEXTO_SIN_DATO)
    st.metric("Campos documentados",
              f"{completos} de {len(resumen.get('campos', []))}")
with c2:
    st.metric("Estudios incluidos", len(ensayos))
with c3:
    st.metric("Observaciones", len(resumen.get("advertencias") or []))

# --- Estado de la revision por especialidad --------------------------------
# El reporte es el insumo de la deliberacion, de modo que debe exhibir si el
# caso fue efectivamente revisado. Un reporte que omita ese dato induce a
# suponer una conformidad que puede no existir.
_circuito = consultas.estado_del_circuito(e["caso_id"])

if _circuito["total"] == 0:
    st.warning(
        "El caso no fue sometido a revision por especialidad. La ausencia de "
        "objeciones no equivale a conformidad."
    )
elif _circuito["pendientes"]:
    st.warning(
        f"Restan {_circuito['pendientes']} respuesta(s) pendiente(s) de "
        f"profesionales consultados."
    )
elif _circuito["con_observaciones"]:
    st.warning(
        f"{_circuito['con_observaciones']} profesional(es) consignaron "
        f"observaciones sin atender."
    )
else:
    st.success(
        f"Revisado por {_circuito['conformes']} profesional(es), sin "
        f"observaciones pendientes."
    )

with st.expander("Detalle de la revision por especialidad",
                 expanded=bool(_circuito["con_observaciones"])):
    if not _circuito["consultas"]:
        st.caption("Sin consultas registradas.")
    for _c in _circuito["consultas"]:
        st.markdown(
            f"- **{_c['nombre']}** "
            f"({consultas.etiqueta_de_especialidad(_c['especialidad'])}): "
            f"{consultas.ETIQUETAS_ESTADO.get(_c['estado'], _c['estado'])}"
        )
        if _c["observacion"]:
            st.caption(f"  {_c['observacion']}")

st.markdown("---")

st.download_button(
    "Descargar reporte en texto",
    data=texto.encode("utf-8"),
    file_name=f"reporte_{e['identificador']}.txt",
    mime="text/plain",
    use_container_width=True,
)

if st.button("Generar reporte en PDF", type="primary",
             use_container_width=True):
    with st.spinner("Generando el documento..."):
        try:
            ruta = reporte.generar_pdf(
                identificador=e["identificador"],
                resumen=resumen,
                ensayos=ensayos,
                origen_ensayos=e.get("origen_ensayos", ""),
                motor_recuperacion=e.get("motor_recuperacion", ""),
            )
            st.success(f"Documento generado: {ruta.name}")
            st.download_button(
                "Descargar PDF",
                data=Path(ruta).read_bytes(),
                file_name=ruta.name,
                mime="application/pdf",
                use_container_width=True,
            )
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"No fue posible generar el documento: {exc}")

st.markdown("---")
st.markdown("### Vista previa")
st.text(texto)
