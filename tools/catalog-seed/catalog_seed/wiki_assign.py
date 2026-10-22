"""Nombres a consultar y asignación de los ítems de Wikidata, Wikipedia en español y Commons a las plantas del universo.

Las descargas son por nombre científico, no por planta, para que sigan valiendo si cambian los grupos de colisión. La asignación se
recalcula sin red desde la caché y desde `universe.json`:

- Cada ítem de Wikidata trae su nombre (P225). Ese nombre se resuelve con `resolve_name` (con el autor de Wikidata como desempate)
  y el ítem se asigna a la planta cuyo aceptado es el resultado; si ninguna planta lo tiene, queda sin asignar con su motivo. Es el
  filtro de homónimos: un ítem de *Lavandula latifolia* no llega a *Lavandula angustifolia* porque su nombre resuelve a otro aceptado.
- En un grupo partido (varias plantas con el mismo aceptado) el ítem va a la planta del mismo nombre, o a la que contiene al
  aceptado si el nombre es el propio aceptado o un sinónimo homotípico. Un sinónimo heterotípico fusionado por la regla de colisiones
  (`fusedMatchedIds` de la planta en `universe.json`) va a la planta del aceptado en la que se fusionó; uno sin planta propia ni
  fusión queda sin asignar (`heterotipico-sin-planta`).
- Wikipedia y Commons se asignan por el ítem que las enlaza (sitelink de eswiki y P18), así que heredan su planta.
"""
from .licenses import MISSING, classify
from .taxonomy import resolve_name
from .taxonomy.universe import RESOLVED, UNRESOLVED_KINDS, classify_relation
from .wiki import commons_title, normalize_name

ASSIGNMENT_FORMAT = "catalog-wiki-assignment/1"
# Homónimos del piloto: se consultan como control para comprobar el filtro con datos reales (no pertenecen a ninguna planta).
CONTROL_NAMES = ("Lavandula latifolia", "Passiflora edulis")
IPNI_PREFIX = "urn:lsid:ipni.org:names:"

STATUS_WITH_ITEM = "con-item"
STATUS_NO_ITEM = "sin-item"
STATUS_NO_RESPONSE = "sin-respuesta"
STATUS_NOT_QUERIED = "no-consultada"


# --- Nombres a consultar --------------------------------------------------------------------------------------------

def load_plants(universe):
    return universe["plants"]


def _queryable(plant):
    return plant["kind"] not in UNRESOLVED_KINDS and plant.get("backbone") and plant.get("acceptedId")


def plant_names(plant, wcvp):
    """Nombres a consultar de una planta: su nombre, los de sus entradas y, en WCVP, el aceptado y sus sinónimos homotípicos."""
    if not _queryable(plant):
        return []
    names = [plant["name"]]
    for entry in plant["entries"]:
        names.append(entry["name"])
        if entry.get("matchedName"):
            names.append(entry["matchedName"])
    if plant["backbone"] == "wcvp" and plant["kind"] == "resolved" and wcvp is not None:
        accepted = wcvp.get(plant["acceptedId"])
        if accepted:
            names.append(accepted["name"])
        for row in wcvp.synonyms(plant["acceptedId"]):
            if row["status"] == "Synonym" and row["homotypic"] == "T" and " " in row["name"]:
                names.append(row["name"])
    out = []
    for name in names:
        name = normalize_name(name)
        if " " in name and name not in out:
            out.append(name)
    return out


def build_name_plan(universe, wcvp, controls=CONTROL_NAMES):
    """`{names, byName, byPlant}`: los nombres a consultar (sin repetir, en orden estable) y qué plantas los piden."""
    names, by_name, by_plant = [], {}, {}
    for plant in load_plants(universe):
        plant_list = plant_names(plant, wcvp)
        by_plant[plant["id"]] = plant_list
        for name in plant_list:
            if name not in by_name:
                by_name[name] = []
                names.append(name)
            by_name[name].append(plant["id"])
    for name in controls:
        name = normalize_name(name)
        if name not in by_name:
            by_name[name] = []
            names.append(name)
    return {"names": names, "byName": by_name, "byPlant": by_plant}


# --- Asignación de ítems --------------------------------------------------------------------------------------------

class PlantIndex:
    """Plantas del universo por (backbone, aceptado)."""

    def __init__(self, universe):
        self.by_accepted = {}
        self.by_id = {}
        for plant in load_plants(universe):
            self.by_id[plant["id"]] = plant
            if _queryable(plant):
                self.by_accepted.setdefault((plant["backbone"], str(plant["acceptedId"])), []).append(plant)

    def group(self, backbone, accepted_id):
        return self.by_accepted.get((backbone, str(accepted_id)), [])


