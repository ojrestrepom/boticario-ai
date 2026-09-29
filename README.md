# Boticario AI

Aplicación móvil para explorar plantas y aceites esenciales, consultar
información especializada y recibir orientación asistida por IA.

## Estado actual

Proyecto en desarrollo con Flutter. La base de la app Android ya existe en
`app/`: scaffold `--empty` para Android, SDK fijado en
[`.flutter-version`](.flutter-version), dependencias `flutter_riverpod` y
`go_router` resueltas en `app/pubspec.lock`, y el shell del Hello World ya
implementado: pantalla inicial en la ruta `/` con el saludo
`Hola, Boticario AI`, contador demo con Riverpod y navegación con `go_router`.
El shell está cubierto por pruebas unit y de widget y por un smoke de
integración Android que arranca la app real; la integración continua ya está
operativa y validada en verde en `.github/workflows/flutter.yml`. Todavía no hay
funcionalidades de producto (plantas, IA, cámara, persistencia): esas features
siguen pendientes.

Disponible en `docs/`:

- Canvas de negocio transcrito.
- Mockups de pantallas y flujo de navegación.
- Research de Flutter con propuestas técnicas.

Los proveedores de servicios están por definir. La distribución inicial prevista
es Google Play (Android); iOS es una posibilidad futura.

## Funcionalidades previstas

- Explorar plantas y aceites con pasaportes digitales.
- Recomendaciones según objetivo, preferencias y restricciones.
- Formulaciones básicas asistidas.
- Chat de consulta con fuentes verificables.
- Identificación por cámara, planteada como experimento.

Los datos de los mockups son ilustrativos. El contenido especializado requiere
revisión experta antes de usarse en el producto.

## Quick start

La base de la app ya existe en `app/`. Esta guía describe la preparación del
entorno, la apertura del proyecto y su ejecución en Android.

### 1. Prerrequisitos

