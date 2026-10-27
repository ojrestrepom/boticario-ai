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

Lo que el cambio 1 deja en `catalog.db` y este cambio lee: `plant_profile` (nombre para mostrar `display_name`, origen, descripción, tipo de aceite), `plant_use_group` y `plant_use_group_ref` (actividad traducida y original, `n`, países), `plant_goal` (con `subarea_id` y `pending_review`) y `plant_goal_ref`, `goal` y `goal_subarea`, `plant_safety` y `plant_safety_ref`, `plant_image`, `plant_alias`, `plant_review_flag`, `reference.dataset` y `reference.license`, y `source` (con `license_url`, que añade la tarea 1.3) con sus tablas de atribución (`plant_*_source`).

## Goals / Non-Goals

**Goals:**

- Servir todo lo que la semilla guarda para el pasaporte con un contrato aditivo dentro de `/v1` y sin consultas a la red.
- Mostrar atribución y licencias de forma neutral (por planta), cumpliendo CC BY y CC BY-SA sin exponer procedencia por campo.
- Que ninguna ausencia de datos se lea como dato: «sin datos de seguridad» no es «segura», y «sin objetivos» no es «sin efecto».
- Que la app siga funcionando contra un backend anterior durante el despliegue.

**Non-Goals:**

- Los de `proposal.md` (cambio 3, capa humana, chat, miniaturas en Explorar, proxy de imágenes).
- Cambiar la semilla, sus herramientas o el esquema de `catalog.db`, salvo la URL de licencia por fuente (tarea 1.3), que no toca ningún registro de planta. Si falta algo más que este cambio necesita, se reporta y se ajusta el cambio 1; no se añade aquí.
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
| `useGroups` | lista | `activity`, `activitySource`, `count`, `countries`, `references[{id, citation, resolved}]` (`id` nulo y `resolved` falso en una cita sin resolver) |
| `goals` | lista | `id`, `name`, `subarea`, `area`, `evidence`, `references` |
| `safety` | objeto o `null` | `level` (`alto`, `medio`, `bajo` o `null`), `text`, `references` |
| `image` | objeto o `null` | `url`, `pageUrl`, `author`, `license`, `licenseUrl`, `attributionRequired` |
| `credits` | lista | `name`, `license`, `licenseUrl`, `attribution`, `url` |

`parts` (que ya contiene `partsUsed`), `names` y `uses` no cambian de forma. `uses` se conserva porque quitarlo sería incompatible dentro de `/v1`; la app nueva lee `useGroups`, y `uses` queda para clientes anteriores y como respaldo del cliente (D11). El mapeo `traditionalUses` a `uses` ya lo escribe el cambio 1 (un uso por cada referencia resuelta), de modo que ambos son coherentes.

Cita completa (DEF-06 de la QA del cambio 1): `reference.citation` guarda una etiqueta («USDA Dr. Duke: referencia Steinmetz») y por eso los 24.286 usos la muestran como cita. La semilla guarda la cita completa en `traditionalUses[].citations[].text`, y el build la escribe en `plant_use_group_ref.text`. Por eso `useGroups[].references[].citation` es ese texto completo (y «<clave> (sin resolver)» en las no resueltas), no la etiqueta. `uses[].reference.citation` se mantiene como hoy, la etiqueta, por compatibilidad con clientes anteriores: cambiarla alteraría un valor de `/v1` ya consumido. La app nueva muestra `useGroups`, de modo que el usuario ve la cita completa; los clientes anteriores siguen viendo la etiqueta hasta que se actualicen. Alternativa descartada: poner el texto completo también en `uses[].reference.citation`; arregla la vista anterior, pero cambia el contenido de un campo existente.

Dos decisiones del usuario durante el cambio 1 fijan el contrato. Primero, `safety.level` es `null` cuando las fuentes traen advertencias (por ejemplo las contraindicaciones de la EMA para el eucalipto) pero ninguna fija un nivel: la API sirve el objeto con `level` nulo, el `text` y las `references`; `safety` es `null` solo cuando no hay ningún dato de precauciones. Segundo, un grupo de uso con al menos una cita resuelta se sirve con todas sus citas: las que no tienen obra identificada llevan `resolved` falso, `id` nulo y la cita «<clave> (sin resolver)»; los grupos sin ninguna cita resuelta (`plant_use_group.pending_review`) no se sirven. `uses` sigue teniendo una fila por referencia resuelta de los grupos servidos.

Alternativas:

- Un objeto anidado `profile` o `consolidated` con los campos nuevos. Agrupa lo nuevo, pero deja `description` y `origin` lejos de `family` y `names`, y obliga a un cliente a conocer dos niveles. Se descarta: el detalle ya es plano.
- Endpoints por subrecurso (`/v1/plants/{id}/safety`, `/images`, `/sources`). Permite pedir solo lo necesario, pero el pasaporte necesita todo para pintar tres pestañas y una cabecera, y se multiplican las peticiones y los estados de error. Se descarta; además nuevas rutas bajo `/v1` ampliarían la superficie sin un consumidor distinto.
- Reemplazar `uses` por `useGroups`. Es incompatible con `/v1` mientras exista un cliente; se descarta.
- Campos requeridos u omitidos si están vacíos. Se prefiere «siempre presentes»: el documento OpenAPI queda más simple y un cliente distingue «sin dato» de «campo que no conozco».

El orden estable es parte del contrato de uso, no de la forma: `useGroups` por `count` descendente y luego actividad, `goals` por nombre, `credits` por nombre y `synonyms` por texto.

