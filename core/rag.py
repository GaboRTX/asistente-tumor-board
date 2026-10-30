"""
Modulo de recuperacion aumentada por generacion (RAG).

Responsabilidad: producir el resumen estructurado del caso a partir de los
fragmentos documentales, citando la fuente de cada campo.

Principio rector del modulo
---------------------------
Ningun campo del resumen puede afirmar un dato que no este respaldado por un
fragmento concreto de la documentacion aportada. Cuando el dato no consta, el
sistema lo declara explicitamente en lugar de completarlo por inferencia.

Esta restriccion es la contrapartida directa de la leccion extraida del caso
IBM Watson for Oncology: la utilidad clinica de la herramienta depende de que
cada afirmacion sea verificable contra su fuente.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core import llm
from core.config import (
    CAMPOS_RESUMEN,
    CAMPOS_SIEMPRE_DETERMINISTAS,
    TEXTO_SIN_DATO,
    TOP_K_CORRECCIONES,
    TOP_K_FRAGMENTOS,
    UMBRAL_SIMILITUD_CORRECCION,
)
from core.perfil_molecular import extraer_perfil
from core.vectorizacion import IndiceVectorial, construir_indice


# ---------------------------------------------------------------------------
# Consultas de recuperacion por campo
# ---------------------------------------------------------------------------

CONSULTAS_CAMPO = {
    "datos_clinicos": "edad sexo motivo de consulta sintomas presentacion clinica "
                      "estado funcional Karnofsky ECOG",
    "antecedentes": "antecedentes personales patologicos comorbilidades "
                    "medicacion habitual antecedentes familiares",
    "hallazgos_patologia": "diagnostico histopatologico tipo tumoral grado OMS "
                           "indice proliferativo Ki-67 biopsia",
    "perfil_molecular": "IDH mutacion codelecion 1p/19q metilacion MGMT ATRX TERT "
                        "EGFR TP53 secuenciacion perfil molecular",
    "hallazgos_imagenes": "resonancia magnetica tomografia lesion localizacion "
                          "realce edema efecto de masa tamanio",
    "tratamientos_previos": "cirugia reseccion radioterapia quimioterapia "
                            "temozolomida esquema dosis tratamiento recibido",
}


@dataclass
class CampoResumen:
    """Un campo del resumen estructurado con su respaldo documental."""
    clave: str
    etiqueta: str
    contenido: str
    fuentes: List[Dict] = field(default_factory=list)
    correcciones_aplicadas: List[Dict] = field(default_factory=list)

    @property
    def tiene_dato(self) -> bool:
        return self.contenido.strip() != TEXTO_SIN_DATO

    def como_dict(self) -> Dict:
        return {
            "clave": self.clave,
            "etiqueta": self.etiqueta,
            "contenido": self.contenido,
            "fuentes": self.fuentes,
            "correcciones_aplicadas": self.correcciones_aplicadas,
        }


@dataclass
class ResultadoResumen:
    campos: List[CampoResumen]
    perfil_molecular: Dict
    modo: str
    modelo: str
    segundos: float
    advertencias: List[str] = field(default_factory=list)

    def como_dict(self) -> Dict:
        return {
            "campos": [c.como_dict() for c in self.campos],
            "perfil_molecular": self.perfil_molecular,
            "modo": self.modo,
            "modelo": self.modelo,
            "segundos": self.segundos,
            "advertencias": self.advertencias,
        }

    def campo(self, clave: str) -> Optional[CampoResumen]:
        for c in self.campos:
            if c.clave == clave:
                return c
        return None


# ---------------------------------------------------------------------------
# Construccion del prompt
# ---------------------------------------------------------------------------

INSTRUCCION_BASE = """Actuas como asistente de sintesis documental para una junta multidisciplinaria de neuro-oncologia.

Tu tarea es completar un resumen estructurado del caso a partir EXCLUSIVAMENTE de los fragmentos documentales que se te proveen.

