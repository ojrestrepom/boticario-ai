import unittest

import taxonomy_support
from catalog_seed.taxonomy import Entry, UniverseError, build_universe


def usda(key, name, author=""):
    return Entry("usda", "usda:" + key, name, author)


class CollisionTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def build(self, entries, **kwargs):
        return build_universe(entries, self.wcvp, self.wfo, **kwargs)

    def ids(self, uni):
        return sorted(p.id for p in uni.plants)

    def test_lemon_lime_and_bergamot_are_three_plants(self):
        uni = self.build([
            usda("279", "Citrus limon"), usda("2156", "Citrus limetta"),
            Entry.from_text("ema", "ema:bergamot", "Citrus bergamia Risso & Poiteau.")])
        self.assertEqual(self.ids(uni), ["citrus-x-bergamia", "citrus-x-limetta", "citrus-x-limon"])
        lemon = uni.plant("citrus-x-limon")
        self.assertEqual((lemon.name, lemon.accepted_id, lemon.kind), ("Citrus × limon", "2724178", "resolved"))
        self.assertTrue(lemon.is_core)
        bergamot = uni.plant("citrus-x-bergamia")
        self.assertEqual((bergamot.name, bergamot.kind), ("Citrus × bergamia", "heterotypic"))
        self.assertIn("split_group", bergamot.flags)
        self.assertIn("grupo-partido", [f["code"] for f in bergamot.review_flags])
        self.assertIn("split_group", lemon.flags)
        self.assertEqual(uni.plant("citrus-x-limetta").matched_id, "2724174")

    def test_orange_and_grapefruit_are_two_plants(self):
        uni = self.build([usda("1", "Citrus sinensis"), usda("2", "Citrus paradisi")])
        self.assertEqual(self.ids(uni), ["citrus-x-paradisi", "citrus-x-sinensis"])
        for plant in uni.plants:
            self.assertEqual(plant.accepted_id, "3287406")
            self.assertEqual(plant.kind, "heterotypic")
            self.assertFalse(plant.is_core)

    def test_brassica_varieties_each_get_their_own_plant(self):
        uni = self.build([
            usda("1", "Brassica oleracea var. italica"), usda("2", "Brassica oleracea var. capitata"),
            usda("3", "Brassica oleracea var. acephala"), usda("4", "Brassica oleracea")])
        self.assertEqual(self.ids(uni), [
            "brassica-oleracea", "brassica-oleracea-var-acephala", "brassica-oleracea-var-capitata",
            "brassica-oleracea-var-italica"])
        self.assertTrue(uni.plant("brassica-oleracea").is_core)

    def test_single_synonym_keeps_the_accepted_id_and_an_alias(self):
        uni = self.build([usda("1", "Rosmarinus officinalis")])
        plant = uni.plants[0]
        self.assertEqual((plant.id, plant.name, plant.aliases, plant.split), ("salvia-rosmarinus", "Salvia rosmarinus", ["rosmarinus-officinalis"], False))

    def test_homotypic_synonyms_merge_into_the_accepted(self):
        uni = self.build([usda("1", "Matricaria recutita"), Entry("ema", "ema:1", "Matricaria recutita", "L.")])
        self.assertEqual(self.ids(uni), ["matricaria-chamomilla"])
        self.assertEqual(len(uni.plants[0].entries), 2)
        # «Citrus medica var. limon» es homotípico del limón (WCVP homotypic_synonym = T): se fusiona.
        uni = self.build([usda("1", "Citrus limon"), usda("2", "Citrus medica var. limon")])
        self.assertEqual(self.ids(uni), ["citrus-x-limon"])

    def test_meyerii_through_the_wfo_backup_is_not_merged_with_the_lemon(self):
        uni = self.build([usda("1", "Citrus limon"), usda("2", "Citrus meyerii")], use_variants=False)
        res = uni.resolutions["usda:2"]
        self.assertEqual((res["backbone"], res["outcome"]), ("wfo", "synonym"))
        self.assertEqual(self.ids(uni), ["citrus-meyerii", "citrus-x-limon"])
        meyerii = uni.plant("citrus-meyerii")
        self.assertIn("wfo_fallback", meyerii.flags)
        self.assertIn("respaldo-wfo", [f["code"] for f in meyerii.review_flags])
        self.assertTrue(uni.plant("citrus-x-limon").is_core)
        # Con la variante ortográfica de WCVP tampoco se fusiona: es heterotípico.
        uni = self.build([usda("1", "Citrus limon"), usda("2", "Citrus meyerii")])
        self.assertEqual(self.ids(uni), ["citrus-x-limon", "citrus-x-meyeri"])

    def test_wfo_accepted_matching_the_wcvp_accepted_joins_the_core(self):
        # Una entrada resuelta por WFO que es el propio aceptado (mismo nombre) se une al núcleo, sin mezclar IDs.
        uni = self.build([usda("1", "Citrus limon"), usda("2", "Citrus limon", "(L.) Osbeck")])
        self.assertEqual(self.ids(uni), ["citrus-x-limon"])

    def test_unresolved_ambiguous_and_genus_only_keep_the_source_identity(self):
        uni = self.build([usda("1", "Prunus dulcis"), usda("2", "Gossypium sp"), usda("3", "Zzzzus nonexistens")])
        by_id = {p.id: p for p in uni.plants}
        self.assertEqual(sorted(by_id), ["gossypium-sp", "prunus-dulcis", "zzzzus-nonexistens"])
        self.assertEqual(by_id["prunus-dulcis"].kind, "ambiguous")
        self.assertIn("identidad-ambigua", [f["code"] for f in by_id["prunus-dulcis"].review_flags])
        self.assertIn("solo-genero", [f["code"] for f in by_id["gossypium-sp"].review_flags])
        self.assertIn("sin-resolucion", [f["code"] for f in by_id["zzzzus-nonexistens"].review_flags])
        for flag in by_id["gossypium-sp"].review_flags:
            self.assertEqual(set(flag), {"code", "target", "message"})

    def test_ema_species_not_in_usda_joins_the_universe_once(self):
        uni = self.build([usda("1", "Matricaria recutita"), Entry.from_text("ema", "ema:1", "Matricaria recutita L."),
                          Entry.from_text("ema", "ema:2", "Valeriana officinalis L.")])
        self.assertEqual(self.ids(uni), ["matricaria-chamomilla", "valeriana-officinalis"])
        self.assertEqual([e.key for e in uni.plant("matricaria-chamomilla").entries], ["usda:1", "ema:1"])

    def test_heterotypic_synonym_next_to_its_accepted_is_a_separate_plant(self):
        # Matricaria recutita es heterotípico de M. chamomilla en WCVP (homotypic_synonym vacío): dos plantas.
        uni = self.build([usda("1", "Matricaria recutita"), usda("2", "Matricaria chamomilla")])
        self.assertEqual(self.ids(uni), ["matricaria-chamomilla", "matricaria-recutita"])

    def test_duplicate_ids_fail_naming_both_plants(self):
        with self.assertRaises(UniverseError) as ctx:
            self.build([usda("1", "Foo ba r"), usda("2", "Foo ba-r")])
        self.assertIn("foo-ba-r", str(ctx.exception))
        self.assertIn("usda:1", str(ctx.exception))
        self.assertIn("usda:2", str(ctx.exception))
        self.assertEqual(ctx.exception.collisions[0][0], "foo-ba-r")

    def test_alias_equal_to_another_plant_id_is_discarded_and_recorded(self):
        uni = self.build([usda("1", "Prunus dulcis"), usda("2", "Prunus dulcis", "(MILLER) D. A. WEBB")])
        self.assertEqual(self.ids(uni), ["prunus-amygdalus", "prunus-dulcis"])
        self.assertEqual(uni.plant("prunus-amygdalus").aliases, [])
        self.assertEqual([(a[0], a[1]) for a in uni.discarded_aliases], [("prunus-amygdalus", "prunus-dulcis")])

    def test_lavandula_angustifolia_id_is_kept(self):
        uni = self.build([usda("1", "Lavandula angustifolia", "MILLER")])
        self.assertEqual(uni.plants[0].id, "lavandula-angustifolia")
        self.assertEqual(uni.plants[0].aliases, [])

    def test_stats(self):
        uni = self.build([usda("1", "Citrus limon"), usda("2", "Citrus limetta"), usda("3", "Gossypium sp")])
        stats = uni.stats()
        self.assertEqual((stats["entries"], stats["plants"], stats["split_groups"], stats["genus_only"]), (3, 3, 1, 1))


class RowAssignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wcvp, cls.wfo = taxonomy_support.backbones()
        cls.uni = build_universe([
            usda("279", "Citrus limon"), usda("2156", "Citrus limetta"),
            Entry.from_text("ema", "ema:bergamot", "Citrus bergamia Risso & Poiteau."),
            usda("5", "Citrus sinensis"), usda("6", "Citrus paradisi"), usda("7", "Rosmarinus officinalis"),
            usda("8", "Prunus dulcis")], cls.wcvp, cls.wfo)

    def setUp(self):
        self.uni.unassigned[:] = []
        for p in self.uni.plants:
            p.flags.discard("unassigned_rows")

    def test_same_key_goes_to_that_member(self):
        self.assertEqual(self.uni.assign("Citrus limon")[0].id, "citrus-x-limon")
        self.assertEqual(self.uni.assign("Citrus limetta")[0].id, "citrus-x-limetta")
        self.assertEqual(self.uni.assign("Citrus x limetta")[0].id, "citrus-x-limetta")
        self.assertEqual(self.uni.assign("Citrus bergamia Risso & Poiteau.")[1], "misma-clave")

    def test_homotypic_names_of_the_bergamot_go_to_the_bergamot(self):
        plant, reason = self.uni.assign("Citrus x aurantium subsp. bergamia")
        self.assertEqual((plant.id, reason), ("citrus-x-bergamia", "homotipico"))
        plant, reason = self.uni.assign("Citrus limetta var. bergamia")   # el basiónimo de la bergamota
        self.assertEqual((plant.id, reason), ("citrus-x-bergamia", "homotipico"))

    def test_limettioides_rows_go_to_the_lemon_as_the_accepted_member(self):
        plant, reason = self.uni.assign("Citrus limettioides")
        self.assertEqual((plant.id, reason), ("citrus-x-limon", "aceptado-propio"))

    def test_row_in_a_split_group_without_accepted_member_is_unassigned_and_recorded(self):
        plant, reason = self.uni.assign("Citrus x aurantium f. aurantium", source="ethnobot")
        self.assertIsNone(plant)
        self.assertEqual(reason, "sin-asignar")
        self.assertEqual(self.uni.unassigned[0]["source"], "ethnobot")
        self.assertEqual(sorted(self.uni.unassigned[0]["group"]), ["citrus-x-paradisi", "citrus-x-sinensis"])
        self.assertIn("filas-sin-asignar", [f["code"] for f in self.uni.plant("citrus-x-sinensis").review_flags])

    def test_unsplit_group_assigns_directly(self):
        plant, reason = self.uni.assign("Salvia rosmarinus")
        self.assertEqual((plant.id, reason), ("salvia-rosmarinus", "grupo-unico"))

    def test_ambiguous_rows_match_their_plant_by_key_or_stay_unassigned(self):
        plant, reason = self.uni.assign("Prunus dulcis")
        self.assertEqual((plant.id, reason), ("prunus-dulcis", "misma-clave"))
        plant, reason = self.uni.assign("Matricaria recutita")
        self.assertIsNone(plant)
        self.assertEqual(reason, "fuera-del-universo")
        self.assertIsNone(self.uni.assign("Zzzzus nonexistens")[0])


if __name__ == "__main__":
    unittest.main()
