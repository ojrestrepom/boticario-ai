"""Comandos `wiki-fetch` y `wiki-assign` (tarea 3.4): descarga dirigida de Wikidata, Wikipedia en español y Commons, y asignación.

`wiki-fetch` consulta Wikidata por nombre para todas las plantas del universo (más dos nombres de control), asigna los ítems
con el filtro de homónimos y descarga solo los resúmenes de Wikipedia y los metadatos de Commons de los ítems que pasan. Es
reanudable: cada respuesta queda en la caché y un límite de peticiones deja el estado de reanudación. `wiki-assign` rehace la
asignación y el informe desde la caché, sin red.
"""
import json
import math
import time
from pathlib import Path

from .sources import SourceError
from .taxonomy import open_backbone
from .wiki import DEFAULT_BATCH, CommonsStep, WikidataStep, WikipediaStep
from .workdb import DEFAULT_WORK_DIR
from .wiki_assign import (CONTROL_NAMES, build_assignment, build_name_plan, control_checks, homonym_examples,
                          pending_downloads, summarize)

DEFAULT_WIKI_DIR = DEFAULT_WORK_DIR / "wiki"
DEFAULT_UNIVERSE = DEFAULT_WORK_DIR / "universe" / "universe.json"
DEFAULT_TAXONOMY_DB = DEFAULT_WORK_DIR / "taxonomy.db"
SERVICES = ("wikidata", "wikipedia_es", "commons")
# Latencia supuesta por petición, para estimar el tiempo antes de lanzar la descarga.
ASSUMED_LATENCY = {"wikidata": 3.0, "wikipedia_es": 0.4, "commons": 1.5}
FETCH_BATCH = {"wikidata": 40, "wikipedia_es": 1, "commons": 50}


def enabled_services(sources):
    declared = {s.id: s.enabled for s in sources}
    return {name: bool(declared.get(name)) for name in SERVICES}


def load_inputs(universe_path, taxonomy_db):
    try:
        universe = json.loads(Path(universe_path).read_text(encoding="utf-8"))
    except OSError:
        raise SourceError("falta el universo %s; ejecute: python3 -I tools/catalog-seed/cli.py resolve" % universe_path)
    if not Path(taxonomy_db).is_file():
        raise SourceError("falta el índice taxonómico %s; ejecute: python3 -I tools/catalog-seed/cli.py resolve" % taxonomy_db)
    return universe, open_backbone(str(taxonomy_db), "wcvp"), open_backbone(str(taxonomy_db), "wfo")


def make_steps(cache_dir, delay, batches=None, **kwargs):
    batches = dict(FETCH_BATCH, **(batches or {}))
    return {"wikidata": WikidataStep(cache_dir=cache_dir, delay=delay, batch_size=batches["wikidata"], **kwargs),
            "wikipedia_es": WikipediaStep(cache_dir=cache_dir, delay=delay, **kwargs),
            "commons": CommonsStep(cache_dir=cache_dir, delay=delay, batch_size=batches["commons"], **kwargs)}


def requests_for(step, entries):
    """Peticiones que haría el paso: las entradas sin archivo en la caché, en lotes."""
    pending = [e for e in entries if not step.is_cached(step.key_of(e))]
    return len(pending), math.ceil(len(pending) / step.batch_size)


def estimate_seconds(service, requests, delay):
    return requests * (delay + ASSUMED_LATENCY[service])


def run_step(step, entries, wait, log, now=time.time, sleep=time.sleep):
    """Ejecuta un paso; si hay límite de peticiones espera hasta `wait` segundos en total (respetando Retry-After) y sigue."""
    waited = 0
    while True:
        result = step.run(entries)
        if result["status"] == "complete":
            return result
        state = step.read_resume() or {}
        pause = max(0, int(state.get("retry_not_before_epoch", 0) - now())) + 1
        if waited + pause > wait:
            return result
        log("%s: límite de peticiones (%s); espera %d s" % (step.service, result["reason"], pause))
        sleep(pause)
        waited += pause


