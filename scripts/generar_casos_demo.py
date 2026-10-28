# -*- coding: utf-8 -*-
"""
Generacion de los casos de demostracion del sistema.

Los casos son sinteticos. No corresponden a pacientes reales ni reproducen
textualmente ningun informe publicado. Su estructura y terminologia siguen
las recomendaciones de las guias internacionales de neuro-oncologia:

  - EANO, guias de diagnostico y tratamiento de gliomas difusos del adulto
    (Weller et al., Nat Rev Clin Oncol 2021): marcadores moleculares
    requeridos, esquemas terapeuticos con dosis y pautas de seguimiento.
  - College of American Pathologists junto con AANP, AMP y SNO
    (Brat et al., Arch Pathol Lab Med 2022): biomarcadores a determinar en
    gliomas difusos y tecnicas aceptadas para cada uno.
  - ICCR, conjunto de datos de diagnostico integrado de tumores del sistema
    nervioso central: informe anatomopatologico en capas.
  - RANO: criterios de medicion bidimensional y de evaluacion de respuesta.

Los ocho casos cubren las entidades diagnosticas mas frecuentes en el
adulto y tres situaciones que el sistema debe resolver correctamente:
documentacion incompleta, redaccion abreviada y evaluacion de respuesta en
el seguimiento.

Uso:
    python scripts/generar_casos_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import DIR_CASOS_DEMO as BASE

CASOS = {}

CASOS['CASO-001'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-001
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Varon de 41 anios, diestro. Docente de nivel medio.

MOTIVO DE CONSULTA
Cefalea holocraneana de tres meses de evolucion y dos episodios de crisis
tonico-clonicas generalizadas en el ultimo mes.

ENFERMEDAD ACTUAL
Cefalea progresiva, de predominio matinal, que cede parcialmente con
analgesicos comunes. Consulta por guardia tras el segundo episodio
convulsivo, presenciado por familiares, de aproximadamente dos minutos de
duracion con periodo posictal de treinta minutos.

EXAMEN NEUROLOGICO AL INGRESO
Vigil, orientado en tiempo y espacio. Lenguaje con dificultad leve en la
denominacion, sin parafasias. Pares craneales sin particularidades. Fuerza
4/5 en miembro superior derecho, 5/5 en el resto. Sensibilidad conservada.
Sin signos meningeos. Fondo de ojo sin edema de papila.
Escala funcional de Karnofsky: 80.
Escala NANO: marcha 0, fuerza 1, ataxia 0, sensibilidad 0, campo visual 0,
lenguaje 1, nivel de conciencia 0, comportamiento 0.

ANTECEDENTES PERSONALES
Hipertension arterial en tratamiento con enalapril 10 mg por dia.
Extabaquista, 15 paquetes/anio, cesado hace 4 anios.
Sin alergias medicamentosas conocidas. Sin antecedentes oncologicos.

ANTECEDENTES FAMILIARES
Madre con carcinoma de mama a los 62 anios. Sin antecedentes de tumores
del sistema nervioso central.

EVOLUCION Y TRATAMIENTO
Se realiza exeresis macroscopicamente completa mediante craneotomia frontal
izquierda guiada por neuronavegacion, con monitoreo neurofisiologico
intraoperatorio. Sin complicaciones. Resonancia de control dentro de las 48
horas posoperatorias sin lesion residual medible ni restriccion en difusion.
Karnofsky posoperatorio: 90.

Inicia radioterapia conformada a las 4 semanas de la cirugia, 59,4 Gy en 33
fracciones de 1,8 Gy sobre volumen blanco con margen clinico de 1,5 cm.
Continua con temozolomida adyuvante 150 a 200 mg/m2, cinco dias cada 28,
completando 12 ciclos segun esquema CATNON. Buena tolerancia hematologica,
con trombocitopenia grado 1 transitoria en el ciclo 7.

Tratamiento anticonvulsivante con levetiracetam 1000 mg cada 12 horas, sin
nuevas crisis desde el inicio.

SITUACION ACTUAL
Asintomatico. Karnofsky 90. En seguimiento con resonancia cada 3 meses.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-001
Documento sintetico de demostracion.

MATERIAL REMITIDO
Pieza de reseccion tumoral, region frontal izquierda.

DESCRIPCION MACROSCOPICA
Fragmentos de tejido blanquecino grisaceo, de consistencia blanda, que en
conjunto miden 3,8 x 2,9 x 1,6 cm.

DESCRIPCION MICROSCOPICA
Proliferacion glial difusamente infiltrante del parenquima cerebral,
constituida por celulas de nucleos irregulares e hipercromaticos con
moderado pleomorfismo nuclear. Se identifican figuras de mitosis, con
recuento de 5 mitosis por 10 campos de gran aumento.
No se observa proliferacion microvascular ni necrosis en el material
examinado.

INMUNOHISTOQUIMICA
GFAP: positivo difuso en celulas tumorales.
IDH1 R132H: positivo, con marcacion nuclear y citoplasmatica.
ATRX: perdida de expresion nuclear en celulas tumorales, con control
interno endotelial conservado.
p53: sobreexpresion nuclear en aproximadamente 60% de las celulas.
Ki-67: indice proliferativo del 12%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Astrocitoma IDH mutante, grado 3 de la OMS.
Apariencia histologica: glioma difuso con actividad mitotica, sin
proliferacion microvascular ni necrosis.
Grado OMS: 3.
Parametros moleculares: mutacion IDH1 R132H; mutacion de ATRX con perdida
de expresion; mutacion de TP53; 1p/19q sin codelecion; CDKN2A/B sin
delecion homocigota.

Clasificacion de la OMS de los Tumores del Sistema Nervioso Central,
quinta edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-001
Documento sintetico de demostracion.

MUESTRA
Tejido tumoral incluido en parafina. Porcentaje de celularidad tumoral
estimado: 70%.

METODOLOGIA
Secuenciacion de nueva generacion, panel dirigido de tumores del sistema
nervioso central (523 genes). Analisis de metilacion del promotor de MGMT
por pirosecuenciacion. Estudio de 1p/19q por hibridacion in situ
fluorescente.

RESULTADOS
IDH1: mutacion p.R132H (c.395G>A) detectada. Fraccion alelica 38%.
IDH2: no se detectan variantes en el codon 172.
Codelecion 1p/19q: ausente. Se conserva material genetico en ambos brazos
cromosomicos.
Promotor de MGMT: metilado. Nivel de metilacion 42%.
ATRX: mutacion p.R1426* con perdida de funcion.
TP53: mutacion p.R273C detectada. Fraccion alelica 41%.
Promotor de TERT: no se detecta mutacion en las posiciones C228T ni C250T.
EGFR: sin amplificacion.
CDKN2A/B: sin delecion homocigota.
H3F3A: sin mutacion en K27 ni en G34.

INTERPRETACION
Perfil molecular compatible con astrocitoma IDH mutante. La ausencia de
delecion homocigota de CDKN2A/B es consistente con el grado 3 asignado por
histologia. El estado metilado del promotor de MGMT se asocia a mayor
sensibilidad a agentes alquilantes.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-001
Documento sintetico de demostracion.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio. Protocolo de
neuro-oncologia: T1 volumetrico 3D pre y poscontraste, T2, FLAIR,
difusion y perfusion.

HALLAZGOS
Lesion expansiva intraaxial en region frontal izquierda, con extension al
giro frontal inferior, de 4,2 x 3,1 x 2,8 cm en sus diametros maximos.
Producto de diametros perpendiculares en el corte axial de mayor
representacion: 42 x 31 mm.

Senal hiperintensa en T2 y FLAIR, hipointensa en T1. Tras la administracion
de gadolinio se observa realce heterogeneo, de distribucion parcheada, en
el sector posteromedial de la lesion.

Alteracion de senal no realzante en T2/FLAIR que se extiende hacia la
sustancia blanca subcortical adyacente, compatible con componente
infiltrativo y edema vasogenico.

Efecto de masa sobre el asta frontal del ventriculo lateral izquierdo, con
desviacion de la linea media de 4 mm hacia la derecha.

En secuencias de difusion no se observan areas de restriccion significativa.
En perfusion, volumen sanguineo cerebral relativo aumentado en el sector
con realce.

No se observan signos de sangrado intratumoral ni diseminacion
leptomeningea.

CONCLUSION
Lesion expansiva intraaxial frontal izquierda con realce heterogeneo y
componente no realzante periferico, compatible con glioma difuso de alto
grado. Enfermedad medible segun criterios RANO. Se sugiere correlacion
histopatologica.
"""
}

