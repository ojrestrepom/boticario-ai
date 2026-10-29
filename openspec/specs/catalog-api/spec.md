# catalog-api Specification

## Purpose
Define la API HTTP de solo lectura v1 que sirve el catálogo de plantas y sus objetivos de uso desde la base neutral, con errores estandarizados, documento OpenAPI y arranque configurable, sin depender de ningún dataset concreto.

## Requirements

### Requirement: API de solo lectura con autorización por token
La API SHALL ofrecer únicamente operaciones de lectura bajo el prefijo `/v1`, protegidas por un token de API (véase «Autorización por token de API en `/v1`»), sin cuentas de usuario y sin manejar datos de usuario. Las peticiones con métodos que no son de lectura SHALL rechazarse con un error de método no permitido.

#### Scenario: Consulta con token
- **WHEN** un cliente consulta cualquier recurso de lectura de `/v1` con un token válido
- **THEN** la API responde con los datos solicitados

#### Scenario: Consulta sin credenciales
- **WHEN** un cliente consulta cualquier recurso de `/v1` sin token
- **THEN** la API responde 401 con `application/problem+json` y no devuelve datos del catálogo

#### Scenario: Método de escritura
- **WHEN** un cliente con un token válido envía una petición de escritura a un recurso de `/v1`
- **THEN** la API responde 405 con `application/problem+json` y no modifica ningún dato

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

### Requirement: Endpoint de salud
La API SHALL exponer `GET /health`, fuera del prefijo `/v1`, que informe que el servicio está activo. El endpoint SHALL ser público: SHALL responder sin token, porque lo consultan la sonda de arranque de Cloud Run y la verificación posterior al despliegue, y SHALL NOT revelar si hay tokens configurados ni cuántos.

#### Scenario: Servicio activo
- **WHEN** un cliente pide `GET /health` con la API en marcha
- **THEN** la API responde 200

#### Scenario: Salud sin token
- **WHEN** un cliente pide `GET /health` sin la cabecera `Authorization`
- **THEN** la API responde 200 con el mismo cuerpo que con token

### Requirement: Errores estandarizados
Los errores SHALL responder con el tipo de medio `application/problem+json` según RFC 9457: 400 para parámetros inválidos, 401 para token ausente o inválido, 404 para recurso no encontrado, 405 para método no permitido y 500 para fallos internos. Los errores 500 SHALL NOT exponer detalles internos como rutas, consultas o mensajes de la base de datos.

#### Scenario: Parámetro inválido
- **WHEN** un cliente envía un parámetro con un valor inválido, como un `limit` no numérico
- **THEN** la API responde 400 con `application/problem+json` que indica el parámetro afectado

#### Scenario: No autorizado
- **WHEN** un cliente pide un recurso de `/v1` sin token o con un token inválido
- **THEN** la API responde 401 con `application/problem+json`

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

### Requirement: Documento OpenAPI
La API SHALL tener un documento OpenAPI generado desde su código y versionado en el repositorio. El documento SHALL declarar el esquema de seguridad Bearer y la respuesta 401 en las operaciones de `/v1`, y SHALL NOT contener ningún valor de token. Una verificación automática SHALL fallar si el documento versionado no coincide con el generado por el código actual.

#### Scenario: Documento al día
- **WHEN** el documento versionado coincide con el generado desde el código
- **THEN** la verificación pasa

#### Scenario: Documento desactualizado
- **WHEN** el código cambia un contrato sin regenerar el documento versionado
- **THEN** la verificación falla

#### Scenario: Seguridad documentada
- **WHEN** se lee el documento OpenAPI
- **THEN** declara un esquema HTTP Bearer, lo exige en las operaciones de `/v1`, no lo exige en `/health` ni en `/openapi.json` y describe la respuesta 401 con `application/problem+json`

### Requirement: Arranque y configuración
La API SHALL tomar la ruta de la base de datos de una variable de entorno o un argumento, su dirección de `HOST` y `PORT`, con `127.0.0.1:8080` por defecto, y sus tokens de API de la variable `API_TOKENS` (véase «Configuración de los tokens de API»). SHALL abrir la base en modo de solo lectura. El arranque SHALL fallar con un mensaje claro si la base no existe, si su versión de esquema no es compatible o si la configuración de tokens es inválida.

