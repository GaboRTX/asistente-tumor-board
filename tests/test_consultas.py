# -*- coding: utf-8 -*-
"""
Pruebas del circuito de consulta a profesionales.

Dos propiedades concentran la atencion, por cuanto su incumplimiento no se
manifiesta como un error visible sino como una fuga silenciosa:

  1. El aviso no debe transportar contenido clinico.
  2. Cada consulta admite un unico destinatario.
"""

import pytest

from core import consultas, correo, db


RESUMEN = {
    "campos": [
        {"clave": "datos_clinicos", "etiqueta": "Datos clinicos relevantes",
         "contenido": "Varon de 41 anios con cefalea holocraneana.",
         "fuentes": [{"etiqueta": "Historia clinica", "texto": "..."}]},
        {"clave": "hallazgos_patologia",
         "etiqueta": "Hallazgos anatomopatologicos",
         "contenido": "Astrocitoma IDH mutante, grado 3 de la OMS.",
         "fuentes": []},
        {"clave": "perfil_molecular", "etiqueta": "Perfil molecular",
         "contenido": "IDH: mutado; MGMT: metilado.", "fuentes": []},
    ],
    "advertencias": [],
}


@pytest.fixture
def base(tmp_path):
    ruta = tmp_path / "prueba.db"
    db.inicializar(ruta)
    caso_id = db.crear_caso("CASO-001", {"patologia": "p.txt"}, ruta=ruta)
    return ruta, caso_id


# ---------------------------------------------------------------------------
# Destinatario unico
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("direccion", [
    "patologo@hospital.org",
    "ana.perez@hospital.gob.ar",
    "a.b+rev@sub.dominio.com",
])
def test_se_admite_una_direccion_valida(direccion):
    assert consultas.validar_destinatario(direccion) == direccion


@pytest.mark.parametrize("direccion", [
    "uno@hospital.org, dos@hospital.org",
    "uno@hospital.org; dos@hospital.org",
    "Ana Perez <ana@hospital.org>",
])
def test_se_rechaza_todo_intento_de_varios_destinatarios(direccion):
    """
    Una revision responde a una persona identificada. La difusion a terceros
    no declarados carece de justificacion asistencial.
    """
    with pytest.raises(consultas.DestinatarioInvalido):
        consultas.validar_destinatario(direccion)


@pytest.mark.parametrize("direccion", [
    "ana@hospital.org\nBcc: tercero@otro.com",
    "ana@hospital.org\r\nCc: tercero@otro.com",
    "ana@hospital.org\tx",
])
def test_se_rechaza_la_inyeccion_de_cabeceras(direccion):
    """
    Un salto de linea en la direccion permite incorporar cabeceras al mensaje
    y, con ellas, destinatarios ocultos.
    """
    with pytest.raises(consultas.DestinatarioInvalido):
        consultas.validar_destinatario(direccion)


@pytest.mark.parametrize("direccion", ["", "   ", "sinarroba", "a@b", None])
def test_se_rechaza_una_direccion_inutilizable(direccion):
    with pytest.raises(consultas.DestinatarioInvalido):
        consultas.validar_destinatario(direccion)


# ---------------------------------------------------------------------------
# Vista entregada al profesional
# ---------------------------------------------------------------------------

def test_la_vista_contiene_el_caso_completo_con_su_seccion_resaltada():
    """
    Una seccion aislada no admite lectura clinica: el patologo necesita el
    cuadro clinico y las imagenes para interpretar la histologia. Se le
    entrega el caso completo y se le senala su seccion.
    """
    vista = consultas.armar_vista(
        RESUMEN, "CASO-001", "Ana Perez", "anatomia_patologica")

    assert len(vista.campos) == len(RESUMEN["campos"])
    assert vista.campo_resaltado["clave"] == "hallazgos_patologia"
    assert sum(1 for c in vista.campos if c["resaltado"]) == 1


