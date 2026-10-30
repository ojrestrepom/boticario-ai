#!/usr/bin/env bash
# Pruebas de la API del catálogo con curl + jq + sqlite3 (solo lectura).
# Uso: PORT=18100 qa/run-api-tests.sh   (la API ya debe estar en marcha en 127.0.0.1:$PORT)
# Salida: evidence/<caso>.{headers,body} por petición y evidence/results-api.tsv con PASS/FAIL por caso.
set -u
QA="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$QA/../../../.." && pwd)"
EV="${EV_DIR:-$QA/evidence}"
PORT="${PORT:-18100}"
B="http://127.0.0.1:$PORT"
DB="$ROOT/data/build/catalog.db"
RES="$EV/results-api.tsv"
mkdir -p "$EV"
: > "$RES"
FAILS=""

sq() { sqlite3 -readonly "$DB" "$@"; }

# req ID [curl args...]  -> guarda cabeceras y cuerpo, imprime el código HTTP
req() {
  local id="$1"; shift
  curl -s --path-as-is -D "$EV/$id.headers" -o "$EV/$id.body" -w '%{http_code}' "$@"
}
hdr() { # hdr ID nombre
  grep -i "^$2:" "$EV/$1.headers" | head -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//'
}
# a "descripción" comando...  -> registra fallo si el comando devuelve != 0
a() { local d="$1"; shift; if ! "$@" >/dev/null 2>&1; then FAILS="$FAILS; $d"; fi; }
aeq() { # aeq desc esperado obtenido
  if [ "$2" != "$3" ]; then FAILS="$FAILS; $1 (esperado '$2', obtenido '$3')"; fi
}
fin() { # fin ID título
  if [ -z "$FAILS" ]; then printf '%s\tPASS\t%s\t\n' "$1" "$2" >> "$RES"; echo "PASS $1 $2";
  else printf '%s\tFAIL\t%s\t%s\n' "$1" "$2" "${FAILS#; }" >> "$RES"; echo "FAIL $1 $2 :: ${FAILS#; }"; fi
  FAILS=""
}
jqb() { jq -e "$2" "$EV/$1.body" >/dev/null 2>&1; } # jqb ID filtro

DB_MD5_BEFORE=$(md5 -q "$DB")

# ---------- Salud y fuentes ----------
c=$(req API-001 "$B/healthz"); aeq "código" 200 "$c"
aeq "content-type" "application/json" "$(hdr API-001 content-type)"
a "cuerpo {status:ok}" jqb API-001 '. == {"status":"ok"}'
fin API-001 "GET /healthz responde 200 con status ok"

c=$(req API-002 "$B/v1/sources"); aeq "código" 200 "$c"
aeq "content-type" "application/json" "$(hdr API-002 content-type)"
a "una entrada" jqb API-002 'length == 1'
a "campos exactos" jqb API-002 '.[0] | keys == ["checksum","citation","id","license","name","url","version"]'
a "usda y CC0" jqb API-002 '.[0].id == "usda" and .[0].license == "CC0"'
sq -json "select id,name,version,license,citation,url,checksum from source" | jq -cS '.' > "$EV/API-002.expected.json"
jq -cS '.' "$EV/API-002.body" > "$EV/API-002.actual.json"
a "coincide con la base" diff -q "$EV/API-002.expected.json" "$EV/API-002.actual.json"
fin API-002 "GET /v1/sources trae usda/CC0 y coincide con la base"

# ---------- Listado ----------
c=$(req API-003 "$B/v1/plants"); aeq "código" 200 "$c"
aeq "content-type" "application/json" "$(hdr API-003 content-type)"
a "total 2376" jqb API-003 '.total == 2376'
a "20 items" jqb API-003 '(.items|length) == 20'
a "limit/offset ecoados" jqb API-003 '.limit == 20 and .offset == 0'
a "claves de página" jqb API-003 '(keys|sort) == ["items","limit","offset","total"]'
a "primer id" jqb API-003 '.items[0].id == "abelmoschus-esculentus"'
a "orden por nombre científico" jqb API-003 '[.items[].scientificName] == ([.items[].scientificName]|sort)'
fin API-003 "Listado sin q: 20 elementos, total 2376, orden por nombre científico"

a "claves del elemento" jqb API-003 'all(.items[]; (keys|sort) == ["commonNames","family","id","scientificName"])'
a "commonNames {text,language}" jqb API-003 'all(.items[].commonNames[]; (keys|sort) == ["language","text"])'
a "family string o null" jqb API-003 'all(.items[]; .family == null or (.family|type) == "string")'
c=$(req API-004 "$B/v1/plants?q=aspidixia%20angulata"); aeq "código" 200 "$c"
a "family null presente como clave" jqb API-004 '.items[0] | has("family") and .family == null'
fin API-004 "Elemento: id, nombre científico, nombres comunes con idioma y family (null si no existe)"

