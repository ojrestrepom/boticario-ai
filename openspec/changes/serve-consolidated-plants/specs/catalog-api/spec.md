# Spec Delta

## MODIFIED Requirements

### Requirement: Listado y búsqueda de plantas
`GET /v1/plants` SHALL devolver las plantas con los elementos de la página solicitada y el total de coincidencias. Cada elemento SHALL incluir el identificador, el nombre científico, el nombre para mostrar, los nombres comunes con su idioma y la familia si existe. El orden SHALL ser total y estable: por nombre científico y, en caso de empate, por identificador. El parámetro opcional `q` SHALL filtrar por subcadena sobre el nombre científico, los sinónimos y los nombres comunes, sin distinguir mayúsculas, acentos ni espacios repetidos o exteriores. `q` SHALL buscar además en los identificadores anteriores (alias) de cada planta: la consulta normalizada, con los caracteres que no son letras ni dígitos reducidos a espacios, se compara por subcadena con el alias con sus guiones como espacios. Una planta SHALL contarse y listarse una sola vez aunque coincida por varias vías, y el alias SHALL NOT aparecer como nombre ni como planta en la respuesta. Sin `q`, o con `q` vacío o formado solo por espacios, SHALL listar todas las plantas. Los caracteres especiales de patrón, como `%` y `_`, SHALL tratarse como texto literal.

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

#### Scenario: Búsqueda por identificador anterior
- **WHEN** un cliente busca `matricaria recutita`, que no es un nombre de ninguna planta pero sí el alias `matricaria-recutita` de `matricaria-chamomilla`
- **THEN** la respuesta incluye `matricaria-chamomilla` con su nombre científico aceptado, y ningún `names`, `commonNames` ni elemento del listado contiene `matricaria-recutita` ni `Matricaria recutita` por el alias

#### Scenario: Alias con puntuación en la consulta
- **WHEN** un cliente busca `Mentha x piperita subsp. nothosubsp. piperita`, cuyo alias guardado es `mentha-x-piperita-subsp-nothosubsp-piperita`
- **THEN** la respuesta incluye `mentha-x-piperita`, porque la puntuación de la consulta se trata como espacio al compararla con el alias

#### Scenario: Alias sin duplicar resultados
- **WHEN** una consulta coincide con el nombre de una planta y también con uno de sus alias, como `rosmarinus officinalis` con `salvia-rosmarinus`
- **THEN** esa planta aparece una sola vez en la lista y cuenta una sola vez en el total

#### Scenario: Consulta sin letras ni dígitos
- **WHEN** `q` contiene solo caracteres que no son letras ni dígitos, como `%`
- **THEN** la búsqueda en alias no devuelve coincidencias y el resultado es el de la búsqueda por nombres, con `%` como texto literal

#### Scenario: Búsqueda insensible a mayúsculas, acentos y espacios
- **WHEN** un cliente busca con otras mayúsculas, con o sin acentos o con espacios repetidos o exteriores
- **THEN** la respuesta es la misma que con la forma normalizada de la consulta

#### Scenario: Sin coincidencias
- **WHEN** ninguna planta coincide con `q`
- **THEN** la respuesta tiene una lista vacía y un total de cero, no un error

### Requirement: Detalle de planta
`GET /v1/plants/{id}` SHALL devolver la identidad de la planta, su nombre para mostrar, sus nombres con tipo e idioma, la familia si existe, sus partes, sus usos (actividad, idioma y referencia con su cita, que sigue siendo la etiqueta de la referencia como hasta ahora) y el contenido consolidado y los créditos definidos en los requisitos «Contenido consolidado del detalle», «Imagen con atribución en el detalle» y «Créditos neutrales a nivel de planta». La familia SHALL ser un texto o `null`. La respuesta SHALL NOT indicar de qué dataset proviene un dato concreto. Lo ausente SHALL devolverse como `null` o lista vacía, nunca inventado.

#### Scenario: Planta existente
- **WHEN** un cliente pide el detalle de un identificador existente
- **THEN** la respuesta incluye identidad, nombre para mostrar, nombres, partes, usos y los campos consolidados, todos presentes aunque vacíos o `null`

#### Scenario: Sin información de procedencia
- **WHEN** un cliente pide el detalle de una planta con datos de una o varias fuentes
- **THEN** ningún nombre, parte, uso, grupo de uso, objetivo, nivel de seguridad ni la familia incluye campos de fuente, dataset u origen

