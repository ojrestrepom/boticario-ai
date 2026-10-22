import argparse
import json
import sys
import time

from .download import download_source, pin_source, require_verified, require_verified_files
from .ema import dedupe_records, describe_snapshot, load_json, snapshot_timestamp
from .extract import EXTRACTABLE, run_extract, skip_reason
from . import workdb
from .safety import DEFAULT_SAFETY_MAP, SafetyMapError, load_safety_map
from .safety_report import format_report
from .workdb import DEFAULT_DB
from .ema_pdf import DEFAULT_DELAY, EmaPdfStep, pin_ema_pdfs
from .goals import DEFAULT_GOALS_CATALOG, DEFAULT_GOALS_MAP, DEFAULT_SEED_DIR, load_goals_catalog, load_goals_map
from .schema import DEFAULT_RECORD_SCHEMA, load_schema
from .seed import DEFAULT_BUNDLES_DIR, DEFAULT_PROMPT, compute_plan, read_prompt_version, schema_version, seal
from .collisions_decide import DEFAULT_DELAY as COLLISIONS_DELAY, run_collisions_decide
from .resolve_universe import (DEFAULT_CATALOG_DB, DEFAULT_DECISIONS, DEFAULT_EXCEPTIONS, DEFAULT_TAXONOMY_DB, DEFAULT_UNIVERSE_DIR,
                               run_resolve)
from .taxonomy import CollisionFileError, UniverseError
from .validate import validate_directory
from .wiki import SERVICES, make_step, read_entries
from . import wiki_fetch
from .sources import DEFAULT_CACHE_DIR, DEFAULT_SOURCES_FILE, SourceError, load_sources


