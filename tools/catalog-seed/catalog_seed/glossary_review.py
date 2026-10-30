"""Candidatos, acepciones y tabla de revisión del glosario de actividades (tareas 1.2, 3.2 y 3.4). Solo lee: caché y catalog.db.

- `candidates`: actividades visibles más frecuentes que aún no están en la lista ni en excluidos.
- `format_senses`: acepciones numeradas de Wikcionario y extracto de Wikipedia de cada término, para la propuesta y la revisión.
- `build_review`: la tabla que aprueba el usuario (texto exacto que se mostraría, literal o adaptado, URL, alertas) y la cobertura.
"""
import sqlite3
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

from .glossary_extract import (article_first_sentence, article_intro, entry_status, first_sentence, length_problem,
                               normalize_space, parse_wiktionary)
from .glossary_terms import base_key, is_sensitive, text_alerts
from .sources import SourceError
from .validate import load_sensitive_activities
from .wiki import WikipediaArticleStep, WiktionaryStep

DEFAULT_CATALOG = Path(__file__).resolve().parents[3] / "data" / "build" / "catalog.db"
MIN_GROUPS = 7
APPROVAL_DATE = "2026-10-29"


def open_catalog(path):
    if not Path(path).is_file():
        raise SourceError("falta el catálogo %s; ejecute la construcción de catalog-ingest" % path)
    return sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(str(path)), uri=True)


def activity_stats(conn):
    """{forma base: {groups, plants, variants}} de los grupos visibles, y los totales de grupos y plantas visibles."""
    stats = defaultdict(lambda: {"groups": 0, "plants": set(), "variants": Counter()})
    all_plants, total = set(), 0
    for plant_id, activity in conn.execute("SELECT plant_id, activity FROM plant_use_group WHERE pending_review = 0"):
        entry = stats[base_key(activity)]
        entry["groups"] += 1
        entry["plants"].add(plant_id)
        entry["variants"][activity] += 1
        all_plants.add(plant_id)
        total += 1
    return stats, total, len(all_plants)


def candidates(conn, document, limit=None, min_groups=MIN_GROUPS):
    """[(actividad, grupos)] por frecuencia, sin las actividades sensibles ni las de la lista o de excluidos."""
    stats, _, _ = activity_stats(conn)
    sensitive = load_sensitive_activities()
    known = {base_key(t["activity"]) for t in document["terms"]} | {base_key(e["activity"]) for e in document.get("excluded", [])}
    rows = []
    for key, entry in stats.items():
        if key in known or entry["groups"] < min_groups or is_sensitive(entry["variants"].most_common(1)[0][0], sensitive):
            continue
        rows.append((entry["variants"].most_common(1)[0][0], entry["groups"]))
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows[:limit] if limit else rows


def _wiktionary_record(cache_dir, title):
    step = WiktionaryStep(cache_dir=cache_dir)
    return step.load(step.key_of(title)) if step.is_cached(step.key_of(title)) else None


def _wikipedia_record(cache_dir, title):
    step = WikipediaArticleStep(cache_dir=cache_dir)
    return step.load(step.key_of(title)) if step.is_cached(step.key_of(title)) else None


def revision_url(host, title, revid):
    return "https://%s/w/index.php?title=%s&oldid=%s" % (host, urllib.parse.quote(title.replace(" ", "_"), safe="_(),"), revid)


