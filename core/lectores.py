# -*- coding: utf-8 -*-
"""
Lectura de documentos en los formatos habituales de la practica clinica.

La documentacion de un caso llega en lo que cada servicio produce: el informe
anatomopatologico en PDF, la historia clinica en Word, el listado de estudios
en una planilla, las imagenes en archivos sueltos. Exigir un formato unico
trasladaria al profesional un trabajo de conversion que el sistema puede
asumir.

Un principio gobierna este modulo: **nunca declarar como leido lo que no se
pudo leer**. Un documento del que no se extrajo texto se registra como tal, de
manera visible, y no se lo omite en silencio ni se lo presenta como procesado.
Un PDF escaneado sin reconocimiento optico disponible aporta cero texto al
analisis, y el profesional debe saberlo: de lo contrario supondria que el
sistema considero un documento que en los hechos ignoro.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Resultado de la lectura
# ---------------------------------------------------------------------------

@dataclass
class Lectura:
    """Resultado de leer un documento."""
    texto: str = ""
    metodo: str = ""
    advertencias: List[str] = field(default_factory=list)
    imagenes: List[str] = field(default_factory=list)
    paginas: Optional[int] = None

    @property
    def tiene_texto(self) -> bool:
        return bool(self.texto and self.texto.strip())

    def como_dict(self) -> Dict:
        return {
            "texto": self.texto,
            "metodo": self.metodo,
            "advertencias": list(self.advertencias),
            "imagenes": list(self.imagenes),
            "paginas": self.paginas,
            "tiene_texto": self.tiene_texto,
        }


class FormatoNoSoportado(ValueError):
    """La extension del archivo no corresponde a ningun lector registrado."""


# ---------------------------------------------------------------------------
# Disponibilidad del reconocimiento optico
# ---------------------------------------------------------------------------

def ocr_disponible() -> bool:
    """
    Indica si hay reconocimiento optico de caracteres operativo.

    Exige dos componentes: el paquete pytesseract y el programa tesseract. El
    primero sin el segundo falla recien al procesar, de modo que se comprueban
    ambos.
    """
    try:
        import pytesseract
    except ImportError:
        return False
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


MOTIVO_SIN_OCR = (
    "Sin reconocimiento optico de caracteres disponible. El documento se "
    "conserva adjunto pero no aporta texto al analisis. Para habilitarlo "
    "instale Tesseract (https://github.com/UB-Mannheim/tesseract/wiki en "
    "Windows) y el paquete pytesseract."
)


def _reconocer(ruta: Path) -> str:
    """Aplica reconocimiento optico sobre una imagen."""
    import pytesseract
    from PIL import Image

    with Image.open(ruta) as imagen:
        # El castellano mejora sensiblemente el resultado sobre texto clinico.
        for idioma in ("spa", "eng", None):
            try:
                if idioma:
                    return pytesseract.image_to_string(imagen, lang=idioma)
                return pytesseract.image_to_string(imagen)
            except Exception:
                continue
    return ""


# ---------------------------------------------------------------------------
# Lectores por formato
# ---------------------------------------------------------------------------

def _leer_texto_plano(ruta: Path) -> Lectura:
    for codificacion in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return Lectura(texto=ruta.read_text(encoding=codificacion),
                           metodo="texto plano")
        except (UnicodeDecodeError, UnicodeError):
            continue
    return Lectura(
        texto=ruta.read_bytes().decode("utf-8", errors="replace"),
        metodo="texto plano",
        advertencias=["La codificacion del archivo no pudo determinarse; "
                      "algunos caracteres pueden haberse sustituido."])


def _leer_html(ruta: Path) -> Lectura:
    bruto = _leer_texto_plano(ruta).texto
    try:
        from bs4 import BeautifulSoup
        sopa = BeautifulSoup(bruto, "html.parser")
        for etiqueta in sopa(["script", "style"]):
            etiqueta.decompose()
        texto = sopa.get_text("\n")
    except ImportError:
        texto = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bruto,
                       flags=re.DOTALL | re.IGNORECASE)
        texto = re.sub(r"<[^>]+>", "\n", texto)
    return Lectura(texto=_compactar(texto), metodo="HTML")


def _leer_rtf(ruta: Path) -> Lectura:
    bruto = _leer_texto_plano(ruta).texto
    try:
        from striprtf.striprtf import rtf_to_text
        return Lectura(texto=rtf_to_text(bruto, errors="ignore"), metodo="RTF")
    except ImportError:
        pass
    # Depuracion minima: se descartan las llaves de grupo y las palabras de
    # control, conservando el texto literal.
    texto = re.sub(r"\\'[0-9a-fA-F]{2}", " ", bruto)
    texto = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", texto)
    texto = texto.replace("{", " ").replace("}", " ")
    return Lectura(
        texto=_compactar(texto), metodo="RTF (depuracion basica)",
        advertencias=["Para una lectura fiel de archivos RTF instale "
                      "striprtf (pip install striprtf)."])


def _leer_docx(ruta: Path) -> Lectura:
    try:
        import docx
    except ImportError:
        return Lectura(
            metodo="DOCX",
            advertencias=["Para leer documentos de Word instale python-docx "
                          "(pip install python-docx)."])

    documento = docx.Document(str(ruta))
    partes = [p.text for p in documento.paragraphs]

    # Las tablas concentran con frecuencia el perfil molecular y los valores
    # de laboratorio, de modo que omitirlas perderia precisamente el dato de
    # mayor densidad del documento.
    for tabla in documento.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells]
            if any(celdas):
                partes.append(" | ".join(celdas))

    imagenes = _nombres_de_imagenes_embebidas(ruta)
    advertencias = []
    if imagenes:
        advertencias.append(
            f"El documento contiene {len(imagenes)} imagen(es) embebida(s). "
            "Su contenido grafico no se analiza.")

    return Lectura(texto=_compactar("\n".join(partes)), metodo="DOCX",
                   advertencias=advertencias, imagenes=imagenes)


def _nombres_de_imagenes_embebidas(ruta: Path) -> List[str]:
    """Enumera las imagenes contenidas en un contenedor de tipo OOXML u ODF."""
    try:
        with zipfile.ZipFile(ruta) as paquete:
            return sorted(
                n for n in paquete.namelist()
                if n.lower().startswith(("word/media/", "pictures/",
                                         "ppt/media/", "xl/media/"))
                and Path(n).suffix.lower() in EXTENSIONES_IMAGEN)
    except (zipfile.BadZipFile, OSError):
        return []


def _leer_odt(ruta: Path) -> Lectura:
    try:
        from odf import teletype, text as odf_text
        from odf.opendocument import load
    except ImportError:
        return Lectura(
            metodo="ODT",
            advertencias=["Para leer documentos ODF instale odfpy "
                          "(pip install odfpy)."])

    documento = load(str(ruta))
    partes = [teletype.extractText(p)
              for p in documento.getElementsByType(odf_text.P)]
    imagenes = _nombres_de_imagenes_embebidas(ruta)
    return Lectura(texto=_compactar("\n".join(partes)), metodo="ODT",
                   imagenes=imagenes)


def _leer_planilla(ruta: Path) -> Lectura:
    try:
        import openpyxl
    except ImportError:
        return Lectura(
            metodo="planilla",
            advertencias=["Para leer planillas instale openpyxl "
                          "(pip install openpyxl)."])

    libro = openpyxl.load_workbook(str(ruta), data_only=True, read_only=True)
    partes = []
    for hoja in libro.worksheets:
        partes.append(f"[{hoja.title}]")
        for fila in hoja.iter_rows(values_only=True):
            celdas = [str(c).strip() for c in fila if c is not None]
            if celdas:
                partes.append(" | ".join(celdas))
    libro.close()
    return Lectura(texto=_compactar("\n".join(partes)), metodo="planilla")


def _leer_pdf(ruta: Path) -> Lectura:
    try:
        from pypdf import PdfReader
    except ImportError:
        return Lectura(
            metodo="PDF",
            advertencias=["Para leer archivos PDF instale pypdf "
                          "(pip install pypdf)."])

    lector = PdfReader(str(ruta))
    paginas = []
    for pagina in lector.pages:
        try:
            paginas.append(pagina.extract_text() or "")
        except Exception:
            paginas.append("")

    texto = _compactar("\n".join(paginas))
    cantidad = len(lector.pages)

    if texto.strip():
        return Lectura(texto=texto, metodo="PDF (texto incorporado)",
                       paginas=cantidad)

    # Sin texto incorporado: se trata de un documento escaneado.
    if not ocr_disponible():
        return Lectura(
            metodo="PDF sin texto incorporado", paginas=cantidad,
            advertencias=[
                "El PDF no contiene texto incorporado; probablemente sea un "
                "documento escaneado. " + MOTIVO_SIN_OCR])

    reconocido = _reconocer_pdf(ruta)
    if not reconocido.strip():
        return Lectura(
            metodo="PDF escaneado", paginas=cantidad,
            advertencias=["El reconocimiento optico no obtuvo texto legible "
                          "de este documento."])
    return Lectura(texto=_compactar(reconocido),
                   metodo="PDF escaneado (reconocimiento optico)",
                   paginas=cantidad,
                   advertencias=["Texto obtenido por reconocimiento optico. "
                                 "Verifique los valores numericos contra el "
                                 "documento original."])


def _reconocer_pdf(ruta: Path) -> str:
    """Rasteriza el PDF y aplica reconocimiento optico pagina por pagina."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return ""
    try:
        import pytesseract
        paginas = convert_from_path(str(ruta))
        return "\n".join(pytesseract.image_to_string(p, lang="spa")
                         for p in paginas)
    except Exception:
        return ""


