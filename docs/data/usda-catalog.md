# Fuente USDA en la semilla del catálogo

Esta guía documenta la fuente USDA Dr. Duke's Phytochemical and Ethnobotanical Databases tal como la usa la semilla consolidada del catálogo (`data/seed/`): de dónde sale, qué datos aporta, qué límites tienen y cómo se asignan sus usos a las plantas. No es una afirmación sobre la vigencia taxonómica o clínica de los datos de la fuente. Las demás fuentes y sus licencias están en [fuentes y licencias](fuentes-y-licencias.md); cómo se arma la semilla y cómo se convierte en `catalog.db` está en el [modelo de datos](modelo-de-datos.md).

USDA ya no se convierte en `catalog.db` por un adaptador del backend. Ahora es una de las fuentes que alimentan los paquetes por planta de las herramientas (`tools/catalog-seed/`), y un LLM consolida esos paquetes en un registro por planta que el backend solo lee.

## Procedencia

- Dataset archivado: [USDA Dr. Duke's Phytochemical and Ethnobotanical Databases, Ag Data Commons, artículo 24660351, versión 1](https://agdatacommons.nal.usda.gov/articles/dataset/Dr_Duke_s_Phytochemical_and_Ethnobotanical_Databases/24660351).
- Archivo original: [`Duke-Source-CSV.zip`, file ID 43363335](https://ndownloader.figshare.com/files/43363335) (6.033.990 bytes; MD5 `45ae44a0544586b8ac22a232beaac344`). La ficha de API del artículo es [v2](https://api.figshare.com/v2/articles/24660351).
- Licencia declarada por USDA: [CC0](https://phytochem.nal.usda.gov/about).
- Cita registrada por la API de Figshare: Duke, James A. (2016). *Dr. Duke's Phytochemical and Ethnobotanical Databases*. Ag Data Commons. Dataset. <https://doi.org/10.15482/USDA.ADC/1239279>. Es la atribución que lleva la fuente `usda` en `tools/catalog-seed/sources.json` y en el manifiesto de la semilla.
- La página [About de USDA](https://phytochem.nal.usda.gov/about) recomienda citar el recurso como 1992–2016. Ese rango pertenece a la recomendación de cita de USDA, no al texto de cita de la API del artículo; tampoco establece la cobertura temporal efectiva de este ZIP, que no fue determinada.
- Verificación: `python3 -I tools/catalog-seed/cli.py download --source usda` descarga el ZIP a `data/.cache/usda/` solo si coincide con el tamaño y el MD5 de `sources.json`. La caché está ignorada por Git y no va en la imagen de Docker.

El identificador de planta de la fuente es `FNFNUM`; no se expande el acrónimo FNF, cuyo significado no se verificó, ni se presenta como identificador universal. El texto científico (`TAXON`) y los nombres comunes de la fuente se conservan literalmente en los paquetes. Los textos que ve el usuario (actividades, nombres comunes mostrados) los consolida el LLM en español y siempre conservan el original: `activitySource` guarda la etiqueta de USDA tal cual.

## Qué aporta

`python3 -I tools/catalog-seed/cli.py extract --source usda` vuelca el ZIP, sin red, a `data/work/sources.db` con estas filas (cifras de la extracción de referencia):

| Dato | Tabla de origen | Filas |
| --- | --- | --- |
| Plantas (`usda_taxon`) | `FNFTAX` | 2.376 |
| Nombres comunes (`usda_common_name`) | `COMMON_NAMES` | 2.920 |
| Partes con compuestos (`usda_part`) | `FARMACY_NEW` cruzada con `PARTS` por `PPCO` | 6.740 |
| Usos (`usda_use`) | `ETHNOBOT` | 82.873 |
| Referencias (`usda_reference`) | `REFERENCES` | 2.043 |

Los nombres comunes de USDA no declaran idioma: un nombre que termina en una etiqueta entre paréntesis (`Rumberry (Eng.)`) se marca `und` y el resto `en`, y el texto nunca se modifica. Las actividades de `ETHNOBOT` están en inglés.

## Límites de los datos

- `FARMACY_NEW` es un registro fitoquímico por planta y parte; no respalda por sí mismo eficacia o propiedad medicinal. Sus nombres de parte como `Essential Oil` no crean una ficha de aceite por sí solos. Para el aceite, el compuesto `EO` y sus variantes cuentan como indicio de aceite esencial (`hasEo`), y si el registro se apoya solo en ese indicio lleva el `reviewFlag` `aceite-por-compuesto-eo`.
- Cada uso es una fila de `ETHNOBOT` con `GENUS`, `SPECIES`, `TAXON`, `ACTIVITY`, `REFERENCE` y `ETHNO`. Son, como máximo, registros tradicionales atribuidos por esa base; no son consejo, dosis, recomendación ni evidencia clínica. Las herramientas no incorporan dosis y el validador avisa de expresiones de dosis o eficacia en los textos visibles.
- Las actividades sensibles tienen un trato especial (`tools/catalog-seed/sensitive-activities.json`). Una enfermedad grave como el cáncer se redacta «Uso tradicional, sin eficacia demostrada: cáncer de mama» y conserva el original en `activitySource`. Una señal de riesgo como `Poison` o `Abortifacient` no se publica como uso: pasa a `safety` como advertencia.
- `ETHNOBOT` no tiene `FNFNUM`: solo trae el nombre (`TAXON`) y el autor (`TAXAUTHOR`). Por eso la asignación a plantas depende de la resolución de nombres (véase la sección siguiente).
- El `LONGREF` propio de `ETHNOBOT` está vacío en todas las filas, y la cita completa solo existe en `REFERENCES`. Del total de filas, 31.629 (38 %, 899 claves distintas) citan una clave `REFERENCE` que no coincide exactamente con ninguna de las 2.043 de `REFERENCES`: unas 6.055 solo difieren en formato (`Burkill,1966` frente a `Burkill, 1966`), 9.576 son `Woi.<n>` (existe `WOI`, «The Wealth of India»), 10.992 son `Eb<vol>:<pág>` (existe `EB`, «Economic Botany»), 3.040 son `Woi.Syria`, de obra poco clara, y 1.966 son otras.
- El flujo anterior descartaba esas filas. Ahora el paquete de cada planta suma, por clave corta, hasta 5 referencias candidatas (la exacta, las de clave normalizada igual y las que comparten el prefijo alfabético) y el LLM decide a cuál corresponde cada clave. Si ninguna corresponde, la cita queda como «(sin resolver)» junto a la clave con un `reviewFlag` `cita-sin-resolver`. Se espera que queden sin resolver unas 5.000 filas (6 %).
- Un grupo de usos sin ninguna cita resuelta queda con `pendingReview` verdadero: se guarda en la semilla y en `plant_use_group`, pero no genera filas en `plant_use` y la API no lo sirve. Un grupo con al menos una cita resuelta se muestra aunque conserve claves «(sin resolver)». La revisión humana de los pendientes queda fuera de alcance.
- Que una planta no tenga usos de USDA no significa que carezca de usos: significa que ninguna fila de `ETHNOBOT` se asignó a ella con este criterio.

## Cruce de usos por sinónimos resueltos

Antes, los usos se cruzaban de forma exacta por `GENUS`, `SPECIES` y `TAXON`, y una fila registrada bajo un sinónimo se perdía. La asignación actual (`catalog_seed/usda_assign.py`) usa la resolución taxonómica:

1. Los nombres comunes y las partes traen `FNFNUM` y se asignan por la entrada `usda:<FNFNUM>` del universo de plantas.
2. Las filas de uso se asignan con la resolución de `TAXON` y `TAXAUTHOR` a un nombre aceptado de WCVP (con WFO como respaldo). Cada par distinto se resuelve una sola vez. Una fila bajo un sinónimo (*Matricaria recutita*) llega a la planta del aceptado (*Matricaria chamomilla*), y una fila bajo un sinónimo heterotípico fusionado por la regla de colisiones llega a la planta en la que se fusionó.
3. Una fila que no se asigna queda registrada con su motivo (`sin-resolver`, `fuera-del-universo`, `sin-asignar` o `fnfnum-sin-planta`) y no entra en ningún paquete.
4. Cada fila asignada conserva su ref `usda_use:<ETHNO>`, y las citas candidatas conservan `usda_reference:<REFERENCE>`, de modo que cada dato del registro final cita la fila de USDA de la que sale.

Resultado medido con los datos reales (universo de 2.355 plantas, tarea 3.2 de `consolidate-catalog-seed`):

| Cifra | Valor |
| --- | --- |
| Filas de uso | 82.873 en 13.899 pares (`TAXON`, `TAXAUTHOR`) |
| Filas de uso asignadas a una planta | 35.935 |
| Filas de uso sin asignar | 46.938, de las cuales 42.635 resuelven a una especie fuera del universo y 4.272 no resuelven |
| Plantas con datos de USDA | 2.316 |
| Manzanilla (`matricaria-chamomilla`) | de 0 a 91 usos (0 con el cruce exacto) |
| Menta (`mentha-x-piperita`) | de 0 a 49 usos (0 con el cruce exacto) |

Antes del cambio, 1.196 de las 2.376 plantas (50 %) no tenían ningún uso en `catalog.db`. Las cifras de arriba son filas de USDA asignadas por planta, no los usos que sirve la API: tras la consolidación, los usos pasan a ser grupos por actividad en español, y los grupos pendientes de revisión no se sirven.

La identidad también cambia. El ID de una planta ya no es el slug del `TAXON` de USDA sino el del nombre aceptado en WCVP, fijo en la semilla; el slug del `TAXON` anterior queda como alias en `plant_alias` (por ejemplo `matricaria-recutita` para `matricaria-chamomilla`). Los detalles de la resolución, la regla de colisiones y los números por planta están en el [README de las herramientas](../../tools/catalog-seed/README.md).
