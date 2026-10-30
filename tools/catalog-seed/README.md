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
- `catalog_seed/`: paquete importable (`sources.py` valida `sources.json` y las listas de fuentes; `download.py` descarga, verifica y fija snapshots; `ema.py` lee y deduplica la EMA; `wiki.py` consulta Wikidata, Wikipedia y Commons con límite de peticiones y reanudación; `goals.py` lee el mapa y el catálogo de objetivos; `schema.py` es el validador mínimo de JSON Schema; `validate.py` valida un registro contra su paquete; `seed.py` calcula el plan de regeneración y sella el manifiesto; `workdb.py`, `usda_extract.py`, `tppt_extract.py`, `efsa_extract.py`, `ema_extract.py`, `pdf_sections.py` y `extract.py` extraen las fuentes al formato intermedio; `ema_pdf.py` descarga los PDF de la EMA; `safety.py` y `safety_report.py` aplican el mapa de seguridad; `taxonomy/` es el resolvedor taxonómico (con `collisions.py`, los datos de la regla de colisiones), `resolve_universe.py` el comando `resolve`, `collisions_decide.py` el comando `collisions-decide`, `usda_assign.py` y `citations.py` la asignación de USDA y las citas candidatas, y `wiki_assign.py` y `wiki_fetch.py` la asignación y la descarga de Wikidata, Wikipedia y Commons; `bundles.py` arma los paquetes por planta y mide su tamaño; `cli.py` define los comandos).
- `sources.json`: registro de fuentes.
- `glossary-terms.json`: lista versionada de términos del glosario de actividades, con la fuente, la acepción o el artículo de cada uno, los excluidos y los patrones aprobados (véase «Glosario de actividades»).
- `schema/record.schema.json`: esquema JSON del registro v1.
- `schema/bundle.schema.json`: esquema JSON del paquete por planta v1 (véase «Paquetes por planta»).
- `safety-map.json`: mapa de seguridad versionado (niveles por fuente y categoría).
- `collision-decisions.json` y `collision-exceptions.json`: decisiones registradas y excepciones «separar siempre» de la regla de colisiones (véase «Regla de colisiones»).
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
python3 -I tools/catalog-seed/cli.py wiki-fetch --plan
python3 -I tools/catalog-seed/cli.py wiki-fetch --wait 7200
python3 -I tools/catalog-seed/cli.py wiki-assign
python3 -I tools/catalog-seed/cli.py ema-pdf --wait 7200
python3 -I tools/catalog-seed/cli.py ema-pdf --status
python3 -I tools/catalog-seed/cli.py extract
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py extract --source efsa --source ema_pdf
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py safety-report
python3 -I tools/catalog-seed/cli.py resolve
python3 -I tools/catalog-seed/cli.py collisions-decide
python3 -I tools/catalog-seed/cli.py bundles
python3 -I tools/catalog-seed/cli.py bundles --plants data/work/plantas.txt --out data/work/bundles
python3 -I tools/catalog-seed/cli.py bundle-sizes --top 10
python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants --bundles data/work/bundles
python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed
python3 -I tools/catalog-seed/cli.py seal --seed data/seed
python3 -I tools/catalog-seed/cli.py seal --seed data/seed --from data/work/control/v7/lote-1 --from data/work/control/v7/lote-2
```

- `download` descarga cada fuente con `enabled: true` a `data/.cache/<id>/<filename>`, comprueba tamaño y checksum y la deja en la caché solo si coinciden. Una fuente con `enabled: false` no se descarga ni se verifica.
- Si el archivo ya está en la caché e íntegro, no vuelve a descargarlo ni usa la red. Si está alterado, falla indicando la fuente; `--force` lo descarga de nuevo.
- `--offline` solo verifica la caché y nunca abre la red. Si el insumo falta o está alterado, termina con error e indica el paso de descarga necesario.
- `pin --source <id>` fija el snapshot de una fuente declarada con `size` y `checksum` en `null` (véase «Fijar un snapshot»).
- `fetch --service <wikidata|wikipedia_es|commons> --input <archivo>` consulta lo pendiente de esos servicios (véase «Wikidata, Wikipedia en español y Commons»).
- `wiki-fetch` descarga Wikidata (por nombre), los resúmenes de Wikipedia en español y los metadatos de Commons de las plantas del universo, y `wiki-assign` rehace sin red la asignación de esos ítems a las plantas (véase «Wikidata, Wikipedia en español y Commons»).
- `glossary-candidates`, `glossary-fetch`, `glossary-senses`, `glossary-review` y `glossary-build` arman el glosario de actividades (véase «Glosario de actividades»).
- `ema-pdf` descarga las páginas y los PDF de la EMA (véase «PDF de la EMA»); `extract [--source <id>]` escribe las filas normalizadas de USDA, la EMA, TPPT y EFSA en `data/work/sources.db` (véase «Extracción y formato intermedio»); `safety-report` muestra la clasificación del mapa de seguridad sobre esas filas (véase «Mapa de seguridad»).
- `resolve` resuelve los nombres de USDA y la EMA y escribe el universo en `data/work/universe/`; lee las decisiones de colisión y no abre la red (véase «Resolvedor taxonómico y universo»). `collisions-decide` es el único paso con red de la regla de colisiones: consulta Wikipedia solo para los grupos sin decisión y agrega las decisiones a `collision-decisions.json` (véase «Regla de colisiones»).
- `bundles` arma sin red los paquetes por planta en `data/work/bundles/` y `bundle-sizes` mide los de un directorio (véase «Paquetes por planta»).
- `validate`, `plan` y `seal` trabajan con la semilla y los paquetes (véanse «Validador», «Plan de regeneración» y «Sellado y manifiesto»); `seal --from <dir>` importa registros de un directorio de trabajo. El orden de todos los comandos está en «Tubería completa, en orden».
- `--source <id>` limita el comando a una fuente y se puede repetir.
- `--sources <ruta>` y `--cache-dir <ruta>` cambian el archivo de fuentes y la caché (útil en pruebas).

El código de los pasos posteriores debe obtener los insumos con `catalog_seed.download.require_verified`, que nunca usa datos sin verificar.

## Tubería completa, en orden

Todos los comandos se ejecutan desde la raíz del repositorio. «Red» indica si el comando abre conexiones. Las rutas por defecto son las de cada comando.

| Paso | Comando | Lee | Escribe | Red |
| --- | --- | --- | --- | --- |
| 1 | `python3 -I tools/catalog-seed/cli.py download` | `sources.json` | `data/.cache/<fuente>/` (con `--offline` solo verifica) | Sí (no con `--offline`) |
| 2 | `python3 -I tools/catalog-seed/cli.py ema-pdf --wait 7200` | caché de `ema_json` | `data/.cache/ema_pdf/` y los PDF registrados en `sources.json` | Sí (no con `--status`) |
| 3 | `tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py extract` | caché | `data/work/sources.db` | No |
| 4 | `python3 -I tools/catalog-seed/cli.py resolve` | `data/work/sources.db`, WCVP y WFO de la caché, `collision-decisions.json` y `collision-exceptions.json` | `data/work/taxonomy.db` y `data/work/universe/` | No |
| 5 | `python3 -I tools/catalog-seed/cli.py collisions-decide` | `data/work/sources.db`, `taxonomy.db` y los dos archivos de colisiones | agrega decisiones a `collision-decisions.json` (después se repite `resolve`) | Sí, solo para grupos sin decisión |
| 6 | `python3 -I tools/catalog-seed/cli.py wiki-fetch --wait 7200` | `universe.json` y `taxonomy.db` | caché de Wikidata, Wikipedia y Commons, y `data/work/wiki/` (`--plan` solo estima) | Sí (no con `--plan`) |
| 7 | `python3 -I tools/catalog-seed/cli.py wiki-assign` | caché de Wikidata, `universe.json` y `taxonomy.db` | `data/work/wiki/` | No |
| 8 | `python3 -I tools/catalog-seed/cli.py bundles` | `sources.db`, `taxonomy.db`, `universe/`, `wiki/` y la caché | `data/work/bundles/` | No |
| 9 | `python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed` | paquetes, `data/seed/plants/`, el prompt y el esquema | solo imprime las plantas a regenerar | No |
| 10 | consolidación (agentes de Claude Code o un script con la API, según la tarea 11.1) | un paquete, `prompt/consolidate.md`, `schema/record.schema.json` y los mapas | un registro por planta en un directorio de trabajo, por ejemplo `data/work/control/v7/lote-1/` | Sí, la del modelo; las herramientas no la abren |
| 11 | `python3 -I tools/catalog-seed/cli.py validate --records data/work/control/v7/lote-1 --bundles data/work/bundles` | registros y paquetes | solo imprime (y el informe con `--out`) | No |
| 12 | `python3 -I tools/catalog-seed/cli.py seal --seed data/seed --from data/work/control/v7/lote-1 --from data/work/control/v7/lote-2` | registros de trabajo, paquetes, `data/seed/goals.json`, `sources.json`, prompt y esquema | `data/seed/plants/<id>.json` y `data/seed/manifest.json` | No |

Notas del orden:

- `extract` de EFSA y de los PDF de la EMA necesita el entorno virtual (véase «Entorno»); el resto usa el `python3` del sistema.
- `wiki-fetch` y `wiki-assign` pueden ir antes o después de `collisions-decide`, pero ambos necesitan el universo de `resolve`. Si `collisions-decide` agrega decisiones, hay que repetir `resolve`, `wiki-assign` y `bundles`.
- `bundles` desactiva las fuentes con `enabled: false` (véase «Fuentes desactivadas»); cambiar `sources.json` cambia el `bundleHash` solo de las plantas afectadas.
- Después de sellar, `plan` debe dar «0 plantas a regenerar» y `validate --records data/seed/plants` cero errores.
- Recorrido ejecutable sin red sobre los fixtures de `tests/fixtures/validate/` (un directorio temporal `$T`, con un prompt de versión 1 porque los registros de los fixtures son de esa versión):

```sh
T=$(mktemp -d)
mkdir -p $T/bundles $T/work
cp tools/catalog-seed/tests/fixtures/validate/bundle_matricaria.json $T/bundles/matricaria-recutita.json
cp tools/catalog-seed/tests/fixtures/validate/bundle_hiperico.json $T/bundles/hypericum-perforatum.json
cp tools/catalog-seed/tests/fixtures/validate/record_matricaria.json $T/work/matricaria-chamomilla.json
cp tools/catalog-seed/tests/fixtures/validate/record_hiperico.json $T/work/hypericum-perforatum.json
printf '# Prompt\n\nprompt-version: 1\n' > $T/prompt.md
python3 -I tools/catalog-seed/cli.py plan --bundles $T/bundles --seed $T/seed --prompt $T/prompt.md
python3 -I tools/catalog-seed/cli.py seal --seed $T/seed --from $T/work --bundles $T/bundles --prompt $T/prompt.md
python3 -I tools/catalog-seed/cli.py plan --bundles $T/bundles --seed $T/seed --prompt $T/prompt.md
python3 -I tools/catalog-seed/cli.py validate --records $T/seed/plants --bundles $T/bundles
```

Salida esperada: «2 plantas a regenerar» (`sin-registro`), «manifest.json actualizado: 2 plantas, seedHash sha256:...», «0 plantas a regenerar» y «2 registros, 0 con errores, 0 errores, 0 advertencias».

## Formato de `sources.json`

Un objeto con la lista `sources`. Cada fuente tiene estos campos comunes, todos obligatorios:

- `id`: identificador de la fuente; debe estar en la lista de admitidas.
- `version`: versión o snapshot fijo (con su fecha cuando la fuente cambia con el tiempo).
- `license`: licencia de los datos.
- `attribution`: atribución exigida por la licencia.
- `enabled`: `true` o `false`; una fuente desactivada no se descarga y permite retirarla por configuración.

Las fuentes pueden llevar además `licenseUrl`, opcional: la URL de la licencia como texto `https` (por ejemplo, la de Creative Commons) o `null` si la fuente no tiene una licencia con una URL única (licencia por archivo o términos propios, como Commons, la EMA y TPPT). El validador rechaza cualquier otro valor; `seal` lo copia al manifiesto cuando la fuente lo declara, y `catalog-ingest build` lo guarda en `source.license_url`. Los valores de `sources.json` son las URL oficiales de Creative Commons: CC0 (`usda`, `wfo`, `wikidata`), CC BY 3.0 (`wcvp`), CC BY 4.0 (`efsa`) y CC BY-SA 4.0 (`wikipedia_es`).

Todas las fuentes llevan además `name` (nombre legible) y `pageUrl` (página del dataset, `http` o `https`; no es la `url` de descarga): el manifiesto los entrega como `name` y `url` para los créditos de la API. Los archivos se declaran de una de dos formas, excluyentes. Fuente de un solo archivo: los campos `url`, `filename` (nombre en la caché, sin rutas), `size` (bytes) y `checksum` (objeto con `algorithm`, `md5` o `sha256`, y `value` en hexadecimal) van en la propia fuente. Fuente con varios archivos: una lista `files` donde cada elemento tiene esos mismos cuatro campos, con `filename` distinto. Los archivos se guardan en `data/.cache/<id>/<filename>` y se verifican todos; basta que uno falle para que falle la fuente.

Tercera forma, para los servicios en línea (`wikidata`, `wikipedia_es` y `commons`): no hay archivo que verificar, porque la respuesta depende de la consulta. Se declaran con los campos comunes más `url` (el servicio que se consulta) y sin `filename`, `size`, `checksum` ni `files`; el validador rechaza esos campos en un servicio. Cada respuesta se guarda en `data/.cache/<id>/` con la fecha de la consulta, y `download` y `pin` los omiten (los descarga `wiki-fetch`). `enabled: false` apaga el servicio: ni se descarga ni se extrae. Wikipedia y Commons se descargan a partir de los ítems de Wikidata, así que sin `wikidata` activa también se omiten.

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
| `wikidata` | Wikidata Query Service, consulta por nombre (servicio en línea) | CC0 1.0 | no aplica | no aplica (cada respuesta se guarda con su fecha) |
| `wikipedia_es` | API REST de es.wikipedia.org, `page/summary` (servicio en línea) | CC BY-SA 4.0 | no aplica | no aplica (cada respuesta se guarda con su revisión y fecha) |
| `wiktionary_es` | API de MediaWiki de es.wiktionary.org, `action=parse`, solo para el glosario de actividades (servicio en línea) | CC BY-SA 4.0 | no aplica | no aplica (cada respuesta se guarda con su revisión y fecha) |
| `commons` | API de Wikimedia Commons, `imageinfo` con `extmetadata` (servicio en línea) | por archivo: CC0, dominio público, CC BY o CC BY-SA | no aplica | no aplica |

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
| `wikidata` | `wikidata` | QID | P225 | 4.319 |
| `wikipedia_es` | `wikipedia_es` | título canónico del artículo | título | 1.412 |
| `commons` | `commons` | `File:...` | `File:...` | 2.634 |

- USDA (parte de la 3.2): los CSV del ZIP se leen en Windows-1252 con comillas CSV estándar, como el adaptador Rust (que no se modifica); en este ZIP todos son ASCII. `usda_part` resume `FARMACY_NEW` por (FNFNUM, PPCO): `rows`, `distinct_compounds`, hasta 10 compuestos por cantidad (`top_amount`: mayor de las columnas `AMT_*` por compuesto, con su `QUANT_UNIT` si lo hay) y hasta 10 por EOPCT (`top_eo`); el compuesto `EO` y sus variantes (`EO (ASSUMED)`, `EO(ASS.)`) llevan `eo: true` y la parte `has_eo`. Las 13 filas de `FARMACY_NEW` sin PPCO se omiten (contadas en `farmacy_rows_empty_ppco`). `usda_use` guarda la REFERENCE corta tal como viene (11 filas no la tienen) y no lleva `longref`, porque el LONGREF propio de ETHNOBOT va siempre vacío. `usda_common_name` lleva un idioma heurístico (`und` si el nombre termina en una etiqueta entre paréntesis, si no `en`), el mismo que el adaptador Rust. Los datos de la fuente traen desplazadas algunas filas de `ETHNOBOT` (por ejemplo, 7 de *Averrhoa carambola*, como la 2254: `CNAME` = «L.» y `COUNTRY` = «Kembang bua», con `REFERENCE` = «Malaya»): no es un error de lectura, porque el CSV tiene 19 campos en las 82.873 filas y las comillas y comas se leen bien, sino que así vienen en el CSV de Duke (la columna del autor del nombre llena `CNAME`, el nombre común queda en `COUNTRY` y el país en `REFERENCE`). Se conservan tal cual; los agentes de generación deben desconfiar del país y de la cita de esas filas. La asignación de los usos a plantas y la selección de hasta 5 candidatas por clave necesitan el resolvedor y están en `usda_assign.py` y `citations.py` (véase «Asignación de USDA y citas candidatas»).
- EMA (JSON): `ema_herbal` guarda `therapeutic_areas` y `outcomes` ya separados por «;» (el resultado combinado `European Union herbal monograph;European Union list entry` queda en dos valores) y, en las fichas fusionadas, las filas originales con sus propias áreas.
- EMA (PDF): `pdf_sections.py` implementa el modo `pdfminer-cols` del spike. Cada fila `ema_pdf` guarda `columns` (`well_established_use`, `traditional_use`, `both_columns` o `single_column`), `text` (las columnas rotuladas), las páginas y el documento. Solo las monografías numeradas tienen 4.3, 4.4 y 4.5: se recuperaron las tres secciones en las 178 monografías (174 finales y 4 borradores, 100 %). En las declaraciones públicas se extrae `CONCLUSIONS` con `safety_data` falso y la nota «declaración pública sin datos de seguridad» cuando las conclusiones no mencionan contraindicaciones, advertencias, interacciones, toxicidad o seguridad (21 de 25; las otras 4, como kava y bálsamo del Perú, hablan de preocupaciones de seguridad). Se corrigieron respecto del spike: títulos partidos en el medio de una palabra por PDF fragmentados, números de sección sin punto («4.3 Contraindications») o solos en una línea (monografías de 2009), y cabeceras en mayúsculas. Residuos conocidos: en un PDF fragmentado (`quercus-cortex`) quedan palabras partidas («Inte rnal»), que pueden esconder un patrón de gravedad.
- TPPT: `tppt_plant` guarda la planta con `human_toxicity`, `animal_toxicity`, `n_toxins` y las toxinas elegidas: todas las de composición «major toxin» (también «major known toxin», «major toxin and aglycone» y «major toxin and metabolite») y hasta 15 más ordenadas por importancia de la composición. Cada toxina lleva `composition`, `major`, `psm_class`, `casrn` y sus dosis de `Toxicity_data` (enlazadas por `Phytotoxin_number`); la planta lleva el comentario de `Remarks` (por `Plant_genus`, quitando espacios) y las entradas de `Bibliography` citadas por esas dosis (por `Abbreviation`; el `Data_source` puede traer varias separadas por «, »; 70 citas, como `clinitox.ch`, no están en Bibliography). Se extrae el SQLite a un directorio temporal y se abre de solo lectura.
- EFSA: ver la sección anterior; cada fila guarda las columnas útiles con sus nombres, números enteros sin «.0» y `scientificNames` sin tocar en `raw_name_cell`.

La extracción de WCVP (taxonomía y distribución) de la 3.3 no está aquí, porque el resolvedor construye el índice de WCVP con la distribución (tarea 2.2); los paquetes la toman de él (`Backbone.distribution`).

## Mapa de seguridad

`safety-map.json` (versión 3) fija el nivel mínimo (`bajo`, `medio`, `alto`) que cada fuente da a una planta; `catalog_seed/safety.py` lo aplica y `safety-report` clasifica con él las filas extraídas y lista las categorías sin cubrir. El nivel de un registro es el más alto entre las fuentes; una planta sin datos lleva `safety` nulo y un `reviewFlag`, y nunca se presenta como segura. Cada categoría presente en los datos tiene un nivel o `level: null` explícito con su motivo (`why`), y las pruebas lo comprueban con los datos reales. La versión 2 aplica las decisiones del usuario: niveles de TPPT aprobados, las declaraciones públicas de la EMA con datos de seguridad en `medio` y EFSA limitada a una lista versionada de sustancias de alta preocupación. La versión 3 agrega la sección `usda`: las señales de riesgo de los usos de USDA (las mismas 23 de `sensitive-activities.json`, comparadas por su forma base) con su nivel y su motivo; las letales (`Fatality`, `Fatal`, `Death`, `Suicide`, `Homicide`, la errata `Homocide` e `Infanticide`) fijan `alto` por decisión del usuario (2026-10-26) y las demás (`Poison`, `Abortifacient`, `Carcinogenic`, ...) siguen sin nivel (`level: null`). Una prueba comprueba que ambas listas tienen los mismos términos.

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

`Animal_toxicity` (9 valores, con calificadores de especie) queda toda sin nivel: no fija el nivel para personas y se conserva como dato. Los niveles de la tabla están aprobados por el usuario (versión 2): cinco vienen del mandato del diseño y el resto (`toxic`, `weak toxic`, `skin-irritating`, `liver toxic`, `cytotoxic`, `estrogenic` y los cuatro sin nivel) los aprobó el usuario tras la propuesta de esta tarea. El motivo de cada categoría está en su campo `why`.

EMA, sección 4.5 de la monografía (una clasificación por columna; la ficha toma la más grave). Una interacción es **grave** (alto) si el texto coincide con alguno de estos patrones, sin distinguir mayúsculas (`severe_patterns` del mapa): `contraindicated`; una prohibición expresa de combinar («not to be used concomitantly», «not to use concomitantly», «concomitant use … should be avoided»); `serotonin syndrome`; riesgo hemorrágico (aumento del efecto de anticoagulantes o antiagregantes, o «bleeding times»); interacción con warfarina (`interactions with warfarin`, `increased INR`, «potentiate … warfarin»); y `life-threatening`, `fatal` o `death`. Si no, el texto es `none-reported` («None reported», «None known», «Not known», «No clinically relevant interactions») o `no-studies` («No interaction studies have been performed», «No data available») cuando, sin los rótulos «Indication n)», es solo eso, y en otro caso `interactions` (interacciones concretas sin término de gravedad, como la absorción retrasada o la precaución con inhibidores de la MAO). `severe` fija `alto` y `statement-with-safety` fija `medio`; las demás clases (y las fichas sin documento o sin sección, o con una declaración pública sin datos de seguridad) quedan sin nivel. Resultado sobre las 204 fichas:

| Clase | Nivel | Fichas | Ejemplos |
| --- | --- | --- | --- |
| `severe` | alto | 10 | `hyperici-herba` y `hyperici-herba-0` (contraindicado con ciclosporina y anticoagulantes cumarínicos, síndrome serotoninérgico), `allii-sativi-bulbus` (contraindicado con saquinavir, tiempos de sangrado), `liquiritiae-radix` (no usar con diuréticos), `ginkgo-folium`, `salicis-cortex`, `sabalis-serrulatae-fructus` (warfarina), `vaccinii-macrocarpi-fructus` (warfarina), `species-digestivae`, `combination-species-pectorales` |
| `interactions` | ninguno | 22 | `matricariae-flos` (CYP450 tras trasplante renal), `lini-semen`, `psyllii-semen` (absorción retrasada), `sennae-folium` (hipopotasemia), `mate-folium` (inhibidores de la MAO), `fucus` (litio), `agni-casti-fructus` |
| `none-reported` | ninguno | 143 | `absinthii-herba`, `arnicae-flos`, `calendulae-flos`, `althaeae-radix` |
| `no-studies` | ninguno | 2 | `fragariae-folium`, `melissae-folium` |
| `statement-no-safety` | ninguno | 20 | `citri-bergamiae-aetheroleum`, `cannabis-flos`, `caryophylli-flos` |
| `statement-with-safety` | medio | 5 | `piperis-methystici-rhizoma`, `balsamum-peruvianum`, `chelidonii-herba`, `adhatodae-vasicae-folium`, `salviae-officinalis-aetheroleum` |
| `sin-documento` | ninguno | 2 | `calendulae-herba`, `valerianae-radix-passiflorae-herba` |
| `no-section`, `no-descargada` | ninguno | 0 | |

Límites de la regla: la clasificación es por texto, no clínica. Los laxantes antraquinónicos (`sennae-folium` y similares: la hipopotasemia potencia los glucósidos cardíacos) quedan en `interactions` porque el texto no usa un término de gravedad, aunque el regaliz, que advierte lo mismo, queda en `severe` por «not to be used concomitantly». Las cinco declaraciones públicas con datos de seguridad (kava, bálsamo del Perú, celidonia, adhatoda y aceite de salvia; por ejemplo, la hepatotoxicidad del kava) no traen sección 4.5 pero documentan un problema de seguridad: por decisión del usuario fijan `medio`, y su texto va al paquete. Los textos de las clases `severe` y `interactions` van al paquete para que el consolidador cite la sección y su columna.

EFSA, lista versionada de alta preocupación (`efsa.concern_list`, versión 1): una planta tiene una sustancia de preocupación si `BOTANIC.xls` la lista con al menos una fila cuyo `SubstanceName` está en la lista y cuyo `ResultType` no es «Non Detected Value (<LOD)» (la sustancia no está). Fija un mínimo `medio` y nunca `alto` por sí sola: EFSA no gradúa gravedad ni dosis, así que `alto` queda para TPPT y las interacciones graves de la EMA. La lista tiene 134 sustancias en 4 grupos, cada una con el nombre exacto del compendio (la comparación ignora mayúsculas y espacios repetidos o duros, pero no cambia prefijos estereoquímicos ni plurales, así que cada variante figura por separado):

| Grupo | Sustancias | Qué reúne |
| --- | --- | --- |
| `veneno-potente` | 82 | Glucósidos cardíacos, alcaloides tropánicos, aconitina, ricina, abrina, taxina, cucurbitacinas y otros venenos potentes |
| `genotoxico-carcinogeno` | 23 | Estragol, metileugenol, safrol, isosafrol, asarona y beta-asarona, ácidos aristolóquicos, alcaloides pirrolizidínicos y ptaquilósido |
| `furocumarina-fototoxica` | 22 | Psoralenos lineales y angulares |
| `toxico-con-limite` | 7 | Tuyona (alfa y beta), pulegona, mentofurano y cumarina |

El resto de las sustancias del compendio es evidencia que va al paquete y no fija nivel. El mapa lo declara en `efsa.evidence_only`: grupos de sustancias fuera de la lista con su motivo (terpenos y aceites esenciales comunes como 1,8-cineol y alcanfor, taninos, oxalatos, lectinas, saponinas y metilxantinas, fenilpropanoides de especias, antraquinonas), y los que están marcados como candidatos (`candidate: true`: glucósidos cianogénicos, emodina, elemicina y miristicina, alcaloides pirrolizidínicos de necina saturada y diterpenos tipo grayanotoxina) que quedan fuera por ahora y se pueden evaluar para sumarlos a la lista. Los estudios de `ENDPOINTSTUDY.xls` también son evidencia y no fijan nivel (cada grupo de efecto, categoría de estudio y tipo de resultado presente está en el mapa, con nivel o explícitamente sin él). Resultado con los datos reales (`safety-report`): de las 863 cadenas `scientificNames` del compendio, 272 tienen una sustancia de la lista (nivel `medio`) y 591 solo evidencia; por grupo, `genotoxico-carcinogeno` activa 116 plantas, `veneno-potente` 81, `toxico-con-limite` 59 y `furocumarina-fototoxica` 28 (una planta puede estar en varios), las 134 sustancias figuran en el compendio, y las que más activan son metileugenol (48), estragol (37), alfa y beta tuyona (31 cada una) y bergapteno (16).

## Wikidata, Wikipedia en español y Commons

Tarea 3.4. Tres servicios en línea declarados en `sources.json` (`wikidata`, `wikipedia_es` y `commons`, con licencia, atribución y `enabled`; véase «Formato de `sources.json`»). La mecánica de descarga está en `catalog_seed/wiki.py`, el flujo en `wiki_fetch.py`, la asignación a plantas en `wiki_assign.py`, la extracción en `wiki_extract.py` y la clasificación de licencias en `licenses.py`.

### Descarga

```sh
python3 -I tools/catalog-seed/cli.py wiki-fetch --plan
python3 -I tools/catalog-seed/cli.py wiki-fetch --wait 7200
python3 -I tools/catalog-seed/cli.py wiki-assign
python3 -I tools/catalog-seed/cli.py extract --source wikidata --source wikipedia_es --source commons
python3 -I tools/catalog-seed/cli.py fetch --service wikidata --input data/work/nombres.txt
```

- `wiki-fetch` necesita `data/work/universe/universe.json` y `data/work/taxonomy.db` (los escribe `resolve`). `--plan` cuenta nombres y peticiones y estima el tiempo sin abrir la red. Sin `--plan` hace tres pasos y termina escribiendo la asignación: (1) Wikidata para todos los nombres, (2) el resumen de Wikipedia de los artículos enlazados por los ítems que pasan el filtro de homónimos y (3) los metadatos de Commons de las imágenes P18 de esos mismos ítems. Los pasos 2 y 3 se calculan desde la caché de Wikidata, así que no descargan nada de un homónimo.
- Es reanudable. Cada respuesta es un archivo de `data/.cache/<servicio>/` y una segunda ejecución solo pide lo que falta. Un 429 o 503 detiene el paso y deja `_resume.json` con la hora mínima de reintento (respeta `Retry-After`); `--wait <segundos>` espera esa hora, hasta el total indicado, y sigue. Si el total no alcanza, el comando termina con código 2 y el mensaje con la hora de reintento: se vuelve a lanzar el mismo comando.
- Descarga por nombre, no por planta, para que valga aunque cambie la regla de colisiones. Los nombres son, por cada planta con aceptado: su nombre, los de sus entradas, el aceptado de WCVP y sus sinónimos homotípicos (`Synonym` con `homotypic_synonym` verdadero, solo en WCVP y en plantas `resolved`). Las plantas sin aceptado se consultan por su nombre propio (véase «Regla de asignación a plantas»): las sin resolver (`unresolved`, `unmatched`) por su nombre y los de sus entradas, y las de solo género (`genus_only`) por su género; las ambiguas (`ambiguous`) no se consultan. Se suman dos nombres de control, *Lavandula latifolia* y *Passiflora edulis*, los homónimos del piloto, para comprobar el filtro con datos reales. El híbrido se normaliza a la forma de P225 (`Mentha ×piperita`).
- Wikidata (`https://query.wikidata.org/sparql`): SPARQL por POST, 40 nombres por petición (`--batch-size` en `fetch`, hasta 100). Por ítem devuelve QID, P225 con su autor (P405 y la abreviatura P428, si existe), su rango taxonómico (P105, como QID; las respuestas en la caché anteriores a esta regla no lo traen), etiqueta y alias en español, nombres comunes en español (P1843 con idioma `es`), imágenes P18, el sitelink de eswiki y los identificadores GBIF (P846), POWO (P5037) e IPNI (P961). En el piloto GET dio 429 con `Retry-After: 1000` y POST funcionó.
- Wikipedia en español (`https://es.wikipedia.org/api/rest_v1/page/summary/<título>`): una petición por título; un 404 se guarda como `{"missing": true}`.
- Commons (`https://commons.wikimedia.org/w/api.php`): `prop=imageinfo` con `iiprop=url|size|mime|extmetadata`, 50 títulos por petición; acepta `File:...` o las URL `Special:FilePath/...` que devuelve P18.
- `User-Agent`: `BoticarioAI-catalog-seed/0.1 (academic project)`, genérico y sin correo ni datos personales.
- Fuente desactivada (`enabled: false`): ni se descarga ni se extrae. Con `wikidata` desactivada tampoco se descargan ni se extraen Wikipedia y Commons, porque dependen de sus ítems. `fetch` (la entrada manual por archivo) también omite un servicio desactivado. Los paquetes omiten las filas y los refs de una fuente desactivada (véase «Paquetes por planta»).

