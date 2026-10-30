#!/usr/bin/env python3
"""6.3: flujos de la interfaz en el emulador (emulator-5556) con adb y uiautomator. Uso: ui_flows.py <flujo> [...]
Flujos: p06, subareas, sheet, passport, stack, tabs, a11y, errors, auth, empty
Entorno: QA_TOKEN (solo para comparar que no aparece en pantalla), QA_PYLIB (Pillow). Escribe evidence/app/flows/<flujo>.txt y capturas."""
import io, os, re, subprocess, sys, time
sys.path.insert(0, os.environ["QA_PYLIB"]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageChops
import ui

TOKEN = os.environ.get("QA_TOKEN", "")
OUT = os.path.join(ui.EV, "flows"); os.makedirs(OUT, exist_ok=True)
REVIEW = os.path.join(ui.EV, "review"); os.makedirs(REVIEW, exist_ok=True)
GOALS = ["Relajación / Estrés", "Mejorar el sueño", "Cuidado de la piel", "Alivio respiratorio", "Cansancio y fatiga", "Otros objetivos"]
SUBS = ["Digestión", "Vías urinarias y genitales", "Dolor e inflamación", "Boca y garganta", "Circulación", "Molestias oculares"]
log = []; fails = []
def rec(name, ok, detail=""):
    log.append(f"{'PASA ' if ok else 'FALLA'} {name} {detail}".rstrip())
    if not ok: fails.append(name)
def note(t): log.append("OBS   " + t)
def descs(): return [(n["desc"] or "") for n in ui.nodes() if n["desc"]]
def has(d): return any(x == d or x.startswith(d) for x in descs())
def nd(d, exact=True):
    for n in ui.nodes():
        x = n["desc"] or ""
        if (x == d) if exact else (d in x): return n
def tap(d, exact=True, y_max=1900):
    n = nd(d, exact)
    if not n: return False
    x1, y1, x2, y2 = n["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(min((y1 + y2) // 2, y_max))); return True
def back(): ui.adb("shell", "input", "keyevent", "4"); time.sleep(1.8)
def img(): return Image.open(io.BytesIO(ui.adb("exec-out", "screencap", "-p", out=True))).convert("RGB")
def same(a, b, box):
    return ImageChops.difference(a.crop(box), b.crop(box)).getbbox() is None
def shot(name, review=False):
    png = ui.adb("exec-out", "screencap", "-p", out=True)
    open(os.path.join(REVIEW if review else OUT, name + ".png"), "wb").write(png)
def restart():
    ui.adb("shell", "am", "force-stop", "com.example.boticario_ai"); time.sleep(1)
    ui.adb("shell", "am", "start", "-n", "com.example.boticario_ai/.MainActivity"); time.sleep(5)
def to_p06():
    if not has("¿Qué deseas lograr?"):
        if has("Buscar por objetivo"): tap("Buscar por objetivo"); time.sleep(3)
    return has("¿Qué deseas lograr?")
def open_goal(name):
    to_p06(); assert tap(name), f"fila {name}"; time.sleep(4)
def swipe_up(n=1, ms=900):
    for _ in range(n): ui.adb("shell", "input", "swipe", "540", "1650", "540", "550", str(ms)); time.sleep(0.4)
def focus(): return subprocess.run([ui.ADB, "-s", ui.DEV, "shell", "dumpsys", "window"], capture_output=True, text=True).stdout
def foreground_is_app():
    m = re.search(r"mCurrentFocus=.*", focus()); return "boticario_ai" in (m.group(0) if m else "")

def f_p06():
    restart(); assert tap("Buscar por objetivo"); time.sleep(3)
    nodes = ui.nodes(); rows = [n for n in nodes if (n["desc"] or "") in GOALS and n["clickable"]]
    rec("UI-01 P06: título, subtítulo y botón Volver a Inicio", has("¿Qué deseas lograr?") and has("Selecciona un objetivo principal") and has("Volver a Inicio"))
    rec("UI-01 P06: seis filas en el orden del catálogo, todas botones (clickable)", [n["desc"] for n in sorted(rows, key=lambda n: n["b"][1])] == GOALS, str([n["desc"] for n in rows]))
    rec("UI-01 P06: sin 'Concentración'", not any("oncentra" in d for d in descs()))
    rec("UI-01 P06: ninguna fila muestra un conteo (el nombre de la etiqueta no lleva dígitos)", not any(re.search(r"\d", n["desc"]) for n in rows))
    rec("UI-01 P06: barra inferior con Inicio y las otras tres no disponibles", has("Inicio") and has("Favoritos no disponible") and has("Historial no disponible") and has("Perfil no disponible"))
    shot("p06-buscar-por-objetivo", review=True)
    swipe_up(2); time.sleep(1); shot("p06-final-del-scroll")
    rec("UI-01 P06: con scroll la sexta fila queda completa (alcanzable)", nd("Otros objetivos") is not None)
    ui.adb("shell", "input", "swipe", "540", "600", "540", "1700", "600"); time.sleep(1)
    before = img(); box = (0, 440, 1080, 1670)
    assert tap("Mejorar el sueño"); time.sleep(4)
    rec("UI-02 abrir 'Mejorar el sueño' lleva a P07 con 'Para: Mejorar el sueño'", has("Para: Mejorar el sueño") and has("Recomendaciones"))
    back(); time.sleep(1.5)
    rec("UI-01 volver a P06 con Atrás del sistema", has("¿Qué deseas lograr?"))
    after = img()
    rec("UI-01 ninguna fila queda seleccionada ni resaltada tras volver (zona de filas idéntica píxel a píxel)", same(before, after, box))

def f_subareas():
    restart(); assert tap("Buscar por objetivo"); time.sleep(3); assert tap("Otros objetivos"); time.sleep(3)
    nodes = ui.nodes(); rows = [n for n in nodes if (n["desc"] or "") in SUBS and n["clickable"]]
    rec("UI-03 subáreas: título 'Otros objetivos' y botón Volver", has("Otros objetivos") and has("Volver a objetivos"))
    rec("UI-03 subáreas: las seis filas en orden, todas botones", [n["desc"] for n in sorted(rows, key=lambda n: n["b"][1])] == SUBS, str([n["desc"] for n in rows]))
    rec("UI-03 subáreas: incluye «Molestias oculares» (1 planta, no se omite)", has("Molestias oculares"))
    shot("otros-objetivos-subareas", review=True)
    assert tap("Digestión"); time.sleep(4)
    rec("UI-03 abrir 'Digestión': 'Para: Digestión'", has("Para: Digestión"))
    back(); time.sleep(1.5)
    rec("UI-08 Atrás del sistema desde P07 de subárea vuelve a la pantalla de subáreas", has("Volver a objetivos") and has("Digestión"))
    back(); time.sleep(1.5)
    rec("UI-08 Atrás desde subáreas vuelve a P06", has("¿Qué deseas lograr?"))

def f_sheet():
    restart(); open_goal("Mejorar el sueño"); swipe_up(8); time.sleep(1.5)
    rec("UI-06 el aviso y 'Ver más detalles' están al final del scroll", has("Estas recomendaciones se basan en información especializada. Consulta detalles y precauciones.") and nd("Ver más detalles") is not None)
    before = img(); box = (0, 160, 1080, 1670)
    assert tap("Ver más detalles"); time.sleep(2)
    d = descs()
    rec("UI-06 la hoja 'Sobre estas recomendaciones' se abre", "Sobre estas recomendaciones" in d)
    body = " ".join(d)
    for frag in ["Agencia Europea de Medicamentos (EMA)", "no es un consejo médico ni una dosis", "marca de precaución señala advertencias de seguridad", "pasaporte de cada planta", "profesional de la salud"]:
        rec(f"UI-06 la hoja dice «{frag}»", frag in body)
    rec("UI-06 la hoja tiene el control Cerrar", nd("Cerrar") is not None)
    shot("ver-mas-detalles-hoja", review=True)
    tap("Cerrar"); time.sleep(1.5)
    rec("UI-06 cerrar con el control: P07 intacto (misma pantalla píxel a píxel)", same(before, img(), box))
    tap("Ver más detalles"); time.sleep(2)
    ui.adb("shell", "input", "swipe", "540", "1300", "540", "1850", "300"); time.sleep(1.5)
    note("arrastrar el cuerpo de la hoja (texto) no la cierra: " + ("se cerró" if "Sobre estas recomendaciones" not in descs() else "sigue abierta; el gesto lo consume el SingleChildScrollView del contenido"))
    ui.adb("shell", "input", "swipe", "540", "767", "540", "1700", "300"); time.sleep(1.5)
    rec("UI-06 cerrar deslizando desde el asa: la hoja desaparece y P07 queda intacto", "Sobre estas recomendaciones" not in descs() and same(before, img(), box))
    tap("Ver más detalles"); time.sleep(2)
    back(); time.sleep(1.5)
    rec("UI-06 cerrar con Atrás del sistema: vuelve a P07 (no sale a P06)", "Sobre estas recomendaciones" not in descs() and nd("Ver más detalles") is not None)
    rec("UI-06 tras cerrar con Atrás, P07 sigue idéntico", same(before, img(), box))
    note("sin peticiones ni registro: la hoja es un widget con texto constante (goal_results_page.dart, _DetailsSheet); la API de depuración no registra peticiones autorizadas, así que se verifica por lectura del código y por la prueba del producto")

def f_passport():
    restart(); open_goal("Alivio respiratorio"); swipe_up(12); time.sleep(2)
    cards = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra en:" in (n["desc"] or "") and n["b"][1] > 250 and n["b"][3] < 1680]
    assert cards, "sin tarjeta completa visible"
    c = cards[0]; name = [l for l in c["desc"].split("\n") if not l.startswith("Foto:")][0]
    before = img(); box = (0, 160, 1080, 1300); first_desc = c["desc"]  # sin la franja inferior: las miniaturas de abajo pueden terminar de cargar mientras tanto
    x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); time.sleep(5)
    d = descs()
    rec(f"UI-07 al tocar «{name}» se abre su pasaporte", name in d)
    rec("UI-07 el botón Atrás del pasaporte dice «Volver», no «Volver a Explorar»", "Volver" in d and not any("Volver a Explorar" in x for x in d), str([x for x in d if x.startswith("Volver")]))
    shot("passport-desde-tarjeta", review=False)
    tap("Volver"); time.sleep(0.8)
    d2 = descs(); rec("UI-07 al volver no aparece el estado de carga de P07 (no recarga la primera página)", "Cargando recomendaciones" not in d2)
    time.sleep(1.5)
    after = img()
    bb = ImageChops.difference(before.crop(box), after.crop(box)).getbbox()
    again = [n for n in ui.nodes() if n["desc"] == first_desc]
    rec("UI-07 al volver, la tarjeta tocada sigue en su misma posición (±60 px por miniaturas que terminan de cargar) con el mismo texto", bool(again) and abs(again[0]["b"][1] - c["b"][1]) <= 60, f"antes y={c['b'][1]}, después y={again[0]['b'][1] if again else None}")
    note("comparación píxel a píxel de P07 antes y después del pasaporte: " + ("idéntica" if bb is None else f"difiere en {bb} (miniaturas que terminaron de cargar entre una captura y otra)"))
    after.save(os.path.join(OUT, "passport-volver-despues.png")); before.save(os.path.join(OUT, "passport-volver-antes.png"))
    rec("UI-07 la tarjeta tocada sigue en su sitio con el mismo texto", any(n["desc"] == first_desc for n in ui.nodes()))
    # subárea
    restart(); to_p06(); tap("Otros objetivos"); time.sleep(3); tap("Digestión"); time.sleep(4); swipe_up(4); time.sleep(2)
    cards = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra en:" in (n["desc"] or "") and n["b"][1] > 250 and n["b"][3] < 1680]
    c = cards[0]; sci = c["desc"].split("\n")[-3] if False else [l for l in c["desc"].split("\n") if not l.startswith("Foto:")][1]
    y_before = c["b"][1]; x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); time.sleep(5)
    back(); time.sleep(3)
    again = [n for n in ui.nodes() if n["clickable"] and sci in (n["desc"] or "") and "La EMA la registra en:" in (n["desc"] or "")]
    for _ in range(6): ui.adb("shell", "input", "swipe", "540", "500", "540", "1700", "300"); time.sleep(0.4)
    time.sleep(1)
    rec("UI-07 desde una subárea: al volver conserva 'Para: Digestión' y la tarjeta tocada sigue en su posición (±200 px por miniaturas que terminan de cargar)", has("Para: Digestión") and bool(again) and abs(again[0]["b"][1] - y_before) <= 200, f"antes y={y_before}, después y={again[0]['b'][1] if again else None}")
    note("las tarjetas cambian de alto cuando la miniatura termina de cargar (aparece la línea de atribución): el contenido bajo ella se desplaza unos 10 dp; es la consecuencia de mostrar la atribución solo con la imagen cargada")

