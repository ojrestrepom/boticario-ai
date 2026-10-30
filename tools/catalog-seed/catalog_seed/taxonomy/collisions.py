"""Datos de la regla de colisiones («criterio de Wikipedia»): decisiones registradas y excepciones «separar siempre».

La regla se aplica en `build_universe` con estos datos, sin red. Los archivos viven en `tools/catalog-seed/`:

- `collision-decisions.json` (`catalog-collision-decisions/1`): por grupo (clave del aceptado) y miembro heterotípico (clave del
  nombre), la decisión `fuse` o `separate`, el motivo y la evidencia de Wikipedia con la que se tomó. Lo escribe el comando
  `collisions-decide` y solo agrega; cambiar una decisión es una edición manual.
- `collision-exceptions.json` (`catalog-collision-exceptions/1`): nombres que se separan siempre, cada uno con su motivo.
"""
import hashlib
import json
import os

from .names import parse_name

DECISIONS_FORMAT = "catalog-collision-decisions/1"
EXCEPTIONS_FORMAT = "catalog-collision-exceptions/1"
FUSE = "fuse"
SEPARATE = "separate"
REASONS = {
    FUSE: ("redireccion", "sin-articulo", "articulo-compartido"),
    SEPARATE: ("articulo-propio", "excepcion"),
}


class CollisionFileError(Exception):
    """Un archivo de decisiones o de excepciones no tiene el formato esperado."""


def name_key(name):
    """Clave de comparación de un nombre científico (la misma que usa el resolvedor)."""
    parsed = parse_name(name or "")
    return parsed.key_full if parsed.ok else " ".join((name or "").lower().split())


class CollisionRules(object):
    """Decisiones registradas y excepciones, como datos inmutables para `build_universe`."""

    def __init__(self, decisions=None, exceptions=None):
        self.groups = (decisions or {}).get("groups", {})
        self.exceptions = list((exceptions or {}).get("exceptions", []))
        self._exception_by_key = {}
        for item in self.exceptions:
            self._exception_by_key.setdefault(name_key(item["name"]), item.get("reason", ""))

    def decision(self, accepted_key, member_key):
        """Decisión registrada `{decision, reason, ...}` del miembro, o None si el grupo o el miembro no tienen."""
        return (self.groups.get(accepted_key, {}).get("members") or {}).get(member_key)

    def exception_reason(self, keys):
        """Motivo de la excepción si alguna de las claves de nombre figura en la lista; None si no."""
        for key in sorted(keys):
            if key in self._exception_by_key:
                return self._exception_by_key[key] or "excepción"
        return None


def _read_json(path):
    try:
        with open(str(path), encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError as error:
        raise CollisionFileError("%s no es JSON válido: %s" % (path, error))


def validate_decisions(document, path="decisiones"):
    if document.get("format") != DECISIONS_FORMAT or not isinstance(document.get("groups"), dict):
        raise CollisionFileError("%s: se esperaba format %s con un objeto 'groups'" % (path, DECISIONS_FORMAT))
    for akey, group in document["groups"].items():
        members = group.get("members")
        if not isinstance(members, dict) or not members:
            raise CollisionFileError("%s: el grupo '%s' no tiene miembros" % (path, akey))
        for mkey, member in members.items():
            decision, reason = member.get("decision"), member.get("reason")
            if decision not in REASONS or reason not in REASONS[decision]:
                raise CollisionFileError("%s: %s / %s: decisión '%s' con motivo '%s' no válida" % (path, akey, mkey, decision, reason))


def load_decisions(path):
    """Documento de decisiones; un archivo ausente equivale a ninguna decisión registrada."""
    if path is None or not os.path.isfile(str(path)):
        return {"format": DECISIONS_FORMAT, "groups": {}}
    document = _read_json(path)
    validate_decisions(document, str(path))
    return document


def load_exceptions(path):
    if path is None or not os.path.isfile(str(path)):
        return {"format": EXCEPTIONS_FORMAT, "exceptions": []}
    document = _read_json(path)
    items = document.get("exceptions")
    if document.get("format") != EXCEPTIONS_FORMAT or not isinstance(items, list):
        raise CollisionFileError("%s: se esperaba format %s con una lista 'exceptions'" % (path, EXCEPTIONS_FORMAT))
    for item in items:
        if not item.get("name") or not item.get("reason"):
            raise CollisionFileError("%s: toda excepción necesita 'name' y 'reason'" % path)
    return document


def load_rules(decisions_path=None, exceptions_path=None):
    return CollisionRules(load_decisions(decisions_path), load_exceptions(exceptions_path))


def dump_decisions(path, document):
    with open(str(path), "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def file_digest(path):
    """sha256 del archivo, o None si no existe."""
    if path is None or not os.path.isfile(str(path)):
        return None
    with open(str(path), "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()