def test_cada_especialidad_resalta_su_campo():
    pares = [
        ("anatomia_patologica", "hallazgos_patologia"),
        ("diagnostico_por_imagenes", "hallazgos_imagenes"),
        ("biologia_molecular", "perfil_molecular"),
    ]
    for especialidad, esperado in pares:
        assert consultas.campo_de_especialidad(especialidad) == esperado


def test_una_especialidad_no_contemplada_no_impide_la_consulta():
    """
    La nomina de especialidades no puede anticiparse por completo. Ante una no
    contemplada el profesional revisa el caso en su conjunto.
    """
    vista = consultas.armar_vista(RESUMEN, "CASO-001", "X", "medicina nuclear")
    assert vista.campo_resaltado is None
    assert len(vista.campos) == len(RESUMEN["campos"])


# ---------------------------------------------------------------------------
# Alta y trazabilidad
# ---------------------------------------------------------------------------

def test_el_alta_conserva_lo_exhibido(base):
    """
    Una respuesta solo significa algo respecto del contenido sobre el cual se
    emitio. Si el resumen se regenera, la instantanea debe conservar lo que el
    profesional efectivamente vio.
    """
    ruta, caso_id = base
    consulta = consultas.crear_consulta(
        caso_id, "CASO-001", RESUMEN, "Ana Perez", "anatomia_patologica",
        "ana@hospital.org", ruta=ruta)

    assert consulta["estado"] == consultas.PENDIENTE
    assert consulta["instantanea"]["campos"][1]["contenido"].startswith(
        "Astrocitoma")
    assert consulta["token"].startswith("TB-CASO001-")


def test_dos_consultas_a_la_misma_especialidad_no_colisionan(base):
    ruta, caso_id = base
    a = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica", "ana@h.org", ruta=ruta)
    b = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Beto",
                                 "anatomia_patologica", "beto@h.org", ruta=ruta)
    assert a["token"] != b["token"]


def test_el_alta_rechaza_el_destinatario_invalido_sin_registrar_nada(base):
    ruta, caso_id = base
    with pytest.raises(consultas.DestinatarioInvalido):
        consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica",
                                 "ana@h.org, otro@h.org", ruta=ruta)
    assert db.listar_consultas(caso_id, ruta=ruta) == []


def test_el_alta_exige_nombre_y_especialidad(base):
    ruta, caso_id = base
    for nombre, especialidad in [("", "anatomia_patologica"), ("Ana", "  ")]:
        with pytest.raises(ValueError):
            consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, nombre,
                                     especialidad, "ana@h.org", ruta=ruta)


# ---------------------------------------------------------------------------
# Respuesta
# ---------------------------------------------------------------------------

def test_la_conformidad_queda_asentada(base):
    ruta, caso_id = base
    c = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica", "ana@h.org", ruta=ruta)
    actualizada = consultas.registrar_respuesta(
        c["id"], consultas.CONFORME, ruta=ruta)

    assert actualizada["estado"] == consultas.CONFORME
    assert actualizada["fecha_respuesta"]


def test_una_observacion_sin_detalle_se_rechaza(base):
    """
    Un caso marcado como objetado sin constancia de la objecion deja a la
    junta sin nada sobre lo cual deliberar.
    """
    ruta, caso_id = base
    c = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica", "ana@h.org", ruta=ruta)
    with pytest.raises(ValueError):
        consultas.registrar_respuesta(
            c["id"], consultas.CON_OBSERVACIONES, "   ", ruta=ruta)

    assert db.obtener_consulta(c["id"], ruta=ruta)["estado"] == \
        consultas.PENDIENTE


def test_no_se_admite_un_estado_arbitrario(base):
    ruta, caso_id = base
    c = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica", "ana@h.org", ruta=ruta)
    with pytest.raises(ValueError):
        consultas.registrar_respuesta(c["id"], "aprobado", ruta=ruta)


# ---------------------------------------------------------------------------
# Estado del circuito
# ---------------------------------------------------------------------------

