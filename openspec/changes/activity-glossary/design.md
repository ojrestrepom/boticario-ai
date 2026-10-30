# Design

## Context

Estado actual, observado en el repositorio y en `data/build/catalog.db` el 2026-10-29:

- La tabla `plant_use_group` tiene 17.160 grupos visibles (`pending_review` falso) y 1.308 actividades distintas, en 1.456 plantas con usos visibles de las 2.354. Los 102 textos «Uso tradicional, sin eficacia demostrada: …» suman 1.299 grupos. Las 100 actividades más frecuentes cubren el 65,7 % de los grupos, las 200 el 80,4 % y las 300 el 87,3 %.
- La actividad que ve el usuario es `plant_use_group.activity`, traducida por el LLM de la consolidación (prompt v7). La traducción no es una función de la etiqueta original: 137 de las etiquetas de USDA tienen más de una traducción (por ejemplo `Aperient` sale como `Aperient`, `Aperiente`, `Laxante suave` y `Aperitivo`).
- La semilla (`data/seed/`) tiene un JSON por planta, `goals.json` y `manifest.json`; el `seedHash` cubre los registros y el catálogo de objetivos, y lo recalculan `tools/catalog-seed` (Python) y `catalog-ingest` (Rust, `seed.rs`). El `Manifest` de Rust usa `deny_unknown_fields`. La imagen de Docker construye `catalog.db` desde `data/seed/` sin red, y `deploy-backend.yml` se dispara con cambios en `backend/**`, `data/migrations/**` y `data/seed/**`.
- Las fuentes en línea (`wikidata`, `wikipedia_es`, `commons`) se declaran en `sources.json` sin archivo ni checksum, se descargan con `wiki.py` (caché por respuesta, `User-Agent` genérico `BoticarioAI-catalog-seed/0.1 (academic project)`, `Retry-After`, `_resume.json`) y se admiten en `ADMITTED_SOURCES` y `SERVICE_SOURCES`. El manifiesto lista toda fuente activa, también las de servicio.
- `credits` lo calcula `load_credits` en `catalog-api/src/repository.rs` a partir de las tablas de atribución y de los datasets de las referencias de lo que se sirve; los grupos pendientes no acreditan.
- El validador de registros tiene `DOSE_PATTERNS` (dosis, posología, unidades, gotas, cucharadas, «cura», «trata», «previen-», «elimina», «alivia», «eficaz», «efectiv-»), que emite advertencias, y `sensitive-activities.json` (enfermedades graves y señales de riesgo, con `Emmenagogue` en `excludedDoubtful`).
- La app tiene tres capas: `UseGroup` en `plant_consolidated.dart`, el parser tolerante en `catalog_json_parser.dart` y `passport_uses_tab.dart`. El cambio paralelo `compact-passport-uses` reescribe el grupo (título, línea «N registros · países», «Ver N citas») y su tarea 2.1 reescribe `_UseGroupCard`; sus artefactos existen al escribir este diseño y no se tocan.

Véase `proposal.md` para el motivo y la decisión del usuario del 2026-10-29: explicación breve bajo los términos técnicos, definiciones de una fuente abierta citada (Wikcionario en español), proceso de la semilla, atribución en `Fuentes` y alcance inicial de unos 80 términos.

### Investigación previa

Se hizo el 2026-10-29 con 10 peticiones seriales a `es.wiktionary.org` (con pausa, sin ningún 429) y 3 a páginas de licencia y de política. Los datos descargados quedaron fuera del repositorio.

**Licencia.** El texto de Wikcionario en español es CC BY-SA 4.0, y los Términos de Uso de Wikimedia lo confirman para todo texto de los proyectos junto con la GFDL sin versión, de las que quien reutiliza puede cumplir una, otra o ambas.

