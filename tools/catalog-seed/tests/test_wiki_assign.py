import json
import os
import tempfile
import unittest

import support  # noqa: F401
import wiki_support as ws

from catalog_seed import wiki_assign as wa
from catalog_seed.wiki import CommonsStep, WikidataStep, WikipediaStep


class AssignTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wcvp, self.wfo = ws.backbones()
        self.universe = ws.universe()
        self.plan = wa.build_name_plan(self.universe, self.wcvp)
        self.steps = {"wikidata": WikidataStep(cache_dir=self.tmp.name), "wikipedia_es": WikipediaStep(cache_dir=self.tmp.name),
                      "commons": CommonsStep(cache_dir=self.tmp.name)}

    def store(self, name, *items):
        self.steps["wikidata"].store(name, {"items": list(items)})

    def assign(self, enabled=None):
        return wa.build_assignment(self.universe, self.wcvp, self.wfo, self.plan, self.steps, enabled)


class NamePlanTests(AssignTestCase):
    def test_names_are_accepted_entries_and_homotypic_synonyms_plus_controls(self):
        names = self.plan["names"]
        self.assertIn("Lavandula angustifolia", names)
        self.assertIn("Lavandula officinalis", names)       # sinónimo homotípico
        self.assertNotIn("Lavandula vera", names)           # sinónimo heterotípico
        self.assertIn("Gendarussa adhatoda", names)
        self.assertIn("Adhatoda vasica", names)
        self.assertEqual(self.plan["byName"]["Passiflora edulis"], [])  # control: no es de ninguna planta
        self.assertEqual(self.plan["byName"]["Lavandula officinalis"], ["lavandula-angustifolia"])
        self.assertEqual(len(names), len(set(names)))

    def test_plants_without_an_accepted_name_are_not_queried(self):
        self.assertEqual(self.plan["byPlant"]["genero-suelto"], [])


class HomonymFilterTests(AssignTestCase):
    def test_lavandula_latifolia_does_not_enter_the_lavender(self):
        # El ítem de L. latifolia llega en la respuesta del nombre de la lavanda (como en el piloto).
        self.store("Lavandula angustifolia",
                   ws.item("Q42081", "Lavandula angustifolia", ["Mill."], spanishNames=["espliego"]),
                   ws.item("Q905916", "Lavandula latifolia", ["Medik."], spanishNames=["alhucema"]))
        document = self.assign()
        lavender = document["plants"]["lavandula-angustifolia"]
        self.assertEqual(lavender["wikidata"]["items"], ["Q42081"])
        self.assertEqual(lavender["spanishNames"], ["espliego"])
        spike = document["items"]["Q905916"]
        self.assertEqual(spike["plantId"], "lavandula-latifolia")
        self.assertTrue(spike["homonym"])
        self.assertEqual(spike["requestedFor"], ["lavandula-angustifolia"])
        self.assertNotIn("alhucema", lavender["spanishNames"])

    def test_passiflora_edulis_does_not_enter_the_passionflower(self):
        self.store("Passiflora incarnata", ws.item("Q128939", "Passiflora incarnata", ["L."]),
                   ws.item("Q156790", "Passiflora edulis", ["Sims"], eswiki="Passiflora edulis",
                           images=["http://commons.wikimedia.org/wiki/Special:FilePath/Maracuya.jpg"]))
        document = self.assign()
        self.assertEqual(document["plants"]["passiflora-incarnata"]["wikidata"]["items"], ["Q128939"])
        edulis = document["items"]["Q156790"]
        self.assertIsNone(edulis["plantId"])
        self.assertEqual(edulis["reason"], "fuera-del-universo")
        self.assertTrue(edulis["homonym"])
        # Ni su artículo ni su imagen se piden ni se asignan.
        self.assertEqual(document["pending"], {"wikipedia_es": [], "commons": []})

    def test_control_names_without_a_plant_are_not_homonym_discards(self):
        self.store("Passiflora edulis", ws.item("Q156790", "Passiflora edulis", ["Sims"]))
        document = self.assign()
        self.assertFalse(document["items"]["Q156790"]["homonym"])
        self.assertEqual(document["items"]["Q156790"]["reason"], "fuera-del-universo")

    def test_control_checks_report(self):
        self.store("Lavandula angustifolia", ws.item("Q42081", "Lavandula angustifolia", ["Mill."]))
        self.store("Lavandula latifolia", ws.item("Q905916", "Lavandula latifolia", ["Medik."]))
        checks = wa.control_checks(self.assign())
        self.assertTrue(checks["lavandula-angustifolia"]["ok"])
        self.assertEqual(checks["lavandula-angustifolia"]["homonymItems"]["Q905916"]["plantId"], "lavandula-latifolia")

    def test_synonym_item_of_the_accepted_name_enters(self):
        self.store("Lavandula officinalis", ws.item("Q111", "Lavandula officinalis", ["Chaix"]))
        document = self.assign()
        self.assertEqual(document["items"]["Q111"]["plantId"], "lavandula-angustifolia")
        self.assertEqual(document["items"]["Q111"]["acceptedName"], "Lavandula angustifolia")
        self.assertFalse(document["items"]["Q111"]["homonym"])
        self.assertEqual(document["plants"]["lavandula-angustifolia"]["wikidata"]["items"], ["Q111"])

    def test_item_without_name_or_with_unresolvable_name_is_not_assigned(self):
        self.store("Lavandula angustifolia", ws.item("Q1", ""), ws.item("Q2", "Inventada nonexistens"))
        document = self.assign()
        self.assertEqual(document["items"]["Q1"]["reason"], "sin-nombre")
        self.assertEqual(document["items"]["Q2"]["reason"], "sin-resolver")


