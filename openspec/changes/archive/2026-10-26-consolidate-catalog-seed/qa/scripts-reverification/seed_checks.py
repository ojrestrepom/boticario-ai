#!/usr/bin/env python3 -I
"""Reverificación de QA (consolidate-catalog-seed): comprobaciones sobre la semilla, los paquetes y la base, sin red ni API.

Uso: seed_checks.py <repo> <carpeta de evidencia> [<id-map.tsv>]
Solo lee data/seed/plants, data/work/bundles (local, no se versiona) y data/build/catalog.db. Escribe un archivo por comprobación en la carpeta de evidencia.
"""
import collections, csv, glob, json, re, sqlite3, sys, unicodedata
from pathlib import Path

REPO = Path(sys.argv[1]); EV = Path(sys.argv[2]); EV.mkdir(parents=True, exist_ok=True)
OLD_MAP = sys.argv[3] if len(sys.argv) > 3 else None
SA = json.load(open(REPO / "tools/catalog-seed/sensitive-activities.json"))["categories"]
GRAVE = {t.lower() for t in SA["enfermedad-grave"]["terms"]}
RISK = {t.lower(): v for t, v in SA["senal-de-riesgo"]["terms"].items()}
PREFIX = SA["enfermedad-grave"]["formulaPrefix"]
def base(a): return a.split("(")[0].strip().lower()
def norm(s): return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

IDS = sorted(Path(f).stem for f in glob.glob(str(REPO / "data/seed/plants/*.json")))
REC = {i: json.load(open(REPO / f"data/seed/plants/{i}.json")) for i in IDS}
BUN = {i: json.load(open(REPO / f"data/work/bundles/{i}.json")) for i in IDS}
db = sqlite3.connect(f"file:{REPO}/data/build/catalog.db?mode=ro", uri=True)
out = {}
def emit(name, lines):
    out[name] = lines
    (EV / f"{name}.txt").write_text("\n".join(lines) + "\n")
    print(f"== {name}"); print("\n".join(lines[:60]))

# ---------- DEF-02: un nombre en latín no es un nombre común ----------
L = []
sci = {}
for pid, sn, snn in db.execute("select id, scientific_name, scientific_name_normalized from plant"):
    sci[pid] = (sn, snn)
sci_names = collections.defaultdict(set)
for pid, text, norm_, kind in db.execute("select plant_id, text, normalized, kind from plant_name"):
    if kind == "scientific": sci_names[pid].add(norm_)
la_common = db.execute("select count(*) from plant_name where kind='common' and language='la'").fetchone()[0]
L.append(f"nombres comunes de idioma la en la base: {la_common}")
dup = [(pid, text) for pid, text, n in db.execute("select plant_id, text, normalized from plant_name where kind='common'") if n in sci_names[pid] or n == sci[pid][1]]
L.append(f"nombres comunes cuyo texto normalizado es un nombre científico de la misma planta: {len(dup)} {dup[:5]}")
# nombre común con forma de binomio científico (dos palabras latinas, inicial mayúscula) en la semilla: informativo
seed_la_display = [i for i in IDS if REC[i]["displayName"]["language"] == "la"]
seed_la_common = [(i, c["text"]) for i in IDS for c in REC[i]["commonNames"] if c["language"] == "la"]
L.append(f"semilla: displayName de idioma la en {len(seed_la_display)} plantas; commonNames de idioma la en {len(seed_la_common)} (se descartan al construir la base)")
no_common = [pid for pid, in db.execute("select id from plant where id not in (select plant_id from plant_name where kind='common')")]
L.append(f"plantas sin ningún nombre común en la base: {len(no_common)} (antes de la corrección: 625 tenían el científico como único nombre común, más las que ya no tenían)")
sin_es = [i for i in IDS if any(f["code"] == "sin-nombre-comun-es" for f in REC[i]["reviewFlags"])]
L.append(f"plantas con el flag sin-nombre-comun-es: {len(sin_es)}")
only_sci = [i for i in sin_es if i in set(no_common)]
foreign = [i for i in sin_es if i not in set(no_common)]
L.append(f"  de ellas sin ningún nombre común en la base (solo nombres científicos): {len(only_sci)}")
L.append(f"  de ellas con nombres comunes de otros idiomas o sin etiqueta (no son el científico): {len(foreign)}")
langs = collections.Counter()
for i in foreign:
    for t, lang in db.execute("select text, language from plant_name where plant_id=? and kind='common'", (i,)): langs[lang] += 1