#### Scenario: Configuración por defecto
- **WHEN** la API se inicia sin `HOST` ni `PORT` y con `API_TOKENS` válido
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

#### Scenario: Tokens inválidos
- **WHEN** la API se inicia con `API_TOKENS` ausente, vacía o con un token inválido
- **THEN** la API no arranca y el mensaje indica la variable y el motivo

### Requirement: Compatibilidad dentro de `/v1`
Dentro de `/v1` SHALL admitirse solo cambios compatibles, es decir, aditivos, en el contrato de datos (rutas, parámetros y campos de las respuestas). Los cambios incompatibles SHALL requerir una nueva versión del prefijo. La política de acceso (exigir un token de API, rotarlo o cambiar sus reglas de validez) SHALL NOT considerarse parte de ese contrato y SHALL poder cambiar dentro de `/v1`. Como única excepción, mientras la API no tenga ningún consumidor, un cambio incompatible SHALL poder hacerse dentro de `/v1` si queda registrado como tal en un cambio de OpenSpec que lo justifique. La excepción SHALL dejar de aplicar cuando un primer cliente integre la API.

#### Scenario: Campo nuevo
- **WHEN** se añade un campo a una respuesta de `/v1`
- **THEN** los clientes que ignoran campos desconocidos siguen funcionando

#### Scenario: Cambio incompatible
- **WHEN** un cambio eliminaría o redefiniría un campo existente de `/v1` y la API ya tiene un cliente integrado
- **THEN** se publica bajo una nueva versión del prefijo y `/v1` conserva su contrato

#### Scenario: Cambio incompatible sin consumidores
- **WHEN** un cambio elimina o redefine un campo de `/v1` y la API no tiene ningún cliente integrado, y un cambio de OpenSpec lo registra como incompatible con su justificación
- **THEN** el cambio puede hacerse dentro de `/v1` sin nueva versión del prefijo

#### Scenario: Cambio de política de acceso
- **WHEN** se exige un token de API en `/v1` o se rota el token válido
- **THEN** el cambio se hace dentro de `/v1` sin nueva versión del prefijo, y un cambio de OpenSpec lo registra y justifica

### Requirement: Apagado ordenado con tiempo máximo
Al recibir SIGTERM o Ctrl-C, la API SHALL dejar de aceptar conexiones nuevas y esperar a las peticiones en curso como máximo 2 s. La API SHALL terminar con código 0 tanto si todas las peticiones terminaron como si se agotó el plazo. Al terminar SHALL registrar «apagado completado»; si se agotó el plazo, SHALL registrar antes un aviso de apagado forzado por conexiones abiertas tras 2 s.

#### Scenario: Conexiones inactivas
- **WHEN** la API no tiene peticiones en curso y recibe SIGTERM
- **THEN** termina de inmediato con código 0 y el log contiene «apagado completado»

#### Scenario: Conexión colgada
- **WHEN** un cliente mantiene una conexión abierta con cabeceras incompletas y la API recibe SIGTERM
- **THEN** la API termina al agotarse el plazo de 2 s con código 0, y el log contiene el aviso de apagado forzado y «apagado completado»

### Requirement: Logs sin secuencias ANSI fuera de una terminal
Los eventos de log de la API (los de `tracing`), que se escriben por la salida estándar, SHALL NOT incluir secuencias de escape ANSI cuando esa salida no es una terminal, de modo que los colectores de logs (como Cloud Logging) y los archivos reciban texto plano. SHALL NOT incluirlas tampoco cuando la variable de entorno `NO_COLOR` tiene un valor no vacío, aunque la salida sea una terminal. Con la salida en una terminal y `NO_COLOR` sin definir o vacía, SHALL conservar los colores. El nivel de logs SHALL seguir controlándose con `RUST_LOG`, con `info` por defecto.

#### Scenario: Salida redirigida
- **WHEN** la API se ejecuta con la salida estándar redirigida a una tubería o a un archivo y escribe la línea de arranque
- **THEN** la salida no contiene ningún carácter de escape `ESC` (0x1B) y la línea incluye el nivel y el mensaje «escuchando»

