#!/usr/bin/env python3
"""AUT-28: tiempo de respuesta según la posición en que difiere el token (indicativo, no prueba de tiempo constante).

Uso: BASE_URL=http://localhost:8080 TOKEN=$TOKEN_LOCAL_1 N=3000 python3 -I timing.py
Una conexión persistente, variantes intercaladas al azar. Imprime medianas y percentiles en microsegundos; no imprime tokens.
"""
import http.client, os, random, statistics, time, urllib.parse

u = urllib.parse.urlparse(os.environ.get("BASE_URL", "http://localhost:8080"))
tok = os.environ["TOKEN"]
n = int(os.environ.get("N", "3000"))
flip = lambda c: "0" if c != "0" else "1"
variants = {
    "primer-caracter-distinto": flip(tok[0]) + tok[1:],
    "ultimo-caracter-distinto": tok[:-1] + flip(tok[-1]),
    "mitad-distinta": tok[:32] + flip(tok[32]) + tok[33:],
    "valido": tok,
}
samples = {k: [] for k in variants}
conn = http.client.HTTPConnection(u.hostname, u.port or 80)
order = [k for k in variants for _ in range(n)]
random.shuffle(order)
for k in order:
    t0 = time.perf_counter_ns()
    conn.request("GET", "/v1/plants?limit=1", headers={"Authorization": "Bearer " + variants[k]})
    r = conn.getresponse(); r.read()
    samples[k].append((time.perf_counter_ns() - t0) / 1000)
    assert r.status == (200 if k == "valido" else 401), (k, r.status)
q = lambda xs, p: sorted(xs)[int(len(xs) * p)]
print(f"N={n} por variante (microsegundos)")
for k, xs in samples.items():
    print(f"{k:28s} mediana={statistics.median(xs):8.1f} p10={q(xs,.10):8.1f} p90={q(xs,.90):8.1f}")
a, b = samples["primer-caracter-distinto"], samples["ultimo-caracter-distinto"]
print(f"diferencia de medianas primer vs ultimo: {statistics.median(a)-statistics.median(b):+.1f} us")
