#!/usr/bin/env python3
"""H-01: muestrea /proc/net/tcp* filtrando el UID de la app mientras se recorre Home, P06, Explorar y Pasaporte; solo debe haber destino 10.0.2.2:8080."""
import subprocess, threading, time, json, re
import aq

assert aq.avd() == 'boticario_catalog_api36'
uid = re.search(r'\buid=(\d+)', aq.sh('shell', 'dumpsys', 'package', aq.PKG)).group(1)
print('uid', uid)
conns = set()
stop = False


def hexip(h):
    b = bytes.fromhex(h)[::-1]
    return '.'.join(str(x) for x in b)


def sample():
    while not stop:
        for f in ('tcp', 'tcp6'):
            out = aq.sh('shell', 'cat', f'/proc/net/tcp{"6" if f == "tcp6" else ""}', check=False)
            for line in out.splitlines()[1:]:
                p = line.split()
                if len(p) > 8 and p[7] == uid:
                    rem, st = p[2], p[3]
                    ip, port = rem.split(':')
                    if f == 'tcp6':
                        # ::ffff:a.b.c.d mapeado
                        if ip.startswith('0000000000000000FFFF0000'):
                            ipd = hexip(ip[24:])
                        else:
                            ipd = 'v6:' + ip
                    else:
                        ipd = hexip(ip)
                    conns.add((ipd, int(port, 16), st))
        time.sleep(0.4)


t = threading.Thread(target=sample, daemon=True)
t.start()
aq.go_explore()
aq.set_query('lavandula'); time.sleep(1.5)
aq.tap('English Lavender, Lavandula angustifolia', exact=True); time.sleep(2)
aq.tap('Propiedades', exact=True); time.sleep(0.8)
aq.tap('Usos', exact=True); time.sleep(0.8)
aq.tap('Volver a Explorar', exact=True); time.sleep(1.2)
aq.tap('Volver a Inicio', exact=True); time.sleep(1)
aq.tap('Buscar por objetivo'); time.sleep(2)
aq.back(); time.sleep(1.5)
stop = True
t.join()
remote = sorted(conns)
# estado 0A = LISTEN (socket de escucha local del VM de depuracion), no es trafico saliente
others = [c for c in remote if c[2] != '0A' and not (c[0] == '10.0.2.2' and c[1] == 8080)]
aq.rec('H-01', 'PASS' if remote and not others else 'FAIL', f'conexiones TCP del UID {uid} observadas (ip, puerto, estado): {remote}; destinos salientes distintos de 10.0.2.2:8080 (excluidos sockets en LISTEN): {others}')
