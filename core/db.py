"""
Capa de persistencia del sistema (SQLite).

Se definen cinco entidades:
  - casos:                 cada caso clinico cargado en el sistema
  - generaciones:          cada ejecucion del pipeline sobre un caso
  - feedback:              cada correccion realizada por un profesional
  - correcciones:          correcciones curadas que alimentan el retrieval
  - consultas:             circulacion del caso a un profesional y su respuesta

La separacion entre "feedback" (lo que el profesional corrigio) y
"correcciones" (lo que efectivamente se incorpora al sistema) es deliberada:
ninguna correccion influye sobre generaciones futuras hasta que es validada.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import RUTA_BASE_DATOS


ESQUEMA = """
CREATE TABLE IF NOT EXISTS casos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    identificador       TEXT NOT NULL UNIQUE,
    fecha_carga         TEXT NOT NULL,
    documentos          TEXT NOT NULL,          -- JSON: {tipo: nombre_archivo}
    estado              TEXT NOT NULL DEFAULT 'cargado',
    notas               TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS generaciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_id             INTEGER NOT NULL,
    tipo                TEXT NOT NULL,          -- resumen | ensayos
    fecha               TEXT NOT NULL,
    contenido           TEXT NOT NULL,          -- JSON con el resultado
    fragmentos_usados   TEXT NOT NULL,          -- JSON con las fuentes citadas
    correcciones_usadas TEXT NOT NULL DEFAULT '[]',
    modelo              TEXT NOT NULL,
    modo                TEXT NOT NULL,          -- conectado | sin_conexion
    segundos            REAL NOT NULL,
    FOREIGN KEY (caso_id) REFERENCES casos (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    generacion_id       INTEGER NOT NULL,
    caso_id             INTEGER NOT NULL,
    campo               TEXT NOT NULL,
    valor_generado      TEXT NOT NULL,
    valor_corregido     TEXT NOT NULL,
    tipo_error          TEXT NOT NULL,
    comentario          TEXT DEFAULT '',
    autor               TEXT DEFAULT '',
    fecha               TEXT NOT NULL,
    FOREIGN KEY (generacion_id) REFERENCES generaciones (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS correcciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id         INTEGER NOT NULL,
    campo               TEXT NOT NULL,
    regla               TEXT NOT NULL,
    estado              TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | activa | desactivada
    autor_validacion    TEXT DEFAULT '',
    fecha_creacion      TEXT NOT NULL,
    fecha_validacion    TEXT DEFAULT '',
    FOREIGN KEY (feedback_id) REFERENCES feedback (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS consultas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_id             INTEGER NOT NULL,
    generacion_id       INTEGER,
    token               TEXT NOT NULL UNIQUE,   -- identificador de la consulta
    nombre              TEXT NOT NULL,
    especialidad        TEXT NOT NULL,
    correo              TEXT NOT NULL,
    campo_interes       TEXT NOT NULL,          -- clave del campo a revisar
    estado              TEXT NOT NULL DEFAULT 'pendiente',
                                                -- pendiente | conforme | con_observaciones
    instantanea         TEXT NOT NULL,          -- JSON: lo exhibido al profesional
    aviso_enviado       INTEGER NOT NULL DEFAULT 0,
    detalle_envio       TEXT DEFAULT '',
    fecha_creacion      TEXT NOT NULL,
    fecha_respuesta     TEXT,
    observacion         TEXT DEFAULT '',
    FOREIGN KEY (caso_id) REFERENCES casos (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tiempos_manuales (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion         TEXT NOT NULL,
    minutos             REAL NOT NULL,
    fuente              TEXT NOT NULL,
    fecha               TEXT NOT NULL
);
"""


@contextmanager
def conexion(ruta: Optional[Path] = None):
    """Context manager que entrega una conexion con filas tipo diccionario."""
    ruta = Path(ruta) if ruta else RUTA_BASE_DATOS
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar(ruta: Optional[Path] = None) -> None:
    """Crea las tablas si no existen. Es idempotente."""
    with conexion(ruta) as con:
        con.executescript(ESQUEMA)


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def crear_caso(identificador: str, documentos: Dict[str, str],
               notas: str = "", ruta: Optional[Path] = None) -> int:
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO casos (identificador, fecha_carga, documentos, estado, notas) "
            "VALUES (?, ?, ?, ?, ?)",
            (identificador, _ahora(), json.dumps(documentos, ensure_ascii=False),
             "cargado", notas),
        )
        return cur.lastrowid


def obtener_caso(caso_id: int, ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute("SELECT * FROM casos WHERE id = ?", (caso_id,)).fetchone()
    if not fila:
        return None
    caso = dict(fila)
    caso["documentos"] = json.loads(caso["documentos"])
    return caso


def buscar_caso_por_identificador(identificador: str,
                                  ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute("SELECT * FROM casos WHERE identificador = ?",
                           (identificador,)).fetchone()
    if not fila:
        return None
    caso = dict(fila)
    caso["documentos"] = json.loads(caso["documentos"])
    return caso


def listar_casos(ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        filas = con.execute("SELECT * FROM casos ORDER BY id DESC").fetchall()
    salida = []
    for f in filas:
        caso = dict(f)
        caso["documentos"] = json.loads(caso["documentos"])
        salida.append(caso)
    return salida


def actualizar_estado_caso(caso_id: int, estado: str, ruta: Optional[Path] = None) -> None:
    with conexion(ruta) as con:
        con.execute("UPDATE casos SET estado = ? WHERE id = ?", (estado, caso_id))


def eliminar_caso(caso_id: int, ruta: Optional[Path] = None) -> None:
    with conexion(ruta) as con:
        con.execute("DELETE FROM casos WHERE id = ?", (caso_id,))


# ---------------------------------------------------------------------------
# Generaciones
# ---------------------------------------------------------------------------

def registrar_generacion(caso_id: int, tipo: str, contenido: Any,
                         fragmentos_usados: Any, modelo: str, modo: str,
                         segundos: float, correcciones_usadas: Any = None,
                         ruta: Optional[Path] = None) -> int:
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO generaciones (caso_id, tipo, fecha, contenido, fragmentos_usados, "
            "correcciones_usadas, modelo, modo, segundos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (caso_id, tipo, _ahora(),
             json.dumps(contenido, ensure_ascii=False),
             json.dumps(fragmentos_usados, ensure_ascii=False),
             json.dumps(correcciones_usadas or [], ensure_ascii=False),
             modelo, modo, round(float(segundos), 3)),
        )
        return cur.lastrowid


def obtener_generacion(generacion_id: int, ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute("SELECT * FROM generaciones WHERE id = ?",
                           (generacion_id,)).fetchone()
    return _desempaquetar_generacion(fila)


def ultima_generacion(caso_id: int, tipo: str,
                      ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute(
            "SELECT * FROM generaciones WHERE caso_id = ? AND tipo = ? "
            "ORDER BY id DESC LIMIT 1", (caso_id, tipo)).fetchone()
    return _desempaquetar_generacion(fila)


def listar_generaciones(ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        filas = con.execute("SELECT * FROM generaciones ORDER BY id DESC").fetchall()
    return [_desempaquetar_generacion(f) for f in filas]


def _desempaquetar_generacion(fila) -> Optional[Dict[str, Any]]:
    if not fila:
        return None
    g = dict(fila)
    g["contenido"] = json.loads(g["contenido"])
    g["fragmentos_usados"] = json.loads(g["fragmentos_usados"])
    g["correcciones_usadas"] = json.loads(g["correcciones_usadas"])
    return g


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def registrar_feedback(generacion_id: int, caso_id: int, campo: str,
                       valor_generado: str, valor_corregido: str,
                       tipo_error: str, comentario: str = "", autor: str = "",
                       ruta: Optional[Path] = None) -> int:
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO feedback (generacion_id, caso_id, campo, valor_generado, "
            "valor_corregido, tipo_error, comentario, autor, fecha) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (generacion_id, caso_id, campo, valor_generado, valor_corregido,
             tipo_error, comentario, autor, _ahora()),
        )
        return cur.lastrowid


def listar_feedback(caso_id: Optional[int] = None,
                    ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        if caso_id is None:
            filas = con.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()
        else:
            filas = con.execute("SELECT * FROM feedback WHERE caso_id = ? ORDER BY id DESC",
                                (caso_id,)).fetchall()
    return [dict(f) for f in filas]


# ---------------------------------------------------------------------------
# Correcciones curadas
# ---------------------------------------------------------------------------

def crear_correccion(feedback_id: int, campo: str, regla: str,
                     ruta: Optional[Path] = None) -> int:
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO correcciones (feedback_id, campo, regla, estado, fecha_creacion) "
            "VALUES (?, ?, ?, 'pendiente', ?)",
            (feedback_id, campo, regla, _ahora()),
        )
        return cur.lastrowid


def cambiar_estado_correccion(correccion_id: int, estado: str, autor: str = "",
                              ruta: Optional[Path] = None) -> None:
    if estado not in ("pendiente", "activa", "desactivada"):
        raise ValueError(f"Estado no valido: {estado}")
    with conexion(ruta) as con:
        con.execute(
            "UPDATE correcciones SET estado = ?, autor_validacion = ?, fecha_validacion = ? "
            "WHERE id = ?",
            (estado, autor, _ahora(), correccion_id),
        )


def listar_correcciones(estado: Optional[str] = None,
                        ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        if estado is None:
            filas = con.execute("SELECT * FROM correcciones ORDER BY id DESC").fetchall()
        else:
            filas = con.execute("SELECT * FROM correcciones WHERE estado = ? ORDER BY id DESC",
                                (estado,)).fetchall()
    return [dict(f) for f in filas]


# ---------------------------------------------------------------------------
# Tiempos manuales de referencia (para la metrica de la hipotesis)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Consultas a profesionales
# ---------------------------------------------------------------------------

def crear_consulta(caso_id: int, token: str, nombre: str, especialidad: str,
                   correo: str, campo_interes: str, instantanea: Any,
                   generacion_id: Optional[int] = None,
                   ruta: Optional[Path] = None) -> int:
    """
    Registra la circulacion de un caso a un profesional.

    La instantanea conserva lo efectivamente exhibido. Sin ella la trazabilidad
    se pierde: una respuesta solo significa algo respecto del contenido sobre
    el cual se emitio, y el resumen puede regenerarse despues.
    """
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO consultas (caso_id, generacion_id, token, nombre, "
            "especialidad, correo, campo_interes, estado, instantanea, "
            "fecha_creacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (caso_id, generacion_id, token, nombre, especialidad, correo,
             campo_interes, "pendiente",
             json.dumps(instantanea, ensure_ascii=False), _ahora()),
        )
        return cur.lastrowid


def obtener_consulta(consulta_id: int,
                     ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute("SELECT * FROM consultas WHERE id = ?",
                           (consulta_id,)).fetchone()
    return _desempaquetar_consulta(fila)


def buscar_consulta_por_token(token: str,
                              ruta: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with conexion(ruta) as con:
        fila = con.execute("SELECT * FROM consultas WHERE token = ?",
                           (token,)).fetchone()
    return _desempaquetar_consulta(fila)


def listar_consultas(caso_id: Optional[int] = None,
                     ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        if caso_id is None:
            filas = con.execute(
                "SELECT * FROM consultas ORDER BY id DESC").fetchall()
        else:
            filas = con.execute(
                "SELECT * FROM consultas WHERE caso_id = ? ORDER BY id DESC",
                (caso_id,)).fetchall()
    return [_desempaquetar_consulta(f) for f in filas]


def registrar_envio_consulta(consulta_id: int, enviado: bool, detalle: str = "",
                             ruta: Optional[Path] = None) -> None:
    with conexion(ruta) as con:
        con.execute(
            "UPDATE consultas SET aviso_enviado = ?, detalle_envio = ? WHERE id = ?",
            (1 if enviado else 0, detalle, consulta_id))


def registrar_respuesta_consulta(consulta_id: int, estado: str,
                                 observacion: str = "",
                                 ruta: Optional[Path] = None) -> None:
    """Asienta la respuesta del profesional. Los estados validos se validan
    en core.consultas, que es donde reside la regla."""
    with conexion(ruta) as con:
        con.execute(
            "UPDATE consultas SET estado = ?, observacion = ?, "
            "fecha_respuesta = ? WHERE id = ?",
            (estado, observacion, _ahora(), consulta_id))


def _desempaquetar_consulta(fila) -> Optional[Dict[str, Any]]:
    if not fila:
        return None
    consulta = dict(fila)
    consulta["instantanea"] = json.loads(consulta["instantanea"])
    consulta["aviso_enviado"] = bool(consulta["aviso_enviado"])
    return consulta


# ---------------------------------------------------------------------------
# Tiempos manuales
# ---------------------------------------------------------------------------

def registrar_tiempo_manual(descripcion: str, minutos: float, fuente: str,
                            ruta: Optional[Path] = None) -> int:
    with conexion(ruta) as con:
        cur = con.execute(
            "INSERT INTO tiempos_manuales (descripcion, minutos, fuente, fecha) "
            "VALUES (?, ?, ?, ?)",
            (descripcion, float(minutos), fuente, _ahora()),
        )
        return cur.lastrowid


def listar_tiempos_manuales(ruta: Optional[Path] = None) -> List[Dict[str, Any]]:
    with conexion(ruta) as con:
        filas = con.execute("SELECT * FROM tiempos_manuales ORDER BY id DESC").fetchall()
    return [dict(f) for f in filas]