- La API del sitio informa `rightsinfo`: «Creative Commons Attribution-Share Alike 4.0», `https://creativecommons.org/licenses/by-sa/4.0/deed.es` (`https://es.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=rightsinfo`).
- Términos de Uso, sección 7, «Licensing of Content»: <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>. La atribución se cumple con un enlace al artículo (cuyo historial lista a los autores), con un enlace a una copia estable que dé crédito equivalente o con una lista de autores. Los datos como hechos pueden reutilizarse sin atribución (renuncia a los derechos sui generis de base de datos), pero la expresión de la definición no.
- Texto legal, sección 3 de <https://creativecommons.org/licenses/by-sa/4.0/legalcode.en>: quien comparte, incluso con cambios, debe conservar la identificación de los autores y un enlace al material «en la medida de lo razonablemente practicable» (3(a)(1)(A)), indicar si lo modificó (3(a)(1)(B)) e indicar la licencia con su texto o enlace (3(a)(1)(C)); puede cumplirlo de cualquier forma razonable según el medio, por ejemplo con un enlace a un recurso que lo incluya (3(a)(2)). Si comparte material adaptado, debe licenciarlo con CC BY-SA o una licencia compatible, sin términos adicionales ni medidas tecnológicas que restrinjan (3(b)).
- Consecuencias: cada fila del glosario guarda la URL permanente de la revisión (`index.php?title=…&oldid=…`), cuyo historial lista a los autores; el glosario se licencia como CC BY-SA 4.0; el recorte a la primera oración y el retiro del marcado son cambios que la atribución declara; `Fuentes` muestra el crédito con la licencia enlazada. No es asesoría legal. Una definición de una oración puede no alcanzar el umbral de originalidad, pero se trata como obra protegida, igual que el resumen de Wikipedia en `consolidate-catalog-seed` (D12).
- Política de `User-Agent` de Wikimedia (<https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy>): pide un `User-Agent` informativo con datos de contacto y advierte que los scripts pueden bloquearse sin aviso. El proyecto usa uno genérico sin correo por decisión previa; con él las 10 peticiones de la investigación y las de `wiki-fetch` funcionaron (hubo 429 en Wikipedia, que `Retry-After` resolvió). Es un riesgo menor que se anota en la pregunta Q4.

**Acceso.** Probado:

- `GET /w/api.php?action=query&prop=revisions&rvprop=content|ids|timestamp&rvslots=main&titles=a|b|…`: devuelve el wikitext y la revisión de hasta 50 entradas por petición. El wikitext trae plantillas que cambian el texto visible (`{{plm|…}}` pone la primera letra en mayúscula, `{{adjetivo de verbo|estimular|estimula}}` da «Que estimula.», `{{impropia|…}}`, `{{forma adjetivo|…}}`), así que limpiarlo a mano es frágil.
- `GET /w/api.php?action=parse&page=<título>&prop=text|revid&redirects=1&formatversion=2`: devuelve el HTML ya renderizado y el `revid`. Cada acepción es un par `<dt>` (número y marca semántica, como «Medicina») y `<dd>` (texto, seguido de listas de sinónimos, antónimos y uso). Mezcla las secciones de todos los idiomas de la página (`estomacal` tiene aragonés, asturiano, catalán, gallego, occitano y portugués), que se separan por el encabezado «Español».
- `GET /api/rest_v1/page/html/<título>`: HTML de Parsoid con el `revid` en el `ETag`; equivalente al anterior.
- `GET /api/rest_v1/page/definition/<título>`: no existe para `es` (responde 501).
- Los títulos distinguen mayúsculas: la entrada es `diurético`, no `Diurético`.

**Cobertura.** De 85 términos candidatos (actividades de acción de la base, ordenadas por frecuencia hasta 7 grupos), Wikcionario tiene entrada con sección en español para 57 y no la tiene para 28. De los 57, 25 tienen una acepción marcada «Medicina» o «Farmacología», y las otras 32 tienen la acepción útil sin marca o con otra (Química, Dermatología). La marca no basta para elegir: `aperitivo` marca «Medicina» la acepción 2 (desobstruir un conducto) y deja sin marca la 1 (estimular el apetito), que es la que usa Dr. Duke; `anodino` tiene tres acepciones figuradas antes de la farmacológica; `tónico` marca la 3.

