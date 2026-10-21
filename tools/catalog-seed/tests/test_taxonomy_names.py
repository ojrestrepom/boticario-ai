import unittest

import taxonomy_support  # noqa: F401
from catalog_seed.taxonomy import (author_score, authors_match, canonical_rank, epithet_variants, parse_name, plant_slug,
                                   slug, split_source_names)


class ParseNameTest(unittest.TestCase):
    def test_hybrid_spellings_share_key_and_flag(self):
        keys = set()
        for text in ("Mentha × piperita", "Mentha x piperita", "Mentha ×piperita", "Mentha X piperita"):
            p = parse_name(text)
            self.assertTrue(p.ok, text)
            self.assertTrue(p.hybrid, text)
            self.assertIn("hybrid", p.flags)
            keys.add(p.key_full)
        self.assertEqual(keys, {"mentha piperita"})
        self.assertEqual(parse_name("Citrus limon").key_full, parse_name("Citrus × limon").key_full)
        self.assertFalse(parse_name("Citrus limon").hybrid)

    def test_genus_level_hybrid_and_chimera(self):
        p = parse_name("× Cupressocyparis leylandii")
        self.assertEqual((p.key_full, p.hybrid), ("cupressocyparis leylandii", True))
        p = parse_name("+ Crataegomespilus dardari")
        self.assertTrue(p.chimera)
        self.assertIn("chimera", p.flags)
        self.assertEqual(p.key_full, "crataegomespilus dardari")

    def test_canonical_ranks(self):
        cases = {
            "Poa annua ssp. reptans": "poa annua subsp. reptans",
            "Poa annua subsp. reptans": "poa annua subsp. reptans",
            "Poa annua var. reptans": "poa annua var. reptans",
            "Poa annua forma reptans": "poa annua f. reptans",
            "Poa annua f. reptans": "poa annua f. reptans",
            "Poa annua nothosubsp. reptans": "poa annua subsp. reptans",
            "Poa annua nothovar. reptans": "poa annua var. reptans",
            "Poa annua prol. reptans": "poa annua prol. reptans",
            "Poa annua lus. reptans": "poa annua lus. reptans",
            "Poa annua convar. reptans": "poa annua convar. reptans",
            "Poa annua subvar. reptans": "poa annua subvar. reptans",
            "Poa annua subf. reptans": "poa annua subf. reptans",
            "Poa annua unranked reptans": "poa annua unranked reptans",
        }
        for text, key in cases.items():
            self.assertEqual(parse_name(text).key_full, key, text)

    def test_last_marker_counts(self):
        p = parse_name("Mentha x piperita subsp. nothosubsp. piperita")
        self.assertEqual((p.infra_rank, p.infra_epithet), ("subsp.", "piperita"))
        p = parse_name("Mentha arvensis var. nothosubsp. piperascens")
        self.assertEqual(p.key_full, "mentha arvensis subsp. piperascens")

    def test_glued_markers(self):
        self.assertEqual(parse_name("Mentha arvensisvar.piperascens").key_full, "mentha arvensis var. piperascens")
        self.assertEqual(parse_name("Mentha arvensis var.piperascens").key_full, "mentha arvensis var. piperascens")
        # Caso ambiguo resuelto con la pista GENUS+SPECIES.
        self.assertEqual(parse_name("Acorus calamusssp.gramineus", hint="Acorus calamus").key_full,
                         "acorus calamus subsp. gramineus")

    def test_implicit_trinomial_does_not_pollute_binomial(self):
        p = parse_name("Veratrum album virescens")
        self.assertEqual(p.key_full, "veratrum album virescens")
        self.assertEqual(p.key_binomial, "veratrum album")
        self.assertIn("implicit_infra", p.flags)
        # Una partícula de autor en minúscula no es un epíteto.
        p = parse_name("Rosa canina ex L.")
        self.assertEqual(p.key_full, "rosa canina")
        self.assertNotIn("implicit_infra", p.flags)

    def test_autonym(self):
        p = parse_name("Valeriana officinalis subsp. officinalis")
        self.assertIn("autonym", p.flags)
        self.assertEqual(p.key_full, "valeriana officinalis")
        self.assertEqual(p.key_alt, "valeriana officinalis subsp. officinalis")
        p = parse_name("Mentha x piperita subsp. nothosubsp. piperita")
        self.assertEqual((p.key_full, p.key_alt), ("mentha piperita", "mentha piperita subsp. piperita"))

    def test_glued_author(self):
        p = parse_name("Lavandula roseaL.")
        self.assertEqual((p.species, p.author), ("rosea", "L."))
        self.assertEqual(p.key_full, "lavandula rosea")

    def test_infraspecific_author_wins(self):
        p = parse_name("Poa annua L. var. reptans Hausskn.")
        self.assertEqual(p.key_full, "poa annua var. reptans")
        self.assertEqual((p.author, p.species_author), ("Hausskn.", "L."))

    def test_author_kept_when_parenthesis_is_part_of_it(self):
        self.assertEqual(parse_name("Aloe vera (L.) Burm.f.").author, "(L.) Burm.f.")
        self.assertEqual(parse_name("Prunus dulcis (Mill.) D.A.Webb").author, "(Mill.) D.A.Webb")

    def test_trailing_parenthesis_qualifier_is_removed(self):
        for text in ("Citrus limon (lemon)", "Achillea millefolium (Common Yarrow)"):
            p = parse_name(text)
            self.assertIn("qualifier_removed", p.flags, text)
            self.assertEqual(p.author, "", text)

    def test_qualifiers_and_cultivars_are_removed_with_flag(self):
        for text in ("Achillea millefolium aggr.", "Achillea millefolium agg.", "Achillea millefolium s.str.",
                     "Achillea millefolium s.l.", "Achillea millefolium sensu lato", "Achillea millefolium sensu stricto"):
            p = parse_name(text)
            self.assertEqual(p.key_full, "achillea millefolium", text)
            self.assertIn("qualifier_removed", p.flags, text)
        for text in ("Mentha x piperita 'Mitcham'", "Mentha x piperita cv. Mitcham"):
            p = parse_name(text)
            self.assertEqual(p.key_full, "mentha piperita", text)
            self.assertIn("cultivar_removed", p.flags, text)
        # El autor «S.L.Welsh» no es un calificador.
        self.assertNotIn("qualifier_removed", parse_name("Astragalus foo S.L.Welsh").flags)

    def test_genus_only(self):
        for text in ("Gossypium sp", "Gossypium sp.", "Gossypium spp", "Gossypium spp.", "Gossypium"):
            p = parse_name(text)
            self.assertTrue(p.genus_only, text)
            self.assertFalse(p.ok, text)
            self.assertIn("genus_only", p.flags)

    def test_case_nfc_quotes_and_entities(self):
        self.assertEqual(parse_name('"LAVANDULA  angustifolia"').key_full, "lavandula angustifolia")
        self.assertEqual(parse_name("Café foó bar").genus, "café")  # NFC
        p = parse_name("Rosa canina L. &amp; Sm.")
        self.assertIn("&", p.author)
        self.assertNotIn("&amp;", p.author)

    def test_capitalized_infraspecific_epithet_is_flagged(self):
        p = parse_name("Poa annua var. Italica")
        self.assertEqual(p.key_full, "poa annua var. italica")
        self.assertIn("capitalized_epithet", p.flags)

    def test_hybrid_formula_is_not_interpretable(self):
        p = parse_name("Mentha aquatica x spicata")
        self.assertFalse(p.ok)
        self.assertIn("hybrid_formula", p.flags)

    def test_canonical_rank_function(self):
        self.assertEqual(canonical_rank("ssp."), "subsp.")
        self.assertEqual(canonical_rank("var"), "var.")
        self.assertIsNone(canonical_rank("f"))   # sin punto sería una inicial
        self.assertEqual(canonical_rank("f."), "f.")
        self.assertIsNone(canonical_rank("L."))


