import argparse
import sys

from .download import download_source, pin_source, require_verified_files
from .ema import describe_snapshot
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
    return parser


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
