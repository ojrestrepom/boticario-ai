# Tasks

Rutas: `lib/`, `test/` e `integration_test/` son relativas a `app/`. Los diagnósticos previos (`flutter --version`, `dart --version`, `flutter doctor`, `flutter devices`) se ejecutan desde la raíz del repositorio o cualquier cwd existente; `flutter create` se ejecuta desde la raíz con destino `app/`. Una vez creada la app, los comandos del proyecto (`pub get`, `analyze`, `build`, `test`, `run`, `format`) se ejecutan con cwd `app/`. Los artefactos de raíz (`.flutter-version`, `.github/workflows/flutter.yml`, `README.md`) se marcan explícitamente.

## 1. Prerequisitos y fijación del SDK

- [x] 1.1 Ubicar o configurar el SDK Flutter 3.47.5 y el Android SDK; verificar que `flutter --version` reporta 3.47.5, que `dart --version` reporta 3.13.4 y que `flutter doctor -v` muestra el estado real. Si el SDK falta, pedir autorización separada al usuario para aprovisionarlo; no instalar de forma implícita ni aceptar licencias automáticamente (resolverlas de forma interactiva si están pendientes).
- [x] 1.2 Verificar con `flutter devices` que hay un dispositivo o emulador Android disponible; Chrome o desktop no cuentan. Registrar el resultado como no disponible si no lo hay, sin bloquear el trabajo unit/widget y sin dar por validado Android.
- [x] 1.3 Crear en la raíz del repositorio `.flutter-version` con el valor exacto `3.47.5`; verificar el contenido exacto del archivo y que coincide con la versión local comprobada en 1.1, sin asumir que la CLI lo lea de forma automática.
- [x] 1.4 Documentar en el README los prerequisitos y la preparación del SDK: Flutter 3.47.5 y Dart 3.13.4, Android Studio con plugins, Android SDK, aceptación interactiva de licencias, dispositivo Android y qué hacer si el SDK falta. Verificar que la versión documentada coincide con `.flutter-version` y que los enlaces resuelven.

## 2. Scaffold de la app y dependencias

- [x] 2.1 Desde la raíz del repositorio ejecutar `flutter create --empty --platforms=android --project-name=boticario_ai --org=com.example app`; verificar que existe `app/pubspec.yaml`, que se generó `app/android/` y que el applicationId es el demo `com.example.boticario_ai`, sin identidad real de publicación.
- [x] 2.2 Revisar los archivos generados y comprobar que `app/android/local.properties` (config local del SDK) y las rutas absolutas del IDE no quedan versionados, preservando el `.gitignore` raíz (incluido `.opencode/`) sin cambios de alcance.
- [x] 2.3 Declarar en `app/pubspec.yaml` `flutter_riverpod ^3.4.3` y `go_router ^18.0.2`, y `integration_test` (SDK) en `dev_dependencies` junto con `flutter_test`/`flutter_lints` del template; verificar que `flutter pub get` desde `app/` resuelve y genera `app/pubspec.lock`. Ante incompatibilidad transitiva, detener y versionar la decisión sin subir majors ni cambiar el SDK.
- [x] 2.4 Verificar desde `app/` que `flutter analyze` pasa y que `flutter build apk --debug` compila el scaffold; si falta Android SDK, registrar el check como pendiente.
- [x] 2.5 Actualizar el estado y el quickstart del README: declarar que la app ya existe en `app/`, explicar cómo abrirla en Android Studio y documentar los comandos de ejecución desde `app/` (`flutter pub get`, `flutter analyze`, `flutter run`). Verificar que el README ya no declara "no hay app" y que los comandos documentados coinciden con los reales.

## 3. Estado del contador con Riverpod

- [x] 3.1 Crear `lib/features/home/presentation/home_controller.dart` con un `Notifier<int>` y su `NotifierProvider` síncrono, sin codegen ni `StateProvider` legacy; verificar con `flutter analyze` desde `app/` que compila.
- [x] 3.2 Crear `test/features/home/home_controller_test.dart` con unit tests de estado inicial 0, incremento N y aislamiento entre dos `ProviderContainer` independientes, registrando el `dispose` de cada uno en el teardown (no crear ni liberar `ProviderScope` en un unit test puro); ejecutar `flutter test test/features/home/home_controller_test.dart` desde `app/` y verificar que pasa.

## 4. Pantalla inicial y accesibilidad

