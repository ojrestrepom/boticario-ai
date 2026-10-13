# Boticario AI

Aplicación móvil para explorar plantas y aceites esenciales, consultar información especializada y recibir orientación asistida por IA.

## Estado actual

Proyecto en desarrollo. La app es una aplicación Flutter para Android y vive en `app/`.

Implementado:

- Pantallas Inicio, Explorar plantas, Pasaporte de planta y Buscar por objetivo, con las rutas `/`, `/explore`, `/explore/:plantId` y `/goals`.
- Buscar por objetivo es solo visual: muestra las categorías de objetivo, pero no selecciona ni devuelve resultados.
- Catálogo local y sin conexión con cinco plantas (Lavanda, Eucalipto, Romero, Manzanilla y Menta), tomadas del snapshot USDA Dr. Duke (CC0). La procedencia y los límites están en la [guía del catálogo USDA](docs/data/usda-catalog.md).
- La búsqueda por nombre ignora mayúsculas y acentos.
- Los usos del Pasaporte son registros tradicionales con referencia, no consejo ni evidencia clínica; no hay dosis ni recomendaciones.
- Existe un backend de catálogo en `backend/`: una ingesta en Rust que construye una base neutral desde USDA Dr. Duke y una API HTTP de solo lectura. La app todavía no lo consume.

No implementado:

- Recomendaciones, formulación de mezclas, identificación con cámara y chat.
- Integración de la app con el backend, login y persistencia de usuario.
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
- `backend/`: workspace de Cargo con tres crates. `catalog-core` tiene los tipos de dominio, la normalización, la versión del esquema y el acceso a la base neutral. `catalog-ingest` descarga los insumos, importa la capa cruda, consolida las fuentes y escribe la base. `catalog-api` sirve esa base por HTTP.
- `data/`: la migración del esquema neutral (`data/migrations/`), la configuración de fuentes (`data/sources.toml`) y las salidas generadas e ignoradas por git `data/.cache/` y `data/build/`.
- `docs/`: canvas, mockups y procedencia de los datos.
- `openspec/`: specs vigentes y registro de cambios.
- `.github/workflows/`: integración continua.
- `.flutter-version`: versión fijada del SDK de Flutter.
- `mise.toml`: versión fijada de Rust para el backend.

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

Abrir `app/` como proyecto (su raíz tiene `pubspec.yaml`). Configurar la ruta raíz del SDK de Flutter en el plugin de Flutter y elegir el dispositivo o emulador Android en la selección de dispositivo. En la terminal integrada, situada en `app/`:

```bash
flutter pub get --enforce-lockfile
flutter analyze
flutter run -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador del dispositivo o emulador Android mostrado por `flutter devices`.

### 3. Pruebas

La app incluye pruebas unit y de widget en `app/test/`. Desde `app/`:

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

El smoke es una prueba de integración que usa la app real en Android. Su punto de entrada es `app/integration_test/app_test.dart` y delega el flujo en `app/integration_test/catalog_smoke.dart`. Requiere un dispositivo o emulador Android iniciado y listado por `flutter devices`. Recorre Inicio, Buscar por objetivo, Explorar y el Pasaporte de planta, con búsqueda, filtros y retorno a Inicio.

Desde `app/`:

```bash
flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador Android de `flutter devices`. Preparar y verificar previamente el SDK Android y sus licencias.

### 5. Comandos de calidad

Desde `app/`, los mismos comandos que ejecuta la CI:

```bash
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test test/
```

## Backend: catálogo y API

El backend construye una base SQLite neutral con las plantas del catálogo y la sirve en modo de solo lectura. El modelo de datos y cómo añadir un dataset están en la [guía del modelo de datos](docs/data/modelo-de-datos.md). Todos los comandos se ejecutan desde la raíz del repositorio, salvo los de verificación, que se ejecutan desde `backend/`.

### 1. Prerrequisitos

