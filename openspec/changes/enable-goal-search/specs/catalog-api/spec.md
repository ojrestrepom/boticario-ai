# Spec Delta

## ADDED Requirements

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
`GET /v1/goals/{goalId}/plants` SHALL devolver una página con `goal` (`id`, `name`), `subarea` (`id`, `name`, o `null`), `items`, `total`, `limit` y `offset`. Cada elemento SHALL incluir `id`, `displayName`, `scientificName`, `commonNames` con idioma y `family` (o `null`) como el listado, `areas` (nombres en español de las áreas de la EMA que respaldan a la planta en ese objetivo o subárea), `safetyLevel` (`alto`, `medio`, `bajo` o `null`; es `null` también cuando la planta tiene precauciones sin nivel) y `hasSafety` (booleano, verdadero cuando la planta tiene datos de precauciones aunque no tengan nivel) e `image`, el mismo objeto del detalle (`url`, `pageUrl`, `author`, `license`, `licenseUrl` y `attributionRequired`) o `null`. Un objetivo desconocido SHALL responder 404. El parámetro opcional `subarea` SHALL filtrar por una subárea del objetivo; un valor que no pertenece al objetivo, o enviado a un objetivo sin subáreas, SHALL responder 400 con `param` igual a `subarea`. Sin `subarea` en un objetivo con subáreas, SHALL devolverse la unión sin repetir plantas.

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
Las plantas de un objetivo SHALL ordenarse de forma total y estable por `displayName` normalizado (sin distinguir mayúsculas ni acentos), luego por nombre científico y luego por identificador. El orden SHALL NOT depender del tipo o la cantidad de respaldo de la EMA. La paginación SHALL aceptar `limit` (1 a 100, por defecto 20) y `offset` con las mismas reglas y errores que `GET /v1/plants`, y `total` SHALL ser independiente de la página.

#### Scenario: Orden por nombre para mostrar
- **WHEN** un cliente pide las plantas de un objetivo
- **THEN** los elementos están ordenados por `displayName`, luego científico y luego identificador

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
Las rutas de objetivos SHALL estar bajo `/v1`, requerir el token de API como el resto, documentarse en el documento OpenAPI con el esquema Bearer, la respuesta 401 y los errores 400 y 404, usar nombres de campo en camelCase y representar lo ausente como `null` o lista vacía. Su incorporación SHALL ser un cambio compatible: SHALL NOT alterar las rutas, los parámetros ni los campos de `GET /v1/plants` y `GET /v1/plants/{id}` existentes.

#### Scenario: OpenAPI actualizado
- **WHEN** se regenera el documento OpenAPI desde el código
- **THEN** incluye `/v1/goals` y `/v1/goals/{goalId}/plants` con Bearer, 401, 400 y 404, y coincide con el versionado

#### Scenario: Rutas existentes intactas
- **WHEN** se compara la respuesta de `GET /v1/plants` y de `GET /v1/plants/{id}` antes y después del cambio
- **THEN** sus campos y su orden no cambian

#### Scenario: Ninguna ruta pública nueva
- **WHEN** se enumeran las rutas del documento OpenAPI
- **THEN** las de objetivos están bajo `/v1` y la API las rechaza sin token con 401
