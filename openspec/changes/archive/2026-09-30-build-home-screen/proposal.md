# Proposal

## Why

El bootstrap Android ya arranca, pero la ruta `/` aún muestra el saludo y el
contador demo. El próximo incremento es la pantalla Inicio (P03) como estructura
visual e interactiva de partida, limitada a depuración. Este cambio la define y
resuelve los contratos demo que la contradicen, sin implementar aún
funcionalidades del producto.

## What Changes

- Nueva pantalla Inicio (P03), solo estructura, en la ruta única `/`:
  - Cabecera: icono de menú a la izquierda, hojas + marca `Boticario AI` al
    centro, icono de persona a la derecha.
  - Banner botánico con el texto exacto `Pequeñas esencias, grandes
    posibilidades`.
  - Grid 2x2 en orden de fila: Explorar plantas y aceites; Buscar por objetivo;
    Identificar con cámara; Formular mezclas.
  - CTA de ancho completo `Preguntar al Boticario`.
  - Barra inferior Inicio, Favoritos, Historial y Perfil, con Inicio único
    seleccionado y persistente. La ruta sigue siendo `/`.
- Los 11 controles (2 de cabecera, 4 tarjetas, 1 chat y 4 tabs incluida Inicio)
  registran al clic un mensaje identificable por acción en la consola de Android
  Studio: solo `debugPrint` bajo `kDebugMode`, un registro por acción, sin logs en
  `build`/hot reload por sí mismo y sin trazas Home en release/profile.
- Logo y banner son decorativos, sin acciones asociadas.
- **BREAKING (contratos demo)**: se retiran/reemplazan de `flutter-app-bootstrap`
  el saludo exacto `Hola, Boticario AI`, el contador demo y el smoke del contador.
  El requisito de accesibilidad no se retira: se actualizan sus referencias de
  saludo/contador a Home, conservando las garantías.
- Accesibilidad: referencia 360x640 dp con texto al 200%, sin recortes y con
  scroll; labels en iconos y áreas de toque >= 48 dp recomendadas; fondos claros y
  verde crema aproximados.
- No incluye: Snackbar, diálogos, "Próximamente", destinos/rutas nuevas, drawers,
  auth, backend, API, persistencia, cámara, permisos, chat real, onboarding,
  splash ni pantallas nuevas.

## Capabilities

### New Capabilities

- `home-screen`: estructura de la pantalla Inicio, registro de las 11 acciones,
  navegación inferior inmóvil con Inicio activo y accesibilidad de Home.

### Modified Capabilities

- `flutter-app-bootstrap`: se conservan el arranque Android de ruta única `/`, el
  funcionamiento local sin autenticación ni servicios remotos y el flujo de
  desarrollo; cambian los contratos demo.
  - Requirement "Arranque Android y pantalla inicial única": se actualiza el
    escenario "Saludo exacto" (`Hola, Boticario AI`); el arranque en `/` y la
    ausencia de otras pantallas se conservan.
  - Requirement "Contador demo con estado por instancia": REMOVED en el delta de
    este cambio.
  - Requirement "Funcionamiento local sin autenticación ni servicios remotos": se
    mantiene MODIFIED porque su texto actual menciona el saludo y el contador; los
    escenarios se reformulan a Home conservando la garantía.
  - Requirements "Accesibilidad de la pantalla inicial" y "Verificaciones
    reproducibles del incremento": se modifican sus escenarios (saludo/contador ->
    Home) manteniendo orden y nombres preservables.
  - Nota: la main spec se preserva hasta el sync/cierre; este proposal declara los
    conflictos en vez de asumir compatibilidad total.

## Impact

- `app/lib/features/home/presentation/home_page.dart`: se reescribe como
  estructura P03.
- `app/lib/features/home/presentation/home_controller.dart`: el contador demo se
  retira.
- `app/lib/app/{router,theme,app}.dart`: el router conserva `/`; tema y shell se
  ajustan solo si la estructura lo exige.
- Tests: se retiran las pruebas del contador demo
  (`home_controller_test.dart`); se añaden pruebas de las 11 acciones y cobertura
  de Home en las suites adecuadas (widget e integración) y se actualizan
  `home_page_test.dart`, `app_test.dart` e `integration_test/app_test.dart`.
- `docs/mockups/*`: referencia de lectura, no se editan.
- Assets: no se dispone de assets individuales, fuentes ni tokens de color del
  diseño original. Se implementará con widgets Flutter de texto vivo y decoración/
  iconos Material locales, sin nuevos paquetes ni descargas, sin usar
  `docs/mockups.png` como sustituto de la UI ni recortar su texto. Sin
  dependencias nuevas previstas.

Finalidad: estructura y jerarquía fiel, no arte final. La decoración botánica será
local y simple con iconos Material y textos accesibles; no se promete fidelidad
pixel-perfect ni fuentes, logo o banner finales, y el arte final queda fuera de
alcance. Su aceptación puede revisarla el usuario al aprobar el plan.