# Recorrido completo limit=100
: > "$EV/API-005.walk.ids"
ok_walk=1
for off in $(seq 0 100 2400); do
  c=$(req API-005 "$B/v1/plants?limit=100&offset=$off")
  [ "$c" = 200 ] || ok_walk=0
  jq -r '.items[].id' "$EV/API-005.body" >> "$EV/API-005.walk.ids"
done
mv "$EV/API-005.body" "$EV/API-005.lastpage.body"
n=$(wc -l < "$EV/API-005.walk.ids" | tr -d ' ')
aeq "elementos recorridos" 2376 "$n"
aeq "sin repetidos" 2376 "$(sort -u "$EV/API-005.walk.ids" | wc -l | tr -d ' ')"
aeq "todas las páginas 200" 1 "$ok_walk"
sq "select id from plant order by scientific_name, id" > "$EV/API-005.expected.ids"
a "mismo orden que scientific_name,id de la base" diff -q "$EV/API-005.walk.ids" "$EV/API-005.expected.ids"
sq "select id from plant order by id" > "$EV/API-005.allids.sorted"
sort "$EV/API-005.walk.ids" > "$EV/API-005.walk.sorted"
a "ninguna planta omitida" diff -q "$EV/API-005.walk.sorted" "$EV/API-005.allids.sorted"
fin API-005 "Recorrido completo limit=100: 2376 elementos únicos, sin omisiones, orden total"

# Desplazamiento
c=$(req API-006 "$B/v1/plants?limit=5&offset=10"); aeq "código" 200 "$c"
jq -r '.items[].id' "$EV/API-006.body" > "$EV/API-006.ids"
sed -n '11,15p' "$EV/API-005.walk.ids" > "$EV/API-006.expected.ids"
a "elementos 11..15" diff -q "$EV/API-006.ids" "$EV/API-006.expected.ids"
a "eco" jqb API-006 '.limit == 5 and .offset == 10 and .total == 2376'
fin API-006 "Desplazamiento: limit=5&offset=10 devuelve los elementos 11..15 del orden"

# Offset más allá del total
for o in 2376 5000 2147483647; do
  c=$(req API-007-$o "$B/v1/plants?offset=$o"); aeq "offset=$o código" 200 "$c"
  a "offset=$o lista vacía y total" jqb API-007-$o '.items == [] and .total == 2376'
done
c=$(req API-007-2375 "$B/v1/plants?limit=5&offset=2375"); aeq "offset=2375 código" 200 "$c"
a "offset=2375 un elemento" jqb API-007-2375 '(.items|length) == 1 and .total == 2376'
fin API-007 "offset >= total: lista vacía, total conservado; offset=total-1: 1 elemento"

# Límites válidos
c=$(req API-008-1 "$B/v1/plants?limit=1"); aeq "limit=1" 200 "$c"; a "1 elemento" jqb API-008-1 '(.items|length) == 1'
c=$(req API-008-100 "$B/v1/plants?limit=100"); aeq "limit=100" 200 "$c"; a "100 elementos" jqb API-008-100 '(.items|length) == 100'
fin API-008 "Valores límite válidos de limit (1 y 100)"

# Parámetros inválidos
inval() { # inval ID URL param
  local id="$1" url="$2" p="$3"
  c=$(req "$id" "$B$url"); aeq "$url código" 400 "$c"
  aeq "$url content-type" "application/problem+json" "$(hdr "$id" content-type)"
  a "$url problema con param=$p" jqb "$id" ".status == 400 and .param == \"$p\" and (.title|type)==\"string\" and (.detail|type)==\"string\" and (.type|type)==\"string\""
}
inval API-009-0 "/v1/plants?limit=0" limit
inval API-009-neg "/v1/plants?limit=-1" limit
inval API-009-101 "/v1/plants?limit=101" limit
inval API-009-abc "/v1/plants?limit=abc" limit
inval API-009-empty "/v1/plants?limit=" limit
inval API-009-1e3 "/v1/plants?limit=1e3" limit
inval API-009-1p5 "/v1/plants?limit=1.5" limit
inval API-009-big "/v1/plants?limit=99999999999999999999" limit
inval API-009-i32 "/v1/plants?limit=2147483648" limit
fin API-009 "limit inválido (0, -1, 101, abc, vacío, 1e3, 1.5, desbordado) -> 400 problem+json con param=limit"

