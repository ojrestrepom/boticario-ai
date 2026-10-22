"""Comando `collisions-decide`: aplica el criterio de Wikipedia a los grupos de colisión sin decisión registrada.

Es el único paso con red de la regla de colisiones. `resolve` solo lee el archivo de decisiones; este comando consulta
es.wikipedia.org (título por título, por lotes, con caché, `Retry-After` y reanudación) únicamente para los miembros
heterotípicos de grupos que aún no tienen decisión, aplica el criterio y las excepciones «separar siempre» y agrega las
decisiones al archivo. Nunca sobrescribe una decisión registrada: cambiarla es una edición manual del archivo.

Criterio, para un miembro heterotípico M frente al aceptado A del grupo (se compara siempre el título final tras seguir
las redirecciones):

- Se prueban varias variantes de título para M y para A: el nombre de WCVP, los nombres de origen de las entradas (USDA o EMA, sin autor) y las formas del híbrido (`×` pegada, separada y sin marca).
- M figura en las excepciones: `separate` / `excepcion`.
- M tiene artículo propio (existe, no es redirección) distinto del artículo de A: `separate` / `articulo-propio`.
- M tiene artículo propio y A redirige a él (o es el mismo): `fuse` / `articulo-compartido`.
- M es una redirección: `fuse` / `redireccion`.
- M no existe (o es una página de desambiguación): `fuse` / `sin-articulo`.
"""
from .resolve_universe import build_universe_from_work
from .taxonomy.collisions import (FUSE, SEPARATE, CollisionRules, dump_decisions, load_decisions, load_exceptions,
                                  validate_decisions)
from .wiki import WikipediaTitlesStep

DEFAULT_DELAY = 1.0


def title_variants(name):
    """Títulos a probar para un nombre: tal cual y, en los híbridos, con la `×` pegada o separada del epíteto y sin la marca
    (en Wikipedia en español los artículos de híbridos suelen estar sin `×`)."""
    name = " ".join(name.split())
    out = [name]
    if "×" in name:
        glued = name.replace("× ", "×")
        spaced = name.replace("×", "× ").replace("×  ", "× ")
        plain = " ".join(name.replace("×", " ").split())
        for alt in (glued, spaced, plain):
            if alt not in out:
                out.append(alt)
    return out


def titles_of(names):
    """Variantes de título de varios nombres (el de WCVP y los de origen de las entradas), sin repetir y en orden."""
    out = []
    for name in names:
        for title in title_variants(name):
            if title not in out:
                out.append(title)
    return out


def member_names(record):
    return [record["name"]] + [n for n in record["names"] if n != record["name"]]


def accepted_names(record):
    return [record["accepted"]] + [n for n in record["accepted_names"] if n != record["accepted"]]


def evidence_of(record):
    """Evidencia que se guarda de una consulta: título consultado, si existe, si es redirección, destino final y fecha."""
    return {"title": record["title"], "exists": record["exists"], "redirect": record["redirect"], "target": record["target"],
            "disambiguation": record["disambiguation"], "date": record["date"]}


def _live(records):
    return [r for r in records if r["exists"] and not r["disambiguation"]]


def judge(member_records, accepted_records, exception_reason=None):
    """`(decisión, motivo)` de un miembro heterotípico según el criterio de Wikipedia.

    Cada lista trae un registro por título probado (nombre de WCVP, nombres de origen de las entradas y variantes de la `×`).
    Si alguna variante del miembro tiene artículo propio distinto de todos los artículos del aceptado, se separa; si todas las
    que tienen artículo propio comparten artículo con el aceptado, se fusiona por artículo compartido; si solo hay redirecciones,
    se fusiona por redirección."""
    if exception_reason:
        return SEPARATE, "excepcion"
    accepted_articles = set(r["target"] for r in _live(accepted_records))
    live = _live(member_records)
    own = [r for r in live if not r["redirect"]]
    if own:
        if all(r["target"] in accepted_articles for r in own):
            return FUSE, "articulo-compartido"
        return SEPARATE, "articulo-propio"
    if live:
        return FUSE, "redireccion"
    return FUSE, "sin-articulo"


