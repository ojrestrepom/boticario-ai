# Boticario AI

Aplicación móvil para explorar plantas y aceites esenciales, consultar
información especializada y recibir orientación asistida por IA.

## Estado actual

Proyecto en desarrollo con Flutter. La base de la app Android ya existe en
`app/`: scaffold `--empty` para Android, SDK fijado en
[`.flutter-version`](.flutter-version), dependencias `flutter_riverpod` y
`go_router` resueltas en `app/pubspec.lock`.

Los recorridos integrados actuales son `/` → `/explore` → `/explore/:plantId`
y `/` → `/goals`: Inicio (P03) abre Explorar (P04), cada planta abre su
Pasaporte (P05), y Buscar por objetivo abre P06. Atrás desde P05 conserva
consulta, filtro y posición de P04; Atrás de app/sistema desde P06 y las rutas
de Inicio regresan a `/`, limpiando la pila al usar Inicio. Inicio conserva
cabecera con icono de menú a la
izquierda, hojas y marca `Boticario AI` al centro, icono de persona a la
derecha; banner
`Pequeñas esencias, grandes posibilidades`; cuadrícula 2x2 con `Explorar plantas
y aceites`, `Buscar por objetivo`, `Identificar con cámara` y `Formular mezclas`;
CTA `Preguntar al Boticario`; y barra inferior con `Inicio`, `Favoritos`,
`Historial` y `Perfil`, con `Inicio` siempre seleccionado.

P06 muestra `¿Qué deseas lograr?`, `Selecciona un objetivo principal` y seis
categorías: `Relajación / Estrés`, `Mejorar el sueño`, `Cuidado de la piel`,
`Alivio respiratorio`, `Concentración` y `Otros objetivos`. Es una pantalla
visual: sus filas no seleccionan ni producen acciones, y no hay búsqueda,
resultados, plantas asociadas ni P07. Las recomendaciones siguen sin estar
implementadas. Los 11 controles de Inicio (2 de cabecera, 4 tarjetas, 1 CTA y 4
pestañas) invocan su callback y, bajo `kDebugMode`, emiten exactamente un mensaje
`[Home]` por activación. `Explorar plantas y aceites` y `Buscar por objetivo`
navegan incluso fuera de debug; las otras nueve acciones son inertes. El mapeo normativo vive en
[`app/lib/features/home/presentation/home_action.dart`](app/lib/features/home/presentation/home_action.dart).
No hay mensajes por render/rebuild ni logs de consultas de usuario. Las pruebas
host no constituyen verificación de un binario profile/release.
No hay backend, API de negocio, cámara funcional, permisos, persistencia de
usuario, login ni chat real. El catálogo offline contiene cinco plantas:
Lavanda, Eucalipto, Romero, Manzanilla y Menta. Sus nombres españoles son
editoriales; los científicos se conservan literalmente del snapshot archivado
USDA Dr. Duke (CC0). Búsqueda local ignora mayúsculas, acentos y espacios
repetidos/exteriores y compara ambos nombres. `Todas` y `Plantas` muestran las
cinco; `Aceites` queda vacío. Favorito, formulaciones y las tres pestañas
inferiores restantes son visibles pero no funcionales. El arte es local y
provisional. No se registran consultas de búsqueda ni datos de usuario.

P05 ofrece `General`, `Propiedades` y `Usos`. Los campos sin fuente indican su
ausencia; propiedades medicinales no evaluadas se indican explícitamente. Los
usos son registros tradicionales con referencias resolubles, no consejo ni
evidencia clínica; no se ofrecen dosis, recomendaciones ni afirmaciones de
eficacia. Procedencia, selección, registros, citas y límites están en la
[guía del catálogo USDA](docs/data/usda-catalog.md).

El recorrido del catálogo dispone de pruebas unit/widget, un smoke automatizado
y QA manual en Android. La revisión funcional/visual manual a 100%/200% y
offline real en AVD, realizada el 2026-10-03 para el catálogo, está aprobada en
el alcance documentado; TalkBack no se ejecutó y esa limitación fue aceptada al
archivar, por lo que la revisión integral sigue parcial. El incremento anterior
del catálogo está archivado y sus cinco specs están sincronizadas; véase el
[registro de archivo](openspec/changes/archive/2026-10-03-build-local-plant-catalog/archival-note.md).
P06 pertenece al incremento OpenSpec `add-goal-search-screen`, archivado con
13/13 tareas completas y sus tres specs delta sincronizadas a las specs
principales. Véase su [registro de archivo](openspec/changes/archive/2026-10-04-add-goal-search-screen/archival-note.md).
Los resultados anteriores de Home/CI se conservan abajo como históricos.

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

Recomendaciones, formulaciones, chat e identificación siguen siendo conceptos,
no funcionalidades implementadas. La exploración local y los pasaportes
limitados descritos arriba sí están implementados.

Los datos de los mockups son ilustrativos. El contenido especializado requiere
revisión experta antes de usarse en el producto.

## Quick start

La base de la app ya existe en `app/`. Esta guía describe la preparación del
entorno, la apertura del proyecto y su ejecución en Android.