Los textos visibles (descripción, actividades traducidas, advertencias) los valida el cambio 1 (en español, sin dosis ni promesas de eficacia); la API los sirve tal cual y no los reescribe.

### D2. Nombre para mostrar: campo explícito y orden de los nombres comunes

Se añade `displayName` al listado y al detalle. El cambio 1 guarda el nombre para mostrar de forma explícita en `plant_profile.display_name`, y la API lo sirve tal cual: `displayName` es siempre ese valor (y, solo como defensa, el nombre científico si la planta no tiene fila de perfil o el valor es nulo). Según la regla del cambio 1, ese nombre es un nombre común en español o, si la planta no tiene ninguno, el nombre científico; la API no elige un nombre en otro idioma. Lo que cambia es el orden de los nombres comunes:

- Si el `displayName` es un nombre común, va primero entre los comunes y el resto sale por texto e idioma.
- Si el `displayName` es el nombre científico (1.195 plantas no tienen nombre común en español, y 571 de ellas tienen nombres comunes en otros idiomas, como «Velvetleaf» en `abutilon-theophrasti`), los comunes salen por texto e idioma, sin ninguno destacado. El nombre en otro idioma sigue disponible en `commonNames` y `names`, pero no es el principal.

Decisión del usuario sobre el caso de las plantas sin nombre en español (tarea 1.1): se mantiene la regla del cambio 1. Alternativa descartada: elegir como nombre para mostrar el primer nombre común en otro idioma. Daría un principal como «Velvetleaf» en una app en español y cambiaría la regla de la semilla, que el cambio 1 ya validó.

Por qué ambos: el campo explícito evita que un cliente dependa del orden de una lista (y es la única forma de saber que el principal es el científico); el orden mantiene el comportamiento de la app anterior («primer nombre común») cuando el nombre para mostrar es un nombre común, que con el orden alfabético mostraría un nombre distinto del elegido. En una planta sin nombre en español, la app anterior seguirá mostrando como principal el primer nombre común (el de otro idioma), porque no lee `displayName`; es un límite aceptado de la compatibilidad.

Alternativas:

- Solo reordenar, sin campo nuevo. Menos superficie, pero deja el contrato dependiendo de un orden implícito y la planta sin nombre común sin un valor de respaldo.
- Solo el campo, sin reordenar. Una app o un cliente de la versión anterior seguiría mostrando el primer nombre alfabético.
- Derivarlo del nombre común de menor `plant_name.id` (orden de inserción del build). No exige columna, pero depende de un orden implícito; se descarta ahora que el cambio 1 guarda `plant_profile.display_name`.

### D3. Qué muestran `Propiedades` y `Usos`

El mockup no define ninguna de las dos. Propuesta:

- `Propiedades`: dos secciones. `Objetivos registrados por la EMA`, con cada objetivo con nombre, subárea, área y tipo de documento de la EMA (monografía o entrada de lista), la cita y una aclaración fija («clasificación de la EMA, no una indicación de uso ni una promesa de eficacia»). `Precauciones`, con el texto, las citas y el nivel si lo hay (D4). El nombre es «Precauciones» y no «Seguridad», una traducción demasiado literal de *safety*.
- `Usos`: siempre al inicio, un aviso fijo (texto provisional que el usuario ajustará en la app): «Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver».» Después, los grupos de uso tradicional traducidos, con actividad, número de registros, países y todas las citas, con la etiqueta `Registro tradicional` y la aclaración de que es un registro y no un consejo. Las citas sin obra identificada se muestran como «(sin resolver)» en un estilo atenuado.
- Actividades sensibles: no hay lógica nueva en la app. Las enfermedades graves llegan de la semilla ya formuladas en el texto de la actividad («Uso tradicional, sin eficacia demostrada: cáncer») y las señales de riesgo (veneno, casos mortales, abortiva) llegan dentro del texto de `Precauciones` como advertencias, no como usos; la app muestra ambos tal como vienen.

Por qué: son los dos conjuntos que la semilla puede respaldar con cita. Los objetivos salen solo de la EMA, así que `Propiedades` es la pestaña donde una afirmación tiene una fuente regulatoria nombrada; los usos son registros etnobotánicos con citas, justo lo que `Usos` ya muestra.

Alternativas:

- `Propiedades` con la fitoquímica de USDA (compuestos y partes). Es dato disponible, pero la spec vigente prohíbe inferir eficacia desde la fitoquímica y una lista de compuestos invita a esa lectura. Se descarta.
- Los objetivos dentro de `Usos`. Mezcla una clasificación regulatoria con registros tradicionales; se pierde la distinción que el pasaporte hace entre «dato de fuente» y «registro tradicional».
- Una pestaña `Precauciones` nueva. Aleja el mockup (tres pestañas); se descarta, y el nivel alto se avisa en `General` (D4).
- `Usos` plano (una fila por uso, como hoy). Repite la actividad por cada cita y no muestra países; se descarta porque la semilla ya entrega el agrupado.
- Mostrar solo la actividad y las citas bajo un «ver más». Oculta contenido que debe ser alcanzable; la spec exige listas desplazables sin truncar.

Nombre de los objetivos: la API sirve `goals[].name` y `goals[].subarea` en español, leídos de las tablas `goal (id, label, position)` y `goal_subarea (id, goal_id, label, position)` que deja el cambio 1 y que el cambio 3 usa para `GET /v1/goals`; `plant_goal` referencia la subárea con `subarea_id`. Los ids de objetivo son `relajacion-estres`, `mejorar-el-sueno`, `cuidado-de-la-piel`, `alivio-respiratorio`, `cansancio-y-fatiga` y `otros-objetivos`, y los de subárea `digestion`, `vias-urinarias-y-genitales`, `dolor-e-inflamacion`, `boca-y-garganta`, `circulacion` y `molestias-oculares`. `goals[].area`, `goals[].evidence` y los países de los grupos de uso llegan en español desde la semilla.

