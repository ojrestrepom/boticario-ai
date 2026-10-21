"""Configuración y verificador de fuentes (sources.json)."""
import json
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOL_DIR.parent.parent
DEFAULT_SOURCES_FILE = TOOL_DIR / "sources.json"
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / ".cache"

ADMITTED_SOURCES = (
    "usda", "wcvp", "wfo", "ema_json", "ema_pdf", "tppt", "efsa",
    "wikidata", "wikipedia_es", "commons",
)
DISCARDED_SOURCES = (
    "aromadb", "essoildb", "scentindb", "fda_ppdb", "comision_e",
    "oms", "who", "nhpid", "inaturalist", "drugbank",
)
CHECKSUM_ALGORITHMS = ("md5", "sha256")
REQUIRED_FIELDS = (
    "id", "version", "url", "filename", "license", "attribution",
    "size", "checksum", "enabled",
)


class SourceError(Exception):
    """Error de configuración o de verificación de una fuente."""


class Source:
    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.version = data["version"]
        self.url = data["url"]
        self.filename = data["filename"]
        self.license = data["license"]
        self.attribution = data["attribution"]
        self.size = data["size"]
        self.algorithm = data["checksum"]["algorithm"]
        self.checksum = data["checksum"]["value"].lower()
        self.enabled = data["enabled"]

    def cache_path(self, cache_dir=DEFAULT_CACHE_DIR):
        return Path(cache_dir) / self.id / self.filename


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


def validate_source(data):
    if not isinstance(data, dict):
        raise SourceError("cada fuente debe ser un objeto JSON")
    if "id" not in data:
        raise SourceError("falta el campo 'id' en una fuente")
    check_source_id(data["id"])
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise SourceError("fuente '%s': falta el campo '%s'" % (data["id"], field))
    for field in ("version", "url", "filename", "license", "attribution"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise SourceError("fuente '%s': '%s' debe ser texto no vacío" % (data["id"], field))
    if "/" in data["filename"] or "\\" in data["filename"] or data["filename"] in (".", ".."):
        raise SourceError("fuente '%s': 'filename' no puede contener rutas" % data["id"])
    if not isinstance(data["size"], int) or isinstance(data["size"], bool) or data["size"] < 0:
        raise SourceError("fuente '%s': 'size' debe ser un entero no negativo" % data["id"])
    if not isinstance(data["enabled"], bool):
        raise SourceError("fuente '%s': 'enabled' debe ser booleano" % data["id"])
    checksum = data["checksum"]
    if (not isinstance(checksum, dict) or checksum.get("algorithm") not in CHECKSUM_ALGORITHMS
            or not isinstance(checksum.get("value"), str) or not checksum["value"].strip()):
        raise SourceError(
            "fuente '%s': 'checksum' requiere 'algorithm' (%s) y 'value'"
            % (data["id"], ", ".join(CHECKSUM_ALGORITHMS))
        )
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
