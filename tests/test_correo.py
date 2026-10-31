# -*- coding: utf-8 -*-
"""
Pruebas del aviso de consulta.

La propiedad central que se verifica aqui es negativa: que el mensaje NO
contenga datos clinicos. Un incumplimiento no se manifiesta como un error
sino como una fuga, de modo que debe comprobarse de manera explicita y no
quedar librado a la inspeccion visual de la plantilla.
"""

import pytest

from core import consultas, correo, db


RESUMEN = {
    "campos": [
        {"clave": "datos_clinicos", "etiqueta": "Datos clinicos relevantes",
         "contenido": "Varon de 41 anios, diestro, con cefalea holocraneana "
                      "y crisis tonico-clonicas.", "fuentes": []},
        {"clave": "hallazgos_patologia",
         "etiqueta": "Hallazgos anatomopatologicos",
         "contenido": "Astrocitoma IDH mutante, grado 3 de la OMS.",
         "fuentes": []},
        {"clave": "perfil_molecular", "etiqueta": "Perfil molecular",
         "contenido": "IDH: mutado (IDH1 R132H); MGMT: metilado.",
         "fuentes": []},
    ],
    "advertencias": ["El marcador TERT no aparece en el resumen."],
}

# Terminos cuya presencia en el aviso constituiria una fuga de informacion
# clinica. Se incluyen tanto datos del paciente como del diagnostico.
TERMINOS_CLINICOS = [
    "41", "cefalea", "holocraneana", "tonico", "crisis", "diestro",
    "astrocitoma", "IDH", "R132H", "MGMT", "metilado", "mutante",
    "grado 3", "OMS", "TERT",
]


@pytest.fixture
def consulta(tmp_path):
    ruta = tmp_path / "prueba.db"
    db.inicializar(ruta)
    caso_id = db.crear_caso("CASO-001", {"patologia": "p.txt"}, ruta=ruta)
    return consultas.crear_consulta(
        caso_id, "CASO-001", RESUMEN, "Ana Perez", "anatomia_patologica",
        "ana.perez@hospital.org", ruta=ruta)


# ---------------------------------------------------------------------------
# Ausencia de contenido clinico
# ---------------------------------------------------------------------------

def test_el_aviso_no_transporta_dato_clinico_alguno(consulta):
    mensaje = correo.construir_mensaje(consulta)
    texto = (mensaje["Subject"] + "\n" + mensaje.get_content()).lower()

    presentes = [t for t in TERMINOS_CLINICOS if t.lower() in texto]
    assert not presentes, (
        f"el aviso contiene informacion clinica: {presentes}")


def test_el_aviso_identifica_el_caso_solo_por_su_codigo(consulta):
    mensaje = correo.construir_mensaje(consulta)
    texto = mensaje.get_content()

    assert "CASO-001" in texto
    assert consulta["token"] in texto
    assert "no incluye documentacion clinica" in texto


def test_el_aviso_nombra_la_especialidad_requerida(consulta):
    cuerpo = correo.componer_cuerpo(consulta)
    assert "Anatomia patologica" in cuerpo
    assert "Ana Perez" in cuerpo


# ---------------------------------------------------------------------------
# Destinatario unico
# ---------------------------------------------------------------------------

def test_el_mensaje_lleva_un_unico_destinatario(consulta):
    mensaje = correo.construir_mensaje(consulta)

    assert mensaje["To"] == "ana.perez@hospital.org"
    assert mensaje["Cc"] is None
    assert mensaje["Bcc"] is None
    assert "," not in mensaje["To"]


def test_una_direccion_adulterada_impide_componer_el_mensaje(consulta):
    """
    Si la direccion se altera despues del alta, la composicion debe fallar
    antes de contactar al servidor.
    """
    adulterada = dict(consulta)
    adulterada["correo"] = "ana@hospital.org\nBcc: tercero@otro.com"

    with pytest.raises(consultas.DestinatarioInvalido):
        correo.construir_mensaje(adulterada)


