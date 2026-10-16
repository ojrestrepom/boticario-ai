#!/usr/bin/env python3
"""Casos N-01..N-04: navegacion, conservacion de estado y reinicio de Explorar."""
import time
import aq

assert aq.avd() == 'boticario_catalog_api36'

# N-01: consulta + filtro + posicion se conservan al volver del pasaporte
aq.go_explore()
aq.tap('Plantas', exact=True); time.sleep(0.8)
aq.set_query('ros'); time.sleep(1.5)
for _ in range(8):
    aq.slow_scroll(700)
time.sleep(1)
before_rows = aq.row_labels()
aq.snap('n01-before-open')
target = before_rows[min(2, len(before_rows) - 1)]
m = aq.req_mark()
aq.tap(target, exact=True); time.sleep(2.5)
labs = aq.labels()
sci = target.split(', ')[-1]
principal = target.split(', ')[0] if ', ' in target else target
aq.snap('n01-passport')
open_ok = sci in labs and principal in labs
reqs = [x['path'] for x in aq.reqs_since(m)]
aq.tap('Volver a Explorar', exact=True); time.sleep(1.5)
after_rows = aq.row_labels()
aq.snap('n01-after-return')
fld = [n.label for n in aq.nodes() if n.cls.endswith('EditText')]
chips = [n for n in aq.nodes() if n.label == 'Plantas']
ok = open_ok and after_rows == before_rows
aq.rec('N-01a', 'PASS' if ok else 'FAIL', f'abrio {target!r}: cabecera correcta={open_ok}; peticiones al abrir={reqs}; filas visibles antes={before_rows} despues={after_rows}; campo={fld}')
# al volver no debe haber nuevas peticiones de lista; verificar la consulta sigue en el campo desplazando arriba
reqs_after = [x['path'] for x in aq.reqs_since(m)]
aq.to_top()
aq.snap('n01-top-after-return')
fld = [n.label for n in aq.nodes() if n.cls.endswith('EditText')]
aq.rec('N-01b', 'PASS' if fld == ['ros'] and reqs_after == reqs else 'FAIL', f'campo={fld}, peticiones tras volver={reqs_after} (solo la del detalle esperada)')

# N-01c: Atras de Android desde el pasaporte (el campo de busqueda se desenfoca antes arrastrando la lista)
aq.hide_kbd(); aq.slow_scroll(300); aq.to_top()
aq.snap('n01c-before')
rows0 = aq.row_labels()
aq.tap(rows0[0], exact=True); time.sleep(2.5)
aq.back(); time.sleep(1.5)
rows1 = aq.row_labels()
aq.rec('N-01c', 'PASS' if rows0 == rows1 else 'FAIL', f'Atras de Android desde pasaporte: filas antes={rows0} despues={rows1}')

# N-02: Inicio desde Explorar y reinicio
aq.tap('Inicio', exact=True); time.sleep(1.5)
home = aq.labels()
ok_home = 'Explorar plantas y aceites' in home
aq.snap('n02-home')
m = aq.req_mark()
aq.tap('Explorar plantas'); time.sleep(2.5)
labs = aq.labels()
fld = [n.label for n in aq.nodes() if n.cls.endswith('EditText')]
rows = aq.row_labels()
reqs = [x['path'] for x in aq.reqs_since(m)]
aq.snap('n02-reentry')
aq.rec('N-02', 'PASS' if ok_home and fld == [''] and rows[:1] == ['Okra, Abelmoschus esculentus'] and reqs == ['/v1/plants?limit=50&offset=0'] else 'FAIL', f'Home={ok_home}; campo={fld}; primera fila={rows[:1]}; peticiones={reqs}')

# N-03: chevron y Atras de Android desde Explorar vuelven a Inicio
aq.tap('Volver a Inicio', exact=True); time.sleep(1.2)
ok1 = 'Explorar plantas y aceites' in aq.labels()
aq.tap('Explorar plantas'); time.sleep(2)
aq.back(); time.sleep(1.2)
ok2 = 'Explorar plantas y aceites' in aq.labels()
aq.rec('N-03', 'PASS' if ok1 and ok2 else 'FAIL', f'chevron->Inicio={ok1}; Atras Android->Inicio={ok2}')

# N-04: barra inferior: Favoritos/Historial/Perfil deshabilitados en Explorar y Pasaporte
aq.tap('Explorar plantas'); time.sleep(2)
dis = [(n.label, n.enabled, n.clickable) for n in aq.nodes() if 'no disponible' in n.label]
aq.tap_xy(405, 1760); aq.tap_xy(675, 1760); aq.tap_xy(945, 1760); time.sleep(0.8)
still = 'Explorar' in aq.labels()
aq.rec('N-04a', 'PASS' if len(dis) == 3 and all(not e and not c for _, e, c in dis) and still else 'FAIL', f'Explorar: {dis}; sigue en Explorar tras tocar las tres={still}')
aq.tap(aq.row_labels()[0], exact=True); time.sleep(2.5)
dis = [(n.label, n.enabled, n.clickable) for n in aq.nodes() if 'no disponible' in n.label]
aq.tap_xy(405, 1760); aq.tap_xy(675, 1760); aq.tap_xy(945, 1760); time.sleep(0.8)
labs = aq.labels()
still = 'General' in labs
aq.tap_xy(996, 220); aq.tap_xy(540, 1584); time.sleep(0.8)
still2 = 'General' in aq.labels()
aq.rec('N-04b', 'PASS' if len(dis) >= 5 and all(not e and not c for _, e, c in dis) and still and still2 else 'FAIL', f'Pasaporte: {dis}; sigue en pasaporte tras tocar pestañas, favorito y formulaciones={still and still2}')
aq.tap('Inicio', exact=True); time.sleep(1.5)
aq.rec('N-04c', 'PASS' if 'Explorar plantas y aceites' in aq.labels() else 'FAIL', 'Inicio desde pasaporte lleva a Home')
print('crash:', aq.crashed())