### D4. Precauciones: texto con nivel opcional, citas, aviso en `General` solo si el nivel es alto

La sección se llama `Precauciones`. Los tres niveles se muestran como texto (`Alto`, `Medio`, `Bajo`) con el texto de advertencia y las citas, en `Propiedades`. Si `safety.level` es `null` (el texto y las citas existen, pero ninguna fuente fija un nivel), se muestra el texto y las citas sin etiqueta de nivel. Si el nivel es `alto`, `General` muestra además un aviso con el nivel que remite a `Propiedades`; sin nivel, o con `medio` o `bajo`, no hay aviso. `safety` nulo se muestra como «No hay precauciones registradas en las fuentes consultadas. Esto no significa que la planta sea segura.»

Por qué: una planta con nivel alto (tóxica) no debe quedar escondida en la tercera pestaña de una ficha cuya primera pestaña es una descripción amable. El aviso se limita al nivel alto para no cubrir de avisos las fichas; los niveles medio y bajo siguen en `Propiedades`. No se muestra nada que sugiera «segura»: el nivel `bajo` es un nivel de alerta (alergénica), no un sello.

Alternativas: aviso para medio y alto (más ruido en la ficha; las fototóxicas y carcinogénicas ya figuran en `Propiedades`); insignia siempre visible con «Sin datos» (alarma sobre ausencia de datos que no es un riesgo conocido); mostrar la seguridad solo en `Propiedades` (menos visible para plantas tóxicas).

### D5. Listado: `displayName` sí, miniatura no

El resumen del listado suma solo `displayName`, para que Explorar muestre «Lavanda» como principal con el orden y la regla del cliente. No suma la miniatura: son 50 imágenes remotas por página, de un host externo, con atribución por archivo, para una pantalla cuyo mockup las muestra pero que la spec ya declara con arte local provisional. El cambio 3 necesita una miniatura en P07 y reutiliza el objeto `image` de este cambio; si más adelante se quiere en Explorar, es un campo aditivo.

Alternativas: `image` completo en el resumen (pesa el listado y obliga a atribución en cada fila); `thumbnailUrl` solo (sin atribución visible en la fila, aceptable solo si la fila enlaza a la ficha, pero fuerza decidir tamaños de Commons ahora); ninguno (elegido).

### D6. `reviewFlags`: la API aplica una regla de omisión y no los expone

La API no expone los `reviewFlags` (estructurados como `{code, target, message}` en la semilla) ni ningún resumen de ellos. Sí aplica una regla: omite de `goals` todo objetivo con `plant_goal.pending_review = true` (hoy, `relajacion-estres` del hipérico). El resto del detalle se sirve completo.

Por qué: el cambio 1 dice que los flags no bloquean la presencia de la planta, y que ese objetivo «queda condicionado… antes de publicarse». Omitir el objetivo es la forma de cumplir ese «antes de publicarse» sin una capa humana. Los grupos de uso siguen la misma lógica: la API omite los grupos con `plant_use_group.pending_review = true` (ninguna cita resuelta) y sirve los demás, aunque el registro conserve el flag `cita-sin-resolver` de una cita suelta; la app no recibe ese flag y muestra la cita como «(sin resolver)». Los demás flags (identidad ambigua, solo género, grupo partido, respaldo de WFO, extracción de seguridad fallida, sin datos de seguridad) describen la procedencia de la identidad o ausencias que la app ya muestra como «sin datos»; exponerlos fijaría un vocabulario interno en el contrato antes de que exista la capa humana que lo gobierne.

Alternativas:

- Ignorar todos los flags (servir todo). Simple, pero publica el objetivo que el cambio 1 pide retener para el hipérico.
- Ocultar la planta entera si tiene cualquier flag. Quita del catálogo plantas legítimas (todas las de «sin datos de seguridad» y los 62 de solo género), contra lo que dice el cambio 1.
- Exponer `reviewFlags` en el detalle y que la app los marque. Honesto, pero deja la decisión de qué mostrar a la app, congela los códigos en el contrato y cualquier cambio de la capa humana sería un cambio de contrato.
- Exponer un booleano `pendingReview`. Con la ausencia de datos de seguridad como flag, sería verdadero en toda planta sin datos de seguridad, que es un flag frecuente, y dejaría de informar.

Cómo se identifica el objetivo condicionado: solo por `plant_goal.pending_review`, que escribe el build del cambio 1; la API no mantiene ninguna tabla de reglas ni interpreta códigos de flags, así que un flag nuevo no condiciona nada por omisión.

Cuando exista la capa humana, aprobar un objetivo cambia un dato (el flag se resuelve) y no el código.

### D7. Alias: 200 con el ID canónico, sin redirección

`GET /v1/plants/{id}` busca primero la planta por ID; si no existe, busca un alias en `plant_alias` y, si lo encuentra, devuelve el detalle de la planta canónica con `id` canónico en el cuerpo y `Content-Location: /v1/plants/<canónico>`. El ID de una planta tiene prioridad (el cambio 1 prohíbe que un alias iguale el ID de otra, pero la API lo comprueba en este orden). Los alias no aparecen en el listado como plantas. `q` sí los usa para encontrar la planta canónica (D14), porque los sinónimos de `plant_name` no cubren todos los nombres anteriores.

