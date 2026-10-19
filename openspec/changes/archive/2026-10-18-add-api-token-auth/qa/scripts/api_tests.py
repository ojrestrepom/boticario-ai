#!/usr/bin/env python3
"""Casos AUT-* del plan de pruebas contra la API (local con compose o Cloud Run).

Uso (los tokens salen del entorno; nunca se escriben en la evidencia):
  TARGET=local BASE_URL=http://localhost:8080 TOKEN=$TOKEN_LOCAL_1 python3 -I api_tests.py
  TARGET=cloud BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app TOKEN=$TOKEN_APP TOKEN2=$TOKEN_CI python3 -I api_tests.py

Variables: TARGET (local|cloud), BASE_URL, TOKEN (válido), TOKEN2 (otro válido, opcional), TIMING=1 (AUT-28, solo local).
Escribe evidence/api/<TARGET>/<caso>.txt y results-<TARGET>.jsonl. Cada valor de token se sustituye por un marcador.
Usa sockets en bruto para controlar la petición byte a byte (cabeceras duplicadas, bytes no ASCII, rutas sin normalizar).
"""
import json, os, secrets, socket, ssl, statistics, sys, time, urllib.parse

TARGET = os.environ.get("TARGET", "local")
BASE = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
VALID = os.environ["TOKEN"]
VALID2 = os.environ.get("TOKEN2", "")
INVALID = secrets.token_hex(32)
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "..", "evidence", "api", TARGET)
OPENAPI_FILE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "backend", "openapi.json"))
os.makedirs(EV, exist_ok=True)

u = urllib.parse.urlparse(BASE)
HOST, SCHEME = u.hostname, u.scheme
PORT = u.port or (443 if SCHEME == "https" else 80)

# Todo lo que no debe aparecer jamás en una salida, con su marcador.
SECRETS = [(VALID, "<token-valido>"), (INVALID, "<token-incorrecto>")]
if VALID2:
    SECRETS.append((VALID2, "<token-valido-2>"))
LEAK_PROBES = [VALID, VALID[:63], VALID[:32], VALID[-32:], INVALID, INVALID[:32]]
if VALID2:
    LEAK_PROBES += [VALID2, VALID2[:32]]


def redact(text):
    for val, mark in SECRETS:
        text = text.replace(val, mark)
    return text


def raw_request(method, path, headers=(), body=b"", timeout=60):
    """Envía una petición HTTP/1.1 en bruto y devuelve (status, cabeceras (lista), cuerpo)."""
    lines = [f"{method} {path} HTTP/1.1".encode(), f"Host: {HOST}".encode(), b"Connection: close", b"Accept: */*"]
    for h in headers:
        lines.append(h if isinstance(h, bytes) else h.encode("latin1"))
    if body or method in ("POST", "PUT", "PATCH"):
        lines.append(f"Content-Length: {len(body)}".encode())
    data = b"\r\n".join(lines) + b"\r\n\r\n" + body
    sock = socket.create_connection((HOST, PORT), timeout=timeout)
    if SCHEME == "https":
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=HOST)
    sock.sendall(data)
    chunks = []
    while True:
        try:
            c = sock.recv(65536)
        except (socket.timeout, ssl.SSLError, ConnectionResetError):
            break
        if not c:
            break
        chunks.append(c)
    sock.close()
    raw = b"".join(chunks)
    head, _, rest = raw.partition(b"\r\n\r\n")
    hl = head.decode("latin1").split("\r\n")
    status = int(hl[0].split()[1]) if hl and hl[0].startswith("HTTP/") else 0
    hdrs = [tuple(x.split(":", 1)) for x in hl[1:] if ":" in x]
    hdrs = [(k.strip().lower(), v.strip()) for k, v in hdrs]
    if any(k == "transfer-encoding" and "chunked" in v for k, v in hdrs):
        out, buf = b"", rest
        while buf:
            size_line, _, buf = buf.partition(b"\r\n")
            try:
                n = int(size_line.split(b";")[0], 16)
            except ValueError:
                break
            if n == 0:
                break
            out += buf[:n]
            buf = buf[n + 2:]
        rest = out
    return status, hdrs, rest


