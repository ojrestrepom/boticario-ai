# Spec Delta

## Purpose

Define cómo se construye, valida, versiona y regenera la semilla del catálogo: un registro limpio por planta consolidado desde varias fuentes abiertas con un LLM, con citas, atribución y revisión marcada, que todos los entornos usan para armar `catalog.db` sin red y sin LLM.

## ADDED Requirements

### Requirement: Fuentes con versión fija, checksum y licencia
Cada fuente que alimenta la semilla SHALL declararse con identificador, versión o snapshot, URL, licencia, atribución exigida y checksum del insumo. Las descargas SHALL ser un paso explícito, SHALL verificarse contra su checksum y SHALL cachearse en `data/.cache/`, ignorada por Git. Una fuente que cambia con el tiempo SHALL fijarse en un snapshot con su fecha. Las fuentes admitidas son USDA Dr. Duke, WCVP, WFO (solo respaldo), EMA (herbal medicines y PDF de seguridad), TPPT de Agroscope, EFSA Compendium of Botanicals, Wikidata, Wikipedia en español y Wikimedia Commons.

#### Scenario: Insumo íntegro
- **WHEN** un insumo cacheado coincide con el checksum declarado
- **THEN** el paso siguiente lo usa sin acceder a la red

#### Scenario: Insumo alterado o ausente
- **WHEN** un insumo cacheado no coincide con su checksum o no ha sido descargado
- **THEN** el paso falla indicando la fuente y el paso de descarga necesario, y no usa datos sin verificar

#### Scenario: Snapshot de una fuente cambiante
- **WHEN** se descarga el JSON de la EMA, que se actualiza dos veces al día
- **THEN** el manifiesto registra el `meta.timestamp` del snapshot y su checksum, y las ejecuciones posteriores usan ese snapshot hasta que se decida actualizarlo

#### Scenario: Retirar una fuente
- **WHEN** una fuente, por ejemplo Wikipedia, se desactiva en la configuración de las herramientas y se calcula el plan de regeneración
- **THEN** solo figuran como pendientes las plantas cuyo paquete usaba esa fuente, ningún registro regenerado contiene refs de ella, `description` queda `null` o se resume de otras fuentes del paquete, el validador no da errores y el manifiesto deja de listar la fuente

#### Scenario: Fuente fuera de la lista
- **WHEN** se intenta añadir una fuente descartada, como DrugBank o iNaturalist
- **THEN** el manifiesto y el validador de fuentes la rechazan por no estar en la lista de fuentes admitidas

### Requirement: Límites de peticiones y reanudación
Las descargas de servicios con límite de peticiones, como Wikidata, SHALL respetar la cabecera `Retry-After`, SHALL guardar cada respuesta en la caché y SHALL poder reanudarse sin repetir las consultas ya resueltas. Un límite agotado SHALL detener el paso con un mensaje que indica cuándo reintentar y SHALL NOT producir datos parciales marcados como completos.

#### Scenario: Respuesta 429
- **WHEN** el servicio responde 429 con `Retry-After`
- **THEN** el paso no reintenta antes del plazo indicado, conserva lo ya descargado y termina con el estado de reanudación

#### Scenario: Reanudación
- **WHEN** se vuelve a ejecutar la descarga tras una interrupción
- **THEN** solo se consultan las plantas sin respuesta en la caché

#### Scenario: Datos de Wikidata no disponibles
- **WHEN** una planta no tiene respuesta de Wikidata al construir su paquete
- **THEN** el paquete lo declara en su sección `wikidata` y en `flags`, y la planta puede consolidarse sin imagen ni nombre común en español de esa fuente

### Requirement: Normalización de nombres científicos
La resolución taxonómica SHALL normalizar los nombres con NFC y comparación sin mayúsculas, tratar el signo híbrido (`×`, una `x` suelta o `×` pegado) como un marcador aparte que no forma parte de la clave, y reducir los rangos a `subsp.`, `var.` y `f.` (`nothosubsp.` y `nothovar.` equivalen a los anteriores; con varios marcadores cuenta el último y los pegados se separan). SHALL resolver los autónimos como la especie, separar el autor pegado al epíteto, quitar con marca los calificadores `aggr.` y `s.str.`, tratar `sp` y `spp` como «solo género» y aceptar trinomios sin marcador. Los datos de la EMA SHALL decodificar entidades HTML, separar nombres unidos por `;` o por coma y expandir géneros abreviados.

#### Scenario: Híbrido con distintas grafías
- **WHEN** entran `Mentha × piperita`, `Mentha x piperita` y `Mentha ×piperita`
- **THEN** los tres producen la misma clave y la marca de híbrido

