"""Extracción de USDA (Dr. Duke): taxones, nombres comunes, partes, usos y referencias, con procedencia.

Lee los CSV del ZIP verificado (Windows-1252, comillas CSV estándar, una cabecera por archivo), como el
adaptador Rust actual. No asigna usos a plantas ni elige citas candidatas: eso necesita el resolvedor y se
hace al armar los paquetes (tareas 3.2 y 3.5). Cada fila de ETHNOBOT conserva su celda TAXON como
raw_name_cell, sin FNFNUM.

Tipos de fila:
- usda_taxon: una por FNFNUM de FNFTAX (raw_name_cell = TAXON).
- usda_common_name: nombres de COMMON_NAMES por FNFNUM, con un idioma heurístico (en, o und si termina en «(...)»).
- usda_part: un resumen por (FNFNUM, PPCO) de FARMACY_NEW con el nombre de la parte de PARTS.
- usda_use: una por fila de ETHNOBOT (row_key = ETHNO) con la REFERENCE corta tal como viene.
- usda_reference: una por clave de REFERENCES con su LONGREF.
"""
import csv
import io
import re
import zipfile

from .workdb import Row

ENCODING = "cp1252"
TOP_COMPOUNDS = 10
TAXON_FIELDS = ("FNFNUM", "TAXON", "TAXAUTHOR", "GENUS", "SPECIES", "SUBSPECIES", "VARIETY", "FORMA", "CULTIVAR", "FAMILY", "SPCMT")
USE_FIELDS = ("ETHNO", "ACTIVITY", "GENUS", "SPECIES", "SPAUT", "SPRANK", "SPXNAM", "SPXAUT", "FAMILY", "CNAME", "COUNTRY",
              "REFERENCE", "LONGREF", "EFFECTIVE", "TAXON", "TAXAUTHOR")
AMOUNT_COLUMNS = ("AMT_OR_HI", "AMT_HI", "AMT_ULHI", "AMT_OR_LO", "AMT_LO")
EO_PCT_COLUMNS = ("EOPCT_OR_HI", "EOPCT_HI", "EOPCT_OR_LO", "EOPCT_LO")
EO_COMPOUND = re.compile(r"^EO(\s*\(.*\))?$")


def read_table(archive, name):
    """Filas de un CSV del ZIP como dicts, con las claves de la cabecera y los valores sin tocar."""
    with archive.open(name + ".csv") as handle:
        text = io.TextIOWrapper(handle, encoding=ENCODING, newline="")
        yield from csv.DictReader(text)


def clean(value):
    return value.strip() if isinstance(value, str) else value


def number(value):
    try:
        return float(value) if value and value.strip() else None
    except ValueError:
        return None


def first_number(row, columns):
    """Mayor valor numérico entre las columnas dadas (la fuente reparte rango bajo/alto en varias)."""
    values = [v for v in (number(row.get(c)) for c in columns) if v is not None]
    return max(values) if values else None


def is_eo(compound):
    """El compuesto EO (aceite esencial total) y sus variantes «EO (ASSUMED)» y «EO(ASS.)»."""
    return bool(EO_COMPOUND.match(compound.strip().upper()))


def name_language(text):
    """Idioma heurístico de un nombre común: «und» si termina en una etiqueta entre paréntesis, si no «en» (como el adaptador Rust)."""
    return "und" if text.endswith(")") and "(" in text else "en"


def _plain(value):
    return int(value) if isinstance(value, float) and value == int(value) else value