- [`mise`](https://mise.jdx.dev) instalado. Desde la raíz, `mise install` instala Rust **1.99.0**, la versión fijada en [`mise.toml`](mise.toml).
- Un compilador de C del sistema (en macOS, las Command Line Tools), porque SQLite se compila embebido.
- `diesel_cli` solo si se cambia el esquema: `mise exec -- cargo install diesel_cli --no-default-features --features sqlite-bundled`.

```bash
mise install
```

### 2. Construir el catálogo

La descarga es el único paso que usa la red. `build` y `rederive` nunca la tocan.

```bash
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- download
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- build
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- rederive
```

- `download` baja y verifica el ZIP de USDA en `data/.cache/Duke-Source-CSV.zip`; si ya está verificado, no lo vuelve a descargar.
- `build` verifica el ZIP, importa la capa cruda a `data/build/raw.db` y escribe la base neutral `data/build/catalog.db`. Imprime el número de fuentes y de plantas y el hash del contenido.
- `rederive` rehace `data/build/catalog.db` desde `data/build/raw.db`, sin el ZIP y sin red. Sirve para probar un cambio en la derivación o en las reglas de consolidación.

Las fuentes activas y su prioridad se leen de [`data/sources.toml`](data/sources.toml). Con `--data-dir <ruta>` se usa otro directorio de datos.

### 3. Ejecutar la API

```bash
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-api
```

La API se niega a arrancar si no encuentra la base. Se configura con argumentos y variables de entorno:

| Nombre | Por defecto | Uso |
|---|---|---|
| `CATALOG_DB` (o `--db <ruta>`) | `data/build/catalog.db` | Ruta de la base; el argumento tiene prioridad. |
| `HOST` | `127.0.0.1` | Dirección de escucha. |
| `PORT` | `8080` | Puerto de escucha. |
| `RUST_LOG` | `info` | Filtro de logs. |

Endpoints, todos `GET`:

- `/healthz`: estado del servicio.
- `/v1/sources`: fuentes con su licencia y procedencia.
- `/v1/plants`: lista paginada, con búsqueda opcional por `q`.
- `/v1/plants/{id}`: detalle de una planta.
- `/openapi.json`: el contrato OpenAPI.

```bash
curl 'http://127.0.0.1:8080/v1/plants?q=lavand'
```

### 4. Contrato OpenAPI

[`backend/openapi.json`](backend/openapi.json) se genera desde el código de la API y la misma API lo sirve en `/openapi.json`. Tras cambiar rutas o DTO, se regenera con:

```bash
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-api -- --openapi > backend/openapi.json
```

Un test falla si el archivo está desactualizado respecto al código.

### 5. Verificación

Desde `backend/`:

```bash
mise exec -- cargo fmt --all --check
mise exec -- cargo clippy --all-targets --workspace -- -D warnings
mise exec -- cargo test --workspace
```

Los tests marcados `#[ignore]` necesitan la salida real de `build` en `data/build/` (y, uno de ellos, `app/assets/data/plant_catalog.json`):

```bash
mise exec -- cargo test --workspace -- --ignored
```

### 6. Cambiar el esquema

1. Editar la migración de [`data/migrations/`](data/migrations/).
2. Subir `SCHEMA_VERSION` en `backend/catalog-core/src/version.rs`.
3. Regenerar `backend/catalog-core/src/schema.rs` con Diesel, desde `backend/`, sobre una base temporal; `backend/diesel.toml` fija la carpeta de migraciones y la ruta del archivo generado: `DATABASE_URL=/tmp/esquema.db mise exec -- diesel migration run`.
4. Reconstruir el catálogo con `rederive` o `build`.

La base no se migra: se regenera entera en cada construcción.

## Integración continua

El workflow [`.github/workflows/flutter.yml`](.github/workflows/flutter.yml) corre en push y pull request, con filtros de ruta `app/**`, `.flutter-version` y el propio workflow. Lee el pin [`.flutter-version`](.flutter-version) desde la raíz, instala ese SDK exacto y verifica la versión efectiva de Flutter antes de seguir.

El job de CI cubre unit y widget; **no** ejecuta el smoke Android ni monta un emulador. Replica los [comandos de calidad](#5-comandos-de-calidad).

Pendiente: el repositorio es un monorepo con `app/` exclusiva de Flutter, `backend/` para la API y la ingesta en Rust y `data/` para los artefactos de datos. Este workflow cubre solo `app/`; `backend/` y `data/` no tienen CI todavía. Cuando la arquitectura esté más asentada habrá que revisar sus filtros de ruta y añadir CI propia para esos componentes; por ahora se deja sin diseñar de forma deliberada.

## Documentación

Orden de lectura sugerido: Canvas, mockups, guía del catálogo USDA y guía del modelo de datos.

- Canvas y negocio: [índice](docs/canvas/README.md) y [modelo de negocio](docs/canvas/modelo-de-negocio.md).
- Mockups: [índice](docs/mockups/README.md), [pantallas](docs/mockups/pantallas.md) y [navegación](docs/mockups/navegacion.md).
- Datos: [guía del catálogo USDA](docs/data/usda-catalog.md) y [guía del modelo de datos](docs/data/modelo-de-datos.md).

Las specs vigentes están en `openspec/specs/`; cada cambio archivado, con sus informes de QA, está en `openspec/changes/archive/`.

### Árbol de docs

```text
docs/
  canvas/              índice y modelo de negocio
  mockups/             índice, pantallas y navegación
  data/               catálogo USDA (procedencia y curación) y modelo de datos del backend
  Canvas.png           canvas original
  mockups.png          lámina original de mockups
```

Referencias originales disponibles: [Canvas.png](docs/Canvas.png), [mockups.png](docs/mockups.png), [Boticario AI.docx](docs/Boticario%20AI.docx), [Boticario_AI_Reto_1.docx](docs/Boticario_AI_Reto_1.docx) y [DADM_Reto_1.pptx](docs/DADM_Reto_1.pptx).
