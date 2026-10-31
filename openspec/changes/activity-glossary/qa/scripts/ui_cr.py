#!/usr/bin/env python3
"""Ayudantes de adb sobre ui.py para la QA en Cloud Run (solo emulator-5554)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui


def scroll_to(pat, tries=25, d=900):
    for _ in range(tries):
        n = ui.find(ui.dump(), pat)
        if n and n["b"][1] > 250 and n["b"][3] < 1680:
            return n
        ui.swipe_up(d)
        time.sleep(0.6)
    return None


def full():
    for n in ui.nodes(ui.dump()):
        t = n["text"] or n["desc"]
        if t:
            print(n["b"], "C" if n["click"] else " ", t.replace("\n", " | "))


def open_plant(query, label_pat, tab="^Usos$"):
    """Desde Inicio: abre Explorar, busca `query`, abre la planta que coincide con `label_pat` y la pestaña `tab`."""
    ui.tap("Explorar plantas")
    time.sleep(3)
    n = next(x for x in ui.nodes(ui.dump()) if x["cls"] == "android.widget.EditText")
    x1, y1, x2, y2 = n["b"]
    ui.tap_xy((x1 + x2) // 2, (y1 + y2) // 2)
    time.sleep(1)
    ui.adb("shell", "input", "text", query.replace(" ", "%s"))
    time.sleep(0.5)
    time.sleep(2.5)
    ok = ui.tap(label_pat)
    time.sleep(4)
    if ok and tab:
        ui.tap(tab)
        time.sleep(2)
    return ok


def home():
    for _ in range(5):
        if ui.find(ui.dump(), "Explorar plantas y aceites"):
            return True
        ui.adb("shell", "input", "keyevent", "4")
        time.sleep(1.2)
    return False


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "full":
        full()
    elif c == "open":
        print(open_plant(sys.argv[2], sys.argv[3]))
    elif c == "home":
        print(home())
    elif c == "scroll":
        print(scroll_to(sys.argv[2]))
    elif c == "scrolltap":
        n = scroll_to(sys.argv[2])
        if n:
            x1, y1, x2, y2 = n["b"]
            ui.tap_xy((x1 + x2) // 2, (y1 + y2) // 2)
        print(n)
