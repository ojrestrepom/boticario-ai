import copy
import json
import os
import tempfile
import unittest

import support  # noqa: F401

from catalog_seed.glossary_terms import (
    GlossaryTermsError, DEFAULT_TERMS_FILE, base_key, is_sensitive, load_terms, text_alerts, validate_terms, write_terms,
)


def doc(**changes):
    document = {"version": 1, "description": "x",
                "terms": [{"activity": "Diurético", "wiktionaryTitle": "diurético"},
                          {"activity": "Tónico", "wiktionaryTitle": "tónico", "source": "wiktionary_es", "sense": 3, "reason": "r"},
                          {"activity": "Estimulante", "wiktionaryTitle": "estimulante", "wikipediaTitle": "Estimulante",
                           "source": "wikipedia_es", "mode": "adapted", "text": "Sustancia que estimula.", "evidence": "es una sustancia", "reason": "r"},
                          {"activity": "Piscicida", "wiktionaryTitle": "piscicida", "wikipediaTitle": "Piscicida",
                           "source": "wikipedia_es", "mode": "literal", "reason": "r"}],
                "excluded": [{"activity": "Vermífugo", "code": "sin-entrada", "reason": "sin entrada", "date": "2026-10-29"}],
                "approvedPatterns": {"Tónico": [{"pattern": "provoca", "reason": "x"}]}}
    document.update(changes)
    return document


class BaseKeyTests(unittest.TestCase):
    def test_form_before_parenthesis_lowercase_nfc(self):
        self.assertEqual(base_key("Antídoto (escorpión)"), "antídoto")
        self.assertEqual(base_key("  Estimulante   (veterinario)"), "estimulante")
        self.assertEqual(base_key("Tónico"), "tónico")
        self.assertEqual(base_key("Tónico"), "tónico")  # NFC
        self.assertNotEqual(base_key("Tonico"), base_key("Tónico"))  # no quita acentos


class ValidationTests(unittest.TestCase):
    def test_valid_document(self):
        validate_terms(doc())

    def test_sensitive_term_is_rejected(self):
        for activity in ("Cancer", "Diabetes (tipo 2)", "Uso tradicional, sin eficacia demostrada: cáncer"):
            document = doc()
            document["terms"][0]["activity"] = activity
            with self.assertRaises(GlossaryTermsError) as ctx:
                validate_terms(document)
            self.assertIn(activity, str(ctx.exception))

    def test_is_sensitive(self):
        self.assertTrue(is_sensitive("Cancer"))
        self.assertTrue(is_sensitive("Cancer(Breast)"))
        self.assertFalse(is_sensitive("Diurético"))

    def test_duplicates_are_rejected(self):
        document = doc()
        document["terms"].append({"activity": "diurético (veterinario)", "wiktionaryTitle": "otro"})
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_term_and_exclusion_at_once(self):
        document = doc()
        document["excluded"].append({"activity": "Tónico", "code": "vaga", "reason": "r", "date": "2026-10-29"})
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_exclusion_needs_reason_code_and_date(self):
        for field in ("reason", "code", "date"):
            document = doc()
            del document["excluded"][0][field]
            with self.assertRaises(GlossaryTermsError):
                validate_terms(document)
        document = doc()
        document["excluded"][0]["code"] = "porque-si"
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_proposal_needs_a_reason(self):
        document = doc()
        del document["terms"][1]["reason"]
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_wiktionary_sense_must_be_a_positive_integer(self):
        for bad in (0, "3", None, True):
            document = doc()
            document["terms"][1]["sense"] = bad
            with self.assertRaises(GlossaryTermsError):
                validate_terms(document)

    def test_adapted_text_needs_text_and_evidence(self):
        for field in ("text", "evidence"):
            document = doc()
            del document["terms"][2][field]
            with self.assertRaises(GlossaryTermsError):
                validate_terms(document)

    def test_literal_wikipedia_term_carries_no_text(self):
        document = doc()
        document["terms"][3]["text"] = "inventado"
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_wikipedia_term_needs_a_title_and_a_mode(self):
        for field in ("wikipediaTitle", "mode"):
            document = doc()
            del document["terms"][3][field]
            with self.assertRaises(GlossaryTermsError):
                validate_terms(document)

    def test_wiktionary_term_has_no_text_or_mode(self):
        document = doc()
        document["terms"][1]["text"] = "inventado"
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_pending_term_cannot_carry_proposal_fields(self):
        document = doc()
        document["terms"][0]["sense"] = 1
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_approved_pattern_must_belong_to_a_term(self):
        document = doc(approvedPatterns={"Fantasma": [{"pattern": "x", "reason": "y"}]})
        with self.assertRaises(GlossaryTermsError):
            validate_terms(document)

    def test_version_and_terms_are_required(self):
        with self.assertRaises(GlossaryTermsError):
            validate_terms(doc(version=2))
        with self.assertRaises(GlossaryTermsError):
            validate_terms(doc(terms=[]))

    def test_write_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "terms.json")
            write_terms(doc(), path)
            self.assertEqual(load_terms(path), doc())

    def test_load_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GlossaryTermsError):
                load_terms(os.path.join(tmp, "no-existe.json"))
            path = os.path.join(tmp, "malo.json")
            with open(path, "w") as handle:
                handle.write("{")
            with self.assertRaises(GlossaryTermsError):
                load_terms(path)