def summarize_parts(rows, part_names):
    """Resumen por (FNFNUM, PPCO): filas, compuestos distintos, hasta 10 por cantidad y hasta 10 por EOPCT."""
    groups = {}
    skipped = {"empty_ppco": 0}
    for row in rows:
        fnfnum, ppco, chem = clean(row["FNFNUM"]), clean(row["PPCO"]), clean(row["CHEM"])
        if not ppco:
            skipped["empty_ppco"] += 1
            continue
        group = groups.setdefault((fnfnum, ppco), {"rows": 0, "chems": {}})
        group["rows"] += 1
        entry = group["chems"].setdefault(chem, {"amount": None, "unit": None, "eopct": None})
        amount = first_number(row, AMOUNT_COLUMNS)
        if amount is not None and (entry["amount"] is None or amount > entry["amount"]):
            entry["amount"], entry["unit"] = amount, clean(row.get("QUANT_UNIT")) or None
        eopct = first_number(row, EO_PCT_COLUMNS)
        if eopct is not None and (entry["eopct"] is None or eopct > entry["eopct"]):
            entry["eopct"] = eopct
    summaries = {}
    for key, group in groups.items():
        chems = group["chems"]

        def top(field):
            ranked = sorted(((c, v) for c, v in chems.items() if v[field] is not None), key=lambda item: (-item[1][field], item[0]))
            return ranked[:TOP_COMPOUNDS]

        eo_entries = {c: v for c, v in chems.items() if is_eo(c)}
        summaries[key] = {
            "ppco": key[1],
            "ppna": part_names.get(key[1]),
            "rows": group["rows"],
            "distinct_compounds": len(chems),
            "has_eo": bool(eo_entries),
            "eo_compounds": sorted(eo_entries),
            "top_amount": [{"compound": c, "amount": _plain(v["amount"]), "unit": v["unit"], "eo": is_eo(c)} for c, v in top("amount")],
            "top_eo": [{"compound": c, "eopct": _plain(v["eopct"]), "eo": is_eo(c)} for c, v in top("eopct")],
        }
    return summaries, skipped


def extract(zip_path):
    """Genera las filas de USDA y devuelve (filas, estadísticas)."""
    rows, stats = [], {}
    with zipfile.ZipFile(str(zip_path)) as archive:
        taxa = {}
        for row in read_table(archive, "FNFTAX"):
            fnfnum = clean(row["FNFNUM"])
            if fnfnum in taxa:
                raise ValueError("FNFNUM repetido en FNFTAX: %s" % fnfnum)
            taxa[fnfnum] = row
            content = {f.lower(): clean(row[f]) for f in TAXON_FIELDS if f in row}
            rows.append(Row("usda_taxon", fnfnum, content, raw_name_cell=row["TAXON"], fnfnum=fnfnum))
        stats["usda_taxon"] = len(taxa)

        per_plant, orphans = {}, 0
        for row in read_table(archive, "COMMON_NAMES"):
            fnfnum, name = clean(row["FNFNUM"]), clean(row["CNNAM"])
            if fnfnum not in taxa:
                orphans += 1
                continue
            per_plant[fnfnum] = per_plant.get(fnfnum, 0) + 1
            rows.append(Row("usda_common_name", "%s-%d" % (fnfnum, per_plant[fnfnum]),
                            {"name": name, "cnid": clean(row.get("CNID")), "language": name_language(name)},
                            raw_name_cell=row["CNNAM"], fnfnum=fnfnum))
        stats["usda_common_name"] = sum(per_plant.values())
        stats["common_name_orphans"] = orphans

        part_names = {clean(r["PPCO"]): clean(r["PPNA"]) for r in read_table(archive, "PARTS")}
        summaries, skipped = summarize_parts((r for r in read_table(archive, "FARMACY_NEW") if clean(r["FNFNUM"]) in taxa), part_names)
        for (fnfnum, ppco), summary in sorted(summaries.items(), key=lambda item: (int(item[0][0]), item[0][1])):
            rows.append(Row("usda_part", "%s-%s" % (fnfnum, ppco), summary, raw_name_cell=taxa[fnfnum]["TAXON"], fnfnum=fnfnum))
        stats["usda_part"] = len(summaries)
        stats["farmacy_rows_empty_ppco"] = skipped["empty_ppco"]

        uses = 0
        for row in read_table(archive, "ETHNOBOT"):
            ethno = clean(row["ETHNO"])
            content = {f.lower(): clean(row[f]) for f in USE_FIELDS if clean(row.get(f))}
            rows.append(Row("usda_use", ethno, content, raw_name_cell=row["TAXON"]))
            uses += 1
        stats["usda_use"] = uses

        references = 0
        for row in read_table(archive, "REFERENCES"):
            key = row["REFERENCE"]
            content = {"reference": clean(key), "longref": clean(row["LONGREF"])}
            if clean(row.get("NOTE")):
                content["note"] = clean(row["NOTE"])
            rows.append(Row("usda_reference", key, content, raw_name_cell=key))
            references += 1
        stats["usda_reference"] = references
    return rows, stats