#### Scenario: Contenedor en Cloud Run
- **WHEN** el servicio desplegado atiende una petición y se leen sus logs en Cloud Logging
- **THEN** las entradas de la API no contienen secuencias ANSI

#### Scenario: NO_COLOR en una terminal
- **WHEN** la salida estándar es una terminal y `NO_COLOR` vale `1`
- **THEN** los logs no contienen secuencias ANSI

#### Scenario: Terminal con colores
- **WHEN** la salida estándar es una terminal y `NO_COLOR` no está definida o está vacía
- **THEN** los logs conservan los colores por nivel

#### Scenario: Nivel por entorno
- **WHEN** la API se ejecuta con `RUST_LOG=warn` y la salida redirigida
- **THEN** la línea INFO de arranque no aparece y sigue sin haber secuencias ANSI

### Requirement: Autorización por token de API en `/v1`
Toda petición a una ruta bajo `/v1`, incluidas las de rutas inexistentes y las de métodos no permitidos, SHALL llevar la cabecera `Authorization: Bearer <token>` con un token configurado; el nombre del esquema SHALL compararse sin distinguir mayúsculas. Si la cabecera falta, no usa el esquema Bearer o el token no coincide con ninguno de los configurados, la API SHALL responder 401 con `application/problem+json` y la cabecera `WWW-Authenticate: Bearer`, SHALL NOT atender la petición y SHALL NOT revelar si el token falta o es inválido, ni su longitud ni el de ninguno de los configurados. La API SHALL NOT escribir ningún token, ni el recibido ni los configurados, en logs, respuestas ni mensajes de error. `/health` y `/openapi.json` SHALL quedar fuera de esta exigencia.

#### Scenario: Token válido
- **WHEN** un cliente pide `GET /v1/plants` con `Authorization: Bearer <token válido>`
- **THEN** la API responde 200 con el listado

#### Scenario: Esquema en otras mayúsculas
- **WHEN** un cliente envía `Authorization: bearer <token válido>`
- **THEN** la API responde 200

#### Scenario: Cabecera ausente
- **WHEN** un cliente pide `GET /v1/plants` sin la cabecera `Authorization`
- **THEN** la API responde 401 con `application/problem+json` y `WWW-Authenticate: Bearer`

#### Scenario: Token incorrecto
- **WHEN** un cliente envía un token que no coincide con ninguno de los configurados, incluido uno que solo difiere en el último carácter o es prefijo de uno válido
- **THEN** la API responde 401 con el mismo cuerpo y las mismas cabeceras que en el caso de cabecera ausente

#### Scenario: Esquema distinto de Bearer
- **WHEN** un cliente envía `Authorization: Basic <valor>` o un valor sin esquema
- **THEN** la API responde 401

#### Scenario: Ruta inexistente o método no permitido sin token
- **WHEN** un cliente pide sin token `GET /v1/no-existe` o envía `POST /v1/plants`
- **THEN** la API responde 401, no 404 ni 405

#### Scenario: Rutas públicas
- **WHEN** un cliente pide `GET /health` o `GET /openapi.json` sin token
- **THEN** la API responde 200

#### Scenario: Ninguna ruta de datos fuera del prefijo
- **WHEN** se enumeran las rutas del documento OpenAPI
- **THEN** toda ruta distinta de `/health` y `/openapi.json` está bajo `/v1`, de modo que una ruta nueva de datos no queda pública por omisión

#### Scenario: El token no se registra
- **WHEN** la API atiende peticiones con un token válido y con uno inválido con el nivel de logs `trace`
- **THEN** ninguna línea del log contiene el valor de un token recibido ni de uno configurado

### Requirement: Configuración de los tokens de API
La API SHALL leer los tokens válidos de la variable de entorno `API_TOKENS`, una lista separada por comas con uno o más tokens, para poder rotarlos sin cortar el servicio. Se SHALL ignorar el espacio en blanco alrededor de cada token y su salto de línea final. Cada token SHALL tener entre 32 y 256 caracteres y SHALL estar formado solo por letras, dígitos y los símbolos `-`, `.`, `_`, `~`, `+` y `/`. La API SHALL NOT arrancar si la variable falta, está vacía o contiene un token inválido, y SHALL NOT ofrecer un modo sin autorización. La comparación SHALL tardar un tiempo independiente de en qué posición difiere el token recibido. La configuración SHALL NOT imprimir los tokens al mostrarse en depuración o en un mensaje de error.

