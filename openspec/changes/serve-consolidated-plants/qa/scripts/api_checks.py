#!/usr/bin/env python3 -I
"""11.2: pruebas de la API local (servicio de docker compose, base de la semilla completa) del cambio serve-consolidated-plants.

Entorno:
  QA_TOKEN   token de prueba valido (nunca se escribe en la evidencia: se sustituye por <token-app>)
  QA_BASE    URL base (por defecto http://127.0.0.1:8080)
  QA_DB      ruta de data/build/catalog.db (solo lectura; es el oraculo independiente de la API)
Uso: api_checks.py <repo> <carpeta de evidencia>
Solo usa la libreria estandar. Escribe results.tsv y un .txt por grupo de casos en la carpeta de evidencia.
"""
import collections, json, os, pathlib, re, sqlite3, statistics, sys, time, unicodedata, urllib.error, urllib.request

REPO = pathlib.Path(sys.argv[1]); EV = pathlib.Path(sys.argv[2]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080")
TOKEN = os.environ["QA_TOKEN"]
DB = os.environ["QA_DB"]
SPEC = json.load(open(REPO / "backend" / "openapi.json"))
OLD_NAMES = REPO / "openspec/changes/archive/2026-10-26-consolidate-catalog-seed/qa/evidence/api/API-04-old-names-not-found.tsv"

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
def get(path, token=TOKEN, headers=None):
    h = dict(headers or {})
    if token is not None: h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=h)
    t0 = time.perf_counter()
    try:
        r = urllib.request.urlopen(req, timeout=30)
        status, hd, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, hd, body = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    dt = (time.perf_counter() - t0) * 1000
    try: j = json.loads(body)
    except Exception: j = None
    return status, hd, j, body.decode("utf-8", "replace"), dt

def redact(s): return s.replace(TOKEN, "<token-app>")

results = []; log = collections.defaultdict(list)
def rec(case, name, ok, detail=""):
    results.append((case, name, "PASA" if ok else "FALLA", detail))
    log[case].append(f"{'PASA ' if ok else 'FALLA'} {name} {detail}")
def obs(case, text): results.append((case, text, "OBS", "")); log[case].append("OBS   " + text)
def dump(case, title, path, status, hd, body, limit=4000, auth=True):
    keep = {k: v for k, v in hd.items() if k in ("content-type", "www-authenticate", "content-location", "content-length")}
    b = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=1)
    if len(b) > limit: b = b[:limit] + f"\n... (recortado, {len(b)} caracteres)"
    log[case].append(redact(f"--- {title}\nGET {path}\n{'Authorization: Bearer <token-app>' if auth else '(sin Authorization)'}\n-> {status} {json.dumps(keep, ensure_ascii=False)}\n{b}\n"))

def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()
def slug(t):
    return re.sub(r"[^a-z0-9]+", " ", norm(t)).strip().replace(" ", "-")

db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ids = [r[0] for r in db.execute("select id from plant order by scientific_name, id")]
N = len(ids)
alias_map = dict(db.execute("select alias, plant_id from plant_alias"))
FLAG_CODES = [r[0] for r in db.execute("select distinct code from plant_review_flag")]
SRC = {r[0]: r[1:] for r in db.execute("select id,name,license,license_url,citation,url from source")}

# =========================================================================================
# API-01 listado: displayName, contenido de cada elemento, paginacion
# =========================================================================================
c = "API-01"
st, hd, j, raw, _ = get("/v1/plants")
dump(c, "listado por defecto", "/v1/plants", st, hd, j, 1800)
_, lsch = op_schema("/v1/plants", "get", 200)
e = validate(j, lsch)
rec(c, "200 y cumple PageDto_PlantSummaryDto", st == 200 and not e, "; ".join(e[:3]))
rec(c, f"total = {N}", j["total"] == N, str(j["total"]))
rec(c, "todos los elementos llevan displayName (texto no vacio)", all(isinstance(i.get("displayName"), str) and i["displayName"] for i in j["items"]))
rec(c, "familia presente como texto o null en cada elemento", all("family" in i and (i["family"] is None or isinstance(i["family"], str)) for i in j["items"]))
seen = []; off = 0; viol = []; t_list = []
while True:
    st, hd, jj, _, dt = get(f"/v1/plants?limit=100&offset={off}"); t_list.append(dt)
    if st != 200: viol.append(f"offset {off}: {st}"); break
    e = validate(jj, lsch)
    if e: viol.append(f"offset {off}: {e[0]}")
    seen += jj["items"]
    if len(jj["items"]) < 100: break
    off += 100
rec(c, "recorrido completo (limit=100) sin errores de contrato", not viol, "; ".join(viol[:3]))
rec(c, f"{N} ids unicos en el orden de nombre cientifico e id", [i["id"] for i in seen] == ids, f"{len(seen)} elementos")
# displayName y orden de nombres comunes en el listado contra la base
prof = dict(db.execute("select plant_id, display_name from plant_profile"))
sci = dict(db.execute("select id, scientific_name from plant"))
bad_dn = [i["id"] for i in seen if i["displayName"] != (prof.get(i["id"]) or sci[i["id"]])]
rec(c, "displayName = plant_profile.display_name en las 2.354 plantas", not bad_dn, str(bad_dn[:5]))
commons = collections.defaultdict(list)
for pid, t, lang in db.execute("select plant_id, text, language from plant_name where kind='common'"): commons[pid].append((t, lang))
bad_order = []; sci_dn = 0; with_other = 0; dup_dn = []
for i in seen:
    exp_set = sorted(commons[i["id"]])
    got = [(x["text"], x["language"]) for x in i["commonNames"]]
    if sorted(got) != exp_set: bad_order.append((i["id"], "conjunto distinto")); continue
    dn = i["displayName"]
    if any(t == dn for t, _ in exp_set):
        exp = [x for x in exp_set if x[0] == dn]
        rest = [x for x in exp_set if x not in exp]
        if len(exp) > 1: dup_dn.append((i["id"], exp))
        if got != exp + rest: bad_order.append((i["id"], got[:3]))
    else:
        sci_dn += 1
        if exp_set: with_other += 1
        if got != exp_set: bad_order.append((i["id"], got[:3]))
