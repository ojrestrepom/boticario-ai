# Preparación del emulador Android para QA

Fecha: 2026-10-03 (UTC). Preparación de entorno solamente: no se compiló,
instaló ni abrió la app y no se ejecutó el smoke.

## Resultado

- AVD configurado `boticario_catalog_api36`; identidad final confirmada por
  `adb -s emulator-5566 emu avd name`, PID QEMU 28376. El AVD ajeno
  `DADM_GraphicsSound_API35` no fue configurado ni borrado. Sí hubo una
  interrupción accidental descrita abajo: no afirmo que el setup inicial
  preservara intacto ese emulador.
- Imagen efectiva: `system-images;android-36;google_apis;arm64-v8a`, revisión
  7 (`AndroidVersion.ApiLevel=36`, extensión 17, ABI arm64-v8a), de Google;
  `PlayStore.enabled=no`. SDK Manager oficial reportó el archivo
  `https://dl.google.com/android/repository/sys-img/google_apis/arm64-v8a-36_r07.zip`.
  Instalación: 4.3 GB. La imagen AOSP `default` API 36, revisión 2 (1.9 GB),
  también se instaló inicialmente desde el URL oficial que reportó SDK Manager,
  y se conservó sin borrarla. El primer log de lectura consultó
  `emulator-5554` y obtuvo API 35 con 1080×2400/420 dpi, pero la identidad de ese
  serial no se había comprobado. La evidencia posterior lo asocia con
  `DADM_GraphicsSound_API35`; esos datos **no demuestran** qué API arrancó la
  imagen AOSP y retiro la atribución previa de API 35 a esa imagen. Se eligió
  Google APIs, que sí arrancó como Android 16/API 36. No se añadió Play Store.
- SDK Manager `1.0.16500706 (Android CLI)`; Flutter 3.47.6/Dart 3.13.5; SDK
  Android local sin actualizar. Flutter Doctor marca Android toolchain ✓.
- Las licencias estaban aceptadas antes de esta acción. No se corrió ningún
  comando de aceptación; el archivo existente
  `licenses/android-sdk-license` conserva SHA-256
  `c43fa37686457c3f18caa3607945f4ec52a9d1beaaad8117e50dc4e863270c85`.
- Aceleración de CPU: Hypervisor.Framework de macOS (`emulator -accel-check` ✓).
  Renderizado: SwiftShader por software (`-gpu swiftshader_indirect`), necesario
  tras un crash del backend gráfico automático del emulador. Se inició headless
  (`-no-window`) para evitar el diálogo de crash; el AVD permanece accesible por
  ADB/Flutter. Los sockets escuchantes del proceso se comprobaron ligados a
  loopback (`127.0.0.1`/`::1`), sin exponer servicios a la red externa.
- Serial dedicado activo `emulator-5566`, `sys.boot_completed=1`, Android 16 / SDK 36,
  ABI `arm64-v8a`. Flutter `devices` lo detecta como emulador Android.
- Panel configurado y observado: 1080×1920 px a 480 dpi = 360×640 dp nominales
  (1080×160/480 y 1920×160/480). Retrato; perfil Pixel 7; teclado físico
  desactivado, teclado software normal. Los 360×640 dp son el panel completo,
  antes de insets de barras del sistema; el área útil de la app será menor según
  sus safe areas. No se usó `wm` para alterar el dispositivo.

Durante el intento inicial se observó un proceso externo de instrumentación ADB
que apuntaba a `emulator-5554`. No lo inicié ni inspeccioné su app; luego envié
por error `adb -s emulator-5554 emu kill` sin comprobar el nombre del AVD. La
asociación posterior de ese serial con `DADM_GraphicsSound_API35` se detalla
abajo. El serial es global; el actual AVD usa `emulator-5566` para evitar esa
colisión. Antes de un smoke futuro, volver a revisar que no haya QA concurrente.