Por qué no una redirección: los clientes de la app usan `http` de Dart y el token viaja en `Authorization`; el comportamiento de las cabeceras al seguir una redirección depende del cliente y del host, y un cliente que no la siga rompería con un 301. Con 200 y `id` canónico, el cliente obtiene los datos y puede corregir su ID guardado, y no hay un salto extra. Hoy nadie guarda IDs, así que el valor es para clientes futuros (favoritos, enlaces).

Alternativas:

- 301 o 308 al ID canónico. Es la semántica correcta de HTTP para un recurso movido y deja una sola URL por recurso, pero depende del seguimiento de redirecciones con `Authorization` en cada cliente; se descarta por riesgo sin consumidor que lo necesite. Es compatible añadirlo después.
- No resolver alias (404). Más simple, pero pierde la única razón por la que el cambio 1 los guarda y deja un 404 sobre cientos de IDs que existían ayer.
- Un endpoint nuevo `GET /v1/aliases/{id}`. Una ruta más para el mismo resultado; se descarta.

Riesgo asumido: dos URLs sirven el mismo recurso (la canónica y las de alias). Una caché por URL duplicaría entradas; no hay caché de respuestas hoy.

### D8. Créditos neutrales a nivel de planta

`credits` es la unión sin repeticiones de los datasets que respaldan los datos de la planta: los de `source` por las tablas de atribución de la planta y los de `reference.dataset` de los objetivos, la seguridad y los grupos de uso, más Wikipedia cuando la descripción la resume. Cada entrada lleva `name`, `license`, `licenseUrl`, `attribution` y `url`. No indica el campo. `licenseUrl` es un dato de la fuente y no lógica de la API: sale de `source.license_url`, que viene de `licenseUrl` en `tools/catalog-seed/sources.json` y en el manifiesto de la semilla (tarea 1.3), y es `null` si la fuente no tiene una licencia con URL única (Commons, que declara la licencia por archivo y cuya imagen ya trae la suya, `ema_json`, `ema_pdf` y `tppt`). Las URL son las oficiales de Creative Commons: CC BY-SA 4.0 (`wikipedia_es`), CC BY 4.0 (`efsa`), CC BY 3.0 (`wcvp`) y CC0 1.0 (`usda`, `wfo` y `wikidata`). La API no la deriva del texto de la licencia, para no atar el código a nombres de licencia. La imagen no se repite en `credits`: su autor y licencia van en `image`, y la app los muestra en el pie de la imagen y en `Fuentes`.

Por qué: es el «dato neutral de créditos» que anticipó `remove-api-provenance`. Cumple la atribución de CC BY y CC BY-SA (nombre, licencia, enlace) sin volver a una lista de datasets por campo, y mantiene la API sin nombres de dataset en su código (los nombres son datos).

Alternativas:

- Procedencia por campo (`sources` en cada nombre, parte y uso). Es lo que se quitó en `remove-api-provenance`; vuelve a atar el contrato al modelo interno.
- Un endpoint `GET /v1/sources` con todas las fuentes. Retira de la ficha la atribución concreta de la planta, obliga a una segunda petición y a mostrar fuentes que la planta no usa. Se descarta.
- Créditos solo en la app como texto fijo. Sería una atribución global, no la de esa planta; la licencia de una imagen de Commons es por archivo, así que no puede ser fija.
- Incluir la imagen también en `credits`. Duplica la información; se prefiere un único origen (`image`).
- Derivar `licenseUrl` en la API a partir del texto de `source.license` (por ejemplo, «CC BY-SA 4.0» a su URL). Ataría el código a nombres de licencia y fallaría con textos libres como los de la EMA y TPPT; se descarta.
- Dejar `licenseUrl` en `null` para todos. CC BY, CC BY-SA y CC BY 3.0 piden indicar la licencia con su URI o un enlace, así que no cumpliría la atribución de Wikipedia, EFSA y WCVP; se descarta.

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
| Nombre común (el `displayName` es el nombre científico) | `No hay nombre común en español registrado`; no se muestra el nombre científico como nombre común |
| Nombres comunes (otros) | `No hay nombres comunes registrados` |
| Objetivos | `No hay objetivos registrados por la EMA para esta planta` |
| Precauciones | `No hay precauciones registradas en las fuentes consultadas. Esto no significa que la planta sea segura.` |
| Usos | `No hay usos tradicionales con referencia verificable disponibles` (texto vigente); el aviso fijo se muestra igualmente al inicio |
| Fuentes | `No hay fuentes registradas para esta planta` |

Alternativas: ocultar las secciones sin datos (la spec vigente exige decirlo explícitamente en `General`, y ocultar «precauciones» en una planta sin datos lo haría pasar por segura); un único mensaje «sin datos» por pestaña (pierde la distinción entre una planta sin usos y una sin seguridad).

Se descarta `Tipo de aceite: No aplicable: ficha de planta`: ahora el tipo de aceite sale de la semilla (`Esencial` según el compuesto `EO`) y la ausencia es «sin dato», no «no aplicable».

### D11. Cliente tolerante con los campos nuevos y respaldo de `uses`

El parser lee los campos nuevos si están y los trata como vacíos si faltan; un tipo erróneo o un `level` desconocido es error legible. Si falta `useGroups` pero hay `uses`, el modelo deriva grupos desde `uses` (uno por actividad). Si falta `displayName`, aplica la regla anterior. Así la app nueva funciona contra el backend viejo durante el despliegue y viceversa (el backend nuevo con la app vieja sigue funcionando por ser aditivo).

