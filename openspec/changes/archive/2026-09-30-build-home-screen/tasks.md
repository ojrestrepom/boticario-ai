# Tasks

Rutas `lib/`, `test/` e `integration_test/` son relativas a `app/`. Los comandos
`flutter` y `dart` se ejecutan con cwd `app/`. Este desglose es solo plan: no
ejecuta código ni comandos Flutter en esta etapa.

## 1. Helper puro de acciones de Home

- [x] 1.1 Crear `lib/features/home/presentation/home_action.dart` con el enum `HomeAction` de 11 valores, el mapeo acción-mensaje exacto del delta `home-screen` (prefijos `[Home] ...`, sin IDs nuevos) y una función pura que, dada la acción y el modo permitido/no permitido, devuelva el mensaje o `null`; sin efectos ni dependencia de configuración de app, preferencias de usuario o variables de entorno; verificar con `flutter analyze` desde `app/`.
- [x] 1.2 Crear `test/features/home/home_action_test.dart` con los 11 casos en modo permitido (mensaje exacto) y en modo no permitido (`null`), determinista, incluyendo la distinción `Cabecera: Perfil` vs `Pestaña: Perfil`; aclarar en el test que no simula un binario release/profile real; ejecutar `flutter test test/features/home/home_action_test.dart` y verificar que pasa.

## 2. Estructura de la pantalla Inicio

- [x] 2.1 Reescribir `lib/features/home/presentation/home_page.dart` como `StatelessWidget` con `Scaffold` + `SafeArea` (cabecera, body y barra inferior), `body` con `SingleChildScrollView` vertical único sin scroll anidado (cabecera, banner, cuadrícula, CTA) y `bottomNavigationBar` propio; sin `ConsumerWidget`, providers ni `setState`; verificar con `flutter analyze`.
- [x] 2.2 Implementar en el mismo archivo el subwidget privado `_HomeHeader` con icono de menú a la izquierda, hojas junto a la marca exacta `Boticario AI` al centro e icono de persona a la derecha, ambos con callback; logo decorativo sin acción; verificar con `flutter analyze`.
- [x] 2.3 Implementar el subwidget privado `_BotanicalBanner` con el texto exacto `Pequeñas esencias, grandes posibilidades`, paleta provisional D5 y decoración floral/hoja local fuera de `Semantics`, sin acción asociada; verificar con `flutter analyze`.
- [x] 2.4 Implementar `_FeatureCard` y la cuadrícula con las 4 tarjetas en orden de fila `Explorar plantas y aceites`, `Buscar por objetivo`, `Identificar con cámara`, `Formular mezclas`: 2 columnas al 100% y 1 columna cuando `MediaQuery.textScalerOf(context).scale(fontSize) / fontSize >= 1.5`, con alturas naturales, sin `childAspectRatio` rígido ni elipsis; verificar con `flutter analyze`.
- [x] 2.5 Implementar el CTA de ancho completo `Preguntar al Boticario` con su callback; verificar con `flutter analyze`.
- [x] 2.6 Implementar el subwidget privado `_HomeBottomBar` (evitando `NavigationBar` por defecto si su altura fija o recorte de labels rompe el 200%) con `Inicio`, `Favoritos`, `Historial` y `Perfil`, `selectedIndex` constante 0, área de toque >= 48x48 en los 4 destinos y labels semánticos distinguibles; verificar con `flutter analyze`.
- [x] 2.7 Cablear los 11 controles a la política de depuración: invocar siempre su callback y emitir `debugPrint` exactamente una vez solo si el cálculo devuelve mensaje y `kDebugMode` es verdadero (una única llamada, sin ruta alternativa que eluda el modo); activar un control no debe mutar la UI (salvo ripple/focus), ni cambiar la ruta `/`, ni el índice seleccionado, ni abrir overlays, SnackBars, diálogos o drawers; verificar con `flutter analyze`.
- [x] 2.8 Aplicar las dimensiones y paleta provisionales D5 (padding 16, separación 12, radio 12, icono 32; `#236335`, `#172A1F`, `#F9FAF7`, `#F3F5F2`, `#D6DDD4`, `#FBF2D4`) con `TextTheme` y `MediaQuery` escalables, sin nuevos assets, paquetes ni fuentes externas; verificar con `flutter analyze`.

## 3. Retiro de contratos demo y shell

- [x] 3.1 Retirar `lib/features/home/presentation/home_controller.dart` y `test/features/home/home_controller_test.dart`, y eliminar referencias restantes en `lib/` al saludo `Hola, Boticario AI`, al contador demo y al botón `Incrementar`; verificar con `flutter analyze` que no quedan referencias colgantes.
- [x] 3.2 Comprobar que `lib/app/router.dart`, `lib/app/app.dart` y `lib/main.dart` conservan la integración actual (`ProviderScope`, `MaterialApp.router`, ruta única `/` y `router.dispose` con `ref.onDispose`) sin cambiar rutas, providers ni ciclo del router; ajustar `lib/app/theme.dart` solo si 2.8 lo exige para la paleta y la legibilidad; verificar con `flutter analyze`.

## 4. Pruebas de widget de Home

