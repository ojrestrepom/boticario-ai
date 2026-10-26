# Resultados de QA: revisión de contenido de la semilla (tarea 10.5)

Alcance: tarea 10.5 de `consolidate-catalog-seed`. Revisión a mano de una muestra de 30 plantas de la semilla (`data/seed/plants/`, 2.354 registros, prompt v7, sello `sha256:0c42c0a285dee2a6fba331e8ab1e32b076b6ced17d8e93814e6a93d386e9800a`) contra sus paquetes (`data/work/bundles/`), más barridos automáticos sobre los 2.354 registros para saber si cada hallazgo es un caso aislado o un patrón. Fecha de ejecución: 2026-10-25. Rama `consolidate-catalog-seed`. Sin red, sin cambios en la semilla, el código, el prompt ni `tasks.md`.

Material de apoyo, todo dentro de `qa/`: `scripts-content-review/` (scripts de solo lectura) y `evidence-content-review/` (muestra, una vista por planta y un archivo por barrido). Los archivos de las tareas 10.1 a 10.4 no se tocaron.

## Resumen

- No hay hallazgos bloqueantes. En los 2.354 registros no se encontró ninguna dosis ni posología, ninguna promesa de eficacia, ningún nombre común inventado (CR-14 recoge tres expansiones de enumeraciones de Wikipedia que acepto), ninguna enfermedad grave sin la fórmula «Uso tradicional, sin eficacia demostrada: …» y ninguna señal de riesgo dentro de `traditionalUses`. La única cantidad en un texto visible es la de CR-02 (dos registros). El validador da 0 errores y 0 advertencias, y mis comprobaciones independientes lo confirman salvo en los puntos de abajo.
- Hallazgos mayores (5): CR-01 la clave `Nas` se resuelve a «Lost Crops of the Incas» en 52 grupos de 16 plantas, casi todas de uso chino; CR-02 una cantidad («1,0 µg/kg») en el texto de seguridad de dos hinojos; CR-03 tres plantas pierden usos del paquete sin aviso; CR-04 un registro mezcla la identidad de la coliflor con la de `Brassica cretica` (ya tiene `reviewFlag`); CR-05 43 plantas con señales de muerte o veneno homicida quedan en nivel medio o sin nivel (decisión de diseño que conviene confirmar).
- Hallazgos menores (13, CR-06 a CR-18) y observaciones (OBS-01 a OBS-06), casi todos de consistencia: fórmulas con comillas sueltas, términos en inglés sin traducir, autores de imagen sucios, «Malesia» traducido como «Malasia», texto de seguridad que cuenta la lógica interna del pipeline.
- De las 30 plantas de la muestra, 9 no tienen hallazgos, 2 tienen solo observaciones, 17 tienen hallazgos menores y 2 tienen un hallazgo mayor (`foeniculum-vulgare-var-dulce`, CR-02, y `abrus-precatorius`, CR-05). Los otros tres mayores (CR-01, CR-03 y CR-04) salieron de los barridos sobre toda la semilla.
- El validador no detecta ninguno de los hallazgos mayores ni de los defectos de forma de CR-06: los 4 registros con comillas sueltas y los 2 con `µg/kg` pasan con 0 errores. Las resoluciones propuestas incluyen reglas nuevas para el validador.

## Muestra y cómo se eligió

Treinta plantas, definidas por la tarea 10.5 y por el encargo de QA. Algunas cumplen más de un criterio (la bergamota es del piloto, separada por colisión y de la EMA fuera de USDA; el hinojo dulce es separado por colisión y de la EMA fuera de USDA); cada una se cuenta una sola vez en su grupo principal.

| Grupo | Plantas |
| --- | --- |
| Piloto (6) | `lavandula-angustifolia`, `matricaria-chamomilla`, `mentha-x-piperita`, `hypericum-perforatum`, `citrus-x-bergamia`, `prunus-amygdalus` |
| Tóxicas de TPPT (5) | `conium-maculatum`, `ricinus-communis`, `datura-stramonium`, `aconitum-napellus`, `abrus-precatorius` |
| Solo género (3) | `aloe-spp`, `crataegus-sp`, `ephedra-spp` (la tercera la elegí por ser un género conocido por sus riesgos y sin ningún dato de seguridad en el paquete) |
| Separadas por colisión (3) | `citrus-x-paradisi`, `brassica-oleracea-var-italica`, `foeniculum-vulgare-var-dulce` |
| Fusionadas por colisión (2) | `cinnamomum-verum`, `ocimum-tenuiflorum` |
| Solo de la EMA, fuera de USDA (3) | `pelargonium-sidoides`, `rhodiola-rosea`, `tilia-cordata` (60 plantas cumplen el criterio; además lo cumplen la bergamota y el hinojo dulce de arriba) |
| Fase 2, al azar (6) | `oryza-sativa`, `cinnamomum-burmanni`, `abutilon-theophrasti`, `malus-domestica`, `zygophyllum-creticum`, `myrciaria-dubia` |
| Fase 2, con actividad sensible (2) | `platycodon-grandiflorus` (Cancer), `geissospermum-laeve` (Malaria) |

Elección de las 8 de la fase 2, reproducible con `scripts-content-review/select_sample.py` (Python 3.9.6, semilla 105):