#### Scenario: Cita de `uses` sin cambios
- **WHEN** un cliente anterior lee `uses[].reference.citation` de una planta con usos
- **THEN** el valor es la etiqueta de la referencia, igual que antes de este cambio, y la cita completa solo está en `useGroups`

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
La API SHALL entregar `displayName` en el listado y en el detalle, siempre igual al nombre para mostrar que guarda la semilla (`plant_profile.display_name`): un nombre común en español o, si la planta no tiene ninguno, su nombre científico. La API SHALL NOT elegir un nombre en otro idioma como nombre para mostrar. Si el `displayName` es un nombre común, SHALL ser el primero de los nombres comunes en el listado y en los nombres del detalle, y los demás SHALL seguir ordenados por texto e idioma. Si el `displayName` es el nombre científico, los nombres comunes que la planta tenga en otros idiomas SHALL seguir ordenados por texto e idioma, sin ninguno destacado. Los nombres científicos SHALL seguir antes que los comunes en el detalle.

#### Scenario: Nombre para mostrar primero
- **WHEN** una planta tiene los nombres comunes «Árnica», «Lavanda» y «Espliego» y la semilla elige «Lavanda»
- **THEN** su `displayName` es «Lavanda» y los nombres comunes salen como «Lavanda», «Árnica», «Espliego»

#### Scenario: Sin nombre común
- **WHEN** la planta no tiene nombres comunes
- **THEN** `displayName` es el nombre científico y en el detalle no hay nombres de tipo común

#### Scenario: Solo nombres en otros idiomas
- **WHEN** la planta tiene como único nombre común «Velvetleaf» (idioma `en`) y la semilla le da como nombre para mostrar su nombre científico `Abutilon theophrasti`
- **THEN** `displayName` es `Abutilon theophrasti`, `Velvetleaf` está entre sus nombres comunes y ningún nombre común va destacado ni se convierte en el nombre para mostrar

#### Scenario: Varios nombres en otros idiomas
- **WHEN** la planta tiene los nombres comunes «Velvetleaf» (`en`) y «Butterprint» (`en`) y su nombre para mostrar es el científico
- **THEN** los nombres comunes salen ordenados por texto e idioma («Butterprint», «Velvetleaf») y `displayName` sigue siendo el nombre científico

### Requirement: Contenido consolidado del detalle
El detalle SHALL incluir siempre estos campos, con `null` o lista vacía cuando la planta no tiene el dato: `synonyms` (sinónimos científicos, sin repetir el nombre aceptado), `description` (texto o `null`), `origin` (texto o `null`), `oil` (objeto con `type` o `null`), `useGroups` (grupos de uso tradicional, cada uno con `activity`, `activitySource`, `count`, `countries` y `references`, cada una con `id`, `citation` y `resolved`; la `citation` de cada referencia es el texto completo de la cita que guarda la semilla y no la etiqueta corta de la referencia; una cita sin obra identificada lleva `id` nulo, `resolved` falso y la cita «<clave> (sin resolver)»), `goals` (cada objetivo con `id`, `name`, `subarea` o `null`, `area`, `evidence` y `references`) y `safety` (objeto con `level` igual a `alto`, `medio`, `bajo` o `null`, `text` y `references`, o `null` solo cuando no hay ningún dato de precauciones). Los grupos SHALL ordenarse por `count` descendente y luego por actividad; los objetivos por nombre. Los textos visibles SHALL estar en español y no contener dosis ni promesas de eficacia, porque la semilla los valida.

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

#### Scenario: Seguridad sin nivel
- **WHEN** las fuentes traen advertencias para la planta (por ejemplo las contraindicaciones de la EMA para el eucalipto) pero ninguna fija un nivel
- **THEN** `safety` es un objeto con `level` igual a `null`, el `text` y las `references`, y la API no inventa un nivel ni lo sustituye por `null` en todo el objeto

#### Scenario: Cita completa en los grupos de uso
- **WHEN** un grupo de uso de la lavanda cita la obra de clave `Steinmetz`, cuya etiqueta de referencia es «USDA Dr. Duke: referencia Steinmetz» y cuyo texto completo en la semilla es «Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam.»
- **THEN** la referencia de `useGroups` lleva `citation` igual al texto completo y no a la etiqueta

