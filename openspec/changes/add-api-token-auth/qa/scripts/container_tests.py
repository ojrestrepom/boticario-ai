#!/usr/bin/env python3
"""Casos CFG-* y CON-* del plan contra la imagen y `docker compose` locales.

Uso (desde la raíz del repositorio; los tokens locales salen del entorno):
  TOKEN_LOCAL_1=... TOKEN_LOCAL_2=... python3 -I openspec/changes/add-api-token-auth/qa/scripts/container_tests.py
No crea ni lee `.env`. Deja el entorno como estaba (`docker compose down`, contenedores y red de prueba eliminados).
Escribe evidence/container/<caso>.txt con cada valor de token sustituido por un marcador.
"""
import json, os, secrets, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
EV = os.path.join(HERE, "..", "evidence", "container")
os.makedirs(EV, exist_ok=True)
T1, T2, T3 = (os.environ[k] for k in ("TOKEN_LOCAL_1", "TOKEN_LOCAL_2", "TOKEN_LOCAL_3"))
IMAGE = "boticario-backend:latest"
SECRET_MARKS = [(T1, "<token-local-1>"), (T2, "<token-local-2>"), (T3, "<token-local-3>")]
EXTRA = []  # valores de prueba generados al vuelo: (valor, marcador)
results = []
log = []
cur = {"id": None}


def red(s):
    for v, m in SECRET_MARKS + EXTRA:
        if v:
            s = s.replace(v, m)
    return s


def sh(cmd, env=None, cwd=ROOT, timeout=300, check=False):
    e = {**os.environ, **(env or {})}
    p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def note(text):
    log.append(red(text))


def case(cid):
    flush()
    cur["id"] = cid