inval API-010-neg "/v1/plants?offset=-1" offset
inval API-010-abc "/v1/plants?offset=abc" offset
inval API-010-1p5 "/v1/plants?offset=1.5" offset
inval API-010-empty "/v1/plants?offset=" offset
inval API-010-big "/v1/plants?offset=99999999999999999999" offset
fin API-010 "offset inválido (-1, abc, 1.5, vacío, desbordado) -> 400 problem+json con param=offset"

# q demasiado largo
q200=$(printf 'a%.0s' $(seq 1 200)); q201=$(printf 'a%.0s' $(seq 1 201))
c=$(req API-011-200 "$B/v1/plants?q=$q200"); aeq "q 200 chars" 200 "$c"
inval API-011-201 "/v1/plants?q=$q201" q
a2=$(printf '%%C3%%A1%.0s' $(seq 1 200)); a3=$(printf '%%C3%%A1%.0s' $(seq 1 201))
c=$(req API-011-200mb "$B/v1/plants?q=$a2"); aeq "q 200 caracteres (400 bytes)" 200 "$c"
inval API-011-201mb "/v1/plants?q=$a3" q
sp=$(printf '%%20%.0s' $(seq 1 300))
c=$(req API-011-spaces300 "$B/v1/plants?q=$sp"); echo "q de 300 espacios -> $c" > "$EV/API-011.note"
fin API-011 "q de 200 caracteres admitido (también multibyte), 201 -> 400 con param=q"

# ---------- Búsqueda ----------
exp_total() { sq "select count(distinct plant_id) from plant_name where normalized like '%$1%'"; }
c=$(req API-012 "$B/v1/plants?q=lavandula"); aeq "código" 200 "$c"
aeq "total = base" "$(exp_total lavandula)" "$(jq .total "$EV/API-012.body")"
a "incluye lavandula-angustifolia" jqb API-012 'any(.items[]; .id == "lavandula-angustifolia")'
a "nombre contiene lavandula" jqb API-012 'all(.items[]; ((.scientificName + " " + ([.commonNames[].text]|join(" ")))|ascii_downcase|contains("lavandula")))'
fin API-012 "q=lavandula: plantas con la subcadena y total de la base"

for term in peppermint rosemary; do
  c=$(req API-013-$term "$B/v1/plants?q=$term"); aeq "$term código" 200 "$c"
  aeq "$term total = base" "$(exp_total $term)" "$(jq .total "$EV/API-013-$term.body")"
done
a "peppermint -> mentha-x-piperita-subsp-nothosubsp-piperita" jqb API-013-peppermint 'any(.items[]; .id == "mentha-x-piperita-subsp-nothosubsp-piperita")'
a "rosemary -> rosmarinus-officinalis" jqb API-013-rosemary 'any(.items[]; .id == "rosmarinus-officinalis")'
fin API-013 "Búsqueda por nombre común (peppermint, rosemary)"

norm_eq() { # norm_eq ID urlA urlB
  local id="$1"; req "$id.A" "$B$2" >/dev/null; req "$id.B" "$B$3" >/dev/null
  a "$2 vs $3" diff -q <(jq -cS . "$EV/$id.A.body") <(jq -cS . "$EV/$id.B.body")
  a "$2 no vacío" jqb "$id.A" '.total > 0'
}
norm_eq API-014-a "/v1/plants?q=LAV%C3%81NDULA" "/v1/plants?q=lavandula"
norm_eq API-014-b "/v1/plants?q=%20%20lavandula%20%20" "/v1/plants?q=lavandula"
norm_eq API-014-c "/v1/plants?q=LaVaNdUlA" "/v1/plants?q=lavandula"
norm_eq API-014-d "/v1/plants?q=blue%20%20%20gum" "/v1/plants?q=blue%20gum"
norm_eq API-014-e "/v1/plants?q=%20%20BLUE%20%20%20Gum%20" "/v1/plants?q=blue%20gum"
norm_eq API-014-f "/v1/plants?q=Lavandula%20Angustifolia" "/v1/plants?q=lavandula%20angustifolia"
norm_eq API-014-g "/v1/plants?q=lava%CC%81ndula" "/v1/plants?q=lavandula"
req API-014-h.A "$B/v1/plants?q=%C2%A0lavandula%C2%A0" >/dev/null
echo "q con NBSP exteriores: total $(jq .total "$EV/API-014-h.A.body") (lavandula: $(jq .total "$EV/API-014-a.B.body"))" > "$EV/API-014.note"
fin API-014 "Insensibilidad a mayúsculas, acentos (NFC y NFD) y espacios repetidos o exteriores"

