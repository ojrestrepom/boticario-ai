# Cómo generar la semilla con Claude Code

Esta guía describe cómo se generaron los registros de `data/seed/plants/` con agentes de Claude Code, para poder repetirlo. Es el modo A de la tarea 11.1 del cambio `consolidate-catalog-seed`. Las herramientas de `tools/catalog-seed/` no llaman al modelo: el contenido de cada registro lo escribe un agente, y el código solo planifica, valida y sella.

## Requisitos

- Claude Code con la herramienta Workflow y el tipo de agente `Worker` (modelo balanceado).
- Los insumos de `data/work/` construidos con la tubería («Tubería completa, en orden» del README de las herramientas): los paquetes en `data/work/bundles/`, el universo en `data/work/universe/universe.json` y la asignación de Wikidata, Wikipedia y Commons ya hecha y reflejada en los paquetes.
- El prompt vigente, `tools/catalog-seed/prompt/consolidate.md` (hoy versión 7), con el esquema, los mapas y las listas que nombra.
- Ningún acceso a la red: los agentes solo leen archivos del repo.

## Archivos

- `generate-seed-phase.js`: el script del workflow. Recibe la fase y el número de lotes y lanza un agente por lote.
- Los agentes escriben en `data/work/generation/phase<N>/`: la lista de cada lote (`lot-NNN.txt`), sus registros (`records/lot-NNN/<id>.json`), el informe del validador (`records/lot-NNN-validate.json`) y, si hace falta, los rechazados (`rejected/lot-NNN/`).

## Pasos

1. **Obtener las plantas pendientes.** Con los paquetes al día, `python3 -I tools/catalog-seed/cli.py plan --bundles data/work/bundles --seed data/seed --json` lista las plantas sin registro o con otro `bundleHash`, `promptVersion` o `recordVersion`, cada una con su motivo. Guarda la salida (en la generación completa, `data/work/generation/plan.json`).
2. **Armar los lotes.** Divide las plantas en grupos de 10, en el orden del plan (por `id`), y escribe cada grupo en `data/work/generation/phase<N>/lot-NNN.txt`, un ID por línea. Si se genera por fases, separa antes las plantas: en la generación completa, la fase 1 fue la de las plantas con alguna entrada de la EMA y la fase 2 el resto. Usa `lot-NN` con 2 dígitos si hay menos de 100 lotes y `lot-NNN` con 3 si hay más.
3. **Lanzar el workflow.** Pide a Claude Code que ejecute `generate-seed-phase.js` con la herramienta Workflow y estos argumentos:
   - `phase`: el número de fase, que da la carpeta `data/work/generation/phase<N>/`.
   - `count`: cuántos lotes hay; el script genera los nombres `lot-01`, `lot-02`… (o también `lots`, una lista de nombres explícita).
   - `pad`: dígitos del número de lote (por defecto 2).
   - `scratch`: una carpeta fuera del repo para los archivos auxiliares de los agentes (por ejemplo, el scratchpad de la sesión); cada agente usa la suya, `<scratch>/gen-phase<N>-<lote>/`.

   La fase 2 usó `{"phase": 2, "count": 215, "pad": 3, "scratch": "<scratchpad de la sesión>"}`. Los agentes son de tipo `Worker`, y el workflow los lanza todos en paralelo y devuelve un resultado por lote.
4. **Revisar el resultado.** El workflow devuelve, por lote, los IDs escritos, los rechazados con su motivo, los errores y advertencias del validador, las horas de inicio y fin y notas sobre casos dudosos. Comprueba que no haya lotes sin resultado (`failedLots`) ni con errores (`lotsWithErrors`), lee las notas, mira los rechazados y revisa algunos registros por muestreo con la lista de comprobación de «Revisión de la corrida de control (tarea 5.3)» del README de las herramientas. Para un rechazado o un lote fallido, repite el lote o corrige la planta (véase «Cómo reanudar»).
5. **Importar.** Por cada lote, `python3 -I tools/catalog-seed/cli.py seal --seed data/seed --from data/work/generation/phase<N>/records/lot-NNN`. La opción `--from` se puede repetir en un solo comando. `seal` importa todo o nada, comprueba el esquema y la `promptVersion`, reescribe los registros con formato estable y actualiza `manifest.json`.
6. **Confirmar.** `python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants --bundles data/work/bundles` debe dar 0 errores, y `plan` debe listar solo lo que falta de las fases siguientes (o «0 plantas a regenerar» al final).

## Cómo reanudar

Si un límite de uso corta la corrida:

- Relanza el workflow con `resumeFromRunId` (el identificador de la ejecución cortada), con los mismos argumentos.
- O vuelve a correr `plan`: solo pone en cola las plantas que no tienen registro (o lo tienen desactualizado), y con ellas se arman lotes nuevos. Los lotes ya importados con `seal` no se repiten.

Cada agente reescribe su carpeta de registros, así que repetir un lote no deja registros mezclados.

## Qué hace cada agente

El script envuelve cada lote en el mismo prompt, parametrizado por fase y lote:

1. Lee el prompt `consolidate.md` entero y lo que nombra: el esquema del registro, los mapas de objetivos y de seguridad, los códigos de flags, las actividades sensibles y el paquete de cada planta.
2. Lee la lista del lote (`lot-NNN.txt`) y, planta por planta, escribe el registro a mano a partir de su paquete.
3. Guarda cada registro en `records/lot-NNN/<id>.json`. Si la planta ya tenía un registro en la semilla cuyo paquete cambió, lo reescribe desde el paquete actual, sin copiar el anterior.
4. Valida con `cli.py validate --records ... --bundles data/work/bundles --out ...-validate.json` y corrige hasta 0 errores. Un registro que sigue con errores tras tres intentos se mueve a `rejected/lot-NNN/` y se reporta con el motivo.
5. Usa su carpeta auxiliar propia para scripts de lectura o borradores, porque otros agentes trabajan en paralelo.
6. Devuelve un resultado estructurado: lote, IDs escritos, rechazados, errores y advertencias del validador, horas de inicio y fin y notas.

## Restricciones de la política

- El agente usa solo el paquete de la planta: ni conocimiento propio ni la red.
- El contenido de los registros lo escribe el agente. No se genera con scripts; la terminal sirve para leer paquetes, validar y tareas mecánicas, como copiar los refs citados y la lista `sources` desde el paquete o el texto literal de una candidata elegida.
- Escribe solo en `data/work/generation/phase<N>/` y en su carpeta auxiliar. No toca `data/seed/`, `tools/` ni `docs/`, no hace commits ni push y no deja procesos en segundo plano.
- Solo `seal` escribe en `data/seed/`.

## Costo y tiempo medidos

| Corrida | Plantas | Lotes | Tiempo | Tokens | Tokens por planta |
| --- | --- | --- | --- | --- | --- |
| Control (prompt v7) | 20 | 2 | 5 a 7 minutos por lote | unos 370.000 | unos 18.500 |
| Fase 1 | 189 | 19 | unos 14 minutos | 3.255.434 | unos 17.200 |
| Fase 2 | 2.150 (2.149 escritas y 1 rechazada) | 215 | unos 23 minutos de reloj en la segunda ventana, más la primera parte antes de la pausa | 13.343.485 (corrida reanudada, incluye los 115 lotes de la primera parte) | unos 6.200 |

La fase 1 dio 0 errores del validador y 0 rechazados. La estimación con 17.200 a 18.500 tokens por planta daba unos 37 a 40 millones de tokens para la fase 2, pero el gasto real fue de unos 6.200 por planta, y el tope práctico fueron las ventanas de uso de la cuenta.

La fase 2 dio 0 errores y 0 advertencias del validador en los 215 lotes y 1 rechazo, `malachra-alaceaefolia`, porque su paquete no trae ningún ref y el esquema exige al menos uno en `scientificName` y `displayName`. Una pausa por el límite de uso cortó la corrida tras 115 lotes y se reanudó con `resumeFromRunId` y los mismos argumentos; los 215 lotes quedaron completos. Los tokens de la tabla son los de la corrida reanudada.

## Aclaraciones recomendadas en el envoltorio por lote

En la regeneración `fix2` los agentes recibieron estas aclaraciones de la QA en el envoltorio de cada lote. Son precisiones de reglas del prompt v7, no reglas nuevas, y se recomiendan para futuras corridas:

- Selección de grupos: se aplica exactamente el orden del prompt y no se omiten grupos; `traditionalUses` debe tener al menos min(20, N) grupos, donde N es el número de actividades del paquete que no son señales de riesgo (el validador lo comprueba).
- Fórmula de enfermedades graves exacta: «Uso tradicional, sin eficacia demostrada: <enfermedad>», con un solo espacio tras los dos puntos, sin espacios dobles ni comillas.
- Sin cantidades: los textos, y en especial `safety.text`, no llevan cifras con unidades (por ejemplo valores guía en µg/kg o mg); se describe el riesgo sin la cifra.
- Clave de cita `Nas` (candidatas NAS «Lost Crops of the Incas» y NAS2 «Herbal pharmacology in the People's Republic of China»): se elige por los países del grupo, NAS2 para usos de China o Asia y NAS para usos de los Andes; si los países no permiten decidir, queda sin resolver.
- Nombres de USDA con anotación de idioma entre paréntesis («(Sp.)», «(Ger.)», «(Fr.)», «(Jap.)», etc.): se quita la anotación del texto del nombre y se usa solo para fijar `language`.
- Origen: «Malesia» es la región biogeográfica de WCVP, no el país Malasia, y se escribe «Malesia».

## Cómo se hizo la corrida de control

Dos lotes de 10 plantas con dos agentes en paralelo y el mismo envoltorio descrito arriba, con la salida en `data/work/control/v<N>/` (por ejemplo, `lote-1` y `lote-2`), donde `<N>` es la versión del prompt. Se validaron con `validate`, se revisaron planta por planta (tarea 5.3) y se sellaron con `seal --from` de los dos directorios. Su detalle está en «Corrida de control (tarea 5.1)» y «Revisión de la corrida de control (tarea 5.3)» del README de las herramientas.
