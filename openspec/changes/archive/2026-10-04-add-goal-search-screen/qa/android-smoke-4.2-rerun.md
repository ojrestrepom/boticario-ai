# Android smoke 4.2 — repetición autorizada

Fecha: 2026-10-04. Documento de esta nueva pasada; no sustituye ni modifica
`android-smoke-4.2.md`, su log ni `test-plan.md` (NOT RUN anterior).

## Autorización y preparación

Autorización explícita adicional: «Sí, arráncalo y continúa», para arrancar solo
el AVD **existente** `boticario_catalog_api36` en puerto 5566. Code review ya
aprobado según orquestador; host 144/144 es evidencia previa y separada.

- Preflight read-only, 15:06:20 UTC: `lsof -nP -iTCP:5566 -iTCP:5567` sin sockets
  (exit 1); `ps` no mostró otra instancia del mismo AVD ni test concurrente.
  Se observó AVD ajeno en 5556, sin operación alguna contra él.
- Configuración existente: imagen Google APIs `android-36`, `arm64-v8a`,
  revisión 7; panel 1080×1920, densidad 480. No se instaló ni cambió el SDK/AVD.
- Arranque único, 15:06:43 UTC, PID **2863**:

```sh
ANDROID_HOME="$HOME/Library/Android/sdk" nohup "$HOME/Library/Android/sdk/emulator/emulator" \
  -avd boticario_catalog_api36 -port 5566 -no-window -no-audio -accel on \
  -gpu swiftshader_indirect -no-snapshot -no-boot-anim
```

Redirección real: log live en temporal autorizado
`/private/var/folders/1x/gxw5xrxs1x12swr4t_4wwmf00000gn/T/opencode/goal-search-4.2-rerun/emulator-live.log`,
stdin `/dev/null`, proceso independiente con `&`. No `wipe-data`, señales,
configuración persistente manual ni snapshots nuevos. `-no-snapshot` procede
del setup aprobado: arranque completo sin cargar/guardar snapshot, no borra datos.

- 15:07:02 UTC: boot 1, nombre exacto `boticario_catalog_api36`, estado `device`,
  API **36**, modelo `sdk_gphone64_arm64`, 1080×1920 a 480 dpi = **360×640 dp**
  nominales antes de insets. Sockets 5566/5567 del PID 2863 solo loopback.
- Ajustes baseline 15:07:21 UTC: font scale **1.0**, wifi **1**, mobile data **1**,
  airplane mode **0**, accessibility enabled **0**, touch exploration **0**.
  No se modificó ninguno.
- Flutter confirmado **3.47.6**, Dart **3.13.5**.

## Plan y resultado

