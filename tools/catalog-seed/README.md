# Herramientas de la semilla del catálogo

Estas herramientas, en Python, preparan offline la semilla del catálogo de plantas: descargan y verifican las fuentes de datos y, en los grupos de tareas siguientes, resuelven nombres, consolidan y validan los paquetes. Son solo para el desarrollador: no van en la imagen de Docker (`tools/` está excluido de `.dockerignore`) y el backend en ejecución no las usa. Véase `openspec/changes/consolidate-catalog-seed/`.

## Entorno

Se necesita Python 3.9 o superior. Los comandos y las pruebas que no leen `.xls` ni PDF usan solo la biblioteca estándar y funcionan con el `python3` del sistema. Las extracciones de EFSA (`xlrd`) y de los PDF de la EMA (`pdfminer.six`) necesitan las dependencias de `tools/catalog-seed/requirements.txt`, con versión fija, en un entorno virtual local ignorado por Git:

```sh
python3 -m venv tools/catalog-seed/.venv
tools/catalog-seed/.venv/bin/pip install -r tools/catalog-seed/requirements.txt
```

Con el entorno creado, esos comandos se ejecutan con `tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py ...` en lugar de `python3 -I ...`. Sin él, `extract --source efsa` y `extract --source ema_pdf` fallan con un mensaje que lo indica, y las pruebas que necesitan esas bibliotecas se omiten (`skipTest`). No se instala nada en el sistema.

## Estructura

- `cli.py`: punto de entrada de línea de comandos.
- `catalog_seed/`: paquete importable (`sources.py` valida `sources.json` y las listas de fuentes; `download.py` descarga, verifica y fija snapshots; `ema.py` lee y deduplica la EMA; `wiki.py` consulta Wikidata, Wikipedia y Commons con límite de peticiones y reanudación; `goals.py` lee el mapa y el catálogo de objetivos; `schema.py` es el validador mínimo de JSON Schema; `validate.py` valida un registro contra su paquete; `seed.py` calcula el plan de regeneración y sella el manifiesto; `workdb.py`, `usda_extract.py`, `tppt_extract.py`, `efsa_extract.py`, `ema_extract.py`, `pdf_sections.py` y `extract.py` extraen las fuentes al formato intermedio; `ema_pdf.py` descarga los PDF de la EMA; `safety.py` y `safety_report.py` aplican el mapa de seguridad; `cli.py` define los comandos).
- `sources.json`: registro de fuentes.
- `schema/record.schema.json`: esquema JSON del registro v1.
- `safety-map.json`: mapa de seguridad versionado (niveles por fuente y categoría).
- `requirements.txt`: dependencias opcionales con versión fija.
- `goals-map.json`: mapa de áreas terapéuticas de la EMA a objetivos y subáreas.
- `prompt/consolidate.md`: prompt versionado del consolidador (variante A).
- `tests/`: pruebas con `unittest`, sin red.

## Comandos

Se ejecutan desde la raíz del repositorio:

```sh
python3 -I tools/catalog-seed/cli.py download
python3 -I tools/catalog-seed/cli.py download --source usda
python3 -I tools/catalog-seed/cli.py download --offline
python3 -I tools/catalog-seed/cli.py download --force
python3 -I tools/catalog-seed/cli.py pin --source ema_json
python3 -I tools/catalog-seed/cli.py fetch --service wikidata --input data/work/nombres.txt
python3 -I tools/catalog-seed/cli.py ema-pdf --wait 7200
python3 -I tools/catalog-seed/cli.py ema-pdf --status
python3 -I tools/catalog-seed/cli.py extract
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py extract --source efsa --source ema_pdf
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py safety-report
python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants --bundles data/work/bundles
python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed
python3 -I tools/catalog-seed/cli.py seal --seed data/seed
```

- `download` descarga cada fuente con `enabled: true` a `data/.cache/<id>/<filename>`, comprueba tamaño y checksum y la deja en la caché solo si coinciden. Una fuente con `enabled: false` no se descarga ni se verifica.
- Si el archivo ya está en la caché e íntegro, no vuelve a descargarlo ni usa la red. Si está alterado, falla indicando la fuente; `--force` lo descarga de nuevo.
- `--offline` solo verifica la caché y nunca abre la red. Si el insumo falta o está alterado, termina con error e indica el paso de descarga necesario.
- `pin --source <id>` fija el snapshot de una fuente declarada con `size` y `checksum` en `null` (véase «Fijar un snapshot»).
- `fetch --service <wikidata|wikipedia_es|commons> --input <archivo>` consulta lo pendiente de esos servicios (véase «Wikidata, Wikipedia en español y Commons»).
- `ema-pdf` descarga las páginas y los PDF de la EMA (véase «PDF de la EMA»); `extract [--source <id>]` escribe las filas normalizadas de USDA, la EMA, TPPT y EFSA en `data/work/sources.db` (véase «Extracción y formato intermedio»); `safety-report` muestra la clasificación del mapa de seguridad sobre esas filas (véase «Mapa de seguridad»).
- `validate`, `plan` y `seal` trabajan con la semilla y los paquetes (véanse «Validador», «Plan de regeneración» y «Sellado y manifiesto»).
- `--source <id>` limita el comando a una fuente y se puede repetir.
- `--sources <ruta>` y `--cache-dir <ruta>` cambian el archivo de fuentes y la caché (útil en pruebas).

El código de los pasos posteriores debe obtener los insumos con `catalog_seed.download.require_verified`, que nunca usa datos sin verificar.

## Formato de `sources.json`

Un objeto con la lista `sources`. Cada fuente tiene estos campos comunes, todos obligatorios:

- `id`: identificador de la fuente; debe estar en la lista de admitidas.
- `version`: versión o snapshot fijo (con su fecha cuando la fuente cambia con el tiempo).
- `license`: licencia de los datos.
- `attribution`: atribución exigida por la licencia.
- `enabled`: `true` o `false`; una fuente desactivada no se descarga y permite retirarla por configuración.

