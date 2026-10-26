"""Barridos sobre los 2.354 registros que respaldan los patrones del informe de la tarea 10.5.

Uso: python3 global_scans.py [--out DIR]   (sin --out imprime todo; con --out escribe un archivo por barrido)
Solo lee data/seed/plants y data/work/bundles.
"""
import json, glob, re, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cr_lib import ROOT, GRAVE, RISK, PREFIX, base, texts, norm

PLANTS = sorted(Path(f).stem for f in glob.glob(ROOT + "data/seed/plants/*.json"))
_cache = {}
def rec(i):
    if ("r", i) not in _cache:
        _cache[("r", i)] = json.load(open(ROOT + f"data/seed/plants/{i}.json"))
        _cache[("b", i)] = json.load(open(ROOT + f"data/work/bundles/{i}.json"))
    return _cache[("r", i)], _cache[("b", i)]

def scan_nas():
    """Claves «Nas»: la candidata NAS (Lost Crops of the Incas) frente a NAS2 (Herbal pharmacology in the PRC)."""
    out, per, countries = [], collections.defaultdict(list), collections.defaultdict(collections.Counter)
    tot = collections.Counter()
    for i in PLANTS:
        r, b = rec(i)
        bu = {u["activity"]: u for u in b["sections"]["uses"]}
        for n, u in enumerate(r["traditionalUses"]):
            for c in u["citations"]:
                if c["key"] == "Nas":
                    tot[c["ref"]] += 1
                    per[c["ref"]].append((i, n, u["activitySource"]))
                    for co in bu[u["activitySource"]]["countries"]:
                        countries[c["ref"]][co] += 1
    out.append("grupos por ref elegido: " + json.dumps(dict(tot), ensure_ascii=False))
    for ref in ("usda_reference:NAS", "usda_reference:NAS2", None):
        out.append(f"-- {ref}: países de las filas {countries[ref].most_common(12)}")
    plants = collections.Counter(i for i, n, a in per["usda_reference:NAS"])
    out.append("plantas con NAS (Lost Crops of the Incas): " + json.dumps(dict(plants), ensure_ascii=False))
    out.append("plantas con Nas sin resolver: " + json.dumps(sorted({i for i, n, a in per[None]})))
    return out

def scan_veterinary():
    """Señales de riesgo y enfermedades graves con calificador (Veterinary): cómo quedan en el registro."""
    out = []
    for i in PLANTS:
        r, b = rec(i)
        vs = [u["activity"] for u in b["sections"]["uses"] if "Veterinary" in u["activity"] and base(u["activity"]) in RISK]
        if vs:
            t = (r["safety"] or {}).get("text", "")
            out.append(f"{i}: {vs} | safety: ...{t[-330:]}")
    return out

def scan_units():
    """Cantidades, unidades y posología en todo el texto visible."""
    Q = re.compile(r"(\d[\d.,]*\s*(?:µg|μg|ug|mg|g|kg|ml|l|%|por ciento|veces|gotas|cucharad\w*|tazas?)\b)|\b(?:µg|μg|mg|kg)\b|\bal d[ií]a\b|\bpor d[ií]a\b|\bdiari[oa]s?\b|\btazas?\b|\bcucharad\w*|\bdosis\b|\bposolog\w*|\bdosific\w*|\bgotas\b", re.I)
    out = []
    for i in PLANTS:
        r, b = rec(i)
        for p, t in texts(r):
            if p.endswith("cit"):
                continue
            for m in Q.finditer(t):
                if re.match(r"\d+\s*(años|meses)", m.group(0)):
                    continue
                out.append(f"{i} {p}: «{m.group(0)}» ...{t[max(0, m.start()-60):m.end()+60]}...")
    return out

def scan_malformed_formula():
    out = []
    for i in PLANTS:
        r, b = rec(i)
        for n, u in enumerate(r["traditionalUses"]):
            a = u["activity"]
            if re.search(r'["«»“”]|  |^\s|\s$', a):
                out.append(f"{i} traditionalUses[{n}]: {a!r} <= {u['activitySource']}")
    return out

