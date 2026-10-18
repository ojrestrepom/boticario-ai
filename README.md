# Boticario AI

Aplicación móvil para explorar plantas y aceites esenciales, consultar información especializada y recibir orientación asistida por IA.

## Estado actual

Proyecto en desarrollo. La app es una aplicación Flutter para Android y vive en `app/`.

Implementado:

- Pantallas Inicio, Explorar plantas, Pasaporte de planta y Buscar por objetivo, con las rutas `/`, `/explore`, `/explore/:plantId` y `/goals`.
- Buscar por objetivo es solo visual: muestra las categorías de objetivo, pero no selecciona ni devuelve resultados.
- Explorar y el Pasaporte consumen por HTTP el catálogo del backend: 2.376 plantas del dataset USDA Dr. Duke's Phytochemical and Ethnobotanical Databases (CC0). Explorar pagina con scroll infinito de 50 en 50. El nombre principal es el primer nombre común que entrega la API (hoy en inglés o `und`; ninguna planta tiene todavía nombre en español) y el secundario es el científico; si no hay nombre común se muestra solo el científico. Sin backend o sin conectividad, Explorar y el Pasaporte muestran un error con «Reintentar»; Inicio y Buscar por objetivo siguen funcionando. La fuente y sus límites están en la [guía de la fuente USDA](docs/data/usda-catalog.md).
- La búsqueda por nombre la resuelve la API (`q`), que normaliza mayúsculas y acentos.
- El Pasaporte muestra la familia (o «No disponible en fuente»), los nombres comunes con su idioma, y las partes y los usos con su referencia bibliográfica.
- Los usos del Pasaporte son registros tradicionales con referencia, no consejo ni evidencia clínica; no hay dosis ni recomendaciones.
- Existe un backend de catálogo en `backend/`: una ingesta en Rust que construye una base neutral desde USDA Dr. Duke y una API HTTP de solo lectura.

No implementado:

- Recomendaciones, formulación de mezclas, identificación con cámara y chat.
- Login y persistencia de usuario.
- Favoritos, Historial y Perfil se ven en la barra inferior, pero no hacen nada.

Los proveedores de servicios están por definir. La distribución inicial prevista es Google Play (Android); iOS es una posibilidad futura.

## Funcionalidades previstas

- Explorar plantas y aceites con pasaportes digitales.
- Recomendaciones según objetivo, preferencias y restricciones.
- Formulaciones básicas asistidas.
- Chat de consulta con fuentes verificables.
- Identificación por cámara, planteada como experimento.

Varias de estas funcionalidades siguen siendo conceptos todavía no implementados.

Los datos de los mockups son ilustrativos. El contenido especializado requiere revisión experta antes de usarse en el producto.

## Estructura del repositorio

- `app/`: aplicación Flutter.
- `backend/`: workspace de Cargo con tres crates, con su guía de desarrollo en [`backend/README.md`](backend/README.md). `catalog-core` tiene los tipos de dominio, la normalización, la versión del esquema y el acceso a la base neutral. `catalog-ingest` descarga los insumos, importa la capa cruda, consolida las fuentes y escribe la base. `catalog-api` sirve esa base por HTTP.
- `data/`: la migración del esquema neutral (`data/migrations/`), la configuración de fuentes (`data/sources.toml`) y las salidas generadas e ignoradas por git `data/.cache/` y `data/build/`.
- `docs/`: canvas, mockups y documentación de los datos.
- `openspec/`: specs vigentes y registro de cambios.
- `.github/workflows/`: integración continua y despliegue.
- `.flutter-version`: versión fijada del SDK de Flutter.
- `mise.toml`: versión fijada de Rust para el desarrollo nativo del backend.
- `Dockerfile`, `compose.yaml` y `.dockerignore`: imagen y arranque con Docker del backend.
- `docs/deploy/cloud-run.md`: guía del despliegue del backend en Google Cloud Run (preparación, operación, costo y desmontaje).
- `.github/workflows/deploy-backend.yml`: workflow que construye la imagen del backend y la despliega en Cloud Run.

El repositorio es un monorepo: `app/` es exclusiva de Flutter, `backend/` es exclusivo de Rust y `data/` contiene artefactos de datos, no código.

## Quick start

Esta guía describe la preparación del entorno, la apertura del proyecto, su ejecución en Android y las pruebas.

### 1. Prerrequisitos

