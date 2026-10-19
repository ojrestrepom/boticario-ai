# Spec Delta

## MODIFIED Requirements

### Requirement: Consumo de la API v1 del catálogo
La app SHALL usar únicamente `GET /v1/plants` (con `q`, `limit` y `offset` codificados) y `GET /v1/plants/{id}` (con el id codificado en la ruta), con la cabecera `Accept: application/json` y la cabecera `Authorization: Bearer <token>` con el token de API de la compilación en cada petición. SHALL NOT usar otros endpoints ni comunicarse con otro host. SHALL NOT enviar otras cabeceras de identidad ni datos de usuario, ni escribir el token en logs, mensajes de error o la interfaz.

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
- **THEN** todas las peticiones son de los dos endpoints permitidos al host de la dirección base, con el token de API como única credencial y sin datos de usuario

### Requirement: Errores de red y del servidor
Cada petición SHALL tener un tiempo máximo de 10 segundos. El fallo de conexión, el tiempo agotado, las respuestas 5xx, las respuestas 400 y el cuerpo inválido SHALL producir un error de cliente legible y reintentable. Una respuesta 401 o 403 SHALL producir un error de cliente legible distinto, que indique que la app no está autorizada para usar el servidor y que SHALL NOT incluir el token. La app SHALL NOT reintentar sola la petición. Una respuesta 404 al pedir el detalle SHALL tratarse como «planta no encontrada», distinta de un error.

#### Scenario: Sin conexión
- **WHEN** no hay conectividad o el backend no está en marcha
- **THEN** se produce un error de cliente legible y reintentable, sin cierre inesperado

#### Scenario: Tiempo agotado
- **WHEN** el backend no responde en 10 segundos
- **THEN** la petición se interrumpe y se produce un error de cliente legible y reintentable

#### Scenario: Error del servidor
- **WHEN** la API responde 5xx
- **THEN** se produce un error de cliente legible y reintentable

#### Scenario: Parámetro inválido
- **WHEN** la API responde 400 con `application/problem+json`
- **THEN** se produce un error de cliente legible y reintentable

#### Scenario: No autorizado
- **WHEN** la API responde 401 con `application/problem+json`, al listar o al pedir un detalle
- **THEN** se produce un error de cliente legible de autorización, sin cierre inesperado, cuyo mensaje no contiene el token y que no se confunde con «planta no encontrada»

#### Scenario: Planta no encontrada
- **WHEN** la API responde 404 al pedir el detalle de un identificador
- **THEN** el resultado es «no encontrada» y no un error de cliente

#### Scenario: Reintento
- **WHEN** el usuario reintenta tras un error y el backend ya responde
- **THEN** la petición se repite y se obtienen los datos

## ADDED Requirements

### Requirement: Token de API configurable
La app SHALL obtener el token de API de la definición de compilación `API_TOKEN`. El token SHALL NOT estar en el repositorio, en valores por defecto del código ni en los archivos de configuración versionados. Sin `API_TOKEN` la app SHALL seguir arrancando, SHALL NOT enviar la cabecera `Authorization` y las peticiones al catálogo SHALL fallar con el error de no autorizado cuando la API lo exija. La documentación SHALL indicar que un token embebido en un APK se puede extraer y que solo identifica a la app, no al usuario.

#### Scenario: Token por compilación
- **WHEN** la app se compila con `--dart-define=API_TOKEN=<token>`
- **THEN** las peticiones al catálogo llevan ese token como `Authorization: Bearer <token>`

#### Scenario: Compilación sin token
- **WHEN** la app se compila sin `API_TOKEN` y se consulta una API que exige token
- **THEN** la petición no lleva `Authorization`, la API responde 401 y la app muestra el error de no autorizado sin cierre inesperado

#### Scenario: Token fuera del repositorio
- **WHEN** se buscan valores de token en el código, los manifests, las pruebas y la documentación versionados
- **THEN** solo aparecen valores ficticios de prueba claramente marcados y ninguno es un token aceptado por el backend desplegado