#### Scenario: Autónimo
- **WHEN** entra un nombre infraespecífico que repite el epíteto de la especie, como `Valeriana officinalis subsp. officinalis`
- **THEN** se resuelve como la especie

#### Scenario: Autor pegado
- **WHEN** entra `Lavandula roseaL.`
- **THEN** el epíteto es `rosea` y el autor `L.`

#### Scenario: Solo género
- **WHEN** entra `Mentha sp`
- **THEN** se trata como «solo género» y la planta se marca para revisión

### Requirement: Resolución al nombre aceptado
La resolución SHALL usar WCVP como backbone principal: primero por clave completa y, si no hay coincidencia, por binomio con marca; el desempate SHALL compararse por autor apellido por apellido, con prefijo de al menos 3 letras y la equivalencia `L.` igual a `Linnaeus`. SHALL priorizar el estado Accepted, luego Synonym, luego Illegitimate, Invalid u Orthographic con aceptado y, al final, Misapplied. Un homónimo que no se resuelva SHALL quedar como ambiguo para revisión manual y SHALL NOT fusionarse con ninguna planta. Si WCVP no resuelve, SHALL usarse WFO solo cuando dé un único aceptado; si los backbones discrepan, SHALL marcarse y conservarse el aceptado de WCVP. Una variante ortográfica de epíteto (-ii/-i, -us/-er) SHALL aceptarse solo como respaldo marcado.

#### Scenario: Sinónimo resuelto
- **WHEN** USDA registra `Matricaria recutita`, sinónimo de *Matricaria chamomilla* en WCVP
- **THEN** la planta resuelve al aceptado *Matricaria chamomilla* y sus filas de uso quedan asociadas a esa planta

#### Scenario: Homónimo ambiguo
- **WHEN** un nombre sin autor corresponde a dos taxones distintos del backbone y el desempate por autor no los separa
- **THEN** la planta queda marcada como ambigua con su identidad de USDA, y no se fusiona con ninguno

#### Scenario: Respaldo de WFO
- **WHEN** WCVP no resuelve un nombre y WFO da un único aceptado
- **THEN** la planta usa ese aceptado con una marca de respaldo, y la colisión se evalúa con el mismo criterio que el resto

#### Scenario: Variante ortográfica
- **WHEN** USDA registra `Cistus ladaniferus` y WCVP tiene `Cistus ladanifer`
- **THEN** la planta resuelve a *Cistus ladanifer* con la marca de variante ortográfica, y nunca a *Cistus creticus*

#### Scenario: Backbones discrepan
- **WHEN** WCVP y WFO dan aceptados distintos para un mismo nombre
- **THEN** se conserva el de WCVP y la planta lleva la marca de discrepancia

### Requirement: Universo de plantas
El universo de la semilla SHALL ser el de las plantas de USDA FNFTAX más las especies de la EMA que no estén en USDA. TPPT, EFSA, Wikidata, Wikipedia y Commons SHALL solo enriquecer plantas del universo y SHALL NOT añadirlas.

#### Scenario: Especie de la EMA ausente en USDA
- **WHEN** la EMA registra *Pelargonium sidoides* y USDA no la tiene
- **THEN** la semilla incluye esa planta con los datos de la EMA y de las fuentes que la enriquecen

#### Scenario: Planta que solo está en TPPT
- **WHEN** TPPT registra una planta tóxica que no está en USDA ni en la EMA
- **THEN** no se crea una planta nueva en la semilla

### Requirement: Regla de colisiones y separación de plantas
Cuando varias plantas del universo resuelvan al mismo aceptado, SHALL fusionarse siempre el propio aceptado con sus sinónimos homotípicos (`homotypic_synonym` verdadero en WCVP). Un miembro heterotípico SHALL quedar como planta propia, con un ID derivado de su propio nombre, su propio nombre científico y un `reviewFlag`, solo si su nombre científico tiene un artículo propio en Wikipedia en español (que exista, no sea una redirección y sea distinto del artículo del nombre aceptado del grupo, también tras seguir las redirecciones) o si figura en una lista versionada de excepciones «separar siempre». En otro caso SHALL fusionarse con la planta del aceptado, su nombre SHALL quedar como sinónimo y alias, y el registro SHALL llevar un `reviewFlag` de fusión heterotípica para revisión humana. La decisión de cada grupo SHALL registrarse una vez en un archivo versionado de las herramientas, con la evidencia de Wikipedia (título consultado, si existe, redirección y destino, fecha), y las corridas siguientes SHALL leer ese archivo en lugar de consultar a Wikipedia, de modo que desactivar Wikipedia o un cambio de Wikipedia no altere decisiones registradas ni IDs. Un grupo sin decisión registrada y sin datos de Wikipedia SHALL usar la regla conservadora: cada heterotípico es planta propia con `reviewFlag`. Las filas de uso y de otras fuentes de un grupo partido SHALL asignarse, en este orden, al miembro con la misma clave, al miembro homotípico con el mismo basiónimo, al miembro que es el propio aceptado y, si ninguno aplica, quedar sin asignar y marcadas para revisión. Las filas de un miembro fusionado SHALL asignarse a la planta del aceptado.