Plan original (IDs, requisitos/capabilities, técnicas, precondiciones, pasos y
esperados): [`test-plan.md`](test-plan.md), intacto. Esta repetición reutiliza
los casos A00–A07, no declara resultados retroactivos de aquella pasada.
El comando ejecutado desde `app/` es:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test integration_test/app_test.dart -d emulator-5566
```

**4.2 PASS: 1/1 testWidgets, exit 0**, una sola ejecución, sin reintentos.
Inicio **15:07:36 UTC**, fin **15:08:21 UTC**. Gradle `assembleDebug` 14,8 s,
instalación 287 ms, test 27 s. `All tests passed!`.

Evidencia: [`evidence/android-smoke-4.2-rerun.log`](evidence/android-smoke-4.2-rerun.log),
39.169 bytes, SHA-256
`9b7aab83997489507f93e9695e00fe3a0cadb39ffc06ebe54612973f0d9e93ee`.
Incluye stdout/stderr, preflight/ajustes, métricas, hashes y snapshot completo del
diff de app con manifiesto de fuentes antes/después. Es evidencia finalizada,
no destino del log live. No contiene credenciales; filtro de URLs VM-service
aplicado antes de versionar: **0** URLs presentes/reemplazadas. No se normalizaron
otros bytes ni se retiraron warnings. Del log live solo se incluyeron versión,
startup completo y boot (12.721 ms); no las claves públicas ADB ni el resto del log.

| Caso de esta repetición | Resultado | Comprobación / evidencia |
|---|---|---|
| A00: preflight | PASS | Puertos libres, AVD existente sin instancia duplicada; identidad/API/boot confirmados |
| A01: Home / nueve controles inertes | PASS | Smoke completo: `/`, selección Inicio, mensajes individuales y ausencia de overlays previstos |
| A02: entrada y contenido P06 | PASS | Tres visitas a `/goals`; título/subtítulo y seis etiquetas exactas, un mensaje por entrada |
| A03: filas y tres pestañas P06 inertes | PASS | Seis filas tocadas en cada visita, ruta/página preservadas, sin Dialog/SnackBar; pestañas deshabilitadas, Inicio seleccionado |
| A04: tres retornos P06 | PASS | Atrás app, pop framework `handlePopRoute`, Inicio; Home y pila limpia |
| A05: contrato Home | PASS | **16 mensajes reales** en secuencia: 9 inertes + 3 Buscar + 4 Explorar; 11 mapeos, sin mensajes Home extra |
| A06: HTTP de la app | PASS | Assertion final del guard habilitado: **0 intentos de crear HttpClient**; no es contador impreso ni prueba de conectividad física |
| A07: regresión P04/P05 | PASS | Cinco identidades; normalización/búsqueda/filtros/vacíos, pasaportes, consulta/filtro/scroll y retorno de sesión preservados |

Los casos son subcomprobaciones del **único** test, no ocho tests independientes.
El paso de pop de framework no equivale a pulsar físicamente Atrás Android.
El smoke confirma presencia de las etiquetas; no declara revisión visual manual
de orden geométrico, ausencia de recortes o semántica exhaustiva de filas.

### Scroll / IME

**7 snapshots** `[CatalogSmoke metrics]` reales en stdout:

1. `P04.before-tap.stable-viewport`
2. `P05.after-navigation`
3. `P05.before-chevron-return`
4. `P04.after-return.stable-viewport`
5. `P04.before-framework-tap.stable-viewport`
6. `P05.after-framework-navigation`
7. `P04.after-return.stable-viewport`

En los siete: inset **0.0**, viewport **514.6666666666666 dp**, maxExtent y offset
**117.33333333333337 dp**, `scrollController=887693545`,
`queryController=965281999`, consulta sintética **A**. La igualdad de retorno
exacta pasó en ambas variantes. El harness cierra el IME antes de capturar esta
sesión estable; el caso de transición de insets sintéticos pertenece al contrato
host, no a esta ejecución Android. **0 traces, capturas o videos** generados por
este harness Flutter; los snapshots son métricas textuales, no Playwright traces.

### APK y warnings

APK generado e instalado: `app/build/app/outputs/flutter-apk/app-debug.apk`,
**116.878.968 bytes**, mtime UTC **2026-10-04T15:07:51Z**, SHA-256
`8bddf79a9d2456d6f2911504cb1cefe6c78bd149f0f2f49b16af7436d5020b5b`.
Es **debug del entrypoint de integración**, no certificación del APK normal
`lib/main.dart` para QA manual, ni de release/profile.

Warnings reales, sin alterar entorno para ocultarlos:
- Java/Gradle: acceso nativo restringido de `java.lang.System::load` y sugerencia
  `--enable-native-access=ALL-UNNAMED`.
- SDK processing: herramienta entiende XML hasta versión 3 y encontró versión 4.
- Resolución: cuatro paquetes tienen versiones nuevas incompatibles con los
  constraints actuales; no se actualizaron dependencias.

No hubo excepción/fallo de test ni frames de error que omitir.

## Integridad y estado final

Comparación de **58 archivos de app** tracked/untracked no ignorados:
**0 cambios**. Diff binario de app byte-idéntico antes/después, SHA-256
`573b465dfdd1e7d98519575e029c637a39c98f333614491437636cc9b080e680`.
Manifiesto SHA-256 antes/después
`4e2d3e07db7f455d66af6d0e0f3a590b13ce90d220b473374a109dec6bc3e63e`.

- `pubspec.yaml`: `903bf6a4e222ec0f2777196399c3faf3dedfaf7604b92de6df206c3ee70eabc4`.
- `pubspec.lock`: `af69c6b69b339d74946004a863954adfa14f9c30d44692e762fbade82bd02626`.
- Diff de ambas dependencias: exit **0**, sin cambios.
- Config AVD antes/después: `7a652fd694876506336ba4483e8b9a53731fee1d33deb8b3b876e816f989b355`.
- Informe NOT RUN anterior, su log y `test-plan.md` conservan exactamente sus
  hashes iniciales (incluidos en evidencia). No se reescribieron resultados.

Snapshot final **15:09:48 UTC**, identidad reconfirmada: mismos seis ajustes
baseline, panel/densidad, estado `device` y boot 1. **Nada se cambió/restauró**:
font 1.0, wifi 1, mobile data 1, airplane 0, accessibility 0, touch exploration 0.
AVD/PID **2863 permanece corriendo** para futura tarea manual. Tras terminar el
smoke `pidof com.example.boticario_ai` no devuelve proceso (exit 1): la app de
integración quedó cerrada; el último estado del flujo comprobado fue Home con
pila limpia. No se relanzó una app para fingir una pantalla manual visible.

No se editaron producto/tests/assertions, README, tasks, configuración SDK/AVD
ni evidencia histórica. No se operó contra otros dispositivos, ni se aceptaron
licencias, hizo stage/commit/push o cambió radios. Únicos artefactos nuevos de
esta repetición: este informe y su log. No se instalaron herramientas de QA;
se usaron Flutter, ADB, emulator, Python y utilidades locales existentes.

## Defectos, cobertura y reejecución

**Sin defectos reproducidos** en el alcance automatizado. Bloqueo previo
resuelto por arranque explícitamente autorizado, no por cambio de producto.
QA manual **4.3 NOT RUN**, pendiente de revisión de esta entrega y encargo
adicional: visual 100%/200%, recortes/orden geométrico, zonas seguras, áreas
táctiles y accesibilidad manual. TalkBack **NOT RUN**; tampoco offline físico,
release/profile, otros dispositivos ni lectura exhaustiva de contenido médico.
No se trasladan resultados host/históricos a esas coberturas.

Para reejecutar: verificar nuevamente nombre exacto, estado y API 36 del único
serial con los comandos del informe anterior, registrar ajustes baseline y
ejecutar el comando Flutter de arriba desde `app/`. Capturar en temporal,
filtrar tokens, guardar evidencia **nueva** sin sobrescribir esta pasada y
comparar ajustes/hashes después. No necesita arrancar otro AVD ni apagar este.
