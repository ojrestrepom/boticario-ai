# Modelo de datos del catálogo y cómo añadir un dataset

Esta guía describe cómo el backend (`backend/`) convierte datasets de terceros en la base neutral que sirve la API, y los pasos para incorporar un dataset nuevo. La procedencia y la curación del asset que hoy usa la app están en la [guía del catálogo USDA](usda-catalog.md); el contrato HTTP está en [`backend/openapi.json`](../../backend/openapi.json). Para ejecutar el backend con Docker, ver el [README de la raíz](../../README.md#backend-catálogo-y-api); los comandos nativos para construir el catálogo, ejecutar la API y verificar están en [`backend/README.md`](../../backend/README.md).

## 1. Por qué tres capas

Los datos pasan por tres capas, cada una con un archivo o tabla propia:

1. **Cruda** (`data/build/raw.db`). Cada CSV del insumo se vuelca sin transformar a una tabla `raw_<fuente>_<tabla>` (por ejemplo `raw_usda_fnftax` o `raw_usda_ethnobot`), con todas las columnas como `TEXT` y una columna `_row` con el número de fila del CSV, que es la única que no viene del dataset. La genera `import_raw` en `raw.rs` y conserva el dataset completo, de modo que un cambio en la derivación se resuelve con `rederive` sin descargar de nuevo.
2. **Enlace** (tabla `plant_source_id`). Une el ID público de cada planta con el identificador que cada fuente le da (`plant_id`, `source_id`, `source_plant_id`). Así una misma planta puede venir de varias fuentes sin que el esquema conozca ninguna.
3. **Neutral** (`data/build/catalog.db`). Es la base derivada y consolidada. Su esquema no contiene nombres ni estructuras de ningún dataset.

La API lee solo la capa neutral, abierta en modo de solo lectura. No abre `raw.db`, no conoce las tablas `raw_*` y no contiene nombres de tablas o campos de USDA; un test (`source_independence.rs`) lo comprueba. Las 12 tablas de la capa neutral son:

| Tabla | Contenido |
|---|---|
| `metadata` | Pares clave-valor de la base; guarda `schema_version`. |
| `source` | Fuentes con nombre, versión, licencia, cita, URL y checksum del insumo. |
| `plant` | Plantas; el ID público es el slug del nombre científico, más la familia y la fuente que la aportó. |
| `plant_source_id` | Enlace: el identificador que cada fuente da a cada planta. |
| `plant_name` | Nombres científicos y comunes, con idioma y versión normalizada para buscar. |
| `plant_part` | Partes de la planta. |
| `reference` | Referencias bibliográficas. |
| `plant_use` | Usos (actividad e idioma) respaldados por una referencia. |
| `plant_name_source` | Atribución: qué fuentes aportan cada nombre. |
| `plant_part_source` | Atribución: qué fuentes aportan cada parte. |
| `plant_use_source` | Atribución: qué fuentes aportan cada uso. |
| `reference_source` | Atribución: qué fuentes aportan cada referencia. |

## 2. Procedencia

La tabla `source` registra, por cada fuente activa, su identificador, nombre, versión, licencia, cita, URL y checksum del insumo. Esos valores los declara el adaptador y `validate_source` (en `adapter.rs`) rechaza la fuente si falta alguno. La API los expone en `/v1/sources`.

Las tablas `plant_name_source`, `plant_part_source`, `plant_use_source` y `reference_source` atribuyen cada nombre, parte, uso y referencia a las fuentes que lo aportan. Que un dato tenga varias fuentes significa que todas ellas lo entregaron de forma idéntica: en el detalle de una planta, `sources` lista todas. La familia es un valor único, así que `plant` guarda cuál fuente fue la elegida (`family_source_id`).

## 3. Reglas de consolidación

`consolidate` (en `consolidate.rs`) une los registros de todas las fuentes activas en un catálogo en memoria, que `write_catalog` escribe después. Las reglas son:

- **Identidad.** Dos registros son la misma planta si su nombre científico normalizado con `normalize_name` (en `catalog-core/src/normalize.rs`) es igual: se recortan espacios, se colapsan los internos y se ignoran mayúsculas.
- **ID público.** Es `slug` de esa identidad normalizada, por ejemplo `lavandula-angustifolia`. La misma regla se usa en la ingesta y en la API.
- **Campos de valor único** (la familia). Gana la fuente de mayor prioridad que traiga un valor no vacío, y se registra cuál fue. La prioridad sale de `data/sources.toml`, donde 1 es la más alta.
- **Campos multivalor** (nombres, partes, usos y referencias). Se suman. Si dos fuentes aportan el mismo dato, ambas quedan en su atribución.
- **Orden.** Las fuentes se procesan por prioridad y, a igualdad, por id, y las colecciones se guardan ordenadas, así que el resultado no depende del orden de entrada.

Estos casos son errores de construcción (`IngestError`) y nunca se resuelven en silencio:

| Error | Causa |
|---|---|
| `DuplicateIdentity` | Una misma fuente entrega dos plantas con la misma identidad normalizada. |
| `SlugCollision` | Dos identidades distintas producen el mismo slug. |
| `UnresolvedReference` | Un uso cita una referencia que la misma fuente no entrega. |
| `ConflictingReference` | Dos fuentes entregan el mismo id de referencia con citas distintas. |
| `EmptyScientificName` | El nombre científico no tiene letras ni dígitos ASCII y daría un ID vacío. |

## 4. Construcción determinista

El comando `build` (función `build` en `build.rs`) verifica el insumo en `data/.cache/`, recrea `raw.db`, importa el crudo y llama a `rederive`. `rederive` lee solo `raw.db` y escribe `catalog.db`, sin el insumo original y sin red; la descarga (`download_input` en `download.rs`) es un paso aparte.

- **Escritura atómica.** `write_catalog` (en `write.rs`) valida el catálogo, escribe en `<destino>.tmp` y renombra al terminar. Si algo falla, el destino previo queda intacto y no queda archivo parcial.
- **Hash de contenido.** `content_hash` (en `hash.rs`) calcula un SHA-256 del contenido lógico de las 12 tablas (`NEUTRAL_TABLES`), volcadas en un orden total. No hashea el archivo, que puede cambiar byte a byte sin cambiar su contenido. Dos construcciones con los mismos insumos y la misma configuración dan el mismo hash, y tanto `build` como `rederive` lo imprimen.

## 5. Esquema y versión

El esquema es una migración de Diesel en `data/migrations/` (hoy `2026-10-12-000000_catalog_v1/up.sql`). `catalog-core` la embebe (`MIGRATIONS` en `version.rs`) y `apply_schema` la aplica a una base nueva. No se usa el arnés de migraciones de Diesel: la base no evoluciona, se regenera entera.

`backend/catalog-core/src/schema.rs` lo genera Diesel y no se edita a mano; `backend/diesel.toml` fija su ruta y la carpeta de migraciones. `SCHEMA_VERSION` (en `version.rs`) se guarda en `metadata` y la API la comprueba al arrancar.

Para cambiar el esquema: editar la migración, subir `SCHEMA_VERSION`, regenerar `schema.rs` con `DATABASE_URL=<base temporal> diesel migration run` desde `backend/` (ver [`backend/README.md`](../../backend/README.md#6-cambiar-el-esquema)), ajustar las filas de `catalog-core/src/rows.rs` y la escritura de `write.rs`, y reconstruir con `rederive` (o `build`). Un test comprueba que el esquema no contiene términos de ningún dataset.

## 6. Cómo añadir un dataset

Añadir una fuente no cambia el esquema ni la API. Los pasos son:

1. **Implementar `SourceAdapter`** (en `catalog-ingest/src/adapter.rs`), con cuatro métodos:
   - `source()` entrega los metadatos (`Source`): `id`, `name`, `version`, `license`, `citation`, `url` y `checksum`. El `id` solo admite `[a-z0-9_]` porque forma parte de los nombres `raw_<fuente>_<tabla>`.
   - `input()` entrega el `InputDescriptor` del insumo: `file_name` en la caché, `download_url`, `expected_size` y `expected_md5`.
   - `raw_import(archive)` entrega el `RawImportSpec` (en `raw.rs`): `source_id`, la ruta del ZIP, la codificación de los CSV y qué entradas importar (`RawFiles::AllCsv` o `RawFiles::Only`).
   - `derive(raw)` lee solo las tablas crudas de su fuente y entrega un `SourceRecords` con `PlantRecord` (identificador en la fuente, nombre científico, familia opcional, `NameRecord`, partes y `UseRecord`) y `ReferenceRecord`. Un uso apunta a su referencia por id, que debe existir en la misma fuente.
2. **Declarar licencia y procedencia** reales en `source()`; sin ellas `validate_source` rechaza la fuente.
3. **Decidir si la fuente permite la capa cruda.** Hoy `build` importa siempre el crudo de cada fuente activa en `raw.db`, que es local, no se versiona y no se despliega. Una fuente cuya licencia prohíbe almacenar su contenido (el diseño menciona AromaDb) no puede usar este flujo tal como está; hay que resolverlo antes de implementar su adaptador.
4. **Registrar el adaptador** en `default_registry` (en `catalog-ingest/src/sources.rs`), que es el único lugar de código que se toca para que el ejecutable conozca la fuente.
5. **Añadir la fuente a `data/sources.toml`** con su `id` y una `priority` única (1 es la más alta). La prioridad decide quién gana en los campos de valor único. El archivo rechaza ids o prioridades repetidos y claves desconocidas.
6. **Probar con fixtures.** `catalog-ingest/src/test_support.rs` ofrece `build_zip` (crea un ZIP de CSV en Windows-1252), `fixture_source`, `FixtureCsv` y `FixtureAdapter`, un adaptador completo sobre CSV pequeños, además de `StaticAdapter` para probar el consolidador sin crudo. Los tests de `adapter.rs`, `sources.rs`, `consolidate.rs` y `build.rs` muestran el patrón: importar el fixture con `import_raw`, derivar y comprobar los registros y los errores de la sección 3.
7. **Reconstruir y comparar el hash.** Ejecutar `download` y `build`, anotar el hash, repetir con `rederive` y confirmar que coincide; después ejecutar los tests con `--ignored` descritos en [`backend/README.md`](../../backend/README.md#5-verificación).

### Ejemplo de referencia: el adaptador de USDA

`catalog-ingest/src/usda.rs` implementa `UsdaAdapter` para el ZIP de USDA Dr. Duke (CC0), con codificación Windows-1252 y todos los CSV importados (`RawFiles::AllCsv`), aunque la derivación solo lee seis tablas. Su criterio de curación, que sigue el de la [guía del catálogo USDA](usda-catalog.md):

- Una planta por fila de `FNFTAX`, con `FNFNUM` como identificador en la fuente y `TAXON` como nombre científico.
- Los nombres comunes salen de `COMMON_NAMES` y las partes de `FARMACY_NEW` cruzada con `PARTS` por código.
- Los usos salen de `ETHNOBOT` solo si el taxón cruza de forma exacta por `GENUS`, `SPECIES` y `TAXON`, la actividad no está vacía y la referencia resuelve a una única fila de `REFERENCES` con `LONGREF` no vacío.
- Solo se entregan las referencias que algún uso elegible cita.

Decisiones ya tomadas:

- **Idioma.** `COMMON_NAMES` no declara idioma: un nombre que termina en una etiqueta entre paréntesis (`Rumberry (Eng.)`) se marca `und` y el resto `en`. El texto nunca se modifica. Las actividades son `en`.
- **Usos fundidos.** Las filas de uso repetidas (misma actividad, idioma y referencia) se funden en un solo uso al consolidar.
- **Familia.** Si `FAMILY` está vacía, la familia es `None`.

## 7. Límites conocidos

- **Sinónimos entre datasets.** La identidad es el nombre científico normalizado, sin resolver sinonimia ni taxonomía: dos fuentes que llaman distinto a la misma planta producen dos plantas.
- **El ID depende del nombre.** Como el ID público es el slug del nombre científico, si una fuente cambia el nombre cambia el ID. Hoy no hay una tabla de alias ni de redirecciones, y los clientes no deben guardar IDs como si fueran permanentes.
- **La capa cruda es local.** `data/build/raw.db` se genera en cada máquina, no se versiona y no se despliega con la API; solo `catalog.db` es el artefacto que se sirve.