- Flutter **3.47.5** stable, que incluye Dart **3.13.4**; no instalar Dart
  aparte. Es la versión fijada en [`.flutter-version`](.flutter-version) para
  local y CI. La CLI no lee ese archivo de forma automática: cada entorno debe
  instalar la misma versión y comprobarla. Ver
  [docs.flutter.dev/install](https://docs.flutter.dev/install).
- Android Studio con los plugins de Flutter y Dart, Android SDK y Command-line
  Tools, según el
  [setup de Android](https://docs.flutter.dev/platform-integration/android/setup).
- Un emulador/AVD Android iniciado. Las pruebas actuales se centran en el
  emulador; Chrome o Linux Desktop no cuentan para el target Android.
- Añadir el directorio `bin` del SDK de Flutter al `PATH`. Configurar la ruta
  raíz del SDK de Flutter en el plugin de Android Studio.

Si el SDK de Flutter no está instalado, instalarlo manualmente en la versión
fijada desde el enlace anterior; no hay instalación automática. Aceptar las
licencias de Android de forma interactiva cuando el doctor las solicite.

```bash
flutter doctor -v
flutter doctor --android-licenses
flutter devices
```

Revisar y aceptar las licencias pendientes de forma interactiva. Verificar que
`flutter devices` liste el emulador Android iniciado; Chrome o Linux Desktop no
cuentan. Resolver los hallazgos de Android aplicables.

### 2. Generación del scaffold (ya ejecutada)

La carpeta `app/` ya contiene el scaffold `--empty` para Android. Este paso no
forma parte del arranque normal de quien clona el repositorio; solo se repite
para regenerar la app desde cero. El comando, ejecutado una única vez desde la
raíz, fue:

```bash
flutter create --empty \
  --platforms=android \
  --project-name=boticario_ai \
  --org=com.example \
  app
```

`--empty` genera un Hello World mínimo para Android. `com.example` es un
identificador demo: el applicationId provisional es `com.example.boticario_ai`,
no una identidad real de publicación.

### 3. Abrir y ejecutar en Android Studio

Abrir `app/` como proyecto (su raíz tiene `pubspec.yaml`). Configurar la ruta
raíz del SDK de Flutter en el plugin de Flutter y elegir el emulador Android en
la selección de dispositivo. En la terminal integrada, situada en `app/`:

```bash
flutter pub get
flutter analyze
flutter build apk --debug
flutter run -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador del emulador Android en
`flutter devices`. Chrome o Linux Desktop no cuentan para el target Android.

### 4. Pruebas

La app incluye pruebas unit y de widget en `app/test/`. Desde `app/`:

```bash
flutter test
```

Para ejecutar solo el test del shell de la app:

```bash
flutter test test/app/app_test.dart
```

### 5. Smoke Android

El smoke de integración vive en `app/integration_test/app_test.dart`, usa la
dependencia `integration_test` del SDK y arranca la app real (`main()` con su
`ProviderScope`, router y tema reales). Comprueba el saludo
`Hola, Boticario AI`, `Contador: 0`, el botón `Incrementar` y que los taps suman
de a 1.

Con un emulador Android iniciado y listado por `flutter devices`, desde `app/`:

```bash
flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador del emulador. Ejemplo de la
máquina actual: serial `emulator-5554`, con el AVD `boticario_api36`. Es un smoke
de un único proceso: no reinicia el proceso del SO ni prueba la vuelta a primer
plano.

### 6. Checklist manual en dispositivo

Verificado manualmente el 2026-09-29 sobre un emulador Android **API 36** con
Android Studio **2026.1.4**. El resultado está acotado a esa pasada y a esas
versiones: no es una garantía permanente. No sustituye al smoke automatizado:

- [x] Sin conectividad (modo avión): el saludo y el contador funcionan. Con el
  modo avión activo y red por defecto `none`, la app siguió mostrando el saludo
  y el contador incrementó.
- [x] Sin inicio de sesión y sin solicitudes a servicios remotos de negocio. No
  hay login ni llamadas de red en el código del shell.
- [x] Arranque en frío del proceso: el contador vuelve a `Contador: 0`. Tras
  detener el proceso y relanzar, el contador volvió a 0 en un proceso nuevo.
- [x] Enviar la app a segundo plano y volver a primer plano: conserva el valor.
  Al volver desde el lanzador se conservaron el contador y la misma instancia.
- [x] Abrir `app/` en Android Studio: se reconoce como proyecto Flutter Android,
  con el SDK raíz detectado y el módulo Flutter inicializado.

### 7. Integración continua y comandos de calidad

El workflow [`.github/workflows/flutter.yml`](.github/workflows/flutter.yml)
está preparado para correr en push y pull request, con filtros de ruta
`app/**`, `.flutter-version` y el propio workflow. Lee el pin
[`.flutter-version`](.flutter-version) desde la raíz, instala ese SDK exacto con
una acción fijada por SHA y verifica la versión efectiva de Flutter antes de
seguir. La CLI local no consume el pin de forma automática: cada entorno debe
instalar la misma versión.

El job de CI cubre unit y widget; **no** ejecuta el smoke Android ni monta un
emulador. Los comandos de calidad, desde `app/`, son:

```bash
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test test/
```

Última verificación del bootstrap en CI: [run 36585970672](https://github.com/sebastianrodriguez1115/boticario-ai/actions/runs/36585970672),
en verde sobre el commit de implementación
`aa0fda088a0a4a1a0e0caa2205574ec17be4057c`. Ese resultado corresponde a esa
pasada concreta; no garantiza que futuras ejecuciones sigan en verde.

El siguiente incremento avanza en las funcionalidades de producto. El shell
actual (pantalla inicial, contador demo y navegación) está implementado y
cubierto por pruebas unit, de widget y smoke Android. Ver
[research Flutter](docs/research/flutter/README.md) y
[plan de trabajo](docs/research/flutter/plan-de-trabajo.md).

## Documentación

Orden de lectura sugerido: Canvas, mockups, research, plan de trabajo.

- Canvas y negocio: [índice](docs/canvas/README.md) y
  [modelo de negocio](docs/canvas/modelo-de-negocio.md).
- Mockups: [índice](docs/mockups/README.md),
  [pantallas](docs/mockups/pantallas.md) y
  [navegación](docs/mockups/navegacion.md).
- Research Flutter: [índice](docs/research/flutter/README.md),
  [fuentes](docs/research/flutter/fuentes.md) y
  [plan de trabajo](docs/research/flutter/plan-de-trabajo.md).

### Árbol de docs

```text
docs/
  canvas/              índice y modelo de negocio
  mockups/             índice, pantallas y navegación
  research/flutter/    índice, fuentes y plan de trabajo
  Canvas.png           canvas original
  mockups.png          lámina original de mockups
```

Referencias originales disponibles: [Canvas.png](docs/Canvas.png),
[mockups.png](docs/mockups.png), [Boticario AI.docx](docs/Boticario%20AI.docx),
[Boticario_AI_Reto_1.docx](docs/Boticario_AI_Reto_1.docx) y
[DADM_Reto_1.pptx](docs/DADM_Reto_1.pptx).

## Próximos pasos

1. Definir el alcance del MVP.
2. Resolver la base de contenido, sus licencias y la validación experta.
3. Tomar las decisiones técnicas pendientes.
4. Priorizar el siguiente incremento funcional del producto; la integración
   continua ya está operativa en verde y el smoke Android ya está implementado y
   ejecutado en emulador.
