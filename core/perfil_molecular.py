"""
Extraccion determinista del perfil molecular a partir del texto clinico.

Este modulo no utiliza un modelo de lenguaje: opera mediante expresiones
regulares sobre la terminologia empleada habitualmente en los informes
anatomopatologicos y de secuenciacion en espaniol.

Cumple dos funciones dentro del sistema:

  1. Alimentar el modulo de busqueda de ensayos clinicos, que requiere
     marcadores normalizados y no texto libre.
  2. Operar como capa de verificacion sobre la salida del modelo de lenguaje
     y como mecanismo de respaldo cuando no hay conexion disponible.

La segunda funcion es deliberada: un resultado obtenido por reglas explicitas
es auditable y reproducible, condicion necesaria en un dominio clinico.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Valores normalizados
# ---------------------------------------------------------------------------

MUTADO = "mutado"
NO_MUTADO = "no mutado"
CODELECION = "codelecion presente"
SIN_CODELECION = "codelecion ausente"
METILADO = "metilado"
NO_METILADO = "no metilado"
CONSERVADO = "conservado"
PERDIDO = "perdido"
AMPLIFICADO = "amplificado"
NO_AMPLIFICADO = "no amplificado"
NO_INFORMADO = "no informado"


@dataclass
class Marcador:
    """Resultado de la deteccion de un marcador molecular."""
    nombre: str
    valor: str = NO_INFORMADO
    detalle: str = ""
    evidencia: str = ""
    tipo_documento: str = ""

    @property
    def informado(self) -> bool:
        return self.valor != NO_INFORMADO


@dataclass
class PerfilMolecular:
    marcadores: Dict[str, Marcador] = field(default_factory=dict)

    def obtener(self, nombre: str) -> Marcador:
        return self.marcadores.get(nombre, Marcador(nombre=nombre))

    def valor(self, nombre: str) -> str:
        return self.obtener(nombre).valor

    @property
    def informados(self) -> Dict[str, Marcador]:
        return {k: v for k, v in self.marcadores.items() if v.informado}

    def como_texto(self) -> str:
        if not self.informados:
            return "No consta perfil molecular en la documentacion aportada."
        partes = []
        for nombre, m in self.informados.items():
            linea = f"{nombre}: {m.valor}"
            if m.detalle:
                linea += f" ({m.detalle})"
            partes.append(linea)
        return "; ".join(partes) + "."

    def como_dict(self) -> Dict[str, Dict]:
        return {
            nombre: {
                "valor": m.valor,
                "detalle": m.detalle,
                "evidencia": m.evidencia,
                "tipo_documento": m.tipo_documento,
            }
            for nombre, m in self.marcadores.items()
        }


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def _sin_tildes(texto: str) -> str:
    """Quita tildes para que la deteccion no dependa de la acentuacion."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _preparar(texto: str) -> str:
    return _sin_tildes(texto or "").lower()


def _oraciones(texto: str) -> List[str]:
    """Divide el texto en oraciones, respetando saltos de linea y punto y coma."""
    bruto = re.split(r"(?<=[.;])\s+|\n+", texto or "")
    return [o.strip() for o in bruto if o and o.strip()]


# La negacion se evalua dentro de una ventana acotada antes del marcador,
# para no arrastrar una negacion que pertenece a otra afirmacion de la oracion.
PATRON_NEGACION = re.compile(
    r"\b(no|sin|ausencia de|ausente|negativ[oa]s?|no se (?:detect|observ|evidenci|identific)\w*|"
    r"no (?:presenta|muestra|se halla|hallado|informad[oa]))\b"
)

PATRON_AFIRMACION = re.compile(
    r"\b(si|presente|positiv[oa]s?|se (?:detect|observ|evidenci|identific)\w*|"
    r"presenta|muestra|hallad[oa]|confirmad[oa])\b"
)


# Una oracion que describe la tecnica empleada no constituye un resultado.
# Sin este filtro, una linea del tipo "Metilacion de MGMT por pirosecuenciacion"
# seria interpretada erroneamente como un hallazgo positivo.
PATRON_CONTEXTO_METODO = re.compile(
    r"\b(?:metodo|metodologia|tecnica|panel|plataforma|se\s+(?:realiza|realizo|"
    r"efectua|efectuo|utiliza|utilizo|emplea|empleo)|mediante|"
    r"estudio\s+(?:solicitado|realizado)|determinacion\s+por)\b"
    r"|\bpor\s+(?:pirosecuenciacion|secuenciacion|fish|pcr|ngs|"
    r"inmunohistoquimica|ihq|hibridacion|metilacion\s+especifica|"
    r"electroforesis|western|array)\b"
)