def build_parser():
    parser = argparse.ArgumentParser(prog="catalog_seed", description="Herramientas offline del catálogo.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_FILE), help="ruta de sources.json")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="directorio de caché")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="descarga las fuentes activas a la caché y verifica su checksum")
    download.add_argument("--source", action="append", help="limita a una fuente (repetible)")
    download.add_argument("--force", action="store_true", help="vuelve a descargar aunque exista en caché")
    download.add_argument("--offline", action="store_true", help="solo verifica la caché; nunca usa la red")
    pin = commands.add_parser("pin", help="fija el snapshot de una fuente cambiante: descarga y registra size y sha256 en sources.json")
    pin.add_argument("--source", action="append", required=True, help="fuente a fijar (repetible)")
    fetch = commands.add_parser("fetch", help="consulta Wikidata, Wikipedia en español o Commons con límite de peticiones y reanudación")
    fetch.add_argument("--service", required=True, choices=SERVICES)
    fetch.add_argument("--input", required=True, help="archivo con una entrada por línea (nombres o QIDs, títulos o archivos)")
    fetch.add_argument("--batch-size", type=int, help="entradas por petición (por defecto según el servicio)")
    fetch.add_argument("--delay", type=float, default=1.0, help="segundos entre peticiones (por defecto 1)")
    fetch.add_argument("--endpoint", help="URL del servicio (solo para pruebas)")
    emapdf = commands.add_parser("ema-pdf", help="descarga las páginas y los PDF de la EMA con espera y reanudación, y registra los checksums en sources.json")
    emapdf.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="segundos entre peticiones (por defecto 15)")
    emapdf.add_argument("--limit", type=int, help="máximo de peticiones en esta ejecución (para pruebas manuales)")
    emapdf.add_argument("--wait", type=int, default=0, help="si hay límite de peticiones, espera hasta este número de segundos por ejecución y sigue (por defecto 0: se detiene)")
    emapdf.add_argument("--status", action="store_true", help="solo imprime cuántos PDF hay descargados y pendientes; no abre la red")
    wiki = commands.add_parser("wiki-fetch", help="descarga Wikidata (por nombre), los resúmenes de Wikipedia y los metadatos de Commons del universo, con límite de peticiones y reanudación")
    wiki.add_argument("--universe", default=str(wiki_fetch.DEFAULT_UNIVERSE), help="universe.json (por defecto data/work/universe/universe.json)")
    wiki.add_argument("--taxonomy-db", default=str(wiki_fetch.DEFAULT_TAXONOMY_DB), help="índice de WCVP y WFO")
    wiki.add_argument("--out-dir", default=str(wiki_fetch.DEFAULT_WIKI_DIR), help="salida de la asignación y el informe (por defecto data/work/wiki)")
    wiki.add_argument("--delay", type=float, default=1.0, help="segundos entre peticiones (por defecto 1)")
    wiki.add_argument("--wait", type=int, default=0, help="si hay límite de peticiones, espera hasta este número de segundos en total y sigue (por defecto 0: se detiene)")
    wiki.add_argument("--plan", action="store_true", help="solo cuenta nombres y peticiones y estima el tiempo; no abre la red")
    assign = commands.add_parser("wiki-assign", help="rehace la asignación de ítems a plantas y el informe desde la caché, sin red")
    assign.add_argument("--universe", default=str(wiki_fetch.DEFAULT_UNIVERSE), help="universe.json")
    assign.add_argument("--taxonomy-db", default=str(wiki_fetch.DEFAULT_TAXONOMY_DB), help="índice de WCVP y WFO")
    assign.add_argument("--out-dir", default=str(wiki_fetch.DEFAULT_WIKI_DIR), help="salida (assignment.json, report.json, report.md)")
    extract = commands.add_parser("extract", help="extrae las filas normalizadas de una fuente a data/work/sources.db")
    extract.add_argument("--source", action="append", choices=EXTRACTABLE, help="fuente a extraer (repetible; por defecto todas las activas)")
    extract.add_argument("--db", default=str(DEFAULT_DB), help="SQLite de salida (por defecto data/work/sources.db)")
    report = commands.add_parser("safety-report", help="clasifica con el mapa de seguridad las filas extraídas y muestra la cobertura")
    report.add_argument("--db", default=str(DEFAULT_DB), help="SQLite de las extracciones")
    report.add_argument("--map", default=str(DEFAULT_SAFETY_MAP), help="mapa de seguridad")
    resolve = commands.add_parser("resolve", help="resuelve los nombres de USDA y de la EMA y escribe el universo de plantas en data/work/universe/")
    resolve.add_argument("--db", default=str(DEFAULT_DB), help="SQLite de las extracciones")
    resolve.add_argument("--taxonomy-db", default=str(DEFAULT_TAXONOMY_DB), help="índice de WCVP y WFO (se recrea si falta o cambian los checksums)")
    resolve.add_argument("--out-dir", default=str(DEFAULT_UNIVERSE_DIR), help="directorio de salida (universe.json, report.json, report.md)")
    resolve.add_argument("--catalog-db", default=str(DEFAULT_CATALOG_DB), help="catalog.db con los IDs actuales, solo para comparar (opcional)")
    resolve.add_argument("--rebuild-index", action="store_true", help="recrea el índice aunque esté vigente")
    resolve.add_argument("--decisions", default=str(DEFAULT_DECISIONS), help="decisiones de colisión registradas (por defecto collision-decisions.json); resolve no abre la red")
    resolve.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS), help="excepciones «separar siempre» (por defecto collision-exceptions.json)")
    decide = commands.add_parser("collisions-decide", help="consulta es.wikipedia.org solo para los grupos de colisión sin decisión, aplica el criterio de Wikipedia y agrega las decisiones al archivo (no sobrescribe las registradas)")
    decide.add_argument("--db", default=str(DEFAULT_DB), help="SQLite de las extracciones")
    decide.add_argument("--taxonomy-db", default=str(DEFAULT_TAXONOMY_DB), help="índice de WCVP y WFO (lo crea resolve)")
    decide.add_argument("--decisions", default=str(DEFAULT_DECISIONS), help="archivo de decisiones")
    decide.add_argument("--exceptions", default=str(DEFAULT_EXCEPTIONS), help="archivo de excepciones")
    decide.add_argument("--delay", type=float, default=COLLISIONS_DELAY, help="segundos entre peticiones (por defecto 1)")
    validate = commands.add_parser("validate", help="valida los registros de la semilla contra sus paquetes")
    validate.add_argument("--records", default=str(DEFAULT_SEED_DIR / "plants"), help="directorio de registros (por defecto data/seed/plants)")
    validate.add_argument("--bundles", default=str(DEFAULT_BUNDLES_DIR), help="directorio de paquetes (por defecto data/work/bundles)")
    validate.add_argument("--schema", default=str(DEFAULT_RECORD_SCHEMA), help="esquema del registro")
    validate.add_argument("--goals-map", default=str(DEFAULT_GOALS_MAP), help="mapa de objetivos")
    validate.add_argument("--goals", default=str(DEFAULT_GOALS_CATALOG), help="catálogo de objetivos")
    validate.add_argument("--out", help="escribe el informe completo en este archivo JSON")
    plan = commands.add_parser("plan", help="lista las plantas a regenerar (sin registro, otro bundleHash, otro prompt u otro esquema)")
    plan.add_argument("--bundles", default=str(DEFAULT_BUNDLES_DIR), help="directorio de paquetes")
    plan.add_argument("--seed", default=str(DEFAULT_SEED_DIR), help="directorio de la semilla (con plants/)")
    plan.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="prompt de consolidación")
    plan.add_argument("--schema", default=str(DEFAULT_RECORD_SCHEMA), help="esquema del registro")
    plan.add_argument("--json", action="store_true", help="imprime el plan como JSON")
    sealer = commands.add_parser("seal", help="escribe o actualiza manifest.json con las fuentes, versiones, conteos y seedHash")
    sealer.add_argument("--seed", default=str(DEFAULT_SEED_DIR), help="directorio de la semilla (con plants/ y goals.json)")
    sealer.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="prompt de consolidación")
    sealer.add_argument("--schema", default=str(DEFAULT_RECORD_SCHEMA), help="esquema del registro")
    return parser