class SplitGroupTests(AssignTestCase):
    def test_item_goes_to_the_plant_of_its_own_name(self):
        self.store("Adhatoda vasica", ws.item("Q10", "Adhatoda vasica", ["Nees"]))
        self.store("Justicia adhatoda", ws.item("Q11", "Justicia adhatoda", ["L."]))
        self.store("Gendarussa adhatoda", ws.item("Q12", "Gendarussa adhatoda", ["Nees"]))
        self.store("Adhatoda zeylanica", ws.item("Q13", "Adhatoda zeylanica", ["Medik."]))
        document = self.assign()
        items = document["items"]
        self.assertEqual((items["Q10"]["plantId"], items["Q10"]["reason"]), ("adhatoda-vasica", "misma-clave"))
        self.assertEqual((items["Q11"]["plantId"], items["Q11"]["reason"]), ("justicia-adhatoda", "aceptado"))
        self.assertEqual((items["Q12"]["plantId"], items["Q12"]["reason"]), ("justicia-adhatoda", "homotipico"))
        # Un heterotípico sin planta propia no se le da al aceptado.
        self.assertIsNone(items["Q13"]["plantId"])
        self.assertEqual(items["Q13"]["reason"], "heterotipico-sin-planta")


class FusedHeterotypicTests(AssignTestCase):
    def setUp(self):
        super().setUp()
        # Adhatoda zeylanica (id 12) se fusionó con el aceptado por la regla de colisiones; Adhatoda vasica sigue separada.
        for plant in self.universe["plants"]:
            if plant["id"] == "justicia-adhatoda":
                plant["fusedMatchedIds"] = ["wcvp:12"]

    def test_item_of_a_fused_heterotypic_goes_to_the_fused_plant(self):
        self.store("Adhatoda zeylanica", ws.item("Q13", "Adhatoda zeylanica", ["Medik."], spanishNames=["adhatoda"], eswiki="Adhatoda"))
        self.store("Adhatoda vasica", ws.item("Q10", "Adhatoda vasica", ["Nees"]))
        document = self.assign()
        items = document["items"]
        self.assertEqual((items["Q13"]["plantId"], items["Q13"]["reason"]), ("justicia-adhatoda", "heterotipico-fusionado"))
        self.assertEqual((items["Q10"]["plantId"], items["Q10"]["reason"]), ("adhatoda-vasica", "misma-clave"))
        self.assertEqual(document["plants"]["justicia-adhatoda"]["spanishNames"], ["adhatoda"])
        self.assertEqual(document["pending"]["wikipedia_es"], ["Adhatoda"])

    def test_heterotypic_without_fusion_or_plant_stays_unassigned(self):
        self.store("Adhatoda zeylanica", ws.item("Q13", "Adhatoda zeylanica", ["Medik."]))
        for plant in self.universe["plants"]:
            plant.pop("fusedMatchedIds", None)
        self.assertEqual(self.assign()["items"]["Q13"]["reason"], "heterotipico-sin-planta")


