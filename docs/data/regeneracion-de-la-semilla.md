# Regeneración incremental, versiones y reviewFlags

Esta guía describe cómo se regenera la semilla del catálogo (`data/seed/`) cuando algo cambia, qué versiones se guardan en cada registro y qué significan los `reviewFlags`. Es el complemento de operación del [modelo de datos](modelo-de-datos.md); el detalle de cada comando está en el [README de las herramientas](../../tools/catalog-seed/README.md), en las secciones «Plan de regeneración», «Sellado y manifiesto» y «Validador».

El LLM no corre en `catalog-ingest build` ni en CI: solo se usa al consolidar, de forma incremental, y su resultado queda versionado en la semilla. Por eso la reproducibilidad vive en la semilla y no en el modelo: dos ejecuciones del LLM pueden dar textos distintos para la misma planta.

## Qué se versiona en cada registro

Cada registro `data/seed/plants/<id>.json` guarda con qué se generó:

| Campo | Qué es | De dónde sale |
| --- | --- | --- |
| `bundleHash` | `sha256:` del JSON canónico del paquete de la planta, sin el propio `bundleHash` | `bundles` (`catalog_seed/bundles.py`) |
| `promptVersion` | Entero de la línea `prompt-version: <n>` del prompt (hoy 7) | `tools/catalog-seed/prompt/consolidate.md` |
| `recordVersion` | Versión del esquema del registro (hoy 1) | `x-recordVersion` de `tools/catalog-seed/schema/record.schema.json` |
| `model` | Nombre del modelo que generó el registro (por ejemplo `claude-sonnet-5-5`) | Lo escribe el consolidador |

El manifiesto (`data/seed/manifest.json`) resume la semilla: `promptVersion` y `recordVersion` vigentes, `models` (los modelos distintos de los registros, ordenados; puede haber más de uno si se regeneró por tandas), `plantCount`, el conteo de `reviewFlags` por código, las fuentes con su versión y checksum, y el `seedHash`.

No confundir `recordVersion` (el esquema del registro de la semilla) con `SCHEMA_VERSION` (el esquema de `catalog.db`, hoy 2): son versiones distintas y el cambio de una no implica el de la otra. El backend solo acepta `recordVersion` 1 y `formatVersion` 1 del manifiesto.

### Paquete y `bundleHash`

El paquete es la entrada del LLM para una planta: identidad, secciones por fuente (usos y citas candidatas, regulatorio de la EMA, seguridad, imágenes, descripciones) y el diccionario de refs. Se arma sin red con una función pura del contenido de `data/.cache/` y `data/work/` y se escribe en `data/work/bundles/`, que no se versiona. Lo que se versiona es el registro, que guarda el `bundleHash` del paquete con el que se generó.

Un cambio en una fuente, en el universo de plantas o en la lista de fuentes activas cambia el `bundleHash` solo de las plantas cuyo paquete se ve afectado. La caché es local: otra máquina u otra fecha puede dar otros paquetes de Wikidata, Wikipedia, Commons o la EMA, que cambian con el tiempo. Eso es parte del diseño incremental (cambia el hash y se regenera esa planta); no se promete reproducir la semilla exacta desde cero.

## El plan de regeneración

`plan` compara los paquetes con los registros y lista las plantas que hay que volver a generar:

```sh
python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed
python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed --json
```

Una planta entra en el plan si cumple alguno de estos motivos (se imprimen junto al `id`):

| Motivo | Cuándo |
| --- | --- |
| `sin-registro` | No existe `<seed>/plants/<id>.json` para el `id` propuesto por el paquete |
| `registro-ilegible` | El registro existe pero no es JSON válido (cuenta como ausente) |
| `bundleHash` | El `bundleHash` del registro es distinto del del paquete actual |
| `promptVersion` | La `promptVersion` del registro es distinta de la del prompt vigente |
| `recordVersion` | La `recordVersion` del registro es distinta de la del esquema vigente |

Con `--json` el plan sale como JSON, con `id`, `plantKey` y `reasons` por planta, ordenado por `id`. Sin cambios imprime «0 plantas a regenerar». Las opciones `--prompt` y `--schema` cambian el prompt y el esquema con los que se comparan (útiles en pruebas).

El plan no compara el campo `model`: cambiar de modelo, por sí solo, no pone ninguna planta en cola. Si se quiere regenerar con otro modelo, hay que subir `prompt-version` (que pone todas en cola) o regenerar las plantas elegidas a mano.

Qué hace cada cambio:

