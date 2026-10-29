#!/usr/bin/env python3 -I
"""6.2: escenarios de la API que la base real no puede ejercitar (objetivo y subarea vacios, sin datos de seguridad, revision pendiente
en un solo objetivo, orden con acentos). Corre contra un servicio levantado con la base modificada por make_modified_db.sh.
Entorno: QA_TOKEN, QA_BASE (por defecto http://127.0.0.1:8081), QA_DB (la copia modificada, solo lectura: es el oraculo).
Uso: api_tests_modified.py <carpeta de evidencia>
"""
import collections, json, os, pathlib, sqlite3, sys, unicodedata, urllib.error, urllib.request
EV = pathlib.Path(sys.argv[1]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8081"); TOKEN = os.environ["QA_TOKEN"]
db = sqlite3.connect(f"file:{os.environ['QA_DB']}?mode=ro", uri=True)

def get(path):
    rq = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        r = urllib.request.urlopen(rq, timeout=30); return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def norm(t):
    t = unicodedata.normalize("NFD", t.lower()); return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").split())

res = []; out = []
def rec(name, ok, detail=""):
    res.append(ok); out.append(f"{'PASA ' if ok else 'FALLA'} {name} {detail}")

def vis(goal, sub=None):
    q = "select distinct plant_id from plant_goal where goal_id=? and pending_review=0" + (" and subarea_id=?" if sub else "")
    return {r[0] for r in db.execute(q, (goal, sub) if sub else (goal,))}

st, goals = get("/v1/goals")
byid = {g["id"]: g for g in goals}
out.append("GET /v1/goals -> " + json.dumps([(g["id"], g["plantCount"], [(s["id"], s["plantCount"]) for s in g["subareas"]]) for g in goals], ensure_ascii=False))
# M-01 objetivo sin plantas
rec("M-01 el objetivo sin plantas visibles sigue en la lista con plantCount 0 y subareas []", "cansancio-y-fatiga" in byid and byid["cansancio-y-fatiga"]["plantCount"] == 0 and byid["cansancio-y-fatiga"]["subareas"] == [])
rec("M-01 el orden y los otros cinco objetivos no cambian", [g["id"] for g in goals] == [r[0] for r in db.execute("select id from goal order by position")])
st, j = get("/v1/goals/cansancio-y-fatiga/plants")
out.append("GET /v1/goals/cansancio-y-fatiga/plants -> " + str(st) + " " + json.dumps(j, ensure_ascii=False))
rec("M-01 las plantas del objetivo vacio: 200, items [], total 0, no es un error", st == 200 and j["items"] == [] and j["total"] == 0 and j["goal"]["name"] == "Cansancio y fatiga" and j["subarea"] is None)
# M-02 subarea sin plantas visibles
subs = {s["id"]: s for s in byid["otros-objetivos"]["subareas"]}
rec("M-02 la subarea sin plantas visibles (molestias-oculares) se omite de subareas", "molestias-oculares" not in subs and len(subs) == 5, str(list(subs)))
st, j = get("/v1/goals/otros-objetivos/plants?subarea=molestias-oculares")
out.append("GET ...?subarea=molestias-oculares -> " + str(st) + " " + json.dumps(j, ensure_ascii=False)[:300])
obs_status = st
rec("M-02 pedir la subarea omitida directamente: 200 con lista vacia y total 0 (o 400)", (st == 200 and j["items"] == [] and j["total"] == 0) or st == 400, f"{st}")
rec("M-02 circulacion cuenta 16 (ginkgo oculto) y la union de otros-objetivos coincide con la base", subs["circulacion"]["plantCount"] == 16 and byid["otros-objetivos"]["plantCount"] == len(vis("otros-objetivos")), f"union {byid['otros-objetivos']['plantCount']} base {len(vis('otros-objetivos'))}")
st, j = get("/v1/goals/otros-objetivos/plants?limit=100")
ids = {i["id"] for i in j["items"]}
rec("M-02 ginkgo-biloba (todas sus filas pendientes) no aparece en la union; hamamelis (pendiente en una subarea, visible en otra) si", "ginkgo-biloba" not in ids and "hamamelis-virginiana" in ids)
st, j = get("/v1/goals/otros-objetivos/plants?subarea=circulacion&limit=100")
rec("M-02 hamamelis-virginiana solo trae el area de circulacion (no la de molestias oculares pendiente)", next(i for i in j["items"] if i["id"] == "hamamelis-virginiana")["areas"] == ["Trastornos circulatorios"])
for s in subs.values():
    t = get(f"/v1/goals/otros-objetivos/plants?subarea={s['id']}&limit=1")[1]["total"]
    rec(f"M-02 plantCount de {s['id']} = total", t == s["plantCount"])
# M-03 datos ausentes
st, j = get("/v1/goals/relajacion-estres/plants?limit=100")
lav = next(i for i in j["items"] if i["id"] == "lavandula-angustifolia")
out.append("lavandula-angustifolia en relajacion-estres -> " + json.dumps({k: lav[k] for k in ("id", "areas", "safetyLevel", "hasSafety", "image")}, ensure_ascii=False))
rec("M-03 planta sin imagen ni seguridad: image null, safetyLevel null, hasSafety false", lav["image"] is None and lav["safetyLevel"] is None and lav["hasSafety"] is False)
# M-04 revision pendiente en un objetivo y no en otro
st, j = get("/v1/goals/mejorar-el-sueno/plants")
rec("M-04 la lavanda (pendiente en sueno) no aparece en mejorar-el-sueno y el objetivo cuenta 7", "lavandula-angustifolia" not in {i["id"] for i in j["items"]} and j["total"] == 7 and byid["mejorar-el-sueno"]["plantCount"] == 7)
rec("M-04 la lavanda sigue en relajacion-estres (su fila no esta pendiente) y se puede pedir por GET /v1/plants/{id}", get("/v1/plants/lavandula-angustifolia")[0] == 200)
# M-05 orden con acentos y mayusculas
st, j = get("/v1/goals/mejorar-el-sueno/plants")
names = [i["displayName"] for i in j["items"]]
out.append("orden en mejorar-el-sueno -> " + json.dumps(names, ensure_ascii=False))
exp = sorted(names, key=norm)
rec("M-05 abedul, Abutilon theophrasti, Arnica, Zarzaparrilla salen en ese orden (sin distinguir mayusculas ni acentos) y entre ellos el resto", names == exp and [n for n in names if n in ("abedul", "Abutilon theophrasti", "Árnica", "Zarzaparrilla")] == ["abedul", "Abutilon theophrasti", "Árnica", "Zarzaparrilla"], str(names))
rec("M-05 el orden binario seria distinto (la prueba discrimina)", names != sorted(names))
# M-06 la lista de objetivos y las plantas ocultas siguen siendo coherentes
for g in goals:
    t = get(f"/v1/goals/{g['id']}/plants?limit=1")[1]["total"]
    rec(f"M-06 {g['id']}: plantCount ({g['plantCount']}) = total ({t}) = base ({len(vis(g['id']))})", g["plantCount"] == t == len(vis(g["id"])))
(EV / "API-24.txt").write_text("\n".join(out).replace(TOKEN, "<token-app>") + "\n")
print(f"{sum(res)} PASA, {len(res) - sum(res)} FALLA")
print("\n".join(l for l in out if l.startswith("FALLA")))
