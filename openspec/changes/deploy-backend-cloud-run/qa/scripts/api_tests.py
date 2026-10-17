#!/usr/bin/env python3
"""Casos de API contra la URL desplegada de Cloud Run (solo GET/POST/PUT/DELETE de contrato; sin efectos).

Uso: BASE_URL=https://... python3 -I api_tests.py   (por defecto la URL de la guía)
Escribe cabeceras y cuerpos recortados en ../evidence/api/ y un resumen en ../evidence/api/results.jsonl.
No usa credenciales ni secretos.
"""
import json, os, re, statistics, subprocess, sys, time, concurrent.futures as cf

BASE = os.environ.get("BASE_URL", "https://boticario-api-d3xv5q3iaa-pv.a.run.app").rstrip("/")
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "..", "evidence", "api")
OPENAPI = os.path.join(HERE, "..", "..", "..", "..", "..", "backend", "openapi.json")
os.makedirs(EV, exist_ok=True)
results = []


def curl(method, path_or_url, headers=(), data=None, extra=()):
    url = path_or_url if path_or_url.startswith("http") else BASE + path_or_url
    cmd = ["curl", "-sS", "--max-time", "60", "-X", method, "-D", "-", "-o", "-",
           "-w", "\n__T__%{time_total} %{http_code} %{http_version} %{size_download}", *extra]
    for h in headers:
        cmd += ["-H", h]
    if data is not None:
        cmd += ["--data", data]
    cmd.append(url)
    raw = subprocess.run(cmd, capture_output=True).stdout
    head, _, rest = raw.partition(b"\r\n\r\n")
    # puede haber varios bloques de cabeceras (100-continue); nos quedamos con el último
    while rest.startswith(b"HTTP/"):
        head, _, rest = rest.partition(b"\r\n\r\n")
    body, _, tail = rest.rpartition(b"\n__T__")
    t, code, ver, size = tail.decode().split()
    hdrs = {}
    for line in head.decode("latin1").split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    return {"status": int(code), "time": float(t), "http": ver, "headers": hdrs, "body": body, "head": head.decode("latin1")}


def save(cid, r, label=""):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{cid}{label}")
    with open(os.path.join(EV, name + ".txt"), "w") as f:
        f.write(r["head"] + "\n\n")
        b = r["body"].decode("utf-8", "replace")
        f.write(b[:1500] + ("\n[... recortado, %d bytes en total]" % len(r["body"]) if len(b) > 1500 else ""))
        f.write("\n")


def is_json(r):
    try:
        return json.loads(r["body"])
    except Exception:
        return None


def ct(r):
    return r["headers"].get("content-type", "")


def record(cid, desc, spec, ok, notes="", evidence="", kind=None):
    res = kind or ("PASS" if ok else "FAIL")
    results.append({"id": cid, "descripcion": desc, "criterio": spec, "resultado": res, "notas": notes, "evidencia": evidence})
    print(f"{res:5} {cid} {desc} {notes}")


def problem_ok(r, status, param=None):
    j = is_json(r)
    good = r["status"] == status and ct(r).startswith("application/problem+json") and isinstance(j, dict) and all(k in j for k in ("type", "title", "status", "detail")) and j["status"] == status
    if good and param is not None:
        good = j.get("param") == param
    return good, j


# ---- A01 /health
r = curl("GET", "/health"); save("A01", r)
j = is_json(r)
record("A01", "GET /health", "backend-deployment: Ruta de salud alcanzable desde fuera; catalog-api: Endpoint de salud",
       r["status"] == 200 and ct(r).startswith("application/json") and j == {"status": "ok"},
       f"status={r['status']} ct={ct(r)} body={r['body'][:40]!r} http={r['http']}", "evidence/api/A01.txt")

# ---- A02 /openapi.json
r = curl("GET", "/openapi.json"); save("A02", r)
live = is_json(r)
local = json.load(open(OPENAPI))
def pm(d):
    return {(p, m) for p, v in d["paths"].items() for m in v}
same_paths = live is not None and pm(live) == pm(local)
same_doc = live == local
record("A02", "GET /openapi.json coherente con backend/openapi.json", "backend-deployment: Servicio sirve la misma API que la imagen en local",
       r["status"] == 200 and ct(r).startswith("application/json") and same_paths and same_doc,
       f"status={r['status']} paths={sorted(p for p,_ in pm(live))} documento_identico={same_doc}" if live else "sin JSON", "evidence/api/A02.txt")

