# Design

## Context

Estado actual, con sus fuentes:

- `catalog-ingest` descarga el ZIP de USDA (6.033.990 bytes, MD5 `45ae44a0544586b8ac22a232beaac344`) desde figshare, lo vuelca sin transformar a `data/build/raw.db` y deriva `catalog.db` mediante el contrato `SourceAdapter` y `default_registry` (`backend/catalog-ingest/src/adapter.rs`, `sources.rs`). La única fuente es `usda` (`data/sources.toml`). La identidad de una planta es su nombre científico normalizado y el ID es su slug (`docs/data/modelo-de-datos.md`, secciones 3 y 6).
- El cruce de usos con ETHNOBOT es exacto por `GENUS`, `SPECIES` y `TAXON` (`docs/data/usda-catalog.md`). Medido sobre la base actual: 2.376 plantas, 18.931 usos y 1.196 plantas sin ningún uso.
- El `Dockerfile` tiene tres etapas; la etapa `catalog` descarga el ZIP con reintento sobre una montura de caché y ejecuta `catalog-ingest build --data-dir /data`. La etapa de compilación solo copia `backend/` y `data/migrations/`, de modo que un cambio en `data/` no recompila Rust.
- La API lee la capa neutral en solo lectura. `backend/catalog-api/src/dto.rs` define el contrato: la lista devuelve `id`, `scientificName`, `commonNames` y `family`; el detalle devuelve además `names` (con `kind` científico o común), `parts` y `uses` (actividad, idioma y referencia con cita). La app muestra como nombre principal el primer nombre común y filtra los nombres por `kind` (`catalog-client`, «Nombre para mostrar»).
- Quién fija IDs de planta hoy: el workflow de despliegue verifica `/v1/plants/lavandula-angustifolia` (`.github/workflows/deploy-backend.yml`), la prueba ignorada `backend/catalog-api/tests/real_catalog.rs` (que además fija 10 usos y 4 partes de la lavanda), los fixtures de la app (`rosmarinus-officinalis`, `rosmarinus-x-lavandulaceus`) y datos sintéticos de los tests del backend, que no dependen del catálogo real. No se encontró ningún lugar que persista IDs (la app no tiene persistencia; Favoritos e Historial son pestañas sin acción).
- Las specs de la API ya prohíben exponer procedencia en las respuestas y mantienen un contrato aditivo dentro de `/v1`; este cambio no toca el contrato.

Motivación y cifras del piloto: véase `proposal.md`. Los archivos del piloto se borraron con un reinicio y no existen en el repo; sus resultados son la evidencia de las decisiones de abajo. Los scripts del piloto (en especial el resolvedor) pueden consultarse como referencia en las transcripciones locales de los subagentes, en `~/.claude/projects/-Users-jsrc1115-Code-boticario-ai/4ddab13b-6789-4d5d-8a32-311afde5ae3e/subagents/agent-*.jsonl` (por ejemplo `agent-a75c02de6d8441688`). Es un apoyo opcional: el repo no depende de ellos y las tareas describen lo que hay que construir.

## Goals / Non-Goals

**Goals:**

- Una semilla versionada, revisable por diff y reproducible, que todos los entornos usen para armar `catalog.db` sin red y sin LLM.
- Un registro por planta que sirva a la app (Explorar, Pasaporte, Buscar por objetivo) y, más adelante, al chat «Boticario» (RAG), con cada dato citado.
- Que ni el contrato HTTP ni la app cambien en este cambio.
- Regeneración incremental: solo se vuelve a pagar el LLM por lo que cambió.

**Non-Goals:**

- Los de `proposal.md` (cambios 2 y 3, capa humana, chat, permiso comercial de TPPT).
- Ejecutar el LLM en cada entorno o en CI.
- Resolver IDs anteriores por alias en la API (los alias se guardan, no se sirven).
- Cambiar el esquema de `plant`/`plant_name`/`plant_use` de forma incompatible: el esquema se amplía con tablas.

## Decisions

### D1. Las herramientas offline viven en `tools/catalog-seed/`, en Python; el build sigue en Rust

Descarga, resolución, paquetes, prompt, validador y orquestación de la consolidación van en Python dentro del repo, con la biblioteca estándar y `xlrd` (suficiente en el piloto) más la herramienta que decida el spike de PDF (D9). Solo las usa el desarrollador, no entran en la imagen ni en la CI del backend. El paso de la semilla a `catalog.db` va en Rust, en `catalog-ingest`, porque comparte el hash de contenido, la escritura atómica, el esquema Diesel y los tests con la API.

Alternativas:

- Todo en Rust. Un solo lenguaje y un solo toolchain, y el validador y el build compartirían tipos. Se descarta porque el piloto con Python/stdlib fue rápido de iterar (XLS, PDF, HTML, JSON, SPARQL) y porque las bibliotecas de PDF y XLS en Rust son menos maduras; el costo es duplicar la validación estructural, que se mitiga en D3 con una prueba de contrato.
- Notebooks o scripts sueltos fuera del repo. Pierden reproducibilidad y versionado del prompt, que es parte del resultado.
- Mantener el contrato `SourceAdapter` y añadir un `SeedAdapter`. Se descarta en D3.

### D2. Formato y ubicación de la semilla: un JSON por planta más un manifiesto

`data/seed/plants/<id>.json` (unos 2.400 archivos de unos 6,5 KB, unos 16 MB) y `data/seed/manifest.json`. JSON con claves ordenadas, sangría de 2 espacios y salto de línea final, para que un cambio de una planta sea un diff de un archivo. El nombre del archivo es el `id` y la construcción lo verifica.

El manifiesto lleva: versión del formato, fuentes (identificador, nombre, versión o snapshot con fecha, URL, licencia, atribución, checksum), versión de prompt, versión del esquema del registro, modelo, número de plantas, conteo de `reviewFlags` por tipo y `seedHash`: un sha256 del contenido canónico de los registros ordenados por `id` y de `data/seed/goals.json`. No lista un hash por archivo, para que el manifiesto no cambie en cada diff de planta más allá de `seedHash` y de los conteos. Un comando de las herramientas (`seal`) recalcula el manifiesto tras editar un registro; la construcción solo verifica.

El registro añade tres campos respecto de la lista acordada, que se registran aquí como decisión para su revisión:

