# Design

## Context

Véase `proposal.md` para la motivación y la spec delta `catalog-api` para los requisitos observables. Hoy la procedencia viaja de punta a punta:

- `catalog-ingest` consolida las fuentes con `Attributed<T>` (valor más las fuentes que lo aportan) y `write.rs` escribe `source`, `plant_name_source`, `plant_part_source`, `plant_use_source` y `reference_source`, además de `family_source_id` y la capa de enlace `plant_source_id`.
- `catalog-core::domain` define `Source`, `SourceId`, `Attributed<T>` y un `Plant` con `family: Option<Attributed<String>>` y `names`, `parts` y `uses` como `Vec<Attributed<_>>`. El trait `CatalogRepository` ofrece `list_plants`, `get_plant` y `list_sources`.
- `catalog-api/src/repository.rs` carga las atribuciones con `group_sources` (una consulta por cada tabla de atribución en cada detalle), `dto.rs` las publica como `sources` y `FamilyDto { value, sources }`, y `http.rs` sirve `/v1/sources` con `SourceDto`.
- `consolidate.rs` también construye `Plant` y `references: Vec<Attributed<Reference>>`, y `write.rs` consume ese resultado.
- La app Flutter no consume la API todavía.

## Goals / Non-Goals

**Goals:**

- Que la API entregue una sola respuesta consolidada, sin pistas de qué dataset aportó cada dato.
- Que el modelo de lectura compartido (`catalog-core`) no prometa atribución que la API no sirve.
- Conservar sin pérdida la procedencia dentro del backend para consolidar, priorizar, depurar y aplicar lógica futura sobre el origen.
- Que la base y su hash no cambien.

**Non-Goals:**

- La lógica o IA de selección de información.
- Resolver la atribución exigida por licencias como CC BY.
- Cambios en el esquema, en la app Flutter o en la spec `catalog-ingest`.

## Decisions

### 1. Modelo de lectura plano en `catalog-core` y modelo con atribución en `catalog-ingest`

`catalog_core::domain::Plant` pasa a ser el modelo plano que sirve la API: `family: Option<String>`, `names: Vec<PlantName>`, `parts: Vec<Part>`, `uses: Vec<Use>`. `Attributed<T>` se mueve a `catalog-ingest`, que es el único que lo necesita, y `consolidate.rs` construye un tipo propio con atribución (por ejemplo `AttributedPlant`) en lugar de `domain::Plant`. `Source` y `SourceId` se quedan en `catalog-core` porque los adaptadores y `write.rs` los usan.

Por qué: el dominio compartido debe describir lo que se lee y se entrega; la atribución es un asunto de la construcción. Así el compilador impide que una atribución se filtre a la API por descuido.

Alternativa descartada: dejar `Attributed` en el dominio compartido y descartar las fuentes solo al convertir a DTO. La API seguiría cargando las tablas de atribución sin usarlas (cuatro consultas por detalle de más) y el dominio seguiría prometiendo algo que la API no expone.

### 2. Repositorio sin fuentes

`CatalogRepository` pierde `list_sources`, y `AsyncCatalog` pierde su versión asíncrona. `catalog-api/src/repository.rs` deja de consultar `plant_name_source`, `plant_part_source` y `plant_use_source` y elimina `group_sources` si queda sin uso: cuatro consultas menos por detalle. `family_source_id` tampoco se lee. Los implementadores del trait en tests (`async_catalog.rs`, `http.rs`, `tests/shutdown.rs`) pierden el método.

Por qué: lo que no se sirve no se consulta; es menos trabajo por petición y menos superficie.

### 3. HTTP y contrato OpenAPI

Se elimina la ruta `/v1/sources` y su handler (responde 404 como cualquier ruta desconocida, con `application/problem+json`), `SourceDto` y `FamilyDto`. `PlantDto.family` pasa a `string | null` y los DTOs de nombre, parte y uso pierden `sources`. Se regenera `backend/openapi.json` con `cargo run -p catalog-api -- --openapi`, y el test de documento al día debe pasar con el archivo nuevo.

Por qué 404 y no 410: no hay consumidores a quienes avisar, y un 404 mantiene la superficie mínima.

### 4. Compatibilidad dentro de `/v1`: excepción explícita, no versión nueva

