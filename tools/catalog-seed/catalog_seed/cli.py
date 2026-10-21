import argparse
import json
import sys

from .download import download_source, pin_source, require_verified_files
from .ema import describe_snapshot
from .goals import DEFAULT_GOALS_CATALOG, DEFAULT_GOALS_MAP, DEFAULT_SEED_DIR, load_goals_catalog, load_goals_map
from .schema import DEFAULT_RECORD_SCHEMA, load_schema
from .seed import DEFAULT_BUNDLES_DIR, DEFAULT_PROMPT, compute_plan, read_prompt_version, schema_version, seal
from .validate import validate_directory
from .wiki import SERVICES, make_step, read_entries
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


def run_fetch(args):
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


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "fetch":
            return run_fetch(args)
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
                elif pin_source(source, args.sources, args.cache_dir,
                                describe=describe_snapshot if source.id == "ema_json" else None):
                    print("%s: snapshot fijado y registrado en %s" % (source.id, args.sources))
                else:
                    print("%s: ya estaba fijada; para cambiar el snapshot ponga size y checksum en null y ejecute pin de nuevo" % source.id)
            return 0
        for source in sources:
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
    except SourceError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    return 0
