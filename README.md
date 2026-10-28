# Asistente de preparación de casos para junta de neuro-oncología

Prototipo funcional de un sistema de asistencia documental basado en
inteligencia artificial, orientado a reducir el tiempo de preparación de
casos previos a su discusión en juntas multidisciplinarias de tumores.

**Proyecto Integrador** — Tecnicatura Superior en Ciencia de Datos e
Inteligencia Artificial, Instituto de Formación Técnica Superior N.° 24.

---

## Qué hace

A partir de los documentos de un caso de glioma (historia clínica, informe
anatomopatológico, informe de secuenciación genómica e informe de imágenes),
el sistema:

1. Genera un **resumen estructurado** del caso, citando para cada campo el
   fragmento documental que lo respalda.
2. Extrae el **perfil molecular** (IDH, 1p/19q, MGMT, ATRX, TERT, EGFR, TP53)
   mediante reglas explícitas y auditables.
3. Propone **estudios clínicos** de ClinicalTrials.gov compatibles con ese
   perfil, informando el criterio que originó cada correspondencia.
4. Registra las **correcciones** de los profesionales y las incorpora, previa
   validación, a la generación de casos posteriores.
5. Mide el **tiempo de procesamiento** y la evolución de la tasa de corrección.

El sistema asiste en la preparación documental del caso. No emite
diagnósticos ni indicaciones terapéuticas: la decisión clínica corresponde
al equipo médico tratante.

---

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone <url-del-repositorio>
cd asistente-tumor-board

python -m venv .venv
source .venv/bin/activate        # en Windows:  .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuración opcional del modelo de lenguaje

El sistema es **plenamente funcional sin configuración adicional**: en ese
caso genera los resúmenes mediante reglas deterministas. Para habilitar la
generación asistida por un modelo de lenguaje:

```bash
cp .env.example .env
# completar CLAVE_API_LLM en el archivo .env
```

Google AI Studio ofrece un nivel gratuito suficiente para desarrollo:
https://aistudio.google.com/apikey

### Verificación del entorno

```bash
python scripts/verificar_entorno.py
python scripts/verificar_entorno.py --completo   # incluye modelo y API
```

Ejecutar la verificación **completa con anticipación** si el sistema se
utilizará en un entorno sin conectividad garantizada: la primera carga del
modelo de embeddings requiere descargarlo (aproximadamente 470 MB).

### Puesta en marcha

```bash
streamlit run app/Inicio.py
```

La aplicación queda disponible en `http://localhost:8501`. Se ejecuta
íntegramente en la máquina local: los documentos no se transmiten a
servicios externos, salvo los fragmentos enviados al proveedor del modelo
de lenguaje cuando esa opción está configurada.

---

## Estructura del proyecto

```
asistente-tumor-board/
├── app/                        interfaz de usuario (Streamlit)
│   ├── Inicio.py               panel de casos y estado del sistema
│   ├── comun.py                estado de sesión y utilidades compartidas
│   └── pages/
│       ├── 1_Carga_de_caso.py
│       ├── 2_Resumen_del_caso.py
│       ├── 3_Estudios_clinicos.py
│       ├── 4_Reporte_final.py
│       ├── 5_Curacion_de_correcciones.py
│       └── 6_Metricas.py
├── core/                       lógica del sistema, sin dependencia de la interfaz
│   ├── config.py               configuración y parámetros
│   ├── db.py                   persistencia (SQLite)
│   ├── ingesta.py              lectura, normalización y fragmentación
│   ├── vectorizacion.py        índice vectorial y recuperación
│   ├── perfil_molecular.py     extracción determinista de marcadores
│   ├── llm.py                  acceso al modelo de lenguaje
│   ├── rag.py                  pipeline de recuperación y generación
│   ├── ensayos.py              correspondencia con ensayos clínicos
│   ├── feedback.py             ciclo de retroalimentación
│   ├── metricas.py             indicadores de desempeño
│   └── reporte.py              generación del reporte final
├── data/
│   ├── casos_demo/             casos sintéticos de demostración
│   └── ensayos_cache.json      copia local de estudios
├── scripts/
│   ├── verificar_entorno.py
│   ├── generar_casos_demo.py
│   └── construir_cache_ensayos.py
├── tests/                      suite de pruebas (pytest)
└── docs/
    └── MANUAL.md               manual de uso y guion de demostración
```

