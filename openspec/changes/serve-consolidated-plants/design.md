# Design

## Context

Este cambio se implementa después de `consolidate-catalog-seed` (cambio 1). Lo que sigue describe el estado actual observado y lo que el cambio 1 deja, según su `design.md` (D2, D3, D5, D7, D8 y D12) y su `tasks.md`; los nombres exactos de tablas y columnas se fijan allí en la tarea 7.1 y aquí se comprueban en la tarea 1.1.

Estado actual de la API (`backend/catalog-api`):

- `dto.rs` define el contrato. `PlantSummaryDto` tiene `id`, `scientificName`, `commonNames` y `family`. `PlantDto` tiene `id`, `scientificName`, `family`, `names`, `parts` y `uses` (actividad, idioma y referencia con cita).
- `repository.rs` ordena los nombres comunes por texto, idioma e id (listado) y los nombres del detalle con los científicos primero y luego por texto e idioma. Por eso el primer nombre común es hoy el primero alfabéticamente. El cambio 1 dice que escribe `displayName` primero «para que sea el primer nombre común», pero con este orden eso no se cumpliría: la API tiene que cambiar el orden (D2).
- El detalle carga nombres, partes y usos con una consulta por tabla. No lee ninguna tabla de las que añade el cambio 1.
- Las specs vigentes prohíben exponer procedencia en el detalle («Detalle de planta», «Independencia de la fuente de datos») y en el pasaporte («Identidad y composición del pasaporte»). El cambio archivado `remove-api-provenance` quitó `sources` por dato y dejó anotado que la atribución exigida por licencias iría como un dato neutral de créditos, no como una lista de datasets por campo.
- `catalog-api` ya admite solo cambios aditivos dentro de `/v1` («Compatibilidad dentro de `/v1`»). La excepción de «sin consumidores» no se usa aquí: la app ya consume la API.

Estado actual de la app (`app/lib/features`):

- `catalog/domain/plant.dart` modela `Plant` con `names`, `parts` y `uses`; `catalog_json_parser.dart` es estricto salvo campos desconocidos. El nombre para mostrar es el primer nombre común (`displayNamesFor`).
- `passport/presentation/plant_passport_page.dart` (472 líneas) tiene tres pestañas. `General` muestra familia, nombres comunes, partes y `Tipo de aceite: No aplicable: ficha de planta`; `Propiedades` muestra el texto fijo `sin propiedades medicinales evaluadas en este catálogo`; `Usos` muestra una fila por uso con actividad, referencia y cita. La cabecera es arte local provisional.
- La app es nativa Android: no hay `app/web`. La QA anterior usó el emulador con `integration_test` y `adb` (véase D13).
- `explore_page.dart` muestra el primer nombre común como principal.

Mockups: P05 define `General` (Nombre común, Origen, Parte utilizada, Tipo de aceite, Descripción) y la imagen de cabecera, y no define `Propiedades` ni `Usos` (`docs/mockups/pantallas.md`). P04 muestra una miniatura por fila.

Lo que el cambio 1 deja en `catalog.db` y este cambio lee: `plant_profile` (nombre para mostrar `display_name`, origen, descripción, tipo de aceite), `plant_use_group` y `plant_use_group_ref` (actividad traducida y original, `n`, países), `plant_goal` (con `subarea_id` y `pending_review`) y `plant_goal_ref`, `goal` y `goal_subarea`, `plant_safety` y `plant_safety_ref`, `plant_image`, `plant_alias`, `plant_review_flag`, `reference.dataset` y `reference.license`, y `source` con sus tablas de atribución (`plant_*_source`).

## Goals / Non-Goals

**Goals:**

- Servir todo lo que la semilla guarda para el pasaporte con un contrato aditivo dentro de `/v1` y sin consultas a la red.
- Mostrar atribución y licencias de forma neutral (por planta), cumpliendo CC BY y CC BY-SA sin exponer procedencia por campo.
- Que ninguna ausencia de datos se lea como dato: «sin datos de seguridad» no es «segura», y «sin objetivos» no es «sin efecto».
- Que la app siga funcionando contra un backend anterior durante el despliegue.

