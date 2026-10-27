#!/usr/bin/env python3 -I
"""Reverificación de QA (consolidate-catalog-seed): comprobaciones puntuales contra la API local.

Entorno: QA_TOKEN (token de prueba, nunca se escribe), QA_BASE (por defecto http://127.0.0.1:8080), QA_DB (base, solo lectura).
Uso: api_checks.py <repo> <carpeta de evidencia>
La API sirve nombres, partes y usos (activity, language, reference); el texto de seguridad, el origen y la descripción no se sirven todavía, así que esos se verifican en la semilla y en la base (seed_checks.py).
"""
import csv, json, os, re, sqlite3, sys, urllib.parse, urllib.request, urllib.error, collections
from pathlib import Path

REPO = Path(sys.argv[1]); EV = Path(sys.argv[2]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080"); TOKEN = os.environ["QA_TOKEN"]
db = sqlite3.connect(f"file:{os.environ['QA_DB']}?mode=ro", uri=True)
def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKEN})
    try: r = urllib.request.urlopen(req, timeout=30); return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"null")
def search(q, limit=100): return get("/v1/plants?" + urllib.parse.urlencode({"q": q, "limit": limit}))
res = []; L = []
def rec(case, name, ok, detail=""):
    res.append((case, name, ok, detail)); L.append(f"{'PASA ' if ok else 'FALLA'} [{case}] {name} {detail}")
IDS = [r[0] for r in db.execute("select id from plant order by scientific_name, id")]

# ---------- DEF-02 ----------
c = "DEF-02"
bad_list = []; empty_common = 0; items_total = 0; off = 0
while True:
    st, j = get(f"/v1/plants?limit=100&offset={off}")
    for it in j["items"]:
        items_total += 1
        names = {x["text"].lower() for x in it["commonNames"]}
        if it["scientificName"].lower() in names or any(x["language"] == "la" for x in it["commonNames"]): bad_list.append(it["id"])
        if not it["commonNames"]: empty_common += 1
    if len(j["items"]) < 100: break
    off += 100
rec(c, f"listado: en los {items_total} resúmenes ningún commonNames repite el nombre científico ni es de idioma la", not bad_list, str(bad_list[:5]))
L.append(f"  resúmenes con commonNames vacío: {empty_common}")
bad_det = []; no_common_det = 0; la_names = 0; sci_missing = []
for pid in IDS:
    st, j = get(f"/v1/plants/{pid}")
    commons = [n for n in j["names"] if n["kind"] == "common"]
    sci = [n for n in j["names"] if n["kind"] == "scientific"]
    if any(n["text"].lower() == j["scientificName"].lower() for n in commons) or any(n["language"] == "la" for n in commons): bad_det.append(pid)
    if not commons: no_common_det += 1
    if not any(n["text"] == j["scientificName"] for n in sci): sci_missing.append(pid)
rec(c, f"detalle: en las {len(IDS)} plantas ningún nombre común repite el científico ni es de idioma la", not bad_det, str(bad_det[:5]))
rec(c, "detalle: el nombre científico de la planta está entre sus nombres de tipo scientific", not sci_missing, str(sci_missing[:5]))
L.append(f"  plantas sin ningún nombre común en el detalle (solo nombres científicos): {no_common_det}")
for pid in ["abutilon-theophrasti", "eleutherococcus-nodiflorus", "lamium-sp", "piper-aduncum-var-aduncum", "acacia-decurrens"]:
    st, j = get(f"/v1/plants/{pid}")
    L.append(f"  {pid}: nombres = {[(n['text'], n['kind'], n['language']) for n in j['names']][:8]}")
st, j = search("abutilon theophrasti", 5)
rec(c, "búsqueda «abutilon theophrasti» encuentra la planta y su commonNames no repite el científico", st == 200 and j["items"] and j["items"][0]["id"] == "abutilon-theophrasti" and all(x["language"] != "la" for x in j["items"][0]["commonNames"]), str(j["items"][0]["commonNames"] if j and j["items"] else None))

