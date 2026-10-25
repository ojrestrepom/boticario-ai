# Spec Delta

## MODIFIED Requirements

### Requirement: Consumo de la API v1 del catálogo
La app SHALL usar únicamente `GET /v1/plants` (con `q`, `limit` y `offset` codificados) y `GET /v1/plants/{id}` (con el id codificado en la ruta), con la cabecera `Accept: application/json` y la cabecera `Authorization: Bearer <token>` con el token de API de la compilación en cada petición. SHALL NOT usar otros endpoints de la API ni comunicarse con otro host, con una única excepción: descargar la imagen de una planta desde la URL que la API entrega en `image.url`, solo si es HTTPS y su host es `commons.wikimedia.org` o `upload.wikimedia.org`, y sin enviar `Authorization` ni datos de usuario. SHALL NOT enviar otras cabeceras de identidad ni datos de usuario, ni escribir el token en logs, mensajes de error o la interfaz.

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

#### Scenario: Token en cada petición
- **WHEN** la app pide un listado y un detalle con un cliente HTTP de prueba
- **THEN** las dos peticiones llevan exactamente la cabecera `Authorization: Bearer <token configurado>`

#### Scenario: Sin otros endpoints, hosts ni datos de usuario
- **WHEN** el usuario recorre Explorar y el Pasaporte
- **THEN** todas las peticiones son de los dos endpoints permitidos al host de la dirección base, con el token de API como única credencial y sin datos de usuario, salvo la descarga de la imagen de la planta

#### Scenario: Imagen de un host permitido
- **WHEN** el detalle trae `image.url` HTTPS con host `upload.wikimedia.org`
- **THEN** la app la descarga sin la cabecera `Authorization` ni otras cabeceras de identidad

#### Scenario: Imagen de un host no permitido
- **WHEN** `image.url` usa HTTP, o un host distinto de `commons.wikimedia.org` y `upload.wikimedia.org`
- **THEN** la app no la descarga y el pasaporte se muestra como si la planta no tuviera imagen

### Requirement: Parseo estricto de las respuestas
La app SHALL validar las respuestas según el contrato OpenAPI de la API: campos requeridos presentes y con el tipo correcto. SHALL ignorar los campos desconocidos y SHALL aceptar `family` igual a `null`. Los campos que el cambio `serve-consolidated-plants` añadió al detalle y al listado (nombre para mostrar, sinónimos, descripción, origen, aceite, grupos de uso, objetivos, seguridad, imagen y créditos) SHALL leerse de forma tolerante: un campo ausente equivale a `null` o a lista vacía, pero uno presente con un tipo erróneo SHALL producir un error. Ante JSON inválido o un campo requerido ausente o de tipo erróneo, SHALL producir un error legible, sin cierre inesperado y sin completar datos con contenido inventado.

#### Scenario: Listado válido
- **WHEN** la API responde un listado con `items`, `total`, `limit` y `offset`
- **THEN** se obtienen las plantas con identificador, nombre científico, nombre para mostrar, nombres comunes con idioma y familia, y el total

#### Scenario: Detalle válido
- **WHEN** la API responde un detalle con nombres (con `kind` e idioma), partes, usos (con actividad, idioma y referencia con cita) y los campos consolidados
- **THEN** se obtiene la planta completa con esos datos, incluidos los grupos de uso con países y citas, los objetivos con su área, las precauciones con su nivel (o sin él), la imagen con su atribución y los créditos

#### Scenario: Precauciones sin nivel
- **WHEN** `safety` llega con `level` igual a `null`, un `text` y referencias
- **THEN** se obtiene la seguridad sin nivel con su texto y sus citas, sin tratarla como error ni como ausencia de datos

#### Scenario: Cita sin resolver
- **WHEN** una referencia de un grupo de uso llega con `id` nulo, `resolved` falso y la cita «<clave> (sin resolver)»
- **THEN** la referencia se acepta y conserva su marca de no resuelta para que la interfaz pueda atenuarla

#### Scenario: Familia nula
- **WHEN** el campo `family` es `null`
- **THEN** la planta se acepta sin familia

#### Scenario: Campos desconocidos
- **WHEN** la respuesta incluye campos que la app no conoce
- **THEN** se ignoran y la respuesta se procesa normalmente

#### Scenario: Campo requerido ausente o de tipo erróneo
- **WHEN** falta un campo requerido, como `items` o `scientificName`, o tiene un tipo distinto del esperado
- **THEN** se produce un error de cliente legible y no se muestran datos parciales o inventados

#### Scenario: Backend anterior sin los campos nuevos
- **WHEN** el detalle no trae `description`, `origin`, `oil`, `useGroups`, `goals`, `safety`, `image`, `credits` ni `displayName`
- **THEN** la planta se acepta con esos datos vacíos o `null`, su nombre para mostrar sale de la regla de respaldo y sus usos se derivan de `uses`, uno por actividad, con la referencia de cada uno

#### Scenario: Campo nuevo con tipo erróneo
- **WHEN** `goals` llega como un texto, o el `level` de `safety` no es `alto`, `medio`, `bajo` ni `null`, o una referencia de un grupo de uso trae `resolved` con un tipo distinto de booleano
- **THEN** se produce un error de cliente legible y no se muestran datos parciales

#### Scenario: JSON inválido
- **WHEN** el cuerpo de una respuesta con éxito no es JSON válido
- **THEN** se produce un error de cliente legible, sin cierre inesperado

### Requirement: Nombre para mostrar
La app SHALL mostrar como nombre principal de una planta su `displayName` y como nombre secundario su nombre científico, salvo que ambos coincidan. Si la respuesta no trae `displayName`, SHALL usar su primer nombre común, en el idioma que venga, y, si tampoco hay, su nombre científico como principal sin nombre secundario. SHALL NOT traducir ni inventar nombres.

#### Scenario: Planta con nombre común
- **WHEN** una planta tiene `displayName` «Lavanda» y el científico `Lavandula angustifolia`
- **THEN** el principal es «Lavanda» y el secundario es `Lavandula angustifolia`

#### Scenario: Planta sin nombre común
- **WHEN** una planta no tiene nombres comunes y su `displayName` es su nombre científico, o la respuesta no trae `displayName` ni nombres comunes
- **THEN** el principal es su nombre científico y no hay nombre secundario

#### Scenario: Backend sin nombre para mostrar
- **WHEN** la respuesta no trae `displayName` y la planta tiene el nombre común «English Lavender»
- **THEN** el principal es «English Lavender» y el secundario es el nombre científico

#### Scenario: Idioma del nombre común
- **WHEN** el nombre para mostrar o el primer nombre común está en un idioma distinto del español, como `en` o `und`
- **THEN** se muestra tal cual, sin traducirlo
