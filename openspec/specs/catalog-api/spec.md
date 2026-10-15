# catalog-api Specification

## Purpose
Define la API HTTP de solo lectura v1 que sirve el catálogo de plantas desde la base neutral, con errores estandarizados, documento OpenAPI y arranque configurable, sin depender de ningún dataset concreto.

## Requirements

### Requirement: API de solo lectura sin autenticación
La API SHALL ofrecer únicamente operaciones de lectura bajo el prefijo `/v1`, sin autenticación y sin manejar datos de usuario. Las peticiones con métodos que no son de lectura SHALL rechazarse con un error de método no permitido.

#### Scenario: Consulta sin credenciales
- **WHEN** un cliente consulta cualquier recurso de lectura sin credenciales
- **THEN** la API responde con los datos solicitados

#### Scenario: Método de escritura
- **WHEN** un cliente envía una petición de escritura a un recurso de `/v1`
- **THEN** la API responde 405 con `application/problem+json` y no modifica ningún dato

### Requirement: Listado y búsqueda de plantas
`GET /v1/plants` SHALL devolver las plantas con los elementos de la página solicitada y el total de coincidencias. Cada elemento SHALL incluir el identificador, el nombre científico, los nombres comunes con su idioma y la familia si existe. El orden SHALL ser total y estable: por nombre científico y, en caso de empate, por identificador. El parámetro opcional `q` SHALL filtrar por subcadena sobre el nombre científico y los nombres comunes, sin distinguir mayúsculas, acentos ni espacios repetidos o exteriores. Sin `q`, o con `q` vacío o formado solo por espacios, SHALL listar todas las plantas. Los caracteres especiales de patrón, como `%` y `_`, SHALL tratarse como texto literal.

#### Scenario: Listado sin búsqueda
- **WHEN** un cliente pide `GET /v1/plants` sin `q`
- **THEN** la respuesta incluye las plantas en orden de nombre científico y el total de plantas del catálogo

#### Scenario: Contenido de cada elemento
- **WHEN** un cliente consulta el listado
- **THEN** cada elemento incluye identificador, nombre científico, nombres comunes con su idioma y familia (o `null` si no existe)

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

#### Scenario: Búsqueda insensible a mayúsculas, acentos y espacios
- **WHEN** un cliente busca con otras mayúsculas, con o sin acentos o con espacios repetidos o exteriores
- **THEN** la respuesta es la misma que con la forma normalizada de la consulta

#### Scenario: Sin coincidencias
- **WHEN** ninguna planta coincide con `q`
- **THEN** la respuesta tiene una lista vacía y un total de cero, no un error

### Requirement: Paginación
El listado SHALL admitir los parámetros `limit` y `offset`. El valor por defecto de `limit` SHALL ser 20 y su máximo 100. La respuesta SHALL incluir el total de coincidencias, independiente de la página.

#### Scenario: Límite por defecto
- **WHEN** un cliente pide el listado sin `limit` y existen más de 20 coincidencias
- **THEN** la respuesta incluye 20 elementos y el total completo

#### Scenario: Desplazamiento
- **WHEN** un cliente pide un `offset` con un `limit` dados
- **THEN** la respuesta contiene los elementos que siguen en el orden definido a partir de esa posición

#### Scenario: Desplazamiento más allá del total
- **WHEN** el `offset` supera el total de coincidencias
- **THEN** la respuesta tiene una lista vacía y conserva el total

#### Scenario: Límite fuera de rango
- **WHEN** el `limit` es cero, negativo o mayor que 100
- **THEN** la API responde con un error de parámetros inválidos

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

### Requirement: Endpoint de salud
La API SHALL exponer `GET /healthz`, fuera del prefijo `/v1`, que informe que el servicio está activo.

#### Scenario: Servicio activo
- **WHEN** un cliente pide `GET /healthz` con la API en marcha
- **THEN** la API responde 200

### Requirement: Errores estandarizados
Los errores SHALL responder con el tipo de medio `application/problem+json` según RFC 9457: 400 para parámetros inválidos, 404 para recurso no encontrado, 405 para método no permitido y 500 para fallos internos. Los errores 500 SHALL NOT exponer detalles internos como rutas, consultas o mensajes de la base de datos.