results = []
ALL_RESP = []  # texto crudo (cabeceras y cuerpo) de todas las respuestas, solo en memoria
current = {"id": None, "log": []}


def hdr(hdrs, name):
    return [v for k, v in hdrs if k == name]


def send(label, method, path, headers=(), body=b""):
    """Envía y registra. `label` describe las cabeceras sin mostrar el token."""
    status, hdrs, rbody = raw_request(method, path, headers, body)
    ALL_RESP.append(rbody.decode("utf-8", "replace") + "\n".join(f"{k}: {v}" for k, v in hdrs))
    text = rbody.decode("utf-8", "replace")
    shown_hdrs = [(k, v) for k, v in hdrs if k != "date"]
    shown_path = redact(path)
    entry = f"### {method} {shown_path}   [{label}]\nstatus={status}\n" + "".join(f"{k}: {redact(v)}\n" for k, v in shown_hdrs) + f"\n{redact(text)[:1500]}\n"
    current["log"].append(entry)
    return {"status": status, "headers": hdrs, "body": rbody, "text": text}


def bearer(tok="", scheme="Bearer"):
    return [f"Authorization: {scheme} {tok}"]


def case(cid, title):
    flush()
    current["id"], current["title"], current["log"] = cid, title, []


def flush():
    if current["id"] and current["log"]:
        with open(os.path.join(EV, f"{current['id']}.txt"), "w") as f:
            f.write(f"# {current['id']} {current.get('title','')} (objetivo: {TARGET})\n\n" + "\n".join(current["log"]))


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append({"case": current["id"], "check": name, "ok": ok, "detail": redact(str(detail))})
    print(("PASS " if ok else "FAIL ") + f"{current['id']} {name}" + (f"  [{redact(str(detail))}]" if detail and not ok else ""), flush=True)
    return ok


def observe(name, detail):
    results.append({"case": current["id"], "check": name, "ok": None, "detail": redact(str(detail))})
    print(f"OBS  {current['id']} {name}: {redact(str(detail))}", flush=True)


def is_problem(r):
    return r["headers"] and any(k == "content-type" and v.startswith("application/problem+json") for k, v in r["headers"])


def no_data(r):
    return b'"items"' not in r["body"] and b"scientificName" not in r["body"]


def comparable(r):
    """Cuerpo y cabeceras sin las que varían por petición."""
    skip = {"date", "x-cloud-trace-context"}
    return (r["status"], r["body"], tuple(sorted((k, v) for k, v in r["headers"] if k not in skip)))


LIST = "/v1/plants?limit=2"
DETAIL = "/v1/plants/lavandula-angustifolia"
rejects = {}  # etiqueta -> respuesta, sobre LIST

# --- AUT-01, AUT-02
case("AUT-01", "Token válido en el listado")
r = send("Bearer <válido>", "GET", LIST, bearer(VALID))
check("200", r["status"] == 200, r["status"])
check("application/json", any(k == "content-type" and v.startswith("application/json") for k, v in r["headers"]))
try:
    j = json.loads(r["text"])
    check("items con 2 elementos y total", len(j["items"]) == 2 and j["total"] > 0, j.get("total"))
except Exception as e:
    check("cuerpo JSON válido", False, e)

case("AUT-02", "Token válido en el detalle")
r = send("Bearer <válido>", "GET", DETAIL, bearer(VALID))
check("200", r["status"] == 200, r["status"])
check("detalle de lavandula-angustifolia", b"Lavandula angustifolia" in r["body"])

# --- AUT-03
case("AUT-03", "Esquema en otras mayúsculas")
for sch in ("bearer", "BEARER", "BeArEr"):
    r = send(f"{sch} <válido>", "GET", LIST, bearer(VALID, sch))
    check(f"esquema {sch} -> 200", r["status"] == 200, r["status"])