El log de instalación, arranques y verificaciones (con redacciones y esta
corrección de identidad/contexto; no es una transcripción íntegra sin editar)
está en
[`evidence/android-emulator-setup.log`](evidence/android-emulator-setup.log).
Incluye intentos de arranque con identidad de serial no confirmada, un crash del
backend gráfico automático y el arranque final correcto; las esperas de
readiness fueron acotadas. No se instaló APK ni se hizo smoke; el entorno no
equivale a aprobación QA.

## Corrección de aislamiento y comandos de parada

El primer arranque del AVD propio sin puerto fijo registró el PID 22959 y gRPC
8556. Después seleccioné el primer serial `emulator-*` de `adb devices` sin
comprobar su nombre; consulté **ese serial**, `emulator-5554`, y leí API 35 con
1080×2400/420 dpi. La revisión posterior asocia el proceso que atendía ese serial
con el AVD ajeno `DADM_GraphicsSound_API35` (PID observado 22131), no con el PID
22959. Por ello, esos datos de API 35 no describían de forma confirmada el
arranque propio.

En ese contexto ejecuté `adb -s emulator-5554 emu kill`, sin comprobación de
identidad previa. Interrumpí por error el AVD ajeno que estaba mapeado a ese
serial. Fue un cierre de consola; no mandé `-wipe-data`, no borré ni reconfiguré
su AVD y no ejecuté `adb kill-server`. No intenté reiniciarlo ni ocultar la
interrupción. No envié una señal directa a PID 22959; no establecí a partir de
estos logs cómo terminó ese proceso. Más tarde se observó un proceso
`DADM_GraphicsSound_API35` PID 28035 en el puerto 5556; no lo inicié ni modifiqué.
No puedo atribuir aquí quién lo arrancó.

Para distinguirlo, también registré las acciones contra **mi** AVD: el proceso
QEMU 25801 era `boticario_catalog_api36` (Google APIs, GPU `auto`); le envié
`kill -TERM 25801`, comprobé que seguía activo y luego `kill -INT 25801`, que lo
cerró para reintentar con SwiftShader. Después, ya verificando que
`emulator-5554` correspondía a `boticario_catalog_api36`, envié una segunda
`adb -s emulator-5554 emu kill` para moverlo al puerto dedicado. Esa segunda
acción sí apuntó al AVD propio.

Antes de cambiar al puerto dedicado se comprobó que PID 27394 y el serial
`emulator-5554` eran `boticario_catalog_api36`, y que no había proceso concurrente
Flutter/ADB instrument apuntando a ese AVD. Se cerró únicamente con
`adb -s emulator-5554 emu kill`; luego se arrancó como serial `emulator-5566`.
La comprobación final volvió a confirmar el nombre del AVD, PID 28376, arranque
completo y sockets loopback. En la comprobación de proceso previa al cambio de
puerto no se encontró un comando Flutter ni `adb shell am instrument` concurrente.
Se observó otro AVD en `emulator-5556`; no se operó sobre él.

## Uso futuro

Desde la raíz del repo, para arrancar en un proceso independiente con log:

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
nohup "$ANDROID_HOME/emulator/emulator" \
  -avd boticario_catalog_api36 -port 5566 -no-window -accel on \
  -gpu swiftshader_indirect -no-snapshot -no-boot-anim \
  >> openspec/changes/build-local-plant-catalog/qa/evidence/android-emulator-setup.log 2>&1 \
  </dev/null &
```

Usar solo el serial dedicado `emulator-5566`. Antes de cada operación ADB de
estado, confirmar `adb -s emulator-5566 emu avd name` devuelve
`boticario_catalog_api36`; esperar `sys.boot_completed=1` con
`adb -s emulator-5566 shell getprop sys.boot_completed`. No usar `adb -e`.
Para apagar **solo este** AVD, verificar primero el nombre y ejecutar
`adb -s emulator-5566 emu kill` (nunca `adb kill-server`).

Comando de smoke pendiente, desde `app/` una vez aprobado/planificado:

```bash
flutter test integration_test/app_test.dart -d emulator-5566
```

No se ejecutó aquí. El proceso dedicado del emulador quedó corriendo al terminar.
