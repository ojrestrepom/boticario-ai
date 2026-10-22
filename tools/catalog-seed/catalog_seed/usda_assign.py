"""Asignación de las filas de USDA a las plantas del universo (tarea 3.2).

Los nombres comunes y las partes traen FNFNUM y se asignan por la entrada `usda:<FNFNUM>` del universo. Las filas de uso
(ETHNOBOT) solo traen el nombre (TAXON) y el autor (TAXAUTHOR): se asignan con `Universe.assign`, por resolución taxonómica y
no por nombre exacto, de modo que una fila bajo un sinónimo (*Matricaria recutita*) llega a la planta del aceptado. Cada par distinto
(TAXON, TAXAUTHOR) se resuelve una sola vez, en orden alfabético. Una fila bajo un sinónimo heterotípico fusionado por la regla de
colisiones (*Cinnamomum zeylanicum*) llega a la planta del aceptado en la que se fusionó, tanto por FNFNUM (la entrada `usda:<FNFNUM>`
es de esa planta) como por `Universe.assign` (comparte sus claves). `Universe.assign` registra en el universo (`unassigned` y el flag
`unassigned_rows`) las filas que no puede asignar, así que la llamada tiene ese efecto lateral.

Resultado por planta (`UsdaAssignment.by_plant[plant_id]`, orden estable):

- `commonNames`: `{name, language, ref}` con ref `usda_common_name:<id>`;
- `parts`: `{ppco, ppna, rows, hasEo, eoCompounds, topAmount, topEo, ref}` con ref `usda_part:<id>`;
- `useGroups`: un grupo por actividad con `{activity, n, countries, refs, keys}`; `refs` son `usda_use:<ETHNO>` y `keys` las claves
  cortas de REFERENCE tal como vienen, `{key, n, candidates}`, con las candidatas de `citations.ReferenceIndex` (ref y LONGREF).
"""
import json
import re

from . import workdb
from .citations import MAX_CANDIDATES, ReferenceIndex

SOURCE = "usda"
NO_ACTIVITY = ""
NO_REFERENCE = ""


def _natural(text):
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", text) if p]


class UsdaAssignment(object):
    def __init__(self):
        self.by_plant = {}
        self.unassigned = []   # dicts: kind, reason, name, author, rows, examples
        self.stats = {}

    def to_dict(self):
        """Documento determinista (se puede hashear con claves ordenadas)."""
        return {"plants": {k: self.by_plant[k] for k in sorted(self.by_plant)}, "unassigned": self.unassigned, "stats": self.stats}

    def canonical(self):
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _plant_entry_map(uni):
    return {entry.key: plant for plant in uni.plants for entry in plant.entries}


def _bucket(by_plant, plant):
    return by_plant.setdefault(plant.id, {"commonNames": [], "parts": [], "useGroups": []})