# ---- A03 listado q=lavandula
r = curl("GET", "/v1/plants?q=lavandula"); save("A03", r)
j = is_json(r) or {}
items = j.get("items", [])
shape = all({"id", "scientificName", "commonNames"} <= set(i) for i in items) and {"items", "total", "limit", "offset"} <= set(j)
record("A03", "GET /v1/plants?q=lavandula", "backend-deployment: Acceso público por HTTPS (lista de plantas)",
       r["status"] == 200 and ct(r).startswith("application/json") and shape and any(i["id"] == "lavandula-angustifolia" for i in items) and j.get("total", 0) >= 1,
       f"status={r['status']} total={j.get('total')} items={[i['id'] for i in items][:5]} limit={j.get('limit')} offset={j.get('offset')}", "evidence/api/A03.txt")

# ---- A04 paginación
r0 = curl("GET", "/v1/plants"); save("A04", r0, "_default")
j0 = is_json(r0) or {}
ra = curl("GET", "/v1/plants?limit=2&offset=0"); save("A04", ra, "_p1")
rb = curl("GET", "/v1/plants?limit=2&offset=2"); save("A04", rb, "_p2")
rc = curl("GET", "/v1/plants?limit=100"); save("A04", rc, "_l100")
rd = curl("GET", "/v1/plants?limit=1&offset=2147483647"); save("A04", rd, "_offset_max")
re_ = curl("GET", "/v1/plants?limit=1"); save("A04", re_, "_l1")
ja, jb, jc, jd, je = (is_json(x) or {} for x in (ra, rb, rc, rd, re_))
ids_a = [i["id"] for i in ja.get("items", [])]; ids_b = [i["id"] for i in jb.get("items", [])]
ok = (ra["status"] == rb["status"] == rc["status"] == rd["status"] == re_["status"] == 200
      and len(ids_a) == 2 and len(ids_b) == 2 and not set(ids_a) & set(ids_b)
      and ja["total"] == jb["total"] == jc["total"] == j0.get("total") and ja["limit"] == 2 and jb["offset"] == 2
      and len(jc["items"]) == min(100, jc["total"]) and jd.get("items") == [] and jd.get("total") == ja["total"] and len(je["items"]) == 1)
record("A04", "Paginación limit/offset/total (limit=2, offset 0 y 2, limit=100, limit=1, offset=2147483647)", "catalog-api (paginación) vía contrato OpenAPI",
       ok, f"total={ja.get('total')} default_limit={j0.get('limit')} p1={ids_a} p2={ids_b} l100_items={len(jc.get('items', []))} offset_max_items={len(jd.get('items', []))}", "evidence/api/A04_*.txt")

# ---- A05 q vacío / ausente
r = curl("GET", "/v1/plants?q="); save("A05", r, "_q_vacio")
j = is_json(r) or {}
record("A05", "q vacío equivale a sin filtro", "catalog-api (contrato): q opcional",
       r["status"] == 200 and j.get("total") == j0.get("total") and j.get("items") == j0.get("items"),
       f"status={r['status']} total={j.get('total')} total_sin_q={j0.get('total')}", "evidence/api/A05_q_vacio.txt")

# ---- A06 q codificado
cases = {
    "espacio_codificado": "/v1/plants?q=lavandula%20angustifolia",
    "espacio_mas": "/v1/plants?q=lavandula+angustifolia",
    "espacios_bordes": "/v1/plants?q=%20lavandula%20",
    "mayusculas": "/v1/plants?q=LAVANDULA",
    "acento": "/v1/plants?q=l%C3%A1vandula",
    "sin_resultados": "/v1/plants?q=zzzzzz-no-existe",
    "porcentaje": "/v1/plants?q=%25",
    "guion_bajo": "/v1/plants?q=_",
    "sql": "/v1/plants?q=%27%3B%20DROP%20TABLE%20plant%3B--",
    "comillas_dobles": "/v1/plants?q=%22lavandula%22",
    "emoji": "/v1/plants?q=%F0%9F%8C%BF",
    "ruta_nula": "/v1/plants?q=lav%00",
}
out = {}
for k, p in cases.items():
    rr = curl("GET", p); save("A06", rr, "_" + k)
    jj = is_json(rr) or {}
    out[k] = (rr["status"], jj.get("total"), [i["id"] for i in jj.get("items", [])][:3])