| Término | Grupos | Entrada | Acepción adecuada | Extracto (acepción elegida) |
| --- | --- | --- | --- | --- |
| Diurético | 479 | sí | sí (1, Medicina) | «Que aumenta o facilita la producción y excreción de orina.» |
| Tónico | 348 | sí | sí (3, Medicina; la 1 y la 2 son otras) | «Que provoca o favorece el tono de un músculo, de un órgano, o del metabolismo en general.» |
| Astringente | 316 | sí | sí (1, sin marca) | «Se dice de la sustancia que se utiliza con fines médicos o industriales para astringir o contraer tejidos orgánicos y reducir el moco, el flujo de sangre y otras secreciones.» |
| Estimulante | 234 | sí | no, circular | «Que estimula.» |
| Carminativo | 224 | sí | sí (1, Medicina) | «Se dice de las sustancias que propician la expulsión de los gases intestinales.» |
| Anodino | 218 | sí | sí, solo la 4 (poco usada) | «Dicho de un medicamento: Que mitiga el dolor.» |
| Expectorante | 200 | sí | sí, débil (1, Medicina) | «Que hace expectorar.» |
| Estomacal | 196 | sí | sí (2, sin marca) | «Que fortalece al estómago, y favorece la digestión.» |
| Vermífugo | 182 | no (solo la forma femenina `vermífuga`) | no | sin entrada |
| Emenagogo | 178 | sí | sí (2, sin marca; la 1 está marcada como impropia), sensible | «Sustancia que estimula el flujo de la sangre en el área de la pelvis y el útero, favoreciendo la menstruación.» |
| Laxante | 170 | sí | sí (1, sin marca) | «Se dice del alimento o medicamento que provoca o facilita la defecación.» |
| Sedante | 159 | sí | no, solo un sinónimo | «Calmante, hablando de remedios.» |
| Antiséptico | 156 | sí | sí (2, Medicina), con «prevenir» | «Capaz de prevenir las infecciones microbianas.» |
| Depurativo | 146 | sí | no, circular | «Que sirve para depurar.» |
| Purgante | 136 | sí | no, circular | «Que purga.» |
| Emético | 133 | sí | sí (1, Medicina) | «Que provoca el vómito.» |
| Sudorífico | 130 | sí | sí (1, Medicina) | «Se dice del medicamento o de la sustancia que hace sudar.» |
| Alterativo | 114 | sí | no, vaga | «Que tiene virtud de alterar positivamente.» |
| Demulcente | 87 | sí | sí (1, Medicina; la 2 menciona tumores) | «Se dice del medicamento o sustancia, generalmente viscosa, que ejerce una acción protectora local.» |
| Aperitivo | 82 | sí | sí (1, sin marca) | «Que sirve para estimular el apetito.» |
| Hemostático | 84 | no (solo `hemostática`) | no | sin entrada |
| Emoliente | 65 | sí | no con filtro: menciona «tumores» | «Se dice del medicamento o sustancia que se usa para ablandar durezas, tumores o similares.» |
| Analgésico | 57 | sí | sí (1, Medicina) | «Que reduce o suprime el dolor.» |
| Catártico | 53 | no (solo `catártica`) | no | sin entrada |
| Vulnerario | 43 | sí | sí (1, Medicina), con «curar» | «Se dice de la planta o sustancia que tiene propiedades beneficiosas para curar heridas o llagas.» |
| Bactericida | 101 | sí | sí (1, Medicina), con «elimina» | «Que elimina las bacterias o los microbios.» |
| Febrífugo | 32 | sí | sí (1, Medicina y Farmacología) | «Que sirve para combatir la fiebre.» |

- Ausentes (28, 867 grupos, 5,05 %): Vermífugo, Hemostático, Piscicida, Refrigerante, Catártico, Colagogo, Antitusivo, Antiflogístico, Alexitérico, Galactagogo, Pediculicida, Estíptico, Desobstruyente, Masticatorio, Fumigante, Resolutivo, Sialagogo, Uterotónico, Hidragogo, Calmante, Supurativo, Antifertilidad, Lactagogo, Discutiente, Larvicida, Detersivo (sin sección en español), Estornutatorio e Intoxicante. Tres (Vermífugo, Hemostático y Catártico) existen solo como la forma femenina (`vermífuga`, `hemostática`, `catártica`), que remite al lema ausente.
- Con entrada (57): 5.156 grupos (30,05 %); por la forma base de la actividad, 5.240 (30,5 %). Con las 40 acepciones que hoy se leen como adecuadas (revisadas a mano; la lista final la aprueba el usuario): 3.864 grupos (22,5 %) y 1.141 plantas de las 1.456 con usos visibles.
- Con los patrones del validador de registros, 7 de las cerca de 100 acepciones revisadas dan advertencia, todas en una acepción descriptiva: `previene` (antidiarreico), `prevenir` (antiespasmódico y antiséptico), `elimina` (bactericida y fungicida), `eliminar` (parasiticida) y `curar` (vulnerario). Dos acepciones nombran una enfermedad grave de la lista sensible («tumores» en la 2 de demulcente y en emoliente).
- Calidad: las definiciones de diccionario describen el término, no la planta, y varias son circulares («Que purga.», «Que estimula.»), remiten a un sinónimo (sedante) o son vagas (alterativo). Las 40 adecuadas son las que explican algo que el usuario no sabía.

