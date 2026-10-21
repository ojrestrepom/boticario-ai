"""Mapa de objetivos (goals-map.json) y catálogo de objetivos de la semilla (data/seed/goals.json)."""
import json

from .sources import REPO_ROOT, TOOL_DIR, SourceError

DEFAULT_GOALS_MAP = TOOL_DIR / "goals-map.json"
DEFAULT_SEED_DIR = REPO_ROOT / "data" / "seed"
DEFAULT_GOALS_CATALOG = DEFAULT_SEED_DIR / "goals.json"


def _load_json(path, what):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise SourceError("no existe %s: %s" % (what, path))
    except ValueError as error:
        raise SourceError("JSON inválido en %s (%s): %s" % (what, path, error))


def load_goals_catalog(path=DEFAULT_GOALS_CATALOG):
    return _load_json(path, "el catálogo de objetivos")


def load_goals_map(path=DEFAULT_GOALS_MAP):
    return _load_json(path, "el mapa de objetivos")


def goal_ids(catalog):
    return [goal["id"] for goal in catalog["goals"]]


def subarea_ids(catalog):
    return [sub["id"] for sub in catalog["subareas"]]


def subareas_of(catalog, goal):
    return [sub["id"] for sub in catalog["subareas"] if sub["goalId"] == goal]


def check_map_against_catalog(goals_map, catalog):
    """Devuelve la lista de problemas (vacía si todo id del mapa existe en el catálogo)."""
    problems = []
    goals = set(goal_ids(catalog))
    subareas = {sub["id"]: sub["goalId"] for sub in catalog["subareas"]}
    for area, entry in goals_map["areas"].items():
        goal, sub = entry["goal"], entry["subarea"]
        if goal not in goals:
            problems.append("área '%s': el objetivo '%s' no existe en el catálogo" % (area, goal))
        if sub is not None and subareas.get(sub) != goal:
            problems.append("área '%s': la subárea '%s' no existe bajo '%s' en el catálogo" % (area, sub, goal))
        if sub is None and goal == "otros-objetivos":
            problems.append("área '%s': 'otros-objetivos' exige subárea" % area)
    return problems


def split_values(text, separator=";"):
    """Separa un campo de la EMA unido por ';' (resultado combinado, varias áreas)."""
    if text is None:
        return []
    return [part.strip() for part in str(text).split(separator) if part.strip()]


def map_area(goals_map, area):
    """(objetivo, subárea, traducción) del área, o None si el mapa no la conoce."""
    entry = goals_map["areas"].get(area)
    if entry is None:
        return None
    return entry["goal"], entry["subarea"], entry["es"]


def map_record_areas(goals_map, record):
    """Asigna cada área de una ficha de la EMA: lista de (área, resultado de map_area).

    Una ficha sin área devuelve [("", (None, None, None))]: el mapa la trata explícitamente.
    """
    areas = split_values(record.get("therapeutic_area"), goals_map.get("separator", ";"))
    if not areas:
        empty = goals_map["emptyArea"]
        return [("", (empty["goal"], empty["subarea"], None))]
    return [(area, map_area(goals_map, area)) for area in areas]


def counted_outcomes(goals_map, outcome):
    """True si el resultado (posiblemente combinado con ';') incluye monografía o entrada de lista."""
    wanted = set(goals_map["countedOutcomes"])
    return any(part in wanted for part in split_values(outcome, goals_map.get("separator", ";")))
