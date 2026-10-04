# Design

## Context

Prerrequisito aprobado antes de implementar el catálogo: el SDK disponible es Flutter 3.47.6 stable con Dart 3.13.5. Se alinean el pin y las instrucciones vigentes con esas versiones y se comprueba la compatibilidad baseline; esto no incorpora nuevas funcionalidades.

Ver `proposal.md` para motivación y las cinco specs delta para comportamiento requerido. La app Flutter (`app/`) hoy tiene una ruta `/`, Home sin estado y dependencias ya disponibles `flutter_riverpod` y `go_router`; no tiene assets de catálogo. Las pruebas de app e integración esperan que ninguna acción cambie de ruta y deberán ajustarse de manera acotada. Los controles/logs de Home, accesibilidad y su contrato visual existente permanecen relevantes.

El contenido se deriva de un snapshot archivado USDA Dr Duke, no de la versión actual del sitio. La procedencia identificable es Figshare artículo 24660351, archivo v1 `Duke-Source-CSV.zip` (file 43363335, https://ndownloader.figshare.com/files/43363335), 6,033,990 bytes, MD5 `45ae44a0544586b8ac22a232beaac344`, inspeccionado el 2026-10-01; CC0 según https://phytochem.nal.usda.gov/about. La referencia/cita recomendada por USDA menciona 1992–2016; eso no establece el rango temporal cubierto por el contenido del ZIP. No presentar ese periodo como fecha de snapshot ni como cobertura observada. Tablas pertinentes: `FNFTAX` (identidad taxonómica enlazada por FNFNUM), `COMMON_NAMES` (nombres comunes fuente), `FARMACY_NEW` (registros fitoquímicos/partes, no identidad taxonómica), `PARTS` (`PPCO`), `ETHNOBOT` (`GENUS`, `SPECIES`, `ACTIVITY`, `REFERENCE`) y `REFERENCES`. `ETHNOBOT` no contiene FNFNUM: la unión requiere validar identidad taxonómica exacta, no solo coincidencia textual parcial.

## Goals / Non-Goals

**Goals:** una capa pequeña de datos inmutables, trazables y cargados offline; límites explícitos entre lo observado en fuente y lo no disponible; navegación y UI separadas del parsing y la búsqueda para que sean comprobables sin red.

**Non-Goals:** conservar/importar el ZIP completo, añadir servicios o dependencias, inferir taxonomía actual, convertir fitoquímica en eficacia, o generalizar el catálogo a una plataforma de ingestión.

Decisión aprobada para pruebas P05: versionar Roboto Regular y Medium con su licencia en `app/test/fixtures/fonts/`, cargarlo solo desde el harness de tests para métricas tipográficas reproducibles (local/CI); no registrar fuentes en runtime/pubspec ni añadir fuentes a la app.

## Decisions

### Bundle local y límites de datos

Empaquetar un JSON pequeño versionado como Flutter asset, registrado en `app/pubspec.yaml`, con un manifiesto de procedencia y cinco registros. Propuesta de código feature-first:

```text
app/assets/data/plant_catalog.json
app/lib/features/catalog/data/plant_catalog_asset_data_source.dart
app/lib/features/catalog/data/plant_catalog_repository.dart
app/lib/features/catalog/domain/plant.dart
app/lib/features/catalog/domain/plant_catalog_provenance.dart
app/lib/features/catalog/domain/plant_search.dart
app/lib/features/explore/presentation/explore_page.dart
app/lib/features/passport/presentation/plant_passport_page.dart
```

Los paths concretos son una organización mínima propuesta, no un requisito de API pública. El modelo de dominio será inmutable; el repositorio expone carga async, colección ordenada y búsqueda/lookup por ID estable. Un data source recibe `rootBundle` o un loader equivalente inyectable. Riverpod provee repositorio/estado async y permite sustituir fuente o repositorio en pruebas sin rutas de depuración ni toggles dentro de la app. El JSON se decodifica con `dart:convert`, valida versión/campos y falla explícitamente ante datos inválidos. Evitar reflejar mapas crudos en widgets.

Se elige asset JSON frente a constantes mezcladas con UI porque separa contenido del render y mantiene edición/auditoría de procedencia legibles; frente a SQLite/cache o importación del ZIP, porque cinco registros estáticos no justifican almacenamiento, migración ni coste de empaquetar/parsear todo el archivo. No se añade paquete.

Modelo conceptual mínimo: `usdaPlantId` (corresponde al FNFNUM original), `displayNameEditorial`, `sourceScientificName`, tipo `plant`, partes respaldadas, campos opcionales de origen/descripción con ausencia explícita, estado de evaluación de propiedades, `traditionalUses` (etiqueta fuente y referencias), y manifiesto de fuente/licencia/versión/archivo/checksum. Las referencias son registros bibliográficos citables, no una cita genérica al USDA. No inventar valores faltantes ni aliases taxonómicos.

Semillas del catálogo, en orden, con nombre científico exacto archivado:

| FNFNUM | Nombre editorial | Nombre científico fuente |
|---:|---|---|
| 544 | Lavanda | `Lavandula angustifolia` |
| 401 | Eucalipto | `Eucalyptus globulus` |
| 873 | Romero | `Rosmarinus officinalis` |
| 605 | Manzanilla | `Matricaria recutita` |
| 619 | Menta | `Mentha x piperita subsp. nothosubsp. piperita` |

Las cinco tienen registros fitoquímicos en `FARMACY_NEW`; eso no es evaluación medicinal de la planta. Hay registros `ETHNOBOT` asociados a Lavandula (13) y Eucalyptus (57) en la inspección, pero la elegibilidad final depende de unión exacta y bibliografía resoluble; las otras pueden legítimamente quedar sin usos elegibles. Excluir registros ambiguos o con referencia faltante/no resoluble. No afirmar que los usos sean actuales. No rellenar origen/descripción ni propiedades. `PPCO` se muestra solo si está expresamente asociado mediante los registros pertinentes de `PARTS`; en pasaporte, tipo de aceite es no aplicable. Un componente/actividad no prueba eficacia.

La categoría Aceites sigue vacía aunque haya registros de aceites esenciales en tres plantas: no son identidad de aceite independiente. La búsqueda pura normaliza recorte, espacios consecutivos, mayúsculas y diacríticos; busca subcadena sobre ambos nombres y combina con filtro conservando orden. `Todas` y `Plantas` abarcan las cinco, `Aceites` ninguna.

### Navegación y estado de sesión

Ampliar `app/lib/app/router.dart` con rutas anidadas `/` → `/explore` → `/explore/:plantId` (ID estable FNFNUM). La navegación Home→Explorar y Explorar→Pasaporte debe ser push sobre el Navigator, manteniendo P04 debajo de P05; Android Back y chevron hacen pop, formando la pila `[Home, Explorar, Pasaporte]` y restaurando filtro, consulta y scroll de P04. Desde Explorar, pop vuelve a Home. Al resolver la ruta de ficha, también para un ID desconocido, la jerarquía crea o retiene esa pila: si no existía estado previo de P04, su padre nace con consulta vacía, filtro `Todas` y scroll inicial. Resolver el ID dentro de P05: el válido muestra su ficha y el desconocido muestra allí estado legible; en ambos casos, chevron y Android Back vuelven al padre Explorar seguro. No se implementan redirects, deep links de sistema, enlaces externos ni guards de autenticación. El botón Inicio en ambas pantallas del catálogo limpia/reemplaza la pila y lleva a `/`, no apila otra Home. Se prefiere esta anidación a rutas flat (`/plants/:id`), que requieren lógica adicional para reconstruir el padre y el retorno, mientras aquí la jerarquía expresa y preserva el flujo requerido.

En catálogo, mostrar barra inferior con Inicio activo que vuelve a Home; otros tres ítems son controles deshabilitados y accesibles. No extraer una barra compartida que altere el contrato inmóvil de Home. Mantener en Home exactamente sus 11 acciones y mensajes: las diez ajenas a Explorar no navegan/mutan UI; Explorar navega también fuera de debug y conserva su único log condicionado por `kDebugMode`.

### Pantallas y estados

Las vistas consumen estado async del proveedor del catálogo y tienen estados diferenciados de carga, error con reintento local y datos. No añadir spinner artificial si la carga del asset termina antes del frame visible. Vacío de búsqueda, vacío específico de Aceites y error son estados distintos. No registrar consultas ni datos del usuario.

P04 usa arte decorativo local provisional y filas comunes/científicas. P05 ofrece tabs General, Propiedades y Usos operativas. Campos ausentes muestran el literal de spec; propiedades declaran sin evaluación en este catálogo. Usos llevan etiqueta explícita de registro tradicional, fuente bibliográfica resoluble y aclaración de que no son recomendación; si ninguno es elegible, vacío explícito. Corazón y CTA de formulaciones siguen visibles, accesiblemente deshabilitados y sin acción/banner. Material provisional existente, sin imágenes remotas, fuentes nuevas ni cambios de tema salvo que una necesidad concreta lo exija.

### Verificación y compatibilidad

Actualizar de forma acotada los tests que fijan ruta única, especialmente `app/test/app/app_test.dart`, `app/test/features/home/home_page_test.dart` y `app/integration_test/app_test.dart`; preservar cobertura de las once acciones, logs y accesibilidad de Home. Añadir pruebas unitarias del parser/validación, búsqueda/acento/espacios, orden/IDs y curación; tests de widget para carga/error/reintento, búsqueda/filtros/vacíos, tabs, no disponibilidad y accesibilidad; router para navegación/retornos/ID inválido y logs; smoke Android real para el flujo completo.

Comandos según README y `.flutter-version`: en `app/`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze`, `flutter test test/`; con emulador Android, `flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO`. CI actual corre unit/widget, no emulador; el smoke debe reportarse no ejecutado si no hay dispositivo. No sustituirlo por Playwright/web. Registrar QA manual futuro en `openspec/changes/build-local-plant-catalog/qa/` con fecha, serial, comandos y resultados, sin credenciales. Las cifras del README se actualizan solo con resultados efectivamente obtenidos.

### Procedencia reproducible

La implementación entregará obligatoriamente, junto al bundle, una guía breve `docs/data/usda-catalog.md` de reproducción/curación. Debe incluir URL e identificadores Figshare v1/file 43363335, fecha de inspección 2026-10-01, tamaño y checksum, CC0 y distinción entre metadata del archivo, fecha de inspección y cita recomendada USDA 1992–2016. Describir selectores trazables por tabla: identidad/nombre científico desde `FNFTAX` por FNFNUM; nombres editoriales separados de `COMMON_NAMES`; partes por `PARTS` y su `PPCO` enlazado a identidad exacta; usos por el par taxonómico exacto `ETHNOBOT.GENUS`/`SPECIES`, preservando `ACTIVITY` y `REFERENCE`, enlazando cada referencia a su registro de `REFERENCES` y documentando la bibliografía resuelta. Fitoquímica de `FARMACY_NEW` no se convierte en propiedad médica ni identidad. Registrar para cada registro incluido sus selectores/refs fuente; excluir de forma explícita las filas sin unión taxonómica exacta, ambiguas, o con `REFERENCE` ausente/no resoluble. La guía debe documentar también campos no encontrados como ausentes, sin inventar origen o descripción. Descargar y verificar tamaño/MD5 antes de extraer; la sesión verificó el digest sobre ZIP en memoria, no persistido. No guardar el ZIP en el repo, exigir instalaciones ni añadir motor de ingestión/dependencias; automatizar la curación con script local es opcional.

## Risks / Trade-offs

- [La cita USDA recomienda una referencia que menciona 1992–2016, pero no se verificó que sea la cobertura temporal del ZIP] → informar cita, metadata de versión del archivo disponible y fecha de inspección por separado; no llamar al rango de la cita fecha/cobertura del snapshot ni equipararlo al portal actual.
- [ETHNOBOT carece de FNFNUM y sus referencias pueden no resolver] → aceptar solo match taxonómico exacto y referencia bibliográfica resoluble; excluir el resto y mostrar ausencia explícita.
- [Nombres científicos archivados pueden diferir de taxonomía vigente] → preservar literal fuente y no inferir sinonimia.
- [Contenido de salud puede interpretarse como consejo] → etiquetar uso tradicional, citar cada registro y evitar dosis, recomendación o eficacia; revisión experta antes de publicación de contenido de salud.
- [Asset manual puede quedar desactualizado o inválido] → manifiesto/versionado, validación y pruebas de carga; corregir datos y código juntos.
- [Bundle, navegación o tests pueden ensanchar el cambio] → limitarlo a cinco registros, tres rutas y el flujo especificado; sin DB, cache, backend ni dependencias.

## Migration Plan

No hay migración de datos de usuario ni despliegue backend. Añadir de forma atómica el asset, parser/repositorio, registro del asset, pantallas y rutas; validar mediante pruebas. Rollback consiste en revertir juntos esos cambios, restaurando el router `/` y Home previos. No se persiste estado de catálogo ni usuario.

## Open Questions

No hay decisiones pendientes que alteren las specs o el enfoque. La fecha de captura de QA Android y cualquier registro ETHNOBOT que resulte elegible se determinan durante la implementación/verificación; la falta de registros elegibles es un resultado válido, no bloqueante.
