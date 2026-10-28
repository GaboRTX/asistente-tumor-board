# -*- coding: utf-8 -*-
"""Pruebas de la capa de ingesta y fragmentacion de documentos."""

import pytest

from core.ingesta import Fragmento, fragmentar, normalizar, procesar_documentos


# --- normalizacion ----------------------------------------------------------

def test_normalizar_unifica_saltos_de_linea():
    """Los retornos de carro se unifican al salto de linea estandar."""
    # Se emplean lineas con mayuscula inicial para que no las reuna la
    # logica de reconstruccion de parrafos, que se verifica aparte.
    assert normalizar("Linea1\r\nLinea2\rLinea3") == "Linea1\nLinea2\nLinea3"


def test_normalizar_reune_oracion_partida_en_dos_renglones():
    """
    Regresion. Los documentos exportados con ancho de renglon fijo parten
    oraciones a la mitad. Si no se reunen, los marcadores expresados a
    caballo del salto no se detectan.
    """
    texto = normalizar("ganancia del cromosoma 7 y perdida del\ncromosoma 10.")
    assert texto == "ganancia del cromosoma 7 y perdida del cromosoma 10."


def test_normalizar_preserva_los_encabezados():
    """Una linea siguiente con mayuscula inicial no continua la anterior."""
    texto = normalizar("RESULTADOS\nIDH1: mutacion detectada.")
    assert texto == "RESULTADOS\nIDH1: mutacion detectada."


def test_normalizar_preserva_los_elementos_de_enumeracion():
    texto = normalizar("Marcadores evaluados\n- idh1 mutado\n- mgmt metilado")
    assert texto.count("\n") == 2


def test_normalizar_no_reune_tras_punto():
    texto = normalizar("Primera oracion.\nsegunda linea")
    assert "\n" in texto


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


def test_los_fragmentos_no_cortan_palabras_por_la_mitad():
    """
    Regresion. El corte por limite de caracteres partia palabras, de modo que
    el fragmento siguiente comenzaba con un resto sin sentido. El defecto se
    detecto en CASO-001, donde el resumen incorporaba "tracion de gadolinio
    se observa realce heterogeneo" en lugar de la oracion completa.

    La consecuencia excede lo estetico: la cita que el profesional verifica
    contra el documento fuente debe reproducir texto existente.
    """
    from core.ingesta import fragmentar

    # Texto sin puntuacion terminal, que fuerza el corte por caracteres.
    texto = " ".join(f"palabra{n:03d}" for n in range(400))

    fragmentos = fragmentar(texto, tamanio=400, solapamiento=80)
    assert len(fragmentos) > 1, "el caso de prueba debe producir varios cortes"

    vocabulario = set(texto.split())
    for i, fragmento in enumerate(fragmentos, 1):
        for palabra in fragmento.split():
            assert palabra in vocabulario, (
                f"el fragmento {i} contiene el resto '{palabra}', "
                "producto de un corte en el interior de una palabra")


def test_el_solapamiento_no_arranca_en_mitad_de_palabra():
    from core.ingesta import _inicio_de_palabra

    texto = "Tras la administracion de gadolinio se observa realce"
    # Posicion en el interior de "administracion"
    posicion = texto.index("administracion") + 6
    corregida = _inicio_de_palabra(texto, posicion)
    assert texto[corregida:].startswith("de gadolinio")
