# flutter-app-bootstrap Specification

## Purpose

Establece el andamiaje Android mínimo de Boticario AI: una pantalla inicial con
saludo fijo y un contador demo observable, junto con un flujo de desarrollo y
verificación reproducible, sin autenticación, backend ni persistencia.

## Requirements

### Requirement: Arranque Android y pantalla inicial única
El proyecto SHALL poder compilarse y ejecutarse como aplicación Android con una
única pantalla inicial accesible en la ruta `/`, sin navegación adicional ni
otras pantallas; esa pantalla inicial es la estructura Inicio (P03).

#### Scenario: Arranque en frío
- **WHEN** la aplicación se inicia en un dispositivo o emulador Android
- **THEN** la pantalla Inicio de la ruta `/` es la vista visible

#### Scenario: Saludo exacto
- **WHEN** se muestra la pantalla inicial
- **THEN** la cabecera muestra exactamente la marca `Boticario AI` y no aparece el saludo `Hola, Boticario AI`

#### Scenario: Sin navegación adicional
- **WHEN** el usuario interactúa con la pantalla inicial
- **THEN** no se expone ninguna otra pantalla ni ruta de navegación

### Requirement: Funcionamiento local sin autenticación ni servicios remotos
La aplicación SHALL mostrar la estructura Inicio y sus controles sin inicio de
sesión y sin realizar solicitudes a servicios remotos de negocio, incluso sin
conectividad.

#### Scenario: Uso sin inicio de sesión
- **WHEN** se abre la aplicación
- **THEN** no se solicita autenticación y la pantalla Inicio es utilizable

#### Scenario: Funcionamiento sin conectividad
- **WHEN** el dispositivo no tiene conectividad
- **THEN** la estructura y los controles de Inicio siguen funcionando

#### Scenario: Ausencia de solicitudes de negocio
- **WHEN** el usuario interactúa con los controles de Inicio
- **THEN** no se envían solicitudes a servicios remotos de negocio

### Requirement: Accesibilidad de la pantalla inicial
La aplicación SHALL presentar la estructura Inicio, sus textos y sus controles
con texto legible y semántica accesible, sin recorte al aumentar el tamaño de
texto.

#### Scenario: Semántica accesible
- **WHEN** una tecnología de asistencia recorre la pantalla inicial
- **THEN** los controles de Inicio exponen etiquetas distinguibles y el contenido esencial se expone como información accesible

#### Scenario: Texto aumentado sin recorte
- **WHEN** el tamaño de texto del sistema se aumenta al 200% en un viewport de 360x640 dp
- **THEN** el contenido esencial de Inicio permanece visible, sin recorte, y alcanzable con scroll vertical

### Requirement: Flujo de desarrollo reproducible y documentado
El repositorio SHALL contener la app Android en `app/`, abrible en Android Studio,
con prerequisitos, versión exacta de SDK, dependencias fijadas y comandos
documentados; la configuración local del SDK SHALL permanecer sin versionar.

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

### Requirement: Verificaciones reproducibles del incremento
El proyecto SHALL ofrecer verificaciones reproducibles de formato, análisis y
pruebas de la estructura de Inicio, de las 11 acciones y de la política de
emisión de mensajes solo en depuración, evaluando casos con el modo permitido y
el no permitido; y SHALL reportar fallo en la integración continua ante error.
Estas verificaciones SHALL ejecutarse con los comandos de prueba actuales en
configuración de depuración; no se exige ni se presenta como prueba de binarios
release/profile, cuyo silencio real es comportamiento normativo de
`home-screen`.

#### Scenario: Verificaciones automatizadas
- **WHEN** se ejecutan los comandos de verificación documentados en configuración de depuración
- **THEN** se ejecutan la comprobación de formato, el análisis y las pruebas de la estructura de Inicio, de las 11 acciones y de la política de emisión solo en depuración, con casos de modo permitido y no permitido

#### Scenario: CI reporta fallo
- **WHEN** una verificación falla
- **THEN** la integración continua reporta el resultado como fallo

#### Scenario: Smoke Android
- **WHEN** existe un dispositivo o emulador Android disponible
- **THEN** el smoke test demuestra el arranque y la interacción con la pantalla Inicio

#### Scenario: Smoke Android sin dispositivo
- **WHEN** no hay dispositivo o emulador Android disponible
- **THEN** el resultado del smoke test se reporta explícitamente como no ejecutado o no exitoso