Q_COMMON = "select text from plant_name where plant_id=? and kind='common'"
ej = [(i, [r[0] for r in db.execute(Q_COMMON, (i,))][:3]) for i in foreign[:4]]
L.append(f"  idiomas de esos nombres: {dict(langs)}; ejemplos: {ej}")
spanish = collections.Counter()
for i in foreign:
    es = db.execute("select count(*) from plant_name where plant_id=? and kind='common' and language='es'", (i,)).fetchone()[0]
    spanish[es > 0] += 1
L.append(f"  de esas {len(foreign)}, con algún nombre en es (idioma asignado por el agente a un nombre dudoso): {spanish[True]}; sin es: {spanish[False]}")
# display_name de perfil: se conserva
dn_sci = sum(1 for i in IDS if REC[i]["displayName"]["language"] == "la" and db.execute("select display_name from plant_profile where plant_id=?", (i,)).fetchone()[0] == REC[i]["displayName"]["value"])
L.append(f"plant_profile.display_name conserva el científico en {dn_sci} de {len(seed_la_display)} plantas con displayName la")
cnt_name = db.execute("select count(*) from plant_name").fetchone()[0]
L.append(f"plant_name: {cnt_name} filas")
emit("DEF-02-db", L)

# ---------- DEF-03: usos de las plantas que los perdían ----------
L = []
PERD = {}
if OLD_MAP:
    for r in csv.DictReader(open(OLD_MAP), delimiter="\t"):
        PERD[r["id_anterior"]] = (int(r["usos_anteriores"] or 0), r["id_nuevo"])
lost = []
for old, (n_old, new) in PERD.items():
    if not new: continue
    n_new = db.execute("select count(*) from plant_use where plant_id=?", (new,)).fetchone()[0]
    if n_old > 0 and n_new == 0: lost.append((old, new, n_old))
L.append(f"plantas con usos en la base anterior y 0 usos ahora (según id-map.tsv): {len(lost)}")
for old, new, n_old in sorted(lost):
    b = BUN.get(new); r = REC.get(new)
    risk_only = None
    if b is not None:
        ups = [u["activity"] for u in b["sections"]["uses"]]
        risk_only = bool(ups) and all(base(a) in RISK for a in ups)
    saf = db.execute("select level, text from plant_safety where plant_id=?", (new,)).fetchone()
    refs = db.execute("select count(*) from plant_safety_ref where plant_id=?", (new,)).fetchone()[0]
    L.append(f"  {old} (antes {n_old}) -> {new}: paquete solo con señales de riesgo={risk_only}; safety={'sí' if saf else 'NO'} nivel={saf[0] if saf else None}; refs de safety={refs}; texto: {saf[1][-90:] if saf else ''}")
# plantas con usos del paquete que no son señales de riesgo y 0 grupos
no_groups = []
for i in IDS:
    ups = [u["activity"] for u in BUN[i]["sections"]["uses"] if base(u["activity"]) not in RISK]
    if ups and not REC[i]["traditionalUses"]: no_groups.append(i)
L.append(f"plantas cuyo paquete trae usos que no son señales de riesgo y cuyo registro no tiene ningún grupo: {len(no_groups)} {no_groups[:10]}")
withrisk_only_no_safety = [i for i in IDS if BUN[i]["sections"]["uses"] and all(base(u["activity"]) in RISK for u in BUN[i]["sections"]["uses"]) and not (REC[i]["safety"] or {}).get("text")]
L.append(f"plantas cuyo paquete solo trae señales de riesgo y sin texto de seguridad: {len(withrisk_only_no_safety)} {withrisk_only_no_safety[:10]}")
tot_no_use = db.execute("select count(*) from plant where id not in (select plant_id from plant_use)").fetchone()[0]
L.append(f"plantas sin usos en la base: {tot_no_use} (antes de las correcciones: 923); plant_use: {db.execute('select count(*) from plant_use').fetchone()[0]} (antes 24.286); plant_use_group: {db.execute('select count(*) from plant_use_group').fetchone()[0]}")
emit("DEF-03-db", L)