**Non-Goals:**

- Los de `proposal.md` (cambio 3, capa humana, chat, miniaturas en Explorar, proxy de imágenes).
- Cambiar la semilla, sus herramientas o el esquema de `catalog.db`. Si falta algo que este cambio necesita, se reporta en la tarea 1.1 y se ajusta el cambio 1; no se añade aquí.
- Un modelo de «favoritos» o de historial sobre los IDs (no hay persistencia en la app).

## Decisions

### D1. Forma del DTO: campos nuevos en la raíz del detalle, `uses` se conserva

El detalle suma estos campos, siempre presentes (valor, `null` o lista vacía):

| Campo | Tipo | Contenido |
|---|---|---|
| `displayName` | texto | Nombre para mostrar (D2) |
| `synonyms` | lista de textos | Nombres científicos distintos del aceptado |
| `description` | texto o `null` | Descripción neutra de hasta 400 caracteres |
| `origin` | texto o `null` | Origen |
| `oil` | `{type}` o `null` | Tipo de aceite (por ahora `Esencial`) |
| `useGroups` | lista | `activity`, `activitySource`, `count`, `countries`, `references[{id, citation}]` |
| `goals` | lista | `id`, `name`, `subarea`, `area`, `evidence`, `references` |
| `safety` | objeto o `null` | `level` (`alto`, `medio`, `bajo`), `text`, `references` |
| `image` | objeto o `null` | `url`, `pageUrl`, `author`, `license`, `licenseUrl`, `attributionRequired` |
| `credits` | lista | `name`, `license`, `licenseUrl`, `attribution`, `url` |

`parts` (que ya contiene `partsUsed`), `names` y `uses` no cambian de forma. `uses` se conserva porque quitarlo sería incompatible dentro de `/v1`; la app nueva lee `useGroups`, y `uses` queda para clientes anteriores y como respaldo del cliente (D11). El mapeo `traditionalUses` a `uses` ya lo escribe el cambio 1 (un uso por cada referencia resuelta), de modo que ambos son coherentes.

Alternativas:

- Un objeto anidado `profile` o `consolidated` con los campos nuevos. Agrupa lo nuevo, pero deja `description` y `origin` lejos de `family` y `names`, y obliga a un cliente a conocer dos niveles. Se descarta: el detalle ya es plano.
- Endpoints por subrecurso (`/v1/plants/{id}/safety`, `/images`, `/sources`). Permite pedir solo lo necesario, pero el pasaporte necesita todo para pintar tres pestañas y una cabecera, y se multiplican las peticiones y los estados de error. Se descarta; además nuevas rutas bajo `/v1` ampliarían la superficie sin un consumidor distinto.
- Reemplazar `uses` por `useGroups`. Es incompatible con `/v1` mientras exista un cliente; se descarta.
- Campos requeridos u omitidos si están vacíos. Se prefiere «siempre presentes»: el documento OpenAPI queda más simple y un cliente distingue «sin dato» de «campo que no conozco».

El orden estable es parte del contrato de uso, no de la forma: `useGroups` por `count` descendente y luego actividad, `goals` por nombre, `credits` por nombre y `synonyms` por texto.

Los textos visibles (descripción, actividades traducidas, advertencias) los valida el cambio 1 (en español, sin dosis ni promesas de eficacia); la API los sirve tal cual y no los reescribe.

### D2. Nombre para mostrar: campo explícito y orden de los nombres comunes

Se añade `displayName` al listado y al detalle, y además el nombre para mostrar pasa a ser el primero entre los nombres comunes. El cambio 1 lo guarda de forma explícita en `plant_profile.display_name` y la API lo lee de ahí (o usa el nombre científico si la planta no tiene nombres comunes). Con eso `commonNames` y `names` salen con ese nombre primero y el resto por texto e idioma.

