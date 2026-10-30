// Workflow de Claude Code (herramienta Workflow) que consolida una fase de la semilla: un agente Worker por lote de 10 plantas.
// Argumentos: {"phase": N, "count": C, "pad": P, "scratch": "<carpeta auxiliar>"}, o {"phase": N, "lots": ["lot-01", ...]} con nombres explícitos.
// Los agentes trabajan en la raíz del repo; si el repo no está en /Users/jsrc1115/Code/boticario-ai, ajusta esa ruta en el prompt (función prompt).
// Véase tools/catalog-seed/generation/README.md.
export const meta = {
  name: 'generate-seed-phase',
  description: 'Consolidate one phase of catalog seed records: one Worker agent per lot of 10 plants, each validated',
  whenToUse: 'Full generation of the consolidate-catalog-seed records, phase by phase',
  phases: [
    { title: 'Consolidar', detail: 'one Worker per lot of 10 plants, prompt v7, validator per lot' },
  ],
}

const PHASE = args.phase
const LOTS = args.lots || Array.from({ length: args.count }, (_, i) => 'lot-' + String(i + 1).padStart(args.pad || 2, '0'))
const SCRATCH = args.scratch

const RESULT = {
  type: 'object',
  properties: {
    lot: { type: 'string' },
    written: { type: 'array', items: { type: 'string' } },
    rejected: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, reason: { type: 'string' } }, required: ['id', 'reason'] } },
    validatorErrors: { type: 'integer' },
    validatorWarnings: { type: 'integer' },
    startedAt: { type: 'string' },
    finishedAt: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['lot', 'written', 'rejected', 'validatorErrors', 'validatorWarnings', 'startedAt', 'finishedAt', 'notes'],
}

function prompt(lot) {
  const dir = `data/work/generation/phase${PHASE}/records/${lot}`
  return `Eres el consolidador del catálogo de Boticario AI en la generación completa (fase ${PHASE}, ${lot}) del cambio OpenSpec \`consolidate-catalog-seed\`. Trabajas en el repo \`/Users/jsrc1115/Code/boticario-ai\`, rama \`consolidate-catalog-seed\`.

Lee y sigue al pie de la letra tu prompt, \`tools/catalog-seed/prompt/consolidate.md\` (prompt-version 7), entero antes de empezar, y lo que nombra: \`tools/catalog-seed/schema/record.schema.json\`, \`tools/catalog-seed/goals-map.json\`, \`data/seed/goals.json\`, \`tools/catalog-seed/safety-map.json\`, \`tools/catalog-seed/flag-codes.json\`, \`tools/catalog-seed/sensitive-activities.json\` y el paquete de cada planta en \`data/work/bundles/<id>.json\`.

Las plantas de tu lote están en \`data/work/generation/phase${PHASE}/${lot}.txt\` (un ID por línea).

Cómo trabajar:
- Escribe tú el contenido de cada registro, planta por planta, a partir de su paquete (traducciones, resúmenes, elección de nombres y grupos, emparejamiento de claves de cita con candidatas, texto de precauciones con las advertencias de las señales de riesgo). Puedes usar la terminal para leer los paquetes, ejecutar el validador y tareas mecánicas (copiar los refs citados y la lista \`sources\` desde el paquete, o el texto literal de una candidata elegida). No generes el contenido con un script. No uses conocimiento propio ni la red.
- Para tus archivos auxiliares (scripts de lectura o ensamblado, borradores) usa solo tu carpeta propia \`${SCRATCH}/gen-phase${PHASE}-${lot}/\`: otros agentes trabajan en paralelo y una carpeta compartida se pisa.
- Guarda cada registro en \`${dir}/<id>.json\` (crea la carpeta). Algunas plantas del lote pueden tener ya un registro en \`data/seed/plants/\` cuyo paquete cambió: escríbelas de nuevo desde su paquete actual, sin copiar el registro anterior.
- Valida desde la raíz del repo: \`python3 -I tools/catalog-seed/cli.py validate --records ${dir} --bundles data/work/bundles --out data/work/generation/phase${PHASE}/records/${lot}-validate.json\`. Corrige hasta 0 errores. Si un registro sigue con errores tras tres intentos de corrección, muévelo a \`data/work/generation/phase${PHASE}/rejected/${lot}/<id>.json\` para que el directorio del lote valide limpio, y repórtalo en \`rejected\` con el motivo.
- Anota la hora de inicio y de fin con \`date -u +%Y-%m-%dT%H:%M:%SZ\`.

Restricciones: escribe solo dentro de \`data/work/generation/phase${PHASE}/\` y de tu carpeta auxiliar. No toques ningún otro archivo del repo (en particular \`data/seed/\`, \`tools/\` y \`docs/\`). No hagas commits ni push, no uses la red y no dejes procesos en segundo plano.

Devuelve: el nombre del lote, los IDs escritos en la carpeta del lote, los rechazados con su motivo, el número de errores y advertencias del validador en la última ejecución, las horas de inicio y fin, y en \`notes\` una o dos frases con reglas ambiguas o casos dudosos que convenga revisar (o vacío).`
}

phase('Consolidar')
log(`Fase ${PHASE}: ${LOTS.length} lotes`)
const results = await parallel(LOTS.map(lot => () =>
  agent(prompt(lot), { label: `fase${PHASE}:${lot}`, phase: 'Consolidar', schema: RESULT, agentType: 'Worker' })))

const done = results.filter(Boolean)
const failed = LOTS.filter((lot, i) => !results[i])
const written = done.reduce((n, r) => n + r.written.length, 0)
const rejected = done.flatMap(r => r.rejected.map(x => ({ lot: r.lot, ...x })))
const withErrors = done.filter(r => r.validatorErrors > 0).map(r => r.lot)
log(`Escritos ${written}; rechazados ${rejected.length}; lotes sin resultado ${failed.length}; lotes con errores ${withErrors.length}`)
return { phase: PHASE, lots: LOTS.length, written, rejected, failedLots: failed, lotsWithErrors: withErrors, results: done }
