"""Comando resolve (tarea 2.6): índice taxonómico, entradas del universo, resolución y salidas en data/work/universe/.

Entradas: cada `usda_taxon` de `data/work/sources.db` (nombre = TAXON, autor = TAXAUTHOR) y cada especie de las fichas de la EMA
(`ema_herbal`). La celda `botanical_name` de la EMA se separa con `split_source_names`, que descarta los fragmentos
«Combination: ...». Así, las fichas de combinaciones no aportan especies (no tienen objetivos y sus especies ya están en las
monografías simples); la ficha fusionada `hyperici-herba` (marcada como combinación al deduplicar, pero formada por dos
monografías simples) sí aporta sus dos especies. Una especie de la EMA que ya está en USDA no crea una planta: se une a la
planta que ya existe. Solo crea una planta nueva la que ningún nombre de USDA alcanza.
"""
import json
import os
import sqlite3
import time

from . import workdb
from .download import require_verified_files
from .sources import REPO_ROOT, SourceError
from .taxonomy import Entry, build_universe, open_backbone, parse_name, split_source_cell
from .taxonomy.index import INDEX_VERSION, build_index
from .taxonomy.universe import RESOLVED

DEFAULT_TAXONOMY_DB = workdb.DEFAULT_WORK_DIR / "taxonomy.db"
DEFAULT_UNIVERSE_DIR = workdb.DEFAULT_WORK_DIR / "universe"
DEFAULT_CATALOG_DB = REPO_ROOT / "data" / "build" / "catalog.db"
UNIVERSE_FORMAT = "catalog-universe/1"
REPORT_FORMAT = "catalog-universe-report/1"
WCVP_MEMBERS = ("wcvp_names.csv", "wcvp_distribution.csv")
WFO_MEMBER = "classification.csv"
PILOT_CHECK_ID = "lavandula-angustifolia"
RELATION_LABEL = {"A": "aceptado", "H": "homotípico", "X": "heterotípico"}


# --- Índice ---------------------------------------------------------------------------------------------------------

def index_labels(sources):
    """Etiquetas que identifican los insumos del índice: algoritmo y checksum declarados en sources.json."""
    labels = {}
    for source_id in ("wcvp", "wfo"):
        source = next((s for s in sources if s.id == source_id), None)
        if source is None or not source.enabled:
            raise SourceError("la fuente '%s' no está declarada o está desactivada" % source_id)
        if not source.pinned:
            raise SourceError("la fuente '%s' no tiene el checksum fijado" % source_id)
        labels[source_id] = "%s:%s" % (source.algorithm, source.checksum)
    return labels


def index_is_current(path, labels):
    """El índice existe, tiene la versión del formato y se hizo con los mismos checksums de WCVP y WFO."""
    if not os.path.isfile(path):
        return False
    try:
        connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        try:
            meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
        finally:
            connection.close()
    except sqlite3.Error:
        return False
    return (meta.get("index_version") == str(INDEX_VERSION) and meta.get("wcvp") == labels["wcvp"]
            and meta.get("wfo") == labels["wfo"])


def ensure_index(sources, cache_dir, path, force=False, log=print):
    """Devuelve (etiquetas, estadísticas de la carga o None si se reutilizó). Reconstruye si falta o cambió un checksum."""
    labels = index_labels(sources)
    if not force and index_is_current(path, labels):
        log("índice taxonómico vigente: %s" % path)
        return labels, None
    by_id = {s.id: s for s in sources}
    wcvp_zip = require_verified_files(by_id["wcvp"], cache_dir)[0]
    wfo_zip = require_verified_files(by_id["wfo"], cache_dir)[0]
    log("construyendo el índice taxonómico (unos 30 s y 1 GB en disco)...")
    stats = build_index(str(path), (str(wcvp_zip), WCVP_MEMBERS[0]), (str(wcvp_zip), WCVP_MEMBERS[1]),
                        (str(wfo_zip), WFO_MEMBER), wcvp_label=labels["wcvp"], wfo_label=labels["wfo"])
    return labels, stats


# --- Entradas -------------------------------------------------------------------------------------------------------

