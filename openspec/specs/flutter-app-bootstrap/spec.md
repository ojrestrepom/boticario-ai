# flutter-app-bootstrap Specification

## Purpose

Establece el andamiaje Android mínimo de Boticario AI: una pantalla inicial con saludo fijo y un contador demo observable, junto con un flujo de desarrollo y verificación reproducible, sin autenticación, backend ni persistencia.

## Requirements

### Requirement: Arranque Android y pantalla inicial única
El proyecto SHALL poder compilarse y ejecutarse como aplicación Android con una pantalla inicial accesible en la ruta `/`, con los recorridos permitidos Inicio (P03) → Explorar → Pasaporte y sus retornos, e Inicio → P06 Buscar por objetivo y retorno a Inicio, e Inicio → /identify y retorno a Inicio; SHALL NOT ofrecer navegación adicional. La pantalla inicial es la estructura Inicio (P03).

#### Scenario: Arranque en frío
- **WHEN** la aplicación se inicia en un dispositivo o emulador Android
- **THEN** la pantalla Inicio de la ruta `/` es la vista visible

#### Scenario: Saludo exacto
- **WHEN** se muestra la pantalla inicial
- **THEN** la cabecera muestra exactamente la marca `Boticario AI` y no aparece el saludo `Hola, Boticario AI`

#### Scenario: Sin navegación adicional
- **WHEN** el usuario abre Explorar desde Inicio, selecciona una planta, regresa o activa Inicio
- **THEN** el flujo se limita a Inicio, Explorar y el pasaporte correspondiente, con retorno seguro, sin otras pantallas ni rutas

#### Scenario: Recorrido de Buscar por objetivo
- **WHEN** el usuario abre Buscar por objetivo desde Inicio y usa Atrás de app, Atrás del sistema o Inicio
- **THEN** se muestra P06 y cada retorno vuelve a la raíz Inicio sin abrir otras pantallas ni rutas

#### Scenario: Ninguna otra ruta desde Inicio
- **WHEN** se activan las otras ocho acciones de Inicio o las pestañas inertes
- **THEN** no se abre una ruta o pantalla adicional

### Requirement: Funcionamiento local sin autenticación ni servicios remotos
La aplicación SHALL mostrar Inicio, P06 y los controles de navegación sin inicio de sesión y sin conectividad. Explorar y los pasaportes SHALL consumir la API del catálogo y, sin conectividad, SHALL mostrar un error reintentable sin afectar a Inicio ni a P06. La aplicación SHALL NOT pedir autenticación al usuario; el único credencial que envía es el token de API de la compilación, que identifica a la app y no a una persona. Las únicas peticiones remotas SHALL ser las de la API del catálogo y SHALL NOT llevar datos de usuario.

#### Scenario: Uso sin inicio de sesión
- **WHEN** se abre la aplicación
- **THEN** no se solicita autenticación y la pantalla Inicio es utilizable

#### Scenario: Funcionamiento sin conectividad
- **WHEN** el dispositivo no tiene conectividad
- **THEN** Inicio y P06 siguen funcionando, y Explorar y el pasaporte muestran un error reintentable sin cierre inesperado

#### Scenario: Ausencia de solicitudes de negocio
- **WHEN** el usuario interactúa con Inicio o con P06
- **THEN** no se envían solicitudes remotas

#### Scenario: Solicitudes limitadas a la API del catálogo
- **WHEN** el usuario recorre Explorar y el pasaporte
- **THEN** las únicas peticiones son lecturas de la API del catálogo, con el token de API como única credencial y sin datos de usuario

#### Scenario: Token rechazado
- **WHEN** la API del catálogo responde 401 en Explorar o en el pasaporte
- **THEN** se muestra un error de no autorizado sin cierre inesperado, Inicio y P06 siguen funcionando y no se solicita inicio de sesión

### Requirement: Accesibilidad de la pantalla inicial
La aplicación SHALL presentar la estructura Inicio, sus textos y sus controles con texto legible y semántica accesible, sin recorte al aumentar el tamaño de texto.

#### Scenario: Semántica accesible
- **WHEN** una tecnología de asistencia recorre la pantalla inicial
- **THEN** los controles de Inicio exponen etiquetas distinguibles y el contenido esencial se expone como información accesible

#### Scenario: Texto aumentado sin recorte
- **WHEN** el tamaño de texto del sistema se aumenta al 200% en un viewport de 360x640 dp
- **THEN** el contenido esencial de Inicio permanece visible, sin recorte, y alcanzable con scroll vertical

