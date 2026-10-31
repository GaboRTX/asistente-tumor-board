"""
Pantalla de carga de caso y ejecucion del procesamiento.

El avance se presenta por etapas explicitas, de modo que el usuario pueda
observar que operacion realiza el sistema en cada momento. No se trata de un
recurso ornamental: en una herramienta de apoyo clinico, exhibir el
procedimiento seguido forma parte de la trazabilidad que el sistema debe
ofrecer.
"""

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app.comun import (aviso_clinico, barra_lateral, configurar_pagina, dato, encabezado, enlace_pagina, estado, etiqueta_documento, fijar, limpiar_caso, requerir_sesion)
from core import db
from core.config import TIPOS_DOCUMENTO
from core.ingesta import procesar_documentos
from core.lectores import extensiones_admitidas, ocr_disponible

EXTENSIONES_ADMITIDAS = extensiones_admitidas()
from core.perfil_molecular import extraer_perfil, resumir_para_busqueda
from core.rag import generar_resumen
from core.vectorizacion import construir_indice


configurar_pagina("Carga de caso")

# Streamlit admite dirigirse a cualquier pantalla por su direccion, de modo
# que proteger unicamente la inicial dejaria el resto accesible.
requerir_sesion()
encabezado(
    "Carga de caso",
    "Cargue los documentos del caso para su procesamiento.",
)
barra_lateral()
aviso_clinico()

e = estado()



# ---------------------------------------------------------------------------
# Procesamiento
# ---------------------------------------------------------------------------

def procesar(identificador: str, documentos: dict = None,
             textos: dict = None, notas: str = "") -> None:
    """Ejecuta el pipeline completo y deja el resultado en la sesion."""
    barra = st.progress(0, text="Iniciando el procesamiento...")
    inicio = time.perf_counter()

    try:
        # Etapa 1: ingesta y normalizacion
        barra.progress(12, text="Normalizando los documentos del caso...")
        fragmentos = procesar_documentos(identificador, documentos or {},
                                         textos_directos=textos or {})
        if not fragmentos:
            barra.empty()
            st.error(
                "No se obtuvo contenido procesable de los documentos "
                "aportados. Verifique que los archivos contengan texto "
                "extraible; los PDF compuestos por imagenes escaneadas "
                "requieren reconocimiento optico previo."
            )
            return

        # Etapa 2: fragmentacion y vectorizacion
        barra.progress(32, text=f"Vectorizando {len(fragmentos)} fragmentos...")
        indice = construir_indice(fragmentos)

        # Etapa 3: correcciones validadas
        barra.progress(48, text="Recuperando correcciones previas validadas...")
        from core.feedback import construir_indice_correcciones
        indice_correcciones = construir_indice_correcciones()

        # Etapa 4: generacion del resumen
        barra.progress(62, text="Generando el resumen estructurado del caso...")
        resultado = generar_resumen(fragmentos, indice=indice,
                                    indice_correcciones=indice_correcciones)

        # Etapa 5: persistencia
        barra.progress(86, text="Registrando la generacion...")
        caso = db.buscar_caso_por_identificador(identificador)
        if caso:
            caso_id = caso["id"]
        else:
            registro = {t: (Path(r).name if documentos and t in documentos else f"{t}.txt")
                        for t, r in (documentos or {}).items()}
            for t in (textos or {}):
                registro[t] = f"{t}.txt"
            caso_id = db.crear_caso(identificador, registro, notas=notas)

        generacion_id = db.registrar_generacion(
            caso_id=caso_id, tipo="resumen", contenido=resultado.como_dict(),
            fragmentos_usados=[f.como_dict() for f in fragmentos],
            modelo=resultado.modelo, modo=resultado.modo,
            segundos=resultado.segundos,
            correcciones_usadas=[
                c for campo in resultado.campos
                for c in campo.correcciones_aplicadas
            ],
        )
        db.actualizar_estado_caso(caso_id, "procesado")

        barra.progress(100, text="Procesamiento completado.")
        time.sleep(0.3)
        barra.empty()

        fijar(
            caso_id=caso_id, identificador=identificador,
            fragmentos=fragmentos, resumen=resultado.como_dict(),
            generacion_id=generacion_id, ensayos=None, origen_ensayos="",
            resumen_ensayos=None,
            motor_recuperacion=indice.describir_motor(),
            degradacion=(indice.motivo_degradacion if indice.degradado else ""),
        )

        transcurrido = time.perf_counter() - inicio
        st.success(
            f"Caso **{identificador}** procesado en {transcurrido:.1f} segundos. "
            f"Se generaron {len(fragmentos)} fragmentos documentales."
        )

        perfil = extraer_perfil(fragmentos)
        if perfil.informados:
            st.markdown("**Perfil molecular detectado**")
            columnas = st.columns(min(len(perfil.informados), 4))
            for i, (nombre, marcador) in enumerate(perfil.informados.items()):
                with columnas[i % len(columnas)]:
                    dato(nombre, marcador.valor)
        else:
            st.warning(
                "No se detectaron marcadores moleculares en la documentacion "
                "aportada. La busqueda de estudios clinicos no podra aplicar "
                "criterios moleculares."
            )

        if resultado.advertencias:
            with st.expander(
                f"Observaciones del sistema ({len(resultado.advertencias)})",
                expanded=True,
            ):
                for a in resultado.advertencias:
                    st.warning(a)

        enlace_pagina("pages/2_Resumen_del_caso.py", "Continuar al resumen del caso")

    except Exception as exc:
        barra.empty()
        st.error(f"El procesamiento no pudo completarse: {exc}")
        st.caption(
            "Revise que los documentos sean legibles y vuelva a intentarlo. "
            "Si el problema persiste, consulte el registro de la aplicacion."
        )


