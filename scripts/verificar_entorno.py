# -*- coding: utf-8 -*-
"""
Verificacion del entorno de ejecucion.

Comprueba que el sistema pueda operar correctamente antes de su utilizacion,
en particular antes de una presentacion en un entorno sin conectividad
garantizada.

Uso:
    python scripts/verificar_entorno.py
    python scripts/verificar_entorno.py --completo    (incluye el modelo de
                                                       embeddings y la API)

La verificacion distingue entre condiciones que impiden la operacion y
condiciones que unicamente degradan la calidad del resultado. El sistema
esta disenado para seguir siendo utilizable en el segundo caso, de modo que
una advertencia no implica que la herramienta no pueda utilizarse.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


VERDE = "\033[92m"
AMARILLO = "\033[93m"
ROJO = "\033[91m"
GRIS = "\033[90m"
FIN = "\033[0m"

resultados = {"ok": 0, "advertencia": 0, "error": 0}


def ok(mensaje, detalle=""):
    resultados["ok"] += 1
    print(f"  {VERDE}[ OK ]{FIN} {mensaje}")
    if detalle:
        print(f"         {GRIS}{detalle}{FIN}")


def advertencia(mensaje, detalle=""):
    resultados["advertencia"] += 1
    print(f"  {AMARILLO}[ ADV ]{FIN} {mensaje}")
    if detalle:
        print(f"         {GRIS}{detalle}{FIN}")


def error(mensaje, detalle=""):
    resultados["error"] += 1
    print(f"  {ROJO}[ ERR ]{FIN} {mensaje}")
    if detalle:
        print(f"         {GRIS}{detalle}{FIN}")


def seccion(titulo):
    print(f"\n{titulo}")
    print("-" * 72)


# ---------------------------------------------------------------------------

def verificar_python():
    seccion("1. Interprete de Python")
    version = sys.version_info
    if version >= (3, 10):
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        error(f"Python {version.major}.{version.minor}",
              "Se requiere Python 3.10 o superior.")


def verificar_dependencias():
    seccion("2. Dependencias")

    obligatorias = {
        "streamlit": "interfaz de usuario",
        "pandas": "presentacion de metricas",
        "numpy": "operaciones vectoriales",
        "sklearn": "motor de recuperacion TF-IDF",
        "requests": "consultas a servicios externos",
        "pypdf": "lectura de documentos PDF",
        "reportlab": "exportacion del reporte a PDF",
    }
    opcionales = {
        "sentence_transformers": "recuperacion semantica por embeddings",
        "dotenv": "lectura de la configuracion desde archivo .env",
    }

    for modulo, proposito in obligatorias.items():
        try:
            __import__(modulo)
            ok(f"{modulo}", proposito)
        except ImportError:
            error(f"{modulo} no esta instalado", f"Necesario para: {proposito}. "
                  f"Ejecute: pip install -r requirements.txt")

    for modulo, proposito in opcionales.items():
        try:
            __import__(modulo)
            ok(f"{modulo}", proposito)
        except ImportError:
            advertencia(f"{modulo} no esta instalado",
                        f"Sin esta dependencia el sistema opera igualmente. "
                        f"Se pierde: {proposito}.")


def verificar_estructura():
    seccion("3. Estructura del proyecto")

    from core.config import DIR_CASOS_DEMO, DIR_DATOS, RUTA_CACHE_ENSAYOS

    if DIR_DATOS.exists():
        ok("Directorio de datos", str(DIR_DATOS))
    else:
        error("No existe el directorio de datos")

    if DIR_CASOS_DEMO.exists():
        casos = [d for d in DIR_CASOS_DEMO.iterdir() if d.is_dir()]
        if casos:
            ok(f"Casos de demostracion disponibles: {len(casos)}",
               ", ".join(sorted(c.name for c in casos)))
        else:
            advertencia("No hay casos de demostracion",
                        "Ejecute: python scripts/generar_casos_demo.py")
    else:
        advertencia("No existe el directorio de casos de demostracion")

    if RUTA_CACHE_ENSAYOS.exists():
        import json
        try:
            datos = json.loads(RUTA_CACHE_ENSAYOS.read_text(encoding="utf-8"))
            cantidad = len(datos.get("estudios", []))
            if datos.get("_origen") == "muestra_de_referencia":
                advertencia(
                    f"Copia local de ensayos: {cantidad} estudios (muestra de referencia)",
                    "Los criterios estan resumidos. Regenere con datos reales: "
                    "python scripts/construir_cache_ensayos.py --regenerar")
            else:
                ok(f"Copia local de ensayos: {cantidad} estudios reales")
        except Exception as exc:
            error("La copia local de ensayos no pudo leerse", str(exc))
    else:
        advertencia("No existe la copia local de ensayos",
                    "Sin conexion no habra estudios disponibles. Ejecute: "
                    "python scripts/construir_cache_ensayos.py")


def verificar_base_datos():
    seccion("4. Base de datos")
    try:
        from core import db
        db.inicializar()
        casos = db.listar_casos()
        correcciones = db.listar_correcciones()
        ok("Base de datos operativa",
           f"{len(casos)} caso(s) registrado(s), "
           f"{len(correcciones)} correccion(es) almacenada(s)")
    except Exception as exc:
        error("La base de datos no pudo inicializarse", str(exc))


def verificar_pipeline():
    seccion("5. Procesamiento de un caso de prueba")
    try:
        from core.config import DIR_CASOS_DEMO
        from core.ingesta import cargar_caso_demo, procesar_documentos
        from core.perfil_molecular import extraer_perfil
        from core.rag import generar_resumen

        casos = sorted([d for d in DIR_CASOS_DEMO.iterdir() if d.is_dir()])
        if not casos:
            advertencia("No hay casos disponibles para verificar el pipeline")
            return

        caso = casos[0]
        documentos = cargar_caso_demo(caso)
        fragmentos = procesar_documentos(caso.name, documentos)

        if not fragmentos:
            error("El caso de prueba no produjo fragmentos procesables")
            return
        ok(f"Ingesta y fragmentacion: {len(fragmentos)} fragmentos de {caso.name}")

        perfil = extraer_perfil(fragmentos)
        if perfil.informados:
            detalle = ", ".join(f"{k}={v.valor}"
                                for k, v in perfil.informados.items())
            ok(f"Extraccion del perfil molecular: {len(perfil.informados)} marcadores",
               detalle)
        else:
            advertencia("No se detectaron marcadores en el caso de prueba")

        resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)
        completos = sum(1 for c in resultado.campos if c.tiene_dato)
        ok(f"Generacion del resumen: {completos} de {len(resultado.campos)} "
           f"campos documentados",
           f"Tiempo de procesamiento: {resultado.segundos} s (modo determinista)")

    except Exception as exc:
        error("El pipeline de procesamiento fallo", f"{type(exc).__name__}: {exc}")


def verificar_reporte():
    seccion("6. Generacion del reporte")
    try:
        from core.config import DIR_CASOS_DEMO
        from core.ingesta import cargar_caso_demo, procesar_documentos
        from core.rag import generar_resumen
        from core import reporte

        casos = sorted([d for d in DIR_CASOS_DEMO.iterdir() if d.is_dir()])
        if not casos:
            advertencia("Sin casos disponibles para verificar el reporte")
            return

        fragmentos = procesar_documentos(casos[0].name,
                                         cargar_caso_demo(casos[0]))
        resultado = generar_resumen(fragmentos, forzar_sin_conexion=True)

        texto = reporte.generar_texto(casos[0].name, resultado.como_dict())
        ok(f"Reporte en texto: {len(texto)} caracteres")

        try:
            ruta = reporte.generar_pdf(casos[0].name, resultado.como_dict())
            ok(f"Reporte en PDF: {ruta.name}",
               f"{ruta.stat().st_size} bytes en {ruta.parent}")
        except RuntimeError as exc:
            advertencia("La exportacion a PDF no esta disponible", str(exc))

    except Exception as exc:
        error("La generacion del reporte fallo", f"{type(exc).__name__}: {exc}")


def verificar_llm():
    seccion("7. Modelo de lenguaje")
    from core.llm import detectar_proveedor

    proveedor, modelo = detectar_proveedor()
    if proveedor == "offline":
        advertencia("Sin clave de API configurada",
                    "El sistema operara en modo determinista, que es "
                    "reproducible y auditable pero produce resumenes menos "
                    "fluidos. Para habilitar el modelo de lenguaje, complete "
                    "CLAVE_API_LLM en el archivo .env")
    else:
        ok(f"Proveedor configurado: {proveedor}", f"Modelo: {modelo}")


def verificar_embeddings(completo: bool):
    seccion("8. Motor de recuperacion")
    from core.vectorizacion import MOTOR_EMBEDDINGS, motor_disponible

    motor = motor_disponible()
    if motor != MOTOR_EMBEDDINGS:
        advertencia("Se utilizara el motor TF-IDF",
                    "Instale sentence-transformers para habilitar la "
                    "recuperacion semantica por embeddings.")
        return

    ok("Biblioteca de embeddings instalada")

    if not completo:
        advertencia("No se verifico la carga efectiva del modelo",
                    "La primera carga requiere descargar el modelo (unos 470 MB) "
                    "con conexion a internet. Ejecute este script con --completo "
                    "para verificarlo, preferentemente con anticipacion a "
                    "cualquier presentacion.")
        return

    print(f"  {GRIS}Cargando el modelo de embeddings, puede demorar...{FIN}")
    from core.vectorizacion import verificar_modelo
    disponible, mensaje = verificar_modelo()
    if disponible:
        ok("Modelo de embeddings operativo", mensaje)
    else:
        advertencia("El modelo de embeddings no pudo cargarse", mensaje)


def verificar_api_ensayos(completo: bool):
    seccion("9. API de ensayos clinicos")
    if not completo:
        advertencia("No se verifico la conexion con ClinicalTrials.gov",
                    "Ejecute con --completo para comprobarla.")
        return

    from core.ensayos import consultar_api
    ensayos, origen = consultar_api("glioma", maximo=3)
    if ensayos:
        ok(f"ClinicalTrials.gov responde correctamente: {len(ensayos)} estudios")
    else:
        advertencia("No se obtuvo respuesta de ClinicalTrials.gov",
                    "El sistema utilizara la copia local de estudios.")


# ---------------------------------------------------------------------------

def main():
    completo = "--completo" in sys.argv

    print("=" * 72)
    print("  VERIFICACION DEL ENTORNO")
    print("  Asistente de preparacion de casos para junta de neuro-oncologia")
    print("=" * 72)
    if not completo:
        print(f"{GRIS}  Modo rapido. Ejecute con --completo para verificar "
              f"tambien\n  el modelo de embeddings y la conexion a "
              f"ClinicalTrials.gov.{FIN}")

    verificar_python()
    verificar_dependencias()
    verificar_estructura()
    verificar_base_datos()
    verificar_pipeline()
    verificar_reporte()
    verificar_llm()
    verificar_embeddings(completo)
    verificar_api_ensayos(completo)

    print("\n" + "=" * 72)
    print(f"  Resultado: {VERDE}{resultados['ok']} correctas{FIN}, "
          f"{AMARILLO}{resultados['advertencia']} advertencias{FIN}, "
          f"{ROJO}{resultados['error']} errores{FIN}")
    print("=" * 72)

    if resultados["error"]:
        print(f"\n{ROJO}Hay condiciones que impiden la operacion del sistema.{FIN}")
        print("Revise los elementos marcados como error antes de continuar.")
        return 1

    if resultados["advertencia"]:
        print(f"\n{AMARILLO}El sistema es operativo.{FIN} Las advertencias "
              f"indican funcionalidades degradadas o no verificadas,")
        print("no impedimentos para su utilizacion.")
        return 0

    print(f"\n{VERDE}El entorno esta correctamente configurado.{FIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
