# Modelo de datos del catálogo

Esta guía describe cómo se obtiene el catálogo que sirve la API: las fuentes abiertas se descargan y se consolidan offline en una semilla versionada (`data/seed/`), y el backend (`backend/catalog-ingest`) convierte esa semilla en `catalog.db` sin red ni LLM. Cubre las capas, las tablas (incluidas las del esquema v2), el mapeo de la semilla, las reglas de consolidación, los errores de construcción, la versión de esquema, cómo se regenera la semilla y cómo añadir una fuente nueva a las herramientas.

Documentos relacionados:

- [Fuentes y licencias](fuentes-y-licencias.md): cada fuente, su versión, licencia y atribución, y las fuentes descartadas.
- [La fuente USDA](usda-catalog.md): procedencia, límites y cruce de usos por sinónimos resueltos.
- [Regeneración incremental, versiones y reviewFlags](regeneracion-de-la-semilla.md): `plan`, `bundleHash`, versionado de prompt y modelo, y el catálogo de `reviewFlags`.
- [README de las herramientas](../../tools/catalog-seed/README.md): referencia operativa de cada comando de `tools/catalog-seed/`.
- [`backend/openapi.json`](../../backend/openapi.json): el contrato HTTP. La API sirve los campos consolidados de la semilla, los créditos y los identificadores anteriores (véase «Lo que la API sirve»).
- Para ejecutar el backend, ver el [README de la raíz](../../README.md); los comandos nativos para construir el catálogo, ejecutar la API y verificar están en [`backend/README.md`](../../backend/README.md).

## 1. Las capas

Los datos pasan por cuatro capas. Solo la tercera y la cuarta llegan al backend en ejecución:

1. **Fuentes** (`data/.cache/`, ignorada por Git). Los insumos descargados con versión y checksum: USDA, WCVP, WFO, EMA (JSON y PDF), TPPT, EFSA y las respuestas guardadas de Wikidata, Wikipedia en español y Commons. `sources.json` los declara y `download` los verifica; un insumo alterado o ausente detiene el paso e indica qué descargar. No va en la imagen de Docker.
2. **Trabajo** (`data/work/`, ignorada por Git). Productos intermedios deterministas de las herramientas: `sources.db` (filas normalizadas de todas las fuentes), `taxonomy.db` y `universe/` (resolución taxonómica y universo de plantas), `wiki/` (asignación de Wikidata, Wikipedia y Commons), `bundles/` (un paquete JSON por planta, la entrada del LLM) y los directorios de registros recién generados antes de sellar.
3. **Semilla** (`data/seed/`, versionada). Un registro JSON por planta en `plants/<id>.json`, `goals.json` (catálogo de objetivos y subáreas) y `manifest.json`. Es el único insumo del build y el resultado de la consolidación con el LLM.
4. **Base neutral** (`data/build/catalog.db`, derivada). La construye `catalog-ingest build` desde la semilla. Su esquema no contiene nombres ni estructuras de ningún dataset, y la API la lee en modo de solo lectura; un test (`backend/catalog-api/tests/source_independence.rs`) lo comprueba.

Ya no existen la descarga de figshare, la capa cruda `raw.db`, `data/sources.toml` ni el marco de adaptadores (`SourceAdapter`, `default_registry`).

### La semilla

- `plants/<id>.json`: el registro de una planta con el nombre científico y sus sinónimos, la familia, el nombre para mostrar, los nombres comunes, el origen, la descripción, las partes usadas, el aceite, los grupos de usos tradicionales con sus citas, los objetivos, la seguridad, la imagen, los alias, el subconjunto de `refs` que usa (cada una con `dataset`, `label`, `license` y, a veces, `url`) y los `reviewFlags`. Cada dato cita sus refs. Guarda además `recordVersion`, `bundleHash`, `promptVersion` y `model`. El esquema es `tools/catalog-seed/schema/record.schema.json`, fuente única de la forma del registro: el validador de Python lo aplica y el lector de Rust usa tipos estrictos (`deny_unknown_fields`).
- Los archivos tienen claves ordenadas, sangría de 2 espacios y salto de línea final, sin marcas de tiempo, así que un cambio en una planta es el diff de un archivo.
- `manifest.json`: `formatVersion`, las fuentes activas (id, nombre, URL de la página, versión, licencia, atribución y checksum de sus archivos), `promptVersion`, `recordVersion`, `models`, `plantCount`, el conteo de `reviewFlags` por código y el `seedHash`.
- `seedHash`: `sha256:` del contenido canónico de los registros ordenados por `id` más el de `goals.json`. No depende de la sangría de los archivos. El build lo recalcula y rechaza una semilla alterada.