def collect_entries(connection):
    """Entradas del universo desde `sources.db`: primero USDA, luego las especies de la EMA. Devuelve (entradas, resumen)."""
    entries = []
    usda_rows = workdb.fetch_rows(connection, "usda", "usda_taxon")
    if not usda_rows:
        raise SourceError("sources.db no tiene filas usda_taxon; ejecute: python3 -I tools/catalog-seed/cli.py extract --source usda")
    for row in usda_rows:
        content = row["content"]
        entries.append(Entry("usda", "usda:%s" % row["row_key"], row["raw_name_cell"] or content.get("taxon") or "",
                             (content.get("taxauthor") or "").strip()))
    ema_rows = workdb.fetch_rows(connection, "ema_json", "ema_herbal")
    if not ema_rows:
        raise SourceError("sources.db no tiene filas ema_herbal; ejecute: python3 -I tools/catalog-seed/cli.py extract --source ema_json")
    ema_entries = 0
    ficha_without_species = []
    modified_cells = []
    for row in ema_rows:
        fragments, changes = split_source_cell("ema", row["raw_name_cell"])
        if not fragments:
            ficha_without_species.append(row["row_key"])
        made = []
        for i, text in enumerate(fragments):
            entry = Entry.from_text("ema", "ema:%s#%d" % (row["row_key"], i + 1), text)
            entries.append(entry)
            made.append(entry)
            ema_entries += 1
            parsed = parse_name(text)
            if parsed.author_removed:
                changes = changes + ["autor de %s limpiado, se quitó «%s»" % (entry.name, "; ".join(parsed.author_removed))]
        if changes:
            modified_cells.append({"fiche": row["row_key"], "cell": row["raw_name_cell"], "changes": changes,
                                   "entries": [{"name": e.name, "author": e.author} for e in made]})
    summary = {"usda_entries": len(usda_rows), "ema_fiches": len(ema_rows), "ema_entries": ema_entries,
               "ema_fiches_without_species": sorted(ficha_without_species), "ema_modified_cells": modified_cells}
    return entries, summary


def extraction_versions(connection):
    rows = connection.execute("SELECT source, version FROM extraction WHERE source IN ('usda', 'ema_json')").fetchall()
    return dict(rows)


# --- Relación de cada entrada con el aceptado -----------------------------------------------------------------------

def relation_of(uni, key):
    """`A` (propio aceptado), `H` (homotípico) o `X` (heterotípico); None si la entrada no resolvió."""
    return uni.relation(key)


# --- universe.json --------------------------------------------------------------------------------------------------

def _group_of(uni, plant):
    for group in uni.groups.values():
        if any(p is plant for p in group):
            return group
    return None


def plant_document(uni, plant, group):
    entries = []
    for entry in plant.entries:
        res = uni.resolutions[entry.key]
        item = {"source": entry.source, "key": entry.key, "name": entry.name, "author": entry.author,
                "outcome": res["outcome"], "matchedName": res["matched_name"] or None}
        rel = relation_of(uni, entry.key)
        item["relation"] = RELATION_LABEL[rel] if rel else None
        entries.append(item)
    collision = None
    if group is not None and len(group) > 1:
        collision = {"acceptedName": uni.resolutions[group[0].entries[0].key]["accepted_name"],
                     "members": sorted(p.id for p in group), "split": True}
    return {"id": plant.id, "name": plant.name, "author": plant.author, "kind": plant.kind, "backbone": plant.backbone or None,
            "acceptedId": plant.accepted_id or None, "matchedId": plant.matched_id or None, "family": plant.family or None,
            "entries": entries, "aliases": list(plant.aliases), "flags": sorted(plant.flags),
            "reviewFlags": plant.review_flags, "collision": collision}


def universe_document(uni, inputs, checks):
    plants = [plant_document(uni, p, _group_of(uni, p)) for p in uni.plants]
    return {"format": UNIVERSE_FORMAT, "inputs": inputs, "checks": checks, "plantCount": len(plants), "plants": plants}


# --- Informe --------------------------------------------------------------------------------------------------------

def _binomial(name):
    parsed = parse_name(name or "")
    return parsed.key_binomial if parsed.ok else None


def classify_disagreement(res):
    """`rango` si WCVP y WFO aceptan el mismo binomio y solo difieren en el rango infraespecífico; `especie` si no."""
    a, b = _binomial(res["accepted_name"]), _binomial(res.get("wfo_accepted_name"))
    return "rango" if a and a == b else "especie"


def current_ids(catalog_db):
    if not catalog_db or not os.path.isfile(str(catalog_db)):
        return None
    connection = sqlite3.connect("file:%s?mode=ro" % catalog_db, uri=True)
    try:
        return set(r[0] for r in connection.execute("SELECT id FROM plant"))
    finally:
        connection.close()


