# -*- coding: utf-8 -*-
"""
Pruebas de la correspondencia con ensayos clinicos.

La separacion entre criterios de inclusion y de exclusion concentra la mayor
parte de estas pruebas. Su ausencia produjo, durante el desarrollo, el
defecto mas grave detectado en el proyecto: el sistema proponia a cada
paciente precisamente los estudios para los que no era elegible, porque leia
los marcadores mencionados bajo exclusion como si fueran requisitos.
"""

from core.ensayos import (Ensayo, evaluar_correspondencia, separar_criterios)


def ensayo_con(criterios, titulo="Estudio de prueba", condiciones=None):
    return Ensayo(nct="NCT00000000", titulo=titulo, fase="Fase 2",
                  estado="RECRUITING", condiciones=condiciones or ["Glioma"],
                  criterios=criterios)


# ---------------------------------------------------------------------------
# Separacion de secciones
# ---------------------------------------------------------------------------

def test_separar_reconoce_ambas_secciones():
    inclusion, exclusion = separar_criterios(
        "Inclusion: IDH mutant glioma. Exclusion: prior radiotherapy.")
    assert "idh mutant" in inclusion.lower()
    assert "radiotherapy" in exclusion.lower()
    assert "idh mutant" not in exclusion.lower()


def test_sin_seccion_de_exclusion_todo_es_inclusion():
    inclusion, exclusion = separar_criterios("Patients with IDH mutant glioma.")
    assert "idh mutant" in inclusion.lower()
    assert exclusion == ""


def test_separar_texto_vacio():
    assert separar_criterios("") == ("", "")
    assert separar_criterios(None) == ("", "")


# ---------------------------------------------------------------------------
# Correspondencia positiva
# ---------------------------------------------------------------------------

def test_coincidencia_por_criterio_de_inclusion():
    ensayo = ensayo_con("Inclusion criteria: patients with IDH mutant glioma.")
    resultado = evaluar_correspondencia(ensayo, [("IDH", "mutado")])
    assert resultado.elegible
    assert any("IDH" in c for c in resultado.coincidencias)
    assert resultado.puntaje > 0


def test_varias_coincidencias_elevan_el_puntaje():
    ensayo = ensayo_con(
        "Inclusion: IDH mutant glioma with methylated MGMT promoter.")
    una = evaluar_correspondencia(ensayo, [("IDH", "mutado")])
    dos = evaluar_correspondencia(
        ensayo, [("IDH", "mutado"), ("MGMT", "metilado")])
    assert dos.puntaje >= una.puntaje
    assert len(dos.coincidencias) == 2


# ---------------------------------------------------------------------------
# Exclusiones (regresiones del defecto principal)
# ---------------------------------------------------------------------------

def test_marcador_bajo_exclusion_no_se_lee_como_requisito():
    """
    Regresion. Un estudio para pacientes IDH mutados que excluye a los
    wild-type no debe proponerse a un paciente wild-type.
    """
    ensayo = ensayo_con(
        "Inclusion: grade 2 glioma with IDH mutation. "
        "Exclusion: IDH wild-type tumors.")
    resultado = evaluar_correspondencia(ensayo, [("IDH", "no mutado")])
    assert not resultado.elegible
    assert resultado.puntaje == 0
    assert resultado.coincidencias == []


def test_estudio_que_requiere_el_estado_contrario_queda_excluido():
    """
    Regresion. Un estudio que exige codelecion 1p/19q no debe proponerse a un
    paciente sin codelecion.
    """
    ensayo = ensayo_con(
        "Inclusion: oligodendroglioma with 1p/19q co-deleted status. "
        "Exclusion: non-co-deleted tumors.")
    resultado = evaluar_correspondencia(
        ensayo, [("1p/19q", "codelecion ausente")])
    assert not resultado.elegible


def test_exclusion_negada_no_descarta_al_paciente():
    """
    Regresion. 'Exclusion: absence of EGFRvIII' excluye a quien NO presenta el
    marcador, de modo que un paciente que si lo presenta resulta compatible.
    """
    ensayo = ensayo_con(
        "Inclusion: recurrent glioblastoma with EGFR amplification and "
        "EGFRvIII expression. Exclusion: absence of EGFRvIII.")
    resultado = evaluar_correspondencia(ensayo, [("EGFR", "amplificado")])
    assert resultado.elegible
    assert resultado.coincidencias


def test_exclusion_del_estado_contrario_indica_compatibilidad():
    ensayo = ensayo_con(
        "Inclusion: high grade glioma. Exclusion: unmethylated MGMT promoter.")
    resultado = evaluar_correspondencia(ensayo, [("MGMT", "metilado")])
    assert resultado.elegible
    assert resultado.coincidencias or resultado.compatibilidades


# ---------------------------------------------------------------------------
# Casos limite
# ---------------------------------------------------------------------------

def test_estudio_sin_criterios_moleculares_no_se_descarta():
    ensayo = ensayo_con(
        "Inclusion: adults with a primary brain tumor. No molecular "
        "requirement.")
    resultado = evaluar_correspondencia(ensayo, [("IDH", "mutado")])
    assert resultado.elegible
    assert resultado.coincidencias == []


def test_perfil_vacio_no_produce_error():
    ensayo = ensayo_con("Inclusion: IDH mutant glioma.")
    resultado = evaluar_correspondencia(ensayo, [])
    assert resultado.elegible
    assert resultado.coincidencias == []


def test_criterios_vacios_no_producen_error():
    resultado = evaluar_correspondencia(ensayo_con(""), [("IDH", "mutado")])
    assert resultado is not None


def test_la_url_se_construye_desde_el_identificador():
    ensayo = ensayo_con("Inclusion: glioma.")
    assert ensayo.nct in ensayo.url
    assert ensayo.url.startswith("https://clinicaltrials.gov/study/")


def test_el_resultado_informa_el_criterio_de_correspondencia():
    """
    La correspondencia debe ser auditable: el sistema informa que marcador
    la origino, y no unicamente el resultado.
    """
    ensayo = ensayo_con("Inclusion: IDH mutant glioma.")
    resultado = evaluar_correspondencia(ensayo, [("IDH", "mutado")])
    assert "IDH" in resultado.coincidencias[0]
    assert "mutado" in resultado.coincidencias[0]