# Terminos que indican un resultado efectivo y habilitan la interpretacion.
# Se excluyen deliberadamente los sustantivos "metilacion" y "mutacion" por si
# solos, ya que forman parte del nombre de la propia tecnica.
PATRON_RESULTADO = re.compile(
    r"\b(?:metilad\w*|hipermetilad\w*|mutad\w*|codelecion\w*|codelecionad\w*|"
    r"presente|ausente|ausencia|positiv\w*|negativ\w*|conservad\w*|perdid\w*|"
    r"perdida|amplificad\w*|amplificacion|detect\w*|identific\w*|observ\w*|"
    r"evidenci\w*|hallad\w*|wild\s*-?\s*type|wildtype|salvaje|"
    r"delecion\w*|ganancia|sobreexpres\w*)\b"
    r"|\b\d+(?:[.,]\d+)?\s*%"
    r"|\b[rc]\d{2,4}[a-z]\b"          # variantes puntuales: R132H, C228T
    r"|\bp\.\s*[a-z]\d+"              # nomenclatura proteica: p.R132H
)


def _es_solo_metodo(oracion_plana: str) -> bool:
    """
    Indica si la oracion describe unicamente la tecnica empleada, sin informar
    un resultado. En ese caso no debe extraerse ningun valor de marcador.

    Ejemplo de oracion descartada:
        "Metilacion de MGMT por pirosecuenciacion."
    Ejemplo de oracion conservada, pese a mencionar la tecnica:
        "Se detecta mutacion IDH1 R132H por secuenciacion."
    """
    if not PATRON_CONTEXTO_METODO.search(oracion_plana):
        return False
    return not PATRON_RESULTADO.search(oracion_plana)


def _hay_negacion_antes(texto_plano: str, inicio_marcador: int,
                        ventana: int = 60) -> bool:
    """Indica si hay una negacion en la ventana previa al marcador."""
    desde = max(0, inicio_marcador - ventana)
    previo = texto_plano[desde:inicio_marcador]
    # Un conector corta el alcance de la negacion anterior
    corte = max(previo.rfind(", "), previo.rfind(" y "), previo.rfind(" pero "))
    if corte != -1:
        previo = previo[corte:]
    return bool(PATRON_NEGACION.search(previo))


def _hay_negacion_despues(texto_plano: str, inicio_marcador: int,
                          ventana: int = 35) -> bool:
    """
    Indica si hay una negacion inmediatamente posterior al marcador.

    Cubre construcciones habituales del tipo "TP53 sin mutacion" o
    "EGFR negativo", en las que la negacion sigue al marcador en lugar de
    precederlo. La ventana se corta ante un conector o un signo de puntuacion
    para no capturar la negacion de una afirmacion distinta.
    """
    posterior = texto_plano[inicio_marcador:inicio_marcador + ventana]
    # Se descarta el propio nombre del marcador
    posterior = re.sub(r"^\S+\s*", "", posterior)
    corte = min(
        [p for p in (posterior.find(", "), posterior.find(" y "),
                     posterior.find(";"), posterior.find("."))
         if p != -1] or [len(posterior)]
    )
    return bool(PATRON_NEGACION.search(posterior[:corte]))


def _hay_negacion_cerca(texto_plano: str, inicio_marcador: int,
                        ventana: int = 60) -> bool:
    """Evalua la negacion tanto antes como inmediatamente despues del marcador."""
    return (_hay_negacion_antes(texto_plano, inicio_marcador, ventana)
            or _hay_negacion_despues(texto_plano, inicio_marcador))


# Separadores que delimitan afirmaciones independientes dentro de una oracion
PATRON_SEPARADOR_CLAUSULA = re.compile(r",|;|\s+y\s+|\s+e\s+|\|")


def _clausula(texto_plano: str, inicio_marcador: int) -> str:
    """
    Devuelve la clausula que contiene al marcador.

    Los informes de inmunohistoquimica enumeran varios marcadores separados
    por comas en una misma oracion, por ejemplo:

        "IHQ: GFAP +, IDH1 R132H negativo, ATRX conservado, Ki67 30%."

    Sin esta delimitacion, el termino "negativo" correspondiente a IDH1 seria
    atribuido erroneamente a ATRX. Acotar el analisis a la clausula del propio
    marcador evita esa contaminacion entre afirmaciones.
    """
    inicios = [m.end() for m in PATRON_SEPARADOR_CLAUSULA.finditer(texto_plano)
               if m.end() <= inicio_marcador]
    desde = max(inicios) if inicios else 0

    finales = [m.start() for m in PATRON_SEPARADOR_CLAUSULA.finditer(texto_plano)
               if m.start() > inicio_marcador]
    hasta = min(finales) if finales else len(texto_plano)

    # Si la clausula resultante no contiene el nombre del marcador, se
    # devuelve la oracion completa como resguardo.
    recorte = texto_plano[desde:hasta].strip()
    return recorte if recorte else texto_plano


