"""Universo de plantas, regla de colisiones, IDs únicos, alias y asignación de filas (tarea 2.5).

Flujo: `build_universe(entries, wcvp, wfo)` resuelve cada entrada (`Entry`: una planta de USDA o una especie de la EMA),
agrupa las que llegan al mismo aceptado y aplica la regla de colisiones. `Universe.assign(...)` asigna después las filas
de uso y de otras fuentes a una planta del universo.
"""
from .ids import plant_slug
from .names import parse_name
from .resolver import resolve_name

RESOLVED = ("accepted", "synonym")
UNRESOLVED_KINDS = ("ambiguous", "unresolved", "unmatched", "genus_only")


class UniverseError(Exception):
    """El armado falla: dos plantas con el mismo ID. `collisions` lista (id, [plantas])."""

    def __init__(self, message, collisions=None):
        Exception.__init__(self, message)
        self.collisions = collisions or []


class Entry(object):
    """Una planta candidata del universo (USDA FNFTAX o especie de la EMA).

    `name` es el nombre tal como viene (sin autor); `author` el autor aparte (puede ir vacío); `key` identifica la entrada
    (p. ej. `usda:279`, `ema:<url>`); `source` es `usda` o `ema`.
    """

    def __init__(self, source, key, name, author="", hint=None):
        self.source = source
        self.key = key
        self.name = name
        self.author = author or ""
        self.hint = hint

    @classmethod
    def from_text(cls, source, key, text, hint=None):
        """Entrada desde un texto con autor incluido (p. ej. un fragmento de `split_source_names` de la EMA)."""
        p = parse_name(text, hint=hint)
        if p.ok:
            return cls(source, key, p.display, p.species_author if not p.infra_epithet else p.author, hint)
        return cls(source, key, text.strip(), "", hint)


class Plant(object):
    """Una planta del universo. `kind`: `resolved` (grupo del aceptado), `heterotypic` (planta propia en un grupo partido)
    o uno de `ambiguous`, `unresolved`, `unmatched`, `genus_only` (identidad de la fuente)."""

    def __init__(self, id_, name, author, kind):
        self.id = id_
        self.name = name
        self.author = author
        self.kind = kind
        self.backbone = ""
        self.accepted_id = ""
        self.matched_id = ""
        self.family = ""
        self.entries = []
        self.aliases = []
        self.flags = set()
        self.split = False
        self.keys = set()           # claves de nombre que identifican a la planta (para asignar filas)
        self.member_rows = []       # filas del backbone que pertenecen a la planta (para la regla de homotipia)
        self.is_core = False        # contiene al propio aceptado

    @property
    def review_flags(self):
        return _review_flags(self)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "author": self.author, "kind": self.kind, "backbone": self.backbone,
                "accepted_id": self.accepted_id, "matched_id": self.matched_id, "family": self.family,
                "entries": [e.key for e in self.entries], "aliases": list(self.aliases), "flags": sorted(self.flags),
                "reviewFlags": self.review_flags, "split": self.split}

    def __repr__(self):
        return "Plant(%s, %r, %s)" % (self.id, self.name, self.kind)


_FLAG_CODES = (
    ("homonym_unresolved", "identidad-ambigua", "El nombre es un homónimo que el backbone no resuelve; la planta conserva la identidad de la fuente."),
    ("genus_only", "solo-genero", "La entrada solo nombra el género."),
    ("unresolved", "sin-resolucion", "El nombre no resuelve a un aceptado en ningún backbone."),
    ("unmatched", "sin-resolucion", "El nombre no aparece en ningún backbone."),
    ("wfo_fallback", "respaldo-wfo", "El aceptado viene del respaldo de WFO, no de WCVP."),
    ("fuzzy_match", "coincidencia-aproximada", "El nombre resolvió por coincidencia aproximada (errata probable); requiere revisión."),
    ("accepted_above_species", "aceptado-superior-a-especie", "El aceptado del nombre es de rango superior a especie; la planta conserva el nombre de la fuente."),
    ("orthographic_variant", "variante-ortografica", "El nombre resolvió por una variante ortográfica del epíteto."),
    ("backbone_disagreement", "backbones-discrepan", "WCVP y WFO discrepan en el aceptado; se conserva el de WCVP."),
    ("split_group", "grupo-partido", "El aceptado lo comparten plantas heterotípicas; esta es una de las separadas."),
    ("unassigned_rows", "filas-sin-asignar", "Hay filas del grupo que no se pudieron asignar a ninguna planta."),
)