#### Scenario: Un token válido
- **WHEN** `API_TOKENS` contiene un único token de 64 caracteres hexadecimales
- **THEN** la API arranca y acepta ese token

#### Scenario: Varios tokens para rotar
- **WHEN** `API_TOKENS` contiene dos tokens válidos separados por coma, con espacios o un salto de línea final
- **THEN** la API acepta cualquiera de los dos

#### Scenario: Variable ausente o vacía
- **WHEN** la API se inicia sin `API_TOKENS` o con un valor vacío o solo espacios
- **THEN** termina con código 2 y un mensaje que nombra la variable, sin servir ninguna ruta

#### Scenario: Token demasiado corto
- **WHEN** algún elemento de `API_TOKENS` tiene menos de 32 caracteres
- **THEN** la API termina con código 2 y un mensaje que indica la longitud mínima y no contiene el valor ofrecido

#### Scenario: Elemento vacío o carácter no permitido
- **WHEN** `API_TOKENS` contiene un elemento vacío (como `a,,b`) o un token con un carácter no permitido
- **THEN** la API termina con código 2 y un mensaje sin el valor ofrecido

#### Scenario: Configuración sin secretos al depurar
- **WHEN** la configuración resuelta se formatea con la representación de depuración
- **THEN** el resultado no contiene ningún token

#### Scenario: Ayuda y OpenAPI sin tokens
- **WHEN** la API se ejecuta con `--help` o `--openapi` sin `API_TOKENS`
- **THEN** imprime la ayuda o el documento y termina con código 0, porque no sirve ninguna ruta

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

### Requirement: Catálogo de objetivos
`GET /v1/goals` SHALL devolver la lista completa de objetivos, sin paginar, en el orden de presentación definido por el catálogo. Cada objetivo SHALL incluir `id`, `name` (en español), `plantCount` y `subareas` (lista vacía si no las tiene), y cada subárea `id`, `name` y `plantCount`. Las subáreas sin plantas visibles SHALL omitirse. Los conteos SHALL contar plantas distintas visibles, es decir, las que `GET /v1/goals/{goalId}/plants` devolvería, y el de un objetivo con subáreas SHALL ser la unión sin repetir plantas. Los nombres, el orden y las subáreas SHALL salir del catálogo y no de valores fijos en la API.

#### Scenario: Lista de objetivos
- **WHEN** un cliente con token pide `GET /v1/goals`
- **THEN** la respuesta incluye los objetivos del catálogo en su orden, cada uno con `id`, `name`, `plantCount` y `subareas`

#### Scenario: Objetivo con subáreas
- **WHEN** el objetivo `otros-objetivos` tiene plantas en varias subáreas
- **THEN** su `subareas` lista cada subárea con plantas, y su `plantCount` cuenta una vez a la planta que está en dos subáreas

#### Scenario: Subárea sin plantas
- **WHEN** una subárea no tiene plantas visibles
- **THEN** no aparece en `subareas`

#### Scenario: Objetivo sin plantas
- **WHEN** un objetivo del catálogo no tiene plantas visibles
- **THEN** sigue en la lista con `plantCount` igual a cero y `subareas` vacía

#### Scenario: Coherencia con los resultados
- **WHEN** un cliente compara el `plantCount` de un objetivo con el `total` de `GET /v1/goals/{goalId}/plants`
- **THEN** son iguales

#### Scenario: Sin token
- **WHEN** un cliente pide `GET /v1/goals` sin token
- **THEN** la API responde 401 con `application/problem+json`

