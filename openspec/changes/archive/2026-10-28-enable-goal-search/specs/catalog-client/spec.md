# Spec Delta

## MODIFIED Requirements

### Requirement: Consumo de la API v1 del catálogo
La app SHALL usar únicamente `GET /v1/plants` (con `q`, `limit` y `offset` codificados), `GET /v1/plants/{id}` (con el id codificado en la ruta), `GET /v1/goals` y `GET /v1/goals/{goalId}/plants` (con el id codificado en la ruta y `subarea`, `limit` y `offset` codificados), con la cabecera `Accept: application/json` y la cabecera `Authorization: Bearer <token>` con el token de API de la compilación en cada petición. SHALL NOT usar otros endpoints de la API ni comunicarse con otro host, con una única excepción: descargar la imagen de una planta, en la miniatura de 500 px derivada de la URL que la API entrega en `image.url` (en el detalle o en las plantas de un objetivo), solo si es HTTPS y su host es `commons.wikimedia.org` o `upload.wikimedia.org`, y sin enviar `Authorization` ni datos de usuario. SHALL NOT enviar otras cabeceras de identidad ni datos de usuario, ni escribir el token en logs, mensajes de error o la interfaz.

#### Scenario: Listado con parámetros
- **WHEN** se pide una página del listado con consulta `lavandula`, `limit` 50 y `offset` 100
- **THEN** se envía `GET /v1/plants?q=lavandula&limit=50&offset=100` con `Accept: application/json` y `Authorization: Bearer <token>`

#### Scenario: Consulta con caracteres especiales
- **WHEN** la consulta contiene espacios, acentos o caracteres reservados de URL
- **THEN** el valor de `q` se codifica correctamente en la URL

#### Scenario: Consulta vacía
- **WHEN** la consulta está vacía o solo contiene espacios
- **THEN** se lista el catálogo sin filtrar, sin enviar texto de búsqueda

#### Scenario: Consulta larga
- **WHEN** la consulta supera los 200 caracteres
- **THEN** se recorta a 200 caracteres antes de enviarse

#### Scenario: Detalle por identificador
- **WHEN** se pide el detalle del identificador `lavandula-angustifolia`
- **THEN** se envía `GET /v1/plants/lavandula-angustifolia` con `Accept: application/json` y `Authorization: Bearer <token>`, y un identificador con caracteres reservados se codifica en la ruta

#### Scenario: Catálogo de objetivos
- **WHEN** se pide el catálogo de objetivos
- **THEN** se envía `GET /v1/goals` con `Accept: application/json` y `Authorization: Bearer <token>`

#### Scenario: Plantas de un objetivo
- **WHEN** se pide la segunda página de 20 de la subárea `digestion` del objetivo `otros-objetivos`
- **THEN** se envía `GET /v1/goals/otros-objetivos/plants?subarea=digestion&limit=20&offset=20` con `Accept: application/json` y `Authorization: Bearer <token>`, y los identificadores con caracteres reservados se codifican

#### Scenario: Plantas de un objetivo sin subárea
- **WHEN** se pide la primera página de un objetivo sin subárea
- **THEN** la petición no incluye el parámetro `subarea`

#### Scenario: Token en cada petición
- **WHEN** la app pide un listado, un detalle, el catálogo de objetivos y las plantas de un objetivo con un cliente HTTP de prueba
- **THEN** las cuatro peticiones llevan exactamente la cabecera `Authorization: Bearer <token configurado>`

#### Scenario: Imagen de un host permitido
- **WHEN** el detalle o las plantas de un objetivo traen `image.url` HTTPS con host `upload.wikimedia.org`
- **THEN** la app descarga su miniatura de 500 px sin la cabecera `Authorization` ni otras cabeceras de identidad, salvo un `User-Agent` genérico con el nombre y la versión de la app

#### Scenario: Imagen de un host no permitido
- **WHEN** `image.url` usa HTTP, o un host distinto de `commons.wikimedia.org` y `upload.wikimedia.org`
- **THEN** la app no la descarga y el pasaporte o la tarjeta se muestra como si la planta no tuviera imagen

