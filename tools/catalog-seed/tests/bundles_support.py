"""Soporte de las pruebas de los paquetes: un mundo pequeño (WCVP mínimo, universo en memoria, `sources.db` en memoria y cachés de
Wikidata, Wikipedia y Commons) con la lavanda y su homónimo, la pasiflora y la suya, el hipérico, la canela fusionada y la menta."""
import atexit
import copy
import csv
import os
import shutil
import tempfile
import types

import support  # noqa: F401
import wiki_support as ws
from catalog_seed import bundles, safety, workdb
from catalog_seed import goals as goals_lib
from catalog_seed import wiki_assign as wa
from catalog_seed.taxonomy import Entry, build_index, build_universe, open_backbone
from catalog_seed.taxonomy.collisions import CollisionRules
from catalog_seed.wiki import CommonsStep, WikidataStep, WikipediaStep
from catalog_seed.workdb import Row

FIXTURES = ws.FIXTURES
LICENSES = {"usda": "CC0", "wcvp": "CC BY 3.0", "wfo": "CC0", "ema_json": "Reutilización citando a la EMA", "ema_pdf": "Reutilización citando a la EMA",
            "tppt": "Uso abierto citando la fuente", "efsa": "CC BY 4.0", "wikidata": "CC0 1.0", "wikipedia_es": "CC BY-SA 4.0",
            "commons": "por archivo"}

# (id, ipni, familia, género, especie, autor, estado, aceptado, homotípico)
NAMES = [
    (1, "449008-1", "Lamiaceae", "Lavandula", "angustifolia", "Mill.", "Accepted", 1, ""),
    (2, "449051-1", "Lamiaceae", "Lavandula", "latifolia", "Medik.", "Accepted", 2, ""),
    (3, "449100-1", "Lamiaceae", "Lavandula", "officinalis", "Chaix", "Synonym", 1, "T"),
    (5, "675096-1", "Passifloraceae", "Passiflora", "incarnata", "L.", "Accepted", 5, ""),
    (6, "321964-2", "Passifloraceae", "Passiflora", "edulis", "Sims", "Accepted", 6, ""),
    (7, "1-1", "Hypericaceae", "Hypericum", "perforatum", "L.", "Accepted", 7, ""),
    (8, "2-1", "Lauraceae", "Cinnamomum", "verum", "J.Presl", "Accepted", 8, ""),
    (9, "3-1", "Lauraceae", "Cinnamomum", "zeylanicum", "Blume", "Synonym", 8, ""),
    (13, "4-1", "Lamiaceae", "Mentha", "spicata", "L.", "Accepted", 13, ""),
]
# (id de WCVP, continente, región, código, área, introducida)
DISTRIBUTION = [(1, "EUROPE", "Southwestern Europe", "FRA", "France", 0), (1, "EUROPE", "Southwestern Europe", "SPA", "Spain", 0),
                (1, "EUROPE", "Middle Europe", "GER", "Germany", 1), (7, "EUROPE", "Middle Europe", "AUT", "Austria", 0)]

_state = {}


def _write_wcvp(path):
    header = ws.HEADER
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
        writer.writerow(header)
        for id_, ipni, family, genus, species, author, status, accepted, homotypic in NAMES:
            row = dict.fromkeys(header, "")
            row.update(plant_name_id=id_, ipni_id=ipni, taxon_rank="Species", taxon_status=status, family=family, genus=genus, species=species,
                       taxon_name="%s %s" % (genus, species), taxon_authors=author, accepted_plant_name_id=accepted, homotypic_synonym=homotypic)
            writer.writerow([row[name] for name in header])


