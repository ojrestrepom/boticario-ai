#!/usr/bin/env python3 -I
"""10.1: compara la base anterior (main) con la nueva y genera la tabla ID anterior -> destino.

Uso: compare_bases.py <old catalog.db> <new catalog.db> <seed dir> <salida dir> [<data/work dir>]
Con <data/work dir> añade la relación taxonómica de USDA (aceptado, homotípico, heterotípico...) de cada ID anterior, leída de los paquetes.
Solo lee. Escribe id-map.tsv, id-map-summary.json y checks.txt en <salida dir>.
"""
import json, sqlite3, sys, collections, pathlib

old_db, new_db, seed, out = sys.argv[1:5]
work = sys.argv[5] if len(sys.argv) > 5 else None
out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
o = sqlite3.connect(f"file:{old_db}?mode=ro", uri=True)
n = sqlite3.connect(f"file:{new_db}?mode=ro", uri=True)

old = {r[0]: dict(sci=r[1], fam=r[2], uses=r[3]) for r in o.execute(
    "select p.id,p.scientific_name,p.family,(select count(*) from plant_use u where u.plant_id=p.id) from plant p")}
new = {r[0]: dict(sci=r[1], fam=r[2], uses=r[3]) for r in n.execute(
    "select p.id,p.scientific_name,p.family,(select count(*) from plant_use u where u.plant_id=p.id) from plant p")}
alias = dict(n.execute("select alias, plant_id from plant_alias"))
syn = collections.defaultdict(set)
for pid, t in n.execute("select plant_id, text from plant_name where kind='scientific'"):
    syn[pid].add(t.lower())
flags = collections.defaultdict(list)
for pid, code in n.execute("select plant_id, code from plant_review_flag"):
    flags[pid].append(code)

def nrm(t):
    return t.lower().replace("\u00d7", "x").replace("  ", " ").strip()

# relación USDA por ID anterior: plant_source_id (fnfnum) -> universo del paquete de la planta destino
fnf = dict(o.execute("select plant_id, source_plant_id from plant_source_id where source_id='usda'"))
rel_by_key = {}
if work:
    import glob
    for fp in glob.glob(f"{work}/bundles/*.json"):
        b = json.load(open(fp))
        for u in b["identity"].get("universe", []):
            rel_by_key[u["key"]] = (b["plantKey"], u.get("outcome"), u.get("relation"))

checks = []
def chk(name, ok, detail=""):
    checks.append((("INFO" if name.startswith("(informativo)") else "PASA" if ok else "FALLA"), name, detail))

# Destino de cada ID anterior
dest = {}
for oid, info in old.items():
    if oid in new and oid in alias:
        dest[oid] = ("CONFLICTO", oid)
    elif oid in new:
        dest[oid] = ("MISMO", oid)
    elif oid in alias:
        dest[oid] = ("ALIAS", alias[oid])
    else:
        dest[oid] = ("AUSENTE", "")
absorbed = collections.defaultdict(list)  # destino -> ids anteriores que llegan
for oid, (k, d) in dest.items():
    if d:
        absorbed[d].append(oid)

rows = []
for oid in sorted(old):
    k, d = dest[oid]
    info = old[oid]
    if k == "MISMO":
        same_name = nrm(info["sci"]) == nrm(new[d]["sci"])
        cls = "igual" if same_name else "igual-ID-nombre-distinto"
        if same_name and len(absorbed[d]) > 1:
            cls = "igual-absorbe"  # conserva ID y absorbe otros
        note = ""
    elif k == "ALIAS":
        cls = "renombrado" if len(absorbed[d]) == 1 else "fusionado"
        in_syn = nrm(info["sci"]) in {nrm(x) for x in syn[d]}
        note = "nombre anterior es sinónimo/nombre de la nueva" if in_syn else "nombre anterior NO está entre los nombres científicos de la nueva"
    else:
        cls = "ausente"; note = "SIN DESTINO"
    fl = ",".join(sorted(set(flags.get(d, [])) & {"fusion-heterotipica", "grupo-partido", "identidad-ambigua", "variante-ortografica", "solo-genero", "sin-resolucion", "aceptado-superior-a-especie"})) if d else ""
    rk = rel_by_key.get("usda:" + fnf.get(oid, ""), None)
    rel = "" if rk is None else f"{rk[1]}/{rk[2] or '-'}" + ("" if rk[0] == d else f" (paquete de {rk[0]})")
    rows.append((oid, info["sci"], info["uses"], k, d, new[d]["sci"] if d else "", new[d]["uses"] if d else "", cls, note, fl, ",".join(x for x in absorbed[d] if x != oid) if (d and len(absorbed[d]) > 1) else "", rel))

