# Boticario AI

Aplicación móvil para explorar plantas y aceites esenciales, consultar
información especializada y recibir orientación asistida por IA.

## Estado actual

Proyecto en desarrollo con Flutter. La base de la app Android ya existe en
`app/`: scaffold `--empty` para Android, SDK fijado en
[`.flutter-version`](.flutter-version), dependencias `flutter_riverpod` y
`go_router` resueltas en `app/pubspec.lock`.

En la ruta única `/` está la estructura de la pantalla Inicio (P03), como
partida visual e interactiva: cabecera con icono de menú a la izquierda, hojas y
marca `Boticario AI` al centro, icono de persona a la derecha; banner
`Pequeñas esencias, grandes posibilidades`; cuadrícula 2x2 con `Explorar plantas
y aceites`, `Buscar por objetivo`, `Identificar con cámara` y `Formular mezclas`;
CTA `Preguntar al Boticario`; y barra inferior con `Inicio`, `Favoritos`,
`Historial` y `Perfil`, con `Inicio` siempre seleccionado.

Es solo estructura: los 11 controles (2 de cabecera, 4 tarjetas, 1 CTA y 4
pestañas) invocan su callback y, bajo `kDebugMode`, emiten exactamente un mensaje
`[Home]` por activación. El mapeo normativo vive en
[`app/lib/features/home/presentation/home_action.dart`](app/lib/features/home/presentation/home_action.dart).
No hay navegación funcional, SnackBars, diálogos, drawers ni pantallas nuevas;
tampoco backend, API, cámara, permisos, persistencia, login ni chat real. La
composición usa texto Flutter vivo, iconos y decoración Material locales, sin
assets descargados ni branding final: el arte es provisional.