El requisito vigente «Compatibilidad dentro de `/v1`» exige que los cambios incompatibles salgan en una nueva versión del prefijo. Este cambio elimina campos y un endpoint, así que lo viola tal cual. Se resuelve modificando el requisito, no ignorándolo, con una excepción acotada: mientras la API no tenga ningún consumidor, un cambio incompatible puede hacerse dentro de `/v1` si un cambio de OpenSpec lo registra y justifica; la excepción deja de aplicar cuando un primer cliente integre la API. Este mismo cambio es el registro que la excepción pide.

Por qué: crear `/v2` para una API sin clientes añade rutas, OpenAPI y mantenimiento duplicado sin proteger a nadie, y silenciar la regla la vaciaría de sentido. La excepción conserva la garantía para cuando importe.

Alternativas descartadas: (a) publicar `/v2` y mantener `/v1` con la procedencia, que obliga a sostener dos contratos sin beneficiarios; (b) cambiar `/v1` sin tocar el requisito, que deja la spec incumplida por decisión propia.

### 5. Tests

`source_independence.rs` se mantiene: sigue vigente porque la API no debe conocer nombres de datasets. Se ajustan los tests de `http.rs`, `repository.rs`, `async_catalog.rs`, `openapi.rs`, `test_support.rs`, `fixture_end_to_end.rs` y `shutdown.rs`, y los de `consolidate.rs` y `write.rs` que usen `Attributed` o `Plant`. Se añaden comprobaciones de que el detalle no contiene `sources` en ningún nivel, de que `family` es texto o `null` y de que `/v1/sources` responde 404. El test de ingesta que comprueba las tablas de atribución no cambia: es la garantía de que la procedencia sigue en la base.

### 6. Documentación

`README.md` y `backend/README.md` quitan `/v1/sources` de la lista de endpoints. La sección 2 de `docs/data/modelo-de-datos.md` explica que la procedencia es interna al backend y no se expone por la API, y reescribe la frase sobre `sources` en el detalle y sobre `/v1/sources`. El `## Purpose` de `openspec/specs/catalog-api/spec.md` se edita directamente para quitar «y sus fuentes» (un delta de una capacidad existente no lleva Purpose).

### 7. `catalog-ingest` sin delta

Sus requisitos «Consolidación multi-fuente con atribución», «Resolución de campos de valor único» y «Procedencia de cada dato» hablan de lo que la base contiene y registra, no de lo que la API entrega. Como la base no cambia, no necesitan delta.

### 8. Escenarios de `backend-container` ajustados a endpoints vigentes

La spec `backend-container` referenciaba `GET /v1/sources` en los escenarios «Servir sin red» y «Búsqueda real». Lo detectó la QA: al archivar este cambio esos escenarios serían insatisfacibles porque el endpoint responde 404. El delta los ajusta para usar `/v1/plants/lavandula-angustifolia` (y el listado), sin cambiar el comportamiento de la imagen: sigue sirviendo sin red y con datos reales.

## Risks / Trade-offs

- [Cambio incompatible del contrato de `/v1`] → no hay consumidores (la app Flutter no usa la API) y la excepción queda escrita en la spec; cuando exista el primer cliente, la regla estricta vuelve a aplicar.
- [Atribución futura para licencias como CC BY: si un dataset exige créditos visibles, quitar la lista de fuentes obliga a resolverlo después] → se resolverá con un dato neutro de créditos, no con una lista de datasets, en un cambio propio; mientras tanto la fuente activa (USDA Dr. Duke, dominio público) no exige atribución visible.
- [La base conserva datos que la API ya no sirve (tablas de atribución, `source`)] → es deliberado: sostienen la consolidación, la priorización y la depuración. El coste es espacio y mantenimiento de escritura, y queda cubierto por los tests de ingesta.
- [Mover `Attributed` a `catalog-ingest` toca `consolidate.rs` y `write.rs`, con riesgo de alterar la base] → el hash de contenido del catálogo debe seguir idéntico; se comprueba en la verificación de extremo a extremo.
- [Un cliente futuro podría querer saber el origen para mostrar confianza o depurar] → se podría añadir de forma neutra y aditiva más adelante; la procedencia sigue en la base.

## Migration Plan

No hay migración de datos: la base no cambia. Se despliega con una imagen reconstruida. Reversión: revertir el cambio de código y regenerar `openapi.json`; no queda estado que deshacer.