## 2. Las tablas de `catalog.db`

La base tiene 25 tablas: las 12 del esquema v1 (las que lee la API) y 13 nuevas del esquema v2. Las 25 forman el hash de contenido.

### Esquema v1 (lo que lee la API)

| Tabla | Contenido |
| --- | --- |
| `metadata` | Pares clave-valor de la base; guarda `schema_version`. |
| `source` | Fuentes del manifiesto: id, nombre, versión, licencia, cita (la atribución), URL de la página, checksum del insumo y `license_url`, la URL de la licencia (nulable: es `null` en las fuentes sin una licencia con URL única). |
| `plant` | Plantas; el ID es el de la semilla, con el nombre científico, su forma normalizada, la familia y la fuente que la aportó (`family_source_id`). |
| `plant_source_id` | Procedencia: el identificador que cada fuente da a la planta (`plant_id`, `source_id`, `source_plant_id`). Es un dato de procedencia, no un identificador público. |
| `plant_name` | Nombres científicos y comunes, con idioma y versión normalizada para buscar. |
| `plant_part` | Partes de la planta. |
| `reference` | Referencias bibliográficas; en la v2 gana `dataset`, `license` y `url`. |
| `plant_use` | Usos (actividad en español, idioma `es`) respaldados por una referencia. |
| `plant_name_source`, `plant_part_source`, `plant_use_source`, `reference_source` | Atribución: qué fuentes aportan cada nombre, parte, uso y referencia. |

### Esquema v2 (tablas nuevas)

La migración está en `data/migrations/2026-10-26-000000_catalog_v2/up.sql`. Las posiciones (`position`) conservan el orden del registro y los valores lógicos son `BOOLEAN` con `CHECK (x IN (0, 1))`.

| Tabla | Contenido |
| --- | --- |
| `plant_profile` | Una fila por planta: `display_name` (la fuente de verdad del nombre para mostrar), `authors`, `origin`, `description`, `oil_type`, `record_version`, `bundle_hash` y `prompt_version`. |
| `plant_profile_ref` | Referencias de los campos del perfil, para saber de qué dataset sale cada uno. `field` es una lista cerrada: `scientificName`, `family`, `displayName`, `origin`, `description`, `oil` y `partsUsed`. |
| `plant_use_group` | Grupos de uso tradicional: `activity` en español, `activity_source` (la etiqueta original), `n`, `countries` (arreglo JSON de textos en español) y `pending_review`. |
| `plant_use_group_ref` | Citas de cada grupo, resueltas o no. Una cita sin resolver no tiene `reference_id` y su `text` termina en «(sin resolver)»; un `CHECK` exige que `resolved` sea verdadero si y solo si hay `reference_id`. |
| `goal`, `goal_subarea` | Catálogo de objetivos y subáreas, cargado de `data/seed/goals.json`. |
| `plant_goal` | Objetivos de cada planta con subárea (opcional), `area`, `evidence` y `pending_review`. Una clave foránea compuesta exige que la subárea sea del objetivo, y un índice único evita repetir objetivo, subárea y área. |
| `plant_goal_ref` | Referencias que respaldan cada objetivo. |
| `plant_safety` | A lo sumo una fila por planta: `level` (`alto`, `medio`, `bajo` o nulo, que es una precaución sin nivel) y `text`. Sin fila si el registro no trae `safety`. |
| `plant_safety_ref` | Referencias que respaldan la seguridad. |
| `plant_image` | A lo sumo una imagen por planta con URL, página, autor (nulable), licencia, URL de la licencia (nulable) y si la atribución es obligatoria. |
| `plant_alias` | IDs anteriores de la planta. El alias es único en toda la base. |
| `plant_review_flag` | `reviewFlags` del registro: código, `target` y mensaje. |

### Procedencia y atribución

