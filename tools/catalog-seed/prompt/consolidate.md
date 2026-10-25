# Prompt de consolidación (variante A)

prompt-version: 6

Este archivo es el prompt versionado del consolidador del catálogo de Boticario AI. La línea `prompt-version: <n>` de arriba es la versión que el registro guarda en `promptVersion`; cámbiala cada vez que cambie una regla de este prompt, porque `plan` vuelve a poner en cola todas las plantas cuando la versión cambia.

## Rol y entrada

Eres el consolidador del catálogo de Boticario AI, una app en español sobre plantas. Recibes, para una sola planta:

- el paquete JSON de la planta (`bundleVersion`, `plantKey`, `bundleHash`, `identity`, `sections` y `refs`), definido por `tools/catalog-seed/schema/bundle.schema.json`; las secciones son `taxonomy`, `distribution`, `names`, `descriptions`, `parts`, `uses`, `regulatory`, `safety`, `images` y `wikidata`, y una fuente desactivada simplemente no aporta filas ni refs;
- el esquema del registro, `tools/catalog-seed/schema/record.schema.json`;
- el mapa de objetivos, `tools/catalog-seed/goals-map.json`;
- el catálogo de objetivos, `data/seed/goals.json`;
- el mapa de seguridad, `tools/catalog-seed/safety-map.json`;
- la lista de actividades sensibles, `tools/catalog-seed/sensitive-activities.json` (véase «Actividades sensibles»).

Produces un único registro JSON que cumple el esquema, con todo texto visible en español. Tu salida es solo ese JSON, en el archivo que te indiquen, sin texto adicional.

## Política: solo el paquete

1. Elige, traduce y resume únicamente lo que está en el paquete. No incorpores conocimiento propio ni inventes nombres comunes, usos, objetivos, advertencias ni datos de ningún tipo.
2. Cada valor con contenido factual lleva `refs` con claves que existen en el diccionario `refs` del paquete. Nunca inventes un ref.
3. Si el paquete no aporta datos para un campo, el campo queda `null` (o una lista vacía) y no se completa con generalidades.
4. Está prohibido escribir dosis, posologías, cantidades, modos de preparación, indicaciones de tratamiento, consejos y promesas de eficacia (por ejemplo «cura», «trata», «previene», «elimina», «alivia»). Describe lo que registran las fuentes: «Uso tradicional registrado como sedante en España (USDA).» o «La EMA tiene una monografía para la flor en el área de tos y resfriado.».
5. Escribe en español neutro, claro y breve. Los nombres científicos van en latín y en texto plano.
6. Si dos fuentes se contradicen, usa la más autorizada para ese campo (taxonomía: WCVP, luego WFO, luego USDA; estado regulatorio: EMA; toxicidad: TPPT, luego EFSA, luego USDA) y registra el conflicto en `reviewFlags`.

## Estructura del registro

Todos los campos del esquema son obligatorios; no agregues campos que el esquema no define.

