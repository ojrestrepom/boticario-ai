import unittest

import support  # noqa: F401

from catalog_seed import goals
from catalog_seed.download import require_verified
from catalog_seed.ema import EXPECTED_RECORDS, dedupe_records, load_json
from catalog_seed.sources import SourceError, load_sources

SPEC_TABLE = {
    "Mental stress and mood disorders": "relajacion-estres",
    "Sleep disorders and temporary insomnia": "mejorar-el-sueno",
    "Skin disorders and minor wounds": "cuidado-de-la-piel",
    "Cough and cold": "alivio-respiratorio",
    "Fatigue and weakness": "cansancio-y-fatiga",
}
GOAL_IDS = ["relajacion-estres", "mejorar-el-sueno", "cuidado-de-la-piel", "alivio-respiratorio", "cansancio-y-fatiga", "otros-objetivos"]
SUBAREA_IDS = ["digestion", "vias-urinarias-y-genitales", "dolor-e-inflamacion", "boca-y-garganta", "circulacion", "molestias-oculares"]
REAL_VARIANTS = ["Urinary tract and gynaecology disorders", "Digestive disorder", "Eye discomfort"]


def fixture_records():
    """Fichas pequeñas con las variantes reales del JSON, un área vacía y un resultado combinado."""
    areas = list(SPEC_TABLE) + REAL_VARIANTS + [
        "Gastrointestinal disorders", "Loss of appetite", "Constipation", "Urinary tract and genital disorders",
        "Pain and inflammation", "Mouth and throat disorders", "Circulatory disorders", ""]
    records = [{"therapeutic_area": area, "outcome_of_european_assessment": "European Union herbal monograph"} for area in areas]
    records.append({"therapeutic_area": "Gastrointestinal disorders;Urinary tract and genital disorders",
                    "outcome_of_european_assessment": "European Union herbal monograph;European Union list entry"})
    return records


class GoalsCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = goals.load_goals_catalog()
        cls.goals_map = goals.load_goals_map()

    def test_catalog_has_the_spec_ids_and_order(self):
        self.assertEqual(goals.goal_ids(self.catalog), GOAL_IDS)
        self.assertEqual(goals.subarea_ids(self.catalog), SUBAREA_IDS)
        self.assertEqual({s["goalId"] for s in self.catalog["subareas"]}, {"otros-objetivos"})

    def test_catalog_has_labels_and_increasing_positions(self):
        for items in (self.catalog["goals"], self.catalog["subareas"]):
            self.assertTrue(all(item["label"] for item in items))
            self.assertEqual([item["position"] for item in items], list(range(1, len(items) + 1)))
        self.assertEqual(self.catalog["goals"][0]["label"], "Relajación / Estrés")
        self.assertEqual(self.catalog["goals"][5]["label"], "Otros objetivos")

    def test_every_map_id_exists_in_the_catalog(self):
        self.assertEqual(goals.check_map_against_catalog(self.goals_map, self.catalog), [])

    def test_check_detects_unknown_ids(self):
        broken = {"areas": {"X": {"es": "x", "goal": "concentracion", "subarea": None},
                            "Y": {"es": "y", "goal": "otros-objetivos", "subarea": "inventada"},
                            "Z": {"es": "z", "goal": "otros-objetivos", "subarea": None}}}
        self.assertEqual(len(goals.check_map_against_catalog(broken, self.catalog)), 3)

    def test_five_own_goal_areas_match_the_spec_table(self):
        own = {area: e["goal"] for area, e in self.goals_map["areas"].items() if e["goal"] != "otros-objetivos"}
        self.assertEqual(own, SPEC_TABLE)
        for area in SPEC_TABLE:
            self.assertIsNone(self.goals_map["areas"][area]["subarea"])

    def test_every_other_area_has_a_subarea_and_a_spanish_translation(self):
        for area, entry in self.goals_map["areas"].items():
            self.assertTrue(entry["es"].strip(), area)
            if entry["goal"] == "otros-objetivos":
                self.assertIn(entry["subarea"], SUBAREA_IDS)

    def test_real_variants_are_mapped(self):
        areas = self.goals_map["areas"]
        self.assertEqual(areas["Urinary tract and gynaecology disorders"]["subarea"], "vias-urinarias-y-genitales")
        self.assertEqual(areas["Digestive disorder"]["subarea"], "digestion")
        self.assertEqual(areas["Eye discomfort"]["subarea"], "molestias-oculares")

    def test_counted_outcomes_split_the_combined_result(self):
        counted = goals.counted_outcomes
        self.assertTrue(counted(self.goals_map, "European Union herbal monograph;European Union list entry"))
        self.assertTrue(counted(self.goals_map, "European Union list entry"))
        self.assertFalse(counted(self.goals_map, "Public statement"))
        self.assertFalse(counted(self.goals_map, None))

    def assert_all_areas_assigned(self, records):
        for record in records:
            for area, mapped in goals.map_record_areas(self.goals_map, record):
                self.assertIsNotNone(mapped, "área sin asignar: %r" % area)
                if area:
                    self.assertIsNotNone(mapped[0], area)
                else:
                    self.assertIsNone(mapped[0])  # el área vacía está tratada de forma explícita: sin objetivo

    def test_fixture_records_areas_are_assigned(self):
        self.assert_all_areas_assigned(fixture_records())

    def test_multi_area_record_gives_one_assignment_per_area(self):
        (area_a, area_b) = goals.map_record_areas(self.goals_map, fixture_records()[-1])
        self.assertEqual(area_a[1][:2], ("otros-objetivos", "digestion"))
        self.assertEqual(area_b[1][:2], ("otros-objetivos", "vias-urinarias-y-genitales"))

    def test_real_ema_snapshot(self):
        try:
            source = [s for s in load_sources() if s.id == "ema_json"][0]
            path = require_verified(source)
        except SourceError as error:
            self.skipTest("la caché de la EMA no está disponible: %s" % error)
        records = dedupe_records(load_json(path))
        self.assertEqual(len(records), EXPECTED_RECORDS)
        self.assert_all_areas_assigned(records)
        seen = {area for record in records for area, _ in goals.map_record_areas(self.goals_map, record) if area}
        self.assertTrue(set(SPEC_TABLE) <= seen)
        self.assertTrue(seen <= set(self.goals_map["areas"]))


if __name__ == "__main__":
    unittest.main()
