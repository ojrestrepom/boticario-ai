#!/usr/bin/env python3 -I
"""10.1: para cada planta que tenía usos en la base anterior y ninguno en la nueva, muestra el motivo de la asignación de filas de USDA.

Uso: lost_uses_reasons.py <evidence/ids/lost-uses.tsv> <data/work/usda/assignment-report.json> <data/seed/plants>
"""
import csv, json, sys, pathlib
lost = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
rep = json.load(open(sys.argv[2]))
una = {}
for u in rep["unassigned"]:
    una.setdefault(u["name"].lower(), []).append(u)
seed = pathlib.Path(sys.argv[3])
print("id_anterior\tusos_antes\tid_nuevo\tsolo_genero\tgrupos_en_semilla\tfilas_USDA_sin_asignar (motivo)")
for r in lost:
    oid, name, uses, _, nid = r[0], r[1], int(r[2]), r[3], r[4]
    rec = json.load(open(seed / f"{nid}.json"))
    g = "solo-genero" in [f["code"] for f in rec["reviewFlags"]]
    m = una.get(name.lower(), [])
    txt = "; ".join(f"{x['rows']} filas {x['reason']}" for x in m) or "no figura como sin asignar"
    print(f"{oid}\t{uses}\t{nid}\t{'si' if g else 'no'}\t{len(rec['traditionalUses'])}\t{txt}")