# --- AUT-04 a AUT-10: rechazos sobre LIST
case("AUT-04", "Cabecera ausente")
r = send("sin Authorization", "GET", LIST)
rejects["ausente"] = r
check("401", r["status"] == 401, r["status"])
check("application/problem+json", is_problem(r))
check("WWW-Authenticate: Bearer", hdr(r["headers"], "www-authenticate") == ["Bearer"], hdr(r["headers"], "www-authenticate"))
check("sin datos del catálogo", no_data(r))
try:
    pj = json.loads(r["text"])
    check("cuerpo problem+json con status 401", pj.get("status") == 401 and pj.get("title") == "Unauthorized", pj)
except Exception as e:
    check("cuerpo JSON válido", False, e)

case("AUT-05", "Token incorrecto")
r = send("Bearer <aleatorio 64 hex>", "GET", LIST, bearer(INVALID))
rejects["aleatorio"] = r
check("401 problem+json con WWW-Authenticate", r["status"] == 401 and is_problem(r) and hdr(r["headers"], "www-authenticate") == ["Bearer"])
check("mismo cuerpo y cabeceras que la cabecera ausente", comparable(r) == comparable(rejects["ausente"]))

case("AUT-06", "Último carácter distinto")
last = VALID[-1]
other = "0" if last != "0" else "1"
r = send("Bearer <válido con el último carácter cambiado>", "GET", LIST, bearer(VALID[:-1] + other))
rejects["ultimo"] = r
check("401 idéntico a ausente", r["status"] == 401 and comparable(r) == comparable(rejects["ausente"]), r["status"])

case("AUT-07", "Prefijos del token válido")
for n in (63, 32, 1):
    r = send(f"Bearer <primeros {n} caracteres del válido>", "GET", LIST, bearer(VALID[:n]))
    rejects[f"prefijo{n}"] = r
    check(f"prefijo de {n} caracteres -> 401 idéntico", r["status"] == 401 and comparable(r) == comparable(rejects["ausente"]), r["status"])

case("AUT-08", "Válido más un carácter, otras mayúsculas y recortes")
for lab, tok in (("válido + x", VALID + "x"), ("válido en mayúsculas", VALID.upper()), ("válido sin el primer carácter", VALID[1:])):
    r = send(f"Bearer <{lab}>", "GET", LIST, bearer(tok))
    rejects[lab] = r
    check(f"{lab} -> 401 idéntico", r["status"] == 401 and comparable(r) == comparable(rejects["ausente"]), r["status"])

case("AUT-09", "Esquema distinto")
import base64
b64 = base64.b64encode(b"usuario:clave-de-prueba").decode()
for lab, hv in (("Basic <base64>", [f"Authorization: Basic {b64}"]), ("token sin esquema", [f"Authorization: {VALID}"]), ("Token <válido>", bearer(VALID, "Token")), ("Bearer<válido> pegado", [f"Authorization: Bearer{VALID}"])):
    r = send(lab, "GET", LIST, hv)
    rejects[lab] = r
    check(f"{lab} -> 401 idéntico", r["status"] == 401 and comparable(r) == comparable(rejects["ausente"]), r["status"])

case("AUT-10", "Cabecera degenerada")
for lab, hv in (("Authorization vacía", ["Authorization:"]), ("solo «Bearer»", ["Authorization: Bearer"]), ("«Bearer » sin token", ["Authorization: Bearer "])):
    r = send(lab, "GET", LIST, hv)
    rejects[lab] = r
    check(f"{lab} -> 401 idéntico", r["status"] == 401 and comparable(r) == comparable(rejects["ausente"]), r["status"])

# --- AUT-11, AUT-12
case("AUT-11", "Ruta inexistente")
r1 = send("sin Authorization", "GET", "/v1/no-existe")
check("sin token -> 401, no 404", r1["status"] == 401 and is_problem(r1), r1["status"])
r2 = send("Bearer <válido>", "GET", "/v1/no-existe", bearer(VALID))
check("con token -> 404 problem+json", r2["status"] == 404 and is_problem(r2), r2["status"])
r3 = send("sin Authorization, ruta con comillas codificadas", "GET", "/v1/a%22b")
try:
    json.loads(r3["text"])
    check("el cuerpo 401 sigue siendo JSON válido con %22 en la ruta", r3["status"] == 401)
