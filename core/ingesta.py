"""
Capa de ingesta de documentos.

Responsabilidades:
  1. Leer documentos en PDF o texto plano.
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
    """Lee un documento segun su extension."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el documento: {ruta}")
    if ruta.suffix.lower() == ".pdf":
        return leer_pdf(ruta)
    return leer_texto(ruta)


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
    return "\n".join(lineas).strip()


# ---------------------------------------------------------------------------
# Fragmentacion
# ---------------------------------------------------------------------------

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

        pieza = texto[inicio:fin].strip()
        if pieza:
            fragmentos.append(pieza)

        if fin >= largo:
            break
        inicio = max(fin - solapamiento, inicio + 1)

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
    fragmentos: List[Fragmento] = []
    textos_directos = textos_directos or {}

    fuentes: Dict[str, tuple] = {}
    for tipo, ruta in (documentos or {}).items():
        fuentes[tipo] = (Path(ruta).name, leer_documento(ruta))
    for tipo, contenido in textos_directos.items():
        fuentes[tipo] = (f"{tipo}.txt", contenido)

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

    return fragmentos


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
