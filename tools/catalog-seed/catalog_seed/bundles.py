"""Paquetes por planta (tarea 3.5): la entrada del LLM de la variante A.

Un paquete es una función pura de las filas de `sources.db`, el índice taxonómico, las decisiones de colisión y la asignación de
Wikidata, Wikipedia y Commons. No abre la red ni lee la fecha: dos construcciones con los mismos insumos dan el mismo JSON canónico y el
mismo `bundleHash` (sha256 del JSON canónico sin el propio `bundleHash`). Forma (véase `schema/bundle.schema.json` y el README):

- raíz: `bundleVersion`, `plantKey`, `bundleHash`, `identity`, `sections` y `refs`;
- `identity`: ID propuesto, la identidad del universo, backbone principal, aceptados de WCVP y de WFO, conjunto de nombres con motivo y
  backbone, colisión, `flags` (objetos `{code, target, message}`) y `notes`;
- `sections`: `taxonomy`, `distribution`, `names`, `descriptions`, `parts`, `uses`, `regulatory`, `safety`, `images` y `wikidata`;
- `refs`: ref (`<record_type>:<row_key>`) a `{dataset, label, license, url?}`. `dataset` es el `id` de la fuente de `sources.json`.

Fuentes desactivadas (D14, tarea 4.7): una fuente con `enabled: false` no aporta filas ni refs. El paquete no declara qué fuentes están
activas (si lo hiciera, cambiaría el hash de todas las plantas): simplemente no trae sus filas, así que desactivar Wikipedia solo cambia
el hash de las plantas que tenían un resumen de Wikipedia. Wikipedia y Commons se asignan por los ítems de Wikidata, de modo que sin
`wikidata` tampoco hay Wikipedia ni Commons.

Asignación de filas a plantas: USDA con `assign_usda`; TPPT y EFSA con `Universe.assign` (EFSA trae varios nombres por celda, separados
por «;» o «$»: una fila va a cada planta distinta a la que llega alguno de sus nombres); las fichas de la EMA por las entradas del
universo (`ema:<slug>#<n>`); Wikidata, Wikipedia y Commons con la asignación de `wiki_assign.py` (filtro de homónimos).
"""
import hashlib
import json
import re
import time
from pathlib import Path

from . import goals as goals_lib
from . import safety, workdb
from .licenses import clean_file_url, is_displayable
from .resolve_universe import universe_document
from .seed import DEFAULT_BUNDLES_DIR, canonical_json
from .sources import SourceError
from .taxonomy.names import split_source_names
from .taxonomy.resolver import resolve as resolve_in_backbone
from .taxonomy.universe import Entry, RESOLVED
from .usda_assign import assign_usda
from .validate import _is_combination

BUNDLE_VERSION = "1"
SECTIONS = ("taxonomy", "distribution", "names", "descriptions", "parts", "uses", "regulatory", "safety", "images", "wikidata")
EMA_SECTIONS = ("4.3", "4.4", "4.5")
CHARS_PER_TOKEN = 3.5

# Topes que acotan el tamaño del paquete (los que no acotan una selección dicen su total en el campo `...Total`).
DEFAULT_LIMITS = {
    "homotypicSynonyms": 15,        # sinónimos homotípicos de WCVP en taxonomy y nameSet
    "nativeAreas": 25,              # nombres de áreas nativas en distribution
    "images": 5,                    # imágenes de Commons admitidas
    "efsaEvidence": 25,             # sustancias de EFSA que son solo evidencia
    "efsaStudies": 10,              # estudios de ENDPOINTSTUDY
    "tpptToxins": 20,               # toxinas de TPPT
    "useGroups": None,              # grupos de uso (por actividad) con más filas (None: todos)
    "useRefs": None,                # refs usda_use:* por grupo de uso (None: todos)
    "useKeys": None,                # claves cortas de cita por grupo de uso (None: todas)
}

EMA_HERBAL = "ema_herbal"
WIKIDATA_URL = "https://www.wikidata.org/wiki/%s"
STATUS_NOT_QUERIED = "no-consultada"
STATUS_NO_RESPONSE = "sin-respuesta"
STATUS_NO_ITEM = "sin-item"
WIKIDATA_FLAGS = {
    STATUS_NOT_QUERIED: ("wikidata-no-consultada", "La planta no tiene nombre aceptado, así que no se consultó Wikidata."),
    STATUS_NO_RESPONSE: ("wikidata-sin-respuesta", "Wikidata no respondió para esta planta (ninguna de sus consultas está en la caché, o Wikidata está desactivada); sin imagen ni nombre en español de Wikidata."),
    STATUS_NO_ITEM: ("wikidata-sin-item", "Wikidata respondió, pero ningún ítem pasa el filtro de homónimos para esta planta."),
}