#### Scenario: Sin otros endpoints, hosts ni datos de usuario
- **WHEN** el usuario recorre Explorar, Buscar por objetivo y el Pasaporte
- **THEN** todas las peticiones de datos son de los cuatro endpoints permitidos al host de la dirección base, con el token de API como única credencial y sin datos de usuario, salvo la descarga de la imagen de la planta

## ADDED Requirements

### Requirement: Parseo estricto de objetivos
La app SHALL validar las respuestas de objetivos según el contrato OpenAPI: en `GET /v1/goals`, `id`, `name`, `plantCount` y `subareas` (con `id`, `name` y `plantCount`) requeridos; en las plantas por objetivo, `goal`, `subarea` (que puede ser `null`), `items`, `total`, `limit` y `offset`, y en cada elemento `id`, `scientificName`, `commonNames`, `areas` y `safetyLevel` (que puede ser `null`); `hasSafety` (booleano; si falta, se toma como verdadero cuando `safetyLevel` no es `null` y como falso en otro caso), `displayName` e `image` (que puede ser `null`, con el mismo objeto que el detalle) se leen de forma tolerante como en el detalle, y si falta `displayName` se aplica la regla de nombre para mostrar. SHALL ignorar los campos desconocidos. Ante JSON inválido, un campo requerido ausente o de tipo erróneo, o un `safetyLevel` distinto de `alto`, `medio`, `bajo` o `null`, SHALL producir un error legible, sin cierre inesperado y sin completar datos con contenido inventado.

#### Scenario: Catálogo válido
- **WHEN** la API responde un catálogo con objetivos y subáreas
- **THEN** se obtienen los objetivos en el mismo orden con sus nombres, conteos y subáreas

#### Scenario: Plantas por objetivo válidas
- **WHEN** la API responde una página con elementos que tienen `displayName`, áreas, nivel de seguridad e imagen con su atribución
- **THEN** se obtienen las plantas con esos datos, el objetivo, la subárea y el total

#### Scenario: Datos nulos
- **WHEN** `subarea`, `safetyLevel` o `image` son `null`
- **THEN** se aceptan sin sustituirlos por valores inventados

#### Scenario: Campo ausente o nivel desconocido
- **WHEN** falta `items` o `areas`, tiene un tipo erróneo, o `safetyLevel` vale un texto no definido
- **THEN** se produce un error de cliente legible y no se muestran datos parciales o inventados

#### Scenario: Campos desconocidos
- **WHEN** la respuesta incluye campos que la app no conoce
- **THEN** se ignoran y la respuesta se procesa normalmente

### Requirement: Errores de objetivos
Las peticiones de objetivos SHALL tener un tiempo máximo de 10 segundos y producir los mismos errores de cliente legibles que las de plantas: reintentables para conexión, tiempo agotado, 5xx, 400 y cuerpo inválido, y de autorización para 401 y 403, sin incluir el token. Una respuesta 404 al pedir las plantas de un objetivo SHALL tratarse como «objetivo no encontrado», distinto de un error. La app SHALL NOT reintentar sola.

#### Scenario: Sin conexión o 5xx
- **WHEN** falla la conexión, se agota el tiempo o la API responde 5xx al pedir objetivos o sus plantas
- **THEN** se produce un error de cliente legible y reintentable, sin cierre inesperado

#### Scenario: No autorizado
- **WHEN** la API responde 401 al pedir el catálogo o las plantas de un objetivo
- **THEN** se produce el error legible de autorización, sin el token y distinto de «objetivo no encontrado»

#### Scenario: Objetivo no encontrado
- **WHEN** la API responde 404 al pedir las plantas de un objetivo
- **THEN** el resultado es «objetivo no encontrado» y no un error de cliente

#### Scenario: Reintento
- **WHEN** el usuario reintenta tras un error y el backend ya responde
- **THEN** la petición se repite y se obtienen los datos
