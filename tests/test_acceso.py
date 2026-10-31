# -*- coding: utf-8 -*-
"""
Pruebas del control de acceso.

El modulo no pretende ser un sistema de identidad institucional, pero si
respetar el minimo exigible a cualquier manejo de credenciales. Esas
propiedades se verifican de manera expresa, porque su incumplimiento no
produce ningun sintoma visible.
"""

import json

import pytest

from core import acceso


@pytest.fixture
def base(tmp_path):
    ruta = tmp_path / "sistema.db"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    acceso.inicializar_padron(ruta)
    return ruta


# ---------------------------------------------------------------------------
# Almacenamiento de la clave
# ---------------------------------------------------------------------------

def test_la_clave_no_se_almacena_en_texto_plano(base):
    """
    Propiedad central. El padron es un archivo del sistema de archivos: si
    contuviera las claves, cualquiera con acceso al equipo las obtendria.
    """
    contenido = acceso.ruta_padron(base).read_text(encoding="utf-8")

    for registro in acceso.PADRON_INICIAL:
        assert registro["clave"] not in contenido, (
            f"la clave de {registro['usuario']} figura en texto plano")


def test_cada_usuario_tiene_sal_propia(base):
    """
    Sin sal por usuario, dos personas con la misma clave presentarian la
    misma derivacion, y una tabla precalculada las resolveria de una vez.
    """
    registros = json.loads(acceso.ruta_padron(base).read_text(encoding="utf-8"))
    sales = [r["sal"] for r in registros]
    derivadas = [r["derivada"] for r in registros]

    assert len(set(sales)) == len(sales), "las sales se repiten"
    # Las tres credenciales iniciales comparten clave: aun asi las
    # derivaciones deben diferir.
    assert len(set(derivadas)) == len(derivadas), "las derivaciones se repiten"


def test_la_derivacion_emplea_un_numero_de_iteraciones_sustantivo(base):
    registros = json.loads(acceso.ruta_padron(base).read_text(encoding="utf-8"))
    for registro in registros:
        assert registro["iteraciones"] >= 100_000


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------

def test_las_credenciales_validas_resuelven_el_usuario(base):
    usuario = acceso.autenticar("mrossi", "tumorboard.2026", base)
    assert usuario is not None
    assert usuario.nombre == "Dra. Mariana Rossi"
    assert "Neuro-oncologia" in usuario.especialidad


def test_el_nombre_de_usuario_no_distingue_mayusculas(base):
    assert acceso.autenticar("MRossi", "tumorboard.2026", base) is not None


def test_la_clave_si_distingue_mayusculas(base):
    assert acceso.autenticar("mrossi", "TumorBoard.2026", base) is None


@pytest.mark.parametrize("usuario,clave", [
    ("mrossi", "incorrecta"),
    ("inexistente", "tumorboard.2026"),
    ("", ""),
    ("mrossi", ""),
])
def test_se_rechazan_las_credenciales_invalidas(base, usuario, clave):
    assert acceso.autenticar(usuario, clave, base) is None


def test_existen_tres_lideres_de_tumor_board(base):
    usuarios = acceso.listar_usuarios(base)
    assert len(usuarios) == 3
    assert all(u.nombre and u.especialidad for u in usuarios)


def test_no_existe_una_figura_administrativa(base):
    """
    El sistema es una herramienta de apoyo documental y todos sus usuarios
    operan sobre los mismos casos. Un perfil administrativo sugeriria
    atribuciones que el sistema no contempla.
    """
    nombres = {u.usuario.lower() for u in acceso.listar_usuarios(base)}
    assert not nombres & {"admin", "administrador", "root", "supervisor"}


# ---------------------------------------------------------------------------
# Cambio de clave
# ---------------------------------------------------------------------------

def test_la_clave_puede_cambiarse(base):
    acceso.cambiar_clave("mrossi", "tumorboard.2026", "clave.nueva.2026", base)

    assert acceso.autenticar("mrossi", "tumorboard.2026", base) is None
    assert acceso.autenticar("mrossi", "clave.nueva.2026", base) is not None


def test_el_cambio_exige_la_clave_vigente(base):
    with pytest.raises(ValueError, match="actual"):
        acceso.cambiar_clave("mrossi", "incorrecta", "clave.nueva.2026", base)
    assert acceso.autenticar("mrossi", "tumorboard.2026", base) is not None


def test_se_rechaza_una_clave_nueva_demasiado_corta(base):
    with pytest.raises(ValueError, match="8 caracteres"):
        acceso.cambiar_clave("mrossi", "tumorboard.2026", "corta", base)


def test_el_cambio_de_clave_no_altera_a_los_demas_usuarios(base):
    acceso.cambiar_clave("mrossi", "tumorboard.2026", "clave.nueva.2026", base)

    assert acceso.autenticar("jlaguna", "tumorboard.2026", base) is not None
    assert acceso.autenticar("cvera", "tumorboard.2026", base) is not None
    assert len(acceso.listar_usuarios(base)) == 3


# ---------------------------------------------------------------------------
# Padron
# ---------------------------------------------------------------------------

def test_la_inicializacion_es_idempotente(base):
    """Una segunda inicializacion no debe restablecer las claves cambiadas."""
    acceso.cambiar_clave("mrossi", "tumorboard.2026", "clave.nueva.2026", base)
    acceso.inicializar_padron(base)

    assert acceso.autenticar("mrossi", "clave.nueva.2026", base) is not None


def test_un_padron_corrupto_no_interrumpe_la_ejecucion(base):
    acceso.ruta_padron(base).write_text("{ esto no es json", encoding="utf-8")

    assert acceso.listar_usuarios(base) == []
    assert acceso.autenticar("mrossi", "tumorboard.2026", base) is None
