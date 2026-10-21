# Spec Delta

## MODIFIED Requirements

### Requirement: Listado y búsqueda de plantas
`GET /v1/plants` SHALL devolver las plantas con los elementos de la página solicitada y el total de coincidencias. Cada elemento SHALL incluir el identificador, el nombre científico, el nombre para mostrar, los nombres comunes con su idioma y la familia si existe. El orden SHALL ser total y estable: por nombre científico y, en caso de empate, por identificador. El parámetro opcional `q` SHALL filtrar por subcadena sobre el nombre científico, los sinónimos y los nombres comunes, sin distinguir mayúsculas, acentos ni espacios repetidos o exteriores. Sin `q`, o con `q` vacío o formado solo por espacios, SHALL listar todas las plantas. Los caracteres especiales de patrón, como `%` y `_`, SHALL tratarse como texto literal.

#### Scenario: Listado sin búsqueda
- **WHEN** un cliente pide `GET /v1/plants` sin `q`
- **THEN** la respuesta incluye las plantas en orden de nombre científico y el total de plantas del catálogo

#### Scenario: Contenido de cada elemento
- **WHEN** un cliente consulta el listado
- **THEN** cada elemento incluye identificador, nombre científico, nombre para mostrar (texto), nombres comunes con su idioma y familia (o `null` si no existe)

#### Scenario: Nombre para mostrar en el listado
- **WHEN** una planta tiene el nombre para mostrar «Lavanda» y otros nombres comunes
- **THEN** su elemento del listado lleva `displayName` igual a «Lavanda», y esa misma cadena es el primer elemento de sus nombres comunes

#### Scenario: Planta sin nombre común
- **WHEN** una planta no tiene nombres comunes
- **THEN** su `displayName` es su nombre científico y sus nombres comunes son una lista vacía

#### Scenario: Orden estable en empate
- **WHEN** dos plantas tienen el mismo nombre científico
- **THEN** se ordenan por identificador y la paginación no repite ni omite elementos

#### Scenario: Consulta vacía
- **WHEN** `q` está vacío o contiene solo espacios
- **THEN** la respuesta es la misma que sin `q`

#### Scenario: Caracteres de patrón literales
- **WHEN** `q` contiene `%` o `_`
- **THEN** se buscan como texto literal y no actúan como comodines

#### Scenario: Búsqueda por nombre científico
- **WHEN** un cliente pide `GET /v1/plants?q=lavandula`
- **THEN** la respuesta incluye las plantas cuyo nombre científico contiene esa subcadena y el total de coincidencias

#### Scenario: Búsqueda por nombre común
- **WHEN** un cliente busca una subcadena de un nombre común de una planta
- **THEN** la respuesta incluye esa planta

#### Scenario: Búsqueda por sinónimo
- **WHEN** un cliente busca `rosmarinus officinalis`, un sinónimo científico de la planta `salvia-rosmarinus`
- **THEN** la respuesta incluye `salvia-rosmarinus`, con su nombre científico aceptado

#### Scenario: Búsqueda insensible a mayúsculas, acentos y espacios
- **WHEN** un cliente busca con otras mayúsculas, con o sin acentos o con espacios repetidos o exteriores
- **THEN** la respuesta es la misma que con la forma normalizada de la consulta

#### Scenario: Sin coincidencias
- **WHEN** ninguna planta coincide con `q`
- **THEN** la respuesta tiene una lista vacía y un total de cero, no un error

### Requirement: Detalle de planta
`GET /v1/plants/{id}` SHALL devolver la identidad de la planta, su nombre para mostrar, sus nombres con tipo e idioma, la familia si existe, sus partes, sus usos (actividad, idioma y referencia con su cita) y el contenido consolidado y los créditos definidos en los requisitos «Contenido consolidado del detalle», «Imagen con atribución en el detalle» y «Créditos neutrales a nivel de planta». La familia SHALL ser un texto o `null`. La respuesta SHALL NOT indicar de qué dataset proviene un dato concreto. Lo ausente SHALL devolverse como `null` o lista vacía, nunca inventado.

#### Scenario: Planta existente
- **WHEN** un cliente pide el detalle de un identificador existente
- **THEN** la respuesta incluye identidad, nombre para mostrar, nombres, partes, usos y los campos consolidados, todos presentes aunque vacíos o `null`

#### Scenario: Sin información de procedencia
- **WHEN** un cliente pide el detalle de una planta con datos de una o varias fuentes
- **THEN** ningún nombre, parte, uso, grupo de uso, objetivo, nivel de seguridad ni la familia incluye campos de fuente, dataset u origen

#### Scenario: Planta sin usos
- **WHEN** la planta no tiene usos en el catálogo
- **THEN** la respuesta tiene listas de usos y de grupos de uso vacías

#### Scenario: Familia presente
- **WHEN** la planta tiene familia en el catálogo
- **THEN** el campo de familia es un texto

#### Scenario: Familia ausente
- **WHEN** ninguna fuente aporta la familia de la planta
- **THEN** el campo de familia es `null`

