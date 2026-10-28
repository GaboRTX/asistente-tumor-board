"""
Modulo de busqueda y correspondencia de ensayos clinicos.

Consulta la API publica de ClinicalTrials.gov (version 2) y evalua la
correspondencia entre el perfil molecular del caso y los criterios de
elegibilidad de cada estudio.

Consideraciones de disenio
--------------------------
1. La correspondencia se calcula mediante reglas explicitas sobre marcadores
   normalizados, no mediante un modelo de lenguaje. El motivo es que el
   criterio de correspondencia debe poder exhibirse y auditarse: el sistema
   informa que marcador origino cada coincidencia.

2. El resultado nunca constituye una recomendacion terapeutica. Se presenta
   como un listado de estudios a considerar, cuya elegibilidad definitiva
   debe ser evaluada por el equipo tratante contra el protocolo completo.

3. Ante la ausencia de conectividad se recurre a una copia local de
   referencia, de modo que el modulo siga siendo demostrable sin internet.
   El origen de los datos se informa siempre de forma explicita.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.config import RUTA_CACHE_ENSAYOS, TIMEOUT_RED


URL_API = "https://clinicaltrials.gov/api/v2/studies"

ORIGEN_API = "ClinicalTrials.gov (consulta en linea)"
ORIGEN_CACHE = "Copia local de referencia (sin conexion)"


@dataclass
class Ensayo:
    nct: str
    titulo: str
    fase: str
    estado: str
    condiciones: List[str] = field(default_factory=list)
    intervenciones: List[str] = field(default_factory=list)
    criterios: str = ""
    paises: List[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://clinicaltrials.gov/study/{self.nct}"

    def como_dict(self) -> Dict:
        d = {
            "nct": self.nct, "titulo": self.titulo, "fase": self.fase,
            "estado": self.estado, "condiciones": self.condiciones,
            "intervenciones": self.intervenciones, "paises": self.paises,
            "url": self.url,
        }
        return d


@dataclass
class Correspondencia:
    ensayo: Ensayo
    puntaje: float
    coincidencias: List[str] = field(default_factory=list)
    exclusiones: List[str] = field(default_factory=list)
    compatibilidades: List[str] = field(default_factory=list)

    @property
    def elegible(self) -> bool:
        """Indica que no se detectaron criterios que excluyan al caso."""
        return not self.exclusiones

    def como_dict(self) -> Dict:
        d = self.ensayo.como_dict()
        d.update({
            "puntaje": round(self.puntaje, 3),
            "coincidencias": self.coincidencias,
            "exclusiones": self.exclusiones,
            "compatibilidades": self.compatibilidades,
            "elegible": self.elegible,
        })
        return d


# ---------------------------------------------------------------------------
# Obtencion de estudios
# ---------------------------------------------------------------------------

def _parsear_estudio(estudio: Dict) -> Optional[Ensayo]:
    """Convierte la estructura devuelta por la API en un objeto Ensayo."""
    try:
        proto = estudio.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        estado_mod = proto.get("statusModule", {})
        disenio = proto.get("designModule", {})
        cond = proto.get("conditionsModule", {})
        elig = proto.get("eligibilityModule", {})
        brazos = proto.get("armsInterventionsModule", {})
        ubic = proto.get("contactsLocationsModule", {})

        nct = ident.get("nctId", "")
        if not nct:
            return None

        fases = disenio.get("phases", []) or []
        intervenciones = [i.get("name", "") for i in brazos.get("interventions", []) or []]
        paises = sorted({l.get("country", "") for l in ubic.get("locations", []) or []
                         if l.get("country")})

        return Ensayo(
            nct=nct,
            titulo=ident.get("briefTitle", "") or ident.get("officialTitle", ""),
            fase=", ".join(f.replace("PHASE", "Fase ") for f in fases) or "No especificada",
            estado=estado_mod.get("overallStatus", ""),
            condiciones=cond.get("conditions", []) or [],
            intervenciones=[i for i in intervenciones if i],
            criterios=elig.get("eligibilityCriteria", "") or "",
            paises=paises,
        )
    except Exception:
        return None


def consultar_api(termino: str = "glioma", maximo: int = 50,
                  solo_reclutando: bool = True) -> Tuple[List[Ensayo], str]:
    """
    Consulta la API publica de ClinicalTrials.gov.

    Devuelve (lista de ensayos, origen). Ante cualquier error devuelve una
    lista vacia, dejando a la capa superior la decision de recurrir a la
    copia local.
    """
    try:
        import requests

        parametros = {
            "query.cond": termino,
            "pageSize": min(int(maximo), 100),
            "format": "json",
        }
        if solo_reclutando:
            parametros["filter.overallStatus"] = "RECRUITING|NOT_YET_RECRUITING"

        respuesta = requests.get(URL_API, params=parametros, timeout=TIMEOUT_RED)
        respuesta.raise_for_status()
        datos = respuesta.json()

        ensayos = []
        for estudio in datos.get("studies", []) or []:
            e = _parsear_estudio(estudio)
            if e:
                ensayos.append(e)
        return ensayos, ORIGEN_API
    except Exception:
        return [], ""


def cargar_cache(ruta: Optional[Path] = None) -> List[Ensayo]:
    """Carga la copia local de estudios de referencia."""
    ruta = Path(ruta) if ruta else RUTA_CACHE_ENSAYOS
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return []

    ensayos = []
    for d in datos.get("estudios", []):
        ensayos.append(Ensayo(
            nct=d.get("nct", ""), titulo=d.get("titulo", ""),
            fase=d.get("fase", ""), estado=d.get("estado", ""),
            condiciones=d.get("condiciones", []),
            intervenciones=d.get("intervenciones", []),
            criterios=d.get("criterios", ""), paises=d.get("paises", []),
        ))
    return ensayos


def guardar_cache(ensayos: List[Ensayo], ruta: Optional[Path] = None) -> None:
    """Persiste una copia local de los estudios obtenidos de la API."""
    ruta = Path(ruta) if ruta else RUTA_CACHE_ENSAYOS
    datos = {
        "estudios": [
            {**e.como_dict(), "criterios": e.criterios} for e in ensayos
        ]
    }
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def obtener_ensayos(termino: str = "glioma", maximo: int = 50,
                    preferir_cache: bool = False) -> Tuple[List[Ensayo], str]:
    """
    Obtiene los estudios, recurriendo a la copia local si la API no responde.
    """
    if not preferir_cache:
        ensayos, origen = consultar_api(termino, maximo)
        if ensayos:
            try:
                guardar_cache(ensayos)
            except Exception:
                pass
            return ensayos, origen

    return cargar_cache(), ORIGEN_CACHE


# ---------------------------------------------------------------------------
# Reglas de correspondencia por marcador
# ---------------------------------------------------------------------------

# Patrones que identifican cada estado de marcador dentro del texto de los
# criterios de elegibilidad, redactados en ingles por ser el idioma del
# registro.
PATRONES_ESTADO = {
    ("IDH", "mutado"): [r"idh[\s\-/12]*\s*mutant", r"idh[\s\-/12]*\s*mutat",
                        r"mutant\s+idh", r"idh1?\s*r132", r"idh2?\s*r172"],
    ("IDH", "no mutado"): [r"idh[\s\-/12]*\s*wild[\s\-]*type", r"idh[\s\-/12]*\s*wildtype",
                           r"wild[\s\-]*type\s+idh", r"idh[\s\-]*non[\s\-]*mutant"],
    ("1p/19q", "codelecion presente"): [r"1p\s*/?\s*19q[\s\-]*co[\s\-]*delet",
                                        r"co[\s\-]*deleted\s+1p"],
    ("1p/19q", "codelecion ausente"): [r"non[\s\-]*co[\s\-]*delet",
                                       r"1p\s*/?\s*19q[\s\-]*intact",
                                       r"without\s+1p\s*/?\s*19q",
                                       r"1p\s*/?\s*19q[\s\-]*retained"],
    ("MGMT", "metilado"): [r"mgmt[^.]{0,30}\bmethylat", r"\bmethylated\s+mgmt"],
    ("MGMT", "no metilado"): [r"mgmt[^.]{0,30}unmethylat", r"unmethylated\s+mgmt",
                              r"mgmt[^.]{0,30}non[\s\-]*methylat"],
    ("EGFR", "amplificado"): [r"egfr\s*amplif", r"egfrviii", r"egfr\s*viii"],
    ("EGFR", "no amplificado"): [r"without\s+egfr\s*amplif", r"egfr\s*non[\s\-]*amplif"],
    ("TERT", "mutado"): [r"tert\s*(?:promoter\s*)?mutat", r"c228t", r"c250t"],
    ("TERT", "no mutado"): [r"tert[^.]{0,30}wild[\s\-]*type"],
    ("ATRX", "perdido"): [r"atrx\s*(?:loss|mutat|deficien|negative)"],
    ("ATRX", "conservado"): [r"atrx\s*(?:retained|intact|preserved)"],
    ("TP53", "mutado"): [r"tp53\s*mutat", r"\bp53\s*mutat"],
    ("TP53", "no mutado"): [r"tp53[^.]{0,30}wild[\s\-]*type"],
}

# Estado contrario de cada valor, utilizado para detectar incompatibilidad
OPUESTOS = {
    "mutado": "no mutado",
    "no mutado": "mutado",
    "metilado": "no metilado",
    "no metilado": "metilado",
    "codelecion presente": "codelecion ausente",
    "codelecion ausente": "codelecion presente",
    "amplificado": "no amplificado",
    "no amplificado": "amplificado",
    "perdido": "conservado",
    "conservado": "perdido",
}


# Encabezados que delimitan las secciones del texto de elegibilidad
PATRON_INCLUSION = re.compile(
    r"\b(?:inclusion\s*criteria|inclusion|eligible\s+patients?\s+must|"
    r"key\s+inclusion)\b[:\s]*", re.IGNORECASE)
PATRON_EXCLUSION = re.compile(
    r"\b(?:exclusion\s*criteria|exclusion|ineligible|"
    r"patients?\s+(?:will\s+be\s+)?excluded|key\s+exclusion)\b[:\s]*",
    re.IGNORECASE)


def separar_criterios(texto: str) -> Tuple[str, str]:
    """
    Separa el texto de elegibilidad en sus secciones de inclusion y exclusion.

    Esta separacion es indispensable para la correccion del modulo: un
    marcador mencionado bajo la seccion de exclusion indica lo contrario de
    uno mencionado bajo inclusion. Evaluar el texto como un bloque unico
    produce correspondencias invertidas, es decir, estudios propuestos
    precisamente a los pacientes que no son elegibles para ellos.
    """
    texto = texto or ""
    if not texto.strip():
        return "", ""

    marca_exclusion = PATRON_EXCLUSION.search(texto)
    if not marca_exclusion:
        # Sin seccion de exclusion explicita, todo el texto se trata como
        # criterio de inclusion.
        return texto, ""

    inclusion = texto[:marca_exclusion.start()]
    exclusion = texto[marca_exclusion.end():]

    # Se descarta el encabezado de inclusion si esta presente
    marca_inclusion = PATRON_INCLUSION.search(inclusion)
    if marca_inclusion:
        inclusion = inclusion[marca_inclusion.end():]

    return inclusion, exclusion


def _coincide(patrones: List[str], texto: str) -> bool:
    return any(re.search(p, texto) for p in patrones)


# Terminos que niegan la presencia del marcador que los sigue. Son relevantes
# dentro de la seccion de exclusion: "exclusion: absence of EGFRvIII" excluye
# a los pacientes que NO presentan el marcador, de modo que un paciente que si
# lo presenta resulta compatible con el estudio.
PATRON_AUSENCIA_EN = re.compile(
    r"\b(?:absence\s+of|lack\s+of|without|negative\s+for|no\s+evidence\s+of|"
    r"not\s+(?:harboring|having|presenting)|non[\s\-]|un(?=methylat)|"
    r"failure\s+to\s+(?:demonstrate|show))\s*$"
)


def _coincide_no_negado(patrones: List[str], texto: str,
                        ventana: int = 30) -> bool:
    """
    Indica si alguno de los patrones aparece sin una negacion inmediatamente
    previa. Se utiliza dentro de la seccion de exclusion para distinguir
    "exclusion: EGFR amplification" de "exclusion: absence of EGFR amplification".
    """
    for patron in patrones:
        for hallazgo in re.finditer(patron, texto):
            desde = max(0, hallazgo.start() - ventana)
            previo = texto[desde:hallazgo.start()]
            if not PATRON_AUSENCIA_EN.search(previo):
                return True
    return False


def evaluar_correspondencia(ensayo: Ensayo,
                            marcadores: List[Tuple[str, str]]) -> Correspondencia:
    """
    Evalua un ensayo contra el perfil molecular del caso.

    Para cada marcador del caso se contrastan cuatro situaciones:

      - El estado del paciente figura en los criterios de INCLUSION:
        constituye una coincidencia a favor.
      - El estado del paciente figura en los criterios de EXCLUSION:
        el paciente queda excluido del estudio.
      - El estado CONTRARIO figura en los criterios de INCLUSION:
        el estudio requiere un estado distinto, por lo que el paciente
        no es elegible.
      - El estado CONTRARIO figura en los criterios de EXCLUSION:
        se interpreta como compatibilidad implicita, con menor peso que
        una coincidencia explicita.

    El puntaje resultante nunca constituye una recomendacion: expresa
    unicamente el grado de respaldo documental de la correspondencia.
    """
    inclusion_bruta, exclusion_bruta = separar_criterios(ensayo.criterios)
    contexto = " ".join([ensayo.titulo or "", " ".join(ensayo.condiciones or [])]).lower()
    inclusion = (inclusion_bruta + " " + contexto).lower()
    exclusion = exclusion_bruta.lower()

    coincidencias: List[str] = []
    exclusiones: List[str] = []
    compatibilidades: List[str] = []

    for nombre, valor in marcadores:
        patrones_valor = PATRONES_ESTADO.get((nombre, valor), [])
        opuesto = OPUESTOS.get(valor)
        patrones_opuesto = PATRONES_ESTADO.get((nombre, opuesto), []) if opuesto else []

        if patrones_valor and _coincide_no_negado(patrones_valor, exclusion):
            exclusiones.append(
                f"{nombre} ({valor}): figura entre los criterios de exclusion del estudio"
            )
            continue

        if patrones_opuesto and _coincide(patrones_opuesto, inclusion):
            exclusiones.append(
                f"{nombre}: el estudio requiere '{opuesto}' y el caso presenta '{valor}'"
            )
            continue

        if patrones_valor and _coincide(patrones_valor, inclusion):
            coincidencias.append(f"{nombre}: {valor}")
            continue

        # El estudio excluye el estado contrario, o excluye la ausencia del
        # estado que el caso presenta: en ambos casos hay compatibilidad.
        if patrones_opuesto and _coincide(patrones_opuesto, exclusion):
            compatibilidades.append(
                f"{nombre}: el estudio excluye '{opuesto}'; el caso presenta '{valor}'"
            )
        elif patrones_valor and _coincide(patrones_valor, exclusion):
            compatibilidades.append(
                f"{nombre}: el estudio excluye la ausencia de '{valor}', "
                f"que el caso presenta"
            )

    base = max(len(marcadores), 1)
    puntaje = (len(coincidencias) + 0.5 * len(compatibilidades)) / base
    if exclusiones:
        puntaje = 0.0

    return Correspondencia(ensayo=ensayo, puntaje=puntaje,
                           coincidencias=coincidencias, exclusiones=exclusiones,
                           compatibilidades=compatibilidades)


def buscar_para_perfil(marcadores: List[Tuple[str, str]],
                       termino: str = "glioma",
                       maximo_resultados: int = 10,
                       preferir_cache: bool = False
                       ) -> Tuple[List[Correspondencia], str, Dict]:
    """
    Busca y ordena los ensayos aplicables al perfil molecular indicado.

    Devuelve (correspondencias ordenadas, origen de los datos, resumen).
    """
    ensayos, origen = obtener_ensayos(termino, maximo=50,
                                      preferir_cache=preferir_cache)

    correspondencias = [evaluar_correspondencia(e, marcadores) for e in ensayos]

    # Los estudios que excluyen explicitamente al caso no se proponen.
    # Los restantes se ordenan por respaldo documental de la correspondencia.
    excluidos = [c for c in correspondencias if not c.elegible]
    elegibles = [c for c in correspondencias if c.elegible]

    con_coincidencia = [c for c in elegibles if c.coincidencias or c.compatibilidades]
    sin_criterio = [c for c in elegibles
                    if not c.coincidencias and not c.compatibilidades]

    con_coincidencia.sort(key=lambda c: (-c.puntaje, c.ensayo.nct))
    sin_criterio.sort(key=lambda c: c.ensayo.nct)

    seleccion = (con_coincidencia + sin_criterio)[:maximo_resultados]

    resumen = {
        "total_evaluados": len(correspondencias),
        "con_coincidencia": len(con_coincidencia),
        "descartados_por_exclusion": len(excluidos),
        "sin_criterio_molecular": len(sin_criterio),
        "marcadores_utilizados": [f"{n}: {v}" for n, v in marcadores],
    }

    return seleccion, origen, resumen