def _author_of(item):
    authors = item.get("authors") or []
    return authors[0] if len(authors) == 1 else None


class Assigner:
    """Resuelve los nombres (P225) con el resolvedor y los asigna a plantas. Memoriza cada resolución."""

    def __init__(self, universe, wcvp, wfo):
        self.index = PlantIndex(universe)
        self.wcvp = wcvp
        self.wfo = wfo
        self.cache = {}

    def resolve(self, taxon, author):
        key = (taxon, author or "")
        if key not in self.cache:
            self.cache[key] = resolve_name(taxon, self.wcvp, self.wfo, author=author or None)
        return self.cache[key]

    def assign(self, item):
        """`{plantId, reason, ...}` de un ítem de Wikidata. `plantId` es None si el ítem no entra en ninguna planta."""
        taxon = normalize_name(item.get("taxon") or "")
        out = {"plantId": None, "reason": None, "taxon": taxon, "outcome": None, "acceptedName": None, "acceptedId": None,
               "backbone": None, "matchedName": None, "flags": []}
        if not taxon:
            out["reason"] = "sin-nombre"
            return out
        res = self.resolve(taxon, _author_of(item))
        out.update(outcome=res["outcome"], acceptedName=res["accepted_name"] or None, acceptedId=res["accepted_id"] or None,
                   backbone=res["backbone"], matchedName=res["matched_name"] or None, flags=sorted(res["flags"]))
        if res["outcome"] not in RESOLVED:
            out["reason"] = "ambiguo" if res["outcome"] == "ambiguous" else "sin-resolver"
            return out
        if res.get("fallback_binomial"):
            out["reason"] = "rango-inferior-sin-coincidencia"
            return out
        group = self.index.group(res["backbone"], res["accepted_id"])
        if not group:
            out["reason"] = "fuera-del-universo"
            return out
        if len(group) == 1:
            out["plantId"], out["reason"] = group[0]["id"], "grupo-unico"
            return out
        for plant in group:
            if plant.get("matchedId") and str(plant["matchedId"]) == str(res["matched_id"]):
                out["plantId"], out["reason"] = plant["id"], "misma-clave"
                return out
        fused_id = "%s:%s" % (res["backbone"], res["matched_id"])
        for plant in group:
            if fused_id in (plant.get("fusedMatchedIds") or []):
                out["plantId"], out["reason"] = plant["id"], "heterotipico-fusionado"
                return out
        backbone = self.wcvp if res["backbone"] == "wcvp" else self.wfo
        relation = classify_relation(backbone.get(res["matched_id"]), backbone.get(res["accepted_id"]), res["backbone"])
        if relation in ("A", "H"):
            for plant in group:
                if not plant.get("matchedId"):
                    out["plantId"], out["reason"] = plant["id"], "aceptado" if relation == "A" else "homotipico"
                    return out
        out["reason"] = "heterotipico-sin-planta"
        return out

    def ipni_evidence(self, item, assigned):
        """Contrasta P961/P5037 con los `ipni_id` de WCVP del aceptado y sus sinónimos: coincide, discrepa o sin-dato."""
        ids = set()
        for value in list(item.get("ipni") or []) + list(item.get("powo") or []):
            ids.add(value[len(IPNI_PREFIX):] if value.startswith(IPNI_PREFIX) else value)
        if not ids:
            return "sin-dato"
        if assigned.get("backbone") != "wcvp" or not assigned.get("acceptedId"):
            return "sin-dato"
        known = set()
        accepted = self.wcvp.get(assigned["acceptedId"])
        if accepted and accepted.get("source_id"):
            known.add(str(accepted["source_id"]))
        for row in self.wcvp.synonyms(assigned["acceptedId"]):
            if row.get("source_id"):
                known.add(str(row["source_id"]))
        return "coincide" if ids & known else "discrepa"


# --- Documento de asignación ----------------------------------------------------------------------------------------

def _wikidata_items(step):
    """Ítems de la caché de Wikidata por QID, con los nombres consultados que los devolvieron."""
    items = {}
    for key, response in step.iter_cached():
        for item in response.get("items", []):
            current = items.setdefault(item["qid"], dict(item, queried=[]))
            if key not in current["queried"]:
                current["queried"].append(key)
    return items


def _commons_record(step, title):
    """Clasifica una imagen de la caché de Commons. None si no se ha consultado."""
    if not step.is_cached(title):
        return None
    response = step.load(title)
    if response.get("missing"):
        return {"title": title, "admitted": False, "reason": MISSING}
    result = classify(response["imageinfo"].get("extmetadata"))
    info = response["imageinfo"]
    result.update(title=response.get("title", title), pageUrl=info.get("descriptionurl"), fileUrl=info.get("url"),
                  mime=info.get("mime"), width=info.get("width"), height=info.get("height"))
    return result