- `refs`: el subconjunto del diccionario de refs que el registro usa (`{dataset, label, license}`). Los paquetes no se versionan (D6), y sin este diccionario la construcción no podría resolver citas ni atribución sin reconstruir los paquetes.
- `promptVersion` y `model`, para decidir qué regenerar (D11).
- `aliases`: IDs anteriores de la planta (D5).

Alternativas:

- Un único archivo JSON/JSONL con 2.400 registros: un diff por cambio pequeño es ilegible y los conflictos de fusión son frecuentes.
- Un archivo SQLite versionado: binario, sin diff revisable.
- Un registro por planta sin manifiesto: no hay forma de saber con qué fuentes y prompt se generó, ni de detectar ediciones accidentales.
- Hash por archivo en el manifiesto: detecta mejor qué archivo se alteró, pero hace que cada regeneración toque el manifiesto en miles de líneas.

### D3. Mapeo de la semilla a `catalog.db`: el contrato de la API no cambia y los campos nuevos van en tablas nuevas

La API actual sigue funcionando sin cambios de código. La construcción escribe:

| Dato del registro | Destino en la capa neutral |
|---|---|
| `id`, `scientificName.name`, `family` | `plant` (el ID de la semilla se escribe tal cual; `family_source_id` es el dataset del primer ref de `scientificName`) |
| `scientificName.name` y `synonyms` | `plant_name` con `kind = scientific` e idioma `la` (como hoy). Los sinónimos mantienen la búsqueda por nombres antiguos (`rosmarinus officinalis` encuentra `salvia-rosmarinus`) sin cambiar el contrato: la app filtra los nombres por `kind` |
| `displayName` | `plant_profile.display_name`, que es la fuente de verdad del nombre para mostrar. Además se escribe como nombre común en `plant_name` (junto con `commonNames`), de modo que siga encontrándose por búsqueda. No se confía en el orden de `plant_name`: la API actual ordena los nombres comunes alfabéticamente, así que "el primero" no es el `displayName`; los cambios 2 y 3 leen `display_name` |
| `commonNames` | `plant_name` con `kind = common` e idioma por nombre |
| `partsUsed` | `plant_part` |
| `traditionalUses` | `plant_use`: un uso por cada ref con cita resuelta de cada grupo, con `activity` en español, idioma `es` y esa referencia. Un grupo con `pendingReview` (alguna cita sin resolver) no genera ningún uso de la API |
| Todo lo demás | tablas nuevas |

Tablas nuevas (los nombres y columnas exactos se fijan en la tarea 7.1 y se registran en `docs/data/modelo-de-datos.md`): `plant_profile` (`plant_id`, `display_name`, `authors`, `origin`, `description`, `oil_type`, `record_version`, `bundle_hash`, `prompt_version`), `plant_use_group` (con `pending_review`) y `plant_use_group_ref` (actividad traducida y original, `n`, países ya en español), `goal` y `goal_subarea` (catálogo de objetivos, véase D8), `plant_goal` (`plant_id`, `goal_id`, `subarea_id`, `area`, `evidence`, `pending_review`) y `plant_goal_ref`, `plant_safety` y `plant_safety_ref`, `plant_image`, `plant_alias` y `plant_review_flag` (`plant_id`, `code`, `target`, `message`). `reference` se amplía con `dataset` y `license`, y `source` y las tablas de atribución (`plant_*_source`) siguen vigentes: se rellenan con el dataset de los refs de cada dato. Las claves de fuente quedan como dato de procedencia, no como identificador público. `SCHEMA_VERSION` sube; la API la comprueba al arrancar y debe aceptar la nueva (tarea 7.1).

Nombres y columnas fijados en la tarea 7.1 (migración `data/migrations/2026-10-26-000000_catalog_v2`, `SCHEMA_VERSION` 2). Los valores lógicos son `BOOLEAN` con `CHECK (x IN (0, 1))` y las posiciones (`position`) conservan el orden del registro.

`plant_profile (plant_id PK, display_name, authors, origin, description, oil_type, record_version, bundle_hash, prompt_version)`: una fila por planta; `display_name`, `authors`, `origin`, `description` y `oil_type` son nulables porque el registro admite `null` en esos campos. `authors` son los del nombre científico canónico y `oil_type` guarda `oil.type` (hoy solo `Esencial`).

`plant_profile_ref (plant_id, field, reference_id)` con clave primaria `(plant_id, field, reference_id)` guarda las referencias de los campos del perfil, para saber de qué dataset sale cada uno (por ejemplo, que la descripción sale de Wikipedia). `field` es una lista cerrada con los nombres del registro: `scientificName`, `family`, `displayName`, `origin`, `description`, `oil` y `partsUsed` (las referencias de todas las partes). Los demás datos ya tienen su atribución: nombres en `plant_name_source`, usos en `plant_use_source` y `plant_use_group_ref`, objetivos en `plant_goal_ref`, seguridad en `plant_safety_ref`, y la imagen lleva su licencia en `plant_image`.

Las fuentes del manifiesto llevan `name` (nombre legible) y `url` (página del dataset), que la construcción copia a `source.name` y `source.url`; salen de los campos `name` y `pageUrl` de `tools/catalog-seed/sources.json`.

`plant_use_group (id, plant_id, position, activity, activity_source, n, countries, pending_review)`: `countries` es un arreglo JSON de textos en español, porque solo se lee completo y nunca se filtra por país; `pending_review` es verdadero solo si el grupo no tiene ninguna cita resuelta, y esos grupos no generan filas en `plant_use`.

`plant_use_group_ref (use_group_id, key, position, text, resolved, reference_id)` con clave primaria `(use_group_id, key)`: guarda también las citas sin resolver (`reference_id` nulo, `text` = «<clave> (sin resolver)»), y un `CHECK` exige que `resolved` sea verdadero si y solo si hay `reference_id`.

`goal (id, label, position)` y `goal_subarea (id, goal_id, label, position)` salen de `data/seed/goals.json`. `plant_goal (id, plant_id, goal_id, subarea_id, position, area, evidence, pending_review)` lleva una clave foránea compuesta `(goal_id, subarea_id)` hacia `goal_subarea (goal_id, id)`, de modo que la subárea debe ser del objetivo (si es nula no se comprueba), y un índice único `(plant_id, goal_id, COALESCE(subarea_id, ''), area)`. El índice `(goal_id, subarea_id, plant_id)` sirve la consulta de plantas por objetivo y subárea. `plant_goal_ref (plant_goal_id, reference_id)` enlaza con `reference`.

