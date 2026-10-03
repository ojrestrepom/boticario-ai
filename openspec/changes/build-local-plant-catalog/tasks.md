# Tasks

## 0. Prerrequisito de toolchain

- [x] 0.1 Alinear el pin y las instrucciones vigentes con Flutter 3.47.6 stable/Dart 3.13.5; verificar versiones efectivas y compatibilidad baseline con `flutter pub get --enforce-lockfile`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test test/` desde `app/`, sin modificar el lockfile ni ampliar dependencias.

## 1. Catálogo, procedencia y búsqueda pura

- [x] 1.1 Definir modelos inmutables de planta, procedencia y referencias en `app/lib/features/catalog/domain/`; verificar con pruebas unitarias `app/test/features/catalog/domain/plant_test.dart` los cinco IDs/nombres exactos y orden, campos ausentes, IDs desconocidos y límites de identidad planta/aceite.
- [x] 1.2 Crear `app/assets/data/plant_catalog.json` con manifiesto y cinco registros curados, nombres editoriales separados de nombres científicos fuente, partes/usos únicamente respaldados y vacíos explícitos; verificar mediante fuente, manifiesto y guía que partes/usos y referencias tienen trazabilidad, que se excluyen referencias no resueltas y que no se guarda ni descarga el ZIP en CI/tests.
- [x] 1.3 Implementar la guía obligatoria `docs/data/usda-catalog.md` con URLs, identificadores, tamaño, MD5, licencia, fecha de inspección diferenciada de la cita, selectores por tabla, referencias resueltas y exclusiones; verificar que cada fila del asset tenga trazabilidad reproducible y que no afirme cobertura temporal no comprobada.
- [x] 1.4 Implementar parser/versionado/validación y loader inyectable en `app/lib/features/catalog/data/plant_catalog_asset_data_source.dart`, registrar el JSON en `app/pubspec.yaml` y verificar `app/test/features/catalog/data/plant_catalog_asset_data_source_test.dart` para carga válida, JSON malformado, versión no soportada, IDs duplicados, referencias huérfanas o usos sin identidad/referencia válida y fallo legible.
- [x] 1.5 Implementar repositorio y provider Riverpod en `app/lib/features/catalog/data/plant_catalog_repository.dart`; verificar pruebas unitarias de carga ordenada, lookup inexistente, propagación de error/reintento con fuente sustituible y ausencia de red/dependencias adicionales.
- [x] 1.6 Implementar búsqueda/filtro pura en `app/lib/features/catalog/domain/plant_search.dart`; verificar `app/test/features/catalog/domain/plant_search_test.dart` para diacríticos, mayúsculas, espacios repetidos/exteriores, ambos nombres, subcadena, combinación de filtros, orden estable y Aceites vacío.

## 2. Pantalla Explorar (P04)

- [x] 2.1 Implementar `app/lib/features/explore/presentation/explore_page.dart` con diseño provisional local, búsqueda, filtros, filas, estados de carga/error/reintento/vacíos distintos, accesibilidad y barra de catálogo con pestañas no disponibles; verificar en `app/test/features/explore/explore_page_test.dart` contenido inicial, búsqueda/filtros, vacíos, estado/error/reintento e inyección del repositorio.
- [x] 2.2 Completar en `app/test/features/explore/explore_page_test.dart` la semántica de controles/etiquetas y áreas mínimas de toque, safe areas, desplazamiento y legibilidad sin truncado a 360x640 dp con escala 1.0 y 2.0, incluidos nombres largos; ejecutar `flutter test test/features/explore/explore_page_test.dart` desde `app/`.
- [x] 2.3 Documentar en `docs/data/usda-catalog.md` cómo corresponden los campos mostrados en P04 a los registros curados y sus límites; verificar que los comandos de reproducción documentados no requieran descargar ni almacenar el ZIP en el repositorio.

## 3. Pasaporte (P05)

- [x] 3.1 Implementar `app/lib/features/passport/presentation/plant_passport_page.dart` con General, Propiedades y Usos, campos ausentes explícitos, usos tradicionales con cita resoluble y aclaración no recomendatoria, favorito/formulaciones deshabilitados y tabs inferiores accesibles; verificar `app/test/features/passport/plant_passport_page_test.dart` con registros elegibles y sin usos, partes, procedencia y ausencia de evaluaciones.
- [x] 3.2 Resolver IDs conocidos/desconocidos dentro de P05, mostrando estado no encontrado sin redirect y con regreso seguro; verificar en `app/test/features/passport/plant_passport_page_test.dart` que ambas acciones no disponibles no mutan ni navegan y que faltan recomendaciones, dosis e inferencias de eficacia.
- [x] 3.3 Cubrir en `app/test/features/passport/plant_passport_page_test.dart` etiquetas/semántica, áreas de toque de al menos 48 dp, safe areas y texto esencial desplazable sin truncado a 360x640 dp con escala 1.0 y 2.0; usar las fixtures Roboto autorizadas solo para tests y ejecutar `flutter test test/features/passport/plant_passport_page_test.dart` desde `app/`.
- [x] 3.4 Actualizar `docs/data/usda-catalog.md` para explicar límites y trazabilidad de las citas visibles y el estado vacío de usos; verificar correspondencia entre documentación, asset y casos de prueba.

## 4. Navegación integrada y documentación de uso

- [x] 4.1 Extender `app/lib/app/router.dart` con la jerarquía `/` → `/explore` → `/explore/:plantId`, conservando push/pop y estado de P04; al resolver un identificador de planta desconocido, mostrar P05 no encontrado y padre seguro, incluso si no había estado previo de P04; verificar en `app/test/app/app_test.dart` pila/retornos, filtro-consulta-scroll restaurados, padre inicial `Todas`/consulta vacía y Home desde P04/P05 que limpia la pila, sin añadir manejo global 404 ni pantallas.
- [x] 4.2 Habilitar solo la acción Explorar en `app/lib/features/home/presentation/home_page.dart`, preservando los 11 callbacks/logs y sin mutación para las otras diez acciones; verificar con pruebas unitarias existentes de `home_action` y pruebas widget/router exactamente un log por activación en debug, cero logs automáticos, silencio en modo no permitido y navegación Explorar independiente de `kDebugMode`, sin exigir prueba de binario release/profile.
- [x] 4.3 Ajustar `app/integration_test/app_test.dart` para smoke Android de arranque, P03→P04→P05, retorno/estado de sesión, navegación Inicio, catálogo local offline y controles restantes/logs; verificar el comando documentado `flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO` en dispositivo Android y registrar explícitamente no ejecutado/no exitoso si no hay dispositivo.
- [x] 4.4 Actualizar `README.md` con alcance del catálogo, funcionamiento offline, límites de evidencia, guía de procedencia y comandos/ruta del smoke; verificar que los comandos indiquen directorio `app/`, mantengan el SDK pin y no presenten resultados previos como resultados de esta implementación.
- [x] 4.5 Registrar la QA manual únicamente en `openspec/changes/build-local-plant-catalog/qa/`, con fecha, serial, comandos/resultados, revisión visual del flujo, texto ampliado y offline Android; verificar que no se declare QA aprobada sin evidencia ejecutada y que limitaciones de emulador/ADB queden explícitas.

## 5. Verificación global de integración

- [x] 5.1 Desde `app/`, ejecutar `flutter pub get --enforce-lockfile`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test test/`; registrar resultados reales y corregir regresiones sin modificar el pin SDK ni el target Android.
- [x] 5.2 Con emulador/dispositivo Android disponible, ejecutar `flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO` y verificar flujo y retorno en la app real; si no está disponible, registrar el smoke como pendiente/no ejecutado, nunca como verde.
- [ ] 5.3 Realizar revisión integral de P03→P04→P05, retorno y Home, modo offline, legibilidad 100%/200%, accesibilidad y ausencia de solicitudes/logs de datos de usuario; guardar evidencia y limitaciones en `openspec/changes/build-local-plant-catalog/qa/` y verificar concordancia con el resultado automatizado Android.
  - Pendiente validación manual TalkBack (voz, foco, orden, gestos, lectura y scroll); evidencia parcial y alcance en [QA manual Android](qa/android-manual-4.5.md).
