"""
Capa de ingesta de documentos.

Responsabilidades:
  1. Leer documentos en los formatos habituales de la practica clinica
     (ver core.lectores).
  2. Normalizarlos a texto procesable.
  3. Fragmentarlos en unidades de tamanio acotado, preservando la referencia
     al documento y a la posicion de origen de cada fragmento.

La trazabilidad se sostiene desde aca: cada fragmento conserva de que
documento y de que parte del documento proviene, lo que permite luego citar
la fuente exacta de cada dato del resumen.
"""

import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from core import lectores
from core.config import (
    TAMANIO_FRAGMENTO,
    SOLAPAMIENTO_FRAGMENTO,
    TIPOS_DOCUMENTO,
)


@dataclass
class Fragmento:
    """Unidad minima de texto recuperable, con su procedencia."""
    id: str
    caso: str
    tipo_documento: str
    nombre_documento: str
    indice: int
    texto: str

    @property
    def etiqueta_fuente(self) -> str:
        legible = TIPOS_DOCUMENTO.get(self.tipo_documento, self.tipo_documento)
        return f"{legible} (fragmento {self.indice + 1})"

    def como_dict(self) -> Dict:
        d = asdict(self)
        d["etiqueta_fuente"] = self.etiqueta_fuente
        return d


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

