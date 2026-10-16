#!/usr/bin/env python3
"""E-01: primera pagina (50, orden alfabetico por cientifico), scroll infinito mas alla de 50 y posicion al volver desde el pasaporte tras la segunda pagina."""
import json, time, urllib.request
import aq

assert aq.avd() == 'boticario_catalog_api36'
aq.go_explore()
m = aq.req_mark()
rows, footer, sw = aq.collect_rows(max_swipes=34, px=800, footer='__sin_pie__')
reqs = [x['path'] for x in aq.reqs_since(m)]
items = []
for off in (0, 100):
    items += json.load(urllib.request.urlopen(f'http://localhost:18080/v1/plants?limit=100&offset={off}'))['items']
exp = [(i['commonNames'][0]['text'] + ', ' + i['scientificName']) if i['commonNames'] else i['scientificName'] for i in items]
n = len(rows)
sci = [i['scientificName'] for i in items]
ok = rows == exp[:n] and n > 100 and sci == sorted(sci, key=str.lower)
aq.rec('E-01', 'PASS' if ok else 'FAIL', f'primera carga limit=50&offset=0; tras {sw} arrastres se recorrieron {n} filas (>50) en el mismo orden que la API; peticiones de la sesion={reqs}')
# posicion tras volver: abrir una fila de la 2a pagina
aq.snap('e01-deep')
row = aq.row_labels()
tgt = row[1]
rows_before = aq.row_labels()
aq.tap(tgt, exact=True); time.sleep(2.5)
aq.tap('Volver a Explorar', exact=True); time.sleep(1.5)
rows_after = aq.row_labels()
aq.snap('e01-deep-after-return')
aq.rec('E-01b', 'PASS' if rows_before == rows_after else 'FAIL', f'posicion tras 2a pagina (>50 filas cargadas): antes={rows_before} despues={rows_after}')