req API-015.ref "$B/v1/plants" >/dev/null
for v in "q=" "q=%20" "q=%20%20%20" "q=+"; do
  id="API-015.$(echo "$v" | tr -c 'A-Za-z0-9' '_')"
  req "$id" "$B/v1/plants?$v" >/dev/null
  a "$v igual que sin q" diff -q <(jq -cS . "$EV/$id.body") <(jq -cS . "$EV/API-015.ref.body")
done
fin API-015 "q vacío o solo espacios == sin q"

c=$(req API-016-pct "$B/v1/plants?q=%25"); aeq "q=% código" 200 "$c"
aeq "q=% total = base" "$(sq "select count(distinct plant_id) from plant_name where instr(normalized,'%')>0")" "$(jq .total "$EV/API-016-pct.body")"
c=$(req API-016-us "$B/v1/plants?q=_"); aeq "q=_ código" 200 "$c"
aeq "q=_ total = base" "$(sq "select count(distinct plant_id) from plant_name where instr(normalized,'_')>0")" "$(jq .total "$EV/API-016-us.body")"
a "q=_ no es comodín (total < 2376)" jqb API-016-us '.total < 2376'
c=$(req API-016-tea "$B/v1/plants?q=Tea_tree"); aeq "q=Tea_tree" 200 "$c"
a "Tea_tree encuentra Paperbark Tea_tree" jqb API-016-tea '.total >= 1 and any(.items[]; any(.commonNames[]; .text == "Paperbark Tea_tree"))'
c=$(req API-016-tea2 "$B/v1/plants?q=Tea%25tree"); aeq "q=Tea%tree" 200 "$c"; a "Tea%tree 0" jqb API-016-tea2 '.total == 0'
c=$(req API-016-tea3 "$B/v1/plants?q=Tea_tre_"); aeq "q=Tea_tre_" 200 "$c"; a "Tea_tre_ 0 (no comodín)" jqb API-016-tea3 '.total == 0'
c=$(req API-016-bs "$B/v1/plants?q=%5C"); aeq "q=\\ código" 200 "$c"
aeq "q=\\ total = base" "$(sq "select count(distinct plant_id) from plant_name where instr(normalized,char(92))>0")" "$(jq .total "$EV/API-016-bs.body")"
c=$(req API-016-pct2 "$B/v1/plants?q=%25%25"); aeq "q=%% código" 200 "$c"; a "q=%% 0" jqb API-016-pct2 '.total == 0'
fin API-016 "% y _ (y \\) son texto literal; Paperbark Tea_tree se encuentra"

c=$(req API-017 "$B/v1/plants?q=zzzzqqqq"); aeq "código" 200 "$c"
a "vacío y total 0" jqb API-017 '.items == [] and .total == 0'
aeq "content-type" "application/json" "$(hdr API-017 content-type)"
fin API-017 "Sin coincidencias: 200, lista vacía, total 0"

: > "$EV/API-018.ids"; tot=$(curl -s "$B/v1/plants?q=a&limit=1" | jq .total)
for off in $(seq 0 50 "$tot"); do curl -s "$B/v1/plants?q=a&limit=50&offset=$off" | jq -r '.items[].id' >> "$EV/API-018.ids"; done
aeq "recorrido q=a = total" "$tot" "$(wc -l < "$EV/API-018.ids" | tr -d ' ')"
aeq "sin repetidos q=a" "$tot" "$(sort -u "$EV/API-018.ids" | wc -l | tr -d ' ')"
aeq "total q=a = base" "$(exp_total a)" "$tot"
fin API-018 "Paginación estable dentro de una búsqueda (q=a, limit=50)"

# ---------- Detalle ----------
detail_truth() {
  sq "select json_object(
    'family', (select family from plant where id='$1'),
    'names', (select count(*) from plant_name where plant_id='$1'),
    'parts', (select count(*) from plant_part where plant_id='$1'),
    'uses', (select count(*) from plant_use where plant_id='$1'))"
}
for id in lavandula-angustifolia eucalyptus-globulus rosmarinus-officinalis matricaria-recutita mentha-x-piperita-subsp-nothosubsp-piperita; do
  c=$(req API-019-$id "$B/v1/plants/$id"); aeq "$id código" 200 "$c"
  aeq "$id content-type" "application/json" "$(hdr API-019-$id content-type)"
  t=$(detail_truth $id)
  aeq "$id usos" "$(echo "$t" | jq .uses)" "$(jq '.uses|length' "$EV/API-019-$id.body")"
  aeq "$id partes" "$(echo "$t" | jq .parts)" "$(jq '.parts|length' "$EV/API-019-$id.body")"
  aeq "$id nombres" "$(echo "$t" | jq .names)" "$(jq '.names|length' "$EV/API-019-$id.body")"
  aeq "$id familia" "$(echo "$t" | jq -r .family)" "$(jq -r '.family.value' "$EV/API-019-$id.body")"
  a "$id claves" jqb API-019-$id '(keys|sort) == ["family","id","names","parts","scientificName","uses"]'
  a "$id atribución en todo dato" jqb API-019-$id 'all(.names[]; (.sources|length)>0) and all(.parts[]; (.sources|length)>0) and all(.uses[]; (.sources|length)>0) and (.family.sources|length)>0'
  a "$id claves de uso" jqb API-019-$id 'all(.uses[]; (keys|sort)==["activity","language","reference","sources"] and (.reference|keys|sort)==["citation","id"])'
  a "$id claves de nombre" jqb API-019-$id 'all(.names[]; (keys|sort)==["kind","language","sources","text"])'
