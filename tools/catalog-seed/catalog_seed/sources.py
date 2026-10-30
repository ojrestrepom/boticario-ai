"""Configuración y verificador de fuentes (sources.json)."""
import json
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOL_DIR.parent.parent
DEFAULT_SOURCES_FILE = TOOL_DIR / "sources.json"
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / ".cache"

ADMITTED_SOURCES = (
    "usda", "wcvp", "wfo", "ema_json", "ema_pdf", "tppt", "efsa",
    "wikidata", "wikipedia_es", "wiktionary_es", "commons",
)
DISCARDED_SOURCES = (
    "aromadb", "essoildb", "scentindb", "fda_ppdb", "comision_e",
    "oms", "who", "nhpid", "inaturalist", "drugbank",
)
CHECKSUM_ALGORITHMS = ("md5", "sha256")
# `name` y `pageUrl` (página del dataset, distinta de `url`, que es lo que se descarga) son los datos legibles que la semilla entrega para los créditos.
BASE_FIELDS = ("id", "name", "pageUrl", "version", "license", "attribution", "enabled")
FILE_FIELDS = ("url", "filename", "size", "checksum")
# Fuentes cuya lista de archivos se genera al descargar (la EMA: los PDF salen de las páginas de cada ficha): 'files' puede estar vacía.
GENERATED_FILE_LISTS = ("ema_pdf",)
# Servicios en línea: no hay archivo ni checksum, porque la respuesta depende de la consulta. Se declaran con `url` (el servicio)
# y sin `filename`, `size`, `checksum` ni `files`; cada respuesta se guarda en data/.cache/<id>/ con la fecha de la consulta.
SERVICE_SOURCES = ("wikidata", "wikipedia_es", "wiktionary_es", "commons")


class SourceError(Exception):
    """Error de configuración o de verificación de una fuente."""


class SourceFile:
    """Un archivo de una fuente. size y checksum son None mientras el snapshot no está fijado."""

    def __init__(self, source_id, data):
        self.source_id = source_id
        self.data = data
        self.url = data["url"]
        self.filename = data["filename"]
        self.size = data["size"]
        checksum = data["checksum"]
        self.algorithm = checksum["algorithm"] if checksum else None
        self.checksum = checksum["value"].lower() if checksum else None

    @property
    def pinned(self):
        return self.size is not None and self.checksum is not None

    def cache_path(self, cache_dir=DEFAULT_CACHE_DIR):
        return Path(cache_dir) / self.source_id / self.filename


class Source:
    """Una fuente: un archivo (campos url/filename/size/checksum) o varios (lista 'files')."""

    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.name = data["name"]
        self.page_url = data["pageUrl"]
        self.version = data["version"]
        self.license = data["license"]
        # URL de la licencia (opcional): texto https o null; el manifiesto la copia y la base la guarda en `source.license_url`.
        self.has_license_url = "licenseUrl" in data
        self.license_url = data.get("licenseUrl")
        self.attribution = data["attribution"]
        self.enabled = data["enabled"]
        self.is_service = self.id in SERVICE_SOURCES
        if self.is_service:
            entries = []
        else:
            entries = data["files"] if "files" in data else [data]
        self.files = [SourceFile(self.id, entry) for entry in entries]

    @property
    def pinned(self):
        return all(f.pinned for f in self.files)

    # Compatibilidad con las fuentes de un solo archivo.
    @property
    def url(self):
        return self.data["url"] if self.is_service else self.files[0].url

    @property
    def filename(self):
        return None if self.is_service else self.files[0].filename

    @property
    def size(self):
        return None if self.is_service else self.files[0].size

    @property
    def algorithm(self):
        return None if self.is_service else self.files[0].algorithm

    @property
    def checksum(self):
        return None if self.is_service else self.files[0].checksum

    def cache_path(self, cache_dir=DEFAULT_CACHE_DIR):
        """Archivo de la caché; para un servicio, su carpeta."""
        return Path(cache_dir) / self.id if self.is_service else self.files[0].cache_path(cache_dir)


def check_source_id(source_id):
    """Falla si la fuente está descartada o no figura en la lista admitida."""
    key = str(source_id).strip().lower()
    if key in DISCARDED_SOURCES:
        raise SourceError("la fuente '%s' está descartada y no puede declararse" % source_id)
    if key not in ADMITTED_SOURCES:
        raise SourceError(
            "la fuente '%s' no está en la lista de fuentes admitidas (%s)"
            % (source_id, ", ".join(ADMITTED_SOURCES))
        )


