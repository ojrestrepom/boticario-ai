#!/usr/bin/env python3
"""Casos ROT-01 a ROT-05: rotación de tokens contra el contenedor local (docker compose), sin tocar Google Cloud.

Uso (desde la raíz; tokens locales del entorno): TOKEN_LOCAL_1/2/3=... python3 -I .../rotation_test.py
Estados: A={t1}; B={t2,t1}; C={t2}; D={t3,t2}; E={t1,t2,t3} (orden y posición). Se recrea el contenedor entre estados con el mismo
comando que el README (`docker compose up -d` con otro API_TOKENS), sin reconstruir la imagen. No crea .env.
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
EV = os.path.join(HERE, "..", "evidence", "rotation")
os.makedirs(EV, exist_ok=True)
T = {n: os.environ[f"TOKEN_LOCAL_{n}"] for n in (1, 2, 3)}
MARK = {v: f"<token-local-{n}>" for n, v in T.items()}
out_lines, results = [], []


def red(s):
    for v, m in MARK.items():
        s = s.replace(v, m)
    return s


def say(s):
    out_lines.append(red(s))
    print(red(s), flush=True)


def compose(args, tokens):
    env = {k: v for k, v in os.environ.items() if k != "API_TOKENS"}
    env["API_TOKENS"] = tokens
    p = subprocess.run(["docker", "compose", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    return p.stdout + p.stderr


def status(path, tok=None):
    req = urllib.request.Request("http://localhost:8080" + path, headers={"Authorization": f"Bearer {tok}"} if tok else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def wait():
    for _ in range(60):
        if status("/health") == 200:
            return True
        time.sleep(0.5)
    return False


def container_id():
    return subprocess.run(["docker", "inspect", "-f", "{{.Id}}", "boticario-ai-api-1"], capture_output=True, text=True).stdout.strip()[:12]


def state(cid, label, tokens, expect):
    out = compose(["up", "-d"], tokens)
    names = ",".join(MARK[t] for t in tokens.replace("\r", "").replace("\n", "").replace(" ", "").split(","))
    say(f"\n## {cid} {label}\n$ API_TOKENS={names} docker compose up -d\n" + out.strip())
    assert wait(), "el servicio no arrancó"
    row = {}
    for n in (1, 2, 3):
        row[f"t{n}"] = status("/v1/plants?limit=1", T[n])
    row["sin token"] = status("/v1/plants?limit=1")
    row["/health"] = status("/health")
    ok = all(row[k] == v for k, v in expect.items())
    say(f"matriz: {row}   esperado: {expect}")
    say(("PASS " if ok else "FAIL ") + f"{cid} {label}")
    results.append({"case": cid, "check": label, "ok": ok, "detail": row})
    return out


compose(["down"], T[1])
cid_a = None
state("ROT-01", "A: solo el viejo (t1)", T[1], {"t1": 200, "t2": 401, "t3": 401, "sin token": 401, "/health": 200})
id_a = container_id()
outb = state("ROT-02", "B: nuevo y viejo (t2,t1), ambos aceptan", f"{T[2]},{T[1]}", {"t1": 200, "t2": 200, "t3": 401, "sin token": 401})
id_b = container_id()
recreated = id_a != id_b and "Recreate" in outb
say(f"ROT-05: contenedor A={id_a} B={id_b}; salida de compose menciona Recreate: {'Recreate' in outb}; sin «Building» en la salida: {'Building' not in outb}")
results.append({"case": "ROT-05", "check": "docker compose up -d con otro API_TOKENS recrea el contenedor sin reconstruir", "ok": recreated and "Building" not in outb, "detail": f"{id_a}->{id_b}"})
say(("PASS" if results[-1]["ok"] else "FAIL") + " ROT-05")
state("ROT-03", "C: se retira el viejo (solo t2)", T[2], {"t1": 401, "t2": 200, "t3": 401, "sin token": 401})
state("ROT-04", "D: segunda rotación (t3,t2)", f"{T[3]},{T[2]}", {"t1": 401, "t2": 200, "t3": 200, "sin token": 401})
state("ROT-04", "E: tres tokens (t1,t2,t3): primero, medio y último", f"{T[1]},{T[2]},{T[3]}", {"t1": 200, "t2": 200, "t3": 200, "sin token": 401})
state("ROT-04", "F: se retira el del medio (t1,t3)", f"{T[1]},{T[3]}", {"t1": 200, "t2": 401, "t3": 200, "sin token": 401})
compose(["down"], T[1])
with open(os.path.join(EV, "rotation.txt"), "w") as f:
    f.write("\n".join(out_lines) + "\n")
nf = sum(1 for r in results if not r["ok"])
say(f"\n{len(results) - nf} PASS, {nf} FAIL")
sys.exit(1 if nf else 0)
