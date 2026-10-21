"""Resolución de nombres al nombre aceptado: WCVP principal, WFO de respaldo y variantes ortográficas de epíteto."""
from .index import STATUS_CLASS  # noqa: F401  (reexportado para quien lo necesite)
from .names import author_score, make_keys, parse_name

OUTCOMES = ("accepted", "synonym", "ambiguous", "unresolved", "unmatched", "genus_only")
AUTHOR_THRESHOLD = 0.5

# Variantes ortográficas de epíteto (2.4). Cada par (a, b) se aplica en ambos sentidos al final del epíteto
# («suffix») o en cualquier posición («any»). La lista es deliberadamente corta: cada variante se prueba contra el
# backbone y solo se acepta si hay un único aceptado.
VARIANT_SUFFIX_PAIRS = (
    ("ii", "i"),          # meyerii / meyeri
    ("erus", "er"),       # ladaniferus / ladanifer
    ("us", "a"), ("us", "um"), ("a", "um"),           # género gramatical: albus / alba / album
    ("er", "ra"), ("er", "rum"), ("ra", "rum"),       # ruber / rubra / rubrum
    ("is", "e"),          # communis / commune
    ("ensis", "iensis"), ("ensis", "ense"),            # canadensis / canadiensis
    ("anus", "ianus"), ("ana", "iana"),
    ("ifolia", "ifolius"), ("ifolia", "ifolium"), ("ifolius", "ifolium"),
    ("oides", "oidea"), ("oides", "oideus"),
    ("ae", "i"),          # genitivo femenino / masculino: lindleyae / lindleyi
    ("ae", "e"),          # final -ae / -e
)
VARIANT_ANYWHERE_PAIRS = (
    ("ae", "e"), ("oe", "e"),    # caerulea / cerulea, foetida / fetida
    ("ph", "f"), ("y", "i"), ("k", "c"),
    ("ll", "l"), ("ss", "s"), ("tt", "t"), ("nn", "n"), ("rr", "r"),
)


def epithet_variants(epithet):
    """Variantes ortográficas de un epíteto, sin repetir y sin el propio epíteto, en orden determinista."""
    out = []

    def add(v):
        if v and v != epithet and v not in out:
            out.append(v)

    for a, b in VARIANT_SUFFIX_PAIRS:
        for x, y in ((a, b), (b, a)):
            if epithet.endswith(x) and len(epithet) > len(x) + 1:
                add(epithet[:-len(x)] + y)
    for a, b in VARIANT_ANYWHERE_PAIRS:
        for x, y in ((a, b), (b, a)):
            start = 0
            while True:
                pos = epithet.find(x, start)
                if pos < 0:
                    break
                add(epithet[:pos] + y + epithet[pos + len(x):])
                start = pos + 1
    return out


def _empty(outcome, backbone):
    return {"outcome": outcome, "backbone": backbone, "matched_id": "", "matched_name": "", "matched_status": "",
            "matched_key": "", "accepted_id": "", "accepted_name": "", "accepted_authors": "", "accepted_rank": "",
            "accepted_family": "", "accepted_key": "", "fallback_binomial": False, "homonym_present": False,
            "flags": [], "notes": "", "candidates": [], "parsed": None}


def _accepted_of(row, bb):
    """Sigue la cadena hasta un aceptado. Devuelve (fila_aceptada | None, nota)."""
    cur = row
    for _ in range(6):
        if bb.status_class(cur["status"]) == 1:
            return cur, ""
        aid = cur["accepted_id"]
        if not aid:
            return None, "sin_aceptado"
        nxt = bb.get(aid)
        if nxt is None:
            return None, "aceptado_%s_no_esta_en_el_indice" % aid
        cur = nxt
    return None, "cadena_de_aceptados_demasiado_larga"


def _evaluate(candidates, bb):
    ev = []
    for c in candidates:
        cls = bb.status_class(c["status"])
        acc, note = _accepted_of(c, bb)
        if acc is None:
            cls_eff = 5
        elif cls == 5:
            cls_eff = 3   # Unplaced/Unchecked con aceptado utilizable: se trata como ilegítimo (con marca)
        else:
            cls_eff = cls
        ev.append({"c": c, "cls": cls_eff, "acc": acc, "note": note})
    return ev


def _cand_info(e):
    return {"id": e["c"]["id"], "name": e["c"]["name"], "author": e["c"]["author"], "status": e["c"]["status"],
            "accepted_id": e["acc"]["id"] if e["acc"] else "", "accepted_name": e["acc"]["name"] if e["acc"] else ""}


