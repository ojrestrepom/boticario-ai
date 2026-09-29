# Design

## Context

El repositorio no tiene código de aplicación; solo docs de negocio, mockups y
research Flutter provisional. La motivación está en
[proposal.md](proposal.md) y los requisitos en
[spec.md](specs/flutter-app-bootstrap/spec.md). Este documento no los repite:
decide el *cómo*.

Restricciones que condicionan el enfoque:

- Canal inicial Android únicamente; iOS no entra.
- El toolchain (`flutter`/`dart`) no estaba en `PATH`, único hecho comprobado:
  no se validó si existe SDK, dispositivo o emulador fuera de `PATH`, así que
  no se asume ninguna de las dos cosas.
- No se autorizan instalaciones silenciosas ni aceptación automática de
  licencias.
- El repo debe preservar su documentación raíz y su `.gitignore` existente.

## Goals / Non-Goals

**Goals:**

- Estructura de app mínima y testeable que valide toolchain, ruta inicial y
  estado demo, con un patrón de Riverpod y go_router listo para crecer.
- Un pin de SDK Flutter exacto y reproducible entre local y CI, sin depender de
  un canal móvil ("latest").
- Señales de verificación repetibles: unit, widget y un smoke Android.

**Non-Goals:**

- No estructura de producto: sin repositorios, servicios, backend, DB, IA,
  cámara, login, pagos ni persistencia.
- No monorepo multi-paquete.
- No diseño pixel-perfect ni assets; los mockups no son especificación.
- No navegación adicional "de relleno" para justificar el router.
- No release, ni firma de distribución/publicación, ni Play, ni iOS. La firma
  debug que genera el toolchain para ejecutar en dispositivo no se prohíbe.
- No FVM obligatorio en el arranque, no codegen de estado.
- No ejecutar el smoke Android dentro del job de CI de unit/widget ni montar
  un emulador pesado en el primer hito.

## Decisions

### 1. Una sola app en `app/`

Se crea la app en `app/` (con `pubspec.yaml` en esa raíz) para preservar los
documentos de la raíz. Alternativa descartada: la raíz como proyecto Flutter,
que mezclaría tooling con docs y planificación.

### 2. Estructura de carpetas y bootstrap

- `lib/main.dart`: `runApp` con `ProviderScope`.
- `lib/app/app.dart`, `lib/app/router.dart`, `lib/app/theme.dart`.
- `lib/features/home/presentation/home_page.dart` y `home_controller.dart`.
- `test/` con unit del controller y widget de la app.
- `integration_test/app_test.dart` para el smoke Android.