`plant_safety (plant_id PK, level, text)` con `level` nulable (`alto`, `medio` o `bajo`; nulo es una precaución sin nivel) y sin fila cuando el registro no trae `safety`. `plant_safety_ref (plant_id, reference_id)` enlaza con `reference`.

`plant_image (plant_id PK, url, page_url, author, license, license_url, attribution_required)`: como máximo una imagen por planta; `author` y `license_url` son nulables.

`plant_alias (alias PK, plant_id)`: el alias es único en toda la base porque resuelve a una sola planta; el error de alias que iguala el ID de otra planta lo detecta la construcción (tarea 7.4). `plant_review_flag (id, plant_id, code, target, message)` con índices por planta y por código.

`reference` gana `dataset`, `license` y `url` como columnas nulables (las filas de la v1 no las traen); la construcción desde la semilla las escribe siempre y rechaza un dato sin dataset o licencia (tarea 7.4). El `label` de las referencias de la semilla va a `citation`, y su `url` a `reference.url` (el cambio 2 la usa para enlazar el artículo en la atribución de «Fuentes»). Las `refs` a nivel de dato (nombre, origen, descripción, grupo de uso, imagen) siguen reflejándose en la atribución (`plant_*_source`) y no tienen tabla propia.

Se retira el marco de adaptadores: `SourceAdapter`, `default_registry`, el adaptador de USDA, `raw.rs`, `download.rs` y `data/sources.toml`. Se conservan `normalize`/`slug`, la escritura atómica, `content_hash`, el esquema neutral y su test de independencia de datasets.

Alternativas:

- Conservar el marco y añadir un `SeedAdapter`. El contrato asume una fuente = un conjunto de plantas por identidad, con consolidación por prioridad; la semilla ya está consolidada y trae campos que el contrato no modela (objetivos, seguridad, imagen). Se mantendría código sin uso real y sin sentido de prioridad entre fuentes. Se descarta.
- Escribir los sinónimos solo en una tabla nueva. Evita cambiar `names`, pero la búsqueda por nombre antiguo deja de funcionar hasta el cambio 2, y los IDs ya cambian. Se prefiere mantener la búsqueda.
- Guardar el registro JSON completo en una columna. Simple, pero no es consultable por la API ni por el cambio 3 (plantas por objetivo) y rompe la regla del esquema neutral.
- Un uso por grupo con una sola cita. Pierde las citas restantes y cambia la cardinalidad actual del contrato (un uso = una referencia).

Cambios visibles para quien consume la API (todos de contenido, no de forma): nombres comunes en español, usos en español, plantas fusionadas o separadas, IDs nuevos y unas 35 plantas más. Se documentan en la QA (tarea 10).

Para que la validación de la semilla no diverja entre Python y Rust, el esquema JSON del registro es la fuente única: el validador de Python lo aplica y el lector de Rust usa tipos con `deny_unknown_fields`; una prueba de contrato lee en Rust los registros de la corrida de control (tarea 5) y exige que el validador de Python los acepte con el mismo conteo.

### D4. WCVP es el backbone principal y WFO el respaldo

Evidencia del piloto (2.376 plantas de USDA): tras corregir los homónimos, WCVP resuelve 2.125 y WFO 2.127, y coinciden en el aceptado el 94,9 % de las veces. WCVP gana por tres motivos: trae distribución nativa e introducida para el 99,6 % de las plantas, marca la homotipia (`homotypic_synonym`) que la regla de colisiones necesita, y deja menos nombres sin aceptado (3 frente a 12). La manzanilla solo resuelve con WCVP (en WFO queda «Unchecked»). WFO se usa solo si WCVP no resuelve y da un único aceptado, y pasa por la regla de colisiones.

El piloto dejó 164 nombres de USDA sin resolver en ningún backbone y 62 o 63 entradas que solo nombran el género. Permanecen en el catálogo con la identidad de USDA y un `reviewFlag`. Las reglas de normalización y resolución están en `specs/catalog-seed/spec.md`.

Alternativas: WFO como principal (menos distribución, sin homotipia, la manzanilla no resuelve), GBIF Backbone (taxonomía compuesta de varias fuentes, sin marca homotípica fiable y con otra licencia) y Kew POWO por API (límites de peticiones; el dataset descargable de WCVP tiene lo mismo con versión fija).

### D5. Colisiones, IDs fijos y alias

Regla de colisiones («criterio de Wikipedia»): en un grupo de plantas del universo que resuelven al mismo aceptado se fusionan siempre el aceptado y sus sinónimos homotípicos. Un miembro heterotípico queda como planta propia, con ID de su nombre, su nombre científico y un `reviewFlag`, solo si se cumple una de dos condiciones: su propio nombre científico tiene un artículo propio en Wikipedia en español (existe, no es una redirección y es distinto del artículo del nombre aceptado del grupo, también tras seguir las redirecciones), o está en la lista versionada de excepciones «separar siempre». Si no, se fusiona con la planta del aceptado: su nombre queda como sinónimo y como alias, y el registro lleva un `reviewFlag` de fusión heterotípica para revisión humana. El armado sigue fallando si dos plantas terminan con el mismo ID.

Evidencia medida con datos reales: de 71 miembros heterotípicos, el criterio fusiona los duplicados claros. *Cinnamomum zeylanicum* redirige a *C. verum* y *Thevetia peruviana* tiene artículo, pero el del aceptado *Cascabela thevetia* redirige a él, así que comparten artículo y se fusionan. Separa bergamota, lima, naranja, pomelo, brócoli, repollo y *Grindelia robusta*, que tienen artículo propio. Sin excepciones fusionaría variedades de uso diferenciado sin artículo en español, como el hinojo dulce o la col china. Lista inicial de excepciones, que el usuario revisa: *Brassica napus* var. *napobrassica*, *Brassica oleracea* var. *acephala*, *Brassica chinensis*, *Brassica pekinensis* (*B. rapa*), *Citrus meyeri*, *Foeniculum vulgare* var. *dulce*, *Grindelia humilis*, *Lactuca sativa* var. *capitata*, *Origanum creticum* y *Origanum vulgare* var. *hirtum*.

