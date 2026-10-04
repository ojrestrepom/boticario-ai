# Spec Delta

## MODIFIED Requirements

### Requirement: Arranque Android y pantalla inicial única
El proyecto SHALL poder compilarse y ejecutarse como aplicación Android con una
pantalla inicial accesible en la ruta `/`, con los recorridos permitidos Inicio
(P03) → Explorar → Pasaporte y sus retornos, e Inicio → P06 Buscar por objetivo
y retorno a Inicio; SHALL NOT ofrecer navegación adicional. La pantalla inicial
es la estructura Inicio (P03).

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
- **WHEN** se activan las otras nueve acciones de Inicio o las pestañas inertes
- **THEN** no se abre una ruta o pantalla adicional

### Requirement: Funcionamiento local sin autenticación ni servicios remotos
La aplicación SHALL mostrar Inicio, Explorar, pasaportes, P06 y controles del
catálogo sin inicio de sesión ni solicitudes a servicios remotos de negocio,
incluso sin conectividad; el catálogo disponible SHALL funcionar localmente.

#### Scenario: Uso sin inicio de sesión
- **WHEN** se abre la aplicación
- **THEN** no se solicita autenticación y la pantalla Inicio es utilizable

#### Scenario: Funcionamiento sin conectividad
- **WHEN** el dispositivo no tiene conectividad
- **THEN** Inicio, P06, la exploración, las fichas y los datos archivados disponibles siguen funcionando

#### Scenario: Ausencia de solicitudes de negocio
- **WHEN** el usuario interactúa con Inicio, P06 o con el recorrido del catálogo
- **THEN** no se envían solicitudes a servicios remotos de negocio

### Requirement: Verificaciones reproducibles del incremento
El proyecto SHALL ofrecer verificaciones reproducibles de formato, análisis y
pruebas de Inicio, P06, el recorrido del catálogo, sus datos locales y la
política de emisión de mensajes solo en depuración, evaluando casos con el modo
permitido y el no permitido; SHALL verificar retornos, inercia de las seis
filas y estados de error y SHALL reportar fallo en CI ante error. Estas
verificaciones SHALL ejecutarse con los comandos de prueba actuales en
configuración de depuración; no se exige ni se presenta como prueba de binarios
release/profile, cuyo silencio real es comportamiento normativo de
`home-screen`.

#### Scenario: Verificaciones automatizadas
- **WHEN** se ejecutan los comandos de verificación documentados en configuración de depuración
- **THEN** se ejecutan formato, análisis y pruebas de Inicio, P06, el catálogo, búsqueda y filtros, fichas, retornos, inercia de las filas P06, estados de error y política de emisión solo en depuración con casos de modo permitido y no permitido

#### Scenario: CI reporta fallo
- **WHEN** una verificación falla
- **THEN** la integración continua reporta el resultado como fallo

#### Scenario: Smoke Android
- **WHEN** existe un dispositivo o emulador Android disponible
- **THEN** el smoke test demuestra arranque, navegación al catálogo y pasaporte, retorno y funcionamiento local del flujo, así como entrada a P06 desde Inicio, sus retornos a Inicio y la inercia de sus seis filas, sin perder la cobertura existente del catálogo y pasaporte

#### Scenario: Smoke Android sin dispositivo
- **WHEN** no hay dispositivo o emulador Android disponible
- **THEN** el resultado del smoke test se reporta explícitamente como no ejecutado o no exitoso
