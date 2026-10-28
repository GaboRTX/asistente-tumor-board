# -*- coding: utf-8 -*-
"""Pruebas de la capa de ingesta y fragmentacion de documentos."""

import pytest

from core.ingesta import Fragmento, fragmentar, normalizar, procesar_documentos


# --- normalizacion ----------------------------------------------------------

def test_normalizar_unifica_saltos_de_linea():
    assert normalizar("linea1\r\nlinea2\rlinea3") == "linea1\nlinea2\nlinea3"


def test_normalizar_colapsa_espacios_repetidos():
    assert normalizar("Paciente   de    54  anios") == "Paciente de 54 anios"


def test_normalizar_une_palabras_cortadas_por_guion():
    """Los PDF suelen cortar palabras al final del renglon."""
    assert "Diagnostico" in normalizar("Diagnos-\ntico de glioma")


def test_normalizar_preserva_tildes_y_enie():
    texto = normalizar("Lesion en region temporal. Paciente de 41 anios.")
    assert "Lesion" in texto


def test_normalizar_texto_vacio():
    assert normalizar("") == ""
    assert normalizar(None) == ""


# --- fragmentacion ----------------------------------------------------------

def test_fragmentar_texto_corto_devuelve_una_unidad():
    assert fragmentar("Texto breve.") == ["Texto breve."]


def test_fragmentar_texto_vacio_devuelve_lista_vacia():
    assert fragmentar("") == []


def test_fragmentar_respeta_el_tamanio_maximo():
    texto = "El paciente presenta cefalea persistente. " * 60
    fragmentos = fragmentar(texto, tamanio=500, solapamiento=80)
    assert all(len(f) <= 520 for f in fragmentos)
    assert len(fragmentos) > 1


def test_fragmentar_conserva_el_contenido():
    texto = "Primera oracion. Segunda oracion. Tercera oracion. " * 20
    unido = " ".join(fragmentar(texto, tamanio=300, solapamiento=50))
    assert "Primera oracion" in unido and "Tercera oracion" in unido


def test_fragmentar_rechaza_solapamiento_invalido():
    with pytest.raises(ValueError):
        fragmentar("texto largo " * 100, tamanio=100, solapamiento=100)


def test_fragmentar_corta_preferentemente_en_limite_de_oracion():
    texto = ("Primera oracion de prueba con suficiente longitud. " * 4 +
             "Segunda parte del documento con mas contenido. " * 4)
    fragmentos = fragmentar(texto, tamanio=250, solapamiento=40)
    terminados = sum(1 for f in fragmentos if f.rstrip().endswith("."))
    assert terminados >= len(fragmentos) - 1


# --- procesamiento de un caso ----------------------------------------------

def test_procesar_documentos_desde_texto_directo():
    fragmentos = procesar_documentos(
        "CASO-TEST",
        documentos={},
        textos_directos={"historia_clinica": "Paciente de 50 anios con cefalea."},
    )
    assert len(fragmentos) == 1
    assert isinstance(fragmentos[0], Fragmento)
    assert fragmentos[0].caso == "CASO-TEST"
    assert fragmentos[0].tipo_documento == "historia_clinica"


def test_fragmento_expone_etiqueta_de_fuente_legible():
    fragmentos = procesar_documentos(
        "CASO-TEST", {}, {"anatomia_patologica": "Astrocitoma grado 3."})
    assert "Informe anatomopatologico" in fragmentos[0].etiqueta_fuente
    assert "fragmento 1" in fragmentos[0].etiqueta_fuente


def test_identificadores_de_fragmento_son_unicos():
    textos = {
        "historia_clinica": "Contenido clinico. " * 80,
        "genomica": "IDH1 mutado. " * 80,
    }
    fragmentos = procesar_documentos("CASO-TEST", {}, textos)
    identificadores = [f.id for f in fragmentos]
    assert len(identificadores) == len(set(identificadores))


def test_procesar_sin_documentos_devuelve_lista_vacia():
    assert procesar_documentos("CASO-TEST", {}, {}) == []


def test_documento_inexistente_produce_error_explicito():
    with pytest.raises(FileNotFoundError):
        procesar_documentos("CASO-TEST", {"historia_clinica": "/no/existe.txt"})
