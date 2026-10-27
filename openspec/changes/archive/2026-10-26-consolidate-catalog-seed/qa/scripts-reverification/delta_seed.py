#!/usr/bin/env python3 -I
"""Diferencias de campo entre los registros de la semilla en la base de la QA anterior (8647a01) y el HEAD actual.
Uso: delta_seed.py <repo> <commit-anterior>
Solo lee git y data/seed/plants."""
import json, subprocess, sys, collections
repo, old = sys.argv[1], sys.argv[2]
files = subprocess.check_output(["git", "-C", repo, "diff", "--name-only", old, "HEAD", "--", "data/seed/plants"], text=True).split()
fields = collections.Counter(); per = {}
for f in files:
    new = json.load(open(f"{repo}/{f}"))
    o = json.loads(subprocess.check_output(["git", "-C", repo, "show", f"{old}:{f}"], text=True))
    ch = [k for k in sorted(set(o) | set(new)) if o.get(k) != new.get(k)]
    per[new["id"]] = ch
    fields.update(ch)
print(f"registros cambiados: {len(files)}")
print("campos cambiados (registros):", dict(fields.most_common()))
only = collections.Counter(tuple(v) for v in per.values())
print("combinaciones:")
for k, n in only.most_common(): print(n, k)
