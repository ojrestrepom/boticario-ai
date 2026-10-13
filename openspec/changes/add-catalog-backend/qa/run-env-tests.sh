#!/usr/bin/env bash
# Pruebas de arranque, configuración, fallos internos y atribución multi-fuente de la API.
# Usa copias de data/build/catalog.db en un directorio temporal; no modifica la base real.
# Uso: qa/run-env-tests.sh   (no necesita la API de las otras pruebas; usa los puertos 18101-18104 y 8080)
set -u
QA="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$QA/../../../.." && pwd)"
EV="${EV_DIR:-$QA/evidence}"
BIN="$ROOT/backend/target/release/catalog-api"
REALDB="$ROOT/data/build/catalog.db"
TMP="${QA_TMP:-$(mktemp -d)}"
RES="$EV/results-env.tsv"
: > "$RES"
FAILS=""
a() { local d="$1"; shift; if ! "$@" >/dev/null 2>&1; then FAILS="$FAILS; $d"; fi; }
aeq() { if [ "$2" != "$3" ]; then FAILS="$FAILS; $1 (esperado '$2', obtenido '$3')"; fi; }
fin() {
  if [ -z "$FAILS" ]; then printf '%s\tPASS\t%s\t\n' "$1" "$2" >> "$RES"; echo "PASS $1 $2";
  else printf '%s\tFAIL\t%s\t%s\n' "$1" "$2" "${FAILS#; }" >> "$RES"; echo "FAIL $1 $2 :: ${FAILS#; }"; fi
  FAILS=""
}
MD5_REAL=$(md5 -q "$REALDB")

# run_rc ID "VAR=val ..." [args]: ejecuta el binario hasta que sale (máx. 40 s), guarda stdout/stderr y el código de salida en evidence/ID.{stdout,stderr,rc}.
run_rc() {
  local id="$1" envs="$2"; shift 2
  ( cd "$ROOT" && env $envs bash -c '"$@" > "'"$EV/$id"'.stdout" 2> "'"$EV/$id"'.stderr"; echo $? > "'"$EV/$id"'.rc"' _ "$BIN" "$@" ) &
  local bgpid=$!; local i=0; local t0=$SECONDS
  while kill -0 "$bgpid" 2>/dev/null && [ $i -lt 160 ]; do sleep 0.25; i=$((i+1)); done
  if kill -0 "$bgpid" 2>/dev/null; then echo "SIGUE_VIVO" > "$EV/$id.rc"; pkill -P "$bgpid" 2>/dev/null; kill "$bgpid" 2>/dev/null; fi
  echo "$((SECONDS-t0))" > "$EV/$id.secs"
  # La salida puede inundarse de errores (ver ENV-016): se registra el tamaño y se conserva solo una muestra.
  local sz; sz=$(wc -c < "$EV/$id.stdout" | tr -d ' ')
  if [ "$sz" -gt 200000 ]; then
    local ln; ln=$(wc -l < "$EV/$id.stdout" | tr -d ' ')
    head -c 3000 "$EV/$id.stdout" > "$EV/$id.stdout.sample"
    echo "[recortado: $ln líneas y $sz bytes en $(cat "$EV/$id.secs") s; muestra en $id.stdout.sample]" > "$EV/$id.stdout"
    echo "$ln" > "$EV/$id.stdout.lines"
  fi
}

start_api() { # start_api ID "ENVS" -> arranca en segundo plano, log en evidence/ID.log, pid en $TMP/ID.pid
  local id="$1" envs="$2"; shift 2
  cd "$ROOT" || return
  env $envs "$BIN" "$@" > "$EV/$id.log" 2>&1 &
  echo $! > "$TMP/$id.pid"
  cd "$QA" || return
  local i=0
  until grep -q "escuchando" "$EV/$id.log" 2>/dev/null || [ $i -gt 40 ]; do sleep 0.25; i=$((i+1)); done
}
stop_api() { kill "$(cat "$TMP/$1.pid")" 2>/dev/null; sleep 0.3; }

