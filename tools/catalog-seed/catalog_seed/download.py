"""Descarga con caché y verificación de checksum."""
import hashlib
import os
import urllib.request

from .sources import DEFAULT_CACHE_DIR, SourceError

CHUNK = 1024 * 1024
USER_AGENT = "boticario-catalog-seed/0.1 (offline tooling)"


def file_digest(path, algorithm):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(source, path):
    """Devuelve None si el archivo es íntegro o el motivo del fallo."""
    size = os.path.getsize(path)
    if size != source.size:
        return "tamaño %d distinto del declarado %d" % (size, source.size)
    actual = file_digest(path, source.algorithm)
    if actual != source.checksum:
        return "%s %s distinto del declarado %s" % (source.algorithm, actual, source.checksum)
    return None


def require_verified(source, cache_dir=DEFAULT_CACHE_DIR):
    """Devuelve la ruta del insumo verificado; nunca abre la red."""
    path = source.cache_path(cache_dir)
    step = "python3 -I tools/catalog-seed/cli.py download --source %s" % source.id
    if not path.is_file():
        raise SourceError("falta el insumo de la fuente '%s' (%s); ejecute el paso de descarga: %s" % (source.id, path, step))
    problem = check_file(source, path)
    if problem:
        raise SourceError(
            "el insumo de la fuente '%s' está alterado (%s); vuelva a descargarlo con: %s --force" % (source.id, problem, step)
        )
    return path


def _fetch(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, open(destination, "wb") as out:
        for block in iter(lambda: response.read(CHUNK), b""):
            out.write(block)


def download_source(source, cache_dir=DEFAULT_CACHE_DIR, force=False, fetch=_fetch):
    """Devuelve (estado, ruta). Estados: disabled, cached, downloaded."""
    if not source.enabled:
        return "disabled", None
    path = source.cache_path(cache_dir)
    if path.is_file() and not force:
        require_verified(source, cache_dir)
        return "cached", path
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    try:
        fetch(source.url, str(partial))
        problem = check_file(source, str(partial))
        if problem:
            raise SourceError("la descarga de '%s' no coincide con lo declarado: %s" % (source.id, problem))
        os.replace(str(partial), str(path))
    finally:
        if partial.exists():
            partial.unlink()
    return "downloaded", path