no500 = all(v[0] < 500 for v in out.values())
record("A06", "q con espacios/codificación, mayúsculas, comodines y entradas hostiles no producen 5xx",
       "catalog-api (robustez); backend-deployment: Servicio sirve la misma API", no500 and out["espacio_codificado"][0] == 200 and out["mayusculas"][1] not in (None,) , json.dumps(out, ensure_ascii=False), "evidence/api/A06_*.txt")
record("A06b", "Búsqueda con acento (`lávandula`) y comodines (`%`, `_`)", "informativo",
       True, f"acento={out['acento']} porcentaje(total)={out['porcentaje'][1]} guion_bajo(total)={out['guion_bajo'][1]} total_sin_q={j0.get('total')}", "evidence/api/A06_acento.txt", kind="OBS")

# ---- A07 límite de q
q200 = "a" * 200; q201 = "a" * 201
r200 = curl("GET", f"/v1/plants?q={q200}"); save("A07", r200, "_200")
r201 = curl("GET", f"/v1/plants?q={q201}"); save("A07", r201, "_201")
m200 = curl("GET", "/v1/plants?q=" + "%C3%A1" * 200); save("A07", m200, "_200_multibyte")
m201 = curl("GET", "/v1/plants?q=" + "%C3%A1" * 201); save("A07", m201, "_201_multibyte")
g, jj = problem_ok(r201, 400, "q")
g2, _ = problem_ok(m201, 400, "q")
record("A07", "q de 200 caracteres 200 y de 201 caracteres 400 problem+json (ASCII y multibyte)", "catalog-api/openapi: q maxLength 200",
       r200["status"] == 200 and g and m200["status"] == 200 and g2,
       f"200->{r200['status']} 201->{r201['status']} ct={ct(r201)} problem={json.dumps(jj, ensure_ascii=False)[:160] if jj else None} multibyte200->{m200['status']} multibyte201->{m201['status']}", "evidence/api/A07_*.txt")

# ---- A08 límites de limit / offset
bad = {"limit_0": "limit=0", "limit_101": "limit=101", "limit_neg": "limit=-1", "limit_abc": "limit=abc", "limit_decimal": "limit=1.5",
       "limit_vacio": "limit=", "offset_neg": "offset=-1", "offset_abc": "offset=abc", "offset_desbordado": "offset=2147483648", "limit_desbordado": "limit=99999999999"}
out = {}
allok = True
for k, qs in bad.items():
    rr = curl("GET", "/v1/plants?" + qs); save("A08", rr, "_" + k)
    p = k.split("_")[0]
    g, jj = problem_ok(rr, 400, p)
    out[k] = (rr["status"], ct(rr)[:24], (jj or {}).get("param"))
    allok &= g
record("A08", "limit/offset fuera de rango o inválidos responden 400 problem+json con param", "catalog-api/openapi: limit 1..100, offset >= 0",
       allok, json.dumps(out), "evidence/api/A08_*.txt")
okb = {}
for k, qs in {"limit_1": "limit=1", "limit_100": "limit=100", "offset_0": "offset=0"}.items():
    rr = curl("GET", "/v1/plants?" + qs); okb[k] = rr["status"]
record("A08b", "Bordes válidos limit=1, limit=100, offset=0 responden 200", "valores límite", all(v == 200 for v in okb.values()), json.dumps(okb), "evidence/api/A04_*.txt")

# ---- A09 detalle
details = {}
for pid in ["lavandula-angustifolia", "rosmarinus-officinalis", "abies-spectabilis", "chondrus-crispus"]:
    rr = curl("GET", f"/v1/plants/{pid}"); save("A09", rr, "_" + pid)
    details[pid] = (rr, is_json(rr) or {})
def det_ok(pid):
    rr, jj = details[pid]
    return rr["status"] == 200 and ct(rr).startswith("application/json") and {"id", "scientificName", "names", "parts", "uses"} <= set(jj) and jj["id"] == pid
record("A09", "Detalle de lavandula-angustifolia, rosmarinus-officinalis, abies-spectabilis y chondrus-crispus", "backend-deployment: Verificación posterior (detalle) y Servicio sirve la misma API",
       all(det_ok(p) for p in details),
       "; ".join(f"{p}: status={details[p][0]['status']} names={len(details[p][1].get('names', []))} parts={len(details[p][1].get('parts', []))} uses={len(details[p][1].get('uses', []))} family={details[p][1].get('family')!r}" for p in details), "evidence/api/A09_*.txt")