class AlertTests(unittest.TestCase):
    def test_plain_definition_has_no_alerts(self):
        self.assertEqual(text_alerts("Que aumenta o facilita la producción y excreción de orina."), [])

    def test_watched_efficacy_patterns(self):
        self.assertIn("patrón vigilado «elimina»", text_alerts("Que elimina las bacterias o los microbios."))
        self.assertIn("patrón vigilado «prevenir»", text_alerts("Capaz de prevenir las infecciones microbianas."))
        self.assertIn("patrón vigilado «curar»", text_alerts("Tiene propiedades beneficiosas para curar heridas o llagas."))
        self.assertTrue(text_alerts("Fármaco empleado para tratar la tos."))

    def test_dose_patterns(self):
        self.assertTrue(text_alerts("Una sustancia dependiente de la dosis."))
        self.assertTrue(text_alerts("Tomar 5 mg al día."))

    def test_serious_diseases(self):
        alerts = text_alerts("Para ablandar durezas, tumores o similares.")
        self.assertIn("enfermedad grave «tumores»", alerts)
        self.assertTrue(text_alerts("Contra el cáncer."))
        self.assertTrue(text_alerts("Contra la diabetes."))

    def test_alerts_are_not_repeated(self):
        self.assertEqual(len(text_alerts("elimina y elimina")), 1)


class SharedFileTests(unittest.TestCase):
    def test_the_versioned_list_is_valid_and_has_no_pending_terms(self):
        document = load_terms(DEFAULT_TERMS_FILE)
        self.assertTrue(all("source" in t for t in document["terms"]))
        keys = [base_key(t["activity"]) for t in document["terms"]] + [base_key(e["activity"]) for e in document["excluded"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_approved_patterns_are_the_six_the_user_approved(self):
        document = load_terms(DEFAULT_TERMS_FILE)
        self.assertEqual(set(document["approvedPatterns"]),
                         {"Antiséptico", "Bactericida", "Vulnerario", "Antidiarreico", "Fungicida", "Parasiticida"})

    def test_every_literal_term_has_a_clean_text_or_an_approved_pattern(self):
        # Garantiza con la lista real que ninguna propuesta literal trae un patrón sin aprobar.
        from catalog_seed.glossary_review import _row
        cache = os.path.join(support.TOOL_DIR, "..", "..", "data", ".cache")
        if not os.path.isdir(os.path.join(cache, "wiktionary_es")):
            self.skipTest("la caché de descargas no está en este equipo")
        document = load_terms(DEFAULT_TERMS_FILE)
        for term in document["terms"]:
            row = _row(term, cache, document["approvedPatterns"])
            self.assertFalse([a for a in row["alerts"] if "SIN APROBAR" in a or "NO ES LITERAL" in a], term["activity"])


if __name__ == "__main__":
    unittest.main()
