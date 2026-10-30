# Design

## Context

El bootstrap Android ya arranca en `/` con `MaterialApp.router`, un
`appRouterProvider` que libera su `GoRouter` con `ref.onDispose` y una
`HomePage` que hoy muestra saludo y contador demo. El contador vive en un
`Notifier` Riverpod y está cubierto por pruebas unit, de widget, de app y de
integración. Ver `proposal.md` para la motivación.

`design.md` es necesario (no opcional) porque el cambio adapta layout y
accesibilidad al 100% y 200%, define una política de logs condicionada por
`kDebugMode` verificable, y retira contratos demo que hoy ocupan varias suites.
Esos cruces no se resuelven con el detalle de los specs de comportamiento.

Restricciones vigentes: ruta única `/`, sin paquetes, fuentes ni descargas
nuevas; arte provisional con texto vivo e iconos Material locales; mensajes solo
bajo `kDebugMode`; referencia 360x640 dp con scroll y sin recorte.

## Goals / Non-Goals

**Goals:**

- Implementar la estructura visual P03 y sus 11 controles sin funcionalidad de
  producto.
- Mantener `ProviderScope`, `MaterialApp.router`, la ruta única `/` y el
  `dispose` del router.
- Separar el cálculo puro del mensaje (acción y modo) del efecto de emisión;
  política testeable con modo permitido y no permitido.
- Cumplir 360x640 dp al 100% y 200% con áreas de toque >= 48 dp y semántica.
- Dejar lista la migración de contratos demo y la actualización de README.

**Non-Goals:**

- Navegación funcional, rutas, overlays, drawers, SnackBars, diálogos o
  pantallas nuevas.
- Auth, backend, API, cámara, permisos, persistencia o chat real.
- Arte final, tokens de marca reales, fuentes, imágenes remotas ni fidelidad
  pixel-perfect.
- `ThemeExtension`, paquetes, capas de arquitectura o canal de logs en release.
- Promover el delta a main spec o archivar el cambio en esta etapa.

## Decisions

### D1. Shell y HomePage sin estado Riverpod

- Se conservan `main.dart` (`ProviderScope`), `app.dart`
  (`MaterialApp.router`) y `router.dart` (`appRouterProvider` con `onDispose`).
- `HomePage` pasa de `ConsumerWidget` a `StatelessWidget`: no depende de estado
  ni de providers. Se retira `home_controller.dart` y su prueba unit.
- No se introducen `Notifier`, providers, controladores, servicios de logging,
  bus de eventos ni paquetes.
- Alternativas: mantener `ConsumerWidget` o un `Notifier` para el índice de
  pestañas. Se descartan porque el índice es constante 0 y no muta la UI.

### D2. Composición por widgets privados en la feature home

- `home_page.dart` define `Scaffold` + `SafeArea`, un `body` con
  `SingleChildScrollView` vertical (cabecera, banner, cuadrícula, CTA) y un
  `bottomNavigationBar` propio separado.
- Los bloques se resuelven con clases privadas simples en el mismo archivo o en
  la misma carpeta `presentation/`: `_HomeHeader`, `_BotanicalBanner`,
  `_FeatureCard`, `_HomeBottomBar`. Sin capas domain/data, sin DI, sin estado.
- Se reutilizan los textos exactos y el orden del spec `home-screen`; el diseño
  no los repite, los referencia.

### D3. Layout adaptable y barra inferior inmóvil

- Cabecera y barra inferior usan altura adaptable a su contenido y a la escala
  de texto; no se fijan cotas que recorten al 200%. `SafeArea` cubre notch e
  insets del sistema.
- Cuerpo con scroll vertical único; se evita scroll anidado y `GridView` con
  `childAspectRatio` rígido que provoca overflow del texto.
- Cuadrícula: al 100% en 2 columnas y orden de fila del spec (`Explorar plantas
  y aceites`, `Buscar por objetivo`, `Identificar con cámara`, `Formular
  mezclas`). Con escala alta se pasa a 1 columna conservando el mismo orden de
  lectura. El umbral se calcula con
  `MediaQuery.textScalerOf(context).scale(fontSize) / fontSize` (>= 1.5), no con
  la API deprecada `textScaleFactor`. La disposición se resuelve con
  `Column`/`Row` o `Wrap` y alturas naturales, no con un grid de proporción
  fija.
