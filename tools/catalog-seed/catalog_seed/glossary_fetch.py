"""Comando `glossary-fetch`: descarga de las entradas de Wikcionario y de los artículos de Wikipedia del glosario.

Wikcionario se consulta para todos los términos de la lista (`wiktionaryTitle`); Wikipedia solo para los que declaran un
artículo (`wikipediaTitle`). Una petición a la vez, con pausa, `User-Agent` genérico, `Retry-After` y reanudación. Las respuestas
quedan en `data/.cache/wiktionary_es/` y `data/.cache/wikipedia_es/glossary/` (ignoradas por Git). `--refresh <título>` vuelve a
pedir una entrada: es el único modo de actualizar una revisión fijada.
"""
from pathlib import Path

from .sources import SourceError
from .wiki import WikipediaArticleStep, WiktionaryStep
from .wiki_fetch import ASSUMED_LATENCY, run_step

SOURCE_FIELDS = {"wiktionary_es": "wiktionaryTitle", "wikipedia_es": "wikipediaTitle"}
# Wikcionario cuesta dos peticiones por entrada hallada (parse y metadatos de la revisión).
ASSUMED_LATENCY.setdefault("wiktionary_es", 2.5)
ASSUMED_LATENCY.setdefault("wikipedia_es_glossary", 0.5)


def titles_for(document, source):
    field = SOURCE_FIELDS[source]
    seen = []
    for term in document["terms"]:
        if field in term and term[field] not in seen:
            seen.append(term[field])
    return seen


def make_steps(cache_dir, delay, **kwargs):
    return {"wiktionary_es": WiktionaryStep(cache_dir=cache_dir, delay=delay, **kwargs),
            "wikipedia_es": WikipediaArticleStep(cache_dir=cache_dir, delay=delay, **kwargs)}


def fetch(document, cache_dir, delay=1.0, wait=0, plan_only=False, refresh=(), sources=None, log=print, steps=None, enabled=None):
    """Descarga lo pendiente. Devuelve `(estado, resumen)`: `complete`, `incomplete` o `plan`."""
    steps = steps or make_steps(cache_dir, delay)
    enabled = enabled or {"wiktionary_es": True, "wikipedia_es": True}
    chosen = [s for s in (sources or SOURCE_FIELDS) if s in SOURCE_FIELDS]
    summary = {}
    for source in chosen:
        step = steps[source]
        if not enabled.get(source, True):
            log("%s: desactivada, omitida" % source)
            continue
        titles = titles_for(document, source)
        for title in refresh:
            if title in titles and step.is_cached(step.key_of(title)):
                if plan_only:
                    continue
                step.cache_path(step.key_of(title)).unlink()
        pending = [t for t in titles if not step.is_cached(step.key_of(t))]
        per_entry = 2 if source == "wiktionary_es" else 1
        summary[source] = {"titles": len(titles), "pending": len(pending), "requests": len(pending) * per_entry}
        log("%s: %d títulos, %d sin respuesta en la caché, hasta %d peticiones (pausa de %s s)"
            % (source, len(titles), len(pending), len(pending) * per_entry, delay))
        if plan_only:
            continue
        result = run_step(step, titles, wait, log)
        summary[source]["madeRequests"] = result["fetched_requests"]
        log("%s: %s, %d peticiones en esta ejecución" % (source, result["status"], result["fetched_requests"]))
        if result["status"] != "complete":
            log("%s: detenido; pendientes %d de %d. No reintentar antes de %s (%s). Vuelva a ejecutar el mismo comando."
                % (source, result["pending"], result["total"], result["retry_at"], result["reason"]))
            return "incomplete", summary
    return ("plan" if plan_only else "complete"), summary
