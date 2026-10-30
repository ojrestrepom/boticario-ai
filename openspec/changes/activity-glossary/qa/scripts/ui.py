#!/usr/bin/env python3
"""Ayudante de adb para el recorrido a mano en el emulador (solo emulator-5554)."""
import os, re, subprocess, sys, xml.etree.ElementTree as ET
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = "emulator-5554"

def adb(*a, **k):
    return subprocess.run([ADB, "-s", DEV, *a], capture_output=True, **k)

def dump():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    x = adb("exec-out", "cat", "/sdcard/ui.xml").stdout.decode("utf-8", "replace")
    return ET.fromstring(x)

def nodes(root):
    for n in root.iter("node"):
        b = re.findall(r"\d+", n.get("bounds"))
        x1, y1, x2, y2 = map(int, b)
        yield dict(text=n.get("text") or "", desc=n.get("content-desc") or "", b=(x1, y1, x2, y2), click=n.get("clickable") == "true", cls=n.get("class"))

def texts(root):
    for n in nodes(root):
        t = n["text"] or n["desc"]
        if t:
            print(n["b"], "C" if n["click"] else " ", t.replace("\n", " | ")[:300])

def tap_xy(x, y):
    adb("shell", "input", "tap", str(x), str(y))

def find(root, pat):
    r = re.compile(pat)
    for n in nodes(root):
        if r.search(n["text"]) or r.search(n["desc"]):
            return n

def tap(pat):
    n = find(dump(), pat)
    if not n:
        print("NO ENCONTRADO", pat); return False
    x1, y1, x2, y2 = n["b"]; tap_xy((x1 + x2) // 2, (y1 + y2) // 2); return True

def swipe_up(d=700):
    y0 = 1300
    adb("shell", "input", "swipe", "540", str(y0), "540", str(max(150, y0 - d)), "400")

def shot(path):
    open(path, "wb").write(adb("exec-out", "screencap", "-p").stdout)

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "dump": texts(dump())
    elif c == "tap": print(tap(sys.argv[2]))
    elif c == "xy": tap_xy(sys.argv[2], sys.argv[3])
    elif c == "up": swipe_up(int(sys.argv[2]) if len(sys.argv) > 2 else 700)
    elif c == "shot": shot(sys.argv[2])