Registro de decisiones y D14: la decisión de cada grupo se registra una vez en un archivo versionado de las herramientas, con la evidencia de Wikipedia (título consultado, si existe, redirección y destino, fecha), junto con la lista de excepciones. Las corridas siguientes leen ese archivo y no consultan de nuevo a Wikipedia para un grupo ya decidido, así que desactivar Wikipedia (D14) o un cambio posterior de Wikipedia no altera las decisiones tomadas ni los IDs. Un grupo nuevo sin decisión registrada y sin datos de Wikipedia, por ejemplo con Wikipedia desactivada, usa la regla conservadora anterior: cada heterotípico es planta propia con `reviewFlag`. Cambiar una decisión ya registrada es una edición explícita del archivo, no un efecto de la corrida.

Alternativas descartadas: la regla anterior (todo heterotípico es planta propia) deja unas 48 plantas duplicadas, como *Cinnamomum zeylanicum* junto a *C. verum*; y la fusión por defecto con excepciones para separar, que funde por error plantas de uso diferenciado y obliga a mantener una lista larga que crece con cada versión de WCVP. Motivos del piloto que se conservan: sin separar los heterotípicos con artículo propio, la bergamota y la lima se fusionan con el limón, naranja y pomelo comparten aceptado, y brócoli, repollo y kale son *Brassica oleracea*. Aparte, la regla «homónimo no resuelto → ambiguo» evitó que el almendro (*Prunus dulcis*) se fusionara con el cerezo; quedaron 19 homónimos para revisión.

El ID es el slug del nombre aceptado de WCVP, generado una vez y fijo en la semilla. Si Kew renombra, cambia el nombre mostrado y no el ID. Cambian 629 de los 2.376 IDs actuales (el piloto estimaba unos 500). `lavandula-angustifolia` se conserva y su prueba va como tarea (la verificación del despliegue depende de él).

Alias: sí se guardan los IDs anteriores (el slug del `TAXON` literal de USDA de cada planta fusionada o renombrada) en `aliases` del registro y en `plant_alias`. Cuestan poco, y no pueden reconstruirse después sin conservar el ZIP de USDA. Hoy nada los consulta: la API no los resuelve en este cambio (el cambio 2 puede añadir una redirección o una búsqueda por alias). Un alias nunca puede igualar el ID de otra planta: el generador lo descarta y lo registra, y la construcción lo trata como error.

Alternativas:

- No guardar alias, porque no hay consumidores. Más simple, pero pierde la única forma barata de explicar o migrar un ID antiguo (por ejemplo para favoritos futuros).
- Mantener los IDs de USDA y añadir el nombre aceptado aparte. Evita el cambio de los IDs (629 con el universo real; el piloto estimaba ~500), pero deja IDs que no coinciden con el nombre mostrado y no resuelve la fusión de sinónimos.
- ID por nombre aceptado recalculado en cada build. Un renombre de Kew cambiaría IDs ya publicados; se descarta.

### D6. Paquete por planta: determinista, no versionado, con filtro de homónimos

Formato v1 validado en el piloto (raíz con `bundleVersion`, `plantKey`, `bundleHash`; `identity`; `sections`; `refs`). Se construye con una función pura del contenido de `data/.cache/` y se escribe en `data/work/bundles/` (ignorado por Git): son unos 9,7 millones de tokens de texto (p50 de unos 2.900 tokens por planta; en el piloto el promedio fue de unos 8.300 y el máximo de 21.700, porque se eligieron plantas con más datos). Lo que se versiona es el registro, que guarda el `bundleHash`.

Tareas del piloto que se incorporan: filtrar los ítems de Wikidata, Wikipedia y Commons a nombres que resuelven al aceptado de la planta (por homónimos entraron datos de *L. latifolia* en la lavanda y de *P. edulis* en la pasiflora), y sumar las secciones de seguridad de la EMA (D9).

Alternativas: versionar los paquetes (unos 34 MB de JSON, ruido en el historial y duplicación de licencias de terceros) y calcular los paquetes dentro del lote del LLM (pierde el determinismo y el hash).

Limitación aceptada: Wikidata, Wikipedia, Commons y la EMA cambian. Los snapshots se cachean con checksum y fecha, pero la caché es local: otra máquina o fecha puede dar otros paquetes. Para la semilla eso es parte del diseño incremental (cambia el `bundleHash`, se regenera esa planta); no se promete reproducir la semilla exacta desde cero.

### D7. Política «variante A» del LLM y validador

El LLM solo elige, traduce y resume lo que está en el paquete, y cada campo cita refs del paquete. El riesgo concreto es que invente un nombre común inofensivo para una planta tóxica. El registro v1 está en `specs/catalog-seed/spec.md`; con la variante A el campo `basis` del piloto sobra, porque todo es «bundle».

Correcciones del piloto que entran en el prompt, el mapa y el validador: separar el resultado combinado de la EMA por `;` (menta, árbol del té y caléndula perdían objetivos); usar el nombre científico propio en plantas separadas por colisión (*Citrus × bergamia*); aceptar nombres con idioma `und` si son claramente españoles y llevan ref; contar el compuesto `EO` de USDA como aceite esencial y no un aceite fijo como el de ricino; definir los niveles de seguridad (D8); y marcar para revisión una planta con interacciones graves en «Mental stress and mood disorders» (hipérico) antes de publicarla en `relajacion-estres`.

Alternativas:

- Variante B: el LLM completa con su conocimiento y marca `basis: model`. Da registros más ricos para el 41 % de las plantas sin usos de USDA, pero introduce afirmaciones sin cita en un catálogo de plantas con riesgo de toxicidad, y el requisito vigente de `plant-passport` lo prohibía. Se descarta.
- Plantillas deterministas sin LLM: no traducen ni resumen, y el texto en español no es viable a escala.
- Validar solo por muestreo: no detecta refs rotos ni objetivos sin respaldo; el validador automático es el control principal y la revisión humana (fuera de alcance) solo se apoya en `reviewFlags`.