def _write_distribution(path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
        writer.writerow("plant_locality_id|plant_name_id|continent_code_l1|continent|region_code_l2|region|area_code_l3|area|introduced|extinct|location_doubtful".split("|"))
        for index, (plant, continent, region, code, area, introduced) in enumerate(DISTRIBUTION):
            writer.writerow([index + 1, plant, 1, continent, 10, region, code, area, introduced, 0, 0])


def backbones():
    if "wcvp" not in _state:
        tmp = tempfile.mkdtemp(prefix="bundles-index-")
        atexit.register(shutil.rmtree, tmp, True)
        names, distribution = os.path.join(tmp, "wcvp_names.csv"), os.path.join(tmp, "wcvp_distribution.csv")
        _write_wcvp(names)
        _write_distribution(distribution)
        path = os.path.join(tmp, "taxonomy.db")
        build_index(path, names, distribution, os.path.join(FIXTURES, "wfo_classification.csv"), "fixture", "fixture")
        _state.update(path=path, wcvp=open_backbone(path, "wcvp"), wfo=open_backbone(path, "wfo"))
    return _state["wcvp"], _state["wfo"]


def index_path():
    backbones()
    return _state["path"]


def sources(disabled=()):
    return [types.SimpleNamespace(id=i, license=license, enabled=i not in disabled) for i, license in LICENSES.items()]


def entry(source, key, name, author=""):
    return Entry(source, key, name, author)


ENTRIES = [
    entry("usda", "usda:1", "Lavandula angustifolia", "Mill."), entry("usda", "usda:2", "Lavandula latifolia", "Medik."),
    entry("usda", "usda:5", "Passiflora incarnata", "L."), entry("usda", "usda:7", "Hypericum perforatum", "L."),
    entry("usda", "usda:8", "Cinnamomum verum", "J.Presl"), entry("usda", "usda:9", "Cinnamomum zeylanicum", "Blume"),
    entry("usda", "usda:13", "Mentha spicata", "L."),
    Entry.from_text("ema", "ema:lavandulae-flos#1", "Lavandula angustifolia Mill."),
    Entry.from_text("ema", "ema:hyperici-herba-0#1", "Hypericum perforatum L."),
    Entry.from_text("ema", "ema:hyperici-herba#1", "Hypericum perforatum L."),
    Entry.from_text("ema", "ema:passiflorae-herba#1", "Passiflora incarnata L."),
    Entry.from_text("ema", "ema:cinnamomi-cortex#1", "Cinnamomum verum J.Presl"),
    Entry.from_text("ema", "ema:menthae-spicatae-folium#1", "Mentha spicata L."),
]


def build_universe_in_memory():
    wcvp, wfo = backbones()
    first = build_universe(ENTRIES, wcvp, wfo)
    decisions = {}
    for record in first.collisions:
        if record["name"] == "Cinnamomum zeylanicum":
            decisions[record["accepted_key"]] = {"accepted": record["accepted"], "members": {
                record["member"]: {"name": record["name"], "decision": "fuse", "reason": "redireccion"}}}
    return build_universe(ENTRIES, wcvp, wfo, rules=CollisionRules({"format": "catalog-collision-decisions/1", "groups": decisions}, None))


def usda_rows():
    rows = [
        Row("usda_taxon", "1", {"taxon": "Lavandula angustifolia"}, raw_name_cell="Lavandula angustifolia", fnfnum="1"),
        Row("usda_common_name", "1-1", {"name": "English Lavender", "language": "en"}, raw_name_cell="English Lavender", fnfnum="1"),
        Row("usda_common_name", "2-1", {"name": "Spike lavender", "language": "en"}, raw_name_cell="Spike lavender", fnfnum="2"),
        Row("usda_common_name", "9-1", {"name": "Ceylon cinnamon", "language": "en"}, raw_name_cell="Ceylon cinnamon", fnfnum="9"),
        Row("usda_part", "1-FL", {"ppco": "FL", "ppna": "Flower", "rows": 3, "has_eo": True, "eo_compounds": ["EO"], "distinct_compounds": 3,
                                  "top_amount": [{"compound": "EO", "amount": 4, "unit": None, "eo": True}], "top_eo": []},
            raw_name_cell="Lavandula angustifolia", fnfnum="1"),
        Row("usda_use", "101", {"activity": "Sedative", "taxon": "Lavandula angustifolia", "reference": "Woi.10", "country": "Spain"},
            raw_name_cell="Lavandula angustifolia"),
        Row("usda_use", "102", {"activity": "Sedative", "taxon": "Lavandula angustifolia", "reference": "Burkill,1966", "country": "France"},
            raw_name_cell="Lavandula angustifolia"),
        Row("usda_use", "103", {"activity": "Carminative", "taxon": "Lavandula angustifolia", "reference": "Woi.Syria", "country": "Egypt"},
            raw_name_cell="Lavandula angustifolia"),
        Row("usda_use", "201", {"activity": "Sedative", "taxon": "Lavandula latifolia", "reference": "Woi.10"}, raw_name_cell="Lavandula latifolia"),
        Row("usda_use", "901", {"activity": "Colic", "taxon": "Cinnamomum zeylanicum", "reference": "Burkill,1966", "country": "India"},
            raw_name_cell="Cinnamomum zeylanicum"),
        Row("usda_reference", "Burkill, 1966", {"reference": "Burkill, 1966", "longref": "Burkill, H.M. 1966. The useful plants of West Tropical Africa."},
            raw_name_cell="Burkill, 1966"),
        Row("usda_reference", "WOI", {"reference": "WOI", "longref": "The Wealth of India"}, raw_name_cell="WOI"),
    ]
    return rows


def ema_rows():
    def herbal(slug, cell, areas, outcomes=("European Union herbal monograph",), combination="No", latin=None, rows=None):
        content = {"slug": slug, "botanical_name": cell, "combination": combination, "english_common_name": latin or slug,
                   "latin_name": latin or slug, "outcomes": list(outcomes), "status": "F: Assessment finalised", "therapeutic_areas": list(areas),
                   "url": "https://www.ema.europa.eu/en/medicines/herbal/%s" % slug}
        content["rows"] = rows or [{"botanical_name": cell, "combination": combination, "latin_name": content["latin_name"], "outcomes": list(outcomes),
                                    "status": content["status"], "therapeutic_areas": list(areas)}]
        return Row("ema_herbal", slug, content, raw_name_cell=cell)

    merged_rows = [
        {"botanical_name": "Hypericum perforatum L.", "combination": "Yes", "latin_name": "Hyperici herba;Cimicifugae rhizoma",
         "outcomes": ["European Union herbal monograph"], "status": "F: Assessment finalised", "therapeutic_areas": ["Urinary tract and genital disorders"]},
        {"botanical_name": "Cimicifuga racemosa (L.) Nutt.", "combination": "Yes", "latin_name": "Hyperici herba;Cimicifugae rhizoma",
         "outcomes": ["European Union herbal monograph"], "status": "F: Assessment finalised", "therapeutic_areas": ["Fatigue and weakness"]}]
    return [
        herbal("lavandulae-flos", "Lavandula angustifolia Mill.", ["Sleep disorders and temporary insomnia", "Mental stress and mood disorders"],
               latin="Lavandulae flos"),
        herbal("hyperici-herba-0", "Hypericum perforatum L.", ["Mental stress and mood disorders", "Gastrointestinal disorders"], latin="Hyperici herba"),
        herbal("hyperici-herba", "Hypericum perforatum L.;Cimicifuga racemosa (L.) Nutt.",
               ["Urinary tract and genital disorders", "Fatigue and weakness"], combination="Yes", latin="Hyperici herba;Cimicifugae rhizoma",
               rows=merged_rows),
        herbal("passiflorae-herba", "Passiflora incarnata L.", ["Sleep disorders and temporary insomnia"], outcomes=("Public statement",),
               latin="Passiflorae herba"),
        herbal("cinnamomi-cortex", "Cinnamomum verum J.Presl", ["Gastrointestinal disorders"], latin="Cinnamomi cortex"),
        herbal("menthae-spicatae-folium", "Mentha spicata L.", ["Gastrointestinal disorders", "Cough and cold"],
               outcomes=("European Union herbal monograph", "European Union list entry"), latin="Menthae spicatae folium"),
    ]


SEVERE_TEXT = ("[well_established_use] Concomitant use with coumarin-type anticoagulants and cyclosporine is contraindicated (see section 4.3). "
               "Serotonin syndrome has been reported with antidepressants.")


def ema_pdf_rows():
    def doc(slug, status, sections, kind="monograph-final"):
        return Row("ema_pdf_doc", slug, {"slug": slug, "status": status, "url": "https://www.ema.europa.eu/en/medicines/herbal/%s" % slug,
                                         "documents": [{"filename": "%s.pdf" % slug, "kind": kind, "draft": False, "sections": sections,
                                                        "url": "https://www.ema.europa.eu/en/documents/%s_en.pdf" % slug}]}, raw_name_cell=slug)

    def section(slug, number, text, heading="Section", **extra):
        content = {"slug": slug, "section": number, "heading": heading, "document": "%s.pdf" % slug, "kind": "monograph-final", "draft": False,
                   "page_from": 3, "page_to": 3, "text": text}
        content.update(extra)
        return Row("ema_pdf", "%s:%s" % (slug, number), content, raw_name_cell=slug)

    rows = [doc("hyperici-herba-0", "ok", ["4.3", "4.4", "4.5"]), doc("lavandulae-flos", "ok", ["4.3", "4.4", "4.5"]),
            doc("menthae-spicatae-folium", "ok", ["4.3", "4.5"]), doc("cinnamomi-cortex", "no-descargada", []),
            doc("passiflorae-herba", "declaracion-publica", ["CONCLUSIONS"], kind="public-statement")]
    for number, heading in (("4.3", "Contraindications"), ("4.4", "Special warnings"), ("4.5", "Interactions")):
        rows.append(section("hyperici-herba-0", number, SEVERE_TEXT if number == "4.5" else "Hypersensitivity.", heading))
        rows.append(section("lavandulae-flos", number, "None reported." if number == "4.5" else "Hypersensitivity.", heading))
    rows.append(section("menthae-spicatae-folium", "4.3", "Hypersensitivity.", "Contraindications"))
    rows.append(section("menthae-spicatae-folium", "4.5", "None known.", "Interactions"))
    rows.append(section("passiflorae-herba", "CONCLUSIONS", "Safety concerns were identified.", "CONCLUSIONS", safety_data=True, kind="public-statement"))
    return rows


def tppt_rows():
    return [Row("tppt_plant", "P291", {"latin_name": "Hypericum perforatum L. s.str.", "english_name": "Common St. John's wort",
                                        "german_name": "Echtes Johanniskraut", "family": "Hypericaceae", "human_toxicity": "phototoxic",
                                        "animal_toxicity": "toxic", "toxic_part": "Whole plant", "n_toxins": 1,
                                        "toxins": [{"name": "Hypericin", "major": False, "composition": "toxin in toxin mixture", "psm_class": "Anthracene",
                                                    "casrn": "548-04-9", "number": "T779", "toxicity_data": [{"dose": "53"}]}],
                                        "remarks": {"comment": "Photosensitive anthracene derivatives are toxic."}},
                raw_name_cell="Hypericum perforatum L. s.str."),
            Row("tppt_plant", "P5", {"latin_name": "Passiflora incarnata L.", "english_name": "Passionflower", "german_name": "", "family": "Passifloraceae",
                                     "human_toxicity": "nontoxic", "animal_toxicity": "", "toxic_part": "", "n_toxins": 0, "toxins": [], "remarks": None},
                raw_name_cell="Passiflora incarnata L.")]


def efsa_rows():
    def botanic(key, cell, substance, part="Flower", result_type="Quantified Value"):
        return Row("efsa_botanic", key, {"substance_name": substance, "part": part, "result_type": result_type, "plant_name": "Lavender"},
                   raw_name_cell=cell)

    cell = "Lavandula angustifolia Mill.; Lavandula officinalis Chaix"
    return [botanic("1", cell, "alpha-thujone"), botanic("2", cell, "1,8-cineole"), botanic("3", cell, "beta-thujone", result_type="Non Detected Value (<LOD)"),
            botanic("4", "Lavandula latifolia Medik.", "Camphor"),
            Row("efsa_endpoint", "7", {"study_category": "Human health", "test_species": "Human", "route": "oral", "test_type": "x",
                                        "toxicity_summary": "digestive: Liver", "effect_description": "Efecto", "part": "Flower", "plant_name": "Lavender",
                                        "title": "Estudio", "year": 2001}, raw_name_cell=cell)]


def wikimedia_rows():
    return [
        Row("wikidata", "Q42081", {"qid": "Q42081", "taxon": "Lavandula angustifolia", "authors": ["Mill."], "labelEs": "lavanda", "aliasesEs": [],
                                   "spanishNames": ["espliego"], "eswiki": "Lavandula angustifolia", "images": [], "gbif": [], "ipni": ["449008-1"], "powo": []},
            raw_name_cell="Lavandula angustifolia", qid="Q42081"),
        Row("wikidata", "Q905916", {"qid": "Q905916", "taxon": "Lavandula latifolia", "authors": ["Medik."], "labelEs": "alhucema", "aliasesEs": [],
                                    "spanishNames": ["alhucema"], "eswiki": "", "images": [], "gbif": [], "ipni": [], "powo": []},
            raw_name_cell="Lavandula latifolia", qid="Q905916"),
        Row("wikidata", "Q128939", {"qid": "Q128939", "taxon": "Passiflora incarnata", "authors": ["L."], "labelEs": "pasionaria", "aliasesEs": [],
                                    "spanishNames": [], "eswiki": "Passiflora incarnata", "images": [], "gbif": [], "ipni": [], "powo": []},
            raw_name_cell="Passiflora incarnata", qid="Q128939"),
        Row("wikidata", "Q156790", {"qid": "Q156790", "taxon": "Passiflora edulis", "authors": ["Sims"], "labelEs": "maracuyá", "aliasesEs": [],
                                    "spanishNames": ["maracuyá"], "eswiki": "Passiflora edulis", "images": [], "gbif": [], "ipni": [], "powo": []},
            raw_name_cell="Passiflora edulis", qid="Q156790"),
        Row("wikidata", "Q158289", {"qid": "Q158289", "taxon": "Hypericum perforatum", "authors": ["L."], "labelEs": "hipérico", "aliasesEs": [],
                                    "spanishNames": ["hierba de San Juan"], "eswiki": "Hypericum perforatum", "images": [], "gbif": [], "ipni": [], "powo": []},
            raw_name_cell="Hypericum perforatum", qid="Q158289"),
        Row("wikipedia_es", "Lavandula angustifolia", {"title": "Lavandula angustifolia", "description": "especie de planta",
                                                       "extract": "La lavanda es una planta.", "url": "https://es.wikipedia.org/wiki/Lavandula_angustifolia",
                                                       "revision": "1", "timestamp": "2026-01-01T00:00:00Z"}, raw_name_cell="Lavandula angustifolia"),
        Row("wikipedia_es", "Passiflora incarnata", {"title": "Passiflora incarnata", "description": "especie de planta", "extract": "La pasiflora es una planta.",
                                                     "url": "https://es.wikipedia.org/wiki/Passiflora_incarnata", "revision": "2", "timestamp": "2026-01-01T00:00:00Z"},
            raw_name_cell="Passiflora incarnata"),
        Row("wikipedia_es", "Hypericum perforatum", {"title": "Hypericum perforatum", "description": None, "extract": "El hipérico es una planta.",
                                                     "url": "https://es.wikipedia.org/wiki/Hypericum_perforatum", "revision": "3", "timestamp": "2026-01-01T00:00:00Z"},
            raw_name_cell="Hypericum perforatum"),
        Row("wikipedia_es", "Passiflora edulis", {"title": "Passiflora edulis", "description": None, "extract": "La maracuyá.",
                                                  "url": "https://es.wikipedia.org/wiki/Passiflora_edulis", "revision": "4", "timestamp": "2026-01-01T00:00:00Z"},
            raw_name_cell="Passiflora edulis"),
        Row("commons", "File:Lavanda.jpg", {"title": "File:Lavanda.jpg", "fileUrl": "https://upload.example/Lavanda.jpg",
                                            "pageUrl": "https://commons.wikimedia.org/wiki/File:Lavanda.jpg", "author": "Ana", "license": "CC BY-SA 4.0",
                                            "licenseCode": "cc-by-sa", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
                                            "attributionRequired": True, "mime": "image/jpeg", "width": 800, "height": 600}, raw_name_cell="File:Lavanda.jpg"),
        Row("commons", "File:Hiperico.jpg", {"title": "File:Hiperico.jpg", "fileUrl": "https://upload.example/Hiperico.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
                                             "pageUrl": "https://commons.wikimedia.org/wiki/File:Hiperico.jpg", "author": None, "license": "Public domain",
                                             "licenseCode": "public-domain", "licenseUrl": None, "attributionRequired": False, "mime": "image/jpeg",
                                             "width": 10, "height": 10}, raw_name_cell="File:Hiperico.jpg"),
    ]


def wikidata_cache():
    """Respuestas de Wikidata por nombre consultado. El ítem de L. latifolia llega en la respuesta del nombre de la lavanda (como en el piloto)."""
    return {
        "Lavandula angustifolia": [ws.item("Q42081", "Lavandula angustifolia", ["Mill."], spanishNames=["espliego"], labelEs="lavanda",
                                           eswiki="Lavandula angustifolia", ipni=["449008-1"]),
                                   ws.item("Q905916", "Lavandula latifolia", ["Medik."], spanishNames=["alhucema"], labelEs="alhucema")],
        "Lavandula latifolia": [ws.item("Q905916", "Lavandula latifolia", ["Medik."], spanishNames=["alhucema"], labelEs="alhucema")],
        "Passiflora incarnata": [ws.item("Q128939", "Passiflora incarnata", ["L."], labelEs="pasionaria", eswiki="Passiflora incarnata"),
                                 ws.item("Q156790", "Passiflora edulis", ["Sims"], spanishNames=["maracuyá"], labelEs="maracuyá", eswiki="Passiflora edulis")],
        "Hypericum perforatum": [ws.item("Q158289", "Hypericum perforatum", ["L."], spanishNames=["hierba de San Juan"], labelEs="hipérico",
                                         eswiki="Hypericum perforatum",
                                         images=["http://commons.wikimedia.org/wiki/Special:FilePath/Hiperico.jpg"])],
        "Cinnamomum verum": [], "Mentha spicata": [],
    }


class World(object):
    """Mundo de prueba: filas de `sources.db` y cachés de Wikimedia modificables, y un armado de paquetes."""

    def __init__(self):
        self.rows = {"usda": usda_rows(), "ema_json": ema_rows(), "ema_pdf": ema_pdf_rows(), "tppt": tppt_rows(), "efsa": efsa_rows(),
                     "wikidata": [r for r in wikimedia_rows() if r.record_type == "wikidata"],
                     "wikipedia_es": [r for r in wikimedia_rows() if r.record_type == "wikipedia_es"],
                     "commons": [r for r in wikimedia_rows() if r.record_type == "commons"]}
        self.wikidata = wikidata_cache()
        self.tmp = tempfile.mkdtemp(prefix="bundles-cache-")
        atexit.register(shutil.rmtree, self.tmp, True)
        self.safety_map = safety.load_safety_map()
        self.goals_map = goals_lib.load_goals_map()

    def _steps(self):
        steps = {"wikidata": WikidataStep(cache_dir=self.tmp), "wikipedia_es": WikipediaStep(cache_dir=self.tmp), "commons": CommonsStep(cache_dir=self.tmp)}
        for name, items in self.wikidata.items():
            steps["wikidata"].store(name, {"items": items})
        steps["wikipedia_es"].store("Lavandula angustifolia", {"type": "standard", "title": "Lavandula angustifolia", "extract": "x", "wikibase_item": "Q42081"})
        steps["wikipedia_es"].store("Passiflora incarnata", {"type": "standard", "title": "Passiflora incarnata", "extract": "x", "wikibase_item": "Q128939"})
        steps["wikipedia_es"].store("Hypericum perforatum", {"type": "standard", "title": "Hypericum perforatum", "extract": "x", "wikibase_item": "Q158289"})
        steps["wikipedia_es"].store("Passiflora edulis", {"type": "standard", "title": "Passiflora edulis", "extract": "x", "wikibase_item": "Q156790"})
        steps["commons"].store("File:Lavanda.jpg", ws.commons_response("File:Lavanda.jpg", License="cc-by-sa-4.0", LicenseShortName="CC BY-SA 4.0", Artist="Ana"))
        steps["commons"].store("File:Hiperico.jpg", ws.commons_response("File:Hiperico.jpg", License="pd", LicenseShortName="Public domain"))
        return steps

    def build(self, disabled=(), limits=None, with_wikidata=True, plant_ids=None):
        """Paquetes de las plantas del mundo con las fuentes dadas por desactivadas."""
        uni = build_universe_in_memory()
        connection = workdb.open_db(":memory:")
        for source, rows in self.rows.items():
            workdb.replace_source(connection, source, rows, "prueba", {})
        steps = self._steps()

        def assigner(document, enabled):
            plan = wa.build_name_plan(document, uni.wcvp, ())
            return wa.build_assignment(document, uni.wcvp, uni.wfo, plan, steps, {k: enabled.get(k, False) for k in ("wikidata", "wikipedia_es", "commons")})

        builder = bundles.Builder(uni, sources(disabled), self.safety_map, self.goals_map, limits=limits)
        builder.prepare(connection, assigner if with_wikidata else None, log=lambda *a: None)
        result = builder.build(plant_ids)
        connection.close()
        return result

    def copy_of(self):
        return copy.deepcopy(self.rows)
