#!/usr/bin/env python3 -I
"""10.3: pruebas de la API local contra la base nueva y el contrato de backend/openapi.json.

Entorno:
  QA_TOKEN   token de prueba valido (nunca se escribe en la evidencia: se sustituye por <token>)
  QA_BASE    URL base (por defecto http://127.0.0.1:8080)
  QA_DB      ruta de la base nueva (solo lectura, para comparar)
  QA_OLD_MAP evidence/ids/id-map.tsv (de compare_bases.py), para la busqueda por nombres anteriores
Uso: api_tests.py <repo> <carpeta de evidencia>
"""
import csv, json, os, re, sqlite3, sys, time, urllib.parse, urllib.request, urllib.error, pathlib, collections, unicodedata

REPO = pathlib.Path(sys.argv[1]); EV = pathlib.Path(sys.argv[2]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080")
TOKEN = os.environ["QA_TOKEN"]
DB = os.environ["QA_DB"]
OLD_MAP = os.environ.get("QA_OLD_MAP")
SPEC = json.load(open(REPO / "backend" / "openapi.json"))

# ---------- validador minimo de JSON Schema / OpenAPI 3.1 (lo que usa openapi.json) ----------
def resolve(s):
    while isinstance(s, dict) and "$ref" in s:
        s = SPEC["components"]["schemas"][s["$ref"].split("/")[-1]] | {k: v for k, v in s.items() if k != "$ref"}
    return s

def validate(v, schema, path="$"):
    errs = []
    s = resolve(schema)
    t = s.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    def isty(x, ty):
        return {"string": isinstance(x, str), "integer": isinstance(x, int) and not isinstance(x, bool),
                "number": isinstance(x, (int, float)) and not isinstance(x, bool), "boolean": isinstance(x, bool),
                "array": isinstance(x, list), "object": isinstance(x, dict), "null": x is None}[ty]
    if types and not any(isty(v, ty) for ty in types):
        return [f"{path}: tipo {type(v).__name__} no es {types}"]
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: {v!r} fuera de {s['enum']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]: errs.append(f"{path}: {v} < minimo")
        if "maximum" in s and v > s["maximum"]: errs.append(f"{path}: {v} > maximo")
    if isinstance(v, str) and "maxLength" in s and len(v) > s["maxLength"]:
        errs.append(f"{path}: longitud > maxLength")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v: errs.append(f"{path}: falta {r}")
        for k, sub in s.get("properties", {}).items():
            if k in v: errs += validate(v[k], sub, f"{path}.{k}")
        extra = set(v) - set(s.get("properties", {}))
        if extra and s.get("properties") is not None and t == "object":
            errs.append(f"{path}: campos fuera del contrato {sorted(extra)}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            errs += validate(x, s["items"], f"{path}[{i}]")
    return errs

def op_schema(path, method, status):
    c = SPEC["paths"][path][method]["responses"].get(str(status), {}).get("content", {})
    for ct, body in c.items():
        return ct, body.get("schema")
    return None, None

# ---------- http ----------
def get(path, token=TOKEN, headers=None, raw=False):
    h = dict(headers or {})
    if token is not None: h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        status, hd, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, hd, body = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    if raw: return status, hd, body
    try: j = json.loads(body)
    except Exception: j = None
    return status, hd, j

def redact(s): return s.replace(TOKEN, "<token>")

# ---------- registro de resultados ----------
results = []  # (caso, estado, detalle)
log = collections.defaultdict(list)
def rec(case, name, ok, detail=""):
    results.append((case, name, "PASA" if ok else "FALLA", detail))
    log[case].append(f"{'PASA ' if ok else 'FALLA'} {name} {detail}")
def obs(case, text): log[case].append("OBS   " + text); results.append((case, text, "OBS", ""))
def dump(case, title, method, path, status, hd, body, limit=3500):
    keep = {k: v for k, v in hd.items() if k.lower() in ("content-type", "www-authenticate", "allow", "content-length")}
    b = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=1) if body is not None else ""
    if len(b) > limit: b = b[:limit] + f"\n... (recortado, {len(b)} caracteres)"
    tok = "Authorization: Bearer <token>\n" if "TOKEN" in title else ""
    log[case].append(redact(f"--- {title}\n{method} {path}\n{tok}-> {status} {json.dumps(keep, ensure_ascii=False)}\n{b}\n"))

def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()

db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
db_ids = [r[0] for r in db.execute("select id from plant order by scientific_name, id")]
db_n = len(db_ids)
db_alias = dict(db.execute("select alias, plant_id from plant_alias"))

# ---------- API-01 listado ----------
c = "API-01"
st, hd, j = get("/v1/plants")
dump(c, "listado por defecto (se recorta)", "GET", "/v1/plants", st, hd, j)
rec(c, "200", st == 200, str(st))
rec(c, "Content-Type application/json", hd.get("content-type", "").startswith("application/json"), hd.get("content-type", ""))
ct, sch = op_schema("/v1/plants", "get", 200)
e = validate(j, sch); rec(c, "respuesta cumple PageDto_PlantSummaryDto", not e, "; ".join(e[:3]))
rec(c, "limit=20 y offset=0 por defecto", j["limit"] == 20 and j["offset"] == 0 and len(j["items"]) == 20, f"limit={j['limit']} offset={j['offset']} n={len(j['items'])}")
rec(c, f"total = plantas de la base ({db_n})", j["total"] == db_n, f"total={j['total']}")
rec(c, "orden por nombre cientifico e id", [i["id"] for i in j["items"]] == db_ids[:20])

# ---------- API-02 paginacion ----------
c = "API-02"
seen = []; totals = set(); pages = 0; off = 0; viol = []
t0 = time.time()
while True:
    st, hd, j = get(f"/v1/plants?limit=100&offset={off}")
    if st != 200: viol.append(f"offset {off}: {st}"); break
    e = validate(j, sch)
    if e: viol.append(f"offset {off}: {e[0]}")
    totals.add(j["total"]); seen += [i["id"] for i in j["items"]]; pages += 1
    if off == 0: dump(c, "primera pagina de 100 (se recorta)", "GET", "/v1/plants?limit=100&offset=0", st, hd, j, 800)
    if len(j["items"]) < 100: break
    off += 100
rec(c, "recorrido completo con limit=100", not viol, "; ".join(viol[:3]) + f" paginas={pages} en {time.time()-t0:.1f}s")
rec(c, "sin duplicados", len(seen) == len(set(seen)), f"{len(seen)} ids, {len(set(seen))} unicos")
rec(c, f"el recorrido cubre exactamente los {db_n} ids de la base y en su orden", seen == db_ids)
rec(c, "total constante en todas las paginas", totals == {db_n}, str(totals))
st, hd, j = get(f"/v1/plants?limit=100&offset={db_n}")
rec(c, "offset = total: 200 con items vacio", st == 200 and j["items"] == [] and j["total"] == db_n, f"{st} {len(j['items'])}")
dump(c, "offset = total", "GET", f"/v1/plants?limit=100&offset={db_n}", st, hd, j)
st, hd, j = get("/v1/plants?limit=1&offset=5")
rec(c, "limit=1 offset=5 devuelve el sexto", st == 200 and [i["id"] for i in j["items"]] == db_ids[5:6])
for q, name in [("limit=0", "limit=0"), ("limit=101", "limit=101"), ("limit=abc", "limit=abc"), ("offset=-1", "offset=-1"), ("limit=", "limit vacio"), ("offset=2147483648", "offset desbordado")]:
    st, hd, j = get("/v1/plants?" + q)
    ct, ps = op_schema("/v1/plants", "get", 400)
    ok = st == 400 and hd.get("content-type", "").startswith("application/problem+json") and not validate(j, ps)
    rec(c, f"{name} -> 400 problem+json", ok, f"{st}")
    dump(c, name, "GET", "/v1/plants?" + q, st, hd, j, 600)

# ---------- API-03 busqueda ----------
c = "API-03"
def search(q, limit=100):
    st, hd, j = get("/v1/plants?" + urllib.parse.urlencode({"q": q, "limit": limit}))
    return st, hd, j
def ids_of(j): return [i["id"] for i in j["items"]]
cases = [
    ("nombre cientifico exacto", "lavandula angustifolia", "lavandula-angustifolia"),
    ("nombre cientifico con mayusculas", "LAVANDULA Angustifolia", "lavandula-angustifolia"),
    ("fragmento cientifico", "angustif", "lavandula-angustifolia"),
    ("sinonimo cientifico (Rosmarinus officinalis)", "rosmarinus officinalis", "salvia-rosmarinus"),
    ("nombre aceptado nuevo", "salvia rosmarinus", "salvia-rosmarinus"),
    ("sinonimo anterior de manzanilla", "matricaria recutita", "matricaria-chamomilla"),
    ("nombre aceptado de manzanilla", "matricaria chamomilla", "matricaria-chamomilla"),
    ("comun es: manzanilla", "manzanilla", "matricaria-chamomilla"),
    ("comun es: menta", "menta", "mentha-x-piperita"),
    ("comun es: lavanda", "lavanda", "lavandula-angustifolia"),
    ("comun es: romero", "romero", "salvia-rosmarinus"),
    ("comun es con acento (hipérico)", "hipérico", "hypericum-perforatum"),
    ("comun es sin acento (hiperico)", "hiperico", "hypericum-perforatum"),
    ("comun es: hierba de san juan", "hierba de san juan", "hypericum-perforatum"),
    ("comun en: English Lavender", "english lavender", "lavandula-angustifolia"),
    ("espacios repetidos y exteriores", "  rosmarinus    officinalis  ", "salvia-rosmarinus"),
    ("sinonimo: Mentha piperita", "mentha piperita", "mentha-x-piperita"),
    ("hibrido escrito con x ASCII (Mentha x piperita)", "mentha x piperita", "mentha-x-piperita"),
    ("hibrido escrito con el signo × (Mentha × piperita)", "mentha × piperita", "mentha-x-piperita"),
]
for name, q, want in cases:
    st, hd, j = search(q)
    ok = st == 200 and want in ids_of(j) and not validate(j, sch)
    rec(c, f"{name}: q={q!r} encuentra {want}", ok, f"{st} total={j['total'] if j else None} posicion={ids_of(j).index(want)+1 if j and want in ids_of(j) else None}")
    dump(c, name, "GET", "/v1/plants?q=" + urllib.parse.quote(q), st, hd, {"total": j and j["total"], "ids": j and ids_of(j)[:12]}, 600)
for name, q in [("sin coincidencias", "zzzzzz"), ("vacio no filtra", ""), ("solo espacios no filtra", "   ")]:
    st, hd, j = search(q, 5)
    if q.strip() == "": rec(c, f"{name}: total = {db_n}", st == 200 and j["total"] == db_n, f"{st} {j and j['total']}")
    else: rec(c, f"{name}: total 0", st == 200 and j["total"] == 0 and j["items"] == [], f"{st} {j and j['total']}")
for q, name in [("%", "% literal"), ("_", "_ literal")]:
    st, hd, j = search(q, 5)
    rec(c, f"{name} no actua como comodin", st == 200 and j["total"] < db_n // 2, f"{st} total={j and j['total']}")
st, hd, j = get("/v1/plants?q=" + "a" * 201)
rec(c, "q de 201 caracteres -> 400", st == 400, str(st))
st, hd, j = get("/v1/plants?q=%00")
rec(c, "q con caracter de control -> 400", st == 400, str(st))
# todos los nombres cientificos y comunes del catalogo se pueden encontrar por si mismos? (muestra de 300)
import random
random.seed(7)
sample = random.sample(db_ids, 300)
miss = []
for pid in sample:
    sci = db.execute("select scientific_name from plant where id=?", (pid,)).fetchone()[0]
    st, hd, j = search(sci)
    if pid not in ids_of(j): miss.append(pid)
rec(c, "300 plantas al azar se encuentran por su nombre cientifico", not miss, str(miss[:5]))
miss = []
for pid in random.sample([r[0] for r in db.execute("select distinct plant_id from plant_name where kind='common' and language='es'")], 300):
    t = db.execute("select text from plant_name where plant_id=? and kind='common' and language='es' order by id limit 1", (pid,)).fetchone()[0]
    st, hd, j = search(t)
    if pid not in ids_of(j): miss.append((pid, t))
rec(c, "300 plantas al azar se encuentran por un nombre comun en espanol", not miss, str(miss[:5]))

# ---------- API-04 busqueda por nombres anteriores ----------
c = "API-04"
if OLD_MAP:
    rows = list(csv.DictReader(open(OLD_MAP), delimiter="\t"))
    ch = [r for r in rows if r["estado"] == "ALIAS"]
    found = notfound = 0; nf = []
    for r in ch:
        st, hd, j = search(r["nombre_anterior"])
        if r["id_nuevo"] in ids_of(j): found += 1
        else: notfound += 1; nf.append((r["id_anterior"], r["nombre_anterior"], r["id_nuevo"], r["nota"], r["relacion_usda"]))
    obs(c, f"De {len(ch)} IDs anteriores que pasan a alias, buscar su nombre cientifico anterior encuentra la planta nueva en {found} y no la encuentra en {notfound}.")
    with open(EV / "API-04-old-names-not-found.tsv", "w") as f:
        f.write("id_anterior\tnombre_anterior\tid_nuevo\tnota\trelacion_usda\n")
        for x in nf: f.write("\t".join(x) + "\n")
    byrel = collections.Counter(x[4].split(" (")[0] for x in nf)
    log[c].append(f"no encontrados por relacion USDA: {dict(byrel)}")
    # los que si son sinonimos listados deben encontrarse
    listed = [r for r in ch if "es sinónimo" in r["nota"]]
    lf = [r for r in listed if r["id_nuevo"] not in ids_of(search(r["nombre_anterior"])[2])]
    rec(c, f"los {len(listed)} nombres anteriores que la planta nueva lista como sinonimo se encuentran", not lf, str([r["id_anterior"] for r in lf[:5]]))

# ---------- API-05 detalle ----------
c = "API-05"
def detail(pid, token=TOKEN):
    return get(f"/v1/plants/{pid}", token)
ct, psch = op_schema("/v1/plants/{id}", "get", 200)
for pid, label in [("matricaria-chamomilla", "manzanilla"), ("mentha-x-piperita", "menta"), ("lavandula-angustifolia", "lavanda"), ("hypericum-perforatum", "hiperico"), ("lavandula-sp", "solo genero (Lavandula sp)")]:
    st, hd, j = detail(pid)
    dump(f"{c}-{pid}", f"detalle {label}", "GET", f"/v1/plants/{pid}", st, hd, j, 6000)
    ok = st == 200 and hd.get("content-type", "").startswith("application/json") and not validate(j, psch)
    rec(c, f"{label} ({pid}): 200 y cumple PlantDto", ok, f"{st} {validate(j, psch)[:2] if j else ''}")
    if st == 200:
        rec(c, f"{label}: id = {pid}", j["id"] == pid)
        if label in ("manzanilla", "menta"):
            rec(c, f"{label} tiene usos", len(j["uses"]) > 0, f"{len(j['uses'])} usos")
        if label in ("lavanda", "hiperico"):
            rec(c, f"{label} tiene usos", len(j["uses"]) > 0, f"{len(j['uses'])} usos")
        rec(c, f"{label}: actividades en espanol (language=es)", all(u["language"] == "es" for u in j["uses"]), str(collections.Counter(u["language"] for u in j["uses"])))
        rec(c, f"{label}: cada uso con referencia con id y cita no vacios", all(u["reference"]["id"] and u["reference"]["citation"] for u in j["uses"]))
        rec(c, f"{label}: sin usos repetidos", len({(u["activity"], u["reference"]["id"]) for u in j["uses"]}) == len(j["uses"]))
        log[f"{c}-{pid}"].append(f"resumen: {len(j['uses'])} usos, {len(j['names'])} nombres, {len(j['parts'])} partes, familia={j['family']}")
st, hd, j = detail("lavandula-sp")
if st == 200:
    obs(c, f"Planta de solo genero lavandula-sp: usos={len(j['uses'])}, nombres={[n['text'] for n in j['names']][:6]}")

# ---------- API-06 404, 401, 400 ----------
c = "API-06"
ct, p404 = op_schema("/v1/plants/{id}", "get", 404)
for pid in ["no-existe", "rosmarinus-officinalis", "matricaria-recutita", "LAVANDULA-ANGUSTIFOLIA", "lavandula-angustifolia%20", "malachra-alaceaefolia"]:
    st, hd, j = detail(pid)
    ok = st == 404 and hd.get("content-type", "").startswith("application/problem+json") and not validate(j, p404)
    rec(c, f"/v1/plants/{pid} -> 404 problem+json", ok, f"{st}")
    dump(c, f"404 {pid}", "GET", f"/v1/plants/{pid}", st, hd, j, 500)
ct, p401 = op_schema("/v1/plants", "get", 401)
bodies = set()
for path in ["/v1/plants", "/v1/plants/lavandula-angustifolia", "/v1/plants?q=lavanda", "/v1/plants/no-existe", "/v1/otra-cosa"]:
    for label, tok in [("sin token", None), ("token incorrecto", "x" * 64)]:
        st, hd, j = get(path, tok)
        ok = st == 401 and hd.get("www-authenticate") == "Bearer" and hd.get("content-type", "").startswith("application/problem+json") and not validate(j, p401)
        rec(c, f"{path} {label} -> 401 + WWW-Authenticate: Bearer", ok, f"{st}")
        bodies.add(json.dumps(j, sort_keys=True))
        if path == "/v1/plants" or path == "/v1/plants/lavandula-angustifolia": dump(c, f"401 {label}", "GET", path, st, hd, j, 500)
strip = {json.dumps({k: v for k, v in json.loads(b).items() if k != "instance"}, sort_keys=True) for b in bodies}
rec(c, "el cuerpo del 401 es el mismo para toda ruta y credencial salvo `instance` (no revela el motivo)", len(strip) == 1, f"{len(strip)} variantes")
for p in ["/health", "/openapi.json"]:
    st, hd, j = get(p, None)
    rec(c, f"{p} publico sin token -> 200", st == 200, str(st))

# ---------- API-07 barrido de todos los detalles ----------
c = "API-07"
t0 = time.time()
tot_uses = tot_names = tot_parts = 0; zero_uses = 0; bad = []; first_common_mismatch = []; sci_as_common = []; empty_cit = 0
prof = dict(db.execute("select plant_id, display_name from plant_profile"))
dbuses = dict(db.execute("select plant_id, count(*) from plant_use group by 1"))
names_by = collections.defaultdict(list)
for pid, text, kind, lang in db.execute("select plant_id, text, kind, language from plant_name order by id"):
    names_by[pid].append((text, kind, lang))
mism_uses = []; mism_names = []; lang_counter = collections.Counter(); cit_counter = collections.Counter()
for pid in db_ids:
    st, hd, j = detail(pid)
    if st != 200: bad.append((pid, st)); continue
    e = validate(j, psch)
    if e: bad.append((pid, e[0])); continue
    if j["id"] != pid: bad.append((pid, "id distinto"))
    tot_uses += len(j["uses"]); tot_names += len(j["names"]); tot_parts += len(j["parts"])
    if not j["uses"]: zero_uses += 1
    if len(j["uses"]) != dbuses.get(pid, 0): mism_uses.append(pid)
    if len(j["names"]) != len(names_by[pid]): mism_names.append(pid)
    for u in j["uses"]:
        lang_counter[u["language"]] += 1
        cit_counter["etiqueta 'USDA Dr. Duke: referencia'" if u["reference"]["citation"].startswith("USDA Dr. Duke: referencia") else "otra"] += 1
    commons = [n for n in j["names"] if n["kind"] == "common"]
    if commons and prof.get(pid) and commons[0]["text"] != prof[pid]:
        first_common_mismatch.append((pid, commons[0]["text"], prof[pid]))
    if any(n["text"] == j["scientificName"] for n in commons): sci_as_common.append(pid)
rec(c, f"los {db_n} detalles responden 200 y cumplen PlantDto", not bad, f"{len(bad)} con problema {bad[:3]} en {time.time()-t0:.0f}s")
rec(c, "usos servidos = plant_use de la base (24.286)", tot_uses == db.execute("select count(*) from plant_use").fetchone()[0] and not mism_uses, f"api={tot_uses} mismatch={mism_uses[:3]}")
rec(c, "nombres servidos = plant_name de la base", tot_names == db.execute("select count(*) from plant_name").fetchone()[0] and not mism_names, f"api={tot_names}")
rec(c, "plantas sin usos = base", zero_uses == db.execute("select count(*) from plant where id not in (select plant_id from plant_use)").fetchone()[0], f"{zero_uses}")
rec(c, "idioma de los usos: todos es", set(lang_counter) == {"es"}, str(dict(lang_counter)))
rec(c, "el primer nombre comun de la API es el nombre para mostrar (plant-passport)", not first_common_mismatch, f"{len(first_common_mismatch)} distintos; ejemplos {first_common_mismatch[:3]}")
log[c].append("citas de los usos: " + json.dumps(dict(cit_counter), ensure_ascii=False))
log[c].append(f"plantas cuyo nombre comun repite el nombre cientifico: {len(sci_as_common)}; ejemplos {sci_as_common[:5]}")
if sci_as_common: obs(c, f"{len(sci_as_common)} plantas sirven su nombre cientifico como nombre comun (language la): p. ej. {sci_as_common[:3]}")
if cit_counter["etiqueta 'USDA Dr. Duke: referencia'"]: obs(c, f"{cit_counter['etiqueta' + chr(32) + chr(39) + 'USDA Dr. Duke: referencia' + chr(39)]} de {tot_uses} usos sirven como `reference.citation` la etiqueta 'USDA Dr. Duke: referencia X' en lugar de la cita completa")
(EV / "API-07-first-common-mismatch.tsv").write_text("\n".join("\t".join(x) for x in first_common_mismatch))
(EV / "API-07-sci-as-common.txt").write_text("\n".join(sci_as_common))

# ---------- API-08 contrato OpenAPI ----------
c = "API-08"
st, hd, body = get("/openapi.json", None, raw=True)
served = json.loads(body)
rec(c, "/openapi.json servido = backend/openapi.json versionado", served == SPEC)
rec(c, "rutas del contrato: solo /health, /openapi.json, /v1/plants y /v1/plants/{id}", sorted(SPEC["paths"]) == ["/health", "/openapi.json", "/v1/plants", "/v1/plants/{id}"], str(sorted(SPEC["paths"])))
git_spec = os.popen(f"git -C {REPO} show main:backend/openapi.json").read()
rec(c, "backend/openapi.json no cambia respecto de main", json.loads(git_spec) == SPEC)
st, hd, j = get("/health", None)
ct, hs = op_schema("/health", "get", 200)
rec(c, "/health cumple HealthDto", st == 200 and not validate(j, hs))
for m in ["POST", "PUT", "DELETE"]:
    req = urllib.request.Request(BASE + "/v1/plants", method=m, headers={"Authorization": "Bearer " + TOKEN}, data=b"{}" if m != "DELETE" else None)
    try: r = urllib.request.urlopen(req); s = r.status; hh = {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e: s = e.code; hh = {k.lower(): v for k, v in e.headers.items()}
    rec(c, f"{m} /v1/plants -> 405 con Allow: GET", s == 405 and "GET" in hh.get("allow", ""), f"{s} {hh.get('allow')}")

# ---------- salida ----------
for case, lines in log.items():
    (EV / f"{case}.txt").write_text(redact("\n".join(lines)) + "\n")
summary = collections.Counter(r[2] for r in results)
out = ["caso\testado\tcomprobacion\tdetalle"] + [f"{a}\t{c}\t{b}\t{d}" for a, b, c, d in results]
(EV / "results.tsv").write_text(redact("\n".join(out)) + "\n")
print(dict(summary))
for a, b, c, d in results:
    if c != "PASA": print(redact(f"{c} {a} {b} {d}"))
