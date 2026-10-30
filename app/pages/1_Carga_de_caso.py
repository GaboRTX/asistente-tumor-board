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

from app.comun import (aviso_clinico, barra_lateral, configurar_pagina, dato, encabezado, enlace_pagina, estado, etiqueta_documento, fijar, limpiar_caso)
from core import db
from core.config import DIR_CASOS_DEMO, TIPOS_DOCUMENTO
from core.ingesta import cargar_caso_demo, procesar_documentos
from core.perfil_molecular import extraer_perfil, resumir_para_busqueda
from core.rag import generar_resumen
from core.vectorizacion import construir_indice


configurar_pagina("Carga de caso")
encabezado(
    "Carga de caso",
    "Seleccione un caso de demostracion o cargue los documentos de un caso "
    "propio.",
)
barra_lateral()
aviso_clinico()

e = estado()

pestania_demo, pestania_propia = st.tabs(
    ["Casos de demostracion", "Cargar documentos"]
)


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
# Casos de demostracion
# ---------------------------------------------------------------------------

with pestania_demo:
    disponibles = sorted(
        [d.name for d in DIR_CASOS_DEMO.iterdir() if d.is_dir()]
    ) if DIR_CASOS_DEMO.exists() else []

    if not disponibles:
        st.warning(
            "No se encontraron casos de demostracion. Ejecute "
            "`python scripts/generar_casos_demo.py` para crearlos."
        )
    else:
        st.markdown(
            "Los casos de demostracion son documentos sinteticos construidos "
            "a partir de patrones descriptos en la literatura publicada. "
            "No corresponden a pacientes reales ni contienen datos "
            "identificatorios."
        )

        seleccion = st.selectbox("Caso de demostracion", disponibles)
        documentos = cargar_caso_demo(DIR_CASOS_DEMO / seleccion)

        st.markdown("**Documentos disponibles en el caso**")
        faltantes = [t for t in TIPOS_DOCUMENTO if t not in documentos]
        columnas = st.columns(len(TIPOS_DOCUMENTO))
        for i, tipo in enumerate(TIPOS_DOCUMENTO):
            with columnas[i]:
                if tipo in documentos:
                    st.success(etiqueta_documento(tipo))
                else:
                    st.error(f"{etiqueta_documento(tipo)}: ausente")

        if faltantes:
            st.info(
                "El caso no incluye la totalidad de los documentos. El sistema "
                "procesara los disponibles y declarara como no documentados "
                "los campos que no pueda respaldar."
            )

        with st.expander("Ver el contenido de los documentos"):
            for tipo, ruta in documentos.items():
                st.markdown(f"**{etiqueta_documento(tipo)}**")
                st.text(Path(ruta).read_text(encoding="utf-8")[:1500])

        if st.button("Procesar caso", type="primary", use_container_width=True):
            existente = db.buscar_caso_por_identificador(seleccion)
            if existente:
                st.caption(
                    "El caso ya estaba registrado. Se generara un nuevo "
                    "resumen conservando el historial anterior."
                )
            procesar(seleccion, documentos=documentos)


# ---------------------------------------------------------------------------
# Carga de documentos propios
# ---------------------------------------------------------------------------

with pestania_propia:
    st.markdown(
        "Cargue los documentos del caso en formato PDF o texto. "
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
                etiqueta, type=["pdf", "txt", "md"], key=f"carga_{tipo}"
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