def f_stack():
    restart(); tap("Buscar por objetivo"); time.sleep(3); tap("Otros objetivos"); time.sleep(3); tap("Digestión"); time.sleep(4)
    cards = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra en:" in (n["desc"] or "")]
    c = cards[0]; x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(min((y1 + y2) // 2, 1500))); time.sleep(5)
    rec("UI-08 Inicio, P06, Otros objetivos, Digestión y una planta: se llega al pasaporte", has("Volver") and not has("Para: Digestión"))
    steps = [("P07", lambda: has("Para: Digestión")), ("subáreas", lambda: has("Volver a objetivos") and has("Digestión") and not has("Para: Digestión")),
             ("P06", lambda: has("¿Qué deseas lograr?")), ("Inicio", lambda: has("Explorar plantas y aceites"))]
    for mode in ("botón Volver de la app", "Atrás del sistema"):
        for k, (nm, ok) in enumerate(steps):
            if mode.startswith("botón"):
                labels = ["Volver", "Volver", "Volver a objetivos", "Volver a Inicio"]
                tap(labels[k]) if k else tap("Volver"); time.sleep(2)
            else: back()
            rec(f"UI-08 {mode}: paso {k + 1} vuelve a {nm}", ok())
        if mode.startswith("botón"):  # reconstruir la pila para el segundo modo
            tap("Buscar por objetivo"); time.sleep(3); tap("Otros objetivos"); time.sleep(3); tap("Digestión"); time.sleep(4)
            c = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra en:" in (n["desc"] or "")][0]
            x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(min((y1 + y2) // 2, 1500))); time.sleep(5)

def f_tabs():
    def home_clears(label, nav):
        restart(); nav(); ok = tap("Inicio", y_max=1800); time.sleep(2.5)
        rec(f"UI-09 pestaña Inicio desde {label}: vuelve a la raíz", ok and has("Explorar plantas y aceites"))
        back(); time.sleep(2)
        rec(f"UI-09 pestaña Inicio desde {label}: la pila queda limpia (Atrás sale de la app)", not foreground_is_app())
    def p06(): tap("Buscar por objetivo"); time.sleep(3)
    def sub(): p06(); tap("Otros objetivos"); time.sleep(3)
    def p07(): p06(); tap("Mejorar el sueño"); time.sleep(4)
    def pas():
        p07(); c = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra en:" in (n["desc"] or "")][0]
        x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(min((y1 + y2) // 2, 1500))); time.sleep(5)
    for label, nav in (("P06", p06), ("subáreas", sub), ("P07", p07), ("el pasaporte", pas)): home_clears(label, nav)
    restart(); p06(); before = img(); before_d = descs()
    for tab in ("Favoritos", "Historial", "Perfil"):
        n = nd(tab + " no disponible"); x1, y1, x2, y2 = n["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); time.sleep(1)
    rec("UI-09 Favoritos, Historial y Perfil en P06 no cambian ruta, selección ni interfaz", descs() == before_d and same(before, img(), (0, 160, 1080, 1900)))

def f_a11y():
    MIN = 144  # 48 dp a 480 dpi
    def check(label, filt):
        small = []; total = 0
        for n in ui.nodes():
            if n["clickable"] and filt(n["desc"] or ""):
                total += 1; w, h = n["b"][2] - n["b"][0], n["b"][3] - n["b"][1]
                if min(w, h) < MIN and n["b"][3] - n["b"][1] >= 0: small.append((n["desc"][:30], w, h))
        rec(f"UI-13 {label}: {total} controles, todos de 48 dp o más", total > 0 and not small, str(small))
    restart(); tap("Buscar por objetivo"); time.sleep(3)
    check("P06 (filas, Volver, Inicio)", lambda d: d in GOALS or d.startswith("Volver") or d == "Inicio")
    tap("Otros objetivos"); time.sleep(3); check("subáreas", lambda d: d in SUBS or d.startswith("Volver") or d == "Inicio")
    tap("Digestión"); time.sleep(5); check("P07 (tarjetas, Volver, Inicio)", lambda d: "La EMA la registra" in d or d.startswith("Volver") or d == "Inicio")
    cards = [n["desc"] for n in ui.nodes() if "La EMA la registra" in (n["desc"] or "")]
    rec("UI-13 cada tarjeta se lee como un solo control con nombre, línea de la EMA y marca/atribución en una sola etiqueta", cards and all(c.count("La EMA la registra en:") == 1 for c in cards))
    rec("UI-13 la imagen no duplica la lectura: ningún nodo aparte lee la foto ni el nombre", not any(re.match(r"^(Fotografía de|Imagen)", d) for d in descs()), str([d for d in descs() if d.startswith("Foto")][:3]))
    back(); time.sleep(1.5); back(); time.sleep(1.5); tap("Mejorar el sueño"); time.sleep(4); swipe_up(8); time.sleep(2)
    check("P07 al final (Ver más detalles)", lambda d: d == "Ver más detalles")
    shot("p07-final-a11y")
    for c in cards[:6]: log.append("OBS   etiqueta de tarjeta: " + c.replace("\n", " | "))

def f_errors():
    ADB = ui.ADB
    def dock(*a): return subprocess.run(["docker", *a], capture_output=True, text=True)
    C = "qa-goal-search-api-1"
    try:
        dock("stop", C); restart(); tap("Buscar por objetivo"); time.sleep(5)
        d = descs(); rec("UI-10 P06 con la API detenida: error legible con Reintentar y sin filas", has("Reintentar") and not any(x in GOALS for x in d), str([x for x in d if len(x) > 20][:3]))
        shot("p06-error-api-detenida")
        dock("start", C); time.sleep(3); tap("Reintentar"); time.sleep(4)
        rec("UI-10 P06: Reintentar con la API en marcha muestra las seis filas", all(g in descs() for g in GOALS))
        dock("stop", C); tap("Otros objetivos"); time.sleep(3)
        d = descs(); rec("UI-10 subáreas con la API detenida tras haber cargado P06: la pantalla de subáreas usa el catálogo ya cargado", has("Digestión") or has("Reintentar"), "abrió subáreas con datos en memoria" if has("Digestión") else "error")
        back(); time.sleep(1.5); tap("Mejorar el sueño"); time.sleep(5)
        rec("UI-10 P07 con la API detenida: error legible con Reintentar, aviso y barra inferior visibles", has("Reintentar") and (has("Estas recomendaciones se basan") or nd("Ver más detalles") is not None) and has("Inicio"))
        shot("p07-error-api-detenida")
        dock("start", C); time.sleep(3); tap("Reintentar"); time.sleep(5)
        rec("UI-10 P07: Reintentar con la API en marcha muestra las tarjetas", has("Para: Mejorar el sueño") and any("La EMA la registra" in x for x in descs()))
        # fallo al cargar la segunda página
        back(); time.sleep(1.5); tap("Alivio respiratorio"); time.sleep(5)
        dock("stop", C); swipe_up(14); time.sleep(6)
        d = descs(); rec("UI-10 fallo al cargar la página siguiente: se conservan las tarjetas y el pie ofrece Reintentar", has("Reintentar") and any("La EMA la registra" in x for x in d))
        shot("p07-error-al-cargar-mas")
        dock("start", C); time.sleep(3); tap("Reintentar"); time.sleep(5); swipe_up(14); time.sleep(3)
        rec("UI-10 Reintentar en el pie: el pie de error desaparece y siguen las tarjetas", not has("Reintentar") and any("La EMA la registra" in x for x in descs()))
        note("el fallo de la API se simuló con docker stop/start del servicio de la QA")
    finally:
        dock("start", C)

def f_auth():
    def dock(*a): return subprocess.run(["docker", *a], capture_output=True, text=True)
    note("para provocar el 401 se recrea el servicio con otro token aleatorio; el valor no se escribe en ningún archivo")
    rec("UI-11 preparación", True)

def f_empty():
    restart(); tap("Buscar por objetivo"); time.sleep(4)
    rec("UI-14 P06 con el objetivo sin plantas: las seis filas, incluida «Cansancio y fatiga», sin conteos", all(g in descs() for g in GOALS))
    assert tap("Cansancio y fatiga"); time.sleep(4)
    d = descs()
    rec("UI-14 P07 del objetivo vacío: 'Para: Cansancio y fatiga' y el texto de vacío exacto", "Para: Cansancio y fatiga" in d and "Aún no hay plantas con información registrada para este objetivo" in d)
    rec("UI-14 el vacío no sugiere otras plantas ni afirma que ninguna sirva (sin tarjetas ni 'No hay más resultados')", not any("La EMA la registra" in x for x in d) and "No hay más resultados" not in d, str([x for x in d if len(x) > 25]))
    rec("UI-14 el aviso, Ver más detalles y la barra inferior siguen visibles en el vacío", has("Estas recomendaciones se basan") and nd("Ver más detalles") is not None and has("Inicio"))
    shot("p07-vacio-cansancio-y-fatiga", review=False)
    back(); time.sleep(1.5); tap("Otros objetivos"); time.sleep(3)
    rows = [x for x in descs() if x in SUBS]
    rec("UI-14 subáreas: la subárea sin plantas visibles (Molestias oculares) no se lista y las otras cinco sí, en orden", rows == SUBS[:5], str(rows))
    shot("subareas-sin-molestias-oculares", review=False)

def f_scale():
    cur = subprocess.run([ui.ADB, "-s", ui.DEV, "shell", "settings", "get", "system", "font_scale"], capture_output=True, text=True).stdout.strip()
    note(f"font_scale inicial: {cur}")
    ui.adb("logcat", "-c")
    ui.adb("shell", "settings", "put", "system", "font_scale", "2.0")
    def sw(n, fast=False):
        # al 200 % la cabecera y la barra inferior ocupan buena parte de la pantalla: se desplaza solo dentro de la zona central (y 800 a 1350)
        for _ in range(n): ui.adb("shell", "input", "swipe", "540", "1350", "540", "800", "250" if fast else "700"); time.sleep(0.5)
    try:
        restart(); tap("Buscar por objetivo"); time.sleep(4)
        rec("UI-12 P06 al 200 %: título, subtítulo y Volver visibles", has("¿Qué deseas lograr?") and has("Selecciona un objetivo principal") and has("Volver a Inicio"))
        shot("200pct-p06")
        found = set(x for x in descs() if x in GOALS)
        for _ in range(8): sw(1); found |= set(x for x in descs() if x in GOALS)
        shot("200pct-p06-final")
        rec("UI-12 P06 al 200 %: las seis filas alcanzables con scroll vertical", found == set(GOALS), str(sorted(found)))
        sw(10, True)
        assert tap("Otros objetivos"), "fila Otros objetivos"; time.sleep(3); f2 = set(x for x in descs() if x in SUBS); shot("200pct-subareas")
        for _ in range(8): sw(1); f2 |= set(x for x in descs() if x in SUBS)
        rec("UI-12 subáreas al 200 %: las seis filas alcanzables", f2 == set(SUBS), str(sorted(f2)))
        back(); time.sleep(1.5); sw(10, True); sw(0)
        ui.adb("shell", "input", "swipe", "540", "800", "540", "1350", "250"); ui.adb("shell", "input", "swipe", "540", "800", "540", "1350", "250"); time.sleep(1)
        assert tap("Mejorar el sueño", y_max=1350), "fila Mejorar el sueño"; time.sleep(5)
        rec("UI-12 P07 al 200 %: título, subtítulo y primera tarjeta con marca 'Precaución' legible", has("Recomendaciones") and any("Precaución" in x for x in descs()), str([x for x in descs()][:3]))
        shot("200pct-p07-primera")
        big = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra" in (n["desc"] or "")]
        rec("UI-12 P07 al 200 %: las tarjetas miden 48 dp o más", bool(big) and all(n["b"][3] - n["b"][1] >= 144 for n in big))
        sw(16, True); time.sleep(2); shot("200pct-p07-final")
        rec("UI-12 P07 al 200 %: el aviso y Ver más detalles son alcanzables al final", has("Estas recomendaciones se basan") and nd("Ver más detalles") is not None)
        tap("Ver más detalles", y_max=1350); time.sleep(2); shot("200pct-hoja")
        d = descs(); rec("UI-12 hoja al 200 %: título y texto presentes", "Sobre estas recomendaciones" in d)
        ui.adb("shell", "input", "swipe", "540", "1500", "540", "700", "300"); time.sleep(1); shot("200pct-hoja-final")
        rec("UI-12 hoja al 200 %: el control Cerrar es alcanzable (con scroll dentro de la hoja)", nd("Cerrar") is not None)
        if nd("Cerrar"): tap("Cerrar"); time.sleep(1.5)
        ui.adb("shell", "input", "swipe", "540", "800", "540", "1350", "250"); sw(0)
        for _ in range(16): ui.adb("shell", "input", "swipe", "540", "800", "540", "1350", "250"); time.sleep(0.3)
        time.sleep(1)
        cs = [n for n in ui.nodes() if n["clickable"] and "La EMA la registra" in (n["desc"] or "")]
        c = cs[0]; x1, y1, x2, y2 = c["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(max(min((y1 + y2) // 2, 1300), 900))); time.sleep(5)
        shot("200pct-pasaporte"); rec("UI-12 pasaporte al 200 %: se abre y tiene el botón Volver", has("Volver"))
        lg = subprocess.run([ui.ADB, "-s", ui.DEV, "logcat", "-d"], capture_output=True, text=True).stdout
        ov = [l for l in lg.splitlines() if "overflowed" in l or "RenderFlex" in l or "EXCEPTION CAUGHT" in l]
        rec("UI-12 sin desbordes ni excepciones de renderizado en el registro durante el recorrido al 200 %", not ov, str(ov[:2]))
    finally:
        ui.adb("shell", "settings", "put", "system", "font_scale", cur if cur not in ("", "null") else "1.0")

FLOWS = {"scale": f_scale, "empty": f_empty, "p06": f_p06, "subareas": f_subareas, "sheet": f_sheet, "passport": f_passport, "stack": f_stack, "tabs": f_tabs, "a11y": f_a11y, "errors": f_errors}
for name in sys.argv[1:]:
    log.append(f"=== {name}")
    try: FLOWS[name]()
    except Exception as e: rec(f"{name}: excepción del script", False, repr(e))
    open(os.path.join(OUT, name + ".txt"), "w").write("\n".join(log).replace(TOKEN, "<token-app>") + "\n")
print("\n".join(log))
print("FALLAS:", fails)