rec(c, "commonNames: displayName primero (si es nombre comun) y el resto por texto e idioma (orden binario); sin destacado si displayName es cientifico", not bad_order, f"{len(bad_order)} desvios, p. ej. {bad_order[:3]}")
obs(c, f"plantas cuyo displayName coincide en texto con mas de un nombre comun (p. ej. 'Sisal' en y es): {len(dup_dn)}; el de idioma en queda antes que el es en {sum(1 for _, e in dup_dn if e[0][1] != 'es')}; p. ej. {dup_dn[:2]}")
obs(c, f"plantas cuyo displayName no es un nombre comun (nombre cientifico): {sci_dn}; de ellas con comunes en otros idiomas: {with_other}")
no_common_dn_sci = [i for i in seen if not i["commonNames"] and i["displayName"] != sci[i["id"]]]
rec(c, "planta sin nombres comunes: displayName = nombre cientifico y commonNames vacio", not no_common_dn_sci, str([i["id"] for i in no_common_dn_sci[:5]]))
log[c].append(f"tiempo del listado (limit=100): mediana {statistics.median(t_list):.1f} ms, max {max(t_list):.1f} ms, {len(t_list)} paginas")

# =========================================================================================
# API-02 detalle de todas las plantas contra la base (censo)
# =========================================================================================
c = "API-02"
_, dsch = op_schema("/v1/plants/{id}", "get", 200)
details = {}; times = []; sizes = {}; contract_err = []; raws = {}
for pid in ids:
    st, hd, jj, raw, dt = get(f"/v1/plants/{pid}")
    times.append((dt, pid)); sizes[pid] = len(raw)
    if st != 200: contract_err.append((pid, f"HTTP {st}")); continue
    e = validate(jj, dsch)
    if e: contract_err.append((pid, e[0]))
    if "Content-Location".lower() in hd: contract_err.append((pid, "Content-Location en un id canonico"))
    details[pid] = jj; raws[pid] = raw
rec(c, f"GET /v1/plants/{{id}} responde 200 y cumple PlantDto en las {N} plantas", len(details) == N and not contract_err, f"{len(contract_err)} fallos {contract_err[:3]}")
rec(c, "ningun id canonico lleva Content-Location", not any("Content-Location" in str(x) for _, x in contract_err))
bad = [p for p, d in details.items() if any(k not in d for k in SPEC["components"]["schemas"]["PlantDto"]["required"])]
rec(c, "campos requeridos siempre presentes (aunque vacios o null)", not bad, str(bad[:3]))
fam_missing = [p for p, d in details.items() if "family" not in d]
rec(c, "family siempre presente (texto o null)", not fam_missing, f"{len(fam_missing)} sin la clave, p. ej. {fam_missing[:3]}")
allraw = "\n".join(raws.values()) + "\n".join(json.dumps(x) for x in [])
rec(c, "ninguna respuesta contiene 'reviewFlags'", "reviewFlags" not in allraw and "reviewflags" not in allraw.lower())
hits = [code for code in FLAG_CODES if code in allraw]
rec(c, "ninguna respuesta contiene un codigo de reviewFlag", not hits, str(hits))
def keys_deep(x, acc):
    if isinstance(x, dict):
        for k, v in x.items(): acc.add(k); keys_deep(v, acc)
    elif isinstance(x, list):
        for v in x: keys_deep(v, acc)
allkeys = set()
for d in details.values(): keys_deep(d, allkeys)
rec(c, "ningun nombre de campo es de fuente/dataset/flag (source, dataset, flags...)", not (allkeys & {"source", "sources", "dataset", "datasets", "flags", "reviewFlags", "pendingReview", "pending_review"}), str(sorted(allkeys)))
log[c].append("campos usados en el detalle: " + ", ".join(sorted(allkeys)))
ts = sorted(t for t, _ in times)
log[c].append(f"tiempos del detalle (una peticion secuencial por planta, {N} plantas, base real, API en contenedor local): mediana {statistics.median(ts):.1f} ms, p95 {ts[int(len(ts)*.95)]:.1f} ms, p99 {ts[int(len(ts)*.99)]:.1f} ms, max {ts[-1]:.1f} ms")
log[c].append("las 5 mas lentas: " + ", ".join(f"{p} {t:.0f} ms ({sizes[p]} B)" for t, p in sorted(times, reverse=True)[:5]))
log[c].append("las 5 de mayor tamano: " + ", ".join(f"{p} {s} B" for p, s in sorted(sizes.items(), key=lambda x: -x[1])[:5]) + f"; mediana {int(statistics.median(sizes.values()))} B")

# --- displayName, nombres
c = "API-03"
bad_dn = [p for p, d in details.items() if d["displayName"] != (prof.get(p) or sci[p])]
rec(c, "detalle: displayName = plant_profile.display_name", not bad_dn, str(bad_dn[:5]))
bad = []
scn = collections.defaultdict(list)
for pid, t, lang in db.execute("select plant_id, text, language from plant_name where kind='scientific'"): scn[pid].append((t, lang))
for p, d in details.items():
    kinds = [n["kind"] for n in d["names"]]
    if kinds != sorted(kinds, key=lambda k: 0 if k == "scientific" else 1): bad.append((p, "cientificos no van antes"))
    got_c = [(n["text"], n["language"]) for n in d["names"] if n["kind"] == "common"]
    dn = d["displayName"]
    exp = sorted(commons[p])
    if any(t == dn for t, _ in exp):
        first = [x for x in exp if x[0] == dn]
        exp = first + [x for x in exp if x not in first]
    if got_c != exp: bad.append((p, "comunes", got_c[:3], exp[:3]))
    if sorted((n["text"], n["language"]) for n in d["names"] if n["kind"] == "scientific") != sorted(scn[p]): bad.append((p, "cientificos distintos"))
rec(c, "names: cientificos antes que comunes; comunes con displayName primero y el resto por texto e idioma", not bad, f"{len(bad)} desvios {bad[:2]}")
syn_bad = [p for p, d in details.items() if d["scientificName"] in d["synonyms"] or d["synonyms"] != sorted(d["synonyms"])]
rec(c, "synonyms: sin repetir el nombre aceptado y ordenados por texto", not syn_bad, str(syn_bad[:5]))
exp_syn_bad = []
for p, d in details.items():
    exp = sorted({t for t, _ in scn[p]} - {d["scientificName"]})
    if d["synonyms"] != exp: exp_syn_bad.append((p, d["synonyms"][:2], exp[:2]))