Por qué ambos: el campo explícito evita que un cliente dependa del orden de una lista; el orden mantiene el comportamiento de la app anterior («primer nombre común»), que con el orden alfabético mostraría un nombre distinto del elegido.

Alternativas:

- Solo reordenar, sin campo nuevo. Menos superficie, pero deja el contrato dependiendo de un orden implícito y la planta sin nombre común sin un valor de respaldo.
- Solo el campo, sin reordenar. Una app o un cliente de la versión anterior seguiría mostrando el primer nombre alfabético.
- Derivarlo del nombre común de menor `plant_name.id` (orden de inserción del build). No exige columna, pero depende de un orden implícito; se descarta ahora que el cambio 1 guarda `plant_profile.display_name`.

### D3. Qué muestran `Propiedades` y `Usos`

El mockup no define ninguna de las dos. Propuesta:

- `Propiedades`: dos secciones. `Objetivos registrados por la EMA`, con cada objetivo con nombre, subárea, área y tipo de documento de la EMA (monografía o entrada de lista), la cita y una aclaración fija («clasificación de la EMA, no una indicación de uso ni una promesa de eficacia»). `Seguridad`, con el nivel y el texto por nivel (D4).
- `Usos`: los grupos de uso tradicional traducidos, con actividad, número de registros, países y todas las citas, con la etiqueta `Registro tradicional` y la aclaración de que es un registro y no un consejo.

Por qué: son los dos conjuntos que la semilla puede respaldar con cita. Los objetivos salen solo de la EMA, así que `Propiedades` es la pestaña donde una afirmación tiene una fuente regulatoria nombrada; los usos son registros etnobotánicos con citas, justo lo que `Usos` ya muestra.

Alternativas:

- `Propiedades` con la fitoquímica de USDA (compuestos y partes). Es dato disponible, pero la spec vigente prohíbe inferir eficacia desde la fitoquímica y una lista de compuestos invita a esa lectura. Se descarta.
- Los objetivos dentro de `Usos`. Mezcla una clasificación regulatoria con registros tradicionales; se pierde la distinción que el pasaporte hace entre «dato de fuente» y «registro tradicional».
- Una pestaña `Seguridad` nueva. Aleja el mockup (tres pestañas); se descarta, y el nivel alto se avisa en `General` (D4).
- `Usos` plano (una fila por uso, como hoy). Repite la actividad por cada cita y no muestra países; se descarta porque la semilla ya entrega el agrupado.
- Mostrar solo la actividad y las citas bajo un «ver más». Oculta contenido que debe ser alcanzable; la spec exige listas desplazables sin truncar.

Nombre de los objetivos: la API sirve `goals[].name` y `goals[].subarea` en español, leídos de las tablas `goal (id, label, position)` y `goal_subarea (id, goal_id, label, position)` que deja el cambio 1 y que el cambio 3 usa para `GET /v1/goals`; `plant_goal` referencia la subárea con `subarea_id`. Los ids de objetivo son `relajacion-estres`, `mejorar-el-sueno`, `cuidado-de-la-piel`, `alivio-respiratorio`, `cansancio-y-fatiga` y `otros-objetivos`, y los de subárea `digestion`, `vias-urinarias-y-genitales`, `dolor-e-inflamacion`, `boca-y-garganta`, `circulacion` y `molestias-oculares`. `goals[].area`, `goals[].evidence` y los países de los grupos de uso llegan en español desde la semilla.

### D4. Seguridad: nivel con texto, citas, aviso en `General` solo si es alto

Los tres niveles se muestran como texto (`Alto`, `Medio`, `Bajo`) con el texto de advertencia y las citas, en `Propiedades`. Si el nivel es `alto`, `General` muestra además un aviso con el nivel que remite a `Propiedades`. `safety` nulo se muestra como «No hay datos de seguridad en las fuentes consultadas. Esto no significa que la planta sea segura.»

Por qué: una planta con nivel alto (tóxica) no debe quedar escondida en la tercera pestaña de una ficha cuya primera pestaña es una descripción amable. El aviso se limita al nivel alto para no cubrir de avisos las fichas; los niveles medio y bajo siguen en `Propiedades`. No se muestra nada que sugiera «segura»: el nivel `bajo` es un nivel de alerta (alergénica), no un sello.

