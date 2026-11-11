# Guía de instalación

Asistente de preparación de casos para junta de neuro-oncología.

Esta guía parte de una máquina sin nada instalado y llega al sistema
funcionando. Está escrita para Windows, que es el caso más frecuente, y
cada paso indica su equivalente en macOS y Linux.

---

## Índice

1. [Antes de empezar](#1-antes-de-empezar)
2. [Instalar Python](#2-instalar-python)
3. [Descargar el proyecto](#3-descargar-el-proyecto)
4. [Crear el entorno virtual e instalar dependencias](#4-crear-el-entorno-virtual-e-instalar-dependencias)
5. [Verificar la instalación](#5-verificar-la-instalación)
6. [Ejecutar el sistema](#6-ejecutar-el-sistema)
7. [Cargar un caso](#7-cargar-un-caso)
8. [Modelo de lenguaje local, opcional](#8-modelo-de-lenguaje-local-opcional)
9. [Capacidades opcionales adicionales](#9-capacidades-opcionales-adicionales)
10. [Instalación sin conexión](#10-instalación-sin-conexión)
11. [Solución de problemas](#11-solución-de-problemas)
12. [Lista de comprobación previa a una demostración](#12-lista-de-comprobación-previa-a-una-demostración)

---

## 1. Antes de empezar

### Qué hace falta

| Requisito | Detalle |
|---|---|
| Sistema operativo | Windows 10 u 11, macOS 12 o posterior, o Linux |
| Python | Versión 3.10 a 3.13. **No use 3.14 ni 3.15** |
| Espacio en disco | 1,2 GB |
| Conexión a internet | Solo durante la instalación |
| Permisos de administrador | No son necesarios si se sigue esta guía |

### Tiempo estimado

Entre 15 y 25 minutos con una conexión razonable, contando la instalación
de Python. Las dependencias son 55 paquetes que suman **166 MB de
descarga** y ocupan **714 MB** una vez instalados. Sobre una conexión rápida
la instalación demora menos de un minuto.

Las cifras provienen de una instalación limpia verificada, no de una
estimación.

### Sobre la versión de Python

El sistema exige **Python 3.10 o posterior**, y conviene no pasar de 3.13.
Las versiones más nuevas suelen carecer de paquetes precompilados para
bibliotecas como NumPy o scikit-learn, de modo que `pip` intenta compilarlas
desde el código fuente y falla si la máquina no tiene un compilador de C.

Si la máquina ya tiene Python, verifique la versión antes de avanzar:

```powershell
py --version
```

### Una advertencia que conviene leer

Si va a usar el sistema en una **máquina ajena y en una fecha
comprometida**, como una demostración o una defensa, no deje la instalación
para ese día. La red de una institución puede ser lenta, el antivirus puede
bloquear la descarga y el equipo puede no permitir instalar programas.

Dos alternativas, en orden de preferencia:

1. **Llevar su propia máquina** con todo instalado y probado. Elimina todos
   los riesgos de una sola vez.
2. **Preparar un paquete sin conexión** con antelación. El procedimiento
   está en el [apartado 10](#10-instalación-sin-conexión).

---

## 2. Instalar Python

### Windows

1. Abra <https://www.python.org/downloads/windows/>
2. Descargue el instalador de **Python 3.13** (*Windows installer 64-bit*).
   No descargue la versión más reciente si es 3.14 o posterior.
3. Ejecute el instalador.
4. **Marque la casilla «Add python.exe to PATH»** antes de continuar. Es el
   error más común y obliga a reinstalar.
5. Elija *Install Now*.

No hacen falta permisos de administrador: el instalador ofrece una
instalación para el usuario actual.

Cierre la terminal y abra una nueva. Después compruebe:

```powershell
py --version
```

Debe responder `Python 3.13.x` o similar.

### macOS

```bash
brew install python@3.13
python3 --version
```

Sin Homebrew, descargue el instalador desde
<https://www.python.org/downloads/macos/>.

### Linux (Debian y Ubuntu)

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
python3 --version
```

---

## 3. Descargar el proyecto

Hay dos vías. La primera es preferible porque permite actualizar después.

### Vía A, con Git

Si la máquina no tiene Git, descárguelo de <https://git-scm.com/download/win>
e instálelo con las opciones por defecto.

```powershell
cd %USERPROFILE%\Documents
git clone https://github.com/GaboRTX/asistente-tumor-board.git
cd asistente-tumor-board
```

En macOS y Linux:

```bash
cd ~/Documents
git clone https://github.com/GaboRTX/asistente-tumor-board.git
cd asistente-tumor-board
```

### Vía B, sin Git

1. Abra <https://github.com/GaboRTX/asistente-tumor-board>
2. Botón verde **Code**, luego **Download ZIP**
3. Descomprima el archivo en una carpeta
4. Abra una terminal dentro de esa carpeta

> **Atención.** Si descarga el ZIP, el comando `git pull` no va a funcionar
> y recibirá el error `not a git repository`. Para actualizar tendrá que
> descargar el ZIP de nuevo.

### Evite la carpeta de Descargas

Descomprimir el ZIP dos veces produce carpetas como
`asistente-tumor-board (2)`, y se vuelve fácil trabajar sobre la copia
equivocada. Conviene mover el proyecto a `Documentos`.

### Verificar que está en la carpeta correcta

```powershell
dir
```

Debe ver, entre otros, `README.md`, `requirements.txt` y las carpetas
`app`, `core`, `data`, `docs`, `scripts` y `tests`.

---

## 4. Crear el entorno virtual e instalar dependencias

El entorno virtual mantiene las dependencias del proyecto separadas del
Python del sistema. Evita conflictos con otros programas instalados en la
máquina.

### Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> **Por qué se invoca `.venv\Scripts\python.exe` y no se activa el entorno.**
> El comando de activación es un script de PowerShell, y la directiva de
> ejecución de Windows suele bloquearlo en equipos institucionales. Llamar
> al intérprete por su ruta evita ese problema por completo. Es más largo de
> escribir pero no falla nunca.
>
> Si prefiere activar el entorno y su equipo lo permite:
> `.\.venv\Scripts\Activate.ps1`. A partir de ahí puede escribir `python` y
> `pip` a secas.

### macOS y Linux

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

### Qué se instala

Quince dependencias declaradas, que con las suyas propias suman 55
paquetes y 166 MB de descarga. Entre ellas Streamlit para la interfaz,
scikit-learn para la recuperación de fragmentos, y las bibliotecas de
lectura de Word, ODF, planillas y PDF.

**No se instala PyTorch**, que pesa más de 2 GB. Es una capacidad opcional y
está en `requirements-opcionales.txt`, descrita en el
[apartado 9](#9-capacidades-opcionales-adicionales).

---

## 5. Verificar la instalación

Este paso no es opcional. Comprueba cada componente por separado y nombra
con precisión lo que falte.

```powershell
.\.venv\Scripts\python.exe scripts\verificar_entorno.py
```

En macOS y Linux:

```bash
./.venv/bin/python scripts/verificar_entorno.py
```

El informe recorre ocho secciones. Debe terminar con:

```
El sistema es operativo.
```

### Cómo leer el resultado

| Marca | Significado |
|---|---|
| `[ OK ]` | El componente funciona |
| `[ ADV ]` | Falta una capacidad opcional. El sistema opera igual |
| `[ ERR ]` | Falta algo necesario. Resuélvalo antes de continuar |

Las advertencias sobre `sentence_transformers` y sobre el reconocimiento
óptico son esperables y no impiden nada.

Para una verificación más exhaustiva, que incluye una consulta real a
ClinicalTrials.gov:

```powershell
.\.venv\Scripts\python.exe scripts\verificar_entorno.py --completo
```

### Comprobación adicional: la suite de pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Deben pasar las 319 pruebas en unos veinte segundos. Es la forma más
contundente de confirmar que la instalación quedó íntegra.

---

## 6. Ejecutar el sistema

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\Inicio.py
```

En macOS y Linux:

```bash
./.venv/bin/python -m streamlit run app/Inicio.py
```

El navegador se abre solo en <http://localhost:8501>. Si no lo hace, abra
esa dirección a mano.

**Deje la terminal abierta.** Mientras esa ventana esté abierta, el sistema
funciona. Si la cierra, se detiene. Para detenerlo a propósito, pulse
`Ctrl + C` en la terminal.

### Ingreso al sistema

La primera pantalla pide usuario y clave. El sistema se distribuye con tres
credenciales de puesta en marcha:

| Usuario | Clave | Perfil |
|---|---|---|
| `mrossi` | `tumorboard.2026` | Dra. Mariana Rossi, neuro-oncología clínica |
| `jlaguna` | `tumorboard.2026` | Dr. Julián Laguna, neurocirugía |
| `cvera` | `tumorboard.2026` | Dra. Carolina Vera, anatomía patológica |

Estas credenciales están publicadas en el repositorio y en la propia
pantalla de ingreso. Por esa razón **no constituyen un secreto** y deben
sustituirse en cualquier despliegue real. Las claves se almacenan derivadas
con PBKDF2 y nunca en texto plano.

---

## 7. Cargar un caso

El sistema no incluye un selector de casos de ejemplo: la carga es siempre
manual, como lo será en uso real.

En `data/casos_demo/` hay ocho casos sintéticos, distribuidos a propósito en
formatos distintos para ejercitar todos los lectores. El archivo
`data/casos_demo/LEEME.md` detalla qué contiene cada uno.

1. Vaya a **Carga de caso**
2. Escriba un identificador anonimizado, por ejemplo `CASO-001`
3. Adjunte cada documento en el casillero de su tipo. Para CASO-001:
   - Historia clínica → `historia_clinica.docx`
   - Anatomía patológica → `anatomia_patologica.pdf`
   - Genómica → `genomica.xlsx`
   - Imágenes → `imagenes.txt`
4. Pulse **Procesar caso**

### Formatos admitidos

Texto plano, Markdown, CSV, JSON, HTML, RTF, Word (`.docx`), ODF (`.odt`),
planillas (`.xlsx`), PDF e imágenes (`.png`, `.jpg`, `.tiff`, `.bmp`,
`.webp`).

Los documentos de Word anteriores a 2007 (`.doc`) deben convertirse
previamente a `.docx` o a PDF.

---

## 8. Modelo de lenguaje local, opcional

**El sistema funciona sin esto.** Sin modelo de lenguaje genera los
resúmenes mediante reglas deterministas, que producen un texto menos fluido
pero reproducible y auditable.

Ollama ejecuta el modelo en el propio equipo. No requiere clave de API ni
medio de pago, y la documentación clínica no abandona la máquina, lo que
resuelve por construcción la objeción de confidencialidad que pesa sobre
cualquier servicio remoto.

### Instalación

1. Descargue el instalador desde <https://ollama.com/download>
2. Ejecútelo. En Windows se instala para el usuario actual y queda
   corriendo como un ícono en la bandeja del sistema, junto al reloj.
3. **Cierre la terminal y abra una nueva.** Windows lee las rutas de
   programas al abrir la terminal, de modo que una ventana abierta antes de
   la instalación no reconocerá el comando.
4. Compruebe que responde:

```powershell
ollama --version
```

5. Descargue un modelo. Es una sola vez:

```powershell
ollama pull llama3.2:3b
```

### Configuración

Copie el archivo de ejemplo y edítelo:

```powershell
copy .env.example .env
```

En macOS y Linux: `cp .env.example .env`

Abra `.env` con cualquier editor de texto y deje estas dos líneas así:

```
PROVEEDOR_LLM=ollama
CLAVE_API_LLM=
```

Sin comillas, sin signos de menor y mayor, y sin espacios alrededor del
signo igual. La clave queda vacía porque la ejecución local no requiere
credencial.

### Verificación

```powershell
.\.venv\Scripts\python.exe scripts\verificar_entorno.py --modelos
```

Debe responder que el modelo `llama3.2:3b` contesta correctamente.

### Elección del modelo según la memoria del equipo

| Modelo | Descarga | Memoria recomendada |
|---|---|---|
| `llama3.2:3b` | 2,0 GB | 8 GB |
| `qwen2.5:7b` | 4,7 GB | 16 GB |
| `llama3.1:8b` | 4,7 GB | 16 GB |

Conviene empezar por el más liviano. Un modelo mayor mejora la redacción,
no la exactitud: los datos estructurados los extraen las reglas
deterministas y no el modelo.

Para cambiar de modelo, descárguelo con `ollama pull` y consigne su nombre
en `MODELO_LLM` dentro de `.env`.

### Nota sobre la primera consulta

La primera vez que se procesa un caso, el modelo se carga de disco a
memoria. Puede demorar entre uno y dos minutos. Las consultas siguientes
son sensiblemente más rápidas.

---

## 9. Capacidades opcionales adicionales

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-opcionales.txt
```

Antes de ejecutarlo, tenga presente el volumen: **más de 2,5 GB**.

### Recuperación semántica

`sentence-transformers` habilita la búsqueda por significado en lugar de por
coincidencia de términos. Instala PyTorch, y en la primera ejecución
descarga un modelo de unos 470 MB.

Sin esta dependencia el sistema emplea TF-IDF y lo declara en pantalla.

### Reconocimiento óptico de caracteres

Habilita la lectura de PDF escaneados e imágenes. Además de los paquetes de
Python requiere instalar el programa Tesseract, que no se distribuye por
`pip`:

- Windows: <https://github.com/UB-Mannheim/tesseract/wiki>
- macOS: `brew install tesseract tesseract-lang`
- Debian y Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils`

Sin él, las imágenes y los PDF escaneados se conservan adjuntos y el sistema
**declara de manera expresa que no aportan texto al análisis**. No los omite
en silencio.

---

## 10. Instalación sin conexión

Procedimiento para instalar en una máquina con red lenta, restringida o sin
conexión. Se prepara con antelación en una máquina que sí tenga internet.

Exige que ambas máquinas tengan el **mismo sistema operativo y la misma
versión de Python**, porque los paquetes vienen compilados para una
plataforma concreta.

### En la máquina preparada, con internet

```powershell
cd asistente-tumor-board
py -3.13 -m pip download -r requirements.txt -d paquetes
```

Se descargan 55 archivos que ocupan unos 166 MB. Cualquier pendrive sirve.

Copie a un pendrive:

- La carpeta completa del proyecto
- La carpeta `paquetes` recién creada
- El instalador de Python, descargado desde python.org

Si va a usar el modelo de lenguaje, agregue también:

- El instalador de Ollama
- La carpeta de modelos ya descargados, que en Windows está en
  `%USERPROFILE%\.ollama` y en macOS y Linux en `~/.ollama`

### En la máquina de destino

1. Instale Python desde el instalador del pendrive, marcando
   «Add python.exe to PATH»
2. Copie la carpeta del proyecto al disco, por ejemplo a `Documentos`
3. Abra una terminal dentro de esa carpeta y ejecute:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links paquetes -r requirements.txt
```

La opción `--no-index` impide que `pip` consulte internet, y
`--find-links` le indica que use los archivos del pendrive.

4. Verifique con `scripts\verificar_entorno.py`

Para el modelo de lenguaje, instale Ollama y copie la carpeta `.ollama`
completa a la carpeta personal del usuario en la máquina de destino. Así
evita volver a descargar los 2 GB del modelo.

---

## 11. Solución de problemas

Los errores están ordenados por frecuencia. Cada uno incluye su causa, no
solo la solución, de modo que sea posible reconocerlo si reaparece de otra
forma.

### `streamlit no se reconoce como un comando`

### `ollama no se reconoce como un comando`

**Causa.** Windows lee las rutas de programas cuando se abre la terminal. Si
instaló el programa con la terminal ya abierta, esa ventana no se enteró.

**Solución.** Cierre la terminal y abra una nueva. Si el problema persiste,
el programa no quedó instalado.

En el caso de Streamlit hay una segunda causa, más frecuente: está
invocándolo a secas en lugar de usar el intérprete del entorno virtual.
Escriba siempre `.\.venv\Scripts\python.exe -m streamlit`.

### `ModuleNotFoundError: No module named 'numpy'` o similar

**Causa.** Está ejecutando el Python del sistema y no el del entorno
virtual. Son dos intérpretes distintos, y las dependencias se instalaron en
uno solo.

**Solución.** Anteponga siempre `.\.venv\Scripts\python.exe` en lugar de
escribir `python`. Para comprobar cuál está usando:

```powershell
.\.venv\Scripts\python.exe --version
py --version
```

### El entorno virtual no se activa, error de directiva de ejecución

**Causa.** PowerShell bloquea por defecto la ejecución de scripts.

**Solución.** No active el entorno. Invoque el intérprete por su ruta, como
indica esta guía. Si prefiere activarlo, habilítelo solo para esa ventana:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Error al compilar un paquete, «building wheel for ... failed»

**Causa.** La versión de Python es demasiado nueva y el paquete todavía no
publica binarios precompilados para ella, de modo que `pip` intenta
compilarlo y la máquina no tiene compilador de C.

**Solución.** Instale Python 3.13 y recree el entorno virtual:

```powershell
rmdir /s /q .venv
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para ver qué versiones de Python tiene instaladas: `py -0`

### `not a git repository`

**Causa.** Descargó el proyecto como ZIP en lugar de clonarlo, de modo que
no hay historial de versiones.

**Solución.** Para actualizar, descargue el ZIP nuevamente. Para poder usar
`git pull` en el futuro, clone el repositorio con Git.

### `File does not exist: app.py`

**Causa.** El punto de entrada no es `app.py`.

**Solución.** El comando correcto es:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\Inicio.py
```

### `El servicio local de Ollama no responde en http://127.0.0.1:11434`

**Causa.** Ollama no está en ejecución.

**Solución.** Ábralo desde el menú de inicio. Queda como ícono en la bandeja
del sistema. Si no lo encuentra, ejecute `ollama serve` en una terminal
aparte y **deje esa ventana abierta**.

Para comprobar si está corriendo: `ollama list`. Si responde con una lista,
el servicio está activo.

### `Error: listen tcp 127.0.0.1:11434: bind`

**Causa.** Ollama ya está corriendo. No hace falta levantarlo.

**Solución.** Ninguna. Es el comportamiento esperado al intentar iniciar un
segundo servicio sobre el mismo puerto.

### `El modelo 'llama3.2:3b' no se encuentra descargado en este equipo`

**Causa.** Falta descargar el modelo, o la descarga se interrumpió.

**Solución.** `ollama pull llama3.2:3b`. Para ver los modelos disponibles en
la máquina: `ollama list`.

### `El modelo local no respondió dentro de los 300 segundos previstos`

**Causa.** La primera consulta carga el modelo en memoria y es
sensiblemente más lenta. En un equipo con poca memoria puede exceder el
límite.

**Solución.** Reintente. Si la demora persiste, use un modelo más pequeño:

```powershell
ollama pull gemma2:2b
```

Y consigne `MODELO_LLM=gemma2:2b` en el archivo `.env`.

### El puerto 8501 está ocupado

**Causa.** Hay otra instancia de Streamlit corriendo.

**Solución.** Use otro puerto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\Inicio.py --server.port 8502
```

### La configuración del archivo `.env` no surte efecto

**Causa.** Falta el paquete `python-dotenv`, de modo que el archivo no se
lee. La verificación del entorno lo informa como advertencia.

**Solución.** `.\.venv\Scripts\python.exe -m pip install python-dotenv`

### El antivirus bloquea la instalación

**Causa.** Algunos antivirus corporativos inspeccionan los paquetes que
descarga `pip` y abortan la conexión.

**Solución.** Use la instalación sin conexión del
[apartado 10](#10-instalación-sin-conexión), que no requiere que la máquina
de destino descargue nada.

---

## 12. Lista de comprobación previa a una demostración

### Con una semana de antelación

- [ ] Instalar y verificar en la máquina que se va a usar
- [ ] Ejecutar la suite de pruebas: deben pasar las 319
- [ ] Procesar al menos dos casos de principio a fin
- [ ] Preparar el pendrive con el paquete sin conexión del apartado 10
- [ ] Confirmar si el equipo del lugar admite conectar una notebook propia

### El día anterior

- [ ] Volver a ejecutar `verificar_entorno.py --completo`
- [ ] Procesar un caso completo y dejarlo cargado en el sistema
- [ ] Si va a usar Ollama, procesar un caso para que el modelo quede
      cargado en memoria
- [ ] Anotar las credenciales de ingreso

### Momentos antes

- [ ] Abrir la terminal y dejar el sistema corriendo
- [ ] Ingresar con un usuario y dejar la sesión iniciada
- [ ] Tener el caso ya procesado en pantalla
- [ ] Verificar que el navegador muestre la aplicación en el proyector

### Si algo falla durante la demostración

El sistema está diseñado para degradarse de manera controlada y nunca en
silencio.

- Sin conexión a internet, la consulta de estudios clínicos usa una copia
  local y lo declara en pantalla
- Sin modelo de lenguaje, el resumen se genera por reglas deterministas y lo
  declara en pantalla
- Sin modelo de embeddings, la recuperación emplea TF-IDF y lo declara en
  pantalla

Ninguna de las tres situaciones interrumpe la demostración. Si ocurre
alguna, conviene señalarla: es la degradación controlada funcionando, y
constituye una de las decisiones de diseño del proyecto.

---

## Soporte

El repositorio está en
<https://github.com/GaboRTX/asistente-tumor-board>.

El funcionamiento del sistema y el fundamento de cada decisión de diseño
están documentados en [`MANUAL.md`](MANUAL.md).