def run_validate(args):
    report = validate_directory(args.records, args.bundles, schema=load_schema(args.schema),
                                goals_map=load_goals_map(args.goals_map), catalog=load_goals_catalog(args.goals))
    for message in report["global"]:
        print("error: %s" % message)
    for plant, result in report["plants"].items():
        for message in result["errors"]:
            print("error: %s: %s" % (plant, message))
        for message in result["warnings"]:
            print("advertencia: %s: %s" % (plant, message))
    summary = report["summary"]
    print("%d registros, %d con errores, %d errores, %d advertencias"
          % (summary["records"], summary["recordsWithErrors"], summary["errors"], summary["warnings"]))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    return 1 if summary["errors"] else 0


def run_resolve_command(args):
    sources = load_sources(args.sources)
    try:
        _, report = run_resolve(sources, args.cache_dir, args.db, args.taxonomy_db, args.out_dir,
                                catalog_db=args.catalog_db, force_index=args.rebuild_index,
                                decisions_path=args.decisions, exceptions_path=args.exceptions)
    except UniverseError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    failed = report["checks"]["duplicate_ids"] or not report["checks"]["lavandula-angustifolia"]
    return 1 if failed else 0


def run_collisions_decide_command(args):
    result = run_collisions_decide(load_sources(args.sources), args.cache_dir, args.db, args.taxonomy_db, args.decisions,
                                   args.exceptions, delay=args.delay)
    return 2 if result["status"] in ("rate_limited", "waiting") else 0


def run_plan(args):
    schema = load_schema(args.schema)
    plan = compute_plan(args.bundles, args.seed, read_prompt_version(args.prompt), schema_version(schema))
    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        for item in plan:
            print("%s\t%s" % (item["id"], ",".join(item["reasons"])))
        print("%d plantas a regenerar" % len(plan))
    return 0


def run_seal(args):
    manifest, changed = seal(args.seed, args.sources, schema_path=args.schema, prompt_path=args.prompt)
    print("manifest.json %s: %d plantas, seedHash %s" % ("actualizado" if changed else "sin cambios", manifest["plantCount"], manifest["seedHash"]))
    return 0


def _ema_records(args):
    source = next((s for s in load_sources(args.sources) if s.id == "ema_json"), None)
    if source is None:
        raise SourceError("la fuente 'ema_json' no está declarada en %s" % args.sources)
    return dedupe_records(load_json(require_verified(source, args.cache_dir)))


def run_ema_pdf(args):
    records = _ema_records(args)
    step = EmaPdfStep(args.cache_dir, delay=args.delay)
    if args.status:
        print(json.dumps(dict(step.inventory(records), state=step.read_state()), indent=2, ensure_ascii=False))
        return 0
    waited = 0
    while True:
        result = step.run(records, limit=args.limit)
        if result["status"] != "rate_limited" and result["status"] != "waiting":
            break
        wait = max(0, int(step.read_state().get("retry_not_before_epoch", 0) - time.time())) + 1
        if waited + wait > args.wait:
            break
        print("límite de peticiones (%s); espera %d s" % (result["reason"], wait), flush=True)
        time.sleep(wait)
        waited += wait
    added, total = pin_ema_pdfs(args.sources, records, args.cache_dir, version=_pdf_version(records, args))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("sources.json: %d PDF nuevos registrados, %d en total" % (added, total))
    return 2 if result["status"] in ("rate_limited", "waiting") else 0


def _pdf_version(records, args):
    ema = next(s for s in load_sources(args.sources) if s.id == "ema_json")
    stamp = snapshot_timestamp(load_json(require_verified(ema, args.cache_dir)))
    return ("PDF de las páginas de las fichas del snapshot de ema_json (meta.timestamp %s); "
            "monografía final de la UE o borrador y declaración pública final, registrados por el comando ema-pdf" % stamp)


def run_safety_report(args):
    connection = workdb.open_db(args.db)
    try:
        print(format_report(connection, load_safety_map(args.map)))
    finally:
        connection.close()
    return 0