Alternativa: parseo estricto de los campos nuevos (como los requeridos). Detecta antes un backend mal desplegado, pero rompe el pasaporte entero si la app se publica antes que la API o si se retrocede la API. Se descarta; el costo es que un backend defectuoso que omita `goals` se vería como «sin objetivos». Se mitiga con las pruebas de contrato de la API (todos los campos siempre presentes).

### D12. Consultas y esquema

Este cambio no modifica el esquema de la API: la columna `source.license_url` (D8) la añade la tarea 1.3 a la migración v2 del cambio 1, que no se ha desplegado, sin crear una v3 y con `SCHEMA_VERSION` en 2. `catalog-core` suma tipos de dominio y filas para las tablas del cambio 1; `catalog-api` suma cargadores por planta (perfil, grupos de uso con referencias, objetivos, seguridad, imagen, alias, créditos, flags). La cita completa de los grupos de uso se lee de `plant_use_group_ref.text`, no de `reference.citation` siguiendo el patrón de `load_names` y `load_uses`. El detalle pasa de 3 a unas 9 consultas indexadas por `plant_id` sobre una base SQLite de solo lectura; no se espera impacto medible, y la tarea 11.2 lo mide con la base real. Los tests unitarios amplían `test_support.rs` (la `Fixture` que arma una base mínima) con filas de las tablas nuevas, y `tests/real_catalog.rs` se actualiza para la semilla.

Alternativa: una sola consulta con uniones. Menos viajes, pero cartesianos entre grupos de uso, objetivos y referencias, y más difícil de leer y mantener; no hace falta con este volumen.

### D13. Estrategia de QA

- API: Postman sobre los endpoints que cambian (listado, detalle con y sin alias, plantas con distintos niveles de precauciones, una con `level` nulo como el eucalipto, un grupo con una cita sin resolver, imagen y créditos), con el token como variable de entorno secreta. En QA anteriores el CLI de Postman estaba instalado pero sin sesión; si sigue así, se usa el equivalente con `curl` o un script de Python, y se anota.
- Interfaz: la app es nativa Android y no tiene destino web, así que Playwright no aplica (la QA archivada de `add-goal-search-screen` lo anotó). Se usan el emulador con `integration_test`, `adb` y `uiautomator`, como en `connect-app-to-backend` y `add-api-token-auth`. Si el emulador no está disponible, se reporta como no ejecutado.

### D14. Búsqueda por identificadores anteriores (alias)

`q` busca, además de en los nombres (`plant_name.normalized`), en `plant_alias.alias`. La consulta se normaliza como hoy y, para los alias, se reduce con `slug` (los caracteres que no son letras ni dígitos pasan a un guion); se compara por subcadena con el alias. Es equivalente a comparar la consulta con el alias con sus guiones como espacios. La planta se selecciona con `plant.id IN (nombres) OR plant.id IN (alias)`, de modo que cada planta cuenta una vez en la lista y en el total, y el alias no se devuelve como nombre: el elemento lleva solo el nombre científico y los comunes de siempre. Si `slug(q)` es vacío (por ejemplo `q=%`), los alias no aportan nada. El orden sigue siendo por nombre científico e identificador.

Por qué: la QA del cambio 1 (DEF-04) halló que `q=matricaria recutita` y `q=mentha piperita` dan 0 resultados, una regresión frente a la API anterior, que sí los encontraba. De los 628 identificadores que cambian, 357 tienen un nombre anterior que no está entre los nombres de la planta: 181 heterotípicos resueltos al aceptado, 135 nombres que USDA tenía como aceptados y 41 homotípicos. Su única huella es el alias, que es el slug del `TAXON` literal de USDA.

Medición con `data/build/catalog.db` construida desde la semilla completa (2.354 plantas, 650 alias) y los 357 casos de `qa/evidence/api/API-04-old-names-not-found.tsv` del cambio archivado:

| Regla | Casos recuperados |
|---|---|
| Alias, consulta solo normalizada con `normalize_name` (puntuación intacta) | 311 de 357 (87 %) |
| Alias, consulta reducida con `slug` (la regla de esta decisión) | 357 de 357 (100 %) |

La diferencia entre las dos filas son 46 nombres con puntuación, como `Acinos alpinus var. meridionalis`, cuyo alias es `acinos-alpinus-var-meridionalis`. En todos los casos la coincidencia es la planta nueva y ninguna consulta devuelve más de una planta. Con la regla, `matricaria recutita` encuentra `matricaria-chamomilla` y `mentha x piperita` encuentra `mentha-x-piperita`. `mentha piperita` sigue sin resultados: no es alias de ninguna planta y el único alias de `mentha-x-piperita` que lo menciona es `mentha-x-piperita-subsp-nothosubsp-piperita`, que lleva la `x` en medio y no contiene `mentha piperita` como subcadena. Es un límite conocido de la búsqueda por subcadena, no una pérdida nueva de este cambio.

Alternativas:

- Añadir los nombres anteriores como sinónimos científicos en la semilla (`plant_name`). La búsqueda por nombres los encontraría sin tocar la API y el detalle los mostraría, pero obliga a regenerar la semilla del cambio 1, que ya está archivada y verificada, y mezcla en `synonyms` nombres que la fuente taxonómica no da como sinónimos del aceptado (por ejemplo, el nombre que USDA tenía como aceptado). Se descarta aquí; sigue siendo posible como cambio de la semilla.
- No hacer nada. Deja la regresión de la búsqueda y el caso de la propuesta del cambio 1 (`matricaria-recutita`) sin resolver. Se descarta.
- Normalizar la consulta solo con `normalize_name` y compararla con el alias con guiones como espacios. Recupera 311 de 357: los nombres con `var.`, `subsp.` o `f.` fallan porque el alias no tiene puntos. Se descarta por la medición.

