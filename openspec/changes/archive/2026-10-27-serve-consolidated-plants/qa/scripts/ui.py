#!/usr/bin/env python3 -I
"""Ayudante de adb/uiautomator para la QA 11.3 (solo el emulador emulator-5554, nunca un telefono fisico).
Uso como modulo: import ui (desde un script en la misma carpeta, sin -I) o por linea de comandos:
  ui.py dump                   imprime los nodos con texto o descripcion y sus limites
  ui.py tap "texto"            toca el primer nodo cuyo texto o content-desc contiene "texto"
  ui.py tapxy X Y
  ui.py shot nombre            guarda evidence/app/nombre.png
  ui.py swipe x1 y1 x2 y2 [ms]
  ui.py type "texto"           escribe en el campo con foco
  ui.py back
"""
import os, re, subprocess, sys, time, xml.etree.ElementTree as ET
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = "emulator-5554"
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence", "app")

def adb(*a, out=False):
    r = subprocess.run([ADB, "-s", DEV, *a], capture_output=True)
    return r.stdout if out else r

def nodes():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("exec-out", "cat", "/sdcard/ui.xml", out=True).decode("utf-8", "replace")
    root = ET.fromstring(xml[xml.index("<"):])
    res = []
    for n in root.iter("node"):
        b = tuple(map(int, re.findall(r"\d+", n.get("bounds"))))
        res.append(dict(text=n.get("text"), desc=n.get("content-desc"), cls=n.get("class"), b=b, clickable=n.get("clickable") == "true", focused=n.get("focused") == "true", id=n.get("resource-id")))
    return res

def show():
    for n in nodes():
        if n["text"] or n["desc"]:
            print(f"{n['b']} {'C' if n['clickable'] else ' '} text={n['text']!r} desc={n['desc']!r}")

def find(sub):
    for n in nodes():
        if sub in (n["text"] or "") or sub in (n["desc"] or ""):
            return n
    return None

def tap(sub):
    n = find(sub)
    if not n: print("no encontrado:", sub); return False
    x1, y1, x2, y2 = n["b"]; adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); return True

def shot(name):
    os.makedirs(EV, exist_ok=True)
    open(os.path.join(EV, name + ".png"), "wb").write(adb("exec-out", "screencap", "-p", out=True))

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "dump": show()
    elif c == "tap": tap(sys.argv[2])
    elif c == "tapxy": adb("shell", "input", "tap", sys.argv[2], sys.argv[3])
    elif c == "shot": shot(sys.argv[2])
    elif c == "swipe": adb("shell", "input", "swipe", *sys.argv[2:6], *(sys.argv[6:7] or ["300"]))
    elif c == "type": adb("shell", "input", "text", sys.argv[2].replace(" ", "%s"))
    elif c == "back": adb("shell", "input", "keyevent", "4")
