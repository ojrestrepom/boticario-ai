# Spec Delta

## Purpose

Establece el andamiaje Android mínimo de Boticario AI: una pantalla inicial con
saludo fijo y un contador demo observable, junto con un flujo de desarrollo y
verificación reproducible, sin autenticación, backend ni persistencia.

## ADDED Requirements

### Requirement: Arranque Android y pantalla inicial única
El proyecto SHALL poder compilarse y ejecutarse como aplicación Android con una
única pantalla inicial accesible en la ruta `/`, sin navegación adicional ni
otras pantallas.

#### Scenario: Arranque en frío
- **WHEN** la aplicación se inicia en un dispositivo o emulador Android
- **THEN** la pantalla inicial de la ruta `/` es la vista visible

#### Scenario: Saludo exacto
- **WHEN** se muestra la pantalla inicial
- **THEN** el texto visible incluye exactamente `Hola, Boticario AI`

#### Scenario: Sin navegación adicional
- **WHEN** el usuario interactúa con la pantalla inicial
- **THEN** no se expone ninguna otra pantalla ni ruta de navegación

### Requirement: Contador demo con estado por instancia
La aplicación SHALL mostrar en la pantalla inicial un contador demo que inicia en
0 y aumenta exactamente 1 por cada activación del botón `Incrementar`, reflejando
el valor actual en la interfaz.

#### Scenario: Estado inicial
- **WHEN** la pantalla inicial se muestra por primera vez en una nueva instancia
- **THEN** el contador muestra `Contador: 0` y el botón `Incrementar` está visible

#### Scenario: Una activación
- **WHEN** el contador muestra `Contador: 0` y el usuario activa `Incrementar` una vez
- **THEN** el contador muestra `Contador: 1`

#### Scenario: N activaciones
- **WHEN** el contador muestra `Contador: 0` y el usuario activa `Incrementar` N veces
- **THEN** el contador muestra `Contador: N`

#### Scenario: Reinicio en nueva instancia
- **WHEN** la aplicación se inicia en frío en una nueva instancia
- **THEN** el contador vuelve a `Contador: 0` sin persistencia previa

### Requirement: Funcionamiento local sin autenticación ni servicios remotos
La aplicación SHALL mostrar el saludo y operar el contador sin inicio de sesión y
sin realizar solicitudes a servicios remotos de negocio, incluso sin
conectividad.

#### Scenario: Uso sin inicio de sesión
- **WHEN** se abre la aplicación
- **THEN** no se solicita autenticación y la pantalla inicial es utilizable

#### Scenario: Funcionamiento sin conectividad
- **WHEN** el dispositivo no tiene conectividad
- **THEN** el saludo y el contador siguen funcionando

#### Scenario: Ausencia de solicitudes de negocio
- **WHEN** el usuario interactúa con el saludo y el contador
- **THEN** no se envían solicitudes a servicios remotos de negocio

### Requirement: Accesibilidad de la pantalla inicial
La aplicación SHALL presentar el saludo, el valor del contador y el botón
`Incrementar` con texto legible y semántica accesible, sin recorte al aumentar el
tamaño de texto.

#### Scenario: Semántica accesible
- **WHEN** una tecnología de asistencia recorre la pantalla inicial
- **THEN** el botón expone la etiqueta `Incrementar` y el valor actual del contador se expone como información accesible

#### Scenario: Texto aumentado sin recorte
- **WHEN** el tamaño de texto del sistema se aumenta al 200% en un viewport de 360x640 dp
- **THEN** el saludo, el valor del contador y el botón permanecen visibles y sin recorte

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
pruebas del saludo, la interacción del contador y el aislamiento de estado, y
SHALL reportar fallo en la integración continua ante error.

#### Scenario: Verificaciones automatizadas
- **WHEN** se ejecutan los comandos de verificación documentados
- **THEN** se ejecutan la comprobación de formato, el análisis y las pruebas de saludo, interacción del contador y aislamiento de estado

#### Scenario: CI reporta fallo
- **WHEN** una verificación falla
- **THEN** la integración continua reporta el resultado como fallo

#### Scenario: Smoke Android
- **WHEN** existe un dispositivo o emulador Android disponible
- **THEN** el smoke test demuestra el arranque y la operación del contador

#### Scenario: Smoke Android sin dispositivo
- **WHEN** no hay dispositivo o emulador Android disponible
- **THEN** el resultado del smoke test se reporta explícitamente como no ejecutado o no exitoso