def _review_flags(plant):
    out = []
    for flag, code, message in _FLAG_CODES:
        if flag in plant.flags:
            out.append({"code": code, "target": "scientificName", "message": message})
    return out


def _row_rank_is_species(row):
    return (row.get("rank") or "").lower() == "species"


class _Resolved(object):
    """Entrada con su resolución y las filas del backbone ya leídas."""

    def __init__(self, entry, res, matched, accepted):
        self.entry = entry
        self.res = res
        self.matched = matched
        self.accepted = accepted
        self.kind = None   # A (propio aceptado), H (homotípico), X (heterotípico o desconocido)


def _homotypic_with(row, other):
    """`row` es homotípico de `other` si comparten basiónimo o uno es el basiónimo del otro (mismo backbone)."""
    if not row or not other:
        return False
    if row["id"] == other["id"]:
        return True
    rb, ob = row.get("basionym_id") or "", other.get("basionym_id") or ""
    return bool((rb and rb == ob) or (rb and rb == other["id"]) or (ob and ob == row["id"]))


def classify_relation(matched, accepted, backbone_kind):
    """Relación de una fila coincidente con su aceptado: `A` (es el propio aceptado), `H` (homotípico) o `X` (heterotípico)."""
    return _classify(_Resolved(None, {"backbone": backbone_kind}, matched, accepted))


def _classify(r):
    matched, accepted = r.matched, r.accepted
    if matched["key_full"] == accepted["key_full"]:
        return "A"
    if r.res["backbone"] == "wcvp":
        if matched.get("homotypic") == "T":
            return "H"
        return "H" if _homotypic_with(matched, accepted) else "X"
    return "H" if _homotypic_with(matched, accepted) else "X"


class Universe(object):
    def __init__(self, wcvp, wfo):
        self.wcvp = wcvp
        self.wfo = wfo
        self.plants = []
        self.entries = {}            # key -> Entry
        self.resolutions = {}        # key -> dict de resolución
        self.groups = {}             # accepted_key -> [Plant]
        self.discarded_aliases = []  # (planta, alias, motivo)
        self.unassigned = []         # filas sin asignar: dicts

    # --- consultas
    def plant(self, plant_id):
        for p in self.plants:
            if p.id == plant_id:
                return p
        return None

    def relation(self, key):
        """Relación de una entrada con su aceptado (`A`, `H` o `X`); None si la entrada no resolvió."""
        res = self.resolutions[key]
        if res["outcome"] not in RESOLVED:
            return None
        bb = self.wcvp if res["backbone"] == "wcvp" else self.wfo
        return classify_relation(bb.get(res["matched_id"]), bb.get(res["accepted_id"]), res["backbone"])

    def plant_of_entry(self, key):
        for p in self.plants:
            if any(e.key == key for e in p.entries):
                return p
        return None

    def stats(self):
        counts = {}
        for res in self.resolutions.values():
            counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
        return {"entries": len(self.entries), "plants": len(self.plants),
                "resolution_outcomes": counts,
                "split_groups": sum(1 for g in self.groups.values() if any(p.split for p in g)),
                "ambiguous": sum(1 for p in self.plants if p.kind == "ambiguous"),
                "genus_only": sum(1 for p in self.plants if p.kind == "genus_only"),
                "unresolved": sum(1 for p in self.plants if p.kind in ("unresolved", "unmatched")),
                "discarded_aliases": len(self.discarded_aliases)}

    # --- asignación de filas
    def assign(self, name, author=None, hint=None, source="row"):
        """Asigna una fila (de uso o de otra fuente) a una planta. Devuelve `(plant | None, motivo)`.

        Orden en un grupo partido: misma clave; miembro homotípico (mismo basiónimo o uno es el basiónimo del otro);
        el miembro que es el propio aceptado; si ninguno, sin asignar (se registra en `self.unassigned`).
        """
        res = resolve_name(name, self.wcvp, self.wfo, hint=hint, author=author)
        p = res["parsed"]
        if res["outcome"] not in RESOLVED:
            keys = set(k for k in (p.key_full, p.key_alt) if k) if p is not None else set()
            for plant in self.plants:
                if plant.kind in UNRESOLVED_KINDS and keys & plant.keys:
                    return plant, "misma-clave"
            return self._unassigned(name, author, source, res, "sin-resolver")
        group = self.groups.get(res["accepted_key"])
        if not group:
            return self._unassigned(name, author, source, res, "fuera-del-universo")
        if len(group) == 1:
            return group[0], "grupo-unico"
        keys = set(k for k in (p.key_full, p.key_alt, res["matched_key"]) if k)
        for plant in group:
            if keys & plant.keys:
                return plant, "misma-clave"
        matched = self._row(res["backbone"], res["matched_id"])
        for plant in group:
            if any(_homotypic_with(matched, row) for row in plant.member_rows if row.get("_bb") == res["backbone"]):
                return plant, "homotipico"
        if matched is not None and matched.get("homotypic") == "T":
            for plant in group:
                if plant.is_core:
                    return plant, "homotipico"
        for plant in group:
            if plant.is_core:
                return plant, "aceptado-propio"
        return self._unassigned(name, author, source, res, "sin-asignar", group)

    def _unassigned(self, name, author, source, res, reason, group=None):
        self.unassigned.append({"source": source, "name": name, "author": author or "", "reason": reason,
                                "outcome": res["outcome"], "accepted_key": res.get("accepted_key", ""),
                                "group": [p.id for p in group] if group else []})
        if group:
            for plant in group:
                plant.flags.add("unassigned_rows")
        return None, reason

    def _row(self, kind, id_):
        bb = self.wcvp if kind == "wcvp" else self.wfo
        return bb.get(id_) if (bb is not None and id_) else None


