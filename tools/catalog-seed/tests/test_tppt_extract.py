import os
import unittest

import extract_support as support
from catalog_seed import tppt_extract, workdb
from catalog_seed.tppt_extract import composition_rank, split_citations

SCHEMA = [
    ("CREATE TABLE Toxic_plant_species (Plant_number TEXT PRIMARY KEY, Latin_plant_name TEXT, German_plant_name TEXT, English_plant_name TEXT, "
     "Plant_genus TEXT, Plant_family TEXT, Global_spatial_distribution TEXT, Swiss_frequency TEXT, Swiss_appearance TEXT, Vegetation_type TEXT, "
     "Blooming_period TEXT, Toxic_plant_part TEXT, Human_toxicity TEXT, Animal_toxicity TEXT, Invasive_foreign TEXT, Garden_plant TEXT, Agricultural_plant TEXT)", ()),
    ("CREATE TABLE Phytotoxins (Phytotoxin_number TEXT PRIMARY KEY, Phytotoxin_name TEXT, CASRN TEXT, PSM_class TEXT)", ()),
    ("CREATE TABLE Phytotoxin_toxic_plant_species_relationships (Number INTEGER PRIMARY KEY, Phytotoxin_number TEXT, Phytotoxin_name TEXT, "
     "Plant_number TEXT, Latin_plant_name TEXT, Composition TEXT)", ()),
    ("CREATE TABLE Toxicity_data (Number INTEGER PRIMARY KEY, Phytotoxin_number TEXT, Phytotoxin_name TEXT, Test_animal TEXT, Exposure_route TEXT, Dose TEXT, Data_source TEXT)", ()),
    ("CREATE TABLE Remarks (Plant_genus TEXT PRIMARY KEY, Comment TEXT, \"Scientific-knowledge_availability_score\" INTEGER)", ()),
    ("CREATE TABLE Bibliography (Abbreviation TEXT PRIMARY KEY, Literature_reference TEXT)", ()),
]


def statements():
    out = list(SCHEMA)
    plant = "INSERT INTO Toxic_plant_species VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    out.append((plant, ("P601", "Conium maculatum L.", "Schierling", "Hemlock", "Conium ", "Apiaceae", "", "7", "", "", "", "Whole plant", "very strong toxic", "very strong toxic", "", "", "")))
    out.append((plant, ("P2", "Lavandula angustifolia Mill.", "Lavendel", "Lavender", "Lavandula", "Lamiaceae", "", "3", "", "", "", "Flower", "nontoxic", "", "", "", "")))
    out.append((plant, ("P3", "Sin toxinas L.", "", "", "Nullus", "Nullaceae", "", "1", "", "", "", "", "unknown", "", "", "", "")))
    # Conium: 3 major, 2 "toxin" y 20 minor => 3 + 15 de las demás; 25 relaciones en total
    number = 0
    for i, composition in enumerate(["major toxin"] * 3 + ["major toxin and aglycone"] + ["minor toxin"] * 20 + ["single toxin"]):
        number += 1
        tox = "T%d" % (100 + i)
        out.append(("INSERT INTO Phytotoxin_toxic_plant_species_relationships VALUES (?,?,?,?,?,?)", (number, tox, "Toxina %d" % i, "P601", "Conium maculatum L.", composition)))
        out.append(("INSERT INTO Phytotoxins VALUES (?,?,?,?)", (tox, "Toxina %d" % i, "1-%d" % i, "Alkaloid")))
    out.append(("INSERT INTO Toxicity_data VALUES (?,?,?,?,?,?,?)", (1, "T100", "Toxina 0", "mouse", "i.v.", "19", "Teuscher and Lindequist (2010), Duke and Williams (1977)")))
    out.append(("INSERT INTO Toxicity_data VALUES (?,?,?,?,?,?,?)", (2, "T100", "Toxina 0", "cat", "p.o.", "5", "clinitox.ch")))
    out.append(("INSERT INTO Toxicity_data VALUES (?,?,?,?,?,?,?)", (3, "T119", "Toxina 19", "rat", "p.o.", "7", "Roth et al. (2012)")))   # minor fuera del tope
    out.append(("INSERT INTO Remarks VALUES (?,?,?)", ("Conium", "Piperidine alkaloids are the toxins.", 2)))
    out.append(("INSERT INTO Bibliography VALUES (?,?)", ("Teuscher and Lindequist (2010)", "Teuscher E., Lindequist U. Biogene Gifte, 2010.")))
    out.append(("INSERT INTO Bibliography VALUES (?,?)", ("Duke and Williams (1977)", "Duke J. and Williams L. 1977.")))
    out.append(("INSERT INTO Bibliography VALUES (?,?)", ("Roth et al. (2012)", "Roth L. et al. 2012.")))
    return out