#### Scenario: Grupo de uso con una cita sin resolver
- **WHEN** un grupo de uso tiene una cita resuelta y otra sin obra identificada
- **THEN** `useGroups` incluye el grupo con ambas referencias, la resuelta con `resolved` verdadero y su cita, y la otra con `id` nulo, `resolved` falso y la cita «<clave> (sin resolver)»

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
El detalle SHALL incluir `credits`, una lista de los datasets que respaldan los datos de la planta, cada uno con `name`, `license`, `licenseUrl` (o `null`), `attribution` y `url` (o `null`). La lista SHALL ser a nivel de planta, sin repeticiones y ordenada por nombre. La `licenseUrl` de cada entrada SHALL leerse del dato de la fuente en la base (`source.license_url`), sin derivarla del texto de la licencia, y SHALL ser `null` cuando la fuente no tiene una. La lista SHALL NOT indicar qué campo proviene de qué dataset. Si la descripción de la planta resume una obra con licencia CC BY-SA, `credits` SHALL incluir esa obra con su licencia y su enlace.

#### Scenario: Créditos de una planta con varias fuentes
- **WHEN** se pide el detalle de una planta con datos de WCVP, la EMA y Wikipedia
- **THEN** `credits` tiene una entrada por cada uno, con su licencia y atribución, y ninguna indica un campo

#### Scenario: URL de licencia por fuente
- **WHEN** se pide el detalle de una planta cuya descripción resume Wikipedia y que tiene un objetivo de la EMA
- **THEN** el crédito de Wikipedia lleva `licenseUrl` igual a `https://creativecommons.org/licenses/by-sa/4.0/` y el de la EMA lleva `licenseUrl` igual a `null`

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
`GET /v1/plants/{id}` SHALL resolver un identificador que no es el de ninguna planta pero sí un alias guardado de una planta, y SHALL responder 200 con el detalle de la planta canónica, con su identificador canónico en el campo `id` y en la cabecera `Content-Location`. Un identificador que sea el de una planta SHALL resolverse siempre a esa planta. La API SHALL NOT responder con redirección. El listado SHALL NOT incluir alias como plantas, aunque `q` los use para encontrar la planta canónica.

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
La API SHALL omitir de `goals` un objetivo marcado como pendiente de revisión (`plant_goal.pending_review`) antes de publicarse, como el objetivo `relajacion-estres` de una planta con interacciones graves en el área de estrés y ánimo. La API SHALL NOT exponer los `reviewFlags` ni indicar que un contenido se omitió. SHALL omitir de `useGroups` los grupos marcados como pendientes de revisión (`plant_use_group.pending_review`), es decir, los que no tienen ninguna cita resuelta; un grupo con al menos una cita resuelta SHALL servirse con todas sus citas, aunque otra esté sin resolver. El resto del detalle de la planta SHALL servirse con normalidad.

#### Scenario: Objetivo condicionado
- **WHEN** una planta tiene el objetivo `relajacion-estres` marcado como pendiente de revisión por interacciones graves en estrés y ánimo
- **THEN** su detalle no incluye ese objetivo en `goals`, y el resto de sus objetivos y campos se sirve igual

#### Scenario: Grupo sin ninguna cita resuelta
- **WHEN** un grupo de uso tiene `pending_review` verdadero porque ninguna de sus citas está resuelta
- **THEN** su detalle no incluye ese grupo en `useGroups` ni genera filas en `uses`, y el resto de la planta se sirve igual

#### Scenario: Grupo con una cita resuelta y otra sin resolver
- **WHEN** un grupo tiene `pending_review` falso con una cita sin resolver y el registro conserva el flag `cita-sin-resolver`
- **THEN** el grupo se sirve completo, con la cita sin resolver marcada, y el detalle no expone el flag

#### Scenario: Planta con otros flags
- **WHEN** una planta tiene un `reviewFlag` de identidad ambigua o de grupo partido
- **THEN** su detalle se sirve completo y no contiene ningún campo con los flags

#### Scenario: Sin flags en las respuestas
- **WHEN** se inspeccionan el detalle, el listado y el documento OpenAPI
- **THEN** ningún campo expone los `reviewFlags` ni sus códigos
