#!/usr/bin/env python3
"""DEP-09: ejecuta en local el paso «Verificar el servicio desplegado» de deploy-backend.yml (extraído tal cual del YAML).

Uso: TOKEN_CI=... TOKEN_LOCAL_1=... CLOUD_URL=https://... python3 -I verify_step_sim.py
Casos: (a) token de CI correcto contra Cloud Run; (b) token obsoleto (aleatorio); (c) servicio «abierto» simulado (responde 200 a todo);
(d) sin API_VERIFY_TOKEN; (e) token local contra el contenedor local (si está en marcha en :8080).
No escribe ningún valor de token: la salida se sanea antes de guardarla.
"""
import http.server, os, re, secrets, subprocess, sys, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
EV = os.path.join(HERE, "..", "evidence", "cloud")
yml = open(os.path.join(ROOT, ".github", "workflows", "deploy-backend.yml")).read().splitlines()
i = next(n for n, l in enumerate(yml) if "name: Verificar el servicio desplegado" in l)
j = next(n for n in range(i, len(yml)) if yml[n].strip() == "run: |")
indent = len(yml[j + 1]) - len(yml[j + 1].lstrip())
body = []
for l in yml[j + 1:]:
    if l.strip() and (len(l) - len(l.lstrip())) < indent:
        break
    body.append(l[indent:] if len(l) >= indent else "")
script = "\n".join(body)
open(os.path.join(HERE, "..", "evidence", "cloud", "verify-step-extracted.sh"), "w").write(script + "\n")

SECRETS = {v: m for v, m in ((os.environ.get("TOKEN_CI", ""), "<token-ci>"), (os.environ.get("TOKEN_LOCAL_1", ""), "<token-local-1>")) if v}
stale = secrets.token_hex(32)
SECRETS[stale] = "<token-obsoleto>"


def red(s):
    for v, m in SECRETS.items():
        s = s.replace(v, m)
    return s


def run(label, url, token, expect_ok, must_contain=()):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", ""), "SERVICE_URL": url, "API_VERIFY_TOKEN": token}
    p = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=120)
    out = p.stdout + p.stderr
    leaked = any(v in out for v in SECRETS)
    ok = (p.returncode == 0) == expect_ok and not leaked and all(m in out for m in must_contain)
    print(("PASS " if ok else "FAIL ") + f"{label}: exit={p.returncode} (esperado {'0' if expect_ok else '!=0'}), token en la salida={leaked}")
    text = f"## {label}\nexit={p.returncode}\n{red(out)}\n"
    return ok, text


class Open(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b"{}")
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 18099), Open)
threading.Thread(target=srv.serve_forever, daemon=True).start()

CLOUD = os.environ.get("CLOUD_URL", "https://boticario-api-d3xv5q3iaa-pv.a.run.app")
res = []
res.append(run("(a) token de CI correcto contra Cloud Run", CLOUD, os.environ["TOKEN_CI"], True, ("/health -> 200", "(sin token) -> 401", "Servicio disponible")))
res.append(run("(b) token obsoleto (aleatorio) contra Cloud Run", CLOUD, stale, False))
res.append(run("(c) servicio abierto simulado (200 a todo, sin token incluido)", "http://127.0.0.1:18099", "token-cualquiera-de-prueba-0000000000000000", False, ("respondio 200 sin token",)))
res.append(run("(d) sin API_VERIFY_TOKEN", CLOUD, "", False, ("Falta el secreto de GitHub API_VERIFY_TOKEN",)))
if os.environ.get("TOKEN_LOCAL_1"):
    res.append(run("(e) token válido contra el contenedor local", "http://localhost:8080", os.environ["TOKEN_LOCAL_1"], True, ("(sin token) -> 401",)))
open(os.path.join(EV, "verify-step-sim.txt"), "w").write("\n".join(t for _, t in res))
sys.exit(0 if all(o for o, _ in res) else 1)
