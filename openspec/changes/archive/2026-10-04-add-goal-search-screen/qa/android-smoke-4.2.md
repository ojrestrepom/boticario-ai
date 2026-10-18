# Android smoke 4.2 — NOT RUN

Fecha: 2026-10-04. Autorización y code review aprobados según delegación del
orquestador. Único destino permitido: `emulator-5566`, AVD
`boticario_catalog_api36`. No se ejecutó la tarea manual 4.3.

## Resultado y evidencia

**Bloqueo de entorno, no defecto de producto:** el preflight obtuvo
`error: could not connect to TCP port 5566: Connection refused` al consultar
la identidad y `error: device 'emulator-5566' not found` al consultar estado.
Modelo, API, tamaño y densidad tampoco pudieron leerse. Se detuvo la ejecución
sin iniciar/recrear emuladores ni consultar o usar otro dispositivo.

- Evidencia real del preflight: [`evidence/android-smoke-4.2.log`](evidence/android-smoke-4.2.log), shell exit **1**.
- Comando Flutter: **no ejecutado**; exit N/A, **0 pruebas ejecutadas**,
  0 pasadas/0 falladas. El entrypoint contiene 1 `testWidgets` planificado.
- Plan y resultados por caso: [`test-plan.md`](test-plan.md): A00 PASS solo
  de la política de bloqueo; A01–A07 **NOT RUN**. No hay PASS de smoke Android.
- HTTP guard y secuencia Home no observados. El código del smoke exige
  **16** mensajes (9 inertes + 3 Buscar por objetivo + 4 Explorar), cubriendo
  los 11 mapeos normativos; esto es lectura del oráculo, no logs del dispositivo.
- No hubo build/install ni APK generado por esta pasada: hash APK N/A.
  No hubo warnings de Flutter: Flutter no se inició.

La evidencia se conservó primero como transcripción de stdout/stderr real en
temporal autorizado y luego se aplicó filtro de URLs VM-service antes de copiar
al log versionable. No apareció ninguna URL/token que redactar. No se afirma que
sea un log Flutter; las horas individuales del preflight no fueron capturadas.
Referencia posterior de ensamblado: `2026-10-04T14:41:00Z` (`date -u`).

## Integridad y estado final

No se editaron código, assertions, dependencias, README, tareas ni archivos
históricos; no hubo stage/commit/push. El diff de producto se leyó, no se corrigió.
Antes de generar los informes se registró SHA-256 del diff binario de `app/`:
`573b465dfdd1e7d98519575e029c637a39c98f333614491437636cc9b080e680`.
SHA-256 de archivos (comparación final registrada en el log):

- `app/lib/features/goal_search/presentation/goal_search_page.dart`:
  `85c4ab1f247115939affd12ddd30f1b1120d6a1de370d53826b49fe6fd865268`.
- `app/pubspec.yaml`:
  `903bf6a4e222ec0f2777196399c3faf3dedfaf7604b92de6df206c3ee70eabc4`.
- `app/pubspec.lock`:
  `af69c6b69b339d74946004a863954adfa14f9c30d44692e762fbade82bd02626`.

El archivo histórico `archive/2026-10-03-build-local-plant-catalog/qa/evidence/android-emulator-setup.log`
ya estaba modificado al inicio y no se tocó. README/tareas pueden variar por el
worker paralelo; no son modificaciones de esta QA.

Font scale, wifi, datos móviles y accesibilidad: **no leídos**, al no estar
disponible el destino; no se cambiaron. Snapshot posterior no obtenible; no
se afirma restauración/verificación de sus valores. Estado final de app/AVD
**desconocido/no accesible**, no iniciado ni modificado por esta pasada.

## Cobertura y riesgos

No se pudo validar ejecución nativa, regresiones P06/P04/P05, HTTP de app ni
logs en Android. No hay defecto reproducido de implementación; la limitación
es disponibilidad del AVD. Los **144/144 host** y el contrato compartido **2/2**
son evidencia previa de [`host-verification.md`](host-verification.md), no
ejecuciones de este agente ni sustituyen Android. QA visual 100%/200%, zonas
seguras, accesibilidad manual/TalkBack, offline físico y binarios release/profile
**NOT RUN**. Sin radios modificados; el guard automatizado solo cubriría HTTP
de la aplicación y no comprobaría offline real.

## Reejecución

Cuando el orquestador confirme nuevamente disponible el AVD autorizado (esta QA
no lo arranca), comprobar exclusivamente:

```sh
ADB="$HOME/Library/Android/sdk/platform-tools/adb"
"$ADB" -s emulator-5566 emu avd name   # debe ser boticario_catalog_api36
"$ADB" -s emulator-5566 get-state     # debe ser device
"$ADB" -s emulator-5566 shell getprop ro.build.version.sdk  # debe ser 36
"$ADB" -s emulator-5566 shell getprop ro.product.model
"$ADB" -s emulator-5566 shell wm size
"$ADB" -s emulator-5566 shell wm density
"$ADB" -s emulator-5566 shell settings get system font_scale
```

Detener si falla identidad/estado/API. Sin cambiar radios ni otros dispositivos,
desde `app/` ejecutar solo después del preflight confirmado:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test integration_test/app_test.dart -d emulator-5566
```

Capturar salida en temporal autorizado, exit/hora real, filtrar URLs/tokens
antes de guardar evidencia nueva sin sobrescribir esta pasada, y registrar
ajustes pre/post. No se instaló herramienta alguna; solo ADB existente y
comandos de lectura local. Playwright/Postman no aplican a este entorno nativo.