## Goals / Non-Goals

**Goals:**

- Que el usuario entienda los términos técnicos de `Usos` sin salir de la app, con una explicación citada de una fuente abierta, nunca escrita por el modelo.
- Que la explicación no se lea como una promesa sobre la planta.
- Que el proceso sea el de la semilla: lista versionada, descarga con caché y revisión fija, validación, sellado, atribución y construcción determinista sin red.
- Cambios aditivos en la API y compatibles hacia atrás con la app instalada.

**Non-Goals:**

- Regenerar o modificar los registros de las plantas, cambiar el prompt o la traducción de las actividades (la inconsistencia de `Aperient` queda como limitación).
- Explicar enfermedades, síntomas o términos arcaicos que no son de acción (Hidropesía, Escrófula, Caquexia, Biliosidad), ni las actividades con la fórmula de enfermedad grave. Podrían ser un cambio posterior.
- Buscar otra fuente para los 28 términos ausentes, o que el proyecto contribuya a Wikcionario.
- Traducir, resumir o parafrasear las definiciones, o mostrarlas fuera de `Usos`.
- Cambiar el diseño del grupo (lo hace `compact-passport-uses`).

## Decisions

### D1. Fuente, licencia y atribución

Wikcionario en español, CC BY-SA 4.0 (decisión del usuario, confirmada por la investigación). Se declara como `wiktionary_es` en `sources.json` (servicio en línea, `licenseUrl` de CC BY-SA 4.0, `pageUrl` `https://es.wiktionary.org`) y se añade a `ADMITTED_SOURCES` y `SERVICE_SOURCES`; el manifiesto y `catalog.db` la listan como a las demás. Su `attribution` dice que las definiciones son de Wikcionario, que se les retiró el marcado y las notas y se recortaron a la primera oración, y que el historial de cada entrada lista a sus autores. El glosario (`glossary.json`) es una obra derivada: lleva su licencia CC BY-SA 4.0 y la URL permanente de la revisión de cada entrada. En `Fuentes` la atribución sale por `credits`, como la de Wikipedia.

Alternativas:

- Cumplir con la GFDL en vez de CC BY-SA. Se descarta: añade obligaciones (texto completo de la licencia) sin ventaja, y el repositorio ya usa CC BY-SA para Wikipedia.
- Enlazar solo al sitio y no a cada entrada. Cumple peor la atribución («un enlace al material, en lo razonablemente practicable»); se guarda la URL por fila y la app decide si la enlaza (pregunta Q5).
- Evitar la licencia redactando definiciones propias. No es posible: el usuario prohibió definiciones con conocimiento del modelo.

### D2. Qué términos entran

La lista inicial la propone el desarrollador y la aprueba el usuario, y vive versionada en `tools/catalog-seed/glossary-terms.json`. Se arma así: se toman las actividades de `plant_use_group` (visibles, sin la fórmula de enfermedad grave) ordenadas por frecuencia; se conserva un término si es de acción (un tipo de remedio o de efecto atribuido a una sustancia: diurético, tónico, astringente) y no una enfermedad, síntoma, parte del cuerpo, forma de uso (té, licor, jabón, cataplasma) o actividad sensible; y se corta cuando la frecuencia baja de 7 grupos. Salen 85 candidatos que suman 6.031 grupos (35,15 %). Cada término declara su texto de actividad, el título de Wikcionario y la acepción; los excluidos quedan en una sección con su motivo.