La procedencia por dato es interna: la API no dice de qué fuente viene cada nombre, parte, uso, grupo, objetivo o nivel. Un dato con varias fuentes significa que todas lo respaldan, y la atribución las conserva todas. La familia es un valor único, así que `plant` guarda cuál fuente la aportó (el dataset del primer ref del nombre científico). Las tablas `plant_*_source` y `reference_source` se rellenan con el dataset de los refs de cada dato; `plant_profile_ref`, `plant_goal_ref`, `plant_safety_ref` y `plant_use_group_ref` conservan la referencia concreta.

Lo que sí sale por la API es la atribución a nivel de planta (`credits`), descrita en la sección siguiente.

### Lo que la API sirve

El listado de `GET /v1/plants` suma `displayName` (el `plant_profile.display_name` de la semilla, o el nombre científico si la planta no tiene perfil) y deja ese nombre primero entre los `commonNames` cuando es un nombre común. El detalle de `GET /v1/plants/{id}` conserva `id`, `scientificName`, `family`, `names`, `parts` y `uses` (cuya cita sigue siendo la etiqueta de `reference.citation`) y suma, siempre presentes y con `null` o lista vacía si no hay dato:

| Campo del detalle | De dónde sale |
| --- | --- |
| `displayName`, `description`, `origin`, `oil` | `plant_profile` (`display_name`, `description`, `origin`, `oil_type`). |
| `synonyms` | Los demás nombres científicos de `plant_name`, sin repetir. |
| `useGroups` | `plant_use_group` y `plant_use_group_ref`, por `n` descendente y actividad. La `citation` de cada referencia es `plant_use_group_ref.text` (la cita completa) y no la etiqueta de `reference`; una cita sin resolver lleva `id` nulo y `resolved` falso. |
| `goals` | `plant_goal` con `goal.label` como nombre y `goal_subarea.label` como subárea, por nombre. |
| `safety` | `plant_safety` y `plant_safety_ref`; `level` es `alto`, `medio`, `bajo` o `null`, y todo el objeto es `null` solo sin fila. |
| `image` | `plant_image`; la API no descarga ni sirve la imagen. |
| `credits` | La unión sin repeticiones de las fuentes de la planta, ordenada por nombre: `source` por las tablas `plant_name_source`, `plant_part_source` y `plant_use_source`, por `plant.family_source_id` y por el `reference.dataset` de las referencias del perfil, de los objetivos, de las precauciones y de los grupos de uso servidos. `name`, `license`, `licenseUrl` (`source.license_url`), `attribution` (`source.citation`) y `url` salen de `source`, no de `reference`. Si la descripción cita un artículo, la `url` de ese dataset es la `reference.url` del artículo. No indica qué campo viene de qué dataset. |

Reglas de lo que no se sirve:

- La API omite los objetivos con `plant_goal.pending_review` y los grupos de uso con `plant_use_group.pending_review` (ninguna cita resuelta); estos últimos tampoco generan filas en `uses`. Un grupo con al menos una cita resuelta se sirve con todas sus citas. La regla depende solo de esas columnas, sin tabla de reglas en la API, y no indica que algo se omitió.
- Los `reviewFlags` (`plant_review_flag`) no salen en ninguna respuesta ni en el documento OpenAPI, y una planta con flags se sirve completa. Lo omitido por `pending_review` tampoco acredita su fuente en `credits`.

Los alias de `plant_alias` se usan en dos sitios. En `GET /v1/plants/{id}`, un ID que no es el de una planta pero sí un alias responde 200 con el detalle de la planta canónica y la cabecera `Content-Location: /v1/plants/<canónico>`, sin redirección; un ID de planta gana siempre a un alias igual. En `q`, la consulta reducida con `slug` se compara por subcadena con el alias, y la planta se une al resultado de la búsqueda por nombres sin duplicarla ni devolver el alias como nombre. El listado nunca incluye alias como plantas. Con la base real, los 357 nombres anteriores que la QA del cambio `consolidate-catalog-seed` no encontraba (API-04) encuentran su planta nueva; `mentha piperita` sigue sin resultado porque no es subcadena de ningún nombre ni alias (`mentha x piperita` sí lo encuentra).

