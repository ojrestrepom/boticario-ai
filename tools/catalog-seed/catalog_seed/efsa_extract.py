"""Extracción de EFSA (Compendium of Botanicals 2016): BOTANIC.xls y ENDPOINTSTUDY.xls, con procedencia.

- efsa_botanic: una fila por fila de BOTANIC (sustancia, parte, preparación, valor, unidad, cita).
- efsa_endpoint: una fila por fila de ENDPOINTSTUDY (estudio, especie, vía, efecto, cita).
Ambas guardan scientificNames tal cual en raw_name_cell (con sus separadores «;» o «$»). row_key es el número de fila
de la hoja (la primera fila de datos es la 2), estable en el archivo fijado. Necesita xlrd (requirements.txt).
"""
import io

from .sources import SourceError
from .workdb import Row

NEEDS_XLRD = ("leer los .xls de EFSA necesita xlrd; use el entorno virtual: "
              "tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py ... (véase requirements.txt)")

BOTANIC_FIELDS = (
    ("citation", "CITATION"), ("doctype", "DOCTYPE"), ("year", "PUBLICATION_YEAR"), ("title", "TITLE"), ("plant_name", "PlantName"),
    ("botanical", "BOTANICAL"), ("family", "PlantFamily"), ("part", "PlantPart"), ("preparation", "Preparation"),
    ("product_treatment", "PRODTREAT"), ("substance_name", "SubstanceName"), ("param_text", "PARAMTEXT"), ("substance", "Substance"),
    ("analytical_method", "AnalyticalMethod"), ("expression", "expression_result"), ("value", "RESVAL"), ("unit", "Unit"),
    ("result_type", "ResultType"),
)
ENDPOINT_FIELDS = (
    ("citation", "CITATION"), ("doctype", "DOCTYPE"), ("year", "PUBLICATIONYEAR"), ("title", "TITLE"), ("plant_name", "PlantName"),
    ("botanical", "BOTANICAL"), ("family", "PLANTFAMILY"), ("part", "PLANTPART"), ("study_category", "STUDYCATEGORY"),
    ("param_name", "PARAMNAME"), ("test_substance", "TESTSUBSTANCE"), ("preparation", "PREPARATION"), ("test_type", "TESTTYPE"),
    ("test_species", "TESTSPECIES"), ("sex", "SEX"), ("route", "ROUTE"), ("exposure_duration", "EXPDURATION"),
    ("duration_unit", "DURATIONUNIT"), ("endpoint", "ENDPOINT"), ("individuals", "NUMBERINDIVIDUALS"), ("qualifier", "QUALIFIER"),
    ("value", "VALUE"), ("dose_unit", "DOSEUNIT"), ("observed_effect", "OBSERVEDEFFECT"), ("toxicity", "TOXICITY"),
    ("target_tissue", "TARGETTISSUE"), ("effect_description", "EFFECT_DESC"), ("substance", "SUBSTANCE"),
    ("toxicity_summary", "TOXICITYSUMMARY"),
)


def _value(cell):
    """Texto limpio de una celda de xlrd: floats enteros sin «.0», cadenas sin espacios exteriores; vacío → ausente."""
    if isinstance(cell, float):
        return int(cell) if cell == int(cell) else cell
    text = str(cell).strip()
    return text or None


def read_sheet(path):
    """Filas de la primera hoja como (número de fila, dict por cabecera) con los valores crudos de xlrd."""
    try:
        import xlrd  # dependencia opcional: solo esta fuente la necesita
    except ImportError:
        raise SourceError(NEEDS_XLRD)
    workbook = xlrd.open_workbook(str(path), logfile=io.StringIO())
    sheet = workbook.sheet_by_index(0)
    header = [str(v).strip() for v in sheet.row_values(0)]
    for index in range(1, sheet.nrows):
        yield index + 1, dict(zip(header, sheet.row_values(index)))


def build(path, record_type, fields):
    rows = []
    for number, raw in read_sheet(path):
        names = raw.get("scientificNames")
        content = {key: _value(raw[column]) for key, column in fields if column in raw and _value(raw[column]) is not None}
        rows.append(Row(record_type, number, content, raw_name_cell=names if isinstance(names, str) else str(names)))
    return rows


def extract(botanic_path, endpoint_path):
    botanic = build(botanic_path, "efsa_botanic", BOTANIC_FIELDS)
    endpoint = build(endpoint_path, "efsa_endpoint", ENDPOINT_FIELDS)
    return botanic + endpoint, {"efsa_botanic": len(botanic), "efsa_endpoint": len(endpoint)}