- Un cambio de una fuente que altera un solo paquete deja solo esa planta en el plan, con el motivo `bundleHash`.
- Subir `prompt-version` pone todas las plantas en cola (`promptVersion`). Cada cambio de reglas del prompt, y de las listas que el prompt lee (`sensitive-activities.json`, `flag-codes.json`, `safety-map.json`, `goals-map.json`), se acompaña de esa subida. Una prueba comprueba que el prompt lista exactamente los códigos de `flag-codes.json`.
- Subir `x-recordVersion` del esquema pone todas en cola (`recordVersion`) y exige también que el lector de Rust acepte la nueva versión.
- Desactivar una fuente (`"enabled": false` en `sources.json`) cambia el `bundleHash` de las plantas que la usaban, y `plan` regenera solo esas.

## Flujo para regenerar

1. Actualizar los insumos y los paquetes: `download`, `extract`, `resolve`, `wiki-fetch`, `wiki-assign` y `bundles`. El orden completo, con lo que lee y escribe cada paso, está en «Tubería completa, en orden» del README de las herramientas.
2. `plan`: ver qué plantas se regeneran y por qué.
3. Consolidar esas plantas con el prompt y el esquema vigentes (un paquete por planta, un registro por planta en un directorio de trabajo, por ejemplo `data/work/control/v7/lote-1/`). El modo de ejecución de la generación completa (agentes de Claude Code por lotes, un script con la API de Anthropic o lotes manuales) es una decisión del usuario pendiente en la tarea 11.1 del cambio; las herramientas no abren la red del modelo.
4. `validate --records <directorio de trabajo> --bundles data/work/bundles`: errores y advertencias por planta; termina con código 1 si hay algún error.
5. `seal --seed data/seed --from <directorio de trabajo>`: importa los registros válidos (todo o nada), comprueba que su `promptVersion` es la vigente, reescribe cada registro con formato estable y escribe `manifest.json` con el `seedHash`.
6. `plan` debe dar «0 plantas a regenerar» y `validate --records data/seed/plants` cero errores.
7. Reconstruir: `catalog-ingest build` lee la semilla, verifica el `seedHash` y escribe `catalog.db`, sin red ni LLM.

El mismo plan y el mismo validador sirven para cualquier modo de ejecución del LLM. Un lote se reintenta solo si el validador reporta errores.

La guía para generar con agentes de Claude Code, con el script del workflow, está en [`tools/catalog-seed/generation/README.md`](../../tools/catalog-seed/generation/README.md).

## Versionado del prompt y del modelo

- `prompt/consolidate.md` es el prompt autocontenido de la variante A: el LLM solo elige, traduce y resume lo que está en el paquete, y cada campo cita refs del paquete. Su línea `prompt-version: <n>` es la que cada registro guarda en `promptVersion`.
- Historial de versiones, de la 1 a la 7: la 2 lo alinea con el paquete real; la 3 y la 4 aplican la revisión de la corrida de control (fuentes del nombre mostrado, catálogo cerrado de códigos, formato de citas, actividades sin traducción segura); la 5 muestra los grupos de uso con al menos una cita resuelta y admite `safety` sin nivel; la 6 incorpora las actividades sensibles; la 7 reordena la regla de `displayName` y añade el código `aceite-por-compuesto-eo`. El detalle está en «Prompt de consolidación» del README de las herramientas.
- El modelo de los 20 registros de la semilla provisional es `claude-sonnet-5-5`, y el manifiesto lo lista en `models`.
- La semilla provisional (20 registros de la corrida de control, prompt 7) no se publica: el `push` a `main` despliega. La generación completa es la última tarea del cambio.
- Un registro con una versión de prompt anterior a la vigente no se puede sellar: `seal` falla y pide regenerar antes.

## reviewFlags

Un `reviewFlag` es un objeto `{code, target, message}` del registro. El `code` va en minúsculas con guiones, el `target` es el campo o el elemento afectado (`scientificName`, `goals.relajacion-estres`, `traditionalUses[2]`) y el `message` explica el caso. Los flags no son cadenas sueltas. Se guardan en la semilla, el manifiesto cuenta cuántas plantas tiene cada código, y `catalog.db` los guarda en `plant_review_flag (plant_id, code, target, message)`.

El catálogo cerrado está en `tools/catalog-seed/flag-codes.json`, que leen el validador (un código fuera del catálogo es una advertencia, no un error) y la prueba que lo compara con el prompt. El origen `paquete` indica que el flag viene en el paquete y el consolidador lo copia; `registro` indica que lo escribe el consolidador.

