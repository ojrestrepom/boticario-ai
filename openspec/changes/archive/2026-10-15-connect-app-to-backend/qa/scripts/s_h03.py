#!/usr/bin/env python3
"""H-03: analiza proxy-all.jsonl (solo peticiones de la app: user-agent Dart)."""
import collections, re
import aq
log = aq.req_log()
dart = [x for x in log if 'Dart' in x['headers'].get('user-agent', '')]
methods = collections.Counter(x['method'] for x in dart)
pat = collections.Counter(re.sub(r'/v1/plants/[^?]+', '/v1/plants/{id}', x['path'].split('?')[0]) for x in dart)
hdrs = collections.Counter(k.lower() for x in dart for k in x['headers'])
hosts = collections.Counter(x['headers'].get('host') for x in dart)
bad = [x['path'] for x in dart if not re.match(r'^/v1/plants(/[^/?]+)?(\?.*)?$', x['path'])]
lim = collections.Counter(re.findall(r'limit=(\d+)', ' '.join(x['path'] for x in dart if x['path'].startswith('/v1/plants?'))))
accept = collections.Counter(x['headers'].get('accept') for x in dart)
ok = (not bad and set(pat) <= {'/v1/plants', '/v1/plants/{id}'} and set(methods) == {'GET'}
      and set(hdrs) <= {'user-agent', 'accept', 'accept-encoding', 'host'} and set(lim) == {'50'}
      and accept == {'application/json': len(dart)} and set(hosts) == {'10.0.2.2:8080'})
aq.rec('H-03', 'PASS' if ok else 'FAIL', f'{len(dart)} peticiones de la app en toda la sesion (proxy-all.jsonl): metodos={dict(methods)}, rutas={dict(pat)}, cabeceras presentes={dict(hdrs)}, host={dict(hosts)}, limit={dict(lim)}, Accept={dict(accept)}, rutas fuera de patron={bad}')