def build_assignment(universe, wcvp, wfo, name_plan, steps, enabled=None):
    """Asigna los ítems de la caché a las plantas. `steps` = {servicio: Step} (solo se lee la caché, nunca la red).

    `enabled` dice qué fuentes están activas: una fuente desactivada no aporta nada al resultado.
    """
    enabled = enabled or {"wikidata": True, "wikipedia_es": True, "commons": True}
    assigner = Assigner(universe, wcvp, wfo)
    wikidata = steps["wikidata"]
    plants = {p["id"]: {"wikidata": {"status": None, "items": []}, "spanishNames": [], "wikipedia": [],
                        "commons": {"admitted": [], "discarded": []}} for p in load_plants(universe)}
    items_out = {}
    wiki_items = _wikidata_items(wikidata) if enabled.get("wikidata") else {}
    if wiki_items:
        for qid, item in sorted(wiki_items.items()):
            result = assigner.assign(item)
            requested = sorted({pid for name in item["queried"] for pid in name_plan["byName"].get(name, [])})
            result.update(requestedFor=requested, ipni=assigner.ipni_evidence(item, result) if result["plantId"] else "sin-dato",
                          eswiki=item.get("eswiki") or None, queried=sorted(item["queried"]),
                          hasSpanishAliases=bool(item.get("aliasesEs")))
            result["homonym"] = bool(requested) and result["plantId"] not in requested
            items_out[qid] = result
            if result["plantId"]:
                plants[result["plantId"]]["wikidata"]["items"].append(qid)
                for name in item.get("spanishNames") or []:
                    if name not in plants[result["plantId"]]["spanishNames"]:
                        plants[result["plantId"]]["spanishNames"].append(name)
    for pid, plant in plants.items():
        names = name_plan["byPlant"].get(pid, [])
        if not names:
            plant["wikidata"]["status"] = STATUS_NOT_QUERIED
        elif plant["wikidata"]["items"]:
            plant["wikidata"]["status"] = STATUS_WITH_ITEM
        elif not enabled.get("wikidata") or not any(wikidata.is_cached(name) for name in names):
            plant["wikidata"]["status"] = STATUS_NO_RESPONSE
        else:
            plant["wikidata"]["status"] = STATUS_NO_ITEM
    pending_wikipedia, pending_commons = [], []
    for qid, result in items_out.items():
        if not result["plantId"]:
            continue
        item = wiki_items[qid]
        plant = plants[result["plantId"]]
        if enabled.get("wikipedia_es") and item.get("eswiki"):
            wiki = steps["wikipedia_es"]
            title = wiki.key_of(item["eswiki"])
            if not wiki.is_cached(title):
                pending_wikipedia.append(title)
            else:
                response = wiki.load(title)
                if response.get("missing"):
                    state = "sin-articulo"
                else:
                    state = "ok" if response.get("type") == "standard" else response.get("type", "otro")
                result["wikipedia"] = {"title": response.get("title", title), "state": state}
                if state == "ok":
                    plant["wikipedia"].append({"title": response["title"], "qid": qid,
                                               "wikibaseItem": response.get("wikibase_item")})
        if enabled.get("commons"):
            commons = steps["commons"]
            for image in item.get("images") or []:
                title = commons_title(image)
                record = _commons_record(commons, title)
                if record is None:
                    pending_commons.append(title)
                    continue
                entry = {"title": record["title"], "qid": qid}
                if record["admitted"]:
                    entry.update(license=record["license"], licenseCode=record["licenseCode"])
                    plant["commons"]["admitted"].append(entry)
                else:
                    entry["reason"] = record["reason"]
                    plant["commons"]["discarded"].append(entry)
    return {"format": ASSIGNMENT_FORMAT, "universe": universe.get("inputs"),
            "sources": {k: bool(enabled.get(k)) for k in ("wikidata", "wikipedia_es", "commons")},
            "items": items_out, "plants": plants,
            "pending": {"wikipedia_es": sorted(set(pending_wikipedia)), "commons": sorted(set(pending_commons))}}


def pending_downloads(universe, wcvp, wfo, name_plan, steps, enabled):
    """Lo que falta descargar de Wikipedia y Commons para los ítems que pasan el filtro (desde la caché de Wikidata)."""
    document = build_assignment(universe, wcvp, wfo, name_plan, steps, enabled)
    return document["pending"]["wikipedia_es"], document["pending"]["commons"], document


# --- Cifras e informe -----------------------------------------------------------------------------------------------

