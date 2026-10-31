# -*- coding: utf-8 -*-
"""
Pruebas de la interfaz.

Una verificacion por peticion HTTP resulta insuficiente: Streamlit devuelve el
documento HTML aun cuando el script de la pantalla falle, por cuanto el error
se transmite despues por el canal de la sesion. AppTest ejecuta el script y
expone las excepciones, de modo que un error de nombre o de importacion en una
pantalla no pase inadvertido.
"""

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest


RAIZ = Path(__file__).resolve().parent.parent
PANTALLAS = sorted(p.name for p in (RAIZ / "app" / "pages").glob("*.py"))

RESUMEN = {
    "modo": "sin_conexion",
    "modelo": "reglas-deterministas",
    "segundos": 0.4,
    "advertencias": [],
    "campos": [
        {"clave": "datos_clinicos", "etiqueta": "Datos clinicos relevantes",
         "contenido": "Varon de 41 anios.", "fuentes": [],
         "correcciones_aplicadas": []},
        {"clave": "hallazgos_patologia",
         "etiqueta": "Hallazgos anatomopatologicos",
         "contenido": "Astrocitoma IDH mutante, grado 3.", "fuentes": [],
         "correcciones_aplicadas": []},
        {"clave": "perfil_molecular", "etiqueta": "Perfil molecular",
         "contenido": "IDH: mutado; MGMT: metilado.", "fuentes": [],
         "correcciones_aplicadas": []},
    ],
    "perfil_molecular": {},
}


def _iniciar_sesion(at, ruta_db):
    """Siembra una sesion iniciada en la prueba."""
    from app.comun import CLAVE_SESION
    from core import acceso

    acceso.inicializar_padron(ruta_db)
    usuario = acceso.autenticar("mrossi", "tumorboard.2026", ruta_db)
    assert usuario is not None, "el padron inicial debe permitir el ingreso"
    at.session_state[CLAVE_SESION] = usuario
    return usuario


