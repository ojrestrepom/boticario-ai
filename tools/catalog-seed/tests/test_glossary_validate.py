import copy
import unittest

import support  # noqa: F401
from test_seed import glossary_document, glossary_row

from catalog_seed.glossary_validate import looks_spanish, validate_glossary


def errors(*rows, **kwargs):
    return validate_glossary(glossary_document(*rows), **kwargs)


class SchemaTests(unittest.TestCase):
    def test_valid_glossary(self):
        self.assertEqual(errors(), [])

    def test_missing_top_field_and_wrong_license(self):
        document = glossary_document()
        del document["changes"]
        document["license"] = "CC0"
        found = validate_glossary(document)
        self.assertTrue(any("changes" in e for e in found) and any("license" in e for e in found))

    def test_row_with_extra_or_missing_fields(self):
        row = glossary_row()
        row["extra"] = 1
        self.assertTrue(errors(row))
        row = glossary_row()
        del row["entryUrl"]
        self.assertTrue(errors(row))

    def test_keys_must_be_sorted_and_unique(self):
        document = glossary_document(glossary_row("tónico"), glossary_row("diurético"))
        document["rows"].reverse()
        self.assertIn("las filas no están ordenadas por clave", validate_glossary(document))
        self.assertIn("hay claves repetidas", errors(glossary_row(), glossary_row()))

    def test_key_must_be_the_base_form(self):
        self.assertTrue(any("forma base" in e for e in errors(glossary_row(term="Diurético (veterinario)", key="diurético (veterinario)"))))

    def test_url_must_be_https_with_the_revision(self):
        self.assertTrue(errors(glossary_row(entryUrl="http://es.wiktionary.org/w/index.php?oldid=7")))
        self.assertTrue(errors(glossary_row(entryUrl="https://es.wiktionary.org/wiki/diurético")))

    def test_source_and_mode_consistency(self):
        self.assertTrue(errors(glossary_row(sourceId="otra", sourceName="Otra")))
        self.assertTrue(errors(glossary_row(adapted=True)))  # Wikcionario no puede ser adaptado
        self.assertTrue(errors(glossary_row(sourceId="wikipedia_es", sourceName="Wikipedia", sense=1)))
        self.assertEqual(errors(glossary_row(sourceId="wikipedia_es", sourceName="Wikipedia", sense=None, adapted=True)), [])


class TextTests(unittest.TestCase):
    def test_text_must_end_in_a_period_and_be_normalized(self):
        self.assertTrue(errors(glossary_row(text="Que estimula el apetito")))
        self.assertTrue(errors(glossary_row(text="Que  estimula el apetito.")))
        self.assertTrue(errors(glossary_row(text="")))

    def test_text_must_be_spanish(self):
        self.assertTrue(looks_spanish("Que aumenta o facilita la producción y excreción de orina."))
        self.assertFalse(looks_spanish("That increases urine production."))
        self.assertFalse(looks_spanish("Это мочегонное средство."))
        self.assertTrue(any("español" in e for e in errors(glossary_row(text="That increases urine production."))))

    def test_dose_is_an_error_and_cannot_be_approved(self):
        for text in ("Una sustancia dependiente de la dosis.", "Tomar 5 mg al día.", "Se usa en gotas de agua.", "Según la posología."):
            row = glossary_row(text=text)
            self.assertTrue(errors(row), text)
            approved = {row["term"]: [{"pattern": "dosis", "reason": "x"}, {"pattern": "mg", "reason": "x"}]}
            self.assertTrue([e for e in errors(row, approved=approved) if "dosis o posología" in e], text)

    def test_efficacy_pattern_without_approval(self):
        found = errors(glossary_row("bactericida", "Que elimina las bacterias o los microbios."))
        self.assertEqual(len(found), 1)
        self.assertIn("«elimina»", found[0])

    def test_efficacy_pattern_approved_for_that_term_only(self):
        row = glossary_row("bactericida", "Que elimina las bacterias o los microbios.")
        approved = {"Bactericida": [{"pattern": "elimina", "reason": "aprobado"}]}
        self.assertEqual(errors(row, approved=approved), [])
        other = glossary_row("fungicida", "Que elimina los hongos.")
        self.assertTrue(errors(other, approved=approved))
        mixed = glossary_row("bactericida", "Que elimina y cura las bacterias.")
        self.assertIn("«cura»", " ".join(errors(mixed, approved=approved)))

    def test_serious_disease_in_text(self):
        found = errors(glossary_row("emoliente", "Se usa para ablandar durezas, tumores o similares."))
        self.assertTrue(any("enfermedad grave" in e and "tumores" in e for e in found))
        self.assertTrue(errors(glossary_row(text="Contra el cáncer.")))

    def test_sensitive_term(self):
        self.assertTrue(any("sensible" in e for e in errors(glossary_row("cancer", "Que estimula el apetito."))))