#### Scenario: Canela fusionada
- **WHEN** *Cinnamomum zeylanicum* es heterotípico del aceptado *Cinnamomum verum* y su artículo de Wikipedia en español es una redirección a *C. verum*
- **THEN** se fusiona con la planta de *Cinnamomum verum*, `Cinnamomum zeylanicum` queda como sinónimo y alias, y el registro lleva el `reviewFlag` de fusión heterotípica

#### Scenario: Bergamota separada
- **WHEN** la bergamota comparte aceptado con el limón por sinonimia heterotípica y su nombre `Citrus × bergamia` tiene artículo propio en Wikipedia en español
- **THEN** queda como planta distinta con su propio ID y nombre científico, con `reviewFlag`, y no usa el nombre del aceptado

#### Scenario: Cítricos y brasicas separados
- **WHEN** lima, naranja, pomelo, brócoli y repollo comparten aceptado con otra planta y cada nombre tiene artículo propio en Wikipedia en español
- **THEN** cada uno queda como planta distinta con su propio ID y nombre científico

#### Scenario: Hinojo dulce separado por excepción
- **WHEN** *Foeniculum vulgare* var. *dulce* no tiene artículo propio en Wikipedia en español y figura en la lista de excepciones «separar siempre»
- **THEN** queda como planta propia con su ID y `reviewFlag`, y no se fusiona con *Foeniculum vulgare*

#### Scenario: Thevetia fusionada por artículo compartido
- **WHEN** *Thevetia peruviana* tiene artículo en Wikipedia en español pero el artículo del aceptado *Cascabela thevetia* redirige a él
- **THEN** ambos nombres comparten artículo, *Thevetia peruviana* se fusiona con la planta de *Cascabela thevetia* y el registro lleva el `reviewFlag` de fusión heterotípica

#### Scenario: Wikipedia desactivada sin cambiar decisiones registradas
- **WHEN** se desactiva Wikipedia en la configuración y existe una decisión registrada para un grupo
- **THEN** la corrida usa la decisión registrada, y los IDs y la composición de las plantas del grupo no cambian

#### Scenario: Grupo nuevo sin datos de Wikipedia
- **WHEN** aparece un grupo sin decisión registrada y no hay datos de Wikipedia
- **THEN** cada miembro heterotípico queda como planta propia con `reviewFlag`, sin fusiones

#### Scenario: Fila sin asignación
- **WHEN** una fila de uso no coincide con la clave, el basiónimo ni el aceptado de ningún miembro del grupo partido
- **THEN** la fila queda sin asignar, no se atribuye a ninguna planta y se registra para revisión

#### Scenario: Respaldo de WFO y colisiones
- **WHEN** el respaldo de WFO lleva *Citrus meyerii* al aceptado del limón
- **THEN** se aplica el mismo criterio de colisiones: *Citrus meyerii* no se fusiona con el limón solo si tiene artículo propio en Wikipedia en español o figura en las excepciones (*Citrus meyeri* está en la lista inicial), y en otro caso se fusiona con `reviewFlag`

### Requirement: Identificadores públicos fijos y únicos
El ID público de cada planta SHALL ser el slug del nombre aceptado de WCVP (minúsculas, `×` como `x`, `-` como separador), generado una sola vez y guardado en la semilla. Un cambio posterior del nombre aceptado en WCVP SHALL cambiar el nombre mostrado y SHALL NOT cambiar el ID. Los IDs anteriores de la planta SHALL guardarse como alias en la semilla. Si dos plantas terminan con el mismo ID, el armado SHALL fallar, y un alias SHALL NOT coincidir con el ID de otra planta.

#### Scenario: ID por nombre aceptado
- **WHEN** USDA registra `Rosmarinus officinalis` y WCVP lo acepta como *Salvia rosmarinus*
- **THEN** el ID es `salvia-rosmarinus` y `rosmarinus-officinalis` queda como alias