- Flutter **3.47.6** stable, que incluye Dart **3.13.5**; no instalar Dart aparte. Es la versión fijada en [`.flutter-version`](.flutter-version) para local y CI. La CLI no lee ese archivo de forma automática: cada entorno debe instalar la misma versión y comprobarla. Ver [docs.flutter.dev/install](https://docs.flutter.dev/install).
- Android Studio con los plugins de Flutter y Dart, Android SDK y Command-line Tools, según el [setup de Android](https://docs.flutter.dev/platform-integration/android/setup).
- Un dispositivo Android o un emulador/AVD Android iniciado. Chrome o Linux Desktop no cuentan para el target Android.
- Añadir el directorio `bin` del SDK de Flutter al `PATH`. Configurar la ruta raíz del SDK de Flutter en el plugin de Android Studio.

Si el SDK de Flutter no está instalado, instalarlo manualmente en la versión fijada desde el enlace anterior; no hay instalación automática.

```bash
flutter doctor -v
flutter doctor --android-licenses
flutter devices
```

Revisar y aceptar las licencias pendientes de forma interactiva. Verificar que `flutter devices` liste el dispositivo o emulador Android iniciado. Resolver los hallazgos de Android aplicables.

### 2. Abrir y ejecutar en Android Studio

La app necesita el backend en marcha y un token de API: desde la raíz del repositorio, `docker compose up` (ver [Backend: catálogo y API](#backend-catálogo-y-api)). Por defecto la app llama a `http://10.0.2.2:8080`, que es como el emulador Android alcanza al backend que corre en el Mac. Para un dispositivo físico en la misma red, pasar la dirección con `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080` (también en `flutter build` y en el smoke). El permiso `INTERNET` está en todos los builds; `debug` y `profile` habilitan además el HTTP en claro en la pila de red de Android, que es lo que permite llegar al backend local, y `release` no lo habilita. Esa restricción no alcanza al cliente Dart (`dart:io`), así que la garantía de HTTPS la da la URL que se pasa en `API_BASE_URL`, no el build.

La API exige `Authorization: Bearer <token>` en `/v1`. La app toma el token al compilar de `--dart-define=API_TOKEN=<token>` (no hay valor por defecto ni token en el repositorio), junto a `API_BASE_URL`, en `flutter run`, `flutter build` y el smoke. Sin `API_TOKEN` la app arranca pero no envía `Authorization`, la API responde 401 y la app muestra un error de «no autorizada». El token sale de la lista `API_TOKENS` del backend: para el backend local, uno de los valores de `API_TOKENS` del `.env` de la raíz (ver [Backend: catálogo y API](#backend-catálogo-y-api)); para Cloud Run, el token de la app que guarda el secreto, según [`docs/deploy/cloud-run.md`](docs/deploy/cloud-run.md). Un token embebido en el APK se puede extraer, y solo identifica a la app, no al usuario: no es una credencial de usuario.

Para no escribir el token en cada comando, Flutter admite `--dart-define-from-file`. Crear `app/dart_defines.local.json` (ignorado por git, nunca se commitea) con este contenido, sustituyendo los marcadores:

```json
{
  "API_BASE_URL": "<URL-del-backend>",
  "API_TOKEN": "<token-de-la-app>"
}
```

y pasarlo desde `app/` con `--dart-define-from-file=dart_defines.local.json` (desde la raíz sería `app/dart_defines.local.json`), por ejemplo `flutter run -d ID_DEL_DISPOSITIVO --dart-define-from-file=dart_defines.local.json`. Es opcional: equivale a escribir los dos `--dart-define`.

Para usar el backend desplegado en Cloud Run no hace falta `docker compose up`: el build `release` debe apuntar a esa URL HTTPS (un `release` compilado con una URL `http://` la usaría tal cual) y se compila con `flutter build apk --release --dart-define=API_BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app --dart-define=API_TOKEN=<token-de-la-app>` (o `flutter run --release -d ID_DEL_DISPOSITIVO --dart-define=API_BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app --dart-define=API_TOKEN=<token-de-la-app>`); sin el define de la dirección, esta sigue siendo la del emulador, y sin el del token la API responde 401. Las pruebas con el backend local (`http://`) se dejan para `debug` y `profile`, que además no consumen la capa gratuita. La guía del despliegue está en [`docs/deploy/cloud-run.md`](docs/deploy/cloud-run.md).

Abrir `app/` como proyecto (su raíz tiene `pubspec.yaml`). Configurar la ruta raíz del SDK de Flutter en el plugin de Flutter y elegir el dispositivo o emulador Android en la selección de dispositivo. En la terminal integrada, situada en `app/`:

```bash
flutter pub get --enforce-lockfile
flutter analyze
flutter run -d ID_DEL_DISPOSITIVO --dart-define=API_TOKEN=<token-de-la-app>
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador del dispositivo o emulador Android mostrado por `flutter devices`. Para un dispositivo físico: `flutter run -d ID_DEL_DISPOSITIVO --dart-define=API_BASE_URL=http://<IP-del-Mac>:8080 --dart-define=API_TOKEN=<token-de-la-app>`.

### 3. Pruebas

La app incluye pruebas unit y de widget en `app/test/`. No usan red: emplean un cliente HTTP falso y fixtures en [`app/test/fixtures/api/`](app/test/fixtures/api/). Desde `app/`:

```bash
flutter test test/
```

Para ejecutar una sola suite, desde `app/`:

```bash
flutter test test/features/home/home_action_test.dart
flutter test test/features/home/home_page_test.dart
flutter test test/app/app_test.dart
flutter test test/app/catalog_smoke_contract_test.dart
```

Las fixtures de tipografía Roboto usadas por pruebas de layout están en [`app/test/fixtures/fonts/`](app/test/fixtures/fonts/) y son solo para tests; no son assets ni fuentes de la aplicación.

### 4. Smoke Android

El smoke es una prueba de integración que usa la app real en Android. Su punto de entrada es `app/integration_test/app_test.dart` y delega el flujo en `app/integration_test/catalog_smoke.dart`. Requiere un dispositivo o emulador Android iniciado y listado por `flutter devices`, y el backend en marcha (`docker compose up` desde la raíz) con su `API_TOKENS`. El smoke exige `--dart-define=API_TOKEN=<token-de-la-app>` y falla enseguida con un mensaje claro si falta. Recorre Inicio, Buscar por objetivo, Explorar y el Pasaporte de planta, con la búsqueda de una planta real (`lavandula` → «English Lavender» / «Lavandula angustifolia»), filtros y retorno a Inicio.

Desde `app/`:

```bash
flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO --dart-define=API_TOKEN=<token-de-la-app>
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador Android de `flutter devices`. Con un dispositivo físico, añadir `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080`. También acepta `--dart-define-from-file=dart_defines.local.json`. Preparar y verificar previamente el SDK Android y sus licencias.

Para correr el smoke contra el backend desplegado, sin `docker compose up`, pasar la dirección de Cloud Run: `flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO --dart-define=API_BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app --dart-define=API_TOKEN=<token-de-la-app>`.

### 5. Comandos de calidad

Desde `app/`, los mismos comandos que ejecuta la CI:

```bash
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test test/
```

## Backend: catálogo y API

El backend construye una base SQLite neutral con las plantas del catálogo y la sirve en modo de solo lectura. El modelo de datos y cómo añadir un dataset están en la [guía del modelo de datos](docs/data/modelo-de-datos.md). La app lo consume desde el emulador Android en `http://10.0.2.2:8080`. `/v1` solo admite cambios aditivos, porque la app ya es su primer consumidor. Para ejecutarlo solo hace falta Docker.

### Prerrequisito

Docker Desktop, o un Docker compatible, con Compose.

### Arrancar

Desde la raíz del repositorio:

```bash
docker compose up --build
```

La primera construcción compila el backend, descarga el dataset de USDA y construye el catálogo dentro de la imagen. Tarda varios minutos la primera vez y segundos las siguientes, gracias a las cachés de construcción. La imagen resultante contiene la API y el catálogo ya construido, así que el contenedor sirve sin red.

### Endpoints

Todos son `GET`, por defecto en `http://localhost:8080`:

- `/health`: estado del servicio.
- `/v1/plants`: lista paginada, con búsqueda opcional por `q`.
- `/v1/plants/{id}`: detalle de una planta.
- `/openapi.json`: el contrato OpenAPI.

```bash
curl 'http://localhost:8080/v1/plants?q=lavand'
```

La imagen no define un `healthcheck`; para sondear el servicio desde fuera, usar `/health`.

### Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `PORT` | `8080` | Puerto de escucha y puerto publicado en el anfitrión. |
| `RUST_LOG` | `info` | Filtro de logs. |

```bash
PORT=9090 docker compose up
RUST_LOG=warn docker compose up
```

Dentro del contenedor la API siempre escucha en `0.0.0.0`; esa dirección no es configurable.

### Hash del catálogo

La construcción imprime el hash del contenido del catálogo en su log:

```bash
docker compose --progress=plain build 2>&1 | grep 'hash:'
```

Si todas las capas vienen de la caché, el log no repite la línea; en ese caso, `docker compose --progress=plain build --no-cache 2>&1 | grep 'hash:'` la vuelve a imprimir, a costa de repetir toda la construcción. El hash depende solo de los datos y es el mismo que da una construcción nativa del mismo insumo.

### Reconstruir y parar

Tras cambiar el código o los datos, se reconstruye y se arranca de nuevo con `docker compose up --build`. Para parar y eliminar el contenedor:

```bash
docker compose down
```

Las cachés de construcción viven en el almacenamiento de Docker, no en el repositorio; se limpian con `docker builder prune`. Si una construcción se comporta de forma inexplicable, `docker compose build --no-cache` ignora la caché de capas y reconstruye todo (las monturas de caché solo se limpian con `docker builder prune`).

### Despliegue en Cloud Run

El workflow [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) verifica el backend (`fmt`, `clippy` y pruebas, con el workflow reutilizable `backend-ci.yml`) y, solo si pasa, construye la imagen amd64 y la despliega en Cloud Run en cada push a `main` que toque el backend (`backend/`, `data/migrations/`, `data/sources.toml`, `Dockerfile`, `mise.toml`, `.dockerignore` o el propio workflow), o a mano con `workflow_dispatch`. Si la verificación falla, no se publica ninguna imagen ni se crea ninguna revisión. El servicio responde en https://boticario-api-d3xv5q3iaa-pv.a.run.app.

La imagen local se construye para la arquitectura del anfitrión (arm64 en un Mac con Apple Silicon); `docker build --platform linux/amd64 .` queda como prueba local de la imagen que despliega el workflow.

La preparación en Google Cloud, la operación, el costo esperado y el desmontaje están en la [guía de Cloud Run](docs/deploy/cloud-run.md).

### Desarrollo del backend

Para modificar el código Rust o ejecutarlo sin Docker, ver [`backend/README.md`](backend/README.md).

## Integración continua

El workflow [`.github/workflows/flutter.yml`](.github/workflows/flutter.yml) corre en push y pull request, con filtros de ruta `app/**`, `.flutter-version` y el propio workflow. Lee el pin [`.flutter-version`](.flutter-version) desde la raíz, instala ese SDK exacto y verifica la versión efectiva de Flutter antes de seguir.

El job de CI de Flutter cubre unit y widget; **no** ejecuta el smoke Android ni monta un emulador. Replica los [comandos de calidad](#5-comandos-de-calidad).

El workflow [`.github/workflows/backend-ci.yml`](.github/workflows/backend-ci.yml) verifica el backend: `cargo fmt --check`, `cargo clippy` con `-D warnings` y `cargo test` sobre el workspace, con el Rust fijado en [`mise.toml`](mise.toml). Corre en pull requests y en pushes a ramas distintas de `main` que toquen `backend/`, `data/migrations/`, el `Dockerfile`, `mise.toml` o el propio workflow. El comando local equivalente está en la guía de [`backend/README.md`](backend/README.md#integración-continua).

El workflow [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) verifica el backend y, solo si pasa, construye la imagen amd64 y la despliega en Cloud Run en cada push a `main` que toque el backend; ver [Despliegue en Cloud Run](#despliegue-en-cloud-run).

## Documentación

Orden de lectura sugerido: Canvas, mockups, guía de la fuente USDA y guía del modelo de datos.

- Canvas y negocio: [índice](docs/canvas/README.md) y [modelo de negocio](docs/canvas/modelo-de-negocio.md).
- Mockups: [índice](docs/mockups/README.md), [pantallas](docs/mockups/pantallas.md) y [navegación](docs/mockups/navegacion.md).
- Datos: [guía de la fuente USDA](docs/data/usda-catalog.md) y [guía del modelo de datos](docs/data/modelo-de-datos.md).
- Desarrollo del backend: [`backend/README.md`](backend/README.md), con el flujo nativo con mise y cargo.
- Despliegue: [guía de Cloud Run](docs/deploy/cloud-run.md).

Las specs vigentes están en `openspec/specs/`; cada cambio archivado, con sus informes de QA, está en `openspec/changes/archive/`.

### Árbol de docs

```text
docs/
  canvas/              índice y modelo de negocio
  mockups/             índice, pantallas y navegación
  data/               fuente USDA (procedencia y criterio) y modelo de datos del backend
  Canvas.png           canvas original
  mockups.png          lámina original de mockups
```

Referencias originales disponibles: [Canvas.png](docs/Canvas.png), [mockups.png](docs/mockups.png), [Boticario AI.docx](docs/Boticario%20AI.docx), [Boticario_AI_Reto_1.docx](docs/Boticario_AI_Reto_1.docx) y [DADM_Reto_1.pptx](docs/DADM_Reto_1.pptx).
