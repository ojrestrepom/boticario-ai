#!/usr/bin/env python3
"""11.1/11.4 (catalog-seed y catalog-ingest): coherencia de la URL de licencia entre sources.json, el manifiesto sellado y source.license_url
de la base, y rechazo de valores invalidos por el validador de fuentes (con copias en memoria; no se escribe nada).
Uso (desde la raiz del repo): python3 -B qa/scripts/seed_ingest_checks.py   (sin -I: importa catalog_seed de tools/catalog-seed)
"""
import copy, json, sqlite3, sys, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools" / "catalog-seed"))
from catalog_seed.sources import load_sources, validate_source, SourceError, DEFAULT_SOURCES_FILE
out = []
def rec(name, ok, detail=""): out.append(("PASA" if ok else "FALLA", name, detail)); print(out[-1][0], name, detail)
srcs = {s.id: s for s in load_sources(DEFAULT_SOURCES_FILE)}
man = {s["id"]: s for s in json.load(open(ROOT / "data/seed/manifest.json"))["sources"]}
db = sqlite3.connect(f"file:{ROOT}/data/build/catalog.db?mode=ro", uri=True)
dbu = dict(db.execute("select id, license_url from source"))
rec("fuentes del manifiesto = fuentes de la base", set(man) == set(dbu), f"{len(man)} fuentes")
bad = [i for i in man if man[i].get("licenseUrl") != dbu[i]]
rec("manifiesto.licenseUrl = source.license_url para cada fuente (null donde no hay)", not bad, str(bad))
exp = {"wikipedia_es": "https://creativecommons.org/licenses/by-sa/4.0/", "efsa": "https://creativecommons.org/licenses/by/4.0/", "wcvp": "https://creativecommons.org/licenses/by/3.0/",
       "usda": "https://creativecommons.org/publicdomain/zero/1.0/", "wfo": "https://creativecommons.org/publicdomain/zero/1.0/", "wikidata": "https://creativecommons.org/publicdomain/zero/1.0/",
       "commons": None, "ema_json": None, "ema_pdf": None, "tppt": None}
rec("URL de licencia por fuente = las oficiales de Creative Commons (y null para Commons, EMA y TPPT)", dbu == exp, str({k: v for k, v in dbu.items() if exp.get(k) != v}))
src_ok = all(srcs[i].data.get("licenseUrl", "<ausente>") == man[i].get("licenseUrl", "<ausente>") for i in man if i in srcs)
rec("sources.json declara el mismo licenseUrl que el manifiesto", src_ok, f"{sum(1 for i in srcs if i in man)} fuentes comparadas")
base = srcs["wikipedia_es"].data
for badv in ("http://creativecommons.org/licenses/by-sa/4.0/", "", "   ", "https://", "https://a b/", "ftp://x", 3, True, ["https://x/"], " https://x/"):
    d = copy.deepcopy(base); d["licenseUrl"] = badv
    try: validate_source(d); rec(f"URL de licencia invalida {badv!r} rechazada", False, "aceptada")
    except SourceError as e: rec(f"URL de licencia invalida {badv!r} rechazada nombrando fuente y campo", "wikipedia_es" in str(e) and "licenseUrl" in str(e), str(e))
for okv in (None, "https://creativecommons.org/licenses/by-sa/4.0/"):
    d = copy.deepcopy(base); d["licenseUrl"] = okv
    try: validate_source(d); rec(f"licenseUrl {okv!r} aceptada", True)
    except SourceError as e: rec(f"licenseUrl {okv!r} aceptada", False, str(e))
d = copy.deepcopy(base); d.pop("licenseUrl", None)
try: validate_source(d); rec("fuente sin licenseUrl aceptada", True)
except SourceError as e: rec("fuente sin licenseUrl aceptada", False, str(e))
# registros y seedHash sin cambios respecto al cambio 1: solo manifest.json cambio en data/seed desde 7e6cbfe
r = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "7e6cbfe..HEAD", "--", "data/seed"], capture_output=True, text=True).stdout.split()
rec("desde el cambio 1 solo cambio data/seed/manifest.json (ningun registro de planta)", r == ["data/seed/manifest.json"], str(r))
d = subprocess.run(["git", "-C", str(ROOT), "diff", "7e6cbfe..HEAD", "--", "data/seed/manifest.json"], capture_output=True, text=True).stdout
changed = [l for l in d.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
rec("el diff del manifiesto son solo lineas licenseUrl (seedHash intacto)", changed and all('"licenseUrl"' in l and l.startswith("+") for l in changed), f"{len(changed)} lineas")
if any(o[0] == "FALLA" for o in out): sys.exit(1)
