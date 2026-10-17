#!/usr/bin/env python3
"""Servidor HTTP mínimo (NO es el backend) para comprobar si el build release admite HTTP en claro.

Devuelve una página vacía válida del contrato en cualquier GET y registra cada petición en stdout.
Uso: cleartext_probe_server.py [puerto]   (por defecto 8089; el emulador lo ve en http://10.0.2.2:<puerto>)
"""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"items": [], "total": 0, "limit": 50, "offset": 0}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print("PETICION", self.command, self.path, self.headers.get("user-agent"), flush=True)
    def log_message(self, *a):
        pass

HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8089), H).serve_forever()