done
a "lavandula 10 usos 4 partes" jqb API-019-lavandula-angustifolia '(.uses|length)==10 and (.parts|length)==4'
a "lavandula nombre común English Lavender (en)" jqb API-019-lavandula-angustifolia 'any(.names[]; .text=="English Lavender" and .kind=="common" and .language=="en")'
a "eucalyptus 49 usos 15 partes" jqb API-019-eucalyptus-globulus '(.uses|length)==49 and (.parts|length)==15'
fin API-019 "Detalle de plantas de referencia coincide con la base (conteos, familia, atribución, claves)"

sq -json "select pu.activity as activity, pu.language as language, r.id as rid, r.citation as citation from plant_use pu join reference r on r.id=pu.reference_id where pu.plant_id='lavandula-angustifolia'" | jq -cS 'sort_by(.activity,.rid)' > "$EV/API-020.expected-uses.json"
jq -cS '[.uses[]|{activity,language,rid:.reference.id,citation:.reference.citation}]|sort_by(.activity,.rid)' "$EV/API-019-lavandula-angustifolia.body" > "$EV/API-020.actual-uses.json"
a "usos idénticos a la base" diff -q "$EV/API-020.expected-uses.json" "$EV/API-020.actual-uses.json"
sq "select label from plant_part where plant_id='lavandula-angustifolia' order by label" > "$EV/API-020.expected-parts.txt"
jq -r '.parts[].label' "$EV/API-019-lavandula-angustifolia.body" | sort > "$EV/API-020.actual-parts.txt"
a "partes idénticas a la base" diff -q "$EV/API-020.expected-parts.txt" "$EV/API-020.actual-parts.txt"
sq "select text||'|'||kind||'|'||language from plant_name where plant_id='lavandula-angustifolia' order by 1" > "$EV/API-020.expected-names.txt"
jq -r '.names[]|.text+"|"+.kind+"|"+.language' "$EV/API-019-lavandula-angustifolia.body" | sort > "$EV/API-020.actual-names.txt"
a "nombres idénticos a la base" diff -q "$EV/API-020.expected-names.txt" "$EV/API-020.actual-names.txt"
fin API-020 "Detalle de lavandula-angustifolia idéntico a la base (usos+citas, partes, nombres)"

a "matricaria uses == []" jqb API-019-matricaria-recutita '.uses == []'
a "matricaria con partes" jqb API-019-matricaria-recutita '(.parts|length)==3'
a "mentha uses == []" jqb API-019-mentha-x-piperita-subsp-nothosubsp-piperita '.uses == []'
fin API-021 "Planta sin usos: lista de usos vacía"

for id in $(sq "select id from plant where family is null limit 3"); do
  c=$(req API-022-$id "$B/v1/plants/$id"); aeq "$id código" 200 "$c"
  a "$id family null" jqb API-022-$id 'has("family") and .family == null'
  a "$id tiene nombres" jqb API-022-$id '(.names|length)>=1'
done
fin API-022 "Planta sin familia: family == null en el detalle"

c=$(req API-023 "$B/v1/plants/no-existe"); aeq "código" 404 "$c"
aeq "content-type" "application/problem+json" "$(hdr API-023 content-type)"
a "problema 404" jqb API-023 '.status==404 and (.title|type)=="string" and (.detail|type)=="string" and (.type|type)=="string"'
fin API-023 "Id inexistente: 404 problem+json"

: > "$EV/API-024.note"
for p in "/nada" "/v1/nada" "/v1" "/v2/plants" "/v1/plants/" "/V1/plants" "/healthz/x" "/v1/plants/a/b" "/v1/sources/usda" "/"; do
  id="API-024.$(echo "$p" | tr -c 'A-Za-z0-9' '_')"
  c=$(req "$id" "$B$p")
  echo "$p -> $c ($(hdr $id content-type))" >> "$EV/API-024.note"
  aeq "$p código" 404 "$c"
  aeq "$p content-type" "application/problem+json" "$(hdr "$id" content-type)"
