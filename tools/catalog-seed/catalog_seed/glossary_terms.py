"""Lista versionada de términos del glosario de actividades (glossary-terms.json): carga, validación y alertas.

La lista decide qué actividades llevan explicación. Cada término declara la actividad tal como aparece en los grupos de uso,
el título de su entrada en Wikcionario y, tras la propuesta (tarea 3.3), la fuente elegida:

- `wiktionary_es`: el número de acepción (`sense`) de la entrada; el texto sale de la caché y es literal.
- `wikipedia_es`: el artículo (`wikipediaTitle`), el modo (`literal` o `adapted`) y, si es `adapted`, el texto parafraseado
  (`text`) con la evidencia literal del extracto (`evidence`).

Los términos que no entran quedan en `excluded` con su motivo. Los patrones de eficacia que el usuario aprobó por término
quedan en `approvedPatterns`.
"""
import json
import re
import unicodedata
from pathlib import Path

from .sources import SourceError, TOOL_DIR
from .validate import DOSE_RE, load_sensitive_activities

DEFAULT_TERMS_FILE = TOOL_DIR / "glossary-terms.json"
SOURCES = ("wiktionary_es", "wikipedia_es")
MODES = ("literal", "adapted")
EXCLUSION_CODES = ("sin-entrada", "solo-forma-flexionada", "circular", "sinonimo", "vaga", "sensible", "patron-no-aprobado",
                   "sin-articulo", "desambiguacion", "articulo-no-define")
# Enfermedades graves nombradas en español (la lista sensible de los registros está en inglés, como USDA).
SERIOUS_DISEASE_ES = (
    r"cáncer|cancer", r"tumor(?:es)?", r"carcinoma\w*", r"sarcoma\w*", r"melanoma\w*", r"leucemia\w*", r"linfoma\w*", r"diabetes",
    r"sida", r"vih", r"tuberculosis", r"malaria", r"paludismo", r"cólera", r"rabia", r"tétanos", r"ántrax", r"peste", r"viruela",
    r"difteria", r"tifoidea", r"fiebre\s+amarilla", r"dengue", r"polio\w*", r"lepra", r"hepatitis", r"cirrosis", r"epilepsia",
    r"apoplej\w+", r"ictus", r"infarto", r"parkinson\w*",
)
SERIOUS_DISEASE_RE = re.compile(r"\b(?:%s)\b" % "|".join(SERIOUS_DISEASE_ES), re.IGNORECASE)


class GlossaryTermsError(SourceError):
    """La lista de términos del glosario es inválida."""


def base_key(activity):
    """Forma base de una actividad (D8): el texto antes del primer paréntesis, en minúsculas NFC y con los espacios colapsados."""
    text = unicodedata.normalize("NFC", str(activity or "")).split("(")[0]
    return " ".join(text.split()).lower()


def is_sensitive(activity, sensitive=None):
    """True si la actividad es de la lista sensible (forma base) o empieza por la fórmula de enfermedad grave."""
    sensitive = sensitive if sensitive is not None else load_sensitive_activities()
    key = base_key(activity)
    return key in sensitive["terms"] or str(activity or "").startswith(sensitive["prefix"])


def text_alerts(text, sensitive=None):
    """Alertas de un texto que se mostraría: patrones vigilados de dosis y eficacia, y enfermedades graves.

    Devuelve una lista de textos cortos; vacía si no hay ninguna.
    """
    sensitive = sensitive if sensitive is not None else load_sensitive_activities()
    alerts = []
    for match in DOSE_RE.finditer(text):
        alerts.append("patrón vigilado «%s»" % match.group(0).lower())
    for match in SERIOUS_DISEASE_RE.finditer(text):
        alerts.append("enfermedad grave «%s»" % match.group(0).lower())
    lowered = text.lower()
    for term in sensitive["terms"]:
        if re.search(r"\b%s\b" % re.escape(term), lowered):
            alerts.append("término sensible «%s»" % term)
    seen = []
    for alert in alerts:
        if alert not in seen:
            seen.append(alert)
    return seen