Actividades sensibles (decisión del usuario, prompt v6, tarea 4.10). Entre los usos de USDA hay actividades que, dichas como «uso tradicional para cáncer», pueden leerse como promesa de curación, y otras que son en realidad una señal de toxicidad. Una lista versionada, `tools/catalog-seed/sensitive-activities.json`, define dos categorías y los términos de USDA que entran en cada una (comparados por la forma base, sin el calificador entre paréntesis y sin distinguir mayúsculas, de modo que `Cancer(Breast)` cuenta como `Cancer`). Enfermedades graves (cáncer y tumores, diabetes, sida o VIH, tuberculosis, malaria, epilepsia, hepatitis, cirrosis y otras): el grupo sigue en `traditionalUses` con `activity` «Uso tradicional, sin eficacia demostrada: <enfermedad>» y `activitySource` con el original. Señales de riesgo (`Poison`, `Fatality`, `Abortifacient`, `Toxic` y similares): el grupo no va en `traditionalUses`, va a `safety` como advertencia («Advertencia: registrada como veneno en usos tradicionales»), con los refs `usda_use:*` de sus filas; no fijan nivel por sí solas, así que sin otra fuente `safety` queda `{level: null, text, refs}` (regla de la v5). El validador exige la fórmula, impide las señales de riesgo en `traditionalUses` y exige la advertencia en `safety` con al menos un ref `usda_use:*` de esos grupos. Los términos dudosos quedan fuera de la lista y documentados en ella. En la app la sección `safety` se llamará «Precauciones» (cambio 2). Alternativas descartadas: dejarlas literales, porque podía leerse como promesa de curación; ocultarlas hasta una revisión humana, que no existe por ahora; y excluirlas, porque perdía información que sí está en las fuentes.

La palabra de dosis o eficacia es una advertencia y no un error, porque una lista de palabras produce falsos positivos (por ejemplo la cita de un título de artículo).

### D13. El LLM resuelve las citas abreviadas

Medido en `raw.db`: 31.629 filas de ETHNOBOT (38 %, 899 claves distintas) tienen una REFERENCE sin coincidencia exacta entre las 2.043 claves de las referencias de USDA, y su LONGREF propio está vacío. Desglose: 6.055 solo difieren en formato (`Burkill,1966` / `Burkill, 1966`, mayúsculas o puntuación), 9.576 son `Woi.<n>` (existe `WOI`, «The Wealth of India», 1948-1976), 10.992 son `Eb<vol>:<pág>` (existen `EB`, «Economic Botany», y algunas `EBxx:yyy`), 3.040 son `Woi.Syria` (obra poco clara) y 1.966 son otras.

Decisión: la resolución es parte de la consolidación. Cada grupo de uso conserva las claves cortas tal como vienen. El paquete suma, por clave, hasta 5 entradas candidatas de las referencias de USDA, cada una con su ref `usda_reference:<REFERENCE>` y su LONGREF, en este orden de prioridad: la entrada exacta; las de clave normalizada igual (minúsculas, sin espacios ni puntuación); las que comparten el prefijo alfabético (`woi` encuentra `WOI`, `eb` encuentra `EB` y las `EBxx:yyy`, `burkill` encuentra `Burkill, 1966`), ordenadas por el prefijo común más largo de la clave normalizada. El tope de 5 acota el tamaño del paquete. La selección de candidatas es una heurística simple y deliberada, no la resolución: la decisión de a qué cita corresponde cada clave la toma el LLM, que cita el ref de la candidata (`Woi.10` → «The Wealth of India, vol. 10»; `Eb24: 441` → «Economic Botany 24: 441»). Si ninguna corresponde, la cita queda como la clave con la marca «(sin resolver)» (`{key, ref: null, text: "<clave> (sin resolver)"}`) y el registro lleva un `reviewFlag` por cada grupo con una clave sin resolver `{code: "cita-sin-resolver", target: "traditionalUses[<índice>]", message}` (el índice es la posición del grupo en `traditionalUses`), para que el revisor humano sepa exactamente qué revisar. Se espera que queden sin resolver unas 5.000 filas (6 %) si el emparejamiento es correcto. Decisión del usuario sobre ese 6 %: se marcan para revisión humana, y una segunda decisión (prompt v5, tarea 4.9) acota qué grupo queda oculto. En la corrida de control, 68 de los 69 grupos ocultos tenían al menos una cita válida y solo los ocultaba una clave extra sin candidata, casi siempre `Woi.Syria`. Regla: `pendingReview` es verdadero solo si el grupo no tiene ninguna cita resuelta; un grupo con al menos una cita resuelta se muestra aunque conserve claves «(sin resolver)», que se ven como tales en `citations`. Cada grupo con al menos una clave sin resolver conserva su `reviewFlag` `cita-sin-resolver` aunque se muestre, para el futuro módulo de validación humana, que todavía no existe. Los grupos pendientes se guardan en la semilla y en las tablas nuevas (`plant_use_group.pending_review`) pero no generan filas en `plant_use` hasta que una revisión humana los apruebe; esa capa de revisión queda fuera de alcance, igual que para los objetivos pendientes. El validador exige un flag por cada grupo pendiente, que todo grupo con alguna cita sin resolver tenga el flag `cita-sin-resolver` y que `pendingReview` sea verdadero si y solo si ninguna cita del grupo está resuelta. Impacto para el cambio 2: mostrará un aviso fijo en la sección de usos tradicionales, y las claves «(sin resolver)» de los grupos visibles se ven como tales; el aviso no es de este cambio. Respeta la variante A: solo elige y formatea lo que está en el paquete.

Alternativas descartadas:

- Reglas deterministas de normalización y prefijo que resuelvan la cita en las herramientas: reproducibles, pero obligan a mantener reglas por fuente y por formato de cita (`Woi.`, `Eb`, `Burkill,`) y a decidir casos ambiguos con código.
- Descartar las filas sin coincidencia exacta (comportamiento actual): pierde el 38 % de las filas de uso, incluidas obras muy citadas.

Pros: no hay que mantener reglas por fuente y el pipeline de datos sigue simple. Contras: es menos determinista (otra corrida puede emparejar distinto). Mitigación: el validador exige que toda cita apunte a un ref `usda_reference:*` del paquete o esté marcada «(sin resolver)», y la corrida de control mide cuántas quedan sin resolver y revisa a mano una muestra de emparejamientos (Burkill, Wealth of India, Economic Botany y `Woi.Syria`).

