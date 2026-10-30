## MODIFIED Requirements

### Requirement: Recorrido local de identificación

La aplicación SHALL permitir Inicio → /identify y retorno mediante Atrás de app, Atrás del sistema o Inicio, también desde acceso directo. El recorrido SHALL funcionar sin conectividad ni autenticación y sin peticiones remotas. Las verificaciones automatizadas SHALL cubrir entrada, retornos, ausencia de HTTP y adquisición local.

#### Scenario: Identificación sin servicios

- **WHEN** se abre /identify desde Inicio o directamente y se regresa
- **THEN** se muestra la pantalla local con cámara y galería funcionales sin servicios remotos y se vuelve a / sin peticiones remotas