### Requirement: Plantas por objetivo
`GET /v1/goals/{goalId}/plants` SHALL devolver una página con `goal` (`id`, `name`), `subarea` (`id`, `name`, o `null`), `items`, `total`, `limit` y `offset`. Cada elemento SHALL incluir `id`, `displayName`, `scientificName`, `commonNames` con idioma y `family` (o `null`) como el listado, `areas` (nombres en español de las áreas de la EMA que respaldan a la planta en ese objetivo o subárea), `safetyLevel` (`alto`, `medio`, `bajo` o `null`; es `null` también cuando la planta tiene precauciones sin nivel) y `hasSafety` (booleano, verdadero cuando la planta tiene datos de precauciones aunque no tengan nivel) e `image`, el mismo objeto del detalle (`url`, `pageUrl`, `author`, `license`, `licenseUrl` y `attributionRequired`) o `null`. El `image` SHALL ser el mismo `ImageDto` del detalle y la API SHALL NOT derivar miniaturas ni consultar la red. Un objetivo desconocido SHALL responder 404. El parámetro opcional `subarea` SHALL filtrar por una subárea del objetivo; un valor que no pertenece al objetivo, o enviado a un objetivo sin subáreas, SHALL responder 400 con `param` igual a `subarea`. Sin `subarea` en un objetivo con subáreas, SHALL devolverse la unión sin repetir plantas.

#### Scenario: Plantas de un objetivo
- **WHEN** un cliente pide `GET /v1/goals/mejorar-el-sueno/plants`
- **THEN** la respuesta incluye `goal` con ese objetivo, `subarea` igual a `null`, las plantas de la primera página con su `displayName`, `areas`, `safetyLevel`, `hasSafety` e `image`, y el total

#### Scenario: Subárea
- **WHEN** un cliente pide `GET /v1/goals/otros-objetivos/plants?subarea=digestion`
- **THEN** la respuesta incluye solo plantas de esa subárea, `subarea` con su `id` y `name`, y en `areas` solo las áreas de esa subárea

#### Scenario: Unión sin subárea
- **WHEN** un cliente pide `GET /v1/goals/otros-objetivos/plants` sin `subarea`
- **THEN** cada planta aparece una vez aunque pertenezca a varias subáreas, y `areas` reúne sus áreas

#### Scenario: Subárea ajena
- **WHEN** un cliente pide `subarea` con un valor que no es de ese objetivo, o una subárea para un objetivo sin subáreas
- **THEN** la API responde 400 con `application/problem+json` y `param` igual a `subarea`

#### Scenario: Objetivo desconocido
- **WHEN** un cliente pide las plantas de un `goalId` inexistente
- **THEN** la API responde 404 con `application/problem+json`

#### Scenario: Objetivo sin plantas
- **WHEN** un objetivo del catálogo no tiene plantas visibles
- **THEN** la respuesta tiene una lista vacía y un total de cero, no un error

#### Scenario: Datos ausentes
- **WHEN** una planta no tiene imagen ni datos de seguridad
- **THEN** su `image` y su `safetyLevel` son `null`, su `hasSafety` es falso, y la API no consulta la red ni sirve bytes de imágenes

#### Scenario: Precauciones sin nivel
- **WHEN** una planta tiene `safety` con `level` nulo, texto y referencias (por ejemplo el eucalipto con las contraindicaciones de la EMA)
- **THEN** su `safetyLevel` es `null` y su `hasSafety` es verdadero

#### Scenario: Token y método
- **WHEN** un cliente pide la ruta sin token, o envía un método que no es de lectura con token
- **THEN** la API responde 401 y 405 respectivamente, con `application/problem+json`

### Requirement: Orden y paginación de plantas por objetivo
Las plantas de un objetivo SHALL ordenarse de forma total y estable por `displayName` normalizado (sin distinguir mayúsculas ni acentos, con la misma normalización de nombres que la búsqueda de `GET /v1/plants`), luego por nombre científico normalizado y luego por identificador. El `displayName` puede ser el nombre científico, y entonces se ordena entre los demás por ese texto. El orden SHALL NOT depender del tipo o la cantidad de respaldo de la EMA. La paginación SHALL aceptar `limit` (1 a 100, por defecto 20) y `offset` con las mismas reglas y errores que `GET /v1/plants`, y `total` SHALL ser independiente de la página.