# ---------------------------------------------------------------------------
# Reglas por marcador
# ---------------------------------------------------------------------------

def _detectar_idh(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    m = re.search(r"\bidh\s*-?\s*([12])?\b", oracion_plana)
    if not m:
        return None

    subtipo = f"IDH{m.group(1)}" if m.group(1) else "IDH"
    # Notaciones combinadas del tipo "IDH1/2" o "IDH 1 y 2"
    if re.search(r"idh\s*-?\s*1\s*(?:/|\s+y\s+|\s+e\s+)\s*2", oracion_plana):
        subtipo = "IDH1/2"

    # Formas explicitas que no dependen del analisis de negacion
    if re.search(r"idh\s*-?\s*(?:[12]\s*(?:/|\s+y\s+|\s+e\s+)?\s*[12]?)?\s*"
                 r"(?:wild\s*-?\s*type|wildtype|salvaje|nativo|no\s*mutad)", oracion_plana):
        return Marcador("IDH", NO_MUTADO, f"{subtipo} wild-type", oracion_original)
    if re.search(r"(?:wild\s*-?\s*type|wildtype|salvaje|nativo)\s*(?:para|de|del)?\s*idh", oracion_plana):
        return Marcador("IDH", NO_MUTADO, f"{subtipo} wild-type", oracion_original)

    # Mutacion puntual habitual
    puntual = re.search(r"\b(r132[a-z]|r172[a-z])\b", oracion_plana)

    if re.search(r"mutaci|mutad|mutant", oracion_plana) or puntual:
        if _hay_negacion_cerca(oracion_plana, m.start()):
            return Marcador("IDH", NO_MUTADO, f"{subtipo} sin mutacion", oracion_original)
        detalle = f"{subtipo} {puntual.group(1).upper()}" if puntual else f"{subtipo} mutado"
        return Marcador("IDH", MUTADO, detalle, oracion_original)

    if re.search(r"inmunohistoquimica|ihq", oracion_plana):
        if PATRON_NEGACION.search(oracion_plana):
            return Marcador("IDH", NO_MUTADO, f"{subtipo} IHQ negativa", oracion_original)
        if PATRON_AFIRMACION.search(oracion_plana):
            return Marcador("IDH", MUTADO, f"{subtipo} IHQ positiva", oracion_original)

    return None


def _detectar_1p19q(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if not re.search(r"1p\s*/?\s*19q|codelec|co-delec", oracion_plana):
        return None

    pos = oracion_plana.find("1p")
    if pos == -1:
        pos = max(oracion_plana.find("codelec"), 0)

    # Negacion o conservacion expresada antes del marcador
    if re.search(r"(?:no|sin|ausen|conserv|indemne|intact)\w*\s*(?:se\s+\w+\s+)?"
                 r"(?:la\s+)?(?:co-?delec\w*|1p)", oracion_plana):
        return Marcador("1p/19q", SIN_CODELECION, "sin codelecion", oracion_original)

    # Conservacion expresada despues del marcador ("1p/19q conservados")
    if re.search(r"1p\s*/?\s*19q[^.;]{0,40}?\b(conserv\w*|indemne\w*|intact\w*|"
                 r"sin\s+perdida|no\s+delecionad\w*)\b", oracion_plana):
        return Marcador("1p/19q", SIN_CODELECION, "sin codelecion", oracion_original)

    # Estado expresado tras dos puntos ("codelecion 1p/19q: ausente")
    if re.search(r"(?:co-?delec\w*|1p\s*/?\s*19q)[^.;]{0,30}:\s*"
                 r"(?:ausen\w*|negativ\w*|no\b)", oracion_plana):
        return Marcador("1p/19q", SIN_CODELECION, "sin codelecion", oracion_original)

    if re.search(r"codelec|co-delec|perdida combinada|delecion combinada", oracion_plana):
        if _hay_negacion_cerca(oracion_plana, pos):
            return Marcador("1p/19q", SIN_CODELECION, "sin codelecion", oracion_original)
        return Marcador("1p/19q", CODELECION, "codelecion 1p/19q", oracion_original)

    return None


def _detectar_mgmt(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if "mgmt" not in oracion_plana:
        return None

    pos = oracion_plana.find("mgmt")

    # Estudio no valorable: se evalua antes que cualquier otra regla, porque
    # la oracion contiene terminos de metilacion que de otro modo se
    # interpretarian como un resultado.
    if re.search(r"mgmt[^.;]{0,60}?\bno\s+(?:\w+\s+){0,2}"
                 r"(?:valorable|evaluable|concluyente|interpretable|informativ\w*)"
                 r"|\bno\s+(?:\w+\s+){0,2}(?:valorable|evaluable|concluyente)"
                 r"[^.;]{0,60}?mgmt"
                 r"|material\s+insuficiente", oracion_plana):
        return Marcador("MGMT", NO_INFORMADO, "estudio no valorable", oracion_original)

    # Descripcion de la tecnica sin resultado asociado
    if _es_solo_metodo(oracion_plana):
        return None

    # Forma explicita "no metilado" / "no metilacion"
    if re.search(r"\bno\s+metilad|\bno\s+metilaci|ausencia de metilaci|"
                 r"metilaci\w*\s+(?:ausente|negativ)", oracion_plana):
        return Marcador("MGMT", NO_METILADO, "promotor no metilado", oracion_original)

    # Estado expresado tras dos puntos ("metilacion del promotor de MGMT: ausente")
    if re.search(r"(?:metilaci\w*|mgmt)[^.;]{0,40}:\s*"
                 r"(?:ausen\w*|negativ\w*|no\s+metilad\w*|no\b)", oracion_plana):
        return Marcador("MGMT", NO_METILADO, "promotor no metilado", oracion_original)

    if re.search(r"hipermetilad|metilad|metilaci", oracion_plana):
        if _hay_negacion_cerca(oracion_plana, pos) or _hay_negacion_cerca(
                oracion_plana, oracion_plana.find("metilad") if "metilad" in oracion_plana else pos):
            return Marcador("MGMT", NO_METILADO, "promotor no metilado", oracion_original)
        detalle = "promotor metilado"
        porcentaje = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*%", oracion_plana)
        if porcentaje:
            detalle += f", {porcentaje.group(1).replace(',', '.')}%"
        return Marcador("MGMT", METILADO, detalle, oracion_original)

    return None


def _detectar_atrx(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if "atrx" not in oracion_plana:
        return None
    pos = oracion_plana.find("atrx")

    # El analisis se acota a la clausula del marcador para no capturar el
    # estado informado de otro marcador de la misma enumeracion.
    ambito = _clausula(oracion_plana, pos)
    pos_ambito = ambito.find("atrx")
    if pos_ambito == -1:
        pos_ambito = 0

    if re.search(r"perdida|perdid|ausencia|ausente|negativ|no expres", ambito):
        return Marcador("ATRX", PERDIDO, "perdida de expresion", oracion_original)
    if re.search(r"conserv|retenid|preserv|positiv|expres|indemne|intact", ambito):
        if _hay_negacion_cerca(ambito, pos_ambito):
            return Marcador("ATRX", PERDIDO, "perdida de expresion", oracion_original)
        return Marcador("ATRX", CONSERVADO, "expresion conservada", oracion_original)

    # Mutacion informada por secuenciacion
    if re.search(r"mutaci|mutad|perdida de funcion", ambito):
        if _hay_negacion_cerca(ambito, pos_ambito):
            return Marcador("ATRX", CONSERVADO, "sin mutacion", oracion_original)
        return Marcador("ATRX", PERDIDO, "mutacion con perdida de funcion", oracion_original)
    return None


def _detectar_tert(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if "tert" not in oracion_plana:
        return None
    pos = oracion_plana.find("tert")
    ambito = _clausula(oracion_plana, pos)
    pos_ambito = max(ambito.find("tert"), 0)

    if re.search(r"mutaci|mutad|c228t|c250t", ambito):
        if _hay_negacion_cerca(ambito, pos_ambito):
            return Marcador("TERT", NO_MUTADO, "promotor no mutado", oracion_original)
        variante = re.search(r"\b(c228t|c250t)\b", ambito)
        detalle = f"promotor mutado {variante.group(1).upper()}" if variante else "promotor mutado"
        return Marcador("TERT", MUTADO, detalle, oracion_original)
    return None


def _detectar_egfr(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if "egfr" not in oracion_plana:
        return None
    pos = oracion_plana.find("egfr")
    ambito = _clausula(oracion_plana, pos)
    pos_ambito = max(ambito.find("egfr"), 0)

    if re.search(r"amplificaci|amplificad", ambito):
        if _hay_negacion_cerca(ambito, pos_ambito):
            return Marcador("EGFR", NO_AMPLIFICADO, "sin amplificacion", oracion_original)
        detalle = "amplificacion"
        if re.search(r"vi{2,3}\b|v\s*3\b", oracion_plana):
            detalle += " con variante EGFRvIII"
        return Marcador("EGFR", AMPLIFICADO, detalle, oracion_original)
    return None


def _detectar_tp53(oracion_plana: str, oracion_original: str) -> Optional[Marcador]:
    if "tp53" not in oracion_plana and "p53" not in oracion_plana:
        return None
    pos = oracion_plana.find("tp53")
    if pos == -1:
        pos = max(oracion_plana.find("p53"), 0)

    ambito = _clausula(oracion_plana, pos)
    pos_ambito = ambito.find("p53")
    if pos_ambito == -1:
        pos_ambito = 0

    if re.search(r"sin\s+sobreexpres|no\s+sobreexpres", ambito):
        return Marcador("TP53", NO_MUTADO, "sin sobreexpresion", oracion_original)

    if re.search(r"mutaci|mutad|sobreexpres|acumulacion nuclear", ambito):
        if _hay_negacion_cerca(ambito, pos_ambito):
            return Marcador("TP53", NO_MUTADO, "sin mutacion", oracion_original)
        return Marcador("TP53", MUTADO, "mutacion detectada", oracion_original)
    return None


DETECTORES = {
    "IDH": _detectar_idh,
    "1p/19q": _detectar_1p19q,
    "MGMT": _detectar_mgmt,
    "ATRX": _detectar_atrx,
    "TERT": _detectar_tert,
    "EGFR": _detectar_egfr,
    "TP53": _detectar_tp53,
}

# Prioridad de las fuentes documentales ante resultados discrepantes.
# El informe de secuenciacion prevalece sobre el resto por ser la tecnica
# de mayor especificidad para la determinacion molecular.
PRIORIDAD_DOCUMENTO = {
    "genomica": 3,
    "anatomia_patologica": 2,
    "historia_clinica": 1,
    "imagenes": 0,
}


def extraer_perfil(fragmentos: List) -> PerfilMolecular:
    """
    Extrae el perfil molecular a partir de una lista de fragmentos.

    Cada fragmento debe exponer los atributos `texto` y `tipo_documento`
    (objeto Fragmento) o bien ser un diccionario con esas claves.

    Ante resultados discrepantes entre documentos, prevalece el de mayor
    prioridad documental; a igual prioridad, prevalece el primero detectado.
    """
    perfil = PerfilMolecular()
    prioridad_actual: Dict[str, int] = {}

    for fragmento in fragmentos or []:
        if isinstance(fragmento, dict):
            texto = fragmento.get("texto", "")
            tipo_doc = fragmento.get("tipo_documento", "")
        else:
            texto = getattr(fragmento, "texto", "")
            tipo_doc = getattr(fragmento, "tipo_documento", "")

        peso = PRIORIDAD_DOCUMENTO.get(tipo_doc, 0)

        for oracion in _oraciones(texto):
            plana = _preparar(oracion)

            # Las oraciones que solo describen la tecnica empleada no aportan
            # resultados y se descartan antes de aplicar los detectores.
            # MGMT se exceptua porque su detector contempla internamente el
            # caso de estudio no valorable, que si debe registrarse.
            solo_metodo = _es_solo_metodo(plana)

            for nombre, detector in DETECTORES.items():
                if solo_metodo and nombre != "MGMT":
                    continue
                resultado = detector(plana, oracion.strip())
                if resultado is None:
                    continue
                if nombre in perfil.marcadores and peso <= prioridad_actual.get(nombre, -1):
                    continue
                resultado.tipo_documento = tipo_doc
                perfil.marcadores[nombre] = resultado
                prioridad_actual[nombre] = peso

    return perfil


def resumir_para_busqueda(perfil: PerfilMolecular) -> List[Tuple[str, str]]:
    """
    Devuelve los marcadores accionables para la busqueda de ensayos clinicos,
    en forma de pares (marcador, valor).

    Solo se incluyen los marcadores efectivamente informados, de manera de no
    introducir criterios de busqueda que la documentacion no respalda.
    """
    return [(n, m.valor) for n, m in perfil.informados.items()]