- Barra inferior: `selectedIndex` constante 0. Los 11 callbacks se invocan en
  todos los modos; solo bajo condición de depuración se emite el mensaje. Al
  activar `Favoritos`, `Historial` o `Perfil` se invoca su callback, pero no se
  hace `setState`, no se llama `router.go`, no se cambia la ruta ni el índice y
  no se muestra otro contenido. Se emite también el callback de `Inicio` aunque
  ya esté activo.
- Se evita `NavigationBar` por defecto si su altura fija o el recorte de labels
  rompe el 200%; se construyen destinos con área de toque >= 48 dp.

### D4. Cálculo puro del mensaje y política de debug

- Un único archivo `app/lib/features/home/presentation/home_action.dart`
  concentra: `enum HomeAction` con 11 valores, el mapeo acción -> mensaje exacto
  y una función de cálculo pura que, dada la acción y el modo, devuelve mensaje
  o `null`. El cálculo no tiene efectos.
- El efecto de emisión queda aislado en el llamador: producción pasa
  exclusivamente `kDebugMode` y llama `debugPrint` exactamente una vez solo si el
  cálculo devuelve mensaje. No hay configuración de app, preferencia de usuario,
  variable de entorno ni ruta alternativa que eluda el modo.
- Mapeo normativo de los 11 mensajes (idéntico al spec `home-screen`, sin IDs
  nuevos):
  1. `[Home] Cabecera: Menú`
  2. `[Home] Cabecera: Perfil`
  3. `[Home] Explorar plantas y aceites`
  4. `[Home] Buscar por objetivo`
  5. `[Home] Identificar con cámara`
  6. `[Home] Formular mezclas`
  7. `[Home] Preguntar al Boticario`
  8. `[Home] Pestaña: Inicio`
  9. `[Home] Pestaña: Favoritos`
  10. `[Home] Pestaña: Historial`
  11. `[Home] Pestaña: Perfil`
- Sin emisión por `build`, rebuild o hot reload; sin SnackBars, diálogos,
  tooltips ni operaciones silenciosas de producto. El mapeo debe verse en
  Run/Debug de Android Studio. Detalles del helper pueden ajustarse sin añadir
  capas ni canales.

### D5. Arte provisional propuesto (solo estructura)

- Texto vivo Flutter e iconos Material locales. Cabecera con icono de menú,
  hojas junto a `Boticario AI` (aprox. con `Icons.eco`/`Icons.local_florist`) e
  icono de persona. Banner con fondo crema y motivos florales/hoja con iconos
  Material decorativos, fuera de `Semantics`; su texto exacto es texto vivo.
- Paleta aproximada propuesta para esta estructura, no colores de marca ni hex
  originales: acento `#236335`, texto `#172A1F`, fondo `#F9FAF7`, tarjeta
  `#F3F5F2`, borde `#D6DDD4`, banner `#FBF2D4`.
- Dimensiones base propuestas y escalables con `TextTheme` y `MediaQuery`:
  padding 16, separación 12, radio 12, icono 32; tipografía del sistema/Material
  escalable. Contraste previsto adecuado entre texto y fondo, sin afirmar ratios
  WCAG medidos.
- No se promete fidelidad pixel-perfect ni hex originales. No hay imágenes
  remotas, collage a pantalla completa, extracción de texto del mockup ni
  archivos de marca, fuentes nuevas o dependencias. No se exige
  `ThemeExtension`. La escala se adapta, sin elipsis ni altura fija al 200%, con
  toque mínimo 48x48.
- Supuesto explícito menor: estos colores, dimensiones e iconos son una
  propuesta provisional para esta estructura y no están confirmados; el arte
  final y su aprobación quedan fuera de alcance.

### D6. Estrategia de pruebas y render

- Widget: estructura y orden de fila, los 11 callbacks, ausencia de cambio de
  ruta/índice/overlays, semántica, áreas >= 48 dp, insets y 360x640 dp al 100%
  y 200%.
- Unit de `home_action.dart`: los 11 casos con modo permitido y no permitido. La
  prueba negativa de política es determinista y unitaria; aclara que no equivale
  a haber ejecutado un perfil o release real, sin afirmarlo.
- Widget con `debugPrint` interceptado, filtrando solo mensajes con prefijo
  `[Home]`, restaurado en `finally`/`tearDown`: sin tap durante el build = 0
  mensajes, cada acción = 1 mensaje, `Cabecera: Perfil` y `Pestaña: Perfil`
  distinguibles, e `Inicio` activo emite.
