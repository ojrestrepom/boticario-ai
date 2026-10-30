# Spec Delta

## MODIFIED Requirements

### Requirement: Funcionamiento local sin autenticación ni servicios remotos
La aplicación SHALL mostrar Inicio, P06 y los controles de navegación sin inicio de sesión y sin conectividad. Explorar y los pasaportes SHALL consumir la API del catálogo y, sin conectividad, SHALL mostrar un error reintentable sin afectar a Inicio ni a P06. Las únicas peticiones remotas SHALL ser las de la API del catálogo y SHALL NOT llevar datos de usuario.

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
- **THEN** las únicas peticiones son lecturas de la API del catálogo, sin autenticación ni datos de usuario

### Requirement: Flujo de desarrollo reproducible y documentado
El repositorio SHALL contener la app Android en `app/`, abrible en Android Studio, con prerequisitos, versión exacta de SDK, dependencias fijadas y comandos documentados; la configuración local del SDK SHALL permanecer sin versionar. La documentación SHALL cubrir cómo arrancar el backend con Docker y la dirección con la que lo alcanzan el emulador y un dispositivo físico.

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