### D8. Objetivos y niveles de seguridad

El catálogo de objetivos (ids, etiquetas en español, orden y subáreas) vive en un archivo versionado de la semilla, `data/seed/goals.json`, que forma parte del `seedHash`; la construcción lo carga en `goal (id, label, position)` y `goal_subarea (id, goal_id, label, position)`, para que los cambios 2 y 3 lean de `catalog.db` los nombres, el orden y las subáreas sin duplicarlos en la app o la API. Ids de objetivo: `relajacion-estres`, `mejorar-el-sueno`, `cuidado-de-la-piel`, `alivio-respiratorio`, `cansancio-y-fatiga` y `otros-objetivos`; subáreas de `otros-objetivos`: `digestion`, `vias-urinarias-y-genitales`, `dolor-e-inflamacion`, `boca-y-garganta`, `circulacion` y `molestias-oculares`. Las etiquetas son provisionales: el usuario las revisa en la app. Se eligió un archivo de la semilla y no el manifiesto porque el manifiesto describe cómo se generó la semilla y no contenido servido; alternativa descartada: codificarlo en Rust (obliga a recompilar y duplica el mapa). El mapa de las herramientas (`goals-map.json`: área de la EMA a objetivo, subárea y traducción del área al español) se valida contra este catálogo.

Los objetivos salen solo de las áreas terapéuticas de la EMA con monografía o entrada de lista (tabla en la spec). «Cansancio y fatiga» reemplaza a la fila «Concentración» de P06; el ajuste en la app es del cambio 3 y el usuario aprobó revisarlo allí. `otros-objetivos` lleva la subárea: digestión (gastrointestinales, falta de apetito, estreñimiento, digestivos), vías urinarias y genitales, dolor e inflamación, boca y garganta, circulación y molestias oculares.

Objetivo pendiente de revisión: el hipérico (interacciones graves) en `relajacion-estres` queda en el registro con `pendingReview: true` y un `reviewFlag` cuyo `target` es ese objetivo; `plant_goal.pending_review` lo refleja y los cambios 2 y 3 omiten esos objetivos. Los `reviewFlags` son objetos `{code, target, message}` (`target` es el campo o el objetivo afectado, por ejemplo `goals.relajacion-estres`) y no cadenas sueltas.

Textos visibles en español: `goals[].area` es la traducción del área tomada del mapa, `goals[].evidence` se escribe en español y los países de `traditionalUses[].countries` se traducen al español sin conservar el original (el original sigue disponible en el paquete y en la cita; no hay un campo duplicado para no engordar el registro).

Seguridad (decisiones del usuario, mapa `safety-map.json` versión 3):

- TPPT: «very strong toxic» y «strong toxic» a alto; «toxic» y «toxic (unknown strength)», «liver toxic», «cytotoxic», «estrogenic», «carcinogenic» y «phototoxic» a medio; «weak toxic», «skin-irritating» y «allergenic» a bajo; «nontoxic», «unknown», «infested plants only» y «stimulating» sin nivel. La toxicidad en animales no fija nivel.
- EMA: las interacciones graves (patrones versionados) a alto. Las declaraciones públicas con datos de seguridad (kava, bálsamo del Perú, celidonia, adhatoda y aceite de salvia) pasan de sin nivel a medio: no tienen sección 4.5, pero la EMA documenta un problema de seguridad.
- EFSA, variante «B: lista amplia»: una planta del compendio fija medio solo si tiene al menos una fila (no «Non Detected Value (<LOD)») cuya sustancia está en una lista versionada de alta preocupación, con los nombres exactos de `SubstanceName`. El resto de las sustancias es evidencia para el texto de seguridad y no fija nivel. La lista tiene cuatro grupos: genotóxicas o carcinógenas (estragol, metileugenol, safrol, isosafrol, asarona y beta-asarona, *Aristolochia*, alcaloides pirrolizidínicos y ptaquilósido); tuyona alfa y beta, pulegona, mentofurano y cumarina; furocumarinas fototóxicas (bergapteno, psoraleno, metoxaleno, imperatorina y las demás del compendio); y venenos potentes (glucósidos cardíacos, alcaloides tropánicos, aconitina, ricina, abrina, taxina, cucurbitacinas, coniina, estricnina, colchicina, cicutoxina y enantotoxina). Quedan fuera como evidencia el 1,8-cineol, el alcanfor, los taninos, los oxalatos, las lectinas, las saponinas, la cafeína, el anetol, el carvacrol y las antraquinonas; los glucósidos cianogénicos, la emodina, la elemicina y la miristicina son dudosos y quedan fuera anotados como candidatos. - USDA (decisión del usuario del 2026-10-26, mapa versión 3): las señales letales de los usos (`Fatality`, `Fatal`, `Death`, `Suicide` y `Homicide`, comparadas por la forma base de la actividad, igual que en `sensitive-activities.json`) fijan alto por precaución. El paquete las trae como una entrada más de `sections.safety` (`source` `usda`, `level` `alto`, `levelReason`, los refs `usda_use:*` de esas filas y los términos), de modo que el prompt, que ya manda tomar el más alto entre los `level` de las entradas, no cambia (sigue en la versión 7). Las demás señales de riesgo (`Poison`, `Abortifacient`, `Carcinogenic`, ...) siguen siendo advertencia sin nivel: el mapa las declara con `level: null` y su motivo. Antes de esta decisión, de las 57 plantas con señales letales, 13 quedaban en alto, 16 en medio y 28 sin nivel. El validador exige que `safety.level` sea igual al más alto entre los `level` de las entradas del paquete, o nulo si ninguna fija nivel.
- El estado completo vive en `tools/catalog-seed/safety-map.json`.

Alternativas medidas para EFSA: cualquier sustancia del compendio fija medio (la propuesta inicial; unas 550 plantas con «Precaución», demasiado amplio porque el 1,8-cineol, el alcanfor o los taninos las marcarían) y otras variantes con listas más cortas o más largas. La variante B deja unas 300 plantas del universo en medio o alto y, de las 190 con objetivos, 47; la lavanda, la menta, el romero, la salvia y el hinojo quedan en medio, y el eucalipto, el jengibre y el tomillo, no. EFSA por sí sola no fija alto: no gradúa la gravedad ni la dosis.