#### Scenario: Renombre posterior en Kew
- **WHEN** una versión nueva de WCVP cambia el nombre aceptado de una planta que ya está en la semilla
- **THEN** el registro conserva su ID y su archivo, y solo cambia el nombre científico mostrado

#### Scenario: Colisión de IDs
- **WHEN** dos plantas de la semilla tendrían el mismo ID
- **THEN** el armado falla identificando ambas plantas y no escribe una base utilizable

#### Scenario: ID conservado
- **WHEN** se regenera la semilla
- **THEN** `lavandula-angustifolia` conserva su ID, porque el despliegue lo usa en su verificación

### Requirement: Plantas marcadas para revisión que permanecen en el catálogo
Las entradas que solo nombran el género y las que no resuelven en ningún backbone SHALL permanecer en el catálogo con la identidad de USDA y SHALL llevar un `reviewFlag`. Las plantas ambiguas, las de grupos partidos y las de resolución por respaldo SHALL llevarlo también.

#### Scenario: Entrada de solo género
- **WHEN** USDA registra `Gossypium sp`
- **THEN** la planta permanece en la semilla con su química y sus nombres comunes, con el flag de solo género y sin sinónimos inventados

#### Scenario: Sin resolución en ningún backbone
- **WHEN** un nombre de USDA no resuelve ni en WCVP ni en WFO
- **THEN** la planta conserva la identidad de USDA, el ID sale de su nombre literal y lleva el flag correspondiente

### Requirement: Paquete por planta determinista
La entrada del LLM SHALL ser un paquete por planta con `bundleVersion`, `plantKey` y `bundleHash`, un bloque `identity` (ID propuesto, universo, backbone principal, aceptados de WCVP y de WFO, conjunto de nombres con motivo y backbone, colisión, `flags` y `notes`), las secciones `taxonomy`, `distribution`, `names`, `descriptions`, `parts`, `uses`, `regulatory`, `safety`, `images` y `wikidata`, y un diccionario `refs` de ref a dataset, etiqueta y licencia. Cada fila SHALL llevar un ref `<record_type>:<row_key>`. El paquete SHALL ser determinista y su `bundleHash` SHALL ser el sha256 del JSON canónico. Los usos de ETHNOBOT SHALL agruparse por actividad con n, países y las claves cortas de REFERENCE tal como vienen. Para cada clave, el paquete SHALL incluir, con un tope de candidatas por clave, las entradas candidatas de las referencias de USDA, cada una con su ref `usda_reference:<REFERENCE>` y su cita completa: la entrada directa si la clave coincide exactamente y, si no, las de clave normalizada igual o con el mismo prefijo alfabético. La selección de candidatas no resuelve la cita.

#### Scenario: Mismo insumo, mismo hash
- **WHEN** se construye el paquete de una planta dos veces con los mismos insumos
- **THEN** el JSON canónico y el `bundleHash` son idénticos

#### Scenario: Cambio en un insumo
- **WHEN** cambia un dato que entra en el paquete de una planta
- **THEN** su `bundleHash` cambia y el de las plantas no afectadas no cambia

#### Scenario: Candidatas de una clave abreviada
- **WHEN** un grupo de uso cita la clave `Woi.10`, que no coincide exactamente con ninguna entrada
- **THEN** el paquete incluye como candidatas, hasta el tope, las entradas como `WOI` («The Wealth of India»), cada una con su ref `usda_reference:*` y su cita completa, y conserva la clave `Woi.10` tal como viene

#### Scenario: Clave con coincidencia exacta
- **WHEN** la clave coincide exactamente con una entrada de las referencias
- **THEN** el paquete incluye esa entrada como candidata directa

#### Scenario: Filtro de homónimos en fuentes abiertas
- **WHEN** Wikidata, Wikipedia o Commons devuelven un ítem cuyo nombre no resuelve al aceptado de la planta
- **THEN** el ítem no entra en el paquete, de modo que datos de *L. latifolia* no aparecen en la lavanda ni los de *P. edulis* en la pasiflora

#### Scenario: Secciones de seguridad de la EMA
- **WHEN** la EMA publica una monografía o una declaración pública de una planta
- **THEN** su paquete incluye las contraindicaciones, advertencias e interacciones extraídas del PDF, cada una con su ref, o declara que la extracción falló