Los archivos se declaran de una de dos formas, excluyentes. Fuente de un solo archivo: los campos `url`, `filename` (nombre en la caché, sin rutas), `size` (bytes) y `checksum` (objeto con `algorithm`, `md5` o `sha256`, y `value` en hexadecimal) van en la propia fuente. Fuente con varios archivos: una lista `files` donde cada elemento tiene esos mismos cuatro campos, con `filename` distinto. Los archivos se guardan en `data/.cache/<id>/<filename>` y se verifican todos; basta que uno falle para que falle la fuente.

`size` y `checksum` deben ser ambos valores o ambos `null`. `null` significa «snapshot sin fijar»: la fuente no se descarga con `download` hasta que `pin` registre ambos valores.

Ejemplo de un solo archivo (USDA):

```json
{
  "id": "usda",
  "version": "Ag Data Commons 24660351, v1 (Duke-Source-CSV.zip, file ID 43363335)",
  "url": "https://ndownloader.figshare.com/files/43363335",
  "filename": "Duke-Source-CSV.zip",
  "license": "CC0",
  "attribution": "Duke, James A. (2016). Dr. Duke's Phytochemical and Ethnobotanical Databases. Ag Data Commons. https://doi.org/10.15482/USDA.ADC/1239279",
  "size": 6033990,
  "checksum": {"algorithm": "md5", "value": "45ae44a0544586b8ac22a232beaac344"},
  "enabled": true
}
```

Ejemplo con varios archivos (EFSA, abreviado):

```json
{
  "id": "efsa",
  "version": "EFSA Compendium of Botanicals 2016 (Zenodo 996024, publicado 2016-07-05)",
  "license": "CC BY 4.0",
  "attribution": "EFSA (2016). EFSA's compendium of botanicals. Zenodo. https://doi.org/10.5281/zenodo.996024",
  "enabled": true,
  "files": [
    {"url": "https://zenodo.org/api/records/996024/files/BOTANIC.xls/content", "filename": "BOTANIC.xls", "size": 1297920, "checksum": {"algorithm": "md5", "value": "5f906c745071266a3726421db6a0deb0"}}
  ]
}
```

## Fuentes declaradas

| id | Contenido | Licencia | Tamaño (bytes) | Checksum |
| --- | --- | --- | --- | --- |
| `usda` | Dr. Duke, `Duke-Source-CSV.zip` | CC0 | 6.033.990 | md5 `45ae44a0544586b8ac22a232beaac344` |
| `wcvp` | WCVP v16, `wcvp.zip` (Kew SFTP) | CC BY 3.0 | 88.179.649 | sha256 `d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa` |
| `wfo` | WFO Plant List 2026-06, `_DwC_backbone_R.zip` (Zenodo 20782718) | CC0 | 121.660.019 | md5 `0e4486945cd9f7af548ca87eb9a870ed` (el que publica Zenodo) |
| `ema_json` | Hierbas de la EMA, snapshot con `meta.timestamp` 2026-10-20T18:00:54Z | citando a la EMA (términos no verificados) | 202.757 | sha256 `e2b19f2fe9114514d593940d77684d39ab9977d22cbccb8a54354db2c93eee17` |
| `ema_pdf` | PDF de las monografías y declaraciones públicas de la EMA: 205 archivos (fuente de varios archivos), registrados por `ema-pdf` | citando a la EMA (términos no verificados) | por archivo | sha256 por archivo, fijado en `sources.json` |
| `tppt` | Agroscope TPPT, `tppt-db.zip` (SQLite) | uso abierto citando la fuente (opendata.swiss) | 1.188.682 | sha256 `8c16c7c5f8032ddd20ebcbb06f35ed1d9fb94ee10a91bd1384cc504465a47b85` |
| `efsa` | Compendium of Botanicals 2016: `BOTANIC.xls` y `ENDPOINTSTUDY.xls` (Zenodo 996024) | CC BY 4.0 | 1.297.920 y 468.992 | md5 `5f906c745071266a3726421db6a0deb0` y `d0c10ece17f726470b34cf2fe6d313e6` (los de Zenodo) |

Los datos de WCVP, WFO, USDA y EFSA coinciden con los del piloto o con los checksums publicados por sus repositorios. Los checksums de la EMA y TPPT los registró `pin`, porque estas fuentes no publican uno.

## Fijar un snapshot

La EMA actualiza su JSON dos veces al día y TPPT no publica un checksum, así que su snapshot se fija al descargarlo por primera vez. Se declaran con `size` y `checksum` en `null` y se ejecuta:

```sh
python3 -I tools/catalog-seed/cli.py pin --source ema_json
```

`pin` descarga los archivos sin fijar, deja la copia en la caché, escribe `size` y `checksum` (sha256) en `sources.json` y, para la EMA, deja en `version` la fecha de fijación y el `meta.timestamp` del archivo. Desde entonces `download` y `download --offline` verifican ese snapshot y no descargan otro. Si la fuente ya está fijada, `pin` no hace nada. Para actualizar el snapshot hay que decidirlo: se ponen `size` y `checksum` en `null`, se borra el archivo de la caché y se vuelve a ejecutar `pin`; el cambio de checksum queda visible en Git.

## EMA

El JSON tiene `meta` (`total_records` y `timestamp`) y `data` con una fila por producto y por área o planta. `catalog_seed.ema.dedupe_records` deduplica por `herbal_medicine_url` al leer, sin modificar el archivo: las filas idénticas se descartan y las filas distintas con la misma URL se fusionan, uniendo con `;` los campos que difieren (`rows` conserva las originales). El snapshot tiene 251 filas y quedan 204 fichas, igual que `meta.total_records`. Hay 34 URLs repetidas; `.../hyperici-herba` es un combinado de *Hypericum perforatum* y *Cimicifuga racemosa* con dos filas distintas, que se fusionan en una ficha con «St. John's Wort;Black Cohosh».

## TPPT de Agroscope