def _decide(ev, author, out, flags):
    """Elige entre los candidatos evaluados y rellena `out`. Aplica desempate por autor, prioridad de estado y homónimos."""
    sel = ev
    tiebreak = False
    if author and len(ev) > 1:
        scores = [author_score(author, e["c"]["author"]) for e in ev]
        best_score = max(scores)
        matched = [e for e, sc in zip(ev, scores) if sc == best_score]
        if best_score >= AUTHOR_THRESHOLD and len(matched) < len(ev):
            if all(e["cls"] == 5 for e in matched) and any(e["cls"] != 5 for e in ev):
                flags.append("author_tiebreak_ignored")
            else:
                sel = matched
                tiebreak = True
                flags.append("author_tiebreak")
    best = min(e["cls"] for e in sel)
    top = [e for e in sel if e["cls"] == best]
    out["candidates"] = [_cand_info(e) for e in ev]
    if best == 5:
        e = top[0]
        out["outcome"] = "unresolved"
        _set_matched(out, e)
        out["notes"] = "solo filas sin aceptado utilizable (%s)" % ", ".join(sorted(set(x["c"]["status"] for x in top)))
        return
    acc_ids = sorted(set(e["acc"]["id"] for e in top))
    if len(acc_ids) > 1:
        out["outcome"] = "ambiguous"
        flags.append("homonym_unresolved")
        out["notes"] = "%d aceptados distintos sin desempate: %s" % (
            len(acc_ids), "; ".join("%s (%s)" % (e["acc"]["name"], e["acc"]["id"]) for e in top))
        return
    top.sort(key=lambda e: int(e["c"]["id"]) if e["c"]["id"].isdigit() else e["c"]["id"])
    e = top[0]
    acc = e["acc"]
    rivals = [x for x in ev if x["cls"] in (1, 2, 3) and x["acc"] is not None and x["acc"]["id"] != acc["id"]]
    if best != 1 and rivals and not tiebreak:
        out["outcome"] = "ambiguous"
        flags.append("homonym_unresolved")
        out["notes"] = "homónimo sin resolver: %s frente a %s" % (
            acc["name"], "; ".join(sorted(set("%s (%s)" % (x["acc"]["name"], x["c"]["status"]) for x in rivals))))
        return
    _set_matched(out, e)
    out.update({"accepted_id": acc["id"], "accepted_name": acc["name"], "accepted_authors": acc["author"],
                "accepted_rank": acc["rank"], "accepted_family": acc["family"], "accepted_key": acc["key_full"]})
    if best == 1:
        out["outcome"] = "accepted"
    else:
        out["outcome"] = "synonym"
        if best == 3:
            flags.append("status_" + e["c"]["status"].lower().replace(" ", "_"))
        if best == 4:
            flags.append("misapplied")
    if rivals:
        out["homonym_present"] = True
        flags.append("homonym_present")
        out["notes"] = "otros candidatos hacia: " + "; ".join(
            sorted(set("%s (%s)" % (x["acc"]["name"], x["c"]["status"]) for x in rivals)))


def _set_matched(out, e):
    c = e["c"]
    out["matched_id"], out["matched_name"], out["matched_status"], out["matched_key"] = (
        c["id"], c["name"], c["status"], c["key_full"])


def _tiebreak_author(p, fallback):
    """Autor para el desempate: el infraespecífico si la clave es infraespecífica; si no, el de la especie."""
    if p.autonym:
        return p.species_author or p.author
    if p.infra_epithet and not fallback:
        return p.author
    return p.species_author


def resolve(name_text, backbone, hint=None, author=None):
    """Resuelve un nombre contra un backbone. `author` opcional se añade al autor del texto (p. ej. USDA lo trae aparte).

    Devuelve un dict con `outcome` (accepted, synonym, ambiguous, unresolved, unmatched o genus_only), `backbone`,
    los datos de la fila coincidente y del aceptado, `flags`, `notes`, `candidates` y `parsed` (ParsedName).
    """
    text = name_text if not author else "%s %s" % (name_text, author)
    p = parse_name(text, hint=hint)
    out = _empty("unmatched", backbone.kind)
    out["parsed"] = p
    flags = list(p.flags)
    out["flags"] = flags
    if p.genus_only:
        out["outcome"] = "genus_only"
        return out
    if not p.ok:
        out["notes"] = "nombre no interpretable"
        return out
    cands = backbone.lookup(p.key_full)
    if not cands and p.key_alt:
        cands = backbone.lookup(p.key_alt)
        if cands:
            flags.append("autonym_infra_key")
    fallback = False
    if not cands and p.infra_epithet and p.key_binomial != p.key_full:
        cands = backbone.lookup(p.key_binomial)
        if cands:
            fallback = True
            flags.append("fallback_binomial")
    out["fallback_binomial"] = fallback
    if not cands:
        out["notes"] = "sin candidatos para %s" % p.key_full
        return out
    ev = _evaluate(cands, backbone)
    _decide(ev, _tiebreak_author(p, fallback), out, flags)
    out["flags"] = sorted(set(flags))
    return out