### Requirement: Registro consolidado v1 con citas
Cada planta SHALL tener un registro con identificación (`id`, `recordVersion`, `bundleHash`, versión de prompt y modelo), taxonomía (`scientificName` con nombre, autores y refs; `synonyms` hasta 10; `family`), nombres (`displayName`, `commonNames` por idioma), descripción (`origin`, `description` de hasta 400 caracteres neutra, `partsUsed` hasta 5, `oil`), usos y objetivos (`traditionalUses` hasta 20 grupos con `activity` traducida, `activitySource` original, `n`, `countries`, `refs` y `pendingReview`; `goals` con `goal`, `subarea` (nulo salvo en `otros-objetivos`), `area`, `evidence`, `pendingReview` y refs), `safety` (nivel alto, medio o bajo, texto y refs), `image` (URL, página, autor, licencia, URL de licencia, atribución requerida y refs), `sources`, el subconjunto del diccionario `refs` que usa y `reviewFlags`, cada uno con la forma `{code, target, message}`. Todo texto visible SHALL estar en español, en particular `goals[].area` (traducción del área desde el mapa), `goals[].evidence` y los países de `traditionalUses[].countries`, que se traducen sin conservar el original.

#### Scenario: Registro completo
- **WHEN** se valida el registro de una planta con todas las fuentes
- **THEN** cumple el esquema, cada campo con contenido factual lleva refs y el texto visible está en español

#### Scenario: Textos de objetivos y países en español
- **WHEN** el registro tiene un objetivo del área «Cough and cold» y un grupo de uso con países
- **THEN** `area` y `evidence` están en español y los países están traducidos al español, sin el valor original

#### Scenario: Campo sin respaldo
- **WHEN** una fuente no aporta datos para un campo
- **THEN** el campo queda `null` o vacío y no se completa con conocimiento del modelo

#### Scenario: Nombre de idioma desconocido
- **WHEN** USDA registra un nombre con idioma `und` que es claramente español
- **THEN** puede usarse como nombre común en español, siempre con ref

#### Scenario: Aceite esencial
- **WHEN** el compuesto `EO` de USDA aparece en las partes de la planta
- **THEN** `oil` es `{type: "Esencial"}`, y un aceite fijo, como el de ricino, no lo activa

### Requirement: Resolución de citas abreviadas por el LLM
El LLM SHALL emparejar cada clave corta de REFERENCE de un grupo de uso con su cita completa eligiendo entre las candidatas del paquete, y SHALL citar el ref `usda_reference:*` de la candidata elegida; por ejemplo `Woi.10` con «The Wealth of India, vol. 10» y `Eb24: 441` con «Economic Botany 24: 441». Si ninguna candidata corresponde, la cita SHALL conservar su clave con la marca «(sin resolver)», el grupo SHALL llevar `pendingReview: true` y el registro SHALL llevar un `reviewFlag` `{code: "cita-sin-resolver", target: "traditionalUses[<índice>]", message}` por cada grupo afectado. El LLM SHALL NOT construir una cita que no esté en las candidatas.

#### Scenario: Clave emparejada
- **WHEN** un grupo cita `Woi.10` y el paquete trae la candidata `WOI` con «The Wealth of India»
- **THEN** el grupo cita el ref de esa candidata y su cita completa es la de la candidata, con el volumen tomado de la clave

#### Scenario: Diferencia de formato
- **WHEN** un grupo cita `Burkill,1966` y el paquete trae la candidata `Burkill, 1966`
- **THEN** el grupo cita el ref de esa candidata

#### Scenario: Sin candidata correspondiente
- **WHEN** ninguna candidata corresponde a la clave, por ejemplo una obra poco clara como `Woi.Syria`
- **THEN** la cita conserva la clave con la marca «(sin resolver)», el grupo tiene `pendingReview` verdadero y el registro tiene un `reviewFlag` `cita-sin-resolver` con `target` en ese grupo

### Requirement: Política de consolidación sin conocimiento propio
El LLM SHALL elegir, traducir y resumir únicamente lo que está en el paquete y SHALL citar la fuente de cada campo con refs del paquete. SHALL NOT incorporar conocimiento propio ni inventar nombres comunes. SHALL NOT escribir dosis, posologías, indicaciones de tratamiento ni promesas de eficacia. Una planta separada por colisión SHALL usar su propio nombre científico.

#### Scenario: Planta tóxica sin nombre inofensivo inventado
- **WHEN** una planta tóxica no tiene nombre común en español en el paquete
- **THEN** `displayName` usa un nombre del paquete o el científico, nunca un nombre que el modelo aporte por su cuenta

#### Scenario: Texto sin dosis ni eficacia
- **WHEN** el registro generado contiene una dosis, una posología o una promesa de eficacia
- **THEN** el validador lo advierte y el registro no se acepta sin revisión

