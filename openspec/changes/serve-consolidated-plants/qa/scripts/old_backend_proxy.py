#!/usr/bin/env python3 -I
"""APP-12: emula un backend anterior al cambio 2 (puerto 8081). Reenvia a la API real y quita de las respuestas los campos nuevos
(displayName, synonyms, description, origin, oil, useGroups, goals, safety, image, credits) y la cabecera Content-Location.
El token llega en la cabecera Authorization de la app y se reenvia tal cual; no se guarda ni se imprime.
Uso: old_backend_proxy.py [puerto] [url de la API real]   (se detiene con Ctrl+C o matando el proceso)
"""
import json, sys, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
UP = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8080"
NEW = ("displayName", "synonyms", "description", "origin", "oil", "useGroups", "goals", "safety", "image", "credits")
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        req = urllib.request.Request(UP + self.path, headers={k: v for k, v in self.headers.items() if k.lower() in ("authorization", "accept")})
        try: r = urllib.request.urlopen(req, timeout=30); status, body, ct = r.status, r.read(), r.headers.get("content-type", "")
        except urllib.error.HTTPError as e: status, body, ct = e.code, e.read(), e.headers.get("content-type", "")
        if status == 200 and "json" in ct:
            j = json.loads(body)
            for o in (j["items"] if isinstance(j, dict) and "items" in j else [j]):
                for k in NEW: o.pop(k, None)
            body = json.dumps(j, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("content-type", ct); self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
