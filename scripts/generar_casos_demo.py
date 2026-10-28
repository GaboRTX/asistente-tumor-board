# -*- coding: utf-8 -*-
"""
Genera los casos demo sinteticos del sistema.

Los casos fueron construidos a partir de patrones de presentacion descriptos
en la literatura publicada sobre gliomas del adulto (clasificacion OMS 2021).
No corresponden a pacientes reales ni contienen datos identificatorios.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import DIR_CASOS_DEMO as BASE

CASOS = {}

# ---------------------------------------------------------------------------
# CASO-001 - Astrocitoma IDH mutado grado 3
# ---------------------------------------------------------------------------
CASOS['CASO-001'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-001
Documento sintetico de demostracion. No corresponde a un paciente real.

Paciente de 41 años, sexo masculino, diestro.

MOTIVO DE CONSULTA: Cefalea holocraneana de tres meses de evolucion, progresiva,
de predominio matinal, asociada en el ultimo mes a dos episodios de crisis
convulsivas tonico-clonicas generalizadas.

ENFERMEDAD ACTUAL: Consulta por guardia tras el segundo episodio convulsivo.
Al examen neurologico se constata leve hemiparesia braquial derecha (fuerza 4/5)
y dificultad en la denominacion. No presenta alteracion del sensorio.
Escala de Karnofsky al ingreso: 80.

ANTECEDENTES PERSONALES: Hipertension arterial en tratamiento con enalapril.
Tabaquista de 15 paquetes/año, cesado hace 4 años. Niega alergias medicamentosas.
Sin antecedentes oncologicos previos.

ANTECEDENTES FAMILIARES: Madre con carcinoma de mama a los 62 años.
Sin antecedentes de tumores del sistema nervioso central.

EVOLUCION: Se realiza exeresis macroscopicamente completa de la lesion mediante
craneotomia frontal izquierda guiada por neuronavegacion. Buena evolucion
posoperatoria, sin nuevo deficit focal. Karnofsky posoperatorio: 90.
Posteriormente inicia radioterapia conformada 59.4 Gy en 33 fracciones,
seguida de temozolomida adyuvante segun esquema estandar, completando 6 ciclos.
Actualmente en seguimiento, asintomatico.
""",
'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-001
Documento sintetico de demostracion.

MATERIAL REMITIDO: Pieza de reseccion tumoral, region frontal izquierda.

DESCRIPCION MACROSCOPICA: Fragmentos de tejido blanquecino-grisaceo,
de consistencia blanda, que en conjunto miden 3.8 x 2.9 x 1.6 cm.

DESCRIPCION MICROSCOPICA: Proliferacion glial difusamente infiltrante,
constituida por celulas de nucleos irregulares e hipercromaticos, con moderado
pleomorfismo nuclear. Se identifican figuras de mitosis, con recuento de
5 mitosis por 10 campos de gran aumento. No se observa proliferacion
microvascular ni necrosis en el material examinado.

INMUNOHISTOQUIMICA:
- GFAP: positivo difuso.
- IDH1 R132H: positivo nuclear y citoplasmatico.
- ATRX: perdida de expresion nuclear en celulas tumorales.
- p53: sobreexpresion nuclear en aproximadamente 60% de las celulas.
- Ki-67: indice proliferativo del 12%.

DIAGNOSTICO: Astrocitoma IDH mutado, grado 3 de la OMS (Clasificacion OMS 2021
de Tumores del Sistema Nervioso Central).
""",
'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-001
Documento sintetico de demostracion.

METODO: Secuenciacion de nueva generacion (NGS), panel dirigido de tumores
del sistema nervioso central. Analisis de metilacion por pirosecuenciacion.

RESULTADOS:
- IDH1: mutacion p.R132H detectada (variante patogenica).
- IDH2: no se detectan variantes.
- Codeleccion 1p/19q: ausente. Se conserva material en ambos brazos cromosomicos.
- Promotor de MGMT: metilado. Nivel de metilacion 42%.
- ATRX: mutacion con perdida de funcion.
- TP53: mutacion p.R273C detectada.
- Promotor de TERT: no se detecta mutacion.
- EGFR: sin amplificacion.
- CDKN2A/B: sin delecion homocigota.

INTERPRETACION: Perfil molecular compatible con astrocitoma IDH mutado.
La ausencia de delecion homocigota de CDKN2A/B es consistente con grado 3.
""",
'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-001
Documento sintetico de demostracion.

ESTUDIO: Resonancia magnetica de encefalo con y sin contraste endovenoso.

