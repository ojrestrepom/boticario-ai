#!/usr/bin/env python3
"""F-01..F-06: fallos inyectados por el proxy (5xx, 400, JSON invalido, campo faltante, campos extra, 404 en listado)."""
import json, time
import aq

R = '/private/tmp/claude-501/-Users-jsrc1115-Code-boticario-ai/33eca2b0-2538-4cac-a7d1-83935d2c2271/scratchpad/rules.json'
assert aq.avd() == 'boticario_catalog_api36'


def rules(r):
    open(R, 'w').write(json.dumps(r))


def case(cid, rule, expect_sub, desc, route=None):
    rules([rule])
    aq.stop()
    if route:
        aq.sh('shell', 'am', 'start', '-n', aq.PKG + '/.MainActivity', '--es', 'route', route)
        aq.wait_for('Volver a Explorar', timeout=25)
    else:
        aq.launch()
        aq.wait_for('Explorar plantas', timeout=25)
        aq.tap('Explorar plantas')
    time.sleep(3.5)
    labs = aq.labels()
    aq.snap(cid.lower())
    ok = any(expect_sub in l for l in labs) and bool(aq.find('Reintentar', exact=True)) and not aq.crashed()
    aq.rec(cid, 'PASS' if ok else 'FAIL', f'{desc}: labels={labs}')
    rules([])


case('F-01', {'match': 'limit=50&offset=0', 'status': 503}, 'HTTP 503', 'listado responde 503')
case('F-02', {'match': 'limit=50&offset=0', 'status': 400}, 'rechazó la solicitud', 'listado responde 400 problem+json')
case('F-03', {'match': 'limit=50&offset=0', 'status': 200, 'ctype': 'application/json', 'body': '{"items": [ {"id": '}, 'no es válida', 'listado 200 con JSON truncado')
case('F-04', {'match': 'limit=50&offset=0', 'status': 200, 'ctype': 'application/json', 'body': '{"total":2,"limit":50,"offset":0}'}, 'no es válida', 'listado 200 sin campo items')
case('F-05', {'match': '/v1/plants/lavandula-angustifolia', 'status': 500}, 'HTTP 500', 'detalle responde 500', route='/explore/lavandula-angustifolia')
case('F-06', {'match': '/v1/plants/lavandula-angustifolia', 'status': 200, 'ctype': 'application/json', 'body': '{"id":"lavandula-angustifolia","family":"X","names":[],"parts":[],"uses":[]}'}, 'no es válida', 'detalle 200 sin scientificName', route='/explore/lavandula-angustifolia')
# F-07: campos desconocidos se ignoran (cambio aditivo de /v1)
body = json.dumps({"items": [{"id": "x-y", "scientificName": "Xus yus", "commonNames": [{"text": "Prueba", "language": "es", "extra": 1}], "family": None, "nuevoCampo": {"a": 1}}], "total": 1, "limit": 50, "offset": 0, "campoFuturo": [1, 2]})
rules([{'match': 'limit=50&offset=0', 'status': 200, 'ctype': 'application/json', 'body': body}])
aq.launch(); aq.wait_for('Explorar plantas', timeout=25); aq.tap('Explorar plantas'); time.sleep(3)
rows = aq.row_labels(); aq.snap('f-07')
aq.rec('F-07', 'PASS' if rows == ['Prueba, Xus yus'] else 'FAIL', f'respuesta con campos desconocidos y family null: filas={rows} labels={aq.labels()[:8]}')
rules([])
