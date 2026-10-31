"""
Configuracion central del proyecto.

Toda ruta o parametro ajustable del sistema se define aca, de manera que
ningun otro modulo tenga rutas escritas de forma fija en el codigo.
"""

import re
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Carga de la configuracion local
# ---------------------------------------------------------------------------

# Las credenciales se leen de un archivo .env que no se versiona. Su ausencia
# no es un error: el sistema opera en modo determinista cuando no hay clave
# de API configurada.
_RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_RAIZ_PROYECTO / ".env")
except ImportError:
    # python-dotenv no instalado: se leen unicamente las variables de entorno
    # ya definidas en el sistema.
    pass

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------

RAIZ = _RAIZ_PROYECTO

DIR_DATOS = RAIZ / "data"
DIR_CASOS_DEMO = DIR_DATOS / "casos_demo"
DIR_GUIAS = DIR_DATOS / "guias"
DIR_ALMACEN = DIR_DATOS / "almacen"          # base vectorial persistente
DIR_SALIDAS = DIR_DATOS / "salidas"          # reportes generados

RUTA_BASE_DATOS = DIR_DATOS / "asistente.db"
RUTA_CACHE_ENSAYOS = DIR_DATOS / "ensayos_cache.json"

for _d in (DIR_DATOS, DIR_CASOS_DEMO, DIR_GUIAS, DIR_ALMACEN, DIR_SALIDAS):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Parametros del pipeline
# ---------------------------------------------------------------------------

# Fragmentacion de documentos
TAMANIO_FRAGMENTO = 700        # caracteres por fragmento
SOLAPAMIENTO_FRAGMENTO = 120   # caracteres de solapamiento entre fragmentos

# Recuperacion
TOP_K_FRAGMENTOS = 6           # fragmentos del caso recuperados por consulta
TOP_K_CORRECCIONES = 3         # correcciones previas recuperadas por consulta

# Umbral minimo de similitud para considerar relevante una correccion previa
UMBRAL_SIMILITUD_CORRECCION = 0.25


# ---------------------------------------------------------------------------
# Proveedor de modelo de lenguaje
# ---------------------------------------------------------------------------

# Se lee de variable de entorno. Si no hay clave configurada, el sistema
# opera en modo determinista sin conexion (ver core/llm.py).
PROVEEDOR_LLM = os.getenv("PROVEEDOR_LLM", "auto")   # auto | google | anthropic | openai | offline
CLAVE_API_LLM = os.getenv("CLAVE_API_LLM", "")
MODELO_LLM = os.getenv("MODELO_LLM", "")

# ---------------------------------------------------------------------------
# Aviso de consulta por correo
# ---------------------------------------------------------------------------
# El aviso no transporta contenido clinico; anuncia la consulta y remite al
# sistema. La configuracion es opcional: sin ella el circuito de consulta
# funciona igualmente y el aviso se entrega para su envio manual.
SMTP_SERVIDOR = os.getenv("SMTP_SERVIDOR", "")
SMTP_PUERTO = int(os.getenv("SMTP_PUERTO", "587") or "587")
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
def _normalizar_clave_smtp(valor: str) -> str:
    """
    Tolera el formato en que Google exhibe las contrasenias de aplicacion.

    Google las presenta en cuatro bloques de cuatro letras separados por
    espacios. Los espacios son de presentacion y no integran la contrasenia,
    de modo que copiarla tal como se la ve produce un rechazo de credenciales
    cuyo motivo no resulta evidente.

    La normalizacion se restringe a esa forma exacta. Toda otra contrasenia se
    conserva intacta, incluidos los espacios que pudiera contener
    legitimamente.
    """
    bruto = (valor or "").strip()
    if re.fullmatch(r"[a-z]{4}(?: [a-z]{4}){3}", bruto):
        return bruto.replace(" ", "")
    return bruto


SMTP_CLAVE = _normalizar_clave_smtp(os.getenv("SMTP_CLAVE", ""))
SMTP_REMITENTE = os.getenv("SMTP_REMITENTE", "") or SMTP_USUARIO
SMTP_INSTITUCION = os.getenv("SMTP_INSTITUCION", "")
TIMEOUT_SMTP = 20

# Tiempo maximo de espera para llamadas de red (segundos)
TIMEOUT_RED = 20

# La ejecucion local exige una espera sustancialmente mayor. La primera
# consulta carga el modelo desde disco a memoria, y la generacion corre sobre
# el procesador del equipo en lugar de sobre el acelerador de un proveedor.
# Un limite de veinte segundos interrumpe la primera consulta de manera
# sistematica, aun cuando el servicio funcione correctamente.
TIMEOUT_LOCAL = 300


# ---------------------------------------------------------------------------
# Marcadores moleculares contemplados por el sistema
# ---------------------------------------------------------------------------

MARCADORES = ["IDH", "1p/19q", "MGMT", "ATRX", "TERT", "EGFR", "TP53",
              "H3", "CDKN2A/B", "Cromosomas 7/10"]


# ---------------------------------------------------------------------------
# Tipos de documento aceptados por caso
# ---------------------------------------------------------------------------

TIPOS_DOCUMENTO = {
    "historia_clinica": "Historia clinica",
    "anatomia_patologica": "Informe anatomopatologico",
    "genomica": "Informe de secuenciacion genomica",
    "imagenes": "Informe de imagenes",
}


# ---------------------------------------------------------------------------
# Campos del resumen estructurado
# ---------------------------------------------------------------------------

CAMPOS_RESUMEN = [
    ("datos_clinicos", "Datos clinicos relevantes"),
    ("antecedentes", "Antecedentes"),
    ("hallazgos_patologia", "Hallazgos anatomopatologicos"),
    ("perfil_molecular", "Perfil molecular"),
    ("hallazgos_imagenes", "Hallazgos imagenologicos"),
    ("tratamientos_previos", "Tratamientos previos"),
]

# El perfil molecular no es prosa sino un conjunto de pares marcador-estado.
# La extraccion determinista lo produce completo y ordenado, de modo que
# encomendarlo al modelo de lenguaje no aporta redaccion y si introduce
# riesgo de omision. Cada tarea se asigna al procedimiento que corresponde:
# el modelo redacta, las reglas reportan.
CAMPOS_SIEMPRE_DETERMINISTAS = frozenset({"perfil_molecular"})

TEXTO_SIN_DATO = "No consta en la documentacion aportada."
