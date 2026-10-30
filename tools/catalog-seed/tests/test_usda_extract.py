import os
import unittest

import extract_support as support
from catalog_seed import usda_extract, workdb
from catalog_seed.usda_extract import is_eo, name_language

TAX_H = ["FNFNUM", "TAXON", "TAXAUTHOR", "GENUS", "SPECIES", "SUBSPECIES", "VARIETY", "FORMA", "CULTIVAR", "FAMILY", "SPCMT"]
FARM_H = ["FNFNUM", "CHEM", "PPCO", "AMT_OR_LO", "AMT_HI", "AMT_ULHI", "EOPCT_OR_LO", "EOPCT_HI", "QUANT_UNIT", "AMT_LO", "AMT_OR_HI", "EOPCT_LO", "EOPCT_OR_HI"]
ETH_H = ["ETHNO", "ACTIVITY", "GENUS", "SPECIES", "SPAUT", "FAMILY", "CNAME", "COUNTRY", "REFERENCE", "LONGREF", "TAXON"]


def farm(fnfnum, chem, ppco, amt_hi="", eopct_hi="", unit="", amt_or_lo=""):
    return [fnfnum, chem, ppco, amt_or_lo, amt_hi, "", "", eopct_hi, unit, "", "", "", ""]


def tables():
    chems = [farm("1", "EO", "FL", amt_hi="6000")]
    chems += [farm("1", "COMPOUND%02d" % i, "FL", amt_hi=str(i * 10), eopct_hi=str(i)) for i in range(1, 14)]
    chems += [farm("1", "COMPOUND05", "FL", amt_hi="500")]   # repetido: se queda con la mayor cantidad
    chems += [farm("1", "EO (ASSUMED)", "LF"), farm("1", "AZULENE", "LF", amt_hi=".6", unit="MICROMOLS/G")]
    chems += [farm("1", "ORPHAN", ""), farm("999", "ORPHAN", "FL", amt_hi="1")]  # sin parte; planta que no existe
    return {
        "FNFTAX": (TAX_H, [["1", "Matricaria chamomilla", "L.", "Matricaria", "chamomilla", "", "", "", "", "Asteraceae", ""],
                           ["2", "Mentha × piperita", "L.", "Mentha", "piperita", "", "", "", "", "Lamiaceae", ""]]),
        "COMMON_NAMES": (["CNNAM", "FNFNUM", "CNID"], [["Chamomile", "1", "CHAMOMILE"], ["Manzanilla (Sp.)", "1", "MANZ"], ["Mint", "2", "MINT"]]),
        "PARTS": (["PPCO", "PPNA"], [["FL", "Flower"], ["LF", "Leaf"]]),
        "FARMACY_NEW": (FARM_H, chems),
        "ETHNOBOT": (ETH_H, [["10", "Abcess", "Matricaria", "chamomilla", "", "Asteraceae", "", "Elsewhere", "Eb24: 441", "", "Matricaria chamomilla"],
                             ["11", "Cold", "Matricaria", "chamomilla", "", "Asteraceae", "", "Syria", "Woi.Syria", "", "Matricaria chamomilla"],
                             ["12", "Fever", "Mentha", "piperita", "", "Lamiaceae", "", "Italy", "Burkill,1966", "", "Mentha × piperita"]]),
        "REFERENCES": (["REFERENCE", "LONGREF", "NOTE"], [["Burkill,1966", "Burkill, 1966. Dictionary of the Economic Products.", ""],
                                                         ["Eb24: 441", "Economic Botany 24: 441", "Una nota"]]),
    }