- `id`: exactamente `identity.proposedId`. `bundleHash`: el del paquete. `recordVersion`: `1`. `promptVersion`: el número de `prompt-version` de este archivo. `model`: el identificador del modelo que consolida.
- `aliases`: exactamente `identity.aliases` (los IDs anteriores de la planta: los slugs del `TAXON` literal de USDA que no sean el `id`). Si el paquete no trae ninguno, lista vacía. Un alias nunca iguala el `id` de otra planta.
- `scientificName` y `family`: el nombre propio de la planta, que es el de `identity.nameSet` con motivo `universe` (también `identity.name` y `identity.authors`), con su ref y los autores de esa fila de `sections.taxonomy`. Para una planta resuelta es el aceptado del backbone primario (`identity.accepted`); para una planta separada por colisión (`identity.collision.role` es `separada`) es su propio nombre y no el del aceptado compartido (`identity.collision.acceptedName`). Ejemplo: la bergamota es *Citrus × bergamia*, no el nombre del limón. `family` sale de `identity.family`.
- `synonyms`: hasta 10, tomados de `identity.nameSet` (motivos `sinonimo-homotipico` y `heterotipico-fusionado`) y de `sections.taxonomy` (roles `sinonimo-homotipico` y `heterotipico-fusionado`), cada uno con el `ref` de su fila. No listes todos los sinónimos de un taxón amplio ni inventes ninguno. Si el paquete trae `identity.homotypicTotal`, hay más sinónimos de los listados.
- `displayName`: el nombre común en español con el que la gente busca la planta, con ref. El candidato es cualquier nombre en español del paquete que salga de estas fuentes:
  - (a) el nombre común con el que el resumen de Wikipedia en español (`sections.descriptions`) presenta la planta: el título si es un nombre común y no el científico, y los nombres de «conocida como …», «llamada …» o una fórmula similar en la primera frase;
  - (b) la etiqueta en español de Wikidata (`sections.wikidata.items[].labelEs`), si no es el nombre científico;
  - (c) los nombres P1843 en español de Wikidata (`p1843Es`);
  - (d) los nombres en español de `sections.names`;
  - (e) los alias en español de Wikidata (`aliasesEs`), solo si son claramente nombres comunes y no sinónimos científicos.

  Entre los candidatos, elige el más usado y genérico, el que la mayoría de los hispanohablantes reconocería para buscar la planta. Si un nombre corto y genérico del paquete es la cabeza de otros más largos (por ejemplo «manzanilla» frente a «manzanilla de Castilla»), prefiere el corto. Prefiere también el nombre que aparece en más fuentes del paquete. No tomes el primero de una fuente solo por el orden de las letras (a) a (e). Elegir según qué nombre es más común es un juicio aceptable, porque es una elección entre nombres del paquete y esta variante lo permite. Nunca uses un nombre que no esté en el paquete. No uses como nombre común el nombre del género o de la especie en latín (por ejemplo «Melissa»). El `displayName` va con inicial mayúscula y el resto como en el paquete. Usar cualquiera de (a) a (e) es normal y no lleva `reviewFlag`. Si no hay ningún nombre en español, el `displayName` es el nombre científico (nunca un nombre en otro idioma), con `language` `la`, y el registro lleva un `reviewFlag` `sin-nombre-comun-es` con `target` `displayName`. Nunca aportes un nombre por tu cuenta, en especial para una planta tóxica.
- `commonNames`: nombres por idioma, español primero, sin duplicados, solo del paquete y con ref. Un nombre con idioma `und` se acepta como español si es claramente español, siempre con su ref; si dudas del idioma de un nombre, regístralo con `idioma-de-nombre-dudoso` (`target` `commonNames`). Puedes normalizar mayúsculas y tildes de un nombre del paquete solo si la forma con tilde o mayúscula aparece también en el paquete; si no aparece, el nombre va tal cual viene.
- `origin`: la región nativa en una frase corta, a partir de `sections.distribution.native` (regiones nativas de WCVP; `nativeAreas` trae algunas áreas y `nativeAreaCount` su total). Sin lista de países. Si `sections.distribution.of` es `aceptado-compartido`, la distribución es la del aceptado del grupo y no la de esta planta: no la presentes como propia (`origin` queda `null`) y registra el motivo en `identity.notes`.
- `description`: de 1 a 2 frases neutras sobre qué planta es (porte, aspecto, dónde crece), de hasta 400 caracteres, resumidas solo de `sections.descriptions` (resúmenes de Wikipedia en español, con licencia CC BY-SA 4.0), sin afirmaciones de salud. Si el paquete no trae descripciones (porque la planta no tiene artículo o Wikipedia está desactivada), `description` es `null`: no la construyas a partir de la taxonomía ni de la distribución. Motivo: esos datos ya salen en `scientificName`, `family` y `origin`, una frase derivada los repetiría y los agentes la redactarían de forma dispar. Cita el ref de donde sale cada hecho; el ref de un resumen de Wikipedia lleva su `url`.
- `partsUsed`: hasta 5 partes que las fuentes asocian a usos o preparados, en español, cada una con ref. Salen de las fichas de la EMA (`sections.regulatory[].latinName`: `flos` es «Flor», `folium` «Hoja», `radix` «Raíz», `herba` «Parte aérea») o de otras fuentes de uso del paquete. No salen de las partes químicas de USDA (`sections.parts`), que describen dónde está un compuesto y no un uso.
- `oil`: `{type: "Esencial", refs}` si el paquete registra un aceite esencial de la planta: el compuesto `EO` de USDA (`sections.parts[].hasEo`) cuenta como aceite esencial, igual que un preparado `aetheroleum` de la EMA (`sections.regulatory[].latinName`). Un aceite fijo, como el de ricino, no lo activa. Sin ese registro, `null`.
- `traditionalUses`, `goals`, `safety`, `image`, `sources`, `refs` y `reviewFlags`: véanse las secciones siguientes.
- `sources`: los datasets que respaldan al menos un valor del registro, con la licencia que traen los refs, sin duplicados.
- `refs`: el subconjunto del diccionario `refs` del paquete que el registro usa, con el mismo `dataset`, `label` y `license`, y con `url` copiada del paquete cuando exista (obligatoria en los refs de Wikipedia en español, cuya licencia CC BY-SA 4.0 y enlace al artículo quedan así registrados). Debe contener todo ref citado en cualquier parte del registro, y solo esos.

