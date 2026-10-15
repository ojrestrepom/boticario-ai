# Tasks

## 1. Dominio, repositorio y modelo con atribución

- [x] 1.1 En `catalog-core`, hacer que `domain::Plant` sea plano (`family: Option<String>`, `names: Vec<PlantName>`, `parts: Vec<Part>`, `uses: Vec<Use>`), quitar `Attributed` del dominio y `list_sources` de `CatalogRepository`, conservando `Source` y `SourceId`; verificar con `cargo fmt --all --check` y que `cargo build -p catalog-core` compila.
- [x] 1.2 En `catalog-ingest`, definir `Attributed<T>` y un tipo propio con atribución (por ejemplo `AttributedPlant`) y hacer que `consolidate.rs` y `write.rs` los usen en lugar de `domain::Plant`, sin cambiar lo que se escribe; verificar con `cargo test -p catalog-ingest` (incluido el test que comprueba las tablas de atribución, sin modificar) y con `cargo clippy --all-targets -p catalog-ingest -- -D warnings`.

## 2. API

- [x] 2.1 En `catalog-api/src/repository.rs`, construir el `Plant` plano sin consultar `plant_name_source`, `plant_part_source` ni `plant_use_source`, eliminar `group_sources` si queda sin uso y `list_sources` (también en `async_catalog.rs` y en los implementadores del trait de `http.rs` y `tests/shutdown.rs`), y ajustar sus tests; verificar con `cargo test -p catalog-api` sobre los tests de repositorio y de catálogo asíncrono.
- [x] 2.2 En `dto.rs`, `http.rs` y `openapi.rs`, eliminar `SourceDto`, `FamilyDto`, la ruta y el handler de `/v1/sources` y los campos `sources`, y hacer `PlantDto.family` un `string | null`; añadir tests de que el detalle no contiene `sources` en ningún nivel, de que `family` es texto o `null` y de que `/v1/sources` responde 404 con `application/problem+json`; verificar con `cargo test -p catalog-api`.
- [x] 2.3 Ajustar `test_support.rs`, `tests/fixture_end_to_end.rs` y `tests/shutdown.rs`, conservando `tests/source_independence.rs`; verificar con `cargo test --workspace`, `cargo fmt --all --check` y `cargo clippy --all-targets --workspace -- -D warnings`.
- [x] 2.4 Regenerar `backend/openapi.json` con `cargo run -p catalog-api -- --openapi`; verificar que el diff elimina `SourceDto`, `FamilyDto`, `/v1/sources` y los `sources`, y que el test de documento al día pasa.

## 3. Documentación y Purpose

- [x] 3.1 Quitar `/v1/sources` de la lista de endpoints de `README.md` y de `backend/README.md`; verificar con `grep -rn "v1/sources" README.md backend/README.md` sin resultados.
- [x] 3.2 En la sección 2 de `docs/data/modelo-de-datos.md`, explicar que la procedencia es interna al backend y no se expone por la API, y reescribir la frase sobre `/v1/sources` y la de `sources` en el detalle; verificar con `grep -rn "v1/sources\|\`sources\`" docs README.md backend/README.md` sin menciones a la API y que se respeta la regla de una línea por párrafo.
- [x] 3.3 Editar directamente `openspec/specs/catalog-api/spec.md` para quitar «y sus fuentes» del `## Purpose`; verificar con `grep -n "sus fuentes" openspec/specs/catalog-api/spec.md` sin resultados y con `openspec validate remove-api-provenance --strict`.

## 4. Verificación de extremo a extremo y QA

- [x] 4.1 Ejecutar `docker compose up --build` y verificar con `curl` que `/v1/plants/lavandula-angustifolia` responde sin `sources` y con `family` como texto, que `/v1/plants?q=lavand` sigue devolviendo datos, y que `/v1/sources` responde 404 con `application/problem+json`; verificar que el hash del catálogo impreso en la construcción es `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, igual que antes, porque la base no cambia.
- [x] 4.2 Ejecutar `cargo fmt --all --check`, `cargo clippy --all-targets --workspace -- -D warnings` y `cargo test --workspace` desde `backend/`, `docker compose build`, y `openspec validate remove-api-provenance --strict`; verificar que todo queda en verde.
- [x] 4.3 Pasar QA sobre el cambio completo (contrato del detalle, 404 de `/v1/sources`, documentación y OpenAPI) y registrar el informe en `qa/` dentro del cambio, corrigiendo los defectos hallados.
- [x] 4.4 Añadir el delta de `backend-container` que sustituye `/v1/sources` en sus escenarios de verificación por endpoints vigentes, y actualizar proposal y design; verificar con `openspec validate remove-api-provenance --strict`
