#!/usr/bin/env python3
"""Detecta párrafos y elementos de lista cortados a mano (AGENTS.md): una línea de texto seguida de otra línea de continuación."""
import re, sys
bad = 0
for f in sys.argv[1:]:
    lines = open(f, encoding="utf-8").read().splitlines()
    fence = False
    prev = None
    for i, l in enumerate(lines, 1):
        if l.lstrip().startswith("```"):
            fence = not fence
            prev = None
            continue
        if fence or not l.strip() or l.lstrip().startswith("|") or l.startswith("#"):
            prev = None
            continue
        is_item = re.match(r"^\s*([-*]|\d+\.)\s", l)
        # una línea que no abre elemento ni encabezado y sigue a otra de texto es continuación
        if prev is not None and not is_item:
            print(f"{f}:{i}: posible línea de continuación (la anterior es la {prev})")
            bad += 1
        prev = i
print(f"{bad} hallazgos")
sys.exit(1 if bad else 0)