def format_senses(document, cache_dir, only=None):
    """Texto con las acepciones de cada término, para la propuesta de un agente y la revisión."""
    lines = []
    for term in document["terms"]:
        if only and term["activity"] not in only and term["wiktionaryTitle"] not in only:
            continue
        record = _wiktionary_record(cache_dir, term["wiktionaryTitle"])
        lines.append("== %s (Wikcionario: %s)" % (term["activity"], term["wiktionaryTitle"]))
        if record is None:
            lines.append("   sin descargar")
        elif entry_status(record) == "sin-entrada":
            lines.append("   sin entrada")
        else:
            parsed = parse_wiktionary(record["html"])
            status = entry_status(record)
            if status == "sin-español":
                lines.append("   la entrada no tiene sección en español (idiomas: %s)" % ", ".join(parsed["languages"]))
            else:
                if status == "forma-flexionada":
                    lines.append("   solo forma flexionada")
                lines.append("   revisión %s (%s)" % (record["revid"], record["timestamp"]))
                for sense in parsed["senses"]:
                    lines.append("   %d%s%s [%s] %s" % (sense["n"], " (%s)" % sense["mark"] if sense["mark"] else "",
                                                     " (IMPROPIA)" if sense["improper"] else "", sense["pos"], sense["text"]))
        if "wikipediaTitle" in term:
            article = _wikipedia_record(cache_dir, term["wikipediaTitle"])
            lines.append("   -- Wikipedia: %s" % term["wikipediaTitle"])
            if article is None:
                lines.append("      sin descargar")
            elif article.get("missing"):
                lines.append("      sin artículo")
            else:
                lines.append("      %s%s, revisión %s (%s)" % (article["title"], " [DESAMBIGUACIÓN]" if article["disambiguation"] else "",
                                                             article["revid"], article["timestamp"]))
                lines.append("      primera oración: %s" % article_first_sentence(article))
                for paragraph in article_intro(article)[:3]:
                    lines.append("      | %s" % paragraph)
    return "\n".join(lines)


def _row(term, cache_dir, approved):
    """Datos de una fila de la tabla de revisión, o None en `source` si el término aún no tiene propuesta."""
    row = {"activity": term["activity"], "source": term.get("source"), "reason": term.get("reason", ""), "alerts": []}
    source = term.get("source")
    if source == "wiktionary_es":
        record = _wiktionary_record(cache_dir, term["wiktionaryTitle"])
        sense = next((s for s in parse_wiktionary(record["html"])["senses"] if s["n"] == term["sense"]), None)
        if sense is None:
            raise SourceError("'%s': la entrada no tiene la acepción %s" % (term["activity"], term["sense"]))
        text = first_sentence(sense["text"])
        row.update(sourceName="Wikcionario", where="%s, acepción %d%s" % (term["wiktionaryTitle"], sense["n"], " (%s)" % sense["mark"] if sense["mark"] else ""),
                   text=text, mode="literal", url=revision_url("es.wiktionary.org", record["title"], record["revid"]))
        problem = length_problem(text)
    elif source == "wikipedia_es":
        record = _wikipedia_record(cache_dir, term["wikipediaTitle"])
        if record is None or record.get("missing"):
            raise SourceError("'%s': el artículo '%s' no está en la caché" % (term["activity"], term["wikipediaTitle"]))
        if term["mode"] == "literal":
            text, problem = article_first_sentence(record), None
            problem = length_problem(text)
        else:
            text, problem = term["text"], length_problem(term["text"]) if len(term["text"]) > 300 else None
            haystack = " ".join(article_intro(record))
            if normalize_space(term["evidence"]) not in haystack:
                row["alerts"].append("LA EVIDENCIA NO ES LITERAL respecto del extracto")
        row.update(sourceName="Wikipedia", where="artículo «%s»" % record["title"], text=text, mode=term["mode"],
                   url=revision_url("es.wikipedia.org", record["title"], record["revid"]))
        row["evidence"] = term.get("evidence")
        if record.get("disambiguation"):
            row["alerts"].append("el artículo es una página de desambiguación")
    else:
        row.update(sourceName="", where="", text="", mode="", url="")
        return row
    patterns = [a["pattern"].lower() for a in approved.get(term["activity"], [])]
    for alert in text_alerts(row["text"]):
        approved_here = any(("«%s" % p) in alert for p in patterns)
        row["alerts"].append(alert + (" (aprobado por el usuario el %s)" % APPROVAL_DATE if approved_here else " (SIN APROBAR)"))
    if problem:
        row["alerts"].append("revisar el recorte: %s" % problem)
    return row


