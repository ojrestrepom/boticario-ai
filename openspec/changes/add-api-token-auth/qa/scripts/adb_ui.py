#!/usr/bin/env python3
"""Ayudas de UI para el emulador con adb y uiautomator (sin dependencias).

Uso:
  adb_ui.py dump                      lista textos y content-desc visibles con sus límites
  adb_ui.py tap "texto"               toca el primer elemento cuyo texto o content-desc contiene el texto
  adb_ui.py has "texto"               código 0 si hay un elemento con ese texto
  adb_ui.py shot ruta.png             captura de pantalla
  adb_ui.py swipe x1 y1 x2 y2 [ms]    desliza
  adb_ui.py type "texto"              escribe texto en el campo enfocado
  adb_ui.py wait "texto" [segundos]   espera a que aparezca el texto (por defecto 20 s)
"""
import os, re, subprocess, sys, time, xml.etree.ElementTree as ET

ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = os.environ.get("ANDROID_SERIAL", "emulator-5554")


def adb(*a, binary=False):
    return subprocess.run([ADB, "-s", DEV, *a], capture_output=True, text=not binary).stdout


def nodes():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("shell", "cat", "/sdcard/ui.xml")
    xml = xml[xml.find("<?xml"):] if "<?xml" in xml else xml
    out = []
    for n in ET.fromstring(xml).iter("node"):
        t = (n.get("text") or "").strip()
        d = (n.get("content-desc") or "").strip()
        if t or d:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds"))
            x1, y1, x2, y2 = map(int, m.groups())
            out.append((t, d, (x1 + x2) // 2, (y1 + y2) // 2, (x1, y1, x2, y2)))
    return out


def find(text):
    for t, d, cx, cy, b in nodes():
        if text.lower() in t.lower() or text.lower() in d.lower():
            return cx, cy
    return None


cmd = sys.argv[1]
if cmd == "dump":
    for t, d, cx, cy, b in nodes():
        print(f"{b} text={t!r} desc={d!r}")
elif cmd == "tap":
    p = find(sys.argv[2])
    if not p:
        print("no encontrado:", sys.argv[2]); sys.exit(1)
    adb("shell", "input", "tap", str(p[0]), str(p[1])); print("tap", p)
elif cmd == "has":
    sys.exit(0 if find(sys.argv[2]) else 1)
elif cmd == "shot":
    open(sys.argv[2], "wb").write(adb("exec-out", "screencap", "-p", binary=True))
elif cmd == "swipe":
    adb("shell", "input", "swipe", *sys.argv[2:6], *(sys.argv[6:7] or ["400"]))
elif cmd == "type":
    adb("shell", "input", "text", sys.argv[2].replace(" ", "%s"))
elif cmd == "wait":
    end = time.time() + float(sys.argv[3] if len(sys.argv) > 3 else 20)
    while time.time() < end:
        if find(sys.argv[2]):
            print("visible:", sys.argv[2]); sys.exit(0)
        time.sleep(1)
    print("no apareció:", sys.argv[2]); sys.exit(1)
