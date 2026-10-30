"""Soporte de las pruebas de la regla de colisiones: un WCVP mínimo con los grupos de los escenarios de la spec.

Canela (*Cinnamomum zeylanicum* heterotípico de *C. verum*), *Thevetia peruviana* (heterotípico de *Cascabela thevetia*, con su
basiónimo *Cerbera peruviana* como homotípico propio) y el hinojo dulce (*Foeniculum vulgare* var. *dulce*). La bergamota usa el
índice del resolvedor (`taxonomy_support`).
"""
import atexit
import csv
import os
import shutil
import tempfile

import support  # noqa: F401
from catalog_seed.taxonomy import build_index, open_backbone
from catalog_seed.taxonomy.collisions import DECISIONS_FORMAT, EXCEPTIONS_FORMAT, CollisionRules

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "taxonomy")
HEADER = ("plant_name_id|ipni_id|taxon_rank|taxon_status|family|genus_hybrid|genus|species_hybrid|species|infraspecific_rank|"
          "infraspecies|parenthetical_author|primary_author|publication_author|place_of_publication|volume_and_page|first_published|"
          "nomenclatural_remarks|geographic_area|lifeform_description|climate_description|taxon_name|taxon_authors|"
          "accepted_plant_name_id|basionym_plant_name_id|replaced_synonym_author|homotypic_synonym|parent_plant_name_id|powo_id|"
          "hybrid_formula|reviewed").split("|")

# (id, familia, nombre, autor, estado, aceptado, basiónimo, homotípico)
NAMES = [
    (9001, "Lauraceae", "Cinnamomum verum", "J.Presl", "Accepted", 9001, "", ""),
    (9002, "Lauraceae", "Cinnamomum zeylanicum", "Blume", "Synonym", 9001, "", ""),
    (9003, "Lauraceae", "Cinnamomum aromaticum", "Nees", "Synonym", 9001, "", ""),
    (9010, "Apocynaceae", "Cascabela thevetia", "(L.) Lippold", "Accepted", 9010, 9011, ""),
    (9011, "Apocynaceae", "Cerbera thevetia", "L.", "Synonym", 9010, "", "T"),
    (9012, "Apocynaceae", "Thevetia peruviana", "(Pers.) K.Schum.", "Synonym", 9010, 9013, ""),
    (9013, "Apocynaceae", "Cerbera peruviana", "Pers.", "Synonym", 9010, "", ""),
    (9020, "Apiaceae", "Foeniculum vulgare", "Mill.", "Accepted", 9020, "", ""),
    (9021, "Apiaceae", "Foeniculum vulgare var. dulce", "(Mill.) Batt. & Trab.", "Synonym", 9020, 9022, ""),
    (9022, "Apiaceae", "Foeniculum dulce", "Mill.", "Synonym", 9020, "", ""),
]

_state = {}


def write_wcvp(path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
        writer.writerow(HEADER)
        for id_, family, name, author, status, accepted, basionym, homotypic in NAMES:
            parts = name.split()
            row = dict.fromkeys(HEADER, "")
            row.update(plant_name_id=id_, ipni_id="%d-1" % id_, taxon_rank="Variety" if len(parts) > 2 else "Species",
                       taxon_status=status, family=family, genus=parts[0], species=parts[1], taxon_name=name, taxon_authors=author,
                       accepted_plant_name_id=accepted, basionym_plant_name_id=basionym, homotypic_synonym=homotypic)
            if len(parts) > 2:
                row.update(infraspecific_rank=parts[2], infraspecies=parts[3])
            writer.writerow([row[name] for name in HEADER])


def build_collision_index(path):
    tmp = os.path.dirname(path)
    names = os.path.join(tmp, "wcvp_names.csv")
    write_wcvp(names)
    build_index(path, names, os.path.join(FIXTURES, "wcvp_distribution.csv"), os.path.join(FIXTURES, "wfo_classification.csv"),
                "fixture", "fixture")


def index_path():
    if "path" not in _state:
        tmp = tempfile.mkdtemp(prefix="collision-index-")
        atexit.register(shutil.rmtree, tmp, True)
        _state["path"] = os.path.join(tmp, "taxonomy.db")
        build_collision_index(_state["path"])
    return _state["path"]


def backbones():
    if "wcvp" not in _state:
        path = index_path()
        _state["wcvp"] = open_backbone(path, "wcvp")
        _state["wfo"] = open_backbone(path, "wfo")
    return _state["wcvp"], _state["wfo"]


def decisions_document(uni, choices):
    """Documento de decisiones a partir de un universo armado sin reglas: `choices` = {nombre del miembro: (decisión, motivo)}."""
    groups = {}
    for record in uni.collisions:
        if record["name"] in choices:
            decision, reason = choices[record["name"]]
            group = groups.setdefault(record["accepted_key"], {"accepted": record["accepted"], "members": {}})
            group["members"][record["member"]] = {"name": record["name"], "decision": decision, "reason": reason}
    return {"format": DECISIONS_FORMAT, "groups": groups}


def exceptions_document(*names):
    return {"format": EXCEPTIONS_FORMAT, "exceptions": [{"name": n, "reason": "prueba"} for n in names]}


def rules_for(uni, choices, exceptions=()):
    return CollisionRules(decisions_document(uni, choices), exceptions_document(*exceptions))
