import unittest

import taxonomy_support
from catalog_seed.taxonomy import resolve, resolve_name, resolve_variants, synonyms


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_fixture_rows_are_loaded_and_keyed(self):
        stats = taxonomy_support.build_stats()
        self.assertGreater(stats["table_rows"]["wcvp_name"], 40)
        self.assertGreater(stats["table_rows"]["wfo_name"], 40)
        self.assertGreater(stats["table_rows"]["wcvp_distribution"], 0)
        rows = self.wcvp.lookup("lavandula angustifolia")
        self.assertEqual(sorted((r["id"], r["status"]) for r in rows), [("108970", "Illegitimate"), ("108971", "Accepted")])
        accepted = self.wcvp.get("108971")
        self.assertEqual((accepted["author"], accepted["family"], accepted["accepted_id"]), ("Mill.", "Lamiaceae", "108971"))

    def test_hybrid_sign_is_not_part_of_the_key(self):
        self.assertTrue(self.wcvp.lookup("citrus limon"))
        self.assertTrue(self.wcvp.get("2724178")["is_hybrid"])
        self.assertTrue(self.wfo.lookup("mentha piperita"))

    def test_wcvp_keeps_homotypy_basionym_and_distribution(self):
        homotypic = [r for r in synonyms("2724178", self.wcvp) if r["homotypic"] == "T"]
        self.assertTrue(homotypic)
        bergamia = self.wcvp.get("2724031")
        self.assertEqual(bergamia["basionym_id"], "2906616")
        self.assertEqual(self.wcvp.get("2906616")["name"], "Citrus × limetta var. bergamia")
        self.assertTrue(self.wcvp.distribution("2724178") or self.wcvp.distribution("125188"))

    def test_implicit_trinomial_rows_do_not_pollute_the_binomial_key(self):
        self.assertEqual([r["name"] for r in self.wcvp.lookup("veratrum album virescens")], ["Veratrum album virescens"])
        names = [r["name"] for r in self.wcvp.lookup("veratrum album")]
        self.assertNotIn("Veratrum album virescens", names)

    def test_wfo_uses_original_name_as_basionym_and_has_no_homotypy(self):
        row = self.wfo.get("wfo-0000607952")      # Citrus bergamia
        self.assertEqual(self.wfo.get("wfo-0000607911")["basionym_id"], "wfo-0000607952")
        self.assertEqual(row["homotypic"], "")

    def test_synonyms_lists_names_of_an_accepted(self):
        names = {r["name"] for r in synonyms("2906535", self.wcvp)}
        self.assertIn("Matricaria recutita", names)
        self.assertNotIn("Matricaria chamomilla", names)
        names = {r["name"] for r in synonyms("2906535", self.wcvp, include_self=True)}
        self.assertIn("Matricaria chamomilla", names)


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_matricaria_recutita_is_a_synonym_in_wcvp_and_unresolved_in_wfo(self):
        r = resolve("Matricaria recutita", self.wcvp)
        self.assertEqual((r["outcome"], r["accepted_id"], r["accepted_name"], r["accepted_authors"]),
                         ("synonym", "2906535", "Matricaria chamomilla", "L."))
        self.assertEqual(resolve("Matricaria recutita", self.wfo)["outcome"], "unresolved")
        # El respaldo no se usa: WCVP ya resolvió, y WFO no discrepa porque no resuelve.
        full = resolve_name("Matricaria recutita", self.wcvp, self.wfo)
        self.assertEqual((full["backbone"], full["accepted_id"], full["flags"]), ("wcvp", "2906535", []))

    def test_mentha_x_piperita_autonym(self):
        r = resolve("Mentha x piperita subsp. nothosubsp. piperita", self.wcvp)
        self.assertEqual((r["outcome"], r["accepted_id"], r["accepted_name"], r["accepted_authors"]),
                         ("accepted", "125188", "Mentha × piperita", "L."))
        self.assertIn("autonym", r["flags"])
        for text in ("Mentha × piperita", "Mentha x piperita", "Mentha ×piperita"):
            self.assertEqual(resolve(text, self.wcvp)["accepted_id"], "125188", text)

    def test_almond_with_usda_author_resolves_to_prunus_amygdalus(self):
        r = resolve("Prunus dulcis", self.wcvp, author="(MILLER) D. A. WEBB")
        self.assertEqual((r["outcome"], r["accepted_name"], r["accepted_authors"]), ("synonym", "Prunus amygdalus", "Batsch"))
        self.assertEqual(r["matched_status"], "Illegitimate")
        self.assertIn("author_tiebreak", r["flags"])

    def test_almond_without_author_is_ambiguous_and_not_merged_with_the_cherry(self):
        r = resolve("Prunus dulcis", self.wcvp)
        self.assertEqual(r["outcome"], "ambiguous")
        self.assertIn("homonym_unresolved", r["flags"])
        self.assertEqual(r["accepted_id"], "")
        statuses = sorted(c["status"] for c in r["candidates"])
        self.assertEqual(statuses, ["Illegitimate", "Synonym"])
        self.assertEqual(sorted(c["accepted_name"] for c in r["candidates"]), ["Prunus amygdalus", "Prunus avium"])

    def test_lavandula_angustifolia_with_miller(self):
        r = resolve("Lavandula angustifolia", self.wcvp, author="MILLER")
        self.assertEqual((r["outcome"], r["accepted_id"]), ("accepted", "108971"))
        self.assertIn("homonym_present", r["flags"])
        self.assertIn("author_tiebreak", r["flags"])
        # Sin autor gana el estado Accepted, y el homónimo queda anotado.
        r = resolve("Lavandula angustifolia", self.wcvp)
        self.assertEqual((r["outcome"], r["accepted_id"]), ("accepted", "108971"))
        self.assertIn("homonym_present", r["flags"])
        self.assertNotIn("author_tiebreak", r["flags"])
        # Con el autor del homónimo, la fila ilegítima con aceptado gana el desempate.
        r = resolve("Lavandula angustifolia", self.wcvp, author="Moench")
        self.assertEqual(r["matched_status"], "Illegitimate")

    def test_rosmarinus_officinalis_resolves_to_salvia_rosmarinus(self):
        r = resolve("Rosmarinus officinalis", self.wcvp)
        self.assertEqual((r["outcome"], r["accepted_id"], r["accepted_name"]), ("synonym", "183733", "Salvia rosmarinus"))

    def test_homonym_without_author_between_synonyms_is_ambiguous(self):
        # Mismo caso que el almendro, con la frontera del estado: el Synonym no gana a un Illegitimate con otro aceptado.
        r = resolve("Prunus dulcis", self.wcvp, author="Smith")
        self.assertEqual(r["outcome"], "ambiguous")

    def test_genus_only_and_unmatched(self):
        self.assertEqual(resolve("Gossypium sp", self.wcvp)["outcome"], "genus_only")
        self.assertEqual(resolve("Zzzzus nonexistens", self.wcvp)["outcome"], "unmatched")
        self.assertEqual(resolve("", self.wcvp)["outcome"], "unmatched")

    def test_fallback_to_binomial_is_flagged(self):
        r = resolve("Lavandula latifolia var. inventada", self.wcvp)
        self.assertEqual(r["outcome"], "accepted")
        self.assertTrue(r["fallback_binomial"])
        self.assertIn("fallback_binomial", r["flags"])

    def test_autonym_resolves_as_the_species(self):
        r = resolve("Valeriana officinalis subsp. officinalis", self.wcvp)
        self.assertEqual((r["outcome"], r["accepted_name"]), ("accepted", "Valeriana officinalis"))
        self.assertIn("autonym", r["flags"])

    def test_implicit_trinomial_resolves_to_its_own_row(self):
        r = resolve("Veratrum album virescens", self.wcvp)
        self.assertEqual((r["matched_name"], r["outcome"]), ("Veratrum album virescens", "synonym"))
        self.assertEqual(resolve("Veratrum album", self.wcvp)["accepted_name"], "Veratrum album")