def test_una_observacion_pendiente_no_habilita_la_decision(base):
    ruta, caso_id = base
    a = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                                 "anatomia_patologica", "ana@h.org", ruta=ruta)
    b = consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Beto",
                                 "diagnostico_por_imagenes", "beto@h.org",
                                 ruta=ruta)

    assert not consultas.estado_del_circuito(caso_id, ruta=ruta)[
        "habilitado_para_decision"]

    consultas.registrar_respuesta(a["id"], consultas.CONFORME, ruta=ruta)
    estado = consultas.estado_del_circuito(caso_id, ruta=ruta)
    assert estado["pendientes"] == 1
    assert not estado["habilitado_para_decision"]

    consultas.registrar_respuesta(b["id"], consultas.CON_OBSERVACIONES,
                                  "Revisar el realce posterior.", ruta=ruta)
    estado = consultas.estado_del_circuito(caso_id, ruta=ruta)
    assert estado["pendientes"] == 0
    assert estado["con_observaciones"] == 1
    assert not estado["habilitado_para_decision"], (
        "una observacion sin atender no puede habilitar la decision")


def test_sin_consultas_no_hay_circuito_habilitado(base):
    """
    Un caso sin consulta alguna no debe presentarse como revisado. La ausencia
    de objeciones no equivale a conformidad.
    """
    ruta, caso_id = base
    assert not consultas.estado_del_circuito(caso_id, ruta=ruta)[
        "habilitado_para_decision"]


# ---------------------------------------------------------------------------
# Borrado del historico
# ---------------------------------------------------------------------------

def test_el_borrado_total_vacia_todas_las_tablas(base):
    """
    El borrado debe alcanzar a la totalidad del historico. Una tabla omitida
    dejaria registros huerfanos que reapareceran en las metricas.
    """
    ruta, caso_id = base
    db.registrar_generacion(caso_id, "resumen", {"x": 1}, [], "modelo",
                            "conectado", 1.0, ruta=ruta)
    consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                             "anatomia_patologica", "ana@h.org", ruta=ruta)
    db.registrar_tiempo_manual("preparacion", 30.0, "medicion", ruta=ruta)

    antes = db.contar_historico(ruta)
    assert sum(antes.values()) > 0

    db.borrar_historico(ruta)

    despues = db.contar_historico(ruta)
    assert sum(despues.values()) == 0, f"quedaron registros: {despues}"


def test_el_borrado_informa_lo_efectivamente_eliminado(base):
    ruta, caso_id = base
    consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                             "anatomia_patologica", "ana@h.org", ruta=ruta)

    borrados = db.borrar_historico(ruta)
    assert borrados["casos"] == 1
    assert borrados["consultas"] == 1


def test_el_borrado_de_un_caso_arrastra_sus_consultas(base):
    ruta, caso_id = base
    consultas.crear_consulta(caso_id, "CASO-001", RESUMEN, "Ana",
                             "anatomia_patologica", "ana@h.org", ruta=ruta)
    otro = db.crear_caso("CASO-002", {"patologia": "p.txt"}, ruta=ruta)
    consultas.crear_consulta(otro, "CASO-002", RESUMEN, "Beto",
                             "neurologia", "beto@h.org", ruta=ruta)

    db.eliminar_caso(caso_id, ruta=ruta)

    assert db.listar_consultas(caso_id, ruta=ruta) == []
    assert len(db.listar_consultas(otro, ruta=ruta)) == 1, (
        "el borrado de un caso no debe afectar a los demas")


def test_el_borrado_no_alcanza_al_padron_de_usuarios(base, tmp_path):
    """
    El objeto del borrado es dejar el sistema listo para una demostracion, no
    desinstalarlo. Perder el padron impediria volver a ingresar.
    """
    from core import acceso

    ruta, caso_id = base
    acceso.inicializar_padron(ruta)
    db.borrar_historico(ruta)

    assert len(acceso.listar_usuarios(ruta)) == 3
    assert acceso.autenticar("mrossi", "tumorboard.2026", ruta) is not None


def test_el_borrado_sobre_un_historico_vacio_no_falla(base):
    ruta, _caso_id = base
    db.borrar_historico(ruta)
    db.borrar_historico(ruta)
    assert sum(db.contar_historico(ruta).values()) == 0