def scan_empty_uses():
    out = []
    for i in PLANTS:
        r, b = rec(i)
        us = [u for u in b["sections"]["uses"] if base(u["activity"]) not in RISK]
        if us and len(r["traditionalUses"]) < min(20, len(us)):
            have = {u["activitySource"] for u in r["traditionalUses"]}
            out.append(f"{i}: paquete {len(us)} grupos no riesgo, registro {len(r['traditionalUses'])}; faltan {[u['activity'] for u in us if u['activity'] not in have][:4]}")
    return out

def scan_images():
    pats = {
        "fuente-wikipedia": re.compile(r"original uploader|uploader was", re.I),
        "unknown/anonymous": re.compile(r"unknown|anonymous", re.I),
        "url": re.compile(r"https?://|www\.", re.I),
        "photo-by/(c)": re.compile(r"photo by|\(c\)|©|location credit|taken by|picture taken", re.I),
        "transferred": re.compile(r"transferred from", re.I),
        "own-work": re.compile(r"own work", re.I),
        "largo>=150": re.compile(r".{150,}"),
        "email/galería": re.compile(r"email the author|personal gallery", re.I),
    }
    res = collections.defaultdict(list)
    svg = []
    for i in PLANTS:
        r, b = rec(i)
        im = r.get("image")
        if not im:
            continue
        if im["url"].lower().endswith(".svg"):
            svg.append(i)
        for k, p in pats.items():
            if im["author"] and p.search(im["author"]):
                res[k].append(i)
    out = [f"{k}: {len(v)} {v}" for k, v in res.items()]
    out.append(f"imágenes SVG: {svg}")
    return out

def scan_origin():
    c = collections.Counter(); ex = collections.defaultdict(list)
    for i in PLANTS:
        r, b = rec(i)
        o = r["origin"]
        if not o:
            continue
        v = o["value"]
        c["con origen"] += 1
        c["termina en punto" if v.endswith(".") else "sin punto final"] += 1
        m = re.match(r"(Región nativa:|Nativa del?)", v)
        if m: c["prefijo " + m.group(1)] += 1
        if "Malasia" in v: c["Malasia (WCVP dice Malesia)"] += 1; ex["Malasia"].append(i)
        if "Malesia" in v: c["Malesia"] += 1
    return [json.dumps(dict(c), ensure_ascii=False), "ejemplos Malasia: " + json.dumps(ex["Malasia"][:50])]

def scan_safety_meta():
    P = re.compile(r"(no fij\w+|ninguna fij\w+|sin que fij\w+|sin fijar|fijen|sin nivel|nivel de (riesgo|preocupación|seguridad)|nivel asignado)", re.I)
    out = []
    eng = []
    for i in PLANTS:
        r, b = rec(i)
        t = (r["safety"] or {}).get("text", "")
        if P.search(t): out.append(f"{i}: ...{t[max(0, P.search(t).start()-50):P.search(t).end()+40]}...")
        for m in re.finditer(r"«(?:very strong toxic|strong toxic|nontoxic|toxic)»", t): eng.append(f"{i}: {m.group(0)}")
    return [f"texto de seguridad con lógica interna: {len(out)}"] + out + ["", f"categorías TPPT en inglés: {len(eng)}"] + eng

def scan_lethal_levels():
    c = collections.Counter(); ex = collections.defaultdict(list)
    for i in PLANTS:
        r, b = rec(i)
        bases = {base(u["activity"]) for u in b["sections"]["uses"] if base(u["activity"]) in RISK}
        if not bases: continue
        lethal = bool(bases & {"fatality", "fatal", "death", "suicide", "homicide"})
        lv = (r["safety"] or {}).get("level")
        k = ("señal letal (Fatality/Fatal/Death/Suicide/Homicide)" if lethal else "otras señales de riesgo", str(lv))
        c[k] += 1; ex[k].append(i)
    return [f"{k}: {v}  ej. {ex[k][:8]}" for k, v in sorted(c.items())]

def scan_untranslated():
    eng = {"Fumitory", "Aperient", "Gravel", "Ague", "Antivinous", "Decoagulant", "Bilious", "Carbuncle", "Corn", "Boil", "Sore", "Canker", "Flux", "Gripes", "Labor", "Hemostat", "Blood", "Anodyne", "Alexiteric", "Eczema", "Side", "Bot", "Charm", "Funeral", "Scurf", "Pocks", "Maggot", "Cowitch", "Chewstick"}
    c = collections.Counter(); recs = set()
    for i in PLANTS:
        r, b = rec(i)
        for u in r["traditionalUses"]:
            if u["activity"] == u["activitySource"] and u["activitySource"] in eng:
                c[u["activitySource"]] += 1; recs.add(i)
    return [f"grupos sin traducir: {sum(c.values())} en {len(recs)} registros", json.dumps(dict(c.most_common()), ensure_ascii=False)]

