"""Validador del registro consolidado contra su paquete (tarea 4.5).

El contrato del paquete (bundle v1) sale de la spec «Paquete por planta determinista». El validador
solo depende de estos campos: refs; identity.proposedId; bundleHash; sections.regulatory[]
(ref, therapeuticAreas, outcome, combination); sections.safety[] (source, humanToxicity y, para la EMA,
severeInteractions); sections.images[].ref; sections.uses[] (activity y, opcional, candidates).
"""
import json
import re
from pathlib import Path

from . import goals as goals_lib
from .schema import load_schema, validate as validate_schema
from .sources import TOOL_DIR, SourceError

FLAG_CODES_PATH = TOOL_DIR / "flag-codes.json"
SENSITIVE_ACTIVITIES_PATH = TOOL_DIR / "sensitive-activities.json"
SERIOUS_DISEASE = "enfermedad-grave"
RISK_SIGNAL = "senal-de-riesgo"


def load_flag_codes(path=FLAG_CODES_PATH):
    """Conjunto de códigos de reviewFlags del catálogo cerrado (flag-codes.json)."""
    try:
        with open(path, encoding="utf-8") as handle:
            return set(json.load(handle)["codes"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SourceError("catálogo de códigos de flag ilegible %s: %s" % (path, error))


def load_sensitive_activities(path=SENSITIVE_ACTIVITIES_PATH):
    """Lista versionada de actividades sensibles (sensitive-activities.json).

    Devuelve {"prefix": fórmula de las enfermedades graves, "terms": {forma base en minúsculas: categoría}}.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            categories = json.load(handle)["categories"]
        terms = {}
        for term in categories[SERIOUS_DISEASE]["terms"]:
            terms[term.strip().lower()] = SERIOUS_DISEASE
        for term in categories[RISK_SIGNAL]["terms"]:
            terms[term.strip().lower()] = RISK_SIGNAL
        return {"prefix": categories[SERIOUS_DISEASE]["formulaPrefix"], "terms": terms}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SourceError("lista de actividades sensibles ilegible %s: %s" % (path, error))


def activity_category(activity, sensitive):
    """Categoría sensible de una actividad de USDA o None. Compara la forma base: sin el calificador entre paréntesis y sin distinguir mayúsculas."""
    base = str(activity or "").split("(")[0].strip().lower()
    return sensitive["terms"].get(base)


UNRESOLVED_MARK = "(sin resolver)"
TOXIC_LEVELS = ("strong toxic", "very strong toxic")
STRESS_GOAL = "relajacion-estres"

DOSE_PATTERNS = [
    r"\bdosis\b", r"\bposolog\w*", r"\bmg\b", r"\bml\b", r"\b(?:\d+|un|una|unas|unos|dos|tres|cuatro|cinco|seis|diez|varias|algunas|pocas)\s+gotas?\b", r"\bgotas\s+de\b", r"\bcucharad\w*",
    r"\bcura(?:r|n|tiv\w*)?\b", r"\btrata(?:n|r)?\b", r"\btratamientos?\b", r"\bprevien\w*", r"\bprevenir\b",
    r"\d+(?:[.,]\d+)?\s*(?:[µμ]g|mcg|ug|mg|kg|g)\b(?:\s*/\s*(?:kg|día|dia|d)\b)?", r"\bpor\s+(?:kg|kilo|kilogramo)s?\b(?:\s+de\s+peso)?",
    r"\belimina\w*", r"\balivia\w*", r"\baliviar\b", r"\beficaz\w*", r"\beficacia\b", r"\befectiv\w*",
]
DOSE_RE = re.compile("|".join(DOSE_PATTERNS), re.IGNORECASE)

# Anotación de idioma de USDA al final de un nombre: «Canela de la China (Sp.)», «Weihrauchbaum (Ger.)».
LANGUAGE_NOTE_RE = re.compile(r"\(\s*(?:[A-Z][a-z]{1,7}\.|(?:Sp|Ger|Fr|Jap|Chin|Port|Ital|Dut|Rus|Peru|Bol)\.?|Zulu|Pinyin|Chinese|Japanese|Spanish|German|French|Portuguese|Italian|Latin)\s*\)\s*$")
MAX_USE_GROUPS = 20

PUBLIC_DOMAIN_RE = re.compile(r"^(?:cc0(?:[ -]?1\.0)?|public domain|dominio p[uú]blico|pd(?:[ -].*)?)$", re.IGNORECASE)
CC_BY_RE = re.compile(r"^cc[ -]by(?P<sa>[ -]sa)?(?:[ -]\d\.\d)?(?:[ -]\w+)?$", re.IGNORECASE)


class BundleIndex:
    """Paquetes de un directorio, indexados por identity.proposedId."""

    def __init__(self, directory):
        self.by_id = {}
        self.errors = []
        for path in sorted(Path(directory).glob("*.json")):
            try:
                with open(path, encoding="utf-8") as handle:
                    bundle = json.load(handle)
                self.by_id[bundle["identity"]["proposedId"]] = bundle
            except (ValueError, KeyError, TypeError) as error:
                self.errors.append("paquete ilegible %s: %s" % (path.name, error))


def image_license_kind(license_text):
    """'public' | 'cc-by' | 'cc-by-sa' | None (licencia no aceptada, incluidas NC y ND)."""
    text = (license_text or "").strip()
    if PUBLIC_DOMAIN_RE.match(text):
        return "public"
    match = CC_BY_RE.match(text)
    if match and not re.search(r"\b(nc|nd)\b", text, re.IGNORECASE):
        return "cc-by-sa" if match.group("sa") else "cc-by"
    return None


def toxic_categories(value):
    """Categorías de TPPT: separa por ', ' y toma el prefijo antes del paréntesis."""
    if not isinstance(value, str):
        return []
    return [part.split("(")[0].strip().lower() for part in value.split(", ") if part.strip()]


def is_toxic_by_tppt(bundle):
    for entry in bundle.get("sections", {}).get("safety", []):
        if entry.get("source") == "tppt" and any(c in TOXIC_LEVELS for c in toxic_categories(entry.get("humanToxicity"))):
            return True
    return False


def has_severe_interactions(bundle):
    """El armado de paquetes (bundles.py) marca severeInteractions en la sección 4.5 de la EMA con safety.ema_interaction_class (mapa de seguridad v2)."""
    return any(entry.get("source") == "ema_pdf" and entry.get("severeInteractions") is True
               for entry in bundle.get("sections", {}).get("safety", []))


def _is_combination(value):
    return any(part.strip().lower() == "yes" for part in str(value or "").split(";"))


def ema_goal_support(bundle, goals_map):
    """Dict (objetivo, subárea) -> {ref de la EMA que lo respalda} y lista de motivos por los que otras fichas no cuentan."""
    support, skipped = {}, []
    for entry in bundle.get("sections", {}).get("regulatory", []):
        ref = entry.get("ref")
        if not goals_lib.counted_outcomes(goals_map, entry.get("outcome")):
            skipped.append("%s: el resultado '%s' no es monografía ni entrada de lista" % (ref, entry.get("outcome")))
            continue
        if _is_combination(entry.get("combination")):
            skipped.append("%s: es un producto combinado" % ref)
            continue
        for raw in entry.get("therapeuticAreas") or []:
            for area in goals_lib.split_values(raw, goals_map.get("separator", ";")):
                mapped = goals_lib.map_area(goals_map, area)
                if mapped is not None and mapped[0] is not None:
                    support.setdefault((mapped[0], mapped[1]), set()).add(ref)
    return support, skipped


def _collect_refs(record):
    """(ruta, ref) de todo ref citado en el registro."""
    found = []

    def visit(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "refs" and isinstance(value, list):
                    found.extend(("%s.refs" % path, ref) for ref in value)
                elif key == "citations" and isinstance(value, list):
                    for index, citation in enumerate(value):
                        if isinstance(citation, dict) and citation.get("ref"):
                            found.append(("%s.citations[%d]" % (path, index), citation["ref"]))
                elif key != "refs":
                    visit(value, "%s.%s" % (path, key))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, "%s[%d]" % (path, index))

    visit({k: v for k, v in record.items() if k != "refs"}, "$")
    return found


def _visible_texts(record, formula_prefix=""):
    texts = []

    def add(path, value):
        if isinstance(value, str):
            texts.append((path, value))

    for key in ("displayName", "origin", "description"):
        if record.get(key):
            add(key + ".value", record[key]["value"])
    for index, item in enumerate(record["commonNames"]):
        add("commonNames[%d].text" % index, item["text"])
    for index, item in enumerate(record["partsUsed"]):
        add("partsUsed[%d].value" % index, item["value"])
    for index, group in enumerate(record["traditionalUses"]):
        activity = group["activity"]
        if formula_prefix and activity.startswith(formula_prefix):
            activity = activity[len(formula_prefix):]  # la fórmula «sin eficacia demostrada» no es una promesa
        add("traditionalUses[%d].activity" % index, activity)
        for country in group["countries"]:
            add("traditionalUses[%d].countries" % index, country)
    for index, goal in enumerate(record["goals"]):
        add("goals[%d].area" % index, goal["area"])
        add("goals[%d].evidence" % index, goal["evidence"])
    if record.get("safety"):
        add("safety.text", record["safety"]["text"])
    return texts


def _flag_targets(record):
    return {flag["target"] for flag in record["reviewFlags"]}


def _goal_targets(goal, index):
    targets = {"goals.%s" % goal["goal"], "goals[%d]" % index}
    if goal.get("subarea"):
        targets.add("goals.%s.%s" % (goal["goal"], goal["subarea"]))
    return targets


def validate_record(record, bundle, schema, goals_map, catalog, flag_codes=None, sensitive=None):
    """Valida un registro contra su paquete. Devuelve (errores, advertencias)."""
    errors, warnings = [], []
    sensitive = sensitive if sensitive is not None else load_sensitive_activities()
    plant = record.get("id", "?") if isinstance(record, dict) else "?"

    schema_errors = validate_schema(record, schema)
    if schema_errors:
        return ["esquema: %s" % message for message in schema_errors], warnings
    if bundle is None:
        return ["no hay paquete para la planta '%s'" % plant], warnings

    # Identidad.
    if record["id"] != bundle["identity"]["proposedId"]:
        errors.append("id '%s' distinto de identity.proposedId '%s'" % (record["id"], bundle["identity"]["proposedId"]))
    if record["bundleHash"] != bundle.get("bundleHash"):
        errors.append("bundleHash '%s' distinto del del paquete '%s'" % (record["bundleHash"], bundle.get("bundleHash")))

    # Refs.
    bundle_refs = bundle.get("refs", {})
    used = set()
    for path, ref in _collect_refs(record):
        used.add(ref)
        if ref not in bundle_refs:
            errors.append("%s: el ref '%s' no existe en refs del paquete de '%s'" % (path, ref, plant))
        elif ref not in record["refs"]:
            errors.append("%s: el ref '%s' no está en refs del registro" % (path, ref))
    for ref, entry in record["refs"].items():
        if ref not in bundle_refs:
            errors.append("refs.%s: no existe en refs del paquete de '%s'" % (ref, plant))
        elif entry != bundle_refs[ref]:
            errors.append("refs.%s: dataset, etiqueta, licencia o url distintos de los del paquete" % ref)
        if entry.get("dataset") == "wikipedia_es" and re.search(r"cc[ -]by-sa", entry.get("license", ""), re.IGNORECASE) and not entry.get("url"):
            errors.append("refs.%s: un ref de Wikipedia con licencia CC BY-SA exige 'url' del artículo" % ref)

    # Objetivos.
    support, skipped = ema_goal_support(bundle, goals_map)
    goal_catalog = set(goals_lib.goal_ids(catalog))
    toxic = is_toxic_by_tppt(bundle)
    seen = set()
    targets = _flag_targets(record)
    if toxic and record["goals"]:
        errors.append("planta tóxica según TPPT (strong o very strong toxic) con objetivos")
    for index, goal in enumerate(record["goals"]):
        label = "goals[%d] (%s)" % (index, goal["goal"])
        if goal["goal"] not in goal_catalog:
            errors.append("%s: el objetivo no existe en el catálogo de objetivos" % label)
            continue
        sub = goal["subarea"]
        if goal["goal"] == "otros-objetivos":
            if sub is None:
                errors.append("%s: 'otros-objetivos' exige subárea" % label)
            elif sub not in goals_lib.subareas_of(catalog, goal["goal"]):
                errors.append("%s: la subárea '%s' no existe en el catálogo" % (label, sub))
        elif sub is not None:
            errors.append("%s: solo 'otros-objetivos' lleva subárea" % label)
        if (goal["goal"], sub) in seen:
            errors.append("%s: objetivo repetido" % label)
        seen.add((goal["goal"], sub))
        backing = support.get((goal["goal"], sub), set())
        if not backing & set(goal["refs"]):
            detail = "; ".join(skipped) if skipped else "el paquete no tiene áreas de la EMA que lo mapeen"
            errors.append("%s: sin respaldo de la EMA (%s)" % (label, detail))
        else:
            translations = {entry["es"] for area, entry in goals_map["areas"].items()
                            if entry["goal"] == goal["goal"] and entry["subarea"] == sub}
            if not all(part.strip() in translations for part in goal["area"].split(";")):
                warnings.append("%s: 'area' no coincide con la traducción del mapa (%s)" % (label, " | ".join(sorted(translations))))
        if goal["goal"] == STRESS_GOAL and has_severe_interactions(bundle) and not goal["pendingReview"]:
            errors.append("%s: la planta tiene interacciones graves en la EMA y el objetivo debe llevar pendingReview verdadero" % label)
        if goal["pendingReview"] and not targets & _goal_targets(goal, index):
            errors.append("%s: pendingReview sin un reviewFlag cuyo target lo señale (p. ej. 'goals.%s')" % (label, goal["goal"]))

    # Usos tradicionales.
    activities = {use.get("activity"): use for use in bundle.get("sections", {}).get("uses", [])}
    for index, group in enumerate(record["traditionalUses"]):
        label = "traditionalUses[%d]" % index
        source_group = activities.get(group["activitySource"])
        category = activity_category(group["activitySource"], sensitive)
        if category == SERIOUS_DISEASE and not group["activity"].startswith(sensitive["prefix"]):
            errors.append("%s: la actividad '%s' es una enfermedad grave y 'activity' debe empezar por «%s»" % (label, group["activitySource"], sensitive["prefix"]))
        elif category == SERIOUS_DISEASE:
            rest = group["activity"][len(sensitive["prefix"]):]
            if not rest or not rest[0].isalpha() or "  " in rest or rest != rest.strip() or re.search(r"[\"“”«»'‘’]$|\"", rest):
                errors.append("%s: la fórmula de enfermedad grave está mal formada ('%s'): exige «%s» con un solo espacio, sin espacios dobles y sin comillas sueltas" % (label, group["activity"], sensitive["prefix"]))
        if category == RISK_SIGNAL:
            errors.append("%s: la actividad '%s' es una señal de riesgo y va en safety como advertencia, no en traditionalUses" % (label, group["activitySource"]))
        if source_group is None:
            errors.append("%s: activitySource '%s' no es una actividad del paquete" % (label, group["activitySource"]))
        candidates = (source_group or {}).get("candidates") or {}
        all_candidates = {c.get("ref") for options in candidates.values() for c in options}
        unresolved = False
        resolved = False
        for c_index, citation in enumerate(group["citations"]):
            c_label = "%s.citations[%d]" % (label, c_index)
            marked = UNRESOLVED_MARK in citation["text"]
            if citation["ref"] is None:
                unresolved = True
                if not marked:
                    errors.append("%s: cita sin ref y sin la marca '%s'" % (c_label, UNRESOLVED_MARK))
                continue
            resolved = True
            if marked:
                errors.append("%s: cita con ref '%s' y con la marca '%s'" % (c_label, citation["ref"], UNRESOLVED_MARK))
            if not citation["ref"].startswith("usda_reference:"):
                errors.append("%s: el ref '%s' no es un usda_reference:*" % (c_label, citation["ref"]))
            elif citation["ref"] not in bundle_refs:
                errors.append("%s: el ref '%s' no existe en el paquete (cita inventada)" % (c_label, citation["ref"]))
            elif candidates:
                allowed = {c.get("ref") for c in candidates.get(citation["key"], [])} or all_candidates
                if citation["ref"] not in allowed:
                    errors.append("%s: el ref '%s' no es una candidata del paquete para la clave '%s'" % (c_label, citation["ref"], citation["key"]))
        if unresolved and not resolved and not group["pendingReview"]:
            errors.append("%s: ninguna cita está resuelta (todas '%s') y pendingReview falso" % (label, UNRESOLVED_MARK))
        if resolved and group["pendingReview"]:
            errors.append("%s: tiene al menos una cita resuelta y pendingReview verdadero (el grupo se muestra)" % label)
        if group["pendingReview"] and "%s[%d]" % ("traditionalUses", index) not in targets:
            errors.append("%s: pendingReview sin un reviewFlag cuyo target sea '%s'" % (label, label))
        if unresolved and not any(f["code"] == "cita-sin-resolver" and f["target"] == label for f in record["reviewFlags"]):
            errors.append("%s: falta el reviewFlag 'cita-sin-resolver' con target '%s'" % (label, label))

    # Cobertura mínima: los grupos del paquete que no son señales de riesgo llegan al registro hasta el tope.
    package_groups = {use.get("activity") for use in bundle.get("sections", {}).get("uses", [])
                      if activity_category(use.get("activity"), sensitive) != RISK_SIGNAL}
    expected = min(MAX_USE_GROUPS, len(package_groups))
    if len(record["traditionalUses"]) < expected:
        errors.append("traditionalUses: tiene %d grupos y el paquete trae %d usos que no son señales de riesgo (se esperan al menos %d)"
                        % (len(record["traditionalUses"]), len(package_groups), expected))

    # Seguridad: el nivel nulo con texto es válido cuando ninguna entrada fija nivel; sin información, safety es nulo con su flag.
    safety = record["safety"]
    bundle_levels = [entry.get("level") for entry in bundle.get("sections", {}).get("safety", []) if entry.get("level")]
    has_no_data_flag = any(f["code"] == "sin-datos-de-seguridad" for f in record["reviewFlags"])
    if safety is None:
        if bundle_levels:
            errors.append("safety: es nulo pero el paquete fija nivel de seguridad (%s)" % ", ".join(sorted(set(bundle_levels))))
        if not has_no_data_flag:
            errors.append("safety: es nulo y falta el reviewFlag 'sin-datos-de-seguridad'")
    else:
        if safety["level"] is None and bundle_levels:
            errors.append("safety.level: es nulo pero el paquete fija nivel de seguridad (%s)" % ", ".join(sorted(set(bundle_levels))))
        if has_no_data_flag:
            errors.append("safety: tiene contenido y el registro lleva el reviewFlag 'sin-datos-de-seguridad'")

    # Señales de riesgo del paquete: van a safety con los refs usda_use:* de sus filas.
    risk_refs = {ref for use in bundle.get("sections", {}).get("uses", []) if activity_category(use.get("activity"), sensitive) == RISK_SIGNAL
                 for ref in use.get("refs", []) if str(ref).startswith("usda_use:")}
    if risk_refs:
        if safety is None:
            errors.append("safety: es nulo pero el paquete trae señales de riesgo en sus usos (%s) y deben ir como advertencia" % ", ".join(sorted(risk_refs)[:3]))
        elif not risk_refs & set(safety["refs"]):
            errors.append("safety.refs: ningún ref usda_use:* de las señales de riesgo del paquete (p. ej. %s)" % ", ".join(sorted(risk_refs)[:3]))

    # Imagen.
    image = record["image"]
    if image is not None:
        kind = image_license_kind(image["license"])
        if kind is None:
            errors.append("image: licencia '%s' no aceptada (CC0, dominio público, CC BY o CC BY-SA)" % image["license"])
        elif kind in ("cc-by", "cc-by-sa") and not image["attributionRequired"]:
            errors.append("image: la licencia '%s' exige attributionRequired verdadero" % image["license"])
        image_refs = {entry.get("ref") for entry in bundle.get("sections", {}).get("images", [])}
        if not image_refs & set(image["refs"]):
            errors.append("image: ningún ref corresponde a una imagen del paquete")

    # Códigos de flag fuera del catálogo cerrado: advertencia.
    known = flag_codes if flag_codes is not None else load_flag_codes()
    for index, flag in enumerate(record["reviewFlags"]):
        if flag["code"] not in known:
            warnings.append("reviewFlags[%d]: el código '%s' no está en el catálogo de flag-codes.json" % (index, flag["code"]))

    # Anotaciones de idioma de USDA al final de un nombre: advertencia.
    names = [("displayName.value", record["displayName"]["value"])] if record.get("displayName") else []
    names += [("commonNames[%d].text" % i, item["text"]) for i, item in enumerate(record["commonNames"])]
    for path, text in names:
        if isinstance(text, str) and LANGUAGE_NOTE_RE.search(text):
            warnings.append("%s: el nombre '%s' conserva una anotación de idioma de USDA" % (path, text))

    # Palabras de dosis o eficacia: advertencia.
    for path, text in _visible_texts(record, sensitive["prefix"]):
        for found in dict.fromkeys(match.group(0) for match in DOSE_RE.finditer(text)):
            warnings.append("%s: expresión de dosis o eficacia '%s'" % (path, found))
    return errors, warnings


def validate_directory(records_dir, bundles_dir, schema=None, goals_map=None, catalog=None):
    """Valida todos los registros de un directorio. Devuelve el informe (dict)."""
    schema = schema or load_schema()
    goals_map = goals_map or goals_lib.load_goals_map()
    catalog = catalog or goals_lib.load_goals_catalog()
    problems = goals_lib.check_map_against_catalog(goals_map, catalog)
    if problems:
        raise SourceError("el mapa de objetivos no concuerda con el catálogo: " + "; ".join(problems))
    index = BundleIndex(bundles_dir)
    report = {"plants": {}, "global": list(index.errors)}
    for path in sorted(Path(records_dir).glob("*.json")):
        key = path.stem
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except ValueError as error:
            report["plants"][key] = {"errors": ["JSON inválido: %s" % error], "warnings": []}
            continue
        plant = record.get("id") if isinstance(record, dict) else None
        errors, warnings = validate_record(record, index.by_id.get(plant), schema, goals_map, catalog)
        if plant is not None and plant != key:
            errors.append("el archivo %s no se llama como el id '%s'" % (path.name, plant))
        report["plants"][key] = {"errors": errors, "warnings": warnings}
    plants = report["plants"].values()
    report["summary"] = {
        "records": len(report["plants"]),
        "recordsWithErrors": sum(1 for p in plants if p["errors"]),
        "errors": sum(len(p["errors"]) for p in plants) + len(report["global"]),
        "warnings": sum(len(p["warnings"]) for p in plants),
    }
    return report
