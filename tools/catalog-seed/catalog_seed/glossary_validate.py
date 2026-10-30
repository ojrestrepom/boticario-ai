"""Validación del glosario de actividades (tarea 4.2, D10).

Comprueba el esquema, el orden y la unicidad de las claves, que el texto esté en español y termine en punto, que el término no sea
sensible, que no haya dosis ni posología (sin aprobación posible), que los patrones de eficacia solo aparezcan si el usuario los
aprobó para ese término, que no se nombren enfermedades graves y, si se da la lista de términos y la caché, que el texto literal
coincida con la fuente y que la evidencia de un texto adaptado esté en el extracto. Un error impide que el glosario entre en la semilla.
"""
import re

from .glossary_extract import article_first_sentence, article_intro, first_sentence, normalize_space, parse_wiktionary
from .glossary_terms import SERIOUS_DISEASE_RE, base_key, is_sensitive
from .validate import DOSE_PATTERNS, load_sensitive_activities

ROW_FIELDS = ("key", "term", "text", "sourceId", "sourceName", "adapted", "sense", "entryUrl", "revisionId", "revisionTimestamp", "retrievedAt")
TOP_FIELDS = ("format", "license", "licenseUrl", "changes", "rows")
SOURCES = {"wiktionary_es": "Wikcionario", "wikipedia_es": "Wikipedia"}
_DOSE_INDEXES = (0, 1, 2, 3, 4, 5, 6, 12, 13)  # dosis, posología, unidades, gotas, cucharadas: nunca se aprueban
DOSE_ONLY_RE = re.compile("|".join(DOSE_PATTERNS[i] for i in _DOSE_INDEXES), re.IGNORECASE)
EFFICACY_RE = re.compile("|".join(p for i, p in enumerate(DOSE_PATTERNS) if i not in _DOSE_INDEXES), re.IGNORECASE)
SPANISH_WORDS = {"que", "de", "la", "el", "los", "las", "se", "para", "un", "una", "y", "o", "en", "del", "con", "por", "sustancia",
                 "dice", "capaz", "dicho", "medicamento", "fármaco", "al", "a"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def looks_spanish(text):
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(1 for c in letters if c.isascii() or c in "áéíóúüñÁÉÍÓÚÜÑ") / len(letters) < 0.95:
        return False
    return any(word in SPANISH_WORDS for word in re.findall(r"[a-záéíóúüñ]+", text.lower()))


def validate_glossary(document, terms=None, cache_dir=None, sensitive=None, approved=None):
    """Lista de errores (vacía si el glosario es válido). `terms` es la lista de términos ya cargada; `cache_dir`, la caché de descargas."""
    sensitive = sensitive if sensitive is not None else load_sensitive_activities()
    errors = []
    if not isinstance(document, dict):
        return ["el glosario debe ser un objeto"]
    for field in TOP_FIELDS:
        if field not in document:
            errors.append("falta el campo '%s'" % field)
    if document.get("format") != "catalog-glossary/1":
        errors.append("'format' debe ser catalog-glossary/1")
    if document.get("license") != "CC BY-SA 4.0":
        errors.append("'license' debe ser CC BY-SA 4.0")
    if not str(document.get("licenseUrl", "")).startswith("https://"):
        errors.append("'licenseUrl' debe ser una URL https")
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        return errors + ["'rows' debe ser una lista no vacía"]
    keys = []
    by_term = {base_key(t["activity"]): t for t in terms["terms"]} if terms else {}
    approved = approved if approved is not None else (terms or {}).get("approvedPatterns", {})
    for row in rows:
        label = row.get("term", "?") if isinstance(row, dict) else "?"
        if not isinstance(row, dict) or set(row) != set(ROW_FIELDS):
            errors.append("%s: la fila debe tener exactamente los campos %s" % (label, ", ".join(ROW_FIELDS)))
            continue
        keys.append(row["key"])
        if row["key"] != base_key(row["term"]):
            errors.append("%s: la clave '%s' no es la forma base del término" % (label, row["key"]))
        if row["sourceId"] not in SOURCES or row["sourceName"] != SOURCES[row["sourceId"]]:
            errors.append("%s: fuente inválida (%s, %s)" % (label, row["sourceId"], row["sourceName"]))
        if not isinstance(row["adapted"], bool) or (row["adapted"] and row["sourceId"] != "wikipedia_es"):
            errors.append("%s: 'adapted' debe ser booleano y solo puede ser verdadero en Wikipedia" % label)
        if row["sourceId"] == "wiktionary_es" and not (isinstance(row["sense"], int) and row["sense"] >= 1):
            errors.append("%s: la acepción debe ser un entero positivo" % label)
        if row["sourceId"] == "wikipedia_es" and row["sense"] is not None:
            errors.append("%s: la acepción de Wikipedia debe ser nula" % label)
        url = row["entryUrl"]
        if not (isinstance(url, str) and url.startswith("https://") and "oldid=%s" % row["revisionId"] in url):
            errors.append("%s: 'entryUrl' debe ser https y llevar el oldid de la revisión" % label)
        if not isinstance(row["revisionId"], int) or not row["revisionTimestamp"] or not DATE_RE.match(str(row["retrievedAt"])):
            errors.append("%s: revisión o fecha de descarga inválidas" % label)
        text = row["text"]
        if not isinstance(text, str) or not text.strip():
            errors.append("%s: el texto está vacío" % label)
            continue
        if text != normalize_space(text) or not text.endswith("."):
            errors.append("%s: el texto debe estar normalizado y terminar en punto" % label)
        if not looks_spanish(text):
            errors.append("%s: el texto no parece estar en español" % label)
        if is_sensitive(row["term"], sensitive):
            errors.append("%s: es una actividad sensible" % label)
        for match in DOSE_ONLY_RE.finditer(text):
            errors.append("%s: el texto contiene dosis o posología «%s», que no se puede aprobar" % (label, match.group(0)))
        allowed = [p["pattern"].lower() for p in approved.get(row["term"], [])]
        for match in EFFICACY_RE.finditer(text):
            if match.group(0).lower() not in allowed:
                errors.append("%s: patrón de eficacia «%s» sin aprobar para este término" % (label, match.group(0)))
        for match in SERIOUS_DISEASE_RE.finditer(text):
            errors.append("%s: el texto nombra una enfermedad grave «%s»" % (label, match.group(0)))
        if terms is not None:
            term = by_term.get(row["key"])
            if term is None:
                errors.append("%s: no figura en la lista de términos" % label)
            else:
                if "approved" not in term:
                    errors.append("%s: el término no tiene la aprobación del usuario" % label)
                errors.extend(_check_source(row, term, cache_dir, label))
    if keys != sorted(keys):
        errors.append("las filas no están ordenadas por clave")
    if len(keys) != len(set(keys)):
        errors.append("hay claves repetidas")
    return errors


def _check_source(row, term, cache_dir, label):
    """Coherencia de la fila con la lista de términos y, si hay caché, con la fuente."""
    errors = []
    if row["sourceId"] != term.get("source") or row["adapted"] != (term.get("mode") == "adapted"):
        errors.append("%s: la fuente o el modo no coinciden con la lista de términos" % label)
        return errors
    if row["adapted"] and row["text"] != term.get("text"):
        errors.append("%s: el texto adaptado no coincide con la lista de términos" % label)
    if cache_dir is None:
        return errors
    from .wiki import WikipediaArticleStep, WiktionaryStep
    if row["sourceId"] == "wiktionary_es":
        step = WiktionaryStep(cache_dir=cache_dir)
        title = term["wiktionaryTitle"]
        if not step.is_cached(step.key_of(title)):
            return errors + ["%s: falta la entrada '%s' en la caché" % (label, title)]
        record = step.load(step.key_of(title))
        sense = next((s for s in parse_wiktionary(record.get("html", ""))["senses"] if s["n"] == row["sense"]), None)
        if sense is None or first_sentence(sense["text"]) != row["text"]:
            errors.append("%s: el texto no es literal respecto de la acepción %s de la caché" % (label, row["sense"]))
    else:
        step = WikipediaArticleStep(cache_dir=cache_dir)
        title = term["wikipediaTitle"]
        if not step.is_cached(step.key_of(title)):
            return errors + ["%s: falta el artículo '%s' en la caché" % (label, title)]
        record = step.load(step.key_of(title))
        if record.get("missing"):
            return errors + ["%s: el artículo '%s' no existe" % (label, title)]
        if row["adapted"]:
            if normalize_space(term.get("evidence", "")) not in " ".join(article_intro(record)) or not term.get("evidence"):
                errors.append("%s: la evidencia del texto adaptado no es literal respecto del extracto" % label)
        elif article_first_sentence(record) != row["text"]:
            errors.append("%s: el texto no es literal respecto de la primera oración del artículo" % label)
    if record.get("revid") != row["revisionId"]:
        errors.append("%s: la revisión de la fila (%s) no coincide con la de la caché (%s)" % (label, row["revisionId"], record.get("revid")))
    return errors