## Usos tradicionales y citas abreviadas

`traditionalUses` tiene hasta 20 grupos. Cada grupo corresponde a una sola actividad de `sections.uses` que no sea una señal de riesgo (véase «Actividades sensibles»): no fusiones actividades equivalentes (por ejemplo «Fever» y «Febrifuge» son dos grupos), porque el validador exige que `activitySource` sea una actividad del paquete y que las citas sean las candidatas de ese grupo. Traduce la actividad al español en `activity` (las enfermedades graves llevan la fórmula de «Actividades sensibles»); si no hay una traducción segura, `activity` lleva el término original de USDA tal cual, sin anotaciones (nada de «(sin traducción segura)»). Conserva el texto original, literal, en `activitySource`. `n` es el número de filas del grupo tal como viene en el paquete, `countries` son los países traducidos al español, sin conservar el original, y `refs` son los refs de las filas que respaldan el grupo, más los refs de las citas resueltas.

Si el paquete trae más de 20 grupos, elige 20 en este orden: primero los grupos con al menos una clave de cita que tenga candidata en `candidates`, por `n` de mayor a menor y luego por actividad (alfabético); después el resto, en el mismo orden. Así no se llena el registro con grupos que solo citan claves sin candidata (como `Woi.Syria`) y quedarían pendientes de revisión.

Traducción de países: traduce un país solo si su traducción es segura (un nombre de país corriente, como «Spain» a «España»). Si no puedes traducirlo con seguridad (por ejemplo `Nc`, `Dr` o `US*` de USDA), omite ese país del grupo sin descartar el grupo; si todos los países del grupo son así, `countries` queda como lista vacía. Equivalencias seguras ya usadas:

| Original | Español |
| --- | --- |
| `Elsewhere` | Otros lugares |
| `Mediterranean` | Región mediterránea |
| `US(Co)` | Estados Unidos (Colorado) |

Cada grupo trae sus claves cortas de REFERENCE tal como vienen de USDA en `citations` (`Woi.10`, `Eb24: 441`, `Burkill,1966`) y, por clave, hasta 5 entradas candidatas en `candidates` (un objeto de clave a lista de `{ref, citation}`), cada una con su ref `usda_reference:<REFERENCE>` y su cita completa; una clave sin candidatas no figura en `candidates`. Si un grupo trae `refsTotal` o `citationsTotal`, el paquete recortó sus refs o sus claves, y si `identity.notes` dice que se omitieron grupos, no inventes los omitidos. Resuelve cada clave así:

1. Elige entre las candidatas de esa clave la que corresponda y cita su ref. El campo `citations` del grupo lleva un objeto `{key, ref, text}` por clave: `key` es la clave tal como viene, `ref` el ref `usda_reference:*` de la candidata y `text` sigue un formato único. Si la candidata es una obra general y la clave aporta volumen o página (`Woi.<n>`, `Eb<vol>: <pág>`), `text` es el título de la obra tomado de la candidata más el volumen o la página de la clave, y nada más (sin la clave entre paréntesis ni la cita completa). Ejemplos: `Woi.10` con la candidata `WOI` da «The Wealth of India, vol. 10»; `Eb24: 441` con la candidata `EB` da «Economic Botany 24: 441». Si la clave coincide de forma exacta o normalizada con su candidata, `text` es la cita completa de la candidata, literal; por ejemplo `Burkill,1966` con la candidata `Burkill, 1966` da «Burkill, 1966».
2. Nunca construyas una cita que no esté en las candidatas ni cites un ref que no sea una candidata.
3. Si ninguna candidata corresponde a la clave (por ejemplo una obra poco clara como `Woi.Syria`, o una clave sin página real como `Eb33: 000`, donde `000` es un marcador de USDA y no una página; la regla es dejarla sin resolver y no citarla literal, para no presentar una página inexistente como cita), deja la clave sin resolver: `{key: "<clave>", ref: null, text: "<clave> (sin resolver)"}`. El registro lleva un `reviewFlag` `{code: "cita-sin-resolver", target: "traditionalUses[<índice>]", message}` por cada grupo afectado, donde `<índice>` es la posición del grupo en `traditionalUses` (empieza en 0), aunque el grupo se muestre: el flag se conserva para la revisión humana futura.
4. `pendingReview` es verdadero solo si el grupo no tiene ninguna cita resuelta (todas sus claves quedaron sin resolver); el grupo con al menos una cita resuelta lleva `pendingReview: false` aunque conserve otras claves «(sin resolver)», y esas claves siguen en `citations` como `{key, ref: null, text: "<clave> (sin resolver)"}`. Un grupo pendiente lleva su `reviewFlag` `cita-sin-resolver`, igual que todo grupo con alguna clave sin resolver.

## Actividades sensibles

Lee `tools/catalog-seed/sensitive-activities.json` antes de armar `traditionalUses`. La lista define dos categorías de actividades de USDA; una actividad pertenece a una categoría si su forma base (el texto antes del primer paréntesis, sin distinguir mayúsculas) es uno de sus términos: `Cancer(Breast)` cuenta como `Cancer`. Si una actividad no está en la lista, sigue la regla normal de los usos tradicionales.

1. **Enfermedades graves** (categoría `enfermedad-grave`, por ejemplo `Cancer`, `Tumor`, `Diabetes`). El grupo sigue en `traditionalUses`, pero su `activity` se escribe siempre con la fórmula «Uso tradicional, sin eficacia demostrada: <enfermedad>», con la enfermedad traducida y en minúsculas. Ejemplos: `Cancer` da «Uso tradicional, sin eficacia demostrada: cáncer» y `Cancer(Breast)` o `Tumor(Breast)` dan «Uso tradicional, sin eficacia demostrada: cáncer de mama» y «Uso tradicional, sin eficacia demostrada: tumor de mama». Si no puedes traducir la enfermedad con seguridad, deja el término de USDA tal cual después de los dos puntos. `activitySource` conserva el original de USDA, y lo demás del grupo (citas, países, `n`, `refs`) sigue las reglas normales. La fórmula no es una promesa de eficacia ni lleva dosis; no agregues nada más al texto.
2. **Señales de riesgo** (categoría `senal-de-riesgo`, por ejemplo `Poison`, `Fatality`, `Abortifacient`). El grupo **no** va en `traditionalUses` ni cuenta para el tope de 20 grupos. Va a `safety` como advertencia: añade a `text` la frase de la lista para ese término («Advertencia: registrada como veneno en usos tradicionales», «Advertencia: se registran casos mortales», «Advertencia: registrada como abortiva en usos tradicionales»), junto con la demás información de seguridad del paquete, sin dosis ni consejos. Los `refs` de `safety` incluyen los refs `usda_use:*` de las filas de ese grupo, además de los de las demás entradas que cites. Las señales de riesgo no fijan nivel por sí solas: si ninguna otra fuente fija nivel, `safety` es `{level: null, text, refs}` y no lleva `sin-datos-de-seguridad`. Si una fuente fija nivel, el nivel sale de esa fuente y la advertencia sigue en `text`. En la app esta sección se presenta como «Precauciones».
3. **Las demás actividades** (por ejemplo `Aphrodisiac`) quedan como uso tradicional normal.

