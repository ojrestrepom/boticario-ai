# Spec Delta

## MODIFIED Requirements

### Requirement: Detalle de planta
`GET /v1/plants/{id}` SHALL devolver la identidad de la planta, sus nombres con tipo e idioma, la familia si existe, sus partes y sus usos (actividad, idioma y referencia con su cita). La familia SHALL ser un texto o `null`. La respuesta SHALL NOT incluir información de procedencia, como la fuente o el dataset de cada dato. Lo ausente SHALL devolverse como `null` o lista vacía, nunca inventado.

#### Scenario: Planta existente
- **WHEN** un cliente pide el detalle de un identificador existente
- **THEN** la respuesta incluye identidad, nombres, partes y usos

#### Scenario: Sin información de procedencia
- **WHEN** un cliente pide el detalle de una planta con datos de una o varias fuentes
- **THEN** ningún nombre, parte, uso ni la familia de la respuesta incluye campos de fuente u origen

#### Scenario: Planta sin usos
- **WHEN** la planta no tiene usos en el catálogo
- **THEN** la respuesta tiene una lista de usos vacía

#### Scenario: Familia presente
- **WHEN** la planta tiene familia en el catálogo
- **THEN** el campo de familia es un texto

#### Scenario: Familia ausente
- **WHEN** ninguna fuente aporta la familia de la planta
- **THEN** el campo de familia es `null`

#### Scenario: Identificador inexistente
- **WHEN** el identificador no existe en el catálogo
- **THEN** la API responde con un error de recurso no encontrado

### Requirement: Independencia de la fuente de datos
La API SHALL leer únicamente el esquema neutral del catálogo y SHALL NOT contener tablas, campos ni identificadores propios de ningún dataset. Una base construida con cualquier fuente que cumpla el esquema neutral SHALL funcionar con la API sin cambios de código.

#### Scenario: Base construida con otra fuente
- **WHEN** la API se inicia con una base construida solo con una fuente distinta de USDA
- **THEN** todos los endpoints de `/v1` responden correctamente con los datos de esa fuente

#### Scenario: Atribución en las respuestas
- **WHEN** una planta tiene datos de más de una fuente
- **THEN** la respuesta de detalle es una sola planta consolidada con la unión de sus datos y no indica de qué fuente proviene ninguno

### Requirement: Compatibilidad dentro de `/v1`
Dentro de `/v1` SHALL admitirse solo cambios compatibles, es decir, aditivos. Los cambios incompatibles SHALL requerir una nueva versión del prefijo. Como única excepción, mientras la API no tenga ningún consumidor, un cambio incompatible SHALL poder hacerse dentro de `/v1` si queda registrado como tal en un cambio de OpenSpec que lo justifique. La excepción SHALL dejar de aplicar cuando un primer cliente integre la API.

#### Scenario: Campo nuevo
- **WHEN** se añade un campo a una respuesta de `/v1`
- **THEN** los clientes que ignoran campos desconocidos siguen funcionando

#### Scenario: Cambio incompatible
- **WHEN** un cambio eliminaría o redefiniría un campo existente de `/v1` y la API ya tiene un cliente integrado
- **THEN** se publica bajo una nueva versión del prefijo y `/v1` conserva su contrato

#### Scenario: Cambio incompatible sin consumidores
- **WHEN** un cambio elimina o redefine un campo de `/v1` y la API no tiene ningún cliente integrado, y un cambio de OpenSpec lo registra como incompatible con su justificación
- **THEN** el cambio puede hacerse dentro de `/v1` sin nueva versión del prefijo

## REMOVED Requirements

### Requirement: Consulta de fuentes
**Reason**: La procedencia de los datos es responsabilidad del backend, que consolida y decide qué entregar. Exponer la lista de datasets al cliente rompe esa abstracción y lo ata a la estructura de las fuentes.
**Migration**: No hay consumidores del endpoint. La procedencia sigue disponible en la base para el backend (tabla `source` y tablas de atribución). `GET /v1/sources` responde 404 como cualquier ruta desconocida.