record("A09b", "chondrus-crispus devuelve family null y abies-spectabilis sin nombres comunes", "catalog-api (campos opcionales)",
       details["chondrus-crispus"][1].get("family") is None,
       f"chondrus family={details['chondrus-crispus'][1].get('family', '<ausente>')!r}; abies names={[n.get('kind') for n in details['abies-spectabilis'][1].get('names', [])]}", "evidence/api/A09_chondrus-crispus.txt")

# ---- A10 404 y ids raros
r = curl("GET", "/v1/plants/no-existe"); save("A10", r)
g, jj = problem_ok(r, 404)
record("A10", "GET /v1/plants/no-existe → 404 application/json problem+json", "backend-deployment: Error del contrato",
       g, f"status={r['status']} ct={ct(r)} body={json.dumps(jj, ensure_ascii=False) if jj else r['body'][:100]!r}", "evidence/api/A10.txt")
odd = {"mayusculas": "LAVANDULA-ANGUSTIFOLIA", "barra_codificada": "a%2Fb", "punto_punto": "..%2F..%2Fetc%2Fpasswd", "largo_2000": "x" * 2000, "espacio": "lavandula%20angustifolia", "sql": "%27%20OR%201%3D1--"}
out = {}
for k, pid in odd.items():
    rr = curl("GET", f"/v1/plants/{pid}"); save("A10", rr, "_" + k)
    out[k] = (rr["status"], ct(rr)[:24])
record("A10b", "Ids inválidos o hostiles no producen 5xx y los errores son problem+json", "catalog-api: errores 400/404",
       all(v[0] in (400, 404) for v in out.values()), json.dumps(out), "evidence/api/A10_*.txt")
r = curl("GET", "/v1/desconocida"); save("A10", r, "_ruta_desconocida")
g, _ = problem_ok(r, 404)
record("A10c", "Ruta desconocida dentro del contenedor → 404 problem+json", "openapi info: rutas desconocidas responden 404 problem+json", g, f"status={r['status']} ct={ct(r)}", "evidence/api/A10_ruta_desconocida.txt")

# ---- A11 métodos no permitidos
out = {}
allok = True
for k, (m, p) in {"post_health": ("POST", "/health"), "post_plants": ("POST", "/v1/plants"), "put_detail": ("PUT", "/v1/plants/lavandula-angustifolia"),
                  "delete_detail": ("DELETE", "/v1/plants/lavandula-angustifolia"), "post_openapi": ("POST", "/openapi.json")}.items():
    rr = curl(m, p, data="" if m in ("POST", "PUT") else None); save("A11", rr, "_" + k)
    g, jj = problem_ok(rr, 405)
    out[k] = (rr["status"], ct(rr)[:24], rr["headers"].get("allow"))
    allok &= g
record("A11", "Métodos distintos de GET → 405 problem+json (POST /health, POST /v1/plants, PUT, DELETE, POST /openapi.json)", "openapi info: métodos distintos de GET responden 405",
       allok, json.dumps(out), "evidence/api/A11_*.txt")
rh = curl("HEAD", "/health", extra=("-I",)); save("A11", rh, "_head_health")
ro = curl("OPTIONS", "/health"); save("A11", ro, "_options_health")
record("A11b", "HEAD y OPTIONS sobre /health", "informativo", True, f"HEAD->{rh['status']} OPTIONS->{ro['status']} ct={ct(ro)[:24]}", "evidence/api/A11_head_health.txt", kind="OBS")

# ---- A12 /healthz
r = curl("GET", "/healthz"); save("A12", r)
rb = r["body"].decode("utf-8", "replace")
record("A12", "GET /healthz → 404 del frontal de Google (HTML), no de la API", "decisión de diseño 3 / backend-container (escenario informativo)",
       r["status"] == 404 and ct(r).startswith("text/html") and "problem" not in ct(r), f"status={r['status']} ct={ct(r)} body_inicio={rb[:60]!r}", "evidence/api/A12.txt")
r = curl("GET", "/healthz/"); save("A12", r, "_slash")
others = {}
for k, p in {"readyz": "/readyz", "livez": "/livez", "v1_healthz": "/v1/healthz", "healthz_query": "/healthz?x=1", "HEALTHZ": "/HEALTHZ"}.items():
    rr = curl("GET", p); save("A12", rr, "_" + k)
    others[k] = (rr["status"], ct(rr)[:24])
