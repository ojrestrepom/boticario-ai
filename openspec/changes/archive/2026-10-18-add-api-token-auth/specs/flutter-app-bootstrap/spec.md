# Spec Delta

## MODIFIED Requirements

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
