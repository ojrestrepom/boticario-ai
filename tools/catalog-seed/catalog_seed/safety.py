"""Mapa de seguridad versionado (safety-map.json) y las funciones que lo aplican a las filas extraídas.

El mapa decide el nivel mínimo de seguridad (bajo, medio, alto) que cada fuente fija para una planta; el nivel final de un
registro es el más alto entre las fuentes, y una planta sin datos de seguridad lleva `safety` nulo con un reviewFlag (nunca
se presenta como segura). Cada categoría presente en los datos está cubierta con un nivel o declarada explícitamente sin
nivel (`level: null`) con su motivo, y las pruebas lo verifican con los datos reales.

- TPPT: Human_toxicity, separado por «, » y comparado por el prefijo anterior al paréntesis (sin mayúsculas).
- EMA: la sección 4.5 de la monografía se clasifica con reglas de texto explícitas (patrones de interacción grave).
- EFSA: «sustancia de preocupación» según la definición del mapa.
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
    for section in ("tppt", "ema", "efsa"):
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
    return data


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
    """Sustancias de preocupación de una planta: filas de BOTANIC (contenidos de efsa_botanic) que cumplen la definición.

    Devuelve {level, substances: [nombres únicos ordenados], rows_counted, rows_excluded}.
    """
    config = safety_map["efsa"]
    excluded_types = set(config["definition"]["exclude_result_types"])
    counted, excluded = [], 0
    for row in botanic_contents:
        if not row.get("substance_name") or row.get("result_type") in excluded_types:
            excluded += 1
            continue
        counted.append(row["substance_name"])
    level = safety_map["efsa"]["classes"]["substance-of-concern"]["level"] if counted else None
    return {"level": level, "substances": sorted(set(counted)), "rows_counted": len(counted), "rows_excluded": excluded}


def efsa_effect_group(value):
    """Grupo de un efecto de ENDPOINTSTUDY (TOXICITYSUMMARY): la parte anterior a «:» («digestive: Liver» → «digestive»)."""
    return (value or "").split(":")[0].strip().lower()


def combine(*levels):
    return max_level(levels)