class BackupAndVariantsTest(unittest.TestCase):
    def setUp(self):
        self.wcvp, self.wfo = taxonomy_support.backbones()

    def test_cistus_ladaniferus_resolves_to_ladanifer_not_creticus(self):
        # WFO tiene Cistus ladaniferus Stokes como sinónimo de otra especie: no debe usarse.
        wfo = resolve("Cistus ladaniferus", self.wfo)
        self.assertEqual(wfo["outcome"], "synonym")
        self.assertEqual(wfo["accepted_name"], "Cistus creticus")
        r = resolve_name("Cistus ladaniferus", self.wcvp, self.wfo)
        self.assertEqual((r["backbone"], r["outcome"], r["accepted_id"], r["accepted_name"]),
                         ("wcvp", "accepted", "2723459", "Cistus ladanifer"))
        self.assertEqual(r["accepted_authors"], "L.")
        self.assertIn("orthographic_variant", r["flags"])
        self.assertNotIn("wfo_fallback", r["flags"])

    def test_citrus_meyerii_matches_citrus_x_meyeri(self):
        r = resolve_variants("Citrus meyerii", self.wcvp)
        self.assertEqual((r["outcome"], r["matched_name"], r["accepted_name"]), ("synonym", "Citrus × meyeri", "Citrus × limon"))
        self.assertIn("orthographic_variant", r["flags"])
        self.assertEqual(resolve("Citrus meyerii", self.wcvp)["outcome"], "unmatched")

    def test_variants_are_not_used_when_the_exact_name_resolves(self):
        r = resolve_name("Cistus ladanifer", self.wcvp, self.wfo)
        self.assertNotIn("orthographic_variant", r["flags"])

    def test_wfo_backup_only_when_wcvp_does_not_resolve_and_wfo_gives_one_accepted(self):
        r = resolve_name("Citrus meyerii", self.wcvp, self.wfo, use_variants=False)
        self.assertEqual((r["backbone"], r["outcome"]), ("wfo", "synonym"))
        self.assertTrue(r["accepted_id"].startswith("wfo-"))
        self.assertIn("wfo_fallback", r["flags"])
        self.assertEqual(r["accepted_name"], "Citrus limon")
        # Sin respaldo disponible queda sin resolver.
        self.assertEqual(resolve_name("Citrus meyerii", self.wcvp, None, use_variants=False)["outcome"], "unmatched")

    def test_wfo_does_not_replace_an_ambiguous_wcvp_when_wfo_is_not_unique(self):
        r = resolve_name("Prunus dulcis", self.wcvp, self.wfo)
        # WFO tiene tres filas con distinto aceptado o sin aceptado: no hay un único aceptado.
        self.assertIn(r["outcome"], ("ambiguous", "synonym"))
        if r["outcome"] == "synonym":
            self.assertEqual(r["backbone"], "wfo")

    def test_backbone_disagreement_keeps_the_wcvp_accepted(self):
        r = resolve_name("Veratrum album virescens", self.wcvp, self.wfo)
        self.assertEqual((r["backbone"], r["accepted_name"]), ("wcvp", "Veratrum lobelianum"))
        self.assertIn("backbone_disagreement", r["flags"])
        self.assertTrue(r["accepted_id"].isdigit())       # sin IDs de WFO mezclados
        self.assertEqual(r["wfo_accepted_name"], "Veratrum album")

    def test_genus_only_never_goes_to_the_backup(self):
        self.assertEqual(resolve_name("Gossypium sp", self.wcvp, self.wfo)["outcome"], "genus_only")


if __name__ == "__main__":
    unittest.main()
