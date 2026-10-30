"""Extracción de TPPT (Agroscope): toxicidad humana y animal con toxinas, desde el SQLite del ZIP verificado.

Una fila tppt_plant por planta de Toxic_plant_species (row_key = Plant_number, raw_name_cell = Latin_plant_name),
con sus toxinas: todas las «major toxin» y hasta 15 más, ordenadas por la importancia de la composición, y n_toxins
con el total de relaciones planta-sustancia. Enlaces de las tablas auxiliares:
- Toxicity_data por Phytotoxin_number de cada toxina elegida (dosis en animales de prueba).
- Remarks por Plant_genus (comentario del género, con su puntuación de conocimiento científico).
- Bibliography por Abbreviation, con las abreviaturas citadas en Data_source de esas dosis (separadas por «, » entre paréntesis).
El ZIP es un archivo no confiable: se extrae a un directorio temporal nuevo y solo se abre como SQLite de solo lectura.
"""
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from .workdb import Row

MAX_EXTRA_TOXINS = 15
DB_NAME = "tppt-db.db"
# Composiciones que cuentan como «major toxin» (la fuente escribe varias formas).
MAJOR_COMPOSITIONS = ("major toxin", "major known toxin", "major toxin and aglycone", "major toxin and metabolite")
# Orden de importancia del resto: lo más seguro primero; lo desconocido al final.
COMPOSITION_RANK = (
    "single toxin", "single toxin known", "toxin", "toxin and aglycone", "toxin and metabolite", "metabolite and toxin",
    "toxin in toxin mixture", "probable major toxin", "possible major toxin", "possible major toxin (chemotyp dependence)",
    "minor toxin", "possible toxin", "possible toxin in toxin mixture", "possible toxin and metabolite",
    "possible minor toxin", "probable minor toxin",
)
CITATION_SPLIT = re.compile(r"(?<=\)),\s*")


def composition_rank(composition):
    if composition in MAJOR_COMPOSITIONS:
        return -1
    return COMPOSITION_RANK.index(composition) if composition in COMPOSITION_RANK else len(COMPOSITION_RANK)


def split_citations(value):
    """Abreviaturas de Bibliography en un Data_source: «A (2010), B et al. (2012)» → dos."""
    return [part.strip() for part in CITATION_SPLIT.split(value or "") if part.strip()]


def open_database(zip_path, directory):
    with zipfile.ZipFile(str(zip_path)) as archive:
        name = next((n for n in archive.namelist() if n == DB_NAME), None)
        if name is None:
            raise ValueError("el ZIP de TPPT no contiene %s" % DB_NAME)
        target = Path(directory) / DB_NAME
        target.write_bytes(archive.read(name))
    connection = sqlite3.connect("file:%s?mode=ro" % target, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _clean(value):
    return value.strip() if isinstance(value, str) else value


def build_rows(connection):
    """Genera las filas tppt_plant desde una conexión al SQLite de TPPT. Devuelve (filas, estadísticas)."""
    phytotoxins = {r["Phytotoxin_number"]: r for r in connection.execute("SELECT * FROM Phytotoxins")}
    toxicity = {}
    for r in connection.execute("SELECT * FROM Toxicity_data ORDER BY Number"):
        toxicity.setdefault(r["Phytotoxin_number"], []).append(
            {"animal": _clean(r["Test_animal"]), "route": _clean(r["Exposure_route"]), "dose": _clean(r["Dose"]),
             "source": _clean(r["Data_source"])})
    remarks = {_clean(r["Plant_genus"]): r for r in connection.execute("SELECT * FROM Remarks")}
    bibliography = {r["Abbreviation"]: r["Literature_reference"] for r in connection.execute("SELECT * FROM Bibliography")}
    relations = {}
    for r in connection.execute("SELECT * FROM Phytotoxin_toxic_plant_species_relationships ORDER BY Number"):
        relations.setdefault(r["Plant_number"], []).append(r)

    rows, stats = [], {"plants": 0, "plants_with_toxins": 0, "plants_with_remarks": 0, "toxins_without_phytotoxin_row": 0,
                       "citations_without_bibliography": 0}
    for plant in connection.execute("SELECT * FROM Toxic_plant_species ORDER BY rowid"):
        number = plant["Plant_number"]
        related = relations.get(number, [])
        ranked = sorted(related, key=lambda r: (composition_rank(r["Composition"]), r["Number"]))
        majors = [r for r in ranked if r["Composition"] in MAJOR_COMPOSITIONS]
        others = [r for r in ranked if r["Composition"] not in MAJOR_COMPOSITIONS][:MAX_EXTRA_TOXINS]
        toxins, cited = [], []
        for r in majors + others:
            phytotoxin = phytotoxins.get(r["Phytotoxin_number"])
            if phytotoxin is None:
                stats["toxins_without_phytotoxin_row"] += 1
            doses = toxicity.get(r["Phytotoxin_number"], [])
            for dose in doses:
                for abbreviation in split_citations(dose["source"]):
                    if abbreviation not in cited:
                        cited.append(abbreviation)
            toxins.append({
                "number": r["Phytotoxin_number"], "name": _clean(r["Phytotoxin_name"]), "composition": r["Composition"],
                "major": r["Composition"] in MAJOR_COMPOSITIONS,
                "psm_class": _clean(phytotoxin["PSM_class"]) if phytotoxin else None,
                "casrn": _clean(phytotoxin["CASRN"]) if phytotoxin else None,
                "toxicity_data": doses})
        genus = _clean(plant["Plant_genus"])
        remark = remarks.get(genus)
        content = {
            "plant_number": number, "latin_name": _clean(plant["Latin_plant_name"]), "german_name": _clean(plant["German_plant_name"]),
            "english_name": _clean(plant["English_plant_name"]), "genus": genus, "family": _clean(plant["Plant_family"]),
            "toxic_part": _clean(plant["Toxic_plant_part"]), "human_toxicity": _clean(plant["Human_toxicity"]),
            "animal_toxicity": _clean(plant["Animal_toxicity"]), "swiss_frequency": _clean(plant["Swiss_frequency"]),
            "n_toxins": len(related), "toxins": toxins,
            "remarks": {"comment": _clean(remark["Comment"]), "knowledge_score": remark["Scientific-knowledge_availability_score"]} if remark else None,
            "bibliography": {a: bibliography[a] for a in cited if a in bibliography},
        }
        stats["citations_without_bibliography"] += sum(1 for a in cited if a not in bibliography)
        rows.append(Row("tppt_plant", number, content, raw_name_cell=plant["Latin_plant_name"]))
        stats["plants"] += 1
        stats["plants_with_toxins"] += 1 if related else 0
        stats["plants_with_remarks"] += 1 if remark else 0
    return rows, stats


def extract(zip_path):
    with tempfile.TemporaryDirectory() as directory:
        connection = open_database(zip_path, directory)
        try:
            return build_rows(connection)
        finally:
            connection.close()