except Exception as e:
    check("el cuerpo 401 sigue siendo JSON válido con %22 en la ruta", False, e)

case("AUT-12", "Raíz del prefijo")
for p in ("/v1", "/v1/"):
    a = send("sin Authorization", "GET", p)
    check(f"{p} sin token -> 401", a["status"] == 401, a["status"])
    b = send("Bearer <válido>", "GET", p, bearer(VALID))
    check(f"{p} con token -> 404", b["status"] == 404, b["status"])

# --- AUT-13, AUT-14
case("AUT-13", "Escrituras sin token")
for m in ("POST", "PUT", "PATCH", "DELETE"):
    a = send("sin Authorization", m, "/v1/plants", body=b"{}" if m != "DELETE" else b"")
    check(f"{m} sin token -> 401, no 405", a["status"] == 401 and is_problem(a), a["status"])

case("AUT-14", "Escrituras con token")
for m in ("POST", "PUT", "PATCH", "DELETE"):
    a = send("Bearer <válido>", m, "/v1/plants", bearer(VALID), body=b"{}" if m != "DELETE" else b"")
    check(f"{m} con token -> 405 problem+json", a["status"] == 405 and is_problem(a), a["status"])
a = send("Bearer <válido>", "GET", LIST, bearer(VALID))
check("el listado sigue intacto tras las escrituras", a["status"] == 200)

# --- AUT-15
case("AUT-15", "HEAD y OPTIONS")
a = send("sin Authorization", "HEAD", "/v1/plants")
check("HEAD sin token -> 401", a["status"] == 401, a["status"])
a = send("Bearer <válido>", "HEAD", "/v1/plants", bearer(VALID))
check("HEAD con token -> 200", a["status"] == 200, a["status"])
a = send("sin Authorization", "OPTIONS", "/v1/plants")
check("OPTIONS sin token -> 401", a["status"] == 401, a["status"])
a = send("Bearer <válido>", "OPTIONS", "/v1/plants", bearer(VALID))
observe("OPTIONS con token", a["status"])

# --- AUT-16
case("AUT-16", "Rutas públicas")
bodies = []
for p in ("/health", "/openapi.json"):
    for lab, hv in (("sin Authorization", []), ("Bearer <válido>", bearer(VALID)), ("Bearer <incorrecto>", bearer(INVALID))):
        a = send(lab, "GET", p, hv)
        check(f"{p} [{lab}] -> 200", a["status"] == 200, a["status"])
        if p == "/health":
            bodies.append(a["body"])
check("el cuerpo de /health es el mismo con y sin token", len(set(bodies)) == 1, bodies)
check("/health no revela tokens configurados", b"token" not in bodies[0].lower() and bodies[0] == b'{"status":"ok"}', bodies[0])

# --- AUT-17: ya acumulado en rejects
case("AUT-17", "Cuerpo y cabeceras idénticos entre rechazos")
ref = comparable(rejects["ausente"])
bad = [k for k, v in rejects.items() if comparable(v) != ref]
check(f"{len(rejects)} rechazos con un único cuerpo y un único conjunto de cabeceras", not bad, bad)
current["log"].append("Cuerpo común:\n" + redact(rejects["ausente"]["text"]) + "\nCabeceras comunes:\n" + "".join(f"{k}: {v}\n" for k, v in rejects["ausente"]["headers"] if k not in ("date", "x-cloud-trace-context")))
observe("cuerpo común del 401", redact(rejects["ausente"]["text"]))

