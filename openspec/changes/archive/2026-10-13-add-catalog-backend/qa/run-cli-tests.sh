#!/usr/bin/env bash
# Pruebas de la CLI catalog-ingest. Trabaja en directorios temporales (--data-dir); solo `download` toca data/ y no cambia nada si el ZIP ya está verificado.
# Uso: qa/run-cli-tests.sh
set -u
QA="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$QA/../../../.." && pwd)"
EV="${EV_DIR:-$QA/evidence}"
BIN="$ROOT/backend/target/release/catalog-ingest"
TMP="${QA_TMP:-$(mktemp -d)}"
RES="$EV/results-cli.tsv"
: > "$RES"
FAILS=""
a() { local d="$1"; shift; if ! "$@" >/dev/null 2>&1; then FAILS="$FAILS; $d"; fi; }
aeq() { if [ "$2" != "$3" ]; then FAILS="$FAILS; $1 (esperado '$2', obtenido '$3')"; fi; }
fin() {
  if [ -z "$FAILS" ]; then printf '%s\tPASS\t%s\t\n' "$1" "$2" >> "$RES"; echo "PASS $1 $2";
  else printf '%s\tFAIL\t%s\t%s\n' "$1" "$2" "${FAILS#; }" >> "$RES"; echo "FAIL $1 $2 :: ${FAILS#; }"; fi
  FAILS=""
}
# ing ID args... : ejecuta desde la raíz, guarda stdout/stderr/rc en evidence/ID.*
ing() { local id="$1"; shift; ( cd "$ROOT" && "$BIN" "$@" > "$EV/$id.stdout" 2> "$EV/$id.stderr"; echo $? > "$EV/$id.rc" ); }
rc() { cat "$EV/$1.rc"; }
hash_of() { grep -oE '[0-9a-f]{64}' "$EV/$1.stdout" | head -1; }

ZIP="$ROOT/data/.cache/Duke-Source-CSV.zip"
REF_HASH=48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d

# ---------- CLI-001: download idempotente ----------
ZMD5=$(md5 -q "$ZIP"); ZMT=$(stat -f %m "$ZIP")
ing CLI-001a download; ing CLI-001b download
for x in a b; do
  aeq "download $x rc" 0 "$(rc CLI-001$x)"
  a "download $x dice 'ya estaba'" grep -q "ya estaba" "$EV/CLI-001$x.stdout"
done
aeq "ZIP intacto (md5)" "$ZMD5" "$(md5 -q "$ZIP")"
aeq "ZIP intacto (mtime)" "$ZMT" "$(stat -f %m "$ZIP")"
aeq "md5 del ZIP = checksum declarado" 45ae44a0544586b8ac22a232beaac344 "$ZMD5"
fin CLI-001 "download es idempotente: segunda ejecución dice 'ya estaba', sin tocar el ZIP"

# ---------- Preparar directorio temporal ----------
D="$TMP/data1"; mkdir -p "$D/.cache"; cp "$ROOT/data/sources.toml" "$D/sources.toml"; cp "$ZIP" "$D/.cache/"

# ---------- CLI-002: build / rederive: mismo hash ----------
ing CLI-002a build --data-dir "$D"
aeq "build rc" 0 "$(rc CLI-002a)"
a "build imprime fuentes: 1" grep -qE "fuentes: *1" "$EV/CLI-002a.stdout"
a "build imprime plantas: 2376" grep -qE "plantas: *2376" "$EV/CLI-002a.stdout"
H1=$(hash_of CLI-002a)
ing CLI-002b build --data-dir "$D"; H2=$(hash_of CLI-002b)
ing CLI-002c rederive --data-dir "$D"; H3=$(hash_of CLI-002c)
aeq "rederive rc" 0 "$(rc CLI-002c)"
a "hash presente" test -n "$H1"
aeq "segundo build = primer build" "$H1" "$H2"
aeq "rederive = build" "$H1" "$H3"
aeq "hash = referencia del informe 9.1-9.2" "$REF_HASH" "$H1"
a "rederive imprime plantas: 2376" grep -qE "plantas: *2376" "$EV/CLI-002c.stdout"
fin CLI-002 "build, build y rederive producen el mismo hash (y el de referencia 48d71b6b...)"

# ---------- CLI-003: contenido lógico idéntico a la base real ----------
sqlite3 -readonly "$D/build/catalog.db" .dump > "$EV/CLI-003.temp.dump"
sqlite3 -readonly "$ROOT/data/build/catalog.db" .dump > "$EV/CLI-003.real.dump"
a "volcado lógico de la base temporal == base real" diff -q "$EV/CLI-003.temp.dump" "$EV/CLI-003.real.dump"
rm -f "$EV/CLI-003.temp.dump" "$EV/CLI-003.real.dump"
fin CLI-003 "La base reconstruida en un directorio temporal tiene el mismo volcado SQL que data/build/catalog.db"

