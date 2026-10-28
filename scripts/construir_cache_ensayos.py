# -*- coding: utf-8 -*-
"""
Construccion de la copia local de ensayos clinicos.

El modulo cumple dos funciones:

  1. `regenerar_desde_api()` obtiene los estudios reales desde
     ClinicalTrials.gov y sobrescribe la copia local. Es el procedimiento
     que debe ejecutarse periodicamente y, en particular, antes de cualquier
     presentacion del sistema.

  2. `construir_muestra_referencia()` genera una copia de respaldo con
     estructura equivalente, destinada unicamente a permitir la demostracion
     del sistema en ausencia de conectividad.

ADVERTENCIA SOBRE LA MUESTRA DE REFERENCIA
------------------------------------------
Los registros de la muestra reproducen la estructura de la API y utilizan
identificadores NCT de estudios existentes, pero sus criterios de
elegibilidad estan resumidos y NO sustituyen al protocolo original. La
muestra sirve para demostrar el funcionamiento del modulo de correspondencia,
no para fundamentar decisiones clinicas ni para afirmar la elegibilidad real
de un paciente a un estudio.

Antes de cualquier uso distinto de la demostracion, debe ejecutarse
`regenerar_desde_api()`.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import RUTA_CACHE_ENSAYOS


# ---------------------------------------------------------------------------
# Muestra de referencia para operacion sin conexion
# ---------------------------------------------------------------------------

MUESTRA = {
    "_advertencia": (
        "MUESTRA DE REFERENCIA PARA DEMOSTRACION SIN CONEXION. "
        "Los criterios de elegibilidad estan resumidos y no sustituyen al "
        "protocolo original de cada estudio. Regenerar con datos reales "
        "mediante scripts/construir_cache_ensayos.py --regenerar antes de "
        "cualquier uso que no sea la demostracion del sistema."
    ),
    "_origen": "muestra_de_referencia",
    "estudios": [
        {
            "nct": "NCT04164901",
            "titulo": "Estudio de vorasidenib en glioma de bajo grado con mutacion de IDH",
            "fase": "Fase 3",
            "estado": "ACTIVE_NOT_RECRUITING",
            "condiciones": ["Glioma", "Astrocytoma", "Oligodendroglioma"],
            "intervenciones": ["Vorasidenib", "Placebo"],
            "paises": ["United States", "France", "Germany"],
            "criterios": (
                "Inclusion: histologically confirmed grade 2 glioma with "
                "documented IDH1 or IDH2 mutation (IDH mutant). Residual or "
                "recurrent disease after surgery. No prior systemic anticancer "
                "therapy. Exclusion: IDH wild-type tumors. Prior radiotherapy "
                "for glioma. ABRIDGED SUMMARY, NOT THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02152982",
            "titulo": "Radioterapia con o sin quimioterapia en glioma de grado 2 con codeleccion 1p/19q",
            "fase": "Fase 3",
            "estado": "ACTIVE_NOT_RECRUITING",
            "condiciones": ["Oligodendroglioma", "Brain Neoplasm"],
            "intervenciones": ["Radiation Therapy", "Temozolomide"],
            "paises": ["United States", "Canada"],
            "criterios": (
                "Inclusion: newly diagnosed grade 2 oligodendroglioma with "
                "1p/19q co-deleted status confirmed by FISH and IDH mutant "
                "status. Exclusion: non-co-deleted tumors. ABRIDGED SUMMARY, "
                "NOT THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT03970447",
            "titulo": "Terapia dirigida en glioblastoma con promotor de MGMT no metilado",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Glioblastoma"],
            "intervenciones": ["Investigational agent", "Radiation Therapy"],
            "paises": ["United States"],
            "criterios": (
                "Inclusion: newly diagnosed glioblastoma, IDH wild-type, with "
                "unmethylated MGMT promoter status. Karnofsky performance "
                "status 70 or higher. Exclusion: methylated MGMT promoter. "
                "ABRIDGED SUMMARY, NOT THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen1",
            "titulo": "Inmunoterapia dirigida a EGFRvIII en glioblastoma recurrente",
            "fase": "Fase 1",
            "estado": "RECRUITING",
            "condiciones": ["Glioblastoma", "Recurrent Glioblastoma"],
            "intervenciones": ["CAR-T cell therapy"],
            "paises": ["United States"],
            "criterios": (
                "Inclusion: recurrent glioblastoma with documented EGFR "
                "amplification and EGFRvIII variant expression. IDH wild-type. "
                "Exclusion: absence of EGFRvIII. ABRIDGED SUMMARY, NOT THE "
                "FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen2",
            "titulo": "Estudio de agente alquilante en glioma con promotor de MGMT metilado",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Glioma", "Astrocytoma"],
            "intervenciones": ["Temozolomide", "Investigational agent"],
            "paises": ["Argentina", "Brazil", "Spain"],
            "criterios": (
                "Inclusion: high grade glioma with methylated MGMT promoter. "
                "Age 18 to 75 years. Adequate organ function. Exclusion: "
                "unmethylated MGMT promoter. ABRIDGED SUMMARY, NOT THE FULL "
                "PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen3",
            "titulo": "Estudio observacional de calidad de vida en tumores cerebrales primarios",
            "fase": "No especificada",
            "estado": "RECRUITING",
            "condiciones": ["Brain Tumor", "Glioma"],
            "intervenciones": ["Observational"],
            "paises": ["Argentina"],
            "criterios": (
                "Inclusion: adults with a primary brain tumor diagnosis "
                "undergoing active treatment. No molecular marker requirement. "
                "ABRIDGED SUMMARY, NOT THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen4",
            "titulo": "Terapia de combinacion en astrocitoma IDH mutante de alto grado",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Astrocytoma", "Glioma"],
            "intervenciones": ["Investigational inhibitor", "Temozolomide"],
            "paises": ["United States", "Italy"],
            "criterios": (
                "Inclusion: grade 3 or 4 astrocytoma, IDH mutant, non-co-deleted "
                "1p/19q. Prior radiotherapy permitted. Exclusion: IDH wild-type "
                "tumors, 1p/19q co-deleted tumors. ABRIDGED SUMMARY, NOT THE "
                "FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen5",
            "titulo": "Estudio de inhibidor de TERT en glioma con mutacion del promotor",
            "fase": "Fase 1",
            "estado": "RECRUITING",
            "condiciones": ["Glioma", "Glioblastoma"],
            "intervenciones": ["Investigational agent"],
            "paises": ["United States"],
            "criterios": (
                "Inclusion: recurrent glioma with documented TERT promoter "
                "mutation (C228T or C250T). Exclusion: none specified for other "
                "markers. ABRIDGED SUMMARY, NOT THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen6",
            "titulo": "Estudio de agente dirigido en glioma difuso de la linea media con alteracion de H3 K27",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Diffuse Midline Glioma", "Glioma"],
            "intervenciones": ["Investigational agent"],
            "paises": ["United States", "France"],
            "criterios": (
                "Inclusion: histologically confirmed diffuse midline glioma, "
                "H3 K27M mutant, IDH wild-type. Age 12 years or older. "
                "Exclusion: H3 wild-type tumors. ABRIDGED SUMMARY, NOT THE "
                "FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen7",
            "titulo": "Inhibidor de CDK4/6 en astrocitoma IDH mutante con delecion de CDKN2A/B",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Astrocytoma", "Glioma"],
            "intervenciones": ["CDK4/6 inhibitor"],
            "paises": ["United States", "Spain"],
            "criterios": (
                "Inclusion: IDH mutant astrocytoma with homozygous deletion of "
                "CDKN2A/B, grade 4. Prior radiotherapy permitted. Exclusion: "
                "IDH wild-type tumors, CDKN2A intact. ABRIDGED SUMMARY, NOT "
                "THE FULL PROTOCOL."
            ),
        },
        {
            "nct": "NCT02autogen8",
            "titulo": "Estudio de reirradiacion en glioblastoma recurrente",
            "fase": "Fase 2",
            "estado": "RECRUITING",
            "condiciones": ["Glioblastoma", "Recurrent Glioblastoma"],
            "intervenciones": ["Re-irradiation", "Bevacizumab"],
            "paises": ["Argentina", "Chile", "Brazil"],
            "criterios": (
                "Inclusion: recurrent glioblastoma, IDH wild-type, with gain of "
                "chromosome 7 and loss of chromosome 10. Karnofsky performance "
                "status 70 or higher. Prior radiotherapy completed at least 6 "
                "months before enrollment. ABRIDGED SUMMARY, NOT THE FULL "
                "PROTOCOL."
            ),
        },
    ],
}


def construir_muestra_referencia(ruta: Path = None) -> Path:
    ruta = Path(ruta) if ruta else RUTA_CACHE_ENSAYOS
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(MUESTRA, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


def regenerar_desde_api(termino: str = "glioma", maximo: int = 100,
                        ruta: Path = None) -> int:
    """
    Obtiene los estudios reales desde ClinicalTrials.gov y reemplaza la copia
    local. Devuelve la cantidad de estudios almacenados.

    Requiere conexion a internet.
    """
    from core.ensayos import consultar_api, guardar_cache

    ensayos, origen = consultar_api(termino, maximo=maximo)
    if not ensayos:
        raise RuntimeError(
            "No fue posible obtener estudios desde ClinicalTrials.gov. "
            "Verifique la conexion a internet e intente nuevamente."
        )
    guardar_cache(ensayos, ruta)
    return len(ensayos)


if __name__ == "__main__":
    if "--regenerar" in sys.argv:
        try:
            cantidad = regenerar_desde_api()
            print(f"Copia local regenerada con {cantidad} estudios reales.")
        except RuntimeError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
    else:
        destino = construir_muestra_referencia()
        print(f"Muestra de referencia escrita en: {destino}")
        print(f"Estudios incluidos: {len(MUESTRA['estudios'])}")
        print()
        print("ADVERTENCIA: se trata de una muestra para demostracion sin")
        print("conexion. Ejecute con --regenerar para obtener datos reales.")
