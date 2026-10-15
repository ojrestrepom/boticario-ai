# Fuente USDA: procedencia y criterio de selección

Esta guía documenta la fuente USDA Dr. Duke's Phytochemical and Ethnobotanical Databases y el criterio de selección que sigue el adaptador del backend. No es una afirmación sobre la vigencia taxonómica o clínica de los datos de la fuente. La curación manual de cinco plantas (Lavanda, Eucalipto, Romero, Manzanilla y Menta) que sirvió de referencia se conserva como fixture `backend/catalog-ingest/tests/fixtures/plant_catalog.json` del test ignorado `asset_crosscheck.rs`, que comprueba que la derivación del backend coincide con esa curación.

## Fuente, archivo y fechas

- Dataset archivado: [USDA Dr. Duke's Phytochemical and Ethnobotanical Databases, Ag Data Commons, artículo 24660351, versión 1](https://agdatacommons.nal.usda.gov/articles/dataset/Dr_Duke_s_Phytochemical_and_Ethnobotanical_Databases/24660351).
- Archivo original: [`Duke-Source-CSV.zip`, file ID 43363335](https://ndownloader.figshare.com/files/43363335) (6,033,990 bytes; MD5 `45ae44a0544586b8ac22a232beaac344`). La ficha de API del artículo es [v2](https://api.figshare.com/v2/articles/24660351).
- Diccionario de datos del artículo: [file ID 43363338](https://ndownloader.figshare.com/files/43363338) (archivo complementario).
- Licencia declarada por USDA: [CC0](https://phytochem.nal.usda.gov/about).
- Inspección del ZIP: 2026-10-01. Es la fecha de esa inspección, no una fecha de publicación, captura ni periodo cubierto.
- Cita del artículo registrada por la API de Figshare: Duke, James A. (2016). *Dr. Duke's Phytochemical and Ethnobotanical Databases*. Ag Data Commons. Dataset. <https://doi.org/10.15482/USDA.ADC/1239279>.
- La página [About de USDA](https://phytochem.nal.usda.gov/about) recomienda citar el recurso como 1992–2016. Ese rango pertenece a la recomendación de cita de USDA, no al texto de cita de la API del artículo; tampoco establece la cobertura temporal efectiva de este ZIP, que no fue determinada.

El identificador de planta de la fuente es `FNFNUM`; no se expande el acrónimo FNF, cuyo significado no se verificó, ni se presenta como identificador universal. El texto científico mantiene literalmente la forma archivada (`TAXON`); no se valida sinonimia vigente. Los nombres comunes de la fuente no se traducen.

## Límites de los datos

`FARMACY_NEW` es un registro fitoquímico/componente por planta y parte; no respalda por sí mismo eficacia o propiedad medicinal. Sus nombres de parte como `Essential Oil` tampoco crean una ficha de aceite ni permiten inferir aceites.

Cada uso procede de `ETHNOBOT` con `GENUS`, `SPECIES`, `TAXON`, `ACTIVITY`, `REFERENCE` y `ETHNO`. Las cadenas `ACTIVITY` y `LONGREF` se conservan como aparecen en el archivo (incluidos errores tipográficos presentes en la fuente; no se corrigen ni traducen). Son, como máximo, registros tradicionales atribuidos por esa base; no son consejo, dosis, recomendación ni evidencia clínica, y la cita genérica de USDA no los respalda como tales.

## Selector y criterio de curación

1. Leer `FNFTAX.csv` y localizar cada planta por `FNFNUM`. `TAXON`, `GENUS`, `SPECIES` y, cuando exista, `SUBSPECIES` se comparan como campos de identidad. El `TAXON` fuente da el nombre científico literal. No se sustituyen formas por nomenclatura actual.
2. Para cada `FNFNUM`, tomar los códigos `PPCO` asociados a ese número en `FARMACY_NEW.csv`; resolver cada código por `PPCO` en `PARTS.csv` y guardar el `PPNA` archivado. Se conserva la etiqueta fuente, sin traducirla. Esto solo documenta asociaciones fitoquímicas/partes del dataset.
3. `ETHNOBOT.csv` no tiene `FNFNUM`. Cruzar la identidad con `GENUS`, `SPECIES` **y `TAXON` exactos**; no usar coincidencia parcial, alias o solo nombre común. Guardar la fila individual seleccionada, en particular su `ACTIVITY`, `REFERENCE` y `ETHNO`.
4. Resolver `REFERENCE` en `REFERENCES.csv` mediante una única coincidencia de clave no vacía y `LONGREF` no vacío. Se requiere una resolución inequívoca. Excluir usos cuyo taxón no coincide exactamente, cuya fila es ambigua, o cuyo `REFERENCE` falta o no resuelve. No se altera la cita fuente una vez resuelta.

Que una planta no tenga usos elegibles con este cruce y criterio solo significa que no se encontraron filas `ETHNOBOT` que lo satisfagan; no significa que carezca de usos.

La normalización usada al leer y comparar celdas se limita a quitar espacios exteriores (`strip`/`trim`); no se cambia mayúsculas, puntuación, acentos, taxón, actividad ni texto bibliográfico. No se incorporan dosis.