def scan_activity_variants():
    m = collections.defaultdict(collections.Counter)
    for i in PLANTS:
        r, b = rec(i)
        for u in r["traditionalUses"]:
            m[u["activitySource"]][u["activity"]] += 1
    multi = {k: dict(v) for k, v in m.items() if len(v) > 1}
    out = [f"actividades de USDA con más de una traducción: {len(multi)} de {len(m)}"]
    for k, v in sorted(multi.items(), key=lambda x: -sum(x[1].values()))[:40]:
        out.append(f"{k}: {v}")
    return out

def scan_descriptions_health():
    P = re.compile(r"medicin\w+|propiedades|salud|terap\w+|farmac\w+", re.I)
    out = []
    for i in PLANTS:
        r, b = rec(i)
        d = r["description"]
        if d and P.search(d["value"]):
            out.append(f"{i}: {d['value'][:200]}")
    return [f"descripciones con medicinal/medicina/propiedades/salud/farmacéutica: {len(out)}"] + out

def scan_name_annotations():
    P = re.compile(r"\((?:Sp|Ger|Fr|Jap|Port|Ital|Eng|Peru|Bol|Chin|Pinyin|Zulu|Chinese)\.?[;,)]|\([A-Za-z.,; ]+\)\s*$")
    out = []
    for i in PLANTS:
        r, b = rec(i)
        for c in r["commonNames"] + [dict(r["displayName"], text=r["displayName"]["value"], tag="DISPLAYNAME")]:
            if P.search(c["text"]):
                out.append(f"{i} [{c['language']}]{' DISPLAYNAME' if c.get('tag') else ''}: {c['text']}")
    return [f"nombres con anotación de idioma o país: {len(out)}"] + out

def scan_citation_formats():
    bad = []
    for i in PLANTS:
        r, b = rec(i)
        for n, u in enumerate(r["traditionalUses"]):
            for c in u["citations"]:
                m = re.match(r"^Woi\.(\w+)$", c["key"])
                if m and c["ref"] and c["text"] != f"The Wealth of India, vol. {m.group(1)}":
                    bad.append((i, n, c["key"], c["text"][:70]))
                if c["key"] == "Woi" and c["ref"]:
                    bad.append((i, n, c["key"], c["text"][:70]))
    return [f"citas WOI con formato distinto de «The Wealth of India, vol. N»: {len(bad)}"] + [str(x) for x in bad[:30]]

def scan_family_null():
    t = n = 0
    for i in PLANTS:
        r, b = rec(i)
        if r["family"] is None:
            t += 1
            if re.search(r"familia", (r["description"] or {}).get("value", ""), re.I): n += 1
    return [f"registros con family nula: {t}; de ellos la descripción menciona una familia: {n}"]

SCANS = [
    ("nas-citas", scan_nas), ("senales-veterinarias", scan_veterinary), ("cantidades-y-dosis", scan_units),
    ("formula-malformada", scan_malformed_formula), ("usos-perdidos", scan_empty_uses), ("autores-de-imagen", scan_images),
    ("origen", scan_origin), ("texto-de-seguridad", scan_safety_meta), ("senales-letales-y-nivel", scan_lethal_levels),
    ("actividades-sin-traducir", scan_untranslated), ("actividades-variantes", scan_activity_variants),
    ("descripciones-salud", scan_descriptions_health), ("nombres-con-anotacion", scan_name_annotations),
    ("formato-citas-woi", scan_citation_formats), ("family-nula", scan_family_null),
]

if __name__ == "__main__":
    outdir = None
    if "--out" in sys.argv:
        outdir = Path(sys.argv[sys.argv.index("--out") + 1]); outdir.mkdir(parents=True, exist_ok=True)
    for name, fn in SCANS:
        lines = fn()
        if outdir:
            (outdir / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            print("#" * 6, name); print("\n".join(lines)); print()
