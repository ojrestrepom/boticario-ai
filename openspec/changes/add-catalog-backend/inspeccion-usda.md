# Inspección del ZIP real de USDA (tarea 5.2)

Inspección de solo lectura de `data/.cache/Duke-Source-CSV.zip` (6,033,990 bytes, MD5 `45ae44a0544586b8ac22a232beaac344`, verificado por el comando `download` de la tarea 5.1). Los números salen de un análisis con Python (`csv`) sobre los CSV decodificados como Windows-1252 y se contrastaron con la importación cruda real hecha por `import_raw` (mismas filas por tabla). Todas las comparaciones de texto se hicieron tras recortar espacios exteriores, como pide la guía; en este ZIP no hay ninguna celda de las columnas usadas con espacios exteriores, así que el recorte no cambia nada hoy.

## 1. Entradas del ZIP

Las 16 entradas usan el mismo método, `Defl:N` (deflate); basta la feature `deflate` del crate `zip` que ya está en el workspace. No hay carpetas ni entradas cifradas.

| Entrada | Bytes | Filas de datos | Columnas |
|---|---:|---:|---:|
| ACTIVITIES.csv | 156,920 | 2,432 | 7 |
| AGGREGAC.csv | 1,855,470 | 28,929 | 9 |
| ASSAY.csv | 64,943 | 2,630 | 5 |
| CHEM_MEANS.csv | 136,589 | 3,832 | 5 |
| CHEMICALS.csv | 2,204,724 | 29,585 | 8 |
| CODES.csv | 495,109 | 8,926 | 5 |
| COMMON_NAMES.csv | 167,001 | 2,920 | 6 |
| DOSAGE.csv | 69,458 | 1,627 | 3 |
| ETHNOBOT.csv | 12,122,539 | 82,873 | 19 |
| FARMACY.csv | 6,810,139 | 68,844 | 20 |
| FARMACY_NEW.csv | 14,998,874 | 104,388 | 25 |
| FNFTAX.csv | 393,309 | 2,376 | 24 |
| PARTS.csv | 4,341 | 115 | 5 |
| REFERENCES.csv | 317,288 | 2,043 | 6 |
| SUPERACT.csv | 155,415 | 5,358 | 2 |
| YIELDS.csv | 636,384 | 2,824 | 55 |

Cabeceras de las tablas que usa la curación y de las relacionadas:

- `FNFTAX` (24): FNFNUM, TAXON, TAXAUTHOR, GENUS, SPECIES, SUBSPECIES, VARIETY, FORMA, CULTIVAR, SPAUT, SPSAUT, SPVAUT, SPFAUT, CULTAUT, FAMILY, SPCMT, PLCO, TAXNO, VALIDTAXNO, GRINVERIFY, USEAGE, USERID, CREATED, MODIFIED.
- `FARMACY_NEW` (25): FNFNUM, CHEM, CHEMCLASS, PPCO, PLCO, AMT_OR_LO, AMT_HI, AMT_ULHI, EOPCT_OR_LO, EOPCT_HI, INDIVIDUAL, TRACE, REFERENCE, REFYR, LT, USERID, CREATED, MODIFIED, NAPREF, AMT_LO, AMT_OR_HI, EOPCT_LO, EOPCT_OR_HI, QUANT_UNIT, CHEMID.
- `PARTS` (5): PPCO, PPNA, USERID, CREATED, MODIFIED.
- `ETHNOBOT` (19): ETHNO, ACTIVITY, GENUS, SPECIES, SPAUT, SPRANK, SPXNAM, SPXAUT, FAMILY, CNAME, COUNTRY, REFERENCE, LONGREF, EFFECTIVE, TAXON, TAXAUTHOR, USERID, CREATED, MODIFIED.
- `REFERENCES` (6): REFERENCE, LONGREF, NOTE, USERID, CREATED, MODIFIED.
- `COMMON_NAMES` (6): CNNAM, FNFNUM, CNID, USERID, CREATED, MODIFIED.

## 2. Columnas que usará la derivación

