# catalog-client Specification

## Purpose
Define cómo la app Flutter consume la API de solo lectura `/v1` del catálogo: dirección configurable, peticiones permitidas, parseo estricto, errores legibles, nombre para mostrar, permisos de Android y pruebas sin red.

## Requirements

### Requirement: Dirección del backend configurable
La app SHALL obtener la dirección base del backend de la definición de compilación `API_BASE_URL`. Si no se define, SHALL usar `http://10.0.2.2:8080`, con la que el emulador Android llega al backend que corre en el equipo anfitrión. SHALL tolerar una barra final en la dirección.

#### Scenario: Valor por defecto del emulador
- **WHEN** la app se compila sin `API_BASE_URL`
- **THEN** las peticiones se dirigen a `http://10.0.2.2:8080`

#### Scenario: Sobrescritura para dispositivo físico
- **WHEN** la app se compila con `--dart-define=API_BASE_URL=http://192.168.1.20:8080`
- **THEN** las peticiones se dirigen a esa dirección

#### Scenario: Barra final tolerada
- **WHEN** la dirección base termina en `/`
- **THEN** las rutas se forman sin barras duplicadas, por ejemplo `http://host:8080/v1/plants` y no `http://host:8080//v1/plants`

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

### Requirement: Parseo estricto de las respuestas
La app SHALL validar las respuestas según el contrato OpenAPI de la API: campos requeridos presentes y con el tipo correcto. SHALL ignorar los campos desconocidos y SHALL aceptar `family` igual a `null`. Ante JSON inválido o un campo requerido ausente o de tipo erróneo, SHALL producir un error legible, sin cierre inesperado y sin completar datos con contenido inventado.

#### Scenario: Listado válido
- **WHEN** la API responde un listado con `items`, `total`, `limit` y `offset`
- **THEN** se obtienen las plantas con identificador, nombre científico, nombres comunes con idioma y familia, y el total

#### Scenario: Detalle válido
- **WHEN** la API responde un detalle con nombres (con `kind` e idioma), partes y usos (con actividad, idioma y referencia con cita)
- **THEN** se obtiene la planta completa con esos datos

#### Scenario: Familia nula
- **WHEN** el campo `family` es `null`
- **THEN** la planta se acepta sin familia

#### Scenario: Campos desconocidos
- **WHEN** la respuesta incluye campos que la app no conoce
- **THEN** se ignoran y la respuesta se procesa normalmente

#### Scenario: Campo requerido ausente o de tipo erróneo
- **WHEN** falta un campo requerido, como `items` o `scientificName`, o tiene un tipo distinto del esperado
- **THEN** se produce un error de cliente legible y no se muestran datos parciales o inventados

#### Scenario: JSON inválido
- **WHEN** el cuerpo de una respuesta con éxito no es JSON válido
- **THEN** se produce un error de cliente legible, sin cierre inesperado

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

### Requirement: Nombre para mostrar
La app SHALL mostrar como nombre principal de una planta su primer nombre común, en el idioma que venga, y como nombre secundario su nombre científico. Si la planta no tiene nombres comunes, SHALL mostrar el nombre científico como principal y no mostrar nombre secundario. SHALL NOT traducir ni inventar nombres.

#### Scenario: Planta con nombre común
- **WHEN** una planta tiene el nombre común «English Lavender» y el científico `Lavandula angustifolia`
- **THEN** el principal es «English Lavender» y el secundario es `Lavandula angustifolia`

#### Scenario: Planta sin nombre común
- **WHEN** una planta no tiene nombres comunes
- **THEN** el principal es su nombre científico y no hay nombre secundario

#### Scenario: Idioma del nombre común
- **WHEN** el primer nombre común está en un idioma distinto del español, como `en` o `und`
- **THEN** se muestra tal cual, sin traducirlo

### Requirement: Permisos y transporte en Android
El manifest principal de Android SHALL declarar el permiso `INTERNET`. Los manifests de `debug` y `profile` SHALL habilitar el tráfico HTTP en claro para la pila de red de Android. El manifest principal y los recursos de `release` SHALL NOT habilitarlo. La documentación SHALL indicar que el cliente Dart (`dart:io`) no está sujeto a esa restricción, por lo que el build `release` debe recibir una `API_BASE_URL` HTTPS.

#### Scenario: Permiso en todos los builds
- **WHEN** se revisa el manifest principal
- **THEN** declara `INTERNET`, de modo que un build `release` tiene acceso a la red

#### Scenario: HTTP en claro en desarrollo
- **WHEN** se revisan los manifests de `debug` y `profile`
- **THEN** declaran `android:usesCleartextTraffic="true"`, de modo que la app llega al backend local por HTTP

#### Scenario: Release sin HTTP en claro
- **WHEN** se revisan el manifest principal y los recursos de `release`
- **THEN** no habilitan HTTP en claro ni definen una configuración de seguridad de red que lo permita

#### Scenario: Release con dirección HTTP
- **WHEN** se compila un build `release` con `API_BASE_URL=http://…`
- **THEN** el cliente Dart sí usa HTTP en claro, por lo que la documentación exige pasar la URL HTTPS del backend desplegado en `release`

### Requirement: Pruebas sin red
Las pruebas unitarias y de widget SHALL ejecutarse sin red, con un cliente HTTP inyectado que sirve respuestas de prueba. La integración continua SHALL ejecutarlas sin backend ni conectividad.

#### Scenario: Cliente inyectado
- **WHEN** se ejecuta una prueba de unidad o de widget del catálogo
- **THEN** usa un cliente HTTP sustituido por respuestas de prueba y no abre conexiones reales

#### Scenario: CI sin backend
- **WHEN** la integración continua ejecuta las pruebas de la app
- **THEN** pasan sin backend en marcha y sin conectividad

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
