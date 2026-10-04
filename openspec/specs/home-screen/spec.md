# home-screen Specification

## Purpose

Define la pantalla Inicio (P03) como estructura visual e interactiva de partida:
su composición, el contrato de depuración de sus 11 controles y una navegación
inferior inmóvil, sin funcionalidades de producto ni promesa de arte final.

## Requirements

### Requirement: Estructura visual de la pantalla Inicio
En la ruta `/`, la pantalla Inicio SHALL presentar:

- una cabecera con icono de menú a la izquierda, hojas con la marca exacta
  `Boticario AI` al centro e icono de persona a la derecha;
- un banner botánico con el texto exacto
  `Pequeñas esencias, grandes posibilidades`;
- una cuadrícula 2x2 en presentación normal al 100%, en orden de fila:
  `Explorar plantas y aceites`, `Buscar por objetivo`,
  `Identificar con cámara`, `Formular mezclas`;
- un CTA de ancho completo `Preguntar al Boticario`;
- una barra inferior con `Inicio`, `Favoritos`, `Historial` y `Perfil`, con
  `Inicio` como único seleccionado.

El logo y el banner SHALL ser decorativos y SHALL NOT declarar acción ni botón.
La estructura SHALL usar texto Flutter vivo, iconos y decoración Material
locales; SHALL NOT usar paquetes, fuentes ni descargas nuevas, y SHALL NOT
rasterizar la pantalla completa ni usar el collage de mockups como pantalla. No
se garantizan logo, banner ni fidelidad pixel-perfect finales.

#### Scenario: Cabecera con marca
- **WHEN** se muestra la pantalla Inicio
- **THEN** son visibles el icono de menú, la marca exacta `Boticario AI` junto a hojas y el icono de persona

#### Scenario: Banner con frase exacta
- **WHEN** se muestra la pantalla Inicio
- **THEN** el banner muestra exactamente `Pequeñas esencias, grandes posibilidades`

#### Scenario: Cuadrícula 2x2 en orden
- **WHEN** se muestra la pantalla Inicio al 100% de tamaño de texto
- **THEN** las cuatro tarjetas aparecen en 2x2 en orden de fila `Explorar plantas y aceites`, `Buscar por objetivo`, `Identificar con cámara`, `Formular mezclas`

#### Scenario: CTA y barra inferior
- **WHEN** se muestra la pantalla Inicio
- **THEN** el CTA de ancho completo muestra `Preguntar al Boticario` y la barra inferior muestra `Inicio`, `Favoritos`, `Historial` y `Perfil` con `Inicio` seleccionado

#### Scenario: Logo y banner decorativos
- **WHEN** el usuario intenta activar el logo o el banner
- **THEN** no se declara ni se dispara ninguna acción asociada

#### Scenario: Decoración local
- **WHEN** se renderiza la pantalla Inicio
- **THEN** la vista se compone de texto, iconos y decoración Material locales, sin paquetes, fuentes ni descargas nuevas, sin rasterizar la pantalla completa y sin usar el collage de mockups como pantalla

### Requirement: Contrato de depuración de las 11 acciones
Cada uno de los 11 controles de Inicio SHALL invocar su callback y, bajo
`kDebugMode`, SHALL emitir exactamente un mensaje completo por activación vía
`debugPrint`, con este mapeo normativo:

- icono de menú de la cabecera -> `[Home] Cabecera: Menú`
- icono de persona de la cabecera -> `[Home] Cabecera: Perfil`
- tarjeta `Explorar plantas y aceites` -> `[Home] Explorar plantas y aceites`
- tarjeta `Buscar por objetivo` -> `[Home] Buscar por objetivo`
- tarjeta `Identificar con cámara` -> `[Home] Identificar con cámara`
- tarjeta `Formular mezclas` -> `[Home] Formular mezclas`
- CTA `Preguntar al Boticario` -> `[Home] Preguntar al Boticario`
- pestaña `Inicio` -> `[Home] Pestaña: Inicio` (también si ya está activa)
- pestaña `Favoritos` -> `[Home] Pestaña: Favoritos`
- pestaña `Historial` -> `[Home] Pestaña: Historial`
- pestaña `Perfil` -> `[Home] Pestaña: Perfil`

Las otras diez acciones SHALL NOT mutar la UI (salvo el feedback táctil nativo
ripple/focus) ni navegar; la tarjeta Explorar SHALL navegar a Explorar en todos
los modos de ejecución. Ninguna de las once acciones SHALL registrar ni
persistir datos de usuario. El mensaje de cada activación SHALL emitirse
únicamente bajo `kDebugMode`; en profile o release la navegación de Explorar
continúa funcionando sin emitir mensajes. SHALL NOT emitir logs por build,
rebuild o hot reload sin pulsación. Los prefijos del runtime Flutter quedan
fuera del mensaje contratado.

#### Scenario: Cobertura de los 11 controles
- **WHEN** con `kDebugMode` activo se activa cualquiera de los 11 controles listados
- **THEN** se invoca su callback y se emite exactamente una vez, vía `debugPrint`, el mensaje completo mapeado para esa acción

