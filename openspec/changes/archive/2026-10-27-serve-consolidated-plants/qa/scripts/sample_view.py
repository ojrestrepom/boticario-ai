#!/usr/bin/env python3 -I
"""11.4: vista legible de la muestra de 30 plantas segun la API (la misma muestra del cambio 1, tarea 10.5) y chequeos por planta.
Entorno: QA_TOKEN, QA_BASE (por defecto http://127.0.0.1:8080). Uso: sample_view.py <carpeta de evidencia>
Escribe sample-30-view.txt (texto servido, una seccion por planta) y sample-30-checks.tsv.
"""
import json, os, pathlib, re, sys, urllib.request, urllib.error
EV = pathlib.Path(sys.argv[1]); EV.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("QA_BASE", "http://127.0.0.1:8080"); TOKEN = os.environ["QA_TOKEN"]
SAMPLE = {
    "piloto": ["lavandula-angustifolia", "matricaria-chamomilla", "mentha-x-piperita", "hypericum-perforatum", "citrus-x-bergamia", "prunus-amygdalus"],
    "toxicas-tppt": ["conium-maculatum", "ricinus-communis", "datura-stramonium", "aconitum-napellus", "abrus-precatorius"],
    "solo-genero": ["aloe-spp", "crataegus-sp", "ephedra-spp"],
    "separadas-por-colision": ["citrus-x-paradisi", "brassica-oleracea-var-italica", "foeniculum-vulgare-var-dulce"],
    "fusionadas-por-colision": ["cinnamomum-verum", "ocimum-tenuiflorum"],
    "ema-fuera-de-usda": ["pelargonium-sidoides", "rhodiola-rosea", "tilia-cordata"],
    "fase-2-al-azar": ["oryza-sativa", "cinnamomum-burmanni", "abutilon-theophrasti", "malus-domestica", "zygophyllum-creticum", "myrciaria-dubia"],
    "fase-2-con-actividad-sensible": ["platycodon-grandiflorus", "geissospermum-laeve"],
}
def get(p):
    r = urllib.request.Request(BASE + p, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        x = urllib.request.urlopen(r, timeout=30); return x.status, json.loads(x.read()), x.headers
    except urllib.error.HTTPError as e: return e.code, None, e.headers
EFFECT = re.compile(r"\b(cura|curar|curativ\w*|calma|calmar|alivia|aliviar|ayuda a|previene|prevenir|trata|tratar|elimina|sana|mejora|reduce|combate|fortalece|eficaz|efectivo|garantiza)\b", re.I)
DOSE = re.compile(r"\d+([.,]\d+)?\s*(mg|g|kg|ml|µg|mcg|gotas?|cucharad\w+|tazas?|veces)\b|\bdosis\b|\bposolog", re.I)
SAFE = re.compile(r"\b(segur[ao]s?|inocu[ao]s?|sin riesgos?|no (es )?tóxic[ao])\b", re.I)
SENS = re.compile(r"c[aá]ncer|tumor|diabetes|malaria|sida|vih|aborti\w*|embarazo|hipertensi\w*|epilep\w*|lepra|tuberculosis|ictericia|asma|esquizofren\w*", re.I)
view = []; rows = ["grupo\tplanta\tdisplayName\tgrupos_servidos\tsin_resolver\tobjetivos\tsafety_level\timagen\tcc_sin_autor_o_pagina\tcreditos\talias_resuelven\tefecto\tdosis\tseguro\tactividades_sensibles"]
for grp, ids in SAMPLE.items():
    for pid in ids:
        st, d, _ = get(f"/v1/plants/{pid}")
        if st != 200: view.append(f"## {pid}  [{grp}]\nHTTP {st}\n"); rows.append(f"{grp}\t{pid}\tHTTP {st}"); continue
        L = [f"## {pid}  [{grp}]", f"displayName: {d['displayName']} | cientifico: {d['scientificName']} | familia: {d['family']}",
             f"sinonimos: {', '.join(d['synonyms']) or '-'}", f"origen: {d['origin']}", f"aceite: {d['oil']}", f"descripcion: {d['description']}",
             f"partes: {', '.join(p['label'] for p in d['parts']) or '-'}",
             "comunes: " + "; ".join(f"{n['text']} ({n['language']})" for n in d["names"] if n["kind"] == "common")]
        L.append("objetivos EMA: " + (" | ".join(f"{g['name']}{' / ' + g['subarea'] if g['subarea'] else ''} [{g['area']}] ({g['evidence']})" for g in d["goals"]) or "-"))
        s = d["safety"]; L.append("precauciones: " + ("null" if s is None else f"nivel={s['level']} :: {s['text']} :: citas={'; '.join(r['citation'] for r in s['references'])}"))
        unres = 0
        L.append(f"grupos de uso ({len(d['useGroups'])}):")
        for g in d["useGroups"]:
            rr = []
            for r in g["references"]:
                if not r["resolved"]: unres += 1
                rr.append(r["citation"])
            L.append(f"  - {g['activity']} [{g['count']} reg.; {', '.join(g['countries']) or 'sin paises'}] <- " + " || ".join(rr))
        im = d["image"]; L.append("imagen: " + ("null" if im is None else f"{im['license']} | autor={im['author']} | pagina={im['pageUrl']} | licenseUrl={im['licenseUrl']} | attributionRequired={im['attributionRequired']}"))
        L.append("creditos: " + "; ".join(f"{c['name']} [{c['license']}; {c['licenseUrl']}; {c['url']}]" for c in d["credits"]))
        # alias de la planta: ids anteriores que resuelven (los conocemos por el cambio 1 solo via busqueda; aqui solo el propio id)
        view.append("\n".join(L) + "\n")
        texts = [d["description"] or "", d["origin"] or "", s["text"] if s else ""] + [g["activity"] for g in d["useGroups"]] + [f"{g['name']} {g['area']} {g['evidence']}" for g in d["goals"]]
        T = " \n ".join(texts)
        cc_bad = bool(im and im["license"].upper().startswith("CC BY") and (not (im["author"] or "").strip() or not im["pageUrl"]))
        sens = sorted({m.group(0).lower() for g in d["useGroups"] for m in [SENS.search(g["activity"])] if m} | {m.group(0).lower() for m in [SENS.search(s["text"] if s else "")] if m})
        rows.append("\t".join(map(str, [grp, pid, d["displayName"], len(d["useGroups"]), unres, len(d["goals"]), s["level"] if s else "sin-safety", im["license"] if im else "sin-imagen", cc_bad, len(d["credits"]), "-",
                                         ",".join(sorted({m.group(0).lower() for m in EFFECT.finditer(T)})) or "-", ",".join(sorted({m.group(0).lower() for m in DOSE.finditer(T)})) or "-", ",".join(sorted({m.group(0).lower() for m in SAFE.finditer(T)})) or "-", ",".join(sens) or "-"])))
(EV / "sample-30-view.txt").write_text("\n".join(view).replace(TOKEN, "<token-app>"), encoding="utf-8")
(EV / "sample-30-checks.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
print(len(rows) - 1, "plantas")