Es feature-first mínimo, coherente con el research ([F01](../../../docs/research/flutter/fuentes.md#f01)),
sin capas vacías. Alternativa descartada: carpetas `repositories/`/`services/`
sin uso.

### 3. UI de la pantalla inicial

La home muestra el saludo exacto `Hola, Boticario AI`, el texto `Contador: N`
desde 0 y un botón `Incrementar` que suma 1. Se usa Material 3 con un
`ColorScheme` baseline verde y tokens del tema, sin assets ni diseño
pixel-perfect. Los escenarios normativos están en
[spec.md](specs/flutter-app-bootstrap/spec.md); aquí solo se fija el enfoque de
UI.

### 4. Estado con Riverpod moderno

`Notifier<int>` + `NotifierProvider` síncrono, sin codegen ni `StateProvider`
legacy ni `GetIt`. Los unit tests crean su propio `ProviderContainer` y lo
liberan con `dispose`; los widget tests usan `ProviderScope`, que Flutter
libera al desmontar el árbol. Alternativas descartadas: `StateProvider`
(desaconsejado por la dirección de Riverpod), Bloc (mayor ceremonia para un
contador), mezclar DI adicional.

### 5. Ciclo de vida del router con go_router

El router vive en un provider propio de Riverpod que registra `router.dispose`
al descartarse el provider; la app lo consume y usa `MaterialApp.router` con su
`routerConfig`. Una instancia de router por scope de app/test y una sola ruta
`/`, sin redirects, auth ni deep links. Alternativa descartada: `Navigator` 1.0
con rutas ficticias. Se acepta el "peso" del router porque el usuario aprobó
go_router y es la dirección de navegación del producto.

### 6. Versión de SDK fijada

Fuente autoritativa
[releases_linux.json](https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json)
(`current_release.stable`), no pies de página ni master: Flutter **3.47.5**
stable (hash `6a19cca56475dbfba1478ee68d7bd0c2ef891da1`), Dart **3.13.4**,
release 2026-09-18. Es el valor exacto de este cambio; debe validarse al
ejecutarlo en apply, no es una afirmación de vigencia perpetua.

### 7. Pinning: `.flutter-version` en la raíz

Se usa un archivo de texto raíz `.flutter-version` con el único valor exacto
`3.47.5` como fuente del SDK de proyecto. La CI lee ese pin, aprovisiona el SDK
exacto y **verifica la versión efectiva de Flutter** instalada; `pub get`
valida las constraints. La documentación local indica el mismo SDK para Android
Studio. Aclaración clave: la CLI de Flutter **no** consume `.flutter-version`
de forma automática; el pin es declarativo y solo es efectivo por la
verificación real en CI y la disciplina documentada. `environment.sdk` de
`pubspec.yaml` constriñe **Dart**, no se compara en igualdad con la versión de
Flutter. Alternativa considerada y descartada por ahora: FVM (`.fvmrc`), que
gestiona múltiples SDKs pero añade una dependencia de arranque no justificada.

### 8. Dependencias candidatas

- `flutter_riverpod` `^3.4.3`
  ([endpoint de versión](https://pub.dev/api/packages/flutter_riverpod/versions/3.4.3)).
- `go_router` `^18.0.2`
  ([endpoint de versión](https://pub.dev/api/packages/go_router/versions/18.0.2)).

Compatibilidad declarada por las fuentes: ambas exigen Dart `^3.12.0`, y
Riverpod Flutter `>=3.0.0` / go_router `>=3.44.0` de Flutter, satisfechos por
3.47.5. Esto es lo que declaran los paquetes, no una prueba ejecutada: no se
corrió `pub get`, ni se probaron transitivos ni build. Si aparece una
incompatibilidad transitiva, no se resuelve subiendo majors o cambiando el SDK
en silencio: se detiene y se revisa y versiona la elección con validación. Se
versiona `app/pubspec.lock` al implementar y la CI usa resolución *enforced*;
las actualizaciones son deliberadas. No se añaden `http`, `Dio`, `Drift` ni
otras dependencias sin requisito.

### 9. Estrategia de pruebas

`flutter create --empty` incluye `flutter_test`/`flutter_lints` y
`analysis_options`, pero **no** genera `test/`; las pruebas se crean explícitas
antes de `flutter test`. Cobertura de este hito:

- Unit: estado inicial 0, incremento N, aislamiento entre containers.
- Widget: saludo exacto, ruta inicial, contador y botón.
- Adaptabilidad: `textScale 200%` en viewport 360x640 dp sin overflow.
- Smoke Android (`integration_test/app_test.dart`): saludo, estado inicial 0 e
  interacción de taps.

El smoke se implementa con la dependencia dev `integration_test` del SDK y se
ejecuta en Android local/emulador, separado del job de CI de unit/widget.
Comprobar el funcionamiento offline y el arranque frío de proceso se hace con
un checklist manual explícito en dispositivo: reiniciar el estado de providers
en test no prueba un reinicio real del proceso del SO. No se exige reset al
restaurar o volver a primer plano: el arranque frío o una instancia nueva
vuelven a 0, mientras que reanudar una instancia viva conserva su estado. Salvo
el bootstrap, que crea la app desde la raíz del repo con destino `app/`, los
comandos futuros (`pub get`, analyze, test, run) se ejecutan con cwd `app/`; el
comando de smoke previsto es
`flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO`.

### 10. CI básica

`.github/workflows/flutter.yml`: lee `.flutter-version` desde la raíz, opera en
`app/`, aprovisiona el SDK exacto y verifica la versión efectiva de Flutter,
aplica deps con lockfile *enforced* y corre format, analyze, unit y widget.
Falla ante cualquier comando con salida distinta de cero y corre en push/PR
pertinentes. El smoke Android se trata aparte, con emulador o teléfono
disponible; no se monta un emulador pesado en CI en este primer hito. Como
política concreta, las acciones de CI se fijan a revisiones inmutables
verificadas al escribir el workflow.

### 11. Android Studio y `.gitignore`

Se abre `app/` como proyecto, con configuración manual de SDK y plugins y
namespace/applicationId demo `com.example.boticario_ai`. No se commitean rutas
absolutas del IDE. El `.gitignore` existente se preserva (incluido
`.opencode/`); solo se harán ajustes mínimos para artefactos reales del
scaffold.

### 12. Prerequisito de apply

Como `flutter`/`dart` no estaban en `PATH`, apply requiere ubicar el SDK o, si
de verdad falta, aprovisionarlo con autorización separada del usuario, sin
instalaciones de SO silenciosas ni aceptación automática de licencias. No se
asume que haya que instalar siempre. Si faltan SDK o dispositivo Android, los
checks quedan pendientes y se reportan; eso no bloquea esta planificación.

## Risks / Trade-offs

- Versiones de dependencias no probadas (sin `pub get`/build) → validar en
  apply; ante incompatibilidad transitiva, detener y revisar/versionar la
  elección, sin subir majors ni cambiar el SDK en silencio.
- Pin declarativo que la CLI ignora → la CI lee `.flutter-version`, aprovisiona
  el SDK exacto y verifica la versión efectiva; `environment.sdk` de pubspec
  solo constriñe Dart y no se compara con la versión de Flutter.
- Smoke Android dependiente de emulador o dispositivo → separarlo del job de
  unit/widget y, si no hay dispositivo, reportar el check como no ejecutado.
- go_router con una sola ruta puede parecer sobre-ingeniería → justificado por
  dirección aprobada; se evita ampliar rutas solo por "usar" el router.
- Accesibilidad y umbrales visuales son criterios, no mediciones → no declarar
  cumplimiento sin ejecutar en apply.
- `--empty` no genera `test/` → crear pruebas explícitas; no asumir cobertura.
- Entorno sin SDK o dispositivo confirmado → el resultado de apply puede quedar
  parcial; mitigado reportando los checks no ejecutados en lugar de declarar
  completitud.

## Migration Plan

No hay app previa: la "migración" es el arranque del scaffold.

1. Apply: verificar toolchain y fijar `.flutter-version` en la raíz antes del
   scaffold; desde la raíz, `flutter create --empty` con destino `app/`,
   implementar estructura/deps/tests en `app/` y CI/README en la raíz.
2. Despliegue: solo debug local; sin release ni Play.
3. Rollback: revertir los artefactos específicos de este hito (código de
   `app/`, metadatos de SDK/CI) sin borrar cambios ajenos. La planificación es
   reversible y no toca el historial de `docs/`.

## Referencias

- SDK Flutter: [manifest de releases Linux](https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json).
- Estado/DI: [flutter_riverpod 3.4.3](https://pub.dev/api/packages/flutter_riverpod/versions/3.4.3).
- Navegación: [go_router 18.0.2](https://pub.dev/api/packages/go_router/versions/18.0.2).
- Research del repo: [fuentes.md](../../../docs/research/flutter/fuentes.md).
