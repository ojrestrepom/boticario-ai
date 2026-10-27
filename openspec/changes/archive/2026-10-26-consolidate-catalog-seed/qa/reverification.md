# Reverificación de QA: consolidate-catalog-seed

Alcance: comprobar de nuevo los defectos de [`consolidate-catalog-seed-results.md`](consolidate-catalog-seed-results.md) (DEF-01 a DEF-07) y los hallazgos de [`content-review.md`](content-review.md) (CR-01 a CR-18) que se corrigieron después de la QA anterior, y verificar que los que no se corrigieron no empeoraron. Ejecución: 2026-10-26, rama `consolidate-catalog-seed` en `78df6b8`, árbol sin cambios (solo se añadió `qa/evidence-reverification/` y `qa/scripts-reverification/`). La QA anterior corrió sobre `8647a01`; lo que cambió desde entonces: `04f3543` (DEF-02 y DEF-05), `ca3a613` (validador), `6b01eb1` (DEF-03) y `78df6b8` (110 registros regenerados).

## Resumen

- Corregidos y verificados: DEF-02, DEF-03, DEF-05, CR-01, CR-02, CR-03, la fórmula de enfermedad grave malformada (CR-06), las anotaciones de idioma en nombres (parte de CR-14) y «Malasia» frente a «Malesia» (parte de CR-11). Ninguno reaparece en la semilla, en la base ni en la API.
- Sin corregir y sin empeorar, como se esperaba: DEF-01, DEF-04 y DEF-06 (a la espera de la decisión de despliegue), CR-04 y CR-05 (decisiones) y los menores restantes. DEF-07 se corrigió en parte (el README de la herramienta; faltan cuatro lugares).
- Una cifra de DEF-01 sube de 1.023 a 1.285 plantas, pero por un efecto conocido de la corrección de DEF-02 (261 plantas), no por una regresión. Está explicado en DEF-01 más abajo y no cuenta como fallo nuevo.
- Defectos nuevos: ninguno. Hay una observación de documentación (OBS-R1, spec sin actualizar) y otra de tendencia (OBS-R2, grupos sin traducir y citas WOI por las plantas recuperadas).
- Regresión: la base se reconstruye con el mismo hash (`affdf016...3818d`); el validador da 2.354 registros, 0 errores y 0 advertencias; la API cumple el contrato (Newman 17 peticiones y 65 aserciones, 0 fallos; `api_tests.py` 105 pasan, 3 fallan por DEF-01 y DEF-04, 3 observaciones); `flutter analyze` sin problemas, `flutter test` 209 pasan y el smoke falla por DEF-01 igual que antes.

## Estado de cada defecto

| ID | Estado | Evidencia |
| --- | --- | --- |
| DEF-01 (alta) | SIGUE, esperado. El smoke falla igual | `evidence-reverification/app/smoke.txt`, `api/API-07.txt`, `seed/estado-sin-corregir.txt` |
| DEF-02 (media) | CORREGIDO | `api/api-checks.txt`, `seed/DEF-02-db.txt`, `api/API-07.txt` |
| DEF-03 (media) | CORREGIDO. Las 9 sin usos son solo señal de riesgo y tienen precaución | `api/api-checks.txt`, `seed/DEF-03-db.txt` |
| DEF-04 (media) | SIGUE, sin empeorar (355 de 628 sin encontrar, antes 357) | `api/API-03.txt`, `api/API-04.txt` |
| DEF-05 (baja) | CORREGIDO | `api/api-checks.txt`, `api/API-03.txt` |
| DEF-06 (media) | SIGUE, igual (24.568 de 24.568 usos con la etiqueta) | `api/API-07.txt` |
| DEF-07 (baja) | PARCIAL: README de la herramienta corregido; faltan 4 lugares | grep en «DEF-07» |
| CR-01 | CORREGIDO | `seed/CR-01-nas.txt`, `barridos/nas-citas.txt` |
| CR-02 | CORREGIDO | `seed/CR-02-cantidades.txt`, `barridos/cantidades-y-dosis.txt` |
| CR-03 | CORREGIDO | `seed/CR-03-cobertura.txt`, `seed/validador.txt` |
| CR-06 (fórmula) | CORREGIDO | `seed/formula-enfermedad-grave.txt` |
| CR-14 (anotaciones) | CORREGIDO en las anotaciones; mayúsculas y expansiones no se tocaron | `seed/anotaciones-de-idioma.txt` |
| CR-11 (Malesia) | CORREGIDO en «Malasia»; punto final y prefijo no se tocaron | `seed/malesia.txt`, `barridos/origen.txt` |
| CR-04, CR-05 | SIGUEN (decisiones), sin empeorar salvo +1 en CR-05 por una planta recuperada | `seed/estado-sin-corregir.txt` |
| Otros menores | SIGUEN, cifras en «Menores sin corregir» | `barridos/` |

