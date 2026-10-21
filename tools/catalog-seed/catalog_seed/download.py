"""Descarga con caché y verificación de checksum."""
import hashlib
import json
import os
import re
import urllib.request

from .sources import DEFAULT_CACHE_DIR, SourceError

CHUNK = 1024 * 1024
USER_AGENT = "BoticarioAI-catalog-seed/0.1 (academic project)"


def file_digest(path, algorithm):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(source_file, path):
    """Devuelve None si el archivo es íntegro o el motivo del fallo."""
    size = os.path.getsize(path)
    if size != source_file.size:
        return "tamaño %d distinto del declarado %d" % (size, source_file.size)
    actual = file_digest(path, source_file.algorithm)
    if actual != source_file.checksum:
        return "%s %s distinto del declarado %s" % (source_file.algorithm, actual, source_file.checksum)
    return None


def _pin_hint(source):
    return "python3 -I tools/catalog-seed/cli.py pin --source %s" % source.id


def _check_pinned(source):
    if not source.pinned:
        raise SourceError(
            "la fuente '%s' tiene el snapshot sin fijar (size y checksum null); fíjelo con: %s"
            % (source.id, _pin_hint(source))
        )


def require_verified_files(source, cache_dir=DEFAULT_CACHE_DIR):
    """Devuelve las rutas verificadas de todos los archivos de la fuente; nunca abre la red."""
    _check_pinned(source)
    step = "python3 -I tools/catalog-seed/cli.py download --source %s" % source.id
    paths = []
    for source_file in source.files:
        path = source_file.cache_path(cache_dir)
        if not path.is_file():
            raise SourceError("falta el insumo de la fuente '%s' (%s); ejecute el paso de descarga: %s" % (source.id, path, step))
        problem = check_file(source_file, path)
        if problem:
            raise SourceError(
                "el insumo de la fuente '%s' está alterado (%s: %s); vuelva a descargarlo con: %s --force"
                % (source.id, source_file.filename, problem, step)
            )
        paths.append(path)
    return paths


def require_verified(source, cache_dir=DEFAULT_CACHE_DIR):
    """Devuelve la ruta del primer (o único) insumo verificado; nunca abre la red."""
    return require_verified_files(source, cache_dir)[0]


def _fetch(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, open(destination, "wb") as out:
        for block in iter(lambda: response.read(CHUNK), b""):
            out.write(block)


def _download_to_cache(source_file, cache_dir, fetch, verify):
    """Descarga a un .part, aplica verify(path) y mueve a la caché solo si pasa."""
    path = source_file.cache_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    try:
        fetch(source_file.url, str(partial))
        verify(partial)
        os.replace(str(partial), str(path))
    finally:
        if partial.exists():
            partial.unlink()
    return path


def download_source(source, cache_dir=DEFAULT_CACHE_DIR, force=False, fetch=_fetch):
    """Devuelve (estado, ruta del primer archivo). Estados: disabled, cached, downloaded."""
    if not source.enabled:
        return "disabled", None
    _check_pinned(source)
    status = "cached"
    for source_file in source.files:
        path = source_file.cache_path(cache_dir)
        if path.is_file() and not force:
            problem = check_file(source_file, path)
            if problem:
                raise SourceError(
                    "el insumo de la fuente '%s' está alterado (%s: %s); vuelva a descargarlo con --force"
                    % (source.id, source_file.filename, problem)
                )
            continue

        def verify(partial, source_file=source_file):
            problem = check_file(source_file, str(partial))
            if problem:
                raise SourceError("la descarga de '%s' (%s) no coincide con lo declarado: %s" % (source.id, source_file.filename, problem))

        _download_to_cache(source_file, cache_dir, fetch, verify)
        status = "downloaded"
    return status, source.files[0].cache_path(cache_dir)


def _write_sources_file(path, document):
    text = json.dumps(document, indent=2, ensure_ascii=False)
    # Los objetos 'checksum' van en una línea, como en el resto del archivo.
    text = re.sub(
        r'\{\s*"algorithm": ("[^"]*"),\s*"value": ("[^"]*")\s*\}',
        r'{"algorithm": \1, "value": \2}', text)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


def pin_source(source, sources_path, cache_dir=DEFAULT_CACHE_DIR, fetch=_fetch, describe=None):
    """Descarga los archivos sin fijar, registra size y sha256 en sources.json y los deja en la caché.

    describe(source, paths) puede devolver el nuevo texto de 'version' (por ejemplo con el
    meta.timestamp de la EMA). Una fuente ya fijada no se toca: devuelve False.
    """
    if source.pinned:
        return False
    with open(sources_path, encoding="utf-8") as handle:
        document = json.load(handle)
    entry = next(e for e in document["sources"] if e["id"] == source.id)
    entries = entry["files"] if "files" in entry else [entry]
    paths = []
    for source_file, file_entry in zip(source.files, entries):
        if source_file.pinned:
            paths.append(source_file.cache_path(cache_dir))
            continue
        result = {}

        def verify(partial, result=result):
            result["size"] = os.path.getsize(str(partial))
            result["sha256"] = file_digest(str(partial), "sha256")

        paths.append(_download_to_cache(source_file, cache_dir, fetch, verify))
        file_entry["size"] = result["size"]
        file_entry["checksum"] = {"algorithm": "sha256", "value": result["sha256"]}
    if describe:
        entry["version"] = describe(source, paths)
    _write_sources_file(sources_path, document)
    return True