La lógica reside íntegramente en `core/`, sin ninguna dependencia de
Streamlit. La interfaz se limita a invocar funciones y presentar resultados.
Esta separación permite ejecutar las pruebas sin levantar la interfaz y
exponer el mismo núcleo a través de otra capa de presentación sin modificar
una sola línea de la lógica de negocio.

---

## Pruebas

```bash
pytest tests/ -v
```

La suite comprende 116 pruebas distribuidas en cinco módulos. Varias de ellas
corresponden a defectos efectivamente detectados durante el desarrollo y se
conservan como pruebas de regresión, entre ellos:

- Una línea que describe la técnica empleada (`Metilación de MGMT por
  pirosecuenciación`) era interpretada como un resultado positivo.
- En una enumeración de inmunohistoquímica, el estado informado de un
  marcador se atribuía a otro (`IDH1 R132H negativo, ATRX conservado`).
- Los marcadores mencionados bajo los criterios de **exclusión** de un
  estudio se leían como requisitos, de modo que el sistema proponía a cada
  paciente precisamente los estudios para los que no era elegible.
- La verificación de contradicciones comparaba por inclusión de subcadena,
  con lo que `no mutado` contenía `mutado` y la contradicción nunca se
  detectaba.

---

## Decisiones de diseño

### Trazabilidad como requisito, no como añadido

Cada campo del resumen indica el fragmento documental que lo respalda, y
ningún dato se afirma sin respaldo: cuando no consta, el sistema lo declara
explícitamente en lugar de completarlo por inferencia.

Esta restricción responde a la lección del caso IBM Watson for Oncology,
cuyo fracaso no se debió a la insuficiencia del modelo sino a que sus
recomendaciones no podían contrastarse contra fuentes verificables ni contra
las guías locales de cada institución.

### Aprendizaje sin ajuste fino del modelo

El sistema no reentrena el modelo de lenguaje. Las correcciones de los
profesionales se convierten en reglas textuales que se recuperan e incorporan
al contexto de generación de casos posteriores.

El ajuste fino fue evaluado y descartado: requiere un volumen de ejemplos muy
superior al disponible, el conocimiento incorporado no es trazable, y un
error así incorporado no puede revertirse sin reentrenar. El mecanismo
implementado conserva autor, fecha y caso de origen de cada regla, y permite
desactivarla con efecto inmediato.

### Validación previa de las correcciones

Ninguna corrección influye sobre casos futuros hasta ser validada. Una
corrección errónea aplicada automáticamente se propagaría a todos los casos
siguientes sin que nadie lo advirtiera, de modo que la curación no es un
trámite administrativo sino un control de seguridad del propio mecanismo de
aprendizaje.

### Degradación controlada

Los tres componentes que dependen de recursos externos admiten un modo de
respaldo:

| Componente | Modo principal | Modo de respaldo |
|---|---|---|
| Generación | Modelo de lenguaje | Reglas deterministas |
| Recuperación | Embeddings multilingües | TF-IDF sobre n-gramas |
| Ensayos clínicos | API de ClinicalTrials.gov | Copia local |

La degradación **nunca es silenciosa**: el sistema informa en la interfaz qué
modo está utilizando y por qué motivo descendió al modo de respaldo.

### Tratamiento de los datos

El prototipo se desarrolla y valida sobre casos sintéticos construidos a
partir de patrones descriptos en la literatura publicada. No se utilizan
datos reales de pacientes, en cumplimiento de la Ley N.° 25.326 de Protección
de Datos Personales. La interfaz solicita únicamente identificadores
anonimizados.

---

## Limitaciones conocidas

- El alcance se circunscribe a gliomas en pacientes adultos.
- La extracción de marcadores opera sobre documentación redactada en español
  y puede no reconocer formulaciones no contempladas en sus reglas.
- La correspondencia con ensayos clínicos evalúa criterios moleculares; no
  contempla edad, estado funcional ni tratamientos previos, que deben
  verificarse contra el protocolo completo.
- La copia local de estudios incluida es una muestra de referencia con
  criterios resumidos, destinada exclusivamente a la demostración sin
  conexión. Antes de cualquier otro uso debe ejecutarse
  `python scripts/construir_cache_ensayos.py --regenerar`.
- La validación con profesionales se realizó sobre un número acotado de
  casos, por lo que sus resultados constituyen una prueba de concepto y no
  una validación clínica.

---

## Autor

Gabriel Marquez — Proyecto Integrador, IFTS N.° 24, 2026.