def compare_with_current(uni, ids):
    if ids is None:
        return None
    new_ids = set(p.id for p in uni.plants)
    alias_of = {}
    for plant in uni.plants:
        for alias in plant.aliases:
            alias_of.setdefault(alias, []).append(plant.id)
    different = sorted(new_ids - ids)
    covered_by_alias = sorted(i for i in ids - new_ids if i in alias_of)
    lost = sorted(i for i in ids - new_ids if i not in alias_of)
    return {"current_ids": len(ids), "universe_ids": len(new_ids), "ids_not_in_current": len(different),
            "current_ids_kept_as_id": len(ids & new_ids), "current_ids_kept_as_alias": len(covered_by_alias),
            "current_ids_lost": lost, "different_ids": different}


def _outcome_counts(uni, source):
    counts = {}
    for key, res in uni.resolutions.items():
        if uni.entries[key].source != source:
            continue
        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
    return dict(sorted(counts.items()))


def _resolution_route(res):
    flags = set(res["flags"])
    if res["outcome"] not in RESOLVED:
        return None
    if "wfo_fallback" in flags:
        return "wfo_fallback"
    if "fuzzy_match" in flags:
        return "fuzzy_match"
    if "orthographic_variant" in flags:
        return "orthographic_variant"
    return "wcvp"


def _collision_groups(uni):
    groups = []
    for akey in sorted(uni.groups):
        plants = uni.groups[akey]
        n_entries = sum(len(p.entries) for p in plants)
        if n_entries < 2 and len(plants) < 2:
            continue
        members = []
        for plant in plants:
            for entry in plant.entries:
                rel = relation_of(uni, entry.key)
                members.append({"key": entry.key, "source": entry.source, "name": entry.name, "author": entry.author,
                                "relation": RELATION_LABEL[rel], "plant": plant.id,
                                "result": "fusionado" if plant.kind == "resolved" else "planta propia"})
        accepted_name = uni.resolutions[plants[0].entries[0].key]["accepted_name"]
        split = any(p.split for p in plants)
        groups.append({"accepted": accepted_name, "acceptedKey": akey, "split": split,
                       "heterotypicSplit": any(p.kind == "heterotypic" for p in plants),
                       "plants": [p.id for p in plants], "members": members})
    return groups


