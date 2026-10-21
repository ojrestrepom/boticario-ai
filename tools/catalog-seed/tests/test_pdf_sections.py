import unittest

import extract_support as support
from catalog_seed import pdf_sections
from catalog_seed.pdf_sections import NO_SAFETY_NOTE, sections_from_lines


def line(text, col="single", page=1):
    return {"page": page, "text": text, "col": col}


class SectionsFromLinesTests(unittest.TestCase):
    LINES = [
        line("4.2. Posology and method of administration"),
        line("See section 4.4. 'Special warnings'"),                       # referencia cruzada: no es encabezado
        line("4.3. Contraindications"),
        line("Hypersensitivity.", "left"), line("Hypersensitivity to plants of the Asteraceae.", "right"),
        line("Well-established use Traditional use"),                       # cabecera de columna repetida
        line("Children under 12.", "right", 2),
        line("4.4. Special warnings and precautions for use"),
        line("Consult a doctor.", "right"),
        line("4.5. Interactions with other medicinal products and", page=2),
        line("other forms of interaction", page=2),
        line("None reported.", "right", 2),
        line("4.6. Fertility, pregnancy and lactation", page=2),
        line("Not recommended.", "single", 2),
    ]

    def test_sections_by_column_with_numbering(self):
        result = sections_from_lines(self.LINES)["sections"]
        self.assertEqual(sorted(result), ["4.3", "4.4", "4.5"])
        self.assertEqual(result["4.3"]["columns"], {"well_established_use": "Hypersensitivity.",
                                                    "traditional_use": "Hypersensitivity to plants of the Asteraceae. Children under 12."})
        self.assertEqual(result["4.3"]["page_to"], 2)
        self.assertEqual(result["4.5"]["columns"], {"traditional_use": "None reported."})
        self.assertEqual(result["4.5"]["heading"], pdf_sections.SECTION_TITLES["4.5"])

    def test_single_column_documents_have_plain_text(self):
        lines = [line("4.3. Contraindications"), line("None known."), line("4.4. Special warnings and precautions for use"), line("A."), line("4.5. Interactions with other medicinal products and other forms of interaction"), line("B.")]
        result = sections_from_lines(lines)["sections"]
        self.assertEqual(result["4.3"]["text"], "None known.")
        self.assertEqual(result["4.5"]["columns"], {"single_column": "B."})

    def test_public_statement_conclusions_and_safety_flag(self):
        none = sections_from_lines([line("Assessment"), line("CONCLUSIONS"), line("A monograph cannot be established unless new data are provided.")])
        self.assertEqual(none["sections"], {})
        self.assertFalse(none["statement"]["safety_data"])
        some = sections_from_lines([line("CONCLUSIONS"), line("Contraindications: hypersensitivity. Interactions have been reported.")])
        self.assertTrue(some["statement"]["safety_data"])
        self.assertTrue(NO_SAFETY_NOTE.startswith("declaración pública"))

    def test_document_without_sections_or_conclusions(self):
        self.assertEqual(sections_from_lines([line("Something")]), {"sections": {}, "statement": None})

    def test_cross_references_without_dot_are_not_headings(self):
        result = sections_from_lines([line("4.4 'Special warnings and precautions for use' applies"), line("text")])
        self.assertEqual(result["sections"], {})


class SamplePdfTests(unittest.TestCase):
    def setUp(self):
        support.require_module(self, "pdfminer", "pdfminer.six")

    def test_monograph_columns_footnote_and_cross_reference(self):
        result = pdf_sections.extract_pdf(support.fixture("sample_monograph.pdf"))
        sections = result["sections"]
        self.assertEqual(sorted(sections), ["4.3", "4.4", "4.5"])
        self.assertEqual(sections["4.3"]["columns"]["well_established_use"], "Hypersensitivity to the active substance.")
        self.assertEqual(sections["4.3"]["columns"]["traditional_use"], "Hypersensitivity to plants of the Asteraceae. Children under 12 years.")
        self.assertEqual(sections["4.4"]["columns"]["traditional_use"], "The use in children under 12 has not been established.")   # sigue en la página 2
        self.assertEqual(sections["4.4"]["page_to"], 2)
        self.assertEqual(sections["4.5"]["columns"]["well_established_use"], "Concomitant use with anticoagulants is contraindicated.")
        self.assertEqual(sections["4.5"]["columns"]["traditional_use"], "None reported.")
        self.assertNotIn("Footnote", sections["4.5"]["text"])          # nota al pie en letra pequeña
        self.assertNotIn("Special warnings'", sections["4.3"]["text"])  # la referencia cruzada de 4.2 no abre sección
        self.assertEqual(len(result["sha256"]), 64)

    def test_public_statement_without_safety_data(self):
        result = pdf_sections.extract_pdf(support.fixture("sample_statement.pdf"))
        self.assertEqual(result["sections"], {})
        self.assertEqual(result["statement"]["heading"], "CONCLUSIONS")
        self.assertFalse(result["statement"]["safety_data"])
        self.assertIn("cannot be established", result["statement"]["text"])


class RealPdfTests(unittest.TestCase):
    """Con los PDF reales del spike y de la descarga (se omiten si faltan)."""

    def test_hypericum_interactions_in_both_columns(self):
        support.require_module(self, "pdfminer", "pdfminer.six")
        path = support.require_real(self, "ema-pdf", "spike", "hyperici.pdf")
        result = pdf_sections.extract_pdf(path)
        interactions = result["sections"]["4.5"]
        self.assertEqual(sorted(interactions["columns"]), ["traditional_use", "well_established_use"])
        self.assertIn("CYP3A4", interactions["columns"]["well_established_use"])
        self.assertIn("contraindicated", interactions["columns"]["well_established_use"])
        self.assertIn("serotonin syndrome", interactions["text"])
        self.assertNotIn("4.6", interactions["text"][-20:])


if __name__ == "__main__":
    unittest.main()