def _leer_imagen(ruta: Path) -> Lectura:
    """
    Procesa un archivo de imagen.

    Sin reconocimiento optico la imagen no aporta texto. Se la registra como
    adjunta y se lo declara de manera expresa: presentarla como procesada
    induciria a suponer que el sistema considero su contenido.
    """
    if not ocr_disponible():
        return Lectura(metodo="imagen adjunta", imagenes=[ruta.name],
                       advertencias=[MOTIVO_SIN_OCR])

    texto = _reconocer(ruta)
    if not texto.strip():
        return Lectura(
            metodo="imagen adjunta", imagenes=[ruta.name],
            advertencias=["El reconocimiento optico no obtuvo texto legible "
                          "de esta imagen. Se conserva adjunta."])

    return Lectura(
        texto=_compactar(texto), metodo="imagen (reconocimiento optico)",
        imagenes=[ruta.name],
        advertencias=["Texto obtenido por reconocimiento optico. Verifique "
                      "los valores numericos contra el documento original."])


# ---------------------------------------------------------------------------
# Registro de formatos
# ---------------------------------------------------------------------------

EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
                      ".webp", ".gif"}

LECTORES: Dict[str, Callable[[Path], Lectura]] = {
    ".txt": _leer_texto_plano,
    ".text": _leer_texto_plano,
    ".md": _leer_texto_plano,
    ".markdown": _leer_texto_plano,
    ".csv": _leer_texto_plano,
    ".tsv": _leer_texto_plano,
    ".json": _leer_texto_plano,
    ".log": _leer_texto_plano,
    ".dat": _leer_texto_plano,
    ".html": _leer_html,
    ".htm": _leer_html,
    ".xml": _leer_html,
    ".rtf": _leer_rtf,
    ".docx": _leer_docx,
    ".docm": _leer_docx,
    ".odt": _leer_odt,
    ".xlsx": _leer_planilla,
    ".xlsm": _leer_planilla,
    ".pdf": _leer_pdf,
}

