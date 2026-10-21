"""Validador mínimo de JSON Schema (draft 2020-12), solo con la biblioteca estándar.

Subconjunto soportado (todo lo demás en un esquema se rechaza al cargarlo):
  type (nombre o lista: object, array, string, integer, number, boolean, null), enum, const,
  properties, required, additionalProperties (false o esquema), propertyNames (solo pattern),
  items (esquema), minItems, maxItems, minLength, maxLength, minimum, maximum, pattern, $ref
  (solo "#/$defs/<nombre>") y $defs. Se ignoran como anotaciones: $schema, $id, title,
  description, $comment, default, examples y las claves que empiezan por "x-".
"""
import json
import re

from .sources import TOOL_DIR, SourceError

DEFAULT_RECORD_SCHEMA = TOOL_DIR / "schema" / "record.schema.json"

SUPPORTED = {
    "type", "enum", "const", "properties", "required", "additionalProperties", "propertyNames",
    "items", "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum", "pattern",
    "$ref", "$defs",
}
ANNOTATIONS = {"$schema", "$id", "title", "description", "$comment", "default", "examples"}
TYPES = ("object", "array", "string", "integer", "number", "boolean", "null")


def load_schema(path=DEFAULT_RECORD_SCHEMA):
    try:
        with open(path, encoding="utf-8") as handle:
            schema = json.load(handle)
    except FileNotFoundError:
        raise SourceError("no existe el esquema %s" % path)
    except ValueError as error:
        raise SourceError("JSON inválido en el esquema %s: %s" % (path, error))
    check_supported(schema)
    return schema


def check_supported(node, where="#"):
    """Falla si el esquema usa palabras clave fuera del subconjunto implementado."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for name, child in value.items():
                    check_supported(child, "%s/%s/%s" % (where, key, name))
                continue
            if key in ("enum", "const", "required", "default", "examples"):
                continue
            if key in ANNOTATIONS or key.startswith("x-"):
                continue
            if key not in SUPPORTED:
                raise SourceError("el esquema usa '%s' en %s, fuera del subconjunto soportado" % (key, where))
            if key in ("items", "additionalProperties", "propertyNames") and isinstance(value, dict):
                check_supported(value, where + "/" + key)


def _is_type(value, name):
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise SourceError("tipo de esquema desconocido: %s" % name)


def _describe(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    return type(value).__name__


def validate(instance, schema):
    """Devuelve la lista de errores (texto con la ruta); vacía si la instancia cumple el esquema."""
    errors = []
    _walk(instance, schema, schema, "$", errors)
    return errors


def _resolve(root, ref):
    prefix = "#/$defs/"
    if not ref.startswith(prefix) or ref[len(prefix):] not in root.get("$defs", {}):
        raise SourceError("$ref no soportado o inexistente: %s" % ref)
    return root["$defs"][ref[len(prefix):]]


def _walk(value, node, root, path, errors):
    if "$ref" in node:
        _walk(value, _resolve(root, node["$ref"]), root, path, errors)
    if "type" in node:
        names = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_is_type(value, name) for name in names):
            errors.append("%s: se esperaba %s y llegó %s" % (path, " o ".join(names), _describe(value)))
            return
    if "enum" in node and value not in node["enum"]:
        errors.append("%s: el valor %r no está entre los permitidos %s" % (path, value, node["enum"]))
    if "const" in node and (value != node["const"] or isinstance(value, bool) != isinstance(node["const"], bool)):
        errors.append("%s: debe ser %r" % (path, node["const"]))
    if isinstance(value, str):
        if "minLength" in node and len(value) < node["minLength"]:
            errors.append("%s: longitud %d menor que el mínimo %d" % (path, len(value), node["minLength"]))
        if "maxLength" in node and len(value) > node["maxLength"]:
            errors.append("%s: longitud %d mayor que el máximo %d" % (path, len(value), node["maxLength"]))
        if "pattern" in node and not re.search(node["pattern"], value):
            errors.append("%s: no cumple el patrón %s" % (path, node["pattern"]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in node and value < node["minimum"]:
            errors.append("%s: %s menor que el mínimo %s" % (path, value, node["minimum"]))
        if "maximum" in node and value > node["maximum"]:
            errors.append("%s: %s mayor que el máximo %s" % (path, value, node["maximum"]))
    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append("%s: %d elementos, mínimo %d" % (path, len(value), node["minItems"]))
        if "maxItems" in node and len(value) > node["maxItems"]:
            errors.append("%s: %d elementos, máximo %d" % (path, len(value), node["maxItems"]))
        if "items" in node:
            for index, item in enumerate(value):
                _walk(item, node["items"], root, "%s[%d]" % (path, index), errors)
    if isinstance(value, dict):
        for name in node.get("required", []):
            if name not in value:
                errors.append("%s: falta el campo '%s'" % (path, name))
        properties = node.get("properties", {})
        extra = node.get("additionalProperties", True)
        for name, item in value.items():
            child_path = "%s.%s" % (path, name)
            if "propertyNames" in node:
                pattern = node["propertyNames"].get("pattern")
                if pattern and not re.search(pattern, name):
                    errors.append("%s: el nombre de campo no cumple el patrón %s" % (child_path, pattern))
            if name in properties:
                _walk(item, properties[name], root, child_path, errors)
            elif extra is False:
                errors.append("%s: campo desconocido" % child_path)
            elif isinstance(extra, dict):
                _walk(item, extra, root, child_path, errors)