class UsdaExtractTests(support.TempDirTestCase):
    def extract(self):
        path = os.path.join(self.tmp, "usda.zip")
        support.make_usda_zip(path, tables())
        return usda_extract.extract(path)

    def by_type(self, rows, record_type):
        return {r.row_key: r for r in rows if r.record_type == record_type}

    def test_counts_and_provenance(self):
        rows, stats = self.extract()
        self.assertEqual(stats["usda_taxon"], 2)
        self.assertEqual(stats["usda_use"], 3)
        taxa = self.by_type(rows, "usda_taxon")
        self.assertEqual(taxa["2"].raw_name_cell, "Mentha × piperita")   # sin normalizar
        self.assertEqual(taxa["2"].fnfnum, "2")
        self.assertEqual(taxa["1"].content["family"], "Asteraceae")

    def test_common_names_get_language_by_label(self):
        rows, stats = self.extract()
        names = self.by_type(rows, "usda_common_name")
        self.assertEqual(names["1-1"].content["language"], "en")
        self.assertEqual(names["1-2"].content["language"], "und")
        self.assertEqual(names["1-2"].raw_name_cell, "Manzanilla (Sp.)")
        self.assertEqual(name_language("Rumberry (Eng.)"), "und")
        self.assertEqual(name_language("Okra"), "en")

    def test_parts_summary_by_fnfnum_and_ppco(self):
        rows, stats = self.extract()
        parts = self.by_type(rows, "usda_part")
        self.assertEqual(sorted(parts), ["1-FL", "1-LF"])        # el PPCO vacío y la planta inexistente no generan filas
        self.assertEqual(stats["farmacy_rows_empty_ppco"], 1)
        flower = parts["1-FL"].content
        self.assertEqual(flower["ppna"], "Flower")
        self.assertEqual(flower["rows"], 15)                      # EO + 13 compuestos + el repetido
        self.assertEqual(flower["distinct_compounds"], 14)
        self.assertEqual(len(flower["top_amount"]), 10)
        self.assertEqual(flower["top_amount"][0], {"compound": "EO", "amount": 6000, "unit": None, "eo": True})
        self.assertEqual(flower["top_amount"][1]["compound"], "COMPOUND05")   # 500 (la mayor de sus dos filas)
        self.assertEqual(len(flower["top_eo"]), 10)
        self.assertEqual(flower["top_eo"][0]["compound"], "COMPOUND13")
        self.assertEqual(flower["top_eo"][0]["eopct"], 13)
        self.assertTrue(flower["has_eo"])
        self.assertEqual(flower["eo_compounds"], ["EO"])
        self.assertEqual(parts["1-FL"].raw_name_cell, "Matricaria chamomilla")

    def test_eo_variants_are_marked_and_units_kept(self):
        rows, _ = self.extract()
        leaf = self.by_type(rows, "usda_part")["1-LF"].content
        self.assertTrue(leaf["has_eo"])
        self.assertEqual(leaf["eo_compounds"], ["EO (ASSUMED)"])
        azulene = [c for c in leaf["top_amount"] if c["compound"] == "AZULENE"][0]
        self.assertEqual((azulene["amount"], azulene["unit"], azulene["eo"]), (0.6, "MICROMOLS/G", False))
        for value, expected in (("EO", True), ("EO(ASS.)", True), ("EO (ASSUMED)", True), ("EOSIN", False), ("GEO", False)):
            self.assertEqual(is_eo(value), expected, value)

    def test_uses_keep_short_reference_and_raw_taxon_without_fnfnum(self):
        rows, _ = self.extract()
        uses = self.by_type(rows, "usda_use")
        self.assertEqual(sorted(uses), ["10", "11", "12"])
        self.assertEqual(uses["10"].content["reference"], "Eb24: 441")
        self.assertEqual(uses["11"].content["reference"], "Woi.Syria")
        self.assertEqual(uses["12"].raw_name_cell, "Mentha × piperita")
        self.assertIsNone(uses["10"].fnfnum)
        self.assertNotIn("longref", uses["10"].content)           # el LONGREF propio de ETHNOBOT va vacío y se omite

    def test_references_with_longref(self):
        rows, stats = self.extract()
        refs = self.by_type(rows, "usda_reference")
        self.assertEqual(stats["usda_reference"], 2)
        self.assertEqual(refs["Burkill,1966"].content["longref"], "Burkill, 1966. Dictionary of the Economic Products.")
        self.assertEqual(refs["Eb24: 441"].content["note"], "Una nota")

    def test_duplicate_fnfnum_is_an_error(self):
        data = tables()
        data["FNFTAX"] = (TAX_H, data["FNFTAX"][1] + [data["FNFTAX"][1][0]])
        path = os.path.join(self.tmp, "dup.zip")
        support.make_usda_zip(path, data)
        with self.assertRaises(ValueError):
            usda_extract.extract(path)

    def test_replace_source_is_idempotent(self):
        rows, _ = self.extract()
        connection = workdb.open_db(":memory:")
        first = workdb.replace_source(connection, "usda", rows, "v", [])
        second = workdb.replace_source(connection, "usda", rows, "v", [])
        self.assertEqual(first, second)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM source_row").fetchone()[0], first)


class UsdaRealDataTests(unittest.TestCase):
    """Con el ZIP real de la caché (se omiten si falta)."""

    def test_real_zip_totals_and_chamomile(self):
        path = support.require_real(self, "usda", "Duke-Source-CSV.zip")
        rows, stats = usda_extract.extract(path)
        self.assertEqual(stats["usda_taxon"], 2376)
        self.assertEqual(stats["usda_use"], 82873)
        self.assertEqual(stats["usda_reference"], 2043)
        uses = [r for r in rows if r.record_type == "usda_use"]
        self.assertEqual(len({r.row_key for r in uses}), 82873)
        self.assertTrue(all("longref" not in r.content for r in uses))   # LONGREF propio siempre vacío
        chamomile = [r for r in uses if r.raw_name_cell == "Matricaria chamomilla"]
        self.assertGreater(len(chamomile), 80)
        part = [r for r in rows if r.record_type == "usda_part" and r.raw_name_cell == "Matricaria recutita"]   # FNFTAX 605; ETHNOBOT la llama chamomilla
        self.assertTrue(part)
        self.assertTrue(any(p.content["has_eo"] for p in part))


if __name__ == "__main__":
    unittest.main()