- Archivos: el portal ofrece un ZIP con la base SQLite (`tppt-db.zip`, 1.188.682 bytes, contiene `tppt-db.db`) y un XLSX (`tppt-xls.xlsx`, unos 1,36 MB). Se descarga solo el ZIP de SQLite porque contiene las mismas tablas con tipos y claves, sin parsear un libro de Excel; el XLSX no se descarga ni se declara.
- Tablas relevantes: `Toxic_plant_species` (844 plantas; `Latin_plant_name`, `German_plant_name`, `English_plant_name`, `Plant_genus`, `Plant_family`, `Toxic_plant_part`, `Human_toxicity`, `Animal_toxicity`, `Swiss_frequency`), `Phytotoxins` (1.586 sustancias, con `PSM_class`), `Phytotoxin_toxic_plant_species_relationships` (6.268 relaciones planta-sustancia), `Toxicity_data` (318 dosis en animales de prueba), `Remarks` (372 comentarios por género) y `Bibliography` (288 referencias). El resto de tablas (`ECOSAR_data`, `EPISuite_data`, `ACDPercepta_data`, `ProTox_data`, `Aquatic_micropollution_potential_analysis`) y las vistas son datos de modelización ambiental que la semilla no usa.
- `Human_toxicity` es texto libre con 22 valores distintos (844 plantas): `toxic` 314, `weak toxic` 149, `strong toxic` 72, `toxic (unknown strength)` 50, `allergenic` 49, `very strong toxic` 43, `skin-irritating` 42, `nontoxic` 38, `phototoxic` 35, `carcinogenic` 11, `unknown` 10, `infested plants only` 10, `liver toxic` 5, `allergenic, skin-irritating` 5, `stimulating` 3, `estrogenic` 2, `very strong toxic (only wild growing plants)` 1, `toxic (only wild growing plants)` 1, `strong toxic (only wild growing plants)` 1, `estrogenic, skin-irritating` 1, `cytotoxic` 1 y `allergenic, phototoxic` 1.
- `Animal_toxicity` tiene 10 valores distintos: vacío 476, `toxic` 137, `weak toxic` 91, `strong toxic` 73, `very strong toxic` 51, `very strong toxic (cat)` 9, `toxic (horse)` 4, `strong toxic (horses)` 1, `strong toxic (dog)` 1 y `strong toxic (cow, pig)` 1.
- Consecuencia para las reglas: las categorías combinadas usan «, » (siete plantas con más de una) y varias llevan calificadores entre paréntesis (especie animal o «only wild growing plants»), así que las reglas de seguridad deben separar por «, » y comparar el prefijo antes del paréntesis, no el texto completo.
- Términos de uso: según opendata.swiss, el uso es abierto citando la fuente y el uso comercial requiere permiso. El proyecto es académico y usa TPPT con atribución a Agroscope. Si el enfoque cambia a comercial, hay que pedir permiso. No se verificaron más términos en el portal de Agroscope.

## EFSA

El Compendium of Botanicals de 2016 (Zenodo 996024, CC BY 4.0) son dos libros de Excel antiguos (`.xls`) de una sola hoja cada uno. Los md5 declarados son los que publica Zenodo y la descarga los verifica. Leerlos necesita `xlrd` (véase «Entorno»).

- `BOTANIC.xls` (3.449 filas, 863 cadenas `scientificNames` distintas): una fila por botánico y sustancia, con `scientificNames` (varios nombres separados por «;»), `PlantPart`, `Preparation`, `SubstanceName`, `expression_result`, `RESVAL`, `Unit`, `ResultType` y la cita (`CITATION`, `DOCTYPE`).
- `ENDPOINTSTUDY.xls` (972 filas, 332 cadenas `scientificNames`): una fila por estudio, con `STUDYCATEGORY` (salud humana o de animales de destino), `TESTSPECIES`, `ROUTE`, `TESTTYPE`, `ENDPOINT`, `TOXICITYSUMMARY` y `EFFECT_DESC`; 894 de las 972 filas no informan la dosis.
- El compendio reúne botánicos con sustancias de posible preocupación para la salud humana: sirve para la definición de la tarea 4.4 (véase «Mapa de seguridad»).

## PDF de la EMA

`ema-pdf` descarga lo que la tarea 3.3 necesita de la EMA con la misma mecánica de límite de peticiones y reanudación que `fetch`:

```sh
python3 -I tools/catalog-seed/cli.py ema-pdf --wait 7200
python3 -I tools/catalog-seed/cli.py ema-pdf --status
```

- Para cada ficha de `ema_json` (204, deduplicadas) guarda su página en `data/.cache/ema_pdf/pages/<slug>.html` y elige los documentos de esa página con `ema_pdf.select_documents`: la monografía de la UE final, sin `draft-`, `second-draft-`, `superseded-` ni `call-` (convocatorias de datos), y si hay varias de la misma ficha las de la revisión más alta; si no hay final, el borrador más avanzado; y la declaración pública final (un borrador de declaración, publicado a veces bajo `herbal-monograph/`, solo cuando la ficha no tiene nada más).
- Espera 15 s entre peticiones (`--delay`), respeta `Retry-After` y deja el estado en `data/.cache/ema_pdf/_state.json`; una respuesta 200 que no empieza por `%PDF-` (la página HTML de error de la EMA) se rechaza, no se cachea y se trata como un límite disfrazado (reintento tras 60 s). Un documento que falla 3 veces se deja de pedir y se lista en `failed`. Una segunda ejecución solo pide lo que falta.
- `--wait <segundos>` hace que, ante un límite de peticiones, el comando espere hasta ese total y siga; sin él, termina con código 2 y el estado listo para reanudar. `--status` solo cuenta lo descargado y lo pendiente, sin red.
- Los PDF quedan en `data/.cache/ema_pdf/<slug>__<tipo>__<nombre>.pdf` (tipo `monograph-final`, `monograph-draft` o `public-statement`; los nombres de más de 200 caracteres se acortan con un hash). Al terminar, el comando registra en `sources.json` (fuente `ema_pdf`, de varios archivos) la URL, el tamaño y el sha256 de cada PDF: ese es el mecanismo de `pin` de esta fuente, porque la lista de archivos solo se conoce tras leer las páginas. Una ejecución posterior verifica los ya registrados y falla si alguno cambió; retira de la lista los que la selección vigente ya no elige. `download --offline` verifica los 205 PDF; `download` no los descarga (indica usar `ema-pdf`).
- Estado de la descarga completa (20 de octubre de 2026): 204 páginas y 205 PDF descargados y registrados, 0 pendientes y 0 fallidos, en 410 peticiones (unas 1,8 horas con 15 s de espera). 177 fichas tienen monografía (178 documentos: 174 finales y 4 borradores; `epilobii-herba` tiene dos), 25 solo declaración pública y 2 no publican ninguna (`calendulae-herba`, que solo tiene una convocatoria de datos, y `valerianae-radix-passiflorae-herba`, una combinación).

