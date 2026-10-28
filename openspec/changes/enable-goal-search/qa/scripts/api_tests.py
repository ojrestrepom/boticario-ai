#!/usr/bin/env python3 -I
"""6.2: pruebas de la API de objetivos (cambio enable-goal-search) contra el servicio local de docker compose.

Entorno:
  QA_TOKEN   token de prueba valido (nunca se escribe en la evidencia: se sustituye por <token-app>)
  QA_BASE    URL base (por defecto http://127.0.0.1:8080)
  QA_DB      ruta de data/build/catalog.db (solo lectura; es el oraculo independiente de la API)
  QA_LOGS    (opcional) archivo con los logs del contenedor, para comprobar que no llevan el token
Uso: api_tests.py <repo> <carpeta de evidencia>
Solo usa la libreria estandar. Escribe results.tsv y un .txt por caso en la carpeta de evidencia.
"""
import collections, json, os, pathlib, re, sqlite3, statistics, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

REPO = pathlib.Path(sys.argv[1]); EV = pathlib.Path(sys.argv[2]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080")
TOKEN = os.environ["QA_TOKEN"]
DB = os.environ["QA_DB"]
SPEC = json.load(open(REPO / "backend" / "openapi.json"))

# ---------- validador minimo de JSON Schema (lo que usa openapi.json) ----------
def resolve(s):
    while isinstance(s, dict) and "$ref" in s:
        s = SPEC["components"]["schemas"][s["$ref"].split("/")[-1]] | {k: v for k, v in s.items() if k != "$ref"}
    return s

def validate(v, schema, path="$"):
    errs = []
    s = resolve(schema)
    if "oneOf" in s or "anyOf" in s:
        opts = s.get("oneOf") or s.get("anyOf")
        if not any(not validate(v, o, path) for o in opts):
            return [f"{path}: no cumple ninguna opcion de oneOf/anyOf ({str(v)[:40]})"]
        return []
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
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v: errs.append(f"{path}: falta {r}")
        for k, sub in s.get("properties", {}).items():
            if k in v: errs += validate(v[k], sub, f"{path}.{k}")
        extra = set(v) - set(s.get("properties", {}))
        if extra and s.get("properties") is not None and "object" in types:
            errs.append(f"{path}: campos fuera del contrato {sorted(extra)}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            errs += validate(x, s["items"], f"{path}[{i}]")
    return errs

def op_schema(path, method, status):
    for ct, body in SPEC["paths"][path][method]["responses"].get(str(status), {}).get("content", {}).items():
        return ct, body.get("schema")
    return None, None

# ---------- http ----------
def req(path, method="GET", token=TOKEN, headers=None, auth_scheme="Bearer"):
    h = dict(headers or {})
    if token is not None: h["Authorization"] = f"{auth_scheme} {token}"
    rq = urllib.request.Request(BASE + path, headers=h, method=method)
    t0 = time.perf_counter()
    try:
        r = urllib.request.urlopen(rq, timeout=30)
        status, hd, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, hd, body = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    dt = (time.perf_counter() - t0) * 1000
    try: j = json.loads(body)
    except Exception: j = None
    return status, hd, j, body.decode("utf-8", "replace"), dt

def get(path, **kw): return req(path, "GET", **kw)

def redact(s): return s.replace(TOKEN, "<token-app>")

results = []; log = collections.defaultdict(list)
def rec(case, name, ok, detail=""):
    results.append((case, name, "PASA" if ok else "FALLA", detail))
    log[case].append(f"{'PASA ' if ok else 'FALLA'} {name} {detail}")
def obs(case, text): results.append((case, text, "OBS", "")); log[case].append("OBS   " + text)
def dump(case, title, path, status, hd, body, limit=1500, auth="Bearer <token-app>", method="GET"):
    keep = {k: v for k, v in hd.items() if k in ("content-type", "www-authenticate", "allow", "content-length")}
    b = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=1)
    if len(b) > limit: b = b[:limit] + f"\n... (recortado, {len(b)} caracteres)"
    log[case].append(redact(f"--- {title}\n{method} {path}\n{('Authorization: ' + auth) if auth else '(sin Authorization)'}\n-> {status} {json.dumps(keep, ensure_ascii=False)}\n{b}\n"))

def norm(t):
    t = unicodedata.normalize("NFD", t.replace("×", " x ").lower())
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").split())

# ---------- oraculo: la base ----------
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
GOALS = db.execute("select id,label from goal order by position").fetchall()
SUBS = {g: db.execute("select id,label from goal_subarea where goal_id=? order by position", (g,)).fetchall() for g, _ in GOALS}
GOAL_NAME = dict(GOALS); SUB_NAME = {s: n for g in SUBS for s, n in SUBS[g]}
SCI = dict(db.execute("select id, scientific_name from plant"))
DISP = {pid: (dn or SCI[pid]) for pid, dn in db.execute("select plant_id, display_name from plant_profile")}
FAM = dict(db.execute("select id, family from plant"))
COMMONS = collections.defaultdict(set)
for pid, t, lang in db.execute("select plant_id,text,language from plant_name where kind='common'"): COMMONS[pid].add((t, lang))
SAFETY = {pid: lvl for pid, lvl in db.execute("select plant_id, level from plant_safety")}
IMAGE = {r[0]: r[1:] for r in db.execute("select plant_id,url,page_url,author,license,license_url,attribution_required from plant_image")}
ROWS = db.execute("select plant_id,goal_id,subarea_id,position,area,pending_review,id from plant_goal order by id").fetchall()

def visible(goal, sub=None):
    """{plant_id: [areas]} visibles (sin pending_review) de un objetivo o subarea."""
    out = collections.OrderedDict()
    for pid, g, s, pos, area, pend, _ in sorted(ROWS, key=lambda r: (r[3], r[6])):
        if g != goal or pend: continue
        if sub and s != sub: continue
        out.setdefault(pid, [])
        if area not in out[pid]: out[pid].append(area)
    return out

def expected_order(pids):
    return sorted(pids, key=lambda p: (norm(DISP[p]), norm(SCI[p]), p))

ALL_VISIBLE = set(); [ALL_VISIBLE.update(visible(g)) for g, _ in GOALS]
ALL_WITH_ROWS = {r[0] for r in ROWS}
FLAGS = collections.defaultdict(set)
for pid, code in db.execute("select plant_id, code from plant_review_flag"): FLAGS[code].add(pid)

def page_all(path, limit=100):
    items = []; off = 0; first = None
    sep = "&" if "?" in path else "?"
    while True:
        st, hd, j, _, _ = get(f"{path}{sep}limit={limit}&offset={off}")
        if st != 200: return None, items
        first = first or j
        items += j["items"]
        if len(j["items"]) < limit: return first, items
        off += limit

# =========================================================================================
c = "API-01"  # catalogo de objetivos
st, hd, j, raw, dt = get("/v1/goals")
dump(c, "catalogo de objetivos", "/v1/goals", st, hd, j, 1200)
_, gsch = op_schema("/v1/goals", "get", 200)
e = validate(j, gsch)
rec(c, "200, application/json y cumple el esquema de openapi.json", st == 200 and "application/json" in hd["content-type"] and not e, "; ".join(e[:3]))
rec(c, "la raiz es un array (decision: array en la raiz)", isinstance(j, list))
rec(c, "los objetivos del catalogo en su orden, con id y nombre en espanol", [(g["id"], g["name"]) for g in j] == GOALS, str([(g["id"], g["name"]) for g in j]))
rec(c, "nombres exactos de P06 y sin 'Concentracion'", [g["name"] for g in j] == ["Relajación / Estrés", "Mejorar el sueño", "Cuidado de la piel", "Alivio respiratorio", "Cansancio y fatiga", "Otros objetivos"] and not any("oncentraci" in g["name"] for g in j))
rec(c, "claves camelCase (id, name, plantCount, subareas) y nada mas", all(set(g) == {"id", "name", "plantCount", "subareas"} for g in j))
rec(c, "plantCount = plantas distintas visibles segun la base", all(g["plantCount"] == len(visible(g["id"])) for g in j), str({g["id"]: g["plantCount"] for g in j}))
expected_counts = {"relajacion-estres": 17, "mejorar-el-sueno": 8, "cuidado-de-la-piel": 32, "alivio-respiratorio": 52, "cansancio-y-fatiga": 8, "otros-objetivos": 135}
rec(c, "conteos reales de design.md (17, 8, 32, 52, 8, 135)", {g["id"]: g["plantCount"] for g in j} == expected_counts)
rec(c, "solo otros-objetivos trae subareas; los demas, lista vacia (no null)", all((g["subareas"] == []) == (g["id"] != "otros-objetivos") for g in j))
GOALS_API = j

c = "API-02"  # subareas
oo = next(g for g in GOALS_API if g["id"] == "otros-objetivos")
dump(c, "subareas de otros-objetivos", "/v1/goals", 200, {}, oo, 1500)
rec(c, "seis subareas en el orden del catalogo con nombre en espanol", [(s["id"], s["name"]) for s in oo["subareas"]] == SUBS["otros-objetivos"], str([(s["id"], s["name"]) for s in oo["subareas"]]))
rec(c, "nombres de P06: Digestion, Vias urinarias y genitales, Dolor e inflamacion, Boca y garganta, Circulacion, Molestias oculares",
    [s["name"] for s in oo["subareas"]] == ["Digestión", "Vías urinarias y genitales", "Dolor e inflamación", "Boca y garganta", "Circulación", "Molestias oculares"])
rec(c, "plantCount de cada subarea segun la base (68, 42, 22, 20, 17, 1)", [s["plantCount"] for s in oo["subareas"]] == [68, 42, 22, 20, 17, 1] and all(s["plantCount"] == len(visible("otros-objetivos", s["id"])) for s in oo["subareas"]))
rec(c, "claves de subarea: id, name, plantCount", all(set(s) == {"id", "name", "plantCount"} for s in oo["subareas"]))
tot = sum(s["plantCount"] for s in oo["subareas"])
rec(c, "el conteo del objetivo es la union sin repetir (135 < suma de subareas 170)", oo["plantCount"] == 135 and tot == 170, f"suma de subareas {tot}")
two = [p for p in visible("otros-objetivos") if len({r[2] for r in ROWS if r[0] == p and r[1] == "otros-objetivos" and not r[5]}) > 1]
rec(c, "hay plantas en dos subareas y cuentan una vez (32 segun el diseno)", len(two) == 32, f"{len(two)} plantas, p. ej. {two[:3]}")

c = "API-03"  # plantas por objetivo: forma y contrato
_, psch = op_schema("/v1/goals/{goalId}/plants", "get", 200)
for g, name in GOALS:
    st, hd, j, raw, dt = get(f"/v1/goals/{g}/plants")
    if g == "mejorar-el-sueno": dump(c, "mejorar-el-sueno, primera pagina", f"/v1/goals/{g}/plants", st, hd, j, 1800)
    e = validate(j, psch) if st == 200 else ["no es 200"]
    exp = visible(g)
    ok = (st == 200 and "application/json" in hd["content-type"] and not e and j["goal"] == {"id": g, "name": name} and j["subarea"] is None
          and j["total"] == len(exp) and j["limit"] == 20 and j["offset"] == 0 and len(j["items"]) == min(20, len(exp)))
    rec(c, f"{g}: 200, esquema, goal, subarea null, limit 20 por defecto, offset 0 y total {len(exp)}", ok, "; ".join(e[:2]) if e else f"status {st}")
    if st == 200:
        rec(c, f"{g}: cada elemento solo trae id, scientificName, displayName, commonNames, family, areas, safetyLevel, hasSafety, image (sin dosis ni descripcion)",
            all(set(i) == {"id", "scientificName", "displayName", "commonNames", "family", "areas", "safetyLevel", "hasSafety", "image"} for i in j["items"]))

c = "API-04"  # subarea valida
for s, sname in SUBS["otros-objetivos"]:
    first, items = page_all(f"/v1/goals/otros-objetivos/plants?subarea={s}")
    exp = visible("otros-objetivos", s)
    ok = first and first["subarea"] == {"id": s, "name": sname} and first["goal"]["id"] == "otros-objetivos" and first["total"] == len(exp)
    rec(c, f"{s}: subarea con id y name, total {len(exp)}", bool(ok), str(first["subarea"] if first else None))
    rec(c, f"{s}: solo plantas de esa subarea (conjunto igual al de la base)", {i["id"] for i in items} == set(exp) and len(items) == len(exp))
    rec(c, f"{s}: areas solo las de esa subarea", all(set(i["areas"]) == set(exp[i["id"]]) for i in items))
st, hd, j, _, _ = get("/v1/goals/otros-objetivos/plants?subarea=digestion&limit=2")
dump(c, "subarea digestion (2 elementos)", "/v1/goals/otros-objetivos/plants?subarea=digestion&limit=2", st, hd, j, 900)
st, hd, j, _, _ = get("/v1/goals/otros-objetivos/plants?subarea=molestias-oculares")
dump(c, "subarea con una sola planta", "/v1/goals/otros-objetivos/plants?subarea=molestias-oculares", st, hd, j, 900)
rec(c, "molestias-oculares: una planta (limite inferior)", j["total"] == 1 and len(j["items"]) == 1, str([i["id"] for i in j["items"]]))

c = "API-05"  # union sin subarea
first, items = page_all("/v1/goals/otros-objetivos/plants")
ids = [i["id"] for i in items]
rec(c, "135 plantas, cada una una vez", len(ids) == len(set(ids)) == 135 == first["total"] and first["subarea"] is None)
exp = visible("otros-objetivos")
rec(c, "areas = union de las areas de todas sus subareas (como conjunto)", all(set(i["areas"]) == set(exp[i["id"]]) for i in items))
multi = [i for i in items if len({r[2] for r in ROWS if r[0] == i["id"] and r[1] == "otros-objetivos" and not r[5]}) > 1]
rec(c, "plantas en dos subareas aparecen una vez con areas reunidas", len(multi) == 32 and all(len(i["areas"]) >= 1 for i in multi), f"{len(multi)} plantas")
ex = next(i for i in items if i["id"] == "eucalyptus-globulus")
dump(c, "ejemplo de planta con areas reunidas", "/v1/goals/otros-objetivos/plants (eucalyptus-globulus)", 200, {}, {k: ex[k] for k in ("id", "areas", "safetyLevel", "hasSafety")}, 600)
multi_areas = [i for i in multi if len(i["areas"]) > 1]
obs(c, f"{len(multi_areas)} plantas en mas de una subarea traen mas de un area en la union; ejemplo {multi_areas[0]['id'] if multi_areas else '-'}: {multi_areas[0]['areas'] if multi_areas else ''}")

c = "API-06"  # subarea ajena
cases = [
    ("subarea de otro objetivo en un objetivo con subareas? (sin subareas)", "/v1/goals/relajacion-estres/plants?subarea=digestion"),
    ("subarea inexistente en otros-objetivos", "/v1/goals/otros-objetivos/plants?subarea=no-existe"),
    ("subarea sobre un objetivo sin subareas", "/v1/goals/mejorar-el-sueno/plants?subarea=x"),
    ("subarea vacia", "/v1/goals/otros-objetivos/plants?subarea="),
    ("subarea con mayusculas", "/v1/goals/otros-objetivos/plants?subarea=DIGESTION"),
    ("subarea con espacio final", "/v1/goals/otros-objetivos/plants?subarea=digestion%20"),
    ("subarea con id de objetivo", "/v1/goals/otros-objetivos/plants?subarea=otros-objetivos"),
]
for title, path in cases:
    st, hd, j, raw, _ = get(path)
    dump(c, title, path, st, hd, j, 500)
    rec(c, f"{title}: 400 problem+json con param=subarea", st == 400 and "application/problem+json" in hd.get("content-type", "") and (j or {}).get("param") == "subarea", f"{st} {(j or {}).get('param')}")
    if st == 400:
        e = validate(j, op_schema("/v1/goals/{goalId}/plants", "get", 400)[1]); rec(c, f"{title}: cuerpo cumple el esquema de error", not e, "; ".join(e[:2]))

c = "API-07"  # objetivo desconocido
for title, path in [("id inexistente", "/v1/goals/no-existe/plants"), ("id con mayusculas", "/v1/goals/Mejorar-El-Sueno/plants"), ("id con caracteres reservados", "/v1/goals/a%2Fb/plants"),
                    ("id con acento", "/v1/goals/mejorar-el-sue%C3%B1o/plants"), ("id con punto y coma", "/v1/goals/a%3Bb%3Fc/plants"), ("id muy largo (300)", "/v1/goals/" + "z" * 300 + "/plants"),
                    ("inexistente con subarea", "/v1/goals/no-existe/plants?subarea=digestion")]:
    st, hd, j, raw, _ = get(path)
    dump(c, title, path[:90], st, hd, j, 400)
    rec(c, f"{title}: 404 problem+json", st == 404 and "application/problem+json" in hd.get("content-type", ""), f"{st}")
    if st == 404:
        rec(c, f"{title}: cuerpo cumple el esquema de error y no refleja el id", not validate(j, op_schema("/v1/goals/{goalId}/plants", "get", 404)[1]))

c = "API-08"  # limites de limit y offset
lim_ok = {"1": 1, "2": 2, "19": 19, "20": 20, "99": 99, "100": 100}
for v, n in lim_ok.items():
    st, hd, j, _, _ = get(f"/v1/goals/alivio-respiratorio/plants?limit={v}")
    rec(c, f"limit={v}: 200 con {min(n, 52)} elementos (el objetivo tiene 52) y limit={n}", st == 200 and len(j["items"]) == min(n, 52) and j["limit"] == n and j["total"] == 52, f"{st}")
for v in ["0", "-1", "101", "1000", "abc", "1.5", "", "%20", "9999999999999999999999", "1e2", "+5"]:
    p = f"/v1/goals/alivio-respiratorio/plants?limit={v}"
    st, hd, j, _, _ = get(p)
    dump(c, f"limit={v!r}", p, st, hd, j, 300)
    if v == "+5":
        obs(c, f"limit=+5 -> {st} (cadena '+5' se interpreta como {'5' if st == 200 else 'invalida'})")
    else:
        rec(c, f"limit={v!r}: 400 problem+json con param=limit", st == 400 and "problem+json" in hd.get("content-type", "") and j.get("param") == "limit", f"{st} {(j or {}).get('param')}")
for v in ["0", "1", "51", "52", "53", "1000", "2147483647"]:
    st, hd, j, _, _ = get(f"/v1/goals/alivio-respiratorio/plants?offset={v}&limit=5")
    exp_n = max(0, min(5, 52 - int(v)))
    rec(c, f"offset={v}: 200, {exp_n} elementos y total 52 conservado", st == 200 and len(j["items"]) == exp_n and j["total"] == 52 and j["offset"] == int(v), f"{st} {len(j['items']) if j else ''}")
for v in ["-1", "abc", "1.5", "", "99999999999999999999999", "9223372036854775807", "4294967296"]:
    p = f"/v1/goals/alivio-respiratorio/plants?offset={v}"
    st, hd, j, _, _ = get(p)
    dump(c, f"offset={v!r}", p, st, hd, j, 300)
    rec(c, f"offset={v!r}: 400 problem+json con param=offset", st == 400 and "problem+json" in hd.get("content-type", "") and j.get("param") == "offset", f"{st} {(j or {}).get('param')}")
# el mismo comportamiento en el listado de plantas ("mismas reglas y errores que GET /v1/plants")
mism = []
for q in ["limit=0", "limit=101", "limit=abc", "offset=-1", "offset=abc", "limit=%20", "limit=", "offset=", "offset=4294967296", "offset=2147483647"]:
    a = get(f"/v1/plants?{q}")[0]; b = get(f"/v1/goals/mejorar-el-sueno/plants?{q}")[0]
    if a != b: mism.append((q, a, b))
rec(c, "mismas reglas de limit/offset que GET /v1/plants (mismo estado para 10 entradas)", not mism, str(mism))
dups = [("limit=5&limit=10", get("/v1/goals/mejorar-el-sueno/plants?limit=5&limit=10")), ("limit=5&limit=abc", get("/v1/goals/mejorar-el-sueno/plants?limit=5&limit=abc"))]
for q, r in dups: obs(c, f"parametro repetido {q} -> {r[0]} (items {len(r[2]['items']) if r[2] and 'items' in r[2] else '-'}); GET /v1/plants da {get('/v1/plants?' + q)[0]}")
unk = get("/v1/goals/mejorar-el-sueno/plants?foo=bar")
obs(c, f"parametro desconocido foo=bar -> {unk[0]}")

c = "API-09"  # paginacion sin repeticion
for g, _ in GOALS:
    exp = visible(g)
    for lim in (5, 7):
        seen = []; off = 0; tot = None; bad = []
        while True:
            st, hd, j, _, _ = get(f"/v1/goals/{g}/plants?limit={lim}&offset={off}")
            if st != 200: bad.append(st); break
            tot = j["total"]; seen += [i["id"] for i in j["items"]]
            if not j["items"] or len(j["items"]) < lim: break
            off += lim
        rec(c, f"{g} limit={lim}: cada planta una vez y la union tiene total ({len(exp)}) elementos", not bad and len(seen) == len(set(seen)) == tot == len(exp), f"{len(seen)} vistas")
    # las paginas concatenadas igualan la pagina unica de 100
    one = page_all(f"/v1/goals/{g}/plants")[1]
    rec(c, f"{g}: las paginas de 5 y la de 100 dan la misma secuencia", [i["id"] for i in one] == seen)
first, items = page_all("/v1/goals/otros-objetivos/plants?subarea=digestion", 5)
rec(c, "digestion limit=5: 68 elementos sin repeticion", len({i["id"] for i in items}) == len(items) == 68)

c = "API-10"  # orden
for g, _ in GOALS:
    first, items = page_all(f"/v1/goals/{g}/plants")
    got = [i["id"] for i in items]
    rec(c, f"{g}: orden por displayName normalizado, cientifico normalizado e id (oraculo independiente)", got == expected_order(visible(g)), "")
    rec(c, f"{g}: displayName = plant_profile.display_name", all(i["displayName"] == DISP[i["id"]] for i in items))
for s, _ in SUBS["otros-objetivos"]:
    got = [i["id"] for i in page_all(f"/v1/goals/otros-objetivos/plants?subarea={s}")[1]]
    rec(c, f"otros-objetivos/{s}: mismo orden total", got == expected_order(visible("otros-objetivos", s)))
items = page_all("/v1/goals/otros-objetivos/plants")[1]
dn = [i["displayName"] for i in items]
rec(c, "otros-objetivos: el orden no es el binario (mayusculas y acentos no mueven la posicion)", dn != sorted(dn) and [norm(x) for x in dn] == sorted(norm(x) for x in dn))
sci_dn = [i for i in items if i["displayName"] == i["scientificName"]]
obs(c, f"en otros-objetivos {len(sci_dn)} plantas tienen el cientifico como displayName y se mezclan en el orden; ejemplo: {[i['displayName'] for i in sci_dn[:3]]}")
# empates de displayName
for g, _ in GOALS:
    items = page_all(f"/v1/goals/{g}/plants")[1]
    cnt = collections.Counter(norm(i["displayName"]) for i in items)
    ties = [k for k, v in cnt.items() if v > 1]
    if ties: obs(c, f"{g}: empates de displayName normalizado resueltos por cientifico e id: {ties}")
st, hd, a, _, _ = get("/v1/goals/relajacion-estres/plants"); st, hd, b, _, _ = get("/v1/goals/relajacion-estres/plants")
rec(c, "orden estable: dos peticiones iguales devuelven el mismo cuerpo", a == b)

c = "API-11"  # coherencia
for g in GOALS_API:
    t = get(f"/v1/goals/{g['id']}/plants?limit=1")[2]["total"]
    rec(c, f"{g['id']}: plantCount ({g['plantCount']}) = total ({t})", g["plantCount"] == t)
    for s in g["subareas"]:
        t = get(f"/v1/goals/{g['id']}/plants?subarea={s['id']}&limit=1")[2]["total"]
        rec(c, f"{g['id']}/{s['id']}: plantCount ({s['plantCount']}) = total ({t})", s["plantCount"] == t)

c = "API-12"  # revision pendiente
hyp = "hypericum-perforatum"
first, items = page_all("/v1/goals/relajacion-estres/plants")
rec(c, "el hiperico no esta en relajacion-estres (17 de 18)", hyp not in {i["id"] for i in items} and first["total"] == 17)
pend = [r for r in ROWS if r[5]]
rec(c, "la unica fila pendiente en la base es la del hiperico en relajacion-estres", [(r[0], r[1]) for r in pend] == [(hyp, "relajacion-estres")])
st, hd, j, _, _ = get(f"/v1/plants/{hyp}"); dump(c, "detalle del hiperico", f"/v1/plants/{hyp}", st, hd, {k: j[k] for k in ("id", "displayName", "goals")} if st == 200 else j, 900)
rec(c, "el detalle del hiperico responde 200", st == 200)
rec(c, "el detalle no lista relajacion-estres entre sus objetivos (misma regla)", st == 200 and "relajacion-estres" not in json.dumps(j["goals"]))
_, items = page_all(f"/v1/plants?q=hypericum")
rec(c, "el hiperico sigue en el listado GET /v1/plants?q=hypericum", hyp in {i["id"] for i in items})
for g in ("cuidado-de-la-piel", "otros-objetivos"):
    rec(c, f"el hiperico si aparece en {g} (su fila no esta pendiente)", hyp in {i["id"] for i in page_all(f"/v1/goals/{g}/plants")[1]})
rec(c, "hiperico en otros-objetivos/digestion", hyp in {i["id"] for i in page_all("/v1/goals/otros-objetivos/plants?subarea=digestion")[1]})
# flag sin pending_review no oculta
hid = [p for p in FLAGS["sin-datos-de-seguridad"] if p in ALL_WITH_ROWS]
rec(c, "ningun reviewFlag distinto de la marca por objetivo oculta plantas: las de 'sin-datos-de-seguridad' con objetivos siguen visibles", all(p in ALL_VISIBLE for p in hid), f"{len(hid)} plantas")

c = "API-13"  # plantas sin objetivos / toxicas
tox = FLAGS["objetivos-omitidos-por-toxicidad"] | {"conium-maculatum"}
union = set()
for g, _ in GOALS: union |= {i["id"] for i in page_all(f"/v1/goals/{g}/plants")[1]}
rec(c, "ninguna planta tipo 'objetivos-omitidos-por-toxicidad' ni conium-maculatum aparece en ningun objetivo", not (union & tox), str(sorted(tox)))
rec(c, "la union de los seis objetivos son exactamente las 175 plantas con filas visibles en la base", union == ALL_VISIBLE and len(union) == 175, f"{len(union)}")
toxic_alto = [p for p, l in SAFETY.items() if l == "alto" and p not in ALL_WITH_ROWS]
rec(c, "ninguna de las plantas con nivel alto y sin objetivos en la base aparece", not (union & set(toxic_alto)), f"{len(toxic_alto)} plantas")
for p in ["aconitum-napellus", "ricinus-communis", "abrus-precatorius", "angelica-laxiflora"]:
    rec(c, f"{p} no aparece en ningun objetivo", p not in union)
sub_union = set()
for s, _ in SUBS["otros-objetivos"]: sub_union |= {i["id"] for i in page_all(f"/v1/goals/otros-objetivos/plants?subarea={s}")[1]}
rec(c, "la union de las seis subareas es la lista sin subarea (135)", sub_union == {i["id"] for i in page_all('/v1/goals/otros-objetivos/plants')[1]})
two_goals = [p for p in union if len({r[1] for r in ROWS if r[0] == p and not r[5]}) > 1]
rec(c, f"plantas en dos objetivos aparecen en ambos con solo las areas de cada uno ({len(two_goals)} plantas)", len(two_goals) == 71)
laven = {g: next((i for i in page_all(f"/v1/goals/{g}/plants")[1] if i["id"] == "lavandula-angustifolia"), None) for g in ("mejorar-el-sueno", "relajacion-estres")}
dump(c, "lavandula-angustifolia en dos objetivos", "areas por objetivo", 200, {}, {g: (v or {}).get("areas") for g, v in laven.items()}, 500)
rec(c, "lavandula-angustifolia: sueno -> 'Trastornos del sueno...', estres -> 'Estres mental...' (cada uno solo la suya)",
    laven["mejorar-el-sueno"]["areas"] == ["Trastornos del sueño e insomnio pasajero"] and laven["relajacion-estres"]["areas"] == ["Estrés mental y trastornos del ánimo"])

c = "API-14"  # contenido por planta contra la base (censo de las 175)
bad = collections.defaultdict(list); n = 0; areas_order_diff = 0
for g, _ in GOALS:
    exp = visible(g)
    for i in page_all(f"/v1/goals/{g}/plants")[1]:
        n += 1; p = i["id"]
        if i["scientificName"] != SCI[p]: bad["scientificName"].append(p)
        if i["family"] != FAM[p]: bad["family"].append(p)
        if {(x["text"], x["language"]) for x in i["commonNames"]} != COMMONS[p]: bad["commonNames"].append(p)
        if set(i["areas"]) != set(exp[p]): bad["areas"].append(p)
        elif i["areas"] != exp[p]: areas_order_diff += 1
        if len(i["areas"]) != len(set(i["areas"])): bad["areas-duplicadas"].append(p)
        if i["safetyLevel"] != SAFETY.get(p): bad["safetyLevel"].append(p)
        if i["hasSafety"] != (p in SAFETY): bad["hasSafety"].append(p)
        im = IMAGE.get(p)
        want = None if im is None else {"url": im[0], "pageUrl": im[1], "author": im[2], "license": im[3], "licenseUrl": im[4], "attributionRequired": bool(im[5])}
        if i["image"] != want: bad["image"].append(p)
rec(c, f"{n} filas objetivo x planta: scientificName, family, commonNames, areas, safetyLevel, hasSafety e image coinciden con la base", not bad, str({k: v[:3] for k, v in bad.items()}))
obs(c, f"el orden de 'areas' dentro de una planta difiere del orden de la base (position) en {areas_order_diff} filas; la spec no fija ese orden")
first, items = page_all("/v1/goals/otros-objetivos/plants")
byid = {i["id"]: i for i in items}
rec(c, "image.author puede ser null (planta con autor nulo y objetivo)", any(i["image"] and i["image"]["author"] is None for g, _ in GOALS for i in page_all(f"/v1/goals/{g}/plants")[1]))
rec(c, "image null y hasSafety false no se mezclan: plantas sin imagen traen image null (20 de 175)", len([p for p in union if p not in IMAGE]) == 20)
noimg = sorted(p for p in union if p not in IMAGE)[:3]
obs(c, f"ejemplos de plantas sin imagen: {noimg}")
rec(c, "ninguna URL de imagen es distinta de upload.wikimedia.org (la API no deriva miniaturas)", all(v[0].startswith("https://upload.wikimedia.org/") for p, v in IMAGE.items() if p in union))

c = "API-15"  # precauciones
eu = byid["eucalyptus-globulus"]
rec(c, "eucalyptus-globulus: safetyLevel null y hasSafety true (precauciones sin nivel)", eu["safetyLevel"] is None and eu["hasSafety"] is True)
lv = collections.Counter(); cnt = set()
for g, _ in GOALS:
    for i in page_all(f"/v1/goals/{g}/plants")[1]:
        if i["id"] in cnt: continue
        cnt.add(i["id"]); lv[(i["safetyLevel"], i["hasSafety"])] += 1
dump(c, "distribucion (nivel, hasSafety) de las 175 plantas", "censo", 200, {}, {str(k): v for k, v in lv.items()}, 600)
rec(c, "distribucion 13 alto, 30 medio, 21 bajo, 111 sin nivel; hasSafety verdadero en las 175", lv == {("alto", True): 13, ("medio", True): 30, ("bajo", True): 21, (None, True): 111}, str(dict(lv)))
obs(c, "hasSafety=false no ocurre en ninguna planta real con objetivo: el caso se cubre solo con fixtures de la app (tarea 5.2); no hay forma de probarlo con la API real")

c = "API-16"  # lenguaje de eficacia o dosis
BAD = re.compile(r"\b(dosis|dosific\w*|mg|ml|gotas?|cucharad\w*|tomar|ingerir|ingesta|eficaz|eficacia|efectos?|calma\w*|relaj\w*|alivia\w*|cura\w*|trata\w*|ayuda\w*|promueve\w*|reduce|mejora\w*|previene|combate|recomend\w*|indicad\w*|sirve|beneficio\w*|propiedades)\b", re.I)
all_areas = collections.Counter(); hits = []
for g, _ in GOALS:
    for i in page_all(f"/v1/goals/{g}/plants")[1]:
        for a in i["areas"]:
            all_areas[a] += 1
            if BAD.search(a): hits.append((i["id"], a))
dump(c, "valores distintos de areas", "censo", 200, {}, dict(all_areas), 2500)
rec(c, f"ninguna area ({len(all_areas)} valores distintos) contiene lenguaje de dosis o eficacia", not hits, str(hits[:3]))
expected_areas = {"Estrés mental y trastornos del ánimo", "Trastornos del sueño e insomnio pasajero", "Trastornos de la piel y heridas leves", "Tos y resfriado", "Fatiga y debilidad", "Trastornos gastrointestinales", "Estreñimiento", "Pérdida de apetito", "Trastornos urinarios y genitales", "Dolor e inflamación", "Trastornos de boca y garganta", "Trastornos circulatorios", "Molestias oculares", "Pérdida de apetito; Trastornos gastrointestinales", "Estreñimiento; Trastornos gastrointestinales", "Trastornos gastrointestinales; Trastornos digestivos"}
rec(c, "los valores de areas son los 13 del diseno mas los 3 compuestos con '; '", set(all_areas) == expected_areas, str(set(all_areas) ^ expected_areas))
comp = {a: n for a, n in all_areas.items() if "; " in a}
obs(c, f"areas compuestas tal cual (decision tomada): {comp}")
rec(c, "los textos del catalogo de objetivos tampoco contienen lenguaje de dosis", not any(re.search(r"dosis|\bmg\b", json.dumps(g, ensure_ascii=False), re.I) for g in GOALS_API))

c = "API-17"  # autenticacion: tabla de decision
rts = ["/v1/goals", "/v1/goals/mejorar-el-sueno/plants", "/v1/goals/otros-objetivos/plants?subarea=digestion", "/v1/goals/no-existe/plants"]
for p in rts:
    st, hd, j, raw, _ = get(p, token=None)
    dump(c, "sin token", p, st, hd, j, 300, auth=None)
    rec(c, f"{p}: sin token -> 401 problem+json con WWW-Authenticate: Bearer", st == 401 and "application/problem+json" in hd["content-type"] and hd.get("www-authenticate", "").startswith("Bearer"), str(st))
    rec(c, f"{p}: el 401 cumple el esquema de error y no revela si el objetivo existe", st == 401 and not validate(j, op_schema("/v1/goals", "get", 401)[1]))
    st, hd, j, raw, _ = get(p, token="x" * 48)
    rec(c, f"{p}: token incorrecto -> 401 problem+json", st == 401 and "problem+json" in hd["content-type"], str(st))
    st2, hd2, j2, raw2, _ = get(p, token=TOKEN[:-1] + ("0" if TOKEN[-1] != "0" else "1"))
    rec(c, f"{p}: token con el ultimo caracter cambiado -> 401", st2 == 401)
    st3, _, _, _, _ = get(p, token=TOKEN, auth_scheme="Basic")
    rec(c, f"{p}: esquema Basic con el token correcto -> 401", st3 == 401, str(st3))
    st4, _, _, _, _ = get(p, token=TOKEN, auth_scheme="bearer")
    obs(c, f"{p}: esquema 'bearer' en minusculas -> {st4}")
    st5, _, _, _, _ = get(p, token="", auth_scheme="Bearer")
    rec(c, f"{p}: 'Bearer ' sin token -> 401", st5 == 401, str(st5))
    st6, _, _, _, _ = get(p, token=None, headers={"X-Api-Key": TOKEN})
    rec(c, f"{p}: token en X-Api-Key (no admitido) -> 401", st6 == 401)
    st7, _, _, _, _ = get(p + ("&" if "?" in p else "?") + "token=" + TOKEN, token=None)
    rec(c, f"{p}: token en la query (no admitido) -> 401", st7 == 401)
for tok in (TOKEN,):
    st, hd, j, _, _ = get("/v1/goals", token=" " + tok)
    obs(c, f"Authorization con espacio doble antes del token -> {st}")

c = "API-18"  # metodos
for p in ["/v1/goals", "/v1/goals/mejorar-el-sueno/plants", "/v1/goals/no-existe/plants"]:
    for m in ["POST", "PUT", "PATCH", "DELETE"]:
        st, hd, j, raw, _ = req(p, m)
        if m == "POST": dump(c, f"{m} con token", p, st, hd, j, 300, method=m)
        rec(c, f"{m} {p} con token -> 405 problem+json con Allow: GET", st == 405 and "problem+json" in hd.get("content-type", "") and "GET" in hd.get("allow", ""), f"{st} allow={hd.get('allow')}")
        e = validate(j, op_schema("/v1/goals/{goalId}/plants", "get", 405)[1]) if st == 405 else ["no 405"]
        rec(c, f"{m} {p}: el 405 cumple el esquema", not e)
    st, hd, j, _, _ = req(p, "POST", token=None)
    rec(c, f"POST {p} sin token -> 401 (la autenticacion va antes que el metodo)", st == 401, str(st))
for m in ["HEAD", "OPTIONS"]:
    for p in ["/v1/goals", "/v1/goals/mejorar-el-sueno/plants"]:
        st, hd, j, raw, _ = req(p, m)
        obs(c, f"{m} {p} con token -> {st} allow={hd.get('allow')} cuerpo={len(raw)} bytes")

c = "API-19"  # OpenAPI
st, hd, served, raw, _ = get("/openapi.json", token=None)
cur = json.load(open(REPO / "backend" / "openapi.json"))
rec(c, "/openapi.json servido (sin token) es igual al backend/openapi.json versionado", st == 200 and served == cur)
base = json.loads(subprocess.run(["git", "-C", str(REPO), "show", "a15f1eb:backend/openapi.json"], capture_output=True, text=True).stdout)
added_paths = sorted(set(cur["paths"]) - set(base["paths"]))
rec(c, "las rutas nuevas son solo /v1/goals y /v1/goals/{goalId}/plants", added_paths == ["/v1/goals", "/v1/goals/{goalId}/plants"], str(added_paths))
rec(c, "ninguna ruta existente cambia", all(cur["paths"][p] == base["paths"][p] for p in base["paths"]))
rec(c, "ningun esquema existente cambia", all(cur["components"]["schemas"][k] == v for k, v in base["components"]["schemas"].items()), str([k for k, v in base["components"]["schemas"].items() if cur["components"]["schemas"][k] != v]))
new_schemas = sorted(set(cur["components"]["schemas"]) - set(base["components"]["schemas"]))
obs(c, f"esquemas nuevos: {new_schemas}")
for p in added_paths:
    op = cur["paths"][p]["get"]
    sec = op.get("security") or cur.get("security")
    rec(c, f"{p}: Bearer en security", bool(sec) and any("bearer" in k.lower() or "Bearer" in k for s in sec for k in s), str(sec))
    want = {"200", "401", "500"} | ({"400", "404", "405"} if "goalId" in p else {"405"})
    resp = set(op["responses"])
    rec(c, f"{p}: respuestas documentadas {sorted(want)}", want <= resp, f"tiene {sorted(resp)}")
    for code in resp - {"200"}:
        ct = list(op["responses"][code].get("content", {}).keys())
        rec(c, f"{p}: {code} como application/problem+json", ct == ["application/problem+json"], str(ct))
rec(c, "el parametro subarea, limit y offset estan documentados en la ruta de plantas", {x["name"] for x in cur["paths"]["/v1/goals/{goalId}/plants"]["get"]["parameters"]} == {"goalId", "subarea", "limit", "offset"})
rec(c, "/health y /openapi.json siguen sin seguridad; /v1/* con seguridad", all(cur["paths"][p]["get"].get("security") in ([], None) or p.startswith("/v1") for p in cur["paths"]))

c = "API-20"  # rutas existentes intactas
st, hd, lst, _, _ = get("/v1/plants")
e = validate(lst, op_schema("/v1/plants", "get", 200)[1])
rec(c, "GET /v1/plants sigue cumpliendo su esquema (total 2354, limit 20)", st == 200 and not e and lst["total"] == 2354 and lst["limit"] == 20 and len(lst["items"]) == 20, "; ".join(e[:2]))
rec(c, "los elementos de GET /v1/plants conservan sus campos", all(set(i) == set(base["components"]["schemas"]["PlantSummaryDto"]["properties"]) for i in lst["items"]))
okc = 0
for pid in ["lavandula-angustifolia", "eucalyptus-globulus", "hypericum-perforatum", "angelica-laxiflora", "salvia-rosmarinus", "rosmarinus-officinalis"]:
    st, hd, j, _, _ = get(f"/v1/plants/{pid}")
    if st == 200 and not validate(j, op_schema("/v1/plants/{id}", "get", 200)[1]): okc += 1
rec(c, "GET /v1/plants/{id} cumple PlantDto en 6 plantas (incluido un alias y una sin datos)", okc == 6, f"{okc}/6")
lav = get("/v1/plants/lavandula-angustifolia")[2]
rec(c, "el detalle de la lavanda conserva los objetivos 'Mejorar el sueno' y 'Relajacion / Estres'", {g["name"] for g in lav["goals"]} >= {"Mejorar el sueño", "Relajación / Estrés"}, str([g.get("name") for g in lav["goals"]]))
st, hd, j, _, _ = get("/v1/plants?q=zzzz-no-existe")
rec(c, "la busqueda sin resultados sigue devolviendo 200 con total 0", st == 200 and j["total"] == 0)

c = "API-21"  # rutas publicas y logs
for p, want in [("/health", 200), ("/openapi.json", 200)]:
    rec(c, f"{p} sigue publica -> {want}", get(p, token=None)[0] == want)
for p in ["/goals", "/goals/mejorar-el-sueno/plants", "/v2/goals", "/v1/goals/mejorar-el-sueno", "/v1/goals/mejorar-el-sueno/plants/extra", "/v1/goal"]:
    st, hd, j, raw, _ = get(p, token=None)
    rec(c, f"{p} sin token: no es una ruta publica con datos (no 200)", st != 200, str(st))
    st, hd, j, raw, _ = get(p)
    obs(c, f"{p} con token -> {st} {hd.get('content-type')}")
for p in ["/v1/goals/", "/v1/goals/mejorar-el-sueno/plants/"]:
    st, hd, j, raw, _ = get(p)
    obs(c, f"barra final {p} con token -> {st}")
logs = os.environ.get("QA_LOGS")
if logs and os.path.exists(logs):
    txt = open(logs, errors="replace").read()
    rec(c, "los logs del contenedor no contienen el token", TOKEN not in txt and "Bearer" not in txt, f"{len(txt.splitlines())} lineas")
    obs(c, "con RUST_LOG=info la API solo registra el arranque; el barrido con nivel debug va en API-23")
    log[c].append(redact("\n".join(txt.splitlines()[-12:])))

c = "API-22"  # idempotencia y rendimiento
ts = []
for p in ["/v1/goals", "/v1/goals/relajacion-estres/plants", "/v1/goals/otros-objetivos/plants?limit=100", "/v1/goals/otros-objetivos/plants?subarea=digestion"]:
    bodies = []
    for _ in range(5):
        st, hd, j, raw, dt = get(p); bodies.append(raw); ts.append(dt)
    rec(c, f"{p}: cinco GET devuelven el mismo cuerpo byte a byte", len(set(bodies)) == 1)
log[c].append(f"tiempos ({len(ts)} peticiones, contenedor local): mediana {statistics.median(ts):.1f} ms, max {max(ts):.1f} ms")
sizes = {g: len(get(f'/v1/goals/{g}/plants?limit=100')[3]) for g, _ in GOALS}
log[c].append("tamano de la pagina de 100 por objetivo (bytes): " + json.dumps(sizes))
rec(c, "pagina de 100 de otros-objetivos responde en < 500 ms", get("/v1/goals/otros-objetivos/plants?limit=100")[4] < 500)

# ---------- salida ----------
with open(EV / "results.tsv", "w") as f:
    f.write("caso\tcomprobacion\tresultado\tdetalle\n")
    for r in results: f.write(redact("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r)) + "\n")
for c, lines in log.items():
    (EV / f"{c}.txt").write_text(redact("\n".join(lines)) + "\n")
tot = collections.Counter(r[2] for r in results)
print(dict(tot))
for r in results:
    if r[2] == "FALLA": print("FALLA", redact(str(r)))
by = collections.defaultdict(collections.Counter)
for r in results: by[r[0]][r[2]] += 1
for k in sorted(by): print(k, dict(by[k]))