#### Scenario: Orden por nombre para mostrar
- **WHEN** un cliente pide las plantas de un objetivo
- **THEN** los elementos están ordenados por `displayName`, luego científico y luego identificador

#### Scenario: Orden sin distinguir acentos ni mayúsculas
- **WHEN** un objetivo tiene plantas con `displayName` «Árnica», «abedul», «Zarzaparrilla» y el científico `Abutilon theophrasti`
- **THEN** salen en el orden «abedul», `Abutilon theophrasti`, «Árnica», «Zarzaparrilla»

#### Scenario: Páginas sin repetición
- **WHEN** un cliente recorre las páginas con `limit` 5
- **THEN** cada planta aparece exactamente una vez y la unión de las páginas tiene `total` elementos

#### Scenario: Límite fuera de rango
- **WHEN** el `limit` es cero, negativo, no numérico o mayor que 100, o el `offset` es negativo
- **THEN** la API responde 400 con `application/problem+json` que indica el parámetro

#### Scenario: Desplazamiento más allá del total
- **WHEN** el `offset` supera el total
- **THEN** la respuesta tiene una lista vacía y conserva el total

### Requirement: Qué plantas aparecen por objetivo
Una planta SHALL aparecer en un objetivo solo si el catálogo le asigna ese objetivo; las plantas sin objetivos, incluidas las que la semilla excluye por toxicidad, SHALL NOT aparecer en ninguno. Una planta cuya asignación a un objetivo está marcada como pendiente de revisión, como las de interacciones graves en «Relajación / Estrés», SHALL NOT aparecer en ese objetivo ni contarse en sus conteos, y SHALL seguir apareciendo en `GET /v1/plants` y `GET /v1/plants/{id}`. Solo esa marca por objetivo oculta la planta: ningún otro `reviewFlag` la oculta. La API SHALL NOT incluir en estas respuestas dosis, indicaciones ni textos de eficacia.

#### Scenario: Planta sin objetivos
- **WHEN** una planta no tiene objetivos en el catálogo
- **THEN** no aparece en ninguna respuesta de `GET /v1/goals/{goalId}/plants`

#### Scenario: Planta condicionada por revisión
- **WHEN** una planta con interacciones graves en estrés y ánimo tiene el objetivo `relajacion-estres` pendiente de revisión
- **THEN** no aparece en `GET /v1/goals/relajacion-estres/plants`, no cuenta en su `plantCount` y se puede pedir por `GET /v1/plants/{id}`

#### Scenario: Flag sin marca de revisión del objetivo
- **WHEN** una planta tiene un `reviewFlag` (por ejemplo, ausencia de datos de seguridad) pero ninguno de sus objetivos está pendiente de revisión
- **THEN** aparece en los objetivos que tiene

#### Scenario: Planta en dos objetivos
- **WHEN** una planta tiene áreas de la EMA en dos objetivos
- **THEN** aparece en ambos, con en cada uno solo las áreas de ese objetivo

### Requirement: Contrato aditivo de objetivos
Las rutas de objetivos SHALL estar bajo `/v1`, requerir el token de API como el resto, documentarse en el documento OpenAPI con el esquema Bearer, la respuesta 401 y los errores 400, 404, 405 y 500 como `application/problem+json`, usar nombres de campo en camelCase y representar lo ausente como `null` o lista vacía. Su incorporación SHALL ser un cambio compatible: SHALL NOT alterar las rutas, los parámetros ni los campos de `GET /v1/plants` y `GET /v1/plants/{id}` existentes.

#### Scenario: OpenAPI actualizado
- **WHEN** se regenera el documento OpenAPI desde el código
- **THEN** incluye `/v1/goals` y `/v1/goals/{goalId}/plants` con Bearer, 401, 400, 404, 405 y 500 según corresponda, y coincide con el versionado

#### Scenario: Rutas existentes intactas
- **WHEN** se compara la respuesta de `GET /v1/plants` y de `GET /v1/plants/{id}` antes y después del cambio
- **THEN** sus campos y su orden no cambian

#### Scenario: Ninguna ruta pública nueva
- **WHEN** se enumeran las rutas del documento OpenAPI
- **THEN** las de objetivos están bajo `/v1` y la API las rechaza sin token con 401