## Extracción y formato intermedio

`extract` lee los insumos verificados (`download.require_verified`, nunca la red) y escribe las filas normalizadas en el SQLite `data/work/sources.db`, ignorado por Git:

```sh
python3 -I tools/catalog-seed/cli.py extract --source usda --source tppt --source ema_json
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py extract --source efsa --source ema_pdf
```

Tabla `source_row(source, record_type, row_key, raw_name_cell, fnfnum, qid, content_json)`, clave primaria `(source, record_type, row_key)`; el ref de un dato es `<record_type>:<row_key>`. `raw_name_cell` es la celda del nombre científico tal cual, sin normalizar (el resolvedor la normaliza); `fnfnum` solo lo llevan las filas de USDA que ya lo traen; `qid` queda reservado para Wikidata; `content_json` es JSON canónico (claves ordenadas). La tabla `extraction(source, version, rows, inputs_json)` anota con qué insumos se hicieron las filas. Extraer una fuente reemplaza todas sus filas, así que repetir el comando da lo mismo.

| source | record_type | row_key | raw_name_cell | Filas |
| --- | --- | --- | --- | --- |
| `usda` | `usda_taxon` | FNFNUM | TAXON | 2.376 |
| `usda` | `usda_common_name` | `<FNFNUM>-<n>` | CNNAM | 2.920 |
| `usda` | `usda_part` | `<FNFNUM>-<PPCO>` | TAXON de FNFTAX | 6.740 |
| `usda` | `usda_use` | ETHNO | TAXON de ETHNOBOT | 82.873 |
| `usda` | `usda_reference` | REFERENCE | REFERENCE | 2.043 |
| `ema_json` | `ema_herbal` | slug de la ficha | `botanical_name` | 204 |
| `ema_pdf` | `ema_pdf_doc` | slug | `botanical_name` | 204 |
| `ema_pdf` | `ema_pdf` | `<slug>:4.3`, `:4.4`, `:4.5` o `:CONCLUSIONS` | `botanical_name` | 561 |
| `tppt` | `tppt_plant` | Plant_number | Latin_plant_name | 844 |
| `efsa` | `efsa_botanic` | número de fila de la hoja | `scientificNames` | 3.449 |
| `efsa` | `efsa_endpoint` | número de fila de la hoja | `scientificNames` | 972 |

- USDA (parte de la 3.2): los CSV del ZIP se leen en Windows-1252 con comillas CSV estándar, como el adaptador Rust (que no se modifica); en este ZIP todos son ASCII. `usda_part` resume `FARMACY_NEW` por (FNFNUM, PPCO): `rows`, `distinct_compounds`, hasta 10 compuestos por cantidad (`top_amount`: mayor de las columnas `AMT_*` por compuesto, con su `QUANT_UNIT` si lo hay) y hasta 10 por EOPCT (`top_eo`); el compuesto `EO` y sus variantes (`EO (ASSUMED)`, `EO(ASS.)`) llevan `eo: true` y la parte `has_eo`. Las 13 filas de `FARMACY_NEW` sin PPCO se omiten (contadas en `farmacy_rows_empty_ppco`). `usda_use` guarda la REFERENCE corta tal como viene (11 filas no la tienen) y no lleva `longref`, porque el LONGREF propio de ETHNOBOT va siempre vacío. `usda_common_name` lleva un idioma heurístico (`und` si el nombre termina en una etiqueta entre paréntesis, si no `en`), el mismo que el adaptador Rust. **La asignación de usos a plantas y la selección de hasta 5 candidatas por clave quedan para el armado de paquetes** (3.2 y 3.5), porque necesitan el resolvedor; por eso la 3.2 no está marcada.
- EMA (JSON): `ema_herbal` guarda `therapeutic_areas` y `outcomes` ya separados por «;» (el resultado combinado `European Union herbal monograph;European Union list entry` queda en dos valores) y, en las fichas fusionadas, las filas originales con sus propias áreas.
- EMA (PDF): `pdf_sections.py` implementa el modo `pdfminer-cols` del spike. Cada fila `ema_pdf` guarda `columns` (`well_established_use`, `traditional_use`, `both_columns` o `single_column`), `text` (las columnas rotuladas), las páginas y el documento. Solo las monografías numeradas tienen 4.3, 4.4 y 4.5: se recuperaron las tres secciones en las 178 monografías (174 finales y 4 borradores, 100 %). En las declaraciones públicas se extrae `CONCLUSIONS` con `safety_data` falso y la nota «declaración pública sin datos de seguridad» cuando las conclusiones no mencionan contraindicaciones, advertencias, interacciones, toxicidad o seguridad (21 de 25; las otras 4, como kava y bálsamo del Perú, hablan de preocupaciones de seguridad). Se corrigieron respecto del spike: títulos partidos en el medio de una palabra por PDF fragmentados, números de sección sin punto («4.3 Contraindications») o solos en una línea (monografías de 2009), y cabeceras en mayúsculas. Residuos conocidos: en un PDF fragmentado (`quercus-cortex`) quedan palabras partidas («Inte rnal»), que pueden esconder un patrón de gravedad.
- TPPT: `tppt_plant` guarda la planta con `human_toxicity`, `animal_toxicity`, `n_toxins` y las toxinas elegidas: todas las de composición «major toxin» (también «major known toxin», «major toxin and aglycone» y «major toxin and metabolite») y hasta 15 más ordenadas por importancia de la composición. Cada toxina lleva `composition`, `major`, `psm_class`, `casrn` y sus dosis de `Toxicity_data` (enlazadas por `Phytotoxin_number`); la planta lleva el comentario de `Remarks` (por `Plant_genus`, quitando espacios) y las entradas de `Bibliography` citadas por esas dosis (por `Abbreviation`; el `Data_source` puede traer varias separadas por «, »; 70 citas, como `clinitox.ch`, no están en Bibliography). Se extrae el SQLite a un directorio temporal y se abre de solo lectura.
- EFSA: ver la sección anterior; cada fila guarda las columnas útiles con sus nombres, números enteros sin «.0» y `scientificNames` sin tocar en `raw_name_cell`.