Advertencias sin nivel (decisión del usuario, prompt v5 y tarea 4.9): antes, si ninguna entrada de `sections.safety` fijaba nivel, el registro llevaba `safety: null` con el flag `sin-datos-de-seguridad` y se perdían las contraindicaciones, advertencias e interacciones de la EMA (por ejemplo el eucalipto en niños). Ahora hay tres casos. Con nivel: sin cambios, `safety` lleva el nivel más alto. Con información de seguridad pero sin nivel: `safety` es `{level: null, text, refs}`; esa información son las secciones 4.3, 4.4 o 4.5 de la EMA con contenido (que no sea solo «ninguna reportada» o «sin estudios»), categorías de TPPT sin nivel que valga la pena decir y sustancias de evidencia de EFSA; el texto describe lo que registran las fuentes, sin dosis ni consejos, y la planta no se marca como «Precaución». Sin ninguna información de seguridad: `safety` es `null` con el flag `sin-datos-de-seguridad`. El esquema admite `safety.level` nulo (con `text` y `refs` obligatorios) y el validador comprueba la coherencia con el paquete. Impacto para el cambio 2: su contrato cambia porque el nivel de `safety` puede ir vacío; la API y la app deben mostrar el texto de seguridad sin nivel y sin la etiqueta de precaución. No se toca aquí.

La lista exacta de interacciones graves de la EMA se fijó en la tarea 4.4 a partir de los datos reales.

Alternativas: derivar objetivos de los usos tradicionales de USDA (más cobertura, pero convierte registros etnobotánicos en recomendaciones, justo lo que la spec prohíbe) y que el LLM asigne objetivos libremente (no verificable).

### D9. Extracción de seguridad de los PDF de la EMA: spike primero

Las contraindicaciones, advertencias e interacciones solo existen en PDF (comprobado en la página de *Hyperici herba*). Son PDF de texto con secciones numeradas, pero la extracción no está probada. La tarea 3.1 es un spike sobre 5 a 8 PDF (monografías y declaraciones públicas, entre ellos hipérico) con `pdftotext -layout` (poppler) y, como alternativa, `pypdf`. Criterio de éxito: en todos los PDF de la muestra se recuperan las secciones de contraindicaciones, advertencias e interacciones con su numeración y sin mezclar columnas. Si el spike falla, la sección de seguridad de la EMA queda fuera del paquete, se registra el flag de extracción fallida y se vuelve a este diseño antes de seguir (la regla de nivel alto por interacciones graves depende de ella). Cada PDF se descarga con espera entre peticiones, se cachea con checksum y la extracción se guarda como texto en la caché.

Alternativas: limitarse al JSON de la EMA (sin seguridad textual; deja `safety` dependiente solo de TPPT y EFSA) y extracción con LLM de PDF completos (cuesta tokens y pierde el control de las citas).

### D10. Wikidata: consulta dirigida con caché, POST y reanudación

Consulta SPARQL dirigida por lotes de plantas, no el dump (nombre común en español P1843, imagen P18, sitelink de eswiki, GBIF y POWO). El piloto recibió 429 con `Retry-After: 1000`, y POST funcionó cuando GET falló. La herramienta usa POST, un `User-Agent` identificable, lotes pequeños, respeta `Retry-After`, guarda cada respuesta en la caché y se reanuda sin repetir consultas. Si el límite se agota, el paso termina con estado de reanudación en vez de seguir. Las plantas sin respuesta quedan marcadas en su paquete y pueden consolidarse sin imagen.

Alternativas: el dump de Wikidata (decenas de GB para ~2.400 plantas) y la API `wbgetentities` (más peticiones, mismo límite). Para Wikipedia y Commons se usan sus APIs REST con la misma caché y espera.

### D11. Ejecución de la generación completa: decisión explícita del usuario

Estimación del piloto para unas 2.411 plantas (el universo real es de 2.355, con 2.354 en la semilla): unos 23 millones de tokens en unos 240 lotes de 10, y unas 3 horas con 8 lotes en paralelo (el piloto midió 12.000 a 15.500 tokens por planta y 4 a 7 minutos por lote; las plantas del universo son más ligeras que las del piloto). Es la última tarea y no se ejecuta sin que el usuario elija el modo:

- Opción A: agentes de Claude Code por lotes, orquestados con un workflow. Coherente con lo acordado (Claude Code como LLM), sin integración nueva, pero requiere que el usuario pida el workflow explícitamente y consume la cuota del plan.
- Opción B: un script de las herramientas con la API de Anthropic en modo batch. Reanudable, medible y versionado; del orden de US$40 a 70 con Sonnet 5.5 según la estimación acordada; requiere clave de API y un cambio de enfoque respecto de «Claude Code como LLM».
- Opción C: lotes manuales desde sesiones de Claude Code. Sin infraestructura, lento y difícil de reanudar.

Ninguna se elige en el diseño. Para cualquier modo, la regeneración incremental usa el mismo plan (plantas cuyo `bundleHash`, versión de prompt o de esquema difieren) y el mismo validador; la corrida de control de 20 plantas (tarea 5) fija el costo real antes de la corrida completa.

### D12. Licencias y atribución

La semilla guarda dataset, licencia y atribución por dato. Atribución obligatoria: WCVP (CC BY 3.0 según su README), EFSA (CC BY 4.0, Zenodo 996024), Wikipedia (CC BY-SA 4.0), Commons (por archivo: CC0, dominio público, CC BY y CC BY-SA, siempre con atribución), TPPT y la EMA. El resumen de Wikipedia probablemente es obra derivada CC BY-SA 4.0, así que ese campo se registra con esa licencia; el resto del registro es una compilación con licencias mixtas. El cambio 2 muestra la sección «Fuentes».

Términos sin verificar, documentados como tales:

- EMA: reutilización permitida citando a la EMA, según términos no verificados en el portal.
- TPPT (Agroscope): según opendata.swiss el uso es abierto citando la fuente y el uso comercial requiere permiso. El proyecto es académico y se usa con atribución. Si cambia el enfoque, hay que pedir permiso.

Alternativas: excluir TPPT y la EMA hasta verificar (se pierde la seguridad y los objetivos, que son el motivo del cambio) y publicar sin CC BY-SA (no es posible si se resume Wikipedia). Decisión del usuario: Wikipedia se mantiene como fuente de `description`, con la atribución y la licencia CC BY-SA 4.0 registradas por campo.

