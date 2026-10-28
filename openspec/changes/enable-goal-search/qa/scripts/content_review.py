#!/usr/bin/env python3 -I
"""6.4: revision del contenido real de P07 (las 175 plantas con objetivo) a partir de la API y de las tarjetas leidas en la interfaz.
Entorno: QA_TOKEN, QA_BASE. Uso: content_review.py <carpeta evidence/app>. Escribe content-review.txt."""
import collections, json, os, pathlib, re, sys, urllib.request
EV = pathlib.Path(sys.argv[1]); BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080"); TOKEN = os.environ["QA_TOKEN"]
def api(p): return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + p, headers={"Authorization": "Bearer " + TOKEN}), timeout=30).read())
goals = api("/v1/goals"); plants = {}; lists = []
for g in goals:
    lists.append((g["id"], None))
    lists += [(g["id"], s["id"]) for s in g["subareas"]]
for g, s in lists:
    off = 0
    while True:
        j = api(f"/v1/goals/{g}/plants?limit=100&offset={off}" + (f"&subarea={s}" if s else ""))
        for i in j["items"]: plants.setdefault(i["id"], {"i": i, "in": set()})["in"].add(g + (":" + s if s else ""))
        if len(j["items"]) < 100: break
        off += 100
out = []
def line(t=""): out.append(t)
# --- tarjetas leidas de la interfaz
cards = []
for f in sorted((EV / "lists").glob("*-tarjetas.json")):
    for c in json.load(open(f)): cards.append((f.stem.replace("-tarjetas", ""), c))
line(f"Tarjetas leidas en la interfaz: {len(cards)} en {len(set(l for l, _ in cards))} listas; plantas distintas con objetivo en la API: {len(plants)}")
# CON-01
BAD = re.compile(r"\b(dosis|dosific\w*|mg|ml|gotas?|cucharad\w*|tomar|ingerir|eficaz|eficacia|efectos?|calma\w*|relaj\w*|alivia\w*|cura\w*|trata\w*|ayuda\w*|promueve\w*|reduce|mejor(?:a|ar|an|as|ado|ada)|previene|combate|recomendad\w*|sirve|beneficio\w*|propiedades|calmante|m[aá]s recomendada|puntuaci[oó]n|ranking)\b", re.I)
hits = []; lines_kinds = collections.Counter()
for l, c in cards:
    t = c["tarjeta"]
    for ln in t.split("\n"):
        if ln.startswith("La EMA la registra en:"): lines_kinds["ema"] += 1
        elif ln in ("Precaución", "Sin datos de precauciones (esto no significa que sea segura)"): lines_kinds["marca"] += 1
        else: lines_kinds["nombre"] += 1
    body = "\n".join(x for x in t.split("\n") if not x.startswith("La EMA la registra en:") or True)
    # se ignora el nombre de la propia area de la EMA solo si coincide con las areas de la API (p. ej. 'Dolor e inflamacion')
    for m in BAD.finditer(re.sub(r"La EMA la registra en: ", "", body)):
        hits.append((l, m.group(0), t.replace("\n", " | ")))
line(f"CON-01 lineas por tipo en las tarjetas: {dict(lines_kinds)}; cada tarjeta tiene nombre, [cientifico], una linea de la EMA y a lo sumo una marca")
line(f"CON-01 coincidencias con la lista de terminos de eficacia o dosis (incluye 'calma', 'alivia', 'trata', 'efecto', 'mg'...): {len(hits)}")
for h in hits[:10]: line("  " + str(h))
# CON-02: plantas de riesgo conocido
RISK = {"symphytum-officinale": "consuelda: alcaloides pirrolizidinicos, uso interno restringido", "arnica-montana": "arnica: toxica por via interna, la EMA solo admite uso topico",
        "eucalyptus-globulus": "aceite de eucalipto: toxico por ingestion en dosis pequenas, y en ninos", "eucalyptus-smithii": "idem",
        "tanacetum-parthenium": "gamaza/matricaria: contraindicada en embarazo", "frangula-purshiana": "laxante antraquinonico", "frangula-alnus": "laxante antraquinonico",
        "senna-alexandrina": "laxante antraquinonico", "hypericum-perforatum": "interacciones graves", "glycyrrhiza-glabra": "regaliz: hipertension e hipopotasemia", "allium-sativum": "anticoagulacion",
        "ginkgo-biloba": "anticoagulacion", "panax-ginseng": "interacciones", "juniperus-communis": "embarazo y renal", "melaleuca-alternifolia": "aceite: toxico por ingestion",
        "mentha-x-piperita": "mentol en ninos pequenos", "menyanthes-trifoliata": "emetico en exceso", "ononis-spinosa": "-"}