- La fase 2 son las 2.148 plantas cuyo paquete no trae fichas de la EMA (`sections.regulatory` vacío), con los IDs ordenados.
- Las 6 primeras son `random.Random(105).sample(fase2, 6)`.
- Las 2 con actividades sensibles son `random.Random(105).sample(pool, 2)`, donde `pool` son las 851 plantas de la fase 2, fuera de las 6, con al menos una actividad de la lista `sensitive-activities.json` (enfermedad grave o señal de riesgo).
- Entre las 8 hay 5 con enfermedades graves en los usos (`oryza-sativa`, `cinnamomum-burmanni`, `zygophyllum-creticum`, `platycodon-grandiflorus`, `geissospermum-laeve`). Ninguna de las 8 tiene señales de riesgo en el paquete; ese caso lo cubren las 5 tóxicas de TPPT y `hypericum-perforatum` (Poison, Abortifacient, Phototoxic), y las enfermedades graves además `cinnamomum-verum` y `ocimum-tenuiflorum`.

## Método

- Por cada planta leí el registro completo y las secciones del paquete que lo respaldan (nombres, Wikidata, descripciones, distribución, EMA, seguridad, usos con candidatas de cita, imágenes). La vista que usé está guardada en `evidence-content-review/plants/<id>.txt`.
- Comprobé: palabras de dosis, posología, eficacia y consejos imperativos; nombres comunes y `displayName` contra el paquete (texto e idioma); traducción de cada actividad, con atención a las sensibles; fórmula de las enfermedades graves; señales de riesgo fuera de los usos y presentes en `safety` con sus refs `usda_use:*`; datos sin respaldo (descripción, origen, objetivos, precauciones) leyendo el texto del ref; emparejamiento de claves de cita con candidatas (`Woi.<n>`, `Eb<vol>: <pág>`, `Nas`); formato y autor de la imagen; nivel de `safety` frente al máximo de las entradas del paquete.
- `scripts-content-review/cr_lib.py` automatiza lo comprobable por regla (texto de nombres, idioma, `activitySource`, `n`, refs del grupo, claves de cita, candidatas, fórmulas, frases de advertencia, nivel, imagen). `global_scans.py` repite los barridos de cada hallazgo sobre los 2.354 registros. Los juicios de traducción y de respaldo los hice leyendo: revisé a mano los 967 pares de actividad y traducción que difieren del original (sin las variantes de cáncer y tumor, que revisé aparte) y las 101 formas de enfermedades graves que aparecen en los registros.
- Un hallazgo se marca mayor si cambia lo que el usuario lee sobre seguridad, identidad o fuentes, o rompe una regla de la política de contenido (cantidades, cita equivocada, pérdida de datos); menor si es de consistencia, forma o matiz; observación si no es un defecto pero conviene saberlo.

## Resultados por planta

La columna «Hallazgos» remite a la sección «Hallazgos». «Sin hallazgos» significa que no encontré nada que corregir; las advertencias de cada planta (`reviewFlags`) las revisé y son coherentes con el paquete.

