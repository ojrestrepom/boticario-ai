import argparse
import sys

from .download import download_source, require_verified
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        sources = load_sources(args.sources)
        if args.source:
            known = {s.id for s in sources}
            for name in args.source:
                if name not in known:
                    raise SourceError("la fuente '%s' no está declarada en %s" % (name, args.sources))
            sources = [s for s in sources if s.id in args.source]
        for source in sources:
            if args.offline:
                if not source.enabled:
                    print("%s: desactivada, omitida" % source.id)
                    continue
                path = require_verified(source, args.cache_dir)
                print("%s: íntegra (%s)" % (source.id, path))
                continue
            status, path = download_source(source, args.cache_dir, force=args.force)
            print("%s: %s%s" % (source.id, {"disabled": "desactivada, omitida", "cached": "en caché, verificada",
                                              "downloaded": "descargada y verificada"}[status],
                                  " (%s)" % path if path else ""))
    except SourceError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    return 0