def summarize(document, name_plan=None):
    """Cifras del informe: plantas por estado, con nombre en español, resumen e imagen, y descartes."""
    plants = document["plants"]
    items = document["items"]
    statuses = {}
    for plant in plants.values():
        statuses[plant["wikidata"]["status"]] = statuses.get(plant["wikidata"]["status"], 0) + 1
    discard_reasons, images_discarded = {}, {}
    for plant in plants.values():
        for image in plant["commons"]["discarded"]:
            images_discarded[image["reason"]] = images_discarded.get(image["reason"], 0) + 1
    for reason in {i["reason"] for i in items.values() if not i["plantId"]}:
        discard_reasons[reason] = sum(1 for i in items.values() if not i["plantId"] and i["reason"] == reason)
    with_item = [p for p in plants.values() if p["wikidata"]["items"]]
    only_discarded = sum(1 for p in plants.values() if p["commons"]["discarded"] and not p["commons"]["admitted"])
    ipni = {}
    for item in items.values():
        if item["plantId"]:
            ipni[item["ipni"]] = ipni.get(item["ipni"], 0) + 1
    return {
        "plants": len(plants), "plantsByWikidataStatus": dict(sorted(statuses.items())),
        "items": len(items), "itemsAssigned": sum(1 for i in items.values() if i["plantId"]),
        "itemsUnassignedByReason": dict(sorted(discard_reasons.items())),
        "itemsDiscardedAsHomonym": sum(1 for i in items.values() if i["homonym"] and not i["plantId"]),
        "itemsMovedToOtherPlant": sum(1 for i in items.values() if i["homonym"] and i["plantId"]),
        "plantsWithWikidataItem": len(with_item),
        "plantsWithSpanishName": sum(1 for p in plants.values() if p["spanishNames"]),
        "plantsWithSpanishNameOrAlias": sum(
            1 for p in plants.values() if p["spanishNames"] or any(
                items[q]["hasSpanishAliases"] for q in p["wikidata"]["items"])),
        "plantsWithWikipedia": sum(1 for p in plants.values() if p["wikipedia"]),
        "plantsWithAdmittedImage": sum(1 for p in plants.values() if p["commons"]["admitted"]),
        "plantsWithDiscardedImage": sum(1 for p in plants.values() if p["commons"]["discarded"]),
        "plantsWithOnlyDiscardedImages": only_discarded,
        "imagesDiscardedByReason": dict(sorted(images_discarded.items())),
        "ipniEvidence": dict(sorted(ipni.items())),
        "pendingWikipedia": len(document["pending"]["wikipedia_es"]),
        "pendingCommons": len(document["pending"]["commons"]),
    }


def homonym_examples(document, limit=12):
    """Ítems pedidos para una planta cuyo nombre no resuelve a su aceptado, en dos grupos.

    `discarded`: no entran en ninguna planta (el homónimo propiamente dicho, como *Passiflora edulis* pedido por la pasiflora).
    `moved`: entran en otra planta del universo (como *Lavandula latifolia* pedido por la lavanda, que va a su propia planta).
    """
    groups = {"discarded": [], "moved": []}
    for qid, item in document["items"].items():
        if item["homonym"]:
            groups["moved" if item["plantId"] else "discarded"].append(
                {"qid": qid, "taxon": item["taxon"], "requestedFor": item["requestedFor"], "plantId": item["plantId"],
                 "reason": item["reason"], "resolvedTo": item["acceptedName"]})
    return {"discarded": groups["discarded"][:limit], "discardedTotal": len(groups["discarded"]),
            "moved": groups["moved"][:limit], "movedTotal": len(groups["moved"])}


def control_checks(document, checks=(("lavandula-angustifolia", "Lavandula latifolia"),
                                     ("passiflora-incarnata", "Passiflora edulis"))):
    """Para cada planta del piloto: ningún ítem asignado lleva el nombre del homónimo, y qué pasó con el ítem del homónimo."""
    out = {}
    for plant_id, homonym in checks:
        plant = document["plants"].get(plant_id)
        assigned = [q for q in (plant["wikidata"]["items"] if plant else [])]
        taxa = {q: document["items"][q]["taxon"] for q in assigned}
        homonym_items = {q: {"plantId": i["plantId"], "reason": i["reason"], "acceptedName": i["acceptedName"]}
                         for q, i in document["items"].items() if i["taxon"] == homonym}
        out[plant_id] = {"homonym": homonym, "plantItems": taxa, "homonymItems": homonym_items,
                         "ok": plant is not None and homonym not in taxa.values()
                         and all(i["plantId"] != plant_id for i in homonym_items.values())}
    return out