### D14. Retirar una fuente es un cambio de configuración

Las fuentes se activan y desactivan en la configuración de las herramientas (`tools/catalog-seed/sources.json`, campo `enabled`), sin tocar código. Al desactivar una fuente, sus filas y sus refs salen de los paquetes, cambia el `bundleHash` de las plantas que la usaban y `plan` regenera solo esas plantas. El prompt y el validador no dependen de que exista una fuente concreta: un campo sin datos queda `null` y ninguna regla exige que una fuente esté presente (las reglas que usan la EMA o TPPT, como los objetivos y la seguridad, se aplican a lo que haya en el paquete). La atribución y la sección «Fuentes» del cambio 2 se derivan de los refs y de la lista de fuentes del manifiesto, así que la fuente desaparece sola; el manifiesto deja de listarla. Si se retira Wikipedia, `description` queda `null` o se resume de otras fuentes del paquete, como la EMA, y no hay migración manual: se regeneran las plantas afectadas. Esto vale para cualquier fuente; las que alimentan reglas específicas (la EMA para objetivos, TPPT para toxicidad) pueden retirarse igual, con la consecuencia de que las plantas pierden esos datos.

Alternativa descartada: código condicional por fuente en el prompt o el validador, que haría costoso retirar o añadir una.

## Risks / Trade-offs

- **[Cambio de 629 IDs (el piloto estimaba unos 500)]** Un cliente con un ID guardado dejaría de encontrarlo. → Hoy no se encontró persistencia de IDs; los alias se guardan; `lavandula-angustifolia` se conserva; la tarea 10 recorre todos los IDs fijados en tests, fixtures y workflows. El cambio 2 decide si la API los resuelve.
- **[Límite de peticiones de Wikidata]** El piloto recibió 429 con `Retry-After: 1000`. → POST, lotes, caché, reanudación y paquetes marcados como incompletos (D10). La imagen y el nombre en español son enriquecimiento, no bloquean una planta.
- **[Extracción de PDF de la EMA]** No está probada. → Spike antes de generalizar, con criterio de éxito y plan de salida (D9).
- **[Licencias CC BY-SA]** Wikipedia (y posiblemente imágenes de Commons) obliga a conservar la licencia en lo derivado. → Se registran por campo y por imagen; el usuario decidió mantener Wikipedia; retirarla después es un cambio de configuración (D14).
- **[Términos de la EMA y TPPT sin verificar]** → Se documentan como no verificados y se pide verificar antes de publicar la app; TPPT está limitado a uso académico con atribución.
- **[Costo de la generación]** Unos 23 millones de tokens o US$40-70 en batch. → Corrida de control de 20 plantas para medir, generación incremental, decisión explícita del modo (D11) y tope por lote.
- **[Variabilidad del LLM]** Dos ejecuciones pueden dar textos distintos para la misma planta, y el LLM puede omitir, traducir mal o inventar. → La política de la variante A, el validador (refs, objetivos con respaldo, plantas tóxicas sin objetivos, licencias de imagen, palabras de dosis), `reviewFlags`, versionado del prompt y el modelo, y una regeneración que solo toca lo que cambió. No se promete texto idéntico entre corridas, y por eso la reproducibilidad vive en la semilla versionada, no en el LLM. La traducción de `activity` no la verifica ningún validador; la conserva `activitySource` y la revisión de la corrida de control la muestrea.
- **[Fusiones incorrectas]** Un error en la resolución mezcla plantas distintas (el almendro con el cerezo en el piloto), o el criterio de Wikipedia funde una variedad de uso diferenciado sin artículo. → Regla de colisiones con lista de excepciones, homónimo ambiguo, fallo del armado ante IDs repetidos, `reviewFlag` de fusión heterotípica y revisión de los casos marcados en la corrida de control.
- **[Uso de la API que cambia sin cambiar el contrato]** Usos en español, más plantas, plantas separadas, la lavanda con otro número de usos y partes. → La QA (tarea 10) compara antes y después y actualiza las pruebas ignoradas que fijan conteos.
- **[Actividades sensibles traducidas]** La spec anterior exigía conservar la etiqueta literal. → Se conserva `activitySource` y la traducción debe ser literal; el validador comprueba que la original exista en el paquete.
- **[Duplicación de validación Python/Rust]** → Esquema JSON como fuente única y prueba de contrato (D3).
- **[Tamaño de la semilla]** Unos 16 MB en el repo y en el contexto de Docker. → Aceptable; si crece, se revisa con Git LFS o compresión.
- **[Muestras del piloto no representan el universo]** El piloto usó 20 plantas con más datos que el promedio. → La corrida de control reutiliza esas 20 para comparar y la corrida completa se hace por tandas con un informe de flags.

## Migration Plan

1. Construir la semilla en una rama con las tareas 1 a 6 sin tocar el build. Hasta que la tarea 8 cambie el `Dockerfile`, el despliegue sigue con la ingesta de USDA.
2. Cambiar el build y el `Dockerfile` (tareas 7 y 8) con una semilla completa ya presente (tarea 11) o, para probar antes, con la semilla de la corrida de control, que debe producir un `catalog.db` válido aunque pequeño. No se publica (`push` a `main`, que despliega) con una semilla parcial.
3. QA de la API con la base real (tarea 10), antes del despliegue.
4. Decisión del usuario (2026-10-26): el cambio 1 no se publica solo, no hay `push` a `main`. El cambio 2 se implementa en la misma rama y los dos se despliegan juntos. El motivo es que, con el cambio 1 solo, la app mostraría el primer nombre por orden alfabético en lugar del `displayName`, perdería la búsqueda por nombres anteriores y mostraría las citas de los usos como etiquetas. Lo resuelve el cambio 2.
5. Retroceso: `git revert` de los commits del cambio devuelve el marco de adaptadores y el ZIP de USDA; no hay datos de usuario que migrar. Los alias y la semilla no se consumen fuera de este repo.

## Open Questions

- Si el cambio 2 resolverá los alias en la API (redirección o búsqueda por alias). No afecta a la semilla, que ya los guarda.
- El formato exacto del archivo de TPPT y sus categorías de toxicidad completas; se confirman al descargarlo en la tarea 1.3.
