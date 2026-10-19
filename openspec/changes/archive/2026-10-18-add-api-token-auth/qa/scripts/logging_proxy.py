#!/usr/bin/env python3
"""Proxy de registro para la QA de la app (APP-08, APP-14): reenvía a la API local y anota cada petición sin valores de token.

Uso: TOKEN_LOCAL_1/2/3=... python3 -I logging_proxy.py <puerto-escucha> <puerto-api> <archivo-de-registro>
Cada línea: hora método ruta+query; Authorization = ausente | Bearer <token-local-N> | Bearer <otro> | <otro esquema>;
nombres de las demás cabeceras enviadas por la app; estado de la respuesta de la API. Nunca escribe el valor de un token.
"""
import http.client, http.server, os, sys, threading, time

listen, upstream, logfile = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
known = {os.environ[f"TOKEN_LOCAL_{n}"]: f"<token-local-{n}>" for n in (1, 2, 3) if os.environ.get(f"TOKEN_LOCAL_{n}")}
lock = threading.Lock()


def classify(value):
    if value is None:
        return "ausente"
    scheme, _, rest = value.partition(" ")
    if scheme.lower() != "bearer":
        return f"esquema {scheme}"
    return f"Bearer {known.get(rest.strip(), '<otro>')}"


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _do(self):
        conn = http.client.HTTPConnection("127.0.0.1", upstream, timeout=30)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
        conn.request(self.command, self.path, headers=hdrs)
        r = conn.getresponse()
        body = r.read()
        names = sorted(k for k in self.headers.keys() if k.lower() not in ("host", "connection", "authorization", "accept-encoding"))
        line = f"{time.strftime('%H:%M:%S')} {self.command} {self.path} Authorization={classify(self.headers.get('Authorization'))} otras-cabeceras={names} -> {r.status}"
        with lock, open(logfile, "a") as f:
            f.write(line + "\n")
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_HEAD = _do

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("0.0.0.0", listen), H).serve_forever()
