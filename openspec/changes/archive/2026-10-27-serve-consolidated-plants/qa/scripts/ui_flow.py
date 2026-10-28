#!/usr/bin/env python3
"""11.3: recorre el pasaporte de plantas en el emulador y guarda los textos visibles por pestana (uiautomator) y capturas.
Uso: ui_flow.py <busqueda> <fragmento de la fila> <nombre de evidencia> [capturas: 1|0]
Requiere la app en Explorar. Solo emulator-5554. No escribe el token: solo texto de la interfaz.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui

def clear_and_type(q):
    if ui.tap("Borrar búsqueda"): time.sleep(1)
    ui.adb("shell", "input", "tap", "400", "450"); time.sleep(0.7)
    ui.adb("shell", "input", "text", q.replace(" ", "%s")); time.sleep(2.5)
    ui.adb("shell", "input", "keyevent", "4"); time.sleep(1)

def to_top():
    for _ in range(40):
        if any(n["desc"] and n["desc"].startswith("Volver a") for n in ui.nodes()): return True
        ui.adb("shell", "input", "swipe", "540", "400", "540", "1600", "200"); time.sleep(0.4)
    return False

def collect(max_steps=14, shots=None):
    seen = []; last = None
    for step in range(max_steps):
        ns = ui.nodes()
        for n in ns:
            for t in (n["text"], n["desc"]):
                if t and t not in seen and not t.startswith(("Inicio", "Favoritos", "Historial", "Perfil", "Ver formulaciones")): seen.append(t)
        sig = [(n["b"], n["desc"], n["text"]) for n in ns]
        if sig == last or any(t and t.startswith("Fuentes") for t in [n["desc"] for n in ns]) and step > 0 and any("Enlace" in (n["desc"] or "") or "Atribución" in (n["desc"] or "") for n in ns): break
        last = sig
        if shots: ui.shot(f"{shots}-{step}")
        ui.adb("shell", "input", "swipe", "540", "1400", "540", "560", "350"); time.sleep(0.8)
    return seen

def main():
    query, row, name = sys.argv[1:4]; shots = (sys.argv[4] == "1") if len(sys.argv) > 4 else False
    clear_and_type(query)
    if not ui.tap(row): print("fila no encontrada", row); return
    time.sleep(4)
    out = []
    for tab in ("General", "Propiedades", "Usos"):
        # volver arriba y tocar la pestana
        to_top()
        n = []
        for _ in range(8):
            n = [x for x in ui.nodes() if x["desc"] == tab and x["clickable"] and x["b"][1] > 150 and x["b"][3] < 1480]
            if n: break
            ui.adb("shell", "input", "swipe", "540", "1300", "540", "900", "300"); time.sleep(0.6)
        if not n: out.append(f"## {tab}\n(chip no alcanzable)\n"); continue
        x1, y1, x2, y2 = n[0]["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); time.sleep(1)
        seen = collect(shots=f"{name}-{tab}" if shots else None)
        out.append(f"## {tab}\n" + "\n".join(seen) + "\n")
    path = os.path.join(ui.EV, f"passport-{name}.txt")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    for _ in range(3):
        ui.adb("shell", "input", "keyevent", "4"); time.sleep(1)
        if any(n["desc"] == "Todas" for n in ui.nodes()): break
    print("ok", path)

if __name__ == "__main__": main()