| Tabla | Columnas | Papel |
|---|---|---|
| `FNFTAX` | `FNFNUM` | Identificador de la planta en la fuente (`source_plant_id`). |
| `FNFTAX` | `TAXON` | Nombre científico literal e identidad canónica. |
| `FNFTAX` | `GENUS`, `SPECIES` | Parte del selector exacto para cruzar con `ETHNOBOT` junto con `TAXON`. |
| `FNFTAX` | `FAMILY` | Familia (ver sección 4). |
| `FARMACY_NEW` | `FNFNUM`, `PPCO` | Asocia la planta con códigos de parte; se ignoran los `PPCO` vacíos y se deduplica por (`FNFNUM`, `PPCO`). |
| `PARTS` | `PPCO`, `PPNA` | Resuelve el código a la etiqueta literal de la parte. |
| `ETHNOBOT` | `GENUS`, `SPECIES`, `TAXON` | Cruce exacto con `FNFTAX` (ETHNOBOT no tiene `FNFNUM`). |
| `ETHNOBOT` | `ACTIVITY` | Actividad literal del uso. |
| `ETHNOBOT` | `REFERENCE` | Clave que se resuelve en `REFERENCES`. |
| `ETHNOBOT` | `ETHNO` | Identificador único de la fila de uso (82,873 valores distintos, uno por fila). |
| `REFERENCES` | `REFERENCE`, `LONGREF` | Clave y cita completa literal. |
| `COMMON_NAMES` | `FNFNUM`, `CNNAM` | Nombres comunes (ver sección 3). |

Columnas que no se usan: `FARMACY`, `ETHNOBOT.FAMILY`, `ETHNOBOT.CNAME`, `ETHNOBOT.LONGREF` y el resto de columnas. `ETHNOBOT.LONGREF` está vacía en las 82,873 filas, así que la única fuente de citas es `REFERENCES`. `ETHNOBOT.CNAME` trae un nombre común por fila de uso (29,478 filas no vacías) pero no se relaciona con `FNFNUM`; no se propone usarla.

## 3. Nombres comunes

- Tabla `COMMON_NAMES`, columnas `CNNAM` (texto) y `FNFNUM` (relación con `FNFTAX.FNFNUM`). `CNID` no es un identificador de fila: es una etiqueta de agrupación ("CLUBMOSS", "HAWTHORN"...).
- 2,920 filas, todas con `FNFNUM` presente en `FNFTAX` y `CNNAM` no vacío ni con espacios exteriores. No hay pares (`FNFNUM`, nombre) repetidos, ni siquiera ignorando mayúsculas.
- 1,577 taxones de 2,376 tienen al menos un nombre común. Distribución de nombres por taxón: 1 nombre en 959 taxones, 2 en 355, 3 en 112, 4 en 55, 5 en 41, 6 en 24, y más en el resto.
- No hay columna de idioma. Todos los textos son ASCII. Hay indicios de mezcla: 208 nombres llevan un paréntesis al final y 204 parecen etiquetas de idioma o de origen, por ejemplo `Fieberstrauch (Ger.)`, `Malagueta (Sp.)`, `Myrrhe (Fr., Ger.)`, `Umsuzwane (Zulu)`. Etiquetas más frecuentes: `Sp.` 44, `Ger.` 38, `KAB` 31, `Fr.` 20, `BOU` 18, `Sansk.` 18, `Arab.` 12, `Jap.` 11, `USN` 11, `Eng.` 9. Los 2,712 nombres sin paréntesis cubren 1,575 taxones. Un nombre sin paréntesis tampoco garantiza que sea inglés (por ejemplo `Rosella`, `Zhi-Mu`, `Zuta`).
- Los cinco taxones de la guía: 544 `English Lavender`; 401 `Blue Gum`, `Eucalypt`, `Tasmanian Bluegum`; 873 `Rosemary`; 605 `Annual Camomile`, `German Camomile`, `Wild Camomile`; 619 `Peppermint`.

## 4. Familia

- Tabla `FNFTAX`, columna `FAMILY`. 2,342 de 2,376 taxones la tienen; 34 la tienen vacía (la derivación debe producir `None`, no una cadena vacía). 200 familias distintas, sin espacios exteriores. Las más frecuentes: Lamiaceae 288, Fabaceae 269, Asteraceae 113, Myrtaceae 101, Ebenaceae 67.
- `ETHNOBOT.FAMILY` también existe (82,416 filas no vacías) pero no se usa: la familia pertenece a la planta, no al uso.