### Requirement: Flujo de desarrollo reproducible y documentado
El repositorio SHALL contener la app Android en `app/`, abrible en Android Studio, con prerequisitos, versión exacta de SDK, dependencias fijadas y comandos documentados; la configuración local del SDK SHALL permanecer sin versionar. La documentación SHALL cubrir cómo arrancar el backend con Docker y la dirección con la que lo alcanzan el emulador y un dispositivo físico, y SHALL cubrir cómo compilar el build `release` y ejecutar el smoke contra el backend desplegado con `--dart-define=API_BASE_URL=https://…`. La documentación SHALL indicar que el build `release` debe apuntar a la URL HTTPS del backend desplegado y que el HTTP en claro queda para `debug` y `profile` con el backend local.

#### Scenario: Apertura en Android Studio
- **WHEN** un desarrollador abre la raíz `app/` en Android Studio con los prerequisitos documentados
- **THEN** el proyecto se reconoce como proyecto Flutter con target Android

#### Scenario: SDK y dependencias fijadas
- **WHEN** se revisa el repositorio
- **THEN** la versión exacta de SDK usada en local y en CI y las dependencias están fijadas

#### Scenario: Configuración local sin versionar
- **WHEN** se revisa el control de versiones
- **THEN** la configuración local del SDK no está versionada

#### Scenario: Setup y comandos documentados
- **WHEN** un desarrollador consulta la documentación
- **THEN** encuentra los pasos de setup, la selección de dispositivo Android y los comandos de prueba

#### Scenario: SDK ausente
- **WHEN** un desarrollador no dispone del SDK requerido y consulta el quickstart
- **THEN** encuentra la preparación manual del SDK y la revisión y aceptación interactiva de licencias

#### Scenario: Backend y dirección documentados
- **WHEN** un desarrollador consulta el quick start
- **THEN** encuentra que debe arrancar el backend con Docker antes de ejecutar la app, que el emulador lo alcanza en `http://10.0.2.2:8080` y que un dispositivo físico necesita `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080`

#### Scenario: Release contra el backend desplegado
- **WHEN** un desarrollador consulta la documentación para compilar el build `release` o ejecutar el smoke contra el backend desplegado
- **THEN** encuentra los comandos con `--dart-define=API_BASE_URL=https://<url-de-cloud-run>`, que el build `release` debe apuntar a la URL HTTPS del backend desplegado y que el HTTP en claro queda para `debug` y `profile` con el backend local, y que, sin esa definición, la dirección por defecto sigue siendo la del emulador

### Requirement: Verificaciones reproducibles del incremento
El proyecto SHALL ofrecer verificaciones reproducibles de formato, análisis y pruebas de Inicio, P06, el recorrido del catálogo, el cliente de la API y la política de emisión de mensajes solo en depuración, evaluando casos con el modo permitido y el no permitido; SHALL verificar retornos, inercia de las seis filas y estados de error y SHALL reportar fallo en CI ante error. Las pruebas unitarias y de widget SHALL ejecutarse sin red, con el cliente HTTP inyectado. Estas verificaciones SHALL ejecutarse con los comandos de prueba actuales en configuración de depuración; no se exige ni se presenta como prueba de binarios release/profile, cuyo silencio real es comportamiento normativo de `home-screen`.

#### Scenario: Verificaciones automatizadas
- **WHEN** se ejecutan los comandos de verificación documentados en configuración de depuración
- **THEN** se ejecutan formato, análisis y pruebas de Inicio, P06, el cliente de catálogo, Explorar con búsqueda, paginación y filtros, fichas, retornos, inercia de las filas P06, estados de error y política de emisión solo en depuración con casos de modo permitido y no permitido, todo sin red y con el cliente HTTP inyectado

#### Scenario: CI reporta fallo
- **WHEN** una verificación falla
- **THEN** la integración continua reporta el resultado como fallo

#### Scenario: Smoke Android
- **WHEN** existe un dispositivo o emulador Android disponible y el backend está en marcha
- **THEN** el smoke test demuestra arranque, búsqueda de una planta real en Explorar, navegación a su pasaporte y retorno, así como entrada a P06 desde Inicio, sus retornos a Inicio y la inercia de sus seis filas, y deniega las peticiones a cualquier host distinto del de la dirección base

#### Scenario: Smoke Android sin dispositivo
- **WHEN** no hay dispositivo o emulador Android disponible, o el backend no está en marcha
- **THEN** el resultado del smoke test se reporta explícitamente como no ejecutado o no exitoso

### Requirement: Recorrido local de identificación

La aplicación SHALL permitir Inicio → /identify y retorno mediante Atrás de app, Atrás del sistema o Inicio, también desde acceso directo. El recorrido SHALL funcionar sin conectividad ni autenticación y sin peticiones remotas. Las verificaciones automatizadas SHALL cubrir entrada, retornos, ausencia de HTTP y adquisición local.

#### Scenario: Identificación sin servicios

- **WHEN** se abre /identify desde Inicio o directamente y se regresa
- **THEN** se muestra la pantalla local con cámara y galería funcionales sin servicios remotos y se vuelve a / sin peticiones remotas