rec(c, "synonyms = nombres cientificos de la base distintos del aceptado", not exp_syn_bad, f"{len(exp_syn_bad)} desvios {exp_syn_bad[:2]}")
# listado vs detalle
ls = {i["id"]: i for i in seen}
mism = [p for p in ids if ls[p]["displayName"] != details[p]["displayName"] or [(x["text"], x["language"]) for x in ls[p]["commonNames"]] != [(n["text"], n["language"]) for n in details[p]["names"] if n["kind"] == "common"]]
rec(c, "listado y detalle coinciden en displayName y comunes", not mism, str(mism[:5]))

# --- perfil
c = "API-04"
pf = {r[0]: r[1:] for r in db.execute("select plant_id, origin, description, oil_type from plant_profile")}
bad = [p for p, d in details.items() if (d["origin"], d["description"], (d["oil"] or {}).get("type")) != tuple(pf.get(p, (None, None, None)))]
rec(c, "origin, description y oil.type = plant_profile", not bad, str(bad[:5]))
rec(c, "oil es null o {type}", all(d["oil"] is None or set(d["oil"]) == {"type"} for d in details.values()))
rec(c, "description <= 400 caracteres", all((d["description"] or "") and len(d["description"]) <= 400 or d["description"] is None for d in details.values()), str(max(len(d["description"] or "") for d in details.values())))
fam = dict(db.execute("select id, family from plant"))
rec(c, "family = plant.family", all(d.get("family") == fam[p] for p, d in details.items()))
# partes
parts = collections.defaultdict(list)
for pid, lab in db.execute("select plant_id, label from plant_part order by label"): parts[pid].append(lab)
bad = [p for p, d in details.items() if sorted(x["label"] for x in d["parts"]) != sorted(parts[p])]
rec(c, "parts = plant_part", not bad, str(bad[:5]))

# --- useGroups
c = "API-05"
grp = collections.defaultdict(list)
for gid, pid, pos, act, asrc, n, ctry, pend in db.execute("select id, plant_id, position, activity, activity_source, n, countries, pending_review from plant_use_group"):
    grp[pid].append(dict(id=gid, pos=pos, activity=act, activitySource=asrc, count=n, countries=json.loads(ctry), pending=pend))
grefs = collections.defaultdict(list)
for gid, key, pos, text, res, rid in db.execute("select use_group_id, key, position, text, resolved, reference_id from plant_use_group_ref order by use_group_id, position"):
    grefs[gid].append(dict(id=rid, citation=text, resolved=bool(res), key=key))
labels = dict(db.execute("select id, citation from reference"))
bad_set = []; bad_ord = []; bad_ref = []; bad_unres = []; bad_uses = []; pend_served = 0; served_total = 0; unres_served = 0; uses_vs_table = 0
for p, d in details.items():
    served = [g for g in grp[p] if not g["pending"]]
    served_total += len(served)
    exp = sorted(served, key=lambda g: (-g["count"], g["activity"]))
    got = d["useGroups"]
    if sorted((g["activity"], g["activitySource"], g["count"]) for g in got) != sorted((g["activity"], g["activitySource"], g["count"]) for g in served):
        bad_set.append(p); continue
    if [(g["activity"], g["count"]) for g in got] != [(g["activity"], g["count"]) for g in exp]: bad_ord.append(p)
    byact = {(g["activity"], g["activitySource"], g["count"]): g for g in served}
    for g in got:
        s = byact[(g["activity"], g["activitySource"], g["count"])]
        if g["activitySource"] != s["activitySource"] or g["countries"] != s["countries"]: bad_ref.append((p, g["activity"], "fuente o paises"))
        exp_refs = [dict(id=r["id"], citation=r["citation"], resolved=r["resolved"]) for r in grefs[s["id"]]]
        if g["references"] != exp_refs:
            if sorted(map(json.dumps, g["references"])) == sorted(map(json.dumps, exp_refs)): bad_ref.append((p, g["activity"], "orden de referencias"))
            else: bad_ref.append((p, g["activity"], g["references"][:1], exp_refs[:1]))
        for r in g["references"]:
            if r["resolved"] != (r["id"] is not None): bad_unres.append((p, r))
            if not r["resolved"]:
                unres_served += 1
                if not r["citation"].endswith(" (sin resolver)"): bad_unres.append((p, r))
            elif r["citation"] == labels.get(r["id"]) and r["citation"].startswith(("USDA Dr. Duke: referencia", "EMA:")): bad_unres.append((p, "cita = etiqueta", r))
    # uses: una fila por referencia resuelta de los grupos servidos, con la etiqueta
    exp_uses = sorted({(g["activity"], r["id"], labels[r["id"]]) for g in served for r in grefs[g["id"]] if r["resolved"]})
    got_uses = sorted((u["activity"], u["reference"]["id"], u["reference"]["citation"]) for u in d["uses"])
    if got_uses != exp_uses: bad_uses.append((p, len(got_uses), len(exp_uses)))
rec(c, "useGroups: solo los grupos con pending_review = 0 (actividad y count), 17.160 aprox.", not bad_set, f"{len(bad_set)} plantas con conjunto distinto {bad_set[:3]}; servidos={served_total}")
rec(c, "useGroups ordenados por count descendente y luego actividad", not bad_ord, f"{len(bad_ord)} {bad_ord[:3]}")
rec(c, "useGroups: activitySource, paises y referencias (texto completo en citation, orden de la semilla)", not bad_ref, f"{len(bad_ref)} {bad_ref[:3]}")
rec(c, "referencias sin resolver: id nulo, resolved falso y cita '<clave> (sin resolver)'; ninguna cita resuelta es la etiqueta corta", not bad_unres, f"{len(bad_unres)} {bad_unres[:2]}; sin resolver servidas={unres_served}")
rec(c, "uses = una fila por actividad y referencia resuelta de los grupos servidos (sin repetir), con la etiqueta en citation (compatibilidad)", not bad_uses, f"{len(bad_uses)} {bad_uses[:3]}")
pend_api = sum(1 for g in grp.values() for x in g if x["pending"])
obs(c, f"grupos con pending_review=1 en la base: {pend_api}; ninguno debe servirse (servidos {served_total} de {sum(len(v) for v in grp.values())})")

# --- goals
c = "API-06"
gl = collections.defaultdict(list)
gname = dict(db.execute("select id, label from goal")); sname = dict(db.execute("select id, label from goal_subarea"))
grefs_goal = collections.defaultdict(list)
for pgid, rid in db.execute("select plant_goal_id, reference_id from plant_goal_ref order by plant_goal_id, reference_id"): grefs_goal[pgid].append(rid)
for pgid, pid, goal, sub, area, ev, pend in db.execute("select id, plant_id, goal_id, subarea_id, area, evidence, pending_review from plant_goal"):
    gl[pid].append(dict(pgid=pgid, id=goal, sub=sub, area=area, evidence=ev, pending=pend))