# ---------- CLI-004: base neutral solo con esquema neutral; cruda conserva el dataset ----------
TABLES=$(sqlite3 -readonly "$D/build/catalog.db" "select name from sqlite_master where type='table' order by 1" | tr '\n' ' ')
echo "$TABLES" > "$EV/CLI-004.neutral-tables.txt"
a "catalog.db sin tablas raw_*" bash -c "! echo '$TABLES' | grep -q 'raw_'"
a "catalog.db sin términos USDA en nombres de tablas/columnas" bash -c "! sqlite3 -readonly '$D/build/catalog.db' \"select sql from sqlite_master\" | grep -qiE 'usda|fnf|ethnobot|farmacy|duke'"
python3 "$QA/check_raw.py" "$ZIP" "$D/build/raw.db" > "$EV/CLI-004.raw-vs-csv.txt" 2>&1; aeq "capa cruda == CSV (celda a celda)" 0 "$?"
aeq "16 tablas crudas" 16 "$(grep -c '^raw_usda_' "$EV/CLI-004.raw-vs-csv.txt")"
a "raw.db sin tablas neutrales" bash -c "! sqlite3 -readonly '$D/build/raw.db' \"select name from sqlite_master where type='table'\" | grep -qvE '^raw_'"
fin CLI-004 "catalog.db solo esquema neutral; raw.db conserva las 16 tablas del ZIP celda a celda"

# ---------- CLI-005: rederive sin ZIP ni red ----------
mv "$D/.cache" "$D/.cache.off"
ing CLI-005 rederive --data-dir "$D"
aeq "rederive sin .cache rc" 0 "$(rc CLI-005)"
aeq "mismo hash sin ZIP" "$H1" "$(hash_of CLI-005)"
fin CLI-005 "rederive funciona sin el ZIP (solo con raw.db) y da el mismo hash"
mv "$D/.cache.off" "$D/.cache"

# ---------- CLI-006: hash cambia si cambia el contenido crudo ----------
D6="$TMP/data6"; mkdir -p "$D6/build"; cp "$ROOT/data/sources.toml" "$D6/"; cp "$D/build/raw.db" "$D6/build/raw.db"
sqlite3 "$D6/build/raw.db" "update raw_usda_common_names set CNNAM='ZZ cambiado' where _row=1"
ing CLI-006 rederive --data-dir "$D6"
aeq "rederive rc" 0 "$(rc CLI-006)"
a "hash distinto" test "$(hash_of CLI-006)" != "$H1"
a "hash presente" test -n "$(hash_of CLI-006)"
fin CLI-006 "Cambio en un dato del crudo -> hash distinto"

# ---------- CLI-007: build sin .cache ----------
D7="$TMP/data7"; mkdir -p "$D7"; cp "$ROOT/data/sources.toml" "$D7/"
ing CLI-007 build --data-dir "$D7"
aeq "rc" 1 "$(rc CLI-007)"
a "mensaje menciona download" grep -q "download" "$EV/CLI-007.stderr"
a "no deja base" bash -c "[ ! -e '$D7/build/catalog.db' ]"
a "sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/CLI-007.stderr'"
fin CLI-007 "build sin .cache falla (código 1) indicando el paso de descarga y no deja base"

# ---------- CLI-008: rederive sin raw.db ----------
D8="$TMP/data8"; mkdir -p "$D8"; cp "$ROOT/data/sources.toml" "$D8/"
ing CLI-008 rederive --data-dir "$D8"
aeq "rc" 1 "$(rc CLI-008)"
a "mensaje menciona la importación cruda (build)" grep -qiE "build|cruda|raw" "$EV/CLI-008.stderr"
a "no deja base" bash -c "[ ! -e '$D8/build/catalog.db' ]"
a "sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/CLI-008.stderr'"
fin CLI-008 "rederive sin raw.db falla (código 1) indicando la importación cruda y no deja base"

# ---------- CLI-009: insumo alterado ----------
D9="$TMP/data9"; mkdir -p "$D9/.cache"; cp "$ROOT/data/sources.toml" "$D9/"
python3 - "$ZIP" "$D9/.cache/Duke-Source-CSV.zip" <<'EOF'
import sys
b = bytearray(open(sys.argv[1], 'rb').read())
b[1000] ^= 0xFF  # mismo tamaño, distinto contenido
open(sys.argv[2], 'wb').write(b)
EOF
ing CLI-009a build --data-dir "$D9"
aeq "mismo tamaño, checksum distinto: rc" 1 "$(rc CLI-009a)"
a "mensaje menciona checksum o md5" grep -qiE "checksum|md5" "$EV/CLI-009a.stderr"
a "no deja base" bash -c "[ ! -e '$D9/build/catalog.db' ]"
printf 'x' >> "$D9/.cache/Duke-Source-CSV.zip"
ing CLI-009b build --data-dir "$D9"
aeq "tamaño distinto: rc" 1 "$(rc CLI-009b)"
a "mensaje menciona tamaño" grep -qiE "tama" "$EV/CLI-009b.stderr"
: > "$D9/.cache/Duke-Source-CSV.zip"
ing CLI-009c build --data-dir "$D9"
aeq "ZIP vacío: rc" 1 "$(rc CLI-009c)"
a "no deja base ni raw.db utilizable" bash -c "[ ! -e '$D9/build/catalog.db' ]"
for x in a b c; do a "$x sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/CLI-009$x.stderr'"; done
fin CLI-009 "Insumo alterado (checksum, tamaño, vacío): build falla con código 1, lo indica y no deja base"

