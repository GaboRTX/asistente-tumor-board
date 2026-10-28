"""
Capa de vectorizacion y recuperacion semantica.

El sistema admite dos motores de representacion vectorial:

  1. Modelo de embeddings multilingue (sentence-transformers), que captura
     similitud semantica y es el motor previsto para la operacion normal.
  2. Representacion TF-IDF sobre n-gramas de caracteres, que no requiere
     descarga de modelos ni conexion a internet.

La seleccion es automatica: si el modelo de embeddings esta disponible se
utiliza ese; en caso contrario el sistema degrada al motor TF-IDF sin
interrumpir la operacion. Esta decision de disenio responde a un requisito
concreto del contexto de uso: la herramienta debe seguir siendo utilizable
en un entorno sin conectividad garantizada.

Para n-gramas de caracteres, la representacion TF-IDF resulta razonablemente
robusta frente a variaciones morfologicas del espaniol clinico, que es el
caso de uso predominante del sistema.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


MOTOR_EMBEDDINGS = "embeddings"
MOTOR_TFIDF = "tfidf"

_MODELO_EMBEDDINGS_POR_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# ---------------------------------------------------------------------------
# Deteccion del motor disponible
# ---------------------------------------------------------------------------

def motor_disponible(preferido: Optional[str] = None) -> str:
    """
    Determina que motor de vectorizacion utilizar.

    Si se indica un motor preferido se respeta esa eleccion, siempre que sea
    viable; de lo contrario se selecciona el mejor disponible.

    Advertencia: que la biblioteca este instalada no garantiza que el modelo
    pueda cargarse, ya que la primera ejecucion requiere descargarlo. La
    verificacion efectiva la realiza `verificar_modelo`.
    """
    if preferido == MOTOR_TFIDF:
        return MOTOR_TFIDF

    try:
        import sentence_transformers  # noqa: F401
        return MOTOR_EMBEDDINGS
    except Exception:
        return MOTOR_TFIDF


def _describir_error_modelo(exc: Exception) -> str:
    """Traduce el error de carga del modelo a un mensaje interpretable."""
    texto = str(exc).lower()
    if "couldn't connect" in texto or "connection" in texto or "offline" in texto:
        return ("No fue posible descargar el modelo de embeddings. La primera "
                "ejecucion requiere conexion a internet; una vez descargado, "
                "el modelo queda almacenado localmente y opera sin conexion.")
    if "no module named" in texto:
        return ("La biblioteca sentence-transformers no se encuentra instalada.")
    return f"No fue posible inicializar el modelo de embeddings ({type(exc).__name__})."


def verificar_modelo(nombre_modelo: str = _MODELO_EMBEDDINGS_POR_DEFECTO
                     ) -> Tuple[bool, str]:
    """
    Comprueba que el modelo de embeddings pueda cargarse efectivamente.

    Se provee como verificacion previa: conviene ejecutarla una vez, con
    conexion disponible, antes de operar el sistema en un entorno sin
    conectividad garantizada.

    Devuelve (disponible, mensaje).
    """
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False, ("sentence-transformers no esta instalado. El sistema "
                       "operara con el motor TF-IDF.")

    try:
        from sentence_transformers import SentenceTransformer
        modelo = SentenceTransformer(nombre_modelo)
        modelo.encode(["prueba de verificacion"], show_progress_bar=False)
        return True, f"Modelo de embeddings disponible y operativo ({nombre_modelo})."
    except Exception as exc:
        return False, _describir_error_modelo(exc)


# ---------------------------------------------------------------------------
# Indice vectorial
# ---------------------------------------------------------------------------

class IndiceVectorial:
    """
    Indice en memoria que almacena textos junto con sus metadatos y permite
    recuperar los mas similares a una consulta.

    Se mantiene deliberadamente simple y sin dependencia de un servicio
    externo, de modo que el estado del indice sea reproducible y auditable
    caso por caso.
    """

    def __init__(self, motor: Optional[str] = None,
                 nombre_modelo: str = _MODELO_EMBEDDINGS_POR_DEFECTO):
        self.motor = motor_disponible(motor)
        self.nombre_modelo = nombre_modelo
        self.motivo_degradacion: str = ""
        self._textos: List[str] = []
        self._metadatos: List[Dict] = []
        self._matriz = None
        self._vectorizador = None
        self._modelo = None

    # -- construccion --------------------------------------------------------

    def _cargar_modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer
            self._modelo = SentenceTransformer(self.nombre_modelo)
        return self._modelo

    def indexar(self, textos: Sequence[str], metadatos: Sequence[Dict]) -> None:
        """Construye el indice a partir de los textos y sus metadatos."""
        if len(textos) != len(metadatos):
            raise ValueError("La cantidad de textos y de metadatos debe coincidir.")

        self._textos = list(textos)
        self._metadatos = [dict(m) for m in metadatos]

        if not self._textos:
            self._matriz = None
            return

        if self.motor == MOTOR_EMBEDDINGS:
            try:
                modelo = self._cargar_modelo()
                matriz = np.asarray(modelo.encode(self._textos, show_progress_bar=False))
                self._matriz = self._normalizar(matriz)
                return
            except Exception as exc:
                # Degradacion controlada: si el modelo no puede cargarse, el
                # indice continua operando con el motor alternativo. El motivo
                # se conserva para poder informarlo en la interfaz, de modo que
                # la degradacion nunca sea silenciosa.
                self.motor = MOTOR_TFIDF
                self.motivo_degradacion = _describir_error_modelo(exc)

        self._indexar_tfidf()

    def _indexar_tfidf(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizador = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
        )
        matriz = self._vectorizador.fit_transform(self._textos).toarray()
        self._matriz = self._normalizar(np.asarray(matriz, dtype=float))

    @staticmethod
    def _normalizar(matriz: np.ndarray) -> np.ndarray:
        normas = np.linalg.norm(matriz, axis=1, keepdims=True)
        normas[normas == 0] = 1.0
        return matriz / normas

    # -- consulta ------------------------------------------------------------

    def _vectorizar_consulta(self, consulta: str) -> np.ndarray:
        if self.motor == MOTOR_EMBEDDINGS and self._modelo is not None:
            vector = np.asarray(self._modelo.encode([consulta], show_progress_bar=False))
        else:
            vector = np.asarray(
                self._vectorizador.transform([consulta]).toarray(), dtype=float
            )
        return self._normalizar(vector)[0]

    def buscar(self, consulta: str, k: int = 5,
               umbral: float = 0.0) -> List[Tuple[Dict, float, str]]:
        """
        Recupera los k elementos mas similares a la consulta.

        Devuelve una lista de tuplas (metadatos, similitud, texto), ordenada
        de mayor a menor similitud y filtrada por el umbral indicado.
        """
        if self._matriz is None or not self._textos:
            return []

        vector = self._vectorizar_consulta(consulta)
        similitudes = self._matriz @ vector

        k = max(1, min(int(k), len(self._textos)))
        indices = np.argsort(-similitudes)[:k]

        resultados = []
        for i in indices:
            puntaje = float(similitudes[i])
            if puntaje < umbral:
                continue
            resultados.append((self._metadatos[i], puntaje, self._textos[i]))
        return resultados

    # -- utilidades ----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._textos)

    @property
    def vacio(self) -> bool:
        return len(self._textos) == 0

    def describir_motor(self) -> str:
        if self.motor == MOTOR_EMBEDDINGS:
            return f"Embeddings multilingues ({self.nombre_modelo})"
        if self.motivo_degradacion:
            return ("TF-IDF sobre n-gramas de caracteres (modo de respaldo). "
                    + self.motivo_degradacion)
        return "TF-IDF sobre n-gramas de caracteres (modo sin conexion)"

    @property
    def degradado(self) -> bool:
        """Indica si el indice opera en modo de respaldo por un fallo previo."""
        return bool(self.motivo_degradacion)


# ---------------------------------------------------------------------------
# Construccion del indice a partir de fragmentos
# ---------------------------------------------------------------------------

def construir_indice(fragmentos: List, motor: Optional[str] = None) -> IndiceVectorial:
    """Construye un indice vectorial a partir de una lista de Fragmento."""
    indice = IndiceVectorial(motor=motor)
    textos, metadatos = [], []
    for f in fragmentos or []:
        if isinstance(f, dict):
            textos.append(f.get("texto", ""))
            metadatos.append(f)
        else:
            textos.append(f.texto)
            metadatos.append(f.como_dict())
    indice.indexar(textos, metadatos)
    return indice