| Planta | Qué se revisó | Hallazgos |
| --- | --- | --- |
| `lavandula-angustifolia` | nombres (Lavanda sale del resumen de Wikipedia), 11 usos y citas, 2 objetivos EMA, seguridad (EFSA tuyona, TPPT débil, EMA 4.3 y 4.4), aceite, imagen | Sin hallazgos. «Espasmo» y «Nervino» son traducciones literales aceptables |
| `matricaria-chamomilla` | `displayName` Manzanilla (P1843 de Wikidata), 16 nombres, 20 grupos (cap correcto), 4 objetivos, seguridad con CYP450 sin dosis, 15 grupos con `Woi.Syria` sin resolver y su flag | CR-14 (dos nombres reconstruidos de «dulce o cimarrona» y mayúsculas mezcladas), OBS-04 |
| `mentha-x-piperita` | nombre, 20 grupos, cáncer con fórmula, 4 objetivos, seguridad larga (EFSA pulegona, EMA aceite y hoja) comparada con 4.3, 4.4 y 4.5 | Sin hallazgos |
| `hypericum-perforatum` | `displayName` «Hierba de San Juan» (válido, hay «hipérico»), 40 nombres, objetivo `relajacion-estres` pendiente con flag, nivel alto por 4.5, 3 señales de riesgo en `safety` (Abortifacient, Phototoxic, Poison, con sus 3 refs `usda_use`), Cancer(Stomach) y Tumor con fórmula | CR-13 (descripción reducida a «Especie más abundante de la familia de las hipericáceas») |
| `citrus-x-bergamia` | separada por colisión, origen nulo por ser el del aceptado compartido, sin datos de seguridad (solo una declaración pública de la EMA) | OBS-01 |
| `prunus-amygdalus` | nombre, descripción, seguridad TPPT débil con amigdalina, `oil` por compuesto EO con flag, imagen CC BY-SA | Sin hallazgos |
| `conium-maculatum` | sin nombre común en español (flag), nivel alto, 10 Poison y 2 Fatality en `safety` (12 refs), 19 grupos con fórmula en cáncer, tumor y tétanos | OBS-02 |
| `ricinus-communis` | objetivos omitidos por toxicidad con flag, seguridad (TPPT, EFSA ricina, EMA aceite 4.3 a 4.5), 10 refs de riesgo, nombres dudosos con flag, 20 grupos | Sin hallazgos |
| `datura-stramonium` | nivel alto, 4 señales de riesgo en `safety` (Poison, Fatality, Homicide, Cyanogenetic; 12 refs), 20 grupos, Tumor y Carcinoma con fórmula | CR-09 («Fumitory» sin traducir) |
| `aconitum-napellus` | nombres de Wikidata con flag de idioma, Poison y Poison(Arrow) en `safety` (7 refs), 14 grupos | Sin hallazgos |
| `abrus-precatorius` | seguridad: EFSA abrina y estudios de muertes en niños, 4 señales, fórmula en Malaria, Cancer y Epithelioma, origen largo | CR-05 (nivel medio), CR-11 (sin punto final) |
| `aloe-spp` | solo género, nombres de Wikipedia, descripción sin usos, imagen CC BY-SA | CR-14 (Sábila y Acíbar con mayúscula), CR-18 |
| `crataegus-sp` | solo género, `displayName` Espino (P1843) | CR-14 («Majuelos» en plural y mayúscula), CR-18 |
| `ephedra-spp` | solo género, sin ningún dato de seguridad (flag), descripción | OBS-03 (género conocido por sus riesgos, solo con flag), CR-18 |
| `citrus-x-paradisi` | separada, origen nulo, furanocumarinas fototóxicas de EFSA en la cáscara, 3 grupos pendientes por `Woi.Syria` con flag | Sin hallazgos |
| `brassica-oleracea-var-italica` | separada, nombres de Wikidata y Wikipedia, seguridad TPPT «no tóxica» con glucosinolatos | CR-14 (mayúsculas), CR-16 (se omite el matiz de TPPT «solo notable con consumos muy altos») |
| `foeniculum-vulgare-var-dulce` | separada, sin nombre en español (el único es un nombre científico de Wikidata), EMA fruto, EFSA estragol | CR-02 (`1,0 µg/kg`) |
| `cinnamomum-verum` | fusionada con `Cinnamomum zeylanicum`, `displayName` Canelo (único del paquete), EFSA safrol y cumarina | CR-09 («Femenino» literal) |
| `ocimum-tenuiflorum` | fusionada con `Ocimum sanctum`, `displayName` Tulsí, Cholera con fórmula | CR-11 («Malasia» por «Malesia», «Asia tropical» no dicho por la fuente), CR-09 («Dolor (oído)») |
| `pelargonium-sidoides` | solo EMA, nombre de Wikipedia, seguridad con hepatotoxicidad de la EMA, objetivo respiratorio | CR-10 (autor de imagen con «Photo by and (c)2006 … Location credit …») |
| `rhodiola-rosea` | solo EMA, 2 objetivos, 4 usos, seguridad sin nivel | Sin hallazgos |
| `tilia-cordata` | solo EMA, 16 grupos, Tumor(Feet) con fórmula | CR-16 (indicaciones 1 y 2 asignadas a áreas), CR-09 («Fumitory») |
| `oryza-sativa` | fase 2, 20 de 50 grupos, Tumor y Cancer(Breast) con fórmula, sin datos de seguridad (flag) | CR-09 («Carbuncle»), CR-17 |
| `cinnamomum-burmanni` | sin nombre en español (flag), EFSA cumarina y estudio de hepatotoxicidad, Malaria y Tumor con fórmula | CR-09 («Gripes» sin traducir, falso amigo), CR-11 («Región nativa:» y «Malesia»), CR-17 |
| `abutilon-theophrasti` | sin nombre en español (flag), seguridad TPPT «nontoxic» con aclaración | CR-09 («Aperient»), CR-12 («nontoxic» en inglés) |
| `malus-domestica` | `displayName` Manzano (P1843), seguridad débil, `oil` por EO con flag | CR-16 («solo en trazas»), OBS-05 |
| `zygophyllum-creticum` | descripción de `Fagonia cretica` (sinónimo), 13 grupos pendientes (14 con flag) por `Woi.Syria`, nombres catalanes con `und` y flag | Sin hallazgos |
| `myrciaria-dubia` | `displayName` Camu-camu, nombres de USDA sin etiqueta de idioma | CR-14 (anotaciones «(Sp.)», «(Peru)» y «(Bol.)» retiradas sin flag, cuatro nombres marcados `es`) |
| `platycodon-grandiflorus` | `displayName` Campanilla china (alias de Wikidata), 20 grupos, fórmula en Cancer, `Nas` resuelto a NAS2 | Sin hallazgos |
| `geissospermum-laeve` | sin nombre en español (flag), EFSA solo evidencia, Malaria con fórmula | CR-12 («ninguna fija un nivel de riesgo»), OBS-06 |

Recuento: 9 sin hallazgos (`lavandula-angustifolia`, `mentha-x-piperita`, `prunus-amygdalus`, `ricinus-communis`, `aconitum-napellus`, `citrus-x-paradisi`, `rhodiola-rosea`, `zygophyllum-creticum`, `platycodon-grandiflorus`); 2 solo con observaciones (`citrus-x-bergamia`, `conium-maculatum`); 17 con hallazgos menores; 2 con un hallazgo mayor (`foeniculum-vulgare-var-dulce`, CR-02, y `abrus-precatorius`, CR-05). Los otros mayores (CR-01, CR-03, CR-04) no tocan a la muestra de 30 y salieron de los barridos. Ninguna planta de la muestra tiene dosis, promesas de eficacia ni nombres inventados.

## Hallazgos

Cada resolución propuesta es una de: corregir regenerando la planta, añadir un `reviewFlag` (el catálogo de códigos está cerrado en `tools/catalog-seed/flag-codes.json`), ajustar el prompt o el validador, o aceptar. Nota para quien decida: cambiar el prompt sube `prompt-version` y `plan` vuelve a poner en cola las 2.354 plantas, así que para correcciones de forma conviene un paso determinista sobre los registros o una regla del validador, y regenerar solo las plantas afectadas.

### Mayores

**CR-01. La clave de cita `Nas` se resuelve a «Lost Crops of the Incas» en plantas de uso chino.**

