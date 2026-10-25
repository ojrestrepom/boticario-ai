"""Arranque de las pruebas: python -I no añade directorios a sys.path, así que se calcula aquí."""
import hashlib
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

from catalog_seed.sources import Source  # noqa: E402

PAYLOAD = b"contenido de prueba del insumo\n"


def make_source(payload=PAYLOAD, **overrides):
    data = {
        "id": "usda",
        "name": "Fixture",
        "pageUrl": "https://example.invalid/",
        "version": "test",
        "url": "https://example.invalid/insumo.zip",
        "filename": "insumo.zip",
        "license": "CC0",
        "attribution": "Fixture",
        "size": len(payload),
        "checksum": {"algorithm": "md5", "value": hashlib.md5(payload).hexdigest()},
        "enabled": True,
    }
    data.update(overrides)
    return Source(data)


def make_service_source(source_id="wikipedia_es", **overrides):
    """Fuente de un servicio en línea (Wikidata, Wikipedia, Commons): sin archivo ni checksum."""
    data = {
        "id": source_id,
        "name": "Fixture",
        "pageUrl": "https://example.invalid/",
        "version": "test",
        "url": "https://example.invalid/servicio",
        "license": "CC BY-SA 4.0",
        "attribution": "Fixture",
        "enabled": True,
    }
    data.update(overrides)
    return Source(data)