def pending_members(uni):
    """Miembros heterotípicos sin decisión registrada, agrupados por clave del aceptado."""
    groups = {}
    for record in uni.collisions:
        if record["state"] == "sin-decision":
            groups.setdefault(record["accepted_key"], []).append(record)
    return groups


def decide(groups, records_of):
    """Aplica el criterio a `groups` (de `pending_members`); `records_of(titulo)` da el registro de Wikipedia de un título.

    Devuelve `{accepted_key: {accepted, acceptedEvidence, members: {member_key: {...}}}}` listo para el archivo.
    """
    out = {}
    for akey in sorted(groups):
        members = groups[akey]
        accepted_records = [records_of(t) for t in titles_of(accepted_names(members[0]))]
        entry = {"accepted": members[0]["accepted"], "acceptedEvidence": [evidence_of(r) for r in accepted_records], "members": {}}
        for record in sorted(members, key=lambda m: m["member"]):
            member_records = [records_of(t) for t in titles_of(member_names(record))]
            decision, reason = judge(member_records, accepted_records, record["exception"])
            entry["members"][record["member"]] = {
                "name": record["name"], "decision": decision, "reason": reason,
                "evidence": [evidence_of(r) for r in member_records],
                "date": max(r["date"] for r in member_records + accepted_records)}
            if record["exception"]:
                entry["members"][record["member"]]["exception"] = record["exception"]
        out[akey] = entry
    return out


def titles_to_query(groups):
    titles = []
    for members in groups.values():
        names = accepted_names(members[0])
        for record in members:
            names = names + member_names(record)
        for title in titles_of(names):
            if title not in titles:
                titles.append(title)
    return titles


def merge_decisions(document, new_groups):
    """Agrega las decisiones nuevas sin tocar ninguna registrada. Devuelve cuántos miembros se agregaron."""
    added = 0
    for akey, group in new_groups.items():
        target = document["groups"].setdefault(akey, {"accepted": group["accepted"], "acceptedEvidence": group["acceptedEvidence"],
                                                      "members": {}})
        for mkey, member in group["members"].items():
            if mkey not in target["members"]:
                target["members"][mkey] = member
                added += 1
    return added


def run_collisions_decide(sources, cache_dir, db_path, taxonomy_db, decisions_path, exceptions_path, delay=DEFAULT_DELAY,
                          request=None, log=print):
    """Devuelve un dict con `status`: `disabled`, `nothing`, `rate_limited`, `waiting` o `complete`."""
    declared = next((s for s in sources if s.id == "wikipedia_es"), None)
    if declared is None or not declared.enabled:
        log("wikipedia_es: desactivada; collisions-decide no consulta nada y no cambia %s" % decisions_path)
        return {"status": "disabled", "added": 0}
    document = load_decisions(decisions_path)
    rules = CollisionRules(document, load_exceptions(exceptions_path))
    with build_universe_from_work(db_path, taxonomy_db, rules=rules, log=log) as (uni, _):
        groups = pending_members(uni)
    if not groups:
        log("collisions-decide: todos los grupos con colisión ya tienen decisión; no se consulta nada")
        return {"status": "nothing", "added": 0}
    titles = titles_to_query(groups)
    kwargs = {"request": request} if request else {}
    step = WikipediaTitlesStep(cache_dir=cache_dir, delay=delay, **kwargs)
    result = step.run(titles)
    result["groups"] = len(groups)
    if result["status"] != "complete":
        log("collisions-decide: detenido por límite de peticiones (%s); pendientes %d de %d. No reintentar antes de %s; "
            "estado en %s. El archivo de decisiones no cambió." % (result["reason"], result["pending"], result["total"],
                                                                    result["retry_at"], step.resume_path()))
        return dict(result, added=0)
    decided = decide(groups, lambda title: step.load(step.key_of(title)))
    added = merge_decisions(document, decided)
    validate_decisions(document, str(decisions_path))
    dump_decisions(decisions_path, document)
    log("collisions-decide: %d grupos, %d miembros decididos, %d peticiones; archivo %s" % (len(groups), added, step.requests_made, decisions_path))
    return dict(result, added=added)