# ---------------------------------------------------------------------------
# CASO-002  Glioblastoma IDH wild-type
# ---------------------------------------------------------------------------
CASOS['CASO-002'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-002
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Mujer de 67 anios, jubilada.

MOTIVO DE CONSULTA
Deterioro cognitivo progresivo de cinco semanas de evolucion con
desorientacion y episodios de confusion.

ENFERMEDAD ACTUAL
La familia refiere cambios en el comportamiento, dificultad para realizar
tareas habituales y desorientacion temporoespacial de instalacion subaguda.
En la ultima semana se agrega debilidad faciobraquial izquierda de
instalacion progresiva.

EXAMEN NEUROLOGICO AL INGRESO
Vigil, desorientada en tiempo. Bradipsiquia. Hemiparesia faciobraquial
izquierda con fuerza 3/5 en miembro superior y 4/5 en miembro inferior.
Hemihipoestesia izquierda. Sin compromiso de pares craneales.
Escala funcional de Karnofsky: 60.
Evaluacion cognitiva breve MoCA: 19 sobre 30.

ANTECEDENTES PERSONALES
Diabetes mellitus tipo 2 en tratamiento con metformina 850 mg cada 12 horas.
Dislipemia en tratamiento con atorvastatina.
Hipotiroidismo en tratamiento sustitutivo con levotiroxina 75 mcg por dia.
Sin antecedentes oncologicos.

ANTECEDENTES FAMILIARES
Sin datos de relevancia.

EVOLUCION Y TRATAMIENTO
Se realiza reseccion subtotal mediante craneotomia parietal derecha, con
remanente en profundidad por proximidad a la via corticoespinal.
Resonancia posoperatoria dentro de las 48 horas con lesion residual
realzante de 18 x 14 mm.
Mejoria parcial del cuadro cognitivo en el posoperatorio. Karnofsky 70.

Inicia radioterapia 60 Gy en 30 fracciones de 2 Gy con temozolomida
concomitante 75 mg/m2 diarios durante todo el curso de la radioterapia.
Completa la fase concomitante con buena tolerancia.
Cursa actualmente el tercer ciclo de temozolomida adyuvante 150 mg/m2,
cinco dias cada 28.

Profilaxis con trimetoprima sulfametoxazol durante la fase concomitante.
Dexametasona 4 mg por dia, en descenso progresivo.

SITUACION ACTUAL
Karnofsky 70. Hemiparesia izquierda estable. Sin nuevas crisis.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-002
Documento sintetico de demostracion.

MATERIAL REMITIDO
Tejido de reseccion tumoral, region parietal derecha.

DESCRIPCION MICROSCOPICA
Neoplasia glial de alta celularidad, difusamente infiltrante, con marcado
pleomorfismo nuclear y elevada actividad mitotica, con recuento de 14
mitosis por 10 campos de gran aumento.

Se observan extensas areas de necrosis con patron de seudoempalizada
perinecrotica. Proliferacion microvascular prominente con formacion de
estructuras glomeruloides.

INMUNOHISTOQUIMICA
GFAP: positivo en celulas tumorales.
IDH1 R132H: negativo.
ATRX: expresion nuclear conservada.
p53: sin sobreexpresion significativa.
Ki-67: indice proliferativo del 35%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Glioblastoma IDH wild-type, grado 4 de la OMS.
Apariencia histologica: glioma difuso de alto grado con necrosis en
seudoempalizada y proliferacion microvascular.
Grado OMS: 4.
Parametros moleculares: IDH1 e IDH2 sin mutacion; promotor de TERT mutado
C228T; amplificacion de EGFR con variante EGFRvIII; promotor de MGMT no
metilado; 1p/19q sin codelecion; delecion homocigota de CDKN2A/B presente.

Clasificacion de la OMS de los Tumores del Sistema Nervioso Central,
quinta edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-002
Documento sintetico de demostracion.

MUESTRA
Tejido tumoral incluido en parafina. Celularidad tumoral estimada: 80%.

METODOLOGIA
Secuenciacion de nueva generacion, panel de tumores del sistema nervioso
central. Metilacion del promotor de MGMT por pirosecuenciacion. Analisis
de numero de copias por array citogenomico.

RESULTADOS
IDH1 e IDH2: no se detectan mutaciones. Perfil IDH wild-type.
Promotor de TERT: mutacion C228T detectada. Fraccion alelica 44%.
EGFR: amplificacion presente, con numero de copias estimado en 22. Se
identifica ademas la variante de delecion EGFRvIII.
Codelecion 1p/19q: no se evidencia.
Promotor de MGMT: no metilado. Nivel de metilacion 4%, por debajo del
umbral de corte establecido en 9%.
CDKN2A/B: delecion homocigota presente.
Perfil de numero de copias: ganancia completa del cromosoma 7 y perdida
completa del cromosoma 10 (patron +7/-10).
TP53: sin mutacion.
ATRX: sin mutacion.
H3F3A: sin mutacion.

INTERPRETACION
Perfil molecular caracteristico de glioblastoma IDH wild-type, grado 4 de
la OMS. La combinacion de mutacion del promotor de TERT, amplificacion de
EGFR y patron +7/-10 satisface los criterios moleculares de glioblastoma
con independencia de la histologia.
El estado no metilado del promotor de MGMT se asocia a menor beneficio del
tratamiento con agentes alquilantes.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-002
Documento sintetico de demostracion.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio. Protocolo de
neuro-oncologia.

HALLAZGOS
Lesion expansiva intraaxial en region parietal derecha, de 5,6 x 4,8 x 4,1
cm. Producto de diametros perpendiculares en el corte axial de mayor
representacion: 56 x 48 mm.

Centro necrotico con realce anular grueso e irregular tras la
administracion de gadolinio, de espesor variable entre 8 y 14 mm.

Extensa alteracion de senal no realzante en T2/FLAIR perilesional, con
importante efecto de masa, colapso parcial del ventriculo lateral derecho y
desviacion de la linea media de 9 mm hacia la izquierda.

Compromiso del cuerpo calloso con extension hacia el hemisferio
contralateral a traves del esplenio.

En difusion se observa restriccion en los bordes solidos de la lesion.
En perfusion, marcado aumento del volumen sanguineo cerebral relativo en el
anillo de realce.

CONCLUSION
Lesion expansiva parietal derecha con realce anular, necrosis central y
compromiso transcalloso, altamente sugestiva de glioma difuso de alto
grado. Enfermedad medible segun criterios RANO.
"""
}

CASOS['CASO-003'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-003
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Mujer de 35 anios, contadora.

MOTIVO DE CONSULTA
Primera crisis convulsiva focal con generalizacion secundaria, sin
desencadenante identificable.

ENFERMEDAD ACTUAL
En retrospectiva, la paciente refiere episodios de sensacion de deja vu y
percepcion de olores desagradables durante los ultimos ocho meses, no
consultados previamente, compatibles con crisis focales con alteracion de
la conciencia.

EXAMEN NEUROLOGICO AL INGRESO
Vigil, orientada. Lenguaje conservado. Pares craneales sin particularidades.
Fuerza 5/5 global. Sensibilidad conservada. Sin deficit focal.
Escala funcional de Karnofsky: 100.
Escala NANO: sin alteraciones en ninguno de los dominios evaluados.
MoCA: 29 sobre 30.

ANTECEDENTES PERSONALES
Sin antecedentes patologicos de relevancia. No fumadora. Sin medicacion
habitual. Sin alergias conocidas.

ANTECEDENTES FAMILIARES
Sin antecedentes oncologicos conocidos.

EVOLUCION Y TRATAMIENTO
Se realiza reseccion macroscopicamente completa mediante craneotomia
temporal izquierda con mapeo intraoperatorio del lenguaje en paciente
despierta. Sin complicaciones posoperatorias ni nuevo deficit.
Resonancia de control a las 48 horas sin lesion residual.

Dada la reseccion completa, la edad menor de 40 anios, la ausencia de
deficit neurologico y el perfil molecular favorable, se adopta conducta
expectante con seguimiento imagenologico, conforme a las recomendaciones
para oligodendroglioma de grado 2 en pacientes de bajo riesgo.

Tratamiento anticonvulsivante con levetiracetam 500 mg cada 12 horas.
Sin nuevas crisis desde la cirugia.

SITUACION ACTUAL
Asintomatica. Karnofsky 100. Reintegrada a su actividad laboral.
Seguimiento con resonancia cada 3 meses durante el primer anio.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-003
Documento sintetico de demostracion.

MATERIAL REMITIDO
Pieza de reseccion tumoral, lobulo temporal izquierdo.

DESCRIPCION MACROSCOPICA
Fragmento de tejido de 3,2 x 2,5 x 2,0 cm, de consistencia blanda, con
areas de aspecto gelatinoso y focos calcificados al corte.

DESCRIPCION MICROSCOPICA
Proliferacion glial de densidad celular moderada, constituida por celulas
de nucleos redondeados y regulares con halo perinuclear claro, que confiere
el aspecto clasico descripto como en huevo frito.

Red capilar ramificada de disposicion delicada, en patron de alambre de
gallinero. Se identifican microcalcificaciones dispersas.
Actividad mitotica escasa, con 1 mitosis por 10 campos de gran aumento.
No se identifica proliferacion microvascular ni necrosis.

INMUNOHISTOQUIMICA
GFAP: positivo focal.
IDH1 R132H: positivo.
ATRX: expresion nuclear conservada.
p53: sin sobreexpresion.
Ki-67: indice proliferativo del 4%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Oligodendroglioma IDH mutante y 1p/19q
codelecionado, grado 2 de la OMS.
Apariencia histologica: glioma difuso con morfologia oligodendroglial y
microcalcificaciones.
Grado OMS: 2.
Parametros moleculares: mutacion IDH1 R132H; codelecion 1p/19q presente;
ATRX conservado; TP53 sin mutacion; promotor de TERT mutado C228T;
mutacion de CIC.

Clasificacion de la OMS de los Tumores del Sistema Nervioso Central,
quinta edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-003
Documento sintetico de demostracion.

MUESTRA
Tejido tumoral incluido en parafina. Celularidad tumoral estimada: 65%.

METODOLOGIA
Secuenciacion de nueva generacion e hibridacion in situ fluorescente para
evaluacion de 1p/19q. Metilacion del promotor de MGMT por pirosecuenciacion.

RESULTADOS
IDH1: mutacion p.R132H (c.395G>A) detectada. Fraccion alelica 35%.
Codelecion 1p/19q: presente. Perdida combinada completa de los brazos
cromosomicos 1p y 19q confirmada por FISH, con ratio 1p/1q de 0,42 y
ratio 19q/19p de 0,38.
Promotor de TERT: mutacion C228T detectada.
ATRX: sin mutacion. Expresion conservada por inmunohistoquimica.
TP53: sin mutacion.
Promotor de MGMT: metilado. Nivel de metilacion 55%.
CIC: mutacion p.R1515H detectada.
FUBP1: sin mutacion.
CDKN2A/B: sin delecion homocigota.

INTERPRETACION
Perfil molecular diagnostico de oligodendroglioma IDH mutante y 1p/19q
codelecionado. La trimodalidad de mutacion de IDH, codelecion 1p/19q y
mutacion del promotor de TERT es caracteristica de esta entidad.
Este perfil se asocia a mejor pronostico y a mayor sensibilidad al
tratamiento con quimioterapia respecto de los astrocitomas IDH mutantes.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-003
Documento sintetico de demostracion.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio. Tomografia
computada complementaria sin contraste para evaluacion de calcificaciones.

HALLAZGOS
Lesion intraaxial de localizacion cortico subcortical en region temporal
izquierda, de 3,1 x 2,4 x 2,2 cm, de limites relativamente definidos.

Senal hiperintensa en T2 y FLAIR, con areas de senal heterogenea.
La tomografia complementaria confirma la presencia de calcificaciones
groseras en el seno de la lesion.

No se observa realce significativo tras la administracion de gadolinio.
Alteracion de senal no realzante perilesional minima. Sin efecto de masa
significativo ni desviacion de la linea media.

En difusion no se observa restriccion. En perfusion, volumen sanguineo
cerebral relativo levemente aumentado, hallazgo descripto en
oligodendrogliomas aun de bajo grado y que no implica por si solo alto
grado histologico.

CONCLUSION
Lesion temporal izquierda sin realce, con calcificaciones, compatible con
glioma difuso de bajo grado de estirpe oligodendroglial. Ausencia de
enfermedad realzante medible segun criterios RANO; el seguimiento debera
realizarse sobre la lesion no realzante en T2/FLAIR.
"""
}