with open(out / "id-map.tsv", "w") as f:
    f.write("id_anterior\tnombre_anterior\tusos_anteriores\testado\tid_nuevo\tnombre_nuevo\tusos_nuevos\tclase\tnota\tflags\totros_ids_que_llegan\trelacion_usda\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")

cnt = collections.Counter(r[7] for r in rows)
changed = [r for r in rows if r[3] != "MISMO"]
new_only = sorted(set(new) - set(d for _, d in dest.values()))
extra_alias = sorted(a for a in alias if a not in old)
lost_uses = [r for r in rows if r[2] > 0 and r[6] == 0]
gained = [r for r in rows if r[2] == 0 and r[6] not in ("", 0)]

chk("Todo ID anterior tiene destino (mismo ID o alias) o queda ausente listado", True, f"ausentes={cnt['ausente']}")
chk("Ningún ID anterior es a la vez planta y alias", all(r[3] != "CONFLICTO" for r in rows))
chk("Ningún alias coincide con el ID de otra planta", not (set(alias) & set(new)), str(sorted(set(alias) & set(new))[:5]))
chk("Todos los alias apuntan a una planta existente", all(v in new for v in alias.values()))
chk("IDs anteriores que conservan ID pero cambian de nombre científico = 0", cnt["igual-ID-nombre-distinto"] == 0, str([r[:2] + r[4:6] for r in rows if r[7] == "igual-ID-nombre-distinto"][:10]))
chk("(informativo) Alias cuyo nombre anterior está entre los nombres científicos de la nueva", all("NO está" not in r[8] for r in rows), f"{sum('NO está' in r[8] for r in rows)} sin coincidencia")
chk("lavandula-angustifolia existe", "lavandula-angustifolia" in new)
chk("rosmarinus-officinalis -> salvia-rosmarinus", alias.get("rosmarinus-officinalis") == "salvia-rosmarinus")
chk("matricaria-recutita -> matricaria-chamomilla", alias.get("matricaria-recutita") == "matricaria-chamomilla")
chk("mentha-x-piperita-subsp-nothosubsp-piperita -> mentha-x-piperita", alias.get("mentha-x-piperita-subsp-nothosubsp-piperita") == "mentha-x-piperita")
chk("manzanilla y menta tienen usos", new["matricaria-chamomilla"]["uses"] > 0 and new["mentha-x-piperita"]["uses"] > 0, f"{new['matricaria-chamomilla']['uses']} y {new['mentha-x-piperita']['uses']}")

summary = dict(
    plantas_anterior=len(old), plantas_nueva=len(new), alias=len(alias),
    sin_usos_anterior=sum(1 for v in old.values() if v["uses"] == 0),
    sin_usos_nueva=sum(1 for v in new.values() if v["uses"] == 0),
    usos_anterior=o.execute("select count(*) from plant_use").fetchone()[0],
    usos_nueva=n.execute("select count(*) from plant_use").fetchone()[0],
    clases=dict(cnt),
    ids_que_cambian=len(changed),
    ids_nuevos_sin_origen_anterior=len(new_only),
    alias_extra_no_anteriores=len(extra_alias),
    nuevos_con_varios_ids_anteriores=sum(1 for d, l in absorbed.items() if len(l) > 1),
    con_usos_antes_y_sin_usos_ahora=len(lost_uses),
    sin_usos_antes_y_con_usos_ahora=len(gained),
)
(out / "id-map-summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
with open(out / "new-only.txt", "w") as f:
    for i in new_only:
        f.write(f"{i}\t{new[i]['sci']}\t{new[i]['uses']}\t{','.join(flags.get(i, []))}\n")
with open(out / "extra-alias.txt", "w") as f:
    for a in extra_alias:
        f.write(f"{a}\t{alias[a]}\n")
with open(out / "lost-uses.tsv", "w") as f:
    for r in lost_uses:
        f.write("\t".join(str(x) for x in r) + "\n")
with open(out / "checks.txt", "w") as f:
    for c in checks:
        f.write(" | ".join(c) + "\n")
print(json.dumps(summary, indent=1, ensure_ascii=False))
for c in checks:
    print(" | ".join(c))