def resolve_variants(name_text, backbone, hint=None, author=None):
    """Prueba variantes ortográficas del epíteto (el de la especie o el infraespecífico). Resultado marcado.

    Solo acepta la variante si todas las que dan coincidencia resuelven al mismo aceptado; si no, queda `ambiguous`.
    """
    text = name_text if not author else "%s %s" % (name_text, author)
    p = parse_name(text, hint=hint)
    base = _empty("unmatched", backbone.kind)
    base["parsed"] = p
    base["flags"] = list(p.flags)
    if not p.ok or p.genus_only:
        return base
    found = []   # (variante, resolución)
    seen = set()
    targets = [("species", p.species)]
    if p.infra_epithet and not p.autonym:
        targets.append(("infra", p.infra_epithet))
    for where, epithet in targets:
        for variant in epithet_variants(epithet):
            species = variant if where == "species" else p.species
            infra = variant if where == "infra" else p.infra_epithet
            key_full, key_bin = make_keys(p.genus, species, p.infra_rank, infra)
            if p.autonym:
                key_full = key_bin
            if key_full in seen:
                continue
            seen.add(key_full)
            cands = backbone.lookup(key_full)
            if not cands:
                continue
            out = _empty("unmatched", backbone.kind)
            out["parsed"] = p
            flags = list(p.flags)
            out["flags"] = flags
            _decide(_evaluate(cands, backbone), _tiebreak_author(p, False), out, flags)
            if out["outcome"] in ("accepted", "synonym"):
                found.append((key_full, out))
    if not found:
        return base
    accepted_ids = sorted(set(o["accepted_id"] for _, o in found))
    if len(accepted_ids) > 1:
        base["outcome"] = "ambiguous"
        base["flags"] = sorted(set(base["flags"] + ["orthographic_variant", "homonym_unresolved"]))
        base["notes"] = "variantes ortográficas con aceptados distintos: " + "; ".join(
            "%s -> %s" % (k, o["accepted_name"]) for k, o in found)
        return base
    # prefiere la variante cuya fila coincidente es Accepted, luego la de clave más corta; es determinista
    found.sort(key=lambda ko: (ko[1]["outcome"] != "accepted", ko[0]))
    key, out = found[0]
    out["flags"] = sorted(set(out["flags"] + ["orthographic_variant"]))
    out["notes"] = ("variante ortográfica %s; " % key + out["notes"]).strip("; ")
    return out


def _resolved(r):
    return r["outcome"] in ("accepted", "synonym")


def resolve_name(name_text, wcvp, wfo=None, hint=None, author=None, use_variants=True):
    """Resolución completa: WCVP, variantes ortográficas de WCVP, respaldo de WFO y variantes de WFO.

    - WFO solo se usa si WCVP da `unmatched`, `ambiguous` o `unresolved` y WFO da un único aceptado (flag `wfo_fallback`).
    - Si los dos resuelven y discrepan en el aceptado, se conserva el de WCVP con `backbone_disagreement`.
    - Una variante ortográfica se acepta solo como respaldo marcado (`orthographic_variant`); la de WCVP precede al
      respaldo de WFO porque un sinónimo de WFO exacto puede apuntar a otra especie (`Cistus ladaniferus`).
    - Nunca se mezclan IDs de los dos backbones: `backbone` dice cuál dio el resultado.
    """
    rw = resolve(name_text, wcvp, hint, author)
    if rw["outcome"] == "genus_only":
        return rw
    rf = resolve(name_text, wfo, hint, author) if wfo is not None else None
    if _resolved(rw):
        if rf is not None and _resolved(rf) and rf["accepted_key"] != rw["accepted_key"]:
            rw["flags"] = sorted(set(rw["flags"] + ["backbone_disagreement"]))
            rw["notes"] = ("WFO acepta %s; " % rf["accepted_name"] + rw["notes"]).strip("; ")
            rw["wfo_accepted_id"] = rf["accepted_id"]
            rw["wfo_accepted_name"] = rf["accepted_name"]
        return rw
    if use_variants and rw["outcome"] == "unmatched":
        rv = resolve_variants(name_text, wcvp, hint, author)
        if _resolved(rv):
            return rv
        if rv["outcome"] == "ambiguous":
            return rv
    if rf is not None and _resolved(rf):
        rf["flags"] = sorted(set(rf["flags"] + ["wfo_fallback"]))
        rf["notes"] = ("respaldo de WFO (WCVP: %s); " % rw["outcome"] + rf["notes"]).strip("; ")
        return rf
    if wfo is not None and use_variants and rf is not None and rf["outcome"] == "unmatched" and rw["outcome"] == "unmatched":
        rv = resolve_variants(name_text, wfo, hint, author)
        if _resolved(rv):
            rv["flags"] = sorted(set(rv["flags"] + ["wfo_fallback"]))
            return rv
    return rw


def synonyms(accepted_id, backbone, include_self=False):
    """Nombres con ese aceptado (estado, autor, `homotypic`, `basionym_id`)."""
    return backbone.synonyms(accepted_id, include_self)
