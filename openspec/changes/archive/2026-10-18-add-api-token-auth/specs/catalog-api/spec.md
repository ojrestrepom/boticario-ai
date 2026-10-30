# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: API de solo lectura sin autenticación`
- TO: `### Requirement: API de solo lectura con autorización por token`

## MODIFIED Requirements

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

## ADDED Requirements

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
