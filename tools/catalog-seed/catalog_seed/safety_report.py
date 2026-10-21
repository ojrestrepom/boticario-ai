"""Informe del mapa de seguridad sobre las filas extraídas (data/work/sources.db): clasificación de la 4.5 y cobertura de categorías."""
import collections

from . import safety, workdb

EXAMPLES = 4


def ema_classification(connection, safety_map):
    """Clasifica la sección 4.5 de cada ficha con documento. Devuelve {slug: resultado} (más 'status' de la extracción)."""
    sections = {}
    for row in workdb.fetch_rows(connection, "ema_pdf", "ema_pdf"):
        if row["content"].get("section") == "4.5":
            sections.setdefault(row["content"]["slug"], []).append(row["content"])
    result = {}
    for doc in workdb.fetch_rows(connection, "ema_pdf", "ema_pdf_doc"):
        slug, status = doc["row_key"], doc["content"]["status"]
        if status in ("no-descargada", "sin-documento"):
            result[slug] = {"class": status, "level": None, "status": status, "columns": {}, "matched": []}
            continue
        if status == "declaracion-publica":
            result[slug] = {"class": "statement-no-safety" if not _statement_has_safety(connection, slug) else "statement-with-safety",
                            "level": None, "status": status, "columns": {}, "matched": []}
            continue
        # Varias secciones 4.5 (dos documentos en la ficha): gana la clase más grave.
        candidates = [dict(safety.ema_interaction_class(safety_map, section), status=status) for section in sections.get(slug, [])]
        if not candidates:
            candidates = [dict(safety.ema_interaction_class(safety_map, None), status=status)]
        result[slug] = min(candidates, key=lambda c: safety.EMA_CLASS_ORDER.index(c["class"]) if c["class"] in safety.EMA_CLASS_ORDER else 99)
    return result


def _statement_has_safety(connection, slug):
    rows = workdb.fetch_rows(connection, "ema_pdf", "ema_pdf", row_key="%s:CONCLUSIONS" % slug)
    return bool(rows and rows[0]["content"].get("safety_data"))


def ema_table(classification):
    """{clase: [slugs]} ordenado por clase."""
    table = collections.OrderedDict()
    for slug, item in sorted(classification.items()):
        table.setdefault(item["class"], []).append(slug)
    return table


def format_ema(classification, safety_map):
    table = ema_table(classification)
    lines = ["EMA, sección 4.5: %d fichas" % len(classification)]
    for name in list(safety_map["ema"]["classes"]) + sorted(set(table) - set(safety_map["ema"]["classes"])):
        slugs = table.get(name, [])
        covered = "" if name in safety_map["ema"]["classes"] else "  (SIN CUBRIR en el mapa)"
        level = safety_map["ema"]["classes"].get(name, {}).get("level")
        lines.append("  %-22s nivel %-6s %4d  %s%s" % (name, level or "ninguno", len(slugs), ", ".join(slugs[:EXAMPLES]), covered))
    return "\n".join(lines)


def tppt_coverage(connection, safety_map):
    """{campo: {valor: (plantas, nivel, cubierto)}} de los valores presentes en TPPT."""
    out = {}
    for field in ("human_toxicity", "animal_toxicity"):
        counts = collections.Counter()
        for row in workdb.fetch_rows(connection, "tppt", "tppt_plant"):
            counts[row["content"].get(field) or ""] += 1
        out[field] = {value: (n,) + _tppt_pair(safety_map, value, field) for value, n in sorted(counts.items(), key=lambda i: -i[1]) if value}
    return out


def _tppt_pair(safety_map, value, field):
    result = safety.tppt_level(safety_map, value, field)
    return result["level"], not result["uncovered"]


def efsa_coverage(connection, safety_map):
    """Plantas (cadenas scientificNames distintas) con sustancia de preocupación y categorías sin cubrir."""
    config = safety_map["efsa"]
    names, uncovered = {}, set()
    for row in workdb.fetch_rows(connection, "efsa", "efsa_botanic"):
        names.setdefault(row["raw_name_cell"], []).append(row["content"])
        if row["content"].get("result_type", "") not in config["result_types"]:
            uncovered.add(("result_type", row["content"].get("result_type")))
    for row in workdb.fetch_rows(connection, "efsa", "efsa_endpoint"):
        content = row["content"]
        if content.get("study_category") not in config["study_categories"]:
            uncovered.add(("study_category", content.get("study_category")))
        if safety.efsa_effect_group(content.get("toxicity_summary")) not in config["endpoint_effects"]:
            uncovered.add(("endpoint_effect", content.get("toxicity_summary")))
    with_concern = sum(1 for rows in names.values() if safety.efsa_concern(safety_map, rows)["level"])
    return {"botanical_name_cells": len(names), "with_substance_of_concern": with_concern, "uncovered": sorted(uncovered, key=str)}


def format_report(connection, safety_map):
    lines = [format_ema(ema_classification(connection, safety_map), safety_map), ""]
    coverage = tppt_coverage(connection, safety_map)
    for field, values in coverage.items():
        lines.append("TPPT %s: %d valores" % (field, len(values)))
        for value, (n, level, covered) in values.items():
            lines.append("  %-48s %4d  nivel %-6s %s" % (value, n, level or "ninguno", "" if covered else "SIN CUBRIR"))
    efsa = efsa_coverage(connection, safety_map)
    lines += ["", "EFSA: %(botanical_name_cells)d celdas scientificNames distintas, %(with_substance_of_concern)d con sustancia de preocupación" % efsa,
              "  categorías sin cubrir: %s" % (efsa["uncovered"] or "ninguna")]
    return "\n".join(lines)