def leer_pdf(ruta: Union[str, Path]) -> str:
    """Extrae el texto de un PDF. Requiere pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Para leer archivos PDF es necesario instalar pypdf "
            "(pip install pypdf)."
        ) from exc

    lector = PdfReader(str(ruta))
    paginas = []
    for pagina in lector.pages:
        try:
            paginas.append(pagina.extract_text() or "")
        except Exception:
            paginas.append("")
    return "\n".join(paginas)


def leer_texto(ruta: Union[str, Path]) -> str:
    """Lee un archivo de texto probando varias codificaciones habituales."""
    ruta = Path(ruta)
    for codificacion in ("utf-8", "latin-1", "cp1252"):
        try:
            return ruta.read_text(encoding=codificacion)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ruta.read_bytes().decode("utf-8", errors="replace")


def leer_documento(ruta: Union[str, Path]) -> str:
    """
    Lee un documento segun su extension y devuelve su texto.

    Se conserva por compatibilidad. Cuando interese el detalle del proceso
    (metodo empleado, advertencias, imagenes embebidas) corresponde emplear
    core.lectores.leer, que lo devuelve completo.
    """
    return lectores.leer(ruta).texto


# ---------------------------------------------------------------------------
# Normalizacion
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """
    Normaliza el texto de un documento clinico.

    Se unifican saltos de linea, se colapsan espacios repetidos y se
    normalizan los caracteres Unicode, preservando las tildes y la enie,
    que son significativas en la documentacion en espaniol.
    """
    if not texto:
        return ""

    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    # Colapsa espacios y tabulaciones sin destruir los saltos de parrafo
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # Reune palabras cortadas por guion al final de renglon
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)

    lineas = [linea.strip() for linea in texto.split("\n")]
    return _reunir_parrafos(lineas)


def _reunir_parrafos(lineas: List[str]) -> str:
    """
    Reune las lineas que forman parte de una misma oracion.

    Los documentos clinicos se exportan con un ancho de renglon fijo, de modo
    que una misma afirmacion puede quedar repartida en dos lineas. Si esas
    lineas no se reunen, la deteccion posterior opera sobre fragmentos de
    oracion y pierde los marcadores expresados a caballo de un salto de
    renglon: "ganancia del cromosoma 7 y perdida del" en una linea y
    "cromosoma 10" en la siguiente no se reconocen como una unica afirmacion.

    El criterio de union es deliberadamente conservador. Dos lineas se unen
    unicamente cuando la primera no termina en signo de puntuacion terminal y
    la segunda comienza en minuscula, situacion que solo se produce cuando la
    oracion efectivamente continua. De este modo se preservan los
    encabezados, los elementos de enumeracion y los titulos de seccion, que
    constituyen unidades independientes.
    """
    resultado: List[str] = []
    for linea in lineas:
        if not linea:
            resultado.append(linea)
            continue

        if resultado and resultado[-1]:
            previa = resultado[-1]
            termina_oracion = previa[-1] in ".;:!?"
            continua = linea[0].islower() or linea[0].isdigit()
            es_enumeracion = linea[0] in "-*\u2022"
            if not termina_oracion and continua and not es_enumeracion:
                resultado[-1] = previa + " " + linea
                continue

        resultado.append(linea)

    return "\n".join(resultado).strip()


# ---------------------------------------------------------------------------
# Fragmentacion
# ---------------------------------------------------------------------------

def _inicio_de_palabra(texto: str, posicion: int) -> int:
    """
    Adelanta la posicion hasta el comienzo de la siguiente palabra.

    El solapamiento entre fragmentos se calcula en caracteres, de modo que
    puede situarse en el interior de una palabra. Arrancar alli produce
    fragmentos encabezados por restos como "tracion de gadolinio", que luego
    aparecen en el resumen y en la cita.
    """
    if posicion <= 0 or posicion >= len(texto):
        return posicion
    if texto[posicion - 1].isspace() or texto[posicion].isspace():
        return posicion
    siguiente = texto.find(" ", posicion)
    return posicion if siguiente == -1 else siguiente + 1


def fragmentar(texto: str,
               tamanio: int = TAMANIO_FRAGMENTO,
               solapamiento: int = SOLAPAMIENTO_FRAGMENTO) -> List[str]:
    """
    Divide el texto en fragmentos de tamanio acotado con solapamiento.

    El corte se intenta realizar en un limite de oracion o de parrafo, de modo
    de no partir una afirmacion clinica por la mitad, lo que degradaria tanto
    la recuperacion como la trazabilidad de la cita.
    """
    texto = (texto or "").strip()
    if not texto:
        return []
    if len(texto) <= tamanio:
        return [texto]

    if solapamiento >= tamanio:
        raise ValueError("El solapamiento debe ser menor que el tamanio del fragmento.")

    fragmentos: List[str] = []
    inicio = 0
    largo = len(texto)

    while inicio < largo:
        fin = min(inicio + tamanio, largo)

        if fin < largo:
            ventana = texto[inicio:fin]
            corte = max(
                ventana.rfind(". "),
                ventana.rfind(".\n"),
                ventana.rfind("\n\n"),
                ventana.rfind(";"),
            )
            # Solo se acepta el corte si no deja un fragmento demasiado corto
            if corte > tamanio * 0.45:
                fin = inicio + corte + 1
            else:
                # Sin limite de oracion utilizable, se retrocede al ultimo
                # espacio. Cortar a mitad de palabra degrada la cita, que es
                # el elemento que el profesional verifica contra la fuente.
                espacio = ventana.rfind(" ")
                if espacio > tamanio * 0.45:
                    fin = inicio + espacio + 1

        pieza = texto[inicio:fin].strip()
        if pieza:
            fragmentos.append(pieza)

        if fin >= largo:
            break
        inicio = max(fin - solapamiento, inicio + 1)
        inicio = _inicio_de_palabra(texto, inicio)

    return fragmentos


# ---------------------------------------------------------------------------
# Procesamiento de un caso completo
# ---------------------------------------------------------------------------

def procesar_documentos(identificador_caso: str,
                        documentos: Dict[str, Union[str, Path]],
                        textos_directos: Optional[Dict[str, str]] = None
                        ) -> List[Fragmento]:
    """
    Procesa los documentos de un caso y devuelve la lista de fragmentos.

    Parametros
    ----------
    identificador_caso : identificador anonimizado del caso (ej. "CASO-001")
    documentos : diccionario {tipo_documento: ruta_del_archivo}
    textos_directos : diccionario {tipo_documento: contenido}, util cuando el
        texto ya fue leido en memoria (por ejemplo, desde la interfaz web).
    """
    fragmentos, _informes = procesar_documentos_detallado(
        identificador_caso, documentos, textos_directos)
    return fragmentos


def procesar_documentos_detallado(
        identificador_caso: str,
        documentos: Dict[str, Union[str, Path]],
        textos_directos: Optional[Dict[str, str]] = None
) -> tuple:
    """
    Procesa los documentos y devuelve (fragmentos, informes_de_lectura).

    El informe de lectura de cada documento consigna el metodo empleado, las
    advertencias y las imagenes halladas. Es lo que permite exhibir que un
    documento se incorporo sin aportar texto, en lugar de omitirlo en
    silencio: un PDF escaneado sin reconocimiento optico produce cero
    fragmentos, y quien no lo advierta supondra que el sistema lo considero.
    """
    fragmentos: List[Fragmento] = []
    informes: List[Dict] = []
    textos_directos = textos_directos or {}

    fuentes: Dict[str, tuple] = {}
    for tipo, ruta in (documentos or {}).items():
        lectura = lectores.leer(ruta)
        informe = lectura.como_dict()
        informe.pop("texto", None)
        informe.update({"tipo_documento": tipo,
                        "nombre_documento": Path(ruta).name})
        informes.append(informe)
        fuentes[tipo] = (Path(ruta).name, lectura.texto)

    for tipo, contenido in textos_directos.items():
        fuentes[tipo] = (f"{tipo}.txt", contenido)
        informes.append({"tipo_documento": tipo,
                         "nombre_documento": f"{tipo}.txt",
                         "metodo": "texto ingresado directamente",
                         "advertencias": [], "imagenes": [], "paginas": None,
                         "tiene_texto": bool((contenido or "").strip())})

    for tipo, (nombre, crudo) in fuentes.items():
        texto = normalizar(crudo)
        for i, pieza in enumerate(fragmentar(texto)):
            fragmentos.append(
                Fragmento(
                    id=f"{identificador_caso}::{tipo}::{i}",
                    caso=identificador_caso,
                    tipo_documento=tipo,
                    nombre_documento=nombre,
                    indice=i,
                    texto=pieza,
                )
            )

    # Se consigna la cantidad de fragmentos aportados por cada documento, que
    # es la medida concreta de su incidencia sobre el analisis.
    for informe in informes:
        informe["fragmentos"] = sum(
            1 for f in fragmentos
            if f.tipo_documento == informe["tipo_documento"])

    return fragmentos, informes


def cargar_caso_demo(directorio: Union[str, Path]) -> Dict[str, Path]:
    """
    Detecta los documentos de un caso demo a partir del nombre de archivo.

    Convencion esperada dentro del directorio del caso:
        historia_clinica.txt, anatomia_patologica.txt, genomica.txt, imagenes.txt
    """
    directorio = Path(directorio)
    encontrados: Dict[str, Path] = {}
    for tipo in TIPOS_DOCUMENTO:
        for extension in (".txt", ".pdf", ".md"):
            candidato = directorio / f"{tipo}{extension}"
            if candidato.exists():
                encontrados[tipo] = candidato
                break
    return encontrados