class SplitSourceNamesTest(unittest.TestCase):
    def test_ema_semicolon_and_html_entities(self):
        cell = "Crataegus monogyna Jacq.; Crataegus laevigata (Poir.) DC.; Foo bar Smith &amp; Jones"
        self.assertEqual(split_source_names("ema", cell), [
            "Crataegus monogyna Jacq.", "Crataegus laevigata (Poir.) DC.", "Foo bar Smith & Jones"])

    def test_ema_comma_only_when_next_looks_like_a_name(self):
        out = split_source_names("ema", "Crataegus monogyna Jacq., Lindm.; Matricaria recutita L., Chamomilla recutita (L.) Rauschert")
        self.assertEqual(out, ["Crataegus monogyna Jacq., Lindm.", "Matricaria recutita L.",
                               "Chamomilla recutita (L.) Rauschert"])

    def test_ema_abbreviated_genus_expanded_from_nearest_in_cell(self):
        out = split_source_names("ema", "Crataegus monogyna Jacq.; C. azarolus L.; Prunus dulcis; P. avium")
        self.assertEqual(out, ["Crataegus monogyna Jacq.", "Crataegus azarolus L.", "Prunus dulcis", "Prunus avium"])
        out = split_source_names("ema", "C. azarolus L., Crataegus monogyna Jacq.")
        self.assertEqual(out[0], "Crataegus azarolus L.")

    def test_ema_syn_combination_and_short_fragments(self):
        out = split_source_names("ema", "syn. Mentha foo L.; Combination: Mentha x Salvia; ab; Mentha bar L.")
        self.assertEqual(out, ["Mentha foo L.", "Mentha bar L."])

    def test_efsa_semicolon_and_dollar(self):
        out = split_source_names("efsa", "Mentha piperita L.$M. spicata L.;Salvia officinalis L., Smith")
        self.assertEqual(out, ["Mentha piperita L.", "Mentha spicata L.", "Salvia officinalis L., Smith"])

    def test_other_sources_one_name_per_cell(self):
        self.assertEqual(split_source_names("usda", ' "Mentha  x piperita" '), ["Mentha x piperita"])
        self.assertEqual(split_source_names("tppt", "Foo bar; baz"), ["Foo bar; baz"])
        self.assertEqual(split_source_names("usda", "  "), [])