#### Scenario: Planta separada por colisión
- **WHEN** el registro corresponde a la bergamota separada del limón por tener artículo propio en Wikipedia en español
- **THEN** su `scientificName` es el de su propio nombre (por ejemplo *Citrus × bergamia*) y no el del aceptado

### Requirement: Objetivos derivados solo de la EMA
Los `goals` SHALL salir únicamente de las áreas terapéuticas de la EMA y solo cuando el resultado sea una monografía o una entrada de lista; el resultado combinado (`European Union herbal monograph;European Union list entry`) SHALL separarse por `;`. Una declaración pública SHALL NOT asignar objetivos ni los productos combinados de la EMA. Las áreas SHALL mapearse así: «Mental stress and mood disorders» a `relajacion-estres`, «Sleep disorders and temporary insomnia» a `mejorar-el-sueno`, «Skin disorders and minor wounds» a `cuidado-de-la-piel`, «Cough and cold» a `alivio-respiratorio`, «Fatigue and weakness» a `cansancio-y-fatiga` y todas las demás a `otros-objetivos` con su subárea. Una planta que TPPT marque como «strong toxic» o «very strong toxic» SHALL NOT recibir objetivos. Una planta con interacciones graves en el área de estrés y ánimo SHALL llevar ese objetivo con `pendingReview: true` y un `reviewFlag` que lo señale. Los objetivos SHALL referirse a ids del catálogo de objetivos de la semilla y las subáreas solo a las de `otros-objetivos`.

#### Scenario: Resultado combinado
- **WHEN** la EMA registra `European Union herbal monograph;European Union list entry` para la menta con área de digestión
- **THEN** el resultado se separa, la planta cuenta como monografía y recibe el objetivo `otros-objetivos` con la subárea de digestión

#### Scenario: Declaración pública
- **WHEN** el único resultado de la EMA para una planta es una declaración pública
- **THEN** la planta no recibe objetivos

#### Scenario: Planta tóxica
- **WHEN** TPPT marca una planta como «very strong toxic» y la EMA le asigna un área
- **THEN** la planta no recibe objetivos y se marca para revisión

#### Scenario: Hipérico
- **WHEN** una planta con interacciones graves en la EMA tiene el área «Mental stress and mood disorders»
- **THEN** el objetivo `relajacion-estres` se registra con `pendingReview` verdadero y un `reviewFlag` con `target` en ese objetivo, y los consumidores lo omiten hasta que se revise

### Requirement: Niveles de seguridad
El nivel `safety.level` SHALL derivarse de las fuentes con categorías definidas y versionadas en el repo (`safety-map.json`). TPPT: «strong toxic» y «very strong toxic» a alto; «toxic», «toxic (unknown strength)», «liver toxic», «cytotoxic», «estrogenic», «carcinogenic» y «phototoxic» a medio; «weak toxic», «skin-irritating» y «allergenic» a bajo; «nontoxic», «unknown», «infested plants only» y «stimulating» sin nivel; la toxicidad en animales no fija nivel. EMA: las interacciones graves a alto y las declaraciones públicas con datos de seguridad a medio. EFSA: una planta SHALL fijar medio solo si tiene al menos una fila, distinta de «Non Detected Value (<LOD)», cuya sustancia figura en una lista versionada de sustancias de alta preocupación (genotóxicas o carcinógenas; tuyona, pulegona, mentofurano y cumarina; furocumarinas fototóxicas; y venenos potentes), con los nombres exactos de las sustancias del compendio; las demás sustancias SHALL ser evidencia para el texto de seguridad y SHALL NOT fijar nivel. El nivel final SHALL ser el más alto entre las fuentes. Una planta sin datos de seguridad SHALL llevar `safety` nulo y un `reviewFlag`, y SHALL NOT presentarse como segura.

#### Scenario: Planta tóxica
- **WHEN** TPPT clasifica una planta como «strong toxic» para humanos
- **THEN** su `safety.level` es `alto` con ref al registro de TPPT

#### Scenario: Fototóxica
- **WHEN** TPPT clasifica una planta como «phototoxic» y no hay datos de mayor gravedad
- **THEN** su nivel es `medio`

#### Scenario: Sustancia de la lista de EFSA
- **WHEN** el compendio de EFSA registra estragol o tuyona para una planta
- **THEN** su nivel es al menos `medio`, y el paquete indica qué sustancias de la lista lo activaron