## 5. Identidad

- `FNFTAX` tiene 2,376 filas y 2,376 `FNFNUM` distintos; todos son numéricos.
- `TAXON` vacío: 0. `GENUS` vacío: 0. `SPECIES` vacío: 0. `TAXON` con espacios exteriores o dobles: 0.
- `TAXON` repetido entre `FNFNUM` distintos: **0 casos**, tampoco ignorando mayúsculas ni tras convertir a slug (0 colisiones). La tarea 5.2 pedía reportar esto antes de continuar si hubiera repetidos; no los hay, así que no se necesita decisión sobre identidades duplicadas.
- `TAXON` coincide con `GENUS` + espacio + `SPECIES` en 2,326 filas. Hay 50 excepciones, todas con `SUBSPECIES`, `VARIETY`, `FORMA` o `CULTIVAR` rellenos, donde `TAXON` añade el rango infraespecífico. Ejemplos: 1414 `Acinos alpinus var. meridionalis`; 157 `Beta vulgaris subsp. subsp. vulgaris` (el prefijo `subsp.` aparece duplicado en el propio dato); 180 `Brassica oleracea var. gongylodes`.
- Sorpresa en esas excepciones: a veces `SPECIES` ya contiene texto infraespecífico (172 tiene `GENUS` `Brassica` y `SPECIES` `napus var. napobrassica`, con `TAXON` `Brassica napus var. napobrassica var. napobrassica`). Por eso la identidad debe tomarse siempre de `TAXON` literal, nunca recomponerla desde columnas.

## 6. Usos

- `ETHNOBOT` tiene 82,873 filas. Ninguna tiene espacios exteriores en `GENUS`, `SPECIES`, `TAXON`, `ACTIVITY` ni `REFERENCE`.
- Cruce exacto por `GENUS` + `SPECIES` + `TAXON` con `FNFTAX`: **30,484** filas. Otras 403 filas coinciden en `GENUS` + `SPECIES` pero no en `TAXON` y quedan excluidas por el criterio de la guía.
- `REFERENCES`: 2,043 filas, 2,043 claves distintas (ninguna clave repetida, vacía ni distinta solo por mayúsculas) y ningún `LONGREF` vacío. Por eso no existen referencias ambiguas en este ZIP. 13 `LONGREF` contienen saltos de línea dentro del campo.
- De las 30,484 filas exactas, **19,446** tienen `REFERENCE` resoluble de forma inequívoca y **11,038** no: 11,036 por clave ausente en `REFERENCES` (por ejemplo `Burkill,1966`, `Woi.Syria`, `Nas`) y 2 por `REFERENCE` vacío. 0 por ambigüedad.
- Referencias distintas entre los usos elegibles: **32**. Taxones con al menos un uso elegible: **1,180**.
- `ACTIVITY`: sin espacios exteriores y sin variantes de mayúsculas (1,173 textos distintos entre los elegibles, igual tras recortar y tras pasar a minúsculas). Ninguna `ACTIVITY` vacía.
- Las filas elegibles repiten (taxón, `ACTIVITY`, `REFERENCE`) en 515 casos: son filas distintas de la fuente (`ETHNO` distinto, normalmente otro país) con la misma actividad y cita. Ver decisiones.

## 7. Partes

- `FARMACY_NEW` tiene 104,388 filas. 13 filas (12 taxones) tienen `PPCO` vacío; deben ignorarse.
- Códigos `PPCO` distintos no vacíos: 90. Los 90 resuelven en `PARTS` (115 filas, 115 `PPCO` distintos, ninguno duplicado, ningún `PPNA` vacío); 0 no resuelven. No hay diferencias de mayúsculas entre códigos de ambas tablas.
- 2,310 taxones tienen al menos una parte; 66 no tienen ninguna. Pares (`FNFNUM`, `PPCO`) distintos y no vacíos: 6,740.
- Todos los `FNFNUM` de `FARMACY_NEW` existen en `FNFTAX`.

## 8. Verificación de la guía