Alternativas: aviso para medio y alto (más ruido en la ficha; las fototóxicas y carcinogénicas ya figuran en `Propiedades`); insignia siempre visible con «Sin datos» (alarma sobre ausencia de datos que no es un riesgo conocido); mostrar la seguridad solo en `Propiedades` (menos visible para plantas tóxicas).

### D5. Listado: `displayName` sí, miniatura no

El resumen del listado suma solo `displayName`, para que Explorar muestre «Lavanda» como principal con el orden y la regla del cliente. No suma la miniatura: son 50 imágenes remotas por página, de un host externo, con atribución por archivo, para una pantalla cuyo mockup las muestra pero que la spec ya declara con arte local provisional. El cambio 3 necesita una miniatura en P07 y reutiliza el objeto `image` de este cambio; si más adelante se quiere en Explorar, es un campo aditivo.

Alternativas: `image` completo en el resumen (pesa el listado y obliga a atribución en cada fila); `thumbnailUrl` solo (sin atribución visible en la fila, aceptable solo si la fila enlaza a la ficha, pero fuerza decidir tamaños de Commons ahora); ninguno (elegido).

### D6. `reviewFlags`: la API aplica una regla de omisión y no los expone

La API no expone los `reviewFlags` (estructurados como `{code, target, message}` en la semilla) ni ningún resumen de ellos. Sí aplica una regla: omite de `goals` todo objetivo con `plant_goal.pending_review = true` (hoy, `relajacion-estres` del hipérico). El resto del detalle se sirve completo.

Por qué: el cambio 1 dice que los flags no bloquean la presencia de la planta, y que ese objetivo «queda condicionado… antes de publicarse». Omitir el objetivo es la forma de cumplir ese «antes de publicarse» sin una capa humana. Los demás flags (identidad ambigua, solo género, grupo partido, respaldo de WFO, extracción de seguridad fallida, sin datos de seguridad) describen la procedencia de la identidad o ausencias que la app ya muestra como «sin datos»; exponerlos fijaría un vocabulario interno en el contrato antes de que exista la capa humana que lo gobierne.

Alternativas:

- Ignorar todos los flags (servir todo). Simple, pero publica el objetivo que el cambio 1 pide retener para el hipérico.
- Ocultar la planta entera si tiene cualquier flag. Quita del catálogo plantas legítimas (todas las de «sin datos de seguridad» y los 62 de solo género), contra lo que dice el cambio 1.
- Exponer `reviewFlags` en el detalle y que la app los marque. Honesto, pero deja la decisión de qué mostrar a la app, congela los códigos en el contrato y cualquier cambio de la capa humana sería un cambio de contrato.
- Exponer un booleano `pendingReview`. Con la ausencia de datos de seguridad como flag, sería verdadero en toda planta sin datos de seguridad, que es un flag frecuente, y dejaría de informar.

Cómo se identifica el objetivo condicionado: solo por `plant_goal.pending_review`, que escribe el build del cambio 1; la API no mantiene ninguna tabla de reglas ni interpreta códigos de flags, así que un flag nuevo no condiciona nada por omisión.

Cuando exista la capa humana, aprobar un objetivo cambia un dato (el flag se resuelve) y no el código.

### D7. Alias: 200 con el ID canónico, sin redirección

`GET /v1/plants/{id}` busca primero la planta por ID; si no existe, busca un alias en `plant_alias` y, si lo encuentra, devuelve el detalle de la planta canónica con `id` canónico en el cuerpo y `Content-Location: /v1/plants/<canónico>`. El ID de una planta tiene prioridad (el cambio 1 prohíbe que un alias iguale el ID de otra, pero la API lo comprueba en este orden). Los alias no aparecen en el listado ni se resuelven en `q` (la búsqueda por nombre antiguo ya funciona por los sinónimos de `plant_name`).

