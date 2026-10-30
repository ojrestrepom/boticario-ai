import json
import os
import unittest

import support  # noqa: F401

from catalog_seed.glossary_extract import (
    article_first_sentence, article_intro, entry_status, first_sentence, length_problem, parse_wiktionary, sense_text,
)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "glossary")


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return json.load(handle)


def senses(title):
    return parse_wiktionary(load("wiktionary-%s.json" % title)["html"])


class WiktionaryParsingTests(unittest.TestCase):
    def test_anodino_has_four_senses_and_only_the_last_is_medical(self):
        parsed = senses("anodino")
        self.assertEqual([(s["n"], s["mark"]) for s in parsed["senses"]], [(1, ""), (2, ""), (3, ""), (4, "Medicina")])
        self.assertEqual(parsed["senses"][3]["text"], "Dicho de un medicamento: Que mitiga el dolor.")
        self.assertEqual(parsed["senses"][2]["text"], "Sin gracia, soso.")  # el «Uso: figurado» y los ejemplos no entran
        self.assertFalse(parsed["flexed"])

    def test_sense_text_is_the_literal_first_sentence(self):
        self.assertEqual(sense_text(load("wiktionary-anodino.json"), 4), "Dicho de un medicamento: Que mitiga el dolor.")
        self.assertIsNone(sense_text(load("wiktionary-anodino.json"), 9))

    def test_estomacal_keeps_only_the_spanish_section(self):
        parsed = senses("estomacal")
        self.assertIn("Catalán", parsed["languages"])
        self.assertEqual([s["n"] for s in parsed["senses"]], [1, 2])
        self.assertEqual(parsed["senses"][1]["text"], "Que fortalece al estómago, y favorece la digestión.")

    def test_tonico_marks_the_medical_sense_third(self):
        parsed = senses("tónico")
        self.assertEqual([s["mark"] for s in parsed["senses"]], ["", "", "Medicina", "Música", "Lingüística", "Cosmética"])
        self.assertEqual(parsed["senses"][2]["text"], "Que provoca o favorece el tono de un músculo, de un órgano, o del metabolismo en general.")
        self.assertEqual(parsed["senses"][0]["pos"], "Adjetivo")
        self.assertEqual(parsed["senses"][5]["pos"], "Sustantivo masculino")

    def test_astringente_first_sense_has_two_sentences_and_is_trimmed(self):
        record = load("wiktionary-astringente.json")
        full = parse_wiktionary(record["html"])["senses"][0]["text"]
        self.assertIn("Las disoluciones de sales minerales", full)
        trimmed = sense_text(record, 1)
        self.assertTrue(trimmed.endswith("y otras secreciones."))
        self.assertNotIn("sales minerales", trimmed)

    def test_inflected_form_entry_is_detected(self):
        parsed = senses("vermífuga")
        self.assertTrue(parsed["flexed"])
        self.assertEqual(parsed["senses"][0]["text"], "Forma del femenino de vermífugo.")
        self.assertEqual(entry_status(load("wiktionary-vermífuga.json")), "forma-flexionada")

    def test_missing_entry(self):
        self.assertEqual(entry_status(load("wiktionary-vermífugo.json")), "sin-entrada")

    def test_entry_status_with_senses(self):
        self.assertEqual(entry_status(load("wiktionary-anodino.json")), "con-acepciones")

    def test_entry_without_spanish_section(self):
        html = '<div class="mw-parser-output"><div class="mw-heading mw-heading2"><h2 id="Italiano">Italiano</h2></div><dl><dt>1</dt><dd>x.</dd></dl></div>'
        self.assertEqual(entry_status({"html": html}), "sin-español")

    def test_note_marks_and_synonym_lists_are_removed(self):
        html = ('<div class="mw-parser-output"><div class="mw-heading mw-heading2"><h2>Español</h2></div>'
                '<dl><dt>1</dt><dd>Que cura<sup class="reference">[1]</sup> <i>bien</i>.<ul><li><b>Sinónimos:</b> a, b.</li></ul></dd></dl></div>')
        self.assertEqual(parse_wiktionary(html)["senses"][0]["text"], "Que cura bien.")

    def test_one_list_with_several_senses(self):
        html = ('<div class="mw-parser-output"><div class="mw-heading mw-heading2"><h2>Español</h2></div>'
                '<dl><dt>1</dt><dd>Uno.</dd><dt>2 Medicina</dt><dd>Dos.</dd></dl></div>')
        self.assertEqual([(s["n"], s["mark"], s["text"]) for s in parse_wiktionary(html)["senses"]], [(1, "", "Uno."), (2, "Medicina", "Dos.")])


class FirstSentenceTests(unittest.TestCase):
    def test_trims_at_the_first_period(self):
        self.assertEqual(first_sentence("Una cosa. Otra cosa."), "Una cosa.")

    def test_abbreviations_do_not_end_the_sentence(self):
        self.assertEqual(first_sentence("Sirve, p. ej. para algo. Otra."), "Sirve, p. ej. para algo.")
        self.assertEqual(first_sentence("Se dice de sales, etc., que sirven. Otra."), "Se dice de sales, etc., que sirven.")
        self.assertEqual(first_sentence("Fue en el 300 a. C. y siguió. Fin."), "Fue en el 300 a. C. y siguió.")

    def test_etc_that_closes_the_sentence(self):
        self.assertEqual(first_sentence("Sales, hierbas, etc. Otra cosa."), "Sales, hierbas, etc.")

    def test_initials_and_decimals(self):
        self.assertEqual(first_sentence("J. Duke midió 2.5 gramos. Fin."), "J. Duke midió 2.5 gramos.")

    def test_no_period_returns_the_whole_text(self):
        self.assertEqual(first_sentence("Que destruye a los insectos"), "Que destruye a los insectos")

    def test_spaces_are_normalized_and_notes_removed(self):
        self.assertEqual(first_sentence("Un  estimulante es una sustancia[1]. Otra."), "Un estimulante es una sustancia.")

    def test_length_problems(self):
        self.assertIsNone(length_problem("Que estimula el apetito."))
        self.assertIn("punto", length_problem("Que destruye a los insectos"))
        self.assertIn("corta", length_problem("Somnífero."))
        self.assertIn("larga", length_problem("a" * 300 + "."))


class WikipediaExtractTests(unittest.TestCase):
    def test_first_sentence_normalizes_double_spaces(self):
        sentence = article_first_sentence(load("wikipedia-Estimulante.json"))
        self.assertTrue(sentence.startswith("Un estimulante (del verbo latino stimulāre)"))
        self.assertNotIn("  ", sentence)

    def test_intro_paragraphs(self):
        paragraphs = article_intro(load("wikipedia-Hipnótico.json"))
        self.assertTrue(paragraphs[0].startswith("Para el estado psicológico"))
        self.assertTrue(paragraphs[1].startswith("Un hipnótico"))

    def test_missing_article_has_no_intro(self):
        self.assertEqual(article_intro(load("wikipedia-Alterativo.json")), [])
        self.assertIsNone(article_first_sentence(load("wikipedia-Alterativo.json")))


if __name__ == "__main__":
    unittest.main()