Cómo crece: el desarrollador agrega términos a la lista y vuelve a ejecutar `glossary-fetch` (solo descarga los nuevos), `glossary-build`, `validate` y `seal`; el plan de regeneración sigue en cero. Un comando `glossary-candidates` imprime las actividades más frecuentes que aún no están en la lista ni en excluidos, para revisarlas. Una segunda tanda natural son las enfermedades arcaicas, que exigen otra regla de selección y quedan fuera de este cambio.

Alternativas:

- Todas las actividades con entrada en Wikcionario. 1.308 consultas, y la mayoría (enfermedades, partes del cuerpo) no necesita explicación o la tiene de otro tipo (un sustantivo con muchas acepciones).
- Un umbral automático de frecuencia sin criterio humano: incluiría enfermedades y formas de uso, y la selección de lo que es un término de acción es un juicio.
- Una lista fija en el código de la app: no sale de la semilla, no se valida y no se cita.

### D3. Cómo se descarga

Un paso explícito `glossary-fetch` (con `--plan` y `--wait` como `wiki-fetch`) que reutiliza la mecánica de `wiki.py`: una petición `action=parse` por término (`prop=text|revid`, `redirects=1`), en serie, con pausa de 1 segundo, el `User-Agent` del proyecto, respeto de `Retry-After`, `_resume.json` y caché en `data/.cache/wiktionary_es/<título>.json` con la respuesta, el `revid` y la fecha. La entrada inexistente se guarda como ausencia con su fecha. Para 85 términos son 85 peticiones, unos 2 minutos. «Versión fija»: la caché conserva la revisión; cada fila del glosario guarda el `revid` y la URL con `oldid`, y actualizar una entrada es un paso explícito (`--refresh <título>`) cuyo cambio queda visible en el diff de `glossary.json`.

Alternativas:

- `prop=revisions` por lotes de 50 (2 peticiones). Menos tráfico, pero obliga a renderizar plantillas en el cliente. Se conserva como plan B si hubiera límites.
- El endpoint REST de Parsoid: equivalente, con la revisión en un encabezado; se prefiere la API de acción, que lleva el `revid` en el cuerpo.
- Un volcado de Wikcionario: cientos de MB para 85 entradas.
- Fijar el checksum de cada respuesta en `sources.json`: las respuestas llevan marcas dinámicas; el `revid` y la URL con `oldid` son la fijación útil.

### D4. Selección de la acepción

El LLM propone el número de acepción de cada término y una persona lo revisa. El agente recibe las acepciones reales de la entrada (numeradas, con su marca) y responde solo `{term, sense | null, reason}`; nunca escribe texto. Reglas: elegir la acepción que describe una acción o propiedad atribuida a un remedio o sustancia; descartar las figuradas, anatómicas, gramaticales o de otro dominio (música, lingüística, gastronomía); preferir la acepción más general sobre la técnica cuando ambas son farmacológicas; devolver `null` si la acepción solo remite a un sinónimo, repite el término, o la entrada es una forma flexionada. El resultado se guarda en `glossary-terms.json` (el número y la razón), el usuario aprueba la tabla de unas 85 filas, y el armado posterior es determinista, sin LLM.

Alternativas:

- Regla determinista por marca (`Medicina`, `Farmacología`): resuelve 25 de 57 y elige mal `aperitivo`; no basta.
- Elección manual sin LLM: equivalente en calidad y más lenta, pero sin dependencia; es el plan B si el usuario prefiere decidir cada fila.
- Dejar que el LLM redacte la definición a partir de la acepción: descartado por el usuario y porque sería una adaptación que obligaría a indicar cambios más amplios.

### D5. Texto literal, recortado

Se guarda el texto de la acepción tal como Wikcionario lo muestra, con estos únicos cambios, que la atribución declara: se retira el marcado de enlaces y énfasis, las notas al pie (`[1]`) y las listas de sinónimos, antónimos, usos y ejemplos; se normalizan los espacios; y se recorta a la primera oración (hasta el primer punto que no sea de una abreviatura de la lista corta, como «etc.» o «p. ej.»). No se cambia la mayúscula inicial ni se parafrasea. «Dicho de un medicamento: Que mitiga el dolor.» queda como está. El texto debe terminar en punto y estar entero; si el recorte da menos de 12 caracteres o más de 300, el término se revisa a mano.