# ---------------------------------------------------------------------------
# CASO-004  Biopsia con material insuficiente
# ---------------------------------------------------------------------------
CASOS['CASO-004'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-004
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Varon de 58 anios, empleado administrativo.

MOTIVO DE CONSULTA
Deficit motor progresivo en hemicuerpo derecho de aproximadamente dos
meses de evolucion.

ENFERMEDAD ACTUAL
Debilidad de instalacion progresiva, inicialmente en miembro superior
derecho, con extension posterior al miembro inferior homolateral. Se agrega
dificultad en la articulacion de la palabra en las ultimas tres semanas.

EXAMEN NEUROLOGICO AL INGRESO
Vigil, orientado. Disartria leve. Hemiparesia derecha a predominio
braquial, con fuerza 3/5 en miembro superior y 4/5 en miembro inferior.
Reflejos osteotendinosos exaltados del lado derecho. Babinski derecho.
Escala funcional de Karnofsky: 70.

ANTECEDENTES PERSONALES
Hipertension arterial en tratamiento. Extabaquista.
Sin antecedentes oncologicos.

EVOLUCION
Dada la localizacion de la lesion en area elocuente y la extension al
tracto corticoespinal evidenciada por tractografia, se decide en ateneo
conjunto con neurocirugia la realizacion de biopsia estereotaxica en lugar
de reseccion.

Se obtienen tres cilindros de biopsia. El estudio intraoperatorio por
congelacion informa glioma de alto grado.

Pendiente de definicion de conducta terapeutica en junta multidisciplinaria,
a la espera de la ampliacion de estudios moleculares.

SITUACION ACTUAL
Karnofsky 70. Dexametasona 4 mg cada 12 horas con mejoria parcial del
deficit motor.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-004
Documento sintetico de demostracion.

MATERIAL REMITIDO
Tres cilindros de biopsia estereotaxica, region frontal derecha.
Longitud conjunta aproximada: 1,2 cm.

DESCRIPCION MICROSCOPICA
Material escaso, constituido por tejido glial con aumento de la celularidad
y atipia nuclear moderada. Se identifican algunas figuras mitoticas.

El material resulta insuficiente para una evaluacion completa de la
presencia de necrosis y de proliferacion microvascular, elementos
necesarios para la graduacion histologica definitiva.

INMUNOHISTOQUIMICA
GFAP: positivo.
IDH1 R132H: negativo.
ATRX: expresion nuclear conservada.
Ki-67: indice proliferativo aproximado del 18%.

OBSERVACION SOBRE ESTUDIOS COMPLEMENTARIOS
El estudio de metilacion del promotor de MGMT no resulta valorable por
material insuficiente. Se solicita nueva muestra o, en su defecto,
interpretacion en el contexto clinico radiologico.

DIAGNOSTICO
Glioma difuso de alto grado. Se sugiere ampliar estudios moleculares para
tipificacion definitiva conforme a la clasificacion de la OMS, quinta
edicion, 2021.

Nota: la negatividad de IDH1 R132H por inmunohistoquimica en un paciente
mayor de 55 anios, en ausencia de otros hallazgos, orienta a glioma IDH
wild-type, si bien la confirmacion requiere secuenciacion.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-004
Documento sintetico de demostracion.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio, con tractografia
por tensor de difusion.

HALLAZGOS
Lesion expansiva intraaxial frontal derecha, de 4,5 x 3,3 x 3,0 cm.
Producto de diametros perpendiculares: 45 x 33 mm.

Realce heterogeneo tras la administracion de contraste, con areas centrales
de menor senal compatibles con necrosis.

Alteracion de senal no realzante en T2/FLAIR perilesional de extension
moderada, con efecto de masa sobre el ventriculo lateral derecho y
desviacion de la linea media de 5 mm.

La tractografia evidencia desplazamiento e infiltracion parcial del
fasciculo corticoespinal derecho, que transcurre por el margen posterior
de la lesion.

CONCLUSION
Lesion expansiva frontal derecha compatible con glioma difuso de alto
grado, con compromiso del tracto corticoespinal. Enfermedad medible segun
criterios RANO. La relacion con el haz corticoespinal condiciona la
estrategia quirurgica.
"""
}

CASOS['CASO-005'] = {
'historia_clinica': """CASO-005 - HC
Documento sintetico de demostracion.

Masculino 49a. Consulta x cefalea + vomitos de 6 sem. Ex: papiledema
bilateral, sin deficit motor. KPS 80.
Ant: s/particulares. No fuma. No alergias.
Qx: reseccion parcial (craneotomia occipital izq). Post-op s/cambios.
RM post-op 48hs: residuo realzante 12 x 9 mm.
Luego RT 60 Gy/30 fx + TMZ concomitante 75 mg/m2.
Actualmente TMZ adyuvante 150 mg/m2, 2do ciclo. Tolerancia OK.
Dexa 4 mg/d en descenso. Levetiracetam 1 g c/12h.
""",

'anatomia_patologica': """CASO-005 - ANATOMIA PATOLOGICA
Documento sintetico de demostracion.

Material: reseccion occipital izquierda.
Micro: proliferacion glial infiltrante, atipia marcada, mitosis frecuentes
(11/10 CGA), necrosis presente, proliferacion microvascular presente.
IHQ: GFAP +, IDH1 R132H negativo, ATRX conservado, p53 s/sobreexpresion,
Ki67 30%.
Dx integrado: Glioblastoma IDH wild-type, grado 4 OMS 2021.
""",

'genomica': """CASO-005 - MOLECULAR
Documento sintetico de demostracion.

Metodo: NGS panel SNC + pirosecuenciacion MGMT.
IDH1/2: wild-type.
MGMT: metilacion del promotor: ausente (3%).
1p/19q: conservados.
TERT promotor: mutado (C228T).
EGFR: sin amplificacion.
TP53: sin mutacion.
CDKN2A/B: delecion homocigota presente.
Cromosomas: +7/-10 presente.
H3: sin mutacion.
Interpretacion: GBM IDH-WT.
""",

'imagenes': """CASO-005 - RM
Documento sintetico de demostracion.

RM encefalo c/ gadolinio. Lesion occipital izq 3,9 x 3,2 x 2,7 cm.
Producto diametros: 39 x 32 mm. Realce anular irregular, necrosis central.
T2/FLAIR: alteracion no realzante perilesional importante.
Efecto de masa +. LM desviada 6 mm a derecha.
Difusion: restriccion en bordes solidos.
Conclusion: glioma de alto grado. Enfermedad medible RANO.
"""
}

# ---------------------------------------------------------------------------
# CASO-006  Glioma difuso de linea media H3 K27 alterado
# ---------------------------------------------------------------------------
CASOS['CASO-006'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-006
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Varon de 28 anios, estudiante universitario.

MOTIVO DE CONSULTA
Diplopia y ataxia de la marcha de seis semanas de evolucion.

ENFERMEDAD ACTUAL
Vision doble binocular horizontal, de instalacion progresiva, con posterior
agregado de inestabilidad en la marcha y disfagia leve para liquidos.

EXAMEN NEUROLOGICO AL INGRESO
Vigil, orientado. Paresia del VI par craneal izquierdo. Nistagmo horizontal
en la mirada lateral. Ataxia de tronco con marcha de base amplia.
Reflejo nauseoso disminuido. Fuerza 5/5 en los cuatro miembros.
Escala funcional de Karnofsky: 70.
Escala NANO: marcha 2, ataxia 2, resto de los dominios sin alteracion.

ANTECEDENTES PERSONALES
Sin antecedentes de relevancia. Sin medicacion habitual.

EVOLUCION Y TRATAMIENTO
Dada la localizacion protuberancial de la lesion, se desestima la reseccion.
Se realiza biopsia estereotaxica guiada por neuronavegacion, con obtencion
de material representativo y sin complicaciones.

Inicia radioterapia focal 54 Gy en 30 fracciones de 1,8 Gy.
Se indica temozolomida concomitante, si bien se consigna en la discusion
del caso que el beneficio de los agentes alquilantes en esta entidad no
se encuentra establecido con el mismo nivel de evidencia que en el
glioblastoma IDH wild-type.

Dexametasona 8 mg por dia con mejoria parcial de la diplopia.

SITUACION ACTUAL
Karnofsky 70. En curso de radioterapia. Evaluacion de deglucion por
fonoaudiologia con indicacion de dieta de consistencia modificada.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-006
Documento sintetico de demostracion.

MATERIAL REMITIDO
Cilindros de biopsia estereotaxica de lesion protuberancial.

DESCRIPCION MICROSCOPICA
Proliferacion glial infiltrante de celularidad moderada a alta, con atipia
nuclear y presencia de figuras mitoticas. Se identifican focos de
proliferacion microvascular. No se observa necrosis en el material
examinado.

INMUNOHISTOQUIMICA
GFAP: positivo.
H3 K27M: positivo, con marcacion nuclear intensa y difusa en celulas
tumorales.
H3 K27me3: perdida de expresion nuclear.
IDH1 R132H: negativo.
ATRX: perdida de expresion nuclear.
p53: sobreexpresion nuclear en aproximadamente 70% de las celulas.
Ki-67: indice proliferativo del 25%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Glioma difuso de la linea media, H3 K27 alterado,
grado 4 de la OMS.
Apariencia histologica: glioma difuso infiltrante con proliferacion
microvascular.
Grado OMS: 4.
Parametros moleculares: mutacion H3 K27M presente; perdida de H3 K27me3;
IDH wild-type; mutacion de ATRX con perdida de expresion; mutacion de TP53.

Nota: en esta entidad el grado 4 se asigna con independencia de los
hallazgos histologicos, conforme a la clasificacion de la OMS, quinta
edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-006
Documento sintetico de demostracion.

MUESTRA
Tejido de biopsia estereotaxica. Celularidad tumoral estimada: 55%.

METODOLOGIA
Secuenciacion de nueva generacion, panel de tumores del sistema nervioso
central. Metilacion del promotor de MGMT por pirosecuenciacion.

RESULTADOS
H3F3A: mutacion p.K28M (historicamente denominada K27M) detectada.
Fraccion alelica 42%.
IDH1 e IDH2: no se detectan mutaciones. Perfil IDH wild-type.
ATRX: mutacion con perdida de funcion.
TP53: mutacion p.R248Q detectada.
Promotor de MGMT: no metilado.
Codelecion 1p/19q: no se evidencia.
Promotor de TERT: sin mutacion.
EGFR: sin amplificacion.
CDKN2A/B: sin delecion homocigota.
ACVR1: sin mutacion.

INTERPRETACION
Perfil molecular diagnostico de glioma difuso de la linea media, H3 K27
alterado. La presencia de la mutacion H3 K27M define la entidad y asigna
grado 4 con independencia de la histologia.
Esta entidad presenta pronostico desfavorable y se asocia a localizacion
en estructuras de la linea media.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-006
Documento sintetico de demostracion.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio, con cortes finos de
fosa posterior.

HALLAZGOS
Lesion expansiva intraaxial centrada en la protuberancia, que compromete
mas del 50% del area transversal del puente, con extension al pedunculo
cerebeloso medio izquierdo.

Diametros maximos: 3,4 x 2,9 x 2,6 cm. Producto de diametros
perpendiculares: 34 x 29 mm.

Senal hiperintensa en T2 y FLAIR, hipointensa en T1. Realce tenue y
parcheado tras la administracion de gadolinio, en el sector posterolateral
izquierdo.

Englobamiento de la arteria basilar sin estenosis significativa.
Efecto de masa sobre el cuarto ventriculo con dilatacion incipiente del
sistema ventricular supratentorial.

En difusion no se observa restriccion significativa.

CONCLUSION
Lesion expansiva protuberancial infiltrante con realce tenue, compatible
con glioma difuso de la linea media. La localizacion y el patron de
crecimiento desaconsejan la reseccion quirurgica.
"""
}