class TpptExtractTests(support.TempDirTestCase):
    def rows(self):
        path = os.path.join(self.tmp, "tppt-db.zip")
        support.make_tppt_zip(path, statements())
        rows, stats = tppt_extract.extract(path)
        return {r.row_key: r for r in rows}, stats

    def test_all_major_toxins_and_up_to_fifteen_more(self):
        rows, stats = self.rows()
        conium = rows["P601"]
        self.assertEqual(conium.record_type, "tppt_plant")
        self.assertEqual(conium.raw_name_cell, "Conium maculatum L.")
        content = conium.content
        self.assertEqual(content["n_toxins"], 25)
        majors = [t for t in content["toxins"] if t["major"]]
        self.assertEqual(len(majors), 4)                      # «major toxin» y «major toxin and aglycone»
        self.assertEqual(len(content["toxins"]), 4 + 15)
        self.assertEqual(content["toxins"][4]["composition"], "single toxin")   # lo más importante después de las mayores
        self.assertEqual(stats["plants"], 3)

    def test_links_toxicity_remarks_and_bibliography(self):
        rows, stats = self.rows()
        content = rows["P601"].content
        first = content["toxins"][0]
        self.assertEqual(first["number"], "T100")
        self.assertEqual([d["dose"] for d in first["toxicity_data"]], ["19", "5"])
        self.assertEqual(content["remarks"], {"comment": "Piperidine alkaloids are the toxins.", "knowledge_score": 2})   # género con espacio final
        self.assertEqual(sorted(content["bibliography"]), ["Duke and Williams (1977)", "Teuscher and Lindequist (2010)"])
        self.assertEqual(stats["citations_without_bibliography"], 1)   # clinitox.ch
        self.assertNotIn("Roth et al. (2012)", content["bibliography"])   # su toxina quedó fuera del tope

    def test_plants_without_toxins_or_remarks(self):
        rows, _ = self.rows()
        self.assertEqual(rows["P3"].content["toxins"], [])
        self.assertEqual(rows["P3"].content["n_toxins"], 0)
        self.assertIsNone(rows["P3"].content["remarks"])
        self.assertEqual(rows["P2"].content["human_toxicity"], "nontoxic")

    def test_helpers(self):
        self.assertEqual(split_citations("A and B (2010), Roth et al. (2012)"), ["A and B (2010)", "Roth et al. (2012)"])
        self.assertEqual(split_citations("clinitox.ch"), ["clinitox.ch"])
        self.assertLess(composition_rank("major toxin"), composition_rank("single toxin"))
        self.assertLess(composition_rank("minor toxin"), composition_rank("something new"))

    def test_zip_without_database_is_rejected(self):
        import zipfile
        path = os.path.join(self.tmp, "empty.zip")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("other.txt", "x")
        with self.assertRaises(ValueError):
            tppt_extract.extract(path)


class TpptRealDataTests(unittest.TestCase):
    def test_hemlock(self):
        path = support.require_real(self, "tppt", "tppt-db.zip")
        rows, stats = tppt_extract.extract(path)
        self.assertEqual(stats["plants"], 844)
        conium = [r for r in rows if r.raw_name_cell.startswith("Conium maculatum")][0].content
        self.assertEqual((conium["human_toxicity"], conium["animal_toxicity"]), ("very strong toxic", "very strong toxic"))
        self.assertEqual(conium["n_toxins"], 7)
        self.assertEqual([t["name"] for t in conium["toxins"] if t["major"]], ["(+)-Coniine", "(+)-N-Methylconiine", "gamma-Coniceine"])
        self.assertIn("Piperidine", conium["remarks"]["comment"])
        self.assertTrue(conium["bibliography"])
        counts = {}
        for row in rows:
            for toxin in row.content["toxins"]:
                counts[row.row_key] = counts.get(row.row_key, 0) + (0 if toxin["major"] else 1)
        self.assertLessEqual(max(counts.values()), 15)


if __name__ == "__main__":
    unittest.main()