## Casos y resultados

Plan: cada caso repite la comprobación que falló o se señaló, con la misma técnica de la QA anterior (barrido de la semilla y de la base, y peticiones a la API local). Las comprobaciones de la API usan la base nueva `data/build/catalog.db` y un token de prueba generado al ejecutar (no se escribe en ningún archivo; la evidencia lo sustituye por `<token>`).

| Caso | Requisito | Técnica | Resultado |
| --- | --- | --- | --- |
| REV-01 base y semilla | `catalog-ingest` | Reconstruir la base en una carpeta temporal y comparar con `data/build/catalog.db` | PASA. Hash `affdf01687d7aea1a1f0cae8c2b6fd942945609be0898ad53399c193a783818d` en ambas y volcados SQL idénticos |
| REV-02 DEF-02 | `plant-passport`, «Planta sin nombre común»; `catalog-ingest` | Barrido de 2.354 resúmenes y 2.354 detalles, y consulta a la base | PASA. 0 nombres comunes de idioma `la` en la base, 0 en la API; ningún nombre común repite el científico (la única coincidencia por texto es `Centella asiática`, un nombre español legítimo de `centella-asiatica` que solo difiere en el acento) |
| REV-03 DEF-03 | `catalog-seed`, «Sinónimo resuelto» | 26 plantas con usos antes, en la API y en la base | PASA. 17 recuperan usos; 9 siguen en 0 por tener solo señal de riesgo |
| REV-04 DEF-05 | Búsqueda por sinónimo | 7 consultas, los 77 nombres con `×` escritos con `x` y con `×`, y 300 nombres con `x` interna | PASA |
| REV-05 CR-01 | `catalog-seed`, citas | Barrido de la clave `Nas` en toda la semilla, la base y la API | PASA |
| REV-06 CR-02 | Política de contenido: sin cantidades | Barrido de unidades en todo el texto visible de 2.354 registros y en `plant_safety` | PASA |
| REV-07 CR-03 | Cobertura de usos | Los 3 registros, y el mínimo `min(20, grupos del paquete)` en las 2.354 plantas | PASA |
| REV-08 fórmula, anotaciones, Malesia | Política de contenido | Barridos de la semilla | PASA |
| REV-09 validador | `catalog-seed` | `tools/catalog-seed/cli.py validate` | PASA. 2.354 registros, 0 errores, 0 advertencias |
| REV-10 regresión API | Contrato `/v1` | `api_tests.py` y Newman | PASA en contrato; 3 fallas de comportamiento esperadas |
| REV-11 regresión app | `catalog-client`, `plant-passport` | `flutter analyze`, `flutter test`, smoke | PASA analyze y tests; el smoke falla por DEF-01 (esperado) |
| REV-12 regresión del código | Backend y herramientas | `cargo test --workspace`, la prueba `real_catalog` (ignorada por defecto) y 545 pruebas de Python de `tools/catalog-seed` | PASA |
| REV-13 delta de las 110 regeneraciones | Calidad del contenido | Diferencia de campos entre `8647a01` y `HEAD`, barridos y comprobaciones de `cr_lib` | PASA, sin hallazgos nuevos (ver «Las 110 regeneraciones») |

## Verificación por defecto

### DEF-02: corregido