### Regla de asignación a plantas

`wiki-assign` (y el final de `wiki-fetch`) recalcula la asignación solo desde la caché y `universe.json`, en unos 2 segundos, y escribe `data/work/wiki/assignment.json`, `report.json` y `report.md`. El comando `bundles` no lee ese archivo: recalcula la asignación con las mismas funciones desde la caché y las fuentes activas del momento, para que el paquete no dependa de un archivo viejo.

- Filtro de homónimos (spec): un ítem de Wikidata solo entra en una planta si su nombre (P225) resuelve, con `resolve_name` y el autor de Wikidata como desempate, al aceptado de esa planta. Un ítem cuyo nombre resuelve a otro aceptado no entra: *Lavandula latifolia* no llega a la lavanda ni *Passiflora edulis* a la pasiflora.
- Un ítem queda sin asignar, con su motivo: `sin-nombre`, `sin-resolver`, `ambiguo` (homónimo que el resolvedor no resuelve), `rango-inferior-sin-coincidencia` (el nombre infraespecífico solo coincidió por su binomio), `fuera-del-universo` (el aceptado no es de ninguna planta) o `heterotipico-sin-planta`.
- Grupo de una sola planta: el ítem va a esa planta (`grupo-unico`). Grupo partido (varias plantas con el mismo aceptado): a la planta con el mismo nombre (`misma-clave`); si el nombre es el propio aceptado o un sinónimo homotípico, a la planta que contiene al aceptado (`aceptado` u `homotipico`); un sinónimo heterotípico fusionado por la regla de colisiones va a la planta del aceptado en la que se fusionó (`heterotipico-fusionado`, por los `fusedMatchedIds` de la planta en `universe.json`), y uno sin planta propia ni fusión queda sin asignar (`heterotipico-sin-planta`) y no se le da al aceptado. Si la regla de colisiones cambia, basta volver a ejecutar `resolve` y `wiki-assign`: solo hay que descargar los nombres nuevos que el cambio introduce (por ejemplo, el aceptado de un grupo que antes no tenía planta propia).
- Plantas sin aceptado, por el nombre propio (regla conservadora, solo para ellas; las que tienen aceptado no cambian). Un ítem que el filtro deja en `sin-resolver` entra en una planta solo si su P225, normalizado como lo hace el resolvedor, es exactamente el nombre de la planta o el de una de sus entradas, ninguna otra planta pide ese nombre y ningún otro ítem de la caché tiene el mismo P225 (si hay dos o más, son homónimos y no entra ninguno). Para las de solo género el nombre es el género ("Aloe spp." da "Aloe") y el ítem debe declarar el rango género (P105 = Q34740); un ítem sin rango en la caché o con otro rango queda fuera. Se incluyeron las de solo género porque el rango viaja en la misma consulta (un `OPTIONAL` más) y no cuesta peticiones extra. Las ambiguas no se consultan: asignar por nombre podría traer datos de otra especie. El ítem asignado así lleva `match: "nombre-propio"` en el paquete; no hay códigos de `reviewFlags` nuevos ni cambia el prompt (sigue en la versión 7), y los flags de identidad de esas plantas (`sin-resolucion`, `solo-genero`, etc.) se conservan.
- Wikipedia y Commons se asignan por el ítem que las enlaza (sitelink de eswiki y P18). Un artículo cuyo tipo no es `standard` (por ejemplo una desambiguación) no cuenta como resumen.
- Estado de Wikidata por planta: `con-item`, `sin-item` (Wikidata respondió pero ningún ítem pasa el filtro), `sin-respuesta` (ninguna de sus consultas está en la caché, o Wikidata está desactivada) y `no-consultada` (solo las ambiguas, que no tienen nombre propio que consultar; las sin resolver y las de solo género se consultan por su nombre propio y quedan en `con-item` o `sin-item`). El paquete declara el estado en su sección `wikidata` y en `identity.flags` (`wikidata-sin-respuesta`, `wikidata-sin-item` y `wikidata-no-consultada`).
- Evidencia adicional: los identificadores IPNI (P961) y POWO (P5037) se contrastan con los `ipni_id` de WCVP del aceptado y sus sinónimos: `coincide`, `discrepa` o `sin-dato`. No reemplaza el filtro; las discrepancias quedan en el informe para revisión (casi todas son ítems de una subespecie o variedad cuyo ID es el de ese rango).
- `assignment.json` (`catalog-wiki-assignment/1`): `items` (por QID: `plantId`, `reason`, nombre y aceptado resueltos, `flags` del resolvedor, `requestedFor`, `homonym`, `ipni`, `eswiki`) y `plants` (por ID: estado de Wikidata, QIDs, nombres comunes en español de P1843, artículos de Wikipedia e imágenes de Commons admitidas y descartadas con su motivo), más los pendientes de descarga.

### Filas en `sources.db`

`extract --source wikidata|wikipedia_es|commons` lee solo la caché y escribe una fila por elemento, con el ref `<record_type>:<row_key>`:

- `wikidata:<QID>`: `qid`, `taxon` (P225, también en `raw_name_cell`), `authors`, `labelEs`, `aliasesEs`, `spanishNames` (P1843), `images` (títulos `File:...`), `eswiki`, `gbif`, `ipni`, `powo` y `queried` (nombres con los que se encontró). Incluye todos los ítems de la caché, también los que el filtro no asigna a ninguna planta; la asignación dice cuáles usar. La columna `qid` guarda el QID.
- `wikipedia_es:<título>`: `title` (canónico), `displayTitle`, `description`, `extract`, `url` (la del artículo, para el ref del paquete), `revision`, `timestamp`, `lang` y `wikibaseItem`. Solo artículos de tipo `standard` enlazados por algún ítem.
- `commons:<File:...>`: solo imágenes con licencia admitida y formato mostrable, con `title`, `pageUrl`, `fileUrl`, `author` (el `Artist` sin HTML y limpio, o el `Credit` si falta; véase «Autor de la imagen»), `license`, `licenseCode`, `licenseUrl`, `attributionRequired`, `mime`, `width` y `height`. Las descartadas se cuentan en la salida del comando y salen en el informe.

### Licencias

- Wikipedia es CC BY-SA 4.0; su resumen se guarda con título, URL del artículo, revisión y fecha. Wikidata es CC0. Commons se decide por archivo.
- Admitidas (cualquier versión y variantes portadas): CC0, dominio público (`pd`, `PD-old`, ...), CC BY y CC BY-SA. `attributionRequired` es verdadero en CC BY y CC BY-SA (siempre con atribución, D12) y falso en CC0 y dominio público. La URL de la licencia es la de Commons; si falta, la canónica de Creative Commons.
- Descartadas, con su motivo: `no-comercial` (NC), `sin-derivadas` (ND), `gfdl` (GFDL sola; una imagen con GFDL y además CC BY-SA se admite por la segunda), `otra-licencia` (conocida pero fuera de la lista, como Free Art License), `licencia-desconocida` (sin metadatos de licencia), `sin-autor` (exige atribución y no trae ni `Artist` ni `Credit`, así que no se podría atribuir) `archivo-no-encontrado` y `formato-no-mostrable` (el `mime` de Commons no es `image/jpeg`, `image/png`, `image/gif`, `image/webp` ni `image/svg+xml`: las láminas de herbario en PDF o TIFF, que la app no puede mostrar). Una restricción NC o ND prima sobre la familia: CC BY-NC-SA no cuenta como CC BY-SA.

### Autor de la imagen

`licenses.clean_author` limpia el `Artist` (y el `Credit`) al extraer, con `classify`:

- «No machine-readable author provided. X assumed (based on copyright claims).» queda como X (sin el sufijo `~commonswiki`); sin nombre, queda vacío.
- Se quitan los correos electrónicos, los avisos de derechos («(c)», «Copyright by», «some rights reserved», «licensed as noted»), las etiquetas de licencia como «(CC BY)» y el texto «This file is licensed under ... Attribution: X You are free...» (queda X).
- Un autor que es solo una URL, o que queda vacío, no cuenta como autor. Las URL dentro de un nombre («Denis Otkydach - https://...») se conservan.
- Si no queda autor ni crédito y la licencia exige atribución, la imagen se descarta con `sin-autor`; CC0 y dominio público se admiten sin autor.

El filtro de formato (`formato-no-mostrable`) también se aplica en `classify`, que recibe el `mime`; `bundles.py` vuelve a comprobarlo antes de incluir una imagen.

### Resultado con los datos reales

Descarga del 21 de octubre de 2026 con el universo de 2.406 plantas (`catalog-universe/1`); las cifras de plantas, ítems asignados y homónimos son las de la asignación recalculada (sin red, desde la caché) con el universo de 2.355 plantas del criterio de Wikipedia, después de descargar los pocos nombres nuevos que ese universo introdujo (3 peticiones: *Erythroxylum havanense* en Wikidata y su resumen de Wikipedia). Los recuentos de imágenes y resúmenes entre paréntesis son los de la descarga original.

| Cifra | Valor |
| --- | --- |
| Nombres consultados | 5.994, incluidos los 2 de control |
| Plantas consultadas | 2.238 de 2.355 (117 sin aceptado: 21 ambiguas, 34 sin resolver y 62 de solo género) |
| Peticiones | Wikidata 150, Wikipedia 1.553 (1.414 resúmenes y 139 respuestas 429), Commons 61 (56 y 5 respuestas 429) |
| Tiempo | 2 h 42 min; más de 100 min fueron esperas de `Retry-After` (de 40 a 46 s por cada una de las 144 respuestas 429) |
| Ítems de Wikidata | 4.320; 4.267 asignados a una planta y 53 sin asignar (15 `ambiguo`, 37 `fuera-del-universo`, 1 `heterotipico-sin-planta`) |
| Plantas con ítem de Wikidata | 2.212 (`con-item`); 26 `sin-item`; 117 `no-consultada`; ninguna `sin-respuesta` |
| Plantas con nombre común en español (P1843) | 231 (950 si se cuentan los alias en español, que mezclan nombres comunes y sinónimos científicos) |
| Plantas con resumen de Wikipedia | 1.407 (1.412 resúmenes) |
| Plantas con imagen admitida | 1.828 (2.634 imágenes: 1.447 CC BY-SA, 568 dominio público, 522 CC BY, 97 CC0) |
| Plantas con alguna imagen descartada | 160; en 82 se descartaron todas |
| Imágenes descartadas por motivo | `sin-autor` 125, `otra-licencia` 25, `gfdl` 15 (165 archivos; no hay NC ni ND porque Commons solo aloja licencias libres) |
| Homónimos | 53 ítems descartados (ninguna planta los recibe) y 11 reasignados a otra planta |

- Ejemplos de descartados: *Spermacoce assurgens* pedido por `spermacoce-remota` (ambiguo), *Thymus capitatus* pedido por `thymbra-capitata` (ambiguo), *Lonicera alba* pedido por `chiococca-alba` (resuelve a *Symphoricarpos albus*) y *Callicarpa arborea* pedido por `callicarpa-arborea` (resuelve a *Callicarpa tomentosa*, fuera del universo). Ejemplos de reasignados: *Cytisus albus* pedido por `chamaecytisus-albus` va a `cytisus-multiflorus`, y *Nerium grandiflorum* pedido por `cryptostegia-grandiflora` va a `nerium-oleander`.
- Controles del piloto: la lavanda (`lavandula-angustifolia`) tiene solo el ítem Q42081 y su imagen; el ítem de *L. latifolia* (Q905916) va a `lavandula-latifolia`. La pasiflora (`passiflora-incarnata`) tiene los ítems Q128939 y Q111273695 (*Granadilla incarnata*, un sinónimo homotípico); el de *P. edulis* (Q156790) va a `passiflora-edulis`. Una prueba sobre la asignación real lo comprueba (se omite si no existe `data/work/wiki/assignment.json`).
- Evidencia de IPNI y POWO: de los 4.267 ítems asignados, 4.120 coinciden, 73 discrepan y 74 no traen dato.
- La estimación previa (unos 10 min para Wikidata, y de 1 a 1,5 h en total) quedó corta porque Wikipedia REST cortó con 429 cada 10 a 13 peticiones.

## Pruebas de 1.4 y datos reales

Las pruebas de descarga usan un servidor HTTP local (`http.server` en un hilo), sin red externa. Una consulta real de humo con tres nombres (Mentha ×piperita, Arnica montana, Matricaria chamomilla), dos resúmenes de Wikipedia y dos imágenes de Commons confirmó el formato; esas respuestas quedan en la caché local, ignorada por Git.

## Esquema del registro

`schema/record.schema.json` es el esquema JSON (draft 2020-12) del registro v1 de una planta, y es la fuente única de la forma del registro: el validador de Python lo aplica y el lector de Rust usará tipos equivalentes con `deny_unknown_fields`. Declara su versión en la extensión `x-recordVersion` (hoy 1), que el registro copia en `recordVersion` y que `plan` y `seal` comparan.

Campos (todos obligatorios, sin campos adicionales en ningún nivel): `id`, `recordVersion`, `bundleHash`, `promptVersion` (entero), `model`, `aliases`, `scientificName` (`name`, `authors`, `refs`), `synonyms` (hasta 10), `family`, `displayName`, `commonNames`, `origin`, `description` (hasta 400 caracteres), `partsUsed` (hasta 5), `oil`, `traditionalUses` (hasta 20 grupos), `goals`, `safety` (un objeto `{level, text, refs}` donde `level` es alto, medio, bajo o `null`, o `null` cuando el paquete no trae ninguna información de seguridad), `image`, `sources`, `refs` (subconjunto del diccionario del paquete; cada entrada lleva `dataset`, `label`, `license` y, opcional, `url`) y `reviewFlags` (objetos `{code, target, message}`; una cadena suelta no es válida). No hay campo `basis`: la variante A solo usa el paquete.

Decisiones de forma que la spec deja abiertas:

- Un grupo de `traditionalUses` lleva `activity`, `activitySource`, `n`, `countries` (en español), `refs`, `pendingReview` y `citations`: una lista de `{key, ref, text}`, con la clave corta tal como viene de USDA, el ref `usda_reference:*` de la candidata elegida y su cita completa. Una clave sin candidata va como `{key, ref: null, text: "<clave> (sin resolver)"}`. `pendingReview` es verdadero solo si el grupo no tiene ninguna cita resuelta: un grupo con al menos una cita resuelta se muestra aunque conserve claves sin resolver, y cada grupo con una clave sin resolver lleva su `reviewFlag` `cita-sin-resolver`. `safety` con `level` nulo lleva `text` y `refs` obligatorios y no marca la planta como «Precaución»; `safety` nulo lleva el flag `sin-datos-de-seguridad`.
- `goals[]` lleva `goal`, `subarea` (nulo salvo en `otros-objetivos`), `area` (traducción del mapa), `evidence`, `pendingReview` y `refs`; los ids de `goal` y `subarea` son enumeraciones cerradas iguales a las de `data/seed/goals.json` (una prueba lo comprueba).
- `image.author` admite `null`: Commons no trae autor en las imágenes de dominio público o CC0 que no lo informan (73 de las 2.634 admitidas), y el paquete no inventa uno.
- Las entradas de `refs` pueden llevar `url` (enlace a la fuente, que el paquete trae cuando la fuente lo tiene). Es obligatoria para los refs de `wikipedia_es` con licencia CC BY-SA, porque la descripción resumida de Wikipedia registra su licencia y el enlace al artículo.
- Los códigos de `reviewFlags` van en minúsculas con guiones (por ejemplo `cita-sin-resolver`); el esquema no limita la lista de códigos, pero el catálogo cerrado está en `flag-codes.json` y el validador avisa de cualquier otro. El `target` del flag de un objetivo es `goals.<goal>` y el de un grupo, `traditionalUses[<índice>]`.

`catalog_seed/schema.py` implementa a mano, sin `jsonschema`, el subconjunto usado: `type` (nombre o lista), `enum`, `const`, `properties`, `required`, `additionalProperties` (`false` o esquema), `propertyNames` (solo `pattern`), `items`, `minItems`, `maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`, `pattern`, `$ref` a `#/$defs/<nombre>` y `$defs`; ignora las anotaciones (`title`, `description`, `$comment`, `x-*`). Cargar un esquema con otra palabra clave falla, para que nadie confíe en una restricción que no se aplica.

## Mapa de objetivos y catálogo

- `goals-map.json`: para cada área terapéutica de la EMA (`areas`), la traducción al español (`es`), el objetivo (`goal`) y la subárea (`subarea`, solo en `otros-objetivos`). Incluye las 15 áreas del snapshot real, con las variantes «Urinary tract and gynaecology disorders», «Digestive disorder» y «Eye discomfort». Declara además `countedOutcomes` (`European Union herbal monograph` y `European Union list entry`), el separador `;` del campo y `emptyArea`: una ficha sin área (24 de las 204 del snapshot) no genera objetivos y está tratada de forma explícita.
- `data/seed/goals.json`: el catálogo de la semilla con los seis objetivos y las seis subáreas de `otros-objetivos` (`id`, `label` provisional en español y `position`; las subáreas llevan además `goalId`). Forma parte del `seedHash`.
- Las pruebas comprueban con el snapshot real de la EMA de la caché (se omiten con `skipTest` si no está) que cada área de las 204 fichas se asigna, que las cinco áreas con objetivo propio coinciden con la spec y que todo id del mapa existe en el catálogo.

## Prompt de consolidación

`prompt/consolidate.md` es el prompt autocontenido de la variante A. Su línea `prompt-version: <n>` es la versión que cada registro guarda en `promptVersion`; subirla hace que `plan` ponga todas las plantas en cola. Recibe el paquete, el esquema, el mapa de objetivos, el catálogo de objetivos y el mapa de seguridad. Incorpora la política de solo el paquete y las correcciones del piloto: resultado combinado de la EMA separado por `;`, nombre científico propio en plantas separadas por colisión, nombres `und` claramente españoles con ref, `EO` como aceite esencial y no un aceite fijo, ningún objetivo para plantas tóxicas según TPPT, hipérico y similares con `pendingReview`, y emparejamiento de claves cortas de cita con las candidatas del paquete (con «(sin resolver)» y su `reviewFlag` cuando no hay candidata). Cada cambio de reglas sube la versión; la versión 2 lo alinea con el paquete real de la 3.5 (véase «Paquetes por planta») y la versión 3 aplica la revisión de la corrida de control (véase «Revisión de la corrida de control (tarea 5.3)»): fuentes de `displayName` y de nombres comunes, catálogo cerrado de códigos de flag, un grupo por actividad del paquete, orden de selección con más de 20 grupos, países sin traducción segura, partes usadas, claves `Eb<vol>: 000` y descripción sin Wikipedia. La versión 4 aplica la segunda repetición de la 5.3: `displayName` entre todos los nombres en español del paquete (el más usado y genérico), formato único del texto de las citas de obras generales con volumen o página, y actividades sin traducción segura con el término original de USDA tal cual (véase «Defectos de la corrida con el prompt v3 y su corrección (prompt v4)»). La versión 5 aplica dos decisiones del usuario (tarea 4.9): un grupo de usos con al menos una cita resuelta se muestra (`pendingReview` solo si ninguna cita se resolvió, y el flag `cita-sin-resolver` se conserva por cada grupo con una clave sin resolver), y las advertencias de seguridad sin nivel van en `safety` con `level` nulo (`sin-datos-de-seguridad` solo cuando el paquete no trae ninguna información de seguridad). La versión 6 aplica la decisión del usuario sobre actividades sensibles (tarea 4.10): el prompt manda leer `sensitive-activities.json`; una enfermedad grave queda en `traditionalUses` con la fórmula «Uso tradicional, sin eficacia demostrada: <enfermedad>» y una señal de riesgo sale de `traditionalUses` y va a `safety` como advertencia con los refs `usda_use:*` de sus filas (véase «Actividades sensibles»). La versión 7 reordena la regla de `displayName` (el criterio principal es el nombre más usado y genérico entre los del paquete, y aparecer en más fuentes solo desempata; «Caléndula» antes que «Botón de oro») y agrega el código `aceite-por-compuesto-eo`: si `oil` se apoya solo en `hasEo` de USDA, sin ficha `aetheroleum` de la EMA ni otra fuente, el registro lleva ese `reviewFlag` con `target` `oil`.

## Actividades sensibles

`sensitive-activities.json` es la lista versionada que leen el prompt (v6) y el validador, igual que `flag-codes.json`. Define dos categorías y los términos de USDA de cada una, comparados por la forma base de la actividad (el texto antes del primer paréntesis, sin distinguir mayúsculas), de modo que `Cancer(Breast)` cuenta como `Cancer`:

- `enfermedad-grave` (cáncer y tumores, carcinoma, leucemia, linfoma, diabetes, sida o VIH, tuberculosis, malaria, epilepsia, hepatitis, cirrosis y otras enfermedades graves o mortales): el grupo sigue en `traditionalUses` y su `activity` empieza por «Uso tradicional, sin eficacia demostrada: » seguida de la enfermedad (por ejemplo «Uso tradicional, sin eficacia demostrada: cáncer de mama»); `activitySource` conserva el original.
- `senal-de-riesgo` (`Poison`, `Fatality`, `Abortifacient`, `Toxic` y similares): el grupo no va en `traditionalUses`; va a `safety` como advertencia («Advertencia: registrada como veneno en usos tradicionales», «Advertencia: se registran casos mortales», «Advertencia: registrada como abortiva en usos tradicionales»), con los refs `usda_use:*` de sus filas. No fijan nivel por sí solas, salvo las señales letales de USDA (`Fatality`, `Fatal`, `Death`, `Suicide` y `Homicide`), que fijan `alto` mediante una entrada de `sections.safety` (véase «Mapa de seguridad»): sin otra fuente y sin señal letal, `safety` es `{level: null, text, refs}`.
- Las demás actividades (por ejemplo `Aphrodisiac`) quedan como uso tradicional normal.

La lista se armó con las 1.572 actividades distintas de los paquetes reales. Cada categoría documenta su criterio, y los términos dudosos (por ejemplo `Hypertension`, `Syphilis`, `Piscicide` o `Emmenagogue`) quedan fuera y están listados con su motivo en `excludedDoubtful`. Cambiar la lista cambia el comportamiento esperado del consolidador, así que se acompaña de una subida de `prompt-version`. En la app, `safety` se presenta como «Precauciones» (cambio 2).

El validador comprueba (con `activitySource` como entrada de la lista): una enfermedad grave sin la fórmula en `activity` es un error; una señal de riesgo dentro de `traditionalUses` es un error; y si el paquete trae grupos de señales de riesgo, `safety` no puede ser nulo y sus `refs` deben incluir al menos un `usda_use:*` de esos grupos. La fórmula «sin eficacia demostrada» no genera la advertencia de eficacia del validador.

## Paquetes por planta (tareas 3.5, 3.6 y 4.7)

El paquete es la entrada del consolidador de la variante A: todo lo que el LLM puede usar de una planta, con un ref `<record_type>:<row_key>` por fila. `catalog_seed/bundles.py` lo arma sin red como función pura de `sources.db`, `taxonomy.db`, las decisiones de colisión (`collision-decisions.json` y `collision-exceptions.json`), el mapa de seguridad, el mapa de objetivos y la caché de Wikidata, Wikipedia y Commons, y su forma está en `schema/bundle.schema.json` (validada con `schema.py`).

```sh
python3 -I tools/catalog-seed/cli.py bundles
python3 -I tools/catalog-seed/cli.py bundles --plants data/work/plantas.txt --out data/work/bundles --report data/work/bundles-report.json
python3 -I tools/catalog-seed/cli.py bundle-sizes --top 10
```

- `bundles` construye el universo en memoria con `build_universe_from_work` (las mismas decisiones que `resolve`), asigna a las plantas las filas de USDA, TPPT, EFSA, la EMA, Wikidata, Wikipedia y Commons, y escribe `data/work/bundles/<id>.json` (JSON canónico: claves ordenadas, sin espacios y un salto de línea final; ignorado por Git). Tarda unos 80 s para las 2.355 plantas, casi todo en resolver las 2.627 entradas del universo.
- `--plants <archivo>` arma solo los IDs listados (uno por línea; `#` comenta) y no borra los demás paquetes; sin él se arma todo el universo y se retiran los `*.json` de plantas que ya no existen. `--report` guarda las cifras de secciones y tamaños en un JSON. `bundle-sizes` mide un directorio de paquetes ya escrito.
- La asignación de Wikidata, Wikipedia y Commons se recalcula en cada corrida con `wiki_assign.build_assignment` (filtro de homónimos incluido) sobre el universo en memoria y las fuentes activas de `sources.json`; no se lee `data/work/wiki/assignment.json`, para que el paquete no dependa de un archivo viejo.

### Formato

- Raíz: `bundleVersion` (`"1"`), `plantKey` (el ID), `bundleHash` (`sha256:` más el sha256 del JSON canónico sin el propio `bundleHash`), `identity`, `sections` y `refs`.
- `identity`: `proposedId`, `name`, `authors`, `kind` y `family`; `universe` (las entradas de USDA y de la EMA que llegaron a la planta, con su resultado y su relación con el aceptado); `primaryBackbone`; `accepted` (el aceptado de WCVP y el de WFO; el del backbone no principal se obtiene resolviendo allí el nombre aceptado, y falta si no resuelve a uno solo); `nameSet` (nombres con `reason` y `backbone`: `universe` es el nombre propio de la planta, y los demás motivos son `entrada-usda`, `entrada-ema`, `heterotipico-fusionado`, `aceptado-del-grupo` y `sinonimo-homotipico`); `aliases`; `collision`; `flags` y `notes`.
- `identity.collision` es `null` o `{role, acceptedName, split, members, fused, decision}`: `role` es `separada` para un heterotípico con planta propia y `aceptado` para la planta que contiene al aceptado; `members` son las plantas del grupo partido; `fused` lista los heterotípicos fusionados con su motivo y sus entradas; `decision` es la decisión registrada de un heterotípico separado.
- `identity.flags` son objetos `{code, target, message}`: los `reviewFlags` del universo (identidad ambigua, solo género, grupo partido, fusión heterotípica...), los de Wikidata (`wikidata-sin-respuesta`, `wikidata-sin-item` y `wikidata-no-consultada`, con `target` `wikidata`) y `extraccion-seguridad-fallida` cuando la extracción de los PDF de la EMA falló o quedó incompleta. `identity.notes` son frases sobre fusiones, distribución compartida, imágenes descartadas y recortes del paquete.
- `sections.taxonomy`: filas de WCVP y WFO con `role` (`aceptado`, `propio` para un heterotípico separado, `heterotipico-fusionado` y `sinonimo-homotipico`), ref `wcvp:<plant_name_id>` o `wfo:<taxon_id>`. `sections.distribution`: `null` o la distribución de WCVP del aceptado (`native` e `introduced` son regiones; `nativeAreas` trae hasta 25 áreas nativas y `nativeAreaCount` el total; `of` dice `aceptado-compartido` para un heterotípico separado, cuya distribución es la del aceptado del grupo).
- `sections.names`: nombres comunes de USDA (con su idioma heurístico), de Wikidata (P1843 y la etiqueta en español si difiere del nombre científico) y de TPPT (inglés y alemán). `sections.descriptions`: resúmenes de Wikipedia en español con `url`, licencia CC BY-SA 4.0 y revisión. `sections.parts`: las partes de USDA con química (`hasEo`, `eoCompounds`, `topAmount` y `topEo`). `sections.images`: imágenes de Commons con licencia admitida (hasta 5), con `author` nulo cuando Commons no lo trae (solo dominio público o CC0).
- `sections.uses`: un grupo por actividad con `n`, `countries`, `refs` (`usda_use:*`), `citations` (las claves cortas tal como vienen) y `candidates` (clave a lista de hasta 5 `{ref, citation}` con ref `usda_reference:*`; una clave sin candidatas no figura). Salen ordenados por filas y actividad.
- `sections.regulatory`: una ficha de la EMA por fila (`ema_herbal:<slug>`) con `outcome` unido por `;`, `therapeuticAreas`, `combination`, `status` y `goalCandidates`: los objetivos que salen de aplicar `goals-map.json` a las áreas cuando el resultado incluye monografía o entrada de lista y no es un producto combinado (vacía en otro caso, con los mismos criterios que el validador; una prueba compara ambos). En una ficha fusionada de dos especies (`hyperici-herba`) cada planta recibe las áreas y el resultado de su propia fila.
- `sections.safety`: una entrada por fuente y sección, con el nivel que fija el mapa de seguridad (`level`) y su motivo (`levelReason`). TPPT: `humanToxicity`, `categories` con su nivel, parte tóxica y toxinas (hasta 20; sin las dosis en animales); el motivo es el `why` de las categorías de mayor nivel. EMA: una entrada por sección 4.3, 4.4 y 4.5 de la monografía o `CONCLUSIONS` de la declaración pública, con su texto y página; la 4.5 lleva `interactionClass`, `columns`, `matchedPatterns` y `severeInteractions` (la marca que usa el validador, calculada con `safety.ema_interaction_class`), y las `CONCLUSIONS` con datos de seguridad llevan `medio`. EFSA: una sola entrada con `concernSubstances` (las de la lista versionada que activaron el nivel, con su grupo), `evidenceSubstances` (hasta 25, sin nivel) y `studies` de ENDPOINTSTUDY (hasta 10, evidencia). USDA: una sola entrada, solo si la planta tiene grupos de uso con una señal letal (se calcula sobre todos los grupos, aunque un tope deje alguno fuera de `sections.uses`), con `source` `usda`, `level` `alto`, `levelReason` (el motivo del mapa), `refs` (los `usda_use:*` de esas filas; `ref` es el primero) y `terms` (las actividades sin calificador, por ejemplo `["Fatality", "Suicide"]`). Una planta con solo señales no letales (`Poison`) no lleva entrada de USDA. El armado no decide el nivel final: lo calcula el consolidador como el más alto entre las entradas, y el validador lo comprueba.
- `sections.wikidata`: `{status, items}` con `status` `con-item`, `sin-item`, `sin-respuesta` o `no-consultada` (véase «Wikidata, Wikipedia en español y Commons») y un ítem por QID asignado con su P225, autores, nombres en español, título de eswiki, identificadores y `match` (el motivo de la asignación).
- `refs`: ref a `{dataset, label, license, url?}`. `dataset` es el `id` de la fuente de `sources.json`; la licencia es la de la fuente, salvo Commons (la del archivo); `url` la traen la EMA (la página de la ficha o el PDF), Wikidata, Wikipedia (obligatoria) y Commons. Toda fila citada tiene su entrada y no hay entradas sin uso (lo comprueban las pruebas).

Ejemplo resumido de la lavanda (`lavandula-angustifolia`, datos reales):

```json
{
  "bundleVersion": "1",
  "plantKey": "lavandula-angustifolia",
  "bundleHash": "sha256:…",
  "identity": {
    "proposedId": "lavandula-angustifolia", "name": "Lavandula angustifolia", "authors": "Mill.", "kind": "resolved", "family": "Lamiaceae",
    "primaryBackbone": "wcvp",
    "accepted": {"wcvp": {"ref": "wcvp:108971", "name": "Lavandula angustifolia", "…": "…"}, "wfo": {"ref": "wfo:wfo-0000224116", "…": "…"}},
    "nameSet": [{"name": "Lavandula angustifolia", "reason": "universe", "backbone": "wcvp", "ref": "wcvp:108971", "authors": "Mill."}, "…"],
    "collision": null, "flags": [], "notes": [], "aliases": [], "universe": ["…"]
  },
  "sections": {
    "taxonomy": ["…"], "distribution": {"native": ["Southeastern Europe", "Southwestern Europe"], "nativeAreas": ["France", "Italy", "Spain"], "of": "aceptado", "…": "…"},
    "names": [{"ref": "usda_common_name:544-1", "text": "English Lavender", "language": "en", "source": "usda"}, "…"],
    "descriptions": [{"ref": "wikipedia_es:Lavandula angustifolia", "url": "https://es.wikipedia.org/wiki/Lavandula_angustifolia", "license": "CC BY-SA 4.0", "…": "…"}],
    "parts": ["…"], "uses": [{"activity": "…", "n": 3, "refs": ["usda_use:…"], "citations": ["Woi.10"], "candidates": {"Woi.10": [{"ref": "usda_reference:WOI", "citation": "…"}]}, "…": "…"}],
    "regulatory": [{"ref": "ema_herbal:lavandulae-flos", "outcome": "European Union herbal monograph", "goalCandidates": [{"goal": "mejorar-el-sueno", "subarea": null, "…": "…"}, "…"], "…": "…"}],
    "safety": [{"source": "efsa", "level": "medio", "concernSubstances": [{"substance": "alpha-thujone", "group": "toxico-con-limite", "…": "…"}], "…": "…"}, {"source": "ema_pdf", "section": "4.5", "interactionClass": "none-reported", "severeInteractions": false, "…": "…"}, "…"],
    "images": [{"ref": "commons:File:…", "license": "Public domain", "attributionRequired": false, "…": "…"}],
    "wikidata": {"status": "con-item", "items": [{"ref": "wikidata:Q42081", "qid": "Q42081", "p225": "Lavandula angustifolia", "…": "…"}]}
  },
  "refs": {"wcvp:108971": {"dataset": "wcvp", "label": "WCVP: Lavandula angustifolia Mill.", "license": "CC BY 3.0"}, "…": "…"}
}
```

### Asignación de las filas

- USDA: `assign_usda` (véase «Asignación de USDA y citas candidatas»). TPPT: cada planta de `tppt_plant` se asigna con `Universe.assign` por su nombre latino. EFSA: la celda `scientificNames` trae varios nombres separados por «;» o «$» (`split_source_names("efsa", ...)` los separa) y la fila va a cada planta distinta a la que llega alguno de sus nombres. La EMA: por las entradas `ema:<slug>#<n>` de la planta, sin resolver nada más.
- Con los datos reales: TPPT asigna 284 de sus 844 plantas a 283 plantas del universo (de las 560 restantes, 555 resuelven a especies que no están en el universo, 3 no resuelven y 2 caen en un grupo partido sin miembro que las reciba); EFSA asigna 2.143 de las 3.449 filas de `BOTANIC.xls` a 489 plantas y 528 de los 972 estudios de `ENDPOINTSTUDY.xls` a 204 plantas (los nombres que no llegan son sobre todo especies fuera del universo: 594, frente a 30 que no resuelven y 1 sin miembro). Los nombres sin asignar de los grupos partidos marcan el grupo con `filas-sin-asignar`. Una planta del universo sin fila de una fuente simplemente no trae esa sección.
- Una planta sin datos de una fuente lo declara: Wikidata lo dice en `sections.wikidata.status` y en `identity.flags`; una ficha de la EMA sin PDF extraído lo dice con una entrada `ema_pdf` con `status` `extraccion-fallida` (y el flag `extraccion-seguridad-fallida`); las demás fuentes dejan la sección vacía y el consolidador lo traduce en `null` o lista vacía (y `sin-datos-de-seguridad` para `safety`).

### Determinismo

El paquete no usa fechas ni el orden de las tablas: todas las listas se ordenan y el hash es el del JSON canónico. Con los datos reales, dos construcciones completas dan archivos idénticos byte a byte (`diff -r`). Las pruebas comprueban que dos construcciones dan el mismo JSON y que un cambio de un insumo de una planta (un texto de la EMA, un nombre de Wikidata) cambia solo el `bundleHash` de esa planta.

### Fuentes desactivadas (D14, tarea 4.7)

Cada fuente de `sources.json` tiene `enabled`. Una fuente desactivada no aporta filas ni refs al paquete, y el paquete no declara qué fuentes están activas (si lo hiciera, cambiaría el hash de todas las plantas). El prompt y el validador no dependen de ninguna fuente concreta (una prueba comprueba que no mencionan `enabled`): un campo sin datos queda `null`. Desactivar Wikipedia solo cambia el `bundleHash` de las plantas que tenían un resumen; desactivar `wikidata` quita también Wikipedia y Commons, porque se asignan por sus ítems, y deja el estado de Wikidata de las plantas consultadas en `sin-respuesta`; desactivar `wcvp` no es posible (la taxonomía principal es la identidad) y `bundles` falla diciéndolo. Las pruebas usan fixtures con Wikipedia desactivada en 3 de 6 plantas (`plan` detecta solo esas 3 por el cambio de `bundleHash`, los paquetes no traen refs de Wikipedia y un registro de ejemplo con `description` nula o resumida de la EMA pasa el validador sin errores). Con los datos reales, desactivar `wikipedia_es` cambia el hash de exactamente las 1.406 plantas con resumen de Wikipedia (de 2.355) y ningún paquete conserva refs de Wikipedia (comprobado fuera de las pruebas, con una copia en memoria de la configuración).

### Tamaños (tarea 3.6)

`bundle-sizes` (y el final de `bundles`) mide el JSON canónico de cada paquete en tokens estimados (caracteres ÷ 3,5): p50, p90, máximo, promedio y total, las plantas más grandes con sus secciones mayores y el total por sección. Resultado con los datos reales (21 de octubre de 2026, 2.355 paquetes, 38 MB en disco):

| Cifra | Estimado (D6) | Real |
| --- | --- | --- |
| p50 | unos 2.900 tokens | 2.785 |
| Total | unos 9,7 millones | 9.959.543 (9,96 millones, 2,7 % más) |
| p90 | no estimado | 9.262 |
| Promedio | no estimado | 4.229 |
| Máximo | 21.700 en el piloto (20 plantas elegidas) | 35.833 (`curcuma-longa`) |
| Paquetes de más de 10.000 / 20.000 / 30.000 tokens | no estimado | 206 / 25 / 4 |

- Diferencias: el p50 y el total están en el orden de lo estimado. El máximo supera lo del piloto porque el universo incluye plantas con cientos de filas de uso de USDA y porque el paquete v1 suma lo que el piloto no tenía: las secciones 4.3 a 4.5 de la EMA, EFSA, TPPT y los candidatos de objetivos. Como referencia, 20 plantas conocidas parecidas a las del piloto (lavanda, manzanilla, menta, hipérico, pasiflora, valeriana, árbol del té, caléndula, bergamota, canela, jengibre, eucalipto, romero, salvia, tomillo, hinojo, ajo, aloe, equinácea y ginkgo; no es la lista exacta del piloto) dan un promedio de unos 13.900 tokens y un máximo de unos 29.000 (`allium-sativum`), frente a los 8.300 y 21.700 del piloto.
- Qué infla los paquetes grandes: el total por sección es `uses` 3,39 millones (34 %), `refs` 2,48 millones (25 %), `identity` 0,80 millones, `parts` 0,64 millones, `taxonomy` 0,49 millones, `images` 0,47 millones, `safety` 0,40 millones, `wikidata` 0,37 millones, `distribution` 0,31 millones, `descriptions` 0,22 millones, `names` 0,13 millones y `regulatory` 0,05 millones. En las diez plantas más grandes `uses` pesa de 16.800 a 24.300 tokens y `refs` de 5.600 a 7.600: una planta con 100 o más actividades distintas tiene 100 grupos, cada clave de cita lleva hasta 5 candidatas con su cita completa (cerca del 80 % de `uses`) y cada fila `usda_use:*` aparece en su grupo y en `refs`.
- Topes: el paquete ya acota los sinónimos homotípicos (15), las áreas nativas (25), las imágenes (5), las sustancias de evidencia de EFSA (25), los estudios de EFSA (10) y las toxinas de TPPT (20), y cada recorte dice su total (`homotypicTotal`, `nativeAreaCount`, `toxinsTotal`, `evidenceTotal`, `studiesTotal` o una nota). Con los datos reales solo se activan el de áreas nativas (590 plantas, que conservan las regiones), el de imágenes (10), el de estudios (3) y el de toxinas (1).
- Propuesta de tope, sin aplicar: limitar `uses` a los 40 grupos con más filas (`DEFAULT_LIMITS["useGroups"]` en `bundles.py`; el registro tiene hasta 20 grupos y el consolidador agrupa actividades equivalentes, así que 40 deja margen), con una nota en `identity.notes` que dice cuántos grupos y filas se omitieron. Simulado sobre el universo: afecta a 162 plantas, omite 2.529 de las 35.935 filas de uso asignadas (7 %) y todos los grupos omitidos tienen una o dos filas; el máximo baja a 22.074 tokens (`momordica-charantia`), cerca del 21.700 del piloto, el p50 no cambia (2.785), el p90 pasa a 9.140 y el total a 9,60 millones. Con 30 grupos, 5 refs y 10 claves por grupo el máximo sería 19.024 y el total 9,29 millones (263 plantas afectadas). Recortar solo `useRefs` o `useKeys` no baja el máximo. Los límites están en `DEFAULT_LIMITS` (con `useGroups`, `useRefs` y `useKeys` sin límite); adoptar el tope cambia el `bundleHash` de las plantas afectadas y las pone en la cola de `plan`, así que es una decisión del usuario.

### Corrida de control (tarea 5.1)

`tools/catalog-seed/control.txt` fija las 20 plantas de la corrida de control: las del piloto con los IDs del universo actual (romero es `salvia-rosmarinus`, manzanilla `matricaria-chamomilla` y el almendro `prunus-amygdalus`, que lleva `prunus-dulcis` como alias y no se fusiona con el cerezo), con la cicuta como tóxica de TPPT, *Pelargonium sidoides* y *Rhodiola rosea* como plantas solo de la EMA, y el almendro en lugar de *Datura stramonium*. Los comentarios van en líneas propias (`#` solo comenta líneas completas). Sirve para repetir la consolidación sobre un conjunto pequeño y conocido, comparable con el piloto, antes de la generación completa.

```sh
python3 -I tools/catalog-seed/cli.py bundles --plants tools/catalog-seed/control.txt --report data/work/bundles-control-report.json
```

Los 20 paquetes validan contra `schema/bundle.schema.json`. Tamaños en tokens estimados: ricino 30.420, manzanilla 19.197, romero 16.384, hipérico 15.879, eucalipto 13.468, menta 13.463, valeriana 13.274, tomillo 11.519, caléndula 10.685, consuelda 8.036, pasiflora 7.875, cicuta 7.783, melisa 7.685, lavanda 6.551, árbol del té 4.512, almendro 4.015, *Pelargonium sidoides* 3.141, *Rhodiola rosea* 3.132, bergamota 1.982 y lavandín 1.351. Promedio 10.018, p50 8.036 y máximo 30.420 (ricino), frente a 8.300 y 21.700 del piloto. El promedio queda a un 21 % del piloto; el máximo lo explica el ricino, con muchas actividades de uso de USDA (`uses` 19.477 y `refs` 7.601 de sus 30.420), el caso que cubre la propuesta de tope de `useGroups`. Sin el ricino el máximo es 19.197 (manzanilla) y el promedio 8.944. Tras quitar los parámetros `utm_*` de las URL de las imágenes (tarea 5.3), los paquetes se reconstruyeron y el promedio es 9.985, el p50 8.014 y el máximo 30.398.

### Cobertura con los datos reales

| Sección | Plantas con datos | Plantas sin datos |
| --- | --- | --- |
| `taxonomy` | 2.238 | 117 |
| `distribution` | 2.223 | 132 |
| `names` | 1.589 | 766 |
| `descriptions` | 1.406 | 949 |
| `parts` | 2.244 | 111 |
| `uses` | 1.453 | 902 |
| `regulatory` | 206 | 2.149 |
| `safety` | 731 | 1.624 |
| `images` | 1.828 | 527 |
| `wikidata` (con ítems) | 2.212 | 143 |

El estado de Wikidata es `con-item` en 2.212 plantas, `sin-item` en 26 y `no-consultada` en 117 (las sin aceptado: ambiguas, sin resolver o de solo género); ninguna `sin-respuesta`. Las plantas sin `taxonomy` son esas 117. Hay 23 plantas separadas por colisión (su distribución es la del aceptado compartido), 45 con el flag `fusion-heterotipica` y 8 con `filas-sin-asignar`.

Comprobaciones con los paquetes reales (la sección de pruebas `RealBundlesTests` las repite si existen en `data/work/bundles/`):

- La lavanda tiene solo el ítem Q42081 y nada de *L. latifolia* (ni su QID, ni su nombre, ni sus filas); la pasiflora tiene los ítems Q128939 y Q111273695 (*Granadilla incarnata*, homotípico) y nada de *P. edulis*.
- El hipérico (`hypericum-perforatum`) trae `severeInteractions` verdadero en las secciones 4.5 de `hyperici-herba-0` y de `hyperici-herba` y el candidato `relajacion-estres` en `hyperici-herba-0` (la ficha combinada `hyperici-herba` no cuenta).
- La menta (`mentha-x-piperita`) cuenta el resultado combinado `European Union herbal monograph;European Union list entry` y trae los candidatos `dolor-e-inflamacion`, `cuidado-de-la-piel`, `alivio-respiratorio` y `digestion`; el árbol del té (`melaleuca-alternifolia`) y la caléndula (`calendula-officinalis`) traen `boca-y-garganta` y `cuidado-de-la-piel` (la ficha `calendulae-herba` no tiene resultado y no aporta candidatos).
- La bergamota (`citrus-x-bergamia`) se arma como *Citrus × bergamia* (`role` `separada`, aceptado compartido *Citrus × limon*). La canela (`cinnamomum-verum`) trae *Cinnamomum zeylanicum* fusionado: 41 filas de uso de USDA, su ítem de Wikidata Q12892282 y los motivos en `identity.collision.fused`.

### Cambios al contrato con el prompt, el validador y el registro

- `prompt/consolidate.md` sube a la versión 2: describe las secciones reales del paquete, usa `identity.name` y `nameSet` con motivo `universe` para el nombre propio, `goalCandidates` como punto de partida de los objetivos, el nivel por entrada de `sections.safety` (en lugar de las categorías provisionales), los flags de Wikidata y `author` nulo en la imagen, y retira la preparación de EFSA como indicio de aceite esencial (el paquete no la trae).
- `schema/record.schema.json`: `image.author` admite `null`. Commons no trae autor en 73 de sus 2.634 imágenes admitidas, todas de dominio público, que no exigen atribución; el paquete no inventa un autor.
- `catalog_seed/validate.py` no cambia: el contrato que usa coincide con lo que arma el paquete. Los fixtures de `tests/fixtures/validate/` se actualizaron al formato real (datasets por fuente, refs `usda_use:*`, `commons:*` y `wikidata:*`, `wikidata` como objeto) y las pruebas comprueban que cumplen `bundle.schema.json`.

## Revisión de la corrida de control (tarea 5.3)

Revisión de los 20 registros de la corrida 5.2 (prompt v2, `data/work/control/lote-1/` y `lote-2/`). Las correcciones salen en el prompt v3, en el validador y en el armado de paquetes. Las repeticiones con el prompt v3 (`data/work/control/v3/`), el v4 (`data/work/control/v4/`) y el v7 (`data/work/control/v7/`) siguen en las subsecciones finales. La revisión quedó cerrada con la v7 y la aprobación del usuario (véase «Aprobación del usuario (tarea 5.5)»).

### Lista de comprobación planta por planta

«Correcto» es lo comprobado y conforme a la tarea; «-» es que la tarea no pide esa comprobación para la planta. Los niveles de seguridad son los del mapa v2.

| Planta | Objetivos | Identidad | Aceite esencial | Nivel de seguridad | Citas sin resolver (grupos pendientes) |
| --- | --- | --- | --- | --- | --- |
| Lavanda (`lavandula-angustifolia`) | - | Correcto: sin datos de *L. latifolia* | Correcto, según `EO` | medio | 0 (0) |
| Romero (`salvia-rosmarinus`) | - | - | Esencial | medio | 15 (15) |
| Menta (`mentha-x-piperita`) | Correcto: tiene objetivos | - | Esencial | medio | 3 (3) |
| Valeriana (`valeriana-officinalis`) | - | - | Esencial | medio | 0 (0) |
| Consuelda (`symphytum-officinale`) | - | - | `null` | medio | 0 (0) |
| Árbol del té (`melaleuca-alternifolia`) | Correcto: tiene objetivos | - | Esencial | medio | 0 (0) |
| *Pelargonium sidoides* (`pelargonium-sidoides`) | - | - | `null` | medio | 0 (0) |
| Manzanilla (`matricaria-chamomilla`) | - | - | Esencial | bajo | 12 (12) |
| Tomillo (`thymus-vulgaris`) | - | - | Esencial | bajo | 5 (5) |
| Almendro (`prunus-amygdalus`) | - | Correcto: no está fusionado con el cerezo | Esencial (`EO` en USDA); se anota para revisión | bajo | 0 (0) |
| Eucalipto (`eucalyptus-globulus`) | - | - | Esencial | `null` | 3 (3) |
| Pasiflora (`passiflora-incarnata`) | - | Correcto: sin datos de *P. edulis* | `null` | `null` | 0 (0) |
| Melisa (`melissa-officinalis`) | - | - | Esencial | `null` | 0 (0) |
| Caléndula (`calendula-officinalis`) | Correcto: tiene objetivos | - | Esencial | `null` | 6 (5) |
| Lavandín (`lavandula-x-intermedia`) | - | - | Esencial | `null` | 0 (0) |
| Rodiola (`rhodiola-rosea`) | - | - | `null` | `null` | 0 (0) |
| Bergamota (`citrus-x-bergamia`) | - | Correcto: es *Citrus × bergamia* | Esencial | `null` | 0 (0) |
| Cicuta (`conium-maculatum`) | Correcto: sin objetivos | - | Esencial (`EO` en USDA); se anota para revisión | alto | 2 (2) |
| Ricino (`ricinus-communis`) | Correcto: objetivos omitidos por toxicidad de TPPT | - | `null`, porque es un aceite fijo | alto | 9 (9) |
| Hipérico (`hypericum-perforatum`) | Correcto: `relajacion-estres` con `pendingReview` y `reviewFlag` `interacciones-graves-estres` | - | Esencial (`EO` en USDA); se anota para revisión | alto | 4 (4) |

Todas las citas sin resolver son `Woi.Syria`, que no tiene candidatas. Los grupos pendientes de las 20 plantas suman 58, y los casos más cargados fueron el romero (15) y la manzanilla (12), porque el prompt v2 no ordenaba qué grupos entran cuando hay más de 20.

### Revisión manual de emparejamientos de claves de cita

| Clave | Candidata elegida | Veredicto |
| --- | --- | --- |
| `Burkill,1966` | `Burkill, 1966` | Correcto |
| `Woi.6`, `Woi.7`, `Woi.9`, `Woi.10` | `WOI`, con el texto «The Wealth of India, vol. n» | Correcto |
| `Eb24: 441`, `Eb28: 323`, `Eb33: 229` | `EB`, con el texto «Economic Botany <vol>: <pág>», descartando las `EBxx:yyy` de otros volúmenes | Correcto |
| `Duke,1972` | `Duke` (1972), descartando `DUKE1992A` y `DUKE1992B` | Correcto |
| `Nas` | `NAS2` (farmacología herbal de China) y no `NAS` (Lost Crops of the Incas), por los países del grupo | Correcto |
| `Standley` | `Standley` (Trees and shrubs of Mexico) y no `Standley,1931`, por los países del grupo | Discutible |
| `Woi.Syria`, `Uph` | Sin candidata: «(sin resolver)» | Correcto |
| `Eb33: 000` | - | Dudoso: `000` no es una página real |

### Defectos encontrados y su corrección (prompt v3)

1. **`displayName` y nombres comunes dispares** (por ejemplo «Botón de oro» para la caléndula y «Poison Hemlock» en inglés para la cicuta). El prompt fija cinco fuentes válidas de un nombre en español, todas con ref y en orden: (a) el nombre con el que el resumen de Wikipedia presenta la planta, (b) la etiqueta en español de Wikidata, (c) los P1843, (d) `sections.names` en español y (e) los alias de Wikidata, solo si son claramente nombres comunes. Usarlas no lleva flag. Sin nombre en español, el `displayName` es el nombre científico con `sin-nombre-comun-es`. En `commonNames` solo se normalizan tildes y mayúsculas si la forma aparece en el paquete.
2. **Códigos de flag inventados** (`nombre-comun-ausente`, `sin-nombre-comun-en-espanol`, `sin-objetivos-de-bienestar`, `objetivos-omitidos-por-toxicidad` fuera de lista, `idioma-de-nombre-dudoso`, `nombre-comun-de-resumen`). El catálogo cerrado vive en `flag-codes.json`, el prompt lo reproduce en una tabla y el validador da una advertencia ante un código fuera de él; una prueba comprueba que el prompt y el JSON listan los mismos códigos.
3. **Grupos fusionados.** El prompt v2 pedía agrupar actividades equivalentes, pero el validador exige que `activitySource` sea una actividad del paquete y que las citas sean las candidatas de ese grupo. El prompt v3 dice que cada grupo es una sola actividad del paquete, sin fusionar. El esquema no cambia.
4. **Selección con más de 20 grupos.** Primero los grupos con alguna clave con candidata, por `n` descendente y luego por actividad; después el resto en el mismo orden.
5. **Países sin traducción segura** (`Nc`, `Dr`, `US*`): se omite el país, no el grupo; la lista puede quedar vacía. El prompt trae la tabla de equivalencias seguras (`Elsewhere`, `Mediterranean`, `US(Co)`).
6. **URL de las imágenes con `utm_*`.** `licenses.clean_file_url` quita los parámetros `utm_*` al extraer (`wiki_extract.py`) y al armar el paquete (`bundles.py`), con pruebas. Los 20 paquetes de control se reconstruyeron con `bundles --plants tools/catalog-seed/control.txt`; cambia el `bundleHash` de las plantas con imagen, así que los registros de la 5.2 ya no validan contra ellos hasta repetir la corrida.
7. **Ambigüedades menores.** Las partes usadas salen de las fichas de la EMA u otras fuentes de uso, no de las partes químicas de USDA. Una clave `Eb<vol>: 000` se deja sin resolver: `000` es un marcador de USDA y no una página, y citarla literal o con un flag presentaría como cita una página inexistente; el grupo queda pendiente con el flujo habitual. La descripción es `null` cuando no hay resumen de Wikipedia: la taxonomía y la distribución ya salen en `scientificName`, `family` y `origin`, y una frase derivada las repetiría con redacción dispar.

### Defectos de la corrida con el prompt v3 y su corrección (prompt v4)

La repetición de la 5.3 con el prompt v3 (`data/work/control/v3/lote-1/` y `lote-2/`) mostró tres reglas aplicadas de forma dispar o con mal resultado. El prompt v4 las corrige.

1. **`displayName` por orden de fuente, no por uso.** Con «primer nombre de la fuente (a)» salieron «Melissa» (género en latín, con «toronjil» en el paquete), «Pera del Bey» en vez de «bergamota», «manzanilla de Castilla», «eucalipto blanco», «Botón de oro», «Árbol del té de hoja estrecha», «Tomillo común» y «valeriana común». En la v4 el candidato es cualquier nombre en español de las fuentes (a) a (e); se elige el más usado y genérico (el corto si es cabeza de otros más largos, y el que aparece en más fuentes), nunca uno fuera del paquete ni el nombre latino del género o la especie.
2. **Texto de las citas resueltas sin formato único.** El lote 1 copió la cita completa de la candidata con la clave entre paréntesis y el lote 2 escribió la forma corta. En la v4, para una obra general con volumen o página (`Woi.<n>`, `Eb<vol>: <pág>`), `text` es el título de la obra más el volumen o la página («The Wealth of India, vol. 10», «Economic Botany 24: 441»); si la clave coincide con su candidata, es la cita completa literal. `Eb<vol>: 000` sigue sin resolver.
3. **Actividad sin traducción segura anotada.** Un agente escribió «Fumitory (sin traducción segura)». En la v4, `activity` lleva el término original de USDA tal cual, sin anotaciones.

El tratamiento de actividades sensibles como «Cancer», «Tumor», «Abortifacient» o «Fatality» quedó pendiente en esta etapa y lo resuelve el prompt v6 (véase «Actividades sensibles»).

### Costo y tiempo de la corrida 5.2

| Lote | Plantas | Inicio y fin (2026-10-22, UTC) | Duración | Tokens del agente | Tokens por planta |
| --- | --- | --- | --- | --- | --- |
| 1 | 10 | 04:41:12Z a 04:48:07Z | 6 min 55 s | 182.108 | unos 18.200 |
| 2 | 10 | 04:41:12Z a 04:47:15Z | 6 min 3 s | 223.036 | unos 22.300 |

El promedio es de unos 20.300 tokens por planta, contra 12.000 a 15.500 en el piloto. Extrapolado a 2.355 plantas son unos 48 millones de tokens, contra los 23 millones estimados. Los tokens son el total que reporta el agente, incluidas las lecturas del prompt, los esquemas y los mapas en cada lote. Los lotes corrieron en paralelo, con agentes de Claude Code del modelo balanceado. El validador dio 0 errores y 0 advertencias en los 20 registros.

### Resultados con el prompt v4

Los 20 registros de `data/work/control/v4/lote-1/` y `lote-2/` se armaron con los paquetes de `data/work/bundles/` y Wikipedia activa. El validador (`lote-1-validate.json` y `lote-2-validate.json`) da 0 errores y 0 advertencias en los 20. Las cifras salen de los registros.

| Planta | `displayName` | Objetivos | Seguridad | Grupos | Grupos pendientes | Citas sin resolver | Flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lavanda | Lavanda | `mejorar-el-sueno`, `relajacion-estres` | medio | 11 | 0 | 0 | - |
| Eucalipto | Eucalipto blanco | `alivio-respiratorio`, `otros-objetivos` (dolor e inflamación) | `null` | 20 | 3 | 3 | `cita-sin-resolver` (3), `sin-datos-de-seguridad` |
| Romero | Romero | `otros-objetivos` (circulación, digestión) | medio | 20 | 17 | 17 | `cita-sin-resolver` (17) |
| Manzanilla | Manzanilla | `cuidado-de-la-piel`, `alivio-respiratorio`, `otros-objetivos` (boca y garganta, digestión) | bajo | 20 | 15 | 15 | `cita-sin-resolver` (15) |
| Menta | Menta piperita | `cuidado-de-la-piel`, `alivio-respiratorio`, `otros-objetivos` (dolor e inflamación, digestión) | medio | 20 | 4 | 4 | `cita-sin-resolver` (4) |
| Cicuta | Conium maculatum (`la`) | - | alto | 20 | 2 | 2 | `sin-nombre-comun-es`, `cita-sin-resolver` (2) |
| Ricino | Ricino | - (omitidos por toxicidad) | alto | 20 | 11 | 11 | `objetivos-omitidos-por-toxicidad`, `idioma-de-nombre-dudoso`, `cita-sin-resolver` (11) |
| Valeriana | Valeriana común | `mejorar-el-sueno`, `relajacion-estres` | medio | 20 | 1 | 1 | `idioma-de-nombre-dudoso`, `cita-sin-resolver` (1) |
| Pasiflora | Pasiflora | `mejorar-el-sueno`, `relajacion-estres` | `null` | 20 | 0 | 0 | `idioma-de-nombre-dudoso`, `sin-datos-de-seguridad` |
| Melisa | Toronjil | `mejorar-el-sueno`, `relajacion-estres`, `otros-objetivos` (digestión) | `null` | 20 | 0 | 0 | `sin-datos-de-seguridad` |
| Tomillo | Tomillo | `alivio-respiratorio` | bajo | 20 | 5 | 5 | `cita-sin-resolver` (5) |
| Caléndula | Botón de oro | `cuidado-de-la-piel`, `otros-objetivos` (boca y garganta) | `null` | 20 | 5 | 6 | `cita-sin-resolver` (5), `sin-datos-de-seguridad` |
| Hipérico | Hipérico | `cuidado-de-la-piel`, `relajacion-estres` (pendiente), `otros-objetivos` (digestión) | alto | 20 | 4 | 4 | `cita-sin-resolver` (4), `interacciones-graves-estres` |
| Consuelda | Consuelda | `otros-objetivos` (dolor e inflamación) | medio | 20 | 2 | 2 | `cita-sin-resolver` (2) |
| Árbol del té | Árbol de té | `otros-objetivos` (boca y garganta), `cuidado-de-la-piel` | medio | 1 | 0 | 0 | - |
| Lavandín | Lavandula × intermedia (`la`) | - | `null` | 0 | 0 | 0 | `sin-nombre-comun-es`, `sin-datos-de-seguridad` |
| *Pelargonium sidoides* | Geranio africano | `alivio-respiratorio` | medio | 0 | 0 | 0 | - |
| Rodiola | Rodiola | `cansancio-y-fatiga`, `relajacion-estres` | `null` | 4 | 0 | 0 | `sin-datos-de-seguridad` |
| Bergamota | Bergamota | - | `null` | 0 | 0 | 0 | `grupo-partido`, `sin-datos-de-seguridad` |
| Almendro | Almendro | - | bajo | 1 | 0 | 0 | - |

Totales: 277 grupos, 69 pendientes y 70 citas sin resolver (la caléndula tiene un grupo con dos). En la corrida 5.2 (prompt v2) los grupos pendientes sumaban 58.

### Costo y tiempo de cada versión del prompt

| Versión | Lote | Tokens del agente | Duración | Tokens por planta |
| --- | --- | --- | --- | --- |
| v3 | 1 | 215.477 | 7 min 18 s | unos 19.800 en promedio de los dos lotes |
| v3 | 2 | 180.945 | 4 min 58 s | |
| v4 | 1 | 210.122 | 7 min 19 s | unos 18.000 en promedio de los dos lotes |
| v4 | 2 | 149.187 | 4 min 22 s | |

La v4 cuesta unos 1.800 tokens menos por planta que la v3. Ambas siguen por encima de los 12.000 a 15.500 tokens por planta del piloto.

### Resultados con el prompt v7

Los 20 registros de `data/work/control/v7/lote-1/` y `lote-2/` se armaron con los mismos paquetes de `data/work/bundles/` (no cambiaron desde la v4) y Wikipedia activa. El validador (`lote-1-validate.json` y `lote-2-validate.json`) da 0 errores y 0 advertencias en los 20. Las cifras salen de los registros. «Grupos con cita sin resolver» cuenta grupos de `traditionalUses` con al menos una cita marcada «(sin resolver)»; los grupos se muestran y llevan el flag.

| Planta | `displayName` | Objetivos | Seguridad | Grupos | Grupos pendientes | Citas sin resolver | Flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lavanda | Lavanda | `mejorar-el-sueno`, `relajacion-estres` | medio | 11 | 0 | 0 | - |
| Eucalipto | Eucalipto común | `alivio-respiratorio`, `otros-objetivos` (dolor e inflamación) | `null` con texto | 20 | 0 | 3 (3 grupos) | `cita-sin-resolver` (3) |
| Romero | Romero | `otros-objetivos` (circulación, digestión) | medio | 20 | 0 | 17 (17 grupos) | `cita-sin-resolver` (17) |
| Manzanilla | Manzanilla | `cuidado-de-la-piel`, `alivio-respiratorio`, `otros-objetivos` (boca y garganta, digestión) | bajo | 20 | 0 | 15 (15 grupos) | `cita-sin-resolver` (15) |
| Menta | Menta piperita | `alivio-respiratorio`, `cuidado-de-la-piel`, `otros-objetivos` (dolor e inflamación, digestión) | medio | 20 | 0 | 4 (4 grupos) | `cita-sin-resolver` (4) |
| Cicuta | Conium maculatum (`la`) | - | alto | 19 | 0 | 1 (1 grupo) | `aceite-por-compuesto-eo`, `cita-sin-resolver`, `sin-nombre-comun-es` |
| Ricino | Ricino | - (omitidos por toxicidad) | alto | 20 | 0 | 10 (10 grupos) | `cita-sin-resolver` (10), `idioma-de-nombre-dudoso`, `objetivos-omitidos-por-toxicidad` |
| Valeriana | Valeriana común | `mejorar-el-sueno`, `relajacion-estres` | medio | 20 | 0 | 1 (1 grupo) | `cita-sin-resolver`, `idioma-de-nombre-dudoso` |
| Pasiflora | Pasiflora | `mejorar-el-sueno`, `relajacion-estres` | `null` con texto | 19 | 0 | 0 | `idioma-de-nombre-dudoso` |
| Melisa | Toronjil | `mejorar-el-sueno`, `relajacion-estres`, `otros-objetivos` (digestión) | `null` con texto | 20 | 0 | 0 | - |
| Tomillo | Tomillo | `alivio-respiratorio` | bajo | 20 | 0 | 5 (5 grupos) | `cita-sin-resolver` (5) |
| Caléndula | Caléndula | `cuidado-de-la-piel`, `otros-objetivos` (boca y garganta) | `null` con texto | 20 | 0 | 6 (5 grupos) | `aceite-por-compuesto-eo`, `cita-sin-resolver` (5) |
| Hipérico | Hierba de San Juan | `cuidado-de-la-piel`, `relajacion-estres` (pendiente), `otros-objetivos` (digestión) | alto | 20 | 0 | 4 (4 grupos) | `aceite-por-compuesto-eo`, `cita-sin-resolver` (4), `interacciones-graves-estres` |
| Consuelda | Consuelda | `otros-objetivos` (dolor e inflamación) | medio | 20 | 0 | 0 | - |
| Árbol del té | Árbol del té | `otros-objetivos` (boca y garganta), `cuidado-de-la-piel` | medio | 1 | 0 | 0 | - |
| Lavandín | Lavandula × intermedia (`la`) | - | `null` | 0 | 0 | 0 | `aceite-por-compuesto-eo`, `sin-datos-de-seguridad`, `sin-nombre-comun-es` |
| *Pelargonium sidoides* | Geranio africano | `alivio-respiratorio` | medio | 0 | 0 | 0 | - |
| Rodiola | Rodiola | `cansancio-y-fatiga`, `relajacion-estres` | `null` con texto | 4 | 0 | 0 | - |
| Bergamota | Bergamota | - | `null` | 0 | 0 | 0 | `grupo-partido`, `sin-datos-de-seguridad` |
| Almendro | Almendro | - | bajo | 1 | 0 | 0 | `aceite-por-compuesto-eo` |

Totales: 275 grupos, 0 pendientes y 66 citas sin resolver en 65 grupos. En la v4 había 69 grupos pendientes de 277. De las 66 citas sin resolver, 64 son `Woi.Syria`, una es `Uph` y una `Eb33: 000` (la página `000` no existe). Los emparejamientos de claves de los registros v7 repiten los de la revisión manual: `Woi.<n>` va a `WOI`, `Eb<vol>: <pág>` a `EB`, `Burkill,1966` a `Burkill, 1966` y `Nas` a `NAS2`.

Comprobaciones de la tarea 5.3 sobre los registros v7:

- Objetivos presentes en menta, árbol del té y caléndula.
- La bergamota es *Citrus × bergamia* (`citrus-x-bergamia`) y el almendro es `prunus-amygdalus`, sin datos del cerezo.
- Ningún dato de *L. latifolia* en la lavanda ni de *P. edulis* en la pasiflora (el texto de los registros no los contiene).
- El aceite esencial sale según `EO`: donde el único apoyo es el compuesto `EO` (caléndula, hipérico, lavandín, almendro y cicuta) el registro lleva `aceite-por-compuesto-eo`.
- El hipérico conserva `relajacion-estres` con `pendingReview` y el flag `interacciones-graves-estres`.
- Nombres visibles: Caléndula, Árbol del té, Hierba de San Juan, Eucalipto común y Toronjil; *Conium maculatum* queda con `sin-nombre-comun-es`.
- Las enfermedades graves llevan «Uso tradicional, sin eficacia demostrada: …» y las señales de riesgo van a `safety`: el veneno y los casos mortales de la cicuta y el ricino, lo abortivo del romero y el hipérico, la fototoxicidad del hipérico y lo cianogenético del ricino y la pasiflora.
- `safety` con nivel nulo y texto: eucalipto, caléndula, rodiola, pasiflora y melisa.

Costo y tiempo del prompt v7 (corrida del 2026-10-25, UTC):

| Lote | Plantas | Inicio y fin | Duración | Tokens del agente |
| --- | --- | --- | --- | --- |
| 1 | 10 | 02:03:21Z a 02:10:24Z | 7 min 3 s | 203.415 |
| 2 | 10 | 02:03:21Z a 02:08:23Z | 5 min 2 s | 166.665 |

El total es de 370.080 tokens, unos 18.500 por planta, con los lotes en paralelo y agentes del modelo balanceado. Es parecido a la v4 (unos 18.000) y sigue por encima de los 12.000 a 15.500 del piloto.

### Aprobación del usuario (tarea 5.5)

Se mostraron al usuario los 20 registros de la corrida de control con el informe de costo y de flags. Tras ver los registros y decidir, el 2026-10-24 el usuario respondió «3. Si hazlo» (aplicar sus decisiones, repetir una corrida de verificación y seguir) y «Continuemos con el plan original entonces». Con esa respuesta se aprobaron los 20 registros v7 y se pasó al grupo 6.

### Observaciones abiertas para el usuario

Son hallazgos de la repetición con el prompt v4. Todos quedaron resueltos con las decisiones del usuario (prompts v5, v6 y v7), salvo la nota del desdoblamiento de nombres que cierra la lista.

1. **Grupos pendientes (resuelto en el prompt v5, tarea 4.9).** 69 de los 277 grupos quedan pendientes y 68 de ellos tienen al menos una cita resuelta: casi siempre se suma `Woi.Syria`, que no tiene candidata, a las claves que sí se resuelven.
2. **Actividades sensibles (resuelto en el prompt v6, tarea 4.10).** Entre los usos aparecen actividades como Cancer, Tumor, Abortifacient, Fatality, Poison, Aphrodisiac y Diabetes. Desde la v6 las enfermedades graves llevan la fórmula «Uso tradicional, sin eficacia demostrada: <enfermedad>» y las señales de riesgo van a `safety` como advertencia (véase «Actividades sensibles»).
3. **`safety` nulo (resuelto en el prompt v5, tarea 4.9).** `safety` es `null` cuando ninguna entrada fija nivel, aunque la EMA traiga contraindicaciones; es el caso del eucalipto.
4. **`displayName` de la caléndula (resuelto en el prompt v7).** Salía «Botón de oro»; desde la v7 el criterio principal es el nombre más usado y genérico del paquete, así que debe salir «Caléndula».
5. **Falsos positivos de `EO` (resuelto en el prompt v7).** El compuesto `EO` de USDA activaba `oil` en el almendro y la cicuta, que podrían no ser aceites esenciales; desde la v7 un `oil` apoyado solo en `hasEo` lleva el `reviewFlag` `aceite-por-compuesto-eo`.
6. **Desdoblamiento de nombres de una enumeración de Wikipedia (pendiente, sin cambio de prompt).** En la corrida v7 un agente separó los nombres de una enumeración del resumen de Wikipedia y de ahí sacó uno que el texto no da como tal: de «manzanilla alemana, dulce o cimarrona» salió «manzanilla dulce». Es una observación menor, que no rompe ninguna regla del validador. No se cambia el prompt; queda anotada para la revisión de los `commonNames` de la generación completa (tarea 11.4).

### Prueba con Wikipedia desactivada (tarea 5.4)

Se repite el flujo con `wikipedia_es` desactivada en tres plantas de la corrida de control: lavanda, menta y manzanilla. Todo ocurre fuera de `data/seed/` y de `data/work/bundles/`, en `data/work/control/wiki-off/`; `sources.json` se cambia solo durante la prueba y se restaura al final (`git diff tools/catalog-seed/sources.json` queda vacío).

```sh
W=data/work/control/wiki-off
mkdir -p $W/seed/plants $W/bundles
cp data/work/control/v4/lote-*/{lavandula-angustifolia,mentha-x-piperita,matricaria-chamomilla}.json $W/seed/plants/
cp data/seed/goals.json $W/seed/goals.json
printf "lavandula-angustifolia\nmentha-x-piperita\nmatricaria-chamomilla\n" > $W/plants.txt
# desactivar: "enabled": false en wikipedia_es de tools/catalog-seed/sources.json
python3 -I tools/catalog-seed/cli.py bundles --plants $W/plants.txt --out $W/bundles
python3 -I tools/catalog-seed/cli.py plan --bundles $W/bundles --seed $W/seed
# regenerar los tres registros en $W/seed/plants con el prompt v4 y los paquetes nuevos
python3 -I tools/catalog-seed/cli.py validate --records $W/seed/plants --bundles $W/bundles
grep -i wikipedia $W/seed/plants/*.json
python3 -I tools/catalog-seed/cli.py plan --bundles $W/bundles --seed $W/seed
python3 -I tools/catalog-seed/cli.py seal --seed $W/seed
# restaurar "enabled": true y comprobar con git diff
```

- Rutas propias: `bundles --out`, `plan --bundles --seed`, `validate --records --bundles` y `seal --seed` admiten directorios propios, así que no hizo falta cambiar código. `seal` escribe `manifest.json` dentro de `--seed` y lee ahí `goals.json`, por lo que la semilla de prueba lleva una copia de `data/seed/goals.json`. Antes de desactivar la fuente se armaron los mismos tres paquetes con Wikipedia activa y el `plan` dio «0 plantas a regenerar»; los paquetes coinciden con los de `data/work/bundles/`.
- `plan` con Wikipedia desactivada: «3 plantas a regenerar», las tres con el motivo `bundleHash` (`lavandula-angustifolia`, `matricaria-chamomilla` y `mentha-x-piperita`). En cada paquete cambia solo la sección `descriptions` (queda vacía) y se retira el ref `wikipedia_es:<título>`; la identidad y las demás secciones no cambian.
- Regeneración: `displayName`, `commonNames` y `description` se redactaron a partir de los paquetes nuevos, sin copiar lo que dependía de Wikipedia; el resto del registro (usos, objetivos, seguridad, imagen) no depende de ella y se conservó, con el `bundleHash` nuevo y `refs` y `sources` recalculados desde los refs citados.
- `validate`: «3 registros, 0 con errores, 0 errores, 0 advertencias».
- `plan` después: «0 plantas a regenerar».
- `seal`: «manifest.json actualizado: 3 plantas». Las fuentes del manifiesto son `commons`, `efsa`, `ema_json`, `ema_pdf`, `tppt`, `usda`, `wcvp`, `wfo` y `wikidata`; `wikipedia_es` no figura. Los flags contados son `cita-sin-resolver` (2 plantas) y `sin-nombre-comun-es` (1).
- `grep -i wikipedia` sobre los tres registros solo encuentra la URL de la imagen de Commons (`https://upload.wikimedia.org/wikipedia/commons/...`), donde «wikipedia» es un tramo de la ruta del servidor de archivos de Wikimedia y no la fuente `wikipedia_es`. Commons sigue activa y la imagen es legítima, así que no se quitó. Filtrando esa URL (`grep -i wikipedia ... | grep -vi 'upload.wikimedia.org/wikipedia/commons'`) no sale nada; tampoco queda ningún ref ni dataset `wikipedia_es`.

| Planta | `displayName` antes | `displayName` ahora | `description` | Refs |
| --- | --- | --- | --- | --- |
| Lavanda | Lavanda (Wikipedia) | Lavandula angustifolia (`la`), con `sin-nombre-comun-es` | `null` (antes una frase de Wikipedia) | 31 a 30; sin `wikipedia_es:Lavandula angustifolia`; `commonNames` pierde «Lavanda» |
| Menta | Menta piperita (Wikipedia y Wikidata) | Menta piperita (solo `wikidata:Q156037`, el P1843) | `null` | 64 a 63; sin `wikipedia_es:Mentha × piperita`; `commonNames` pasa de 9 a 2 (se pierden los siete nombres de la primera frase del resumen) |
| Manzanilla | Manzanilla (Wikidata) | Manzanilla (sin cambio) | `null` | 81 a 80; sin `wikipedia_es:Matricaria chamomilla`; `commonNames` pierde «Manzanilla de Castilla» y «Manzanilla alemana» queda solo con el ref de Wikidata |

En las tres plantas, `sources` pierde `wikipedia_es` y `bundleHash` cambia; los demás campos son idénticos. La lavanda queda sin nombre común en español porque su único nombre en español venía del resumen de Wikipedia: es el resultado esperado de la política de solo el paquete. Con Wikipedia desactivada ya no hay `description` en ninguna de las tres, porque el prompt no permite construirla desde la taxonomía.

## Contrato del paquete que usa el validador

El validador solo depende de esta parte del paquete (véase «Paquetes por planta» para el resto): `refs`, `bundleHash`, `identity.proposedId`, `sections.regulatory[]` (`ref`, `therapeuticAreas`, `outcome`, `combination`), `sections.safety[]` (`source`, `level`, `humanToxicity` para TPPT y `severeInteractions` para la EMA), `sections.images[].ref`, `sections.descriptions[].url` y `sections.uses[]` (`activity` y, por grupo, `citations` con las claves cortas y `candidates`: un objeto de clave a lista de `{ref, citation}`). La marca `severeInteractions` la genera `bundles` con `safety.ema_interaction_class` (patrones de gravedad del mapa de seguridad v2) y la comprueba `tests/test_bundles.py`.

## Validador

`validate` comprueba cada archivo de `--records` (por defecto `data/seed/plants`) contra su paquete de `--bundles` (por defecto `data/work/bundles`, emparejado por `identity.proposedId`):

- el esquema (si falla, no se hacen las demás comprobaciones);
- que `id` es `identity.proposedId` y `bundleHash` el del paquete, y que el archivo se llama como el `id`;
- que todo ref citado existe en `refs` del paquete y en el subconjunto `refs` del registro, con el mismo dataset, etiqueta, licencia y `url`, y que todo ref de `wikipedia_es` con licencia CC BY-SA trae `url`;
- que cada objetivo tiene respaldo de la EMA (un ref de una ficha cuyo resultado, separado por `;`, incluye monografía o entrada de lista, que no es un producto combinado y cuya área, según el mapa, da ese objetivo y subárea), que `subarea` es nula salvo en `otros-objetivos`, y que no hay objetivos repetidos;
- que una planta con TPPT «strong toxic» o «very strong toxic» (valores separados por «, », prefijo antes del paréntesis) no tiene objetivos;
- que el objetivo `relajacion-estres` de una planta con interacciones graves en la EMA lleva `pendingReview` verdadero, y que todo objetivo con `pendingReview` tiene un `reviewFlag` cuyo `target` lo señala;
- que todo grupo con `pendingReview` tiene un `reviewFlag` con `target` `traditionalUses[<índice>]`, que un grupo es pendiente solo si ninguna de sus citas está resuelta (un grupo con una cita resuelta y `pendingReview` verdadero es un error, y uno sin ninguna resuelta y `pendingReview` falso también), que todo grupo con alguna cita sin resolver tiene el flag `cita-sin-resolver`, que toda cita apunta a un `usda_reference:*` del paquete (y a una candidata de esa clave cuando el paquete las trae) o está marcada «(sin resolver)», y que `activitySource` es una actividad literal del paquete;
- que la imagen tiene licencia CC0, dominio público, CC BY o CC BY-SA (se rechazan NC y ND), `attributionRequired` verdadero para CC BY y CC BY-SA, y es una imagen del paquete;
- que las actividades sensibles cumplen la lista (véase «Actividades sensibles»): fórmula en las enfermedades graves, señales de riesgo fuera de `traditionalUses` y presentes en `safety` con un `usda_use:*` de sus filas;
- que el nivel de `safety` sea el del paquete: si `level` no es nulo, es igual al más alto entre los `level` de las entradas de `sections.safety` (incluida la de USDA con señal letal); si es nulo, ninguna entrada fija nivel;
- que `safety` es coherente con el paquete: nulo solo con el flag `sin-datos-de-seguridad` y sin que ninguna entrada del paquete fije nivel, y con `level` nulo solo si ninguna entrada fija nivel (el esquema exige `text` no vacío y `refs` también con nivel nulo); un `safety` con contenido no lleva el flag `sin-datos-de-seguridad`.

Un `code` de `reviewFlags` que no esté en `flag-codes.json` (el catálogo cerrado que reproduce el prompt, con el `target` y el significado de cada código) es una advertencia, no un error. Las expresiones de dosis o eficacia (`dosis`, `mg`, `ml`, `gotas`, `cucharada`, `cura`, `trata`, `tratamiento`, `previene`, `elimina`, `alivia`, `eficaz` y similares) en los textos visibles son advertencias, no errores. El comando imprime errores y advertencias por planta y un resumen, escribe el informe completo con `--out` y termina con código 1 si hay algún error.

## Plan de regeneración

`plan` recorre los paquetes de `--bundles` y lista las plantas que no tienen registro en `<seed>/plants/<id>.json` o cuyo registro tiene otro `bundleHash`, otra `promptVersion` (la de `prompt/consolidate.md`) u otra `recordVersion` (la del esquema), con los motivos (`sin-registro`, `bundleHash`, `promptVersion`, `recordVersion`). Con `--json` imprime el plan como JSON. Sin cambios, la lista está vacía; subir la versión del prompt las pone todas en cola; un cambio de una fuente que altere un solo paquete deja solo esa planta.

## Sellado y manifiesto

`seal` escribe la semilla y su manifiesto. En orden: (1) si falta `<seed>/goals.json`, lo copia del catálogo versionado (`data/seed/goals.json`); un `goals.json` existente no se reescribe, porque el catálogo se edita a mano y el `seedHash` usa su JSON canónico; (2) con `--from <dir>` (repetible) importa los registros de esos directorios de trabajo; (3) lee `<seed>/plants/*.json` y `<seed>/goals.json`, comprueba que cada registro cumple el esquema, que su archivo se llama como su `id` y que su `promptVersion` es la del prompt vigente (si no, hay que regenerar antes de sellar); (4) reescribe cada registro con el formato estable y (5) escribe `<seed>/manifest.json`. Si algo falla en (1) a (3), no se reescribe nada de la semilla salvo lo ya importado y válido (la importación es todo o nada). Los archivos tienen claves ordenadas, sangría de 2 espacios y salto de línea final, sin marcas de tiempo, así que dos ejecuciones dan archivos idénticos byte a byte.

Importación de registros: `seal --seed data/seed --from data/work/control/v7/lote-1 --from data/work/control/v7/lote-2` toma los `*.json` de cada directorio (un archivo por planta, nombrado como su `id`) y los valida contra su paquete de `--bundles` (por defecto `data/work/bundles`) con las mismas reglas de `validate` y el esquema de `--schema` y el mapa de `--goals-map`. Un registro con errores, con un nombre de archivo distinto de su `id` o con un `id` repetido entre directorios detiene la importación y no entra ninguno. Las advertencias no la detienen. Un registro importado sustituye al que hubiera en `<seed>/plants/` con el mismo `id`. Los informes `*-validate.json` quedan fuera de los directorios de registros.

Campos del manifiesto:

- `formatVersion`: versión del formato del manifiesto (1).
- `sources`: las fuentes con `enabled: true` de `sources.json`, con `id`, `name`, `url` (la página del dataset, tomada de `pageUrl` de `sources.json`), `version`, `license`, `attribution` y `files` (`filename`, `size`, `checksum`). Una fuente activa sin snapshot fijado hace fallar el sellado; una desactivada no se lista.
- `promptVersion` y `recordVersion`: las del prompt y el esquema vigentes.
- `models`: los modelos distintos de los registros, ordenados (puede haber más de uno si se regeneró por tandas).
- `plantCount`: número de plantas.
- `reviewFlags`: para cada `code`, cuántas plantas lo tienen.
- `glossaryHash` y `glossaryCount`: solo si existe `glossary.json`; el sha256 del JSON canónico del glosario y su número de filas. No entran en el `seedHash`. Véase «Glosario de actividades».
- `seedHash`: `sha256:` más el sha256 de la concatenación UTF-8 de `plant\n<id>\n<JSON canónico del registro>\n` para cada registro ordenado por `id`, seguida de `goals\n<JSON canónico de goals.json>\n`. El JSON canónico tiene las claves ordenadas, separadores `,` y `:` sin espacios y caracteres sin escapar, así que no depende de la sangría de los archivos.

Ejemplo resumido (semilla provisional de la tarea 6.2):

```json
{
  "formatVersion": 1,
  "models": ["claude-sonnet-5-5"],
  "plantCount": 20,
  "promptVersion": 7,
  "recordVersion": 1,
  "reviewFlags": {"aceite-por-compuesto-eo": 5, "cita-sin-resolver": 10, "sin-nombre-comun-es": 2},
  "seedHash": "sha256:2dabef0b...",
  "sources": [
    {"id": "usda", "version": "Ag Data Commons 24660351, v1 (...)", "license": "CC0", "attribution": "...",
     "files": [{"filename": "Duke-Source-CSV.zip", "size": 6033990, "checksum": {"algorithm": "md5", "value": "45ae44a0..."}}]},
    {"id": "wikidata", "version": "Wikidata Query Service, consulta dirigida por nombre científico (P225); ...", "license": "CC0 1.0", "attribution": "...", "files": []}
  ]
}
```

Las fuentes de servicio en línea (`wikidata`, `wikipedia_es` y `commons`) van con su descripción de versión (la consulta y que cada respuesta se guarda con su fecha en la caché) y `files` vacío, sin checksum. En el manifiesto real `reviewFlags` lista los ocho códigos presentes y `sources` las diez fuentes activas.

La semilla provisional de la tarea 6.2 (`data/seed/plants/` y `manifest.json`, con los 20 registros v7 de la corrida de control) no se publica: el `push` a `main` despliega.

## Glosario de actividades

El glosario explica en la app los términos técnicos que aparecen como título de un grupo de `Usos` (Diurético, Astringente, Carminativo…). Sus textos salen de dos fuentes abiertas bajo CC BY-SA 4.0, nunca de conocimiento del modelo: Wikcionario en español (`wiktionary_es`) y, para los términos que este no tiene o define de forma circular o insuficiente, Wikipedia en español (`wikipedia_es`). Cambio de origen: `openspec/changes/activity-glossary/` (diseño D1 a D11).

### Archivos

- `glossary-terms.json`: la lista versionada. Cada término declara `activity` (la actividad tal como aparece en los grupos de uso) y `wiktionaryTitle`; `wikipediaTitle` si se consulta Wikipedia; la propuesta (`source` `wiktionary_es` con `sense`, o `wikipedia_es` con `mode` `literal` o `adapted`; un texto `adapted` lleva `text` y `evidence`) con su `reason`; y `approved` (`by`, `date`) cuando el usuario lo aprobó. Los excluidos van en `excluded` con `code`, `reason` y `date`; los patrones de eficacia que el usuario aprobó por término, en `approvedPatterns`. Solo los términos con `approved` entran en el glosario.
- `data/seed/glossary.json` (`catalog-glossary/1`): `format`, `license` (CC BY-SA 4.0), `licenseUrl`, `changes` y `rows` ordenadas por `key` (la forma base de la actividad: el texto antes del primer paréntesis, en minúsculas NFC, sin quitar acentos). Cada fila: `key`, `term`, `text`, `sourceId`, `sourceName` (`Wikcionario` o `Wikipedia`), `adapted`, `sense` (nulo en Wikipedia), `entryUrl` (con `oldid`), `revisionId`, `revisionTimestamp` y `retrievedAt`.
- `data/.cache/wiktionary_es/` y `data/.cache/wikipedia_es/glossary/`: las respuestas descargadas, con su revisión. Están ignoradas por Git, como las demás cachés.

### Comandos

```sh
python3 -I tools/catalog-seed/cli.py glossary-candidates --limit 40
python3 -I tools/catalog-seed/cli.py glossary-fetch --plan
python3 -I tools/catalog-seed/cli.py glossary-fetch --wait 300
python3 -I tools/catalog-seed/cli.py glossary-senses --term Diurético
python3 -I tools/catalog-seed/cli.py glossary-review --out openspec/changes/activity-glossary/review/glossary-review.md
python3 -I tools/catalog-seed/cli.py glossary-build
python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants
python3 -I tools/catalog-seed/cli.py seal
```

- `glossary-candidates` imprime las actividades visibles de `data/build/catalog.db` (solo lectura) más frecuentes que aún no están en la lista ni en excluidos, sin las sensibles.
- `glossary-fetch` descarga Wikcionario para todos los términos y Wikipedia solo para los que declaran `wikipediaTitle`: una petición a la vez, con pausa de al menos 1 segundo, `Retry-After`, reanudación (`_resume.json`) y el `User-Agent` genérico del proyecto, sin correo. Wikcionario cuesta dos peticiones por entrada hallada (el HTML y la hora de la revisión). `--plan` cuenta sin abrir la red; `--refresh <título>` vuelve a pedir una entrada, que es la única forma de cambiar una revisión fijada; `--source` limita a una fuente. Una segunda ejecución usa la caché y hace 0 peticiones.
- `glossary-senses` imprime, sin red, las acepciones numeradas de Wikcionario (con su marca semántica, y «IMPROPIA» si la entrada así la marca) y el extracto de Wikipedia de cada término, para proponer la acepción o el texto.
- `glossary-review` escribe la tabla que revisa el usuario: por término, los grupos y plantas que cubre, la fuente, la acepción o el artículo, el texto exacto, si es literal o adaptado, la URL de la revisión, las alertas del validador y la aprobación; más los excluidos y la cobertura.
- `glossary-build` arma `data/seed/glossary.json` sin red y de forma determinista, lo valida contra la caché y solo lo escribe si no hay errores.
- `validate` valida también `glossary.json` si existe junto a `plants/`, y comprueba que coincida con el manifiesto. `seal` agrega `glossaryHash` y `glossaryCount` al manifiesto sin tocar el `seedHash`, rechaza un glosario inválido y se niega a sellar sin el archivo si el manifiesto anterior lo declaraba.

### Reglas

- **Wikcionario.** El texto es literal: de la acepción elegida se retira el marcado, las notas y las listas de sinónimos, antónimos, usos y ejemplos, se normalizan los espacios y se recorta a la primera oración (sin cortar en abreviaturas como «etc.» o «p. ej.»). La acepción la propone un agente entre las reales de la entrada; no escribe texto.
- **Wikipedia.** Si la primera oración del artículo define bien el término, es el texto (`literal`). Si no basta, un agente escribe una paráfrasis de una o dos oraciones hecha solo con el extracto guardado (`adapted`), con la `evidence` literal en que se apoya. La app la marca «adaptado de Wikipedia».
- **Validación.** Error por dosis o posología (no se puede aprobar), por patrones de eficacia (`curar`, `tratar`, `prevenir`, `eliminar`, `aliviar`, `eficaz`, `efectivo`) salvo los aprobados por término, por enfermedades graves, por términos sensibles, por texto que no está en español o no termina en punto, por texto literal que no coincide con la caché y por evidencia que no está en el extracto. `emoliente` y `demulcente` muestran cómo se evita una mención de «tumores»: otra acepción u otro texto.
- **Licencia.** Cada fila lleva la URL de la revisión (`oldid`), cuyo historial lista a los autores; el glosario es CC BY-SA 4.0 e indica los cambios (marcado y notas retirados, recorte, paráfrasis marcada).
- **Cómo crece la lista.** Se agregan términos a `glossary-terms.json` (los candidatos salen de `glossary-candidates`), se ejecuta `glossary-fetch` (solo descarga lo nuevo), se propone, el usuario aprueba y se ejecutan `glossary-build`, `validate` y `seal`. El plan de regeneración no cambia, porque las fuentes del glosario no entran en los paquetes.

### Resultado con los datos reales (2026-10-29)

- 84 candidatos (83 de la selección por frecuencia y `Anticonceptivo`, que el usuario pidió incluir): 53 con explicación y 31 excluidos con su motivo.
- Las 53 explicaciones: 37 literales de Wikcionario, 5 literales de Wikipedia (Expectorante, Antídoto, Insecticida, Piscicida y Estíptico) y 11 adaptadas de Wikipedia (Estimulante, Sedante, Calmante, Purgante, Vermífugo, Emoliente, Colagogo, Antitusivo, Antibiótico, Hipnótico y Catártico).
- Cobertura por la forma base: 5.172 de los 17.160 grupos visibles (30,1 %) y 1.207 de las 1.456 plantas con usos visibles (82,9 %). Los términos excluidos habrían cubierto 915 grupos más.
- Los seis patrones de eficacia que el usuario aprobó por término son Antiséptico («prevenir»), Bactericida («elimina»), Vulnerario («curar»), Antidiarreico («previene»), Fungicida («elimina») y Parasiticida («eliminar»).
- La descarga tuvo varios 429 de Wikimedia, resueltos con `Retry-After`; se descargaron 83 entradas de Wikcionario (53 con acepciones, 29 sin entrada, 1 sin sección en español) y 50 consultas de Wikipedia (18 sin artículo).

## Generación completa (grupo 11)

La guía para repetir la generación con agentes de Claude Code, con el script del workflow, está en [`generation/README.md`](generation/README.md).

Decisión del usuario para la tarea 11.1 (2026-10-25): modo A, agentes de Claude Code con un workflow. Sus palabras: «El workflow me parece aceptable». Sobre las fases: «Dos fases me parece bien». Sobre el tope: «Lo que nos alcance con las ventanas de 5 horas que tenemos, no importa si nos gastamos todos mis tokens disponibles».

Preparación (tarea 11.2), sin red: se reconstruyeron los paquetes de todo el universo con `bundles` (2.355), porque los de las plantas fuera del control se habían armado antes de la limpieza de `utm_*` en las URL de imágenes. Los 20 paquetes de control conservan el `bundleHash` que guardan sus registros de `data/seed/plants/`. Después `plan --bundles data/work/bundles --seed data/seed --json` dio 2.335 plantas, todas con motivo `sin-registro`: el universo menos las 20 de control. El plan queda en `data/work/generation/plan.json`.

Fases:

- Fase 1: las plantas del plan con al menos una entrada de la EMA, es decir, con alguna entrada `ema:` en `data/work/universe/universe.json`. Es el mismo conjunto que el de las plantas cuyo paquete trae una sección `regulatory` no vacía (los dos criterios coinciden en las 189).
- Fase 2: el resto del plan.

Cifras:

| Fase | Plantas | Lotes de 10 | Archivos |
| --- | --- | --- | --- |
| 1 | 189 | 19 (el último de 9) | `data/work/generation/phase1/lot-NN.txt` y `lots.json` |
| 2 | 2.150 (2.146 sin registro y 4 de la semilla con otro `bundleHash`) | 215 (todos de 10) | `data/work/generation/phase2/lot-NNN.txt` y `lots.json` |
| Total | 2.339 | 234 | |

Los lotes siguen el orden del plan, por `id`. Cada `lots.json` lista los lotes con sus IDs.

Costo estimado: unos 18.500 tokens por planta según la corrida de control, es decir, unos 3,5 millones de tokens para la fase 1 y unos 39,7 millones para la fase 2 (unos 43 millones en total). El tope es el que alcance con las ventanas de 5 horas.

Reanudación: `plan` solo pone en cola las plantas sin registro (o con otro `bundleHash`, `promptVersion` o `recordVersion`), así que, si la ejecución se corta, se vuelve a correr `plan` y se retoman las pendientes. El workflow escribe los registros en `data/work/generation/phase<N>/records/`, un archivo por planta, y esos directorios se importan al final con `seal --from`.

Resultados de la fase 1: se generaron las 189 plantas con el prompt v7 en 19 lotes, en unos 14 minutos y con 3.255.434 tokens (unos 17.200 por planta, por debajo de los 18.500 estimados). El validador no dio errores en ningún lote. Los registros se importaron con `seal --from` por cada `data/work/generation/phase1/records/lot-NN`: la semilla quedó con 209 plantas (20 de control y 189 nuevas), `plan` ya no las lista (quedan las 2.146 de la fase 2) y `validate` sobre `data/seed/plants` da 0 errores y 0 advertencias. La base se construyó con `catalog-ingest build` y las pruebas de Rust, también las ignoradas, pasan. La medición está en `data/work/generation/phase1/report.md`. La tarea 11.3 sigue abierta hasta terminar la fase 2.

Mejora previa a la fase 2 (Wikidata por el nombre propio): de las 117 plantas sin aceptado, 96 (1 sin resolver y 33 sin emparejar, de las 34 `unresolved` o `unmatched`, y 62 de solo género) pasaron a consultarse por su nombre propio, y las 21 ambiguas siguen sin consultarse. Quedaron por descargar 96 nombres: 3 peticiones a Wikidata, 61 a Wikipedia (con cinco esperas por 429, de 23 a 44 s) y 2 a Commons, en unos 5 minutos y medio. Resultado: 61 plantas ganan un ítem de Wikidata (1 sin resolver, 9 sin emparejar y 51 de solo género), 8 un nombre en español (P1843), 56 un resumen de Wikipedia y 50 una imagen admitida de Commons; las otras 35 quedan en `sin-item`. El ejemplo es el diente de león (`taraxacum-officinale`), que WCVP da como sinónimo de una sección: ahora tiene el ítem Q131219, el artículo de Wikipedia y una imagen. Cambiaron los paquetes de esas 96 plantas, más el de `erythroxylum-havanense`, cuya fila de Wikidata y de Wikipedia faltaba en un `sources.db` desactualizado (la asignación no cambió; `extract` de las tres fuentes web lo corrigió). De la semilla afectan a 4 registros (`cetraria-islandica`, `fucus-vesiculosus`, `saccharomyces-cerevisiae` y `taraxacum-officinale`), cuyo `bundleHash` cambió, así que `validate` los reporta y `plan` los vuelve a listar. El plan de la fase 2 queda en 2.150 plantas (las 2.146 sin registro y esas 4) y 215 lotes de 10 en el orden del plan, en `data/work/generation/phase2/lot-NNN.txt` y `lots.json`.

Corrección del validador tras la fase 1: la palabra «gota» ya no es una expresión de dosis por sí sola, porque «Gout» se traduce como «Gota» y el validador marcaba la enfermedad. Ahora solo advierte con una cantidad delante («3 gotas», «unas gotas», «una gota») o en «gotas de». El prompt no cambió (sigue en la versión 7), así que los registros ya generados no se ponen en cola.

Resultados de la fase 2 (2026-10-25): el workflow lanzó 215 lotes de 10 plantas con el prompt v7 y un agente `Worker` por lote. Una pausa por el límite de uso cortó la corrida a mitad de camino (115 lotes ya terminados) y se reanudó con `resumeFromRunId`; la segunda ventana tardó unos 23 minutos de reloj para el resto. La corrida reanudada, que incluye los 115 lotes de la primera parte, gastó 13.343.485 tokens (1.755 llamadas a herramientas), unos 6.200 por planta. Escribió 2.149 registros (2.145 plantas nuevas y las 4 de la semilla cuyo paquete había cambiado: `cetraria-islandica`, `fucus-vesiculosus`, `saccharomyces-cerevisiae` y `taraxacum-officinale`) y rechazó 1, `malachra-alaceaefolia`, cuyo paquete no trae ningún ref (planta sin resolver con una sola fila `usda_taxon` y sin usos, nombres ni partes de USDA), de modo que el esquema no permite escribir su registro; queda pendiente y fuera de la semilla. Los 215 directorios validaron con 0 errores y 0 advertencias. Se importaron con `seal --from` por cada `data/work/generation/phase2/records/lot-NNN`: la semilla quedó con 2.354 plantas, `validate` sobre `data/seed/plants` da 0 errores y 0 advertencias, y `plan` solo lista `malachra-alaceaefolia`. La base se construyó con `catalog-ingest build` (2.354 plantas, hash `8bef65e992caa8dc68259aa922ca1cc54e6ad7c8f4363b6f89b4b223f0153d63`), y las pruebas de Rust, también las ignoradas, y las de Python pasan. Un agente borró por error, con `rm -rf`, la carpeta temporal de la sesión (sin afectar los registros). La medición y el resumen de las notas de los agentes están en el informe al usuario de esa corrida, no en un archivo. La tarea 11.3 queda cumplida; siguen abiertas la 11.4 y la 11.5.

Corrección posterior a la fase 2 (`fix1`): la medición encontró imágenes que la app no puede mostrar (10 PDF y 8 TIFF), autores con correos o texto de licencia (48) y dos plantas de *Averrhoa* con campos desplazados. Se añadieron el filtro `formato-no-mostrable` y la limpieza de autor (véase «Licencias» y «Autor de la imagen»), y se documentó que el desplazamiento de *Averrhoa* viene de la fuente. Con `extract` de las fuentes web, `wiki-assign` y `bundles` (sin red), `plan --seed data/seed` lista 112 plantas con otro `bundleHash` más `malachra-alaceaefolia`. De ellas, 68 tienen en su registro una imagen que ya no es admitida o un autor que cambió; las otras 44 cambian solo por las demás imágenes del paquete (autor limpio o nota de descartes). Los lotes de 10 están en `data/work/generation/fix1/lot-NN.txt` y `lots.json`, con las 68 primero.

Resultados de `fix1`: el workflow regeneró las 112 plantas en 12 lotes, en unos 6 minutos y con 1.910.681 tokens, con 0 errores del validador y 0 rechazos. Se importaron con `seal --from` por cada `data/work/generation/fix1/records/lot-NN` (01 a 12): los 112 registros sustituyeron a los anteriores y `validate` sobre `data/seed/plants` da 2.354 registros, 0 errores y 0 advertencias.

Estado final de la semilla (tarea 11.5): 2.354 plantas, `seedHash` `sha256:0c42c0a285dee2a6fba331e8ab1e32b076b6ced17d8e93814e6a93d386e9800a`. `plan --seed data/seed` solo lista `malachra-alaceaefolia`, que no tiene datos en ninguna fuente y queda fuera del catálogo. `catalog-ingest build` nativo y el `docker build` (etapa del catálogo, sin red) dan el mismo hash de contenido, `4be91c438ced8f41a07bc4873cc7562c869b5c16af44570d934f851bb7d5a639`, con 2.354 plantas, 15.144 nombres, 24.286 usos, 871 registros de seguridad, 1.860 imágenes, 43.638 referencias y 5.209 avisos de revisión. `cargo test --workspace --locked` (con y sin `--ignored`) y las 534 pruebas de Python pasan, y la imagen, arrancada con `--network none`, responde 200 en `GET /v1/plants/lavandula-angustifolia`.

Regeneración `fix2` (defectos de la QA): tras `fix1`, la QA del cambio encontró defectos que obligaron a regenerar plantas: usos recuperados por el defecto 3 (filas de ETHNOBOT que antes no llegaban a la planta), cobertura incompleta de los grupos de uso, fórmula de enfermedad grave mal escrita, cantidades con unidades en los textos, anotaciones de idioma de USDA en los nombres, `Nas` mal interpretado y Malesia. Se regeneraron 110 plantas en 11 lotes, con 3.038.129 tokens, 0 errores del validador y 0 rechazos, y se importaron con `seal --from` por cada `data/work/generation/fix2b/records/lot-NN` (01 a 11). Los agentes recibieron aclaraciones de la QA en el envoltorio por lote. Eran precisiones de reglas del prompt v7 y no reglas nuevas: la selección de grupos (orden del prompt y al menos min(20, N) grupos), la fórmula exacta de las enfermedades graves, textos sin cifras con unidades, la clave de cita `Nas` (NAS2 para China o Asia y NAS para los Andes, según los países del grupo), quitar las anotaciones de idioma de los nombres de USDA y «Malesia» como región de WCVP. Están en el envoltorio recomendado de [`generation/README.md`](generation/README.md).

Estado final tras `fix2`: 2.354 plantas, `seedHash` `sha256:141669c49aa34ab81041f093dc473cc8e9d512e4db716525709910354efedb44`; `validate` da 0 errores y 0 advertencias y `plan --seed data/seed` solo lista `malachra-alaceaefolia`. El hash de contenido de `catalog-ingest build` nativo y el del `docker build` (etapa del catálogo, sin red) son el mismo, `affdf01687d7aea1a1f0cae8c2b6fd942945609be0898ad53399c193a783818d`, con 2.354 plantas, 13.940 nombres, 24.568 usos, 873 registros de seguridad, 1.860 imágenes, 43.932 referencias y 17.526 grupos de uso. `cargo test --workspace --locked` (con y sin `--ignored`), `clippy` y las 545 pruebas de Python pasan.

Regeneración `fix3` (señales letales de USDA): por la decisión del usuario sobre CR-05, las señales letales de USDA (fatalidad, muerte, suicidio, homicidio) fijan el nivel alto mediante una entrada de seguridad de USDA en el paquete (mapa de seguridad v3), y el validador exige que el nivel del registro coincida con el más alto del paquete. El workflow regeneró las 57 plantas afectadas en 6 lotes, con 1.081.188 tokens, 0 errores del validador y 0 rechazos. Se importaron con `seal --from` por cada `data/work/generation/fix3/records/lot-NN` (01 a 06): las 57 quedaron con `safety.level` `alto`, `validate` sobre `data/seed/plants` da 2.354 registros, 0 errores y 0 advertencias, y `plan --seed data/seed` solo lista `malachra-alaceaefolia`.

Estado final tras `fix3`: 2.354 plantas, `seedHash` `sha256:2cbe59ea5db4026416e00d4d181d8e6c2fa5ec006feabea8bc6e076e2613a736`. El hash de contenido de `catalog-ingest build` nativo y el del `docker build` (etapa del catálogo, sin red) son el mismo, `7e6de3b58cdcbb0d3f0991838f9b089af7dd519b79f53d8840882d4d801a406c`, con 2.354 plantas, 13.936 nombres, 24.572 usos, 873 registros de seguridad, 1.860 imágenes, 43.940 referencias y 17.526 grupos de uso. `cargo test --workspace --locked` (146 pruebas), las 3 pruebas ignoradas de la base real y las 556 pruebas de Python (11 omitidas) pasan.

Regeneración `fix4` (DEF-03 del cambio 2): la QA encontró seis registros que decían «no tóxica» en `safety.text` sin la cláusula de que ese dato no hace segura a la planta. El validador ganó una regla con nivel de error: si `safety.text` afirma la no toxicidad («no tóxica», «no es tóxica», «sin toxicidad», «atóxica», «nontoxic», «ausencia de toxicidad»), debe contener «este dato no la hace segura» (el prompt v7 no fija la redacción; se usa la de `abutilon-theophrasti`). Sobre toda la semilla la regla marcó 10 registros, los 6 de la QA (`reynoutria-japonica` y cinco `brassica-*`) y 4 más: `quercus-petraea`, `quercus-pubescens`, `quercus-robur` («no son tóxicas para las personas») y `valeriana-locusta` («nontoxic»). Los 10 se regeneraron a mano desde su paquete con el registro anterior como base: solo cambió `safety.text`, que añade la cláusula sin perder información ni citas. Se importaron con `seal --from data/work/generation/fix4/records`: `validate` sobre la regeneración y sobre `data/seed/plants` da 0 errores y 0 advertencias (2.354 registros) y `plan --seed data/seed` solo lista `malachra-alaceaefolia`.

Estado final tras `fix4`: 2.354 plantas, `seedHash` `sha256:d12807ee8f06b5239986b030ff722e2376abaffdec74bae56b444bd0b0aaff61`; el hash de contenido de `catalog-ingest build` es `a008e3ea474053907bba871577ad9256e0fbc3db99c784548952bf01b1690e75`. Las 560 pruebas de Python (11 omitidas) y las pruebas ignoradas de la base real pasan.

Regeneración `fix5` (revisión del usuario en la tarea 6.5 del cambio 3): el usuario aprobó corregir nombres para mostrar de la semilla que se veían mal en la app (OBS-06 de la QA). Se reescribieron a mano desde su paquete, con el registro anterior como base, 4 plantas; solo cambiaron `displayName` y el orden de `commonNames` (el nombre elegido pasa al frente, y el anterior se conserva como nombre común): `chamaemelum-nobile` (Manzanilla a Manzanilla romana), `urtica-urens` (Ortiga a Ortiga menor), `verbascum-thapsus` (Gordolobo a Verbasco) y `primula-elatior` (Primavera a Bellorita encarnada). No se cambiaron `silybum-marianum` (el paquete solo trae «Cardo de maria» y el prompt solo permite normalizar tildes si la forma con tilde está en el paquete), `arnica-montana` y `capsella-bursa-pastoris` (el paquete no trae «Árnica» ni «Bolsa de pastor» en español), las cuatro *Grindelia* con objetivo (el único nombre, «grindelia», es el del género en latín, que el prompt prohíbe) ni `glycyrrhiza-uralensis` (sin otro nombre en español). Se importaron con `seal --from data/work/generation/fix5/records`: `validate` sobre la regeneración y sobre `data/seed/plants` da 0 errores y 0 advertencias (2.354 registros) y `plan --seed data/seed` solo lista `malachra-alaceaefolia`.

Estado final tras `fix5`: 2.354 plantas, `seedHash` `sha256:e6c7b820653a1d0eded4a53212e9a59afa5870fdbccf6d6c118362e04b1e8e78`; el hash de contenido de `catalog-ingest build` es `529e7960cef0508b3ba218b7c34ea03413c2bbbd5310c632215b69501d1100e7`. `cargo test --workspace --locked` y las pruebas ignoradas de la base real pasan.

Regeneración `fix6` (decisión del usuario, 2026-10-30): el uso tradicional «Café» de la semilla es la traducción literal de la etiqueta «Coffee» de USDA Dr. Duke y no se entendía; por las plantas que lo tienen (*Senna occidentalis*, quimbombó, achicoria, cacao, yerba mate y otras) indica que la planta se usa para preparar una bebida tipo café o como sucedáneo del café. El usuario decidió mostrar la actividad como «Sucedáneo del café». Se reescribieron a mano, con el registro anterior como base, los 36 registros con un grupo cuya `activity` era «Café» (todos con `activitySource` «Coffee»; ningún «Coffee» se tradujo de otra forma, ningún «Café» tenía otro origen y ninguna planta tenía ya «Sucedáneo del café»): solo cambió `activity` de ese grupo, sin tocar otros campos, grupos ni citas. Plantas: `abelmoschus-esculentus`, `brosimum-alicastrum`, `canavalia-ensiformis`, `ceratonia-siliqua`, `cicer-arietinum`, `cichorium-intybus`, `coffea-arabica`, `diospyros-kaki`, `diospyros-virginiana`, `elymus-repens`, `euphorbia-lathyris`, `gleditsia-triacanthos`, `hordeum-vulgare`, `ilex-paraguariensis`, `ligustrum-japonicum`, `lupinus-angustifolius`, `mucuna-pruriens`, `paullinia-cupana`, `phoenix-dactylifera`, `phoradendron-juniperinum`, `phragmites-australis`, `quercus-robur`, `quercus-stellata`, `rosa-canina`, `sabdariffa-gossypiifolia`, `secale-cereale`, `senna-occidentalis`, `senna-tora`, `silybum-marianum`, `simmondsia-chinensis`, `sorbus-aucuparia`, `taraxacum-officinale`, `tephrosia-purpurea`, `theobroma-bicolor`, `theobroma-cacao`, `theobroma-speciosum`. Se importaron con `seal --seed data/seed --from data/work/generation/fix6/records`: `validate` sobre la regeneración y sobre `data/seed/plants` da 0 errores y 0 advertencias (2.354 registros), `plan --seed data/seed` solo lista `malachra-alaceaefolia`, y `glossary.json` y `glossaryHash` no cambian. La regla queda anotada en `generation/README.md`.

Estado final tras `fix6`: 2.354 plantas, `seedHash` `sha256:770ff1c43d3bd951136c926c1f185a67a17ec037414bda65b2ac5bb3beee6b96`; el hash de contenido de `catalog-ingest build` es `ebef17dc54c8e06fd9ebec95e9b3459acf1e253a82f29ae0cba02e7c10207fe0`. En la base no queda ninguna actividad «Café» y hay 36 grupos «Sucedáneo del café». `cargo test --workspace --locked` y las pruebas ignoradas de la base real pasan.

## Extracción de seguridad de los PDF de la EMA (spike 3.1)

El spike de la tarea 3.1 (detalle en [`tools/catalog-seed/spikes/ema-pdf/README.md`](tools/catalog-seed/spikes/ema-pdf/README.md)) comprobó si se pueden extraer de los PDF de la EMA las secciones 4.3 (contraindicaciones), 4.4 (advertencias y precauciones) y 4.5 (interacciones), con su numeración y sin mezclar columnas.

- Se cumple el criterio de D9 en los 8 PDF de la muestra (7 monografías, entre ellas *Hyperici herba*, y 1 declaración pública) con `pdfminer.six`, leyendo las coordenadas de cada línea para separar la columna de uso bien establecido de la de uso tradicional.
- `pypdf` y `pdfminer.six` en texto plano no bastan: `pypdf` concatena las columnas sin etiquetarlas en las monografías con dos columnas con contenido (hipérico, menta, valeriana) y `pdfminer.six` entrelaza líneas en la sección 4.5 del hipérico.
- La declaración pública de *Citrus bergamia* no tiene secciones de seguridad: se registrará como «declaración pública sin datos de seguridad» y no se inventarán secciones vacías.
- La EMA limita las descargas: hay que esperar unos 15 segundos entre PDF, responde 429 con `Retry-After` y a veces entrega una página HTML de error en lugar del PDF, así que antes de cachear un archivo se comprueba que empiece por `%PDF-`.
- Herramienta recomendada para la tarea 3.3: `pdfminer.six` con `extract_pages()` y coordenadas (modo `pdfminer-cols` del spike), solo para el desarrollador. `pdftotext -layout` no se probó y no es necesario.

## Fuentes admitidas y descartadas

El verificador (`catalog_seed/sources.py`) rechaza cualquier fuente que no esté en la lista de admitidas.

- Admitidas: `usda`, `wcvp`, `wfo`, `ema_json`, `ema_pdf`, `tppt`, `efsa`, `wikidata`, `wikipedia_es`, `wiktionary_es` (solo para el glosario) y `commons`.
- Descartadas (mensaje específico): AromaDb, EssOilDB, sCentInDB, FDA PPDB, Comisión E, OMS/WHO, NHPID, iNaturalist y DrugBank.

## Resolvedor taxonómico y universo (tareas 2.1 a 2.6)

El paquete `catalog_seed/taxonomy/` resuelve nombres científicos al aceptado de WCVP (con WFO de respaldo) y arma el universo de plantas. Es biblioteca estándar de Python 3.9 y no usa la red.

### Normalización (`names.py`)

- `parse_name` normaliza a NFC y separa género, especie, rango y epíteto infraespecífico, autor y autor de la especie. Decodifica entidades HTML, reconoce el rango canónico (`subsp.`, `var.`, `f.`, ...) y se queda con el último marcador, separa marcadores pegados al epíteto y el autor pegado al epíteto (`Lavandula roseaL.`), completa los trinomios sin marcador, reconoce los autónimos y descarta cultivares entre comillas o con `cv.`.
- Un híbrido (`×`, `x` o `+`) es una marca del nombre, no parte de la clave. `aggr.`, `s.l.` y `s.str.` también quedan como marca. `sp`/`spp` y los nombres de un solo término son «solo género» y no se buscan.
- Las claves de búsqueda son `key_full` (género, especie, rango y epíteto infraespecífico, en minúsculas) y `key_binomial`. Al cargar el índice se aplican las mismas reglas a WCVP y WFO, así que las dos claves coinciden.
- `split_source_names` (y `split_source_cell`, que además devuelve las notas de lo que cambió) separa una celda con varios nombres: por `;` y por coma cuando lo que sigue parece otro nombre, expande los géneros abreviados de la EMA (`C. laevigata`) y descarta los fragmentos de menos de 4 caracteres. Reglas de las celdas de la EMA:
  - Una celda que empieza por `Combination` no aporta especies (antes solo se descartaba el fragmento que la abría, y `Thymus zygis L. and Primula veris L.` pasaba como nombre).
  - Los nombres que la celda marca como sinónimos no son entradas: se descartan los grupos `(syn. ...)` completos, con paréntesis anidados y con todo lo que sigue hasta el final de la celda si el paréntesis nunca se cierra (`verbenae-citriodorae-folium` queda solo con *Aloysia citrodora*), y los fragmentos `syn. ...` (`Cynara scolymus`, `Paullinia sorbilis`).
  - `Género [various species including G. a L.; G. b L.]` se expande a las especies listadas, con el género completo (`salicis-cortex` da *Salix purpurea*, *S. daphnoides* y *S. fragilis*, con autores limpios).
  - `(various species)` y `and Género (various species)` se descartan: solo salen las especies nombradas. `aloes-folii-succus-siccatus` da únicamente *Aloe barbadensis* Mill., porque la celda no nombra ninguna otra especie y una entrada de solo género crearía una planta `aloe` sin objetivo; las demás especies de *Aloe* entran por otras fuentes.
  - `clean_author` (usado por `parse_name`) limpia el autor: quita los grupos finales entre paréntesis que siguen a un autor (`Bertol. (V. thapsiforme Schrad)` queda `Bertol.`; `(Vent.) Schott et Endl. (C. vera K. Schum.)` queda `(Vent.) Schott et Endl.`), la cola en minúscula tras coma (`(L.) Merr., oleum`) y el autor duplicado (`L.L.`). Conserva el autor del basiónimo, que va al principio (`(L.) Moench`). El flag es `author_note_removed` y `ParsedName.author_removed` guarda lo quitado.

### Índice (`index.py`)

`build_index` carga en `data/work/taxonomy.db` (unos 1 GB, unos 25 s) los nombres y la distribución de WCVP y la clasificación de WFO. Descarta las filas de rango superior a especie y las de epíteto no interpretable (WCVP: 42.142 de género o incompleta y 13 de epíteto inválido; WFO: 57.249 de rango superior o incompleta y 29 de epíteto inválido). Queda con 1.406.829 nombres de WCVP, 1.995.338 filas de distribución y 1.606.736 nombres de WFO. El metadato del índice guarda la versión del formato y el checksum de WCVP y de WFO con que se hizo. `Backbone` lee un backbone de solo lectura: `lookup(key_full)`, `get(id)`, `synonyms(id)` y `distribution(id)`. Cada fila lleva estado, aceptado, `homotypic` (solo WCVP), basiónimo, familia y rango.

### Resolución (`resolver.py`)

- `resolve` busca la clave completa y, si no hay candidatos, la clave de reserva de los autónimos y después el binomio (marca `fallback_binomial`). Cada candidato sigue su cadena de aceptados hasta un nombre aceptado.
- Prioridad por estado: aceptado, luego sinónimo, luego ilegítimo, inválido u ortográfico con aceptado, luego mal aplicado. Los nombres sin aceptado utilizable quedan `unresolved`.
- Desempate por autor: se compara apellido por apellido, el basiónimo con el basiónimo y la combinación con la combinación, con prefijo de 3 letras y `L.` igual a `Linnaeus`; el puntaje debe ser 0,5 o más. Si varios candidatos empatan en estado y apuntan a aceptados distintos, el nombre es `ambiguous` y no se fusiona con ninguno. Un sinónimo con otro candidato hacia un aceptado distinto también es ambiguo salvo que el autor desempate.
- `resolve_name` aplica WCVP primero. Si WCVP no encuentra el nombre, prueba las variantes ortográficas del epíteto (`-ii`/`-i`, `-us`/`-a`/`-um`, `ph`/`f`, ...), que se aceptan solo si todas dan el mismo aceptado y quedan marcadas `orthographic_variant`. Si WCVP sigue sin resolver (no encontrado, ambiguo o sin aceptado) y WFO da un único aceptado, se usa el de WFO con la marca `wfo_fallback`. Si los dos resuelven pero aceptan nombres distintos, se conserva el de WCVP con `backbone_disagreement`. Nunca se mezclan IDs de los dos backbones: `backbone` dice cuál dio el resultado.
- Coincidencia aproximada (`resolve_fuzzy`, flag `fuzzy_match`): es el último recurso en WCVP y solo se aplica cuando el nombre no tiene ningún candidato, ni siquiera con las variantes ortográficas, y antes del respaldo de WFO. Busca (a) un epíteto de especie con distancia de edición pequeña dentro del mismo género o (b) un género con distancia 1 y el epíteto exacto. La distancia cuenta inserción, borrado, sustitución y transposición adyacente. Umbrales: epíteto de menos de 5 letras no se intenta; de 5 a 7 letras, distancia 1; de 8 o más, distancia 1 o 2; género de 5 letras o más, distancia 1. Se toma la distancia mínima en la que existe alguna fila y se exige un único aceptado a esa distancia; si hay dos o más aceptados distintos (o un homónimo sin resolver), el nombre es `ambiguous` con `fuzzy_match` y no se elige ninguno. El resultado lleva `fuzzy` (`distance`, `kind` `epíteto` o `género`, `key`) y una nota. No corrige erratas del epíteto infraespecífico. Desactivar `use_variants` desactiva también la coincidencia aproximada (o `use_fuzzy=False`). Como corre antes del respaldo de WFO, un nombre que WFO tiene exacto pero WCVP no puede pasar por la coincidencia aproximada de WCVP (en los datos reales les pasó a 9 entradas de USDA, listadas en el informe).
- Aceptado de rango superior a especie: si un nombre es sinónimo de un aceptado que el índice no carga (solo guarda especies e inferiores), queda `unresolved` con el flag `accepted_above_species` y la nota «aceptado de rango superior a especie (plant_name_id N)». La planta conserva su nombre y su ID (`taraxacum-officinale`, cuyo aceptado en WCVP es la sección 2916959). El índice no guarda el nombre de ese aceptado; leerlo desde el CSV de WCVP queda como mejora si hace falta.

### Universo, colisiones, IDs y alias (`universe.py`, `ids.py`)

- `build_universe(entries, wcvp, wfo, rules=...)` resuelve las entradas y agrupa las que llegan al mismo aceptado. El propio aceptado y sus sinónimos homotípicos (`homotypic_synonym` verdadero en WCVP o mismo basiónimo) se fusionan siempre. Los sinónimos heterotípicos que son homotípicos entre sí forman un miembro (con el ID y el nombre de su mejor fila, el basiónimo si está en el grupo) y la regla de colisiones decide si se fusiona con la planta del aceptado (flag `fusion-heterotipica`) o queda como planta propia (flags `split_group` y `grupo-partido`); véase «Regla de colisiones». Un grupo sin el propio aceptado ni homotípicos, con un solo miembro heterotípico, no tiene colisión: queda con el aceptado. `rules` son las decisiones y excepciones como datos (`CollisionRules`); sin ellas, todo heterotípico de un grupo con colisión es planta propia.
- Las entradas sin resolver (ambiguas, sin resolver o solo género) son plantas con la identidad de la fuente, con flags `homonym_unresolved`, `unresolved`/`unmatched` o `genus_only`.
- El ID es `plant_slug` del nombre aceptado de WCVP (`×` y `+` como `x`, `-` como separador). Si dos plantas terminan con el mismo ID, `build_universe` lanza `UniverseError` y el comando falla sin escribir nada.
- Los alias son el slug del nombre literal de cada entrada (el `TAXON` de USDA) cuando difiere del ID. Se descartan los que igualan el ID de otra planta y los que quedarían en dos plantas (`Universe.discarded_aliases`).
- `Universe.assign(nombre, autor)` asigna una fila de uso o de otra fuente a una planta. En un grupo partido el orden es: misma clave de nombre, miembro homotípico con el mismo basiónimo, miembro que es el propio aceptado y, si ninguno aplica, queda sin asignar (`Universe.unassigned`) y marca el grupo con `unassigned_rows`. Un heterotípico fusionado aporta sus claves y sus filas del backbone a la planta del aceptado, así que sus filas (y las de sus homotípicos) llegan a ella. La tarea 3.2 la usa para repartir los usos de USDA (véase «Asignación de USDA y citas candidatas») y el armado de paquetes (3.5) para las filas de TPPT y EFSA.

### Regla de colisiones (criterio de Wikipedia)

Cuando varias entradas resuelven al mismo aceptado, `build_universe` aplica esta regla (D5 del diseño y requisito «Regla de colisiones y separación de plantas» de la spec):

- El propio aceptado y sus sinónimos homotípicos se fusionan siempre.
- Un miembro heterotípico (un sinónimo heterotípico, o varios que son homotípicos entre sí) queda como planta propia, con el ID y el nombre científico de su mejor fila y los flags `split_group` y `grupo-partido`, solo si se cumple una de dos condiciones: su nombre científico tiene un artículo propio en Wikipedia en español (existe, no es una redirección y es distinto del artículo del nombre aceptado del grupo, también tras seguir las redirecciones) o figura en la lista de excepciones «separar siempre».
- Si no, se fusiona con la planta del aceptado: su nombre queda como sinónimo y como alias (el alias se descarta si iguala el ID de otra planta, como siempre), sus entradas pasan a la planta y esta lleva el flag `fusion-heterotipica` (`reviewFlag` con el código `fusion-heterotipica`, `target` `scientificName` y los nombres fusionados en el mensaje) para revisión humana.
- En un grupo sin el propio aceptado, los miembros fusionados forman la planta del aceptado (con su ID y nombre) y los separados siguen siendo plantas propias.

Dos archivos versionados en `tools/catalog-seed/` llevan los datos de la regla. Ninguno de los dos se genera en cada corrida:

- `collision-decisions.json` (`catalog-collision-decisions/1`) guarda la decisión de cada miembro, agrupada por la clave del aceptado (`groups.<clave del aceptado>`, con `accepted` y `acceptedEvidence`) y por la clave del nombre del miembro (`members.<clave>`). Cada miembro lleva `name`, `decision` (`fuse` o `separate`), `reason`, `evidence` y `date`. Los motivos de `fuse` son `redireccion` (el artículo del nombre es una redirección), `sin-articulo` (no existe, o es una página de desambiguación) y `articulo-compartido` (tiene artículo propio, pero el del aceptado redirige a él o es el mismo); los de `separate` son `articulo-propio` y `excepcion`. La evidencia es una entrada por título consultado: `title`, `exists`, `redirect`, `target` (el título final tras seguir las redirecciones), `disambiguation` y `date`. Las claves de grupo y de miembro son las claves de nombre del resolvedor (en minúsculas, sin autor ni signo de híbrido).
- `collision-exceptions.json` (`catalog-collision-exceptions/1`) lista los nombres que se separan siempre, cada uno con su motivo. La lista inicial, que el usuario aprobó y revisa en el diff, es: *Brassica napus* var. *napobrassica*, *Brassica oleracea* var. *acephala*, *Brassica chinensis*, *Brassica pekinensis* (*B. rapa*), *Citrus meyeri*, *Foeniculum vulgare* var. *dulce*, *Grindelia humilis*, *Lactuca sativa* var. *capitata*, *Origanum creticum* y *Origanum vulgare* var. *hirtum*.

Comportamiento:

- `resolve` lee los dos archivos y no abre la red. Un miembro sin decisión registrada (un grupo nuevo, o sin datos de Wikipedia) usa la regla conservadora: planta propia con flag. El informe lo lista en «Heterotípicos sin decisión registrada», y en `report.json` está en `collisions.decisions.undecidedMembers`. Las decisiones registradas no dependen de que Wikipedia esté activada ni de lo que Wikipedia diga después: los IDs y la composición de las plantas no cambian por eso.
- `collisions-decide` es el comando con red. Calcula los miembros sin decisión con las reglas actuales, consulta es.wikipedia.org solo para los títulos de esos grupos y agrega las decisiones al archivo. Nunca sobrescribe una decisión registrada: cambiar una es editar el archivo a mano (y volver a ejecutar `resolve`). Si todos los grupos ya tienen decisión, no consulta nada.
- La consulta usa la API de MediaWiki (`https://es.wikipedia.org/w/api.php`, `action=query`, `titles=` por lotes de hasta 50, `redirects=1`, `prop=pageprops` y `format=json`) a través de `wiki.py` (`WikipediaTitlesStep`): una respuesta por título en `data/.cache/wikipedia_es/titulos/`, límite de peticiones con `Retry-After`, estado de reanudación en `_resume.json` y el mismo `User-Agent` genérico, sin datos personales. Un 429 o 503 detiene el comando con código 2 y sin cambiar el archivo; se vuelve a lanzar después de la hora indicada. Por cada nombre prueba su título y, en los híbridos, también la forma con la `×` pegada o separada del epíteto y la forma sin la marca (`Citrus × sudachi`, `Citrus ×sudachi` y `Citrus sudachi`; en Wikipedia en español muchos artículos de híbridos están sin `×`). Los nombres que se prueban son el de WCVP y los nombres de origen de las entradas del miembro (para el aceptado, los de sus entradas propias y homotípicas), tal como vienen de USDA o la EMA y sin autor, si difieren del de WCVP.
- Con `wikipedia_es` desactivada en `sources.json` (`enabled: false`), `collisions-decide` no consulta nada, lo dice y no cambia el archivo.
- Si varias variantes de título dan artículo, cada una se evalúa con el mismo criterio: M se separa si alguna tiene artículo propio distinto de todos los artículos de A (tras seguir las redirecciones); si todas las que tienen artículo propio comparten artículo con A, se fusiona por artículo compartido; si solo hay redirecciones, por redirección; si ninguna existe, sin artículo.
- El criterio, para un miembro M frente al aceptado A del grupo: si M está en las excepciones, `separate`/`excepcion`; si M tiene artículo propio distinto del de A, `separate`/`articulo-propio`; si M tiene artículo propio y el de A es el mismo (A redirige a M), `fuse`/`articulo-compartido`; si M es una redirección, `fuse`/`redireccion`; si no existe, `fuse`/`sin-articulo`. Se comparan los títulos finales tras seguir las redirecciones. Las excepciones se aplican aunque el nombre tenga o no artículo, y su evidencia también se guarda.
- Asignación de filas: las filas de uso y de otras fuentes cuyo nombre es un heterotípico fusionado van a la planta del aceptado (`Universe.assign` por las claves y las filas del backbone que la planta absorbió, `wiki_assign.py` por `fusedMatchedIds` y `usda_assign.py` por la entrada `usda:<FNFNUM>` y por `Universe.assign`).

Resultado con los datos reales (WCVP v16, WFO 2026-06, USDA y EMA de la caché; `collisions-decide` del 21 de octubre de 2026, 4 peticiones a Wikipedia en total, 189 títulos; la primera pasada probaba solo el nombre de WCVP y sus formas con `×`, y la segunda agregó la forma sin marca y los nombres de origen de las entradas, que cambió dos decisiones):

| Cifra | Antes (todo heterotípico es planta propia) | Con el criterio de Wikipedia |
| --- | --- | --- |
| Plantas del universo | 2.406 | 2.355 |
| Plantas `heterotypic` | 75 | 23 |
| Grupos partidos | 56 | 11 |
| Grupos con al menos un heterotípico fusionado | 0 | 45 |
| Miembros heterotípicos (decisiones) | 75 sin regla | 75 decididos en 56 grupos |
| Separados por artículo propio | 75 | 13 |
| Separados por excepción | 0 | 10 |
| Fusionados | 0 | 52: 24 por redirección, 27 sin artículo y 1 por artículo compartido |
| Sin decisión | 75 | 0 |
| IDs actuales que se conservan como ID / pasan a alias / se pierden | 1.790 / 586 / 0 | 1.747 / 628 / 1 (`malachra-alaceaefolia`, sin datos) |
| IDs repetidos; `lavandula-angustifolia` | ninguno; presente | ninguno; presente |

Se separan por artículo propio la bergamota (*Citrus × bergamia*), la lima (*C. × limetta*), la naranja (*C. × sinensis*), el pomelo (*C. × paradisi*), *C. × sudachi* y *C. × sphaerocarpa* (su artículo existe sin la `×`: «Citrus sudachi» y «Citrus sphaerocarpa»), el brócoli (*Brassica oleracea* var. *italica*), el repollo (*B. oleracea* var. *capitata*), *B. oleracea* var. *gemmifera*, var. *gongylodes* y var. *viridis*, *Grindelia robusta* y *Tagetes patula*. Las diez excepciones quedan separadas. Se fusionan, entre otras, *Cinnamomum zeylanicum* (redirige a *C. verum*), *Ocimum sanctum*, *Aloe barbadensis*, *Commiphora molmol* y *Thevetia peruviana* (tiene artículo, pero el de *Cascabela thevetia* redirige a él). La lista completa, con la evidencia de cada una, está en `collision-decisions.json`.

### Comando `resolve`

```sh
python3 -I tools/catalog-seed/cli.py resolve
```

- Entradas: cada `usda_taxon` de `data/work/sources.db` (nombre = `TAXON`, autor = `TAXAUTHOR`) y cada especie de las fichas de la EMA (`ema_herbal`, celda `botanical_name` separada con `split_source_names("ema", ...)`). Una especie de la EMA que ya está en USDA no crea una planta: se une a la que ya existe. Una especie que ningún nombre de USDA alcanza crea una planta nueva. Es el criterio por identidad resuelta, no por texto: si la EMA nombra un sinónimo heterotípico de una planta de USDA, el sinónimo es una planta propia con la regla de colisiones.
- Combinaciones de la EMA: las fichas cuyo `botanical_name` empieza por `Combination` o está vacío no aportan especies, porque no tienen objetivos propios y sus especies ya están en monografías simples. La ficha fusionada `hyperici-herba` (marcada como combinación al deduplicar, pero formada por dos monografías simples, *Hypericum perforatum* y *Cimicifuga racemosa*) sí aporta las suyas. Son 7 fichas sin especies de las 204.
- Índice: usa `data/work/taxonomy.db` si su metadato coincide con los checksums de WCVP y WFO de `sources.json`; si falta o cambió alguno, lo recrea desde la caché verificada (`require_verified_files`, sin red). `--rebuild-index` fuerza la recreación.
- Salidas en `data/work/universe/` (`--out-dir`): `universe.json`, `report.json` y `report.md`. Compara los IDs con `data/build/catalog.db` si existe (`--catalog-db`), solo en lectura. Termina con código 1 si hay IDs repetidos o falta `lavandula-angustifolia`.
- Lee `collision-decisions.json` y `collision-exceptions.json` (`--decisions` y `--exceptions` cambian las rutas) y aplica la regla de colisiones sin abrir la red. El informe cuenta los grupos decididos, los miembros fusionados y separados (por motivo) y lista los miembros sin decisión, que quedan como planta propia con flag.
- Las opciones `--db` y `--taxonomy-db` cambian el SQLite de las extracciones y la ubicación del índice.

### Formato de `universe.json` (`catalog-universe/1`)

- Raíz: `format`, `inputs` (`wcvp` y `wfo` con `<algoritmo>:<checksum>`, `usda` y `ema_json` con la versión de la extracción, `indexVersion`, y `collisionDecisions` y `collisionExceptions` con el sha256 de los dos archivos de la regla de colisiones, o null si no existen), `checks` (`duplicate_ids` y `lavandula-angustifolia`), `plantCount` y `plants`, ordenadas por `id`. No lleva fechas, así que la salida es determinista.
- Planta: `id`, `name` (nombre aceptado o, en una identidad de la fuente, el nombre de la entrada), `author`, `kind`, `backbone` (`wcvp`, `wfo` o null), `acceptedId` y `matchedId` (IDs del backbone indicado; `matchedId` solo en plantas heterotípicas), `family`, `entries`, `aliases`, `flags`, `reviewFlags` y `collision`.
- `kind`: `resolved` (el aceptado, sus homotípicos y los heterotípicos fusionados), `heterotypic` (planta propia de un grupo partido), `ambiguous`, `unresolved`, `unmatched` o `genus_only` (identidad de la fuente).
- `entries`: una por entrada que llegó a la planta, con `source` (`usda` o `ema`), `key` (`usda:<FNFNUM>` o `ema:<slug de la ficha>#<n>`), `name`, `author`, `outcome` (resultado de la resolución), `matchedName` y `relation` (`aceptado`, `homotípico`, `heterotípico` o null si no resolvió). Las claves son las que usarán las tareas 3.2 y 3.5 para ubicar las filas de `sources.db`.
- `flags`: marcas del resolvedor y del grupo (por ejemplo `wfo_fallback`, `orthographic_variant`, `fuzzy_match`, `accepted_above_species`, `backbone_disagreement`, `split_group`, `author_tiebreak`). `reviewFlags` son los flags de revisión en el formato del registro: `{code, target: "scientificName", message}` con los códigos `identidad-ambigua`, `solo-genero`, `sin-resolucion`, `respaldo-wfo`, `variante-ortografica`, `coincidencia-aproximada`, `aceptado-superior-a-especie`, `backbones-discrepan`, `grupo-partido`, `fusion-heterotipica` y `filas-sin-asignar`.
- `collision`: null, o `{acceptedName, members, split}` con los IDs de todas las plantas del grupo partido.
- Campos que suma la regla de colisiones al formato (compatibles: solo agregan claves, así que sigue siendo `catalog-universe/1` y un lector anterior los ignora): `fusedHeterotypic` y `fusedMatchedIds` en la planta que absorbió heterotípicos (`[{name, reason, entries}]` y los IDs `<backbone>:<id>` de las filas fusionadas, que usa `wiki_assign.py`), y `collisionDecision` (`{state, decision, reason}`) en las plantas `heterotypic`. `state` es `decidido` o `sin-decision`.

`report.json` guarda las cifras (incluido `collisions.decisions`: grupos por estado, miembros fusionados y separados por motivo y la lista de miembros sin decisión), la comparación con los IDs actuales, las celdas de la EMA modificadas (`ema_modified_cells`: celda original, especies resultantes y notas), las listas de revisión por motivo (incluidas todas las coincidencias aproximadas, con el nombre de origen, el nombre de WCVP, la distancia y el aceptado, y los nombres con aceptado de rango superior a especie), los alias descartados y todos los grupos con varias entradas (`collision_groups`, con la relación y el resultado de cada miembro). `report.md` es la versión legible, con los grupos partidos y los fusionados por separado.

### Resultado con los datos reales y diferencias con el piloto

| Cifra | Piloto | Real |
| --- | --- | --- |
| Entradas de USDA resueltas con WCVP (de 2.376) | unas 2.125 | 2.125 por WCVP (más 87 por coincidencia aproximada, 44 por variante ortográfica y 5 por respaldo de WFO) |
| Plantas | unas 2.411 | 2.355 (2.295 con entradas de USDA y 60 solo de la EMA); eran 2.406 antes del criterio de Wikipedia |
| Homónimos ambiguos | unos 19 | 21 (19 más dos de la coincidencia aproximada) |
| Sin resolver (USDA) | 164 | 32 tras variantes, coincidencia aproximada y respaldo |
| Solo género | 62 o 63 | 62 de USDA y 62 plantas |
| IDs distintos de los actuales | unos 500 | 629 en la semilla final (527 renombrados, 101 fusionados y 1 ausente; los IDs con errata del catálogo actual y los heterotípicos fusionados pasan a alias) |
| `lavandula-angustifolia` | presente | presente |
| IDs repetidos | ninguno | ninguno |

- Plantas por tipo: 2.215 `resolved`, 23 `heterotypic`, 21 `ambiguous`, 34 sin resolver (33 `unmatched` y 1 `unresolved`), 62 solo género. Hay 650 alias en 620 plantas y 1 descartado (`cynara-cardunculus-subsp-cardunculus`, que es el ID de otra planta).
- Contra los 2.376 IDs actuales de `data/build/catalog.db`: 1.747 se conservan como ID, 628 pasan a alias (los heterotípicos fusionados entre ellos) y 1 queda ausente, `malachra-alaceaefolia`, que no tiene datos en ninguna fuente y no entra en la semilla. Los IDs que cambian son 629 (527 renombrados, 101 fusionados y 1 ausente).
- Antes de las correcciones de calidad (primera generación del universo) había 2.414 plantas, 117 sin resolver, 63 solo género, 52 grupos partidos y 14 entradas por el respaldo de WFO. Las correcciones cambian eso así: 8 plantas menos (las erratas de la EMA y de USDA se unen a su planta; desaparecen `lippia-citriodora`, `salix-various-species-including-s-purpurea-l`, `eschscholzia-california` y `salvia-fructicosa`), 83 sin resolver menos, 1 solo género menos (el de `Salix [...]`), 4 grupos partidos más (al unirse, una entrada nueva vuelve heterotípico a un sinónimo que antes estaba solo) y 9 entradas del respaldo de WFO que pasan a coincidencia aproximada.
- El piloto cuenta 164 sin resolver; aquí quedan 32 de USDA. La tarea 2.7 (contraste con el script del piloto) no se ha hecho, así que las diferencias de cifras con el piloto no se han atribuido.
- Coincidencias aproximadas: 91 entradas (87 de USDA y 4 de la EMA: `Curcuma xanthorrhiza` dos veces, `Eschscholzia california` y `Salvia fructicosa`), todas listadas en `report.md` con la distancia y el aceptado para revisarlas una por una. 54 son de epíteto con distancia 1, 19 de epíteto con distancia 2 y 18 de género (`Zizyphus`, `Macroptylium`, `Syzgium`, ...). Dos más quedaron `ambiguous` (`Croton macrostachys` y `Zizyphus trinervia`).
- Aceptado de rango superior a especie: 5 entradas de *Taraxacum officinale* (USDA y 4 fichas de la EMA), todas una sola planta `taraxacum-officinale` `unresolved` con el flag `accepted_above_species`.
- Las 32 entradas de USDA que siguen sin resolver y las 7 de la EMA (3 sin encontrar y las 4 de *Taraxacum officinale*) aparecen en la lista de revisión; ya no hay plantas espurias por sinónimos de la EMA.
- `backbone_disagreement`: 74 entradas. En 17 WCVP y WFO aceptan el mismo binomio y solo difieren en la variedad o subespecie (por eso la cifra parece inflada), y en 57 aceptan especies distintas (por ejemplo `Urginea maritima` es *Drimia maritima* en WCVP y *Squilla maritima* en WFO).
- Grupos de colisión: 225 grupos reúnen varias entradas con el mismo aceptado. Con la regla anterior (todo heterotípico es planta propia) se partían 56 y había 75 plantas `heterotypic`; con el criterio de Wikipedia se parten 11, hay 23 plantas `heterotypic` y 45 grupos fusionaron al menos un heterotípico (véase «Regla de colisiones (criterio de Wikipedia)»). `report.md` los lista con la relación de cada miembro, su decisión y su resultado.

## Asignación de USDA y citas candidatas (tarea 3.2)

Los datos de USDA se asignan a las plantas del universo en `catalog_seed/usda_assign.py` (`assign_usda`). Los nombres comunes (`usda_common_name`) y las partes (`usda_part`) traen FNFNUM y se asignan por la entrada `usda:<FNFNUM>` del universo. Las filas de uso (`usda_use`, una por ETHNOBOT) solo traen el nombre (TAXON) y el autor (TAXAUTHOR): se asignan con `Universe.assign`, por resolución taxonómica y no por nombre exacto, así que una fila bajo un sinónimo (*Matricaria recutita*) llega a la planta del aceptado, y una fila bajo un heterotípico fusionado por la regla de colisiones (*Cinnamomum zeylanicum*) llega a la planta del aceptado en la que se fusionó. Cada par distinto (TAXON, TAXAUTHOR) se resuelve una sola vez, y un par cuyo TAXON es literalmente el nombre de una entrada de USDA de una sola planta va a esa planta (`taxon-exacto`, véase «Defecto 3 de la QA»). Las filas que no se asignan quedan en `UsdaAssignment.unassigned` con su motivo: `sin-resolver`, `fuera-del-universo` (la especie resuelve, pero no está en el universo), `sin-asignar` o `fnfnum-sin-planta`. `build_universe_from_work` (en `resolve_universe.py`) construye el universo en memoria a partir de `sources.db` y `taxonomy.db` sin escribir salidas; lee `collision-decisions.json` y `collision-exceptions.json`, así que da el mismo universo que `resolve`.

Por planta, el resultado trae `commonNames` (nombre, idioma y ref `usda_common_name:<id>`), `parts` (compuestos, `hasEo` y ref `usda_part:<id>`) y `useGroups`: un grupo por actividad con `n`, los `countries`, los refs `usda_use:<ETHNO>` y las claves cortas de REFERENCE tal como vienen (`keys`, con el número de filas de cada una). Todo se ordena de forma estable, para poder hashearlo.

Por cada clave corta se eligen hasta 5 candidatas de `usda_reference` (`catalog_seed/citations.py`), cada una con su ref `usda_reference:<REFERENCE>`, su LONGREF y el tipo de coincidencia. Orden de prioridad: (1) la entrada exacta; (2) las de clave normalizada igual (minúsculas, sin espacios ni puntuación): `Burkill,1966` encuentra `Burkill, 1966`; (3) las que comparten el prefijo alfabético, por prefijo común más largo de la clave normalizada, y a igualdad la clave más corta primero: `Woi.10` encuentra `WOI` y `Eb24: 441` encuentra `EB` y las `EBxx:yyy` hasta el tope. Una clave numérica solo tiene candidata exacta o normalizada igual. La selección no resuelve la cita: la decisión la toma el LLM (D13).

Resultado con los datos reales (universo de 2.355 plantas con el criterio de Wikipedia; se obtiene llamando a `assign_usda` dentro de `build_universe_from_work` sobre `data/work/sources.db` y `data/work/taxonomy.db`):

| Cifra | Valor |
| --- | --- |
| Filas de uso (`usda_use`) | 82.873 en 13.899 pares (TAXON, TAXAUTHOR) |
| Filas de uso asignadas | 36.262: `grupo-unico` 35.386, `misma-clave` 522, `taxon-exacto` 327, `aceptado-propio` 25, `homotipico` 2 (eran 35.935 antes de `taxon-exacto`) |
| Filas de uso sin asignar | 46.611: `fuera-del-universo` 42.557, `sin-resolver` 4.023, `sin-asignar` 31 (en 11.599 pares) |
| Nombres comunes y partes | 2.920 y 6.740, todos asignados (`fnfnum-sin-planta` 0) |
| Plantas con datos de USDA | 2.317 |
| Manzanilla (`matricaria-chamomilla`) | 91 filas de uso (0 con la asignación por nombre exacto) |
| Menta (`mentha-x-piperita`) | 49 filas de uso (0 con la asignación por nombre exacto) |
| Claves cortas distintas en las plantas asignadas | 679: 638 con candidatas y 41 sin ninguna |

Las 31 filas `sin-asignar` son las de nombres que resuelven a un grupo partido sin el propio aceptado y sin miembro con su clave (*Brassica oleracea*, con 15 filas, y *Citrus bigaradia*, *C. fusca*, *C. natsudaidai* y *C. nobilis*). El efecto de la regla de colisiones sobre USDA: 51 plantas menos, 45 plantas con cambios en sus datos (por ejemplo `aloe-vera` pasa de 24 a 128 filas de uso por *Aloe barbadensis*, y `cinnamomum-verum` de 28 a 41 por *Cinnamomum zeylanicum*) y una fila más asignada (la de *Erythroxylum havanense*, que antes quedaba sin asignar). *Citrus × sudachi* y *C. × sphaerocarpa* siguen siendo plantas propias, con sus nombres comunes.

### Defecto 3 de la QA: plantas que perdían sus usos

La QA del cambio encontró 26 plantas con usos en el catálogo anterior (el de USDA por nombre exacto del TAXON) y ninguno en la semilla nueva. La causa de 17 era un error de la asignación y está corregida. Las filas de ETHNOBOT no traen autor (TAXAUTHOR vacío en las 327 filas afectadas), pero la entrada de USDA de la planta sí (*Eupatorium odoratum* L.). Sin autor, `Universe.assign` resuelve el nombre solo, y eso falla de dos maneras: el nombre es un homónimo ambiguo en WCVP (*Eupatorium odoratum* L. y *E. odoratum* Walter, *Cimicifuga foetida* L. y Pursh, *Chrysanthemum balsamita*, *Origanum creticum*, *Satureja obovata*), así que queda `sin-resolver`; o resuelve a otro aceptado homónimo que no está en el universo (*Senecio aureus* Georgi en WFO en vez de *Packera aurea*, *Piper angustifolium* Lam. en vez de *P. aduncum* var. *aduncum*, *Justicia procumbens* L. en WFO en vez de *Rostellularia procumbens*), así que queda `fuera-del-universo`. Las nueve plantas de solo género (*Eucalyptus sp*, *Gossypium sp*, ...) nunca resuelven porque no tienen especie, y también quedaban `sin-resolver`.

Regla corregida (`usda_assign.py`): si el TAXON de un par es, escrito igual (sin distinguir mayúsculas ni espacios repetidos), el nombre de una entrada `usda:<FNFNUM>` y esas entradas son de una sola planta, la fila va a esa planta con el motivo `taxon-exacto`, tanto si el resolvedor no la resuelve como si la lleva a otra planta. Un nombre que llevan entradas de dos plantas distintas no se fuerza: sigue la resolución taxonómica. La entrada es la misma identidad que el catálogo anterior usaba, y el resolvedor sigue valiendo para los nombres que no coinciden con ninguna entrada (sinónimos como *Matricaria recutita*).

Impacto medido en los 13.899 pares del universo real: 1.509 pares (30.157 filas) ya iban a la planta de su entrada y no cambian; 29 pares (327 filas) no tenían destino y ahora lo tienen; 0 pares cambian de una planta a otra; 0 nombres de entrada ambiguos entre plantas; el resto (12.361 pares) no coincide con ninguna entrada y no se toca. Los 29 pares son los de las 17 plantas más otras 11 que también perdían filas sin que la QA lo viera (*Prunus dulcis* 38 filas, *Diospyros tomentosa* 29, *Thymus capitatus*, *Zanthoxylum alatum*, *Garcinia cambogia*, *Satureja vulgaris*, *Amaranthus sp.*, *Morinda sp*, *Lamium sp*, *Murraya sp* y *Andropogon virginicus*).

Cambian 28 paquetes (solo la sección `uses`) y suman 327 filas de uso; `plan --seed data/seed` los lista por `bundleHash`, más `malachra-alaceaefolia` (sin registro y sin datos, que sigue fuera). Los lotes de 10 están en `data/work/generation/fix2/lot-NN.txt` y `lots.json`, con las 17 plantas que perdían usos primero.

Las otras 9 plantas de la lista (`actaea-pachypoda`, `dalbergia-nitidula`, `dictamnus-hispanicus`, `duboisia-leichhardtii`, `eucalyptus-cladocalyx`, `hyacinthus-orientalis`, `inocarpus-fagifer`, `huperzia-selago` y `strophanthus-gratus`) no tienen un error de asignación: la asignación ya les daba las filas y su paquete las trae. En 8 la única fila de USDA es de toxicidad o abortivo (`Poison`, `Poison(Arrow)`, `Fatality`, `Abortifacient`), y el consolidador la pasó a `safety` y no a `traditionalUses`, que es lo que pide el prompt. El catálogo anterior las contaba como «uso» porque no distinguía seguridad de uso tradicional. La novena, `inocarpus-fagifer`, tiene 12 grupos de uso reales (astringente, diarrea, hemorragia, ...) y su registro quedó con 0: es una omisión del consolidador y no del pipeline, y se corrige regenerándola (ya está con el paquete vigente y no entra en `plan`).

## Pruebas

Desde la raíz del repositorio, sin red:

```sh
python3 -I -m unittest discover -s tools/catalog-seed/tests -v
tools/catalog-seed/.venv/bin/python3 -I -m unittest discover -s tools/catalog-seed/tests -v
```

Con el `python3` del sistema se omiten (con `skipTest`) las pruebas que necesitan `xlrd` o `pdfminer.six`, las que necesitan los insumos reales en `data/.cache/` y las de `RealBundlesTests` (necesitan `data/work/bundles/`); con el entorno virtual corren las de esas bibliotecas, y las de datos reales corren cuando existen esos datos. Los fixtures de la extracción están en `tests/fixtures/extract/` (dos `.xls` y dos PDF mínimos con sus scripts generadores).

Con `-I` Python no añade directorios a `sys.path`, así que `tests/support.py` calcula la ruta de `tools/catalog-seed/` y la agrega antes de importar el paquete; cada archivo de pruebas importa `support` primero.

## Archivos locales

`data/.cache/` (descargas verificadas) y `data/work/` (productos intermedios) están ignorados por Git y excluidos del contexto de Docker, igual que `tools/`. El entorno virtual `tools/catalog-seed/.venv` también está ignorado.
