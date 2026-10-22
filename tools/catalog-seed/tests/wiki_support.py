"""Soporte de las pruebas de Wikidata, Wikipedia y Commons: un WCVP mínimo con los homónimos del piloto y un universo pequeño."""
import csv
import os
import shutil
import tempfile

import support  # noqa: F401
from catalog_seed.taxonomy import build_index, open_backbone

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "taxonomy")
HEADER = ("plant_name_id|ipni_id|taxon_rank|taxon_status|family|genus_hybrid|genus|species_hybrid|species|infraspecific_rank|"
          "infraspecies|parenthetical_author|primary_author|publication_author|place_of_publication|volume_and_page|first_published|"
          "nomenclatural_remarks|geographic_area|lifeform_description|climate_description|taxon_name|taxon_authors|"
          "accepted_plant_name_id|basionym_plant_name_id|replaced_synonym_author|homotypic_synonym|parent_plant_name_id|powo_id|"
          "hybrid_formula|reviewed").split("|")

# (id, ipni, familia, género, especie, autor, estado, aceptado, homotípico)
NAMES = [
    (1, "449008-1", "Lamiaceae", "Lavandula", "angustifolia", "Mill.", "Accepted", 1, ""),
    (2, "449051-1", "Lamiaceae", "Lavandula", "latifolia", "Medik.", "Accepted", 2, ""),
    (3, "449100-1", "Lamiaceae", "Lavandula", "officinalis", "Chaix", "Synonym", 1, "T"),
    (4, "449101-1", "Lamiaceae", "Lavandula", "vera", "DC.", "Synonym", 1, ""),
    (5, "675096-1", "Passifloraceae", "Passiflora", "incarnata", "L.", "Accepted", 5, ""),
    (6, "321964-2", "Passifloraceae", "Passiflora", "edulis", "Sims", "Accepted", 6, ""),
    (10, "1-1", "Acanthaceae", "Justicia", "adhatoda", "L.", "Accepted", 10, ""),
    (11, "2-1", "Acanthaceae", "Adhatoda", "vasica", "Nees", "Synonym", 10, ""),
    (12, "3-1", "Acanthaceae", "Adhatoda", "zeylanica", "Medik.", "Synonym", 10, ""),
    (13, "4-1", "Acanthaceae", "Gendarussa", "adhatoda", "Nees", "Synonym", 10, "T"),
]

_state = {}


def write_wcvp(path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
        writer.writerow(HEADER)
        for id_, ipni, family, genus, species, author, status, accepted, homotypic in NAMES:
            row = dict.fromkeys(HEADER, "")
            row.update(plant_name_id=id_, ipni_id=ipni, taxon_rank="Species", taxon_status=status, family=family, genus=genus,
                       species=species, taxon_name="%s %s" % (genus, species), taxon_authors=author,
                       accepted_plant_name_id=accepted, homotypic_synonym=homotypic)
            writer.writerow([row[name] for name in HEADER])


def backbones():
    """(wcvp, wfo) de un índice temporal con los nombres de NAMES (y el WFO recortado del resolvedor)."""
    if "wcvp" not in _state:
        import atexit
        tmp = tempfile.mkdtemp(prefix="wiki-index-")
        atexit.register(shutil.rmtree, tmp, True)
        names = os.path.join(tmp, "wcvp_names.csv")
        write_wcvp(names)
        path = os.path.join(tmp, "taxonomy.db")
        build_index(path, names, os.path.join(FIXTURES, "wcvp_distribution.csv"), os.path.join(FIXTURES, "wfo_classification.csv"),
                    "fixture", "fixture")
        _state["path"] = path
        _state["wcvp"] = open_backbone(path, "wcvp")
        _state["wfo"] = open_backbone(path, "wfo")
    return _state["wcvp"], _state["wfo"]


def index_path():
    backbones()
    return _state["path"]


def plant(id_, name, accepted_id, matched_id=None, kind="resolved", entries=None):
    return {"id": id_, "name": name, "author": "", "kind": kind, "backbone": "wcvp", "acceptedId": str(accepted_id),
            "matchedId": str(matched_id) if matched_id else None, "family": None,
            "entries": [{"source": "usda", "key": "usda:%s" % id_, "name": n, "author": "", "outcome": "accepted",
                         "matchedName": n, "relation": "aceptado"} for n in (entries or [name])],
            "aliases": [], "flags": [], "reviewFlags": [], "collision": None}


def universe():
    """Lavanda y pasiflora (con sus homónimos fuera o dentro del universo) y un grupo partido (Justicia adhatoda)."""
    plants = [
        plant("lavandula-angustifolia", "Lavandula angustifolia", 1),
        plant("lavandula-latifolia", "Lavandula latifolia", 2),
        plant("passiflora-incarnata", "Passiflora incarnata", 5),
        plant("justicia-adhatoda", "Justicia adhatoda", 10),
        plant("adhatoda-vasica", "Adhatoda vasica", 10, matched_id=11, kind="heterotypic"),
        {"id": "genero-suelto", "name": "Salvia", "author": "", "kind": "genus_only", "backbone": None, "acceptedId": None,
         "matchedId": None, "family": None, "entries": [], "aliases": [], "flags": [], "reviewFlags": [], "collision": None},
    ]
    return {"format": "catalog-universe/1", "inputs": {"wcvp": "fixture"}, "plantCount": len(plants), "plants": plants}


def item(qid, taxon, authors=None, **fields):
    data = {"qid": qid, "taxon": taxon, "authors": authors or [], "labelEs": "", "aliasesEs": [], "spanishNames": [],
            "images": [], "eswiki": "", "gbif": [], "powo": [], "ipni": []}
    data.update(fields)
    return data


def commons_response(title, **meta):
    """Respuesta de la caché de Commons con los extmetadata dados (clave: valor)."""
    return {"title": title, "imageinfo": {
        "url": "https://upload.example/" + title.split(":", 1)[1].replace(" ", "_")
        + "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
        "descriptionurl": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"), "mime": "image/jpeg", "width": 800,
        "height": 600, "extmetadata": {k: {"value": v} for k, v in meta.items()}}}
