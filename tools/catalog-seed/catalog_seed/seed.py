"""Plan de regeneración incremental y sellado del manifiesto de la semilla (tarea 4.6)."""
import hashlib
import json
import re
from pathlib import Path

from . import goals as goals_lib
from .schema import load_schema, validate as validate_schema
from .sources import REPO_ROOT, TOOL_DIR, SourceError, load_sources
from .validate import BundleIndex, validate_record

DEFAULT_PROMPT = TOOL_DIR / "prompt" / "consolidate.md"
DEFAULT_BUNDLES_DIR = REPO_ROOT / "data" / "work" / "bundles"
MANIFEST_FORMAT = 1
PROMPT_VERSION_RE = re.compile(r"^prompt-version:\s*(\d+)\s*$", re.MULTILINE)


def canonical_json(value):
    """JSON canónico: claves ordenadas, sin espacios, UTF-8 sin escapes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def read_prompt_version(path=DEFAULT_PROMPT):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SourceError("no existe el prompt %s" % path)
    match = PROMPT_VERSION_RE.search(text)
    if not match:
        raise SourceError("el prompt %s no declara 'prompt-version: <n>'" % path)
    return int(match.group(1))


def schema_version(schema):
    version = schema.get("x-recordVersion")
    if not isinstance(version, int):
        raise SourceError("el esquema no declara 'x-recordVersion'")
    return version


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError as error:
        raise SourceError("JSON inválido en %s: %s" % (path, error))


def compute_plan(bundles_dir, seed_dir, prompt_version, record_version):
    """Plantas a regenerar: sin registro, con otro bundleHash, otra versión de prompt u otra de esquema.

    Devuelve una lista ordenada por id de dicts {id, plantKey, reasons}. Un registro ilegible cuenta como ausente.
    """
    plan = []
    bundles = []
    for path in sorted(Path(bundles_dir).glob("*.json")):
        bundle = _read_json(path)
        bundles.append(bundle)
    for bundle in sorted(bundles, key=lambda b: b["identity"]["proposedId"]):
        plant_id = bundle["identity"]["proposedId"]
        record_path = Path(seed_dir) / "plants" / ("%s.json" % plant_id)
        reasons = []
        if not record_path.is_file():
            reasons.append("sin-registro")
        else:
            try:
                record = _read_json(record_path)
            except SourceError:
                record = {}
                reasons.append("registro-ilegible")
            if record.get("bundleHash") != bundle.get("bundleHash"):
                reasons.append("bundleHash")
            if record.get("promptVersion") != prompt_version:
                reasons.append("promptVersion")
            if record.get("recordVersion") != record_version:
                reasons.append("recordVersion")
        if reasons:
            plan.append({"id": plant_id, "plantKey": bundle.get("plantKey"), "reasons": reasons})
    return plan


def read_records(seed_dir):
    """Registros de data/seed/plants ordenados por id. Falla si un archivo no se llama como su id."""
    records = []
    for path in sorted((Path(seed_dir) / "plants").glob("*.json")):
        record = _read_json(path)
        if not isinstance(record, dict) or record.get("id") != path.stem:
            raise SourceError("el archivo %s no se llama como el id de su registro (%s)"
                              % (path.name, record.get("id") if isinstance(record, dict) else None))
        records.append(record)
    return sorted(records, key=lambda r: r["id"])


def compute_seed_hash(records, catalog):
    """sha256 del contenido canónico de los registros ordenados por id y del catálogo de objetivos.

    Entrada: para cada registro 'plant\\n<id>\\n<json canónico>\\n' y al final 'goals\\n<json canónico>\\n'.
    """
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda r: r["id"]):
        digest.update(("plant\n%s\n%s\n" % (record["id"], canonical_json(record))).encode("utf-8"))
    digest.update(("goals\n%s\n" % canonical_json(catalog)).encode("utf-8"))
    return "sha256:" + digest.hexdigest()


def manifest_sources(sources):
    entries = []
    for source in sources:
        if not source.enabled:
            continue
        if not source.pinned:
            raise SourceError("la fuente '%s' está activa pero su snapshot no está fijado (size y checksum null)" % source.id)
        entries.append({
            "id": source.id,
            "name": source.name,
            "url": source.page_url,
            "version": source.version,
            "license": source.license,
            "attribution": source.attribution,
            "files": [{"filename": f.filename, "size": f.size,
                       "checksum": {"algorithm": f.algorithm, "value": f.checksum}} for f in source.files],
        })
    return sorted(entries, key=lambda e: e["id"])


def build_manifest(seed_dir, sources_path, schema, prompt_path, catalog=None):
    """Construye el manifiesto de la semilla. Falla si algún registro no es coherente con el prompt y el esquema."""
    catalog = catalog or goals_lib.load_goals_catalog(Path(seed_dir) / "goals.json")
    records = read_records(seed_dir)
    prompt_version = read_prompt_version(prompt_path)
    record_version = schema_version(schema)
    problems = []
    for record in records:
        for message in validate_schema(record, schema):
            problems.append("%s: %s" % (record["id"], message))
        if record.get("promptVersion") != prompt_version:
            problems.append("%s: promptVersion %r distinto del prompt vigente %d" % (record["id"], record.get("promptVersion"), prompt_version))
    if problems:
        raise SourceError("no se puede sellar la semilla:\n  " + "\n  ".join(problems[:20])
                          + ("\n  ... (%d más)" % (len(problems) - 20) if len(problems) > 20 else ""))
    flag_counts = {}
    for record in records:
        for code in {flag["code"] for flag in record["reviewFlags"]}:
            flag_counts[code] = flag_counts.get(code, 0) + 1
    return {
        "formatVersion": MANIFEST_FORMAT,
        "sources": manifest_sources(load_sources(sources_path)),
        "promptVersion": prompt_version,
        "recordVersion": record_version,
        "models": sorted({record["model"] for record in records}),
        "plantCount": len(records),
        "reviewFlags": dict(sorted(flag_counts.items())),
        "seedHash": compute_seed_hash(records, catalog),
    }


def format_json(value):
    """Formato estable de los archivos de la semilla: claves ordenadas, sangría de 2 espacios y salto de línea final."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_if_changed(path, text):
    path = Path(path)
    previous = path.read_text(encoding="utf-8") if path.is_file() else None
    if previous != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return previous != text


