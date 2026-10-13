#!/usr/bin/env python3
"""Compara la capa cruda (raw.db) con los CSV del ZIP original: tablas, columnas, filas y valores (solo biblioteca estándar).

Uso: check_raw.py <zip> <raw.db>
Sale con 0 si todas las tablas coinciden celda a celda; con 1 si no. Imprime una línea por tabla.
"""
import csv
import io
import sqlite3
import sys
import zipfile

zip_path, raw_path = sys.argv[1], sys.argv[2]
con = sqlite3.connect(f"file:{raw_path}?mode=ro", uri=True)
bad = 0
with zipfile.ZipFile(zip_path) as z:
    names = sorted(n for n in z.namelist() if n.lower().endswith(".csv"))
    for n in names:
        table = "raw_usda_" + n[:-4].lower()
        text = z.read(n).decode("cp1252")
        rows = list(csv.reader(io.StringIO(text, newline="")))
        header, data = rows[0], rows[1:]
        cols = [r[1] for r in con.execute(f'pragma table_info("{table}")')]
        db_cols = [c for c in cols if c != "_row"]
        problems = []
        if db_cols != header:
            problems.append(f"columnas distintas: csv={header} db={db_cols}")
        db_rows = [list(r) for r in con.execute(f'select {",".join(chr(34)+c+chr(34) for c in header)} from "{table}" order by _row')]
        if len(db_rows) != len(data):
            problems.append(f"filas: csv={len(data)} db={len(db_rows)}")
        else:
            diffs = sum(1 for a, b in zip(data, db_rows) if a != b)
            if diffs:
                problems.append(f"{diffs} filas con valores distintos")
        status = "OK" if not problems else "FALLA " + "; ".join(problems)
        if problems:
            bad += 1
        print(f"{table}: filas={len(data)} columnas={len(header)} {status}")
sys.exit(1 if bad else 0)