Reglas de obligado cumplimiento:
1. No afirmes ningun dato que no este explicitamente presente en los fragmentos provistos.
2. Si un dato no consta en los fragmentos, escribi exactamente: "{sin_dato}"
3. No infieras diagnosticos, pronosticos ni conductas terapeuticas.
4. No sugieras tratamientos.
5. Redacta en espaniol, en tercera persona, en registro clinico, de forma concisa.
6. Para cada campo, indica los numeros de fragmento en los que te basaste.

Respondes UNICAMENTE con un objeto JSON, sin texto adicional ni delimitadores de bloque de codigo, con esta estructura exacta:
{{"campos": {{"<clave_campo>": {{"contenido": "<texto>", "fragmentos": [<numeros>]}}}}}}
"""


def construir_prompt(campos_solicitados: List[Tuple[str, str]],
                     fragmentos_recuperados: List[Tuple[Dict, float, str]],
                     correcciones: Optional[List[Dict]] = None) -> str:
    """Arma el prompt enviado al modelo de lenguaje."""
    partes = [INSTRUCCION_BASE.format(sin_dato=TEXTO_SIN_DATO)]

    if correcciones:
        partes.append(
            "\nCORRECCIONES PREVIAS VALIDADAS POR ESPECIALISTAS\n"
            "Las siguientes reglas fueron establecidas por profesionales a partir de "
            "errores detectados en casos anteriores. Tienen prioridad sobre tu "
            "interpretacion por defecto, pero NO habilitan a afirmar datos ausentes "
            "en los fragmentos de este caso.\n"
        )
        for i, c in enumerate(correcciones, 1):
            partes.append(f"  R{i}. {c.get('regla', '')}")

    partes.append("\nFRAGMENTOS DOCUMENTALES DEL CASO\n")
    for i, (meta, _score, texto) in enumerate(fragmentos_recuperados, 1):
        etiqueta = meta.get("etiqueta_fuente", meta.get("tipo_documento", "documento"))
        partes.append(f"[Fragmento {i}] ({etiqueta})\n{texto}\n")

    partes.append("\nCAMPOS A COMPLETAR\n")
    for clave, etiqueta in campos_solicitados:
        partes.append(f"  - {clave}: {etiqueta}")

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Generacion determinista de respaldo
# ---------------------------------------------------------------------------

PATRONES_CAMPO = {
    "datos_clinicos": [
        r"\b\d{1,3}\s*(?:anios|anos|años)\b",
        r"\b(?:paciente|varon|var[oó]n|mujer|masculino|femenino)\b",
        r"\b(?:cefalea|convulsi|crisis|deficit|d[eé]ficit|hemiparesia|afasia|"
        r"mareo|vomito|v[oó]mito|naus|consulta)\w*",
        r"\b(?:karnofsky|kps|ecog)\b",
    ],
    "antecedentes": [
        r"\bantecedent\w*", r"\b(?:hipertensi|diabet|tabaqui|alergi|"
        r"comorbilidad|medicaci[oó]n habitual)\w*",
    ],
    "hallazgos_patologia": [
        r"\b(?:astrocitoma|oligodendroglioma|glioblastoma|glioma|ependimoma)\w*",
        r"\bgrado\s+(?:[1-4]|i{1,3}v?)\b",
        r"\b(?:ki-?67|indice proliferativo|mitosis|necrosis|"
        r"proliferaci[oó]n microvascular|biopsia|histolog)\w*",
        r"\boms\s*20\d{2}\b",
    ],
    "hallazgos_imagenes": [
        r"\b(?:resonancia|rm|rmn|tomografia|tomograf[ií]a|tc)\b",
        r"\b(?:lesi[oó]n|realce|edema|efecto de masa|captaci[oó]n|"
        r"frontal|temporal|parietal|occipital|insular|talamic)\w*",
        r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm)\b",
    ],
    "tratamientos_previos": [
        r"\b(?:cirug[ií]a|resecci[oó]n|exeresis|ex[eé]resis|biopsia estereotaxica)\w*",
        r"\b(?:radioterapia|rt|gy|radiocirug)\w*",
        r"\b(?:quimioterapia|temozolomida|tmz|pcv|lomustina|bevacizumab|"
        r"vorasidenib|carmustina)\w*",
        r"\b(?:ciclo|esquema|adyuvante|concomitante|neoadyuvante)\w*",
    ],
}


# Los documentos clinicos intercalan encabezados de seccion entre las
# afirmaciones. Incorporarlos al resumen produce un texto entrecortado, del
# tipo "Varon de 41 anios. DATOS DEL PACIENTE Karnofsky 90".
PATRON_ENCABEZADO = re.compile(
    r"^[A-ZÁÉÍÓÚÑ0-9 ,.:/()-]{3,}$")


# Los documentos incorporan leyendas sobre su propia naturaleza, como los
# avisos de confidencialidad o la constancia de que se trata de material de
# demostracion. Constituyen metadatos del documento y no informacion
# asistencial, de modo que no corresponde incorporarlas al resumen.
PATRON_LEYENDA = re.compile(
    r"documento sintetico|no corresponde a un paciente real|"
    r"material de demostracion|documento de demostracion|"
    r"uso exclusivo|confidencial|prohibida su reproduccion|"
    r"este informe (?:no )?debe|pagina \d+ de \d+",
    re.IGNORECASE)


def _es_oracion_truncada(oracion: str) -> bool:
    """
    Indica si la oracion es el remanente de otra, cortada por el limite de un
    fragmento.

    La fragmentacion se solapa, de modo que la oracion completa suele estar
    disponible en el fragmento contiguo. Conviene entonces descartar el
    remanente antes que exhibirlo: una oracion asistencial comienza en
    mayuscula, en un digito o en un signo de apertura.
    """
    texto = (oracion or "").strip()
    if not texto:
        return True
    primero = texto[0]
    return not (primero.isupper() or primero.isdigit() or primero in "¿¡(\"'")


def _es_leyenda(oracion: str) -> bool:
    """Indica si la oracion describe al documento y no al paciente."""
    return bool(PATRON_LEYENDA.search(oracion))


def _es_encabezado(oracion: str) -> bool:
    """
    Indica si la linea corresponde a un encabezado de seccion.

    Se consideran tales las lineas escritas integramente en mayusculas, que
    en la documentacion clinica delimitan secciones y no contienen
    informacion asistencial.
    """
    limpia = oracion.strip().rstrip(":").strip()
    if len(limpia) < 3:
        return True
    letras = [c for c in limpia if c.isalpha()]
    if not letras:
        return True
    return all(c.isupper() for c in letras)


def _normalizar_para_comparar(oracion: str) -> str:
    """Representacion reducida de una oracion, para detectar repeticiones."""
    import unicodedata
    plano = unicodedata.normalize("NFD", oracion.lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plano).strip()


def _es_redundante(candidata: str, seleccionadas: List[str]) -> bool:
    """
    Indica si la oracion reitera informacion ya incorporada al resumen.

    Los documentos repiten un mismo dato en distintos apartados, por ejemplo
    la escala funcional al ingreso y en el posoperatorio. Sin este control el
    resumen consigna dos veces la misma afirmacion.
    """
    nueva = _normalizar_para_comparar(candidata)
    if not nueva:
        return True

    palabras_nuevas = set(nueva.split())
    for previa in seleccionadas:
        anterior = _normalizar_para_comparar(previa)
        if nueva in anterior or anterior in nueva:
            return True
        palabras_previas = set(anterior.split())
        if not palabras_nuevas or not palabras_previas:
            continue
        comunes = palabras_nuevas & palabras_previas
        proporcion = len(comunes) / min(len(palabras_nuevas),
                                        len(palabras_previas))
        if proporcion > 0.75:
            return True
    return False


def _oraciones_relevantes(texto: str, patrones: List[str],
                          maximo: int = 4) -> List[str]:
    """
    Selecciona las oraciones de mayor correspondencia con los patrones del
    campo, descartando los encabezados de seccion y las reiteraciones.
    """
    oraciones = [o.strip() for o in re.split(r"(?<=[.;])\s+|\n+", texto or "")
                 if o and o.strip()]

    puntuadas = []
    for posicion, o in enumerate(oraciones):
        if _es_encabezado(o) or _es_leyenda(o) or _es_oracion_truncada(o):
            continue
        plano = o.lower()
        puntaje = sum(1 for p in patrones
                      if re.search(p, plano, flags=re.IGNORECASE))
        if puntaje:
            puntuadas.append((puntaje, posicion, o))

    # Mayor correspondencia primero; a igual correspondencia se conserva el
    # orden del documento, que refleja la secuencia clinica de los hechos.
    puntuadas.sort(key=lambda t: (-t[0], t[1]))

    seleccionadas: List[str] = []
    for _puntaje, _pos, o in puntuadas:
        if len(seleccionadas) >= maximo:
            break
        if _es_redundante(o, seleccionadas):
            continue
        seleccionadas.append(o)

    return seleccionadas


def generar_campo_determinista(clave: str,
                               fragmentos: List[Tuple[Dict, float, str]],
                               perfil) -> Tuple[str, List[int]]:
    """
    Genera el contenido de un campo mediante reglas, sin modelo de lenguaje.

    Devuelve (contenido, indices de fragmento utilizados).
    """
    if clave == "perfil_molecular":
        contenido = perfil.como_texto()
        indices = []
        for i, (meta, _s, texto) in enumerate(fragmentos, 1):
            if any(m.evidencia and m.evidencia in texto
                   for m in perfil.informados.values()):
                indices.append(i)
        if not perfil.informados:
            return TEXTO_SIN_DATO, []
        return contenido, indices

    patrones = PATRONES_CAMPO.get(clave, [])
    seleccionadas: List[str] = []
    indices: List[int] = []

    # El control de reiteraciones debe abarcar la totalidad del campo y no
    # cada fragmento por separado: un mismo dato suele constar en mas de un
    # documento, por ejemplo la escala funcional en la evaluacion inicial y
    # en la evolucion posoperatoria.
    for i, (_meta, _score, texto) in enumerate(fragmentos, 1):
        encontradas = _oraciones_relevantes(texto, patrones, maximo=2)
        for o in encontradas:
            if _es_redundante(o, seleccionadas):
                continue
            seleccionadas.append(o)
            if i not in indices:
                indices.append(i)

    if not seleccionadas:
        return TEXTO_SIN_DATO, []

    contenido = " ".join(seleccionadas[:4])
    return contenido, indices


# ---------------------------------------------------------------------------
# Verificacion de la salida del modelo
# ---------------------------------------------------------------------------

def _menciona(texto: str, expresion: str) -> bool:
    """
    Indica si el texto afirma la expresion indicada.

    La comparacion por inclusion de subcadena no es suficiente: "no mutado"
    contiene "mutado", de modo que buscar el valor positivo dentro de un texto
    que afirma el negativo daria un falso positivo. Se exige por ello que la
    expresion aparezca delimitada y, cuando es afirmativa, que no venga
    precedida de una negacion.
    """
    patron = r"(?<![\w-])" + re.escape(expresion) + r"(?![\w-])"
    for hallazgo in re.finditer(patron, texto):
        if expresion.startswith("no "):
            return True
        previo = texto[max(0, hallazgo.start() - 12):hallazgo.start()]
        if not re.search(r"\b(?:no|sin)\s*$", previo):
            return True
    return False


# Pares de polaridad opuesta. La comparacion no puede realizarse por
# inclusion de subcadena: "no mutado" contiene "mutado", de modo que una
# verificacion ingenua jamas detectaria la contradiccion.
VALORES_OPUESTOS = {
    "mutado": "no mutado", "no mutado": "mutado",
    "metilado": "no metilado", "no metilado": "metilado",
    "codelecion presente": "codelecion ausente",
    "codelecion ausente": "codelecion presente",
    "amplificado": "no amplificado",
    "no amplificado": "amplificado",
    "perdido": "conservado", "conservado": "perdido",
    "alterado": "no alterado", "no alterado": "alterado",
}


def verificar_consistencia(campos: List[CampoResumen], perfil,
                           claves_deterministas=frozenset()) -> List[str]:
    """
    Contrasta el resumen generado contra la extraccion determinista.

    Devuelve la lista de advertencias detectadas. No modifica el resumen: la
    decision sobre una discrepancia corresponde al profesional.

    La verificacion recae sobre los campos redactados por el modelo de
    lenguaje. Un campo generado por las propias reglas se contrastaria contra
    si mismo, de modo que incluirlo produciria una conformidad aparente sin
    contenido informativo.
    """
    advertencias: List[str] = []

    if not perfil.informados:
        return _advertencias_de_respaldo(campos)

    # --- Omision de marcadores en el campo molecular -----------------------
    # Solo corresponde cuando ese campo lo redacto el modelo. Cuando lo genera
    # la extraccion determinista, la comprobacion seria circular.
    campo_molecular = next(
        (c for c in campos if c.clave == "perfil_molecular"), None)
    if campo_molecular and "perfil_molecular" not in claves_deterministas:
        texto = campo_molecular.contenido.lower()
        for nombre, marcador in perfil.informados.items():
            if nombre.lower().replace("/", "") not in texto.replace("/", ""):
                advertencias.append(
                    f"El marcador {nombre} fue detectado en la documentacion "
                    f"({marcador.valor}) pero no aparece en el resumen generado."
                )

    # --- Contradiccion de polaridad en todo campo redactado por el modelo ---
    # Un marcador puede mencionarse fuera del campo molecular: el informe
    # anatomopatologico y la discusion del caso lo hacen con frecuencia. Una
    # contradiccion alli reviste la misma gravedad y, descartado el campo
    # molecular de la verificacion, es ademas la unica que resta detectar.
    for campo in campos:
        if campo.clave in claves_deterministas or not campo.tiene_dato:
            continue
        texto = campo.contenido.lower()
        for nombre, marcador in perfil.informados.items():
            if nombre.lower().replace("/", "") not in texto.replace("/", ""):
                continue
            valor = marcador.valor.lower()
            opuesto = VALORES_OPUESTOS.get(valor)
            if opuesto and _menciona(texto, opuesto) and not _menciona(texto, valor):
                advertencias.append(
                    f"Discrepancia en {nombre}, campo '{campo.etiqueta}': la "
                    f"documentacion indica '{marcador.valor}' y el resumen "
                    f"consigna '{opuesto}'."
                )

    advertencias.extend(_advertencias_de_respaldo(campos))
    return advertencias


def _advertencias_de_respaldo(campos: List[CampoResumen]) -> List[str]:
    """Senala todo campo con contenido que carece de fragmento de respaldo."""
    return [
        f"El campo '{campo.etiqueta}' presenta contenido sin fragmento "
        f"de respaldo asociado."
        for campo in campos if campo.tiene_dato and not campo.fuentes
    ]


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def generar_resumen(fragmentos,
                    indice: Optional[IndiceVectorial] = None,
                    indice_correcciones: Optional[IndiceVectorial] = None,
                    forzar_sin_conexion: bool = False) -> ResultadoResumen:
    """
    Ejecuta el pipeline completo de generacion del resumen estructurado.

    Parametros
    ----------
    fragmentos : lista de Fragmento del caso
    indice : indice vectorial del caso (se construye si no se provee)
    indice_correcciones : indice de correcciones activas, opcional
    forzar_sin_conexion : fuerza el modo determinista, util para comparar
        ambos modos durante la validacion del sistema
    """
    inicio = time.perf_counter()

    if indice is None:
        indice = construir_indice(fragmentos)

    perfil = extraer_perfil(fragmentos)

    # --- Recuperacion por campo -------------------------------------------
    recuperados_por_campo: Dict[str, List[Tuple[Dict, float, str]]] = {}
    for clave, _etiqueta in CAMPOS_RESUMEN:
        consulta = CONSULTAS_CAMPO.get(clave, clave)
        recuperados_por_campo[clave] = indice.buscar(consulta, k=TOP_K_FRAGMENTOS)

    # --- Recuperacion de correcciones activas ------------------------------
    correcciones_por_campo: Dict[str, List[Dict]] = {}
    if indice_correcciones is not None and not indice_correcciones.vacio:
        for clave, _etiqueta in CAMPOS_RESUMEN:
            consulta = CONSULTAS_CAMPO.get(clave, clave)
            hallazgos = indice_correcciones.buscar(
                consulta, k=TOP_K_CORRECCIONES, umbral=UMBRAL_SIMILITUD_CORRECCION
            )
            correcciones_por_campo[clave] = [meta for meta, _s, _t in hallazgos]

    # --- Generacion --------------------------------------------------------
    modo = llm.MODO_SIN_CONEXION
    modelo = "reglas-deterministas"
    campos: List[CampoResumen] = []
    advertencias: List[str] = []

    respuesta_modelo = None
    if not forzar_sin_conexion:
        fragmentos_unicos = _unificar_fragmentos(recuperados_por_campo)
        correcciones_unicas = _unificar_correcciones(correcciones_por_campo)
        # No se solicitan al modelo los campos de generacion determinista
        # obligatoria: pedir lo que no se utilizara consume contexto y
        # desplaza la atencion del modelo de los campos que si redacta.
        campos_para_el_modelo = [
            (clave, etiqueta) for clave, etiqueta in CAMPOS_RESUMEN
            if clave not in CAMPOS_SIEMPRE_DETERMINISTAS
        ]
        prompt = construir_prompt(campos_para_el_modelo, fragmentos_unicos,
                                  correcciones_unicas)
        respuesta_modelo = llm.consultar(prompt)

        if respuesta_modelo.exitosa:
            datos = llm.extraer_json(respuesta_modelo.texto)
            campos_modelo = llm.normalizar_campos(
                datos, [clave for clave, _etiqueta in campos_para_el_modelo])
            if campos_modelo:
                modo = llm.MODO_CONECTADO
                modelo = respuesta_modelo.modelo
                campos = _armar_campos_desde_modelo(
                    campos_modelo, fragmentos_unicos, correcciones_por_campo,
                    recuperados_por_campo, perfil
                )
            else:
                # Se consigna el comienzo de la respuesta: sin ese dato el
                # diagnostico exige reproducir la consulta por fuera del
                # sistema.
                muestra = (respuesta_modelo.texto or "").strip()[:200]
                detalle = f' Comienzo de la respuesta recibida: "{muestra}".' \
                    if muestra else " La respuesta llego vacia."
                advertencias.append(
                    "La respuesta del modelo no pudo interpretarse; se aplico "
                    "el procedimiento determinista de respaldo." + detalle
                )
        else:
            advertencias.append(
                f"No fue posible consultar el modelo de lenguaje "
                f"({respuesta_modelo.error}). Se aplico el procedimiento "
                f"determinista de respaldo."
            )

    if not campos:
        campos = _armar_campos_deterministas(
            recuperados_por_campo, perfil, correcciones_por_campo
        )

    # En modo determinista integro la totalidad de los campos proviene de las
    # reglas, de modo que no hay nada que contrastar: la verificacion se
    # reduce entonces al respaldo documental de cada campo.
    if modo == llm.MODO_CONECTADO:
        claves_deterministas = CAMPOS_SIEMPRE_DETERMINISTAS
    else:
        claves_deterministas = frozenset(
            clave for clave, _etiqueta in CAMPOS_RESUMEN)

    advertencias.extend(
        verificar_consistencia(campos, perfil, claves_deterministas))

    segundos = time.perf_counter() - inicio

    return ResultadoResumen(
        campos=campos,
        perfil_molecular=perfil.como_dict(),
        modo=modo,
        modelo=modelo,
        segundos=round(segundos, 3),
        advertencias=advertencias,
    )


def _unificar_fragmentos(recuperados_por_campo) -> List[Tuple[Dict, float, str]]:
    """Unifica los fragmentos recuperados de todos los campos, sin repetir."""
    vistos = set()
    unicos: List[Tuple[Dict, float, str]] = []
    for lista in recuperados_por_campo.values():
        for meta, score, texto in lista:
            clave = meta.get("id") or texto[:80]
            if clave in vistos:
                continue
            vistos.add(clave)
            unicos.append((meta, score, texto))
    return unicos


def _unificar_correcciones(correcciones_por_campo) -> List[Dict]:
    vistos = set()
    unicas: List[Dict] = []
    for lista in correcciones_por_campo.values():
        for c in lista:
            clave = c.get("id") or c.get("regla", "")[:80]
            if clave in vistos:
                continue
            vistos.add(clave)
            unicas.append(c)
    return unicas


def _armar_campos_desde_modelo(campos_modelo: Dict,
                               fragmentos_unicos: List[Tuple[Dict, float, str]],
                               correcciones_por_campo: Dict,
                               recuperados_por_campo: Optional[Dict] = None,
                               perfil=None) -> List[CampoResumen]:
    campos: List[CampoResumen] = []
    for clave, etiqueta in CAMPOS_RESUMEN:
        if clave in CAMPOS_SIEMPRE_DETERMINISTAS:
            campos.append(_armar_campo_determinista(
                clave, etiqueta, recuperados_por_campo or {}, perfil,
                correcciones_por_campo))
            continue

        entrada = campos_modelo.get(clave) or {}
        if isinstance(entrada, str):
            contenido, numeros = entrada, []
        else:
            contenido = str(entrada.get("contenido", "")).strip()
            numeros = entrada.get("fragmentos") or []

        if not contenido:
            contenido = TEXTO_SIN_DATO

        fuentes = []
        for n in numeros:
            try:
                idx = int(n) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(fragmentos_unicos):
                meta, _s, texto = fragmentos_unicos[idx]
                fuentes.append({
                    "etiqueta": meta.get("etiqueta_fuente", ""),
                    "tipo_documento": meta.get("tipo_documento", ""),
                    "texto": texto,
                })

        campos.append(CampoResumen(
            clave=clave, etiqueta=etiqueta, contenido=contenido, fuentes=fuentes,
            correcciones_aplicadas=correcciones_por_campo.get(clave, []),
        ))
    return campos


def _armar_campo_determinista(clave: str, etiqueta: str,
                              recuperados_por_campo: Dict, perfil,
                              correcciones_por_campo: Dict) -> CampoResumen:
    """Arma un unico campo mediante el procedimiento determinista."""
    recuperados = recuperados_por_campo.get(clave, [])
    contenido, indices = generar_campo_determinista(clave, recuperados, perfil)

    fuentes = []
    for i in indices:
        if 1 <= i <= len(recuperados):
            meta, _s, texto = recuperados[i - 1]
            fuentes.append({
                "etiqueta": meta.get("etiqueta_fuente", ""),
                "tipo_documento": meta.get("tipo_documento", ""),
                "texto": texto,
            })

    return CampoResumen(
        clave=clave, etiqueta=etiqueta, contenido=contenido, fuentes=fuentes,
        correcciones_aplicadas=correcciones_por_campo.get(clave, []),
    )


def _armar_campos_deterministas(recuperados_por_campo: Dict, perfil,
                                correcciones_por_campo: Dict) -> List[CampoResumen]:
    return [
        _armar_campo_determinista(clave, etiqueta, recuperados_por_campo,
                                  perfil, correcciones_por_campo)
        for clave, etiqueta in CAMPOS_RESUMEN
    ]