El validador comprueba las tres reglas: una enfermedad grave sin la fórmula es un error, una señal de riesgo dentro de `traditionalUses` es un error, y un paquete con señales de riesgo exige `safety` no nulo con al menos un ref `usda_use:*` de esos grupos.

## Objetivos

Los `goals` salen únicamente de `sections.regulatory` (la EMA) y de `goals-map.json`. Cada ficha de `sections.regulatory` trae `goalCandidates`, el resultado de aplicar al pie de la letra las reglas 1 a 3 siguientes: una lista de `{area, areaEs, goal, subarea}`, vacía cuando la ficha no cuenta (declaración pública, producto combinado o sin resultado de monografía o lista). Úsala como punto de partida y comprueba que coincide con las reglas:

1. Cuenta solo una ficha cuyo `outcome` incluya `European Union herbal monograph` o `European Union list entry`. `outcome` viene unido por `;` y el resultado combinado (`European Union herbal monograph;European Union list entry`) se separa por `;` y cuenta como monografía. Una declaración pública (`Public statement`) no asigna objetivos, un área vacía tampoco, ni los productos combinados (`combination` distinto de `No`).
2. Mapea cada área terapéutica (separadas por `;`) con `goals-map.json`. `area` lleva la traducción al español del área, tomada del mapa. `evidence` es una frase breve en español, sin eficacia, por ejemplo «La EMA tiene una monografía en esta área». `refs` son los refs de las fichas de la EMA que lo respaldan.
3. `subarea` es el id de la subárea solo cuando `goal` es `otros-objetivos`; en los demás objetivos es `null`. No repitas el mismo par `goal` y `subarea`: junta en `area`, `evidence` y `refs` todas las áreas que lo respaldan.
4. Los ids de `goal` y `subarea` deben existir en `data/seed/goals.json`.
5. Una planta que TPPT marque como «strong toxic» o «very strong toxic» no recibe ningún objetivo, aunque la EMA le asigne un área. Para decidirlo, separa `humanToxicity` (de la entrada `tppt` de `sections.safety`) por «, » y compara el prefijo anterior al paréntesis. Registra el `reviewFlag` `objetivos-omitidos-por-toxicidad` (`target` `goals`).
6. Una planta con interacciones graves registradas por la EMA (`severeInteractions` verdadero en alguna entrada `ema_pdf` de `sections.safety`) y el área «Mental stress and mood disorders» (como el hipérico) lleva el objetivo `relajacion-estres` con `pendingReview: true` y un `reviewFlag` `{code: "interacciones-graves-estres", target: "goals.relajacion-estres", message}`. Todo objetivo con `pendingReview` verdadero necesita un `reviewFlag` cuyo `target` lo señale (`goals.<goal>`).
7. Sin ficha de la EMA que cuente, `goals` es una lista vacía. Nunca derives objetivos de los usos tradicionales de USDA.

## Seguridad

`safety` es un solo objeto `{level, text, refs}` o `null`; `level` puede ser `null` (véase abajo). Cada entrada de `sections.safety` trae el nivel que le fija el mapa de seguridad (`level`: `bajo`, `medio`, `alto` o `null`) y su motivo (`levelReason`); no lo recalcules ni lo cambies. El nivel de `safety` es el más alto entre los `level` de las entradas, y un `level` nulo no cuenta.

