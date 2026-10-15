# Tasks

## 1. Cliente de catálogo

- [x] 1.1 Añadir `http` a `app/pubspec.yaml` con versión fijada en `pubspec.lock`; resolver con `flutter pub get` (sin `--enforce-lockfile`) para fijar `http` en `pubspec.lock` y confirmar después con `flutter pub get --enforce-lockfile` y `flutter analyze` desde `app/`.
- [x] 1.2 Definir la dirección base (`String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8080')`, barra final tolerada) y declarar `INTERNET` en el manifest principal y `android:usesCleartextTraffic="true"` solo en los de `debug` y `profile`; verificar con un test unitario de la dirección (por defecto, sobrescrita y con barra final) y con `grep` de los tres manifests (release sin `usesCleartextTraffic`).
- [x] 1.3 Crear en `lib/features/catalog/domain/` los modelos `PlantSummary`, `PlantPage` y `Plant` (con `names`, `kind`, idioma, `parts` y `uses` con `reference`) y la regla de nombre para mostrar; verificar con tests unitarios de la regla (con nombre común, sin nombre común, idioma `en` y `und`).
- [x] 1.4 Implementar el parseo manual estricto (campos requeridos y tipos según `backend/openapi.json`, campos desconocidos ignorados, `family` `null`) y la excepción de cliente legible; verificar con tests unitarios de listado y detalle válidos, campos desconocidos, campo ausente, tipo erróneo y JSON inválido.
- [x] 1.5 Definir `CatalogRepository` y su implementación HTTP (`listPlants` con `q` recortada y limitada a 200 caracteres, `limit` y `offset` codificados; `getPlant` con id codificado, `null` en 404; `Accept: application/json`; 10 s de tiempo máximo; conexión, timeout, 5xx, 400 y cuerpo inválido como error de cliente); verificar con tests unitarios con `MockClient` (URL y cabeceras exactas, codificación, 404, 400, 5xx, timeout y fallo de conexión).
- [x] 1.6 Añadir los providers de Riverpod (`http.Client`, dirección base y repositorio) y las fixtures de `test/fixtures/api/` (planta con nombres comunes, sin ninguno, con `family` `null`, con usos y sin usos, tomadas de la API real); verificar con `flutter test test/features/catalog` y `flutter analyze` sin red.

## 2. Explorar

- [ ] 2.1 Crear el `Notifier` de Riverpod 3 de Explorar que conserve consulta, filtro, páginas, `total`, carga, error y error del pie durante la sesión, con páginas de 50, debounce de unos 300 ms y descarte de respuestas atrasadas; `Aceites` muestra su estado vacío sin pedir nada a la red; verificar con tests unitarios de paginación, fin de lista, error al cargar más con conservación de lo cargado, debounce, respuesta atrasada descartada y consulta vacía.
- [ ] 2.2 Reescribir `explore_page.dart` sobre el `Notifier` (nombre principal y secundario, estados de carga, error con `Reintentar`, vacío y vacío de Aceites, scroll infinito con pie de carga, fin de lista y error reintentable en el pie, restauración de consulta, filtro y posición al volver); verificar con widget tests con `MockClient` y fixtures que cubran los escenarios de `explore-screen`.
- [ ] 2.3 Comprobar la accesibilidad de Explorar (360x640 dp al 100 % y 200 %, etiquetas y áreas de toque de al menos 48 dp, incluidos `Reintentar` y el pie de lista); verificar con los widget tests de accesibilidad existentes adaptados.

## 3. Pasaporte y router

- [ ] 3.1 Cambiar `/explore/:plantId` a id de texto sin `int.tryParse` y crear el provider de planta por id sobre `getPlant`; verificar con tests de router y de provider (datos, no encontrada y error con reintento).
- [ ] 3.2 Reescribir `plant_passport_page.dart` con los estados carga, error reintentable, `Planta no encontrada` y datos, nombre principal y científico, `General` (familia o `No disponible en fuente`, nombres comunes con idioma, partes, `Tipo de aceite` no aplicable, bibliografía deduplicada si ya existe), `Propiedades` sin cambios y `Usos` (actividad, `Registro tradicional`, aclaración no recomendatoria, cita, vacío explícito), sin origen, descripción ni procedencia; verificar con widget tests y fixtures (con y sin nombres comunes, `family` `null`, con y sin usos, Romero con muchos usos).
- [ ] 3.3 Comprobar la accesibilidad del pasaporte y las acciones deshabilitadas a 360x640 dp al 100 % y 200 %; verificar con los widget tests existentes adaptados.

## 4. Retirada del asset y del catálogo local