class IpniEvidenceTests(AssignTestCase):
    def test_ipni_and_powo_ids_are_compared_with_wcvp(self):
        self.store("Lavandula angustifolia", ws.item("Q1", "Lavandula angustifolia", ["Mill."], ipni=["449008-1"]))
        self.store("Lavandula officinalis", ws.item("Q2", "Lavandula officinalis", ["Chaix"],
                                                    powo=["urn:lsid:ipni.org:names:999-1"]))
        self.store("Lavandula latifolia", ws.item("Q3", "Lavandula latifolia", ["Medik."]))
        items = self.assign()["items"]
        self.assertEqual(items["Q1"]["ipni"], "coincide")
        self.assertEqual(items["Q2"]["ipni"], "discrepa")
        self.assertEqual(items["Q3"]["ipni"], "sin-dato")
        # La evidencia no cambia la asignación: Q2 entra por su nombre.
        self.assertEqual(items["Q2"]["plantId"], "lavandula-angustifolia")


class DeclaredStatusTests(AssignTestCase):
    def test_plant_without_wikidata_response_is_declared_so(self):
        self.store("Lavandula angustifolia", ws.item("Q42081", "Lavandula angustifolia", ["Mill."]))
        self.store("Passiflora incarnata")          # respondió, sin ítem
        document = self.assign()
        status = {p: d["wikidata"]["status"] for p, d in document["plants"].items()}
        self.assertEqual(status["lavandula-angustifolia"], wa.STATUS_WITH_ITEM)
        self.assertEqual(status["passiflora-incarnata"], wa.STATUS_NO_ITEM)
        self.assertEqual(status["justicia-adhatoda"], wa.STATUS_NO_RESPONSE)
        self.assertEqual(status["genero-suelto"], wa.STATUS_NOT_QUERIED)
        summary = wa.summarize(document)
        self.assertEqual(summary["plantsByWikidataStatus"][wa.STATUS_NO_RESPONSE], 3)

    def test_disabled_wikidata_assigns_nothing(self):
        self.store("Lavandula angustifolia", ws.item("Q42081", "Lavandula angustifolia", ["Mill."]))
        document = self.assign({"wikidata": False, "wikipedia_es": True, "commons": True})
        self.assertEqual(document["items"], {})
        self.assertEqual(document["plants"]["lavandula-angustifolia"]["wikidata"]["status"], wa.STATUS_NO_RESPONSE)