- App e integración: router real, ruta `/` y aislamiento por `ProviderScope`.
- Smoke real de `main()` siempre en emulador Android, nunca en dispositivo
  físico, sin datos ni red. El AVD de referencia es `boticario_api36`; el serial
  histórico es `emulator-5554`, pero el serial actual se obtiene con
  `flutter devices` y no se asume constante. Si no hay emulador disponible, el
  smoke se reporta explícitamente como no ejecutado o bloqueado, sin declarar
  verificación Android. Capturas comparadas con el mockup por estructura, sin
  golden raster pixel-perfect.
- Se reutilizan SDK fijado, pin y comandos CI; no se cambian workflow ni
  dependencias. No se reporta CI remoto en verde ni smoke verificado sin
  ejecutarlos, ni se aceptan licencias automáticamente. Ninguna prueba se ejecuta
  en esta tarea: esto es plan.

### D7. Migración, README y docs

- Delta bootstrap: 4 requirements MODIFIED (`Arranque Android y pantalla inicial
  única`, `Funcionamiento local sin autenticación ni servicios remotos`,
  `Accesibilidad de la pantalla inicial`, `Verificaciones reproducibles del
  incremento`) y 1 REMOVED (`Contador demo con estado por instancia`). Nuevo
  `home-screen`: 4 requirements / 20 escenarios.
- La main spec actual coincide hoy con el código; la desactualización es
  temporal solo durante el apply y hasta el sync/archive, no antes. Se conserva
  main spec e histórico; no se promueve el delta a main spec ahora. El escenario
  `Saludo exacto` mantiene su título legacy (validador) aunque su cuerpo marque
  la marca actual; se explica la migración para evitar confusión sin reabrir IDs.
- README: al implementar, actualizar Estado actual y lo visible, los logs del Run
  manual y cómo verificar la UI. Las evidencias previas quedan como HISTÓRICAS
  con SHA y fecha, sin presentarlas como resultado de Home. No se reintroducen
  `Próximos pasos` ni `Generación del scaffold` ni se reescriben docs de
  mockups/research a posteriori. El recuento exacto de pruebas se actualiza en el
  README después de ejecutarlas y validarlas, no antes.

### D8. Alcance de archivos y git

- `.gitignore` pertenece al usuario y queda intacto; este diseño no exige commit.
  El registro del cambio se hará cuando el usuario lo autorice, sin forzarlo.

## Risks / Trade-offs

- Recorte de texto al 200% en 2 columnas -> umbral a 1 columna, alturas
  naturales y scroll; se cubre con widget test a 360x640.
- Altura o labels de la barra inferior por defecto se recortan -> barra propia
  adaptable y áreas >= 48 dp.
- Fuga de intercepción de `debugPrint` entre tests -> filtro por prefijo
  `[Home]` y restauración en `finally`/`tearDown`.
- La prueba determinista de política no equivale a un release/profile ejecutado
  -> se declara como límite de evidencia: verifica el cálculo permitido/no
  permitido, no el silencio de un binario real.
- El arte provisional difiere del mockup -> es una propuesta no confirmada; se
  valida la estructura, no el pixel, y el arte final queda fuera de alcance.

## Migration Plan

1. Crear `home_action.dart` (enum, mapeo, cálculo puro) y su prueba unit.
2. Reescribir `home_page.dart` con la estructura P03 y los widgets privados.
3. Retirar `home_controller.dart` y `home_controller_test.dart`.
4. Ajustar `theme.dart` (o constantes locales) solo si la estructura lo exige.
5. Actualizar `home_page_test.dart`, `app_test.dart` e
   `integration_test/app_test.dart` al contrato de Home.
6. Actualizar README (Estado actual, logs manuales, verificación) preservando
   evidencias históricas y fijando el recuento de pruebas tras validarlas.
7. Desde `app/`, verificar con `dart format --output=none --set-exit-if-changed .`,
   `flutter analyze` y `flutter test test/`; usar `flutter pub get --enforce-lockfile`
   si hay base de código sin cambios de dependencias.
8. Ejecutar el smoke real de `main()` en un emulador Android disponible; si no
   hay, reportarlo como no ejecutado o bloqueado.
9. Más adelante, archivar y sincronizar main spec.

Rollback selectivo: revertir solo los archivos de Home afectados
(`home_page.dart`, `home_controller.dart` y pruebas relacionadas, más el README
si se tocó), sin revertir `.gitignore` ni otros archivos del usuario. No hay
datos ni persistencia que migrar.

## Open Questions

- Ninguna bloqueante para specs, enfoque o desglose de tareas. El arte final, los
  tokens de marca y la aprobación de colores e iconos quedan diferidos fuera de
  este cambio.