bad_goal = []; bad_gord = []; pend_goal_p = []
for p, d in details.items():
    exp = [g for g in gl[p] if not g["pending"]]
    if any(g["pending"] for g in gl[p]): pend_goal_p.append(p)
    got = d["goals"]
    key = lambda g: (g["id"], g["subarea"], g["area"])
    if sorted((g["id"], g["subarea"], g["area"], g["evidence"]) for g in got) != sorted((g["id"], sname.get(g["sub"]) if g["sub"] else None, g["area"], g["evidence"]) for g in exp):
        bad_goal.append(p); continue
    names = [g["name"] for g in got]
    if names != sorted(names): bad_gord.append(p)
    for g in got:
        if g["name"] != gname[g["id"]]: bad_goal.append((p, "nombre"))
        if g["subarea"] and g["id"] != "otros-objetivos": bad_goal.append((p, "subarea fuera de otros-objetivos"))
        for r in g["references"]:
            if not r["citation"]: bad_goal.append((p, "cita vacia"))
rec(c, "goals = plant_goal sin los pending_review (id, nombre, subarea, area, evidence)", not bad_goal, f"{len(bad_goal)} {bad_goal[:3]}")
rec(c, "goals ordenados por nombre", not bad_gord, str(bad_gord[:3]))
rec(c, "hypericum-perforatum no sirve relajacion-estres y conserva el resto", "hypericum-perforatum" in pend_goal_p and "relajacion-estres" not in [g["id"] for g in details["hypericum-perforatum"]["goals"]] and bool(details["hypericum-perforatum"]["goals"]), str([g["id"] for g in details["hypericum-perforatum"]["goals"]]))
rec(c, "ninguna otra planta tiene un objetivo pendiente en la base", pend_goal_p == ["hypericum-perforatum"], str(pend_goal_p))

# --- safety
c = "API-07"
sf = {r[0]: r[1:] for r in db.execute("select plant_id, level, text from plant_safety")}
srefs = collections.defaultdict(list)
for pid, rid in db.execute("select plant_id, reference_id from plant_safety_ref order by reference_id"): srefs[pid].append(rid)
bad = []
for p, d in details.items():
    s = d["safety"]
    if p not in sf:
        if s is not None: bad.append((p, "safety sin fila"))
        continue
    if s is None or (s["level"], s["text"]) != sf[p] or [r["id"] for r in s["references"]] != srefs[p] and sorted(r["id"] for r in s["references"]) != sorted(srefs[p]): bad.append((p, "distinto"))
    elif any(r["citation"] != labels[r["id"]] for r in s["references"]): bad.append((p, "cita"))
rec(c, "safety = plant_safety (nivel, texto, referencias con cita); null solo si no hay fila", not bad, f"{len(bad)} {bad[:3]}")
lv = collections.Counter((d["safety"] or {}).get("level", "SIN-SAFETY") if d["safety"] else "safety-null" for d in details.values())
log[c].append(f"distribucion de safety.level (API): {dict(lv)}")
eu = details["eucalyptus-globulus"]["safety"]
rec(c, "eucalipto: safety con level null, texto y referencias (no safety null)", eu is not None and eu["level"] is None and bool(eu["text"]) and bool(eu["references"]), json.dumps(eu, ensure_ascii=False)[:300] if eu else "None")
rec(c, "safety.level solo alto, medio, bajo o null", all((d["safety"] is None) or d["safety"]["level"] in ("alto", "medio", "bajo", None) for d in details.values()))

# --- image
c = "API-08"
im = {r[0]: r[1:] for r in db.execute("select plant_id,url,page_url,author,license,license_url,attribution_required from plant_image")}
bad = []
for p, d in details.items():
    i = d["image"]
    if p not in im:
        if i is not None: bad.append((p, "imagen sin fila"))
        continue
    exp = dict(zip(["url", "pageUrl", "author", "license", "licenseUrl", "attributionRequired"], im[p])); exp["attributionRequired"] = bool(exp["attributionRequired"])
    if i != exp: bad.append((p, i, exp))
rec(c, "image = plant_image; null solo si no hay fila", not bad, f"{len(bad)} {bad[:2]}")
n_img = sum(1 for d in details.values() if d["image"]); n_noimg = N - n_img
log[c].append(f"con imagen: {n_img}; sin imagen: {n_noimg}")
rec(c, "image presente => licencia y pageUrl no vacios", all(d["image"] is None or (d["image"]["license"] and d["image"]["pageUrl"]) for d in details.values()))
rec(c, "todas las image.url son https y de upload.wikimedia.org", all(d["image"] is None or re.match(r"https://upload\.wikimedia\.org/", d["image"]["url"]) for d in details.values()))
rec(c, "todas las image.pageUrl son https", all(d["image"] is None or d["image"]["pageUrl"].startswith("https://") for d in details.values()))
lic = collections.Counter(d["image"]["license"] for d in details.values() if d["image"])
log[c].append(f"licencias de imagen: {dict(lic)}")
missing_author = [p for p, d in details.items() if d["image"] and d["image"]["attributionRequired"] and not (d["image"]["author"] or "").strip()]
rec(c, "imagenes con atribucion obligatoria llevan autor (CC BY / CC BY-SA sin autor seria atribucion faltante)", not missing_author, f"{len(missing_author)} sin autor: {missing_author[:8]}")
cc_no_req = [p for p, d in details.items() if d["image"] and d["image"]["license"].upper().startswith("CC BY") and not d["image"]["attributionRequired"]]
rec(c, "licencias CC BY* marcan attributionRequired verdadero", not cc_no_req, str(cc_no_req[:5]))
cc_no_url = [p for p, d in details.items() if d["image"] and d["image"]["license"].upper().startswith("CC BY") and not d["image"]["licenseUrl"]]
rec(c, "licencias CC BY* llevan licenseUrl", not cc_no_url, f"{len(cc_no_url)} {cc_no_url[:5]}")