#### Scenario: Solo evidencia de EFSA
- **WHEN** el compendio de EFSA registra para una planta solo 1,8-cineol o alcanfor
- **THEN** EFSA no fija nivel y las sustancias quedan como evidencia para el texto

#### Scenario: Declaración pública con datos de seguridad
- **WHEN** la EMA publica para una planta (por ejemplo la kava) una declaración pública cuyas conclusiones mencionan seguridad
- **THEN** su nivel es al menos `medio`

#### Scenario: Categorías aprobadas de TPPT
- **WHEN** TPPT clasifica una planta como «toxic» o «weak toxic» para humanos y no hay datos de mayor gravedad
- **THEN** su nivel es `medio` o `bajo` respectivamente, y «nontoxic» no fija nivel ni hace segura a la planta

#### Scenario: Sin datos
- **WHEN** ninguna fuente de seguridad menciona la planta
- **THEN** `safety` es nulo con un `reviewFlag` de ausencia de datos, y el registro no afirma que sea segura

### Requirement: Imágenes con licencia aceptada
La imagen de un registro SHALL provenir de Wikimedia Commons a través de Wikidata, SHALL tener licencia CC0, dominio público, CC BY o CC BY-SA, y SHALL guardar autor, URL de la página, licencia, URL de la licencia y si la atribución es obligatoria. Una imagen con otra licencia SHALL descartarse.

#### Scenario: Licencia aceptada
- **WHEN** la imagen de Commons tiene licencia CC BY-SA
- **THEN** el registro la incluye con autor, licencia y `attributionRequired` verdadero

#### Scenario: Licencia no aceptada
- **WHEN** la imagen tiene una licencia fuera de la lista
- **THEN** `image` queda nulo y el validador no admite una imagen con esa licencia

### Requirement: Validador automático
El validador SHALL comprobar el esquema, que todo ref existe en el paquete de la planta, que todo objetivo tiene respaldo en la EMA, que una planta tóxica no tiene objetivos, que la imagen tiene licencia aceptada, que todo objetivo con `pendingReview` tiene un `reviewFlag` asociado, que todo grupo con `pendingReview` tiene un `reviewFlag` y todo grupo con una cita sin resolver tiene `pendingReview`, que toda cita de `traditionalUses` apunta a un ref `usda_reference:*` del paquete o está marcada «(sin resolver)», que `activitySource` es una actividad literal del paquete y que ningún texto contiene palabras de dosis o eficacia, esto último como advertencia. Un error SHALL impedir que el registro entre en la semilla.

#### Scenario: Ref inexistente
- **WHEN** un registro cita un ref que no está en el diccionario del paquete
- **THEN** el validador devuelve un error que nombra la planta y el ref, y el registro no se acepta

#### Scenario: Objetivo sin respaldo
- **WHEN** un registro tiene un objetivo que la EMA no respalda para esa planta
- **THEN** el validador devuelve un error

#### Scenario: Objetivo pendiente sin flag
- **WHEN** un objetivo tiene `pendingReview` verdadero y el registro no tiene un `reviewFlag` cuyo `target` lo señale
- **THEN** el validador devuelve un error

#### Scenario: Palabra de dosis
- **WHEN** el texto contiene una expresión de dosis o eficacia
- **THEN** el validador emite una advertencia con el campo y la expresión

#### Scenario: Grupo pendiente sin flag
- **WHEN** un grupo de uso tiene `pendingReview` verdadero y el registro no tiene un `reviewFlag` cuyo `target` lo señale
- **THEN** el validador devuelve un error

#### Scenario: Cita sin resolver sin grupo pendiente
- **WHEN** un grupo de uso tiene una cita «(sin resolver)» y `pendingReview` falso
- **THEN** el validador devuelve un error

#### Scenario: Cita inventada
- **WHEN** un grupo de uso cita un ref que no es una candidata del paquete ni está marcado «(sin resolver)»
- **THEN** el validador devuelve un error

#### Scenario: Actividad alterada
- **WHEN** `activitySource` no coincide con ninguna actividad del paquete
- **THEN** el validador devuelve un error

### Requirement: Semilla versionada con manifiesto
La semilla SHALL guardarse en el repositorio como un archivo JSON por planta (`data/seed/plants/<id>.json`) y un manifiesto (`data/seed/manifest.json`) con las versiones y checksums de las fuentes, la versión de prompt, el esquema y el modelo, el número de plantas y un hash del contenido de los registros y del catálogo de objetivos. El catálogo de objetivos (`data/seed/goals.json`) SHALL declarar, para cada objetivo, su id, su etiqueta en español y su posición, y para cada subárea su id, objetivo, etiqueta y posición. El nombre de cada archivo SHALL coincidir con el `id` de su registro. El prompt, el esquema, el mapa de objetivos y el validador SHALL versionarse en el repositorio.