Dependencia del armado de paquetes (3.5): la extracción de WCVP (taxonomía y distribución) de la 3.3 no está aquí, porque el resolvedor construye el índice de WCVP con la distribución (tarea 2.2); los paquetes la tomarán de él.

## Mapa de seguridad

`safety-map.json` (versión 1) fija el nivel mínimo (`bajo`, `medio`, `alto`) que cada fuente da a una planta; `catalog_seed/safety.py` lo aplica y `safety-report` clasifica con él las filas extraídas y lista las categorías sin cubrir. El nivel de un registro es el más alto entre las fuentes; una planta sin datos lleva `safety` nulo y un `reviewFlag`, y nunca se presenta como segura. Cada categoría presente en los datos tiene un nivel o `level: null` explícito con su motivo (`why`), y las pruebas lo comprueban con los datos reales.

TPPT (`Human_toxicity`, 22 valores; se separa por «, » y se compara el prefijo antes del paréntesis, en minúsculas):

| Categoría | Nivel | Motivo |
| --- | --- | --- |
| very strong toxic, strong toxic | alto | Mandato del diseño |
| carcinogenic, phototoxic | medio | Mandato del diseño |
| allergenic | bajo | Mandato del diseño |
| toxic (también «toxic (unknown strength)») | medio | Tóxica sin gradación, entre «weak toxic» y «strong toxic»; la fuerza desconocida no justifica bajarla |
| weak toxic | bajo | TPPT la califica de débil |
| skin-irritating | bajo | Irritación local y reversible, como «allergenic» |
| liver toxic | medio | Toxicidad de un órgano concreto, sistémica |
| cytotoxic | medio | Una sola planta; por precaución se trata como toxicidad de órgano |
| estrogenic | medio | Actividad hormonal, relevante en embarazo, lactancia y condiciones sensibles a hormonas |
| nontoxic | sin nivel | Ausencia de toxicidad conocida: no hace segura a la planta |
| unknown | sin nivel | Sin dato |
| infested plants only | sin nivel | El peligro es la contaminación, no la planta sana |
| stimulating | sin nivel | Efecto farmacológico, no toxicidad |

`Animal_toxicity` (9 valores, con calificadores de especie) queda toda sin nivel: no fija el nivel para personas y se conserva como dato. Los niveles de `toxic`, `weak toxic`, `skin-irritating`, `liver toxic`, `cytotoxic`, `estrogenic` y los cuatro sin nivel son propuestas de esta tarea (los otros cinco vienen del diseño) y están por aprobar.

EMA, sección 4.5 de la monografía (una clasificación por columna; la ficha toma la más grave). Una interacción es **grave** (alto) si el texto coincide con alguno de estos patrones, sin distinguir mayúsculas (`severe_patterns` del mapa): `contraindicated`; una prohibición expresa de combinar («not to be used concomitantly», «not to use concomitantly», «concomitant use … should be avoided»); `serotonin syndrome`; riesgo hemorrágico (aumento del efecto de anticoagulantes o antiagregantes, o «bleeding times»); interacción con warfarina (`interactions with warfarin`, `increased INR`, «potentiate … warfarin»); y `life-threatening`, `fatal` o `death`. Si no, el texto es `none-reported` («None reported», «None known», «Not known», «No clinically relevant interactions») o `no-studies` («No interaction studies have been performed», «No data available») cuando, sin los rótulos «Indication n)», es solo eso, y en otro caso `interactions` (interacciones concretas sin término de gravedad, como la absorción retrasada o la precaución con inhibidores de la MAO). Solo `severe` fija nivel; las demás clases (y las fichas sin documento, sin sección, o con solo declaración pública) quedan sin nivel. Resultado sobre las 204 fichas:

| Clase | Nivel | Fichas | Ejemplos |
| --- | --- | --- | --- |
| `severe` | alto | 10 | `hyperici-herba` y `hyperici-herba-0` (contraindicado con ciclosporina y anticoagulantes cumarínicos, síndrome serotoninérgico), `allii-sativi-bulbus` (contraindicado con saquinavir, tiempos de sangrado), `liquiritiae-radix` (no usar con diuréticos), `ginkgo-folium`, `salicis-cortex`, `sabalis-serrulatae-fructus` (warfarina), `vaccinii-macrocarpi-fructus` (warfarina), `species-digestivae`, `combination-species-pectorales` |
| `interactions` | ninguno | 22 | `matricariae-flos` (CYP450 tras trasplante renal), `lini-semen`, `psyllii-semen` (absorción retrasada), `sennae-folium` (hipopotasemia), `mate-folium` (inhibidores de la MAO), `fucus` (litio), `agni-casti-fructus` |
| `none-reported` | ninguno | 143 | `absinthii-herba`, `arnicae-flos`, `calendulae-flos`, `althaeae-radix` |
| `no-studies` | ninguno | 2 | `fragariae-folium`, `melissae-folium` |
| `statement-no-safety` | ninguno | 20 | `citri-bergamiae-aetheroleum`, `cannabis-flos`, `caryophylli-flos` |
| `statement-with-safety` | ninguno | 5 | `piperis-methystici-rhizoma`, `balsamum-peruvianum`, `chelidonii-herba`, `adhatodae-vasicae-folium`, `salviae-officinalis-aetheroleum` |
| `sin-documento` | ninguno | 2 | `calendulae-herba`, `valerianae-radix-passiflorae-herba` |
| `no-section`, `no-descargada` | ninguno | 0 | |