for _ext in EXTENSIONES_IMAGEN:
    LECTORES[_ext] = _leer_imagen


# Formatos que el sistema reconoce pero no puede abrir por si mismo.
FORMATOS_HEREDADOS = {
    ".doc": "Word anterior a 2007",
    ".xls": "Excel anterior a 2007",
    ".ppt": "PowerPoint anterior a 2007",
}


def extensiones_admitidas() -> List[str]:
    """Extensiones admitidas, sin el punto inicial, para el cargador."""
    return sorted(e.lstrip(".") for e in LECTORES)


def _compactar(texto: str) -> str:
    """Reduce las lineas en blanco consecutivas y los espacios sobrantes."""
    texto = re.sub(r"[ \t]+", " ", texto or "")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return "\n".join(linea.rstrip() for linea in texto.splitlines()).strip()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def leer(ruta: Union[str, Path]) -> Lectura:
    """
    Lee un documento y devuelve su texto junto con el detalle del proceso.

    No se propaga excepcion por un formato ilegible: se devuelve una lectura
    sin texto y con la advertencia correspondiente, de modo que la carga de un
    caso con varios documentos no se interrumpa por uno de ellos.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el documento: {ruta}")

    extension = ruta.suffix.lower()

    if extension in FORMATOS_HEREDADOS:
        return Lectura(
            metodo=f"formato heredado ({extension})",
            advertencias=[
                f"El formato {extension} ({FORMATOS_HEREDADOS[extension]}) no "
                f"puede abrirse directamente. Convierta el documento a "
                f"{extension}x o a PDF desde la propia aplicacion de origen."])

    lector = LECTORES.get(extension)
    if lector is None:
        raise FormatoNoSoportado(
            f"El formato '{extension or 'sin extension'}' no esta admitido. "
            f"Formatos admitidos: {', '.join(extensiones_admitidas())}.")

    try:
        return lector(ruta)
    except Exception as exc:
        return Lectura(
            metodo=f"lectura fallida ({extension})",
            advertencias=[f"No fue posible leer el documento: "
                          f"{type(exc).__name__}: {exc}"])
