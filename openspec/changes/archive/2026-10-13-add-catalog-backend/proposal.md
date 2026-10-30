# Proposal

## Why

El catálogo de la app es hoy un asset local con cinco plantas curadas a mano. Para crecer hacia todo el dataset USDA Dr. Duke, y poder cambiar o combinar datasets más adelante, hace falta un backend propio que sirva el catálogo. Este primer incremento entrega una API de solo lectura, local, alimentada solo con USDA, separando la API de cualquier dataset concreto mediante una capa de abstracción para que la fuente de datos sea intercambiable y sin perder información de los datasets originales.

## What Changes

- Añadir una ingesta de datos en tres capas: una capa cruda que conserva cada dataset tal como viene, una capa de enlace que relaciona los identificadores propios con los de cada fuente y una capa neutral, derivada de las anteriores al construir, que es lo único que lee la API.
- Añadir un contrato de adaptador de fuente con dos responsabilidades: declarar cómo se importa el dataset crudo y derivar registros normalizados a partir de las tablas crudas. Un consolidador une los registros de una o varias fuentes y construye la base neutral, versionada y con la procedencia de cada dato; esa base puede reconstruirse desde la capa cruda sin descargar de nuevo.
- Añadir el adaptador de USDA Dr. Duke como única fuente activa, con la procedencia y los criterios de curación de `docs/data/usda-catalog.md`, aplicado a todas las plantas del dataset y no solo a las cinco actuales.
- Añadir una API HTTP de solo lectura, versionada con el prefijo `/v1`, que lista y busca plantas, devuelve el detalle de una planta con sus partes, usos y referencias, y expone las fuentes, la salud del servicio y su documento OpenAPI.
- Garantizar que la API depende solo del esquema neutral: cambiar o combinar datasets implica escribir un adaptador, editar la configuración de fuentes y reconstruir la base, sin modificar el esquema ni la API.
- Estructura del monorepo: `backend/` pasa a ser un workspace de Cargo con tres crates (núcleo compartido, ingesta y API), todo en Rust; `data/` queda como carpeta de artefactos de datos (esquema, configuración de fuentes, caché y salidas generadas), sin código; `mise.toml` fija solo Rust.
- Documentar el almacén SQLite como decisión, con los criterios para revisarla, y añadir las reglas de `.gitignore`, el README y una guía en `docs/data/`.
- Sin cambios en la app Flutter ni en sus specs: seguirá usando su catálogo local hasta un incremento posterior que la conecte con la API.

## Capabilities

### New Capabilities
- `catalog-ingest`: contrato de adaptador de fuente, conservación del dataset crudo, modelo neutral, consolidación multi-fuente con atribución, procedencia y construcción determinista de la base.
- `catalog-api`: API HTTP de solo lectura v1 para consultar plantas y fuentes, con errores estandarizados, documento OpenAPI y arranque configurable.

### Modified Capabilities
Ninguna. Las restricciones de las specs vigentes («sin solicitudes a servicios remotos», «sin backend», «disponible sin conectividad») describen el comportamiento de la app, que este cambio no altera.

## Impact

- Repositorio: `backend/` (workspace de Cargo con `catalog-core`, `catalog-ingest` y `catalog-api`), `data/` (esquema, configuración de fuentes y salidas generadas), `mise.toml` en la raíz, ajustes a `.gitignore` y `README.md`, y una guía nueva en `docs/data/`. `app/` no cambia.
- Dependencias y herramientas: toolchain gestionado con mise, solo Rust en versión exacta; los crates se eligen al crear el proyecto. No hay Python ni otro lenguaje en el flujo.
- Datos: la ingesta descarga el ZIP público de USDA (CC0) en un paso explícito y fuera de los tests; la base cruda (`data/build/raw.db`) se conserva localmente y la base neutral que consume la API se genera, ambas sin versionar. La base cruda no se despliega con la API.
- Especificaciones: nuevas capacidades `catalog-ingest` y `catalog-api`; ninguna spec vigente se modifica.
- Fuera de alcance: despliegue y contenedor, CI de los componentes nuevos, otros datasets reales, traducciones, recomendaciones, composición química, autenticación, límites de uso y caché.
