#!/usr/bin/env python3 -I
"""10.2: busca en los archivos versionados (fuera de la semilla, de la propia QA y de openspec/changes/archive) cada ID anterior y
clasifica la coincidencia segun el estado del ID en la base nueva (id-map.tsv de compare_bases.py).

Uso: grep_ids.py <repo> <id-map.tsv> <salida.tsv>
"""
import csv, re, subprocess, sys, pathlib, collections
repo, mapf, out = sys.argv[1:4]
rows = {r["id_anterior"]: r for r in csv.DictReader(open(mapf), delimiter="\t")}
files = subprocess.check_output(["git", "-C", repo, "ls-files", "-z"]).decode().split("\0")
skip = ("data/seed/", "openspec/changes/consolidate-catalog-seed/qa/", "openspec/changes/archive/", "backend/Cargo.lock", "app/pubspec.lock")
pat = re.compile(r"(?<![a-z0-9-])(" + "|".join(sorted(map(re.escape, rows), key=len, reverse=True)) + r")(?![a-z0-9-])")
res = []
for f in files:
    if not f or f.startswith(skip):
        continue
    p = pathlib.Path(repo) / f
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    for n, line in enumerate(text.splitlines(), 1):
        for m in pat.finditer(line):
            r = rows[m.group(1)]
            res.append((f, n, m.group(1), r["estado"], r["id_nuevo"], line.strip()[:160]))
with open(out, "w") as fh:
    fh.write("archivo\tlinea\tid\testado\tid_nuevo\tlinea_texto\n")
    for r in res:
        fh.write("\t".join(map(str, r)) + "\n")
c = collections.Counter((r[0], r[2], r[3]) for r in res)
print("coincidencias:", len(res))
for (f, i, e), n in sorted(c.items()):
    print(f"{f}\t{i}\t{e}\t{n}")
