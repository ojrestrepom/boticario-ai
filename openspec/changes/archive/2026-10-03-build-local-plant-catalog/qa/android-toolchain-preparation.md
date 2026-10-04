# Preparación de toolchain Android (diagnóstico e instalación de herramientas)

Fecha: 2026-10-03 UTC. No se compiló ni instaló la app, no se ejecutó smoke y no se inició una aceptación interactiva de licencias.

## Resultado

- Antes de la acción, Flutter 3.47.6/Dart 3.13.5 detectaba Android SDK 36.0.0, pero informaba que faltaba `cmdline-tools` y que el estado de licencias era desconocido.
- Se instaló únicamente Android SDK Command-line Tools ARM64 para macOS, revisión 23.0, en `$HOME/Library/Android/sdk/cmdline-tools/latest`. Se confirmó que el directorio no existía antes; no se sobrescribieron componentes existentes.
- Fuente oficial: índice Google `https://dl.google.com/android/repository/repository2-3.xml`; archivo `https://dl.google.com/android/repository/commandlinetools-mac_arm64-16111833_latest.zip`. Metadata del índice: tamaño 155,384,151 bytes, SHA-1 `ad03dc49bfacfd52c110b14104ea548b8a07e830`. Descarga: tamaño y SHA-1 coincidieron antes de extraer. `source.properties` reporta `Pkg.Revision=23.0`.
- Posterior a la instalación, `sdkmanager --version` respondió `1.0.16500706 (Android CLI)` y `flutter doctor -v` reportó Android toolchain `[✓]`, API/SDK Android 36.0.0 y “All Android licenses accepted.” El archivo local `licenses/android-sdk-license` ya existía antes y conserva SHA-256 `c43fa37686457c3f18caa3607945f4ec52a9d1beaaad8117e50dc4e863270c85`. No se ejecutó `flutter doctor --android-licenses`, `sdkmanager --licenses` ni ninguna aceptación. Por tanto, aceptación/estado observado corresponde al estado preexistente reconocido por Flutter una vez disponible cmdline-tools; no hubo una aceptación en esta tarea.
- ADB confirmó conectado/autorizado el Samsung `SM_G998B`, serial `R5CR70M9GEE`, Android 15/API 35. `flutter devices` también lista macOS y Chrome; no son target del smoke.
- Requisitos de app leídos sin compilar: `app/android/app/build.gradle.kts` toma `compileSdk`, `targetSdk`, `minSdk` y `ndkVersion` del Flutter plugin. En Flutter fijado, esos valores son compile/target API 36, min API 24 y NDK `28.2.13676358`. SDK manager lista ya instalados Android platform 36 (también 37), build-tools 36.0.0 y NDK 28.2.13676358; no se instaló ninguno de ellos. La revisión AGP del proyecto es 9.1.0; Gradle wrapper es 9.3.1. No se ejecutó Gradle/build ni se verificó compatibilidad de build en esta tarea.
- `flutter doctor` sigue reportando hallazgos iOS/Xcode/CocoaPods, fuera del alcance Android.

## Evidencia de comandos

La transcripción fechada, con versiones Flutter/Dart, `adb devices -l`, versión/listado sdkmanager y `flutter doctor -v`, está en [evidence/android-toolchain-preparation.log](evidence/android-toolchain-preparation.log). El ZIP de instalación y el XML consultado quedaron en el directorio temporal autorizado `/private/var/folders/1x/gxw5xrxs1x12swr4t_4wwmf00000gn/T/opencode/android-toolchain`, fuera del repo.

## Límite / próximo paso autorizado

Doctor Android y dispositivo están listos; **QA Android no está aprobada** y el smoke sigue pendiente. En esta entrega no se ejecutó el smoke; ya existía autorización explícita de la persona usuaria para instalar y probar la app, y la revisión del smoke era una dependencia previa que ya se completó. Aunque Doctor informa las licencias aceptadas, si una operación futura informa licencias pendientes, la persona usuaria debe revisarlas/aceptarlas interactivamente con `flutter doctor --android-licenses` desde la terminal; no usar aceptación automatizada. No se afirma aquí que el smoke Android haya pasado.