class SourceCheckTests(unittest.TestCase):
    def terms(self, **changes):
        term = {"activity": "Diurético", "wiktionaryTitle": "diurético", "source": "wiktionary_es", "sense": 1, "reason": "r",
                "approved": {"by": "usuario", "date": "2026-10-29"}}
        term.update(changes)
        return {"terms": [term], "approvedPatterns": {}}

    def test_row_must_be_in_the_list_and_approved(self):
        self.assertTrue(any("no figura" in e for e in errors(glossary_row("tónico"), terms=self.terms())))
        unapproved = self.terms()
        del unapproved["terms"][0]["approved"]
        self.assertTrue(any("aprobación" in e for e in errors(terms=unapproved)))

    def test_source_and_mode_must_match_the_list(self):
        self.assertTrue(any("no coinciden" in e for e in errors(terms=self.terms(source="wikipedia_es", mode="literal", wikipediaTitle="D"))))

    def test_adapted_text_must_equal_the_one_in_the_list(self):
        terms = self.terms(source="wikipedia_es", mode="adapted", text="Otro texto.", evidence="x", wikipediaTitle="Diurético")
        terms["terms"][0].pop("sense")
        row = glossary_row(sourceId="wikipedia_es", sourceName="Wikipedia", sense=None, adapted=True)
        self.assertTrue(any("adaptado no coincide" in e for e in validate_glossary(glossary_document(row), terms=terms)))

    def test_literal_text_against_the_cache(self):
        import json
        import os
        import tempfile
        from catalog_seed.wiki import WiktionaryStep
        from test_glossary_extract import load
        with tempfile.TemporaryDirectory() as tmp:
            step = WiktionaryStep(cache_dir=tmp)
            record = load("wiktionary-diurético.json")
            step.store("diurético", dict(record, revid=7))
            row = glossary_row()
            self.assertEqual(validate_glossary(glossary_document(row), self.terms(), tmp), [])
            altered = glossary_row(text="Que aumenta la orina.")
            found = validate_glossary(glossary_document(altered), self.terms(), tmp)
            self.assertTrue(any("no es literal" in e for e in found))
            self.assertTrue(any("revisión" in e for e in validate_glossary(glossary_document(glossary_row(revisionId=8, entryUrl="https://x/?oldid=8")), self.terms(), tmp)))

    def test_adapted_evidence_must_be_in_the_extract(self):
        import tempfile
        from catalog_seed.wiki import WikipediaArticleStep
        from test_glossary_extract import load
        article = load("wikipedia-Estimulante.json")
        with tempfile.TemporaryDirectory() as tmp:
            WikipediaArticleStep(cache_dir=tmp).store("Estimulante", dict(article, revid=7))
            row = glossary_row("estimulante", "Sustancia que aumenta la vigilia.", sourceId="wikipedia_es", sourceName="Wikipedia", sense=None, adapted=True)
            good = {"terms": [{"activity": "Estimulante", "wiktionaryTitle": "estimulante", "wikipediaTitle": "Estimulante", "source": "wikipedia_es",
                               "mode": "adapted", "text": row["text"], "evidence": "refuerza la vigilia, el estado de alerta", "reason": "r",
                               "approved": {"by": "u", "date": "2026-10-29"}}], "approvedPatterns": {}}
            self.assertEqual(validate_glossary(glossary_document(row), good, tmp), [])
            bad = copy.deepcopy(good)
            bad["terms"][0]["evidence"] = "no figura en el extracto"
            self.assertTrue(any("evidencia" in e for e in validate_glossary(glossary_document(row), bad, tmp)))


if __name__ == "__main__":
    unittest.main()