#### Scenario: Identificador inexistente
- **WHEN** el identificador no existe en el catálogo ni como identificador anterior
- **THEN** la API responde con un error de recurso no encontrado

### Requirement: Independencia de la fuente de datos
La API SHALL leer únicamente el esquema neutral del catálogo y SHALL NOT contener tablas, campos ni identificadores propios de ningún dataset en su código ni en su contrato. Una base construida con cualquier fuente que cumpla el esquema neutral SHALL funcionar con la API sin cambios de código. Los nombres de dataset y de licencia que la API devuelve en los créditos son datos de la base, no parte del contrato.

#### Scenario: Base construida con otra fuente
- **WHEN** la API se inicia con una base construida solo con una fuente distinta de USDA
- **THEN** todos los endpoints de `/v1` responden correctamente con los datos de esa fuente

#### Scenario: Atribución en las respuestas
- **WHEN** una planta tiene datos de más de una fuente
- **THEN** la respuesta de detalle es una sola planta consolidada, con la unión de sus datos, y los datasets que la respaldan aparecen solo como la lista neutral de créditos de la planta, sin indicar de qué fuente proviene cada dato

#### Scenario: Contrato sin nombres de dataset
- **WHEN** se revisan los nombres de campos y esquemas del documento OpenAPI
- **THEN** ninguno contiene el nombre de un dataset concreto

## ADDED Requirements

### Requirement: Nombre para mostrar y orden de los nombres comunes
La API SHALL entregar `displayName` en el listado y en el detalle: el nombre para mostrar elegido en la semilla o, si la planta no tiene nombres comunes, su nombre científico. Cuando la planta tiene nombres comunes, el nombre para mostrar SHALL ser el primero de sus nombres comunes en el listado y en los nombres del detalle, y los demás SHALL seguir ordenados por texto e idioma. Los nombres científicos SHALL seguir antes que los comunes en el detalle.

#### Scenario: Nombre para mostrar primero
- **WHEN** una planta tiene los nombres comunes «Árnica», «Lavanda» y «Espliego» y la semilla elige «Lavanda»
- **THEN** su `displayName` es «Lavanda» y los nombres comunes salen como «Lavanda», «Árnica», «Espliego»

#### Scenario: Sin nombre común
- **WHEN** la planta no tiene nombres comunes
- **THEN** `displayName` es el nombre científico y en el detalle no hay nombres de tipo común

### Requirement: Contenido consolidado del detalle
El detalle SHALL incluir siempre estos campos, con `null` o lista vacía cuando la planta no tiene el dato: `synonyms` (sinónimos científicos, sin repetir el nombre aceptado), `description` (texto o `null`), `origin` (texto o `null`), `oil` (objeto con `type` o `null`), `useGroups` (grupos de uso tradicional, cada uno con `activity`, `activitySource`, `count`, `countries` y `references` con su cita), `goals` (cada objetivo con `id`, `name`, `subarea` o `null`, `area`, `evidence` y `references`) y `safety` (objeto con `level` igual a `alto`, `medio` o `bajo`, `text` y `references`, o `null`). Los grupos SHALL ordenarse por `count` descendente y luego por actividad; los objetivos por nombre. Los textos visibles SHALL estar en español y no contener dosis ni promesas de eficacia, porque la semilla los valida.

#### Scenario: Planta con todos los campos
- **WHEN** se pide el detalle de una planta con descripción, origen, aceite esencial, usos agrupados, un objetivo y nivel de seguridad
- **THEN** la respuesta lleva esos campos con sus valores y cada grupo de uso, objetivo y seguridad lleva sus referencias con cita

#### Scenario: Planta con campos vacíos
- **WHEN** se pide el detalle de una planta sin descripción, origen, aceite, usos, objetivos ni datos de seguridad
- **THEN** `description`, `origin`, `oil` y `safety` son `null`, y `synonyms`, `useGroups` y `goals` son listas vacías

#### Scenario: Grupos de uso
- **WHEN** una planta tiene un grupo de uso con 12 registros de 3 países y otro con 2 registros
- **THEN** `useGroups` los devuelve en ese orden, el primero con `count` 12 y sus tres países

#### Scenario: Seguridad sin datos
- **WHEN** ninguna fuente de seguridad menciona la planta
- **THEN** `safety` es `null`, y la API no lo sustituye por un nivel

#### Scenario: Objetivo de la EMA
- **WHEN** la planta tiene el objetivo `cuidado-de-la-piel` respaldado por una monografía de la EMA
- **THEN** `goals` incluye un objeto con ese `id`, su nombre en español, el área y el tipo de documento de la EMA y la referencia con cita

#### Scenario: Subárea de otros objetivos
- **WHEN** la planta tiene el objetivo `otros-objetivos` con la subárea de digestión
- **THEN** el objeto lleva `subarea` con el nombre de esa subárea