| Código | Origen | Target | Significado |
| --- | --- | --- | --- |
| `identidad-ambigua` | paquete | `scientificName` | El nombre es un homónimo que el backbone no resuelve; la planta conserva la identidad de la fuente. |
| `solo-genero` | paquete | `scientificName` | La entrada solo nombra el género. |
| `sin-resolucion` | paquete | `scientificName` | El nombre no resuelve a un aceptado en ningún backbone. |
| `respaldo-wfo` | paquete | `scientificName` | El aceptado viene del respaldo de WFO, no de WCVP. |
| `coincidencia-aproximada` | paquete | `scientificName` | El nombre resolvió por coincidencia aproximada (errata probable). |
| `aceptado-superior-a-especie` | paquete | `scientificName` | El aceptado es de rango superior a especie; la planta conserva el nombre de la fuente. |
| `variante-ortografica` | paquete | `scientificName` | El nombre resolvió por una variante ortográfica del epíteto. |
| `backbones-discrepan` | paquete | `scientificName` | WCVP y WFO discrepan en el aceptado; se conserva el de WCVP. |
| `grupo-partido` | paquete | `scientificName` | El aceptado lo comparten plantas heterotípicas; esta es una de las separadas. |
| `fusion-heterotipica` | paquete | `scientificName` | Se fusionaron sinónimos heterotípicos sin artículo propio en Wikipedia en español; requiere revisión humana. |
| `filas-sin-asignar` | paquete | `scientificName` | Hay filas del grupo que no se pudieron asignar a ninguna planta. |
| `wikidata-sin-respuesta` | paquete | `wikidata` | Wikidata no respondió para esta planta o está desactivada. |
| `wikidata-sin-item` | paquete | `wikidata` | Wikidata respondió, pero ningún ítem pasa el filtro de homónimos. |
| `wikidata-no-consultada` | paquete | `wikidata` | La planta no tiene nombre aceptado, así que no se consultó Wikidata. |
| `extraccion-seguridad-fallida` | paquete | `safety` | La extracción de los PDF de la EMA falló para esta planta. |
| `cita-sin-resolver` | registro | `traditionalUses[<índice>]` | Un grupo de usos tiene una clave de cita sin candidata en el paquete; el flag se registra aunque el grupo se muestre (queda pendiente solo si ninguna de sus citas se resolvió). |
| `interacciones-graves-estres` | registro | `goals.relajacion-estres` | La EMA registra interacciones graves y el área de estrés y ánimo; el objetivo queda pendiente de revisión. |
| `sin-datos-de-seguridad` | registro | `safety` | El paquete no trae ninguna información de seguridad (`safety` es nulo); la planta no se presenta como segura. |
| `objetivos-omitidos-por-toxicidad` | registro | `goals` | TPPT marca la planta como muy tóxica o tóxica fuerte y se omiten los objetivos que la EMA le asigna. |
| `sin-nombre-comun-es` | registro | `displayName` | El paquete no trae ningún nombre común en español; el nombre mostrado es el científico. |
| `idioma-de-nombre-dudoso` | registro | `commonNames` | No es seguro que un nombre del paquete sea español o de otro idioma. |
| `aceite-por-compuesto-eo` | registro | `oil` | El aceite esencial se deduce solo del compuesto EO de USDA, sin ficha aetheroleum de la EMA ni otra fuente; queda para revisión futura. |
| `conflicto-entre-fuentes` | registro | `<campo afectado>` | Dos fuentes se contradicen en un campo y se usó la más autorizada. |

Reglas del validador que dependen de los flags:

- Todo grupo de usos o todo objetivo con `pendingReview` verdadero tiene un flag cuyo `target` lo señala (`traditionalUses[<índice>]` o `goals.<objetivo>`); sin él, el registro no valida y la construcción falla con `PendingWithoutFlag`.
- Todo grupo con alguna cita sin resolver lleva `cita-sin-resolver`, y un grupo es pendiente solo si ninguna de sus citas está resuelta.
- Un `safety` nulo lleva `sin-datos-de-seguridad` y solo si ninguna entrada del paquete fija nivel.
- Una planta con interacciones graves en la EMA y objetivo `relajacion-estres` (el hipérico) lleva ese objetivo con `pendingReview` verdadero y el flag `interacciones-graves-estres`.

### La validación humana queda fuera de alcance

Los `reviewFlags` solo se registran: en este cambio no existe una capa de validación humana (un panel para revisarlos y aprobar lo pendiente) y es una función futura del software. Mientras tanto, los grupos de uso y los objetivos con `pendingReview` se guardan en la semilla y en `plant_use_group` y `plant_goal`, pero no generan filas en `plant_use` y los cambios siguientes no deben mostrarlos. Los flags de fusión heterotípica y de identidad ambigua quedan como lista de casos para esa revisión futura.
