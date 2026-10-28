# -*- coding: utf-8 -*-
"""Configuracion compartida por las pruebas."""

import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture
def base_temporal():
    """
    Base de datos aislada para cada prueba.

    Las pruebas nunca deben operar sobre la base de datos real del sistema:
    su contenido corresponde a casos efectivamente procesados y a las
    correcciones validadas por los profesionales.
    """
    from core import db
    ruta = Path(tempfile.mkdtemp()) / "prueba.db"
    db.inicializar(ruta)
    return ruta


@pytest.fixture
def fragmentos_caso():
    """Fragmentos de un caso sintetico completo."""
    return [
        {"id": "T::hc::0", "texto":
            "Paciente de 41 anios, sexo masculino. Cefalea de tres meses de "
            "evolucion y crisis convulsivas. Escala de Karnofsky: 80.",
         "tipo_documento": "historia_clinica",
         "etiqueta_fuente": "Historia clinica (fragmento 1)"},
        {"id": "T::ap::0", "texto":
            "Astrocitoma IDH mutado, grado 3 de la OMS. Ki-67 del 12%.",
         "tipo_documento": "anatomia_patologica",
         "etiqueta_fuente": "Informe anatomopatologico (fragmento 1)"},
        {"id": "T::gen::0", "texto":
            "IDH1: mutacion p.R132H detectada. Promotor de MGMT metilado. "
            "Codelecion 1p/19q: ausente.",
         "tipo_documento": "genomica",
         "etiqueta_fuente": "Informe de secuenciacion genomica (fragmento 1)"},
        {"id": "T::img::0", "texto":
            "Resonancia magnetica: lesion frontal izquierda de 4.2 cm con "
            "realce heterogeneo y edema perilesional.",
         "tipo_documento": "imagenes",
         "etiqueta_fuente": "Informe de imagenes (fragmento 1)"},
    ]