Por qué no una redirección: los clientes de la app usan `http` de Dart y el token viaja en `Authorization`; el comportamiento de las cabeceras al seguir una redirección depende del cliente y del host, y un cliente que no la siga rompería con un 301. Con 200 y `id` canónico, el cliente obtiene los datos y puede corregir su ID guardado, y no hay un salto extra. Hoy nadie guarda IDs, así que el valor es para clientes futuros (favoritos, enlaces).

Alternativas:

- 301 o 308 al ID canónico. Es la semántica correcta de HTTP para un recurso movido y deja una sola URL por recurso, pero depende del seguimiento de redirecciones con `Authorization` en cada cliente; se descarta por riesgo sin consumidor que lo necesite. Es compatible añadirlo después.
- No resolver alias (404). Más simple, pero pierde la única razón por la que el cambio 1 los guarda y deja un 404 sobre cientos de IDs que existían ayer.
- Un endpoint nuevo `GET /v1/aliases/{id}`. Una ruta más para el mismo resultado; se descarta.

Riesgo asumido: dos URLs sirven el mismo recurso (la canónica y las de alias). Una caché por URL duplicaría entradas; no hay caché de respuestas hoy.

### D8. Créditos neutrales a nivel de planta

`credits` es la unión sin repeticiones de los datasets que respaldan los datos de la planta: los de `source` por las tablas de atribución de la planta y los de `reference.dataset` de los objetivos, la seguridad y los grupos de uso, más Wikipedia cuando la descripción la resume. Cada entrada lleva `name`, `license`, `licenseUrl`, `attribution` y `url`. No indica el campo. La imagen no se repite en `credits`: su autor y licencia van en `image`, y la app los muestra en el pie de la imagen y en `Fuentes`.

Por qué: es el «dato neutral de créditos» que anticipó `remove-api-provenance`. Cumple la atribución de CC BY y CC BY-SA (nombre, licencia, enlace) sin volver a una lista de datasets por campo, y mantiene la API sin nombres de dataset en su código (los nombres son datos).

Alternativas:

- Procedencia por campo (`sources` en cada nombre, parte y uso). Es lo que se quitó en `remove-api-provenance`; vuelve a atar el contrato al modelo interno.
- Un endpoint `GET /v1/sources` con todas las fuentes. Retira de la ficha la atribución concreta de la planta, obliga a una segunda petición y a mostrar fuentes que la planta no usa. Se descarta.
- Créditos solo en la app como texto fijo. Sería una atribución global, no la de esa planta; la licencia de una imagen de Commons es por archivo, así que no puede ser fija.
- Incluir la imagen también en `credits`. Duplica la información; se prefiere un único origen (`image`).

La consulta exacta (qué tablas de atribución unir) depende de las tablas del cambio 1 y se fija en la tarea 1.1; el contrato no cambia por ello. Los términos de la EMA y TPPT siguen sin verificarse contra el texto legal; la atribución de ambas se muestra tal como la semilla la guarda.

### D9. Imagen en la app: carga directa desde Wikimedia, con respaldo local

La app carga `image.url` directamente, sin pasar por el backend, solo si es HTTPS y su host es `commons.wikimedia.org` o `upload.wikimedia.org`, sin `Authorization` ni otros datos. Mientras carga, si falla o si no hay imagen, muestra el arte local provisional actual. Bajo la imagen se ve el autor, la licencia y la página del archivo como texto; la URL se abre en el navegador del sistema mediante un paquete de enlaces (`url_launcher`), con la URL siempre visible como texto seleccionable por si no puede abrirse.

Por qué directa: el backend es de solo lectura, sin red y de bajo costo; un proxy añadiría una dependencia de red, caché y el reenvío de licencias. Los hosts de Wikimedia están pensados para el uso directo de las imágenes. La lista de hosts evita que una URL de un registro mal formado haga que la app contacte con un host arbitrario.

Alternativas:

- Un proxy en la API (`/v1/plants/{id}/image`). Deja la app solo con un host, pero hace que la API acceda a la red y guarde o transmita imágenes; contradice «solo lectura» y el despliegue escalable a cero.
- Incluir las imágenes en el contenedor o en la app. Unos 2.400 archivos con licencias variadas y varios MB cada uno; inflan la imagen y el APK. Se descarta.
- Texto de enlace sin abrir (sin `url_launcher`). Evita una dependencia y un cambio en el manifest, pero «enlace» queda como texto copiable. Se deja como alternativa si el usuario prefiere no añadir la dependencia (véase Open Questions).
- Pedir el tamaño reducido a Commons. `Special:FilePath` admite `?width=`, pero no todas las URL del registro tienen esa forma; no se contrata aquí. Se mide en la tarea 6.4 (véase Risks).

Wikimedia pide un `User-Agent` identificable en sus peticiones y puede limitar las anónimas; la descarga de imágenes de Flutter envía el de Dart por defecto. Se identifica en la tarea 6.4.

### D10. Estados vacíos y de «sin datos»

| Campo | Estado vacío en la app |
|---|---|
| Imagen | Arte local provisional, sin pie de atribución, sin error |
| Familia, origen, tipo de aceite, descripción | `No disponible en fuente` |
| Partes | `No hay partes registradas en fuente` |
| Sinónimos | `No hay sinónimos registrados` |
| Nombres comunes (otros) | `No hay nombres comunes registrados` |
| Objetivos | `No hay objetivos registrados por la EMA para esta planta` |
| Seguridad | `No hay datos de seguridad en las fuentes consultadas. Esto no significa que la planta sea segura.` |
| Usos | `No hay usos tradicionales con referencia verificable disponibles` (texto vigente) |
| Fuentes | `No hay fuentes registradas para esta planta` |

Alternativas: ocultar las secciones sin datos (la spec vigente exige decirlo explícitamente en `General`, y ocultar «seguridad» en una planta sin datos lo haría pasar por segura); un único mensaje «sin datos» por pestaña (pierde la distinción entre una planta sin usos y una sin seguridad).

Se descarta `Tipo de aceite: No aplicable: ficha de planta`: ahora el tipo de aceite sale de la semilla (`Esencial` según el compuesto `EO`) y la ausencia es «sin dato», no «no aplicable».

### D11. Cliente tolerante con los campos nuevos y respaldo de `uses`

El parser lee los campos nuevos si están y los trata como vacíos si faltan; un tipo erróneo o un `level` desconocido es error legible. Si falta `useGroups` pero hay `uses`, el modelo deriva grupos desde `uses` (uno por actividad). Si falta `displayName`, aplica la regla anterior. Así la app nueva funciona contra el backend viejo durante el despliegue y viceversa (el backend nuevo con la app vieja sigue funcionando por ser aditivo).

Alternativa: parseo estricto de los campos nuevos (como los requeridos). Detecta antes un backend mal desplegado, pero rompe el pasaporte entero si la app se publica antes que la API o si se retrocede la API. Se descarta; el costo es que un backend defectuoso que omita `goals` se vería como «sin objetivos». Se mitiga con las pruebas de contrato de la API (todos los campos siempre presentes).

### D12. Consultas y esquema

No hay cambio de esquema. `catalog-core` suma tipos de dominio y filas para las tablas del cambio 1; `catalog-api` suma cargadores por planta (perfil, grupos de uso con referencias, objetivos, seguridad, imagen, alias, créditos, flags) siguiendo el patrón de `load_names` y `load_uses`. El detalle pasa de 3 a unas 9 consultas indexadas por `plant_id` sobre una base SQLite de solo lectura; no se espera impacto medible, y la tarea 11.2 lo mide con la base real. Los tests unitarios amplían `test_support.rs` (la `Fixture` que arma una base mínima) con filas de las tablas nuevas, y `tests/real_catalog.rs` se actualiza para la semilla.

Alternativa: una sola consulta con uniones. Menos viajes, pero cartesianos entre grupos de uso, objetivos y referencias, y más difícil de leer y mantener; no hace falta con este volumen.

### D13. Estrategia de QA