Límites de la regla: la clasificación es por texto, no clínica. Los laxantes antraquinónicos (`sennae-folium` y similares: la hipopotasemia potencia los glucósidos cardíacos) quedan en `interactions` porque el texto no usa un término de gravedad, aunque el regaliz, que advierte lo mismo, queda en `severe` por «not to be used concomitantly». Las cinco declaraciones públicas con `safety_data` hablan de preocupaciones de seguridad (hepatotoxicidad del kava, por ejemplo) que esta regla no convierte en nivel; queda como decisión del usuario si deben fijar un mínimo. Los textos de las clases `severe` y `interactions` van al paquete para que el consolidador cite la sección y su columna.

EFSA, definición de «sustancia de preocupación»: una planta la tiene si `BOTANIC.xls` la lista con al menos una fila con `SubstanceName` y con `ResultType` distinto de «Non Detected Value (<LOD)» (la sustancia no está). Fija un mínimo `medio` (la propuesta del diseño) y nunca `alto` por sí sola: EFSA no gradúa gravedad ni dosis. Los estudios de `ENDPOINTSTUDY.xls` son evidencia que va al paquete y no fijan nivel (cada grupo de efecto, categoría de estudio y tipo de resultado presente está en el mapa, con nivel o explícitamente sin él). Advertencia: el mínimo es amplio, porque las 863 cadenas `scientificNames` del compendio tienen al menos una sustancia contada (incluidas 1,8-cineol, alcanfor, tuyona, cumarina y taninos); por ejemplo, la lavanda (alcanfor, 1,8-cineol) quedaría con mínimo `medio`. Conviene que el usuario confirme si esa amplitud es la deseada o si debe restringirse a un subconjunto de sustancias.

## Wikidata, Wikipedia en español y Commons

`catalog_seed/wiki.py` descarga estos tres servicios con la misma mecánica. No son archivos de `sources.json`, porque sus respuestas dependen de la consulta; sus entradas vienen de un archivo de texto con una entrada por línea (vacías y líneas con `#` se ignoran) que generará el resolvedor taxonómico.

- Wikidata (`https://query.wikidata.org/sparql`): consulta SPARQL por lotes y por POST. Las entradas son nombres científicos (P225) o QIDs. Cada lote devuelve P225, nombres comunes en español (P1843 con idioma `es`), imágenes (P18), el sitelink de eswiki, GBIF (P846) y POWO/IPNI (P5037). P225 escribe los híbridos pegando el signo al epíteto (`Mentha ×piperita`), así que `Mentha × piperita` se normaliza a esa forma antes de consultar. En el piloto GET dio 429 con `Retry-After: 1000` y POST funcionó.
- Wikipedia en español (`https://es.wikipedia.org/api/rest_v1/page/summary/<título>`): una petición por título; un 404 se guarda como `{"missing": true}` para no volver a pedirlo.
- Commons (`https://commons.wikimedia.org/w/api.php`): `prop=imageinfo` con `iiprop=url|size|mime|extmetadata` por lotes de títulos; acepta nombres de archivo, `File:...` o las URL `Special:FilePath/...` que devuelve P18.
- `User-Agent`: `BoticarioAI-catalog-seed/0.1 (academic project)`, genérico y sin correo personal.
- Caché: un archivo JSON por entrada en `data/.cache/wikidata/`, `data/.cache/wikipedia_es/` y `data/.cache/commons/` (nombre con el texto de la entrada y un hash corto). Cada archivo guarda la clave, la fecha y la respuesta ya separada por entrada; una entrada sin resultado se guarda vacía y no se vuelve a consultar.
- Lotes: `--batch-size` (por defecto 20 en Wikidata y Commons, 1 en Wikipedia) y una pausa `--delay` de 1 s entre peticiones.
- Límite de peticiones: una respuesta 429 o 503 detiene el paso. Se respeta `Retry-After` (segundos o fecha HTTP); si falta, se espera 300 s. El paso escribe `_resume.json` en la carpeta del servicio con `retry_not_before` y la cantidad pendiente, conserva lo ya guardado y termina con código 2 y un mensaje con la hora de reintento. Mientras no pase esa hora, otra ejecución sale sin abrir la red. Al pasar, consulta solo las entradas sin archivo y borra el estado al completar. Otros errores HTTP detienen el paso con error y no guardan nada del lote.

## Pruebas de 1.4 y datos reales

Las pruebas de descarga usan un servidor HTTP local (`http.server` en un hilo), sin red externa. Una consulta real de humo con tres nombres (Mentha ×piperita, Arnica montana, Matricaria chamomilla), dos resúmenes de Wikipedia y dos imágenes de Commons confirmó el formato; esas respuestas quedan en la caché local, ignorada por Git.

## Esquema del registro

`schema/record.schema.json` es el esquema JSON (draft 2020-12) del registro v1 de una planta, y es la fuente única de la forma del registro: el validador de Python lo aplica y el lector de Rust usará tipos equivalentes con `deny_unknown_fields`. Declara su versión en la extensión `x-recordVersion` (hoy 1), que el registro copia en `recordVersion` y que `plan` y `seal` comparan.

Campos (todos obligatorios, sin campos adicionales en ningún nivel): `id`, `recordVersion`, `bundleHash`, `promptVersion` (entero), `model`, `aliases`, `scientificName` (`name`, `authors`, `refs`), `synonyms` (hasta 10), `family`, `displayName`, `commonNames`, `origin`, `description` (hasta 400 caracteres), `partsUsed` (hasta 5), `oil`, `traditionalUses` (hasta 20 grupos), `goals`, `safety` (un objeto con `level` alto, medio o bajo, o `null`), `image`, `sources`, `refs` (subconjunto del diccionario del paquete; cada entrada lleva `dataset`, `label`, `license` y, opcional, `url`) y `reviewFlags` (objetos `{code, target, message}`; una cadena suelta no es válida). No hay campo `basis`: la variante A solo usa el paquete.

Decisiones de forma que la spec deja abiertas:

- Un grupo de `traditionalUses` lleva `activity`, `activitySource`, `n`, `countries` (en español), `refs`, `pendingReview` y `citations`: una lista de `{key, ref, text}`, con la clave corta tal como viene de USDA, el ref `usda_reference:*` de la candidata elegida y su cita completa. Una clave sin candidata va como `{key, ref: null, text: "<clave> (sin resolver)"}`.
- `goals[]` lleva `goal`, `subarea` (nulo salvo en `otros-objetivos`), `area` (traducción del mapa), `evidence`, `pendingReview` y `refs`; los ids de `goal` y `subarea` son enumeraciones cerradas iguales a las de `data/seed/goals.json` (una prueba lo comprueba).
- Las entradas de `refs` pueden llevar `url` (enlace a la fuente, que el paquete trae cuando la fuente lo tiene). Es obligatoria para los refs de `wikipedia_es` con licencia CC BY-SA, porque la descripción resumida de Wikipedia registra su licencia y el enlace al artículo.
- Los códigos de `reviewFlags` van en minúsculas con guiones (por ejemplo `cita-sin-resolver`); el esquema no limita la lista de códigos. El `target` del flag de un objetivo es `goals.<goal>` y el de un grupo, `traditionalUses[<índice>]`.

`catalog_seed/schema.py` implementa a mano, sin `jsonschema`, el subconjunto usado: `type` (nombre o lista), `enum`, `const`, `properties`, `required`, `additionalProperties` (`false` o esquema), `propertyNames` (solo `pattern`), `items`, `minItems`, `maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`, `pattern`, `$ref` a `#/$defs/<nombre>` y `$defs`; ignora las anotaciones (`title`, `description`, `$comment`, `x-*`). Cargar un esquema con otra palabra clave falla, para que nadie confíe en una restricción que no se aplica.

## Mapa de objetivos y catálogo

- `goals-map.json`: para cada área terapéutica de la EMA (`areas`), la traducción al español (`es`), el objetivo (`goal`) y la subárea (`subarea`, solo en `otros-objetivos`). Incluye las 15 áreas del snapshot real, con las variantes «Urinary tract and gynaecology disorders», «Digestive disorder» y «Eye discomfort». Declara además `countedOutcomes` (`European Union herbal monograph` y `European Union list entry`), el separador `;` del campo y `emptyArea`: una ficha sin área (24 de las 204 del snapshot) no genera objetivos y está tratada de forma explícita.
- `data/seed/goals.json`: el catálogo de la semilla con los seis objetivos y las seis subáreas de `otros-objetivos` (`id`, `label` provisional en español y `position`; las subáreas llevan además `goalId`). Forma parte del `seedHash`.
- Las pruebas comprueban con el snapshot real de la EMA de la caché (se omiten con `skipTest` si no está) que cada área de las 204 fichas se asigna, que las cinco áreas con objetivo propio coinciden con la spec y que todo id del mapa existe en el catálogo.

## Prompt de consolidación

`prompt/consolidate.md` es el prompt autocontenido de la variante A. Su línea `prompt-version: <n>` es la versión que cada registro guarda en `promptVersion`; subirla hace que `plan` ponga todas las plantas en cola. Recibe el paquete, el esquema, el mapa de objetivos, el catálogo de objetivos y, cuando exista (tarea 4.4), el mapa de seguridad. Incorpora la política de solo el paquete y las correcciones del piloto: resultado combinado de la EMA separado por `;`, nombre científico propio en plantas separadas por colisión, nombres `und` claramente españoles con ref, `EO` como aceite esencial y no un aceite fijo, ningún objetivo para plantas tóxicas según TPPT, hipérico y similares con `pendingReview`, y emparejamiento de claves cortas de cita con las candidatas del paquete (con «(sin resolver)» y su `reviewFlag` cuando no hay candidata). Cada cambio de reglas sube la versión.

## Contrato del paquete que usa el validador

El paquete lo construye la tarea 3.5; el validador solo depende de esta parte de su contrato: `refs`, `bundleHash`, `identity.proposedId`, `sections.regulatory[]` (`ref`, `therapeuticAreas`, `outcome`, `combination`), `sections.safety[]` (`source`, `humanToxicity` para TPPT y `severeInteractions` para la EMA), `sections.images[].ref`, `sections.descriptions[].url` y `sections.uses[]` (`activity` y, por grupo, `citations` con las claves cortas y `candidates`: un objeto de clave a lista de `{ref, citation}`). La marca `severeInteractions` es provisional hasta que la tarea 4.4 defina el mapa de seguridad.

## Validador

`validate` comprueba cada archivo de `--records` (por defecto `data/seed/plants`) contra su paquete de `--bundles` (por defecto `data/work/bundles`, emparejado por `identity.proposedId`):

- el esquema (si falla, no se hacen las demás comprobaciones);
- que `id` es `identity.proposedId` y `bundleHash` el del paquete, y que el archivo se llama como el `id`;
- que todo ref citado existe en `refs` del paquete y en el subconjunto `refs` del registro, con el mismo dataset, etiqueta, licencia y `url`, y que todo ref de `wikipedia_es` con licencia CC BY-SA trae `url`;
- que cada objetivo tiene respaldo de la EMA (un ref de una ficha cuyo resultado, separado por `;`, incluye monografía o entrada de lista, que no es un producto combinado y cuya área, según el mapa, da ese objetivo y subárea), que `subarea` es nula salvo en `otros-objetivos`, y que no hay objetivos repetidos;
- que una planta con TPPT «strong toxic» o «very strong toxic» (valores separados por «, », prefijo antes del paréntesis) no tiene objetivos;
- que el objetivo `relajacion-estres` de una planta con interacciones graves en la EMA lleva `pendingReview` verdadero, y que todo objetivo con `pendingReview` tiene un `reviewFlag` cuyo `target` lo señala;
- que todo grupo con `pendingReview` tiene un `reviewFlag` con `target` `traditionalUses[<índice>]`, que todo grupo con una cita sin resolver es pendiente y tiene el flag `cita-sin-resolver`, que toda cita apunta a un `usda_reference:*` del paquete (y a una candidata de esa clave cuando el paquete las trae) o está marcada «(sin resolver)», y que `activitySource` es una actividad literal del paquete;
- que la imagen tiene licencia CC0, dominio público, CC BY o CC BY-SA (se rechazan NC y ND), `attributionRequired` verdadero para CC BY y CC BY-SA, y es una imagen del paquete.