def _cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def build_review(document, cache_dir, conn, today):
    stats, total_groups, total_plants = activity_stats(conn)
    approved = document.get("approvedPatterns", {})
    rows = [_row(t, cache_dir, approved) for t in document["terms"]]
    decided = [r for r in rows if r["source"]]
    pending = [r for r in rows if not r["source"]]

    def coverage(activities):
        groups, plants = 0, set()
        for activity in activities:
            entry = stats.get(base_key(activity))
            if entry:
                groups += entry["groups"]
                plants |= entry["plants"]
        return groups, len(plants)

    def covers(activity):
        entry = stats.get(base_key(activity))
        if not entry:
            return "0 grupos"
        variants = entry["variants"].most_common()
        extra = " (%s)" % "; ".join("%s %d" % v for v in variants[:3]) if len(variants) > 1 else ""
        return "%d grupos, %d plantas%s" % (entry["groups"], len(entry["plants"]), extra)

    out = ["# Revisión del glosario de actividades", "",
           "Tabla de la tarea 3.4 de `activity-glossary`, generada el %s con `glossary-review` desde la caché de descargas y `data/build/catalog.db`, sin red. Nada está sellado: `data/seed/` no se ha tocado." % today, "",
           "Cada fila muestra el texto exacto que la app mostraría bajo el título del grupo, con el formato `<Término>: «<texto>» (<fuente>)` y la etiqueta gris «Significado del término». «Literal» es texto de la fuente recortado a la primera oración; «adaptado» es una paráfrasis hecha solo con el extracto del artículo de Wikipedia y se muestra como «(adaptado de Wikipedia)».", "",
           "Complete la columna «Aprobado» con sí o no por fila. Los patrones vigilados de Antiséptico, Bactericida, Vulnerario, Antidiarreico, Fungicida y Parasiticida ya fueron aprobados por usted el %s; cualquier otra alerta sin aprobar bloquearía la validación." % APPROVAL_DATE, "",
           "## Términos con explicación", "",
           "| Término | Grupos que cubre | Fuente | Acepción o artículo | Texto que se mostraría | Modo | Revisión | Alertas del validador | Aprobado |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in decided:
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | |" % (
            _cell(r["activity"]), covers(r["activity"]), r["sourceName"], _cell(r["where"]), "«%s»" % _cell(r["text"]),
            "adaptado" if r["mode"] == "adapted" else "literal", r["url"], _cell("; ".join(r["alerts"]) or "ninguna")))
    if any(r.get("evidence") for r in decided):
        out += ["", "## Evidencia y motivo de cada propuesta", ""]
        for r in decided:
            out.append("- **%s** (%s): %s" % (r["activity"], "adaptado" if r["mode"] == "adapted" else "literal", r["reason"]))
            if r.get("evidence"):
                out.append("  - Evidencia literal del extracto: «%s»" % r["evidence"])
    else:
        out += ["", "## Motivo de cada propuesta", ""]
        for r in decided:
            out.append("- **%s**: %s" % (r["activity"], r["reason"]))
    if pending:
        out += ["", "## Términos sin propuesta", ""]
        out += ["- %s" % r["activity"] for r in pending]
    excluded = document.get("excluded", [])
    out += ["", "## Términos excluidos", "",
            "| Término | Grupos que cubriría | Motivo | Código | Fecha |", "| --- | --- | --- | --- | --- |"]
    for e in excluded:
        out.append("| %s | %s | %s | `%s` | %s |" % (_cell(e["activity"]), covers(e["activity"]), _cell(e["reason"]), e["code"], e["date"]))
    explained = [r["activity"] for r in decided]
    by_mode = Counter((r["sourceName"], r["mode"]) for r in decided)
    groups, plants = coverage(explained)
    ex_groups, ex_plants = coverage([e["activity"] for e in excluded])
    out += ["", "## Cobertura", "",
            "| Cifra | Valor |", "| --- | --- |",
            "| Términos candidatos | %d |" % (len(rows) + len(excluded)),
            "| Términos con explicación | %d |" % len(decided),
            "| Explicación literal de Wikcionario | %d |" % by_mode[("Wikcionario", "literal")],
            "| Explicación literal de Wikipedia | %d |" % by_mode[("Wikipedia", "literal")],
            "| Explicación adaptada de Wikipedia | %d |" % by_mode[("Wikipedia", "adapted")],
            "| Términos sin explicación (excluidos) | %d |" % len(excluded),
            "| Términos sin propuesta | %d |" % len(pending),
            "| Grupos con explicación (de %d visibles) | %d (%.1f %%) |" % (total_groups, groups, 100.0 * groups / total_groups),
            "| Plantas con alguna explicación (de %d con usos visibles) | %d (%.1f %%) |" % (total_plants, plants, 100.0 * plants / total_plants),
            "| Grupos de los términos excluidos | %d |" % ex_groups,
            "| Plantas con algún grupo de un término excluido | %d |" % ex_plants, ""]
    return "\n".join(out)
