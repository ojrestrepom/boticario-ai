import unittest

import extract_support as support
from catalog_seed import efsa_extract


class EfsaExtractTests(unittest.TestCase):
    def setUp(self):
        support.require_module(self, "xlrd")

    def extract(self):
        return efsa_extract.extract(support.fixture("BOTANIC.xls"), support.fixture("ENDPOINTSTUDY.xls"))

    def test_rows_and_provenance(self):
        rows, stats = self.extract()
        botanic = [r for r in rows if r.record_type == "efsa_botanic"]
        endpoint = [r for r in rows if r.record_type == "efsa_endpoint"]
        self.assertEqual((len(botanic), len(endpoint)), (stats["efsa_botanic"], stats["efsa_endpoint"]))
        self.assertGreater(len(botanic), 3)
        self.assertEqual(len({r.row_key for r in botanic}), len(botanic))
        self.assertTrue(all(r.fnfnum is None and r.raw_name_cell for r in rows))

    def test_hypericum_botanic_row(self):
        rows, _ = self.extract()
        hyper = [r for r in rows if r.record_type == "efsa_botanic" and "Hypericum perforatum" in r.raw_name_cell]
        self.assertTrue(hyper)
        content = hyper[0].content
        self.assertIn("hyper", content["substance_name"].lower())
        self.assertTrue(content["part"])
        self.assertIn("citation", content)
        self.assertNotIn("value", content)    # «not quantified»: sin valor
        self.assertEqual(content["expression"], "not quantified")

    def test_scientific_names_are_kept_as_is(self):
        rows, _ = self.extract()
        names = {r.raw_name_cell for r in rows}
        self.assertIn("Lavandula angustifolia ssp. angustifolia; Lavandula vera D.C.", names)   # sin separar ni normalizar
        self.assertIn("Calendula officinalis L.", names)

    def test_endpoint_row_has_study_fields(self):
        rows, _ = self.extract()
        endpoint = [r for r in rows if r.record_type == "efsa_endpoint"][0].content
        for key in ("citation", "study_category", "test_species", "route", "toxicity", "effect_description"):
            self.assertIn(key, endpoint)
        self.assertIsInstance(endpoint["year"], int)    # sin «.0»


class EfsaRealDataTests(unittest.TestCase):
    def test_real_totals_and_a_row(self):
        support.require_module(self, "xlrd")
        botanic = support.require_real(self, "efsa", "BOTANIC.xls")
        endpoint = support.require_real(self, "efsa", "ENDPOINTSTUDY.xls")
        rows, stats = efsa_extract.extract(botanic, endpoint)
        self.assertEqual((stats["efsa_botanic"], stats["efsa_endpoint"]), (3449, 972))
        conium = [r for r in rows if r.record_type == "efsa_botanic" and r.raw_name_cell.startswith("Conium maculatum")]
        self.assertEqual(sorted({r.content["substance_name"] for r in conium}), ["coniine"])


if __name__ == "__main__":
    unittest.main()