def test_el_envio_de_una_direccion_adulterada_no_alcanza_el_transporte(consulta):
    adulterada = dict(consulta)
    adulterada["correo"] = "ana@hospital.org, tercero@otro.com"

    llamadas = []
    resultado = correo.enviar_aviso(
        adulterada, transporte=lambda m: llamadas.append(m))

    assert not resultado.enviado
    assert not llamadas, "no debe alcanzarse el transporte con una direccion invalida"


def test_el_asunto_no_admite_caracteres_de_control(consulta):
    """
    El asunto se compone en el sistema, pero la verificacion no depende de ese
    supuesto: un identificador de caso con un salto de linea permitiria
    incorporar cabeceras.
    """
    adulterada = dict(consulta)
    adulterada["instantanea"] = dict(consulta["instantanea"])
    adulterada["instantanea"]["identificador_caso"] = "CASO-001\nBcc: x@y.com"

    mensaje = correo.construir_mensaje(adulterada)
    assert "\n" not in mensaje["Subject"]
    assert mensaje["Bcc"] is None


# ---------------------------------------------------------------------------
# Degradacion controlada
# ---------------------------------------------------------------------------

def test_sin_servidor_configurado_se_informa_y_no_se_interrumpe(consulta,
                                                                monkeypatch):
    """
    La ausencia de servidor de correo no debe impedir el circuito: la consulta
    ya esta registrada y el aviso puede entregarse por otro medio.
    """
    monkeypatch.setattr(correo, "SMTP_SERVIDOR", "")
    monkeypatch.setattr(correo, "SMTP_REMITENTE", "")

    resultado = correo.enviar_aviso(consulta)
    assert not resultado.enviado
    assert "SMTP_SERVIDOR" in resultado.detalle


def test_un_fallo_del_servidor_no_propaga_la_excepcion(consulta):
    import smtplib

    def transporte_que_falla(mensaje):
        raise smtplib.SMTPAuthenticationError(535, b"Bad credentials")

    resultado = correo.enviar_aviso(consulta, transporte=transporte_que_falla)
    assert not resultado.enviado
    assert "contrasenia de aplicacion" in resultado.detalle


def test_el_envio_exitoso_se_informa(consulta):
    enviados = []
    resultado = correo.enviar_aviso(consulta,
                                    transporte=lambda m: enviados.append(m))

    assert resultado.enviado
    assert len(enviados) == 1
    assert enviados[0]["To"] == "ana.perez@hospital.org"


# ---------------------------------------------------------------------------
# Formato de la contrasenia de aplicacion
# ---------------------------------------------------------------------------

def test_se_tolera_el_formato_en_que_google_exhibe_la_contrasenia():
    """
    Google presenta las contrasenias de aplicacion en cuatro bloques de cuatro
    letras separados por espacios. Copiarla tal como se la ve produce un
    rechazo de credenciales cuyo motivo no resulta evidente.
    """
    from core.config import _normalizar_clave_smtp

    assert _normalizar_clave_smtp("abcd efgh ijkl mnop") == "abcdefghijklmnop"
    assert _normalizar_clave_smtp("  abcd efgh ijkl mnop  ") == "abcdefghijklmnop"
    assert _normalizar_clave_smtp("abcdefghijklmnop") == "abcdefghijklmnop"


def test_no_se_alteran_las_contrasenias_de_otra_forma():
    """
    La normalizacion se restringe al formato de Google. Una contrasenia
    corriente que contenga espacios debe conservarse intacta: alterarla
    produciria un fallo de autenticacion imputado al servidor.
    """
    from core.config import _normalizar_clave_smtp

    assert _normalizar_clave_smtp("mi clave secreta") == "mi clave secreta"
    assert _normalizar_clave_smtp("Abcd Efgh Ijkl Mnop") == "Abcd Efgh Ijkl Mnop"
    assert _normalizar_clave_smtp("abcd efgh ijkl") == "abcd efgh ijkl"
    assert _normalizar_clave_smtp("") == ""