CASOS['CASO-007'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-007
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Mujer de 44 anios, enfermera.

MOTIVO DE PRESENTACION EN JUNTA
Evaluacion de respuesta al tratamiento tras completar seis ciclos de
quimioterapia adyuvante. Caso ya discutido previamente al diagnostico.

ANTECEDENTES DE LA ENFERMEDAD ACTUAL
Diagnostico inicial hace 14 meses a partir de crisis focal motora.
Reseccion macroscopicamente completa mediante craneotomia frontal derecha.
Diagnostico anatomopatologico de astrocitoma IDH mutante, grado 3.

TRATAMIENTO RECIBIDO
Radioterapia conformada 59,4 Gy en 33 fracciones de 1,8 Gy, finalizada
hace 11 meses.
Temozolomida adyuvante 150 a 200 mg/m2, cinco dias cada 28. Completo 12
ciclos, finalizados hace 2 meses.

Toxicidad registrada: trombocitopenia grado 2 en los ciclos 4 y 9, que
motivo reduccion de dosis al 75% a partir del ciclo 10. Nauseas grado 1
controladas con ondansetron.

EXAMEN NEUROLOGICO ACTUAL
Vigil, orientada. Sin deficit motor ni sensitivo. Lenguaje conservado.
Escala funcional de Karnofsky: 90.
Escala NANO: sin alteraciones.
MoCA: 28 sobre 30.

MEDICACION ACTUAL
Levetiracetam 500 mg cada 12 horas. Sin crisis en los ultimos 10 meses.
Sin corticoides desde hace 9 meses.

SITUACION ACTUAL
Asintomatica, con actividad laboral habitual. Se presenta en junta para
definir conducta de seguimiento.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-007
Documento sintetico de demostracion.
Informe correspondiente a la cirugia inicial, realizada hace 14 meses.

MATERIAL REMITIDO
Pieza de reseccion tumoral, region frontal derecha.

DESCRIPCION MICROSCOPICA
Proliferacion glial difusamente infiltrante con atipia nuclear moderada y
actividad mitotica, con recuento de 6 mitosis por 10 campos de gran
aumento. No se observa proliferacion microvascular ni necrosis.

INMUNOHISTOQUIMICA
GFAP: positivo difuso.
IDH1 R132H: positivo.
ATRX: perdida de expresion nuclear.
p53: sobreexpresion nuclear en aproximadamente 55% de las celulas.
Ki-67: indice proliferativo del 15%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Astrocitoma IDH mutante, grado 3 de la OMS.
Apariencia histologica: glioma difuso con actividad mitotica.
Grado OMS: 3.
Parametros moleculares: mutacion IDH1 R132H; mutacion de ATRX; mutacion de
TP53; 1p/19q sin codelecion; CDKN2A/B sin delecion homocigota.

Clasificacion de la OMS de los Tumores del Sistema Nervioso Central,
quinta edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-007
Documento sintetico de demostracion.
Informe correspondiente a la muestra de la cirugia inicial.

METODOLOGIA
Secuenciacion de nueva generacion, panel de tumores del sistema nervioso
central. Metilacion del promotor de MGMT por pirosecuenciacion.

RESULTADOS
IDH1: mutacion p.R132H detectada. Fraccion alelica 40%.
IDH2: sin variantes.
Codelecion 1p/19q: ausente.
Promotor de MGMT: metilado. Nivel de metilacion 48%.
ATRX: mutacion con perdida de funcion.
TP53: mutacion p.R175H detectada.
Promotor de TERT: sin mutacion.
EGFR: sin amplificacion.
CDKN2A/B: sin delecion homocigota.

INTERPRETACION
Perfil molecular de astrocitoma IDH mutante. El estado metilado del
promotor de MGMT es consistente con la respuesta favorable observada al
tratamiento con temozolomida.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-007
Documento sintetico de demostracion.
Estudio de seguimiento con evaluacion de respuesta.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio. Protocolo de
neuro-oncologia. Comparacion con estudio basal posterior a radioterapia,
realizado hace 11 meses.

HALLAZGOS
Cavidad de reseccion frontal derecha, de bordes regulares, sin cambios
respecto del estudio previo.

Lesion diana realzante en el margen posteromedial de la cavidad:
Estudio basal: 22 x 16 mm. Producto de diametros: 352 mm2.
Estudio actual: 12 x 9 mm. Producto de diametros: 108 mm2.
Reduccion del producto de diametros perpendiculares: 69,3%.

Alteracion de senal no realzante en T2/FLAIR periferica a la cavidad, sin
cambios significativos respecto del estudio previo.

No se identifican nuevas lesiones realzantes ni a distancia.
Sin efecto de masa. Linea media centrada.
En difusion no se observan areas de restriccion.
En perfusion, volumen sanguineo cerebral relativo disminuido en el sector
realzante respecto del estudio basal.

EVALUACION DE RESPUESTA SEGUN CRITERIOS RANO
Reduccion del producto de diametros perpendiculares del 69,3%, superior al
umbral del 50% requerido para respuesta parcial.
Sin aparicion de nuevas lesiones.
Alteracion no realzante en T2/FLAIR estable.
La paciente no recibe corticoides.
Estado clinico estable o mejorado.

CONCLUSION
Respuesta parcial segun criterios RANO. Se sugiere confirmacion en estudio
de control a las 4 semanas y continuidad del seguimiento imagenologico.
"""
}

# ---------------------------------------------------------------------------
# CASO-008  Sospecha de pseudoprogresion
# ---------------------------------------------------------------------------
CASOS['CASO-008'] = {
'historia_clinica': """HISTORIA CLINICA - CASO-008
Documento sintetico de demostracion. No corresponde a un paciente real.

DATOS DEL PACIENTE
Varon de 54 anios, comerciante.

MOTIVO DE PRESENTACION EN JUNTA
Aumento del realce en la resonancia de control realizada a las 4 semanas
de finalizada la quimiorradioterapia. Se plantea el diagnostico
diferencial entre progresion tumoral y pseudoprogresion.

ANTECEDENTES DE LA ENFERMEDAD ACTUAL
Diagnostico hace 4 meses a partir de cefalea y hemianopsia homonima
izquierda. Reseccion subtotal mediante craneotomia temporooccipital
derecha. Diagnostico de glioblastoma IDH wild-type, grado 4.

TRATAMIENTO RECIBIDO
Radioterapia 60 Gy en 30 fracciones de 2 Gy con temozolomida concomitante
75 mg/m2 diarios, finalizada hace 4 semanas.
Pendiente el inicio de la fase adyuvante.

EXAMEN NEUROLOGICO ACTUAL
Vigil, orientado. Hemianopsia homonima izquierda, sin cambios respecto del
examen previo al inicio del tratamiento. Fuerza 5/5 global. Sin nuevo
deficit focal.
Escala funcional de Karnofsky: 80, sin variacion respecto del control previo.
Escala NANO: campo visual 2, resto de los dominios sin alteracion, sin
cambios respecto de la evaluacion anterior.

MEDICACION ACTUAL
Dexametasona 4 mg por dia, dosis estable desde hace 6 semanas, sin
necesidad de incremento.
Levetiracetam 1000 mg cada 12 horas.

CONSIDERACION CLINICA PARA LA JUNTA
El paciente se encuentra clinicamente estable, sin deterioro neurologico
ni necesidad de aumentar la dosis de corticoides, en el contexto de un
aumento del realce radiologico dentro de las 12 semanas posteriores a la
finalizacion de la radioterapia.
""",

'anatomia_patologica': """INFORME ANATOMOPATOLOGICO - CASO-008
Documento sintetico de demostracion.
Informe correspondiente a la cirugia inicial, realizada hace 4 meses.

MATERIAL REMITIDO
Tejido de reseccion tumoral, region temporooccipital derecha.

DESCRIPCION MICROSCOPICA
Neoplasia glial de alta celularidad con marcado pleomorfismo nuclear y
elevada actividad mitotica, con recuento de 16 mitosis por 10 campos de
gran aumento. Areas de necrosis con seudoempalizada perinecrotica y
proliferacion microvascular glomeruloide.

INMUNOHISTOQUIMICA
GFAP: positivo.
IDH1 R132H: negativo.
ATRX: expresion nuclear conservada.
Ki-67: indice proliferativo del 40%.

DIAGNOSTICO INTEGRADO (formato en capas segun ICCR)
Diagnostico integrado: Glioblastoma IDH wild-type, grado 4 de la OMS.
Apariencia histologica: glioma difuso de alto grado con necrosis y
proliferacion microvascular.
Grado OMS: 4.
Parametros moleculares: IDH wild-type; promotor de TERT mutado C250T;
promotor de MGMT metilado; amplificacion de EGFR ausente; delecion
homocigota de CDKN2A/B presente.

Clasificacion de la OMS de los Tumores del Sistema Nervioso Central,
quinta edicion, 2021.
""",

'genomica': """INFORME DE SECUENCIACION GENOMICA - CASO-008
Documento sintetico de demostracion.

METODOLOGIA
Secuenciacion de nueva generacion, panel de tumores del sistema nervioso
central. Metilacion del promotor de MGMT por pirosecuenciacion.

RESULTADOS
IDH1 e IDH2: no se detectan mutaciones. Perfil IDH wild-type.
Promotor de TERT: mutacion C250T detectada.
Promotor de MGMT: metilado. Nivel de metilacion 31%.
EGFR: sin amplificacion.
Codelecion 1p/19q: no se evidencia.
CDKN2A/B: delecion homocigota presente.
TP53: sin mutacion.
ATRX: sin mutacion.
Perfil de numero de copias: ganancia del cromosoma 7 y perdida del
cromosoma 10.

INTERPRETACION
Perfil molecular de glioblastoma IDH wild-type.
El estado metilado del promotor de MGMT resulta relevante en el contexto
clinico actual: se asocia tanto a mayor beneficio de los agentes
alquilantes como a una mayor frecuencia de pseudoprogresion tras la
quimiorradioterapia, dato a considerar en la interpretacion del estudio
de control.
""",

'imagenes': """INFORME DE RESONANCIA MAGNETICA - CASO-008
Documento sintetico de demostracion.
Estudio de control posterior a quimiorradioterapia.

ESTUDIO
Resonancia magnetica de encefalo sin y con gadolinio. Protocolo de
neuro-oncologia con perfusion. Comparacion con estudio posoperatorio
realizado hace 4 meses y con estudio previo al inicio de la radioterapia.

HALLAZGOS
Cavidad de reseccion temporooccipital derecha.

Lesion diana realzante en el margen anterior de la cavidad:
Estudio previo: 14 x 11 mm. Producto de diametros: 154 mm2.
Estudio actual: 21 x 16 mm. Producto de diametros: 336 mm2.
Incremento del producto de diametros perpendiculares: 118%.

El incremento del realce se localiza integramente dentro del volumen
irradiado, en la region de alta dosis correspondiente a la isodosis del
95%.

Alteracion de senal no realzante en T2/FLAIR perilesional con leve
incremento respecto del estudio previo.

No se identifican lesiones nuevas fuera del campo de irradiacion.

En difusion, valores de coeficiente de difusion aparente elevados en el
sector de nuevo realce, sin restriccion.
En perfusion, volumen sanguineo cerebral relativo disminuido en el sector
de nuevo realce respecto del parenquima contralateral, con valor de 0,9.

CONSIDERACIONES PARA LA EVALUACION DE RESPUESTA
El incremento del realce se produce dentro de las 12 semanas posteriores a
la finalizacion de la radioterapia y se localiza por completo dentro del
campo de alta dosis.
Conforme a los criterios RANO, en esta ventana temporal la progresion
solo puede establecerse radiologicamente si aparece realce nuevo por fuera
del campo de irradiacion, circunstancia que no se verifica en el presente
estudio.
Los hallazgos de perfusion, con volumen sanguineo cerebral relativo
disminuido, y de difusion, sin restriccion, resultan mas compatibles con
cambios posterapeuticos que con progresion tumoral.

CONCLUSION
Aumento del realce dentro del campo de alta dosis, en ventana temporal y
con patron de perfusion compatibles con pseudoprogresion. No corresponde
establecer progresion segun criterios RANO en el presente estudio.
Se sugiere resonancia de confirmacion en 4 a 8 semanas antes de modificar
la conducta terapeutica.
"""
}

if __name__ == "__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    for caso, docs in sorted(CASOS.items()):
        d = BASE / caso
        d.mkdir(parents=True, exist_ok=True)
        for tipo, contenido in docs.items():
            (d / f"{tipo}.txt").write_text(contenido, encoding="utf-8")
        print(f"{caso}: {len(docs)} documentos")
    print(f"\nTotal: {len(CASOS)} casos generados en {BASE}")