# --- AUT-19
case("AUT-19", "Token por canales no admitidos")
# Cloud Run registra la URL completa (con la query) en sus logs de petición: contra el servicio real nunca se envía un token válido en la query.
q_tok = VALID if TARGET == "local" else INVALID
a = send("token en la query (válido solo en local)", "GET", f"/v1/plants?token={q_tok}")
check("?token=<token> -> 401" + (" (con un token válido)" if TARGET == "local" else " (con uno incorrecto: el real quedaría en los logs de Cloud Run)"), a["status"] == 401, a["status"])
check("la respuesta no incluye la query", b"token=" not in a["body"], redact(a["text"]))
a = send("X-Api-Key", "GET", LIST, [f"X-Api-Key: {VALID}"])  # cabecera: no se registra en la URL
check("X-Api-Key -> 401", a["status"] == 401, a["status"])
a = send("Proxy-Authorization", "GET", LIST, [f"Proxy-Authorization: Bearer {VALID}"])
check("Proxy-Authorization -> 401", a["status"] == 401, a["status"])
a = send("Cookie", "GET", LIST, [f"Cookie: token={VALID}"])
check("Cookie -> 401", a["status"] == 401, a["status"])

# --- AUT-20
case("AUT-20", "Cabeceras Authorization duplicadas")
a = send("inválida y luego válida", "GET", LIST, bearer(INVALID) + bearer(VALID))
observe("inválida + válida", a["status"])
b = send("válida y luego inválida", "GET", LIST, bearer(VALID) + bearer(INVALID))
observe("válida + inválida", b["status"])
c = send("inválida y luego inválida", "GET", LIST, bearer(INVALID) + bearer(INVALID))
check("dos inválidas -> 401 sin datos", c["status"] == 401 and no_data(c), c["status"])

# --- AUT-21
case("AUT-21", "Separadores entre esquema y token")
a = send("dos espacios", "GET", LIST, [f"Authorization: Bearer  {VALID}"])
observe("dos espacios entre esquema y token", a["status"])
b = send("tabulador", "GET", LIST, [f"Authorization: Bearer\t{VALID}"])
observe("tabulador entre esquema y token", b["status"])
c = send("token con espacio final", "GET", LIST, [f"Authorization: Bearer {VALID} "])
observe("espacio final tras el token", c["status"])

# --- AUT-22
case("AUT-22", "Cabecera no ASCII y cabecera enorme")
a = send("bytes no ASCII", "GET", LIST, [b"Authorization: Bearer \xc3\xa9\xc3\xa9\xc3\xa9"])
check("bytes no ASCII -> 401, no 200 ni 5xx", a["status"] in (400, 401), a["status"])
b = send("valor de 16 KB", "GET", LIST, ["Authorization: Bearer " + "A" * 16000])
check("16 KB -> rechazo, no 200 ni 5xx", b["status"] in (400, 401, 413, 431), b["status"])
c = send("valor de 100 KB", "GET", LIST, ["Authorization: Bearer " + "A" * 100000])
observe("100 KB", c["status"])
check("100 KB no da 200 ni 5xx", c["status"] not in (200,) and c["status"] < 500, c["status"])

# --- AUT-23
case("AUT-23", "Evasión de ruta")
paths = ["/V1/plants", "/v1X", "/v1x/plants", "//v1/plants", "/x/../v1/plants", "/./v1/plants", "/v1/./plants", "/%76%31/plants", "/v1%2Fplants",
         "/v1/plants/", "/v1;a/plants", "/v1/plants;a=1", "/v1/plants%00", "/v1/plants/..;/plants", "/v1/plants#x", "/v1/%2e%2e/v1/plants",
         "/v1/plants%2F", "/v1/%70lants", "/v1/plants?%00", "http://" + HOST + "/v1/plants", "http://" + HOST + "//v1/plants"]
for p in paths:
    for lab, hv in (("sin Authorization", []), ("Bearer <incorrecto>", bearer(INVALID))):
        a = send(lab, "GET", p, hv)
        leaked = a["status"] == 200 or not no_data(a)
        check(f"{p} [{lab}] sin datos (estado {a['status']})", not leaked, a["status"])

# --- AUT-24
case("AUT-24", "Errores del contrato con token")
a = send("Bearer <válido>", "GET", "/v1/plants?limit=abc", bearer(VALID))
check("limit=abc con token -> 400 problem+json que nombra limit", a["status"] == 400 and is_problem(a) and b"limit" in a["body"], a["status"])
a = send("Bearer <válido>", "GET", "/v1/plants/no-existe", bearer(VALID))
check("/v1/plants/no-existe con token -> 404 problem+json", a["status"] == 404 and is_problem(a), a["status"])
a = send("sin Authorization", "GET", "/v1/plants?limit=abc")
check("limit=abc sin token -> 401 (la autorización precede)", a["status"] == 401, a["status"])
a = send("sin Authorization", "GET", "/v1/plants/no-existe")
check("/v1/plants/no-existe sin token -> 401, no 404", a["status"] == 401, a["status"])

