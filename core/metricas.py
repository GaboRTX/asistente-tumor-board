"""
Calculo de metricas de desempenio del sistema.

El modulo produce la evidencia cuantitativa asociada a la hipotesis de
trabajo del proyecto: que la herramienta reduce el tiempo de preparacion de
casos sin comprometer la calidad de la informacion.

Sobre la medicion del tiempo
----------------------------
El tiempo de procesamiento automatico se registra en cada ejecucion y no
requiere estimacion. El tiempo de preparacion manual, en cambio, no puede
medirse desde el sistema: se releva con los profesionales y se carga como
valor de referencia, dejando constancia de su fuente.

Esta distincion se mantiene explicita en toda la presentacion de resultados.
Informar un ahorro de tiempo sin aclarar que el termino de comparacion
proviene de un relevamiento externo, y no de una medicion del sistema,
sobreestimaria el alcance de la evidencia disponible.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional

from core import db
from core.config import CAMPOS_RESUMEN


ETIQUETAS_CAMPO = dict(CAMPOS_RESUMEN)


def metricas_procesamiento(ruta=None) -> Dict:
    """Tiempos de procesamiento automatico registrados por el sistema."""
    generaciones = [g for g in db.listar_generaciones(ruta=ruta)
                    if g["tipo"] == "resumen"]

    if not generaciones:
        return {
            "casos_procesados": 0,
            "segundos_promedio": 0.0,
            "segundos_mediana": 0.0,
            "segundos_minimo": 0.0,
            "segundos_maximo": 0.0,
            "por_modo": {},
        }

    tiempos = [g["segundos"] for g in generaciones]
    por_modo: Dict[str, int] = {}
    for g in generaciones:
        por_modo[g["modo"]] = por_modo.get(g["modo"], 0) + 1

    return {
        "casos_procesados": len({g["caso_id"] for g in generaciones}),
        "generaciones_totales": len(generaciones),
        "segundos_promedio": round(statistics.mean(tiempos), 2),
        "segundos_mediana": round(statistics.median(tiempos), 2),
        "segundos_minimo": round(min(tiempos), 2),
        "segundos_maximo": round(max(tiempos), 2),
        "por_modo": por_modo,
    }


def comparacion_con_referencia(ruta=None) -> Dict:
    """
    Compara el tiempo automatico con el tiempo manual de referencia.

    Devuelve un diccionario que incluye siempre la fuente del valor manual y
    la cantidad de relevamientos que lo sustentan, de modo que el dato nunca
    se presente descontextualizado.
    """
    procesamiento = metricas_procesamiento(ruta=ruta)
    referencias = db.listar_tiempos_manuales(ruta=ruta)

    if not referencias:
        return {
            "disponible": False,
            "motivo": ("No se registraron tiempos de preparacion manual de "
                       "referencia. La comparacion requiere al menos un "
                       "relevamiento con profesionales."),
            "procesamiento": procesamiento,
        }

    minutos = [r["minutos"] for r in referencias]
    manual_promedio = statistics.mean(minutos)
    automatico_minutos = procesamiento["segundos_promedio"] / 60.0

    ahorro = manual_promedio - automatico_minutos
    porcentaje = (ahorro / manual_promedio * 100) if manual_promedio else 0.0

    return {
        "disponible": True,
        "manual_minutos_promedio": round(manual_promedio, 1),
        "manual_relevamientos": len(referencias),
        "manual_fuentes": sorted({r["fuente"] for r in referencias}),
        "automatico_minutos_promedio": round(automatico_minutos, 2),
        "ahorro_minutos": round(ahorro, 1),
        "ahorro_porcentaje": round(porcentaje, 1),
        "advertencia": ("El tiempo manual proviene de un relevamiento con "
                        "profesionales, no de una medicion realizada por el "
                        "sistema. El tiempo automatico no incluye el tiempo de "
                        "revision y validacion del resumen por parte del "
                        "profesional, que sigue siendo necesario."),
        "procesamiento": procesamiento,
    }


def metricas_calidad(ruta=None) -> Dict:
    """
    Indicadores de calidad de las salidas generadas.

    La tasa de correccion por caso es el indicador central: su evolucion
    descendente a lo largo de los casos procesados constituye la evidencia
    de que el ciclo de retroalimentacion mejora el desempenio del sistema.
    """
    generaciones = [g for g in db.listar_generaciones(ruta=ruta)
                    if g["tipo"] == "resumen"]
    feedback = db.listar_feedback(ruta=ruta)

    if not generaciones:
        return {"casos_con_generacion": 0, "correcciones_por_caso": [],
                "promedio_correcciones": 0.0, "campos_mas_corregidos": {}}

    # Correcciones por caso, ordenadas cronologicamente
    correcciones_por_caso: Dict[int, int] = {}
    for g in generaciones:
        correcciones_por_caso.setdefault(g["caso_id"], 0)
    for f in feedback:
        correcciones_por_caso[f["caso_id"]] = correcciones_por_caso.get(f["caso_id"], 0) + 1

    casos = db.listar_casos(ruta=ruta)
    orden = {c["id"]: c["fecha_carga"] for c in casos}
    serie = sorted(
        [{"caso_id": cid, "correcciones": n,
          "identificador": next((c["identificador"] for c in casos if c["id"] == cid), str(cid)),
          "fecha": orden.get(cid, "")}
         for cid, n in correcciones_por_caso.items()],
        key=lambda d: d["fecha"],
    )

    campos: Dict[str, int] = {}
    for f in feedback:
        etiqueta = ETIQUETAS_CAMPO.get(f["campo"], f["campo"])
        campos[etiqueta] = campos.get(etiqueta, 0) + 1

    valores = [d["correcciones"] for d in serie]

    return {
        "casos_con_generacion": len(serie),
        "correcciones_por_caso": serie,
        "promedio_correcciones": round(statistics.mean(valores), 2) if valores else 0.0,
        "campos_mas_corregidos": dict(sorted(campos.items(),
                                             key=lambda kv: -kv[1])),
        "total_correcciones": len(feedback),
    }


def tendencia_aprendizaje(ruta=None) -> Dict:
    """
    Compara la tasa de correccion de la primera mitad de los casos con la de
    la segunda, como indicador de la evolucion del desempenio.

    Con pocos casos el resultado no es concluyente, y el modulo lo declara
    explicitamente en lugar de presentar una tendencia sin sustento.
    """
    calidad = metricas_calidad(ruta=ruta)
    serie = calidad["correcciones_por_caso"]

    if len(serie) < 4:
        return {
            "concluyente": False,
            "motivo": (f"Se requieren al menos 4 casos procesados para evaluar "
                       f"una tendencia. Actualmente hay {len(serie)}."),
            "casos": len(serie),
        }

    mitad = len(serie) // 2
    primera = [d["correcciones"] for d in serie[:mitad]]
    segunda = [d["correcciones"] for d in serie[mitad:]]

    prom_primera = statistics.mean(primera)
    prom_segunda = statistics.mean(segunda)
    variacion = prom_segunda - prom_primera

    return {
        "concluyente": True,
        "casos": len(serie),
        "promedio_primera_mitad": round(prom_primera, 2),
        "promedio_segunda_mitad": round(prom_segunda, 2),
        "variacion": round(variacion, 2),
        "mejora": variacion < 0,
        "advertencia": ("Con un numero reducido de casos, esta comparacion es "
                        "indicativa y no sustituye una validacion estadistica."),
    }


def resumen_general(ruta=None) -> Dict:
    """Conjunto completo de metricas para su presentacion en la interfaz."""
    from core import feedback as mod_feedback

    return {
        "procesamiento": metricas_procesamiento(ruta=ruta),
        "comparacion": comparacion_con_referencia(ruta=ruta),
        "calidad": metricas_calidad(ruta=ruta),
        "tendencia": tendencia_aprendizaje(ruta=ruta),
        "retroalimentacion": mod_feedback.estadisticas(ruta=ruta),
    }