def fetch(universe_path, taxonomy_db, cache_dir, enabled, delay, wait, plan_only=False, log=print, steps=None,
          now=time.time, sleep=time.sleep):
    """Descarga lo pendiente. Devuelve (estado, resumen): estado `complete`, `incomplete` o `plan`."""
    if not enabled["wikidata"]:
        log("wikidata: desactivada; no se descarga ni se consulta nada (Wikipedia y Commons dependen de Wikidata)")
        return "disabled", {}
    universe, wcvp, wfo = load_inputs(universe_path, taxonomy_db)
    steps = steps or make_steps(cache_dir, delay)
    plan = build_name_plan(universe, wcvp, CONTROL_NAMES)
    names = plan["names"]
    count, requests = requests_for(steps["wikidata"], names)
    summary = {"names": len(names), "wikidataPending": count, "wikidataRequests": requests,
               "wikidataSeconds": estimate_seconds("wikidata", requests, delay)}
    log("wikidata: %d nombres, %d sin respuesta en la caché, %d peticiones (lotes de %d), unos %d min"
        % (len(names), count, requests, steps["wikidata"].batch_size, summary["wikidataSeconds"] / 60))
    if plan_only:
        if count == 0:
            pending_wp, pending_cm, _ = pending_downloads(universe, wcvp, wfo, plan, steps, enabled)
            for service, pending in (("wikipedia_es", pending_wp), ("commons", pending_cm)):
                if enabled[service]:
                    n, r = requests_for(steps[service], pending)
                    log("%s: %d pendientes, %d peticiones, unos %d min" % (
                        service, n, r, estimate_seconds(service, r, delay) / 60))
        return "plan", summary
    complete = True
    result = run_step(steps["wikidata"], names, wait, log, now, sleep)
    log("wikidata: %s (%d peticiones en esta ejecución)" % (result["status"], result["fetched_requests"]))
    if result["status"] != "complete":
        log("wikidata: detenido; pendientes %d de %d. No reintentar antes de %s (%s). Vuelva a ejecutar el mismo comando."
            % (result["pending"], result["total"], result["retry_at"], result["reason"]))
        return "incomplete", summary
    pending_wp, pending_cm, _ = pending_downloads(universe, wcvp, wfo, plan, steps, enabled)
    for service, pending in (("wikipedia_es", pending_wp), ("commons", pending_cm)):
        if not enabled[service]:
            log("%s: desactivada, omitida" % service)
            continue
        result = run_step(steps[service], pending, wait, log, now, sleep)
        log("%s: %s, %d entradas, %d peticiones en esta ejecución" % (
            service, result["status"], result["total"], result["fetched_requests"]))
        if result["status"] != "complete":
            complete = False
            log("%s: detenido; pendientes %d. No reintentar antes de %s (%s)." % (
                service, result["pending"], result["retry_at"], result["reason"]))
    summary["requests"] = {name: step.requests_made for name, step in steps.items()}
    return ("complete" if complete else "incomplete"), summary


# --- Asignación e informe -------------------------------------------------------------------------------------------