# --- credits
c = "API-09"
bad_cr = []; dup = []; unsorted = []
src_by_name = {v[0]: (k, *v[1:]) for k, v in SRC.items()}
for p, d in details.items():
    cr = d["credits"]
    names = [x["name"] for x in cr]
    if len(names) != len(set(names)): dup.append(p)
    if names != sorted(names): unsorted.append(p)
    for x in cr:
        s = src_by_name.get(x["name"])
        if not s: bad_cr.append((p, "credito sin fuente", x["name"])); continue
        _, lic_, lurl, cit, url = s
        if (x["license"], x["licenseUrl"], x["attribution"], x["url"]) != (lic_, lurl, cit, url):
            # la URL de Wikipedia es la del articulo de la planta
            if x["name"] == "Wikipedia en español" and (x["license"], x["licenseUrl"], x["attribution"]) == (lic_, lurl, cit) and x["url"] and x["url"].startswith("https://es.wikipedia.org/wiki/"): continue
            bad_cr.append((p, "campos distintos de source", x["name"], x))
rec(c, "credits sin repeticiones", not dup, str(dup[:3]))
rec(c, "credits ordenados por nombre", not unsorted, str(unsorted[:3]))
rec(c, "cada credito = fila de source (licencia, licenseUrl de source.license_url, atribucion, url)", not bad_cr, f"{len(bad_cr)} {bad_cr[:2]}")
lu = collections.defaultdict(set)
for d in details.values():
    for x in d["credits"]: lu[x["name"]].add(x["licenseUrl"])
log[c].append("licenseUrl por credito: " + json.dumps({k: sorted(map(str, v)) for k, v in lu.items()}, ensure_ascii=False))
want = {"Wikipedia en español": {"https://creativecommons.org/licenses/by-sa/4.0/"}, "EFSA Compendium of Botanicals": {"https://creativecommons.org/licenses/by/4.0/"}, "World Checklist of Vascular Plants (WCVP)": {"https://creativecommons.org/licenses/by/3.0/"}}
rec(c, "licenseUrl oficial de Creative Commons en Wikipedia, EFSA y WCVP", all(lu.get(k) == v for k, v in want.items()), "")
nulls = [k for k, v in lu.items() if k.startswith(("EMA", "TPPT", "Wikimedia", "Commons"))]
rec(c, "licenseUrl null para la EMA y TPPT", all(lu[k] == {None} for k in nulls) and len(nulls) >= 3, str({k: sorted(map(str, lu[k])) for k in nulls}))
rec(c, "licenseUrl siempre null o https", all(u is None or u.startswith("https://") for v in lu.values() for u in v))
# esperado: fuentes alcanzables desde los datos de la planta
rsrc = collections.defaultdict(set)
for rid, sid in db.execute("select reference_id, source_id from reference_source"): rsrc[rid].add(sid)
exp_src = collections.defaultdict(set)
for pid, sid in db.execute("select pn.plant_id, s.source_id from plant_name_source s join plant_name pn on pn.id = s.plant_name_id"): exp_src[pid].add(sid)
for pid, sid in db.execute("select pu.plant_id, s.source_id from plant_use_source s join plant_use pu on pu.id = s.plant_use_id"): exp_src[pid].add(sid)
for pid, sid in db.execute("select id, family_source_id from plant where family_source_id is not null"): exp_src[pid].add(sid)
for pid, rid in db.execute("select plant_id, reference_id from plant_profile_ref"): exp_src[pid] |= rsrc[rid]
for pid, rid in db.execute("select g.plant_id, r.reference_id from plant_goal_ref r join plant_goal g on g.id = r.plant_goal_id where r.reference_id is not null"): exp_src[pid] |= rsrc[rid]
for pid, rid in db.execute("select plant_id, reference_id from plant_safety_ref"): exp_src[pid] |= rsrc[rid]
for pid, rid in db.execute("select g.plant_id, r.reference_id from plant_use_group_ref r join plant_use_group g on g.id = r.use_group_id where r.reference_id is not null and g.pending_review = 0"): exp_src[pid] |= rsrc[rid]
missing = []; extra = []
idname = {k: v[0] for k, v in SRC.items()}
for p, d in details.items():
    got = {x["name"] for x in d["credits"]}
    exp = {idname[s] for s in exp_src[p]}
    if exp - got: missing.append((p, sorted(exp - got)))
    if got - exp: extra.append((p, sorted(got - exp)))
rec(c, "credits incluye cada fuente que respalda un dato servido de la planta (nombres, usos, familia, perfil, objetivos, seguridad, grupos de uso)", not missing, f"{len(missing)} plantas con faltantes, p. ej. {missing[:3]}")
rec(c, "credits no incluye fuentes que no respaldan ningun dato servido", not extra, f"{len(extra)} plantas con sobrantes, p. ej. {extra[:3]}")
wk_desc = [p for p, d in details.items() if d["description"] and any(x["name"] == "Wikipedia en español" for x in d["credits"])]
wk_ref = {r[0] for r in db.execute("select ppr.plant_id from plant_profile_ref ppr join reference r on r.id=ppr.reference_id where ppr.field='description' and (r.dataset like '%Wikipedia%' or r.id like 'wikipedia%')")}
nowk = [p for p, d in details.items() if p in wk_ref and not any(x["name"] == "Wikipedia en español" for x in d["credits"])]
rec(c, "descripcion respaldada por Wikipedia => credito de Wikipedia con enlace al articulo", not nowk, f"{len(nowk)} {nowk[:5]}; con credito de Wikipedia: {len(wk_desc)}")
none_cr = [p for p, d in details.items() if not d["credits"]]
log[c].append(f"plantas con credits vacio: {len(none_cr)} {none_cr[:5]}")

# =========================================================================================
# API-10 alias de identificadores
# =========================================================================================
c = "API-10"
bad = []; t_alias = []
for a, pid in alias_map.items():
    if a in details: bad.append((a, "alias igual a un id de planta")); continue
    st, hd, jj, raw, dt = get(f"/v1/plants/{a}"); t_alias.append(dt)
    if st != 200 or jj["id"] != pid or hd.get("content-location") != f"/v1/plants/{pid}": bad.append((a, st, jj.get("id") if jj else None, hd.get("content-location")))
    elif jj != details[pid]: bad.append((a, "cuerpo distinto al canonico"))
