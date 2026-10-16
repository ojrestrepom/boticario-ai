#!/usr/bin/env python3
"""Proxy HTTP de QA: escucha en 127.0.0.1:8080 y reenvia al backend real (puerto 18080).

Registra cada peticion (metodo, ruta con query, cabeceras, estado, ms) en JSONL y permite inyectar fallos
leyendo reglas de un archivo JSON (ver RULES). No modifica las respuestas salvo que una regla lo pida.
Uso: logproxy.py LOG.jsonl [RULES.json]
Regla: {"match": "subcadena de la ruta", "delay": segundos, "status": 500, "body": "texto", "ctype": "application/json", "drop": true}
"""
import http.client
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = sys.argv[1]
RULES = sys.argv[2] if len(sys.argv) > 2 else None
UP = ('127.0.0.1', 18080)
lock = threading.Lock()


def rules():
    if not RULES:
        return []
    try:
        return json.load(open(RULES))
    except Exception:
        return []


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def do_GET(self):
        t0 = time.time()
        rec = {'start': round(t0, 3), 'ts': time.strftime('%H:%M:%S'), 'method': 'GET', 'path': self.path,
               'headers': {k: v for k, v in self.headers.items()}}
        rule = next((r for r in rules() if r['match'] in self.path), None)
        status = None
        try:
            if rule and rule.get('delay'):
                time.sleep(rule['delay'])
            if rule and rule.get('drop'):
                rec['injected'] = 'drop'
                self.close_connection = True
                self.connection.close()
                status = 'dropped'
                return
            if rule and rule.get('status'):
                body = rule['body'].encode() if 'body' in rule else b'{"title":"injected"}'
                self.send_response(rule['status'])
                self.send_header('Content-Type', rule.get('ctype', 'application/problem+json'))
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                status = rule['status']
                rec['injected'] = rule['status']
                return
            c = http.client.HTTPConnection(*UP, timeout=30)
            c.request('GET', self.path, headers={'Accept': self.headers.get('Accept', '*/*')})
            r = c.getresponse()
            body = r.read()
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() in ('content-type',):
                    self.send_header(k, v)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            status = r.status
            if rule:
                rec['injected'] = 'delay %s' % rule.get('delay')
        except Exception as e:  # el cliente pudo cerrar (timeout)
            status = status or 'client-closed: %s' % type(e).__name__
        finally:
            rec['status'] = status
            rec['ms'] = int((time.time() - t0) * 1000)
            with lock:
                open(LOG, 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')


ThreadingHTTPServer.daemon_threads = True
ThreadingHTTPServer(('127.0.0.1', 8080), H).serve_forever()