La estructura está cubierta por pruebas unit y de widget, más un smoke de
integración Android que arranca la app real. El incremento tiene verificación
local (ver [Verificación local](#5-verificación-local-y-comandos-de-calidad)) y
una CI remota en verde sobre su commit de implementación (ver
[Integración continua](#7-integración-continua)).

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

Estas funcionalidades siguen siendo el concepto del canvas y de los mockups;
ninguna está implementada todavía en la app.

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

### 2. Abrir y ejecutar en Android Studio

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

### 3. Pruebas

La app incluye pruebas unit y de widget en `app/test/`. Desde `app/`:

```bash
flutter test
```

Recuento local validado: **58 pruebas**.

- 26 unit en `test/features/home/home_action_test.dart`: las 11 acciones en modo
  permitido, las 11 en modo no permitido y 4 de cobertura del enum (incluida la
  distinción `Cabecera: Perfil` vs `Pestaña: Perfil`).
- 29 widget en `test/features/home/home_page_test.dart`: estructura y textos,
  contrato de logs de las 11 acciones, no mutación y ausencia de logs
  automáticos, accesibilidad y layout 360x640 dp al 100% y 200%.
- 3 widget en `test/app/app_test.dart`: arranque en `/`, ruta inmóvil al activar
  controles y aislamiento del router por `ProviderScope`.

Para ejecutar una sola suite, desde `app/`:

```bash
flutter test test/features/home/home_action_test.dart
flutter test test/features/home/home_page_test.dart
flutter test test/app/app_test.dart
```

### 4. Smoke Android

El smoke de integración vive en `app/integration_test/app_test.dart`, usa la
dependencia `integration_test` del SDK y arranca la app real (`main()` con su
`ProviderScope`, router y tema reales). Comprueba la ruta `/`, `HomePage`, la
marca y el banner, la ausencia del contrato demo retirado, las 11 acciones (una
activación = un mensaje, sin cambios de ruta ni de pantalla y sin overlays) y
que `Inicio` queda seleccionado.

Con un emulador Android iniciado y listado por `flutter devices`, desde `app/`:

```bash
flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador devuelto por
`flutter devices`; no se asume un serial fijo. Ejemplo observado en la máquina
actual: serial `emulator-5554`, con el AVD `boticario_api36` (Android API 36).
Es un smoke de un único proceso: no reinicia el proceso del SO ni prueba la
vuelta a primer plano.

### 5. Verificación local y comandos de calidad

Comandos, desde `app/`:

```bash
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test test/
```

Resultados locales observados (pasada local de `build-home-screen`, working
tree; **no** son una ejecución de CI remota):

- `dart format --output=none --set-exit-if-changed .`: 0 archivos por cambiar.
- `flutter pub get --enforce-lockfile`: resuelve con lock sin cambios.
- `flutter analyze`: sin issues.
- `flutter test test/`: 58 pruebas en verde (26 unit y 32 widget).
- El smoke compiló e instaló un APK debug (`assembleDebug`) antes de ejecutar la
  integración, y pasó 1 prueba en el emulador Android API 36 (`boticario_api36`).

Estos resultados son locales y acotados a esta pasada. No sustituyen la revisión
manual en Run/Debug ni la ejecución de un binario release/profile.

### 6. Verificación manual

La verificación manual tiene dos partes: lo observado en el emulador por
CLI/ADB (6.1) y la observación en Run/Debug de Android Studio (6.2), confirmada
por el usuario/desarrollador.

#### 6.1 Comprobado en emulador mediante CLI/ADB

Se observó sobre el AVD `boticario_api36` (Android API 36), sin usar el IDE,
tras arrancar una vez con
`flutter run --debug --target lib/main.dart --no-resident -d emulator-5554`
(`--no-resident` deja la app viva). Evidencia del 2026-09-29: capturas locales
entre 23:20 y 23:27, sin añadir archivos al repo. Marcar cada ítem solo tras
observarlo.

- [x] Home se muestra en `/`, sin el contrato demo retirado.
- [x] Estructura visible comparada con el mockup
  ([`docs/mockups.png`](docs/mockups.png),
  [`docs/mockups/pantallas.md`](docs/mockups/pantallas.md)): cabecera, banner,
  cuadrícula y barra inferior conformes en estructura y arte provisional, sin
  recortes (el arte no busca fidelidad pixel-perfect).
- [x] Tamaño de texto del sistema al 200% (`font_scale 2.0`): la cuadrícula pasa
  a 1 columna y no hay recorte en la vista; con swipe real se llega al CTA
  completo y legible, y al pulsarlo se obtuvo exactamente un mensaje
  `[Home] Preguntar al Boticario`. Después se restauró `font_scale` a `1.0`.
- [x] Sin conectividad: con wifi y datos móviles desactivados (`Active default
  network: none`) la app siguió visible y al pulsar `Explorar plantas y aceites`
  se obtuvo exactamente un mensaje `[Home] Explorar plantas y aceites`. Después
  se restauraron wifi y datos móviles a `1`; el modo avión quedó en `0`.
- [x] Ajustes finales del emulador: `font_scale 1`, wifi `1`, datos móviles `1`,
  modo avión `0`; el AVD queda con Home abierta. No se usaron otros dispositivos
  ni se tocó el IDE.

Nota de alcance: la prueba real al 200% fue sobre el AVD observado (1080x2400 a
densidad 420, unos 411x914 dp, con el escalado de fuente del sistema), no sobre
360x640 dp reales. No se afirma igualdad exacta de densidad con el caso de
widget ni que no haga falta otro dispositivo. El caso 360x640 dp al 100% y 200%
sigue cubierto solo por widget test simulado (`TextScaler.linear(2)`), no por
observación manual en pantalla.

#### 6.2 Validado en Android Studio (Run/Debug)

La observación manual en Run/Debug del IDE fue confirmada por el
usuario/desarrollador al cerrar `build-home-screen`; el agente no observó el IDE.
Los ítems se marcan tras esa confirmación.

En Android Studio: abrir `app/` como proyecto, configurar el SDK de Flutter y
elegir el emulador Android. Usar Run/Debug sobre `lib/main.dart` dentro del
proyecto `app/` y leer los mensajes `[Home] ...` en la consola Run/Debug.

- [x] Arrancar en Debug desde el IDE: Home se muestra en `/`, sin el contrato
  demo retirado.
- [x] Activar Hot Reload real desde el IDE, sin pulsar controles: 0 mensajes
  `[Home]` nuevos en la consola.
- [x] Pulsar los 11 controles: 1 pulsación = 1 mensaje `[Home]` con el texto
  normativo (2 de cabecera, 4 tarjetas, CTA y 4 pestañas).
- [x] Activar `Favoritos`, `Historial` o `Perfil`: `Inicio` sigue seleccionado y
  la ruta `/` no cambia.

Límite de evidencia: el helper de mensajes y la política `kDebugMode` se
verifican en unit y widget, incluido el caso de modo no permitido; eso no
ejecuta un binario release/profile real, cuyo silencio es el comportamiento
normativo. La observación CLI/ADB (6.1) y la observación manual en el IDE (6.2)
son evidencias distintas, y ninguna equivale a un binario release/profile.

### 7. Integración continua

El workflow [`.github/workflows/flutter.yml`](.github/workflows/flutter.yml)
está preparado para correr en push y pull request, con filtros de ruta
`app/**`, `.flutter-version` y el propio workflow. Lee el pin
[`.flutter-version`](.flutter-version) desde la raíz, instala ese SDK exacto con
una acción fijada por SHA y verifica la versión efectiva de Flutter antes de
seguir. La CLI local no consume el pin de forma automática: cada entorno debe
instalar la misma versión.

El job de CI cubre unit y widget; **no** ejecuta el smoke Android ni monta un
emulador. Los comandos de calidad que replica son los de
[Verificación local](#5-verificación-local-y-comandos-de-calidad).

La CI remota de la pantalla Inicio quedó `completed`/`success` en
[run 36705725682](https://github.com/sebastianrodriguez1115/boticario-ai/actions/runs/36705725682),
sobre el commit de implementación `c0f02efb20e9014ddfdee4c7f1c70aa36919ef3d`. La
verificación remota del bootstrap demo queda registrada como histórica más
abajo.

## Histórico del bootstrap

Antes de la pantalla Inicio, el bootstrap `aa0fda0` (2026-09-29) entregó el
shell demo retirado:

- Saludo `Hola, Boticario AI`, contador demo con Riverpod y botón `Incrementar`
  en `/`.
- 13 pruebas unit y de widget (4 de `HomeController`, 6 de la Home demo y 3 del
  shell) más 1 smoke de integración Android.
- Checklist manual en emulador Android **API 36** con Android Studio **2026.1.4**:
  modo avión con el saludo y el contador funcionando, ausencia de login y de
  solicitudes de negocio, arranque en frío con `Contador: 0`, vuelta a primer
  plano conservando el valor y apertura de `app/` como proyecto Flutter Android.
- CI remota: [run 36585970672](https://github.com/sebastianrodriguez1115/boticario-ai/actions/runs/36585970672),
  en verde sobre el commit `aa0fda088a0a4a1a0e0caa2205574ec17be4057c`.

Ese shell, su contador y su checklist ya no describen el estado actual; se
conservan como evidencia histórica con su fecha y SHA. Ese resultado corresponde
a esa pasada concreta y no garantiza ejecuciones futuras.

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
