// Valida respuestas reales de la API contra los esquemas de backend/openapi.json con Ajv (2020-12).
// Uso: NODE_PATH=<dir con ajv>/node_modules PORT=18100 node validate-contract.mjs
// Requiere Node 18+ (fetch) y el paquete ajv instalado fuera del proyecto (p. ej. `npm i ajv` en un directorio temporal).
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const Ajv2020 = require(path.join(process.env.AJV_DIR, 'node_modules/ajv/dist/2020.js')).default;

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../../..');
const spec = JSON.parse(readFileSync(path.join(root, 'backend/openapi.json'), 'utf8'));
const base = `http://127.0.0.1:${process.env.PORT || 18100}`;

const ajv = new Ajv2020({ strict: false, allErrors: true });
ajv.addFormat('int32', { type: 'number', validate: (n) => Number.isInteger(n) && n >= -2147483648 && n <= 2147483647 });
ajv.addFormat('int64', { type: 'number', validate: (n) => Number.isInteger(n) });
const wrap = (ref) => ({ $ref: `#/components/schemas/${ref}`, components: spec.components });
const validators = {};
const v = (name) => (validators[name] ??= ajv.compile(wrap(name)));

const results = [];
const failures = [];
function check(label, schemaName, value) {
  const f = v(schemaName);
  const ok = f(value);
  results.push({ label, schemaName, ok });
  if (!ok) failures.push({ label, schemaName, errors: f.errors.slice(0, 3) });
}
async function get(p, init) {
  const r = await fetch(base + p, init);
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch {}
  return { status: r.status, ct: r.headers.get('content-type'), json };
}

// Rutas
let r = await get('/healthz'); check('GET /healthz', 'HealthDto', r.json);
r = await get('/v1/sources'); for (const s of r.json) check('GET /v1/sources item', 'SourceDto', s);
r = await get('/v1/plants?limit=100&offset=0'); check('GET /v1/plants', 'PageDto_PlantSummaryDto', r.json);
// Todas las páginas y todos los detalles
const ids = [];
for (let off = 0; off < 2400; off += 100) {
  r = await get(`/v1/plants?limit=100&offset=${off}`);
  check(`GET /v1/plants?offset=${off}`, 'PageDto_PlantSummaryDto', r.json);
  ids.push(...r.json.items.map((i) => i.id));
}
for (const id of ids) {
  r = await get(`/v1/plants/${id}`);
  check(`GET /v1/plants/${id}`, 'PlantDto', r.json);
}
// Errores
for (const p of ['/v1/plants?limit=0', '/v1/plants?offset=x', '/v1/plants/%FF', '/v1/plants/no-existe', '/nada']) {
  r = await get(p); check(`GET ${p} (${r.status})`, 'ProblemDto', r.json);
}
r = await get('/v1/plants', { method: 'POST' }); check(`POST /v1/plants (${r.status})`, 'ProblemDto', r.json);

const summary = { total: results.length, ok: results.filter((x) => x.ok).length, failed: failures.length, plantsValidated: ids.length, failures: failures.slice(0, 10) };
writeFileSync(path.join(process.env.EV_DIR || path.join(here, 'evidence'), 'CONTRACT-001.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
process.exit(failures.length ? 1 : 0);
