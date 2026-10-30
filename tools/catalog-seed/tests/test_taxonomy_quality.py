"""Defectos de calidad del resolvedor con datos reales: coincidencia aproximada, aceptado de rango superior a especie
y entradas de la EMA con sinónimos o listas. Los fixtures son filas reales recortadas (`trim_fixtures.py`)."""
import unittest

import taxonomy_support
from catalog_seed.taxonomy import Entry, build_universe, resolve_fuzzy, resolve_name
from catalog_seed.taxonomy.resolver import edit_distance, fuzzy_max_distance


def usda(key, name, author=""):
    return Entry("usda", "usda:" + key, name, author)


class EditDistanceTest(unittest.TestCase):
    def test_distances_and_thresholds(self):
        self.assertEqual(edit_distance("california", "californica", 2), 1)
        self.assertEqual(edit_distance("fructicosa", "fruticosa", 2), 1)
        self.assertEqual(edit_distance("abcd", "abdc", 2), 1)          # transposición
        self.assertEqual(edit_distance("abcdef", "uvwxyz", 2), 3)      # supera el límite
        self.assertEqual([fuzzy_max_distance(e) for e in ("alba", "rubra", "rosea", "officinalis", "fruticosa")], [0, 1, 1, 2, 2])


class FuzzyTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_epithet_typo_in_the_same_genus(self):
        r = resolve_name("Eschscholzia california", self.wcvp, self.wfo, author="Cham.")
        self.assertEqual((r["outcome"], r["accepted_name"], r["backbone"]), ("accepted", "Eschscholzia californica", "wcvp"))
        self.assertIn("fuzzy_match", r["flags"])
        self.assertEqual(r["fuzzy"], {"distance": 1, "kind": "epíteto", "key": "eschscholzia californica"})
        r = resolve_name("Salvia fructicosa", self.wcvp, self.wfo, author="Mill.")
        self.assertEqual((r["outcome"], r["accepted_name"]), ("accepted", "Salvia fruticosa"))
        self.assertIn("fuzzy_match", r["flags"])

    def test_genus_typo_with_exact_epithet(self):
        r = resolve_name("Zizyphus jujuba", self.wcvp, self.wfo, author="MILL.")
        self.assertEqual((r["outcome"], r["accepted_name"], r["accepted_id"]), ("accepted", "Ziziphus jujuba", "2470699"))
        self.assertEqual((r["fuzzy"]["distance"], r["fuzzy"]["kind"]), (1, "género"))
        self.assertIn("fuzzy_match", r["flags"])

    def test_curcuma_xanthorrhiza_resolves_to_wcvp_spelling(self):
        r = resolve_name("Curcuma xanthorrhiza", self.wcvp, self.wfo, author="ROXB.")
        self.assertEqual((r["outcome"], r["accepted_name"]), ("accepted", "Curcuma zanthorrhiza"))
        self.assertIn("fuzzy_match", r["flags"])

    def test_two_candidates_at_the_same_distance_are_ambiguous(self):
        # Croton macrostachys: macrostachyus (Accepted) y microstachys (Illegitimate hacia otro aceptado), ambos a distancia 1.
        r = resolve_name("Croton macrostachys", self.wcvp, self.wfo)
        self.assertEqual(r["outcome"], "ambiguous")
        self.assertIn("fuzzy_match", r["flags"])
        self.assertIn("homonym_unresolved", r["flags"])
        self.assertEqual(r["accepted_id"], "")
        self.assertIn("croton macrostachyus", r["notes"])
        self.assertIn("croton microstachys", r["notes"])

    def test_correct_names_never_use_the_fuzzy_match(self):
        for name in ("Lavandula angustifolia", "Matricaria recutita", "Salvia fruticosa", "Ziziphus jujuba"):
            r = resolve_name(name, self.wcvp, self.wfo)
            self.assertNotIn("fuzzy_match", r["flags"], name)
            self.assertIsNone(r["fuzzy"], name)
        # Con candidatos en WCVP (aunque sean ilegítimos) tampoco se intenta.
        r = resolve_name("Aloysia triphylla", self.wcvp, self.wfo)
        self.assertNotIn("fuzzy_match", r["flags"])

    def test_short_epithets_and_far_names_stay_unmatched(self):
        self.assertEqual(resolve_fuzzy("Salvia alva", self.wcvp)["outcome"], "unmatched")
        r = resolve_name("Salvia fruticoides", self.wcvp, self.wfo)    # distancia 3
        self.assertEqual(r["outcome"], "unmatched")
        self.assertNotIn("fuzzy_match", r["flags"])

    def test_fuzzy_can_be_switched_off(self):
        r = resolve_name("Eschscholzia california", self.wcvp, self.wfo, use_variants=False)
        self.assertEqual(r["outcome"], "unmatched")


class AcceptedAboveSpeciesTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_taraxacum_officinale_is_flagged_and_keeps_its_own_identity(self):
        r = resolve_name("Taraxacum officinale", self.wcvp, self.wfo, author="F.H. Wigg.")
        self.assertEqual(r["outcome"], "unresolved")
        self.assertIn("accepted_above_species", r["flags"])
        self.assertIn("rango superior a especie (plant_name_id 2916959)", r["notes"])
        uni = build_universe([usda("995", "Taraxacum officinale", "WEBER EX F. H. WIGG.")], self.wcvp, self.wfo)
        plant = uni.plant("taraxacum-officinale")
        self.assertEqual(plant.kind, "unresolved")
        self.assertIn("accepted_above_species", plant.flags)
        self.assertIn("aceptado-superior-a-especie", [f["code"] for f in plant.review_flags])
        self.assertEqual(uni.relation("usda:995"), None)

    def test_other_unresolved_names_keep_the_generic_note(self):
        r = resolve_name("Matricaria recutita", self.wcvp, None)
        self.assertNotIn("accepted_above_species", r["flags"])


class UniverseTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_ema_typos_join_the_usda_plant(self):
        uni = build_universe([
            usda("1", "Eschscholzia californica", "CHAM."), usda("2", "Salvia fruticosa", "MILL."),
            Entry.from_text("ema", "ema:eschscholziae-herba#1", "Eschscholzia california Cham."),
            Entry.from_text("ema", "ema:salviae-trilobae-folium#1", "Salvia fructicosa Mill.")], self.wcvp, self.wfo)
        self.assertEqual(sorted(p.id for p in uni.plants), ["eschscholzia-californica", "salvia-fruticosa"])
        esch = uni.plant("eschscholzia-californica")
        self.assertEqual(sorted(e.key for e in esch.entries), ["ema:eschscholziae-herba#1", "usda:1"])
        self.assertIn("fuzzy_match", esch.flags)
        self.assertIn("coincidencia-aproximada", [f["code"] for f in esch.review_flags])
        self.assertEqual(esch.aliases, ["eschscholzia-california"])

    def test_public_relation_of_an_entry(self):
        uni = build_universe([usda("1", "Salvia fruticosa"), usda("2", "Salvia triloba")], self.wcvp, self.wfo)
        self.assertEqual(uni.relation("usda:1"), "A")
        self.assertIn(uni.relation("usda:2"), ("H", "X"))
        uni = build_universe([Entry("usda", "usda:9", "Foo bar")], self.wcvp, self.wfo)
        self.assertIsNone(uni.relation("usda:9"))


if __name__ == "__main__":
    unittest.main()