- [x] 4.1 Reescribir `test/features/home/home_page_test.dart` para verificar estructura y textos exactos: marca `Boticario AI`, frase del banner, CTA, 4 tabs y orden de fila de las 4 tarjetas, además de la ausencia de `Hola, Boticario AI`, `Contador:` e `Incrementar`; ejecutar `flutter test test/features/home/home_page_test.dart` y verificar que pasa.
- [x] 4.2 Añadir a `home_page_test.dart` las pruebas de los 11 callbacks con `debugPrint` interceptado, filtrando solo mensajes con prefijo `[Home]` y restaurando en `finally`/`tearDown`: sin pulsación durante el build = 0 mensajes, cada acción = exactamente 1 mensaje, `Cabecera: Perfil` vs `Pestaña: Perfil` distinguibles e `Inicio` ya activo emite; ejecutar el test y verificar que pasa.
- [x] 4.3 Añadir a `home_page_test.dart` las comprobaciones de no mutación y de ausencia de logs automáticos con rebuild y reassemble SIMULADOS en widget test (`pumpWidget`/`pump` y `tester.binding.reassembleApplication`), filtrando solo mensajes con prefijo `[Home]`: sin pulsación no hay mensajes, la ruta `/` no cambia, `Inicio` sigue seleccionado y no aparecen SnackBars/diálogos/drawers ni rutas nuevas. La recarga en caliente real del compilador se observa en la revisión manual 7.2; ejecutar el test y verificar que pasa.
- [x] 4.4 Añadir a `home_page_test.dart` las comprobaciones de accesibilidad: labels semánticos distinguibles (incluida la distinción cabecera Perfil vs pestaña Perfil), área de toque >= 48x48 en los 11 controles (incluidos los 4 de la barra inferior) e iconos decorativos que no duplican la lectura; ejecutar el test y verificar que pasa.
- [x] 4.5 Añadir a `home_page_test.dart` el layout 360x640 dp al 100% (2 columnas) y al 200% (`TextScaler.linear(2)`, umbral 1.5) exigiendo 1 columna, sin `flutter exception`/overflow, sin recorte ni elipsis de los textos esenciales y con labels legibles, y con `MediaQuery` de insets artificiales (notch/insets del sistema) para comprobar que `SafeArea` protege cabecera y barra inferior, garantizando que los 11 controles son alcanzables con scroll vertical; ejecutar el test y verificar que pasa.
- [x] 4.6 Adaptar `test/app/app_test.dart` al contrato de Home: router y tema reales, ruta `/`, `HomePage`, aislamiento por `ProviderScope` y ausencia de contador demo; ejecutar `flutter test test/app/app_test.dart` y verificar que pasa.

## 5. Integración y smoke Android

- [x] 5.1 Adaptar `integration_test/app_test.dart` al arranque real `main()`/Home y los controles, para emulador Android; comprobar el análisis estático con `flutter analyze` (la compilación y ejecución reales corresponden al smoke 5.2).
- [x] 5.2 Ejecutar `flutter test integration_test/app_test.dart -d ID_DEL_EMULADOR` solo con emulador Android disponible y autorización, obteniendo el serial con `flutter devices` (sin hardcodear; AVD de referencia `boticario_api36`) y sin aceptar permisos ni licencias de forma silenciosa; si no hay emulador, no marcar la validación Android y reportar el bloqueo/no ejecutado.

## 6. README

- [x] 6.1 Actualizar el README (Estado actual, Quick start, lo visible y recuento de pruebas tras validarlas) para reflejar la pantalla Inicio en `/`, sin presentar el demo como estado actual; conservar las evidencias CI/checklist del bootstrap como históricas con sus SHAs y fechas y no asumir nuevas CI en verde; no reintroducir `Próximos pasos` ni `Generación del scaffold`; verificar que los comandos documentados coinciden con los reales.
- [x] 6.2 Documentar en el README el smoke y la verificación manual (Run/Debug de Android Studio con los 11 mensajes, comparación de estructura con el mockup, insets y 200%, comportamiento offline y restauración de settings si se alteran), distinguiendo lo diseñado de lo ejecutado; no añadir capturas ni archivos al repo.

## 7. Verificación integrada y cierre

- [x] 7.1 Desde `app/` ejecutar `flutter pub get --enforce-lockfile`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test test/`, registrar resultados y no modificar workflow, dependencias ni `.flutter-version`.
- [x] 7.2 Revisión manual en Android Studio: activar Hot Reload en Run/Debug SIN pulsar controles y comprobar cero eventos `[Home]` NUEVOS; después comprobar que las pulsaciones siguen emitiendo 1 acción = 1 log, con los 11 mensajes distinguibles; comparar estructura con el mockup, insets y 200%, y validar el comportamiento offline restaurando los settings si se alteran; declarar los límites de evidencia (la prueba unitaria no equivale a un release/profile ejecutado).
- [x] 7.3 Verificación de cierre: confirmar que no hay rutas ni pantallas nuevas, SnackBars/diálogos/drawers, contador demo ni escenarios dummy, que `.gitignore` queda intacto y que no se alteran workflow, dependencias ni pin; reportar cualquier check no ejecutado sin declarar completitud.