done
fin API-024 "Ruta desconocida: 404 problem+json"

for m in POST PUT DELETE PATCH; do
  for p in /v1/plants /v1/plants/lavandula-angustifolia /v1/sources; do
    id="API-025.$m.$(echo "$p" | tr -c 'A-Za-z0-9' '_')"
    c=$(req "$id" -X $m "$B$p" -H 'content-type: application/json' -d '{"id":"x"}')
    aeq "$m $p código" 405 "$c"
    aeq "$m $p content-type" "application/problem+json" "$(hdr "$id" content-type)"
    aeq "$m $p Allow" "GET" "$(hdr "$id" allow)"
    a "$m $p problema 405" jqb "$id" '.status==405'
  done
  for p in /healthz /openapi.json; do
    id="API-025.$m.$(echo "$p" | tr -c 'A-Za-z0-9' '_')"
    c=$(req "$id" -X $m "$B$p")
    aeq "$m $p código" 405 "$c"
    aeq "$m $p content-type" "application/problem+json" "$(hdr "$id" content-type)"
  done
done
fin API-025 "POST/PUT/DELETE/PATCH -> 405 problem+json con Allow: GET (recursos de /v1, /healthz y /openapi.json)"

: > "$EV/API-026.note"
for m in HEAD OPTIONS; do
  for p in /v1/plants /healthz; do
    id="API-026.$m.$(echo "$p" | tr -c 'A-Za-z0-9' '_')"
    if [ $m = HEAD ]; then c=$(curl -s -I -D "$EV/$id.headers" -o /dev/null -w '%{http_code}' "$B$p"); else c=$(req "$id" -X OPTIONS "$B$p"); fi
    echo "$m $p -> $c allow=$(hdr $id allow) ct=$(hdr $id content-type)" >> "$EV/API-026.note"
  done
done
fin API-026 "HEAD/OPTIONS observados (ver API-026.note)"

c=$(req API-027 "$B/openapi.json"); aeq "código" 200 "$c"
aeq "content-type" "application/json" "$(hdr API-027 content-type)"
a "JSON == backend/openapi.json" diff -q <(jq -S . "$EV/API-027.body") <(jq -S . "$ROOT/backend/openapi.json")
a "openapi 3.1" jqb API-027 '.openapi|startswith("3.1")'
fin API-027 "/openapi.json 200 y JSON idéntico a backend/openapi.json"

bad=$(for f in "$EV"/API-003.body "$EV"/API-005.lastpage.body "$EV"/API-019-*.body "$EV"/API-002.body "$EV"/API-023.body "$EV"/API-009-0.body; do jq -r '[paths|map(select(type=="string"))|.[]]|.[]' "$f"; done | sort -u | grep -vE '^[a-z][A-Za-z0-9]*$' || true)
aeq "claves que no son camelCase" "" "$bad"
fin API-028 "Todas las claves JSON en camelCase"

# ---------- Barrido completo de detalle ----------
sweep_bad=0
: > "$EV/API-029.sweep.tsv"; : > "$EV/API-029.errors"
while read -r id; do
  c=$(curl -s -o "$EV/API-029.tmp" -w '%{http_code}' "$B/v1/plants/$id")
  if [ "$c" != 200 ]; then sweep_bad=$((sweep_bad+1)); echo "$id $c" >> "$EV/API-029.errors"; continue; fi
  jq -r --arg id "$id" '[$id, (.uses|length), (.parts|length), (.names|length), (.family==null), ([.names[],.parts[],.uses[]]|all(.sources|length>0)), (.id==$id)]|@tsv' "$EV/API-029.tmp" >> "$EV/API-029.sweep.tsv"