Los conteos coinciden exactamente con `docs/data/usda-catalog.md` para los cinco taxones.

| FNFNUM | Taxón | Exactas | Elegibles | Excluidas | Partes (códigos distintos, todos resuelven) | Referencias | Familia |
|---:|---|---:|---:|---:|---:|---:|---|
| 544 | Lavandula angustifolia | 13 | 10 | 3 | 4 | 1 | Lamiaceae |
| 401 | Eucalyptus globulus | 57 | 51 | 6 | 15 | 8 | Myrtaceae |
| 873 | Rosmarinus officinalis | 92 | 60 | 32 | 9 | 11 | Lamiaceae |
| 605 | Matricaria recutita | 0 | 0 | 0 | 3 | 0 | Asteraceae |
| 619 | Mentha x piperita subsp. nothosubsp. piperita | 0 | 0 | 0 | 5 | 0 | Lamiaceae |

Las partes (4, 15, 9, 3, 5 = 36) y los usos elegibles (10 + 51 + 60 = 121) coinciden con el resumen de la guía. Los valores de referencia de la tarea 5.6 también salen idénticos en esta inspección: 2,376 taxones, 1,180 con al menos un uso elegible, 19,446 usos elegibles y 32 referencias.

## 9. Otras observaciones para el adaptador

- Codificación: los 16 CSV son ASCII puro (ningún byte mayor que 0x7F), así que Windows-1252 y UTF-8 dan el mismo texto. Se mantiene Windows-1252 por lo que documenta la guía; no hay bytes sin definir en Windows-1252. No hay BOM.
- Saltos de línea: mezcla de `\r\n` (ACTIVITIES, AGGREGAC, CHEM_MEANS, REFERENCES, SUPERACT) y `\n` (el resto). Solo `REFERENCES` tiene saltos de línea dentro de campos (13 `LONGREF`), por lo que va entrecomillada. En ningún CSV hay comillas dentro de los campos.
- Todas las filas de todos los CSV tienen exactamente el número de campos de su cabecera; no hay columnas duplicadas ni vacías en ninguna cabecera.
- `import_raw` con `UsdaAdapter::raw_import` importó el ZIP real sin error en unos 0.3 s (compilación release), en una base temporal fuera del repo, creando las 16 tablas `raw_usda_*` con exactamente las filas de la tabla del punto 1. Se hizo con un ejemplo temporal que no quedó en el repositorio.
- Las 11 filas de `ETHNOBOT` con `REFERENCE` vacío y las claves ausentes son datos de la fuente: el criterio las excluye sin cambiarlas.

## Decisiones que requiere el usuario

1. **Idioma de los nombres comunes.** `COMMON_NAMES` no declara idioma. Opciones: (a) asignar `en` a todos, lo que etiquetaría como inglés unos 204 nombres que el propio dato marca como alemán, español, francés, sánscrito, etc.; (b) asignar `en` solo a los nombres sin paréntesis (2,712 nombres, 1,575 taxones) y descartar los marcados, aun sabiendo que algunos sin marca tampoco son ingleses; (c) conservar los marcados pero con idioma inferido de la etiqueta cuando exista, lo que añade lógica y más supuestos. El diseño dice "nombres comunes en inglés con su idioma": hay que decidir cuál aplica.
2. **Etiquetas entre paréntesis en los nombres.** Aunque se conserven, ¿se deja el texto literal (`Rumberry (Eng.)`) o se recorta el paréntesis? Hoy se propone no modificar el texto de la fuente.
3. **Usos repetidos.** Hay 515 filas elegibles que repiten (taxón, actividad, referencia) con distinto `ETHNO`. ¿Se conservan como usos separados (19,446, que es el valor de referencia de la tarea 5.6) o se deduplican? Mantenerlas respeta el valor de referencia y la guía; el esquema decide si es posible.
4. **Plantas sin familia.** 34 taxones no tienen familia: se propone `None`, sin inventar nada.
5. **Nombres científicos con `subsp.` duplicado.** Algunos `TAXON` literales contienen texto repetido (por ejemplo `Beta vulgaris subsp. subsp. vulgaris`). Se propone conservarlos tal cual, como la guía; confirmar.