class WikipediaAndCommonsTests(AssignTestCase):
    def setUp(self):
        super().setUp()
        self.store("Lavandula angustifolia", ws.item(
            "Q42081", "Lavandula angustifolia", ["Mill."], eswiki="Lavandula angustifolia",
            images=["http://commons.wikimedia.org/wiki/Special:FilePath/Ok.jpg",
                    "http://commons.wikimedia.org/wiki/Special:FilePath/Nc.jpg",
                    "http://commons.wikimedia.org/wiki/Special:FilePath/Falta.jpg",
                    "http://commons.wikimedia.org/wiki/Special:FilePath/Sin%20consultar.jpg"]))
        self.steps["wikipedia_es"].store("Lavandula angustifolia", {
            "type": "standard", "title": "Lavandula angustifolia", "extract": "Es una planta.", "revision": "1",
            "wikibase_item": "Q42081"})
        commons = self.steps["commons"]
        commons.store("File:Ok.jpg", ws.commons_response("File:Ok.jpg", License="cc-by-sa-4.0", LicenseShortName="CC BY-SA 4.0",
                                                         Artist="Ana"))
        commons.store("File:Nc.jpg", ws.commons_response("File:Nc.jpg", License="cc-by-nc-2.0", LicenseShortName="CC BY-NC 2.0",
                                                         Artist="Luis"))
        commons.store("File:Falta.jpg", {"missing": True})

    def test_images_are_classified_per_plant_and_pending_is_listed(self):
        document = self.assign()
        plant = document["plants"]["lavandula-angustifolia"]
        self.assertEqual([i["title"] for i in plant["commons"]["admitted"]], ["File:Ok.jpg"])
        self.assertEqual(plant["commons"]["admitted"][0]["licenseCode"], "cc-by-sa")
        reasons = {i["title"]: i["reason"] for i in plant["commons"]["discarded"]}
        self.assertEqual(reasons, {"File:Nc.jpg": "no-comercial", "File:Falta.jpg": "archivo-no-encontrado"})
        self.assertEqual(document["pending"]["commons"], ["File:Sin consultar.jpg"])
        self.assertEqual(plant["wikipedia"][0]["title"], "Lavandula angustifolia")
        summary = wa.summarize(document)
        self.assertEqual(summary["plantsWithAdmittedImage"], 1)
        self.assertEqual(summary["imagesDiscardedByReason"], {"archivo-no-encontrado": 1, "no-comercial": 1})
        self.assertEqual(summary["plantsWithWikipedia"], 1)

    def test_disabled_services_contribute_nothing(self):
        document = self.assign({"wikidata": True, "wikipedia_es": False, "commons": False})
        plant = document["plants"]["lavandula-angustifolia"]
        self.assertEqual(plant["wikipedia"], [])
        self.assertEqual(plant["commons"], {"admitted": [], "discarded": []})
        self.assertEqual(document["pending"], {"wikipedia_es": [], "commons": []})

    def test_missing_or_disambiguation_articles_are_not_summaries(self):
        self.steps["wikipedia_es"].store("Lavandula angustifolia", {"type": "disambiguation", "title": "Lavandula angustifolia"})
        document = self.assign()
        self.assertEqual(document["plants"]["lavandula-angustifolia"]["wikipedia"], [])
        self.assertEqual(document["items"]["Q42081"]["wikipedia"]["state"], "disambiguation")


class AssignmentIsDeterministicTests(AssignTestCase):
    def test_same_cache_same_document(self):
        self.store("Lavandula angustifolia", ws.item("Q42081", "Lavandula angustifolia", ["Mill."]))
        first = json.dumps(self.assign(), sort_keys=True)
        second = json.dumps(self.assign(), sort_keys=True)
        self.assertEqual(first, second)


class RealDataTests(unittest.TestCase):
    """Con la asignación real (`wiki-assign` sobre la caché descargada): los homónimos del piloto quedan fuera."""

    def setUp(self):
        import extract_support
        path = os.path.join(extract_support.REPO_ROOT, "data", "work", "wiki", "assignment.json")
        if not os.path.isfile(path):
            self.skipTest("falta data/work/wiki/assignment.json: ejecute wiki-fetch o wiki-assign")
        with open(path, encoding="utf-8") as handle:
            self.document = json.load(handle)

    def taxa(self, plant_id):
        return {self.document["items"][q]["taxon"] for q in self.document["plants"][plant_id]["wikidata"]["items"]}

    def test_lavender_gets_nothing_from_lavandula_latifolia(self):
        self.assertNotIn("Lavandula latifolia", self.taxa("lavandula-angustifolia"))
        latifolia = self.document["plants"]["lavandula-latifolia"]["wikidata"]["items"] if "lavandula-latifolia" in self.document["plants"] else []
        lavender = set(self.document["plants"]["lavandula-angustifolia"]["wikidata"]["items"])
        self.assertFalse(lavender & set(latifolia))

    def test_passionflower_gets_nothing_from_passiflora_edulis(self):
        self.assertNotIn("Passiflora edulis", self.taxa("passiflora-incarnata"))
        for qid, item in self.document["items"].items():
            if item["taxon"] == "Passiflora edulis":
                self.assertNotEqual(item["plantId"], "passiflora-incarnata")


if __name__ == "__main__":
    unittest.main()
