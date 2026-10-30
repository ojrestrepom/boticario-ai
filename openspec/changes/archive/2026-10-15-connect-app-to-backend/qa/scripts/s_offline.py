#!/usr/bin/env python3
"""S-01..S-06: backend detenido con `docker compose stop` / `start` (topologia directa, sin proxy)."""
import subprocess, time, urllib.request
import aq

ROOT = '/Users/jsrc1115/Code/boticario-ai'
assert aq.avd() == 'boticario_catalog_api36'


def dc(*a):
    subprocess.run(['docker', 'compose', *a], cwd=ROOT, check=True, capture_output=True)


def healthy():
    try:
        return urllib.request.urlopen('http://localhost:8080/healthz', timeout=2).status == 200
    except Exception:
        return False


def wait_health(up=True, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if healthy() == up:
            return True
        time.sleep(0.5)
    return False


def reveal(label='Reintentar', tries=6):
    """Devuelve el nodo; si esta fuera de pantalla (texto al 200 %) desplaza el contenido hasta alcanzarlo."""
    for _ in range(tries):
        r = aq.find(label, exact=True)
        if r:
            return r
        aq.swipe(540, 1300, 540, 500, 800)
    return []


def tap_retry():
    r = reveal()
    assert r, 'Reintentar inalcanzable'
    aq.tap_xy(*r[0].center)
    time.sleep(0.8)


scale = aq.sh('shell', 'settings', 'get', 'system', 'font_scale').strip()
tag = 'a200-' if scale.startswith('2') else ''
print('font_scale', scale)

# S-01 Explorar con backend detenido desde el inicio
dc('start'); assert wait_health(True)
dc('stop'); assert wait_health(False)
aq.launch()
aq.wait_for('Explorar plantas', timeout=25)
aq.snap(tag + 's01-home-backend-down')
home_ok = bool(aq.find('Buscar por objetivo'))
aq.tap('Explorar plantas'); time.sleep(4)
labs = aq.labels()
aq.snap(tag + 's01-explore-error')
err = [l for l in labs if 'conectar' in l or 'servidor' in l]
retry = reveal()
aq.rec(tag + 'S-01', 'PASS' if err and retry and not aq.crashed() else 'FAIL', f'backend detenido: Explorar muestra {err} y boton Reintentar={bool(retry)} ({[(n.w//3, n.h//3) for n in retry]} dp); labels={labs}')
# S-02 Reintentar con backend aun detenido
tap_retry(); time.sleep(0.5)
loading = aq.labels()
time.sleep(3)
labs2 = aq.labels()
aq.rec(tag + 'S-02', 'PASS' if any('conectar' in l for l in labs2) and reveal() and not aq.crashed() else 'FAIL', f'Reintentar con backend detenido: tras el reintento vuelve a mostrar el error sin cierre; durante={[l for l in loading if "Cargando" in l]} despues={[l for l in labs2 if "conectar" in l]}')
# S-03 Inicio y P06 siguen funcionando con backend detenido
for _ in range(3):
    aq.swipe(540, 400, 540, 1300, 300)
aq.tap('Volver a Inicio', exact=True); time.sleep(1.2)
h1 = bool(aq.find('Explorar plantas'))
aq.tap('Buscar por objetivo'); time.sleep(2)
p06 = bool(aq.find('Selecciona un objetivo principal'))
aq.snap(tag + 's03-p06-backend-down')
aq.tap('Relajación / Estrés') if aq.find('Relajación / Estrés') else None
time.sleep(0.5)
aq.back(); time.sleep(1.2)
h2 = bool(aq.find('Explorar plantas'))
aq.rec(tag + 'S-03', 'PASS' if h1 and p06 and h2 and not aq.crashed() else 'FAIL', f'Inicio={h1}, P06 abre={p06}, regreso a Inicio={h2}, sin cierre inesperado={not aq.crashed()}')
# S-04 recuperacion: start y Reintentar
aq.tap('Explorar plantas'); time.sleep(3)
assert reveal()
dc('start'); assert wait_health(True), 'backend no volvio'
time.sleep(1)
tap_retry(); time.sleep(3)
rows = aq.row_labels()
aq.snap(tag + 's04-explore-recovered')
aq.rec(tag + 'S-04', 'PASS' if rows and rows[0].startswith('Okra') and not aq.find('Reintentar', exact=True) else 'FAIL', f'tras docker compose start, Reintentar carga la lista: filas={rows[:2]}')
# S-05 Pasaporte con backend detenido, error y recuperacion
dc('stop'); assert wait_health(False)
aq.stop()
aq.sh('shell', 'am', 'start', '-n', aq.PKG + '/.MainActivity', '--es', 'route', '/explore/lavandula-angustifolia')
aq.wait_for('Volver a Explorar', timeout=25); time.sleep(4)
labs = aq.labels()
aq.snap(tag + 's05-passport-error')
ok_err = ('No se pudo cargar la planta' in labs and reveal() and 'Planta no encontrada' not in labs and aq.find('Volver a Explorar', exact=True))
dc('start'); assert wait_health(True)
time.sleep(1)
tap_retry(); time.sleep(3)
labs2 = aq.labels()
aq.snap(tag + 's05-passport-recovered')
ok_rec = 'English Lavender' in labs2 and 'Lavandula angustifolia' in labs2
aq.rec(tag + 'S-05', 'PASS' if ok_err and ok_rec and not aq.crashed() else 'FAIL', f'pasaporte con backend detenido: error={labs}; tras start+Reintentar cabecera={labs2[1:3]}')
# S-06 pie de lista: backend se cae despues de la primera pagina
aq.go_explore()
dc('stop'); assert wait_health(False)
for i in range(30):
    aq.swipe(540, 1250, 540, 450, 250); time.sleep(0.3)
    if aq.find('Reintentar', exact=True):
        break
time.sleep(2)
reveal()
aq.slow_scroll(300)
labs = aq.labels()
aq.snap(tag + 's06-footer-error')
rows = aq.row_labels()
foot = [l for l in labs if 'conectar' in l]
aq.rec(tag + 'S-06a', 'PASS' if foot and reveal() and rows else 'FAIL', f'error en el pie sin perder lo cargado: filas visibles={rows[-2:]}, pie={foot}')
dc('start'); assert wait_health(True); time.sleep(1)
tap_retry(); time.sleep(3)
aq.slow_scroll(300)
rows2 = aq.row_labels()
aq.snap(tag + 's06-footer-recovered')
aq.rec(tag + 'S-06b', 'PASS' if not aq.find('Reintentar', exact=True) and rows2 else 'FAIL', f'Reintentar del pie tras start: sigue la lista; filas={rows2[:3]}')
print('crash:', aq.crashed())