rec(c, f"los {len(alias_map)} alias resuelven 200 con el id canonico en el cuerpo y en Content-Location (cuerpo igual al canonico)", not bad, f"{len(bad)} {bad[:3]}")
st, hd, jj, raw, _ = get("/v1/plants/rosmarinus-officinalis"); dump(c, "alias de un renombre", "/v1/plants/rosmarinus-officinalis", st, hd, {"id": jj["id"], "scientificName": jj["scientificName"], "displayName": jj["displayName"]}, 600)
rec(c, "rosmarinus-officinalis -> salvia-rosmarinus, Content-Location /v1/plants/salvia-rosmarinus", st == 200 and jj["id"] == "salvia-rosmarinus" and hd.get("content-location") == "/v1/plants/salvia-rosmarinus")
st, hd, jj, raw, _ = get("/v1/plants/salvia-rosmarinus"); rec(c, "id canonico: 200 sin Content-Location", st == 200 and "content-location" not in hd)
st, hd, jj, raw, _ = get("/v1/plants/no-existe-xyz"); dump(c, "id inexistente", "/v1/plants/no-existe-xyz", st, hd, jj)
_, psch = op_schema("/v1/plants/{id}", "get", 404)
rec(c, "id desconocido: 404 application/problem+json con el formato de error", st == 404 and hd.get("content-type", "").startswith("application/problem+json") and not validate(jj, psch), f"{st} {hd.get('content-type')}")
st, hd, jj, raw, _ = get("/v1/plants/rosmarinus-officinalis", token=None); dump(c, "alias sin token", "/v1/plants/rosmarinus-officinalis", st, hd, jj, auth=False)
rec(c, "alias sin token: 401 con WWW-Authenticate: Bearer y sin Content-Location", st == 401 and hd.get("www-authenticate") == "Bearer" and "content-location" not in hd, str(st))
listed_alias = [i["id"] for i in seen if i["id"] in alias_map]
rec(c, "ningun alias aparece como id en el listado", not listed_alias, str(listed_alias[:3]))
log[c].append(f"tiempo del detalle por alias: mediana {statistics.median(t_alias):.1f} ms, max {max(t_alias):.1f} ms")

# =========================================================================================
# API-11 autenticacion
# =========================================================================================
c = "API-11"
for path in ("/v1/plants", "/v1/plants/lavandula-angustifolia"):
    for label, tok, hdrs in (("sin token", None, None), ("token incorrecto", "x" * 40, None), ("esquema Basic", None, {"Authorization": "Basic abcdefgh"}), ("token vacio", "", None)):
        st, hd, jj, raw, _ = get(path, token=tok, headers=hdrs)
        dump(c, f"{path} {label}", path, st, hd, jj, 500, auth=False)
        rec(c, f"{path} {label}: 401 con WWW-Authenticate: Bearer", st == 401 and hd.get("www-authenticate") == "Bearer", str(st))
st, hd, jj, raw, _ = get("/health", token=None); rec(c, "/health sin token: 200", st == 200)
st, hd, jj, raw, _ = get("/openapi.json", token=None)
rec(c, "/openapi.json sin token: 200 y coincide con backend/openapi.json (campos nuevos presentes)", st == 200 and jj == SPEC, str(st))
txt = json.dumps(SPEC)
names_all = set(re.findall(r'"([A-Za-z_]+)":', txt)) | set(SPEC["components"]["schemas"])
forb = [w for w in ("usda", "wcvp", "efsa", "wikipedia", "tppt", "duke", "wikidata", "commons", "reviewflag", "dataset") if any(w in n.lower() for n in names_all)]
rec(c, "OpenAPI: ningun campo ni esquema contiene el nombre de un dataset ni reviewFlags", not forb, str(forb))

# =========================================================================================
# API-12 busqueda: sinonimo, alias, nombres anteriores, normalizacion
# =========================================================================================
c = "API-12"
def ids_of(q, limit=100):
    st, hd, jj, raw, dt = get(f"/v1/plants?limit={limit}&q=" + urllib.request.quote(q, safe=""))
    return st, jj, dt