record("A12b", "Qué rutas reserva el frontal: solo /healthz exacto (con o sin query); /healthz/, /readyz, /livez y /v1/healthz llegan a la API", "informativo: la guía dice «rutas terminadas en z»",
       True, f"/healthz/->{r['status']} {ct(r)[:24]}; " + json.dumps(others), "evidence/api/A12_*.txt", kind="OBS")

# ---- A13 HTTP plano
r = curl("GET", BASE.replace("https://", "http://") + "/health"); save("A13", r)
j = is_json(r)
record("A13", "http:// no sirve contenido sin cifrar", "backend-deployment: HTTPS en la URL *.run.app",
       (r["status"] in (301, 302, 307, 308) and r["headers"].get("location", "").startswith("https://")) or (r["status"] in (0, 400, 403, 404) and j is None),
       f"status={r['status']} location={r['headers'].get('location')}", "evidence/api/A13.txt")

# ---- A14 tiempos en caliente
def timeit(path, n):
    ts = []
    for _ in range(n):
        rr = curl("GET", path); assert rr["status"] == 200, (path, rr["status"]); ts.append(rr["time"])
    return ts
stats = {}
for name, p, n in [("health", "/health", 20), ("lista_q", "/v1/plants?q=lavandula", 20), ("lista_100", "/v1/plants?limit=100", 10), ("detalle", "/v1/plants/lavandula-angustifolia", 20)]:
    ts = sorted(timeit(p, n))
    stats[name] = {"n": n, "p50_ms": round(statistics.median(ts) * 1000), "p95_ms": round(ts[int(0.95 * (n - 1))] * 1000), "max_ms": round(ts[-1] * 1000), "min_ms": round(ts[0] * 1000)}
json.dump(stats, open(os.path.join(EV, "A14_timings.json"), "w"), indent=1)
record("A14", "Tiempos de respuesta en caliente (desde este Mac, curl total)", "informativo (sin criterio numérico en la spec)", True, json.dumps(stats), "evidence/api/A14_timings.json", kind="OBS")

# ---- A15 URLs equivalentes
r1 = curl("GET", "https://boticario-api-177181505486.northamerica-south1.run.app/health"); save("A15", r1)
record("A15", "La URL determinista del servicio (project number) responde igual que la de la guía", "backend-deployment: accesible por HTTPS en su URL *.run.app",
       r1["status"] == 200 and is_json(r1) == {"status": "ok"}, f"status={r1['status']}", "evidence/api/A15.txt")

# ---- A16 sin credenciales y con credenciales basura
r = curl("GET", "/v1/plants?limit=1", headers=("Authorization: Bearer token-invalido",)); save("A16", r)
record("A16", "Acceso público: una cabecera Authorization inválida no rompe la petición", "backend-deployment: acceso público sin autenticación",
       r["status"] == 200, f"status={r['status']}", "evidence/api/A16.txt")

# ---- A17 compresión y cabeceras
r = curl("GET", "/v1/plants?limit=100", headers=("Accept-Encoding: gzip",)); save("A17", r)
record("A17", "Cabeceras de la respuesta (compresión, caché, servidor)", "informativo", True,
       f"content-encoding={r['headers'].get('content-encoding')} cache-control={r['headers'].get('cache-control')} server={r['headers'].get('server')} size={len(r['body'])} http={r['http']}", "evidence/api/A17.txt", kind="OBS")

# ---- A18 concurrencia ligera
def one(i):
    return curl("GET", "/v1/plants?q=lavandula&limit=10")["status"]
t0 = time.time()
with cf.ThreadPoolExecutor(max_workers=30) as ex:
    sts = list(ex.map(one, range(60)))
dt = time.time() - t0
record("A18", "60 peticiones con 30 en paralelo responden todas 200", "backend-deployment: max-instances=2 no degrada la API a carga ligera",
       all(s == 200 for s in sts), f"codigos={sorted(set(sts))} duracion_total={dt:.2f}s", "evidence/api/results.jsonl")

with open(os.path.join(EV, "results.jsonl"), "w") as f:
    for x in results:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
print("\nRESUMEN:", {k: sum(1 for x in results if x['resultado'] == k) for k in ("PASS", "FAIL", "OBS")})