Riesgo: una consulta corta como `a` coincide con muchos alias; es el mismo comportamiento de subcadena que ya tienen los nombres. La consulta suma un `IN` sobre `plant_alias` (650 filas); el `LIKE '%…%'` no usa el índice, pero la tabla es pequeña. La tarea 4.3 lo verifica y la 11.2 mide el listado con la base real.

## Risks / Trade-offs

- **[El cambio 1 no deja lo que este cambio lee]** `display_name`, `goal`, `goal_subarea`, `plant_goal.subarea_id` y `pending_review`, y la atribución con texto. → La tarea 1.1 comprueba la migración real antes de escribir consultas y detiene la implementación si falta algo, para ajustar el cambio 1 y no duplicarlo aquí.
- **[Imágenes pesadas o limitadas por Wikimedia]** El `url` puede ser el original de varios MB, y Wikimedia limita a clientes anónimos con un agente genérico. → Medir tamaños y respuestas con la base real (tarea 6.4), pedir un ancho acotado si la URL lo admite y fijar un `User-Agent`; sin imagen la ficha sigue completa.
- **[Imágenes pesadas: decisión pendiente sobre la miniatura]** La medición de la tarea 6.4 (`qa/image-sizes.md`, 20 plantas) arroja lo siguiente y la decisión es del usuario.
  - Los originales van de 0,02 MB a 74,65 MB (`berberis-aquifolium`), con mediana de 1,28 MB.
  - El 40 % (8 de 20) supera 2 MB y dos pasan de 7 MB; lavanda, menta y eucalipto son ligeras (menos de 200 KB).
  - Wikimedia sirve miniaturas de 500 px (de 33 a 115 KB en la muestra), pero no de 640 px, y la app hoy carga `image.url` tal cual.
  - Está pendiente decidir si se adopta una función pura que convierta la URL en la de la miniatura de 500 px.
- **[El aviso fijo de `Usos` es provisional]** El texto lo ajustará el usuario en la app. → Vive en un solo lugar del código de la app, con una prueba que verifica que se muestra siempre al inicio y no contiene lenguaje de eficacia.
- **[La planta tóxica no avisa suficiente]** El aviso de `General` solo aparece con nivel alto. → Los niveles se definen en la semilla desde TPPT y la EMA; la QA revisa tóxicas conocidas y una planta sin datos.
- **[«Objetivos de la EMA» se lee como indicación]** → Aclaración fija junto a cada objetivo, nombres sin verbos de efecto, prueba que los textos fijos no contienen palabras de efecto, y el origen (EMA) nombrado.
- **[Licencias CC BY-SA y términos no verificados de la EMA y TPPT]** La atribución visible mejora el cumplimiento pero no lo certifica. → El cambio 1 sigue exigiendo verificar los términos antes de publicar; la sección `Fuentes` muestra lo que la semilla guarda.
- **[Dos URL para un recurso (alias)]** → Sin caché de respuestas hoy; `Content-Location` identifica el canónico.
- **[Tolerancia del cliente oculta un backend defectuoso]** → Pruebas de contrato de la API y OpenAPI regenerado y verificado.
- **[Las fichas de plantas con muchos grupos de uso son largas]** → Lista desplazable y probada a 200 % de texto; sin paginación.
- **[Dependencia nueva `url_launcher`]** Añade un plugin nativo y una consulta de intents en el manifest. → Versión fijada en `pubspec.lock`, prueba con la plataforma simulada y alternativa de solo texto si el usuario lo prefiere.
- **[`display_name` vacío o ausente]** Si el registro no tiene nombre para mostrar, la API usa el nombre científico. → Prueba con una planta sin nombres comunes y con la lavanda de la semilla.

## Migration Plan

1. Implementar y probar en local con la semilla completa del cambio 1 (2.354 plantas, `data/seed/`) y con fixtures.
2. Desplegar primero la API (aditiva: la app anterior ignora los campos nuevos), verificando el detalle de `lavandula-angustifolia` con el token.
3. Publicar la app nueva, que tolera un backend anterior.
4. Retroceso: revertir los commits de este cambio. La API vuelve a servir el contrato anterior y la app anterior sigue funcionando; no hay datos que migrar. Si el cambio 1 ya está desplegado, el retroceso solo quita lo servido, no lo guardado.

Los cambios 1 y 2 se despliegan juntos, porque `main` despliega y la app necesita el contenido y el contrato nuevos a la vez; no se hace `push` a `main` hasta que ambos estén implementados.

## Open Questions

- **`url_launcher` o solo texto.** Se propone abrir los enlaces de licencia e imagen con `url_launcher` (D9). Si el usuario prefiere no añadir la dependencia, cambia una tarea y un escenario de `plant-passport` (el enlace queda como texto copiable).

## Esquema real

Resultado de la tarea 1.1. Se construyó `data/build/catalog.db` desde la semilla completa con `mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- build` (2.354 plantas, 650 alias, 5.200 avisos de revisión, 43.940 referencias, 10 fuentes en la salida; `metadata.schema_version` es 2) y se leyeron `data/migrations/2026-10-26-000000_catalog_v2/up.sql`, `backend/catalog-core/src/schema.rs`, `rows.rs` y `backend/catalog-ingest/src/seed_build.rs`. Las consultas se hicieron con `sqlite3`. Hay 25 tablas y no falta ninguna de las que lista la tarea.

Tablas y columnas comprobadas (todas existen con estos nombres):