def _tag(row, kind):
    row = dict(row)
    row["_bb"] = kind
    return row


def build_universe(entries, wcvp, wfo=None, use_variants=True):
    """Resuelve las entradas, aplica la regla de colisiones y asigna IDs únicos y alias.

    Pasa primero las entradas de USDA y luego las de la EMA que no estén en USDA; las de la EMA que caigan en una planta
    ya existente se unen a ella. Falla con `UniverseError` si dos plantas terminan con el mismo ID.
    """
    uni = Universe(wcvp, wfo)
    resolved = []
    standalone = []
    for entry in entries:
        if entry.key in uni.entries:
            raise UniverseError("clave de entrada repetida: %s" % entry.key)
        uni.entries[entry.key] = entry
        res = resolve_name(entry.name, wcvp, wfo, hint=entry.hint, author=entry.author, use_variants=use_variants)
        uni.resolutions[entry.key] = res
        if res["outcome"] in RESOLVED:
            bb = wcvp if res["backbone"] == "wcvp" else wfo
            resolved.append(_Resolved(entry, res, bb.get(res["matched_id"]), bb.get(res["accepted_id"])))
        else:
            standalone.append(entry)

    # Grupos por aceptado (clave de nombre, para unir los dos backbones sin mezclar sus IDs).
    groups = {}
    for r in resolved:
        r.kind = _classify(r)
        groups.setdefault(r.accepted["key_full"], []).append(r)
    for akey in sorted(groups):
        uni.groups[akey] = _plants_for_group(akey, groups[akey])
        uni.plants.extend(uni.groups[akey])

    # Identidades de la fuente (sin resolver, ambiguas, solo género).
    by_id = {}
    for entry in standalone:
        res = uni.resolutions[entry.key]
        pid = plant_slug(entry.name)
        existing = by_id.get(pid)
        p = res["parsed"]
        key = p.key_full if p is not None and p.key_full else None
        if existing is not None and existing.kind == res["outcome"] and (key is None or key in existing.keys or not existing.keys):
            _attach(existing, entry, res)
            continue
        plant = Plant(pid, entry.name, entry.author, res["outcome"])
        plant.backbone = res["backbone"]
        _attach(plant, entry, res)
        if key:
            plant.keys.add(key)
        if res["outcome"] == "ambiguous":
            plant.flags.add("homonym_unresolved")
        elif res["outcome"] == "genus_only":
            plant.flags.add("genus_only")
        else:
            plant.flags.add(res["outcome"])
        if existing is None:
            by_id[pid] = plant
        uni.plants.append(plant)

    _finish(uni)
    return uni


def _attach(plant, entry, res):
    plant.entries.append(entry)
    plant.flags.update(res["flags"])