def oracle(q):
    nq = norm(q)
    if not nq: return set(ids)
    out = {r[0] for r in db.execute("select distinct plant_id from plant_name where normalized like ? escape '\\'", ("%" + nq.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",))}
    sq = slug(q)
    if sq:
        for a, pid in alias_map.items():
            if sq in a: out.add(pid)
    return out
checks = [("rosmarinus officinalis", "salvia-rosmarinus"), ("matricaria recutita", "matricaria-chamomilla"), ("Matricaria  Recutita ", "matricaria-chamomilla"),
          ("MATRICARIA RECUTITA", "matricaria-chamomilla"), ("Mentha x piperita subsp. nothosubsp. piperita", "mentha-x-piperita"), ("mentha x piperita", "mentha-x-piperita"),
          ("lavandula", "lavandula-angustifolia"), ("manzanilla", "matricaria-chamomilla"), ("menta", "mentha-x-piperita"), ("romero", "salvia-rosmarinus"), ("eucalipto", "eucalyptus-globulus"), ("Espliego", None)]
for q, exp in checks:
    st, jj, _ = ids_of(q); got = [i["id"] for i in jj["items"]] if jj else []
    ok = st == 200 and (exp is None or exp in got) and len(got) == len(set(got)) and jj["total"] == len(got) if jj and jj["total"] <= 100 else st == 200 and exp in got
    rec(c, f"q={q!r} encuentra {exp}", ok, f"total={jj['total'] if jj else None} ids={got[:4]}")
    if jj: dump(c, f"q={q!r}", f"/v1/plants?q={q}", st, {}, {"total": jj["total"], "ids": got[:8]}, 500)
st, jj, _ = ids_of("matricaria recutita")
txt = json.dumps(jj, ensure_ascii=False).lower()
rec(c, "matricaria recutita: el alias no aparece como nombre (ni 'matricaria-recutita' ni 'Matricaria recutita' en el resultado)", "matricaria-recutita" not in txt and "matricaria recutita" not in txt)
st, jj, _ = ids_of("mentha piperita")
rec(c, "limite conocido: 'mentha piperita' (sin la x) da 0 resultados", st == 200 and jj["total"] == 0 and jj["items"] == [], f"total={jj['total']}")
# sin duplicados: nombre y alias coinciden
st, jj, _ = ids_of("rosmarinus officinalis"); g = [i["id"] for i in jj["items"]]
rec(c, "rosmarinus officinalis: salvia-rosmarinus una sola vez y total coherente", g.count("salvia-rosmarinus") == 1 and jj["total"] == len(g), str(g))
# 357 nombres anteriores
rows = [l.rstrip("\n").split("\t") for l in open(OLD_NAMES, encoding="utf-8")][1:]
fail = []; dups = []; extra_alias = []; tq = []
for old_id, old_name, new_id, *_ in rows:
    st, jj, dt = ids_of(old_name, 100); tq.append(dt)
    got = [i["id"] for i in jj["items"]] if jj else []
    if st != 200 or new_id not in got: fail.append((old_name, new_id, got[:3]))
    if len(got) != len(set(got)) or (jj and jj["total"] != len(got)): dups.append(old_name)
    if jj and any(old_id == i["id"] for i in jj["items"]): extra_alias.append(old_name)
rec(c, f"los {len(rows)} nombres anteriores de API-04 (cambio 1) encuentran su planta nueva", not fail, f"{len(fail)} sin resultado {fail[:3]}")
rec(c, "sin duplicados ni total incoherente en esas busquedas", not dups, str(dups[:3]))
rec(c, "el alias (id anterior) nunca aparece como id de un elemento", not extra_alias, str(extra_alias[:3]))
log[c].append(f"tiempo de la busqueda por nombre anterior: mediana {statistics.median(tq):.1f} ms, max {max(tq):.1f} ms")
# oraculo sobre consultas variadas
qs = ["lavanda", "LAVANDA", "  lavanda  ", "la  vanda", "lávanda", "salvia", "mentha", "x", "a", "e", "ae", "aceite", "arnica", "árnica", "velvetleaf", "Abutilon theophrasti", "abutilon", "sp", "subsp", "var.", "-", "mentha-x-piperita", "mentha x", "recutita", "nothosubsp", "chamomilla", "ñ", "eucalyptus", "hypericum", "hipérico", "1", "2000"]
bad_or = []; tq2 = []
for q in qs:
    st, jj, dt = ids_of(q, 100); tq2.append(dt)
    if st != 200: bad_or.append((q, st)); continue
    exp = oracle(q)
    if jj["total"] != len(exp): bad_or.append((q[:20], jj["total"], len(exp)))
    elif jj["total"] <= 100 and {i["id"] for i in jj["items"]} != exp: bad_or.append((q[:20], "conjunto"))
rec(c, f"{len(qs)} consultas variadas: total y conjunto = oraculo SQL (nombres normalizados + alias con slug)", not bad_or, f"{len(bad_or)} {bad_or[:4]}")
for q in ("%", "_", "%%", "_a", "a%", "100%", "\\"):
    st, jj, dt = ids_of(q, 100)
    if q in ("%", "_", "%%", "\\"):
        exp = {r[0] for r in db.execute("select distinct plant_id from plant_name where normalized like ? escape '!'", ("%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%",))}
        rec(c, f"q={q!r}: literal, sin comodin (total = nombres que contienen el caracter)", st == 200 and jj["total"] == len(exp), f"total={jj['total'] if jj else st} esperado={len(exp)}")
    else:
        rec(c, f"q={q!r}: 200 sin error", st == 200, f"total={jj['total'] if jj else st}")
for q, name in (("", "vacio"), ("%20%20%20", "solo espacios")):
    st, hd, jj, raw, _ = get("/v1/plants?limit=3&q=" + q)
    rec(c, f"q {name}: igual que sin q", st == 200 and jj["total"] == N)
st, hd, jj, raw, _ = get("/v1/plants?q=zzzzzzzz"); dump(c, "sin coincidencias", "/v1/plants?q=zzzzzzzz", st, hd, jj)
rec(c, "sin coincidencias: 200, lista vacia y total 0", st == 200 and jj["items"] == [] and jj["total"] == 0)
for n in (200, 201, 5000):
    st, hd, jj, raw, _ = get("/v1/plants?q=" + "a" * n)
    rec(c, f"consulta de {n} caracteres: {'200' if n <= 200 else '400 problem+json (limite de q, sin cambios)'}", (st == 200) if n <= 200 else (st == 400 and hd.get("content-type", "").startswith("application/problem+json")), str(st))
for q, name in (("limit=0", "limit=0"), ("limit=101", "limit=101"), ("limit=abc", "limit=abc"), ("offset=-1", "offset=-1")):
    st, hd, jj, raw, _ = get("/v1/plants?" + q)
    rec(c, f"{name}: 400 problem+json", st == 400 and hd.get("content-type", "").startswith("application/problem+json"), str(st))
# orden estable con q que activa alias
st, jj, _ = ids_of("a", 100); g = [i["scientificName"] for i in jj["items"]]
rec(c, "orden por nombre cientifico y luego id tambien en una busqueda amplia", [(i["scientificName"], i["id"]) for i in jj["items"]] == sorted((i["scientificName"], i["id"]) for i in jj["items"]))

# =========================================================================================
# API-13 casos puntuales (manzanilla, menta, hiperico, toxica, sin datos, lavanda)
# =========================================================================================
c = "API-13"
def show(pid, keys=None, limit=3000):
    d = details[pid]
    sub = {k: d[k] for k in (keys or d)}
    dump(c, f"detalle de {pid}" + (f" ({', '.join(keys)})" if keys else ""), f"/v1/plants/{pid}", 200, {"content-type": "application/json"}, sub, limit)
lav = details["lavandula-angustifolia"]
rec(c, "lavanda: displayName Lavanda y Lavanda primero entre los comunes", lav["displayName"] == "Lavanda" and lav["names"][1]["text"] == "Lavanda")
stein = [r for g in lav["useGroups"] for r in g["references"] if r["id"] == "usda_reference:Steinmetz"]
rec(c, "lavanda: cita completa de Steinmetz en useGroups", bool(stein) and all(r["citation"] == "Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam." for r in stein), stein[0]["citation"] if stein else "")
rec(c, "lavanda: uses[].reference.citation sigue siendo la etiqueta 'USDA Dr. Duke: referencia Steinmetz'", any(u["reference"]["citation"] == "USDA Dr. Duke: referencia Steinmetz" for u in lav["uses"]) and all(u["reference"]["citation"].startswith("USDA Dr. Duke: referencia") for u in lav["uses"]))
rec(c, "lavanda: grupo de 2 registros con 2 paises antes que los de 1 y orden por actividad", [g["count"] for g in lav["useGroups"]] == sorted((g["count"] for g in lav["useGroups"]), reverse=True))
rec(c, "lavanda: objetivos de la EMA (mejorar-el-sueno, relajacion-estres) con area y cita", {g["id"] for g in lav["goals"]} == {"mejorar-el-sueno", "relajacion-estres"} and all(g["area"] and g["references"] for g in lav["goals"]))
rec(c, "lavanda: credito de Wikipedia con CC BY-SA 4.0, URL de licencia y enlace al articulo; EMA con licenseUrl null", any(x["name"] == "Wikipedia en español" and x["licenseUrl"] == "https://creativecommons.org/licenses/by-sa/4.0/" and x["url"] == "https://es.wikipedia.org/wiki/Lavandula_angustifolia" for x in lav["credits"]) and all(x["licenseUrl"] is None for x in lav["credits"] if x["name"].startswith("EMA")))
show("lavandula-angustifolia", ["id", "displayName", "synonyms", "description", "origin", "oil", "image"]); show("lavandula-angustifolia", ["goals", "credits"], 3500)
for pid in ("matricaria-chamomilla", "chamaemelum-nobile", "mentha-x-piperita"):
    d = details[pid]
    rec(c, f"{pid}: 200, displayName en espanol y usos presentes", bool(d["displayName"]) and d["displayName"] != d["scientificName"] and d["useGroups"] != [] and d["uses"] != [], f"displayName={d['displayName']} grupos={len(d['useGroups'])} usos={len(d['uses'])}")
    show(pid, ["id", "scientificName", "displayName", "synonyms", "goals", "safety"], 2200)
h = details["hypericum-perforatum"]
rec(c, "hiperico: sin relajacion-estres en goals, resto del detalle completo", "relajacion-estres" not in {g["id"] for g in h["goals"]} and h["useGroups"] and h["credits"] is not None, str([g["id"] for g in h["goals"]]))
show("hypericum-perforatum", ["id", "displayName", "goals", "safety"], 2500)
alto = [p for p, d in details.items() if d["safety"] and d["safety"]["level"] == "alto"]
rec(c, f"existen plantas de nivel alto ({len(alto)}) y todas sirven texto y citas", len(alto) == 112 and all(details[p]["safety"]["text"] and details[p]["safety"]["references"] for p in alto), f"{len(alto)}")
show("aconitum-napellus", ["id", "displayName", "safety", "goals"], 2500)
empty = [p for p, d in details.items() if not d["useGroups"] and not d["goals"] and d["safety"] is None and d["image"] is None and d["description"] is None and d["origin"] is None and d["oil"] is None and not d["parts"] and d["family"] is None]
e0 = details["angelica-laxiflora"]
rec(c, "planta sin datos (angelica-laxiflora): 200 con useGroups, goals, uses, parts y synonyms vacios, safety, image, description, origin, oil y family null", "angelica-laxiflora" in empty and e0["uses"] == [] and e0["synonyms"] == [], f"{len(empty)} plantas sin ningun dato consolidado")
show("angelica-laxiflora", None, 2500)
genus = [p for p in details if details[p]["scientificName"].endswith(" sp") or " sp." in details[p]["scientificName"]]
log[c].append(f"plantas de solo genero (nombre cientifico termina en ' sp'): {len(genus)}")
ab = details["abutilon-theophrasti"]
rec(c, "abutilon-theophrasti: displayName cientifico y Velvetleaf entre los comunes sin destacar", ab["displayName"] == "Abutilon theophrasti" and any(n["text"] == "Velvetleaf" for n in ab["names"]))
show("abutilon-theophrasti", ["id", "displayName", "names"], 1500)
cnt_sci = sum(1 for d in details.values() if d["displayName"] == d["scientificName"])
log[c].append(f"plantas con displayName = nombre cientifico: {cnt_sci} (se esperan unas 1.195)")
rec(c, "unas 1.195 plantas con displayName = nombre cientifico", 1190 <= cnt_sci <= 1200, str(cnt_sci))

# =========================================================================================
# API-14 texto: lenguaje de efecto, dosis, seguridad, en los textos servidos
# =========================================================================================
c = "API-14"
EFFECT = re.compile(r"\b(cura|curar|curativ|calma|calmar|alivia|aliviar|ayuda a|ayudar|previene|prevenir|trata|tratar|elimina|eliminar|sana|sanar|mejora|reduce|combate|fortalece|reconforta|beneficios?|eficaz|efectivo|garantiza)\b", re.I)
DOSE = re.compile(r"\b\d+([.,]\d+)?\s*(mg|g|kg|ml|mL|l|gotas?|cucharadas?|cucharaditas?|tazas?|comprimidos?|cápsulas?|capsulas?|veces al día|al día|diarios?|µg|mcg|ui|UI)\b|\bdosis\b|\bposolog", re.I)
SAFE = re.compile(r"\b(segur[ao]s?|inocu[ao]s?|sin riesgos?|libre de riesgos?|no (es )?tóxic[ao]|no tiene toxicidad|apta? para|recomendad[ao]s?)\b", re.I)
hits = collections.defaultdict(list)
for p, d in details.items():
    texts = []
    if d["description"]: texts.append(("description", d["description"]))
    if d["origin"]: texts.append(("origin", d["origin"]))
    for g in d["useGroups"]: texts.append(("useGroup.activity", g["activity"])); texts += [("useGroup.country", x) for x in g["countries"]]
    for g in d["goals"]: texts += [("goal.name", g["name"]), ("goal.area", g["area"]), ("goal.evidence", g["evidence"])]
    if d["safety"]: texts.append(("safety.text", d["safety"]["text"]))
    for field, t in texts:
        for rx, tag in ((EFFECT, "efecto"), (DOSE, "dosis"), (SAFE, "seguridad")):
            m = rx.search(t)
            if m: hits[(tag, field)].append((p, m.group(0), t[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")))
for (tag, field), v in sorted(hits.items()):
    obs(c, f"{tag} en {field}: {len(v)} coincidencias; p. ej. " + "; ".join(f"{p} [{w}] ...{ctx}..." for p, w, ctx in v[:3]))
with open(EV / "API-14-text-scan-hits.tsv", "w", encoding="utf-8") as f:
    f.write("tipo\tcampo\tplanta\tcoincidencia\tcontexto\n")
    for (tag, field), v in sorted(hits.items()):
        for p, w, ctx in v: f.write(f"{tag}\t{field}\t{p}\t{w}\t{ctx}\n")

# =========================================================================================
# salida
# =========================================================================================
with open(EV / "results.tsv", "w", encoding="utf-8") as f:
    f.write("caso\tcomprobacion\testado\tdetalle\n")
    for r in results: f.write(redact("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r)) + "\n")
for case, lines in log.items():
    (EV / f"{case}.txt").write_text(redact("\n".join(lines)) + "\n", encoding="utf-8")
cnt = collections.Counter(r[2] for r in results)
print(dict(cnt))
for r in results:
    if r[2] == "FALLA": print(redact("FALLA", ) , r[0], r[1][:110], "|", redact(str(r[3]))[:200])
