"""Mapa de seguridad versionado (safety-map.json) y las funciones que lo aplican a las filas extraídas.

El mapa decide el nivel mínimo de seguridad (bajo, medio, alto) que cada fuente fija para una planta; el nivel final de un
registro es el más alto entre las fuentes, y una planta sin datos de seguridad lleva `safety` nulo con un reviewFlag (nunca
se presenta como segura). Cada categoría presente en los datos está cubierta con un nivel o declarada explícitamente sin
nivel (`level: null`) con su motivo, y las pruebas lo verifican con los datos reales.

- TPPT: Human_toxicity, separado por «, » y comparado por el prefijo anterior al paréntesis (sin mayúsculas).
- EMA: la sección 4.5 de la monografía se clasifica con reglas de texto explícitas (patrones de interacción grave).
- EFSA: «sustancia de preocupación» según la lista versionada `efsa.concern_list` del mapa; el resto de las sustancias es evidencia sin nivel.
- USDA: las señales de riesgo de los usos (sección `usda` del mapa, versión 3) se comparan por su forma base; las letales (Fatality, Fatal, Death, Suicide, Homicide) fijan el nivel alto y las demás no fijan nivel.
"""
import json
import re

from .sources import TOOL_DIR

DEFAULT_SAFETY_MAP = TOOL_DIR / "safety-map.json"
LEVELS = ("bajo", "medio", "alto")
SEPARATOR = ", "


class SafetyMapError(Exception):
    """El mapa de seguridad es inválido."""


def level_rank(level):
    return LEVELS.index(level) if level in LEVELS else -1


def max_level(levels):
    """El nivel más alto de una colección (ignora None); None si no hay ninguno."""
    ranked = [lv for lv in levels if lv in LEVELS]
    return max(ranked, key=level_rank) if ranked else None


def _check_entry(where, entry):
    if not isinstance(entry, dict) or "level" not in entry or not isinstance(entry.get("why"), str) or not entry["why"].strip():
        raise SafetyMapError("%s: cada categoría necesita 'level' (bajo, medio, alto o null) y 'why'" % where)
    if entry["level"] is not None and entry["level"] not in LEVELS:
        raise SafetyMapError("%s: nivel inválido %r" % (where, entry["level"]))


def load_safety_map(path=DEFAULT_SAFETY_MAP):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise SafetyMapError("no existe el mapa de seguridad %s" % path)
    except ValueError as error:
        raise SafetyMapError("JSON inválido en %s: %s" % (path, error))
    if not isinstance(data.get("version"), int):
        raise SafetyMapError("el mapa necesita 'version' entera")
    for section in ("tppt", "ema", "efsa", "usda"):
        if not isinstance(data.get(section), dict):
            raise SafetyMapError("falta la sección '%s'" % section)
    for field in ("human_toxicity", "animal_toxicity"):
        for name, entry in data["tppt"][field].items():
            _check_entry("tppt.%s.%s" % (field, name), entry)
            if name != name.lower() or "(" in name:
                raise SafetyMapError("tppt.%s: la clave %r debe estar en minúsculas y sin paréntesis" % (field, name))
    for name, entry in data["ema"]["classes"].items():
        _check_entry("ema.classes.%s" % name, entry)
    for table in ("classes", "result_types", "study_categories", "endpoint_effects"):
        for name, entry in data["efsa"][table].items():
            _check_entry("efsa.%s.%s" % (table, name), entry)
    for name in ("substance-of-concern", "evidence-only", "no-substance"):
        if name not in data["efsa"]["classes"]:
            raise SafetyMapError("efsa.classes: falta la clase %r" % name)
    signals = data["usda"].get("risk_signals")
    if not isinstance(signals, dict) or not signals:
        raise SafetyMapError("usda.risk_signals: necesita al menos una señal")
    for name, entry in signals.items():
        _check_entry("usda.risk_signals.%s" % name, entry)
        if name != name.strip().lower() or "(" in name:
            raise SafetyMapError("usda.risk_signals: la clave %r debe estar en minúsculas y sin paréntesis" % name)
    _check_concern_list(data["efsa"].get("concern_list"))
    for index, group in enumerate(data["efsa"].get("evidence_only", [])):
        names = group.get("substances") if isinstance(group, dict) else None
        if not names or not all(isinstance(n, str) and n.strip() for n in names) or not isinstance(group.get("why"), str) or not group["why"].strip():
            raise SafetyMapError("efsa.evidence_only[%d]: necesita 'substances' (lista de nombres) y 'why'" % index)
    return data