Alternativas: la acepción completa (algunas son largas, como `astringente`, que sigue con ejemplos de sales); una paráfrasis hecha por el LLM (descartada, véase D4); minúscula inicial para encajar tras un encabezado (es un cambio más que indicar, sin beneficio).

### D6. Sin acepción adecuada

El término queda sin definición, registrado en la sección de excluidos con motivo y fecha (`sin-entrada`, `solo-forma-flexionada`, `circular`, `sinonimo`, `vaga`, `sensible`, `patron-no-aprobado`). Nunca se completa con otra fuente ni con conocimiento propio. Los términos ausentes más frecuentes (Vermífugo, 182 grupos; Hemostático, 84) quedan sin explicación hasta que Wikcionario cree la entrada o el usuario decida otra fuente abierta (pregunta Q2).

### D7. Dónde vive el glosario

Tres capas, todas derivadas de la semilla:

- **Semilla.** `data/seed/glossary.json` (`catalog-glossary/1`) con la fuente, la licencia, su URL y las filas ordenadas por clave: `key` (forma base normalizada), `term`, `text`, `sense`, `entryUrl` (con `oldid`), `revisionId`, `revisionTimestamp` y `retrievedAt`. El manifiesto suma `glossaryHash` (sha256 del JSON canónico) y `glossaryCount`. El `seedHash` no cambia: así los registros y su hash quedan como están y no hay que tocar el cálculo de Python ni el de Rust para ellos.
- **Base.** Una migración `2026-10-30-000000_catalog_v3` crea `activity_glossary` (`key` llave, `term`, `text`, `entry_url`, `revision_date`, `source_id` que referencia `source`) y añade `plant_use_group.glossary_key` nula que referencia `activity_glossary(key)`. `SCHEMA_VERSION` pasa a 3 y se actualizan `schema.rs`, `rows.rs`, la lista de tablas esperadas y `NEUTRAL_TABLES`. Los nombres son neutrales y no contienen el nombre de ningún dataset.
- **API.** `useGroups[].glossary` (D9) y el crédito en `credits`.

Alternativas:

- Incluir el glosario en el `seedHash`. Más uniforme, pero cambia el hash de la semilla vigente y exige que Python y Rust lo calculen igual desde el primer día; el hash propio es más simple y deja la verificación intacta.
- Escribir la definición dentro de cada registro de planta. Cambiaría hasta 1.196 archivos y exigiría subir el prompt o el esquema de registro (regenerar con el LLM); un glosario compartido es una sola fuente de verdad.
- Resolver el enlace en la consulta de la API con un `JOIN` por texto. Obliga a repetir la regla de la forma base en SQL y en cada consulta; guardar la clave en el build deja la regla en un solo sitio.
- Una tabla de enlace `use_group_glossary`. Más tablas para una relación 1 a 0..1.

### D8. Relación con la actividad del grupo

La coincidencia es por la forma base de la actividad que ve el usuario (`plant_use_group.activity`): el texto antes del primer paréntesis, en minúsculas NFC y con los espacios colapsados, sin quitar acentos; es la misma idea que `sensitive-activities.json` aplica a `activitySource`. `Antídoto (escorpión)` y `Estimulante (veterinario)` heredan la definición de `antídoto` y `estimulante`, y el calificador sigue en el título. No se enlazan las actividades con la fórmula «Uso tradicional, sin eficacia demostrada: », ni ninguna actividad sensible (el validador impide que el término esté en la lista sensible). La regla se implementa dos veces (Python al armar la clave, Rust al enlazar) con un archivo de casos compartido (`glossary-key-cases.json`) que ambos prueban. Con la forma base, los 57 términos con entrada enlazan 5.240 grupos y 112 actividades distintas.

Se enlaza por la actividad traducida y no por `activitySource`, porque la explicación debe corresponder a la palabra que se muestra: con `Aperient` → `Aperiente` o `Laxante suave`, el original en inglés llevaría una definición ajena a lo que se lee. Las actividades que el LLM dejó sin traducir (`Aperient`) no tienen explicación; arreglarlas exige regenerar la traducción y está fuera de alcance.

