# Proposal

## Why

Tras `consolidate-catalog-seed`, `catalog.db` guardará por planta mucho más de lo que la API sirve: nombre para mostrar en español, sinónimos, descripción, origen, tipo de aceite, usos agrupados con países y citas, objetivos de la EMA, nivel de seguridad, imagen con licencia y la licencia de cada fuente. Pero ese cambio no toca el contrato HTTP a propósito, así que la app sigue viendo lo mismo de antes: el pasaporte muestra `Propiedades` vacía por diseño, `General` sin origen ni descripción, `Tipo de aceite` como «No aplicable» y arte local provisional.

Además, la licencia de lo que se publica obliga a mostrar atribución: WCVP (CC BY 3.0), EFSA (CC BY 4.0), Wikipedia (CC BY-SA 4.0), Commons (por archivo), TPPT (Agroscope) y la EMA. Hoy las specs prohíben exponer procedencia en la API y mostrar procedencia o créditos en el pasaporte, y el cambio archivado `remove-api-provenance` anticipó que los créditos futuros irían como un dato neutral de créditos, no como una lista de datasets por campo. Este cambio levanta esa prohibición de forma acotada.

Este es el segundo de tres cambios (semilla, detalle de planta y pasaporte, búsqueda por objetivo) y se implementa después del primero.

## What Changes

- **Detalle de planta ampliado (aditivo dentro de `/v1`)**: `GET /v1/plants/{id}` suma `displayName`, `synonyms`, `description`, `origin`, `oil`, `useGroups` (actividad traducida con número de registros, países y citas, incluidas las citas sin resolver marcadas como tales), `goals` (objetivos de la EMA con área, tipo de documento y citas), `safety` (nivel, que puede ser `null`, texto y citas), `image` (URL, página del archivo, autor, licencia y atribución) y `credits` (dataset, licencia, atribución y enlace, a nivel de planta). Los campos existentes (`names`, `parts`, `uses`) se conservan.
- **Listado**: cada elemento suma `displayName`. No suma miniatura (véase `design.md`, D5).
- **Orden de nombres comunes**: el nombre para mostrar de la semilla va primero entre los nombres comunes. Hoy la API los ordena alfabéticamente, de modo que el «primer nombre común» no sería el que la semilla eligió.
- **Alias de identificadores**: un ID anterior guardado como alias en el cambio 1 se resuelve en `GET /v1/plants/{id}` con 200 y el ID canónico en el cuerpo y en `Content-Location`; no hay redirección.
- **Contenido pendiente de revisión**: la API no sirve un objetivo que un `reviewFlag` deja condicionado a revisión (el caso del hipérico y `relajacion-estres`). Los demás `reviewFlags` no se exponen. Un grupo de uso con al menos una cita resuelta se sirve, con sus citas sin resolver marcadas; solo se omiten los grupos sin ninguna cita resuelta (`plant_use_group.pending_review`).
- **Se levanta la prohibición de procedencia**: la API y el pasaporte pueden mostrar créditos y atribución como un dato neutral a nivel de planta (nombre del dataset, licencia, atribución y enlace), sin indicar qué campo vino de qué fuente. Se mantiene el rechazo de procedencia por campo.
- **Cliente (`catalog-client`)**: parsea los campos nuevos de forma tolerante (ausente equivale a vacío o `null`), usa `displayName` como nombre para mostrar y admite pedir imágenes solo de los hosts de Wikimedia, sin credenciales, además del host de la API.
- **Pasaporte (`plant-passport`)**: imagen de cabecera con atribución visible; `General` con nombre común, sinónimos, familia, origen, parte utilizada, tipo de aceite y descripción (P05); `Propiedades` con los objetivos registrados por la EMA y `Precauciones` con el nivel (si lo hay), el texto y las citas; `Usos` con un aviso fijo al inicio y los grupos de uso tradicional con países y citas, mostrando las citas sin resolver como «(sin resolver)» en estilo atenuado; sección `Fuentes` con dataset, licencia y atribución; estados «sin datos» para cada campo ausente. `Propiedades sin inferencia de eficacia` se reescribe: sigue sin haber lenguaje de eficacia ni inferencia desde la fitoquímica.
- **Explorar**: la fila muestra `displayName` (español) como nombre principal.
- **Documentación** de la API ampliada, del modelo de datos y de las licencias visibles.
- **BREAKING**: ninguno en el contrato. Cambian contenidos y el orden de los nombres comunes, que la spec no fijaba.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `catalog-api`: el listado suma `displayName`; el detalle suma los campos nuevos y créditos neutrales (se retira la prohibición de procedencia y se reescribe «Atribución en las respuestas»); resolución de alias; omisión de objetivos pendientes de revisión.
- `catalog-client`: parseo tolerante de los campos nuevos, nombre para mostrar desde `displayName` y carga de imágenes de hosts de Wikimedia acotada.
- `plant-passport`: imagen con atribución, `General` de P05, `Propiedades` (objetivos y `Precauciones`), `Usos` por grupos, sección `Fuentes`, estados sin datos y accesibilidad. Se retira la prohibición de mostrar procedencia o créditos.
- `explore-screen`: la fila muestra el nombre para mostrar en español.