# ---------- CR-01: clave Nas ----------
L = []
tot = collections.Counter(); china_lost = []; andean = []
ANDES = {"Peru", "Bolivia", "Ecuador", "Colombia", "Chile", "Argentina", "Venezuela"}
SIXTEEN = "andrographis-paniculata ardisia-japonica areca-catechu arisaema-consanguineum aristolochia-debilis artemisia-capillaris celosia-argentea datura-metel glycyrrhiza-uralensis lonicera-japonica lophatherum-gracile paeonia-lactiflora rosa-laevigata rubia-cordifolia silybum-marianum zea-mays".split()
per16 = {}
nas_any = []
for i in IDS:
    bu = {u["activity"]: u for u in BUN[i]["sections"]["uses"]}
    for n, u in enumerate(REC[i]["traditionalUses"]):
        for c in u["citations"]:
            if c["ref"] == "usda_reference:NAS" or "Lost Crops" in (c["text"] or ""):
                nas_any.append((i, n, c["key"], c["ref"]))
            if c["key"] == "Nas":
                tot[c["ref"]] += 1
                if i in SIXTEEN: per16.setdefault(i, collections.Counter())[c["ref"]] += 1
                co = set(bu[u["activitySource"]]["countries"])
                if co & ANDES: andean.append((i, n, c["ref"], sorted(co)))
        # el ref del grupo también
        if "usda_reference:NAS" in u["refs"]: nas_any.append((i, n, "refs-del-grupo", "usda_reference:NAS"))
L.append(f"claves Nas en toda la semilla por ref elegido: {dict(tot)}")
L.append(f"citas (por clave cualquiera) o refs de grupo que apuntan a usda_reference:NAS / «Lost Crops of the Incas»: {len(nas_any)} {nas_any[:5]}")
L.append(f"grupos con clave Nas y algún país andino en las filas: {len(andean)} {andean[:5]}")
L.append("las 16 plantas señaladas por la QA anterior (ref elegido para la clave Nas y marca cita-sin-resolver):")
for i in SIXTEEN:
    fl = sorted({f["code"] for f in REC[i]["reviewFlags"] if f["code"] == "cita-sin-resolver"})
    L.append(f"  {i}: {dict(per16.get(i, {}))} {fl}")
db_nas = db.execute("select reference_id, count(*) from plant_use_group_ref where key='Nas' group by 1").fetchall()
L.append(f"base, plant_use_group_ref con clave Nas: {db_nas}")
db_lost = db.execute("select count(*) from plant_use_group_ref where reference_id='usda_reference:NAS' or text like '%Lost Crops%'").fetchone()[0]
q1 = db.execute("select count(*) from reference where citation like '%Lost Crops%' or id='usda_reference:NAS'").fetchone()[0]
q2 = db.execute("select count(*) from plant_use where reference_id='usda_reference:NAS'").fetchone()[0]
L.append(f"base, referencias de grupo a Lost Crops of the Incas: {db_lost}; filas en reference con ese texto: {q1}")
L.append(f"base, plant_use enlazados a usda_reference:NAS: {q2}")
unres = sorted({i for i in IDS for u in REC[i]["traditionalUses"] for c in u["citations"] if c["key"] == "Nas" and c["ref"] is None})
L.append(f"plantas con clave Nas sin resolver ({len(unres)}), todas con cita-sin-resolver: {all(any(f['code']=='cita-sin-resolver' for f in REC[i]['reviewFlags']) for i in unres)}: {unres}")
emit("CR-01-nas", L)