### 1. Prerrequisitos

- Flutter **3.47.6** stable, que incluye Dart **3.13.5**; no instalar Dart
  aparte. Es la versión fijada en [`.flutter-version`](.flutter-version) para
  local y CI. La CLI no lee ese archivo de forma automática: cada entorno debe
  instalar la misma versión y comprobarla. Ver
  [docs.flutter.dev/install](https://docs.flutter.dev/install).
- Android Studio con los plugins de Flutter y Dart, Android SDK y Command-line
  Tools, según el
  [setup de Android](https://docs.flutter.dev/platform-integration/android/setup).
- Un dispositivo Android OEM o emulador/AVD Android iniciado. Chrome o Linux
  Desktop no cuentan para el smoke Android.
- Añadir el directorio `bin` del SDK de Flutter al `PATH`. Configurar la ruta
  raíz del SDK de Flutter en el plugin de Android Studio.

El pin y esta guía están alineados con Flutter 3.47.6/Dart 3.13.5. Los
resultados locales fechados en secciones posteriores son evidencia histórica de
las pasadas allí descritas, no resultados de validación de esta actualización.

Si el SDK de Flutter no está instalado, instalarlo manualmente en la versión
fijada desde el enlace anterior; no hay instalación automática. Aceptar las
licencias de Android de forma interactiva cuando el doctor las solicite.

```bash
flutter doctor -v
flutter doctor --android-licenses
flutter devices
```

Revisar y aceptar las licencias pendientes de forma interactiva. Verificar que
`flutter devices` liste el dispositivo o emulador Android iniciado; Chrome o
Linux Desktop no cuentan. Resolver los hallazgos de Android aplicables.

### 2. Abrir y ejecutar en Android Studio

Abrir `app/` como proyecto (su raíz tiene `pubspec.yaml`). Configurar la ruta
raíz del SDK de Flutter en el plugin de Flutter y elegir el dispositivo o
emulador Android en la selección de dispositivo. En la terminal integrada,
situada en `app/`:

```bash
flutter pub get --enforce-lockfile
flutter analyze
flutter run -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador del dispositivo o emulador
Android mostrado por `flutter devices`. Chrome o Linux Desktop no cuentan para
el target Android.

### 3. Pruebas

La app incluye pruebas unit y de widget en `app/test/`. Desde `app/`:

```bash
flutter test test/
```

La verificación global host 5.1 ejecutada el 2026-10-03 registró **137 pruebas
de 137 pasadas** en `test/`; resultados y salidas completas en el
[informe 5.1](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/global-5.1.md).
El [informe AVD 4.3/5.2](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-emulator-smoke-4.3.md)
registra el smoke automatizado Android **aprobado: 1/1, exit 0**. Es una pasada
separada de esta verificación host. El Samsung ejecutó
build e instalación, pero **falló** el retorno de scroll antes de la corrección
revisada del harness; su causa retrospectiva no está confirmada ni ese informe
histórico se convierte en aprobado ([informe Samsung 4.3](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-smoke-4.3.md)).

Las fixtures de tipografía Roboto usadas por pruebas de layout están en
[`app/test/fixtures/fonts/`](app/test/fixtures/fonts/) y son solo para tests;
no son assets ni fuentes de la aplicación.

Para ejecutar una sola suite, desde `app/`:

```bash
flutter test test/features/home/home_action_test.dart
flutter test test/features/home/home_page_test.dart
flutter test test/app/app_test.dart
flutter test test/app/catalog_smoke_contract_test.dart
```

### 4. Smoke Android

El punto de entrada Android es `app/integration_test/app_test.dart`; delega el
flujo UI en `app/integration_test/catalog_smoke.dart`. El host
`app/test/app/catalog_smoke_contract_test.dart` ejecuta ese flujo compartido,
pero no Android. El smoke Android usa la app real y comprueba P03→P04→P05,
búsqueda/filtros/vacíos, las cinco identidades, límites P05, retorno y estado de
sesión, Inicio desde P04/P05, controles inertes y logs. Su guard `HttpClient`
cubre solo creación de clientes HTTP de la aplicación: no cambia radios ni
prueba conectividad física. El preflight host no activa ese guard.

Con un dispositivo o emulador Android iniciado y listado por `flutter devices`,
desde `app/`:

```bash
flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO
```

Sustituir `ID_DEL_DISPOSITIVO` por el identificador Android de `flutter devices`;
no se asume serial fijo. Preparar y verificar previamente el SDK Android y sus
licencias; estos comandos no cubren por sí solos toda la configuración del
entorno. Las licencias pendientes se aceptan interactivamente. El smoke Samsung
del 2026-10-03 sí ejecutó compilación e instalación Android, pero falló al
comprobar el retorno de scroll. Después, el smoke automatizado pasó 1/1 (exit 0)
en un AVD dedicado API 36; véase el
[informe Android AVD 4.3/5.2](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-emulator-smoke-4.3.md)
y el [informe histórico Samsung 4.3](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-smoke-4.3.md).
El PASS AVD no confirma retrospectivamente la causa del fallo Samsung. La QA
manual 4.5 ejecutada y sus límites, así como la revisión integral 5.3 parcial,
están en el [informe QA manual Android](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-manual-4.5.md).

### 5. Verificación local y comandos de calidad

Comandos, desde `app/`:

```bash
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test test/
```

La verificación global host de este incremento (5.1) se ejecutó el 2026-10-03:
Flutter 3.47.6 stable/Dart 3.13.5; resolución con lockfile exigido, formato sin
cambios, análisis sin issues y **137/137 pruebas pasadas**. El
[informe 5.1](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/global-5.1.md)
contiene resultados, conteos y logs completos. Es evidencia host, distinta del
smoke Android AVD aprobado 1/1; el historial Samsung conserva su resultado
FALLÓ. QA manual 4.5 tiene evidencia propia; 5.3 sigue parcial. Informes: [AVD 4.3/5.2](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-emulator-smoke-4.3.md)
y [Samsung 4.3](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-smoke-4.3.md).

### QA actual y pendiente

La verificación host de P06 ejecutada el 2026-10-04 pasó **144/144 pruebas**;
incluyó formato, análisis y contrato host compartido. El detalle y límites están
en el [informe host P06](openspec/changes/archive/2026-10-04-add-goal-search-screen/qa/host-verification.md).
El smoke Android P06 **pasó 1/1** el 2026-10-04 en el AVD autorizado; véanse el
[informe de repetición 4.2](openspec/changes/archive/2026-10-04-add-goal-search-screen/qa/android-smoke-4.2-rerun.md)
y su [log de evidencia](openspec/changes/archive/2026-10-04-add-goal-search-screen/qa/evidence/android-smoke-4.2-rerun.log).
Se observaron 16 mensajes Home, cero intentos de crear `HttpClient` de la app y
siete snapshots de métricas. Esto no prueba conectividad offline física. El
preflight NOT RUN anterior permanece en su
[informe](openspec/changes/archive/2026-10-04-add-goal-search-screen/qa/android-smoke-4.2.md); no se
sobrescribe ni se cuenta como resultado de esta pasada.

La QA visual manual P06 4.3 en el AVD autorizado pasó **10 casos, 0 fallos**;
observó textos/orden, inercia, navegación, escalas 100%/200%, zonas seguras y
targets. TalkBack, offline físico, profile/release y otros dispositivos siguen
**NOT RUN**. Véanse el [informe manual 4.3](openspec/changes/archive/2026-10-04-add-goal-search-screen/qa/android-manual-4.3.md)
y sus límites detallados; no se extrapola el resultado fuera del alcance.

La QA manual del 2026-10-03 se ejecutó en `emulator-5566`, AVD
`boticario_catalog_api36` (API 36; 360×640 dp nominales antes de insets). El
alcance funcional/visual 100%/200% y offline real del emulador pasó según las
muestras y límites consignados en el
[informe QA manual Android](openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa/android-manual-4.5.md);
no representa lectura visual exhaustiva de los 121 usos ni todos los dispositivos.
TalkBack manual no se ejecutó; la limitación fue aceptada al archivar, sin
declarar PASS de voz, foco, orden, gestos o lectura. Por tanto la revisión
integral 5.3 continúa parcial. El resultado histórico
Samsung FALLÓ y su causa sigue sin confirmar; el PASS de AVD no lo sustituye.

### Histórico: verificación manual de Home (2026-09-29)

Los checklists siguientes pertenecen únicamente al histórico `build-home-screen`
(commit `c0f02ef`), no al catálogo ni su recorrido. Se conservan como evidencia
previa y no son una comprobación nueva.

Histórico de verificación local de Home en ese commit: `flutter test test/`
pasó **58 pruebas** (26 unit y 32 widget); `dart format --output=none
--set-exit-if-changed .` no encontró archivos por cambiar; `flutter analyze` no
reportó issues y `flutter pub get --enforce-lockfile` resolvió sin cambios al
lockfile. El smoke Android pasó 1 prueba en el emulador API 36. Estos resultados
son solo de esa pasada histórica, no de este incremento.

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

### Integración continua

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

Pendiente: el repositorio se tratará como monorepo, con `app/` exclusiva de
Flutter y carpetas futuras para el backend y la ingesta de datos, que aún no
existen. Este workflow cubre solo `app/`. Cuando la arquitectura esté más
definida habrá que revisar sus filtros de ruta y añadir CI propia para los
componentes nuevos; por ahora se deja sin diseñar de forma deliberada.

Histórico de `build-home-screen`: la CI remota quedó `completed`/`success` en
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
  data/               procedencia, curación y límites del catálogo USDA
  Canvas.png           canvas original
  mockups.png          lámina original de mockups
```

Referencias originales disponibles: [Canvas.png](docs/Canvas.png),
[mockups.png](docs/mockups.png), [Boticario AI.docx](docs/Boticario%20AI.docx),
[Boticario_AI_Reto_1.docx](docs/Boticario_AI_Reto_1.docx) y
[DADM_Reto_1.pptx](docs/DADM_Reto_1.pptx).
