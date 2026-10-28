# Spec Delta

## MODIFIED Requirements

### Requirement: Composición y contenido de Explorar
Explorar SHALL presentar navegación de regreso, el título `Explorar`, búsqueda con sugerencia `Buscar planta o aceite...`, filtros `Todas`, `Plantas` y `Aceites`, y la lista de plantas del catálogo que entrega la API, paginada. Cada fila SHALL mostrar el nombre principal y el secundario según la regla de nombre para mostrar de `catalog-client`: el `displayName` de la planta como principal y el científico como secundario, o solo el científico si ambos coinciden. SHALL usar solo ilustraciones o decoraciones locales provisionales, no fotografías externas, ni siquiera la imagen de la planta.

#### Scenario: Vista inicial
- **WHEN** se abre Explorar por primera vez con el backend disponible
- **THEN** se muestra la primera página de 50 plantas, `Todas` está seleccionada y cada fila presenta su nombre principal y, si lo hay, el secundario

#### Scenario: Arte local
- **WHEN** se muestra una fila de planta, incluso una cuyo detalle tiene imagen
- **THEN** su decoración proviene de recursos locales provisionales y la lista no descarga imágenes externas

#### Scenario: Planta sin nombre común
- **WHEN** se muestra una planta cuyo `displayName` es su nombre científico
- **THEN** su fila presenta el nombre científico como principal y no presenta nombre secundario

#### Scenario: Nombre en español
- **WHEN** se muestra la planta `salvia-rosmarinus` cuyo `displayName` es «Romero»
- **THEN** su fila presenta «Romero» como principal y `Salvia rosmarinus` como secundario