#### Scenario: Distinción entre cabecera y pestaña
- **WHEN** con `kDebugMode` activo se activa el icono de persona de la cabecera y luego la pestaña `Perfil`
- **THEN** los mensajes emitidos son `[Home] Cabecera: Perfil` y `[Home] Pestaña: Perfil`, distintos entre sí

#### Scenario: Sin log por render
- **WHEN** la pantalla Inicio se construye, reconstruye o recarga en caliente sin pulsación del usuario
- **THEN** no se emite ningún mensaje de las 11 acciones

#### Scenario: Silencio fuera de depuración
- **WHEN** la aplicación se ejecuta en profile o release
- **THEN** la UI de Inicio se muestra igual y no se emite ningún mensaje de las 11 acciones

#### Scenario: Inicio ya activo
- **WHEN** con `kDebugMode` activo el usuario activa la pestaña `Inicio` estando ya seleccionada
- **THEN** se emite `[Home] Pestaña: Inicio` y la selección visible no cambia

#### Scenario: Sin mutación de UI ni datos
- **WHEN** se activa cualquier control de Inicio excepto la tarjeta Explorar
- **THEN** la UI no cambia salvo el feedback táctil nativo, no se navega y no se registra ni persiste ningún dato de usuario

#### Scenario: Explorar en depuración
- **WHEN** con `kDebugMode` activo se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se emite exactamente una vez su mensaje normativo y se navega a P04 sin registrar ni persistir datos de usuario

#### Scenario: Explorar fuera de depuración
- **WHEN** en profile o release se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se navega a P04 sin emitir el mensaje ni registrar o persistir datos de usuario

### Requirement: Barra inferior inmóvil sin navegación funcional
La barra inferior SHALL ser la única barra visual de pestañas de Inicio, sin
navegación funcional: `Inicio` SHALL permanecer siempre seleccionado y la ruta
SHALL continuar siendo `/`, salvo que la tarjeta `Explorar plantas y aceites`
abra la pantalla Explorar del recorrido permitido. Activar cualquier otro
control o pestaña SHALL NOT cambiar la ruta ni la pestaña seleccionada, ni abrir
pantallas, rutas, overlays, SnackBars, diálogos, drawers, permisos, cámara, API,
backend, persistencia ni chat real.

#### Scenario: Ruta sin cambios
- **WHEN** se activa cualquier control o pestaña de Inicio excepto la tarjeta Explorar
- **THEN** la ruta actual permanece `/` sin cambios

#### Scenario: Explorar abre P04
- **WHEN** se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se abre únicamente la pantalla Explorar del recorrido permitido

#### Scenario: Índice de pestaña sin cambios
- **WHEN** se activan las pestañas `Favoritos`, `Historial` o `Perfil`
- **THEN** `Inicio` sigue siendo la pestaña seleccionada

#### Scenario: Sin navegación ni overlays
- **WHEN** el usuario interactúa con Inicio
- **THEN** no se abre ninguna pantalla o ruta ajena al recorrido Explorar y Pasaporte, ni overlay, SnackBar, diálogo o drawer

#### Scenario: Sin operaciones de producto
- **WHEN** el usuario interactúa con Inicio
- **THEN** no se solicita ningún permiso ni se ejecuta cámara, API, backend, persistencia, chat real ni login de producto

### Requirement: Accesibilidad y adaptación de layout de Inicio
La pantalla Inicio SHALL ser legible en una referencia de 360x640 dp al 100% y al
200% de tamaño de texto: todo el contenido SHALL ser alcanzable con scroll
vertical y SHALL NOT sufrir recorte, overflow horizontal ni elipsis de texto
esencial. La cuadrícula SHALL mostrar 2 columnas en presentación normal al 100%;
al 200% SHALL poder adaptar altura o número de columnas si hace falta, conservando
el orden de fila y priorizando legibilidad sobre fidelidad rígida. Cabecera y
barra inferior SHALL respetar zonas seguras (notch e insets del sistema). Cada
control SHALL ofrecer un área de toque >= 48 dp y una etiqueta semántica
distinguible; los iconos decorativos SHALL NOT duplicar la lectura.

#### Scenario: Legibilidad a 100% y 200%
- **WHEN** el tamaño de texto del sistema es 100% o 200% en 360x640 dp
- **THEN** el texto esencial de Inicio permanece legible, sin recorte, overflow horizontal ni elipsis, y todo el contenido es alcanzable con scroll vertical

#### Scenario: Cuadrícula adaptable
- **WHEN** la cuadrícula se renderiza al 100% y luego al 200% de tamaño de texto
- **THEN** al 100% muestra 2 columnas y al 200% adapta altura o número de columnas según haga falta, conservando el orden de fila y la legibilidad

#### Scenario: Áreas de toque y semántica
- **WHEN** una tecnología de asistencia recorre la pantalla Inicio
- **THEN** cada control tiene un área de toque de al menos 48 dp y una etiqueta semántica distinguible, y los iconos decorativos no duplican la lectura

#### Scenario: Zonas seguras
- **WHEN** el dispositivo presenta notch o insets del sistema
- **THEN** la cabecera y la barra inferior no quedan solapadas por el sistema
