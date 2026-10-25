# Proposal

## Why

«Buscar por objetivo» (P06) es hoy una pantalla solo visual: seis filas que no hacen nada, sin API ni resultados, y la spec `goal-search-screen` lo exige así («Filas de objetivos sin acción ni selección», «Sin resultados ni comportamiento de producto»). Es una de las cinco funciones de Inicio y la única que el usuario toca y no responde. Tampoco existe P07 («Recomendaciones»), a la que lleva P06 en el mapa de navegación.

Con la semilla consolidada del cambio `consolidate-catalog-seed` ya hay datos para hacerlo bien: cada planta puede llevar objetivos derivados solo de las áreas terapéuticas de la EMA (monografía o entrada de lista), con cita y sin lenguaje de eficacia, y las plantas tóxicas según TPPT no reciben objetivos. Falta exponerlos por la API y construir las dos pantallas. El cambio `serve-consolidated-plants` expone el detalle de planta y el pasaporte; este cambio solo añade la búsqueda por objetivo y navega a ese pasaporte.

Este es el tercero de tres cambios (semilla, API y pasaporte, búsqueda por objetivo) y se implementa después de los otros dos.

## What Changes

- **API (aditivo dentro de `/v1`)**: `GET /v1/goals` devuelve el catálogo de objetivos con nombre, orden, subáreas y conteos, y `GET /v1/goals/{goalId}/plants` devuelve las plantas de un objetivo (o de una subárea con `?subarea=`), paginadas con `limit` y `offset`, con el mismo token Bearer y los mismos errores `problem+json` que el resto. Cada planta del resultado lleva lo necesario para su tarjeta: `displayName`, el objeto `image` del cambio 2, las áreas de la EMA que la respaldan, su nivel de precauciones (que puede faltar) y si tiene datos de precauciones.
- **Nombres desde la API**: los nombres, el orden y las subáreas de los objetivos salen de la semilla (el mapa de objetivos versionado), no están fijos en la app. La app solo asocia un icono local a cada identificador de objetivo.
- **P06 funcional**: las filas pasan a ser controles con acción. Las filas son «Relajación / Estrés», «Mejorar el sueño», «Cuidado de la piel», «Alivio respiratorio», «Cansancio y fatiga» (sustituye a «Concentración») y «Otros objetivos». Los nombres son provisionales y se revisan con el usuario en la app. **BREAKING (spec de presentación)**: se retiran los requisitos «Filas de objetivos sin acción ni selección» y «Sin resultados ni comportamiento de producto».
- **«Otros objetivos»**: una pantalla nueva con las subáreas que devuelve la API (Digestión; Vías urinarias y genitales; Dolor e inflamación; Boca y garganta; Circulación; Molestias oculares), cada una con su lista de resultados.
- **P07 «Recomendaciones»** (capacidad nueva `goal-results-screen`): subtítulo «Para: <objetivo>», tarjetas con miniatura, nombre y un texto que sale del registro («La EMA la registra en: …»), marca «Precaución» solo con nivel `alto` o `medio` (sin marca de nivel cuando las precauciones no traen nivel, y con «esto no significa que sea segura» cuando no hay ningún dato de precauciones), miniatura con autor y licencia, el aviso del mockup, estados de carga, error con reintento y vacío, y el botón «Ver más detalles» que abre una hoja con la base de la información y las precauciones.
- **Navegación**: Inicio -> P06 -> (Otros objetivos ->) P07 -> pasaporte del cambio 2, con retorno paso a paso y la pestaña Inicio que limpia la pila.
- **Cliente**: `catalog-client` añade los dos endpoints y su parseo estricto; deja de limitarse a los dos endpoints de plantas.
- **Contenido marcado para revisión**: mientras no exista la capa de validación humana, P07 oculta las plantas cuyo objetivo está marcado `pending_review` en la semilla (por ejemplo, las de interacciones graves en «Relajación / Estrés», como el hipérico). Siguen en Explorar y en su pasaporte.
- **Documentación y QA**: contrato de los endpoints en `backend/README.md` y `docs/`, y la QA de API (Postman) y de la app.

