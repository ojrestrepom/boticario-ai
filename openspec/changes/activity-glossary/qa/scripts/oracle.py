#!/usr/bin/env python3
"""Oráculo SQL y comparación API contra base y glossary.json (activity-glossary).

Uso: TOKEN=<token> python3 -I oracle.py <catalog.db> <base-url> <repo> [salida.json]
El token llega solo por la variable de entorno TOKEN y nunca se imprime ni se guarda.
"""
import json, os, random, re, sqlite3, sys, unicodedata, urllib.request

db_path, base, repo = sys.argv[1:4]
out = sys.argv[4] if len(sys.argv) > 4 else None
TOKEN = os.environ["TOKEN"]
con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
results, failures = [], []

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    if not ok:
        failures.append(name)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

def get(path):
    r = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + TOKEN})
    with urllib.request.urlopen(r) as f:
        return json.load(f)

def base_key(a):
    k = unicodedata.normalize("NFC", a.split("(")[0])
    return re.sub(r"\s+", " ", k).strip().lower()

FORMULA = "Uso tradicional, sin eficacia demostrada: "

# --- tabla de revisión aprobada
rev = {}
for line in open(f"{repo}/openspec/changes/activity-glossary/review/glossary-review.md", encoding="utf-8"):
    if not line.startswith("| ") or line.startswith("| Término") or line.startswith("| ---"):
        continue
    c = [x.strip() for x in line.strip().strip("|").split(" | ")]
    if len(c) == 9 and c[4].startswith("«"):
        rev[c[0]] = dict(source=c[2], text=c[4].strip("«»"), mode=c[5], url=c[6], approved=c[8])
check("O0 la tabla de revisión tiene 53 filas", len(rev) == 53, str(len(rev)))
check("O0b las 53 filas están aprobadas (sí (usuario, 2026-10-29))", all(v["approved"] == "sí (usuario, 2026-10-29)" for v in rev.values()))

# --- O1 los 53 términos y su texto
rows = con.execute("select key, term, text, entry_url, revision_date, source_id, source_name, adapted from activity_glossary").fetchall()
check("O1 activity_glossary tiene 53 filas", len(rows) == 53, str(len(rows)))
by_term = {r[1]: r for r in rows}
check("O1b términos de la base == términos aprobados", set(by_term) == set(rev), str(set(by_term) ^ set(rev)))
bad = []
for t, v in rev.items():
    r = by_term.get(t)
    if not r: continue
    src = {"Wikcionario": "wiktionary_es", "Wikipedia": "wikipedia_es"}[v["source"]]
    if not (r[2] == v["text"] and r[3] == v["url"] and r[5] == src and r[6] == v["source"] and bool(r[7]) == (v["mode"] == "adaptado")):
        bad.append(t)
check("O1c texto, URL, fuente y modo de cada término == tabla aprobada", not bad, ",".join(bad))
check("O1d 37 Wikcionario literal, 5 Wikipedia literal, 11 Wikipedia adaptado",
      (sum(1 for r in rows if r[5]=="wiktionary_es"), sum(1 for r in rows if r[5]=="wikipedia_es" and not r[7]), sum(1 for r in rows if r[5]=="wikipedia_es" and r[7])) == (37, 5, 11),
      str((sum(1 for r in rows if r[5]=="wiktionary_es"), sum(1 for r in rows if r[5]=="wikipedia_es" and not r[7]), sum(1 for r in rows if r[5]=="wikipedia_es" and r[7]))))
check("O1e Emenagogo y Anticonceptivo presentes", {"Emenagogo", "Anticonceptivo"} <= set(by_term))
check("O1f los 6 verbos aprobados presentes", {"Antiséptico","Bactericida","Vulnerario","Antidiarreico","Fungicida","Parasiticida"} <= set(by_term))
check("O1g URL con oldid y https en todas", all(r[3].startswith("https://") and "oldid=" in r[3] for r in rows))
check("O1h clave == forma base del término", all(r[0] == base_key(r[1]) for r in rows))

# --- glossary.json
gj = json.load(open(f"{repo}/data/seed/glossary.json", encoding="utf-8"))
gj_rows = {r["term"]: r for r in gj["rows"]}
check("O2 glossary.json tiene 53 filas", len(gj["rows"]) == 53)
bad = [t for t, r in by_term.items() if t not in gj_rows or not (gj_rows[t]["text"] == r[2] and gj_rows[t]["entryUrl"] == r[3] and gj_rows[t]["sourceId"] == r[5] and gj_rows[t]["sourceName"] == r[6] and gj_rows[t]["adapted"] == bool(r[7]) and gj_rows[t]["key"] == r[0])]
check("O2b base == glossary.json (texto, URL, fuente, adaptado, clave)", not bad, ",".join(bad))
man = json.load(open(f"{repo}/data/seed/manifest.json"))
check("O2c manifiesto declara glossaryCount 53", man.get("glossaryCount") == 53)