- [x] 4.1 Crear `lib/features/home/presentation/home_page.dart` con el saludo EXACTO `Hola, Boticario AI`, el texto `Contador: N` iniciando en 0 y el botón `Incrementar` que suma 1, consumiendo el provider del controller; verificar con `flutter analyze`.
- [x] 4.2 Crear `test/features/home/home_page_test.dart` con widget tests de saludo exacto, `Contador: 0`, botón visible y actualización tras un tap y tras N taps; ejecutar `flutter test test/features/home/home_page_test.dart` y verificar que pasa.
- [x] 4.3 Ampliar `test/features/home/home_page_test.dart` con accesibilidad: la semántica expone la etiqueta `Incrementar` y el valor del contador, y con textScale 200% en viewport 360x640 dp el saludo, el contador y el botón siguen visibles sin recorte; ejecutar el test y verificar que pasa.

## 5. Shell de la app: tema, router y arranque

- [x] 5.1 Crear `lib/app/theme.dart` con `ThemeData` Material 3 y `ColorScheme` base verde; verificar con `flutter analyze`.
- [x] 5.2 Crear `lib/app/router.dart` con un provider de Riverpod que construye un `GoRouter` con la única ruta `/` y registra `router.dispose` al descartarse el provider, una instancia por scope; verificar con `flutter analyze`.
- [x] 5.3 Crear `lib/app/app.dart` (`MaterialApp.router` con el `routerConfig` del provider y el tema real) y `lib/main.dart` (`runApp` con `ProviderScope`); verificar con `flutter analyze`.
- [x] 5.4 Crear `test/app/app_test.dart` con un widget test que arranca la app completa en un `ProviderScope` aislado, usando el tema y el router reales, y confirma la ruta inicial `/` y la home renderizada; ejecutar `flutter test test/app/app_test.dart` y verificar que pasa.

## 6. Smoke Android y verificación manual en dispositivo

- [x] 6.1 Crear `integration_test/app_test.dart` con la dependencia `integration_test` del SDK: verifica el arranque, `Contador: 0` y que los taps incrementan; verificar con `flutter analyze` que compila.
- [x] 6.2 Con dispositivo o emulador Android disponible, ejecutar desde `app/` `flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO` y verificar la salida en verde; si no hay dispositivo, reportar el check como no ejecutado y no marcarlo como hecho.
- [x] 6.3 Documentar en el README el comando de smoke y el checklist manual en dispositivo: offline, sin login ni solicitudes de negocio, arranque en frío vuelve a 0, volver a primer plano conserva el estado y apertura de `app/` en Android Studio; verificar que los enlaces resuelven y no exponer identificadores privados de dispositivos.
- [x] 6.4 Ejecutar el checklist manual en dispositivo y registrar el resultado de cada escenario (offline, arranque en frío, vuelta a primer plano y apertura en el IDE); no confundir el reset de providers en test con un reinicio real del proceso. Si no puede observarse, por falta de dispositivo o de GUI, dejarlo pendiente con el motivo y sin darlo por validado.

## 7. CI y comandos de calidad

- [x] 7.1 Crear `.github/workflows/flutter.yml` que lee `.flutter-version` de la raíz y comprueba la versión efectiva de Flutter (sin comparar Flutter 3.47.5 en igualdad contra `environment.sdk` de Dart), opera en `app/`, corre `flutter pub get --enforce-lockfile` (valida deps), `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test`, falla con salida distinta de cero y se dispara en push/PR; fijar las acciones a revisiones inmutables y validar la sintaxis YAML. No ejecutar commit ni push como parte de esta tarea.
- [x] 7.2 Documentar en el README los comandos de calidad (formato, analyze, unit y widget) alineados con el workflow; verificar que coinciden con los comandos reales ejecutados desde `app/`.
- [x] 7.3 Verificar que el workflow lee el pin y que la comprobación de la versión efectiva de SDK es coherente; si la CI remota no se ejecuta, reportar el resultado como pendiente explícito y no asumir verde por haber validado el YAML.

## 8. Integración transversal

- [x] 8.1 Desde `app/` ejecutar `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test`, y confirmar que todo queda en verde; reportar cualquier check no ejecutado.
- [x] 8.2 Verificación de cierre: confirmar que no hay pantallas ni rutas adicionales, que las dependencias directas de `app/pubspec.yaml` son solo las aprobadas (más Flutter SDK y dev deps del template, sin prohibir transitivas del lockfile), que `.flutter-version` y `app/pubspec.lock` existen y son versionables, y que el README ya no declara "no hay app"; reportar el estado real sin declarar completitud si el smoke o la CI remota quedan pendientes.
