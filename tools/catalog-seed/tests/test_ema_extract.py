import json
import os
import unittest

import extract_support as support
from catalog_seed import ema, ema_extract
from catalog_seed.ema_extract import herbal_rows, pdf_rows, split_values


def record(url, **extra):
    base = {"latin_name": "Matricariae flos", "combination": "No", "english_common_name": "Matricaria Flower",
            "botanical_name": "Matricaria recutita L.", "therapeutic_area": "Mouth and throat disorders;Cough and cold",
            "status": "F: Assessment finalised", "outcome_of_european_assessment": "European Union herbal monograph",
            "herbal_medicine_url": url}
    base.update(extra)
    return base


class HerbalRowsTests(unittest.TestCase):
    def test_areas_and_combined_outcome_are_split_on_semicolon(self):
        rows = herbal_rows(ema.dedupe_records({"data": [record(
            "https://x/en/medicines/herbal/menthae", therapeutic_area="Pain and inflammation;Cough and cold",
            outcome_of_european_assessment="European Union herbal monograph;European Union list entry")]}))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row.record_type, row.row_key, row.raw_name_cell), ("ema_herbal", "menthae", "Matricaria recutita L."))
        self.assertEqual(row.content["therapeutic_areas"], ["Pain and inflammation", "Cough and cold"])
        self.assertEqual(row.content["outcomes"], ["European Union herbal monograph", "European Union list entry"])

    def test_merged_fiche_keeps_original_rows_with_their_own_areas(self):
        a = record("https://x/hyperici-herba", botanical_name="Hypericum perforatumL.", therapeutic_area="Urinary tract and genital disorders", combination="Yes")
        b = record("https://x/hyperici-herba", botanical_name="Cimicifuga racemosa (L.) Nutt.", therapeutic_area="Mental stress and mood disorders", combination="Yes")
        (row,) = herbal_rows(ema.dedupe_records({"data": [a, b]}))
        self.assertEqual(len(row.content["rows"]), 2)
        self.assertEqual(row.content["rows"][1]["therapeutic_areas"], ["Mental stress and mood disorders"])
        self.assertEqual(row.raw_name_cell, "Hypericum perforatumL.;Cimicifuga racemosa (L.) Nutt.")

    def test_empty_values(self):
        self.assertEqual(split_values(""), [])
        self.assertEqual(split_values(None), [])
        self.assertEqual(split_values(" a ; ;b"), ["a", "b"])


def fake_pdf_reader(extractions):
    def read(path):
        return extractions[os.path.basename(path)]
    return read


def monograph(sections):
    return {"sha256": "ab", "tool": "t", "statement": None,
            "sections": {n: {"heading": "h", "page_from": 1, "page_to": 1, "columns": {"traditional_use": t}, "text": t} for n, t in sections.items()}}