def _require(condition, message):
    if not condition:
        raise GlossaryTermsError(message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_term(term, sensitive):
    activity = term.get("activity")
    _require(_text(activity), "un término no tiene 'activity'")
    _require(_text(term.get("wiktionaryTitle")), "término '%s': falta 'wiktionaryTitle'" % activity)
    _require(not is_sensitive(activity, sensitive), "término '%s': es una actividad sensible de sensitive-activities.json" % activity)
    _require(not is_sensitive(term["wiktionaryTitle"], sensitive), "término '%s': su título es una actividad sensible" % activity)
    source = term.get("source")
    if source is None:
        # Aún sin propuesta (tarea 3.3): solo puede declarar títulos.
        for field in ("sense", "mode", "text", "evidence"):
            _require(field not in term, "término '%s': '%s' sin 'source'" % (activity, field))
        return
    _require(source in SOURCES, "término '%s': 'source' debe ser %s" % (activity, " o ".join(SOURCES)))
    _require(_text(term.get("reason")), "término '%s': falta el motivo ('reason') de la propuesta" % activity)
    if source == "wiktionary_es":
        sense = term.get("sense")
        _require(isinstance(sense, int) and not isinstance(sense, bool) and sense >= 1, "término '%s': 'sense' debe ser un entero positivo" % activity)
        for field in ("mode", "text", "evidence"):
            _require(field not in term, "término '%s': '%s' no aplica a Wikcionario" % (activity, field))
        return
    _require(_text(term.get("wikipediaTitle")), "término '%s': falta 'wikipediaTitle'" % activity)
    _require("sense" not in term, "término '%s': 'sense' no aplica a Wikipedia" % activity)
    _require(term.get("mode") in MODES, "término '%s': 'mode' debe ser literal o adapted" % activity)
    if term["mode"] == "adapted":
        _require(_text(term.get("text")), "término '%s': un texto adaptado necesita 'text'" % activity)
        _require(_text(term.get("evidence")), "término '%s': un texto adaptado necesita su 'evidence' literal" % activity)
    else:
        for field in ("text", "evidence"):
            _require(field not in term, "término '%s': un texto literal no lleva '%s'" % (activity, field))


def validate_terms(document, sensitive=None):
    """Valida el documento ya leído. Devuelve el mismo documento."""
    sensitive = sensitive if sensitive is not None else load_sensitive_activities()
    _require(isinstance(document, dict), "glossary-terms.json debe ser un objeto")
    _require(document.get("version") == 1, "'version' debe ser 1")
    terms, excluded = document.get("terms"), document.get("excluded", [])
    _require(isinstance(terms, list) and terms, "'terms' debe ser una lista no vacía")
    _require(isinstance(excluded, list), "'excluded' debe ser una lista")
    keys = {}
    for term in terms:
        _require(isinstance(term, dict), "cada término debe ser un objeto")
        validate_term(term, sensitive)
        key = base_key(term["activity"])
        _require(key not in keys, "término duplicado: '%s'" % term["activity"])
        keys[key] = term["activity"]
    for item in excluded:
        _require(isinstance(item, dict) and _text(item.get("activity")), "cada excluido necesita 'activity'")
        _require(item.get("code") in EXCLUSION_CODES, "excluido '%s': 'code' debe ser uno de %s" % (item.get("activity"), ", ".join(EXCLUSION_CODES)))
        _require(_text(item.get("reason")), "excluido '%s': falta el motivo ('reason')" % item.get("activity"))
        _require(_text(item.get("date")), "excluido '%s': falta la fecha ('date')" % item.get("activity"))
        _require(base_key(item["activity"]) not in keys, "'%s' está a la vez en términos y en excluidos" % item["activity"])
    approved = document.get("approvedPatterns", {})
    _require(isinstance(approved, dict), "'approvedPatterns' debe ser un objeto")
    for activity, patterns in approved.items():
        _require(base_key(activity) in keys, "approvedPatterns: '%s' no es un término de la lista" % activity)
        _require(isinstance(patterns, list) and patterns, "approvedPatterns '%s': debe ser una lista no vacía" % activity)
        for entry in patterns:
            _require(isinstance(entry, dict) and _text(entry.get("pattern")) and _text(entry.get("reason")),
                     "approvedPatterns '%s': cada patrón necesita 'pattern' y 'reason'" % activity)
    return document


def load_terms(path=DEFAULT_TERMS_FILE, sensitive=None):
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        raise GlossaryTermsError("no existe la lista de términos %s" % path)
    except ValueError as error:
        raise GlossaryTermsError("JSON inválido en %s: %s" % (path, error))
    return validate_terms(document, sensitive)


def write_terms(document, path=DEFAULT_TERMS_FILE):
    """Escribe la lista con un formato estable: un término por línea."""
    validate_terms(document)
    lines = ["{", '  "version": %d,' % document["version"], '  "description": %s,' % json.dumps(document["description"], ensure_ascii=False)]
    for name in ("terms", "excluded"):
        items = document.get(name, [])
        lines.append('  "%s": [' % name)
        lines.append(",\n".join("    " + json.dumps(i, ensure_ascii=False) for i in items))
        lines.append("  ],")
    lines.append('  "approvedPatterns": %s' % json.dumps(document.get("approvedPatterns", {}), ensure_ascii=False, indent=2).replace("\n", "\n  "))
    lines.append("}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
