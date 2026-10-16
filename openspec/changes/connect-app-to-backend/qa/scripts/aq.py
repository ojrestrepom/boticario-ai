#!/usr/bin/env python3
"""Helper de QA para Android (adb + uiautomator). Solo opera sobre emulator-5554 / AVD boticario_catalog_api36.

Uso como libreria desde los escenarios y como CLI: `aq.py dump|shot NAME|tap TEXT|back|text`.
"""
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

QA = Path(__file__).resolve().parents[1]
EV = QA / 'evidence'
ADB = str(Path.home() / 'Library/Android/sdk/platform-tools/adb')
SERIAL = 'emulator-5554'
PKG = 'com.example.boticario_ai'


def sh(*args, binary=False, check=True):
    p = subprocess.run([ADB, '-s', SERIAL, *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.decode(errors='replace'))
    return p.stdout if binary else p.stdout.decode(errors='replace')


def avd():
    return sh('emu', 'avd', 'name').splitlines()[0].strip()


class Node:
    def __init__(self, e):
        self.text = e.get('text', '')
        self.desc = e.get('content-desc', '')
        self.cls = e.get('class', '')
        self.clickable = e.get('clickable') == 'true'
        self.enabled = e.get('enabled') == 'true'
        self.scrollable = e.get('scrollable') == 'true'
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', e.get('bounds', '[0,0][0,0]'))
        self.x1, self.y1, self.x2, self.y2 = map(int, m.groups())

    @property
    def label(self):
        return self.text or self.desc

    @property
    def center(self):
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def w(self):
        return self.x2 - self.x1

    @property
    def h(self):
        return self.y2 - self.y1

    def __repr__(self):
        return f'<{self.cls.split(".")[-1]} {self.label!r} [{self.x1},{self.y1},{self.x2},{self.y2}] clk={self.clickable} en={self.enabled}>'


def dump_xml():
    for _ in range(5):
        raw = sh('exec-out', 'uiautomator', 'dump', '/dev/tty', check=False)
        s, e = raw.find('<?xml'), raw.rfind('</hierarchy>')
        if s >= 0 and e >= 0:
            return raw[s:e + len('</hierarchy>')]
        time.sleep(1)
    raise RuntimeError('sin arbol de UI')


def nodes():
    root = ET.fromstring(dump_xml())
    return [Node(e) for e in root.iter('node')]


def labels():
    return [n.label for n in nodes() if n.label]


def find(sub, exact=False, nds=None):
    nds = nds if nds is not None else nodes()
    out = []
    for n in nds:
        l = n.label
        if not l:
            continue
        if (exact and sub == l) or (not exact and sub.lower() in l.lower()):
            out.append(n)
    return out


def wait_for(sub, timeout=15, exact=False):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = find(sub, exact=exact)
        if r:
            return r[0]
        time.sleep(0.5)
    return None


def wait_gone(sub, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not find(sub):
            return True
        time.sleep(0.5)
    return False


def tap_xy(x, y):
    sh('shell', 'input', 'tap', x, y)


def tap(sub, exact=False, timeout=10):
    n = wait_for(sub, timeout, exact)
    if not n:
        raise RuntimeError(f'no encontrado: {sub}')
    tap_xy(*n.center)
    time.sleep(0.8)
    return n


def back():
    sh('shell', 'input', 'keyevent', 'KEYCODE_BACK')
    time.sleep(0.8)


def swipe(x1, y1, x2, y2, ms=300):
    sh('shell', 'input', 'swipe', x1, y1, x2, y2, ms)
    time.sleep(0.6)


def scroll_down(frac=0.5):
    # arrastra hacia arriba (contenido sube)
    swipe(540, int(1500), 540, int(1500 - 1000 * frac * 1.5), 350)


def scroll_up(frac=0.5):
    swipe(540, int(700), 540, int(700 + 1000 * frac * 1.5), 350)


def type_text(s):
    import shlex
    sh('shell', 'input', 'text', shlex.quote(s.replace(' ', '%s')))
    time.sleep(0.5)


def shot(name):
    EV.mkdir(parents=True, exist_ok=True)
    p = EV / f'{name}.png'
    p.write_bytes(sh('exec-out', 'screencap', '-p', binary=True))
    return p


def save_dump(name):
    EV.mkdir(parents=True, exist_ok=True)
    (EV / f'{name}.xml').write_text(dump_xml())


def snap(name):
    shot(name)
    save_dump(name)


def launch(clear=True):
    if clear:
        sh('shell', 'am', 'force-stop', PKG)
    sh('shell', 'am', 'start', '-n', PKG + '/.MainActivity', check=False)
    time.sleep(3)


def stop():
    sh('shell', 'am', 'force-stop', PKG)


def crashed():
    """True si logcat reciente tiene FATAL EXCEPTION del paquete."""
    out = sh('logcat', '-d', '-b', 'crash', check=False)
    return PKG in out


if __name__ == '__main__':
    assert avd() == 'boticario_catalog_api36', 'AVD incorrecto'
    c = sys.argv[1]
    if c == 'dump':
        for n in nodes():
            if n.label or n.clickable:
                print(n)
    elif c == 'shot':
        print(shot(sys.argv[2]))
    elif c == 'tap':
        print(tap(sys.argv[2]))
    elif c == 'back':
        back()
    elif c == 'labels':
        print('\n'.join(labels()))


def row_labels(nds=None):
    """Etiquetas de filas de resultados (Button grandes que no son chips ni barra)."""
    out = []
    for n in (nds if nds is not None else nodes()):
        if n.cls.endswith('Button') and n.h > 150 and n.y1 > 700 and n.y2 < 1700 + 1 and n.w > 900 and n.label:
            out.append(n.label)
    return out


def slow_scroll(px=600):
    """Arrastre lento (sin inercia apreciable) de px pixeles hacia abajo en el contenido."""
    swipe(540, 1350, 540, 1350 - px, 1200)


def collect_rows(max_swipes=150, footer='No hay más resultados', px=600):
    """Desplaza hasta ver el pie o agotar; devuelve (filas en orden, pie visto, swipes)."""
    seen, order = set(), []
    stable = 0
    for i in range(max_swipes):
        nds = nodes()
        new = [l for l in row_labels(nds) if l not in seen]
        for l in new:
            seen.add(l)
            order.append(l)
        if find(footer, nds=nds):
            return order, True, i
        stable = stable + 1 if not new else 0
        if stable >= 4:
            return order, False, i
        slow_scroll(px)
    return order, False, max_swipes


import json as _json


def req_log():
    p = EV / 'proxy-all.jsonl'
    if not p.exists():
        return []
    return [_json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def req_mark():
    return len(req_log())


def reqs_since(mark):
    return req_log()[mark:]


RESULTS = QA / 'results.jsonl'


def rec(case, status, notes=''):
    with RESULTS.open('a') as f:
        f.write(_json.dumps({'case': case, 'status': status, 'notes': notes, 'ts': time.strftime('%Y-%m-%d %H:%M:%S')}, ensure_ascii=False) + '\n')
    print(f'[{status}] {case}: {notes}')


def go_explore(fresh=True):
    if fresh:
        launch()
    tap('Explorar plantas', timeout=25)
    time.sleep(2)


def to_top(max_swipes=40):
    for _ in range(max_swipes):
        if any(n.cls.endswith('EditText') for n in nodes()):
            return True
        swipe(540, 300, 540, 1600, 150)
    return False


def field_center():
    for n in nodes():
        if n.cls.endswith('EditText'):
            return n.center
    return (540, 450)


def set_query(text, dismiss=True):
    to_top()
    tap_xy(*field_center())
    time.sleep(0.4)
    # borrar lo previo con el boton de la app si existe
    c = find('Borrar búsqueda', exact=True)
    if c:
        tap_xy(*c[0].center)
        time.sleep(0.6)
        tap_xy(*field_center())
        time.sleep(0.4)
    if text:
        type_text(text)
    if dismiss:
        time.sleep(1.2)
        back()


def scroll_content_to_end(y1=1400, y2=700, max_swipes=80, name=None):
    """Arrastra dentro del area de contenido hasta que la captura deja de cambiar. Devuelve nº de arrastres."""
    import hashlib
    last = None
    for i in range(max_swipes):
        h = hashlib.md5(sh('exec-out', 'screencap', '-p', binary=True)).hexdigest()
        if h == last:
            return i
        last = h
        swipe(540, y1, 540, y2, 900)
    return max_swipes


def kbd_visible():
    out = sh('shell', 'dumpsys', 'input_method', check=False)
    return 'mInputShown=true' in out


def hide_kbd():
    if kbd_visible():
        back()
        time.sleep(0.5)
