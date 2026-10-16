# Spec Delta

## REMOVED Requirements

### Requirement: Catálogo fijo con identidad de fuente
**Reason**: La app ya no embebe un catálogo de cinco plantas con identificadores FNFNUM; el catálogo completo (2.376 plantas con identificadores tipo slug) vive en el backend.
**Migration**: La identidad, los nombres y el orden de las plantas los definen `catalog-ingest` y `catalog-api`. La app los consume mediante `catalog-client`, que trata un identificador inexistente como «planta no encontrada».

### Requirement: Procedencia verificable y límites del snapshot
**Reason**: La procedencia es interna al backend (`remove-api-provenance`) y la app no la muestra ni la conoce; el origen USDA Dr Duke (CC0) queda documentado en `README.md` y `docs/`.
**Migration**: La procedencia por dato la cubre `catalog-ingest`. La atribución del snapshot queda en `README.md` y `docs/data/usda-catalog.md`. Que una planta no equivale a un aceite lo conserva `plant-passport` (campo de aceite no aplicable).

### Requirement: Solo datos sustentados y ausencias explícitas
**Reason**: La app ya no cura ni valida datos: muestra lo que entrega la API. Lo ausente llega como `null` o lista vacía (`catalog-api`).
**Migration**: Los límites de contenido de la app (sin dosis, recomendaciones ni afirmaciones de eficacia, y ausencias explícitas) siguen en `plant-passport` («General con vacíos explícitos», «Propiedades sin inferencia de eficacia» y «Usos como registros tradicionales trazables»).

### Requirement: Disponibilidad local y errores de datos
**Reason**: El catálogo deja de ser local: requiere el backend y no funciona sin conectividad.
**Migration**: La disponibilidad y los errores pasan a `catalog-client` («Errores de red y del servidor» y «Parseo estricto de las respuestas») y a los estados de error reintentable de `explore-screen` y `plant-passport`.