- Plantas: 16 (52 grupos): `andrographis-paniculata`, `ardisia-japonica`, `areca-catechu`, `arisaema-consanguineum`, `aristolochia-debilis`, `artemisia-capillaris`, `celosia-argentea`, `datura-metel`, `glycyrrhiza-uralensis`, `lonicera-japonica`, `lophatherum-gracile`, `paeonia-lactiflora`, `rosa-laevigata`, `rubia-cordifolia`, `silybum-marianum`, `zea-mays`.
- Evidencia: la clave `Nas` tiene dos candidatas en el paquete, `usda_reference:NAS` («Lost Crops of the Incas.») y `usda_reference:NAS2` («Herbal pharmacology in the People's Republic of China. National Academy of Sciences…»). En `andrographis-paniculata`, `traditionalUses[0]` (Dysentery; China, India, Malaya) y `[11]` (Antiseptic; China) citan `NAS` con el texto «Lost Crops of the Incas.». De los 52 grupos, 49 incluyen a China entre sus países y ninguno incluye un país andino. En el resto de la semilla la misma clave se resolvió a `NAS2` en 540 grupos (497 de China) y quedó sin resolver en 17 grupos de 8 plantas (`capsella-bursa-pastoris`, `dianthus-chinensis`, `dianthus-superbus`, `persicaria-hydropiper`, `portulaca-oleracea`, `rumex-crispus`, `solanum-nigrum`, `tussilago-farfara`). En la muestra, `platycodon-grandiflorus` la resuelve bien a `NAS2`.
- Efecto: un uso tradicional chino queda respaldado por una obra sobre cultivos andinos; la cita no dice lo que el registro afirma. El ref del grupo (`usda_reference:NAS`) también es el equivocado.
- Resolución propuesta: corregir regenerando las 16 plantas o, mejor, con un paso determinista que cambie `ref`, `text` y el ref del grupo de `NAS` a `NAS2` en esas 52 citas. Añadir una regla al validador: si una clave tiene dos o más candidatas, la elegida debe coincidir con los países de las filas del grupo; mientras no exista, dejarla sin resolver con `cita-sin-resolver`. Opcional: resolver también a `NAS2` las 17 sin resolver cuando todas las filas sean de China.
- Evidencia guardada: `evidence-content-review/barridos/nas-citas.txt`.

**CR-02. Cantidad en el texto de seguridad de los dos hinojos.**

- Plantas: `foeniculum-vulgare` y `foeniculum-vulgare-var-dulce` (de la muestra).
- Evidencia: `safety.text` dice «… que en niños de 4 a 12 años no se recomienda si la ingesta diaria de estragol supera el valor guía de 1,0 µg/kg de peso corporal salvo evaluación de riesgo …». El paquete (`ema_pdf:foeniculi-dulcis-fructus:4.4`) lo dice en inglés: «if the daily intake of estragole exceeds the guidance value of 1.0 µg/kg bw». La política prohíbe cantidades, dosis y posologías en el texto; `DOSE_PATTERNS` del validador cubre `mg` y `ml` pero no `µg` ni `kg`, por eso pasa.
- Resolución propuesta: corregir regenerando las 2 plantas con una redacción sin la cifra («no se recomienda en niños de 4 a 12 años según la ingesta de estragol, salvo evaluación de riesgo»). Ajustar el validador: añadir `\bµg\b`, `\bμg\b`, `\bkg\b`, `\bg\b` y cualquier número seguido de unidad a `DOSE_PATTERNS`. Los límites de edad (206 menciones como «menores de 12 años» o «de 18 años» en `safety.text`) son poblaciones, no dosis, y se aceptan; el barrido `cantidades-y-dosis.txt` solo devuelve estas 2 plantas.

**CR-03. Plantas con usos del paquete perdidos sin aviso.**

- Plantas: `inocarpus-fagifer` (12 grupos de usos en el paquete y 0 en el registro), `inga-edulis` (2 y 0), `heimia-salicifolia` (21 y 19, cuando el tope es 20; faltan `Sore` y `Sudorific`).
- Evidencia: los paquetes tienen candidatas para todas las claves y ninguna señal de riesgo; el `bundleHash` coincide; los registros no llevan ningún `reviewFlag` que lo explique (`inocarpus-fagifer` solo `sin-datos-de-seguridad`; `inga-edulis` `idioma-de-nombre-dudoso` y `sin-datos-de-seguridad`). De las 441 plantas con más de 20 grupos que no son señales de riesgo, 440 siguen exactamente el orden que fija el prompt (primero grupos con alguna clave con candidata, por `n` y por actividad), así que estos son errores puntuales del generador (barrido `usos-perdidos.txt`).
- Resolución propuesta: corregir regenerando las 3 plantas. Ajustar el validador: si el paquete trae grupos de usos que no son señales de riesgo, `traditionalUses` debe tener al menos `min(20, n)` grupos; hoy solo comprueba que cada grupo sea del paquete.

**CR-04. Registro con la identidad de la coliflor bajo `Brassica cretica subsp. cretica`.**

- Planta: `brassica-cretica-subsp-cretica` (de los barridos; no está en la muestra).
- Evidencia: `scientificName` es `Brassica cretica subsp. cretica` (WCVP), pero `displayName` es «Coliflor», la descripción es la de `Brassica oleracea var. botrytis (coliflor)`, la imagen es `19_-_cauliflower.jpg`, los nombres en inglés y alemán son Cauliflower y Blumenkohl y la seguridad es la de TPPT para la coliflor. La causa es que USDA registra `Brassica oleracea var. botrytis` como alias y WCVP lo resuelve a `Brassica cretica`. El registro ya lleva `conflicto-entre-fuentes` (target `description`) y `backbones-discrepan`, con el mensaje «conviene una revisión humana».
- Resolución propuesta: registrado como `reviewFlag`, que cumple el criterio de la tarea. Recomendación: decidir si la entrada debe ser la coliflor (nombre científico `Brassica oleracea var. botrytis`) o si hay que quitar nombre, imagen, descripción y seguridad de la coliflor; es una corrección de identidad en la resolución taxonómica, no de redacción. Mientras tanto, aceptar con el flag.

**CR-05. Plantas con señales de muerte o veneno homicida quedan con nivel medio o sin nivel.**

- Plantas: 56 tienen en USDA alguna señal letal (`Fatality`, `Fatal`, `Death`, `Suicide` u `Homicide`); 13 salen con nivel alto (por TPPT), 16 con medio y 27 sin nivel. En la muestra: `abrus-precatorius` (nivel medio). Fuera de la muestra: `cicuta-maculata` (medio), `hippomane-mancinella`, `croton-tiglium`, `blighia-sapida`, `manihot-esculenta` (sin nivel); la lista completa está en `senales-letales-y-nivel.txt`.
- Evidencia: `abrus-precatorius.safety.level` es `medio` aunque el paquete trae `efsa_endpoint:155` («Severe poisonings among adults following the intake of one half or two seeds, as well as cases of death among children following the consumption of two seeds»), cinco grupos de riesgo (`Poison`, `Fatality`, `Fatal`, `Homicide` y `Abortifacient`), y la abrina de EFSA como veneno potente. `safety-map.json` (decisión D8 del usuario) dice que EFSA no fija alto por sí sola, y la spec y `design.md` (decisión del usuario, regla de la v5) dicen que una señal de riesgo «por sí sola SHALL NOT fijar el nivel». Las dos reglas se cumplieron al pie de la letra: no es un error del generador sino el efecto combinado de dos decisiones.
- Efecto: la app mostrará «precaución media» o ningún nivel para plantas cuyos propios paquetes registran muertes. El texto de `safety` sí lleva las advertencias.
- Resolución propuesta: ajustar el validador o `safety-map.json` solo si el usuario lo decide (por ejemplo, `Fatality`, `Fatal`, `Death`, `Suicide` y `Homicide` fijan al menos medio, y el grupo EFSA `veneno-potente` fija alto). Si no, aceptar y documentarlo en la spec para que la app presente el texto de advertencia aunque `level` sea nulo. No requiere regenerar nada para aceptarlo.

### Menores

**CR-06. Fórmula de enfermedad grave malformada.** Cuatro registros (cinco textos) tienen la fórmula con dos espacios y una comilla final: `bursera-simaruba` (`traditionalUses[12]` «Uso tradicional, sin eficacia demostrada:  fiebre amarilla"» y `[17]` «…  cáncer de estómago"»), `byrsonima-crassifolia` (`[19]` «…  tumor de pierna"»), `caesalpinia-pulcherrima` (`[18]` «…  epilepsia"») y `cajanus-cajan` (`[7]` «…  accidente cerebrovascular"»). El validador quita el prefijo con `startswith` y no revisa el resto, por eso los acepta. Resolución: corregir con un paso determinista que normalice los 5 textos (o regenerar las 4 plantas) y exigir en el validador que lo que sigue a la fórmula empiece por una letra y no lleve comillas.

**CR-07. Señal de riesgo veterinaria presentada como advertencia general.** `mesosphaerum-suaveolens` solo tiene `Poison(Veterinary)` (ref `usda_use:75243`) y su `safety.text` termina en «Advertencia: registrada como veneno en usos tradicionales.», sin decir que es de uso veterinario; `cascabela-thevetia` y `chrysobalanus-icaco` sí lo dicen («… (uso veterinario)»). Es un caso aislado entre las 5 plantas con ese calificador (`gliricidia-sepium` y `mangifera-indica` tienen además un `Poison` sin calificador, así que su advertencia es correcta). Resolución: regenerar `mesosphaerum-suaveolens` con la redacción de `chrysobalanus-icaco`. Opcional: regla del validador para que una señal cuyas filas son todas `(Veterinary)` lo diga.

**CR-08. Dos usos de enfermedad grave quedan fuera de la lista por un envoltorio.** `actaea-spicata` tiene «Preventivo (malaria)» (de `Preventitive(Malaria)`) y `eucalyptus-globulus` «Antipalúdico» (de `Antimalaria`), sin la fórmula de enfermedad grave porque la lista compara solo la forma base. Resolución: ajustar `sensitive-activities.json` (añadir `Preventitive` y `Antimalaria` como envoltorios que heredan la categoría de lo que contienen) y regenerar esas 2 plantas, o aceptar por ser 2 casos.

**CR-09. Actividades sin traducir, falsos amigos y traducciones inconsistentes.**

- Evidencia: 179 grupos en 155 registros conservan el término inglés de USDA (`Fumitory` 39, `Aperient` 22, `Gravel` 20, `Ague` 13, `Antivinous` 13, `Decoagulant` 11, `Bilious` 10, `Carbuncle` 9, `Corn` 7, `Boil` 5, …), aunque el prompt lo permite solo «si no hay una traducción segura». Otros agentes tradujeron las mismas palabras (`Boil` es «Forúnculo» en 92 grupos y `Corn` es «Callo» en 22). 140 de las 1.198 actividades distintas de USDA tienen más de una traducción en la semilla, por ejemplo `Sore` («Llaga» 223, «Llagas» 11, «Sore» 4), `Anodyne` («Anodino» 216, «Analgésico» 11), `Ache(Tooth)` (7 formas) y `Tumor(Abdomen)` («tumor de abdomen» 14, «tumor abdominal» 6).
- Casos con riesgo de lectura equivocada: `Gripes` sin traducir en `cinnamomum-burmanni` (en español «gripes» es el plural de «gripe»; en inglés son retortijones), `Labor` sin traducir en `spondias-dulcis`, `Aperient` traducido «Aperitivo» en `argemone-mexicana` (laxante suave, no aperitivo), `Tubercle` traducido «Tubérculo» en `sterculia-urens`, `Corn` sin traducir (en español se lee «maíz»). `Fumitory` (39 grupos) se deja en inglés y no es una palabra española corriente.
- La formación de los calificadores varía: «Dolor de oído» (29) y «Dolor (oído)» (9); «(uso veterinario)» y «(veterinario)».
- Las 101 formas de enfermedades graves que aparecen en los registros están bien traducidas (Phthisis es «tisis», Apoplexy «apoplejía», Hodgkin's Disease «enfermedad de Hodgkin», etc.); solo cambia la redacción de algunas (CR-06 y la variante «tumor abdominal»).
- Resolución propuesta: aceptar las variantes de redacción; tratar las traducciones erróneas con un glosario determinista (una tabla `activitySource` a `activity` aplicada a los registros) que corrija como mínimo `Gripes`, `Aperient`, `Tubercle`, `Corn`, `Labor`, `Fumitory` y `Boil`. Un glosario evita subir `prompt-version`. Revisión completa de las 967 traducciones distintas: `evidence-content-review/barridos/actividades-variantes.txt` y `actividades-sin-traducir.txt`.

**CR-10. Autor de imagen sucio y formatos.**

- Evidencia: después de la limpieza de `fix1` quedan autores con ruido en 68 registros: texto de plantilla de Commons («The original uploader was X at English Wikipedia .», 15), «Photo by and (c)2006 Derek Ramsey ( Ram-Man ). Location credit to the Chanticleer Garden.» (`euphorbia-tirucalli`, `juglans-nigra`, `pelargonium-sidoides`, `ilex-verticillata` con variantes), «Unknown author Unknown author» (`ferula-gummosa`, `herniaria-hirsuta`, `hydnocarpus-kurzii`, `angelica-sinensis`), «Transferred from en.wikipedia to Commons.» como autor (`eucalyptus-melanophloia`), «Own work» como único autor (`gentiana-scabra`, `sarcomphalus-joazeiro`, `tagetes-lucida`), autores de 150 a 245 caracteres con citas bibliográficas y URL (13, por ejemplo `carya-glabra`, `diospyros-virginiana`, `chondrodendron-tomentosum`) y notas de suposición («Unknown (presumably Father Hernández himself)», `ipomoea-corymbosa`). Dos registros (`saccharomyces-cerevisiae`, `triticum-aestivum`) usan una imagen SVG, formato que la app (aún sin imágenes) probablemente no mostrará con un `Image.network` normal. Los demás formatos son JPEG, PNG y GIF.
- Efecto: la atribución existe y la licencia es la correcta, pero «Own work» no nombra al autor.
- Resolución propuesta: ampliar la limpieza de autor de `licenses.py` y regenerar solo los registros cuyo `image.author` cambie; decidir si el SVG se admite. No bloquea.

**CR-11. Origen: «Malesia» traducido como «Malasia» y estilos mezclados.**

- Evidencia: WCVP usa la región botánica «Malesia» (Indonesia, Filipinas, Malasia, Nueva Guinea…). 48 registros la escriben «Malasia», el país (`ocimum-tenuiflorum`, `albizia-procera`, `arctium-lappa`, `artemisia-annua`, …); 167 la escriben «Malesia». Además `ocimum-tenuiflorum` dice «Asia tropical y oriental», que el paquete no dice (solo trae regiones como `Indian Subcontinent` o `Indo-China`), y agrupa países entre paréntesis como si fueran subregiones. De los 2.197 orígenes, 1.322 terminan en punto y 875 no; 763 empiezan con «Nativa de» o «Nativa del» y 10 con «Región nativa» (`cinnamomum-burmanni`).
- Resolución propuesta: sustituir «Malasia» por «Malesia» en los 48 orígenes con un paso determinista; normalizar punto final y prefijo; aceptar el resto.

**CR-12. El texto de seguridad cuenta la lógica interna y deja términos en inglés.**

- Evidencia: 30 registros incluyen frases como «ninguna fija un nivel de riesgo» (`geissospermum-laeve`), «no fija un nivel de riesgo» (`coptis-chinensis`), «sin nivel de preocupación asignado» (`lycium-chinense`) o «esas sustancias no fijan nivel de seguridad por sí solas» (`croton-eluteria`). Es lógica de la pipeline, no un dato de la fuente, y sale en «Precauciones». También quedan categorías en inglés entre comillas: «very strong toxic» (`cascabela-thevetia`, `nerium-oleander`), «strong toxic» (`papaver-somniferum`) y «nontoxic» (`abutilon-theophrasti`, `helianthus-tuberosus`, `valeriana-locusta`).
- Resolución propuesta: aceptar o limpiar con un paso determinista sobre los 30 textos; no es una promesa ni un consejo. Opcional: regla del validador contra «fij» más «nivel» en `safety.text`.

**CR-13. Descripciones con afirmaciones de salud o sin contenido.**

- Evidencia: 41 descripciones dicen «planta medicinal», «medicina tradicional», «propiedades estimulantes/edulcorantes» o «industria farmacéutica» (`agastache-rugosa`, `aloe-vera`, `atractylodes-lancea`, `areca-catechu`, `stevia-rebaudiana`, `mitragyna-speciosa`, …). El prompt pide «sin afirmaciones de salud»; son resúmenes fieles de Wikipedia, no promesas, pero «Especie de planta medicinal de la familia X» no dice qué planta es. Además `hypericum-perforatum` queda con «Especie más abundante de la familia de las hipericáceas.».
- Resolución propuesta: aceptar las 41 y regenerar `hypericum-perforatum` solo si se quiere una descripción útil (el paquete no trae más, así que el resultado sería igual de pobre). Opcional: advertencia del validador para «medicinal».

**CR-14. Nombres: anotaciones de USDA, mayúsculas y expansiones.**

- Evidencia: 28 nombres de 11 registros conservan la anotación de idioma de USDA en el texto, por ejemplo «Oliban (Sp.)» y «Weihrauchbaum (Ger.)» (`boswellia-sacra`), «Zakuro (Jap.)» (`punica-granatum`) y, lo más visible, `displayName` = «Canela de la China (Sp.)» en `cinnamomum-aromaticum`. En otros registros la anotación se quitó (Myrciaria dubia: «Araza de Agua (Sp.)» pasa a «Araza de Agua» y «Camo Camo (Peru)», «Guapuro Blanco (Bol.)» pasan a `es` sin la marca de país ni `idioma-de-nombre-dudoso`). Las mayúsculas se normalizan en unos casos y no en otros: «Majuelos» y «Sábila» y «Brécol» pasan a mayúscula aunque el paquete los trae en minúscula, y el prompt solo lo permite si la forma aparece en el paquete. Tres registros añaden nombres que el paquete no escribe de forma literal pero salen de una enumeración elíptica o de un alias compuesto: `matricaria-chamomilla` («manzanilla dulce» y «manzanilla cimarrona», de «manzanilla de Castilla, manzanilla alemana, dulce o cimarrona»), `vigna-angularis` («alubia adzuki», «judía adzuki» y «frijol adzuki», de «alubia, judía, frijol o poroto adzuki») y `valeriana-officinalis` («hierba de los gatos» y «yerba de los gatos», de «hierba o yerba de los gatos»).
- Resolución propuesta: quitar la anotación del `displayName` de `cinnamomum-aromaticum` regenerando la planta y normalizar los otros 27 nombres con un paso determinista; aceptar las expansiones (son lecturas válidas de la fuente) y la variación de mayúsculas.

**CR-15. Frases de advertencia no literales.** En `datura-metel`, `dermatophyllum-secundiflorum`, `manihot-esculenta` y `thuja-occidentalis` las señales de riesgo se funden en una sola frase (en `datura-metel`: «Advertencias: registrada como veneno en usos tradicionales y como veneno homicida en usos tradicionales.»; en `thuja-occidentalis`: «registrada como abortiva; se registran casos mortales; registrada como veneno», sin «en usos tradicionales»). Significan lo mismo que las frases de `sensitive-activities.json` y llevan todos los refs `usda_use:*`, pero no son las frases de la lista. Resolución: aceptar.

**CR-16. Matices que el paquete no dice del todo.**

- `tilia-cordata`: «no se ha establecido el uso en menores de 4 años (indicación respiratoria) ni en menores de 12 años (indicación de estrés y ánimo)»; el paquete solo dice «Indication 1)» e «Indication 2)». La indicación 1 se apoya en «dyspnoea … purulent sputum» y coincide con la monografía real, pero la 2 se infiere por orden.
- `malus-domestica`: «amigdalina solo en trazas» frente a «but only at low concentrations» del paquete (concentración baja, no trazas).
- `brassica-oleracea-var-italica`: el texto de seguridad enumera los glucosinolatos «tóxicos» y omite el matiz de la misma fuente («the toxic effect is only remarkable after very high consumptions»).
- Resolución propuesta: aceptar (el primero y el tercero tienen respaldo razonable) o ajustar el matiz de `malus-domestica` al regenerar otras correcciones.

**CR-17. Formato de las citas generales.** 26 grupos escriben la cita de `Woi.<n>` como «The Wealth of India raw materials, vol. 8» (`piper-betle`, `plantago-major`, `diospyros-peregrina`), o con la cita completa (`cola-nitida`, clave `Woi.2`), o sin volumen (`alangium-salviifolium`, clave `Woi`), en vez del «The Wealth of India, vol. N» que fija el prompt. Resolución: aceptar (el título más largo es el de la candidata) o normalizar con un paso determinista.

**CR-18. `family` nula en 116 registros.** En los 62 registros de solo género y en otros 54 sin familia en el paquete, `family` es `null`, aunque en 47 la descripción de Wikipedia nombra la familia (por ejemplo `aloe-spp`: «de la familia Asphodelaceae»). El prompt solo permite tomar la familia de `identity.family`, y el paquete no la trae. Resolución: aceptar; si se quiere mostrar, hay que resolverlo en el paquete, no en el registro.

### Observaciones (no son defectos)

- OBS-01. `citrus-x-bergamia`: `oil` (esencial) se apoya en `ema_herbal:citri-bergamiae-aetheroleum`, que es una declaración pública de la EMA («a Community herbal monograph … cannot be established»). Cumple la regla del prompt (ficha `aetheroleum`), y la descripción de Wikipedia menciona el aceite esencial, pero el ref no es el de una monografía. Además no lleva datos de seguridad (flag `sin-datos-de-seguridad`), aunque el aceite de bergamota es conocido por ser fototóxico: el paquete no lo dice y no se puede añadir.
- OBS-02. `conium-maculatum`: sin nombre común en español porque Wikipedia dice «una de las dos cicutas presentes en Europa» (plural genérico). El flag `sin-nombre-comun-es` lo registra. Quien busque «cicuta» no encontrará la planta por nombre; si se busca en la descripción, sí. Aceptar o permitir en el prompt el nombre genérico en plural cuando es el único.
- OBS-03. 1.483 registros (63%) salen sin `safety` y con `sin-datos-de-seguridad`, entre ellos `ephedra-spp` y `aloe-spp`. Es lo que fija la política, pero la app debe presentar `safety: null` como «sin datos», no como «segura». Residual para 10.4.
- OBS-04. `matricaria-chamomilla` conserva «Woi.Syria (sin resolver)» en 15 de sus 20 grupos, cada uno con su flag `cita-sin-resolver`; como todos tienen además otra cita resuelta salen con `pendingReview` falso, como fija el prompt.
- OBS-05. Los paquetes pueden traer artículos de Wikipedia de variedades con el mismo nombre científico: `malus-domestica` trae también el artículo «Milton (manzana)» y un nombre `es` «Milton». El registro eligió bien, pero otro generador podría haber tomado «Milton» como nombre. Origen aguas arriba (filtro de homónimos de Wikidata).
- OBS-06. `geissospermum-laeve`: «Pau pereira» está marcado `en` en USDA y es portugués; el registro lo copia tal cual. Además 80 nombres que el paquete marca `en` pasan a `es` por juicio del agente (por ejemplo «Ayahuasca» y «Yerba mansa»); no encontré ninguno claramente equivocado.

## Patrones

- Lo que se hace bien, verificado en los 2.354 registros: nombres (solo 4 registros tienen nombres que no son literales del paquete y son expansiones de enumeraciones); idioma de los nombres (sin errores claros); `activitySource`, `n`, países y refs de cada grupo (0 diferencias con el paquete); selección de los 20 grupos (440 de 441 correctas); fórmula de enfermedad grave (1.297 grupos de 811 plantas, 101 formas, todas con la fórmula; solo CR-06 es de forma); señales de riesgo (592 grupos de 422 plantas, ninguna en `traditionalUses`, todas en `safety` con sus refs `usda_use:*`); objetivos (idénticos a los `goalCandidates` del paquete, 56 plantas tóxicas sin objetivos con flag); nivel de `safety` (siempre el máximo de las entradas del paquete); coherencia del texto de seguridad con sus refs (TPPT, EFSA, EMA y USDA mencionados si y solo si hay ref); refs inventados (ninguno); citas con candidatas (todas las resueltas son candidatas de su clave, salvo CR-01).
- Patrón 1: los errores de contenido son puntuales y los genera el LLM al parafrasear (CR-02, CR-03, CR-07, CR-16), no un fallo sistemático. El validador no los detecta porque comprueba reglas formales (refs, prefijos, regex de `mg`/`ml`) y no el significado.
- Patrón 2: las reglas ambiguas del prompt producen decisiones distintas según el agente (CR-01 `Nas`, CR-09 traducción, CR-14 mayúsculas y anotaciones, CR-11 origen). Se arreglan mejor con un paso determinista o un glosario que con otra versión del prompt, que reencolaría las 2.354 plantas.
- Patrón 3: las tres decisiones de diseño que el usuario debería confirmar son CR-05 (nivel de seguridad frente a señales letales), OBS-03 (63% sin datos de seguridad) y CR-18 (familia nula).
- Reglas del validador que cerrarían la mayoría de los hallazgos: cantidades con unidad (`µg`, `g`, `kg`, `%`) en el texto visible; la fórmula exacta de la enfermedad grave; cobertura mínima de `traditionalUses`; la candidata de `Nas` según el país; el calificador `(Veterinary)` en las señales; ausencia de anotaciones `(Sp.)` y similares en `displayName` y `commonNames`.

## Qué falta o no se probó

- No revisé a mano las 2.354 plantas: solo las 30 de la muestra; el resto se cubrió con barridos automáticos, que detectan patrones pero no matices de redacción.
- No evalué la calidad de la traducción de los nombres de Wikidata ni de los 1.194 `displayName` científicos por falta de nombre en español (todos llevan `sin-nombre-comun-es`).
- No comprobé contra la fuente original (PDF de la EMA, TPPT, EFSA) fuera de lo que trae el paquete, y no usé la red. Lo que el paquete resume mal queda fuera de este informe.
- No verifiqué cómo muestra la app los textos de `safety`, las citas ni las imágenes (SVG): eso es de la tarea 10.4.

## Cómo re-ejecutar

- Muestra: `python3 openspec/changes/consolidate-catalog-seed/qa/scripts-content-review/select_sample.py` (da el mismo JSON que `evidence-content-review/sample.json` con Python 3.9).
- Vista de una planta: `python3 openspec/changes/consolidate-catalog-seed/qa/scripts-content-review/view_plant.py <id>`.
- Barridos: `python3 openspec/changes/consolidate-catalog-seed/qa/scripts-content-review/global_scans.py --out openspec/changes/consolidate-catalog-seed/qa/evidence-content-review/barridos`. Solo leen `data/seed/plants/` y `data/work/bundles/`, y no necesitan red ni dependencias.
- Validador del proyecto, para confirmar que no detecta los hallazgos: `python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants --bundles data/work/bundles` (2.354 registros, 0 errores, 0 advertencias).
- No se instaló ninguna herramienta ni se agregó ninguna dependencia.