# ---------- ENV-001: configuración por defecto ----------
if lsof -ti tcp:8080 >/dev/null 2>&1; then
  echo "NOT RUN ENV-001 puerto 8080 ocupado" ; printf 'ENV-001\tNOT RUN\tConfiguración por defecto 127.0.0.1:8080\tpuerto 8080 ocupado\n' >> "$RES"
else
  start_api ENV-001 "RUST_LOG=info"
  c=$(curl -s -o "$EV/ENV-001.body" -w '%{http_code}' http://127.0.0.1:8080/healthz); aeq "healthz en 8080" 200 "$c"
  lsof -nP -iTCP:8080 -sTCP:LISTEN > "$EV/ENV-001.lsof" 2>&1
  a "escucha en 127.0.0.1:8080" grep -q "127.0.0.1:8080" "$EV/ENV-001.lsof"
  a "log indica 127.0.0.1:8080" grep -q "127.0.0.1:8080" "$EV/ENV-001.log"
  stop_api ENV-001
  fin ENV-001 "Sin HOST ni PORT escucha en 127.0.0.1:8080 (base por defecto data/build/catalog.db)"
fi

# ---------- ENV-002: base ausente ----------
run_rc ENV-002 "CATALOG_DB=/tmp/no-existe.db PORT=18102"
aeq "código de salida" 1 "$(cat "$EV/ENV-002.rc")"
a "mensaje con la ruta" grep -q "/tmp/no-existe.db" "$EV/ENV-002.stderr"
a "mensaje con catalog-ingest build" grep -q "catalog-ingest" "$EV/ENV-002.stderr"
a "mensaje con build" grep -q "build" "$EV/ENV-002.stderr"
a "sin pánico ni backtrace" bash -c "! grep -qiE 'panicked|backtrace|RUST_BACKTRACE' '$EV/ENV-002.stderr'"
fin ENV-002 "Base ausente: sale con código 1 y el mensaje indica ruta y cómo construirla"

# ---------- ENV-003: versión de esquema incompatible ----------
mkdir -p "$TMP/v2"; cp "$REALDB" "$TMP/v2/catalog.db"
sqlite3 "$TMP/v2/catalog.db" "update metadata set value='2' where key='schema_version'"
run_rc ENV-003 "CATALOG_DB=$TMP/v2/catalog.db PORT=18102"
aeq "código de salida" 1 "$(cat "$EV/ENV-003.rc")"
a "indica versión encontrada (2)" grep -q "2" "$EV/ENV-003.stderr"
a "indica versión soportada (1)" grep -qE "soporta|soportad" "$EV/ENV-003.stderr"
a "sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/ENV-003.stderr'"
fin ENV-003 "schema_version distinta: no arranca, indica versión encontrada y soportada"

mkdir -p "$TMP/vabc"; cp "$REALDB" "$TMP/vabc/catalog.db"
sqlite3 "$TMP/vabc/catalog.db" "update metadata set value='abc' where key='schema_version'"
run_rc ENV-004a "CATALOG_DB=$TMP/vabc/catalog.db PORT=18102"
aeq "schema_version=abc: código" 1 "$(cat "$EV/ENV-004a.rc")"
mkdir -p "$TMP/vnone"; cp "$REALDB" "$TMP/vnone/catalog.db"
sqlite3 "$TMP/vnone/catalog.db" "delete from metadata"
run_rc ENV-004b "CATALOG_DB=$TMP/vnone/catalog.db PORT=18102"
aeq "sin metadata: código" 1 "$(cat "$EV/ENV-004b.rc")"
mkdir -p "$TMP/vnotab"; cp "$REALDB" "$TMP/vnotab/catalog.db"
sqlite3 "$TMP/vnotab/catalog.db" "drop table metadata"
run_rc ENV-004c "CATALOG_DB=$TMP/vnotab/catalog.db PORT=18102"
aeq "sin tabla metadata: código" 1 "$(cat "$EV/ENV-004c.rc")"
printf 'esto no es sqlite\n' > "$TMP/garbage.db"
run_rc ENV-004d "CATALOG_DB=$TMP/garbage.db PORT=18102"
aeq "archivo que no es SQLite: código" 1 "$(cat "$EV/ENV-004d.rc")"
: > "$TMP/empty.db"
run_rc ENV-004e "CATALOG_DB=$TMP/empty.db PORT=18102"
aeq "archivo vacío: código" 1 "$(cat "$EV/ENV-004e.rc")"
[ -e "$TMP/empty.db" ] && aeq "no crea/escribe en archivo vacío" 0 "$(wc -c < "$TMP/empty.db" | tr -d ' ')"
run_rc ENV-004f "CATALOG_DB=$TMP PORT=18102"
aeq "ruta es un directorio: código" 1 "$(cat "$EV/ENV-004f.rc")"
for x in 004a 004b 004c 004d 004e 004f; do
  a "$x sin pánico ni backtrace" bash -c "! grep -qiE 'panicked|backtrace' '$EV/ENV-$x.stderr'"
  a "$x mensaje no vacío" test -s "$EV/ENV-$x.stderr"
done
fin ENV-004 "Bases inválidas (schema_version no numérica, metadata vacía o ausente, archivo basura, vacío, directorio): salen con código 1 y mensaje, sin pánico"

# ---------- ENV-005: --db tiene prioridad sobre CATALOG_DB ----------
start_api ENV-005 "CATALOG_DB=/tmp/no-existe.db PORT=18103" --db "$REALDB"
c=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18103/v1/plants?limit=1); aeq "con --db arranca" 200 "$c"
stop_api ENV-005
fin ENV-005 "El argumento --db tiene prioridad sobre CATALOG_DB"