HALLAZGOS: Se identifica lesion expansiva intraaxial localizada en region
frontal izquierda, con extension al giro frontal inferior, que mide
4.2 x 3.1 x 2.8 cm en sus diametros maximos.

La lesion presenta senal hiperintensa en secuencias T2 y FLAIR, e hipointensa
en T1. Tras la administracion de contraste se observa realce heterogeneo,
de distribucion parcheada, en el sector posteromedial de la lesion.

Se acompaña de edema vasogenico perilesional que se extiende hacia la sustancia
blanca subcortical adyacente, con efecto de masa sobre el asta frontal del
ventriculo lateral izquierdo y desviacion de la linea media de 4 mm hacia
la derecha.

No se observan signos de sangrado intratumoral ni de diseminacion leptomeningea.

CONCLUSION: Lesion expansiva intraaxial frontal izquierda con realce
heterogeneo, compatible con glioma de alto grado. Se sugiere correlacion
histopatologica.
"""
}

# ---------------------------------------------------------------------------
# CASO-002 - Glioblastoma IDH wild-type
# ---------------------------------------------------------------------------
CASOS['CASO-002'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-002
Documento sintetico de demostracion. No corresponde a un paciente real.

Paciente de 67 años, sexo femenino.

MOTIVO DE CONSULTA: Cuadro de instalacion subaguda, de aproximadamente cinco
semanas de evolucion, caracterizado por deterioro cognitivo progresivo,
desorientacion temporoespacial y episodios de confusion.

ENFERMEDAD ACTUAL: La familia refiere cambios en el comportamiento y dificultad
para realizar tareas habituales. En la ultima semana se agrega hemiparesia
faciobraquial izquierda de instalacion progresiva. Escala de Karnofsky: 60.

ANTECEDENTES PERSONALES: Diabetes mellitus tipo 2 en tratamiento con metformina.
Dislipemia. Hipotiroidismo en tratamiento sustitutivo con levotiroxina.
Sin antecedentes oncologicos.

ANTECEDENTES FAMILIARES: Sin datos relevantes.

EVOLUCION: Se realiza reseccion subtotal de la lesion por craneotomia
parietal derecha. Posoperatorio con mejoria parcial del cuadro cognitivo.
Inicia tratamiento con radioterapia 60 Gy en 30 fracciones con temozolomida
concomitante segun protocolo. Completa la fase concomitante con buena tolerancia.
Se encuentra cursando el tercer ciclo de temozolomida adyuvante.
""",
'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-002
Documento sintetico de demostracion.

MATERIAL REMITIDO: Tejido de reseccion tumoral, region parietal derecha.

DESCRIPCION MICROSCOPICA: Neoplasia glial de alta celularidad, difusamente
infiltrante, con marcado pleomorfismo nuclear y elevada actividad mitotica
(14 mitosis por 10 campos de gran aumento).

Se observan extensas areas de necrosis con patron de seudoempalizada
perinecrotica, asi como proliferacion microvascular con formacion de
estructuras glomeruloides.

INMUNOHISTOQUIMICA:
- GFAP: positivo.
- IDH1 R132H: negativo.
- ATRX: expresion nuclear conservada.
- Ki-67: indice proliferativo del 35%.

DIAGNOSTICO: Glioblastoma, IDH wild-type, grado 4 de la OMS
(Clasificacion OMS 2021 de Tumores del Sistema Nervioso Central).
""",
'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-002
Documento sintetico de demostracion.

METODO: Secuenciacion de nueva generacion, panel de tumores del sistema
nervioso central. Metilacion de MGMT por pirosecuenciacion.

RESULTADOS:
- IDH1 e IDH2: no se detectan mutaciones. Perfil IDH wild-type.
- Promotor de TERT: mutacion C228T detectada.
- EGFR: amplificacion presente. Se identifica ademas la variante EGFRvIII.
- Codeleccion 1p/19q: no se evidencia.
- Promotor de MGMT: no metilado.
- CDKN2A/B: delecion homocigota presente.
- Ganancia del cromosoma 7 y perdida del cromosoma 10.

INTERPRETACION: Perfil molecular caracteristico de glioblastoma IDH wild-type.
El estado no metilado del promotor de MGMT se asocia a menor sensibilidad
a agentes alquilantes.
""",
'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-002
Documento sintetico de demostracion.

ESTUDIO: Resonancia magnetica de encefalo con contraste endovenoso.

HALLAZGOS: Lesion expansiva intraaxial en region parietal derecha, de
5.6 x 4.8 x 4.1 cm, con centro necrotico y realce anular grueso e irregular
tras la administracion de gadolinio.