### Requirement: Imagen con atribución en el detalle
El detalle SHALL incluir `image`, un objeto con `url`, `pageUrl`, `author`, `license`, `licenseUrl` y `attributionRequired`, o `null` si la planta no tiene imagen con licencia aceptada. La API SHALL NOT servir los bytes de la imagen ni consultar la red: solo entrega los datos del registro. Un `image` presente SHALL llevar licencia y página del archivo.

#### Scenario: Imagen con licencia
- **WHEN** la planta tiene una imagen de Commons con licencia CC BY-SA
- **THEN** `image` incluye la URL, la página del archivo, el autor, la licencia, la URL de la licencia y `attributionRequired` verdadero

#### Scenario: Sin imagen
- **WHEN** la planta no tiene imagen
- **THEN** `image` es `null`

#### Scenario: Sin acceso a la red
- **WHEN** la API atiende el detalle de una planta con imagen en un entorno sin red
- **THEN** responde 200 con los datos de la imagen, porque no descarga nada

### Requirement: Créditos neutrales a nivel de planta
El detalle SHALL incluir `credits`, una lista de los datasets que respaldan los datos de la planta, cada uno con `name`, `license`, `licenseUrl` (o `null`), `attribution` y `url` (o `null`). La lista SHALL ser a nivel de planta, sin repeticiones y ordenada por nombre. La lista SHALL NOT indicar qué campo proviene de qué dataset. Si la descripción de la planta resume una obra con licencia CC BY-SA, `credits` SHALL incluir esa obra con su licencia y su enlace.

#### Scenario: Créditos de una planta con varias fuentes
- **WHEN** se pide el detalle de una planta con datos de WCVP, la EMA y Wikipedia
- **THEN** `credits` tiene una entrada por cada uno, con su licencia y atribución, y ninguna indica un campo

#### Scenario: Sin repeticiones
- **WHEN** varios datos de la planta provienen del mismo dataset
- **THEN** `credits` lo incluye una sola vez

#### Scenario: Descripción derivada de Wikipedia
- **WHEN** la descripción resume el artículo de Wikipedia de la planta
- **THEN** `credits` incluye Wikipedia con la licencia CC BY-SA 4.0 y el enlace al artículo

#### Scenario: Planta sin créditos
- **WHEN** una planta no tiene ningún dato con dataset registrado
- **THEN** `credits` es una lista vacía

### Requirement: Identificadores anteriores
`GET /v1/plants/{id}` SHALL resolver un identificador que no es el de ninguna planta pero sí un alias guardado de una planta, y SHALL responder 200 con el detalle de la planta canónica, con su identificador canónico en el campo `id` y en la cabecera `Content-Location`. Un identificador que sea el de una planta SHALL resolverse siempre a esa planta. La API SHALL NOT responder con redirección. El listado SHALL NOT incluir alias como plantas.

#### Scenario: Alias de un renombre
- **WHEN** un cliente pide `GET /v1/plants/rosmarinus-officinalis` y esa cadena es un alias de `salvia-rosmarinus`
- **THEN** la API responde 200 con el detalle de `salvia-rosmarinus`, `id` igual a `salvia-rosmarinus` y `Content-Location: /v1/plants/salvia-rosmarinus`

#### Scenario: Identificador canónico
- **WHEN** un cliente pide el identificador canónico de una planta
- **THEN** la API responde 200 sin la cabecera `Content-Location` de alias

#### Scenario: Identificador desconocido
- **WHEN** el identificador no es el de una planta ni un alias
- **THEN** la API responde 404 con `application/problem+json`

#### Scenario: Alias sin autorización
- **WHEN** un cliente pide un alias sin token
- **THEN** la API responde 401, igual que para cualquier ruta de `/v1`

#### Scenario: Alias fuera del listado
- **WHEN** un cliente lista el catálogo
- **THEN** ningún elemento tiene como identificador un alias que no sea el identificador canónico de una planta

### Requirement: Contenido pendiente de revisión no se sirve
La API SHALL omitir de `goals` un objetivo marcado como pendiente de revisión (`plant_goal.pending_review`) antes de publicarse, como el objetivo `relajacion-estres` de una planta con interacciones graves en el área de estrés y ánimo. La API SHALL NOT exponer los `reviewFlags` ni indicar que un contenido se omitió. El resto del detalle de la planta SHALL servirse con normalidad.

#### Scenario: Objetivo condicionado
- **WHEN** una planta tiene el objetivo `relajacion-estres` marcado como pendiente de revisión por interacciones graves en estrés y ánimo
- **THEN** su detalle no incluye ese objetivo en `goals`, y el resto de sus objetivos y campos se sirve igual

#### Scenario: Planta con otros flags
- **WHEN** una planta tiene un `reviewFlag` de identidad ambigua o de grupo partido
- **THEN** su detalle se sirve completo y no contiene ningún campo con los flags

#### Scenario: Sin flags en las respuestas
- **WHEN** se inspeccionan el detalle, el listado y el documento OpenAPI
- **THEN** ningún campo expone los `reviewFlags` ni sus códigos