def build_report(uni, entries_summary, inputs, catalog_ids):
    plants_by_kind = {}
    for plant in uni.plants:
        plants_by_kind[plant.kind] = plants_by_kind.get(plant.kind, 0) + 1
    usda_routes, all_routes = {}, {}
    for key, res in uni.resolutions.items():
        route = _resolution_route(res)
        if route:
            all_routes[route] = all_routes.get(route, 0) + 1
            if uni.entries[key].source == "usda":
                usda_routes[route] = usda_routes.get(route, 0) + 1
    review = {"ambiguous": [], "unresolved": [], "genus_only": [], "wfo_fallback": [], "orthographic_variant": [],
              "fuzzy_match": [], "accepted_above_species": [], "backbone_disagreement": []}
    disagreement = {"rango": 0, "especie": 0}
    for key in sorted(uni.resolutions, key=lambda k: (uni.entries[k].source, k)):
        res, entry = uni.resolutions[key], uni.entries[key]
        base = {"key": key, "name": entry.name, "author": entry.author}
        if res["outcome"] == "ambiguous":
            review["ambiguous"].append(dict(base, notes=res["notes"]))
        elif res["outcome"] in ("unresolved", "unmatched"):
            review["unresolved"].append(dict(base, outcome=res["outcome"], notes=res["notes"]))
            if "accepted_above_species" in res["flags"]:
                review["accepted_above_species"].append(dict(base, matched=res["matched_name"], notes=res["notes"]))
        elif res["outcome"] == "genus_only":
            review["genus_only"].append(base)
        else:
            flags = set(res["flags"])
            if "wfo_fallback" in flags:
                review["wfo_fallback"].append(dict(base, accepted=res["accepted_name"], backbone=res["backbone"]))
            if "fuzzy_match" in flags:
                review["fuzzy_match"].append(dict(base, matched=res["matched_name"], accepted=res["accepted_name"],
                                                  acceptedId=res["accepted_id"], backbone=res["backbone"],
                                                  distance=res["fuzzy"]["distance"], kind=res["fuzzy"]["kind"],
                                                  fuzzyKey=res["fuzzy"]["key"]))
            if "orthographic_variant" in flags:
                review["orthographic_variant"].append(dict(base, matched=res["matched_name"], accepted=res["accepted_name"]))
            if "backbone_disagreement" in flags:
                kind = classify_disagreement(res)
                disagreement[kind] += 1
                review["backbone_disagreement"].append(dict(base, wcvp=res["accepted_name"], wfo=res.get("wfo_accepted_name"),
                                                            difference=kind))
    groups = _collision_groups(uni)
    stats = uni.stats()
    ema_only = [p for p in uni.plants if p.entries and all(e.source == "ema" for e in p.entries)]
    ema_joined = sum(1 for p in uni.plants if {e.source for e in p.entries} == {"usda", "ema"})
    return {
        "format": REPORT_FORMAT,
        "inputs": inputs,
        "entries": dict(entries_summary, outcomes_usda=_outcome_counts(uni, "usda"), outcomes_ema=_outcome_counts(uni, "ema")),
        "routes": {"usda": usda_routes, "all": all_routes},
        "plants": {"total": len(uni.plants), "by_kind": dict(sorted(plants_by_kind.items())),
                   "from_usda": len(uni.plants) - len(ema_only), "ema_only": len(ema_only), "usda_and_ema": ema_joined,
                   "ambiguous": stats["ambiguous"], "genus_only": stats["genus_only"], "unresolved": stats["unresolved"],
                   "with_aliases": sum(1 for p in uni.plants if p.aliases),
                   "aliases": sum(len(p.aliases) for p in uni.plants), "discarded_aliases": len(uni.discarded_aliases)},
        "collisions": {"groups_with_several_entries": len(groups), "split_groups": sum(1 for g in groups if g["split"]),
                       "groups_with_heterotypic_split": sum(1 for g in groups if g["heterotypicSplit"]),
                       "unassigned_rows": len(uni.unassigned)},
        "backbone_disagreement": dict(disagreement, total=disagreement["rango"] + disagreement["especie"]),
        "comparison_with_current": compare_with_current(uni, catalog_ids),
        "checks": checks_of(uni),
        "ema_modified_cells": entries_summary.get("ema_modified_cells", []),
        "review": review,
        "discarded_aliases": [{"plant": p, "alias": a, "reason": r} for p, a, r in uni.discarded_aliases],
        "collision_groups": groups,
    }


def checks_of(uni):
    ids = [p.id for p in uni.plants]
    return {"duplicate_ids": len(ids) - len(set(ids)), PILOT_CHECK_ID: PILOT_CHECK_ID in set(ids)}


# --- report.md ------------------------------------------------------------------------------------------------------

def _author(item):
    return (" " + item["author"]) if item.get("author") else ""


def _plain(value):
    return str(value).replace("\n", " ").strip()