Extenso edema vasogenico perilesional con importante efecto de masa,
colapso parcial del ventriculo lateral derecho y desviacion de la linea media
de 9 mm hacia la izquierda.

Se observa compromiso del cuerpo calloso con extension hacia el hemisferio
contralateral a traves del esplenio.

CONCLUSION: Lesion expansiva parietal derecha con realce anular y necrosis
central, con compromiso transcalloso, altamente sugestiva de glioma de alto
grado.
"""
}

# ---------------------------------------------------------------------------
# CASO-003 - Oligodendroglioma IDH mutado, 1p/19q codelecionado
# ---------------------------------------------------------------------------
CASOS['CASO-003'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-003
Documento sintetico de demostracion. No corresponde a un paciente real.

Paciente de 35 años, sexo femenino.

MOTIVO DE CONSULTA: Primera crisis convulsiva focal con generalizacion
secundaria, sin desencadenante identificable.

ENFERMEDAD ACTUAL: La paciente refiere en retrospectiva episodios de
sensacion de deja vu y olores desagradables durante los ultimos ocho meses,
no consultados previamente. Examen neurologico sin deficit focal.
Escala de Karnofsky: 100.

ANTECEDENTES PERSONALES: Sin antecedentes patologicos de relevancia.
No fumadora. Sin medicacion habitual.

ANTECEDENTES FAMILIARES: Sin antecedentes oncologicos conocidos.

EVOLUCION: Se realiza reseccion macroscopicamente completa mediante
craneotomia temporal izquierda con mapeo intraoperatorio del lenguaje.
Sin complicaciones posoperatorias. Se indica conducta expectante con
seguimiento imagenologico trimestral, dada la reseccion completa y el
perfil molecular favorable. Recibe tratamiento anticonvulsivante con
levetiracetam.
""",
'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-003
Documento sintetico de demostracion.

MATERIAL REMITIDO: Pieza de reseccion tumoral, lobulo temporal izquierdo.

DESCRIPCION MICROSCOPICA: Proliferacion glial de densidad celular moderada,
constituida por celulas de nucleos redondeados y regulares, con halo
perinuclear claro que confiere el aspecto clasico en huevo frito.

Se observa red capilar ramificada de disposicion delicada. Actividad mitotica
escasa, con 1 mitosis por 10 campos de gran aumento. No se identifica
proliferacion microvascular ni necrosis.

INMUNOHISTOQUIMICA:
- GFAP: positivo focal.
- IDH1 R132H: positivo.
- ATRX: expresion nuclear conservada.
- p53: sin sobreexpresion.
- Ki-67: indice proliferativo del 4%.

DIAGNOSTICO: Oligodendroglioma, IDH mutado y con codeleccion 1p/19q,
grado 2 de la OMS (Clasificacion OMS 2021).
""",
'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-003
Documento sintetico de demostracion.

METODO: Secuenciacion de nueva generacion e hibridacion in situ fluorescente
(FISH) para 1p/19q.

RESULTADOS:
- IDH1: mutacion p.R132H detectada.
- Codeleccion 1p/19q: presente por FISH. Perdida combinada completa de los
  brazos cromosomicos 1p y 19q.
- Promotor de TERT: mutacion C228T detectada.
- ATRX: sin mutacion.
- TP53: sin mutacion.
- Promotor de MGMT: metilado, nivel de metilacion 55%.
- CIC: mutacion detectada.

INTERPRETACION: Perfil molecular diagnostico de oligodendroglioma IDH mutado
con codeleccion 1p/19q, asociado a mejor pronostico y mayor sensibilidad al
tratamiento con quimioterapia.
""",
'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-003
Documento sintetico de demostracion.

ESTUDIO: Resonancia magnetica de encefalo con y sin contraste.

HALLAZGOS: Lesion intraaxial de localizacion cortico-subcortical en region
temporal izquierda, de 3.1 x 2.4 x 2.2 cm, de limites relativamente definidos.

Presenta senal hiperintensa en T2 y FLAIR, con areas de senal heterogenea
que podrian corresponder a calcificaciones, a confirmar con tomografia.

No se observa realce significativo tras la administracion de contraste.
Edema perilesional minimo. Sin efecto de masa significativo ni desviacion
de la linea media.

