# Casos de demostración

Ocho casos sintéticos, distribuidos deliberadamente en formatos heterogéneos.
**Se cargan a mano desde la pantalla «Carga de caso»**: el sistema ya no
incluye un selector de casos de ejemplo.

## Qué son estos casos

Documentos sintéticos. No corresponden a pacientes reales ni reproducen
textualmente ningún informe publicado. Su estructura y terminología siguen:

- **EANO**, guías de diagnóstico y tratamiento de gliomas difusos del adulto
  (Weller et al., *Nat Rev Clin Oncol* 2021): marcadores requeridos, esquemas
  terapéuticos con dosis y pautas de seguimiento.
- **CAP / AANP / AMP / SNO** (Brat et al., *Arch Pathol Lab Med* 2022):
  biomarcadores a determinar y técnicas aceptadas para cada uno.
- **ICCR**, conjunto de datos de diagnóstico integrado de tumores del SNC
  (2.ª edición): informe anatomopatológico en cuatro capas, diagnóstico
  integrado, apariencia histológica, parámetros moleculares y grado CNS WHO.
- **RANO**: medición bidimensional y evaluación de respuesta, con la ventana
  de 12 semanas para pseudoprogresión.

Las figuras incluidas en los documentos de Word son **esquemas rotulados como
sintéticos**. No se generaron imágenes que imiten estudios radiológicos: una
figura verosímil podría desprenderse de su contexto y tomarse por un estudio
auténtico.

## Distribución por formato

| Caso | Entidad | Formatos |
|---|---|---|
| CASO-001 | Astrocitoma IDH mutante grado 3 | docx (con figura), pdf, xlsx, txt |
| CASO-002 | Glioblastoma IDH wild-type | odt, docx, csv, pdf |
| CASO-003 | Oligodendroglioma 1p/19q codelecionado | rtf, txt, md, html |
| CASO-004 | Documentación incompleta | html, docx (con figura), pdf |
| CASO-005 | Redacción abreviada | txt |
| CASO-006 | Glioma de línea media H3 K27 alterado | docx (con figura), pdf, xlsx, md |
| CASO-007 | Evaluación de respuesta RANO | pdf, docx, csv, pdf |
| CASO-008 | Pseudoprogresión | odt, txt, md, docx (con figura) |

## Cómo cargarlos

1. En «Carga de caso», indique el identificador anonimizado (por ejemplo
   `CASO-001`).
2. Adjunte cada documento en el casillero que corresponde a su tipo.
3. Procese el caso.

## Regenerarlos

```bash
python scripts/generar_casos_demo.py                 # formatos variados
python scripts/generar_casos_demo.py --texto-plano   # todo en .txt
```

Una prueba automatizada verifica que **el formato no altere el resultado**:
el perfil molecular extraído de los documentos en formatos variados debe
coincidir exactamente con el obtenido del mismo contenido en texto plano.