# --- AUT-25
case("AUT-25", "Documento OpenAPI")
a = send("sin Authorization", "GET", "/openapi.json")
try:
    doc = json.loads(a["text"])
    sec = doc["components"]["securitySchemes"]["bearerAuth"]
    check("esquema HTTP Bearer", sec.get("type") == "http" and sec.get("scheme") == "bearer", sec)
    paths_doc = list(doc["paths"])
    check("rutas solo /health, /openapi.json y /v1/*", all(p in ("/health", "/openapi.json") or p.startswith("/v1/") for p in paths_doc), paths_doc)
    ok_sec, ok_401, ok_pub = True, True, True
    for p, item in doc["paths"].items():
        for m, op in item.items():
            has = {"bearerAuth": []} in op.get("security", []) or any("bearerAuth" in s for s in op.get("security", []))
            if p.startswith("/v1/"):
                ok_sec &= has
                resp = op.get("responses", {}).get("401", {})
                ok_401 &= "application/problem+json" in resp.get("content", {})
            else:
                ok_pub &= not has
    check("seguridad Bearer en las operaciones de /v1", ok_sec)
    check("respuesta 401 application/problem+json en /v1", ok_401)
    check("sin seguridad en /health ni /openapi.json", ok_pub)
    check("el documento no contiene ningún token", not any(t in a["text"] for t in LEAK_PROBES))
    with open(OPENAPI_FILE) as f:
        check("coincide con backend/openapi.json versionado", json.load(f) == doc)
except Exception as e:
    check("documento OpenAPI legible", False, e)

# --- AUT-26
case("AUT-26", "Consistencia")
seq = []
for i in range(20):
    good = i % 2 == 0
    r = send("válida" if good else "incorrecta", "GET", LIST, bearer(VALID if good else INVALID))
    seq.append((good, r["status"]))
check("20 peticiones alternadas: válidas 200, inválidas 401", all((s == 200) if g else (s == 401) for g, s in seq), seq)

# --- AUT-27 (Cloud Run)
if TARGET == "cloud":
    case("AUT-27", "La cabecera llega intacta a la API en Cloud Run")
    for lab, tok in (("token de la app", VALID), ("token de CI", VALID2)):
        if not tok:
            continue
        a = send(f"Bearer <{lab}>", "GET", DETAIL, bearer(tok))
        check(f"{lab} -> 200 (solo posible si Authorization llega intacta)", a["status"] == 200, a["status"])
    a = send("sin Authorization", "GET", DETAIL)
    sv = hdr(a["headers"], "server")
    check("el 401 es el de la API (problem+json con WWW-Authenticate: Bearer), no el del frontal", a["status"] == 401 and is_problem(a) and hdr(a["headers"], "www-authenticate") == ["Bearer"])
    observe("cabecera server", sv)

# --- Fuga global (AUT-18) sobre todo lo registrado
case("AUT-18", "Ninguna respuesta refleja el token")
hits = {i: sum(t.count(p) for t in ALL_RESP) for i, p in enumerate(LEAK_PROBES)}
check(f"0 apariciones de {len(LEAK_PROBES)} sondas de token (token, prefijos y sufijos) en {len(ALL_RESP)} respuestas", sum(hits.values()) == 0, hits)

flush()
with open(os.path.join(HERE, "..", "evidence", "api", f"results-{TARGET}.jsonl"), "w") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
n_fail = sum(1 for r in results if r["ok"] is False)
print(f"\n{TARGET}: {sum(1 for r in results if r['ok'])} PASS, {n_fail} FAIL, {sum(1 for r in results if r['ok'] is None)} OBS")
sys.exit(1 if n_fail else 0)