def bundle_hash(bundle):
    """`sha256:` más el sha256 del JSON canónico del paquete sin su `bundleHash`."""
    body = {k: v for k, v in bundle.items() if k != "bundleHash"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _natural(text):
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", str(text)) if p]


def _dedupe(items):
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


class Refs(object):
    """Diccionario de refs del paquete: cada ref nuevo debe traer dataset, etiqueta y licencia."""

    def __init__(self, licenses):
        self.licenses = licenses
        self.entries = {}

    def add(self, ref, dataset, label, license=None, url=None):
        entry = {"dataset": dataset, "label": label, "license": license or self.licenses[dataset]}
        if url:
            entry["url"] = url
        current = self.entries.get(ref)
        if current is not None and current != entry:
            raise SourceError("el ref %s se registró con dos contenidos distintos: %r y %r" % (ref, current, entry))
        self.entries[ref] = entry
        return ref


# --- Asignación de las filas de TPPT, EFSA y la EMA a las plantas -----------------------------------------------------------

class Rows(object):
    """Filas de `sources.db` asignadas a plantas, por fuente. Una fuente desactivada queda vacía."""

    def __init__(self):
        self.tppt = {}              # id de planta -> [fila]
        self.efsa_botanic = {}
        self.efsa_endpoint = {}
        self.ema_herbal = {}        # slug -> fila
        self.ema_pdf = {}           # slug -> {"doc": fila | None, "sections": {sección: fila}}
        self.wikidata = {}          # QID -> fila
        self.wikipedia = {}         # título -> fila
        self.commons = {}           # título -> fila
        self.stats = {}


def _assign_by_names(uni, rows, splitter, source, stats_key, stats):
    """Asigna filas con una o varias celdas de nombre. Devuelve {id de planta: [fila]}; memoriza la resolución por celda."""
    by_plant, cell_plants = {}, {}
    assigned = unassigned = 0
    for row in rows:
        cell = row["raw_name_cell"] or ""
        if cell not in cell_plants:
            found = []
            for name in splitter(cell):
                plant, _ = uni.assign(name, source=source)
                if plant is not None and plant.id not in found:
                    found.append(plant.id)
            cell_plants[cell] = found
        if cell_plants[cell]:
            assigned += 1
            for plant_id in cell_plants[cell]:
                by_plant.setdefault(plant_id, []).append(row)
        else:
            unassigned += 1
    stats[stats_key] = {"rows": assigned + unassigned, "assigned": assigned, "unassigned": unassigned, "plants": len(by_plant)}
    return by_plant


def load_rows(uni, connection, enabled, log=print):
    """Asigna TPPT y EFSA y carga las filas de la EMA y de los servicios de Wikimedia (solo de fuentes activas)."""
    rows = Rows()
    stats = rows.stats
    if enabled.get("tppt"):
        log("asignando TPPT...")
        rows.tppt = _assign_by_names(uni, workdb.fetch_rows(connection, "tppt", "tppt_plant"),
                                     lambda cell: split_source_names("tppt", cell), "tppt", "tppt", stats)
    if enabled.get("efsa"):
        log("asignando EFSA...")
        rows.efsa_botanic = _assign_by_names(uni, workdb.fetch_rows(connection, "efsa", "efsa_botanic"),
                                             lambda cell: split_source_names("efsa", cell), "efsa", "efsaBotanic", stats)
        rows.efsa_endpoint = _assign_by_names(uni, workdb.fetch_rows(connection, "efsa", "efsa_endpoint"),
                                              lambda cell: split_source_names("efsa", cell), "efsa", "efsaEndpoint", stats)
    if enabled.get("ema_json"):
        rows.ema_herbal = {r["row_key"]: r for r in workdb.fetch_rows(connection, "ema_json", EMA_HERBAL)}
    if enabled.get("ema_pdf"):
        for r in workdb.fetch_rows(connection, "ema_pdf", "ema_pdf_doc"):
            rows.ema_pdf[r["row_key"]] = {"doc": r, "sections": {}}
        for r in workdb.fetch_rows(connection, "ema_pdf", "ema_pdf"):
            slug = r["content"].get("slug")
            if slug in rows.ema_pdf:
                rows.ema_pdf[slug]["sections"][r["content"].get("section")] = r
    if enabled.get("wikidata"):
        rows.wikidata = {r["row_key"]: r for r in workdb.fetch_rows(connection, "wikidata", "wikidata")}
        if enabled.get("wikipedia_es"):
            rows.wikipedia = {r["row_key"]: r for r in workdb.fetch_rows(connection, "wikipedia_es", "wikipedia_es")}
        if enabled.get("commons"):
            rows.commons = {r["row_key"]: r for r in workdb.fetch_rows(connection, "commons", "commons")}
    return rows


# --- Identidad y taxonomía ---------------------------------------------------------------------------------------------------

def _author_text(author):
    return author or ""


class Builder(object):
    """Arma los paquetes de las plantas de un universo ya construido."""

    def __init__(self, uni, sources, safety_map, goals_map, limits=None):
        self.uni = uni
        self.sources = {s.id: s for s in sources}
        self.enabled = {s.id: bool(s.enabled) for s in sources}
        self.licenses = {s.id: s.license for s in sources}
        self.safety_map = safety_map
        self.goals_map = goals_map
        self.limits = dict(DEFAULT_LIMITS, **(limits or {}))
        self.backbones = {"wcvp": uni.wcvp, "wfo": uni.wfo}
        self._other_accepted = {}
        self._ema_view_cache = {}
        self.usda = None
        self.rows = Rows()
        self.wiki = None
        self.docs = {}

    # -- preparación
    def prepare(self, connection, wiki_assigner=None, log=print):
        """Asigna las filas a las plantas y la asignación de Wikidata. Debe llamarse una vez, antes de `build`."""
        if not self.enabled.get("wcvp"):
            raise SourceError("la fuente 'wcvp' está desactivada: los paquetes no se pueden armar sin la taxonomía principal")
        if self.enabled.get("usda"):
            log("asignando USDA...")
            self.usda = assign_usda(self.uni, connection)
        self.rows = load_rows(self.uni, connection, self.enabled, log)
        # Los documentos de planta se leen después de asignar todo: `Universe.assign` marca `unassigned_rows` en los grupos partidos.
        document = universe_document(self.uni, {}, {})
        self.docs = {p["id"]: p for p in document["plants"]}
        if wiki_assigner is not None and self.enabled.get("wikidata"):
            log("asignando Wikidata, Wikipedia y Commons...")
            self.wiki = wiki_assigner(document, dict(self.enabled))
        return self

    # -- filas de taxonomía
    def _row_ref(self, backbone, row, refs):
        label = "%s: %s%s" % (backbone.upper(), row["name"], (" " + row["author"]) if row.get("author") else "")
        return refs.add("%s:%s" % (backbone, row["id"]), backbone, label)

    def _taxon_row(self, backbone, row, role, refs):
        out = {"ref": self._row_ref(backbone, row, refs), "backbone": backbone, "id": row["id"], "name": row["name"],
               "authors": row.get("author") or "", "rank": row.get("rank") or "", "status": row.get("status") or "",
               "family": row.get("family") or "", "role": role}
        if row.get("source_id"):
            out["sourceId"] = str(row["source_id"])
        return out

    def _accepted_in_other_backbone(self, plant, backbone):
        """Aceptado del nombre aceptado de la planta en el otro backbone, resolviéndolo allí; None si no resuelve a uno solo."""
        accepted = self.backbones[plant.backbone].get(plant.accepted_id)
        if accepted is None:
            return None
        key = (backbone, accepted["name"], accepted["author"])
        if key not in self._other_accepted:
            result = resolve_in_backbone(accepted["name"], self.backbones[backbone], author=accepted["author"] or None)
            row = self.backbones[backbone].get(result["accepted_id"]) if result["outcome"] in RESOLVED and result["accepted_id"] else None
            self._other_accepted[key] = row
        return self._other_accepted[key]

    def _homotypic_synonyms(self, plant):
        """Sinónimos homotípicos del aceptado en WCVP (solo plantas `resolved` de WCVP), ordenados por nombre."""
        if plant.kind != "resolved" or plant.backbone != "wcvp" or not plant.accepted_id:
            return []
        rows = [r for r in self.uni.wcvp.synonyms(plant.accepted_id) if r["status"] == "Synonym" and r["homotypic"] == "T" and " " in r["name"]]
        return sorted(rows, key=lambda r: (r["name"], r["id"]))

    def _identity_and_taxonomy(self, plant, doc, refs):
        primary = plant.backbone if plant.accepted_id and plant.backbone in self.backbones else None
        if primary and not self.enabled.get(primary):
            raise SourceError("la fuente '%s' está desactivada pero la planta %s se resolvió con ella; vuelva a ejecutar resolve" % (primary, plant.id))
        taxonomy, accepted, name_set = [], {}, []

        def usable(backbone):
            return self.enabled.get(backbone) and backbone in self.backbones and self.backbones[backbone] is not None

        if primary:
            accepted_row = self.backbones[primary].get(plant.accepted_id)
            own_row = self.backbones[primary].get(plant.matched_id) if plant.matched_id else None
            if accepted_row:
                entry = self._taxon_row(primary, accepted_row, "aceptado", refs)
                accepted[primary] = {k: entry[k] for k in ("ref", "id", "name", "authors", "rank", "status", "family")}
                taxonomy.append(entry)
            other = "wfo" if primary == "wcvp" else "wcvp"
            if usable(other):
                row = self._accepted_in_other_backbone(plant, other)
                if row is not None:
                    entry = self._taxon_row(other, row, "aceptado", refs)
                    accepted[other] = {k: entry[k] for k in ("ref", "id", "name", "authors", "rank", "status", "family")}
                    taxonomy.append(entry)
            if own_row:
                taxonomy.append(self._taxon_row(primary, own_row, "propio", refs))
        own_ref = None
        if primary:
            own = self.backbones[primary].get(plant.matched_id or plant.accepted_id)
            own_ref = self._row_ref(primary, own, refs) if own else None
        own = {"name": plant.name, "authors": _author_text(plant.author), "reason": "universe", "backbone": primary}
        if own_ref:
            own["ref"] = own_ref
        name_set.append(own)
        for entry in plant.entries:
            res = self.uni.resolutions.get(entry.key) or {}
            name_set.append({"name": entry.name, "authors": _author_text(entry.author), "reason": "entrada-%s" % entry.source,
                             "backbone": res.get("backbone") or None, "keys": [entry.key]})
        for fused in doc.get("fusedHeterotypic") or []:
            name_set.append({"name": fused["name"], "authors": "", "reason": "heterotipico-fusionado", "backbone": primary,
                             "detail": fused["reason"], "keys": sorted(fused["entries"])})
        for backbone_id in doc.get("fusedMatchedIds") or []:
            backbone, _, row_id = backbone_id.partition(":")
            row = self.backbones[backbone].get(row_id) if backbone in self.backbones and usable(backbone) else None
            if row:
                taxonomy.append(self._taxon_row(backbone, row, "heterotipico-fusionado", refs))
        if primary and plant.accepted_id and accepted.get(primary) and accepted[primary]["name"] != plant.name:
            name_set.append({"name": accepted[primary]["name"], "authors": accepted[primary]["authors"], "reason": "aceptado-del-grupo",
                             "backbone": primary, "ref": accepted[primary]["ref"]})
        homotypic = self._homotypic_synonyms(plant)
        for row in homotypic[:self.limits["homotypicSynonyms"]]:
            entry = self._taxon_row("wcvp", row, "sinonimo-homotipico", refs)
            taxonomy.append(entry)
            name_set.append({"name": row["name"], "authors": row["author"] or "", "reason": "sinonimo-homotipico", "backbone": "wcvp", "ref": entry["ref"]})
        # Una fila por ref (con el rol más específico) y un nombre por (nombre, motivo).
        by_ref = {}
        for entry in taxonomy:
            current = by_ref.get(entry["ref"])
            if current is None or _ROLE_ORDER[entry["role"]] < _ROLE_ORDER[current["role"]]:
                by_ref[entry["ref"]] = entry
        taxonomy = sorted(by_ref.values(), key=lambda e: (_ROLE_ORDER[e["role"]], e["backbone"], e["name"], e["id"]))
        name_set = sorted(_dedupe(name_set), key=lambda n: (_NAME_REASON_ORDER[n["reason"]], n["name"]))
        extra = {"homotypicTotal": len(homotypic)} if len(homotypic) > self.limits["homotypicSynonyms"] else {}
        return primary, accepted, name_set, taxonomy, extra

    # -- colisión
    def _collision(self, plant, doc):
        fused = doc.get("fusedHeterotypic") or []
        group = doc.get("collision")
        if not group and not fused:
            return None
        accepted_name = group["acceptedName"] if group else plant.name
        out = {"role": "separada" if plant.kind == "heterotypic" else "aceptado", "acceptedName": accepted_name,
               "split": bool(group), "members": sorted(group["members"]) if group else [],
               "fused": [{"name": f["name"], "reason": f["reason"], "entries": sorted(f["entries"])} for f in sorted(fused, key=lambda f: f["name"])],
               "decision": None}
        decision = doc.get("collisionDecision")
        if decision:
            out["decision"] = {"state": decision["state"], "decision": decision["decision"], "reason": decision["reason"]}
        return out

    # -- distribución
    def _distribution(self, plant, refs):
        if plant.backbone != "wcvp" or not plant.accepted_id or not self.enabled.get("wcvp"):
            return None
        areas = self.uni.wcvp.distribution(plant.accepted_id)
        if not areas:
            return None
        native = [a for a in areas if not a["introduced"] and not a["extinct"] and not a["location_doubtful"]]
        introduced = [a for a in areas if a["introduced"] and not a["extinct"] and not a["location_doubtful"]]
        accepted = self.uni.wcvp.get(plant.accepted_id)
        ref = self._row_ref("wcvp", accepted, refs)
        names = sorted(a["area"] for a in native)
        cap = self.limits["nativeAreas"]
        out = {"ref": ref, "native": sorted({a["region"] for a in native}), "introduced": sorted({a["region"] for a in introduced}),
               "nativeAreas": names[:cap], "nativeAreaCount": len(native), "introducedAreaCount": len(introduced),
               "of": "aceptado-compartido" if plant.kind == "heterotypic" else "aceptado"}
        extinct = sorted(a["area"] for a in areas if a["extinct"])
        if extinct:
            out["extinctAreas"] = extinct[:10]
        return out

    # -- USDA
    def _usda_sections(self, plant, refs, notes):
        names, parts, uses = [], [], []
        bucket = (self.usda.by_plant.get(plant.id) if self.usda else None) or {}
        for c in bucket.get("commonNames", []):
            ref = refs.add(c["ref"], "usda", "USDA Dr. Duke: nombre común «%s»" % c["name"])
            names.append({"ref": ref, "text": c["name"], "language": c["language"], "source": "usda"})
        for part in bucket.get("parts", []):
            ref = refs.add(part["ref"], "usda", "USDA Dr. Duke: química de la parte «%s»" % (part["ppna"] or part["ppco"]))
            parts.append({"ref": ref, "ppco": part["ppco"], "ppna": part["ppna"], "rows": part["rows"], "hasEo": part["hasEo"],
                          "eoCompounds": part["eoCompounds"], "distinctCompounds": part["distinctCompounds"],
                          "topAmount": part["topAmount"], "topEo": part["topEo"]})
        groups = sorted(bucket.get("useGroups", []), key=lambda g: (-g["n"], g["activity"]))
        cap = self.limits["useGroups"]
        if cap is not None and len(groups) > cap:
            notes.append("El paquete trae los %d grupos de uso con más filas; se omitieron %d grupos con %d filas." % (
                cap, len(groups) - cap, sum(g["n"] for g in groups[cap:])))
            groups = groups[:cap]
        for group in groups:
            use_refs = group["refs"] if self.limits["useRefs"] is None else group["refs"][:self.limits["useRefs"]]
            for ref in use_refs:
                refs.add(ref, "usda", "USDA Dr. Duke: uso etnobotánico %s" % ref.split(":", 1)[1])
            keys = [k for k in group["keys"] if k["key"]]
            kept = keys if self.limits["useKeys"] is None else keys[:self.limits["useKeys"]]
            candidates = {}
            for key in kept:
                options = []
                for c in key["candidates"]:
                    refs.add(c["ref"], "usda", "USDA Dr. Duke: referencia %s" % c["reference"])
                    options.append({"ref": c["ref"], "citation": c["longref"]})
                if options:
                    candidates[key["key"]] = options
            item = {"activity": group["activity"], "n": group["n"], "countries": group["countries"], "refs": use_refs,
                    "citations": [k["key"] for k in kept], "candidates": candidates}
            if len(use_refs) < len(group["refs"]):
                item["refsTotal"] = len(group["refs"])
            if len(kept) < len(keys):
                item["citationsTotal"] = len(keys)
            uses.append(item)
        return names, parts, uses

    # -- EMA
    def _ema_view(self, content, entry_name):
        """Áreas, resultado y combinación de una ficha para una especie. En una ficha fusionada se toman las filas de esa especie."""
        cache_key = (content["slug"], entry_name)
        if cache_key in self._ema_view_cache:
            return self._ema_view_cache[cache_key]
        view = {"areas": content.get("therapeutic_areas") or [], "outcomes": content.get("outcomes") or [],
                "combination": content.get("combination"), "status": content.get("status"), "latin": content.get("latin_name")}
        rows = content.get("rows") or []
        if len(rows) > 1:
            matching = []
            for row in rows:
                for fragment in split_source_names("ema", row.get("botanical_name")):
                    if Entry.from_text("ema", "x", fragment).name == entry_name:
                        matching.append(row)
                        break
            if matching:
                view = {"areas": _dedupe(a for r in matching for a in (r.get("therapeutic_areas") or [])),
                        "outcomes": _dedupe(o for r in matching for o in (r.get("outcomes") or [])),
                        "combination": ";".join(_dedupe(str(r.get("combination")) for r in matching)),
                        "status": ";".join(_dedupe(str(r.get("status")) for r in matching)),
                        "latin": matching[0].get("latin_name") or content.get("latin_name")}
        self._ema_view_cache[cache_key] = view
        return view

    def _goal_candidates(self, outcome, combination, areas):
        """Objetivos candidatos de una ficha de la EMA: vacíos si el resultado no es monografía ni entrada de lista o es combinada."""
        if not goals_lib.counted_outcomes(self.goals_map, outcome) or _is_combination(combination):
            return [], []
        candidates, unmapped = [], []
        for raw in areas:
            for area in goals_lib.split_values(raw, self.goals_map.get("separator", ";")):
                mapped = goals_lib.map_area(self.goals_map, area)
                if mapped is None or mapped[0] is None:
                    unmapped.append(area)
                    continue
                item = {"area": area, "areaEs": mapped[2], "goal": mapped[0], "subarea": mapped[1]}
                if item not in candidates:
                    candidates.append(item)
        return candidates, unmapped

    def _regulatory(self, plant, refs):
        out, seen = [], set()
        for entry in plant.entries:
            if entry.source != "ema":
                continue
            slug = entry.key[len("ema:"):].rsplit("#", 1)[0]
            row = self.rows.ema_herbal.get(slug)
            if row is None or slug in seen:
                continue
            seen.add(slug)
            content = row["content"]
            view = self._ema_view(content, entry.name)
            outcome = ";".join(view["outcomes"])
            label = "EMA: %s" % (view["latin"] or content.get("latin_name") or slug)
            ref = refs.add("%s:%s" % (EMA_HERBAL, slug), "ema_json", label, url=content.get("url"))
            candidates, unmapped = self._goal_candidates(outcome, view["combination"], view["areas"])
            item = {"ref": ref, "slug": slug, "latinName": view["latin"], "englishName": content.get("english_common_name"),
                    "botanicalName": content.get("botanical_name"), "outcome": outcome, "therapeuticAreas": list(view["areas"]),
                    "combination": view["combination"], "status": view["status"], "url": content.get("url"),
                    "goalCandidates": candidates}
            if unmapped:
                item["unmappedAreas"] = unmapped
            out.append(item)
        return sorted(out, key=lambda r: r["slug"])

    def _ema_safety(self, plant, refs, flags):
        out = []
        slugs = sorted({e.key[len("ema:"):].rsplit("#", 1)[0] for e in plant.entries if e.source == "ema"})
        for slug in slugs:
            data = self.rows.ema_pdf.get(slug)
            if data is None:
                continue
            doc = data["doc"]["content"]
            status = doc.get("status")
            documents = {d.get("filename"): d for d in doc.get("documents") or []}
            if status in ("ok", "declaracion-publica"):
                expected = EMA_SECTIONS if status == "ok" else ("CONCLUSIONS",)
                missing = [s for s in expected if s not in data["sections"]]
                for section in expected:
                    row = data["sections"].get(section)
                    if row is None:
                        continue
                    out.append(self._ema_section_entry(slug, section, row, documents, refs))
                if missing:
                    out.append(self._ema_failure(slug, doc, refs, "faltan secciones: %s" % ", ".join(missing)))
            elif status == "sin-documento":
                continue
            else:
                out.append(self._ema_failure(slug, doc, refs, "extracción: %s" % status))
        failed = sorted(e["slug"] for e in out if e.get("status") == "extraccion-fallida")
        if failed:
            flags.append({"code": "extraccion-seguridad-fallida", "target": "safety",
                          "message": "La extracción de las secciones de seguridad de la EMA falló o quedó incompleta (%s)." % ", ".join(failed)})
        return out

    def _ema_failure(self, slug, doc, refs, reason):
        ref = refs.add("ema_pdf_doc:%s" % slug, "ema_pdf", "EMA: documento de %s" % slug, url=((doc.get("documents") or [{}])[0].get("url")))
        return {"source": "ema_pdf", "ref": ref, "slug": slug, "status": "extraccion-fallida", "reason": reason, "severeInteractions": False}

    def _ema_section_entry(self, slug, section, row, documents, refs):
        content = row["content"]
        document = documents.get(content.get("document")) or {}
        kind = content.get("kind") or document.get("kind")
        if section == "CONCLUSIONS":
            label = "EMA: declaración pública de %s, conclusiones" % slug
        else:
            label = "EMA: %s de %s, sección %s (%s)" % ("borrador de la monografía" if content.get("draft") else "monografía", slug, section, content.get("heading") or "")
        ref = refs.add("ema_pdf:%s" % row["row_key"], "ema_pdf", label, url=document.get("url"))
        entry = {"source": "ema_pdf", "ref": ref, "slug": slug, "section": section, "heading": content.get("heading"), "documentKind": kind,
                 "pages": [content.get("page_from"), content.get("page_to")], "text": content.get("text"), "severeInteractions": False}
        if section == "4.5":
            result = safety.ema_interaction_class(self.safety_map, content)
            entry.update(interactionClass=result["class"], level=result["level"], columns=result["columns"], matchedPatterns=result["matched"],
                         levelReason=self.safety_map["ema"]["classes"][result["class"]]["why"], severeInteractions=result["class"] == "severe")
        elif section == "CONCLUSIONS":
            klass = "statement-with-safety" if content.get("safety_data") else "statement-no-safety"
            entry.update(interactionClass=klass, level=self.safety_map["ema"]["classes"][klass]["level"], safetyData=bool(content.get("safety_data")),
                         levelReason=self.safety_map["ema"]["classes"][klass]["why"])
            if content.get("note"):
                entry["note"] = content["note"]
        return entry

    # -- TPPT y EFSA
    def _usda_safety(self, plant, refs):
        """Entrada de seguridad de USDA: las señales letales de los usos (safety-map.json, sección `usda`) fijan el nivel alto.

        Se calcula sobre todos los grupos de uso de la planta, aunque un tope deje alguno fuera de `sections.uses`. Las demás señales
        de riesgo (Poison, Abortifacient, ...) no fijan nivel y no generan entrada: siguen visibles en `sections.uses`.
        """
        bucket = (self.usda.by_plant.get(plant.id) if self.usda else None) or {}
        terms, use_refs, reasons = {}, set(), {}
        for group in bucket.get("useGroups", []):
            base = safety.usda_signal_base(group["activity"])
            entry = safety.usda_signal(self.safety_map, group["activity"])
            if not entry or entry["level"] is None:
                continue
            terms.setdefault(base, group["activity"].split("(")[0].strip())
            reasons[base] = entry
            use_refs.update(group["refs"])
        if not terms:
            return []
        ordered = sorted(use_refs, key=_natural)
        for ref in ordered:
            refs.add(ref, "usda", "USDA Dr. Duke: uso etnobotánico %s" % ref.split(":", 1)[1])
        level = safety.max_level(e["level"] for e in reasons.values())
        reason = " ".join(dict.fromkeys(reasons[b]["why"] for b in sorted(reasons) if reasons[b]["level"] == level))
        return [{"ref": ordered[0], "source": "usda", "refs": ordered, "terms": [terms[b] for b in sorted(terms)], "level": level, "levelReason": reason}]

    def _tppt_safety(self, plant, refs):
        out = []
        for row in sorted(self.rows.tppt.get(plant.id, []), key=lambda r: _natural(r["row_key"])):
            c = row["content"]
            ref = refs.add("tppt_plant:%s" % row["row_key"], "tppt", "TPPT (Agroscope): %s" % (c.get("latin_name") or row["raw_name_cell"]))
            human = safety.tppt_level(self.safety_map, c.get("human_toxicity"))
            table = self.safety_map["tppt"]["human_toxicity"]
            top = [x for x in human["categories"] if x["level"] is not None and x["level"] == human["level"]]
            toxins = sorted(c.get("toxins") or [], key=lambda t: (not t.get("major"), t.get("name") or "", t.get("number") or ""))
            cap = self.limits["tpptToxins"]
            entry = {"source": "tppt", "ref": ref, "latinName": c.get("latin_name"), "englishName": c.get("english_name") or None,
                     "germanName": c.get("german_name") or None, "family": c.get("family"), "humanToxicity": c.get("human_toxicity") or "",
                     "animalToxicity": c.get("animal_toxicity") or "", "toxicPart": c.get("toxic_part") or "",
                     "level": human["level"],
                     "levelReason": " | ".join(table[x["category"]]["why"] for x in top) if top else None,
                     "categories": [{"category": x["category"], "level": x["level"]} for x in human["categories"]],
                     "toxinCount": c.get("n_toxins"),
                     "toxins": [{"name": t.get("name"), "major": bool(t.get("major")), "composition": t.get("composition"),
                                 "psmClass": t.get("psm_class"), "casrn": t.get("casrn")} for t in toxins[:cap]],
                     "remarks": (c.get("remarks") or {}).get("comment") or None}
            if human["uncovered"]:
                entry["uncoveredCategories"] = human["uncovered"]
            if len(toxins) > cap:
                entry["toxinsTotal"] = len(toxins)
            out.append(entry)
        return out

    def _efsa_safety(self, plant, refs):
        botanic = sorted(self.rows.efsa_botanic.get(plant.id, []), key=lambda r: _natural(r["row_key"]))
        endpoints = sorted(self.rows.efsa_endpoint.get(plant.id, []), key=lambda r: _natural(r["row_key"]))
        if not botanic and not endpoints:
            return []
        config = self.safety_map["efsa"]
        result = safety.efsa_concern(self.safety_map, [r["content"] for r in botanic])
        groups = config["concern_list"]["groups"]
        by_key = {safety.substance_key(e["substance"]): e for e in config["concern_list"]["substances"]}
        first, parts = {}, {}
        excluded_types = set(config["definition"]["exclude_result_types"])
        for r in botanic:
            c = r["content"]
            name = c.get("substance_name")
            if not name or c.get("result_type") in excluded_types:
                continue
            first.setdefault(name, r)
            if c.get("part"):
                parts.setdefault(name, set()).add(c["part"])

        def substance_item(name):
            row = first[name]
            ref = refs.add("efsa_botanic:%s" % row["row_key"], "efsa", "EFSA Compendium of Botanicals: %s" % name)
            return {"substance": name, "ref": ref, "parts": sorted(parts.get(name, ()))}

        concern = []
        for name in result["concern_substances"]:
            item = substance_item(name)
            item["group"] = by_key[safety.substance_key(name)]["group"]
            concern.append(item)
        evidence_names = result["evidence_substances"]
        cap = self.limits["efsaEvidence"]
        evidence = [substance_item(n) for n in evidence_names[:cap]]
        studies = []
        for r in endpoints[:self.limits["efsaStudies"]]:
            c = r["content"]
            ref = refs.add("efsa_endpoint:%s" % r["row_key"], "efsa", "EFSA Compendium of Botanicals: estudio de %s" % (c.get("plant_name") or r["raw_name_cell"]))
            studies.append({"ref": ref, "studyCategory": c.get("study_category"), "testSpecies": c.get("test_species"), "route": c.get("route"),
                            "testType": c.get("test_type"), "toxicitySummary": c.get("toxicity_summary"), "effect": c.get("effect_description"),
                            "part": c.get("part"), "title": c.get("title"), "year": c.get("year")})
        cited = [i["ref"] for i in concern + evidence + studies]
        if not cited:
            return []
        entry = {"source": "efsa", "ref": cited[0],
                 "level": result["level"],
                 "levelReason": " | ".join(groups[g]["why"] for g in result["concern_groups"]) if result["concern_groups"] else None,
                 "concernGroups": result["concern_groups"], "concernSubstances": concern, "evidenceSubstances": evidence,
                 "rowsCounted": result["rows_counted"], "studies": studies}
        if len(evidence_names) > cap:
            entry["evidenceTotal"] = len(evidence_names)
        if len(endpoints) > len(studies):
            entry["studiesTotal"] = len(endpoints)
        return [entry]

    # -- Wikidata, Wikipedia y Commons
    def _wiki(self, plant, doc, refs, notes):
        info = (self.wiki or {}).get("plants", {}).get(plant.id)
        names, descriptions, images, items = [], [], [], []
        if info is None:
            status = STATUS_NO_RESPONSE if doc["acceptedId"] else STATUS_NOT_QUERIED
        else:
            status = info["wikidata"]["status"]
        if info is not None and self.enabled.get("wikidata"):
            matched = {q: self.wiki["items"][q]["reason"] for q in info["wikidata"]["items"]}
            for qid in sorted(info["wikidata"]["items"]):
                row = self.rows.wikidata.get(qid)
                if row is None:
                    continue
                c = row["content"]
                ref = refs.add("wikidata:%s" % qid, "wikidata", "Wikidata %s" % qid, url=WIKIDATA_URL % qid)
                items.append({"ref": ref, "qid": qid, "p225": c.get("taxon"), "authors": c.get("authors") or [], "labelEs": c.get("labelEs") or None,
                              "p1843Es": c.get("spanishNames") or [], "aliasesEs": (c.get("aliasesEs") or [])[:8],
                              "eswikiTitle": c.get("eswiki") or None, "gbif": c.get("gbif") or [], "ipni": c.get("ipni") or [],
                              "powo": c.get("powo") or [], "match": matched[qid]})
                for text in c.get("spanishNames") or []:
                    names.append({"ref": ref, "text": text, "language": "es", "source": "wikidata", "kind": "p1843"})
                label = c.get("labelEs") or ""
                if label and label.lower() != (c.get("taxon") or "").lower() and label not in (c.get("spanishNames") or []):
                    names.append({"ref": ref, "text": label, "language": "es", "source": "wikidata", "kind": "etiqueta"})
            if self.enabled.get("wikipedia_es"):
                for entry in sorted(info["wikipedia"], key=lambda e: e["title"]):
                    row = self.rows.wikipedia.get(entry["title"])
                    if row is None:
                        continue
                    c = row["content"]
                    ref = refs.add("wikipedia_es:%s" % entry["title"], "wikipedia_es", "Wikipedia en español: %s" % entry["title"],
                                   license=self.licenses["wikipedia_es"], url=c.get("url"))
                    descriptions.append({"ref": ref, "source": "wikipedia_es", "title": c.get("title"), "shortDescription": c.get("description") or None,
                                         "text": c.get("extract"), "url": c.get("url"), "license": self.licenses["wikipedia_es"],
                                         "revision": c.get("revision"), "timestamp": c.get("timestamp"), "qid": entry["qid"]})
            if self.enabled.get("commons"):
                admitted = sorted(info["commons"]["admitted"], key=lambda e: e["title"])
                discarded = info["commons"]["discarded"]
                for entry in admitted[:self.limits["images"]]:
                    row = self.rows.commons.get(entry["title"])
                    if row is None:
                        continue
                    c = row["content"]
                    if not is_displayable(c.get("mime")):
                        continue
                    ref = refs.add("commons:%s" % entry["title"], "commons", "Wikimedia Commons: %s" % entry["title"],
                                   license=c.get("license"), url=c.get("pageUrl"))
                    images.append({"ref": ref, "title": c.get("title"), "url": clean_file_url(c.get("fileUrl")), "pageUrl": c.get("pageUrl"), "author": c.get("author"),
                                   "license": c.get("license"), "licenseCode": c.get("licenseCode"), "licenseUrl": c.get("licenseUrl"),
                                   "attributionRequired": bool(c.get("attributionRequired")), "mime": c.get("mime"), "width": c.get("width"),
                                   "height": c.get("height"), "qid": entry["qid"]})
                if discarded:
                    reasons = {}
                    for entry in discarded:
                        reasons[entry["reason"]] = reasons.get(entry["reason"], 0) + 1
                    notes.append("Imágenes de Commons descartadas por licencia o autoría: %s." % ", ".join("%s (%d)" % kv for kv in sorted(reasons.items())))
                if len(admitted) > self.limits["images"]:
                    notes.append("La planta tiene %d imágenes de Commons admitidas; el paquete trae las primeras %d por título." % (len(admitted), self.limits["images"]))
        return status, items, names, descriptions, images

    # -- armado
    def build_one(self, plant):
        doc = self.docs[plant.id]
        refs = Refs(self.licenses)
        flags = [dict(f) for f in doc["reviewFlags"]]
        notes = []
        primary, accepted, name_set, taxonomy, extra = self._identity_and_taxonomy(plant, doc, refs)
        names, parts, uses = self._usda_sections(plant, refs, notes)
        regulatory = self._regulatory(plant, refs) if self.enabled.get("ema_json") else []
        safety_rows = []
        if self.enabled.get("tppt"):
            safety_rows += self._tppt_safety(plant, refs)
        if self.enabled.get("ema_pdf"):
            safety_rows += self._ema_safety(plant, refs, flags)
        if self.enabled.get("efsa"):
            safety_rows += self._efsa_safety(plant, refs)
        safety_rows += self._usda_safety(plant, refs)
        status, wikidata_items, wiki_names, descriptions, images = self._wiki(plant, doc, refs, notes)
        names = sorted(names + wiki_names + self._tppt_names(safety_rows), key=lambda n: (n["source"], n["language"] or "", n["text"], n["ref"]))
        if status in WIKIDATA_FLAGS:
            code, message = WIKIDATA_FLAGS[status]
            flags.append({"code": code, "target": "wikidata", "message": message})
        if plant.kind == "heterotypic":
            notes.append("La distribución es la del aceptado compartido del grupo (%s), no la de esta planta." % doc["collision"]["acceptedName"])
        for fused in doc.get("fusedHeterotypic") or []:
            notes.append("Se fusionó el sinónimo heterotípico %s (%s); sus filas de las fuentes están en esta planta." % (fused["name"], fused["reason"]))
        sections = {"taxonomy": taxonomy, "distribution": self._distribution(plant, refs), "names": names, "descriptions": descriptions,
                    "parts": parts, "uses": sorted(uses, key=lambda u: (-u["n"], u["activity"])), "regulatory": regulatory,
                    "safety": sorted(safety_rows, key=lambda e: (e["source"], e["ref"])), "images": images,
                    "wikidata": {"status": status, "items": wikidata_items}}
        identity = {"proposedId": plant.id, "universe": doc["entries"], "name": plant.name, "authors": _author_text(plant.author), "kind": plant.kind,
                    "family": plant.family or None, "primaryBackbone": primary, "accepted": accepted, "nameSet": name_set,
                    "aliases": list(doc["aliases"]), "collision": self._collision(plant, doc),
                    "flags": sorted(flags, key=lambda f: (f["code"], f["target"], f["message"])), "notes": notes}
        identity.update(extra)
        bundle = {"bundleVersion": BUNDLE_VERSION, "plantKey": plant.id, "identity": identity, "sections": sections, "refs": refs.entries}
        bundle["bundleHash"] = bundle_hash(bundle)
        return bundle

    def _tppt_names(self, safety_rows):
        out = []
        for entry in safety_rows:
            if entry["source"] == "tppt":
                if entry.get("englishName"):
                    out.append({"ref": entry["ref"], "text": entry["englishName"], "language": "en", "source": "tppt"})
                if entry.get("germanName"):
                    out.append({"ref": entry["ref"], "text": entry["germanName"], "language": "de", "source": "tppt"})
        return out

    def build(self, plant_ids=None, log=print):
        """Paquetes de las plantas pedidas (o de todas), como {id: paquete}."""
        wanted = set(plant_ids) if plant_ids is not None else None
        if wanted is not None:
            missing = sorted(wanted - {p.id for p in self.uni.plants})
            if missing:
                raise SourceError("plantas que no están en el universo: %s" % ", ".join(missing))
        return {p.id: self.build_one(p) for p in self.uni.plants if wanted is None or p.id in wanted}


_ROLE_ORDER = {"aceptado": 0, "propio": 1, "heterotipico-fusionado": 2, "sinonimo-homotipico": 3}
_NAME_REASON_ORDER = {"universe": 0, "entrada-usda": 1, "entrada-ema": 2, "heterotipico-fusionado": 3, "aceptado-del-grupo": 4,
                      "sinonimo-homotipico": 5}


# --- Escritura, cifras y tamaños -------------------------------------------------------------------------------------------

def write_bundles(bundles, out_dir, prune=False):
    """Escribe `<id>.json` (JSON canónico) en `out_dir`. Con `prune`, borra los `*.json` de plantas que ya no están."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for plant_id, bundle in bundles.items():
        path = out / ("%s.json" % plant_id)
        path.write_text(canonical_json(bundle) + "\n", encoding="utf-8")
    removed = []
    if prune:
        for path in sorted(out.glob("*.json")):
            if path.stem not in bundles:
                path.unlink()
                removed.append(path.stem)
    return removed


def read_plant_ids(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SourceError("no se puede leer el archivo de IDs %s: %s" % (path, error))
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def section_presence(bundle):
    """Secciones con contenido en un paquete: {sección: bool}."""
    sections = bundle["sections"]
    present = {}
    for name in SECTIONS:
        value = sections[name]
        if name == "wikidata":
            present[name] = bool(value["items"])
        else:
            present[name] = bool(value)
    return present


def coverage(bundles):
    """Plantas con y sin cada sección, y plantas por estado de Wikidata."""
    out = {name: 0 for name in SECTIONS}
    status = {}
    for bundle in bundles:
        for name, present in section_presence(bundle).items():
            out[name] += 1 if present else 0
        state = bundle["sections"]["wikidata"]["status"]
        status[state] = status.get(state, 0) + 1
    total = len(bundles)
    return {"plants": total, "withSection": out, "withoutSection": {k: total - v for k, v in out.items()}, "wikidataStatus": dict(sorted(status.items()))}


def estimated_tokens(text):
    return int(round(len(text) / CHARS_PER_TOKEN))


def _percentile(sorted_values, q):
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[index]


def size_report(bundles, top=10):
    """Tamaño de los paquetes en tokens estimados (caracteres del JSON canónico ÷ 3,5): p50, p90, máximo, total y las plantas más grandes."""
    sizes = []
    for bundle in bundles:
        text = canonical_json(bundle)
        sizes.append((estimated_tokens(text), len(text), bundle))
    values = sorted(s[0] for s in sizes)
    ranked = sorted(sizes, key=lambda s: (-s[0], s[2]["plantKey"]))[:top]
    biggest = []
    for tokens, chars, bundle in ranked:
        parts = {name: estimated_tokens(canonical_json(bundle["sections"][name])) for name in SECTIONS}
        parts["refs"] = estimated_tokens(canonical_json(bundle["refs"]))
        parts["identity"] = estimated_tokens(canonical_json(bundle["identity"]))
        biggest.append({"id": bundle["plantKey"], "tokens": tokens, "chars": chars,
                        "sections": dict(sorted(parts.items(), key=lambda kv: -kv[1])[:5])})
    section_totals = {name: sum(estimated_tokens(canonical_json(s[2]["sections"][name])) for s in sizes) for name in SECTIONS}
    section_totals["refs"] = sum(estimated_tokens(canonical_json(s[2]["refs"])) for s in sizes)
    section_totals["identity"] = sum(estimated_tokens(canonical_json(s[2]["identity"])) for s in sizes)
    return {"plants": len(sizes), "p50": _percentile(values, 0.5), "p90": _percentile(values, 0.9), "max": values[-1] if values else 0,
            "mean": int(round(sum(values) / len(values))) if values else 0, "total": sum(values), "top": biggest,
            "sectionTotals": dict(sorted(section_totals.items(), key=lambda kv: -kv[1]))}


def format_sizes(report):
    lines = ["%d paquetes; tamaño estimado en tokens (caracteres del JSON canónico ÷ %s)" % (report["plants"], str(CHARS_PER_TOKEN).replace(".", ",")),
             "  p50 %(p50)d, p90 %(p90)d, máximo %(max)d, promedio %(mean)d, total %(total)d" % report, "  las plantas más grandes:"]
    for item in report["top"]:
        lines.append("    %-40s %7d tokens; secciones mayores: %s" % (
            item["id"], item["tokens"], ", ".join("%s %d" % kv for kv in item["sections"].items())))
    lines.append("  tokens totales por sección: %s" % ", ".join("%s %d" % kv for kv in report["sectionTotals"].items()))
    return "\n".join(lines)


def read_bundles(directory):
    out = []
    for path in sorted(Path(directory).glob("*.json")):
        with open(path, encoding="utf-8") as handle:
            out.append(json.load(handle))
    return out


# --- Orquestación -----------------------------------------------------------------------------------------------------------

def run_bundles(sources, cache_dir, db_path, taxonomy_db, out_dir, plant_ids=None, safety_map=None, goals_map=None, log=print,
                limits=None):
    """Arma los paquetes del universo real sin red y los escribe en `out_dir`. Devuelve (paquetes, cifras)."""
    from . import wiki_fetch
    from .resolve_universe import build_universe_from_work
    from .wiki_assign import CONTROL_NAMES, build_assignment, build_name_plan

    started = time.time()
    safety_map = safety_map or safety.load_safety_map()
    goals_map = goals_map or goals_lib.load_goals_map()
    enabled = wiki_fetch.enabled_services(sources)

    def wiki_assigner(universe_doc, flags):
        plan = build_name_plan(universe_doc, uni.wcvp, CONTROL_NAMES)
        steps = wiki_fetch.make_steps(cache_dir, 0)
        return build_assignment(universe_doc, uni.wcvp, uni.wfo, plan, steps, {k: flags.get(k, False) for k in enabled})

    connection = workdb.open_db(db_path)
    try:
        with build_universe_from_work(db_path, taxonomy_db, log=log) as (uni, _):
            builder = Builder(uni, sources, safety_map, goals_map, limits=limits).prepare(connection, wiki_assigner, log=log)
            log("armando %d paquetes..." % len(uni.plants))
            bundles = builder.build(plant_ids)
            stats = {"universePlants": len(uni.plants), "rows": builder.rows.stats, "usda": builder.usda.stats if builder.usda else None}
    finally:
        connection.close()
    removed = write_bundles(bundles, out_dir, prune=plant_ids is None)
    stats.update(bundles=len(bundles), removedStale=removed, seconds=round(time.time() - started, 1), coverage=coverage(list(bundles.values())))
    return bundles, stats