def render_markdown(report):
    out = ["# Universo de plantas: informe de resolución", ""]
    inputs = report["inputs"]
    out.append("Generado por `python3 -I tools/catalog-seed/cli.py resolve`. Insumos: WCVP `%s`, WFO `%s`, USDA «%s», EMA «%s»."
               % (inputs["wcvp"], inputs["wfo"], inputs.get("usda") or "?", inputs.get("ema_json") or "?"))
    out.append("")
    e, p, c = report["entries"], report["plants"], report["collisions"]
    out += ["## Cifras", "",
            "- Entradas: %d de USDA y %d de la EMA (%d fichas; %d sin especies, entre ellas las combinaciones)."
            % (e["usda_entries"], e["ema_entries"], e["ema_fiches"], len(e["ema_fiches_without_species"])),
            "- Resultado de las entradas de USDA: %s." % ", ".join("%s %d" % kv for kv in e["outcomes_usda"].items()),
            "- Resultado de las entradas de la EMA: %s." % ", ".join("%s %d" % kv for kv in e["outcomes_ema"].items()),
            "- Coincidencias aproximadas (`fuzzy_match`): %d; con aceptado de rango superior a especie: %d."
            % (len(report["review"]["fuzzy_match"]), len(report["review"]["accepted_above_species"])),
            "- Vía de resolución de las entradas de USDA: %s." % ", ".join("%s %d" % kv for kv in sorted(report["routes"]["usda"].items())),
            "- Plantas: %d (%s)." % (p["total"], ", ".join("%s %d" % kv for kv in p["by_kind"].items())),
            "- Plantas con entradas de USDA: %d; solo de la EMA: %d; con ambas: %d." % (p["from_usda"], p["ema_only"], p["usda_and_ema"]),
            "- Alias: %d en %d plantas; descartados: %d." % (p["aliases"], p["with_aliases"], p["discarded_aliases"]),
            "- Grupos donde varias entradas resolvieron al mismo aceptado: %d; partidos: %d; con al menos un heterotípico partido: %d."
            % (c["groups_with_several_entries"], c["split_groups"], c["groups_with_heterotypic_split"]),
            "- Discrepancias de backbone: %d (%d solo de rango infraespecífico, %d de especie)."
            % (report["backbone_disagreement"]["total"], report["backbone_disagreement"]["rango"], report["backbone_disagreement"]["especie"]),
            "- Comprobaciones: IDs repetidos %d; `%s` %s."
            % (report["checks"]["duplicate_ids"], PILOT_CHECK_ID, "presente" if report["checks"][PILOT_CHECK_ID] else "AUSENTE")]
    cmp = report["comparison_with_current"]
    if cmp:
        out.append("- Contra los IDs actuales de `data/build/catalog.db` (%d): %d IDs del universo no están entre ellos; %d IDs actuales se conservan, "
                   "%d pasan a alias y %d no quedan como ID ni como alias." % (
                       cmp["current_ids"], cmp["ids_not_in_current"], cmp["current_ids_kept_as_id"],
                       cmp["current_ids_kept_as_alias"], len(cmp["current_ids_lost"])))
    out.append("")
    review = report["review"]

    def section(title, items, line):
        out.append("## %s (%d)" % (title, len(items)))
        out.append("")
        out.extend(line(i) for i in items) if items else out.append("Ninguno.")
        out.append("")

    cells = report["ema_modified_cells"]
    out.append("## Celdas de la EMA modificadas (%d)" % len(cells))
    out.append("")
    out.append("Reglas: una celda que empieza por «Combination» no aporta especies; los grupos `(syn. ...)` y los fragmentos `syn. ...` se descartan; `(various species)` y `and Género (various species)` se descartan; `Género [various species including G. a L.; G. b L.]` se expande a las especies listadas; un grupo final entre paréntesis tras el autor (sinónimo o nota) se quita del autor, salvo el autor del basiónimo al principio (`(L.) Moench`).")
    out.append("")
    for c in cells:
        out.append("- `%s`: «%s» pasa a [%s]; cambios: %s" % (
            c["fiche"], _plain(c["cell"]), "; ".join(("%s%s" % (e["name"], (" " + e["author"]) if e["author"] else "")) for e in c["entries"]) or "sin especies",
            " | ".join(_plain(x) for x in c["changes"])))
    out.append("")
    section("Homónimos ambiguos", review["ambiguous"],
            lambda i: "- `%s` %s%s: %s" % (i["key"], i["name"], _author(i), _plain(i["notes"])))
    section("Sin resolver", review["unresolved"],
            lambda i: "- `%s` %s%s (%s): %s" % (i["key"], i["name"], _author(i), i["outcome"], _plain(i["notes"])))
    section("Solo género", review["genus_only"], lambda i: "- `%s` %s" % (i["key"], i["name"]))
    section("Respaldo de WFO", review["wfo_fallback"],
            lambda i: "- `%s` %s%s resuelve a %s (WFO)" % (i["key"], i["name"], _author(i), i["accepted"]))
    section("Aceptado de rango superior a especie (accepted_above_species)", review["accepted_above_species"],
            lambda i: "- `%s` %s%s: %s" % (i["key"], i["name"], _author(i), _plain(i["notes"])))
    section("Coincidencia aproximada (fuzzy_match)", review["fuzzy_match"],
            lambda i: "- `%s` %s%s -> %s (distancia %d, %s), aceptado %s (%s %s)" % (
                i["key"], i["name"], _author(i), i["matched"], i["distance"], i["kind"], i["accepted"], i["backbone"], i["acceptedId"]))
    section("Variante ortográfica", review["orthographic_variant"],
            lambda i: "- `%s` %s%s coincide con %s, aceptado %s" % (i["key"], i["name"], _author(i), i["matched"], i["accepted"]))
    section("Discrepancia entre backbones (backbone_disagreement)", review["backbone_disagreement"],
            lambda i: "- `%s` %s%s: WCVP acepta %s, WFO acepta %s [%s]" % (
                i["key"], i["name"], _author(i), i["wcvp"], i["wfo"],
                "solo rango infraespecífico" if i["difference"] == "rango" else "especie distinta"))
    out.append("Las discrepancias «solo rango infraespecífico» son las que acepta el mismo binomio en los dos backbones y difieren únicamente en la variedad o subespecie (WCVP acepta la variedad y WFO la especie, o al revés). No cambian la planta.")
    out.append("")
    section("Alias descartados", report["discarded_aliases"],
            lambda i: "- `%s`: alias `%s` descartado, %s" % (i["plant"], i["alias"], i["reason"]))

    groups = report["collision_groups"]
    out.append("## Grupos de colisión (%d)" % len(groups))
    out.append("")
    out.append("Cada grupo reúne varias entradas que resolvieron al mismo aceptado. Relación: aceptado (el propio aceptado), homotípico (se fusiona con el aceptado) o heterotípico (planta propia con flag de revisión cuando el grupo se parte).")
    out.append("")
    out.append("Grupos con al menos un heterotípico partido: %d." % report["collisions"]["groups_with_heterotypic_split"])
    out.append("")
    split_groups = [g for g in groups if g["split"]]
    merged_groups = [g for g in groups if not g["split"]]

    def render_group(g):
        out.append("- Aceptado **%s**: %s" % (g["accepted"], "partido en %s" % ", ".join("`%s`" % i for i in g["plants"])
                                              if g["split"] else "una sola planta `%s`" % g["plants"][0]))
        for m in g["members"]:
            out.append("  - `%s` %s%s: %s; %s `%s`" % (m["key"], m["name"], _author(m), m["relation"], m["result"], m["plant"]))

    out.append("### Grupos partidos (%d)" % len(split_groups))
    out.append("")
    for g in split_groups:
        render_group(g)
    out.append("")
    out.append("### Grupos fusionados (%d)" % len(merged_groups))
    out.append("")
    for g in merged_groups:
        render_group(g)
    out.append("")
    return "\n".join(out)


