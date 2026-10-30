## MODIFIED Requirements

### Requirement: Contrato de depuración de las 11 acciones
Cada uno de los 11 controles de Inicio SHALL invocar su callback y, bajo `kDebugMode`, SHALL emitir exactamente un mensaje completo por activación vía `debugPrint`, con este mapeo normativo:

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

Las otras ocho acciones distintas de las tarjetas Explorar, Buscar por objetivo e Identificar con cámara SHALL NOT mutar la UI (salvo el feedback táctil nativo ripple/focus) ni navegar. Explorar SHALL navegar a Explorar, Buscar por objetivo SHALL navegar a P06 e Identificar con cámara SHALL navegar a /identify en todos los modos de ejecución. Ninguna de las once acciones SHALL registrar ni persistir datos de usuario. El mensaje de cada activación SHALL emitirse únicamente bajo `kDebugMode`; en profile o release la navegación de Explorar, P06 e Identificar planta continúa funcionando sin emitir mensajes. SHALL NOT emitir logs por build, rebuild o hot reload sin pulsación. Los prefijos del runtime Flutter quedan fuera del mensaje contratado.

#### Scenario: Cobertura de los 11 controles
- **WHEN** con `kDebugMode` activo se activa cualquiera de los 11 controles listados
- **THEN** se invoca exactamente una vez su callback y se emite, vía `debugPrint`, exactamente una vez el mensaje completo mapeado para esa acción

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
- **WHEN** se activa cualquiera de las ocho acciones distintas de Explorar, Buscar por objetivo e Identificar con cámara
- **THEN** la UI no cambia salvo el feedback táctil nativo, no se navega y no se registra ni persiste ningún dato de usuario

#### Scenario: Explorar en depuración
- **WHEN** con `kDebugMode` activo se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se emite exactamente una vez su mensaje normativo y se navega a P04 sin registrar ni persistir datos de usuario

#### Scenario: Explorar fuera de depuración
- **WHEN** en profile o release se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se navega a P04 sin emitir el mensaje ni registrar o persistir datos de usuario

#### Scenario: Buscar por objetivo en depuración
- **WHEN** con `kDebugMode` activo se activa la tarjeta `Buscar por objetivo`
- **THEN** se emite exactamente una vez `[Home] Buscar por objetivo` y se navega a P06 sin registrar ni persistir datos de usuario

#### Scenario: Buscar por objetivo fuera de depuración
- **WHEN** en profile o release se activa la tarjeta `Buscar por objetivo`
- **THEN** se navega a P06 sin emitir el mensaje ni registrar o persistir datos de usuario


### Requirement: Barra inferior inmóvil sin navegación funcional
La barra inferior SHALL ser la única barra visual de pestañas de Inicio, sin navegación funcional: `Inicio` SHALL permanecer siempre seleccionado y la ruta SHALL continuar siendo `/`, salvo que las tarjetas `Explorar plantas y aceites` o `Buscar por objetivo` o `Identificar con cámara` abran sus respectivos recorridos permitidos. Activar cualquier otro control o pestaña de Inicio SHALL NOT cambiar la ruta ni la pestaña seleccionada, ni abrir pantallas, rutas, overlays, SnackBars, diálogos, drawers, permisos, cámara, API, backend, persistencia ni chat real.

#### Scenario: Ruta sin cambios
- **WHEN** se activa cualquier control o pestaña de Inicio excepto las tarjetas Explorar, Buscar por objetivo e Identificar con cámara
- **THEN** la ruta actual permanece `/` sin cambios

#### Scenario: Explorar abre P04
- **WHEN** se activa la tarjeta `Explorar plantas y aceites`
- **THEN** se abre únicamente la pantalla Explorar del recorrido permitido

#### Scenario: Buscar por objetivo abre P06
- **WHEN** se activa la tarjeta `Buscar por objetivo`
- **THEN** se abre únicamente P06 del recorrido permitido

#### Scenario: Índice de pestaña sin cambios
- **WHEN** se activan las pestañas `Favoritos`, `Historial` o `Perfil`
- **THEN** `Inicio` sigue siendo la pestaña seleccionada

#### Scenario: Sin navegación ni overlays
- **WHEN** el usuario interactúa con Inicio
- **THEN** no se abre ninguna pantalla o ruta ajena a los recorridos Explorar y Pasaporte, Buscar por objetivo/P06 e Identificar planta, ni overlay, SnackBar, diálogo o drawer

#### Scenario: Sin operaciones de producto
- **WHEN** el usuario interactúa con Inicio
- **THEN** no se solicita ningún permiso ni se ejecuta cámara, API, backend, persistencia, chat real ni login de producto


## ADDED Requirements

### Requirement: Acceso al reconocimiento

La tarjeta «Identificar con cámara» SHALL abrir /identify en todos los modos y emitir exactamente una vez su mensaje contratado únicamente bajo kDebugMode, sin registrar datos de usuario.

#### Scenario: Abrir identificación

- **WHEN** se activa la tarjeta «Identificar con cámara»
- **THEN** se muestra la pantalla inicial de reconocimiento; en depuración se emite [Home] Identificar con cámara una vez y fuera de depuración no se emite