# ---------- CR-02: cantidades ----------
L = []
Q = re.compile(r"(\d[\d.,]*\s*(?:µg|μg|ug|mcg|mg|g|kg|ml|mL|l|L|cc|%|ppm|ppb|UI|IU|por ciento|veces|gotas|cucharad\w*|tazas?|gramos?|miligramos?|microgramos?|litros?|mililitros?)\b)|\b(?:µg|μg|mg|kg)\b|/kg\b|\bal d[ií]a\b|\bpor d[ií]a\b|\bdiari[oa]s?\b|\bdosis\b|\bposolog\w*|\bdosific\w*|\bgotas\b|\bcucharad\w*|\btazas?\b", re.I)
def visible(r):
    out = []
    def add(p, t):
        if isinstance(t, str): out.append((p, t))
    add("description", (r.get("description") or {}).get("value")); add("origin", (r.get("origin") or {}).get("value"))
    add("safety.text", (r.get("safety") or {}).get("text"))
    add("displayName", r["displayName"]["value"])
    for i, c in enumerate(r["commonNames"]): add(f"commonNames[{i}]", c["text"])
    for i, g in enumerate(r["goals"]): add(f"goals[{i}].area", g["area"]); add(f"goals[{i}].evidence", g["evidence"])
    for i, u in enumerate(r["traditionalUses"]): add(f"tu[{i}].activity", u["activity"])
    for i, p in enumerate(r["partsUsed"]): add(f"parts[{i}]", p["value"])
    for i, f in enumerate(r["reviewFlags"]): add(f"flag[{i}]", f["message"])
    return out
hits = []; ages = 0
for i in IDS:
    for p, t in visible(REC[i]):
        for m in Q.finditer(t):
            s = t[max(0, m.start()-50):m.end()+50]
            hits.append((i, p, m.group(0), s))
L.append(f"coincidencias de cantidad, unidad o posología en todo el texto visible (descripción, origen, seguridad, nombres, objetivos, actividades, partes y mensajes de flags): {len(hits)}")
for h in hits[:80]: L.append("  " + " | ".join(h))
fennel = [(i, REC[i]["safety"]["text"][:0]) for i in ("foeniculum-vulgare", "foeniculum-vulgare-var-dulce") if REC[i]["safety"]]
for i in ("foeniculum-vulgare", "foeniculum-vulgare-var-dulce"):
    t = REC[i]["safety"]["text"]; k = t.lower().find("estragol")
    L.append(f"{i}: safety.text menciona estragol: «...{t[max(0,k-120):k+260]}...»")
db_hits = []
for pid, text in db.execute("select plant_id, text from plant_safety"):
    for m in Q.finditer(text): db_hits.append((pid, m.group(0)))
L.append(f"base, plant_safety.text con coincidencias: {len(db_hits)} {db_hits[:5]}")
unit_only = re.compile(r"\d\s*(?:µg|μg|mg|kg|g|ml)\b|/kg", re.I)
L.append(f"cifras con unidad (µg, mg, g, kg, ml, /kg) en safety.text de la semilla: {sum(1 for i in IDS if REC[i]['safety'] and unit_only.search(REC[i]['safety']['text']))}")
emit("CR-02-cantidades", L)

# ---------- CR-03: cobertura de usos ----------
L = []
for i in ("inocarpus-fagifer", "inga-edulis", "heimia-salicifolia"):
    ups = [u["activity"] for u in BUN[i]["sections"]["uses"] if base(u["activity"]) not in RISK]
    n_rec = len(REC[i]["traditionalUses"]); n_db = db.execute("select count(*) from plant_use_group where plant_id=?", (i,)).fetchone()[0]
    L.append(f"{i}: grupos del paquete (sin señales de riesgo)={len(ups)}, grupos del registro={n_rec}, grupos en la base={n_db}, usos en la base={db.execute('select count(*) from plant_use where plant_id=?', (i,)).fetchone()[0]}, mínimo exigido=min(20, {len(ups)})={min(20, len(ups))}")
short = []
for i in IDS:
    ups = {u["activity"] for u in BUN[i]["sections"]["uses"] if base(u["activity"]) not in RISK}
    if len(REC[i]["traditionalUses"]) < min(20, len(ups)): short.append((i, len(REC[i]["traditionalUses"]), len(ups)))
L.append(f"plantas con menos grupos que min(20, grupos del paquete): {len(short)} {short[:10]}")
srcs_bad = [i for i in IDS for u in REC[i]["traditionalUses"] if u["activitySource"] not in {x["activity"] for x in BUN[i]["sections"]["uses"]}]
L.append(f"grupos cuyo activitySource no está en el paquete: {len(srcs_bad)}")
emit("CR-03-cobertura", L)