#### Scenario: Catálogo de objetivos
- **WHEN** se lee `data/seed/goals.json`
- **THEN** contiene los objetivos `relajacion-estres`, `mejorar-el-sueno`, `cuidado-de-la-piel`, `alivio-respiratorio`, `cansancio-y-fatiga` y `otros-objetivos` en ese orden, y las subáreas `digestion`, `vias-urinarias-y-genitales`, `dolor-e-inflamacion`, `boca-y-garganta`, `circulacion` y `molestias-oculares` bajo `otros-objetivos`

#### Scenario: Archivo y ID coinciden
- **WHEN** un registro `salvia-rosmarinus.json` contiene otro `id`
- **THEN** la verificación de la semilla falla identificando el archivo

#### Scenario: Manifiesto al día
- **WHEN** se modifica un registro sin actualizar el hash del manifiesto
- **THEN** la verificación de la semilla falla indicando que el manifiesto no coincide

#### Scenario: Diff revisable
- **WHEN** se regenera un registro
- **THEN** el cambio aparece como un diff de un solo archivo JSON con claves ordenadas

### Requirement: Regeneración incremental
La regeneración SHALL volver a consolidar solo las plantas cuyo `bundleHash` o versión de prompt o de esquema difiera de los del registro, o que no tengan registro. Una planta ya presente SHALL conservar su ID. Las plantas nuevas SHALL generarse sin alterar los registros que no cambiaron.

#### Scenario: Sin cambios
- **WHEN** se calcula el plan de regeneración con los mismos insumos, prompt y esquema
- **THEN** la lista de plantas a regenerar está vacía

#### Scenario: Cambia el prompt
- **WHEN** se sube la versión de prompt
- **THEN** todas las plantas figuran como pendientes de regenerar

#### Scenario: Cambia una fuente
- **WHEN** una fuente cambia datos de una sola planta
- **THEN** solo esa planta figura como pendiente

### Requirement: `reviewFlags` registrados
Cada registro SHALL llevar la lista `reviewFlags`, de objetos `{code, target, message}` donde `target` indica el campo o el objetivo afectado, con los motivos por los que requiere revisión humana: identidad ambigua, solo género, sin resolución, respaldo de WFO o de variante ortográfica, backbones en discrepancia, grupo partido, filas sin asignar, extracción de seguridad fallida, conflicto entre fuentes, interacciones graves en estrés y ánimo, citas de uso sin resolver y ausencia de datos de seguridad. Los `reviewFlags` SHALL registrarse en la semilla y SHALL NOT bloquear la presencia de la planta en el catálogo.

#### Scenario: Flag estructurado
- **WHEN** se valida un `reviewFlag` que es una cadena suelta o no tiene `code`, `target` y `message`
- **THEN** el validador devuelve un error

#### Scenario: Planta con flag en el catálogo
- **WHEN** una planta tiene `reviewFlags`
- **THEN** sigue en la semilla y en `catalog.db`, con los flags guardados

#### Scenario: Conteo de flags
- **WHEN** se arma la semilla completa
- **THEN** el informe de la generación lista cuántas plantas tienen cada flag

### Requirement: Licencias y atribución en la semilla
La semilla SHALL guardar para cada dato el dataset de origen y su licencia, y la atribución exigida por esa licencia. Se exige atribución para WCVP, EFSA, Wikipedia, Commons, TPPT y la EMA. Los textos resumidos a partir de Wikipedia SHALL registrarse con licencia CC BY-SA 4.0 como obra derivada. El uso de TPPT SHALL documentarse como académico con atribución, con la condición de pedir permiso a Agroscope si el enfoque pasa a ser comercial. Los términos de reutilización de la EMA y de TPPT SHALL documentarse como no verificados contra el texto legal hasta que se verifiquen.

#### Scenario: Atribución por dato
- **WHEN** se consulta un campo del registro derivado de WCVP y otro de Wikipedia
- **THEN** cada uno indica su dataset, licencia y atribución en el registro

#### Scenario: Descripción de Wikipedia
- **WHEN** la descripción de un registro resume el artículo de Wikipedia
- **THEN** el campo registra CC BY-SA 4.0 y el enlace al artículo

#### Scenario: Dato sin licencia
- **WHEN** un dato del registro no tiene dataset o licencia
- **THEN** la verificación de la semilla falla