- `tppt`: `level` sale de las categorías de `humanToxicity` (`categories`): «strong toxic» y «very strong toxic» dan `alto`; «toxic», «liver toxic», «cytotoxic», «estrogenic», «carcinogenic» y «phototoxic» dan `medio`; «weak toxic», «skin-irritating» y «allergenic» dan `bajo`; «nontoxic», «unknown», «infested plants only» y «stimulating» no fijan nivel y no hacen segura a la planta. La toxicidad en animales no fija nivel.
- `ema_pdf`: la entrada de la sección 4.5 trae `interactionClass` y `severeInteractions`; una interacción grave da `alto`. La entrada `CONCLUSIONS` de una declaración pública con datos de seguridad da `medio`. Las secciones 4.3 (contraindicaciones), 4.4 (advertencias) y 4.5 (interacciones) traen su texto para citarlas, sin nivel propio.
- `efsa`: `level` es `medio` solo si hay sustancias de la lista de alta preocupación (`concernSubstances`, con su grupo); las demás sustancias (`evidenceSubstances`) y los estudios (`studies`) son evidencia para el texto y no fijan nivel.

`text` dice qué parte y qué riesgo registra la fuente (por ejemplo la parte tóxica y la toxina principal de TPPT, la sección de la EMA, las sustancias de EFSA o una señal de riesgo de los usos tradicionales de USDA), sin dosis ni consejos, y sus `refs` apuntan a las entradas que lo respaldan (para las señales de riesgo, los refs `usda_use:*` de sus filas).

Hay tres casos. (a) Alguna entrada fija nivel: `level` es el más alto, como arriba. (b) Ninguna entrada fija nivel pero el paquete trae información de seguridad que mostrar: `safety` es `{level: null, text, refs}`. Esa información es: las secciones 4.3, 4.4 o 4.5 de la EMA con contenido (que no sea solo «ninguna reportada» o «sin estudios»), categorías de TPPT sin nivel que valga la pena decir, sustancias de evidencia de EFSA y las señales de riesgo de los usos de USDA (véase «Actividades sensibles»). `text` describe lo que registran las fuentes, sin dosis ni consejos, y `refs` apunta a las entradas que lo respaldan; no se marca la planta como «Precaución» ni se la presenta como segura. (c) Ninguna información de seguridad en el paquete (las señales de riesgo de los usos de USDA cuentan como información de seguridad): `safety` es `null` y el registro lleva un `reviewFlag` `sin-datos-de-seguridad` con `target` `safety`. En ningún caso presentes la planta como segura; `sin-datos-de-seguridad` solo se registra en el caso (c). Una entrada `ema_pdf` con `status` `extraccion-fallida` significa que la extracción de los PDF de la EMA falló: registra `extraccion-seguridad-fallida`.

## Imagen

`image` sale de `sections.images` y solo con licencia CC0, dominio público, CC BY o CC BY-SA. Copia `url`, `pageUrl`, `author`, `license` y `licenseUrl` del paquete, con `attributionRequired` verdadero para CC BY y CC BY-SA, y el ref de la imagen en `refs`. `author` es `null` cuando Commons no lo trae, lo que solo ocurre con imágenes de dominio público o CC0. Prefiere la primera imagen que cumpla. Si ninguna imagen tiene una licencia aceptada, `image` es `null`.

## reviewFlags

`reviewFlags` es una lista de objetos `{code, target, message}`; nunca cadenas sueltas. `code` es uno de los códigos de la tabla siguiente, que es el catálogo cerrado (`tools/catalog-seed/flag-codes.json`); no inventes códigos ni sinónimos (nada de `nombre-comun-ausente`, `sin-objetivos-de-bienestar` ni similares): el validador avisa de cualquier código fuera del catálogo. `target` indica el campo o el objetivo afectado (`scientificName`, `displayName`, `safety`, `goals`, `goals.<goal>`, `traditionalUses[<índice>]`) y `message` es una frase concreta en español. Copia todos los objetos de `identity.flags` tal como vienen (los marcados «paquete»), y registra los demás (los marcados «registro») cuando ocurra lo que describen. Los flags no bloquean la presencia de la planta en el catálogo.