done < "$EV/API-005.expected.ids"
rm -f "$EV/API-029.tmp"
aeq "detalles no-200" 0 "$sweep_bad"
aeq "peticiones" 2376 "$(wc -l < "$EV/API-029.sweep.tsv" | tr -d ' ')"
aeq "suma de usos" "$(sq "select count(*) from plant_use")" "$(awk '{s+=$2} END{print s}' "$EV/API-029.sweep.tsv")"
aeq "suma de partes" "$(sq "select count(*) from plant_part")" "$(awk '{s+=$3} END{print s}' "$EV/API-029.sweep.tsv")"
aeq "suma de nombres" "$(sq "select count(*) from plant_name")" "$(awk '{s+=$4} END{print s}' "$EV/API-029.sweep.tsv")"
aeq "familia null" 34 "$(awk '$5=="true"' "$EV/API-029.sweep.tsv" | wc -l | tr -d ' ')"
aeq "plantas con usos" 1180 "$(awk '$2>0' "$EV/API-029.sweep.tsv" | wc -l | tr -d ' ')"
aeq "todo dato con fuente" 0 "$(awk '$6!="true"' "$EV/API-029.sweep.tsv" | wc -l | tr -d ' ')"
aeq "id coincide" 0 "$(awk '$7!="true"' "$EV/API-029.sweep.tsv" | wc -l | tr -d ' ')"
fin API-029 "Barrido de las 2376 plantas: todas 200; 18931 usos, 6740 partes, 5296 nombres; 1180 con usos; 34 sin familia"

# ---------- Robustez ----------
: > "$EV/API-030.note"
rb() { # rb ID URL [curl args]
  local id="$1" url="$2"; shift 2
  local c; c=$(req "$id" "$B$url" "$@")
  echo "$id ${url:0:90} -> $c ct=$(hdr "$id" content-type) bodybytes=$(wc -c < "$EV/$id.body" | tr -d " ")" >> "$EV/API-030.note"
  case "$c" in 5*) FAILS="$FAILS; $url devolvió $c";; esac
}
rb API-030-ff "/v1/plants/%FF"
rb API-030-ffq "/v1/plants?q=%FF"
rb API-030-sp "/v1/plants/a%20b"
rb API-030-nul "/v1/plants/a%00b"
rb API-030-nulq "/v1/plants?q=a%00b"
rb API-030-dots "/v1/plants/..%2f..%2fetc%2fpasswd"
rb API-030-dots2 "/v1/plants/%2e%2e"
rb API-030-slash "/v1/plants/a%2Fb"
rb API-030-upper "/v1/plants/LAVANDULA-ANGUSTIFOLIA"
rb API-030-uni "/v1/plants/l%C3%A1vandula"
rb API-030-sqli "/v1/plants?q=%27%3B%20drop%20table%20plant%3B--"
rb API-030-sqli2 "/v1/plants/%27%20or%201%3D1--"
rb API-030-emoji "/v1/plants?q=%F0%9F%8C%BF"
long1k=$(printf 'a%.0s' $(seq 1 1000)); long10k=$(printf 'a%.0s' $(seq 1 10000)); long100k=$(printf 'a%.0s' $(seq 1 100000))
rb API-030-id1k "/v1/plants/$long1k"
rb API-030-id10k "/v1/plants/$long10k"
rb API-030-id100k "/v1/plants/$long100k"
rb API-030-q10k "/v1/plants?q=$long10k"
rb API-030-rep1 "/v1/plants?limit=1&limit=2"
rb API-030-rep2 "/v1/plants?q=lavandula&q=rosemary"
rb API-030-rep3 "/v1/plants?offset=1&offset=x"
rb API-030-unk "/v1/plants?foo=bar&limit=3"
rb API-030-case "/v1/plants?LIMIT=3&Q=lavandula"
rb API-030-acc1 "/v1/plants?limit=1" -H 'Accept: text/html'
rb API-030-acc2 "/v1/plants?limit=1" -H 'Accept: application/xml'
rb API-030-acc3 "/v1/plants?limit=1" -H 'Accept: */*'
rb API-030-acc4 "/v1/plants?limit=1" -H 'Accept: ;;;garbage'
rb API-030-acc5 "/v1/plants/nope" -H 'Accept: text/html'
rb API-030-acc6 "/v1/plants?limit=0" -H 'Accept: application/json'
rb API-030-plus "/v1/plants?q=blue+gum"
rb API-030-hash "/v1/plants?q=a#frag"
rb API-030-pct1 "/v1/plants?limit=%31"
rb API-030-lim0pad "/v1/plants?limit=007"
rb API-030-limplus "/v1/plants?limit=%2B5"
rb API-030-gzip "/v1/plants?limit=1" -H 'Accept-Encoding: gzip, br'
rb API-030-bodyget "/v1/plants?limit=1" -X GET -d 'x=1'
for f in "$EV"/API-030-*.body; do if [ "$(wc -c < "$f")" -gt 20000 ]; then (head -c 300 "$f"; echo; echo "[...recortado: $(wc -c < "$f") bytes]") > "$f.tmp"; mv "$f.tmp" "$f"; fi; done
leak=$(grep -liE 'sqlite|diesel|/Users/|\.rs:|panicked|catalog\.db|SELECT ' "$EV"/API-030-*.body 2>/dev/null || true)
aeq "fugas de detalles internos" "" "$leak"
fin API-030 "Robustez: ningún 5xx ni fuga de detalles internos (códigos observados en API-030.note)"