- Base: 0 filas `plant_name` de tipo `common` e idioma `la`. La semilla conserva el `displayName` en latín en 1.194 plantas y `plant_profile.display_name` lo guarda en las 1.194 (`seed/DEF-02-db.txt`).
- API: en los 2.354 resúmenes y en los 2.354 detalles ningún nombre común es de idioma `la` ni repite el nombre científico. El nombre científico de cada planta sigue en sus nombres de tipo `scientific` (`api/api-checks.txt`).
- Plantas sin nombre en español (flag `sin-nombre-comun-es`, 1.194): 624 devuelven solo nombres científicos (ningún nombre común) y 570 conservan nombres comunes reales de otros idiomas, casi todos en inglés (863 nombres: `en` 863, `de` 26, `es` 9, `zh` 2, `und` 2, `pt` 1, `zu` 1). Ejemplos: `eleutherococcus-nodiflorus` devuelve `Wu Chia Pi` (en) y tres científicos; `abutilon-theophrasti` devuelve `Abutilon-Hemp`, `Butterprint`, `Chinesische Samtpappel` y otros. Es lo esperado: eran nombres comunes reales de USDA, no el científico. La búsqueda `abutilon theophrasti` encuentra la planta y su `commonNames` ya no lleva el científico.
- Antes: 625 plantas tenían el científico como único nombre común; ahora hay 624 sin ningún nombre común (la diferencia es `lamium-sp`, que no tenía nombres comunes y tras la regeneración tiene `Ortiga muerta`).

### DEF-03: corregido

- Las 26 plantas con usos antes y 0 después (según `evidence/ids/id-map.tsv`): 17 recuperan usos y 9 siguen en 0.
- Recuperadas, en la API: `chromolaena-odorata` 34 usos (antes 31 bajo `eupatorium-odoratum`), `actaea-cimicifuga` 25 (16), `packera-aurea` 20 (17), `piper-aduncum-var-aduncum` 21 (24), `rostellularia-procumbens` 25 (16), `tanacetum-balsamita-var-balsamitoides` 11 (11), `origanum-creticum` 4 (4), `satureja-cuneifolia` 1 (1), `inocarpus-fagifer` 12 (3, es CR-03) y las de solo género `gossypium-sp` 22 (10), `eucalyptus-sp` 10 (4), `eriocaulon-sp` 8 (8), `erythrina-sp` 8 (8), `mentha-sp` 7 (2), `ocimum-sp` 5 (5), `genista-sp` 1 (1) y `teucrium-sp` 1 (1).
- Siguen en 0 y tienen la señal en precauciones, 9: `actaea-pachypoda`, `dalbergia-nitidula`, `dictamnus-hispanicus`, `duboisia-leichhardtii`, `eucalyptus-cladocalyx`, `hyacinthus-orientalis`, `huperzia-selago` (antes `lycopodium-selago`), `strophanthus-gratus` y `taxus-sp` (solo género). En todas el paquete solo trae señales de riesgo (`Poison`, `Fatality`, `Abortifacient`, `Poison(Arrow)`, `Homicide`), ninguna está en `traditionalUses` y cada `plant_safety.text` termina con la frase «Advertencia: …» con sus refs `usda_use:*` (`seed/DEF-03-db.txt`). Esto aclara la causa que la QA anterior no había determinado para las 9 especies sin fila sin asignar: 8 eran solo señal de riesgo y la novena (`inocarpus-edulis`) era CR-03.
- Cifras globales: plantas sin usos 923 a 898, usos 24.286 a 24.568, grupos 17.526. Ninguna planta cuyo paquete trae usos distintos de señales de riesgo queda sin grupos.
- Límite: la API todavía no sirve `safety`, así que la precaución de estas 9 plantas (por ejemplo «se registran casos mortales» en `dalbergia-nitidula`) está en la base pero no llega a la app hasta el cambio 2.

### DEF-05: corregido