class PdfRowsTests(unittest.TestCase):
    RECORDS = [record("https://x/en/medicines/herbal/matricariae-flos"), record("https://x/en/medicines/herbal/citri-bergamiae-aetheroleum", botanical_name="Citrus bergamia"),
               record("https://x/en/medicines/herbal/otra"), record("https://x/en/medicines/herbal/sin-pagina")]

    def files(self):
        return [("/c/matricariae-flos__monograph-final__final-mono.pdf", "matricariae-flos__monograph-final__final-mono.pdf", "https://x/m.pdf"),
                ("/c/citri-bergamiae-aetheroleum__public-statement__final-ps.pdf", "citri-bergamiae-aetheroleum__public-statement__final-ps.pdf", "https://x/p.pdf")]

    def run_rows(self, **overrides):
        extractions = {
            "matricariae-flos__monograph-final__final-mono.pdf": monograph({"4.3": "Hipersensibilidad", "4.5": "None reported."}),
            "citri-bergamiae-aetheroleum__public-statement__final-ps.pdf": {"sha256": "cd", "tool": "t", "sections": {}, "statement": {
                "heading": "CONCLUSIONS", "page_from": 1, "page_to": 1, "text": "no monograph", "safety_data": False}},
        }
        extractions.update(overrides)
        return pdf_rows(self.RECORDS, self.files(), fake_pdf_reader(extractions), pages_cached={"matricariae-flos", "citri-bergamiae-aetheroleum", "otra"})

    def test_monograph_sections_become_rows_with_refs_slug_section(self):
        rows, stats = self.run_rows()
        keys = {(r.record_type, r.row_key) for r in rows}
        self.assertIn(("ema_pdf", "matricariae-flos:4.3"), keys)
        self.assertIn(("ema_pdf", "matricariae-flos:4.5"), keys)
        self.assertNotIn(("ema_pdf", "matricariae-flos:4.4"), keys)    # no se inventan secciones vacías
        doc = [r for r in rows if r.record_type == "ema_pdf_doc" and r.row_key == "matricariae-flos"][0]
        self.assertEqual(doc.content["status"], "ok")
        self.assertEqual(doc.content["documents"][0]["sections"], ["4.3", "4.5"])
        self.assertEqual(stats["ok"], 1)

    def test_public_statement_without_safety_data_is_marked(self):
        rows, stats = self.run_rows()
        row = [r for r in rows if r.row_key == "citri-bergamiae-aetheroleum:CONCLUSIONS"][0]
        self.assertEqual(row.content["note"], "declaración pública sin datos de seguridad")
        self.assertEqual(stats["statements_without_safety"], 1)
        doc = [r for r in rows if r.record_type == "ema_pdf_doc" and r.row_key == "citri-bergamiae-aetheroleum"][0]
        self.assertEqual(doc.content["status"], "declaracion-publica")

    def test_fiches_without_document_or_page(self):
        rows, stats = self.run_rows()
        status = {r.row_key: r.content["status"] for r in rows if r.record_type == "ema_pdf_doc"}
        self.assertEqual(status["otra"], "sin-documento")
        self.assertEqual(status["sin-pagina"], "no-descargada")
        self.assertEqual(stats["fiches"], 4)

    def test_unreadable_pdf_is_reported_and_others_continue(self):
        def reader(path):
            if "matricariae" in path:
                raise ValueError("corrupto")
            return {"sha256": "cd", "tool": "t", "sections": {}, "statement": None}
        rows, stats = pdf_rows(self.RECORDS, self.files(), reader)
        doc = [r for r in rows if r.record_type == "ema_pdf_doc" and r.row_key == "matricariae-flos"][0]
        self.assertEqual(doc.content["status"], "extraccion-fallida")
        self.assertIn("corrupto", doc.content["documents"][0]["error"])
        self.assertEqual(stats["extraccion-fallida"], 1)

    def test_monograph_without_sections_is_flagged(self):
        rows, stats = self.run_rows(**{"matricariae-flos__monograph-final__final-mono.pdf": monograph({})})
        doc = [r for r in rows if r.record_type == "ema_pdf_doc" and r.row_key == "matricariae-flos"][0]
        self.assertEqual(doc.content["status"], "sin-secciones")

    def test_second_document_with_same_section_gets_suffix(self):
        files = self.files() + [("/c/matricariae-flos__monograph-final__final-trad.pdf", "matricariae-flos__monograph-final__final-trad.pdf", "https://x/t.pdf")]
        extractions = {"matricariae-flos__monograph-final__final-mono.pdf": monograph({"4.3": "a"}),
                       "matricariae-flos__monograph-final__final-trad.pdf": monograph({"4.3": "b"}),
                       "citri-bergamiae-aetheroleum__public-statement__final-ps.pdf": {"sha256": "x", "tool": "t", "sections": {}, "statement": None}}
        rows, _ = pdf_rows(self.RECORDS, files, fake_pdf_reader(extractions))
        keys = sorted(r.row_key for r in rows if r.record_type == "ema_pdf" and r.row_key.startswith("matricariae"))
        self.assertEqual(keys, ["matricariae-flos:4.3", "matricariae-flos:4.3#2"])


class RealEmaTests(unittest.TestCase):
    def test_chamomile_areas_and_outcome(self):
        path = support.require_real(self, "ema_json", "herbal_medicines.json")
        records = ema.dedupe_records(ema.load_json(path))
        rows = {r.row_key: r for r in herbal_rows(records)}
        self.assertEqual(len(rows), 204)
        chamomile = rows["matricariae-flos"].content
        self.assertEqual(chamomile["therapeutic_areas"], ["Mouth and throat disorders", "Skin disorders and minor wounds", "Cough and cold", "Gastrointestinal disorders"])
        self.assertEqual(chamomile["outcomes"], ["European Union herbal monograph"])
        combined = [r for r in rows.values() if len(r.content["outcomes"]) > 1]
        self.assertTrue(combined)    # el resultado combinado se separa por «;»
        self.assertIn("European Union list entry", combined[0].content["outcomes"])


if __name__ == "__main__":
    unittest.main()
