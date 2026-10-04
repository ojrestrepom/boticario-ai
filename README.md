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

No implementado:

- Recomendaciones, formulación de mezclas, identificación con cámara y chat.
- Backend, login y persistencia de usuario.
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
- `docs/`: canvas, mockups, research y procedencia de los datos.
- `openspec/`: specs vigentes y registro de cambios.
- `.github/workflows/`: integración continua.
- `.flutter-version`: versión fijada del SDK de Flutter.

El repositorio se trata como monorepo; las carpetas del backend y de la ingesta de datos aún no existen.

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

## Integración continua

El workflow [`.github/workflows/flutter.yml`](.github/workflows/flutter.yml) corre en push y pull request, con filtros de ruta `app/**`, `.flutter-version` y el propio workflow. Lee el pin [`.flutter-version`](.flutter-version) desde la raíz, instala ese SDK exacto y verifica la versión efectiva de Flutter antes de seguir.

El job de CI cubre unit y widget; **no** ejecuta el smoke Android ni monta un emulador. Replica los [comandos de calidad](#5-comandos-de-calidad).

Pendiente: el repositorio se tratará como monorepo, con `app/` exclusiva de Flutter y carpetas futuras para el backend y la ingesta de datos, que aún no existen. Este workflow cubre solo `app/`. Cuando la arquitectura esté más definida habrá que revisar sus filtros de ruta y añadir CI propia para los componentes nuevos; por ahora se deja sin diseñar de forma deliberada.

## Documentación

Orden de lectura sugerido: Canvas, mockups, research, plan de trabajo.

- Canvas y negocio: [índice](docs/canvas/README.md) y [modelo de negocio](docs/canvas/modelo-de-negocio.md).
- Mockups: [índice](docs/mockups/README.md), [pantallas](docs/mockups/pantallas.md) y [navegación](docs/mockups/navegacion.md).
- Research Flutter: [índice](docs/research/flutter/README.md), [fuentes](docs/research/flutter/fuentes.md) y [plan de trabajo](docs/research/flutter/plan-de-trabajo.md).
- Datos: [guía del catálogo USDA](docs/data/usda-catalog.md).

Las specs vigentes están en `openspec/specs/`; cada cambio archivado, con sus informes de QA, está en `openspec/changes/archive/`.

### Árbol de docs

```text
docs/
  canvas/              índice y modelo de negocio
  mockups/             índice, pantallas y navegación
  research/flutter/    índice, fuentes y plan de trabajo
  data/               procedencia, curación y límites del catálogo USDA
  Canvas.png           canvas original
  mockups.png          lámina original de mockups
```

Referencias originales disponibles: [Canvas.png](docs/Canvas.png), [mockups.png](docs/mockups.png), [Boticario AI.docx](docs/Boticario%20AI.docx), [Boticario_AI_Reto_1.docx](docs/Boticario_AI_Reto_1.docx) y [DADM_Reto_1.pptx](docs/DADM_Reto_1.pptx).