def _estado_con_caso(ruta_db):
    from core import db

    db.inicializar(ruta_db)
    caso_id = db.crear_caso("CASO-001", {"patologia": "p.txt"}, ruta=ruta_db)
    return {
        "caso_id": caso_id, "identificador": "CASO-001", "fragmentos": [],
        "resumen": RESUMEN, "generacion_id": None, "ensayos": [],
        "origen_ensayos": "", "resumen_ensayos": None,
        "motor_recuperacion": "TF-IDF", "degradacion": "", "autor": "Gabo",
    }


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Dirige la persistencia a una base efimera."""
    ruta = tmp_path / "interfaz.db"
    monkeypatch.setenv("RUTA_BASE_DATOS", str(ruta))

    import core.config
    import core.db
    monkeypatch.setattr(core.config, "RUTA_BASE_DATOS", ruta)
    monkeypatch.setattr(core.db, "RUTA_BASE_DATOS", ruta)
    return ruta


def test_la_pantalla_de_inicio_se_ejecuta_sin_error(base):
    at = AppTest.from_file(str(RAIZ / "app" / "Inicio.py"), default_timeout=30)
    _iniciar_sesion(at, base)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]


@pytest.mark.parametrize("pantalla", PANTALLAS)
def test_cada_pantalla_se_ejecuta_sin_error(pantalla, base):
    """
    Se siembra un caso procesado en el estado de sesion, de modo que las
    pantallas que lo exigen recorran su camino util y no se detengan en la
    advertencia inicial.
    """
    from app.comun import CLAVE_ESTADO

    at = AppTest.from_file(str(RAIZ / "app" / "pages" / pantalla),
                           default_timeout=30)
    _iniciar_sesion(at, base)
    at.session_state[CLAVE_ESTADO] = _estado_con_caso(base)
    at.run()

    assert not at.exception, (
        f"{pantalla} fallo: {[str(e) for e in at.exception]}")


def test_el_panel_de_consultas_registra_y_exhibe_la_consulta(base):
    """
    Recorrido completo de la pantalla: alta de una consulta y su posterior
    exhibicion entre las registradas.
    """
    from app.comun import CLAVE_ESTADO
    from core import consultas, db

    estado = _estado_con_caso(base)
    consultas.crear_consulta(
        caso_id=estado["caso_id"], identificador_caso="CASO-001",
        resumen=RESUMEN, nombre="Ana Perez",
        especialidad="anatomia_patologica", correo="ana@hospital.org",
        ruta=base)

    at = AppTest.from_file(
        str(RAIZ / "app" / "pages" / "6_Consultas_a_profesionales.py"),
        default_timeout=30)
    _iniciar_sesion(at, base)
    at.session_state[CLAVE_ESTADO] = estado
    at.run()

    assert not at.exception, [str(e) for e in at.exception]

    texto = " ".join(str(m.value) for m in at.markdown)
    texto += " ".join(str(e.label) for e in at.expander)
    assert "Ana Perez" in texto


def test_el_reporte_advierte_que_el_caso_no_fue_revisado(base):
    """
    Un reporte que omita el estado de la revision induce a suponer una
    conformidad que puede no existir.
    """
    from app.comun import CLAVE_ESTADO

    at = AppTest.from_file(str(RAIZ / "app" / "pages" / "4_Reporte_final.py"),
                           default_timeout=30)
    _iniciar_sesion(at, base)
    at.session_state[CLAVE_ESTADO] = _estado_con_caso(base)
    at.run()

    assert not at.exception, [str(e) for e in at.exception]
    avisos = " ".join(str(w.value) for w in at.warning)
    assert "no fue sometido a revision" in avisos


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------

def test_toda_pantalla_exige_sesion_iniciada():
    """
    Streamlit admite dirigirse a cualquier pantalla por su direccion. Proteger
    unicamente la inicial dejaria el resto accesible escribiendo la URL, de
    modo que la verificacion recorre todas.
    """
    archivos = list((RAIZ / "app" / "pages").glob("*.py"))
    archivos.append(RAIZ / "app" / "Inicio.py")

    desprotegidas = [a.name for a in archivos
                     if "requerir_sesion()" not in a.read_text(encoding="utf-8")]

    assert not desprotegidas, (
        f"pantallas accesibles sin sesion: {desprotegidas}")


@pytest.mark.parametrize("pantalla", PANTALLAS)
def test_sin_sesion_la_pantalla_no_exhibe_el_caso(pantalla, base):
    """
    Sin sesion iniciada debe presentarse el ingreso, y no el contenido del
    caso, aun cuando el estado de sesion contenga uno cargado.
    """
    from app.comun import CLAVE_ESTADO

    at = AppTest.from_file(str(RAIZ / "app" / "pages" / pantalla),
                           default_timeout=30)
    at.session_state[CLAVE_ESTADO] = _estado_con_caso(base)
    at.run()

    assert not at.exception, [str(e) for e in at.exception]

    texto = " ".join(str(m.value) for m in at.markdown)
    assert "Ingreso al sistema" in texto, (
        f"{pantalla} no presenta el ingreso sin sesion")
    assert "Astrocitoma" not in texto, (
        f"{pantalla} exhibe contenido del caso sin sesion iniciada")


def test_con_sesion_iniciada_la_pantalla_funciona(base):
    from app.comun import CLAVE_ESTADO, CLAVE_SESION
    from core import acceso

    acceso.inicializar_padron(base)
    usuario = acceso.autenticar("mrossi", "tumorboard.2026", base)
    assert usuario is not None

    at = AppTest.from_file(str(RAIZ / "app" / "pages" / "2_Resumen_del_caso.py"),
                           default_timeout=30)
    at.session_state[CLAVE_SESION] = usuario
    at.session_state[CLAVE_ESTADO] = _estado_con_caso(base)
    at.run()

    assert not at.exception, [str(e) for e in at.exception]
    texto = " ".join(str(m.value) for m in at.markdown)
    assert "Ingreso al sistema" not in texto