Los textos de ejemplo y el detalle de los campos están en el [README del backend](../../backend/README.md#qué-devuelve-la-api).

## 3. Mapeo de la semilla a las tablas

`catalog-ingest build` (módulo `seed_build.rs`) escribe:

| Dato del registro | Destino |
| --- | --- |
| Manifiesto `sources` | `source`: `name`, `version`, `license`, `citation` (la atribución), `url` (la página del dataset) y `checksum` (`<algoritmo>:<valor>` si hay un archivo, un sha256 de la lista ordenada si hay varios, vacío en los servicios en línea) |
| `refs` de todos los registros | `reference` (`citation` es la etiqueta, más `dataset`, `license` y `url`) y `reference_source` |
| `id`, `scientificName.name`, `family` | `plant`; el ID se escribe tal cual |
| Refs del nombre científico | `plant_source_id`: una fila por dataset |
| `scientificName` y `synonyms` | `plant_name` con `kind = scientific` e idioma `la`; los sinónimos mantienen la búsqueda por nombres antiguos sin cambiar el contrato |
| `displayName` y `commonNames` | `plant_name` con `kind = common` y el idioma de cada nombre; `displayName` además va a `plant_profile.display_name`. No se confía en el orden de `plant_name`: la API ordena los nombres comunes alfabéticamente |
| `partsUsed` | `plant_part` (una fila por etiqueta distinta) |
| `traditionalUses` | `plant_use_group` y `plant_use_group_ref` para todos los grupos; `plant_use` solo para los grupos no pendientes: un uso por cada cita con referencia resuelta, con `activity` en español e idioma `es`. Un grupo con `pendingReview` no genera ningún uso de la API |
| `origin`, `description`, `oil`, autores, versiones | `plant_profile` y `plant_profile_ref` |
| `data/seed/goals.json` | `goal` y `goal_subarea` |
| `goals` | `plant_goal` y `plant_goal_ref` |
| `safety` | `plant_safety` y `plant_safety_ref` |
| `image` | `plant_image` |
| `aliases` | `plant_alias` |
| `reviewFlags` | `plant_review_flag` |

La API conserva su contrato: sigue sirviendo `id`, `scientificName`, `commonNames`, `family`, `names`, `parts` y `uses`. Cambia el contenido (nombres y usos en español, plantas fusionadas o separadas, IDs nuevos), no la forma.

## 4. Reglas de consolidación

Las aplican las herramientas de `tools/catalog-seed/` antes de la semilla; el backend no las reevalúa, solo verifica la integridad de lo que recibe.

- **Identidad e ID.** Los nombres de USDA y de la EMA se normalizan y se resuelven con WCVP, con WFO solo como respaldo (flag `respaldo-wfo`). El ID es el slug del nombre aceptado de WCVP, generado una vez y fijo en la semilla: si Kew renombra, cambia el nombre mostrado y no el ID. Los nombres que no resuelven conservan la identidad de la fuente con un `reviewFlag`.
- **Regla de colisiones («criterio de Wikipedia»).** Cuando varias plantas resuelven al mismo aceptado, se fusionan siempre el aceptado y sus sinónimos homotípicos. Un miembro heterotípico queda como planta propia (flag `grupo-partido`) solo si su nombre tiene artículo propio en Wikipedia en español, o si está en `collision-exceptions.json`. Si no, se fusiona con el aceptado (flag `fusion-heterotipica`). La decisión de cada grupo se registra una vez en `collision-decisions.json`, para que un cambio posterior de Wikipedia no altere IDs.
- **Alias.** Los IDs anteriores (el slug del nombre literal de USDA de cada planta fusionada o renombrada) se guardan en `aliases` y en `plant_alias`. La API los resuelve en el detalle (200 con `Content-Location`) y los usa en la búsqueda `q`.
- **Política «variante A» del LLM.** El LLM solo elige, traduce y resume lo que está en el paquete de la planta, y cada campo cita refs del paquete; no aporta conocimiento propio. Se prohíben dosis, posologías, indicaciones de tratamiento y promesas de eficacia.
- **Citas abreviadas.** El paquete conserva las claves cortas de USDA y suma hasta 5 candidatas por clave; el LLM elige. Una clave sin candidata queda «(sin resolver)» con el flag `cita-sin-resolver`. Un grupo es `pendingReview` solo si ninguna de sus citas se resolvió.
- **Objetivos.** Salen solo de las áreas terapéuticas de la EMA con monografía de la UE o entrada de lista, mediante `goals-map.json`. Una planta con TPPT «strong toxic» o «very strong toxic» no recibe objetivos.
- **Seguridad.** El nivel es el más alto entre las fuentes, según `safety-map.json`: TPPT por categoría, las interacciones de la EMA y una lista versionada de sustancias de alta preocupación de EFSA. Una planta sin datos lleva `safety` nulo y el flag `sin-datos-de-seguridad`, y nunca se presenta como segura.
- **Actividades sensibles.** Una enfermedad grave se redacta «Uso tradicional, sin eficacia demostrada: …»; una señal de riesgo (`Poison`, `Abortifacient`…) sale de los usos y va a `safety` como advertencia.
- **Imágenes.** Solo con licencia CC0, dominio público, CC BY o CC BY-SA (véase [fuentes y licencias](fuentes-y-licencias.md)).
- **Validador.** `validate` comprueba cada registro contra su paquete antes de sellarlo (esquema, refs, objetivos con respaldo de la EMA, citas, imagen, actividades sensibles y coherencia de `safety`). Los errores impiden el sellado; las expresiones de dosis o eficacia son advertencias.

## 5. Errores de construcción

`catalog-ingest build` nunca resuelve en silencio un dato inconsistente: la transacción se revierte, el archivo temporal se borra y el error nombra la planta. Si algo falla, el destino previo queda intacto.

Errores de lectura y verificación de la semilla (`SeedError`, en `seed.rs`):

| Error | Causa |
| --- | --- |
| `Missing` | No hay semilla: falta `manifest.json` o `goals.json`. El mensaje indica cómo generarla. |
| `Io` | Fallo de lectura de un archivo. |
| `Parse` | Un archivo no es JSON válido o no cumple los tipos estrictos (campos desconocidos, un nivel de seguridad fuera de `alto`, `medio` y `bajo`…); nombra el archivo y la planta. |
| `FileNameMismatch` | El nombre del archivo no coincide con el `id` del registro. |
| `CountMismatch` | El número de registros no coincide con `plantCount` del manifiesto. |
| `UnsupportedVersion` | `formatVersion` del manifiesto o `recordVersion` de un registro no es la que el lector entiende. |
| `UnknownGoal` | Un registro usa un objetivo o subárea que no está en `goals.json`, o una subárea de otro objetivo. |
| `HashMismatch` | El `seedHash` recalculado no coincide con el del manifiesto (un registro alterado). |

Errores del mapeo y la escritura (`BuildError`, en `seed_build.rs`):

| Error | Causa |
| --- | --- |
| `DuplicateId` | Dos registros con el mismo `id`. |
| `DuplicateScientificName` | Dos plantas con el mismo nombre científico normalizado. |
| `AliasIsPlantId` | Un alias de una planta es el ID de otra. |
| `DuplicateAlias` | Dos plantas declaran el mismo alias. |
| `UnknownRef` | Un campo cita un ref que no está en el `refs` del registro. |
| `DataWithoutRefs` | Un dato no cita ningún ref, y por tanto no tiene dataset ni licencia. |
| `RefWithoutProvenance` | Una entrada de `refs` no tiene `dataset` o `license`. |
| `UnknownDataset` | El dataset de un ref no figura en las fuentes del manifiesto. |
| `ReferenceConflict` | El mismo ref tiene contenido distinto en dos registros. |
| `UnsupportedImageLicense` | La licencia de la imagen no es CC0, dominio público, CC BY ni CC BY-SA. |
| `PendingWithoutFlag` | Un grupo de usos o un objetivo con revisión pendiente no tiene `reviewFlag`. |
| `DuplicateCitationKey` | Un grupo de usos repite la clave de una cita. |
| `DuplicateGoal` | Una planta repite el mismo objetivo con la misma subárea y área. |
| `Storage` | Fallo de SQLite o de las restricciones del esquema; nombra la planta que se escribía, si se sabe. |

## 6. Construcción determinista

- **Escritura atómica.** La base se escribe en `<destino>.tmp` y se renombra al terminar. Un temporal previo de una ejecución interrumpida se descarta.
- **Hash de contenido.** `content_hash` (en `hash.rs`) calcula un SHA-256 del contenido lógico de las 25 tablas (`NEUTRAL_TABLES`), volcadas en un orden total. No hashea el archivo, que puede cambiar byte a byte sin cambiar su contenido. Dos construcciones de la misma semilla dan el mismo hash, y `build` lo imprime junto con los conteos de la base.

Comando (desde la raíz del repositorio; por defecto lee `data/seed` y escribe `data/build/catalog.db`):

```sh
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build --seed <semilla> --out <catalog.db>
```

El CLI solo tiene el subcomando `build`, con las opciones `--data-dir`, `--seed` y `--out`.

## 7. Versión de esquema

Hay dos versiones que no deben confundirse:

- **`SCHEMA_VERSION`** (en `backend/catalog-core/src/version.rs`, hoy 2) es la versión del esquema de `catalog.db`. Se guarda en `metadata` y la API la comprueba al arrancar.
- **`recordVersion`** (hoy 1) es la versión del registro de la semilla, y es la que comparan `plan`, `seal` y el lector de Rust.

El esquema es un conjunto de migraciones de Diesel en `data/migrations/` (`2026-10-12-000000_catalog_v1` y `2026-10-26-000000_catalog_v2`). `catalog-core` las embebe (`MIGRATIONS`) y `apply_schema` ejecuta el `up.sql` de cada una, en orden, sobre una base nueva. No se usa el arnés de migraciones de Diesel: la base no evoluciona, se regenera entera en cada construcción. `backend/catalog-core/src/schema.rs` lo genera Diesel y no se edita a mano.

Para cambiar el esquema: añadir una migración, subir `SCHEMA_VERSION`, regenerar `schema.rs` con `diesel migration run` sobre una base temporal (véase [`backend/README.md`](../../backend/README.md)), ajustar las filas de `catalog-core/src/rows.rs` y el mapeo de `seed_build.rs`, añadir la tabla a `NEUTRAL_TABLES` si es nueva y reconstruir. Un test comprueba que el esquema no contiene términos de ningún dataset.

## 8. Cómo se regenera la semilla

El orden completo, con lo que lee y escribe cada paso, está en «Tubería completa, en orden» del [README de las herramientas](../../tools/catalog-seed/README.md). En resumen, desde la raíz del repositorio:

```sh
python3 -I tools/catalog-seed/cli.py download
python3 -I tools/catalog-seed/cli.py ema-pdf --wait 7200
tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py extract
python3 -I tools/catalog-seed/cli.py resolve
python3 -I tools/catalog-seed/cli.py wiki-fetch --wait 7200
python3 -I tools/catalog-seed/cli.py wiki-assign
python3 -I tools/catalog-seed/cli.py bundles
python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed
# consolidar con el LLM las plantas del plan: un registro por planta en un directorio de trabajo
python3 -I tools/catalog-seed/cli.py validate --records <directorio de trabajo> --bundles data/work/bundles
python3 -I tools/catalog-seed/cli.py seal --seed data/seed --from <directorio de trabajo>
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build
```

`extract` de EFSA y de los PDF de la EMA necesita el entorno virtual de `tools/catalog-seed/requirements.txt`; el resto usa solo la biblioteca estándar. Solo `download`, `ema-pdf`, `wiki-fetch`, `collisions-decide` y la consolidación abren la red. El LLM no corre en el build ni en CI. Qué plantas se regeneran, y por qué, lo decide `plan`: véase [la regeneración incremental](regeneracion-de-la-semilla.md).

### Recorrido de verificación sobre fixtures

Ejecutable sin red y sin tocar `data/seed/`, en un directorio temporal `$T`. Usa un prompt de versión 1 porque los registros de los fixtures son de esa versión:

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
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build --seed $T/seed --out $T/build/catalog.db
```

Salida esperada: «2 plantas a regenerar» (`sin-registro`), «manifest.json actualizado: 2 plantas, seedHash sha256:...», «0 plantas a regenerar», «2 registros, 0 con errores, 0 errores, 0 advertencias», y de `build`: 2 plantas, 1 grupo de uso pendiente de revisión, 1 cita sin resolver, 10 fuentes y una línea `hash:` con 64 caracteres hexadecimales. Para comprobar solo el build sobre la semilla de fixtures del crate:

```sh
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build --seed backend/catalog-ingest/tests/fixtures/seed --out $T/fx/catalog.db
```

Imprime 3 plantas y un hash; repetirlo con otra salida da el mismo hash.

## 9. Cómo añadir una fuente nueva a las herramientas

Añadir una fuente no cambia el esquema de `catalog.db` ni la API, siempre que sus datos entren por los campos que ya tiene el registro. Los pasos, en `tools/catalog-seed/`:

1. **Comprobar licencia y formato.** La fuente debe permitir usar y redistribuir en la semilla sus datos, con la atribución que exija. Las fuentes descartadas (véase [fuentes y licencias](fuentes-y-licencias.md)) se rechazan por nombre.
2. **Admitirla.** Añadir su id a `ADMITTED_SOURCES` en `catalog_seed/sources.py`; cualquier id fuera de esa lista se rechaza.
3. **Declararla en `sources.json`** con `id`, `name`, `pageUrl`, `version`, `license`, `attribution` y `enabled`, y sus archivos (`url`, `filename`, `size` y `checksum`, o una lista `files`). Una fuente cambiante se declara con `size` y `checksum` en `null` y se fija con `pin`; un servicio en línea se declara además en `SERVICE_SOURCES`.
4. **Descargarla y verificarla** con `download --source <id>`.
5. **Extraerla** al formato intermedio: escribir un extractor en `catalog_seed/` y registrarlo en `extract_source` (`extract.py`), que vuelca filas normalizadas (`source`, `record_type`, `row_key`, `raw_name_cell`, `content_json`) a `data/work/sources.db`. Repetir `extract` da lo mismo.
6. **Asignarla a plantas** por la resolución taxonómica (nombre en `raw_name_cell`) o por un identificador de la fuente, y **añadirla al paquete** (`catalog_seed/bundles.py`: `load_rows`, una sección nueva, y `schema/bundle.schema.json`). Las filas de una fuente con `enabled: false` no entran en los paquetes.
7. **Enseñarle al consolidador qué hacer con ella:** una regla en `prompt/consolidate.md` y su subida de `prompt-version`, y, si afecta a objetivos o seguridad, `goals-map.json` o `safety-map.json`, con el validador y los esquemas (`schema/record.schema.json`) si el registro necesita campos nuevos. Si el registro cambia de forma, hay que subir `recordVersion`, adaptar los tipos de `seed.rs` y el mapeo de `seed_build.rs`, y migrar el esquema si hace falta una tabla.
8. **Probar con fixtures** en `tools/catalog-seed/tests/` (sin red), con `python3 -I -m unittest discover -s tools/catalog-seed/tests`.
9. **Regenerar:** `bundles`, `plan` (debe listar solo las plantas afectadas), consolidar, `validate` y `seal`. El manifiesto lista la fuente solo si está activa y con snapshot fijado.

Una fuente cuya licencia no permita redistribuir su contenido no puede entrar en la semilla, porque la semilla se versiona en el repositorio y su contenido se compila en `catalog.db`.

## 10. Límites conocidos

- **La API no indica el origen por dato.** El detalle de una planta no dice qué fuente aportó cada dato; solo entrega los créditos de la planta (`credits`), sin campos. La procedencia por dato queda en la base y no sale por el contrato HTTP.
- **Los IDs cambiaron.** El ID es el slug del nombre aceptado de WCVP, no el literal de USDA, y 629 de los 2.376 IDs anteriores cambian (el piloto estimaba unos 500), por ejemplo `rosmarinus-officinalis` es ahora `salvia-rosmarinus`. Los alias anteriores se guardan en `plant_alias` y la API los resuelve en el detalle y los encuentra con `q`; la búsqueda es por subcadena, así que `mentha piperita` no encuentra `mentha-x-piperita`.
- **No es reproducible desde cero.** Wikidata, Wikipedia, Commons y la EMA cambian, y el LLM puede dar textos distintos. La reproducibilidad está en la semilla versionada.
- **Los pendientes no se sirven.** Los grupos de usos y los objetivos con `pendingReview` se guardan pero la API no los sirve y los grupos no generan `plant_use`; la capa de validación humana está fuera de alcance.
- **Términos sin verificar.** Los términos de reutilización de la EMA y de TPPT no se verificaron contra el texto legal, y TPPT se usa con fines académicos (véase [fuentes y licencias](fuentes-y-licencias.md)).
- **Semilla provisional.** Hasta que termine la generación completa, `data/seed/` contiene los 20 registros de la corrida de control y no se publica.
