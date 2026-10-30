"""Armado determinista de `glossary.json` desde la lista de términos y la caché de descargas (tarea 4.1). Sin red.

Cada fila lleva la clave de la forma base (D8), el término, el texto (literal recortado a la primera oración o adaptado),
la fuente, la marca `adapted`, la acepción (nula en Wikipedia), la URL permanente de la revisión (`oldid`), el identificador y la
hora de la revisión y la fecha de descarga. Solo entran los términos que el usuario aprobó (`approved`).
"""
import json
from pathlib import Path

from .glossary_extract import article_first_sentence, first_sentence, length_problem, normalize_space, parse_wiktionary
from .glossary_review import revision_url
from .glossary_terms import base_key
from .sources import SourceError
from .wiki import WikipediaArticleStep, WiktionaryStep

FORMAT = "catalog-glossary/1"
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
CHANGES = ("Definiciones de Wikcionario y de Wikipedia en español bajo CC BY-SA 4.0. Cambios: se retiró el marcado, las notas y las listas "
           "de sinónimos, antónimos, usos y ejemplos, y el texto se recortó a la primera oración; los textos marcados como adaptados "
           "son paráfrasis hechas solo con el texto del artículo de Wikipedia. El historial de cada entrada lista a sus autores.")
SOURCE_NAMES = {"wiktionary_es": "Wikcionario", "wikipedia_es": "Wikipedia"}


def fetched_date(step, title):
    """Fecha (AAAA-MM-DD) en que se descargó la entrada, tomada del archivo de la caché."""
    path = step.cache_path(step.key_of(title))
    return json.loads(path.read_text(encoding="utf-8"))["fetched_at"][:10]


def build_row(term, cache_dir):
    activity = term["activity"]
    if "approved" not in term:
        raise SourceError("'%s': el término no tiene la aprobación del usuario ('approved')" % activity)
    source = term["source"]
    if source == "wiktionary_es":
        step = WiktionaryStep(cache_dir=cache_dir)
        title = term["wiktionaryTitle"]
        if not step.is_cached(step.key_of(title)):
            raise SourceError("'%s': falta la entrada '%s' en la caché; ejecute glossary-fetch" % (activity, title))
        record = step.load(step.key_of(title))
        sense = next((s for s in parse_wiktionary(record["html"])["senses"] if s["n"] == term["sense"]), None) if not record.get("missing") else None
        if sense is None:
            raise SourceError("'%s': la entrada '%s' no tiene la acepción %s" % (activity, title, term["sense"]))
        text, sense_number, adapted, host = normalize_space(sense["text"]), sense["n"], False, "es.wiktionary.org"
        text = first_sentence(text)
    else:
        step = WikipediaArticleStep(cache_dir=cache_dir)
        title = term["wikipediaTitle"]
        if not step.is_cached(step.key_of(title)):
            raise SourceError("'%s': falta el artículo '%s' en la caché; ejecute glossary-fetch" % (activity, title))
        record = step.load(step.key_of(title))
        if record.get("missing"):
            raise SourceError("'%s': el artículo '%s' no existe" % (activity, title))
        adapted = term["mode"] == "adapted"
        text = term["text"] if adapted else article_first_sentence(record)
        sense_number, host = None, "es.wikipedia.org"
    problem = length_problem(text or "")
    if problem:
        raise SourceError("'%s': el texto %s; revíselo a mano (%s)" % (activity, problem, text))
    return {"key": base_key(activity), "term": activity, "text": text, "sourceId": source, "sourceName": SOURCE_NAMES[source],
            "adapted": adapted, "sense": sense_number, "entryUrl": revision_url(host, record["title"], record["revid"]),
            "revisionId": record["revid"], "revisionTimestamp": record["timestamp"], "retrievedAt": fetched_date(step, title)}


def build_glossary(terms_document, cache_dir):
    rows = sorted((build_row(t, cache_dir) for t in terms_document["terms"]), key=lambda r: r["key"])
    return {"format": FORMAT, "license": LICENSE, "licenseUrl": LICENSE_URL, "changes": CHANGES, "rows": rows}