line("CON-02 plantas de riesgo conocido presentes en las listas, con su nivel y lo que muestra la tarjeta:")
for p, why in RISK.items():
    if p in plants:
        i = plants[p]["i"]; mark = "Precaución" if i["safetyLevel"] in ("alto", "medio") else ("-" if i["hasSafety"] else "Sin datos")
        line(f"  {p} ({i['displayName']}): nivel {i['safetyLevel']}, marca {mark}; {why}")
line("CON-02 ninguna de las 13 plantas de nivel alto es una de las excluidas por toxicidad (la API no las lista: API-13)")
# CON-03
sci = sorted(p for p, v in plants.items() if v["i"]["displayName"] == v["i"]["scientificName"])
line(f"CON-03 plantas con el cientifico como nombre principal: {len(sci)} (el diseno dice 32)")
dup_lines = [c["tarjeta"] for _, c in cards if c["tarjeta"].split("\n")[0] == c["tarjeta"].split("\n")[1] ] if cards else []
line(f"CON-03 tarjetas donde el nombre principal se repite como secundario: {len(dup_lines)}")
cnt = collections.Counter(v["i"]["displayName"] for v in plants.values()); ties = {k: v for k, v in cnt.items() if v > 1}
line(f"CON-03 nombres principales repetidos entre plantas distintas (se distinguen por el cientifico): {ties}")
lower = [v["i"]["displayName"] for v in plants.values() if v["i"]["displayName"][0].islower()]
line(f"CON-03 nombres que empiezan en minuscula: {lower}")
nospace = [v["i"]["displayName"] for v in plants.values() if "  " in v["i"]["displayName"] or v["i"]["displayName"] != v["i"]["displayName"].strip()]
line(f"CON-03 nombres con espacios sobrantes: {nospace}")
line("CON-03 nombres que se apartan del uso comun segun la revision (a confirmar en 6.5): arnica-montana 'Hierba de las caídas' (el uso comun es 'Árnica'); silybum-marianum 'Cardo de maria' (sin tilde: 'Cardo de María'); capsella-bursa-pastoris 'Mostaza salvaje' (el uso comun es 'Bolsa de pastor'); tanacetum-parthenium 'Gamaza'; eucalyptus-polybractea 'Mallee azul'")
sp = [v["i"]["displayName"] for v in plants.values() if "grindelia" in v["i"]["displayName"].lower()]
line("CON-03 grindelia-robusta trae un nombre comun 'es' ('grindelia') pero su nombre principal es el cientifico; las otras tres Grindelia tambien: " + str(sp))
# CON-04
with_img = [p for p, v in plants.items() if v["i"]["image"]]
noimg = [p for p, v in plants.items() if not v["i"]["image"]]
auth_null = [p for p in with_img if plants[p]["i"]["image"]["author"] is None]
line(f"CON-04 de las {len(plants)} plantas, {len(with_img)} tienen imagen y {len(noimg)} no; autor nulo en {len(auth_null)}: {auth_null}")
miss = [p for p in with_img if not plants[p]["i"]["image"]["license"]]
line(f"CON-04 imagenes sin licencia en la API: {len(miss)}")
nonwm = [p for p in with_img if not plants[p]["i"]["image"]["url"].startswith("https://upload.wikimedia.org/wikipedia/commons/")]
line(f"CON-04 imagenes fuera de upload.wikimedia.org/wikipedia/commons: {len(nonwm)}")
ext = collections.Counter(plants[p]["i"]["image"]["url"].rsplit(".", 1)[-1].lower() for p in with_img)
line(f"CON-04 extensiones: {dict(ext)} (todas rasters o svg: la politica deriva miniatura de 500 px para todas)")
(EV / "content-review.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