## Capabilities

### New Capabilities

- `goal-results-screen`: P07, los resultados de un objetivo o subárea: tarjetas, texto derivado del registro, orden, paginación, marca de precaución, estados vacío, de carga y de error, «Ver más detalles» y navegación al pasaporte.

### Modified Capabilities

- `goal-search-screen`: P06 pasa de visual a funcional (filas con acción, nombres actuales, catálogo desde la API, navegación a resultados y la pantalla de «Otros objetivos»); se retiran «sin acción» y «sin resultados».
- `catalog-api`: se añaden los endpoints de objetivos y de plantas por objetivo, y la regla de plantas ocultas por revisión.
- `catalog-client`: la app consume también esos dos endpoints; se modifica el requisito que la limitaba a los dos de plantas y se añaden el parseo y los errores de objetivos.

## Non-goals

- **Cambio 2 (`serve-consolidated-plants`)**: el detalle de planta, el pasaporte, la sección «Fuentes», los créditos y las imágenes con atribución completa. Este cambio solo navega al pasaporte y muestra una miniatura.
- **Capa de validación humana**: un panel para revisar los `reviewFlags`. Aquí solo se oculta lo marcado `pending_review`; no se resuelve ninguna revisión.
- **Chat «Boticario» (RAG)** y «Formular mezcla» (P08): P07 no navega a P08 y no genera mezclas.
- Búsqueda de texto dentro de P06 o P07, filtros, favoritos, historial y persistencia de datos de usuario.
- Dosis, indicaciones de tratamiento, promesas de eficacia y cualquier texto de las tarjetas del mockup («Efecto calmante…», «Ayuda a reducir la ansiedad»): son ejemplos y no se certifican.
- Ordenar por relevancia o eficacia: el orden es alfabético y no es un ranking.
- Cambios en la semilla o en el esquema de `catalog.db`: este cambio solo lee las tablas del cambio 1.

## Dependencias

- **`consolidate-catalog-seed` (cambio 1)**: aporta `goal`, `goal_subarea`, `plant_goal` (con `subarea_id` y `pending_review`), `plant_goal_ref`, los niveles de seguridad (que pueden ser nulos cuando solo hay advertencias sin nivel) y los `reviewFlags` estructurados en `catalog.db`.
- **`serve-consolidated-plants` (cambio 2)**: aporta el pasaporte consolidado al que navegan las tarjetas de P07, `displayName`, el objeto `image` con atribución y la carga directa de imágenes desde Wikimedia.
- Este cambio se implementa después de los dos. Las specs delta se escriben contra las specs actuales y no contra las de los otros cambios; al archivar hay que archivar primero el 1 y el 2 y revisar que no haya conflictos en `catalog-api` y `catalog-client`, que también tocan.

## Impact

- **Backend**: `backend/catalog-core` (consulta de objetivos y de plantas por objetivo en `CatalogRepository`, tipos de dominio, sobre las tablas del cambio 1, sin migraciones propias), `backend/catalog-api` (rutas, DTOs, OpenAPI, tests) y `backend/openapi.json` regenerado.
- **App**: `app/lib/features/goal_search/` (P06, «Otros objetivos», P07, controlador y modelos), `app/lib/features/catalog/` (modelos, parseo y repositorio), `app/lib/app/router.dart` (rutas nuevas) y sus tests y fixtures.
- **Specs**: deltas de `goal-search-screen`, `catalog-api` y `catalog-client`, y la capacidad nueva `goal-results-screen`. Al archivar hay que actualizar a mano el `Purpose` de `goal-search-screen`, que hoy dice que P06 es solo visual.
- **Documentación**: `backend/README.md`, `docs/data/modelo-de-datos.md` (la regla de plantas ocultas por `pending_review`) y `docs/mockups/pantallas.md` solo si el usuario decide registrar las decisiones de P06 y P07 allí (no se toca sin pedirlo).
- **Despliegue**: sin cambios de infraestructura; es un contrato aditivo dentro de `/v1` y la imagen sigue construyendo `catalog.db` desde la semilla.