def read_import_records(from_dirs):
    """Lee los registros de los directorios de trabajo. Devuelve {id: (registro, ruta)}; falla si el nombre no es el id o el id se repite."""
    found = {}
    for directory in from_dirs:
        paths = sorted(Path(directory).glob("*.json"))
        if not paths:
            raise SourceError("no hay registros .json en %s" % directory)
        for path in paths:
            record = _read_json(path)
            plant_id = record.get("id") if isinstance(record, dict) else None
            if plant_id != path.stem:
                raise SourceError("el archivo %s no se llama como el id de su registro (%s)" % (path, plant_id))
            if plant_id in found:
                raise SourceError("el id '%s' está repetido: %s y %s" % (plant_id, found[plant_id][1], path))
            found[plant_id] = (record, path)
    return found


def import_records(from_dirs, seed_dir, bundles_dir, schema, goals_map, catalog):
    """Valida los registros de los directorios de trabajo contra sus paquetes y los escribe en <seed>/plants/<id>.json.

    Todo o nada: si algún registro tiene errores, no se escribe ninguno. Devuelve los ids escritos o actualizados.
    """
    found = read_import_records(from_dirs)
    index = BundleIndex(bundles_dir)
    problems = list(index.errors)
    for plant_id, (record, path) in sorted(found.items()):
        errors, _ = validate_record(record, index.by_id.get(plant_id), schema, goals_map, catalog)
        problems.extend("%s: %s" % (plant_id, message) for message in errors)
    if problems:
        raise SourceError("no se importan los registros:\n  " + "\n  ".join(problems[:20])
                          + ("\n  ... (%d más)" % (len(problems) - 20) if len(problems) > 20 else ""))
    written = []
    for plant_id, (record, _) in sorted(found.items()):
        if _write_if_changed(Path(seed_dir) / "plants" / ("%s.json" % plant_id), format_json(record)):
            written.append(plant_id)
    return written


def normalize_plants(seed_dir):
    """Reescribe cada registro de <seed>/plants con el formato estable. Devuelve los ids cuyo archivo cambió."""
    changed = []
    for record in read_records(seed_dir):
        if _write_if_changed(Path(seed_dir) / "plants" / ("%s.json" % record["id"]), format_json(record)):
            changed.append(record["id"])
    return changed


def seal(seed_dir, sources_path, schema_path=None, prompt_path=DEFAULT_PROMPT, from_dirs=(), bundles_dir=DEFAULT_BUNDLES_DIR,
         goals_map_path=None, goals_source=goals_lib.DEFAULT_GOALS_CATALOG):
    """Escribe la semilla: importa los registros de from_dirs (si hay), normaliza los de <seed>/plants, deja goals.json
    (lo copia de goals_source si falta) y escribe manifest.json. Devuelve (manifest, cambió)."""
    schema = load_schema(schema_path) if schema_path else load_schema()
    seed_dir = Path(seed_dir)
    goals_path = seed_dir / "goals.json"
    if not goals_path.is_file():
        _write_if_changed(goals_path, format_json(goals_lib.load_goals_catalog(goals_source)))
    if from_dirs:
        goals_map = goals_lib.load_goals_map(goals_map_path) if goals_map_path else goals_lib.load_goals_map()
        import_records(from_dirs, seed_dir, bundles_dir, schema, goals_map, goals_lib.load_goals_catalog(goals_path))
    manifest = build_manifest(seed_dir, sources_path, schema, prompt_path)
    normalize_plants(seed_dir)
    return manifest, _write_if_changed(seed_dir / "manifest.json", format_json(manifest))