def assign_usda(uni, connection, max_candidates=MAX_CANDIDATES):
    """Asigna las filas de USDA de `sources.db` a las plantas de `uni`. Devuelve un `UsdaAssignment`."""
    result = UsdaAssignment()
    by_plant = result.by_plant
    entry_plant = _plant_entry_map(uni)
    unassigned_fnf = {}

    def assign_by_fnfnum(kind, rows):
        for row in rows:
            plant = entry_plant.get("usda:%s" % row["fnfnum"])
            if plant is None:
                item = unassigned_fnf.setdefault((kind, row["fnfnum"]), {"kind": kind, "reason": "fnfnum-sin-planta", "name": row["raw_name_cell"] or "",
                                                                      "author": "", "rows": 0, "examples": []})
                item["rows"] += 1
                item["examples"].append(row["row_key"])
                continue
            yield plant, row

    names = workdb.fetch_rows(connection, SOURCE, "usda_common_name")
    for plant, row in assign_by_fnfnum("usda_common_name", names):
        c = row["content"]
        _bucket(by_plant, plant)["commonNames"].append({"name": c.get("name") or row["raw_name_cell"] or "", "language": c.get("language"),
                                                       "ref": "usda_common_name:%s" % row["row_key"]})
    parts = workdb.fetch_rows(connection, SOURCE, "usda_part")
    for plant, row in assign_by_fnfnum("usda_part", parts):
        c = row["content"]
        _bucket(by_plant, plant)["parts"].append({
            "ppco": c.get("ppco"), "ppna": c.get("ppna"), "rows": c.get("rows"), "hasEo": bool(c.get("has_eo")),
            "eoCompounds": c.get("eo_compounds", []), "distinctCompounds": c.get("distinct_compounds"),
            "topAmount": c.get("top_amount", []), "topEo": c.get("top_eo", []), "ref": "usda_part:%s" % row["row_key"]})

    references = [dict(r["content"], reference=r["content"].get("reference") or r["row_key"]) for r in workdb.fetch_rows(connection, SOURCE, "usda_reference")]
    index = ReferenceIndex(references)

    uses = workdb.fetch_rows(connection, SOURCE, "usda_use")
    pairs = {}
    for row in uses:
        pairs.setdefault((row["raw_name_cell"] or row["content"].get("taxon") or "", (row["content"].get("taxauthor") or "").strip()), []).append(row)
    pair_plant = {}
    reasons_assigned, unassigned_pairs = {}, []
    for pair in sorted(pairs):
        name, author = pair
        plant, reason = uni.assign(name, author=author or None, source="usda_use")
        rows = pairs[pair]
        if plant is None:
            unassigned_pairs.append({"kind": "usda_use", "reason": reason, "name": name, "author": author, "rows": len(rows),
                                     "examples": sorted((r["row_key"] for r in rows), key=_natural)[:5]})
            continue
        pair_plant[pair] = plant
        reasons_assigned[reason] = reasons_assigned.get(reason, 0) + len(rows)

    grouped = {}   # (plant id, activity) -> acumuladores
    for pair, plant in pair_plant.items():
        for row in pairs[pair]:
            c = row["content"]
            group = grouped.setdefault((plant.id, c.get("activity") or NO_ACTIVITY), {"refs": [], "countries": set(), "keys": {}})
            group["refs"].append(row["row_key"])
            if c.get("country"):
                group["countries"].add(c["country"])
            key = (c.get("reference") or NO_REFERENCE).strip()
            group["keys"][key] = group["keys"].get(key, 0) + 1
    for (plant_id, activity) in sorted(grouped):
        group = grouped[(plant_id, activity)]
        keys = [{"key": k, "n": n, "candidates": index.candidates(k, max_candidates) if k else []}
                for k, n in sorted(group["keys"].items(), key=lambda kv: (-kv[1], kv[0]))]
        bucket = by_plant.setdefault(plant_id, {"commonNames": [], "parts": [], "useGroups": []})
        bucket["useGroups"].append({"activity": activity, "n": len(group["refs"]), "countries": sorted(group["countries"]),
                                    "refs": ["usda_use:%s" % r for r in sorted(group["refs"], key=_natural)], "keys": keys})
    for bucket in by_plant.values():
        bucket["commonNames"].sort(key=lambda x: (x["name"], x["ref"]))
        bucket["parts"].sort(key=lambda x: (x["ppco"] or "", x["ref"]))

    result.unassigned = sorted(unassigned_fnf.values(), key=lambda i: (i["kind"], i["name"])) + unassigned_pairs
    used_keys = {}
    for bucket in by_plant.values():
        for group in bucket["useGroups"]:
            for k in group["keys"]:
                used_keys[k["key"]] = k["candidates"]
    unassigned_rows = {}
    for item in unassigned_pairs:
        unassigned_rows[item["reason"]] = unassigned_rows.get(item["reason"], 0) + item["rows"]
    assigned_rows = sum(reasons_assigned.values())
    result.stats = {
        "use_rows": len(uses), "use_rows_assigned": assigned_rows, "use_rows_unassigned": len(uses) - assigned_rows,
        "use_rows_assigned_by_reason": dict(sorted(reasons_assigned.items())),
        "use_rows_unassigned_by_reason": dict(sorted(unassigned_rows.items())),
        "use_pairs": len(pairs), "use_pairs_unassigned": len(unassigned_pairs),
        "common_names": len(names), "parts": len(parts),
        "unassigned_by_fnfnum": sum(i["rows"] for i in unassigned_fnf.values()),
        "plants_with_data": len(by_plant),
        "short_keys": len([k for k in used_keys if k]),
        "short_keys_with_candidates": len([k for k, c in used_keys.items() if k and c]),
        "short_keys_without_candidates": len([k for k, c in used_keys.items() if k and not c]),
    }
    return result
