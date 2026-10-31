# Manual de uso y guion de demostración

Asistente de preparación de casos para junta de neuro-oncología
Proyecto Integrador — IFTS N.° 24 — Gabriel Marquez

---

## Índice

1. [Preparación previa](#1-preparación-previa)
2. [Cómo funciona el sistema](#2-cómo-funciona-el-sistema)
3. [Uso de cada pantalla](#3-uso-de-cada-pantalla)
4. [Guion de demostración](#4-guion-de-demostración)
5. [Preguntas previsibles y respuestas](#5-preguntas-previsibles-y-respuestas)
6. [Resolución de problemas](#6-resolución-de-problemas)

---

## 1. Preparación previa

### 1.1 Lista de verificación antes de una presentación

Realizar **con anticipación y con conexión a internet disponible**:

- [ ] Ejecutar `python scripts/verificar_entorno.py --completo` y confirmar
      que no se reportan errores. La verificación completa incluye el
      listado de modelos de lenguaje habilitados, de modo que permite
      detectar un identificador de modelo retirado por el proveedor.
- [ ] Confirmar que la verificación del modelo de embeddings resulta
      satisfactoria. La primera carga descarga aproximadamente 470 MB; una
      vez descargado el modelo queda almacenado localmente.
- [ ] Ejecutar `python scripts/construir_cache_ensayos.py --regenerar` para
      obtener estudios reales de ClinicalTrials.gov. Sin este paso el sistema
      opera con una muestra de referencia cuyos criterios están resumidos.
- [ ] Ejecutar `pytest tests/ -v` y verificar que las 146 pruebas pasan.
- [ ] Procesar al menos un caso completo y registrar una corrección, de modo
      que la pantalla de métricas muestre datos durante la presentación.
- [ ] Cargar un tiempo de preparación manual de referencia en la pantalla de
      métricas, indicando su fuente.

### 1.2 Puesta en marcha

```bash
cd asistente-tumor-board
source .venv/bin/activate        # en Windows:  .venv\Scripts\activate
streamlit run app/Inicio.py
```

Abrir `http://localhost:8501`.

**Recomendación:** ejecutar el sistema de manera local durante la
presentación, sin depender de la conexión del lugar.

---

## 2. Cómo funciona el sistema

### 2.1 Recorrido de un caso

```
Documentos del caso
        ↓
1. Ingesta          normalización a texto procesable
        ↓
2. Fragmentación    división en unidades de tamaño acotado, con solapamiento
        ↓
3. Vectorización    representación de cada fragmento para su recuperación
        ↓
4. Recuperación     selección de los fragmentos pertinentes a cada campo
        ↓
5. Generación       redacción del resumen, citando la fuente de cada dato
        ↓
6. Verificación     contraste contra la extracción determinista
        ↓
7. Ensayos          correspondencia con estudios según el perfil molecular
        ↓
Reporte para la junta  →  revisión y decisión del equipo médico
```

### 2.2 Los dos modos de generación

El sistema puede generar el resumen de dos maneras.

**Con modelo de lenguaje.** Se recuperan los fragmentos pertinentes y se
proveen al modelo junto con instrucciones que le prohíben afirmar datos
ausentes. Produce una redacción más fluida.

**Por reglas deterministas.** Se seleccionan las oraciones que corresponden a
cada campo mediante patrones explícitos. La redacción es menos elaborada,
pero el resultado es reproducible y auditable.

#### Dónde se ejecuta el modelo de lenguaje

El modelo puede ejecutarse en un servicio remoto o en el propio equipo. La
segunda alternativa, disponible mediante Ollama, resulta preferible en este
dominio: la documentación procesada no abandona la máquina, de modo que la
objeción de confidencialidad que pesa sobre cualquier servicio remoto queda
resuelta por construcción y no por contrato.

Puesta en marcha, por una única vez:

1. Instalar Ollama desde https://ollama.com
2. En una terminal: `ollama pull llama3.2:3b` (descarga de unos 2 GB)
3. En el archivo `.env` del proyecto: `PROVEEDOR_LLM=ollama`

No requiere clave de API ni medio de pago. Durante la defensa conviene
mencionarlo: es el argumento que separa a este sistema de una consulta a un
servicio público de inteligencia artificial.

La elección del modelo depende de la memoria del equipo. Conviene comenzar por
el más liviano y ascender solo si la redacción resulta insuficiente, dado que
la extracción de los datos estructurados no depende del modelo sino de las
reglas deterministas.

| Modelo | Descarga | Memoria recomendada |
|---|---|---|
| `llama3.2:3b` | 2,0 GB | 8 GB |
| `qwen2.5:7b` | 4,7 GB | 16 GB |
| `llama3.1:8b` | 4,7 GB | 16 GB |

Si el modelo indicado no se encuentra descargado, o si el servicio no está en
ejecución, la interfaz lo informa con el comando exacto que corresponde
ejecutar. Ante cualquier falla el sistema continúa operando en modo
determinista, de modo que la demostración no se interrumpe.

El segundo modo no es únicamente un respaldo ante la falta de conexión:
funciona además como **verificación** del primero. Tras cada generación con
modelo de lenguaje, el sistema contrasta el resultado contra la extracción
determinista realizada sobre los mismos documentos y advierte toda
discrepancia.

#### Qué campo genera cada procedimiento

Los dos procedimientos no compiten por los mismos campos. Cada tarea se asigna
al que corresponde:

| Campo | Procedimiento |
|---|---|
| Datos clínicos, antecedentes, hallazgos anatomopatológicos, hallazgos imagenológicos, tratamientos previos | Modelo de lenguaje |
| Perfil molecular | Reglas deterministas, siempre |

El perfil molecular no es prosa sino un conjunto de pares marcador-estado. Las
reglas lo producen completo y ordenado, mientras que un modelo de lenguaje
tiende a abreviarlo y omitir marcadores. Encomendárselo no aportaría redacción
y sí introduciría riesgo. **El modelo redacta, las reglas reportan.**

En consecuencia, la verificación de consistencia recae sobre los campos que
redacta el modelo. Contrastar un campo generado por las reglas contra esas
mismas reglas produciría una conformidad aparente sin contenido informativo, y
ocultaría que la verificación dejó de aportar garantía. Lo que se verifica,
entonces, es que el modelo no **contradiga** los marcadores en los campos
narrativos, donde el informe anatomopatológico y la discusión del caso los
mencionan con frecuencia.

### 2.3 El ciclo de aprendizaje

```
El profesional corrige un campo
        ↓
Se redacta una regla textual reutilizable
        ↓
La regla queda PENDIENTE  →  no influye sobre ningún caso
        ↓
Un profesional la valida en la pantalla de curación
        ↓
La regla pasa a ACTIVA  →  se recupera al generar casos posteriores
        ↓
Puede desactivarse en cualquier momento, con efecto inmediato
```

El sistema **no reentrena el modelo**. Modifica aquello que el modelo observa
al generar, no sus parámetros. Esto permite identificar qué corrección
influyó sobre cada salida y revertirla sin reprocesar nada.

---

## 3. Uso de cada pantalla

### Inicio

Muestra el estado del sistema (modo de generación, motor de recuperación,
casos registrados) y el listado de casos procesados. Incluye un botón para
verificar la disponibilidad del modelo de embeddings.

### Carga de caso

Dos modalidades:

- **Casos de demostración:** selección de uno de los cinco casos sintéticos
  incluidos. Permite consultar el contenido de los documentos antes de
  procesar.
- **Cargar documentos:** carga de archivos PDF o de texto propios. Requiere
  un identificador anonimizado.

Durante el procesamiento se muestran las etapas del recorrido. Al finalizar
se presenta el perfil molecular detectado.

### Resumen del caso

Pantalla central. Cada campo se acompaña de:

- El desplegable **«Ver las N fuentes de este campo»**, que muestra el
  fragmento textual exacto del que proviene el dato.
- El interruptor **«Corregir»**, que abre el formulario de corrección.

Al pie se presenta el perfil molecular con la evidencia textual de cada
marcador.

Si el sistema detecta discrepancias entre el resumen generado y la extracción
determinista, las muestra en un recuadro de observaciones.

**Para registrar una corrección:** activar «Corregir», editar el contenido,
seleccionar el tipo de error y confirmar. Requiere haber indicado el nombre
del profesional en el panel lateral.

### Estudios clínicos

Presenta los marcadores utilizados como criterio, el resultado de la búsqueda
y los estudios propuestos.

Para cada estudio se informa **por qué correspondió**: qué marcador originó la
coincidencia. Los estudios cuyos criterios de exclusión resultan
incompatibles con el caso no se proponen, y su cantidad se informa entre los
indicadores.

El interruptor **«Usar copia local»** permite operar sin conexión.

### Reporte final

Genera el documento consolidado en texto o PDF. Incluye siempre, de manera no
configurable, la constancia de que se trata de un documento de apoyo que
requiere validación profesional.

### Consultas a profesionales

Circula el caso a los especialistas antes de la deliberación. Para cada
consulta se registra nombre, especialidad y una dirección de correo, y el
sistema envía un aviso.

El profesional recibe el **caso completo** con **su sección resaltada**: el
patólogo ve los hallazgos anatomopatológicos destacados, el imagenólogo los
imagenológicos. Recibe el caso entero porque una sección aislada no admite
lectura clínica, y se le señala aquella sobre la cual se requiere su dictamen.

Cada consulta se responde con **Conforme** o **Con observaciones**. La segunda
exige el detalle de la observación: un caso marcado como objetado sin
constancia de la objeción dejaría a la junta sin nada sobre lo cual deliberar.

El sistema conserva una **instantánea de lo exhibido** al momento de la
consulta. Si el resumen se regenera después, la respuesta sigue refiriéndose a
lo que el profesional efectivamente vio.

Dos restricciones que conviene poder explicar en la defensa:

1. **El aviso por correo no lleva documentación clínica.** Identifica el caso
   por su código interno y remite al sistema. El correo atraviesa servidores
   de terceros y queda depositado en las casillas de emisor y destinatario; el
   contenido permanece donde reside.
2. **Una consulta, un destinatario.** No se admiten copias ni direcciones
   múltiples, y se rechazan las que contengan caracteres de control, que
   permitirían incorporar destinatarios ocultos al mensaje.

Sin servidor de correo configurado la pantalla funciona igual: la consulta se
registra y se informa que el aviso quedó pendiente de envío.

### Informe de estudios completo (expediente)

Al pie del **Reporte final**. Arma un paquete ZIP con:

- `expediente.pdf`: el expediente completo, con carátula, índice y
  numeración. Cada campo del resumen aparece junto al documento que lo
  respalda, y los campos sin respaldo se señalan como tales.
- `expediente.txt`: el mismo contenido en texto plano.
- `documentacion_origen/`: los documentos tal como fueron aportados, para que
  quien revise pueda contrastar el expediente contra la fuente.
- `CONTENIDO.txt`: manifiesto del paquete.

El expediente incluye el marco normativo (WHO CNS5, CAP/AANP/AMP/SNO, EANO,
ICCR, RANO), el detalle de qué documento se leyó y con qué método, el
registro de la revisión por especialidad con sus observaciones, y las
advertencias del sistema.

**Qué no hace, y por qué conviene poder explicarlo.** El expediente **no
indica ni avala tratamiento alguno**. El sistema tiene prohibido sugerir
conductas terapéuticas, y esa prohibición no cede por el destinatario del
documento. Lo que aporta es el legajo: lo que consta, con su respaldo, y
quién lo revisó. La indicación la formula y la suscribe el médico tratante.

La distinción no es formal. Un documento emitido por un programa que afirmara
que corresponde cubrir determinada terapia sería un acto médico sin médico, y
su eventual error no tendría responsable. Una prueba automatizada recorre el
expediente y rechaza toda fórmula de indicación o aval.

### Curación de correcciones

Tres pestañas: pendientes, activas y desactivadas. Cada corrección puede
consultarse junto con su caso de origen y el contenido original.

Las acciones disponibles son validar, desestimar, desactivar y reactivar.
Todas quedan registradas con autor y fecha.

### Métricas

Presenta tiempos de procesamiento, comparación con el tiempo de preparación
manual, correcciones por caso y tendencia de la tasa de corrección.

Si no hay tiempos manuales cargados, la pantalla ofrece el formulario para
registrarlos indicando su fuente.

---

## 4. Guion de demostración

Duración estimada: entre 8 y 10 minutos, dejando margen para preguntas dentro
de los 15 minutos de la defensa.

### Antes de comenzar

- Aplicación en ejecución, con un caso ya procesado y una corrección
  registrada de antemano.
- Navegador con una sola pestaña abierta, a pantalla completa.
- Pantalla de Inicio a la vista.

---

### Minuto 0 a 1 — El problema

> «Cuando un equipo de neuro-oncología discute un caso en junta
> multidisciplinaria, la información del paciente está repartida en cuatro
> documentos distintos: la historia clínica, el informe de patología, el de
> secuenciación genómica y el de imágenes. Alguien tiene que leerlos,
> ordenarlos y sintetizarlos antes de la reunión. Ese trabajo consume tiempo
> médico especializado y hoy se hace de forma manual.
>
> Lo que construí no decide el tratamiento. Prepara el caso.»

---

### Minuto 1 a 3 — Procesamiento en vivo

Ir a **Carga de caso**, seleccionar CASO-001, desplegar los documentos
brevemente y presionar **Procesar caso**.

Mientras avanzan las etapas:

> «Acá se ve el recorrido: normaliza los documentos, los fragmenta, los
> vectoriza, recupera lo pertinente a cada campo del resumen y genera. Lo que
> están viendo es la arquitectura que presenté en la Entrega 2,
> ejecutándose.»

Al finalizar, señalar el perfil molecular detectado.

> «Detectó siete marcadores moleculares leyendo los informes.»

---

### Minuto 3 a 5 — Trazabilidad

Ir a **Resumen del caso**.

> «Este es el resumen estructurado. Pero lo importante no es el texto.»

Desplegar las fuentes de un campo.

> «Cada dato indica de qué fragmento de qué documento salió. El profesional
> puede verificar cualquier afirmación sin abrir el original.
>
> Esto responde a algo concreto. El antecedente más conocido de IA aplicada a
> oncología es Watson for Oncology, de IBM, que fracasó. No fracasó porque el
> modelo fuera malo: fracasó porque sus recomendaciones no podían
> contrastarse contra una fuente verificable. Mi sistema no afirma nada que
> no pueda mostrar de dónde lo sacó. Y cuando el dato no consta, lo declara
> en lugar de completarlo.»

Mostrar un campo con la leyenda «No consta en la documentación aportada», si
lo hay.

---

### Minuto 5 a 7 — Ensayos clínicos

Ir a **Estudios clínicos** y ejecutar la búsqueda.

> «A partir del perfil molecular busca estudios en curso. Pero fíjense en
> esto.»

Señalar la línea «Correspondencia por».

> «No da una lista sin fundamento: dice qué marcador originó cada
> coincidencia.»

Señalar el indicador de descartados.

> «Y estos se descartaron porque sus criterios de exclusión son incompatibles
> con este paciente.
>
> Acá encontré el error más serio de todo el desarrollo. El sistema leía los
> criterios de elegibilidad como un bloque único de texto. Entonces, cuando
> un protocolo decía "exclusión: IDH wild-type", lo interpretaba como un
> requisito. El resultado era que le proponía a cada paciente justamente los
> estudios para los que no era elegible. Lo corregí separando la sección de
> inclusión de la de exclusión, y dejé una prueba de regresión para que no
> vuelva a pasar.»

---

### Minuto 7 a 9 — El aprendizaje

Ir a **Resumen del caso**, activar «Corregir» en un campo, modificarlo y
registrar la corrección.

> «Cuando el profesional corrige algo, el sistema no lo descarta: lo
> convierte en una regla.»

Ir a **Curación de correcciones**.

> «Pero la regla queda pendiente. No influye sobre ningún caso hasta que
> alguien la valida.
>
> Esto es deliberado. Si el sistema incorporara las correcciones de manera
> automática, un error de carga se propagaría a todos los casos siguientes
> sin que nadie lo advirtiera. En un contexto clínico eso no es admisible.
>
> Y no hago ajuste fino del modelo. Lo evalué y lo descarté por tres motivos:
> necesitaría miles de ejemplos, el conocimiento incorporado no sería
> trazable, y un error así no se puede revertir sin reentrenar. Acá cada
> regla tiene autor, fecha y caso de origen, y se desactiva al instante.»

Validar la corrección para mostrar que pasa a activa.

---

### Casos disponibles para la demostración

Conviene conocer qué muestra cada caso, para elegir según lo que pregunte el
jurado:

- **CASO-001**, astrocitoma IDH mutante: perfil molecular completo, es el
  caso de referencia para la demostración principal.
- **CASO-002**, glioblastoma IDH wild-type: útil para mostrar cómo los
  criterios moleculares establecen el grado 4.
- **CASO-004**: documentación incompleta. Sirve para mostrar que el sistema
  declara lo que no consta en lugar de completarlo.
- **CASO-006**, glioma de la línea media H3 K27 alterado: el marcador define
  la entidad y dispara un estudio clínico específico.
- **CASO-007**: evaluación de respuesta según RANO, con reducción del 69,3%
  del producto de diámetros.
- **CASO-008**: pseudoprogresión. Es el caso más interesante si preguntan por
  los límites del sistema, porque la distinción entre progresión y
  pseudoprogresión es una decisión clínica que la herramienta no toma.

---

### Minuto 9 a 10 — Resultados

Ir a **Métricas**.

> «El sistema mide su propio tiempo de procesamiento en cada ejecución.
>
> Ahora, una aclaración importante: este ahorro no es un ahorro neto. El
> tiempo manual sale de un relevamiento con profesionales, no de una medición
> del sistema, y el tiempo automático no incluye la revisión médica, que
> sigue siendo necesaria. Lo dejé marcado en la propia pantalla porque
> presentar el número suelto sobreestimaría lo que el trabajo demuestra.
>
> Y este gráfico muestra las correcciones por caso en el tiempo. Si el ciclo
> de retroalimentación funciona, la tendencia debería descender.»

---

### Cierre

> «El sistema no reemplaza al médico. Prepara el caso para que la junta
> discuta sobre información ya ordenada y verificable, en lugar de dedicar
> ese tiempo a reunirla.»

---

### Demostración opcional: operación sin conexión

Si el tiempo lo permite, o ante una pregunta sobre robustez:

Ir a **Estudios clínicos**, activar «Usar copia local» y volver a buscar.

> «Si se cae la conexión, el sistema no se detiene: degrada a su copia local
> y avisa en pantalla que lo hizo. Lo mismo ocurre con la generación y con la
> recuperación. La degradación nunca es silenciosa.»

---

## 5. Preguntas previsibles y respuestas

### «¿Esto reemplaza al médico?»

No. Prepara la documentación del caso. No emite diagnósticos ni indicaciones
terapéuticas, y todo reporte lleva esa constancia de manera no configurable.
La decisión es del equipo tratante.

### «¿Cómo sabés que no inventa datos?»

Por tres mecanismos combinados. El prompt prohíbe explícitamente afirmar
datos ausentes y obliga a declarar cuando algo no consta. Cada campo cita el
fragmento del que proviene, de modo que la afirmación es verificable. Y
después de generar, el sistema contrasta el resultado contra una extracción
determinista por reglas sobre los mismos documentos, y advierte toda
discrepancia.

### «¿Por qué no hiciste fine-tuning?»

Lo evalué y lo descarté por tres razones. Requiere un volumen de ejemplos muy
superior al que produce un servicio en el plazo de este proyecto. El
conocimiento incorporado no es trazable: el modelo lo aplica sin que se pueda
identificar el caso de origen. Y un error incorporado así no se revierte sin
reentrenar. El mecanismo que implementé conserva la trazabilidad completa y
permite desactivar cualquier regla al instante.

### «¿Qué pasa si se cae internet?»

El sistema sigue funcionando. Tiene modo de respaldo en sus tres componentes
externos: genera por reglas deterministas, recupera con TF-IDF y consulta una
copia local de estudios. Puedo mostrarlo ahora mismo. Lo importante es que la
degradación nunca es silenciosa: la interfaz informa qué modo está usando y
por qué.

### «¿De dónde salieron los casos de demostración?»

Son sintéticos, construidos por mí. Lo que sí tomé de fuentes reales es la
estructura y la terminología: el informe anatomopatológico sigue el formato
en capas del conjunto de datos del ICCR, los biomarcadores y las técnicas son
los que recomiendan el College of American Pathologists junto con AANP, AMP y
SNO, los esquemas terapéuticos y las dosis provienen de las guías de EANO, y
los informes de imágenes aplican los criterios RANO de medición bidimensional.
Ningún caso reproduce textualmente un informe publicado.

### «¿Usaste datos reales de pacientes?»

No. Trabajé con casos sintéticos construidos a partir de patrones descriptos
en la literatura publicada, en cumplimiento de la Ley 25.326. La interfaz
solicita únicamente identificadores anonimizados y todo el procesamiento
ocurre en la máquina local.

### «¿Por qué Streamlit y no una aplicación web real?»

La lógica está íntegramente desacoplada de la interfaz: el directorio `core/`
no tiene ninguna dependencia de Streamlit. Streamlit es la capa de
presentación del prototipo. El mismo núcleo puede exponerse a través de una
API REST sin modificar una línea de la lógica de negocio. Para un prototipo
de ciencia de datos, invertir el tiempo en un frontend propio no habría
aportado valor al problema que el trabajo aborda.

### «¿Qué tan preciso es?»

La extracción de marcadores moleculares se verifica contra 146 pruebas
automatizadas, incluidos los ocho casos de demostración completos. Ahora,
sobre precisión clínica real necesito ser preciso yo también: la validación
con profesionales se hizo sobre un número acotado de casos, así que esto es
una prueba de concepto, no una validación clínica. Lo dejé asentado entre las
limitaciones del trabajo.

### «¿Encontraste errores durante el desarrollo?»

Varios, y los conservé como pruebas de regresión. El más grave fue el de los
criterios de elegibilidad: el sistema leía los marcadores mencionados bajo
exclusión como si fueran requisitos, y terminaba proponiendo a cada paciente
los estudios para los que no era elegible. Otro fue que en una enumeración de
inmunohistoquímica atribuía a un marcador el estado informado de otro. Y un
tercero, en el verificador de consistencia: comparaba por inclusión de
subcadena, con lo cual «no mutado» contenía «mutado» y la contradicción nunca
se detectaba. Ese último lo encontró una prueba que había escrito yo mismo.

### «¿Cuánto cuesta operarlo?»

Los componentes son de código abierto y sin costo de licenciamiento. El único
costo variable es la API del modelo de lenguaje, que se factura por tokens
consumidos. El desarrollo se realizó íntegramente sobre el nivel gratuito de
un proveedor. El detalle del análisis económico corresponde a la Entrega 3.

### «¿Se puede usar para otros tumores?»

La arquitectura sí. Lo específico de gliomas son las reglas de extracción de
marcadores y las consultas de recuperación, que están concentradas en dos
módulos. Extenderlo a otra patología implica definir sus marcadores y sus
patrones, no rehacer el sistema.

---

## 6. Resolución de problemas

### La aplicación no inicia

Verificar que el entorno virtual esté activo y que las dependencias estén
instaladas:

```bash
pip install -r requirements.txt
python scripts/verificar_entorno.py
```

### El sistema indica que usa TF-IDF en lugar de embeddings

Indica que `sentence-transformers` no está instalado o que el modelo no pudo
descargarse. El sistema es operativo de todos modos. Para habilitar la
recuperación semántica, con conexión disponible:

```bash
pip install sentence-transformers
python scripts/verificar_entorno.py --completo
```

### No aparecen estudios clínicos

Comprobar que exista la copia local:

```bash
python scripts/construir_cache_ensayos.py --regenerar   # con conexión
python scripts/construir_cache_ensayos.py               # muestra de referencia
```

### El resumen se genera por reglas y no por modelo de lenguaje

Indica que no hay clave de API configurada o que la llamada falló. Verificar
el archivo `.env`. La pantalla de Inicio informa el proveedor detectado.

Si el mensaje menciona un error 404 sobre el modelo, el identificador
configurado no está habilitado para esa clave. Los proveedores retiran
modelos con frecuencia. Para conocer los disponibles:

```bash
python scripts/verificar_entorno.py --modelos
```

Luego consignar uno de los identificadores listados en `MODELO_LLM` dentro
del archivo `.env`.

### Un PDF no se procesa

El sistema extrae texto, no realiza reconocimiento óptico. Un PDF compuesto
por imágenes escaneadas requiere procesamiento previo con una herramienta de
OCR.

### Los casos de demostración no aparecen

```bash
python scripts/generar_casos_demo.py
```

### Reiniciar los datos del sistema

Elimina todos los casos, correcciones y métricas registrados:

```bash
rm data/asistente.db
```