Las expresiones de dosis o eficacia (`dosis`, `mg`, `ml`, `gotas`, `cucharada`, `cura`, `trata`, `tratamiento`, `previene`, `elimina`, `alivia`, `eficaz` y similares) en los textos visibles son advertencias, no errores. El comando imprime errores y advertencias por planta y un resumen, escribe el informe completo con `--out` y termina con código 1 si hay algún error.

## Plan de regeneración

`plan` recorre los paquetes de `--bundles` y lista las plantas que no tienen registro en `<seed>/plants/<id>.json` o cuyo registro tiene otro `bundleHash`, otra `promptVersion` (la de `prompt/consolidate.md`) u otra `recordVersion` (la del esquema), con los motivos (`sin-registro`, `bundleHash`, `promptVersion`, `recordVersion`). Con `--json` imprime el plan como JSON. Sin cambios, la lista está vacía; subir la versión del prompt las pone todas en cola; un cambio de una fuente que altere un solo paquete deja solo esa planta.

## Sellado y manifiesto

`seal` lee `<seed>/plants/*.json` y `<seed>/goals.json`, comprueba que cada registro cumple el esquema, que su archivo se llama como su `id` y que su `promptVersion` es la del prompt vigente (si no, hay que regenerar antes de sellar), y escribe `<seed>/manifest.json` con claves ordenadas, sangría de 2 espacios y salto de línea final, sin marcas de tiempo. Campos:

- `formatVersion`: versión del formato del manifiesto (1).
- `sources`: las fuentes con `enabled: true` de `sources.json`, con `id`, `version`, `license`, `attribution` y `files` (`filename`, `size`, `checksum`). Una fuente activa sin snapshot fijado hace fallar el sellado; una desactivada no se lista.
- `promptVersion` y `recordVersion`: las del prompt y el esquema vigentes.
- `models`: los modelos distintos de los registros, ordenados (puede haber más de uno si se regeneró por tandas).
- `plantCount`: número de plantas.
- `reviewFlags`: para cada `code`, cuántas plantas lo tienen.
- `seedHash`: `sha256:` más el sha256 de la concatenación UTF-8 de `plant\n<id>\n<JSON canónico del registro>\n` para cada registro ordenado por `id`, seguida de `goals\n<JSON canónico de goals.json>\n`. El JSON canónico tiene las claves ordenadas, separadores `,` y `:` sin espacios y caracteres sin escapar, así que no depende de la sangría de los archivos.

`seal` no reescribe los registros ni escribe la semilla real (tarea 6.1); las pruebas lo ejercitan sobre un directorio de semilla de fixtures.

## Extracción de seguridad de los PDF de la EMA (spike 3.1)

El spike de la tarea 3.1 (detalle en [`tools/catalog-seed/spikes/ema-pdf/README.md`](tools/catalog-seed/spikes/ema-pdf/README.md)) comprobó si se pueden extraer de los PDF de la EMA las secciones 4.3 (contraindicaciones), 4.4 (advertencias y precauciones) y 4.5 (interacciones), con su numeración y sin mezclar columnas.

- Se cumple el criterio de D9 en los 8 PDF de la muestra (7 monografías, entre ellas *Hyperici herba*, y 1 declaración pública) con `pdfminer.six`, leyendo las coordenadas de cada línea para separar la columna de uso bien establecido de la de uso tradicional.
- `pypdf` y `pdfminer.six` en texto plano no bastan: `pypdf` concatena las columnas sin etiquetarlas en las monografías con dos columnas con contenido (hipérico, menta, valeriana) y `pdfminer.six` entrelaza líneas en la sección 4.5 del hipérico.
- La declaración pública de *Citrus bergamia* no tiene secciones de seguridad: se registrará como «declaración pública sin datos de seguridad» y no se inventarán secciones vacías.
- La EMA limita las descargas: hay que esperar unos 15 segundos entre PDF, responde 429 con `Retry-After` y a veces entrega una página HTML de error en lugar del PDF, así que antes de cachear un archivo se comprueba que empiece por `%PDF-`.
- Herramienta recomendada para la tarea 3.3: `pdfminer.six` con `extract_pages()` y coordenadas (modo `pdfminer-cols` del spike), solo para el desarrollador. `pdftotext -layout` no se probó y no es necesario.

## Fuentes admitidas y descartadas

El verificador (`catalog_seed/sources.py`) rechaza cualquier fuente que no esté en la lista de admitidas.

- Admitidas: `usda`, `wcvp`, `wfo`, `ema_json`, `ema_pdf`, `tppt`, `efsa`, `wikidata`, `wikipedia_es` y `commons`.
- Descartadas (mensaje específico): AromaDb, EssOilDB, sCentInDB, FDA PPDB, Comisión E, OMS/WHO, NHPID, iNaturalist y DrugBank.

## Pruebas

Desde la raíz del repositorio, sin red:

```sh
python3 -I -m unittest discover -s tools/catalog-seed/tests -v
tools/catalog-seed/.venv/bin/python3 -I -m unittest discover -s tools/catalog-seed/tests -v
```

Con el `python3` del sistema se omiten (con `skipTest`) las pruebas que necesitan `xlrd` o `pdfminer.six` y las que necesitan los insumos reales en `data/.cache/`; con el entorno virtual corren todas. Los fixtures de la extracción están en `tests/fixtures/extract/` (dos `.xls` y dos PDF mínimos con sus scripts generadores).

Con `-I` Python no añade directorios a `sys.path`, así que `tests/support.py` calcula la ruta de `tools/catalog-seed/` y la agrega antes de importar el paquete; cada archivo de pruebas importa `support` primero.

## Archivos locales

`data/.cache/` (descargas verificadas) y `data/work/` (productos intermedios) están ignorados por Git y excluidos del contexto de Docker, igual que `tools/`. El entorno virtual `tools/catalog-seed/.venv` también está ignorado.