Alternativas: coincidencia exacta sin forma base (pierde 84 grupos de `Antídoto (…)` y calificadores veterinarios); coincidir también sin acentos (`Tonico`; se descarta porque la traducción ya normaliza el español y un falso positivo pesaría más que un fallo).

### D9. Contrato de la API

Cada elemento de `useGroups` suma `glossary`, siempre presente: `null` o `{text, url}`. `text` es la definición literal y `url` la URL de la revisión. Es aditivo, dentro de `/v1` (`catalog-api`, «Compatibilidad dentro de `/v1`»); `uses`, el orden y los demás campos no cambian. `credits` suma Wikcionario si algún grupo servido tiene `glossary` no nulo, con una consulta más en `load_credits` que sigue el patrón de los datasets de referencias. Se documenta en `openapi.json` y la colección de Postman.

Alternativas: un solo campo `activityNote` de texto (sin la URL, que obligaría a otra solución para la atribución por entrada); un mapa `glossary` en la raíz del detalle por actividad (separa la explicación del grupo y obliga al cliente a unirlos); un campo `label` con el encabezado (la API serviría textos de interfaz; se prefiere la constante en la app, que el escaneo de lenguaje de eficacia cubre).

### D10. Lenguaje de eficacia

Una definición como «Que suaviza y protege las mucosas» describe la palabra. Para que no se lea como una promesa sobre la planta se combinan tres medidas:

- **Encabezado fijo en la app: «Según Wikcionario:»**, con el texto entre comillas angulares, en texto secundario. Es una cita atribuida, no una afirmación del catálogo, y nombra la fuente en el punto de uso. El aviso fijo de `Usos` («No son recomendaciones ni están comprobados clínicamente») sigue arriba.
- **Validador del glosario**, sobre el texto de cada término: error si hay dosis o posología (cantidad con unidad, «dosis», «posología», «gotas», «cucharadas»); error con los patrones de eficacia de `DOSE_PATTERNS` (curar, tratar, prevenir, eliminar, aliviar, eficaz, efectivo) salvo que la lista versionada apruebe ese patrón para ese término, con motivo; error si menciona alguna enfermedad grave de `sensitive-activities.json` (cáncer, tumor, diabetes…). Con los 85 candidatos, 6 términos adecuados necesitarían la aprobación de un patrón (antidiarreico, antiséptico, bactericida, fungicida, parasiticida y vulnerario), `emoliente` quedaría fuera por «tumores» y `demulcente` se resuelve eligiendo la acepción 1.
- **Revisión humana** de la tabla de definiciones antes de sellar, que decide también los verbos de efecto que el validador no ve («fortalece», «favorece», «mitiga», «combatir»), porque son justo el significado de los términos.

Alternativas: sin encabezado, con el texto solo (se confundiría con una afirmación sobre la planta); un prefijo «Término tradicional:» (no dice quién lo define y suena a recomendación tradicional); una redacción neutra propia, como «Se usa para…» (sería texto del modelo, descartado); el encabezado en los datos de la API (rechazado en D9).

### D11. App

La línea de explicación va bajo el título del grupo y antes de la línea de datos del cambio paralelo (`bodySmall`, gris, con el mismo contraste que la atribución de `Fuentes`), solo si el grupo trae `glossary`. El encabezado y las comillas son constantes de `PassportTexts` y entran en `all`, que el escaneo de lenguaje de eficacia recorre. La línea es parte del título para la semántica (un solo nodo de lectura: actividad, explicación y datos). Sin URL visible y sin truncado a 360x640 al 200 %. La atribución de Wikcionario sale de `credits` en `Fuentes` sin código nuevo. Se mantiene en el modelo la `url` de la revisión por si se decide enlazar la explicación (Q5).

Coordinación con `compact-passport-uses`: se implementa después, o sobre el diseño vigente si aquel aún no se aplicó (la línea va bajo la actividad en ambos). Los deltas no chocan: aquel modifica «Usos como registros tradicionales trazables» y «Accesibilidad del pasaporte», y este solo agrega un requisito. Hay que reconciliar `passport_uses_tab.dart` y las pruebas al aplicar el segundo.

## Risks / Trade-offs