# --- Orquestación ---------------------------------------------------------------------------------------------------

def _dump(path, document):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")


def run_resolve(sources, cache_dir, db_path, taxonomy_db, out_dir, catalog_db=None, force_index=False, log=print):
    """Devuelve (universe_document, report) y escribe universe.json, report.json y report.md en `out_dir`."""
    started = time.time()
    if not os.path.isfile(str(db_path)):
        raise SourceError("no existe %s; ejecute primero: python3 -I tools/catalog-seed/cli.py extract" % db_path)
    labels, index_stats = ensure_index(sources, cache_dir, str(taxonomy_db), force=force_index, log=log)
    connection = workdb.open_db(db_path)
    try:
        entries, summary = collect_entries(connection)
        versions = extraction_versions(connection)
    finally:
        connection.close()
    wcvp = open_backbone(str(taxonomy_db), "wcvp")
    wfo = open_backbone(str(taxonomy_db), "wfo")
    try:
        log("resolviendo %d entradas..." % len(entries))
        uni = build_universe(entries, wcvp, wfo)
        inputs = {"wcvp": labels["wcvp"], "wfo": labels["wfo"], "usda": versions.get("usda"), "ema_json": versions.get("ema_json"),
                  "indexVersion": INDEX_VERSION}
        report = build_report(uni, summary, inputs, current_ids(catalog_db))
        if index_stats is not None:
            report["index_build"] = {"wcvp_names": index_stats["wcvp_names"], "wfo_names": index_stats["wfo_names"],
                                     "table_rows": index_stats["table_rows"]}
        document = universe_document(uni, inputs, report["checks"])
    finally:
        wcvp.close()
        wfo.close()
    os.makedirs(str(out_dir), exist_ok=True)
    _dump(os.path.join(str(out_dir), "universe.json"), document)
    _dump(os.path.join(str(out_dir), "report.json"), report)
    with open(os.path.join(str(out_dir), "report.md"), "w", encoding="utf-8") as handle:
        handle.write(render_markdown(report))
    log("universo: %d plantas; salidas en %s (%.0f s)" % (len(document["plants"]), out_dir, time.time() - started))
    return document, report
