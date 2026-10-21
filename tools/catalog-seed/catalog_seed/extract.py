"""Comando extract: lee los insumos verificados de una fuente y escribe sus filas normalizadas en data/work/sources.db."""
from pathlib import Path

from . import ema, ema_extract, efsa_extract, tppt_extract, usda_extract, workdb
from .download import require_verified, require_verified_files
from .ema_pdf import slug_of
from .sources import DEFAULT_CACHE_DIR, SourceError

EXTRACTABLE = ("usda", "ema_json", "ema_pdf", "tppt", "efsa")


def _ema_records(sources, cache_dir):
    source = next((s for s in sources if s.id == "ema_json"), None)
    if source is None or not source.enabled:
        raise SourceError("la extracción de la EMA necesita la fuente ema_json activa")
    document = ema.load_json(require_verified(source, cache_dir))
    return ema.dedupe_records(document)


def _extract_pdf(source, sources, cache_dir):
    from .pdf_sections import extract_pdf
    records = _ema_records(sources, cache_dir)
    paths = require_verified_files(source, cache_dir)
    if not paths:
        raise SourceError("la fuente ema_pdf no tiene PDF registrados; ejecute: python3 -I tools/catalog-seed/cli.py ema-pdf")
    files = [(path, f.filename, f.url) for path, f in zip(paths, source.files)]
    pages = {p.stem for p in (Path(cache_dir) / "ema_pdf" / "pages").glob("*.html")}
    return ema_extract.pdf_rows(records, files, extract_pdf, pages_cached=pages)


def extract_source(source, sources, cache_dir=DEFAULT_CACHE_DIR):
    """Devuelve (filas, estadísticas) de una fuente."""
    if source.id == "usda":
        return usda_extract.extract(require_verified(source, cache_dir))
    if source.id == "tppt":
        return tppt_extract.extract(require_verified(source, cache_dir))
    if source.id == "efsa":
        paths = {f.filename: p for f, p in zip(source.files, require_verified_files(source, cache_dir))}
        return efsa_extract.extract(paths["BOTANIC.xls"], paths["ENDPOINTSTUDY.xls"])
    if source.id == "ema_json":
        rows = ema_extract.herbal_rows(_ema_records(sources, cache_dir))
        return rows, {"ema_herbal": len(rows)}
    if source.id == "ema_pdf":
        return _extract_pdf(source, sources, cache_dir)
    raise SourceError("la fuente '%s' no tiene extracción (%s)" % (source.id, ", ".join(EXTRACTABLE)))


def run_extract(source, sources, cache_dir, db_path):
    rows, stats = extract_source(source, sources, cache_dir)
    inputs = [{"filename": f.filename, "size": f.size, "checksum": f.checksum} for f in source.files]
    connection = workdb.open_db(db_path)
    try:
        workdb.replace_source(connection, source.id, rows, source.version, inputs)
    finally:
        connection.close()
    return stats