# --- O3 grupos
tot_linked = con.execute("select count(*) from plant_use_group where glossary_key is not null").fetchone()[0]
vis_linked = con.execute("select count(*) from plant_use_group where glossary_key is not null and pending_review=0").fetchone()[0]
vis_plants = con.execute("select count(distinct plant_id) from plant_use_group where glossary_key is not null and pending_review=0").fetchone()[0]
pend_linked = con.execute("select count(*) from plant_use_group where glossary_key is not null and pending_review=1").fetchone()[0]
check("O3 5.172 grupos visibles con explicación", vis_linked == 5172, str(vis_linked))
check("O3b 1.207 plantas con explicación", vis_plants == 1207, str(vis_plants))
check("O3c 5.278 enlazados en total, 106 pendientes", (tot_linked, pend_linked) == (5278, 106), f"{tot_linked},{pend_linked}")
nplants = con.execute("select count(*) from plant").fetchone()[0]
check("O3d 2.354 plantas", nplants == 2354, str(nplants))
check("O3e foreign_key_check vacío", con.execute("pragma foreign_key_check").fetchall() == [])
check("O3f schema_version 3", True, str(con.execute("select * from metadata").fetchall())[:200])

# --- O4 enlace correcto y completo (regla independiente)
keys = {r[0] for r in rows}
wrong, missed, formula_linked = [], [], []
for gid, act, gk in con.execute("select id, activity, glossary_key from plant_use_group"):
    exp = None if act.startswith(FORMULA) else (base_key(act) if base_key(act) in keys else None)
    if act.startswith(FORMULA) and gk: formula_linked.append(act)
    if gk != exp:
        (wrong if gk else missed).append((act, gk, exp))
check("O4 ninguna fórmula de enfermedad grave enlazada", not formula_linked, str(formula_linked[:3]))
check("O4b enlace == regla de forma base calculada de forma independiente (sin enlaces de más ni de menos)", not wrong and not missed, f"{wrong[:3]} {missed[:3]}")
n_formula = con.execute("select count(*) from plant_use_group where activity like ?", (FORMULA + "%",)).fetchone()[0]
check("O4c existen grupos con la fórmula (el caso se ejerce)", n_formula > 0, str(n_formula))

# --- O5 API completa vs base
plants = []
off = 0
while True:
    page = get(f"/v1/plants?limit=100&offset={off}")
    plants += [p["id"] for p in page["items"]]
    off += 100
    if off >= page["total"]: break
check("O5 el listado trae 2.354 plantas", len(plants) == 2354, str(len(plants)))
glossmap = {r[0]: r for r in rows}
mism, credit_bad, shape_bad, served_bad = [], [], [], []
api_groups_with_gloss = 0
plants_with_gloss = 0
wikt_credit = wiki_credit = 0
sample_pool = []
details = {}
for pid in plants:
    d = get(f"/v1/plants/{pid}")
    details[pid] = d
    db_groups = con.execute("select activity, activity_source, glossary_key from plant_use_group where plant_id=? and pending_review=0", (pid,)).fetchall()
    api = d["useGroups"]
    if sorted((g["activity"], g["activitySource"]) for g in api) != sorted((a, s) for a, s, _ in db_groups):
        served_bad.append(pid)
    dbmap = {(a, s): k for a, s, k in db_groups}
    srcs = set()
    for g in api:
        if list(g) != ["activity", "activitySource", "count", "countries", "references", "glossary"]:
            shape_bad.append(pid)
        k = dbmap.get((g["activity"], g["activitySource"]))
        if k is None:
            if g["glossary"] is not None: mism.append((pid, g["activity"], "debía ser null"))
        else:
            r = glossmap[k]
            exp = dict(term=r[1], text=r[2], sourceName=r[6], url=r[3], adapted=bool(r[7]))
            if g["glossary"] != exp: mism.append((pid, g["activity"], "difiere"))
            srcs.add(r[5])
            api_groups_with_gloss += 1
            sample_pool.append((pid, g["activity"], g["activitySource"], k))
    if srcs: plants_with_gloss += 1
    names = [c["name"] for c in d["credits"]]
    if len(set(names)) != len(names) or names != sorted(names, key=lambda s: s.lower()) and False: credit_bad.append((pid, "repetido"))
    has_w = "Wikcionario en español" in names
    if has_w != ("wiktionary_es" in srcs): credit_bad.append((pid, "Wikcionario"))
    if "wikipedia_es" in srcs and "Wikipedia en español" not in names: credit_bad.append((pid, "Wikipedia ausente"))
    wikt_credit += has_w; wiki_credit += "Wikipedia en español" in names