# ---------- fórmula de enfermedad grave ----------
L = []
four = {"bursera-simaruba": [12, 17], "byrsonima-crassifolia": [19], "caesalpinia-pulcherrima": [18], "cajanus-cajan": [7]}
for i, idxs in four.items():
    for n in idxs:
        us = REC[i]["traditionalUses"]
        hit = [u for u in us if u["activitySource"] == None]
    pass
for i in four:
    gr = [(u["activitySource"], u["activity"]) for u in REC[i]["traditionalUses"] if base(u["activitySource"]) in GRAVE]
    L.append(f"{i}: " + "; ".join(f"{a!r}" for s_, a in gr))
bad = []; nform = 0
for i in IDS:
    for n, u in enumerate(REC[i]["traditionalUses"]):
        a = u["activity"]; g = base(u["activitySource"]) in GRAVE
        if g:
            nform += 1
            rest = a[len(PREFIX):] if a.startswith(PREFIX) else None
            if rest is None or not rest[:1].isalpha() or re.search(r'["«»“”]|  ', a) or a != a.strip():
                bad.append((i, n, a))
        elif a.startswith(PREFIX): bad.append((i, n, "fórmula en actividad no grave: " + a))
        if re.search(r'["«»“”]|  |^\s|\s$', a): bad.append((i, n, "comillas o espacios: " + repr(a)))
L.append(f"grupos de enfermedad grave: {nform}; con fórmula incorrecta (prefijo exacto, un espacio, sin comillas, empieza por letra): {len(bad)} {bad[:5]}")
L.append(f"prefijo de la fórmula: {PREFIX!r}")
emit("formula-enfermedad-grave", L)

# ---------- anotaciones de idioma en nombres ----------
L = []
ANN = re.compile(r"\(\s*(?:Sp|Spa|Span|Ger|Ge|Fr|Fre|Eng|En|Jap|Jpn|Port|Por|Ital|It|Chin|Ch|Rus|Peru|Bol|Braz|Mex|Col|Ven|Ecu|Arg|Cub|Tur|Ind|Arab|Haw|Viet|Kor|Thai|Mal|Phil)\.?\s*\)", re.I)
ann = []; paren = []
for i in IDS:
    r = REC[i]
    names = [("displayName", r["displayName"]["value"], r["displayName"]["language"])] + [(f"commonNames[{k}]", c["text"], c["language"]) for k, c in enumerate(r["commonNames"])]
    for p, t, lang in names:
        if ANN.search(t): ann.append((i, p, lang, t))
        elif "(" in t: paren.append((i, p, lang, t))
L.append(f"nombres con anotación de idioma o país tipo «(Sp.)», «(Ger.)», «(Peru)»: {len(ann)} {ann[:10]}")
L.append(f"otros nombres con paréntesis ({len(paren)}), para revisión a mano:")
for x in paren: L.append("  " + " | ".join(x))
bd = db.execute("select count(*) from plant_name where kind='common' and text glob '*(*)*'").fetchone()[0]
L.append(f"base, nombres comunes con paréntesis: {bd}")
ten = "boswellia-sacra punica-granatum cinnamomum-aromaticum myrciaria-dubia".split()
for i in ten:
    L.append(f"  {i}: displayName={REC[i]['displayName']['value']!r}; nombres con paréntesis: {[c['text'] for c in REC[i]['commonNames'] if '(' in c['text']]}")
emit("anotaciones-de-idioma", L)

# ---------- Malesia / Malasia ----------
L = []
mal = [i for i in IDS if REC[i]["origin"] and "Malasia" in REC[i]["origin"]["value"]]
mles = [i for i in IDS if REC[i]["origin"] and "Malesia" in REC[i]["origin"]["value"]]
L.append(f"orígenes con «Malasia»: {len(mal)} {mal}; con «Malesia»: {len(mles)}")
bundle_mal = [i for i in IDS if REC[i]["origin"] and "Malesia" in json.dumps(BUN[i]["sections"].get("distribution"), ensure_ascii=False) and "Malasia" in REC[i]["origin"]["value"]]
L.append(f"orígenes que dicen «Malasia» cuando la distribución del paquete dice Malesia: {len(bundle_mal)}")
ocim = REC["ocimum-tenuiflorum"]["origin"]["value"]; L.append(f"ocimum-tenuiflorum: {ocim}")
others = collections.Counter()
for i in IDS:
    for p, t in visible(REC[i]):
        if "Malasia" in t and p != "origin": others[p.split("[")[0]] += 1