# ---------------------------------------------------------------------------
# Carga de documentos propios
# ---------------------------------------------------------------------------

st.markdown(
    "Cargue los documentos del caso. "
    "**Utilice unicamente un identificador anonimizado**: el sistema no "
    "requiere ni debe recibir datos que permitan identificar al paciente."
)

identificador = st.text_input(
    "Identificador anonimizado del caso",
    placeholder="CASO-006",
    help="Por ejemplo: CASO-006. No utilice nombre, documento ni numero "
         "de historia clinica.",
)

archivos = {}
columnas = st.columns(2)
for i, (tipo, etiqueta) in enumerate(TIPOS_DOCUMENTO.items()):
    with columnas[i % 2]:
        archivos[tipo] = st.file_uploader(
            etiqueta, type=EXTENSIONES_ADMITIDAS, key=f"carga_{tipo}"
        )

with st.expander("Formatos admitidos"):
    st.markdown(
        "Documentos de texto (`txt`, `md`, `csv`, `json`), paginas `html`, "
        "documentos de Word (`docx`), ODF (`odt`), `rtf`, planillas `xlsx`, "
        "`pdf` e imagenes (`png`, `jpg`, `tiff`, `bmp`, `webp`)."
    )
    st.caption(
        "El texto de las tablas de un documento de Word se incorpora al "
        "analisis. Los documentos de Word anteriores a 2007 (`.doc`) deben "
        "convertirse previamente a `.docx` o a PDF."
    )
    if ocr_disponible():
        st.caption(
            "Reconocimiento optico disponible: los PDF escaneados y las "
            "imagenes se procesan y aportan texto al analisis."
        )
    else:
        st.caption(
            "Sin reconocimiento optico de caracteres. Los PDF escaneados y "
            "las imagenes se conservan adjuntos pero no aportan texto al "
            "analisis, y el sistema lo declara al procesar el caso."
        )

notas = st.text_area("Observaciones (opcional)", height=80)

cargados = {t: a for t, a in archivos.items() if a is not None}

if cargados:
    st.caption(f"{len(cargados)} documento(s) listo(s) para procesar.")

listo = bool(identificador.strip()) and bool(cargados)
if not identificador.strip() and cargados:
    st.warning("Indique un identificador anonimizado para continuar.")

if st.button("Procesar caso", type="primary", disabled=not listo,
             use_container_width=True, key="procesar_propio"):
    import tempfile

    temporal = Path(tempfile.mkdtemp())
    rutas = {}
    for tipo, archivo in cargados.items():
        destino = temporal / f"{tipo}{Path(archivo.name).suffix or '.txt'}"
        destino.write_bytes(archivo.getbuffer())
        rutas[tipo] = destino

    procesar(identificador.strip(), documentos=rutas, notas=notas)