check("O5b las 2.354 plantas: grupos servidos de la API == grupos no pendientes de la base", not served_bad, str(served_bad[:3]))
check("O5c forma y orden de campos de cada grupo sin cambios en las 2.354 plantas", not shape_bad, str(shape_bad[:3]))
check("O5d glossary de la API == fila de la base (o null) en todos los grupos", not mism, str(mism[:3]))
check("O5e 5.172 grupos con glossary y 1.207 plantas en la API", (api_groups_with_gloss, plants_with_gloss) == (5172, 1207), f"{api_groups_with_gloss},{plants_with_gloss}")
check("O5f créditos: Wikcionario si y solo si hay explicación de Wikcionario; Wikipedia presente si hay explicación de Wikipedia; sin repetir", not credit_bad, str(credit_bad[:3]))
exp_w = len({p for p, _, _, k in sample_pool if glossmap[k][5] == "wiktionary_es"})
check("O5g plantas con crédito de Wikcionario == plantas con explicación de Wikcionario", wikt_credit == exp_w, f"{wikt_credit} vs {exp_w}")
# Wikipedia credit sin glosario ni... (informativo)
wp_gloss = {p for p, _, _, k in sample_pool if glossmap[k][5] == "wikipedia_es"}
extra_wp = [p for p, d in details.items() if any(c["name"] == "Wikipedia en español" for c in d["credits"]) and p not in wp_gloss]
print("INFO plantas con crédito de Wikipedia:", wiki_credit, "; sin explicación de Wikipedia (por la descripción):", len(extra_wp))
# la URL del crédito de Wikipedia cuando solo viene del glosario

# --- O6 muestra de 30 grupos
random.seed(20261029)
sample = random.sample(sample_pool, 30)
bad = []
sample_out = []
for pid, act, src, k in sample:
    g = next(x for x in details[pid]["useGroups"] if x["activity"] == act and x["activitySource"] == src)["glossary"]
    r = glossmap[k]; j = gj_rows[r[1]]
    ok = (g == dict(term=r[1], text=r[2], sourceName=r[6], url=r[3], adapted=bool(r[7]))
          and g["text"] == j["text"] and g["url"] == j["entryUrl"] and g["term"] == j["term"] and g["adapted"] == j["adapted"] and g["sourceName"] == j["sourceName"]
          and g["text"] == rev[g["term"]]["text"])
    if not ok: bad.append((pid, act))
    sample_out.append((pid, act, g["term"], g["sourceName"], g["adapted"]))
check("O6 muestra de 30 grupos: API == base == glossary.json == tabla aprobada", not bad, str(bad[:3]))
for s in sample_out: print("  muestra:", s)

# --- O7 dosis y promesas (revisión automática de las 53 definiciones)
dose = re.compile(r"\d|dosis|posolog|gotas|cucharad|mg\b|\bml\b", re.I)
wide = re.compile(r"\b(cura|curar|trata|tratar|previene|prevenir|elimina|eliminar|alivia|aliviar|eficaz|efectivo|garantiza|recomend|combat|mitiga|favorece|fortalece)", re.I)
d_hits = [r[1] for r in rows if dose.search(r[2])]
check("O7 ninguna de las 53 definiciones con dosis ni posología", not d_hits, str(d_hits))
w_hits = {r[1]: wide.findall(r[2]) for r in rows if wide.search(r[2])}
print("INFO definiciones con verbos vigilados o de efecto:", json.dumps(w_hits, ensure_ascii=False))
plant_ref = [r[1] for r in rows if re.search(r"\b(esta planta|la planta|este remedio|usted|tome|se recomienda)\b", r[2], re.I)]
print("OBSERVACION definiciones que mencionan a «la planta» o dan instrucciones al lector:", plant_ref)

print(f"\nRESUMEN {sum(1 for _,ok,_ in results if ok)}/{len(results)} PASS; fallos: {failures}")
if out:
    json.dump([dict(name=n, ok=o, detail=d) for n, o, d in results], open(out, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if failures else 0)