L.append(f"otras apariciones de «Malasia» fuera del origen (países de uso, descripción, etc.): {dict(others)}")
ctry = collections.Counter()
for i in IDS:
    for u in REC[i]["traditionalUses"]:
        for c in u["countries"]:
            if "alasia" in c or "alesia" in c or "alaya" in c: ctry[c] += 1
L.append(f"países de uso con Malasia, Malesia o Malaya: {dict(ctry)}")
emit("malesia", L)

# ---------- estado de los defectos sin corregir ----------
L = []
prof = dict(db.execute("select plant_id, display_name from plant_profile"))
mism = 0; first_not_es = collections.Counter(); split = collections.Counter()
for pid in prof:
    cs = [(t, lang) for t, lang in db.execute("select text, language from plant_name where plant_id=? and kind='common' order by text, language, id", (pid,))]
    if cs and prof[pid] and cs[0][0] != prof[pid]:
        mism += 1; first_not_es[cs[0][1]] += 1
        split["displayName en latín (sin nombre en español)" if REC[pid]["displayName"]["language"] == "la" else "displayName en español"] += 1
n_with = sum(1 for pid in prof if db.execute("select count(*) from plant_name where plant_id=? and kind='common'", (pid,)).fetchone()[0])
L.append(f"DEF-01: plantas con nombre común cuyo primero (orden de la API: texto, idioma, id) no es el display_name: {mism} de {n_with} con nombre común (antes: 1.024 de 2.354 plantas); idioma del primero: {dict(first_not_es)}; desglose: {dict(split)}")
lab = db.execute("select count(*), sum(citation like 'USDA Dr. Duke: referencia%') from reference r where id in (select reference_id from plant_use)").fetchone()
L.append(f"DEF-06: referencias usadas por plant_use: {lab[0]}; con la etiqueta «USDA Dr. Duke: referencia …»: {lab[1]}")
cr04 = REC["brassica-cretica-subsp-cretica"]
L.append(f"CR-04: brassica-cretica-subsp-cretica displayName={cr04['displayName']['value']!r}; flags={[f['code'] for f in cr04['reviewFlags']]}")
lethal = {"fatality", "fatal", "death", "suicide", "homicide"}
cnt = collections.Counter(); ex = collections.defaultdict(list)
for i in IDS:
    if any(base(u["activity"]) in lethal for u in BUN[i]["sections"]["uses"]):
        lv = (REC[i]["safety"] or {}).get("level"); cnt[lv] += 1; ex[lv].append(i)
L.append(f"CR-05: plantas con señal letal en USDA por nivel: {dict(cnt)} (antes: 56; alto 13, medio 16, sin nivel 27)")
new_lethal = sorted(set(ex[None]))
L.append(f"  sin nivel: {new_lethal}")
untr = 0; unt_t = collections.Counter()
for i in IDS:
    for u in REC[i]["traditionalUses"]:
        if u["activity"] == u["activitySource"] and base(u["activitySource"]) not in {"fever", "edema", "anemia", "asthma"}:
            pass
L.append(f"CR-09: grupos con actividad igual a la original: {db.execute('select count(*) from plant_use_group where activity = activity_source').fetchone()[0]} de {db.execute('select count(*) from plant_use_group').fetchone()[0]} (antes: 1.033 de 17.276)")
L.append(f"CR-10: autores de imagen sospechosos: ver barridos")
fam_null = db.execute("select count(*) from plant where family is null").fetchone()[0]
L.append(f"CR-18: plantas con family nula: {fam_null} (antes 116)")
nosafe = db.execute("select count(*) from plant where id not in (select plant_id from plant_safety)").fetchone()[0]
L.append(f"OBS-03: plantas sin safety: {nosafe} (antes 1.483)")
emit("estado-sin-corregir", L)