# ---------- ENV-006: HOST/PORT inválidos o en uso ----------
run_rc ENV-006a "PORT=abc"
a "PORT=abc: código distinto de 0" bash -c "[ \"\$(cat '$EV/ENV-006a.rc')\" != 0 ] && [ \"\$(cat '$EV/ENV-006a.rc')\" != SIGUE_VIVO ]"
run_rc ENV-006b "PORT=70000"
a "PORT=70000: código distinto de 0" bash -c "[ \"\$(cat '$EV/ENV-006b.rc')\" != 0 ] && [ \"\$(cat '$EV/ENV-006b.rc')\" != SIGUE_VIVO ]"
run_rc ENV-006c "HOST=no-es-un-host PORT=18104"
aeq "HOST inválido: código" 1 "$(cat "$EV/ENV-006c.rc")"
start_api ENV-006d "PORT=18104"
run_rc ENV-006e "PORT=18104"
aeq "puerto en uso: código" 1 "$(cat "$EV/ENV-006e.rc")"
stop_api ENV-006d
for x in 006a 006b 006c 006e; do a "$x sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/ENV-$x.stderr'"; a "$x mensaje" test -s "$EV/ENV-$x.stderr"; done
fin ENV-006 "PORT/HOST inválidos o puerto ocupado: salen con código 1 y mensaje sin pánico"

# ---------- ENV-007: --openapi ----------
( cd "$ROOT" && "$BIN" --openapi > "$EV/ENV-007.openapi.json" 2> "$EV/ENV-007.stderr" ); rc=$?
aeq "rc" 0 "$rc"
a "== backend/openapi.json (JSON)" diff -q <(jq -S . "$EV/ENV-007.openapi.json") <(jq -S . "$ROOT/backend/openapi.json")
a "== backend/openapi.json (byte a byte)" diff -q "$EV/ENV-007.openapi.json" "$ROOT/backend/openapi.json"
fin ENV-007 "catalog-api --openapi imprime el documento versionado"

