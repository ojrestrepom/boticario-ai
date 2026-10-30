#!/usr/bin/env python3
"""6.3 y 6.4: recorre en el emulador (emulator-5556, nunca el telefono fisico) la lista P07 de un objetivo o subarea,
la desplaza hasta el final, y compara cada tarjeta con lo que dice la API.
Uso: ui_goal_lists.py <etiqueta> [<subarea>]      (etiqueta = id del objetivo; subarea solo con otros-objetivos)
Entorno: QA_TOKEN (solo para pedir la API local desde el Mac), QA_BASE, QA_PYLIB (carpeta con Pillow, fuera del proyecto).
Salida: evidence/app/lists/<etiqueta>[-<subarea>].json y .txt, y capturas del primer pantallazo y del final.
No usa Playwright (la app es nativa Android).
"""
import collections, io, json, os, sys, time, urllib.request
sys.path.insert(0, os.environ["QA_PYLIB"])
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080"); TOKEN = os.environ["QA_TOKEN"]
goal = sys.argv[1]; sub = sys.argv[2] if len(sys.argv) > 2 else None
label = goal + ("-" + sub if sub else "")
OUT = os.path.join(ui.EV, os.environ.get("QA_LISTS_DIR", "lists")); os.makedirs(OUT, exist_ok=True)
GOAL_ROW = {"relajacion-estres": "Relajación / Estrés", "mejorar-el-sueno": "Mejorar el sueño", "cuidado-de-la-piel": "Cuidado de la piel",
            "alivio-respiratorio": "Alivio respiratorio", "cansancio-y-fatiga": "Cansancio y fatiga", "otros-objetivos": "Otros objetivos"}
SUB_ROW = {"digestion": "Digestión", "vias-urinarias-y-genitales": "Vías urinarias y genitales", "dolor-e-inflamacion": "Dolor e inflamación",
           "boca-y-garganta": "Boca y garganta", "circulacion": "Circulación", "molestias-oculares": "Molestias oculares"}

def api(path):
    rq = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read())

def expected():
    items = []; off = 0
    while True:
        j = api(f"/v1/goals/{goal}/plants?limit=100&offset={off}" + (f"&subarea={sub}" if sub else ""))
        items += j["items"]
        if len(j["items"]) < 100: return j, items
        off += 100

def card_text(i):
    primary = i["displayName"] or i["scientificName"]
    lines = [primary]
    if primary != i["scientificName"]: lines.append(i["scientificName"])
    a = i["areas"]; more = len(a) - 2
    lines.append("La EMA la registra en: " + ", ".join(a[:2]) + (f" y {more} más" if more > 0 else ""))
    if i["safetyLevel"] in ("alto", "medio"): lines.append("Precaución")
    elif not i["hasSafety"]: lines.append("Sin datos de precauciones (esto no significa que sea segura)")
    return "\n".join(lines)

def screen():
    png = ui.adb("exec-out", "screencap", "-p", out=True)
    return Image.open(io.BytesIO(png)).convert("L"), png

def photo_kind(img, b):
    """Clasifica la region de la miniatura de una tarjeta. El arte local es un fondo plano (gris 240 tras la conversion) con un icono:
    si al menos el 80 % de los pixeles de la region tiene ese gris es 'arte'; si no, 'foto'. Devuelve (tipo, fraccion plana)."""
    x1, y1, x2, y2 = b
    reg = img.crop((x1 + 40, y1 + 40, x2 - 40, y1 + 40 + 330))
    px = list(reg.getdata())
    flat = sum(1 for p in px if 238 <= p <= 242) / len(px)
    return ("arte" if flat >= 0.8 else "foto"), round(flat, 2)

def is_card(n): return n["clickable"] and "La EMA la registra en:" in (n["desc"] or "")

def go_to_list():
    ui.tap("Buscar por objetivo") if ui.find("Buscar por objetivo") and not ui.find("¿Qué deseas lograr?") else None
    time.sleep(2.5)
    assert ui.find("¿Qué deseas lograr?"), "no se llego a P06"
    n = next(x for x in ui.nodes() if (x["desc"] or "") == GOAL_ROW[goal] and x["clickable"])
    x1, y1, x2, y2 = n["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str(min((y1 + y2) // 2, 1640)))
    time.sleep(2.5)
    if sub:
        assert ui.find("Otros objetivos"), "no se abrio la pantalla de subareas"
        n = next(x for x in ui.nodes() if (x["desc"] or "") == SUB_ROW[sub] and x["clickable"])
        x1, y1, x2, y2 = n["b"]; ui.adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)); time.sleep(3)

DWELL = float(os.environ.get("QA_DWELL", "1.5"))

