#!/usr/bin/env python3
"""Casos P-01..P-06: pasaportes abiertos con la ruta real /explore/:id (extra `route` del intent de Flutter)."""
import json, re, time, urllib.request
import aq

API = 'http://localhost:18080'


def api(id_):
    return json.load(urllib.request.urlopen(f'{API}/v1/plants/{id_}'))


def open_route(id_):
    aq.stop()
    aq.sh('shell', 'am', 'start', '-n', aq.PKG + '/.MainActivity', '--es', 'route', f'/explore/{id_}')
    assert aq.wait_for('General', timeout=20, exact=True), 'pasaporte no cargo'
    time.sleep(0.8)


def general_text():
    for n in aq.nodes():
        if n.label.startswith('Familia\n') or n.label.startswith('Familia'):
            return n.label
    return None


def usos_collect(max_swipes=60):
    """Desplaza la pestaña Usos y devuelve la lista ordenada de (actividad, id de referencia, cita)."""
    seen, out = set(), []
    stable = 0
    for _ in range(max_swipes):
        nds = aq.nodes()
        new = 0
        for n in nds:
            if 'Registro tradicional' in n.label and n.label.startswith('Registros tradicionales') or 'Registro tradicional\n' in n.label:
                parts = n.label.split('Registro tradicional\n')[1:]
                for p in parts:
                    lines = p.split('\n')
                    if len(lines) >= 3:
                        key = (lines[0], lines[1].replace('Referencia: ', ''), lines[2])
                        if key not in seen:
                            seen.add(key)
                            out.append(key)
                            new += 1
        stable = stable + 1 if not new else 0
        if stable >= 3:
            break
        aq.slow_scroll(500)
    return out


def run_plant(case, id_, expect):
    d = api(id_)
    open_route(id_)
    aq.snap(f'p-{id_}-general')
    labs = aq.labels()
    gtxt = general_text()
    info = {'header': [l for l in labs if l in (expect['principal'], expect['scientific'])], 'general': gtxt}
    ok = expect['principal'] in labs and (expect['secondary'] is None or expect['scientific'] in labs)
    if expect['secondary'] is None:
        # solo un texto de cabecera con el cientifico (sin secundario duplicado)
        hdr = [n for n in aq.nodes() if n.y1 < 330 and n.label and n.cls.endswith('View')]
        info['header_nodes'] = [n.label for n in hdr]
        ok = ok and [n.label for n in hdr] == [expect['scientific']]
    ok = ok and all(s in (gtxt or '') for s in expect['general_contains'])
    aq.tap('Propiedades', exact=True); time.sleep(0.8)
    aq.snap(f'p-{id_}-propiedades')
    prop = [l for l in aq.labels() if l.startswith('Propiedades\n')]
    ok = ok and bool(prop) and 'sin propiedades medicinales evaluadas en este catálogo' in prop[0]
    aq.tap('Usos', exact=True); time.sleep(0.8)
    aq.snap(f'p-{id_}-usos')
    uses = usos_collect()
    aq.snap(f'p-{id_}-usos-end')
    exp_uses = [(u['activity'], u['reference']['id'], u['reference']['citation']) for u in d['uses']]
    info['usos_ui'] = len(uses)
    info['usos_api'] = len(exp_uses)
    if exp_uses:
        ok = ok and uses == exp_uses
    else:
        ok = ok and any('no hay usos tradicionales' in l.lower() or 'usos tradicionales con referencia' in l.lower() for l in aq.labels())
        info['usos_labels'] = aq.labels()
    aq.rec(case, 'PASS' if ok else 'FAIL', json.dumps(info, ensure_ascii=False)[:1500])
    return ok, info, uses


if __name__ == '__main__':
    assert aq.avd() == 'boticario_catalog_api36'
    run_plant('P-01', 'lavandula-angustifolia', dict(principal='English Lavender', scientific='Lavandula angustifolia', secondary=True,
              general_contains=['Lamiaceae', 'English Lavender (en)', 'Flower, Leaf, Plant, Seed', 'No aplicable']))
    run_plant('P-02', 'abies-spectabilis', dict(principal='Abies spectabilis', scientific='Abies spectabilis', secondary=None,
              general_contains=['Pinaceae']))