# ---------- DEF-03 ----------
c = "DEF-03"
want = {"chromolaena-odorata": 31, "actaea-cimicifuga": 16, "packera-aurea": 17, "piper-aduncum-var-aduncum": 24, "rostellularia-procumbens": 16,
        "tanacetum-balsamita-var-balsamitoides": 11, "origanum-creticum": 4, "satureja-cuneifolia": 1, "inocarpus-fagifer": 3, "gossypium-sp": 10,
        "eucalyptus-sp": 4, "eriocaulon-sp": 8, "erythrina-sp": 8, "genista-sp": 1, "mentha-sp": 2, "ocimum-sp": 5, "teucrium-sp": 1}
for pid, before in want.items():
    st, j = get(f"/v1/plants/{pid}")
    rec(c, f"{pid}: 200 y usos > 0 (la base anterior tenía {before})", st == 200 and len(j["uses"]) > 0, f"usos={len(j['uses']) if st == 200 else st}")
    if pid in ("chromolaena-odorata", "gossypium-sp") and st == 200:
        L.append(f"  {pid}: primeros usos {[(u['activity'], u['reference']['id']) for u in j['uses'][:4]]}")
risk_only = ["actaea-pachypoda", "dalbergia-nitidula", "dictamnus-hispanicus", "duboisia-leichhardtii", "eucalyptus-cladocalyx", "hyacinthus-orientalis", "huperzia-selago", "strophanthus-gratus", "taxus-sp"]
for pid in risk_only:
    st, j = get(f"/v1/plants/{pid}")
    saf = db.execute("select level, text from plant_safety where plant_id=?", (pid,)).fetchone()
    rec(c, f"{pid} (solo señal de riesgo): 200, 0 usos en la API y precaución en la base", st == 200 and len(j["uses"]) == 0 and saf is not None and "Advertencia" in saf[1], f"usos={len(j['uses']) if st == 200 else st} safety={'sí' if saf else 'no'}")
# ninguna planta con usos antes queda en 0 salvo las 9
OLD = {}
omap = os.environ.get("QA_OLD_MAP")
if omap:
    zero_now = []
    for r in csv.DictReader(open(omap), delimiter="\t"):
        if int(r["usos_anteriores"] or 0) > 0 and r["id_nuevo"]:
            st, j = get(f"/v1/plants/{r['id_nuevo']}")
            if st == 200 and not j["uses"]: zero_now.append(r["id_nuevo"])
    zero_now = sorted(set(zero_now))
    rec(c, "plantas con usos en la base anterior y 0 usos en la API: solo las 9 de señal de riesgo", set(zero_now) == set(risk_only), f"{len(zero_now)}: {zero_now}")

# ---------- DEF-05 ----------
c = "DEF-05"
for q, want_id in [("mentha x piperita", "mentha-x-piperita"), ("Mentha × piperita", "mentha-x-piperita"), ("mentha×piperita", "mentha-x-piperita"), ("MENTHA X PIPERITA", "mentha-x-piperita"),
                   ("rosmarinus x lavandulaceus", "salvia-x-lavandulacea"), ("rosmarinus x mendizabalii", None)]:
    st, j = search(q)
    ids = [i["id"] for i in j["items"]] if st == 200 else []
    if want_id: rec(c, f"q={q!r} encuentra {want_id}", want_id in ids, f"total={j.get('total') if j else None} ids={ids[:4]}")
    else: L.append(f"  q={q!r}: total={j.get('total')} ids={ids[:4]}")
# todo nombre científico con × se encuentra escribiéndolo con x
hy = [(pid, t) for pid, t in db.execute("select plant_id, text from plant_name where kind='scientific' and text like '%×%'")]
miss = []
for pid, t in hy:
    st, j = search(t.replace("×", "x"), 100)
    if pid not in [i["id"] for i in j["items"]]: miss.append((pid, t))