def run():
    meta, items = expected()
    go_to_list()
    time.sleep(3.5)  # miniaturas de la primera pantalla
    ui.shot(f"{os.path.basename(OUT)}/{label}-primera")
    title = [n["desc"] for n in ui.nodes() if n["desc"] and (n["desc"].startswith("Para:") or n["desc"] == "Recomendaciones")]
    cards = collections.OrderedDict()   # texto de la tarjeta sin credito -> estado
    end_seen = False; loading_seen = False; steps = 0
    while steps < 260:
        steps += 1
        time.sleep(DWELL)
        n1 = ui.nodes(); img, _ = screen(); n2 = ui.nodes()
        stable = {x["desc"]: x["b"] for x in n2 if is_card(x)}
        for n in n1:
            d = n["desc"] or ""
            if "Cargando más" in d: loading_seen = True
            if not is_card(n): continue
            lines = d.split("\n"); credit = lines[0] if lines[0].startswith("Foto:") else None
            text = "\n".join(lines[1:] if credit else lines)
            c = cards.setdefault(text, {"credito": None, "n_arte": 0, "n_foto": 0, "clasificada": False})
            if credit: c["credito"] = credit
            if stable.get(d) == n["b"] and n["b"][1] + 40 >= 160 and n["b"][1] + 40 + 330 <= 1670:
                kind, flat = photo_kind(img, n["b"]); c["clasificada"] = True
                c["n_arte" if kind == "arte" else "n_foto"] += 1
        if any((n["desc"] or "") == "No hay más resultados" for n in n1):
            end_seen = True; break
        ui.adb("shell", "input", "swipe", "540", "1650", "540", "550", "1500")  # lento: sin impulso que salte tarjetas
    time.sleep(1)
    for _ in range(3): ui.adb("shell", "input", "swipe", "540", "1650", "540", "550", "1500"); time.sleep(0.5)
    time.sleep(1.5); ui.shot(f"{os.path.basename(OUT)}/{label}-final")
    end_texts = [n["desc"] for n in ui.nodes() if n["desc"]]
    got_texts = list(cards.keys()); exp_texts = [card_text(i) for i in items]
    problems = []
    if got_texts != exp_texts:
        for k, (g, e) in enumerate(zip(got_texts, exp_texts)):
            if g != e: problems.append(f"tarjeta {k + 1}: UI {g!r} != API {e!r}"); break
        if len(got_texts) != len(exp_texts): problems.append(f"la UI muestra {len(got_texts)} tarjetas y la API {len(exp_texts)}")
    st = collections.Counter(); detail = []
    for i, t in zip(items, exp_texts):
        c = cards.get(t)
        if c is None: st["no vista"] += 1; continue
        c["foto_sin_credito"] = c["n_foto"] > 0 and c["n_arte"] == 0 and not c["credito"]   # solo si todas las observaciones dicen 'foto'
        c["arte_con_credito"] = c["n_arte"] > 0 and c["n_foto"] == 0 and bool(c["credito"])
        want = f"Foto: {i['image']['author'] or 'autor no disponible'} · {i['image']['license']}" if i["image"] else None
        if want is None:
            st["sin imagen en la API: arte local sin credito" if not c["credito"] and not c["foto_sin_credito"] else "ERROR sin imagen en la API pero con credito o foto"] += 1
            if c["credito"] or c["foto_sin_credito"]: detail.append(f"{i['id']}: sin imagen en la API pero se ve credito o foto")
        elif c["credito"]:
            if c["credito"] != want: st["ERROR credito distinto del de la API"] += 1; detail.append(f"{i['id']}: {c['credito']!r} != {want!r}")
            elif c.get("arte_con_credito"): st["ERROR credito con arte local"] += 1; detail.append(f"{i['id']}: credito con arte local")
            else: st["foto con credito correcto"] += 1
        elif c["foto_sin_credito"]: st["ERROR foto sin credito"] += 1; detail.append(f"{i['id']}: foto sin credito")
        else: st["imagen en la API que no cargo: arte local sin credito"] += 1; detail.append(f"{i['id']}: la miniatura no cargo (arte local, sin credito)")
    res = {"lista": label, "subtitulo_ui": title, "api_total": meta["total"], "tarjetas_ui": len(cards), "fin_de_lista": end_seen, "pie_de_carga_visto": loading_seen,
           "texto_igual_a_la_api_y_mismo_orden": got_texts == exp_texts, "problemas_de_texto": problems, "estado_de_imagenes": dict(st), "detalle_imagenes": detail,
           "sin_clasificar": sum(1 for c in cards.values() if not c["clasificada"]),
           "final": [t for t in end_texts if t in ("No hay más resultados", "Ver más detalles") or t.startswith("Estas recomendaciones")]}
    json.dump(res, open(os.path.join(OUT, label + ".json"), "w"), ensure_ascii=False, indent=1)
    json.dump([{"tarjeta": t, **c} for t, c in cards.items()], open(os.path.join(OUT, label + "-tarjetas.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "detalle_imagenes"}, ensure_ascii=False, indent=1)); print(len(detail), "detalles de imagen")
    for _ in range(4):  # vuelve a P06 con Atras del sistema
        if ui.find("¿Qué deseas lograr?"): break
        ui.adb("shell", "input", "keyevent", "4"); time.sleep(1.5)

run()