# ---------- ENV-008: argumento desconocido y --help ----------
run_rc ENV-008a "" --nope
echo "rc --nope: $(cat "$EV/ENV-008a.rc")" > "$EV/ENV-008.note"
run_rc ENV-008b "" --help
echo "rc --help: $(cat "$EV/ENV-008b.rc")" >> "$EV/ENV-008.note"
aeq "--help rc" 0 "$(cat "$EV/ENV-008b.rc")"
a "--nope no arranca el servidor" bash -c "[ \"\$(cat '$EV/ENV-008a.rc')\" != SIGUE_VIVO ]"
fin ENV-008 "Argumento desconocido no arranca el servidor; --help sale con 0"

# ---------- ENV-009: solo lectura real (archivo y directorio sin escritura) ----------
mkdir -p "$TMP/ro"; cp "$REALDB" "$TMP/ro/catalog.db"; chmod 444 "$TMP/ro/catalog.db"; chmod 555 "$TMP/ro"
start_api ENV-009 "CATALOG_DB=$TMP/ro/catalog.db PORT=18103"
c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:18103/v1/plants/lavandula-angustifolia"); aeq "detalle sobre base 0444 en directorio 0555" 200 "$c"
c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:18103/v1/plants?q=lav"); aeq "búsqueda" 200 "$c"
a "no se crearon archivos extra en el directorio" bash -c "[ \"\$(ls -A '$TMP/ro' | wc -l | tr -d ' ')\" = 1 ]"
stop_api ENV-009; chmod 755 "$TMP/ro"
fin ENV-009 "La API funciona con la base de solo lectura (0444) en directorio sin escritura y no crea archivos auxiliares"

# ---------- ENV-010: orden estable en empate de nombre científico ----------
mkdir -p "$TMP/tie"; cp "$REALDB" "$TMP/tie/catalog.db"
sqlite3 "$TMP/tie/catalog.db" "update plant set scientific_name='Aaa empate' where id in ('zizyphus-vulgaris-var-spinosus','abelmoschus-manihot','lavandula-angustifolia','zizyphus-oenoplia','abies-alba')"
start_api ENV-010 "CATALOG_DB=$TMP/tie/catalog.db PORT=18103"
: > "$EV/ENV-010.ids"
for off in 0 1 2 3 4 5; do curl -s "http://127.0.0.1:18103/v1/plants?limit=1&offset=$off" | jq -r '.items[0].id' >> "$EV/ENV-010.ids"; done
printf '%s\n' abelmoschus-manihot abies-alba lavandula-angustifolia zizyphus-oenoplia zizyphus-vulgaris-var-spinosus > "$EV/ENV-010.expected5"
head -5 "$EV/ENV-010.ids" > "$EV/ENV-010.got5"
a "los 5 empatados salen por id, uno por página, sin repetir ni omitir" diff -q "$EV/ENV-010.expected5" "$EV/ENV-010.got5"
curl -s "http://127.0.0.1:18103/v1/plants?limit=100" | jq -r '.items[0:5][].id' > "$EV/ENV-010.page5"
a "mismo orden con limit=100" diff -q "$EV/ENV-010.expected5" "$EV/ENV-010.page5"
stop_api ENV-010
fin ENV-010 "Empate de nombre científico (5 plantas con el mismo nombre en una copia): orden por id y paginación sin repetidos ni omisiones"

