#!/usr/bin/env python3
"""Barrido de toda la API desplegada contra data/seed/glossary.json (sin base local), 2026-10-31.

Uso: TOKEN=<token> python3 -I cloudrun_sweep.py <base-url> <repo> [salida.json]
El token llega solo por la variable de entorno TOKEN y nunca se imprime ni se guarda.
"""
import json, os, re, sys, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

base, repo = sys.argv[1:3]
out = sys.argv[3] if len(sys.argv) > 3 else None
TOKEN = os.environ["TOKEN"]
FORMULA = "Uso tradicional, sin eficacia demostrada: "
fails, lines = [], []

def check(name, ok, detail=""):
    s = ("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else "")
    print(s); lines.append(s)
    if not ok: fails.append(name)

def get(path):
    r = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + TOKEN})
    for i in range(3):
        try:
            with urllib.request.urlopen(r, timeout=30) as f: return json.load(f)
        except Exception as e:
            if i == 2: raise

def base_key(a):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", a.split("(")[0])).strip().lower()

gj = json.load(open(f"{repo}/data/seed/glossary.json", encoding="utf-8"))
rows = {r["key"]: r for r in gj["rows"]}
check("S0 glossary.json tiene 53 filas", len(rows) == 53, str(len(rows)))
plants, off = [], 0
while True:
    pg = get(f"/v1/plants?limit=100&offset={off}")
    plants += [p["id"] for p in pg["items"]]; off += 100
    if off >= pg["total"]: break
check("S1 el listado desplegado trae 2.354 plantas", len(plants) == 2354, str(len(plants)))
with ThreadPoolExecutor(4) as ex:
    details = list(ex.map(lambda p: get("/v1/plants/" + p), plants))
mism, missing, formula_bad, shape_bad, credit_bad, coffee_bad = [], [], [], [], [], []
n_groups = n_plants = n_wikt_plants = n_wikt_cred = n_wiki_cred = n_coffee = n_cafe = 0
for pid, d in zip(plants, details):
    srcs, has_wikt_g, has_wiki_g = set(), False, False
    for g in d["useGroups"]:
        if list(g) != ["activity", "activitySource", "count", "countries", "references", "glossary"]: shape_bad.append(pid)
        a, gl = g["activity"], g["glossary"]
        if a.startswith(FORMULA):
            if gl is not None: formula_bad.append((pid, a))
            continue
        k = base_key(a)
        if k in rows:
            r = rows[k]
            exp = dict(term=r["term"], text=r["text"], sourceName=r["sourceName"], url=r["entryUrl"], adapted=bool(r["adapted"]))
            if gl is None: missing.append((pid, a))
            elif gl != exp or list(gl) != ["term", "text", "sourceName", "url", "adapted"] and sorted(gl) != sorted(exp): mism.append((pid, a))
        elif gl is not None: mism.append((pid, a, "no debía tener"))
        if gl:
            n_groups += 1
            has_wikt_g |= gl["sourceName"] == "Wikcionario"; has_wiki_g |= gl["sourceName"] == "Wikipedia"
        if g["activitySource"] == "Coffee":
            n_coffee += 1
            if a != "Sucedáneo del café": coffee_bad.append((pid, a))
        if a == "Café": n_cafe += 1
    if has_wikt_g or has_wiki_g: n_plants += 1
    names = [c["name"] for c in d["credits"]]
    if len(set(names)) != len(names): credit_bad.append((pid, "repetido"))
    w1, w2 = names.count("Wikcionario en español"), names.count("Wikipedia en español")
    if w1 != (1 if has_wikt_g else 0): credit_bad.append((pid, "Wikcionario", w1, has_wikt_g))
    if has_wiki_g and w2 != 1: credit_bad.append((pid, "Wikipedia", w2))
    if w2 > 1: credit_bad.append((pid, "Wikipedia repetida"))
    for c in d["credits"]:
        if c["name"] in ("Wikcionario en español", "Wikipedia en español") and (c["license"] != "CC BY-SA 4.0" or c["licenseUrl"] != "https://creativecommons.org/licenses/by-sa/4.0/"):
            credit_bad.append((pid, "licencia", c["name"]))
    n_wikt_cred += bool(w1); n_wiki_cred += bool(w2)
check("S2 todo glossary servido == fila de glossary.json por forma base (texto, URL, fuente, adaptado), y no hay grupo servido con término sin glossary", not mism and not missing, f"{mism[:3]} {missing[:3]}")
check("S3 ninguna fórmula de enfermedad grave con glossary", not formula_bad, str(formula_bad[:3]))
check("S4 forma de cada grupo sin cambios (6 claves en orden)", not shape_bad)
check("S5 créditos: Wikcionario si y solo si hay glossary de Wikcionario, Wikipedia una vez, sin repeticiones, CC BY-SA 4.0 con licenseUrl", not credit_bad, str(credit_bad[:3]))
check("S6 5.172 grupos con explicación en 1.207 plantas", (n_groups, n_plants) == (5172, 1207), f"{n_groups},{n_plants}")
check("S7 el crédito de Wikcionario está en 1.133 plantas", n_wikt_cred == 1133, str(n_wikt_cred))
check("S8 todo grupo con actividad de origen Coffee se llama Sucedáneo del café y ninguno se llama Café", not coffee_bad and n_cafe == 0 and n_coffee > 0, f"coffee={n_coffee} cafe={n_cafe} {coffee_bad[:3]}")
print(f"RESUMEN plantas={len(plants)} gruposConExplicacion={n_groups} plantasConExplicacion={n_plants} creditoWikcionario={n_wikt_cred} creditoWikipedia={n_wiki_cred} gruposCoffee={n_coffee}")
if out: json.dump(dict(fails=fails, lines=lines), open(out, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if fails else 0)