## Non-goals

- **Cambio 3 (`enable-goal-search`)**: el catálogo de objetivos, `GET /v1/goals`, las plantas por objetivo y las pantallas P06 y P07. Aquí solo se sirven y se muestran los objetivos de cada planta dentro del detalle. La miniatura de las tarjetas de P07 es de ese cambio, que reutiliza el objeto `image` definido aquí.
- La capa de validación humana de los `reviewFlags`: aquí la API aplica una sola regla de omisión y no expone los flags.
- El chat «Boticario» (RAG).
- Miniaturas en Explorar, caché de imágenes en el backend o un proxy de imágenes.
- Persistencia de IDs en la app (favoritos, historial) y redirecciones HTTP para alias.
- Cambios en la semilla, en las herramientas de `tools/catalog-seed/` o en el esquema de `catalog.db`, salvo la verificación de lo que deja el cambio 1 (véase `design.md`, Open Questions).
- Cambios en el despliegue de Cloud Run o en la autorización por token.

## Impact

- **Depende de** que `consolidate-catalog-seed` esté implementado: lee sus tablas nuevas (`plant_profile`, `plant_use_group`, `plant_goal`, `plant_safety`, `plant_image`, `plant_alias`, `plant_review_flag`, `reference.dataset` y `reference.license`, `source`). Sin ellas no hay nada que servir; la tarea 1.1 comprueba los nombres reales.
- **Backend**: `backend/catalog-core` (tipos de dominio y filas), `backend/catalog-api` (`dto.rs`, `repository.rs`, `http.rs`, `test_support.rs`, pruebas, `tests/real_catalog.rs`), `backend/openapi.json` regenerado.
- **App**: `app/lib/features/catalog` (modelos y parser), `app/lib/features/passport/presentation/plant_passport_page.dart` (y los widgets que se extraigan), `app/lib/features/explore`, `app/test/` (pruebas y `fixtures/api/`), `app/pubspec.yaml` (posible dependencia para abrir enlaces, véase D9) y el manifest de Android si hace falta.
- **Documentación**: `docs/data/modelo-de-datos.md`, `docs/data/fuentes-y-licencias.md` (del cambio 1), `backend/README.md`, `README.md` y `app/README.md` en lo que describan la API o el pasaporte.
- **Contrato**: aditivo dentro de `/v1` (véase la spec `catalog-api`, «Compatibilidad dentro de `/v1`»). El documento OpenAPI se regenera.
- **Despliegue**: la API se despliega con la imagen nueva; la app debe tolerar un backend anterior (campos ausentes), porque el despliegue del backend y la app no son simultáneos.
- **Riesgo legal**: los términos de reutilización de la EMA y de TPPT siguen sin verificarse contra el texto legal (cambio 1, D12); este cambio los hace visibles al usuario final, así que conviene verificarlos antes de publicar la app.