# ---------- CLI-010: un build fallido no destruye una base previa ni deja parciales ----------
D10="$TMP/data10"; mkdir -p "$D10/.cache"; cp "$ROOT/data/sources.toml" "$D10/"; cp "$ZIP" "$D10/.cache/"
ing CLI-010a build --data-dir "$D10"
M0=$(md5 -q "$D10/build/catalog.db")
printf 'x' >> "$D10/.cache/Duke-Source-CSV.zip"
ing CLI-010b build --data-dir "$D10"
aeq "build corrupto rc" 1 "$(rc CLI-010b)"
echo "catalog.db tras fallo: existe=$([ -e "$D10/build/catalog.db" ] && echo sí || echo no) md5_igual=$([ -e "$D10/build/catalog.db" ] && [ "$(md5 -q "$D10/build/catalog.db")" = "$M0" ] && echo sí || echo no)" > "$EV/CLI-010.note"
ls -la "$D10/build" >> "$EV/CLI-010.note"
a "no quedan archivos temporales en build/" bash -c "[ \"\$(ls -A '$D10/build' | grep -vcE '^(catalog|raw)\.db$')\" = 0 ]"
fin CLI-010 "Tras un build fallido sobre un directorio con base previa no quedan temporales (ver CLI-010.note)"

# ---------- CLI-011: configuración de fuentes ----------
D11="$TMP/data11"; mkdir -p "$D11/.cache"; cp "$ZIP" "$D11/.cache/"
printf '[[sources]]\nid = "no-existe"\npriority = 1\n' > "$D11/sources.toml"
ing CLI-011a build --data-dir "$D11"
aeq "fuente desconocida: rc" 1 "$(rc CLI-011a)"
a "identifica la fuente" grep -q "no-existe" "$EV/CLI-011a.stderr"
rm -f "$D11/sources.toml"
ing CLI-011b build --data-dir "$D11"
aeq "sin sources.toml: rc" 1 "$(rc CLI-011b)"
a "mensaje no vacío" test -s "$EV/CLI-011b.stderr"
printf '[[sources\nid=' > "$D11/sources.toml"
ing CLI-011c build --data-dir "$D11"
aeq "TOML inválido: rc" 1 "$(rc CLI-011c)"
printf '' > "$D11/sources.toml"
ing CLI-011d build --data-dir "$D11"
echo "sources.toml vacío -> rc=$(rc CLI-011d)" > "$EV/CLI-011.note"; cat "$EV/CLI-011d.stdout" "$EV/CLI-011d.stderr" >> "$EV/CLI-011.note"
printf '[[sources]]\nid = "usda"\npriority = 1\n[[sources]]\nid = "usda"\npriority = 2\n' > "$D11/sources.toml"
ing CLI-011e build --data-dir "$D11"
echo "usda duplicada -> rc=$(rc CLI-011e)" >> "$EV/CLI-011.note"; cat "$EV/CLI-011e.stdout" "$EV/CLI-011e.stderr" >> "$EV/CLI-011.note"
for x in a b c; do a "$x sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/CLI-011$x.stderr'"; done
fin CLI-011 "Configuración de fuentes inválida (fuente desconocida, archivo ausente, TOML inválido) falla con código 1 y mensaje"

# ---------- CLI-012: argumentos ----------
ing CLI-012a
ing CLI-012b nope
ing CLI-012c build --data-dir
ing CLI-012d --help
{ for x in a b c d; do echo "CLI-012$x rc=$(rc CLI-012$x)"; done; } > "$EV/CLI-012.note"
a "sin subcomando: rc != 0" test "$(rc CLI-012a)" != 0
a "subcomando desconocido: rc != 0" test "$(rc CLI-012b)" != 0
a "--data-dir sin valor: rc != 0" test "$(rc CLI-012c)" != 0
aeq "--help rc" 0 "$(rc CLI-012d)"
for x in a b c; do a "$x sin pánico" bash -c "! grep -qiE 'panicked|backtrace' '$EV/CLI-012$x.stderr'"; done
fin CLI-012 "Argumentos inválidos terminan con código distinto de 0 y sin pánico; --help sale con 0"

# ---------- CLI-013: base real intacta ----------
aeq "md5 catalog.db real" 29869f77ebc296c8abdd094c0286e98f "$(md5 -q "$ROOT/data/build/catalog.db")"
fin CLI-013 "data/build/catalog.db no cambió durante las pruebas de la CLI"

echo; awk -F'\t' '{c[$2]++} END{for(k in c) print k, c[k]}' "$RES"
echo "tmp: $TMP"