| Tabla | Columnas | Observaciones |
|---|---|---|
| `plant_profile` | `plant_id` (PK), `display_name`, `authors`, `origin`, `description`, `oil_type`, `record_version`, `bundle_hash`, `prompt_version` | 2.354 filas, `display_name` nunca nulo; 1.459 con descripción, 2.197 con origen y 587 con `oil_type` `Esencial` (el resto es nulo) |
| `plant_profile_ref` | `plant_id`, `field`, `reference_id` | `field` en `scientificName`, `family`, `displayName`, `origin`, `description`, `oil`, `partsUsed`; la descripción de la lavanda cita la referencia de Wikipedia con su URL |
| `plant_use_group` | `id`, `plant_id`, `position`, `activity`, `activity_source`, `n`, `countries` (JSON), `pending_review` | 17.526 grupos en 1.459 plantas, 366 con `pending_review` verdadero |
| `plant_use_group_ref` | `use_group_id`, `key`, `position`, `text`, `resolved`, `reference_id` (nulo si no está resuelta) | 24.882 resueltas y 1.361 sin resolver; `text` es la cita completa y, en las no resueltas, «<clave> (sin resolver)» |
| `plant_goal` | `id`, `plant_id`, `goal_id`, `subarea_id`, `position`, `area`, `evidence`, `pending_review` | 288 filas, 170 con subárea y 1 pendiente (`hypericum-perforatum`, `relajacion-estres`) |
| `plant_goal_ref` | `plant_goal_id`, `reference_id` | |
| `goal` | `id`, `label`, `position` | 6 objetivos, con los ids supuestos |
| `goal_subarea` | `id`, `goal_id`, `label`, `position` | 6 subáreas, todas de `otros-objetivos`, con los ids supuestos |
| `plant_safety` | `plant_id` (PK), `level` (`alto`, `medio`, `bajo` o nulo), `text` | 873 plantas: 112 altos, 204 medios, 85 bajos y 472 sin nivel; las demás no tienen fila |
| `plant_safety_ref` | `plant_id`, `reference_id` | 3.653 filas; datasets `efsa`, `ema_pdf`, `tppt`, `usda` y `wikipedia_es` |
| `plant_image` | `plant_id` (PK), `url`, `page_url`, `author`, `license`, `license_url`, `attribution_required` | 1.860 plantas; 51 sin autor y 419 sin `license_url` |
| `plant_alias` | `alias` (PK), `plant_id` | 650 alias, ninguno igual al id de una planta |
| `plant_review_flag` | `id`, `plant_id`, `code`, `target`, `message` | 5.200 filas; `objetivos-omitidos-por-toxicidad` e `interacciones-graves-estres` existen como códigos |
| `reference` | `id`, `citation`, `dataset`, `license`, `url` | 43.940 filas, `dataset` y `license` nunca nulos; `url` nulo en parte de las de USDA, WCVP, EFSA, TPPT y WFO |
| `source` | `id`, `name`, `version`, `license`, `citation`, `url`, `checksum` y, desde la tarea 1.3, `license_url` (nulable) | 10 filas |
| `plant_name_source`, `plant_part_source`, `plant_use_source`, `plant_source_id`, `reference_source` | pares de claves a `source` | Cada nombre, parte y uso tiene al menos una fuente, y las 2.354 plantas tienen `plant_source_id`; toda `reference` tiene `reference_source` |

Atribución por fuente: cada una de las 10 fuentes (`commons`, `efsa`, `ema_json`, `ema_pdf`, `tppt`, `usda`, `wcvp`, `wfo`, `wikidata`, `wikipedia_es`) tiene `name`, `license`, `citation` (el texto de atribución exigido, por ejemplo «Colaboradores de Wikipedia en español (...). Texto bajo CC BY-SA 4.0; el historial de cada artículo lista a sus autores.») y `url`, todos no nulos. Idioma: `area` y `evidence` de `plant_goal` están en español («Tos y resfriado», «La EMA tiene una monografía en esta área.»), y los países de `plant_use_group.countries` también («Turquía», «Estados Unidos», «Otros lugares»); una búsqueda de países en inglés («United States», «Germany», «Turkey») y de textos con «the» u «of» no encontró casos. Las actividades traducidas siguen las observaciones de DEF-07 del cambio 1 (términos sin traducir en algunos grupos).

Diferencias con lo supuesto (ninguna bloquea las tareas siguientes, pero tres cambian lo que hay que implementar):