class AuthorTest(unittest.TestCase):
    def test_surname_prefix_and_linnaeus(self):
        self.assertEqual(author_score("MILLER", "Mill."), 1.0)
        self.assertEqual(author_score("HUDSON", "Huds."), 1.0)
        for variant in ("L.", "Linn.", "Linnaeus", "Linné"):
            self.assertEqual(author_score(variant, "L."), 1.0, variant)
        self.assertEqual(author_score("L.", "Mill."), 0.0)

    def test_basionym_and_combination_are_compared_separately(self):
        self.assertEqual(author_score("(MILLER) D. A. WEBB", "(Mill.) D.A.Webb"), 1.0)
        self.assertEqual(author_score("(MILLER) D. A. WEBB", "Rouchy"), 0.0)
        self.assertEqual(author_score("(L.) Burm.f.", "(L.) Burm. f."), 1.0)
        self.assertTrue(authors_match("Mill.", "(L.) Mill."))
        self.assertFalse(authors_match("Moench", "Mill."))

    def test_ex_and_ampersand_and_initials_are_ignored(self):
        self.assertEqual(author_score("Nees ex Bluff & Fingerh.", "Bluff & Fingerh."), 2 / 3.0)
        self.assertEqual(author_score("J.F.Gmel.", "Gmel."), 1.0)

    def test_short_prefix_needs_three_letters(self):
        self.assertEqual(author_score("Mi", "Mill."), 0.0)


class VariantsTest(unittest.TestCase):
    def test_variants_cover_the_documented_pairs(self):
        self.assertIn("ladanifer", epithet_variants("ladaniferus"))
        self.assertIn("meyeri", epithet_variants("meyerii"))
        self.assertIn("meyerii", epithet_variants("meyeri"))
        self.assertIn("canadiensis", epithet_variants("canadensis"))
        self.assertIn("cerulea", epithet_variants("caerulea"))
        self.assertIn("angustifolius", epithet_variants("angustifolia"))
        self.assertNotIn("ladaniferus", epithet_variants("ladaniferus"))


class SlugTest(unittest.TestCase):
    def test_shared_cases_with_the_backend(self):
        # Los mismos casos que SLUG_CASES de backend/catalog-core/src/normalize.rs.
        for text, expected in (
                ("Lavandula angustifolia", "lavandula-angustifolia"),
                ("Lavándula   Angustifolia ", "lavandula-angustifolia"),
                ("Mentha x piperita subsp. nothosubsp. piperita", "mentha-x-piperita-subsp-nothosubsp-piperita"),
                ("--Aloe (vera)--", "aloe-vera"), ("Ñandú", "nandu"), ("", ""), ("   ", ""), ("!!!", "")):
            self.assertEqual(slug(text), expected, text)

    def test_hybrid_sign_is_x(self):
        self.assertEqual(plant_slug("Mentha × piperita"), "mentha-x-piperita")
        self.assertEqual(plant_slug("Rosmarinus × lavandulaceus"), "rosmarinus-x-lavandulaceus")
        self.assertEqual(plant_slug("Salvia rosmarinus"), "salvia-rosmarinus")
        self.assertEqual(plant_slug("Citrus × aurantium f. aurantium"), "citrus-x-aurantium-f-aurantium")
        self.assertEqual(plant_slug("Mentha x piperita subsp. nothosubsp. piperita"),
                         "mentha-x-piperita-subsp-nothosubsp-piperita")


if __name__ == "__main__":
    unittest.main()
