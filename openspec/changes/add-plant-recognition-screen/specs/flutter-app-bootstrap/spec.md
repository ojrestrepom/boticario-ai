## MODIFIED Requirements

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


## ADDED Requirements

### Requirement: Recorrido local de identificación

La aplicación SHALL permitir Inicio → /identify y retorno mediante Atrás de app, Atrás del sistema o Inicio, también desde acceso directo. El recorrido SHALL funcionar sin conectividad ni autenticación y sin peticiones remotas. Las verificaciones automatizadas SHALL cubrir entrada, retornos, ausencia de HTTP y controles deshabilitados.

#### Scenario: Identificación sin servicios

- **WHEN** se abre /identify desde Inicio o directamente y se regresa
- **THEN** se muestra la pantalla local con cámara y galería deshabilitadas y se vuelve a / sin peticiones remotas