CONCLUSION: Lesion temporal izquierda sin realce, con caracteristicas
sugestivas de glioma de bajo grado.
"""
}

# ---------------------------------------------------------------------------
# CASO-004 - Caso incompleto (falta genomica) - prueba de robustez
# ---------------------------------------------------------------------------
CASOS['CASO-004'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-004
Documento sintetico de demostracion. No corresponde a un paciente real.

Paciente de 58 años, sexo masculino.

MOTIVO DE CONSULTA: Deficit motor de instalacion progresiva en hemicuerpo
derecho, de aproximadamente dos meses de evolucion.

ENFERMEDAD ACTUAL: Se constata hemiparesia derecha a predominio braquial
(fuerza 3/5) y disartria leve. Sin compromiso del sensorio.
Escala de Karnofsky: 70.

ANTECEDENTES PERSONALES: Hipertension arterial. Extabaquista.

EVOLUCION: Se realiza biopsia estereotaxica de la lesion dada su localizacion
en area elocuente. Pendiente definicion de conducta terapeutica en junta
multidisciplinaria.
""",
'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-004
Documento sintetico de demostracion.

MATERIAL REMITIDO: Cilindros de biopsia estereotaxica, region frontal derecha.

DESCRIPCION MICROSCOPICA: Escaso material constituido por tejido glial con
aumento de la celularidad y atipia nuclear moderada. Se identifican algunas
figuras mitoticas. El material resulta insuficiente para una evaluacion
completa de necrosis y proliferacion microvascular.

INMUNOHISTOQUIMICA:
- GFAP: positivo.
- IDH1 R132H: negativo.
- Ki-67: indice proliferativo aproximado del 18%.

DIAGNOSTICO: Glioma difuso de alto grado. Se sugiere ampliar estudios
moleculares para tipificacion definitiva segun clasificacion OMS 2021.

NOTA: El estudio de metilacion del promotor de MGMT no resulta valorable por
material insuficiente.
""",
'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-004
Documento sintetico de demostracion.

ESTUDIO: Resonancia magnetica de encefalo con contraste.

HALLAZGOS: Lesion expansiva intraaxial frontal derecha, de 4.5 x 3.3 x 3.0 cm,
con realce heterogeneo tras el contraste y areas centrales de menor senal
que podrian corresponder a necrosis.

Edema vasogenico perilesional moderado con efecto de masa sobre el ventriculo
lateral derecho. Desviacion de la linea media de 5 mm.

CONCLUSION: Lesion expansiva frontal derecha compatible con glioma de alto
grado.
"""
}

# ---------------------------------------------------------------------------
# CASO-005 - Caso con redaccion desprolija - prueba de robustez
# ---------------------------------------------------------------------------
CASOS['CASO-005'] = {
'historia_clinica': """CASO-005 - HC
Documento sintetico de demostracion.

Masculino 49a. Consulta x cefalea + vomitos de 6 sem. Examen: papiledema
bilateral, sin deficit motor. KPS 80.
Ant: sin antecedentes de jerarquia. No fuma. No alergias.
Se opera: reseccion parcial (craneotomia occipital izq). Post-op sin cambios.
Luego RT 60 Gy/30 fx + TMZ concomitante. Actualmente en TMZ adyuvante, 2do ciclo.
""",
'anatomia_patologica': """CASO-005 - ANATOMIA PATOLOGICA
Documento sintetico de demostracion.

Material: reseccion occipital izquierda.
Micro: proliferacion glial infiltrante, atipia marcada, mitosis frecuentes
(11/10 CGA), necrosis presente, proliferacion microvascular presente.
IHQ: GFAP +, IDH1 R132H negativo, ATRX conservado, Ki67 30%.
Dx: Glioblastoma IDH wild-type grado 4 OMS 2021.
""",
'genomica': """CASO-005 - MOLECULAR
Documento sintetico de demostracion.

IDH1/2: wild-type.
MGMT: metilacion del promotor: ausente.
1p/19q: conservados.
TERT promotor: mutado (C228T).
EGFR: sin amplificacion.
TP53: sin mutacion.
""",
'imagenes': """CASO-005 - RM
Documento sintetico de demostracion.

RM encefalo c/ contraste. Lesion occipital izq 3.9 x 3.2 x 2.7 cm, realce
anular irregular, necrosis central. Edema perilesional importante.
Efecto de masa +. LM desviada 6 mm a derecha.
Conclusion: glioma de alto grado.
"""
}

for caso, docs in CASOS.items():
    d = BASE / caso
    d.mkdir(parents=True, exist_ok=True)
    for tipo, contenido in docs.items():
        (d / f"{tipo}.txt").write_text(contenido, encoding='utf-8')
    print(f"{caso}: {len(docs)} documentos")

print("\nCasos generados en", BASE)