aeq "404 con Accept text/html: content-type" "application/problem+json" "$(hdr API-030-acc5 content-type)"
aeq "400 con Accept json: content-type" "application/problem+json" "$(hdr API-030-acc6 content-type)"
fin API-031 "Errores conservan application/problem+json con Accept inesperado"

a "404 instance = ruta" jqb API-023 '.instance=="/v1/plants/no-existe"'
a "400 param/instance" jqb API-009-0 '.param=="limit" and (.instance|startswith("/v1/plants"))'
fin API-032 "Cuerpo de error: type, title, status, detail, param e instance (RFC 9457)"

DB_MD5_AFTER=$(md5 -q "$DB")
aeq "md5 de la base inalterado" "$DB_MD5_BEFORE" "$DB_MD5_AFTER"
a "no hay -wal/-journal/-shm" bash -c "! ls '$DB'-wal '$DB'-journal '$DB'-shm 2>/dev/null | grep -q ."
fin API-033 "Ninguna petición modifica la base (md5 antes/después, sin archivos -wal/-journal)"

# offset frente al formato int32 declarado en el OpenAPI
c=$(req API-034 "$B/v1/plants?offset=2147483648&limit=1")
aeq "offset=2147483648 debe ser 400" 400 "$c"
a "problema con param=offset" jqb API-034 '.status==400 and .param=="offset"'
aeq "content-type" "application/problem+json" "$(hdr API-034 content-type)"
c=$(req API-034.max "$B/v1/plants?offset=2147483647&limit=1"); aeq "offset=2147483647 debe ser 200" 200 "$c"
a "offset=2147483647 lista vacía y total 2376" jqb API-034.max '.items==[] and .total==2376 and .offset==2147483647'
c=$(req API-034.u32 "$B/v1/plants?offset=4294967295&limit=1"); aeq "offset=4294967295 debe ser 400" 400 "$c"
c=$(req API-034.big "$B/v1/plants?offset=4294967296&limit=1"); aeq "offset=4294967296 debe ser 400" 400 "$c"
fin API-034 "offset respeta el formato int32 del OpenAPI: 200 hasta 2147483647, 400 con param=offset desde 2147483648"

: > "$EV/API-035.note"
for u in "%00zzzz" "a%00zzzz" "lavandula%00zzzz" "a%00" "%0A" "a%0Ab" "%09" "blue%09gum" "%1F" "%7F" "%C2%85"; do
  id="API-035.$(printf '%s' "$u" | tr -c 'A-Za-z0-9' '_')"
  c=$(req "$id" "$B/v1/plants?q=$u&limit=1")
  echo "q=$u -> $c" >> "$EV/API-035.note"
  aeq "q=$u código" 400 "$c"
  aeq "q=$u content-type" "application/problem+json" "$(hdr "$id" content-type)"
  a "q=$u param=q" jqb "$id" '.status==400 and .param=="q"'
done
c=$(req API-035.nbsp "$B/v1/plants?q=%C2%A0lavandula%C2%A0&limit=1"); aeq "NBSP exteriores sigue 200" 200 "$c"
fin API-035 "q con NUL u otro carácter de control (incluidos tab, LF, DEL) -> 400 con param=q"

# OpenAPI frente al comportamiento real
OA="$ROOT/backend/openapi.json"
a "405 documentado en todas las rutas" jq -e '[.paths[]|.get.responses|has("405")]|all' "$OA"
a "405 con application/problem+json" jq -e '[.paths[]|.get.responses["405"].content|has("application/problem+json")]|all' "$OA"
a "/openapi.json es ruta del documento" jq -e '.paths|has("/openapi.json")' "$OA"
a "info.description menciona el 404 de rutas desconocidas" jq -e '.info.description|test("404")' "$OA"
a "404 por ruta solo en /v1/plants/{id}" jq -e '[.paths|to_entries[]|select(.value.get.responses|has("404"))|.key]==["/v1/plants/{id}"]' "$OA"
jq -r '.info.description' "$OA" > "$EV/API-036.info-description.txt"
c=$(req API-036.served "$B/openapi.json"); a "el servido coincide con el versionado" diff -q <(jq -S . "$EV/API-036.served.body") <(jq -S . "$OA")
fin API-036 "El OpenAPI documenta el 405 en todas las rutas, /openapi.json y el 404 de rutas desconocidas (info.description)"

echo; echo "Resultados en $RES"
awk -F'\t' '{c[$2]++} END{for(k in c) print k, c[k]}' "$RES"
