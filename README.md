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
2. Extrae el **perfil molecular** (IDH, 1p/19q, MGMT, ATRX, TERT, EGFR, TP53,
   H3, CDKN2A/B y el patrón cromosómico +7/-10) mediante reglas explícitas y
   auditables, conforme a los biomarcadores que las guías del College of
   American Pathologists, AANP, AMP y SNO establecen para gliomas difusos.
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

El sistema admite varios proveedores. Google AI Studio ofrece un nivel
gratuito, si bien su disponibilidad depende de la configuración del proyecto:
cuando no está habilitado, la interfaz responde con un rechazo por permisos y
exige configurar un medio de pago.

| Proveedor | Medio de pago | Observación |
|---|---|---|
| `ollama` | No requerido | Ejecución local, sin clave de API |
| `google` | Según el proyecto | Modelos Gemini |
| `groq` | No requerido | Modelos de pesos abiertos |
| `cerebras` | No requerido | Modelos de pesos abiertos |
| `openrouter` | No requerido | Acceso unificado |
| `anthropic` | Requerido | Modelos Claude |
| `openai` | Requerido | Modelos GPT |

### Ejecución local

La alternativa `ollama` ejecuta el modelo de lenguaje en el propio equipo. No
requiere clave de API, medio de pago ni conexión a internet una vez descargado
el modelo, y la documentación procesada no abandona la máquina. Esta última
propiedad es la relevante en el dominio clínico: resuelve la objeción de
confidencialidad que pesa sobre cualquier servicio remoto.

```bash
# 1. Instalar Ollama desde https://ollama.com (instalador para Windows)
# 2. Descargar un modelo (una sola vez, alrededor de 2 GB)
ollama pull llama3.2:3b
# 3. Configurar el proyecto
#    en el archivo .env:  PROVEEDOR_LLM=ollama
```

Hecho esto, la interfaz genera los resúmenes mediante el modelo local. El
servicio queda escuchando en `http://127.0.0.1:11434`, de modo que el sistema
lo detecta sin configuración adicional. Un modelo de tres mil millones de
parámetros resulta suficiente para la tarea de redacción solicitada, dado que
la extracción de los datos estructurados corre por cuenta de las reglas
deterministas y no del modelo.

### Consulta a profesionales

Antes de la deliberación de la junta, el caso puede circularse a los
especialistas que corresponden a cada sección del resumen. El circuito deja
constancia de a quién se consultó, qué se le exhibió y qué respondió.

Dos restricciones gobiernan el envío:

- **El aviso no transporta documentación clínica.** Anuncia la consulta e
  identifica el caso por su código interno; el contenido se consulta en el
  sistema. Un mensaje de correo queda depositado de manera persistente en
  casillas ajenas al control institucional, de modo que incorporar allí el
  estudio anularía la premisa sobre la que se sostiene el sistema.
- **Cada consulta admite un único destinatario.** No se aceptan copias ni
  direcciones múltiples, y se rechazan las direcciones que contengan
  caracteres de control, que permitirían incorporar destinatarios ocultos.

La configuración SMTP es opcional (ver `.env.example`). Sin ella las consultas
se registran igualmente y el aviso queda disponible para su envío manual.

Los proveedores declaran financiar sus niveles gratuitos mediante el
aprovechamiento de las consultas recibidas. La circunstancia resulta
relevante en un dominio clínico: no corresponde dirigir documentación de
pacientes a un servicio que la incorpore a sus procesos de entrenamiento. Para
los casos sintéticos de demostración no presenta inconveniente, pero debe
considerarse antes de cualquier uso con documentación real.

Claves de API:
https://aistudio.google.com/apikey (Google) ·
https://console.groq.com/keys (Groq) ·
https://cloud.cerebras.ai (Cerebras)

Los proveedores renuevan su línea de modelos y retiran los identificadores
antiguos con frecuencia, de modo que el valor por defecto puede quedar
desactualizado y la llamada fallar con un error 404. Para conocer los
modelos habilitados para una clave determinada:

```bash
python scripts/verificar_entorno.py --modelos
```

El script comprueba cada candidato mediante una solicitud efectiva, dado que
figurar en el listado del proveedor no implica acceso: los modelos más
recientes suelen requerir facturación habilitada y rechazan la solicitud con
un código 403 aunque la interfaz los enumere.

Ante un modelo que no responde, el sistema prueba de manera automática una
lista de alternativas antes de recurrir al modo determinista, e informa en la
interfaz cuál utilizó. Fijar un identificador operativo en `MODELO_LLM` evita
ese tiempo de búsqueda en cada ejecución.

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

La suite comprende 146 pruebas distribuidas en cinco módulos. Varias de ellas
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
- Una oración repartida en dos renglones, como `ganancia del cromosoma 7 y
  perdida del` seguido de `cromosoma 10`, no se reconocía como una única
  afirmación, de modo que el marcador quedaba sin detectar.
- En los criterios de elegibilidad, una ventana de contexto que atravesaba la
  coma atribuía a un marcador el estado informado para otro: en `H3 K27M
  mutant, IDH wild-type` el estado wild-type se asignaba a H3, lo que
  descartaba el estudio para un paciente que sí reunía las condiciones.

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

### Casos de demostración

El proyecto incluye ocho casos sintéticos que cubren las entidades
diagnósticas más frecuentes en el adulto y tres situaciones que el sistema
debe resolver correctamente:

| Caso | Entidad | Situación que verifica |
|---|---|---|
| CASO-001 | Astrocitoma IDH mutante, grado 3 | Perfil molecular completo |
| CASO-002 | Glioblastoma IDH wild-type, grado 4 | Criterios moleculares de grado 4 |
| CASO-003 | Oligodendroglioma 1p/19q codelecionado, grado 2 | Lesión sin realce |
| CASO-004 | Glioma difuso de alto grado | Documentación incompleta y estudio no valorable |
| CASO-005 | Glioblastoma IDH wild-type | Redacción abreviada |
| CASO-006 | Glioma difuso de la línea media, H3 K27 alterado | Marcador que define la entidad |
| CASO-007 | Astrocitoma IDH mutante en seguimiento | Evaluación de respuesta según RANO |
| CASO-008 | Glioblastoma con aumento del realce | Pseudoprogresión dentro del campo irradiado |

La estructura y la terminología de los documentos siguen las guías de EANO,
el conjunto de datos de diagnóstico integrado del ICCR, las recomendaciones
de biomarcadores del College of American Pathologists junto con AANP, AMP y
SNO, y los criterios RANO para el informe de imágenes.

Los dos últimos casos corresponden a situaciones que se presentan
efectivamente en una junta multidisciplinaria y que el sistema no resuelve
por sí mismo: la evaluación de respuesta y la distinción entre progresión y
pseudoprogresión son decisiones del equipo tratante. El sistema se limita a
reunir y a citar la información sobre la que esa decisión se apoya.

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