- [ ] 4.1 Mover con `git mv` `app/assets/data/plant_catalog.json` a `backend/catalog-ingest/tests/fixtures/plant_catalog.json`, ajustar `backend/catalog-ingest/tests/asset_crosscheck.rs` para leerlo de ahí y actualizar `backend/README.md` (línea 86); verificar con `mise exec -- cargo test -p catalog-ingest --test asset_crosscheck -- --ignored` desde `backend/` (pasa leyendo el fixture desde su nueva ubicación, con `data/build/catalog.db` presente) y `grep -rn "app/assets" backend` sin resultados.
- [ ] 4.2 Eliminar el asset de `pubspec.yaml`, `PlantCatalogAssetDataSource`, `PlantCatalog`, `PlantCatalogProvenance`, `SourceRecord`, `TraditionalUse`, `PlantReference`, `PlantKind`, `plantCatalogProvider`, `plant_search.dart` y los tests que dependían de ellos; verificar con `grep -rn "plant_catalog\|PlantCatalog\|plant_search" app/lib` sin resultados y `flutter analyze` (los usos en `app/test` y `app/integration_test` que quedan se retiran en 5.1 y 5.2).
- [ ] 4.3 Actualizar `test/app/app_test.dart` y los demás tests restantes para usar el repositorio de prueba con las fixtures; verificar con `flutter test test/` desde `app/`.

## 5. Smoke Android y contrato

- [ ] 5.1 Reescribir `test/app/catalog_smoke_contract_test.dart` para ejecutar el flujo (buscar `lavandula`, ver «English Lavender» y «Lavandula angustifolia», abrir el pasaporte, volver, entrar a P06 y sus retornos) con `MockClient` y fixtures, quitando la carga del asset `assets/data/plant_catalog.json` con `rootBundle`; verificar con `flutter test test/app/catalog_smoke_contract_test.dart`.
- [ ] 5.2 Reescribir `integration_test/catalog_smoke.dart`: requiere el backend en marcha, el guard HTTP permite solo el host de la URL base y deniega el resto, y busca una planta real en lugar de las cinco filas fijas, y quitar las cargas con `rootBundle` del asset en `integration_test/app_test.dart` y `integration_test/catalog_smoke.dart`; verificar con `flutter analyze`, `dart format --output=none --set-exit-if-changed .` y `grep -rn "plant_catalog\|PlantCatalog\|plant_search" app/lib app/test app/integration_test` sin resultados.

## 6. Documentación y backend

- [ ] 6.1 Actualizar `README.md`: «Estado actual» (quitar «catálogo local… cinco plantas» y «La app todavía no lo consume»), quick start con `docker compose up` antes de `flutter run`, dirección del emulador, `--dart-define` para dispositivo físico y que el smoke necesita el backend; verificar con `grep -n "cinco plantas\|todavía no lo consume" README.md` sin resultados y que cada párrafo y elemento de lista está en una sola línea.
- [ ] 6.2 Recortar `docs/data/usda-catalog.md` a guía de la fuente USDA (fuente, archivo, licencia, fechas y criterio de curación que sigue el adaptador del backend), quitando las secciones del asset, la correspondencia con P04/P05 y el script de validación del asset, y revisar los enlaces desde `docs/data/modelo-de-datos.md` y `README.md`; verificar con `grep -rn "plant_catalog.json" docs README.md` sin resultados y enlaces que resuelven.
- [x] 6.3 Corregir el doc comment de `backend/catalog-api/src/http.rs` (línea 180) a «Detalle de una planta.» y regenerar `backend/openapi.json` con `mise exec -- cargo run -p catalog-api -- --openapi`; verificar que el diff solo cambia el `summary` de `/v1/plants/{id}` y que `mise exec -- cargo test -p catalog-api` pasa.

## 7. Verificación global y QA

- [ ] 7.1 Desde `app/`, ejecutar `flutter pub get --enforce-lockfile`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test test/`; verificar que todo queda en verde.
- [ ] 7.2 Desde `backend/`, ejecutar `mise exec -- cargo fmt --all --check`, `mise exec -- cargo clippy --all-targets --workspace -- -D warnings` y `mise exec -- cargo test --workspace`; verificar que todo queda en verde.
- [ ] 7.3 Ejecutar `openspec validate connect-app-to-backend --strict`; verificar que pasa.
- [ ] 7.4 Con `docker compose up` en el Mac y el emulador Android, ejecutar el smoke (`integration_test/catalog_smoke.dart`) y comprobar a mano Explorar (scroll infinito, búsqueda, `Reintentar` con el backend detenido) y el pasaporte (con y sin nombre común, `family` `null`, Romero); reportar como no ejecutado lo que falte por dispositivo o backend.
- [ ] 7.5 Pasar QA sobre el cambio completo y registrar el informe en `qa/` dentro del cambio, corrigiendo los defectos hallados.
