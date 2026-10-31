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

from app.comun import (barra_lateral, configurar_pagina, encabezado, requerir_resumen, requerir_sesion, usuario_actual)
from core import consultas, expediente, reporte
from core.config import TEXTO_SIN_DATO


configurar_pagina("Reporte final")

# Streamlit admite dirigirse a cualquier pantalla por su direccion, de modo
# que proteger unicamente la inicial dejaria el resto accesible.
requerir_sesion()
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


st.markdown("---")

# ---------------------------------------------------------------------------
# Expediente documental completo
# ---------------------------------------------------------------------------

st.markdown("### Informe de estudios completo")
st.caption(
    "Reune el expediente del caso en un unico paquete: el resumen con el "
    "respaldo documental de cada dato, el perfil molecular, el detalle de la "
    "documentacion analizada, la revision por especialidad, el marco "
    "normativo y la documentacion de origen tal como fue aportada."
)

st.info(
    "**Alcance.** El expediente compila lo que consta y su respaldo. **No "
    "constituye indicacion, prescripcion ni aval de tratamiento**: la "
    "indicacion terapeutica la formula y la suscribe el medico tratante. "
    "Un documento emitido por un programa que afirmara que corresponde "
    "cubrir determinada terapia seria un acto medico sin medico."
)

_usuario = usuario_actual()

col_a, col_b = st.columns(2)
_institucion = col_a.text_input(
    "Institucion (opcional)", key="expediente_institucion",
    help="Se consigna en la caratula del expediente.")
_incluir_origen = col_b.checkbox(
    "Incluir la documentacion de origen", value=True,
    key="expediente_incluir_origen",
    help="Adjunta los documentos tal como fueron aportados, para que quien "
         "revise pueda contrastar el expediente contra la fuente.")

_documentos_origen = e.get("documentos_origen") or {}
if _incluir_origen and not _documentos_origen:
    st.caption(
        "No se conservan las rutas de los documentos de este caso; el "
        "paquete se generara sin la documentacion de origen. Vuelva a "
        "procesar el caso para incorporarla."
    )

if st.button("Generar informe de estudios completo", type="primary",
             use_container_width=True):
    with st.spinner("Componiendo el expediente..."):
        _datos = expediente.reunir(
            identificador=e["identificador"],
            resumen=resumen,
            ensayos=ensayos,
            consultas=_circuito["consultas"],
            informes_lectura=e.get("informes_lectura") or [],
            emitido_por=(_usuario.etiqueta if _usuario else ""),
            institucion=_institucion.strip(),
        )
        _paquete = expediente.componer_paquete(
            _datos,
            documentos_origen=(_documentos_origen if _incluir_origen else None),
        )

    st.success(
        f"Expediente compuesto: {len(_paquete) / 1024:.0f} KB. "
        f"Incluye el expediente en PDF y en texto"
        + (", y la documentacion de origen." if (_incluir_origen
                                                 and _documentos_origen)
           else ".")
    )

    st.download_button(
        "Descargar el paquete (ZIP)",
        data=_paquete,
        file_name=expediente.nombre_del_paquete(e["identificador"]),
        mime="application/zip",
        use_container_width=True,
    )