def assign(universe_path, taxonomy_db, cache_dir, enabled, out_dir, steps=None, log=print):
    """Rehace la asignación y el informe desde la caché (sin red) y los escribe en `out_dir`."""
    universe, wcvp, wfo = load_inputs(universe_path, taxonomy_db)
    steps = steps or make_steps(cache_dir, 0)
    plan = build_name_plan(universe, wcvp, CONTROL_NAMES)
    document = build_assignment(universe, wcvp, wfo, plan, steps, enabled)
    summary = summarize(document)
    homonyms = homonym_examples(document)
    checks = control_checks(document)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "assignment.json").write_text(json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    report = {"summary": summary, "homonyms": homonyms, "controls": checks,
              "ipniDiscrepancies": _ipni_examples(document)}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    log("asignación escrita en %s" % out)
    return document, report


def _ipni_examples(document, limit=12):
    found = [{"qid": q, "taxon": i["taxon"], "plantId": i["plantId"]}
             for q, i in document["items"].items() if i["plantId"] and i["ipni"] == "discrepa"]
    return {"total": len(found), "examples": found[:limit]}


def render_markdown(report):
    s = report["summary"]
    lines = ["# Informe de asignación de Wikidata, Wikipedia en español y Commons", "",
             "Generado desde la caché de respuestas y `universe.json`, sin red.", "", "## Cifras", "",
             "| Cifra | Valor |", "| --- | --- |",
             "| Plantas del universo | %d |" % s["plants"]]
    for status, n in s["plantsByWikidataStatus"].items():
        lines.append("| Plantas con estado de Wikidata `%s` | %d |" % (status, n))
    lines += ["| Ítems de Wikidata en la caché | %d |" % s["items"],
              "| Ítems asignados a una planta | %d |" % s["itemsAssigned"],
              "| Plantas con ítem de Wikidata | %d |" % s["plantsWithWikidataItem"],
              "| Plantas con nombre común en español (P1843) | %d |" % s["plantsWithSpanishName"],
              "| Plantas con P1843 o alias en español | %d |" % s["plantsWithSpanishNameOrAlias"],
              "| Plantas con resumen de Wikipedia | %d |" % s["plantsWithWikipedia"],
              "| Plantas con imagen admitida | %d |" % s["plantsWithAdmittedImage"],
              "| Plantas con alguna imagen descartada | %d |" % s["plantsWithDiscardedImage"],
              "| Plantas cuyas imágenes se descartaron todas | %d |" % s["plantsWithOnlyDiscardedImages"],
              "| Resúmenes de Wikipedia pendientes | %d |" % s["pendingWikipedia"],
              "| Imágenes de Commons pendientes | %d |" % s["pendingCommons"], ""]
    lines += ["## Ítems sin asignar, por motivo", "", "| Motivo | Ítems |", "| --- | --- |"]
    lines += ["| `%s` | %d |" % item for item in s["itemsUnassignedByReason"].items()]
    lines += ["", "## Imágenes descartadas, por motivo", "", "| Motivo | Imágenes |", "| --- | --- |"]
    lines += ["| `%s` | %d |" % item for item in s["imagesDiscardedByReason"].items()]
    lines += ["", "## Filtro de homónimos", "",
              "Un ítem se pidió por el nombre de una planta y su P225 no resuelve al aceptado de esa planta. Descartados (no entran en "
              "ninguna planta): %d. Reasignados a otra planta del universo: %d." % (
                  report["homonyms"]["discardedTotal"], report["homonyms"]["movedTotal"]), ""]
    for key, title in (("discarded", "Descartados"), ("moved", "Reasignados")):
        if report["homonyms"][key]:
            lines += ["### %s (primeros ejemplos)" % title, "",
                      "| QID | Nombre | Pedido para | Asignado a | Motivo | Resuelve a |", "| --- | --- | --- | --- | --- | --- |"]
            for e in report["homonyms"][key]:
                lines.append("| %s | %s | %s | %s | `%s` | %s |" % (
                    e["qid"], e["taxon"], ", ".join(e["requestedFor"]), e["plantId"] or "ninguna", e["reason"], e["resolvedTo"] or ""))
            lines.append("")
    lines += ["## Controles del piloto", "", "| Planta | Homónimo | Resultado | Ítems de la planta | Ítems del homónimo |",
              "| --- | --- | --- | --- | --- |"]
    for plant_id, c in report["controls"].items():
        lines.append("| %s | %s | %s | %s | %s |" % (
            plant_id, c["homonym"], "correcto" if c["ok"] else "FALLA",
            ", ".join("%s (%s)" % (q, t) for q, t in c["plantItems"].items()) or "ninguno",
            ", ".join("%s (%s, %s)" % (q, i["plantId"] or "sin asignar", i["reason"]) for q, i in c["homonymItems"].items())
            or "no hay ítem"))
    lines += ["", "## Evidencia de IPNI y POWO", "",
              "Se contrasta P961 y P5037 con los `ipni_id` de WCVP del aceptado y sus sinónimos; no reemplaza el filtro por nombre.", "",
              "| Resultado | Ítems asignados |", "| --- | --- |"]
    lines += ["| `%s` | %d |" % item for item in s["ipniEvidence"].items()]
    if report["ipniDiscrepancies"]["examples"]:
        lines += ["", "Ejemplos de discrepancia (%d en total):" % report["ipniDiscrepancies"]["total"], ""]
        lines += ["- %s: %s, asignado a %s" % (e["qid"], e["taxon"], e["plantId"]) for e in report["ipniDiscrepancies"]["examples"]]
    return "\n".join(lines) + "\n"