- `reference.dataset` y la clave de `plant_*_source` son el id de la fuente (`usda`, `wikipedia_es`), no el nombre para mostrar. Para `credits.name`, `license`, `attribution` y `url` hay que unir con `source.id`: `name` sale de `source.name`, `attribution` de `source.citation` y `url` de `source.url`. Para la descripción derivada de Wikipedia, el enlace al artículo sale de `reference.url` de la referencia `description` de `plant_profile_ref` (la de `source.url` es solo el sitio). `source.license` es texto libre («CC BY-SA 4.0», pero también «por archivo: CC0, dominio público, CC BY o CC BY-SA» para Commons).
- No había URL de la licencia en `source` ni en `reference` (`credits.licenseUrl`): el esquema tenía `license_url` solo en `plant_image`. Decisión del usuario: la URL de licencia es un dato de la fuente. Se añade `licenseUrl` opcional (cadena https o `null`) en `tools/catalog-seed/sources.json` y en las fuentes de `data/seed/manifest.json`, la columna nulable `source.license_url` en la migración v2 (nada se ha desplegado, así que no hay v3) y `credits.licenseUrl` se lee de ahí (D8). Valores: `wikipedia_es` CC BY-SA 4.0, `efsa` CC BY 4.0, `wcvp` CC BY 3.0, `usda`, `wfo` y `wikidata` CC0 1.0, y `null` en `commons`, `ema_json`, `ema_pdf` y `tppt`. La implementa la tarea 1.3.
- `reference.license` puede diferir de `source.license` (1.852 referencias; por ejemplo Commons por archivo): en los créditos de una fuente vale `source.license`.
- Dos fuentes de la EMA (`ema_json` y `ema_pdf`) tienen nombres propios distintos, de modo que una planta con objetivos de ambas lleva dos créditos de la EMA.
- `reference.citation` es una etiqueta («USDA Dr. Duke: referencia Steinmetz»); la cita completa de los grupos de uso solo está en `plant_use_group_ref.text` (véase D1).
- Los alias son el slug del nombre de USDA, y para `q` hay que compararlos con `slug(q)` (véase D14).
- Nombre para mostrar: la build ya no escribe el nombre científico como nombre común de idioma `la` (DEF-02 corregido). En 571 plantas el `display_name` es el nombre científico aunque la planta tiene nombres comunes en otro idioma (por ejemplo `abutilon-theophrasti`, con «Velvetleaf» en inglés), porque no tienen nombre común en español (flag `sin-nombre-comun-es`, 1.195 plantas en total, de las cuales 624 no tienen ningún nombre común). En esas, el nombre para mostrar no está entre los nombres comunes y no puede ser «el primero de ellos». Decisión del usuario: se mantiene la regla del cambio 1 (un nombre en español o, si no lo hay, el científico) y D2 y el requisito «Nombre para mostrar y orden de los nombres comunes» se ajustaron: `displayName` es siempre `plant_profile.display_name`, va primero entre los comunes solo si es un nombre común, y si es el científico los comunes salen por texto e idioma sin ninguno destacado. La tarea 2.1 prueba ese caso.
- `catalog-core` ya tenía `schema.rs` y `rows.rs` con todas las filas Diesel de las tablas nuevas (la tarea 1.2 no necesitó añadir ninguna; `SourceRow` ganó `license_url` con la tarea 1.3).

Consultas de muestra, con `sqlite3 data/build/catalog.db`:

- `select display_name, origin, oil_type from plant_profile where plant_id='lavandula-angustifolia'` devuelve «Lavanda», «Sureste y suroeste de Europa.» y «Esencial».
- `select activity, countries, n from plant_use_group where plant_id='lavandula-angustifolia'` devuelve, entre otros, «Carminativo», `["Otros lugares","Turquía"]` y 2.
- `select key, text from plant_use_group_ref where use_group_id=8864` devuelve la clave `Steinmetz` con «Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam.» y la clave `Woi.6`.
- `select level, substr(text,1,60) from plant_safety where plant_id='eucalyptus-globulus'` devuelve `level` nulo con el texto de las contraindicaciones de la EMA, y la lavanda tiene nivel `medio`.
- `select alias, plant_id from plant_alias where plant_id='salvia-rosmarinus'` devuelve `rosmarinus-officinalis`, y `matricaria-recutita` lleva a `matricaria-chamomilla`.
- `select plant_id, goal_id, pending_review from plant_goal where pending_review=1` devuelve solo `hypericum-perforatum` con `relajacion-estres`.

## Notas de implementación (tareas 3.4 a 5.3)

Medición de 4.3 con `data/build/catalog.db` desde la semilla completa (2.354 plantas, 650 alias), ejecutando la búsqueda real del repositorio (`list_plants`) y no una consulta aparte: los 357 nombres anteriores de `qa/evidence/api/API-04-old-names-not-found.tsv` del cambio archivado encuentran su planta nueva, 357 de 357 (100 %), como en la medición previa de D14. La prueba ignorada `the_357_previous_names_find_their_new_plant` de `tests/real_catalog.rs` lo repite y falla si baja de 357. `matricaria recutita` encuentra `matricaria-chamomilla`, `mentha piperita` no encuentra nada (límite conocido), `mentha x piperita` encuentra `mentha-x-piperita` y `rosmarinus officinalis` devuelve `salvia-jordanii`, `salvia-rosmarinus` y `salvia-x-lavandulacea` una sola vez cada una, porque sus nombres científicos (variedades y formas) contienen la consulta.

Diferencias con lo escrito en D8 y en la tarea 3.4, sin cambio de contrato: el crédito de una fuente sale cuando ella respalda algo que la API sirve. Se unen las tablas `plant_name_source`, `plant_part_source` y `plant_use_source`, la fuente de la familia (`plant.family_source_id`) y el `reference.dataset` de todas las referencias del perfil (`plant_profile_ref`, no solo la descripción), de los objetivos y grupos de uso servidos y de las precauciones. Los objetivos y grupos pendientes de revisión no se sirven y por eso no acreditan su fuente. `plant_source_id` (el identificador que cada fuente da a la planta) no acredita, porque no es un dato que la API muestre. Con la base real, la lavanda tiene siete créditos (EFSA, las dos de la EMA, TPPT, USDA, Wikipedia en español y WCVP) y el eucalipto siete (cambia TPPT por Wikidata). La `url` del crédito de un dataset es la `reference.url` de la referencia de la descripción cuando esta es de ese dataset (el artículo de Wikipedia) y, si no, `source.url`.

Detalle por alias: `get_plant` del repositorio resuelve el alias y devuelve la planta canónica; el handler compara el `id` devuelto con el pedido para añadir `Content-Location`, sin cambiar el trait `CatalogRepository`.