rec(c, f"los {len(hy)} nombres científicos con × se encuentran escribiéndolos con x", not miss, str(miss[:5]))
miss = []
for pid, t in hy:
    st, j = search(t, 100)
    if pid not in [i["id"] for i in j["items"]]: miss.append((pid, t))
rec(c, f"los {len(hy)} nombres científicos con × se siguen encontrando con ×", not miss, str(miss[:5]))
# la x dentro de palabras no se altera: 300 nombres científicos con x interna se encuentran por su nombre completo
import random
random.seed(11)
inner = [(pid, t) for pid, t in db.execute("select plant_id, text from plant_name where kind='scientific' and text not like '%×%'") if re.search(r"[a-z]x[a-z]|[a-z]x\b", t)]
sample = random.sample(inner, 300); miss = []
for pid, t in sample:
    st, j = search(t, 100)
    if pid not in [i["id"] for i in j["items"]]: miss.append((pid, t))
rec(c, f"300 de {len(inner)} nombres científicos con una x interna (taxus, fraxinus, ...) se encuentran por su nombre completo", not miss, str(miss[:5]))
for q in ["taxus", "fraxinus", "alexandra"]:
    st, j = search(q, 100)
    n_db = db.execute("select count(distinct plant_id) from plant_name where normalized like ?", (f"%{q}%",)).fetchone()[0]
    rec(c, f"q={q!r}: la API devuelve {n_db} plantas (las de la base con ese fragmento)", st == 200 and j["total"] == n_db, f"api={j and j['total']} base={n_db}")
st, j = search("x", 5); rec(c, "q='x' responde 200", st == 200, f"total={j and j['total']}")
# el nombre anterior sin x sigue sin encontrarse: estado de DEF-04, no de DEF-05
st, j = search("mentha piperita", 5); L.append(f"  (DEF-04, sin corregir) q='mentha piperita': total={j['total']}")
st, j = search("matricaria recutita", 5); L.append(f"  (DEF-04, sin corregir) q='matricaria recutita': total={j['total']}")

# ---------- CR-01 / CR-03 por la API ----------
c = "CR-01"
SIXTEEN = "andrographis-paniculata ardisia-japonica areca-catechu arisaema-consanguineum aristolochia-debilis artemisia-capillaris celosia-argentea datura-metel glycyrrhiza-uralensis lonicera-japonica lophatherum-gracile paeonia-lactiflora rosa-laevigata rubia-cordifolia silybum-marianum zea-mays".split()
nas = 0; nas2 = 0
for pid in SIXTEEN:
    st, j = get(f"/v1/plants/{pid}")
    nas += sum(1 for u in j["uses"] if u["reference"]["id"] == "usda_reference:NAS" or "Lost Crops" in u["reference"]["citation"])
    nas2 += sum(1 for u in j["uses"] if u["reference"]["id"] == "usda_reference:NAS2")
rec(c, "las 16 plantas: ningún uso servido cita usda_reference:NAS ni «Lost Crops»", nas == 0, f"NAS={nas} NAS2={nas2}")
tot_nas = 0
for pid in IDS:
    st, j = get(f"/v1/plants/{pid}")
    tot_nas += sum(1 for u in j["uses"] if u["reference"]["id"] == "usda_reference:NAS")
rec(c, f"las {len(IDS)} plantas: ningún uso servido cita usda_reference:NAS", tot_nas == 0, str(tot_nas))
c = "CR-03"
for pid, n in [("inocarpus-fagifer", 12), ("inga-edulis", 2), ("heimia-salicifolia", 20)]:
    st, j = get(f"/v1/plants/{pid}")
    rec(c, f"{pid}: usos servidos > 0", st == 200 and len(j["uses"]) > 0, f"usos={len(j['uses'])}; grupos en la base={db.execute('select count(*) from plant_use_group where plant_id=?', (pid,)).fetchone()[0]} (esperado {n})")

out = "\n".join(L).replace(TOKEN, "<token>") + "\n"
(EV / "api-checks.txt").write_text(out)
print(out)
print("RESUMEN", collections.Counter("PASA" if r[2] else "FALLA" for r in res))