def _validate_file(source_id, entry):
    for field in FILE_FIELDS:
        if field not in entry:
            raise SourceError("fuente '%s': falta el campo '%s'" % (source_id, field))
    for field in ("url", "filename"):
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise SourceError("fuente '%s': '%s' debe ser texto no vacío" % (source_id, field))
    name = entry["filename"]
    if "/" in name or "\\" in name or name in (".", ".."):
        raise SourceError("fuente '%s': 'filename' no puede contener rutas" % source_id)
    size, checksum = entry["size"], entry["checksum"]
    if (size is None) != (checksum is None):
        raise SourceError("fuente '%s': 'size' y 'checksum' deben ser ambos null (snapshot sin fijar) o ambos valores" % source_id)
    if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size < 0):
        raise SourceError("fuente '%s': 'size' debe ser un entero no negativo" % source_id)
    if checksum is not None and (
            not isinstance(checksum, dict) or checksum.get("algorithm") not in CHECKSUM_ALGORITHMS
            or not isinstance(checksum.get("value"), str) or not checksum["value"].strip()):
        raise SourceError(
            "fuente '%s': 'checksum' requiere 'algorithm' (%s) y 'value'"
            % (source_id, ", ".join(CHECKSUM_ALGORITHMS))
        )


def validate_source(data):
    if not isinstance(data, dict):
        raise SourceError("cada fuente debe ser un objeto JSON")
    if "id" not in data:
        raise SourceError("falta el campo 'id' en una fuente")
    check_source_id(data["id"])
    for field in BASE_FIELDS:
        if field not in data:
            raise SourceError("fuente '%s': falta el campo '%s'" % (data["id"], field))
    for field in ("name", "pageUrl", "version", "license", "attribution"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise SourceError("fuente '%s': '%s' debe ser texto no vacío" % (data["id"], field))
    if not data["pageUrl"].strip().startswith(("http://", "https://")):
        raise SourceError("fuente '%s': 'pageUrl' debe ser una URL http o https" % data["id"])
    license_url = data.get("licenseUrl")
    if license_url is not None and (
            not isinstance(license_url, str) or not license_url.startswith("https://") or license_url != license_url.strip()
            or len(license_url) <= len("https://") or any(c.isspace() for c in license_url)):
        raise SourceError("fuente '%s': 'licenseUrl' debe ser una URL https o null" % data["id"])
    if not isinstance(data["enabled"], bool):
        raise SourceError("fuente '%s': 'enabled' debe ser booleano" % data["id"])
    if data["id"] in SERVICE_SOURCES:
        extra = [field for field in ("filename", "size", "checksum", "files") if field in data]
        if extra:
            raise SourceError("fuente '%s': es un servicio en línea y no lleva %s" % (data["id"], ", ".join(extra)))
        if not isinstance(data.get("url"), str) or not data["url"].strip():
            raise SourceError("fuente '%s': falta 'url' (el servicio que se consulta) como texto no vacío" % data["id"])
    elif "files" in data:
        if any(field in data for field in FILE_FIELDS):
            raise SourceError("fuente '%s': use 'files' o los campos de un solo archivo, no ambos" % data["id"])
        entries = data["files"]
        if not isinstance(entries, list) or (not entries and data["id"] not in GENERATED_FILE_LISTS):
            raise SourceError("fuente '%s': 'files' debe ser una lista no vacía" % data["id"])
        names = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise SourceError("fuente '%s': cada elemento de 'files' debe ser un objeto" % data["id"])
            _validate_file(data["id"], entry)
            names.append(entry["filename"])
        if len(names) != len(set(names)):
            raise SourceError("fuente '%s': nombres de archivo duplicados en 'files'" % data["id"])
    else:
        _validate_file(data["id"], data)
    return Source(data)


def load_sources(path=DEFAULT_SOURCES_FILE):
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        raise SourceError("no existe el archivo de fuentes %s" % path)
    except ValueError as error:
        raise SourceError("JSON inválido en %s: %s" % (path, error))
    entries = document.get("sources") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise SourceError("%s debe contener una lista 'sources'" % path)
    sources = [validate_source(entry) for entry in entries]
    ids = [s.id for s in sources]
    if len(ids) != len(set(ids)):
        raise SourceError("hay identificadores de fuente duplicados en %s" % path)
    return sources
