# Proposal

## Why

La app Flutter sigue leyendo un asset JSON con cinco plantas curadas a mano mientras el backend ya sirve 2.376 plantas con su API `/v1` (`docker compose up` en el puerto 8080). Conectar la app al backend es el siguiente incremento natural: Explorar y el Pasaporte dejan de depender de un snapshot embebido y pasan a mostrar el catálogo real. Con este cambio la app se convierte en el primer consumidor de `/v1`, lo que además cierra el periodo en el que la API podía cambiar de forma incompatible sin consecuencias.

## What Changes

- **BREAKING** (para la app): se retira el asset `app/assets/data/plant_catalog.json`, su lector y los modelos del catálogo local; el catálogo ya no funciona sin conectividad. Explorar y el Pasaporte necesitan el backend en marcha.
- Nueva capacidad `catalog-client`: cliente HTTP (`package:http`) con `http.Client` inyectado por un provider de Riverpod, parseo manual estricto sin codegen, dirección del backend por `--dart-define=API_BASE_URL` (por defecto `http://10.0.2.2:8080`), tiempo máximo de 10 s por petición y errores legibles y reintentables (el 404 del detalle se distingue como «no encontrada»).
- Modelos nuevos `PlantSummary`, `PlantPage` y `Plant` (con `names`, `parts` y `uses`), la regla de nombre para mostrar (primer nombre común como principal y científico como secundario; si no hay nombre común, el científico como principal y sin secundario) y la interfaz `CatalogRepository` con implementación HTTP.
- Explorar: lista paginada desde la API con scroll infinito (páginas de 50), búsqueda delegada a `q` con debounce de unos 300 ms y descarte de respuestas atrasadas, filtros `Todas`/`Plantas`/`Aceites` locales, y un `Notifier` de Riverpod que conserva consulta, filtro y páginas durante la sesión. Se elimina `plant_search.dart`.
- Pasaporte: la ruta `/explore/:plantId` usa el id (slug) contra `GET /v1/plants/{id}` con estados de carga, error reintentable, no encontrada y datos. `General` muestra familia, nombres comunes con idioma y partes; `Usos` muestra los usos de la API con su cita. Desaparecen origen, descripción y procedencia de la pantalla.
- Android: permiso `INTERNET` en el manifest principal y HTTP en claro solo en los manifests `debug` y `profile`.
- El asset se mueve a `backend/catalog-ingest/tests/fixtures/` y `asset_crosscheck.rs` (ignorado) lo lee de ahí; se corrige el doc comment de `http.rs` («Detalle de una planta.») y se regenera `backend/openapi.json`.
- Smoke Android contra el backend en Docker: el guard HTTP solo permite el host de la URL base y el flujo busca una planta real. El test de contrato ejecuta el mismo flujo con `MockClient` y fixtures en `app/test/fixtures/api/`.
- Documentación: `README.md`, `docs/data/usda-catalog.md` (recortado a guía de la fuente USDA), `docs/data/modelo-de-datos.md` y `backend/README.md`.
- Se registra que `catalog-api` tiene su primer consumidor: la excepción de «Compatibilidad dentro de `/v1`» deja de aplicar y, desde aquí, `/v1` solo admite cambios aditivos.

## Capabilities

### New Capabilities

- `catalog-client`: consumo de la API del catálogo desde la app (dirección configurable, peticiones permitidas, parseo estricto, errores, nombre para mostrar, permisos de Android y pruebas sin red).

### Modified Capabilities

- `explore-screen`: la lista viene de la API con paginación infinita, la búsqueda se delega al backend y se añaden estados de red y de carga de más resultados.
- `plant-passport`: el pasaporte se resuelve por id contra la API, sin procedencia, origen ni descripción, con usos y partes del contrato y un estado de error de red reintentable.
- `flutter-app-bootstrap`: la app deja de ser totalmente local (Explorar y Pasaporte usan la API del catálogo), la documentación cubre el backend con Docker y las verificaciones y el smoke se ajustan.

### Removed Capabilities

- `plant-catalog`: el catálogo offline de cinco plantas desaparece de la app; el catálogo vive en el backend y lo cubren `catalog-ingest` y `catalog-api`.

## Impact

- Código en `app/`: `pubspec.yaml` y `pubspec.lock` (dependencia `http`, sin el asset), `lib/features/catalog/` (dominio, datos, providers), `lib/features/explore/`, `lib/features/passport/`, `lib/app/router.dart`, manifests de Android (`main`, `debug`, `profile`) y los tests de unidad, widget, contrato e integración, con fixtures en `test/fixtures/api/`.
- Código en `backend/`: solo el doc comment de `catalog-api/src/http.rs`, `backend/openapi.json` regenerado, el fixture movido y `asset_crosscheck.rs`, además de `backend/README.md`.
- Documentación: `README.md`, `docs/data/usda-catalog.md`, `docs/data/modelo-de-datos.md`.
- Specs: se elimina `plant-catalog`, se añade `catalog-client` y se modifican `explore-screen`, `plant-passport` y `flutter-app-bootstrap`. `catalog-api` no lleva delta.
- Sin cambios: el contrato de la API, la base de datos y su hash, `home-screen`, `goal-search-screen` y la CI (`.github/workflows/flutter.yml`; los tests unitarios y de widget siguen sin red).
- Fuera de alcance: nombres comunes en español (trabajo futuro de consolidación en el backend con una fuente `es`), caché o modo offline, despliegue del backend y HTTPS, favoritos, historial y perfil, resultados de Buscar por objetivo, CI del backend y cualquier cambio del contrato de la API.