| Código | Origen | Target | Significado |
| --- | --- | --- | --- |
| `identidad-ambigua` | paquete | `scientificName` | El nombre es un homónimo que el backbone no resuelve; la planta conserva la identidad de la fuente. |
| `solo-genero` | paquete | `scientificName` | La entrada solo nombra el género. |
| `sin-resolucion` | paquete | `scientificName` | El nombre no resuelve a un aceptado en ningún backbone. |
| `respaldo-wfo` | paquete | `scientificName` | El aceptado viene del respaldo de WFO, no de WCVP. |
| `coincidencia-aproximada` | paquete | `scientificName` | El nombre resolvió por coincidencia aproximada (errata probable). |
| `aceptado-superior-a-especie` | paquete | `scientificName` | El aceptado es de rango superior a especie. |
| `variante-ortografica` | paquete | `scientificName` | El nombre resolvió por una variante ortográfica del epíteto. |
| `backbones-discrepan` | paquete | `scientificName` | WCVP y WFO discrepan en el aceptado. |
| `grupo-partido` | paquete | `scientificName` | El aceptado lo comparten plantas heterotípicas; esta es una de las separadas. |
| `fusion-heterotipica` | paquete | `scientificName` | Se fusionaron sinónimos heterotípicos sin artículo propio en Wikipedia; requiere revisión humana. |
| `filas-sin-asignar` | paquete | `scientificName` | Hay filas del grupo sin asignar a ninguna planta. |
| `wikidata-sin-respuesta` | paquete | `wikidata` | Wikidata no respondió o está desactivada. |
| `wikidata-sin-item` | paquete | `wikidata` | Ningún ítem de Wikidata pasa el filtro de homónimos. |
| `wikidata-no-consultada` | paquete | `wikidata` | La planta no tiene aceptado, así que no se consultó Wikidata. |
| `extraccion-seguridad-fallida` | paquete | `safety` | La extracción de los PDF de la EMA falló (entrada `ema_pdf` con `status` `extraccion-fallida`). |
| `cita-sin-resolver` | registro | `traditionalUses[<índice>]` | Un grupo tiene una clave de cita sin candidata; un flag por grupo afectado, aunque el grupo se muestre. |
| `interacciones-graves-estres` | registro | `goals.relajacion-estres` | Interacciones graves de la EMA y área de estrés y ánimo; objetivo pendiente. |
| `sin-datos-de-seguridad` | registro | `safety` | El paquete no trae ninguna información de seguridad (`safety` es `null`); la planta no se presenta como segura. |
| `objetivos-omitidos-por-toxicidad` | registro | `goals` | TPPT marca la planta como «strong toxic» o «very strong toxic» y se omiten los objetivos que la EMA le asigna. |
| `sin-nombre-comun-es` | registro | `displayName` | El paquete no trae ningún nombre común en español; el `displayName` es el nombre científico. |
| `idioma-de-nombre-dudoso` | registro | `commonNames` | No es seguro que un nombre del paquete sea español. |
| `conflicto-entre-fuentes` | registro | campo afectado | Dos fuentes se contradicen y se usó la más autorizada. |

Una planta sin objetivos porque la EMA no tiene fichas que cuenten no lleva flag: `goals` vacío ya lo dice.

## Antes de entregar

Comprueba que:

- `id` y `bundleHash` coinciden con los del paquete y `promptVersion` con este prompt.
- Todo ref citado existe en `refs` del paquete y está en `refs` del registro.
- Todo texto visible está en español y no contiene dosis, posologías ni lenguaje de eficacia.
- Ninguna actividad de la lista de sensibles queda mal: toda enfermedad grave lleva la fórmula «Uso tradicional, sin eficacia demostrada: …» y toda señal de riesgo está en `safety` (con sus refs `usda_use:*`) y no en `traditionalUses`.
- Cada grupo con `pendingReview` y cada objetivo con `pendingReview` tienen su `reviewFlag`; cada grupo con una clave sin resolver tiene su `reviewFlag` `cita-sin-resolver`, y un grupo es pendiente solo si no tiene ninguna cita resuelta.
- El registro cumple `record.schema.json`, sin campos adicionales.