- API: Postman sobre los endpoints que cambian (listado, detalle con y sin alias, plantas con distintos niveles de seguridad, imagen y créditos), con el token como variable de entorno secreta. En QA anteriores el CLI de Postman estaba instalado pero sin sesión; si sigue así, se usa el equivalente con `curl` o un script de Python, y se anota.
- Interfaz: la app es nativa Android y no tiene destino web, así que Playwright no aplica (la QA archivada de `add-goal-search-screen` lo anotó). Se usan el emulador con `integration_test`, `adb` y `uiautomator`, como en `connect-app-to-backend` y `add-api-token-auth`. Si el emulador no está disponible, se reporta como no ejecutado.

## Risks / Trade-offs

- **[El cambio 1 no deja lo que este cambio lee]** `display_name`, `goal`, `goal_subarea`, `plant_goal.subarea_id` y `pending_review`, y la atribución con texto. → La tarea 1.1 comprueba la migración real antes de escribir consultas y detiene la implementación si falta algo, para ajustar el cambio 1 y no duplicarlo aquí.
- **[Imágenes pesadas o limitadas por Wikimedia]** El `url` puede ser el original de varios MB, y Wikimedia limita a clientes anónimos con un agente genérico. → Medir tamaños y respuestas con la base real (tarea 6.4), pedir un ancho acotado si la URL lo admite y fijar un `User-Agent`; sin imagen la ficha sigue completa.
- **[La planta tóxica no avisa suficiente]** El aviso de `General` solo aparece con nivel alto. → Los niveles se definen en la semilla desde TPPT y la EMA; la QA revisa tóxicas conocidas y una planta sin datos.
- **[«Objetivos de la EMA» se lee como indicación]** → Aclaración fija junto a cada objetivo, nombres sin verbos de efecto, prueba que los textos fijos no contienen palabras de efecto, y el origen (EMA) nombrado.
- **[Licencias CC BY-SA y términos no verificados de la EMA y TPPT]** La atribución visible mejora el cumplimiento pero no lo certifica. → El cambio 1 sigue exigiendo verificar los términos antes de publicar; la sección `Fuentes` muestra lo que la semilla guarda.
- **[Dos URL para un recurso (alias)]** → Sin caché de respuestas hoy; `Content-Location` identifica el canónico.
- **[Tolerancia del cliente oculta un backend defectuoso]** → Pruebas de contrato de la API y OpenAPI regenerado y verificado.
- **[Las fichas de plantas con muchos grupos de uso son largas]** → Lista desplazable y probada a 200 % de texto; sin paginación.
- **[Dependencia nueva `url_launcher`]** Añade un plugin nativo y una consulta de intents en el manifest. → Versión fijada en `pubspec.lock`, prueba con la plataforma simulada y alternativa de solo texto si el usuario lo prefiere.
- **[`display_name` vacío o ausente]** Si el registro no tiene nombre para mostrar, la API usa el nombre científico. → Prueba con una planta sin nombres comunes y con la lavanda de la semilla.

## Migration Plan

1. Implementar y probar en local con la semilla provisional del cambio 1 y con fixtures (la semilla completa es la tarea 11 de ese cambio).
2. Desplegar primero la API (aditiva: la app anterior ignora los campos nuevos), verificando el detalle de `lavandula-angustifolia` con el token.
3. Publicar la app nueva, que tolera un backend anterior.
4. Retroceso: revertir los commits de este cambio. La API vuelve a servir el contrato anterior y la app anterior sigue funcionando; no hay datos que migrar. Si el cambio 1 ya está desplegado, el retroceso solo quita lo servido, no lo guardado.

No se hace `push` a `main` sin el cambio 1 implementado y con la semilla completa, porque `main` despliega.

## Open Questions

- **`url_launcher` o solo texto.** Se propone abrir los enlaces de licencia e imagen con `url_launcher` (D9). Si el usuario prefiere no añadir la dependencia, cambia una tarea y un escenario de `plant-passport` (el enlace queda como texto copiable).