# ---------- ENV-011: dos fuentes, atribución de cada dato ----------
mkdir -p "$TMP/multi"; cp "$REALDB" "$TMP/multi/catalog.db"
sqlite3 "$TMP/multi/catalog.db" "
insert into source values ('fixture2','Fuente fixture','9','CC0','cita fixture','https://example.invalid/f','abc123');
insert into plant_name_source select plant_name_id,'fixture2' from plant_name_source where plant_name_id in (select id from plant_name where plant_id='lavandula-angustifolia' and kind='common');
insert into plant_part_source select plant_part_id,'fixture2' from plant_part_source where plant_part_id in (select id from plant_part where plant_id='lavandula-angustifolia' and label='Flower');
insert into plant_use_source select plant_use_id,'fixture2' from plant_use_source where plant_use_id in (select id from plant_use where plant_id='lavandula-angustifolia' and activity='Perfume');"
start_api ENV-011 "CATALOG_DB=$TMP/multi/catalog.db PORT=18103"
curl -s "http://127.0.0.1:18103/v1/plants/lavandula-angustifolia" > "$EV/ENV-011.detail.json"
curl -s "http://127.0.0.1:18103/v1/sources" > "$EV/ENV-011.sources.json"
a "nombre común con ambas fuentes" jq -e '.names[]|select(.text=="English Lavender")|.sources|sort==["fixture2","usda"]' "$EV/ENV-011.detail.json"
a "parte Flower con ambas fuentes" jq -e '.parts[]|select(.label=="Flower")|.sources|sort==["fixture2","usda"]' "$EV/ENV-011.detail.json"
a "uso Perfume con ambas fuentes" jq -e '.uses[]|select(.activity=="Perfume")|.sources|sort==["fixture2","usda"]' "$EV/ENV-011.detail.json"
a "otro uso solo usda" jq -e '.uses[]|select(.activity=="Diuretic")|.sources==["usda"]' "$EV/ENV-011.detail.json"
a "/v1/sources lista las 2 fuentes" jq -e 'length==2 and ([.[].id]|sort==["fixture2","usda"])' "$EV/ENV-011.sources.json"
stop_api ENV-011
fin ENV-011 "Dato aportado por dos fuentes (copia con fuente fixture2 añadida): el detalle indica ambas"

# ---------- ENV-012: base con una única fuente distinta de USDA ----------
mkdir -p "$TMP/other"; cp "$REALDB" "$TMP/other/catalog.db"
sqlite3 "$TMP/other/catalog.db" "
pragma foreign_keys=off;
update source set id='otra', name='Otra fuente', license='MIT';
update plant set family_source_id='otra' where family_source_id is not null;
update plant_name_source set source_id='otra';
update plant_part_source set source_id='otra';
update plant_use_source set source_id='otra';
update reference_source set source_id='otra';
update plant_source_id set source_id='otra';"
start_api ENV-012 "CATALOG_DB=$TMP/other/catalog.db PORT=18103"
curl -s "http://127.0.0.1:18103/v1/sources" > "$EV/ENV-012.sources.json"
curl -s "http://127.0.0.1:18103/v1/plants/lavandula-angustifolia" > "$EV/ENV-012.detail.json"
c=$(curl -s -o "$EV/ENV-012.list.json" -w '%{http_code}' "http://127.0.0.1:18103/v1/plants?q=lavandula")
aeq "listado" 200 "$c"
a "fuentes = otra" jq -e 'length==1 and .[0].id=="otra" and .[0].license=="MIT"' "$EV/ENV-012.sources.json"
a "toda atribución = otra" jq -e '([.names[],.parts[],.uses[],.family]|all(.sources==["otra"]))' "$EV/ENV-012.detail.json"
a "sin ocurrencias de usda en las respuestas" bash -c "! grep -qi usda '$EV/ENV-012.detail.json' '$EV/ENV-012.list.json' "
stop_api ENV-012
fin ENV-012 "Base con una única fuente distinta de USDA (copia con la fuente renombrada) funciona sin cambios de código"