def substance_key(name):
    """Clave de comparación de un nombre de sustancia: sin mayúsculas, con espacios (también duros) colapsados."""
    return " ".join(str(name).split()).casefold()


def _check_concern_list(concern):
    if not isinstance(concern, dict) or not isinstance(concern.get("version"), int):
        raise SafetyMapError("efsa.concern_list: necesita 'version' entera")
    groups = concern.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise SafetyMapError("efsa.concern_list.groups: necesita al menos un grupo")
    for group, entry in groups.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("why"), str) or not entry["why"].strip():
            raise SafetyMapError("efsa.concern_list.groups.%s: necesita 'why'" % group)
    substances = concern.get("substances")
    if not isinstance(substances, list) or not substances:
        raise SafetyMapError("efsa.concern_list.substances: debe ser una lista no vacía")
    seen = set()
    for index, entry in enumerate(substances):
        where = "efsa.concern_list.substances[%d]" % index
        if not isinstance(entry, dict) or not isinstance(entry.get("substance"), str) or not entry["substance"].strip():
            raise SafetyMapError("%s: necesita 'substance' (nombre exacto del compendio)" % where)
        if entry.get("group") not in groups:
            raise SafetyMapError("%s: el grupo %r no existe en 'groups'" % (where, entry.get("group")))
        if "why" in entry and (not isinstance(entry["why"], str) or not entry["why"].strip()):
            raise SafetyMapError("%s: 'why' debe ser un texto no vacío" % where)
        key = substance_key(entry["substance"])
        if key in seen:
            raise SafetyMapError("%s: sustancia repetida %r" % (where, entry["substance"]))
        seen.add(key)


# --- TPPT ---------------------------------------------------------------

def tppt_categories(value):
    """Categorías de Human_toxicity o Animal_toxicity: separa por «, » y toma el prefijo anterior al paréntesis, en minúsculas.

    «strong toxic (only wild growing plants)» → «strong toxic»; «allergenic, skin-irritating» → dos categorías. Los calificadores
    entre paréntesis pueden llevar comas («strong toxic (cow, pig)»): se quitan antes de separar.
    """
    if not isinstance(value, str):
        return []
    text = re.sub(r"\([^)]*\)", "", value)
    return [part.strip().lower() for part in text.split(SEPARATOR) if part.strip()]


def tppt_level(safety_map, human_toxicity, field="human_toxicity"):
    """Clasifica un valor de TPPT. Devuelve {level, categories: [{category, level, covered}], uncovered: [categoría]}."""
    table = safety_map["tppt"][field]
    categories, uncovered = [], []
    for category in tppt_categories(human_toxicity):
        entry = table.get(category)
        if entry is None:
            uncovered.append(category)
        categories.append({"category": category, "level": entry["level"] if entry else None, "covered": entry is not None})
    return {"level": max_level(c["level"] for c in categories), "categories": categories, "uncovered": uncovered}


# --- EMA ----------------------------------------------------------------

LABEL = re.compile(r"\[(well_established_use|traditional_use|both_columns|single_column)\]\s*")


def ema_columns(section):
    """Textos por columna de una sección extraída: {etiqueta: texto}. Acepta el dict de la sección o su texto rotulado."""
    if isinstance(section, dict) and isinstance(section.get("columns"), dict):
        return dict(section["columns"])
    text = section.get("text", "") if isinstance(section, dict) else str(section or "")
    parts = LABEL.split(text)
    if len(parts) == 1:
        return {"single_column": text.strip()} if text.strip() else {}
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def _ema_text_class(config, text):
    """Clase de un texto de la 4.5 (una columna): severe, none-reported, no-studies o interactions."""
    plain = " ".join(text.split())
    if any(re.search(p["regex"], plain, re.IGNORECASE) for p in config["severe_patterns"]):
        return "severe"
    stripped = re.sub(r"Indications?\s+\d+\)(?:\s*(?:,|and)\s*\d+\))*", " ", plain, flags=re.IGNORECASE).strip(" .:;")
    if re.fullmatch(r"(?:(?:%s)[ .;:]*)+" % config["none_reported_regex"], stripped, re.IGNORECASE):
        return "none-reported"
    if re.fullmatch(r"(?:(?:%s)[ .;:]*)+" % config["no_studies_regex"], stripped, re.IGNORECASE):
        return "no-studies"
    return "interactions"