- `mentha x piperita`, `Mentha × piperita`, `mentha×piperita` y `MENTHA X PIPERITA` encuentran `mentha-x-piperita` con total 1; `rosmarinus x lavandulaceus` encuentra `salvia-x-lavandulacea` y `rosmarinus x mendizabalii` encuentra `salvia-x-mendizabalii`.
- Los 77 nombres científicos con `×` se encuentran escribiéndolos con `x` y con `×`. No hay efecto colateral en las `x` internas: 300 nombres con una `x` interna (`Taxus`, `Fraxinus`, `Alexandra`, …) se encuentran por su nombre completo, y `taxus`, `fraxinus` y `alexandra` devuelven en la API las mismas plantas que la base (10, 5 y 1).
- `api_tests.py`: los casos `Mentha x piperita` y `Mentha × piperita` pasan. Los dos que siguen fallando en la búsqueda son `matricaria recutita` y `mentha piperita` (DEF-04).

### CR-01: corregido

- Ninguna cita de la semilla apunta a `usda_reference:NAS` ni a «Lost Crops of the Incas» (0 en citas y en refs de grupo, antes 52 grupos de 16 plantas). Ninguna fila de la base ni uso servido por la API lo cita (`plant_use_group_ref`, `reference` y `plant_use`: 0; los 24.568 usos de las 2.354 plantas, 0).
- Barrido de la clave `Nas` en toda la semilla: 596 grupos resueltos a `usda_reference:NAS2` («Herbal pharmacology in the People's Republic of China», 551 de ellos con filas de China) y 18 sin resolver (9 plantas, todas con `cita-sin-resolver`). Ningún grupo con clave `Nas` tiene un país andino.
- Las 16 plantas señaladas: 15 resuelven todas sus claves `Nas` a `NAS2` (`datura-metel`, `silybum-marianum` y `zea-mays` llevan el flag `cita-sin-resolver` por otras claves, como `Woi.Syria`); `celosia-argentea` queda con 1 grupo en `NAS2` y 1 con la clave `Nas` sin resolver. Antes, 17 grupos de 8 plantas quedaban sin resolver; ahora 18 de 9 (`celosia-argentea` se suma). Es aceptable: la propuesta de la QA anterior admitía dejarlos sin resolver, con el flag.

### CR-02: corregido

- Ninguna cantidad ni unidad en el texto visible de las 2.354 plantas (descripción, origen, seguridad, nombres, objetivos, actividades, partes y mensajes de flags), con una expresión más amplia que la anterior (`µg`, `mg`, `g`, `kg`, `ml`, `%`, `ppm`, `/kg`, `dosis`, `posología`, `diario`, `tazas`, …): 0 coincidencias (antes 2 registros). La base: `plant_safety.text` con 0 coincidencias.
- `foeniculum-vulgare` y `foeniculum-vulgare-var-dulce` dicen ahora «el uso no está recomendado por falta de datos adecuados y por la ingesta de estragol», sin la cifra. Es una edad, no una dosis, y la EMA así lo registra.

### CR-03: corregido

- `inocarpus-fagifer`: 12 grupos (paquete 12); `inga-edulis`: 2 (paquete 2); `heimia-salicifolia`: 20 (paquete 21, tope 20). En la API sirven 12, 2 y 33 usos.
- Ninguna de las 2.354 plantas tiene menos grupos que `min(20, grupos del paquete que no son señales de riesgo)`. El validador: «2354 registros, 0 con errores, 0 errores, 0 advertencias» (`seed/validador.txt`).

### Fórmula, anotaciones y Malesia: corregido

- Fórmula: las 5 actividades de `bursera-simaruba` (2), `byrsonima-crassifolia`, `caesalpinia-pulcherrima` y `cajanus-cajan` quedaron como «Uso tradicional, sin eficacia demostrada: fiebre amarilla», etc. Los 1.309 grupos de enfermedad grave de la semilla (antes 1.297) llevan el prefijo exacto, un espacio, una letra y ninguna comilla.
- Anotaciones: 0 nombres con «(Sp.)», «(Ger.)», «(Fr.)», «(Jap.)», «(Peru)», etc. (antes 28 de 11 registros). `cinnamomum-aromaticum` tiene `displayName` «Canela de la China». Quedan dos nombres con paréntesis que no son anotaciones de idioma: `Goldmohn (Schlafmuetzchen)` en `eschscholzia-californica` y `Liane chasseur (=chaser vine)` en `davilla-sp`; son variantes de la fuente, no una marca de idioma.
- Malesia: 0 orígenes con «Malasia» (antes 48) y 216 con «Malesia». `ocimum-tenuiflorum` dice «Australia, China, Asia oriental, subcontinente indio, Indochina, Malesia, Papuasia y el Pacífico noroccidental y suroccidental», sin «Asia tropical y oriental». «Malasia» aparece solo en 6 descripciones (`coix-lacryma-jobi`, `dillenia-indica`, `diospyros-blancoi`, `kleinhovia-hospita`, `myristica-fragrans`, `pongamia-pinnata`) y como país de uso en 55 grupos, todos referidos al país: legítimo.

## Sin corregir: estado

### DEF-01 (alta): sigue, esperado

- El smoke falla en el mismo punto y por la misma causa: «Found 0 widgets with text "English Lavender"», `catalog_smoke.dart:778` (`evidence-reverification/app/smoke.txt`, comparable con `evidence/app/smoke-original-fails.txt`). No hay error de red, de autenticación ni de carga: no cuenta como fallo nuevo.
- La API sigue ordenando los nombres por texto y la app usa el primero. Plantas con nombre común cuyo primero no es el nombre para mostrar: 1.285 de 1.730 (antes 1.023 de 2.354).
- El aumento de 262 viene de la corrección de DEF-02, no de una regresión: el `displayName` en latín ya no está entre los nombres comunes, y en 261 de las 570 plantas con nombre en latín y nombres de otros idiomas el nombre en latín quedaba primero por orden de texto (la app mostraba el científico, duplicado). Ahora la app mostrará el primer nombre común real, normalmente en inglés (`abutilon-theophrasti` se mostraría como «Abutilon-Hemp»). Es lo que dice `catalog-client` («primer nombre común, en el idioma que venga»), así que cumple su spec; la raíz sigue siendo la de DEF-01 y se resuelve con la misma decisión (nombre para mostrar primero o `displayName` en la API). Entre las plantas con `displayName` en español, 715 de 1.160 no coinciden con su primer nombre común, que es el defecto original.

### DEF-04 (media): sigue, sin empeorar

- `q=matricaria recutita` y `q=mentha piperita` siguen devolviendo 0 resultados.
- Nombres científicos anteriores de los 628 IDs que pasaron a alias: 273 encuentran la planta nueva y 355 no (antes 271 y 357). Los 2 que mejoraron son los que tenían `x` (`Rosmarinus x lavandulaceus`, `Rosmarinus x mendizabalii`): los 264 nombres que la planta lista como sinónimo ahora se encuentran todos (antes 262). Los no encontrados: 181 heterotípicos, 135 aceptados de USDA y 39 homotípicos.

### DEF-06 (media): sigue, igual

- Los 24.568 usos devuelven `reference.citation` con la etiqueta «USDA Dr. Duke: referencia …» (38 referencias distintas). Contrato HTTP sin cambios.

### DEF-07 (baja): parcial

- Corregido en `tools/catalog-seed/README.md`: ahora dice 1.747 conservados, 628 alias y 1 ausente, y 629 IDs distintos.
- Siguen con «unos 500»: `docs/data/modelo-de-datos.md:240`, `proposal.md:17`, `design.md:132` y `design.md:246`. La propuesta y el diseño siguen hablando de unas 2.411 plantas (`proposal.md:18`, `design.md:219`). El README de la herramienta dice 2.355 en la fila «Plantas» (con la ausente; la semilla tiene 2.354).
- La traducción de actividades: ver CR-09 más abajo.

### Decisiones: CR-04 y CR-05

- CR-04: `brassica-cretica-subsp-cretica` sigue con `displayName` «Coliflor» y los flags `backbones-discrepan` y `conflicto-entre-fuentes`.
- CR-05: 57 plantas con señal letal en USDA (antes 56): 13 con nivel alto, 16 medio y 28 sin nivel (antes 27). La planta de más es `taxus-sp` (`Homicide` y `Poison`, sin nivel), recuperada por la corrección de DEF-03; el motivo es el mismo y no cuenta como fallo nuevo.

### Menores sin corregir

| ID | Antes | Ahora | Nota |
| --- | --- | --- | --- |
| CR-07 veterinaria | 5 plantas | 5 | Sin cambios |
| CR-08 envoltorios `Preventitive`, `Antimalaria` | 2 plantas | no se volvió a medir | `actaea-spicata`, `eucalyptus-globulus` no están entre los 110 regenerados |
| CR-09 actividades sin traducir | 178 grupos en 154 registros | 182 grupos en 159 registros | Sube por plantas recuperadas (por ejemplo `Gravel` 20 a 24); 1.056 de 17.526 grupos con actividad igual a la original (antes 1.033 de 17.276) |
| CR-10 autores de imagen | 68 registros con ruido | sin cambios | El barrido da las mismas líneas |
| CR-11 punto final y prefijo del origen | 1.322 con punto, 875 sin | 1.328 con punto, 869 sin | Prefijos: 529 «Nativa de», 238 «Nativa del», 8 «Región nativa:» |
| CR-12 lógica interna en `safety.text` | 30 textos | 29 | Mejora ligera por la regeneración |
| CR-13 descripciones con afirmaciones de salud | 41 | 40 | |
| CR-14 mayúsculas y expansiones | 3 registros | no se volvió a medir | Solo se verificaron las anotaciones |
| CR-15, CR-16 | | no se volvió a medir | |
| CR-17 formato de cita `Woi` | 26 grupos | 36 grupos | Suben por plantas recuperadas (`actaea-cimicifuga` 9, `gossypium-sp` 1); `plantago-major` y `schleichera-oleosa` ya no |
| CR-18 `family` nula | 116 | 116 | |
| OBS-03 sin `safety` | 1.483 | 1.481 | |

## Las 110 regeneraciones

- Campos que cambiaron entre `8647a01` y `HEAD` (110 registros): `origin` 89, `traditionalUses` 83, `reviewFlags` 79, `description` 54, `refs` 52, `commonNames` 46, `safety` 37, `bundleHash` 28, `displayName` 12, `sources` 11, y menos de 6 en `oil`, `goals`, `scientificName` y `partsUsed` (`seed/delta-semilla-8647a01-HEAD.txt`). Los cambios fuera de los que se pidieron (descripción, objetivos, nombre para mostrar) son los de una regeneración con un modelo no determinista.
- Los niveles de `safety` no cambiaron en ningún registro; `gossypium-sp` y `taxus-sp` pasan de no tener `safety` a tenerlo (la señal de riesgo recuperada). Los 5 registros con `goals` distinto solo reordenan o cambian la frase de evidencia; los objetivos de `foeniculum-vulgare` coinciden con los candidatos del paquete.
- Todos los nombres de los 110 registros están literalmente en su paquete (salvo la anotación de idioma retirada). Ninguna coincidencia nueva de dosis, cantidades ni promesas de eficacia (las 5 menciones de «recomendado» o «se debe» son advertencias de la EMA citadas como tales).
- Cambios de `displayName` que se revisaron: `lamium-sp` pasa de `Lamium sp` (la) a «Ortiga muerta» (es, Wikipedia); `ocimum-tenuiflorum` de «Tulsí» a «Albahaca sagrada»; `ziziphus-mauritiana` de «Ciruela india» a «Ponsigué»; `piper-aduncum-var-aduncum` de «Matico» (es) a su nombre científico, porque USDA marca «Matico» como inglés (el flag `idioma-de-nombre-dudoso` lo dice y el nombre se conserva como común). Son decisiones válidas, con ref del paquete.
- Dos registros cambian la ref de `scientificName` de `wikidata:*` a `usda_part:*` (`amaranthus-sp`, `teucrium-sp`), coherente con el flag `wikidata-sin-item`.
- `cr_lib.check` (la comprobación automática de la tarea 10.5) sobre los 110 registros: sin errores de estructura, de `activitySource`, de `n`, de refs ni de nivel. Marca 7 nombres con idioma `es` donde el paquete dice `en` (`Nance`, `Gotu Kola`, `Taro`, `Sinicuichi`, `Guaba`, `Moringa`, `tulsí`; es el juicio del agente de OBS-06 y los flags lo registran), la clave `Nas` sin resolver de `celosia-argentea` (con el flag), 2 autores de imagen con ruido (`hydnocarpus-kurzii`, `tanacetum-balsamita-var-balsamitoides`, de CR-10) y 1 falso positivo (`paeonia-lactiflora` sin `safety`: su paquete solo trae declaraciones públicas de la EMA sin datos de seguridad).

## Defectos nuevos

Ninguno.

## Observaciones nuevas

- OBS-R1 (baja): el escenario «Nombre para mostrar explícito» de `specs/catalog-ingest/spec.md:16` dice que la base guarda el `displayName` «también como nombre común». La corrección de DEF-02 hace una excepción (un `displayName` de idioma `la` solo va al perfil) y la spec delta no la menciona. Propuesta: añadir la excepción al escenario cuando se actualicen las specs.
- OBS-R2 (informativa): las plantas recuperadas por DEF-03 aumentan en cifras absolutas los grupos sin traducir (CR-09) y las citas `Woi` con formato distinto (CR-17). No es una regresión, y se arregla con el glosario y el paso determinista que ya propone `content-review.md`.
- OBS-R3 (informativa): `inocarpus-fagifer` pasó de 3 a 12 usos y `heimia-salicifolia` tiene 20 grupos de 21 del paquete (el tope es 20); ambos son lo que fija la política.

## Cobertura y riesgos residuales

- No se probó en Android ni en un dispositivo (igual que antes): el smoke y `flutter test` corren en el entorno de host.
- La imagen Docker no se reconstruyó: solo la construcción nativa, con el hash indicado. La tarea 11.5 ya registra el hash de la imagen.
- No se probó contra Cloud Run ni el workflow de despliegue.
- El contenido de las 110 regeneraciones se comprobó con barridos y comparaciones automáticas, y con lectura de los cambios de identidad y nombre; no se releyeron las 110 a mano ni se rehizo la muestra de 30 de la tarea 10.5.
- `safety`, `origin` y `description` aún no se sirven por la API; su corrección se verificó en la semilla y en la base, no por HTTP.
- Docker, GCP y GitHub no se usaron.

## Cómo re-ejecutar

- Compilar fuera del repo (desde `backend/`): `CARGO_TARGET_DIR=<tmp>/target cargo build --release -p catalog-api -p catalog-ingest`. Reconstruir y comparar: `<tmp>/target/release/catalog-ingest build --out <tmp>/rebuilt.db` (hash en la línea `hash:`).
- Todo junto: `openspec/changes/consolidate-catalog-seed/qa/scripts-reverification/run_reverification.sh <tmp>/target/release/catalog-api`. Genera un token al vuelo, arranca la API en `127.0.0.1:8080`, corre `seed_checks.py`, `api_checks.py`, `scripts/api_tests.py`, Newman y las pruebas de la app, y detiene la API al terminar. Necesita `data/work/bundles` (local, no se versiona).
- Por partes: `python3 -I qa/scripts-reverification/seed_checks.py . qa/evidence-reverification/seed qa/evidence/ids/id-map.tsv`; `python3 -I qa/scripts-reverification/delta_seed.py . 8647a01`; con la API arrancada y `QA_TOKEN`, `QA_DB` y `QA_OLD_MAP` definidos, `python3 -I qa/scripts-reverification/api_checks.py . qa/evidence-reverification/api`.
- Código: `cargo test --workspace` (desde `backend/`), `cargo test -p catalog-api --test real_catalog -- --ignored`, `python3 -B -m unittest discover -s tools/catalog-seed/tests` y, en `app/`, `flutter analyze` y `flutter test`.
- Herramientas instaladas: ninguna en el proyecto. Newman 6.2.1 viene de la caché de `npx`; el binario de la API y `catalog-ingest` se compilaron fuera del repositorio. `backend/target` no se tocó.