def flush():
    if cur["id"] and log:
        with open(os.path.join(EV, f"{cur['id']}.txt"), "w") as f:
            f.write(f"# {cur['id']}\n\n" + "\n".join(log) + "\n")
    log.clear()


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append({"case": cur["id"], "check": name, "ok": ok, "detail": red(str(detail))})
    note(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    print(("PASS " if ok else "FAIL ") + f"{cur['id']} {name}" + (f"  [{red(str(detail))}]" if detail and not ok else ""), flush=True)


def obs(name, detail):
    results.append({"case": cur["id"], "check": name, "ok": None, "detail": red(str(detail))})
    note(f"OBS {name}: {detail}")
    print(f"OBS  {cur['id']} {name}: {red(str(detail))}", flush=True)


def get(url, token=None, timeout=5):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # conexión rechazada, etc.
        return 0, str(e).encode()


def wait_health(port, tries=40):
    for _ in range(tries):
        if get(f"http://localhost:{port}/health")[0] == 200:
            return True
        time.sleep(0.5)
    return False


def run_container(name, tokens, port, extra_env=(), net=None):
    args = ["docker", "run", "-d", "--name", name, "-p", f"{port}:8080", "-e", f"API_TOKENS={tokens}"]
    for e in extra_env:
        args += ["-e", e]
    if net:
        args += ["--network", net]
    return sh(args + [IMAGE])


def rm(*names):
    for n in names:
        sh(["docker", "rm", "-f", n])


def compose(args, tokens=None, extra=None):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], **(extra or {})}
    if tokens is not None:
        env["API_TOKENS"] = tokens
    # Sin API_TOKENS heredado del shell salvo que se indique.
    full = {k: v for k, v in os.environ.items() if k != "API_TOKENS"}
    full.update(env)
    p = subprocess.run(["docker", "compose", *args], cwd=ROOT, env=full, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr


# ---------------------------------------------------------------- CFG
sh(["docker", "compose", "down"], env={"API_TOKENS": T1})
case("CFG-01")
rc, out = sh(["docker", "run", "--rm", IMAGE])
note(f"$ docker run --rm {IMAGE}   (sin API_TOKENS)\nexit={rc}\n{out}")
check("código de salida 2", rc == 2, rc)
check("el mensaje nombra API_TOKENS", "API_TOKENS" in out, out)

case("CFG-02")
for lab, val in (("vacía", ""), ("solo espacios", "   "), ("solo salto de línea", "\n")):
    rc, out = sh(["docker", "run", "--rm", "-e", f"API_TOKENS={val}", IMAGE])
    note(f"$ API_TOKENS <{lab}>\nexit={rc}\n{out}")
    check(f"{lab}: código 2 y mensaje con API_TOKENS", rc == 2 and "API_TOKENS" in out, (rc, out))

case("CFG-03")
for n in (31, 257):
    v = "Q" * n
    EXTRA.append((v, f"<valor-de-{n}-caracteres>"))
    rc, out = sh(["docker", "run", "--rm", "-e", f"API_TOKENS={v}", IMAGE])
    note(f"$ API_TOKENS de {n} caracteres\nexit={rc}\n{out}")
    check(f"{n} caracteres: código 2", rc == 2, rc)
    check(f"{n} caracteres: el mensaje indica el límite", ("32" in out) if n == 31 else ("256" in out), out)
    check(f"{n} caracteres: el mensaje no contiene el valor", v not in out)

case("CFG-04")
for n in (32, 256):
    v = secrets.token_hex(n // 2)
    EXTRA.append((v, f"<token-de-{n}-caracteres>"))
    rm("qa-cfg")
    rc, out = run_container("qa-cfg", v, 18081)
    ok = wait_health(18081)
    s_ok = get("http://localhost:18081/v1/plants?limit=1", v)[0]
    s_bad = get("http://localhost:18081/v1/plants?limit=1", v[:-1] + ("0" if v[-1] != "0" else "1"))[0]
    note(f"{n} caracteres: health={ok} con token={s_ok} otro={s_bad}")
    check(f"{n} caracteres: arranca, acepta el token y rechaza otro", ok and s_ok == 200 and s_bad == 401, (ok, s_ok, s_bad))
    rm("qa-cfg")

case("CFG-05")
good = secrets.token_hex(16)
EXTRA.append((good, "<token-valido-de-prueba>"))
cases = [("elemento vacío en medio (a,,b)", f"{good},,{good}"), ("coma final", f"{good},"), ("coma inicial", f",{good}"),
         ("carácter @", good[:-1] + "@"), ("espacio interior", good[:10] + " " + good[10:]), ("carácter no ASCII", good[:-1] + "é"), ("un token malo entre buenos", f"{good},{'Q'*5},{good}")]
for lab, val in cases:
    rc, out = sh(["docker", "run", "--rm", "-e", f"API_TOKENS={val}", IMAGE])
    note(f"$ API_TOKENS: {lab}\nexit={rc}\n{out}")
    check(f"{lab}: código 2, nombra API_TOKENS, sin el valor", rc == 2 and "API_TOKENS" in out and good not in out and "QQQQQ" not in out, (rc, out))

case("CFG-06")
rm("qa-cfg")
run_container("qa-cfg", T1, 18081)
ok = wait_health(18081)
check("arranca con un token de 64 hex y acepta ese token", ok and get("http://localhost:18081/v1/plants?limit=1", T1)[0] == 200)
check("rechaza otro token", get("http://localhost:18081/v1/plants?limit=1", T2)[0] == 401)
rm("qa-cfg")

case("CFG-07")
for lab, val in (("espacios alrededor de la coma y salto final", f"{T1} , {T2}\n"), ("CRLF final", f"{T1},{T2}\r\n")):
    rm("qa-cfg")
    run_container("qa-cfg", val, 18081)
    ok = wait_health(18081)
    a = get("http://localhost:18081/v1/plants?limit=1", T1)[0]
    b = get("http://localhost:18081/v1/plants?limit=1", T2)[0]
    c = get("http://localhost:18081/v1/plants?limit=1", T3)[0]
    note(f"{lab}: health={ok} t1={a} t2={b} t3={c}")
    check(f"{lab}: acepta ambos y rechaza un tercero", ok and a == 200 and b == 200 and c == 401, (ok, a, b, c))
    rm("qa-cfg")

case("CFG-08")
rc, out = sh(["docker", "run", "--rm", IMAGE, "--help"])
check("--help sin API_TOKENS: código 0 e imprime la ayuda", rc == 0 and "Uso: catalog-api" in out and "API_TOKENS" in out, rc)
rc, out = sh(["docker", "run", "--rm", IMAGE, "--openapi"])
check("--openapi sin API_TOKENS: código 0 e imprime el documento", rc == 0 and json.loads(out)["openapi"].startswith("3"), rc)
with open(os.path.join(ROOT, "backend", "openapi.json")) as f:
    check("el documento impreso coincide con backend/openapi.json", json.loads(out) == json.load(f))

case("CFG-09")
check("los mensajes de CFG-01 a CFG-05 no contienen valores de token (comprobado en cada caso)", all(r["ok"] for r in results if r["case"] in ("CFG-01", "CFG-02", "CFG-03", "CFG-05")))

# ---------------------------------------------------------------- CON
case("CON-01")
rc, out = compose(["up", "-d"])
note(f"$ docker compose up -d   (sin API_TOKENS ni .env)\nexit={rc}\n{out}")
check("falla (código distinto de 0)", rc != 0, rc)
check("el mensaje nombra API_TOKENS", "API_TOKENS" in out)
rc2, ps = compose(["ps", "-a", "--format", "json"], tokens=T1)
check("no se creó ningún contenedor", ps.strip() == "", ps)
check("no existe .env en la raíz", not os.path.exists(os.path.join(ROOT, ".env")))
rc, out = compose(["config", "--quiet"], tokens=T1)
check("docker compose config con API_TOKENS definido: pasa", rc == 0, out)

case("CON-02")
rc, out = compose(["up", "-d"], tokens=T1)
note(out)
ok = wait_health(8080)
check("GET /health -> 200", ok)
check("GET /v1/plants sin token -> 401", get("http://localhost:8080/v1/plants")[0] == 401)
check("GET /v1/plants con token -> 200", get("http://localhost:8080/v1/plants", T1)[0] == 200)

case("CON-03")
s, b = get("http://localhost:8080/v1/plants?q=lavand", T1)
j = json.loads(b)
note(f"q=lavand -> {s}, total={j.get('total')}, primer id={j['items'][0]['id'] if j.get('items') else None}")
check("q=lavand -> 200 con resultados reales", s == 200 and j["total"] >= 1 and any("lavandula" in i["id"] for i in j["items"]), j.get("total"))
s, b = get("http://localhost:8080/v1/plants/lavandula-angustifolia", T1)
d = json.loads(b)
note(f"detalle -> {s}, scientificName={d.get('scientificName')}")
check("detalle de lavandula-angustifolia -> 200 con datos reales", s == 200 and d.get("scientificName") == "Lavandula angustifolia", s)
rc, out = compose(["down"], tokens=T1)

case("CON-04")
compose(["down"], tokens=T1)
rc, out = compose(["up", "-d"], tokens=T1, extra={"PORT": "9090"})
note(out)
check("PORT=9090: /health 200 en 9090", wait_health(9090))
check("el puerto 8080 del anfitrión no está publicado", get("http://localhost:8080/health")[0] == 0)
check("401 sin token también en 9090", get("http://localhost:9090/v1/plants")[0] == 401)
compose(["down"], tokens=T1)

case("CON-05")
rc, out = compose(["up", "-d"], tokens=T1, extra={"RUST_LOG": "warn"})
wait_health(8080)
_, lg = sh(["docker", "logs", "boticario-ai-api-1"])
note("RUST_LOG=warn, logs:\n" + lg)
check("con warn no aparece «escuchando»", "escuchando" not in lg, lg)
compose(["down"], tokens=T1)
rc, out = compose(["up", "-d"], tokens=T1)
wait_health(8080)
_, lg = sh(["docker", "logs", "boticario-ai-api-1"])
note("RUST_LOG por defecto, logs:\n" + lg)
check("con el valor por defecto aparece «escuchando»", "escuchando" in lg)
compose(["down"], tokens=T1)

case("CON-06")
rm("qa-cfg")
run_container("qa-cfg", f"{T1},{T2}", 18081)
wait_health(18081)
a, b, c = (get("http://localhost:18081/v1/plants?limit=1", t)[0] for t in (T1, T2, T3))
check("T1 y T2 -> 200, otro valor -> 401", (a, b, c) == (200, 200, 401), (a, b, c))
rm("qa-cfg")

case("CON-07")
rc, out = sh(["docker", "image", "inspect", IMAGE, "--format", "{{json .Config.Env}}"])
note("Config.Env: " + out)
check("la imagen no define API_TOKENS", "API_TOKENS" not in out, out)
rc, hist = sh(["docker", "history", "--no-trunc", IMAGE])
check("docker history sin API_TOKENS con valor ni tokens locales", T1 not in hist and T2 not in hist and T3 not in hist and "API_TOKENS=" not in hist)
tmp = tempfile.mkdtemp(prefix="qa-img-")
sh(["docker", "rm", "-f", "qa-export"])
sh(["docker", "create", "--name", "qa-export", IMAGE])
tar = os.path.join(tmp, "fs.tar")
with open(tar, "wb") as f:
    subprocess.run(["docker", "export", "qa-export"], stdout=f, check=True)
rc, listing = sh(["tar", "-tvf", tar])
fsdir = os.path.join(tmp, "fs")
os.makedirs(fsdir)
sh(["tar", "-xf", tar, "-C", fsdir, "--exclude=dev", "--exclude=proc", "--exclude=sys"])
hits = 0
for t in (T1, T2, T3):
    r = subprocess.run(["grep", "-rlF", "--binary-files=text", t, fsdir], capture_output=True, text=True)
    hits += len(r.stdout.split())
check("0 archivos del sistema de archivos de la imagen contienen un token local", hits == 0, hits)
with open(os.path.join(EV, "image-filesystem-listing.txt"), "w") as f:
    f.write("\n".join(l for l in listing.splitlines() if "/usr/share" not in l and "/var/lib/dpkg" not in l and "/usr/lib" not in l)[:20000] + "\n")
case("CON-08")
interesting = [l for l in listing.splitlines() if any(k in l for k in ("catalog", "cargo", "rustc", ".zip", "/src", ".rs", "app/"))]
note("Archivos relevantes:\n" + "\n".join(l.split()[-1] if l.split() else l for l in interesting))
check("existe el binario /app/catalog-api y la base /app/catalog.db", any(l.split()[-1].endswith("app/catalog-api") for l in interesting) and any(l.split()[-1].endswith("app/catalog.db") for l in interesting))
# usr/src y usr/local/src son directorios vacíos de la imagen base de Debian, no código fuente del proyecto.
bad = [l for l in listing.splitlines() if any(x in l.split()[-1] for x in ("cargo", "rustc", ".zip", "raw.db", ".rs", "Cargo.toml", "Dockerfile")) and "/usr/share" not in l]
srcdirs = [l.split()[-1] for l in listing.splitlines() if l.split()[-1].rstrip("/").endswith("src")]
note("Directorios llamados src (vacíos, de la imagen base): " + ", ".join(srcdirs))
check("no existen cargo, rustc, ZIP, base cruda ni código fuente", not bad, bad[:5])
sh(["docker", "rm", "-f", "qa-export"])
shutil.rmtree(tmp, ignore_errors=True)

case("CON-09")
sh(["docker", "network", "rm", "qa-internal"])
rc, out = sh(["docker", "network", "create", "--internal", "qa-internal"])
rm("qa-nonet")
sh(["docker", "run", "-d", "--name", "qa-nonet", "--network", "qa-internal", "-e", f"API_TOKENS={T1}", IMAGE])
time.sleep(2)
# La imagen alpine no necesita red de salida: solo habla con la API por la red interna.
def alp(url, tok=None):
    cmd = ["docker", "run", "--rm", "--network", "qa-internal", "alpine:latest", "wget", "-q", "-S", "-O", "-", "--timeout=5"]
    if tok:
        cmd += ["--header", f"Authorization: Bearer {tok}"]
    rc, out = sh(cmd + [url])
    return rc, out
rc1, o1 = alp("http://qa-nonet:8080/v1/plants/lavandula-angustifolia", T1)
note(f"con token (red interna, sin salida):\nrc={rc1}\n{o1[:600]}")
check("detalle con token en red sin salida -> 200 con datos", rc1 == 0 and "Lavandula angustifolia" in o1, rc1)
rc2, o2 = alp("http://qa-nonet:8080/v1/plants/lavandula-angustifolia")
note(f"sin token:\nrc={rc2}\n{o2[:600]}")
check("sin token -> 401", "401" in o2, o2[:200])
rc3, o3 = sh(["docker", "run", "--rm", "--network", "qa-internal", "alpine:latest", "wget", "-q", "-O", "-", "--timeout=4", "http://example.com"])
check("la red de prueba no tiene salida a Internet", rc3 != 0, rc3)
rm("qa-nonet")
sh(["docker", "network", "rm", "qa-internal"])

case("CON-10")
rm("qa-trace")
run_container("qa-trace", f"{T1},{T2}", 18082, extra_env=["RUST_LOG=trace"])
wait_health(18082)
for p, tok in (("/v1/plants?limit=1", T1), ("/v1/plants/lavandula-angustifolia", T2), ("/v1/plants", T3), ("/v1/plants", None), ("/v1/plants", T3[:40]), (f"/v1/plants?token={T3}", None), ("/health", T3)):
    get(f"http://localhost:18082{p}", tok)
_, lg = sh(["docker", "logs", "qa-trace"])
n_lines = len(lg.splitlines())
counts = {name: lg.count(v) for name, v in (("T1", T1), ("T2", T2), ("T3", T3), ("T3[:40]", T3[:40]), ("T1[:32]", T1[:32]), ("T2[:32]", T2[:32]))}
note(f"líneas de log a nivel trace: {n_lines}\napariciones: {counts}\nmuestra de las líneas con «autoriz» o «Authorization»:\n" + "\n".join(l for l in lg.splitlines() if "autoriz" in l.lower() or "authorization" in l.lower())[:2000])
check(f"0 apariciones de tokens (válidos, inválidos, prefijos) en {n_lines} líneas de log trace", sum(counts.values()) == 0, counts)
check("el 401 se registra a nivel debug con la clase del fallo", "petición no autorizada" in lg, "")
check("no se registra el valor de la cabecera Authorization", "Bearer " not in lg, "")
rm("qa-trace")

flush()
compose(["down"], tokens=T1)
with open(os.path.join(HERE, "..", "evidence", "container", "results.jsonl"), "w") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
nf = sum(1 for r in results if r["ok"] is False)
print(f"\n{sum(1 for r in results if r['ok'])} PASS, {nf} FAIL, {sum(1 for r in results if r['ok'] is None)} OBS")
sys.exit(1 if nf else 0)