def _cluster_x(items):
    """Agrupa entradas heterotípicas que son homotípicas entre sí (misma fila o mismo basiónimo, mismo backbone)."""
    clusters = []
    for r in items:
        for cl in clusters:
            if any(o.res["backbone"] == r.res["backbone"] and _homotypic_with(r.matched, o.matched) for o in cl):
                cl.append(r)
                break
        else:
            clusters.append([r])
    return clusters


def _best_row(cluster):
    rows = [r.matched for r in cluster]
    ids = set(r["id"] for r in rows)
    basionym_ids = set(r.get("basionym_id") for r in rows)
    pool = [r for r in rows if r["id"] in basionym_ids] or rows
    pool.sort(key=lambda r: (not _row_rank_is_species(r), r["name"], r["id"]))
    return pool[0] if pool else rows[0]


def _plants_for_group(akey, items):
    core = [r for r in items if r.kind in ("A", "H")]
    others = [r for r in items if r.kind == "X"]
    clusters = _cluster_x(others)
    split = (1 if core else 0) + len(clusters) > 1
    # Aceptado de referencia: el de WCVP si existe en el grupo.
    ref = next((r for r in items if r.res["backbone"] == "wcvp"), items[0])
    plants = []
    if core or not split:
        members = core if core else others
        plant = Plant(plant_slug(ref.accepted["name"]), ref.accepted["name"], ref.accepted["author"], "resolved")
        plant.backbone = ref.res["backbone"]
        plant.accepted_id = ref.accepted["id"]
        plant.family = ref.accepted.get("family", "")
        plant.is_core = bool(core)
        plant.keys.add(akey)
        plant.member_rows.append(_tag(ref.accepted, ref.res["backbone"]))
        for r in members:
            _join(plant, r)
        plants.append(plant)
        clusters_left = clusters if core else []
    else:
        clusters_left = clusters
    for cl in clusters_left:
        row = _best_row(cl)
        r0 = cl[0]
        plant = Plant(plant_slug(row["name"]), row["name"], row["author"], "heterotypic")
        plant.backbone = r0.res["backbone"]
        plant.accepted_id = r0.accepted["id"]
        plant.matched_id = row["id"]
        plant.family = r0.matched.get("family", "") or r0.accepted.get("family", "")
        for r in cl:
            _join(plant, r)
        plant.flags.add("split_group")
        plants.append(plant)
    if split:
        for plant in plants:
            plant.split = True
            plant.flags.add("split_group")
    return plants


def _join(plant, r):
    plant.entries.append(r.entry)
    plant.flags.update(r.res["flags"])
    p = r.res["parsed"]
    for k in (p.key_full, p.key_alt, r.res["matched_key"]):
        if k:
            plant.keys.add(k)
    row = _tag(r.matched, r.res["backbone"])
    if not any(x["id"] == row["id"] and x["_bb"] == row["_bb"] for x in plant.member_rows):
        plant.member_rows.append(row)


def _finish(uni):
    """IDs únicos y alias."""
    uni.plants.sort(key=lambda p: (p.id, p.name))
    seen = {}
    collisions = {}
    for plant in uni.plants:
        if plant.id in seen:
            collisions.setdefault(plant.id, [seen[plant.id]]).append(plant)
        else:
            seen[plant.id] = plant
    if collisions:
        detail = "; ".join("%s: %s" % (pid, " | ".join("%s [%s]" % (p.name, ", ".join(e.key for e in p.entries))
                                                        for p in plants))
                           for pid, plants in sorted(collisions.items()))
        raise UniverseError("IDs repetidos: " + detail, [(pid, plants) for pid, plants in sorted(collisions.items())])
    ids = set(seen)
    alias_owner = {}
    for plant in uni.plants:
        for entry in plant.entries:
            alias = plant_slug(entry.name)
            if not alias or alias == plant.id:
                continue
            if alias in ids:
                uni.discarded_aliases.append((plant.id, alias, "igual al ID de otra planta (%s)" % seen[alias].id))
            elif alias not in plant.aliases:
                alias_owner.setdefault(alias, []).append(plant)
                plant.aliases.append(alias)
    for alias, owners in alias_owner.items():
        distinct = sorted(set(o.id for o in owners))
        if len(distinct) > 1:
            for o in owners:
                if alias in o.aliases:
                    o.aliases.remove(alias)
                    uni.discarded_aliases.append((o.id, alias, "alias repetido en %s" % ", ".join(distinct)))
    for plant in uni.plants:
        plant.aliases.sort()