def run_extract_command(args):
    sources = load_sources(args.sources)
    wanted = args.source or list(EXTRACTABLE)
    for source in sources:
        if source.id not in wanted:
            continue
        reason = skip_reason(source, sources)
        if reason:
            print("%s: %s" % (source.id, reason))
            continue
        stats = run_extract(source, sources, args.cache_dir, args.db)
        print("%s: %s" % (source.id, ", ".join("%s=%s" % item for item in sorted(stats.items()))))
    return 0


def run_fetch(args):
    declared = next((s for s in load_sources(args.sources) if s.id == args.service), None)
    if declared is not None and not declared.enabled:
        print("%s: desactivada, omitida" % args.service)
        return 0
    try:
        entries = read_entries(args.input)
    except OSError as error:
        raise SourceError("no se puede leer la entrada %s: %s" % (args.input, error))
    step = make_step(args.service, cache_dir=args.cache_dir, endpoint=args.endpoint,
                     batch_size=args.batch_size, delay=args.delay)
    result = step.run(entries)
    if result["status"] == "complete":
        print("%s: completo, %d entradas en la caché (%d peticiones)" % (args.service, result["total"], result["fetched_requests"]))
        return 0
    print("%s: detenido por límite de peticiones (%s); pendientes %d de %d. No reintentar antes de %s; "
          "estado en %s. Vuelva a ejecutar el mismo comando después."
          % (args.service, result["reason"], result["pending"], result["total"], result["retry_at"], step.resume_path()))
    return 2


def run_wiki_fetch(args):
    enabled = wiki_fetch.enabled_services(load_sources(args.sources))
    status, _ = wiki_fetch.fetch(args.universe, args.taxonomy_db, args.cache_dir, enabled, args.delay, args.wait, plan_only=args.plan)
    if status in ("disabled", "plan"):
        return 0
    wiki_fetch.assign(args.universe, args.taxonomy_db, args.cache_dir, enabled, args.out_dir)
    return 0 if status == "complete" else 2


def run_wiki_assign(args):
    enabled = wiki_fetch.enabled_services(load_sources(args.sources))
    if not enabled["wikidata"]:
        print("wikidata: desactivada; no hay asignación que calcular")
        return 0
    wiki_fetch.assign(args.universe, args.taxonomy_db, args.cache_dir, enabled, args.out_dir)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "fetch":
            return run_fetch(args)
        if args.command == "ema-pdf":
            return run_ema_pdf(args)
        if args.command == "safety-report":
            return run_safety_report(args)
        if args.command == "extract":
            return run_extract_command(args)
        if args.command == "wiki-fetch":
            return run_wiki_fetch(args)
        if args.command == "wiki-assign":
            return run_wiki_assign(args)
        if args.command == "resolve":
            return run_resolve_command(args)
        if args.command == "collisions-decide":
            return run_collisions_decide_command(args)
        if args.command == "validate":
            return run_validate(args)
        if args.command == "plan":
            return run_plan(args)
        if args.command == "seal":
            return run_seal(args)
        sources = load_sources(args.sources)
        if args.source:
            known = {s.id for s in sources}
            for name in args.source:
                if name not in known:
                    raise SourceError("la fuente '%s' no está declarada en %s" % (name, args.sources))
            sources = [s for s in sources if s.id in args.source]
        if args.command == "pin":
            for source in sources:
                if not source.enabled:
                    print("%s: desactivada, omitida" % source.id)
                elif source.is_service:
                    print("%s: servicio en línea, no hay snapshot que fijar" % source.id)
                elif pin_source(source, args.sources, args.cache_dir,
                                describe=describe_snapshot if source.id == "ema_json" else None):
                    print("%s: snapshot fijado y registrado en %s" % (source.id, args.sources))
                else:
                    print("%s: ya estaba fijada; para cambiar el snapshot ponga size y checksum en null y ejecute pin de nuevo" % source.id)
            return 0
        for source in sources:
            if source.is_service:
                print("%s: %s" % (source.id, "desactivada, omitida" if not source.enabled else
                                  "servicio en línea; se consulta con el comando wiki-fetch (con espera entre peticiones y reanudación)"))
                continue
            if source.id == "ema_pdf" and not args.offline:
                print("ema_pdf: se descarga con el comando ema-pdf (espera entre peticiones y reanudación)")
                continue
            if args.offline:
                if not source.enabled:
                    print("%s: desactivada, omitida" % source.id)
                    continue
                paths = require_verified_files(source, args.cache_dir)
                print("%s: íntegra (%s)" % (source.id, ", ".join(str(p) for p in paths)))
                continue
            status, path = download_source(source, args.cache_dir, force=args.force)
            print("%s: %s%s" % (source.id, {"disabled": "desactivada, omitida", "cached": "en caché, verificada",
                                              "downloaded": "descargada y verificada"}[status],
                                  " (%s)" % path if path else ""))
    except (SourceError, SafetyMapError, CollisionFileError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    return 0