# ---------- ENV-013: fallos internos -> 500 genérico ----------
mkdir -p "$TMP/broken"; cp "$REALDB" "$TMP/broken/catalog.db"
sqlite3 "$TMP/broken/catalog.db" "drop table plant_use_source; alter table plant_name rename to plant_name_x;"
start_api ENV-013 "CATALOG_DB=$TMP/broken/catalog.db PORT=18103 RUST_LOG=info"
c=$(curl -s -D "$EV/ENV-013.detail.headers" -o "$EV/ENV-013.detail.body" -w '%{http_code}' "http://127.0.0.1:18103/v1/plants/lavandula-angustifolia"); aeq "detalle roto -> 500" 500 "$c"
c=$(curl -s -D "$EV/ENV-013.list.headers" -o "$EV/ENV-013.list.body" -w '%{http_code}' "http://127.0.0.1:18103/v1/plants?q=lav"); aeq "listado roto -> 500" 500 "$c"
c=$(curl -s -D "$EV/ENV-013.sources.headers" -o "$EV/ENV-013.sources.body" -w '%{http_code}' "http://127.0.0.1:18103/v1/sources"); aeq "fuentes (intactas) -> 200" 200 "$c"
c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:18103/healthz"); aeq "healthz sigue 200" 200 "$c"
for k in detail list; do
  a "$k content-type problem+json" grep -qi '^content-type: application/problem+json' "$EV/ENV-013.$k.headers"
  a "$k status 500 en cuerpo" jq -e '.status==500' "$EV/ENV-013.$k.body"
  a "$k sin detalles internos" bash -c "! grep -qiE 'sqlite|diesel|plant_use_source|plant_name|no such table|SELECT|/Users|\.rs:|catalog\.db' '$EV/ENV-013.$k.body'"
done
a "el detalle técnico va a los logs" grep -qiE "no such table|plant_use_source|plant_name" "$EV/ENV-013.log"
stop_api ENV-013
fin ENV-013 "Fallo interno (tablas rotas en una copia): 500 problem+json genérico sin detalles; el detalle va al log; el servicio sigue vivo"

# ---------- ENV-015: tiempo de fallo con base ilegible ----------
for x in 004d 004f 004e; do echo "ENV-$x: $(cat "$EV/ENV-$x.secs") s" >> "$EV/ENV-015.note"; done
a "base no SQLite falla en menos de 2 s" bash -c "[ \"\$(cat '$EV/ENV-004d.secs')\" -lt 2 ]"
a "ruta que es un directorio falla en menos de 2 s" bash -c "[ \"\$(cat '$EV/ENV-004f.secs')\" -lt 2 ]"
fin ENV-015 "El arranque con una base ilegible (no SQLite, directorio) falla rápido"

# ---------- ENV-016: un solo mensaje de error con la ruta, sin inundar el log ----------
: > "$EV/ENV-016.note"
for x in 004d 004f; do
  so=$(wc -l < "$EV/ENV-$x.stdout" | tr -d ' '); se=$(wc -l < "$EV/ENV-$x.stderr" | tr -d ' ')
  echo "ENV-$x: stdout=$so líneas, stderr=$se líneas, $(cat "$EV/ENV-$x.secs") s; stderr: $(head -c 300 "$EV/ENV-$x.stderr")" >> "$EV/ENV-016.note"
  aeq "ENV-$x stdout sin ruido (0 líneas)" 0 "$so"
  aeq "ENV-$x una sola línea de error en stderr" 1 "$se"
  a "ENV-$x código de salida 1" grep -qx 1 "$EV/ENV-$x.rc"
done
a "mensaje de la base no SQLite incluye la ruta" grep -q "garbage.db" "$EV/ENV-004d.stderr"
a "mensaje del directorio incluye la ruta" grep -q "$TMP" "$EV/ENV-004f.stderr"
fin ENV-016 "El arranque con una base que no es SQLite no inunda la salida con errores repetidos"

# ---------- Verificación: base real intacta, puertos libres ----------
aeq "base real intacta (md5)" "$MD5_REAL" "$(md5 -q "$REALDB")"
fin ENV-014 "La base real data/build/catalog.db no cambió durante las pruebas de entorno"

echo; awk -F'\t' '{c[$2]++} END{for(k in c) print k, c[k]}' "$RES"
echo "tmp: $TMP"