- **Wikcionario cambia o es vandalizado** → cada fila fija la revisión y su URL con `oldid`; actualizar es un paso explícito y se revisa el diff.
- **Una definición se lee como promesa** → encabezado de cita, validador, aprobación por patrón y revisión humana (D10). Residual: verbos de efecto del significado que el usuario ve junto a una planta; se mide en la QA del emulador.
- **Cobertura parcial: ~22 % de los grupos** y términos muy frecuentes sin entrada (Vermífugo, 182 grupos) → se documenta; las preguntas Q2 y Q3 deciden la segunda fuente y la tanda de enfermedades.
- **Traducción inconsistente de las actividades** → algunas variantes no enlazan (`Aperient`); limitación documentada, sin tocar los registros.
- **Falsa coincidencia por la forma base** (`Pectoral` como adjetivo anatómico frente a remedio) → la acepción elegida describe el sentido de remedio y se revisa por término; las actividades ambiguas se excluyen.
- **User-Agent sin contacto** → riesgo de bloqueo sin aviso; las peticiones son pocas y seriales; Q4 propone añadir una URL de contacto.
- **El glosario es CC BY-SA y el resto de la semilla es de licencias mixtas** → ya ocurre con Wikipedia; se declara en `Fuentes` y en `docs/data/fuentes-y-licencias.md`. No es asesoría legal.
- **Dos implementaciones de la regla de la forma base** (Python y Rust) → archivo de casos compartido que ambas prueban.
- **Migración de esquema** → la base se regenera entera en cada build, no hay datos que migrar; la API comprueba `SCHEMA_VERSION` al arrancar, así que el binario y la base deben ir juntos (los construye la misma imagen).

## Migration Plan

1. Herramientas y semilla: fuente, descarga, lista aprobada, armado, validación y sellado. `plan` debe dar 0 plantas.
2. Backend: migración v3, lectura del glosario, enlace, API y crédito, con pruebas, `openapi.json` y Postman. Se prueba con una compilación local contra la semilla nueva.
3. Un solo push a `main` con la semilla y el backend: `deploy-backend.yml` construye la imagen (el `catalog.db` sale de la misma semilla, sin red) y redespliega Cloud Run. La API nueva sirve `glossary` y el crédito; el cliente anterior ignora el campo. QA de la API con Postman contra Cloud Run.
4. App: se compila el APK después de que el backend nuevo esté desplegado. Con un backend anterior (sin `glossary`) la app nueva no muestra explicaciones, sin errores.
5. Reversión: revertir el commit redespliega la imagen anterior; la base no guarda estado, y el APK nuevo sigue funcionando sin `glossary`.

Orden con el cambio paralelo: independiente en backend; en la app, `compact-passport-uses` primero si ya está listo.

## Open Questions

- **Q1.** ¿Se incluye `Emenagogo` (178 grupos)? Su acepción 2 dice «Sustancia que estimula el flujo de la sangre en el área de la pelvis y el útero, favoreciendo la menstruación» y la 1 está marcada como impropia; en `sensitive-activities.json` figura como dudoso. Propuesta por defecto: excluido hasta que el usuario lo apruebe.
- **Q2.** Para los 28 términos ausentes de Wikcionario (Vermífugo y Hemostático entre los más frecuentes), ¿se acepta que queden sin explicación, o se admite una segunda fuente abierta citada, como los artículos de Wikipedia en español que la semilla ya consulta?
- **Q3.** ¿Se hace después una segunda tanda para enfermedades y síntomas arcaicos (Hidropesía, Escrófula, Caquexia), con otra regla de selección?
- **Q4.** ¿Se añade una URL de contacto del proyecto (por ejemplo, su repositorio) al `User-Agent` de Wikcionario, como pide la política de Wikimedia, o se mantiene el genérico sin datos personales?
- **Q5.** ¿La explicación debe llevar un enlace en línea a la entrada de Wikcionario (atribución en el punto de uso), o basta la atribución en `Fuentes` que se pidió? La API ya entrega la URL de la revisión.
- **Q6.** ¿El encabezado «Según Wikcionario:» es aceptable, o se prefiere otro (por ejemplo, «Significado:»)?
- **Q7.** ¿Se aprueban los 6 términos cuyo texto contiene un patrón de eficacia («previene», «elimina», «curar»), o se excluyen?