#### Scenario: Parámetro inválido
- **WHEN** un cliente envía un parámetro con un valor inválido, como un `limit` no numérico
- **THEN** la API responde 400 con `application/problem+json` que indica el parámetro afectado

#### Scenario: Recurso no encontrado
- **WHEN** un cliente pide un recurso inexistente
- **THEN** la API responde 404 con `application/problem+json`

#### Scenario: Método no permitido
- **WHEN** un cliente usa un método no admitido en un recurso existente
- **THEN** la API responde 405 con `application/problem+json`

#### Scenario: Fallo interno
- **WHEN** ocurre un fallo interno al atender una petición
- **THEN** la API responde 500 con `application/problem+json` genérico y sin detalles internos

### Requirement: Formato de las respuestas
Las respuestas JSON SHALL usar nombres de campo en camelCase. Los datos ausentes SHALL representarse como `null` o lista vacía.

#### Scenario: Nombres de campo
- **WHEN** un cliente consulta cualquier recurso de `/v1`
- **THEN** todos los campos de la respuesta usan camelCase

### Requirement: Independencia de la fuente de datos
La API SHALL leer únicamente el esquema neutral del catálogo y SHALL NOT contener tablas, campos ni identificadores propios de ningún dataset. Una base construida con cualquier fuente que cumpla el esquema neutral SHALL funcionar con la API sin cambios de código.

#### Scenario: Base construida con otra fuente
- **WHEN** la API se inicia con una base construida solo con una fuente distinta de USDA
- **THEN** todos los endpoints de `/v1` responden correctamente con los datos de esa fuente

#### Scenario: Atribución en las respuestas
- **WHEN** una planta tiene datos de más de una fuente
- **THEN** la respuesta de detalle es una sola planta consolidada con la unión de sus datos y no indica de qué fuente proviene ninguno

### Requirement: Documento OpenAPI
La API SHALL tener un documento OpenAPI generado desde su código y versionado en el repositorio. Una verificación automática SHALL fallar si el documento versionado no coincide con el generado por el código actual.

#### Scenario: Documento al día
- **WHEN** el documento versionado coincide con el generado desde el código
- **THEN** la verificación pasa

#### Scenario: Documento desactualizado
- **WHEN** el código cambia un contrato sin regenerar el documento versionado
- **THEN** la verificación falla

### Requirement: Arranque y configuración
La API SHALL tomar la ruta de la base de datos de una variable de entorno o un argumento, y su dirección de `HOST` y `PORT`, con `127.0.0.1:8080` por defecto. SHALL abrir la base en modo de solo lectura. El arranque SHALL fallar con un mensaje claro si la base no existe o si su versión de esquema no es compatible.

#### Scenario: Configuración por defecto
- **WHEN** la API se inicia sin `HOST` ni `PORT`
- **THEN** escucha en `127.0.0.1:8080`

#### Scenario: Base ausente
- **WHEN** la ruta configurada no contiene una base de datos
- **THEN** la API no arranca y el mensaje indica la ruta y cómo construir la base

#### Scenario: Versión de esquema incompatible
- **WHEN** la base tiene una versión de esquema que la API no soporta
- **THEN** la API no arranca y el mensaje indica la versión encontrada y las soportadas

#### Scenario: Base de solo lectura
- **WHEN** la API está en marcha
- **THEN** ninguna petición modifica la base de datos

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

### Requirement: Apagado ordenado con tiempo máximo
Al recibir SIGTERM o Ctrl-C, la API SHALL dejar de aceptar conexiones nuevas y esperar a las peticiones en curso como máximo 2 s. La API SHALL terminar con código 0 tanto si todas las peticiones terminaron como si se agotó el plazo. Al terminar SHALL registrar «apagado completado»; si se agotó el plazo, SHALL registrar antes un aviso de apagado forzado por conexiones abiertas tras 2 s.

#### Scenario: Conexiones inactivas
- **WHEN** la API no tiene peticiones en curso y recibe SIGTERM
- **THEN** termina de inmediato con código 0 y el log contiene «apagado completado»

#### Scenario: Conexión colgada
- **WHEN** un cliente mantiene una conexión abierta con cabeceras incompletas y la API recibe SIGTERM
- **THEN** la API termina al agotarse el plazo de 2 s con código 0, y el log contiene el aviso de apagado forzado y «apagado completado»