EMA_CLASS_ORDER = ("severe", "interactions", "no-studies", "none-reported")


def ema_interaction_class(safety_map, section):
    """Clasifica la sección 4.5 de una ficha. section: dict de la extracción (o None si no hay 4.5).

    Devuelve {class, level, columns: {columna: clase}, matched: [id de patrón]}. La clase de la ficha es la más grave de sus columnas.
    """
    config = safety_map["ema"]
    classes = safety_map["ema"]["classes"]
    if not section or not ema_columns(section):
        return {"class": "no-section", "level": classes["no-section"]["level"], "columns": {}, "matched": []}
    per_column = {c: _ema_text_class(config, t) for c, t in ema_columns(section).items()}
    chosen = min(per_column.values(), key=EMA_CLASS_ORDER.index)
    plain = " ".join(" ".join(ema_columns(section).values()).split())
    matched = [p["id"] for p in config["severe_patterns"] if re.search(p["regex"], plain, re.IGNORECASE)]
    return {"class": chosen, "level": classes[chosen]["level"], "columns": per_column, "matched": matched}


# --- EFSA ---------------------------------------------------------------

def efsa_concern(safety_map, botanic_contents):
    """Sustancias de una planta según la lista de alta preocupación (efsa.concern_list).

    botanic_contents: contenidos de efsa_botanic. Una fila cuenta si tiene sustancia y su tipo de resultado no está excluido.
    Devuelve {level, concern_substances: [las de la lista que activaron el nivel, con su grupo en concern_groups], evidence_substances:
    [las demás, solo evidencia], substances: todas las que cuentan, rows_counted, rows_excluded}.
    """
    config = safety_map["efsa"]
    excluded_types = set(config["definition"]["exclude_result_types"])
    by_key = {substance_key(e["substance"]): e for e in config["concern_list"]["substances"]}
    counted, excluded = [], 0
    for row in botanic_contents:
        if not row.get("substance_name") or row.get("result_type") in excluded_types:
            excluded += 1
            continue
        counted.append(row["substance_name"])
    concern = sorted({n for n in counted if substance_key(n) in by_key})
    evidence = sorted({n for n in counted if substance_key(n) not in by_key})
    level = config["classes"]["substance-of-concern"]["level"] if concern else None
    return {"level": level, "concern_substances": concern, "concern_groups": sorted({by_key[substance_key(n)]["group"] for n in concern}),
            "evidence_substances": evidence, "substances": sorted(set(counted)), "rows_counted": len(counted), "rows_excluded": excluded}


def efsa_effect_group(value):
    """Grupo de un efecto de ENDPOINTSTUDY (TOXICITYSUMMARY): la parte anterior a «:» («digestive: Liver» → «digestive»)."""
    return (value or "").split(":")[0].strip().lower()


# --- USDA ---------------------------------------------------------------

def usda_signal_base(activity):
    """Forma base de una actividad de USDA: el texto anterior al primer paréntesis, sin espacios sobrantes y en minúsculas."""
    return str(activity or "").split("(")[0].strip().lower()


def usda_signal(safety_map, activity):
    """La entrada del mapa (`{level, why}`) de una actividad que es señal de riesgo, o None si no lo es."""
    return safety_map["usda"]["risk_signals"].get(usda_signal_base(activity))


def usda_signal_level(safety_map, activity):
    """Nivel que fija una actividad de USDA (alto para las señales letales), o None."""
    entry = usda_signal(safety_map, activity)
    return entry["level"] if entry else None


def combine(*levels):
    return max_level(levels)
