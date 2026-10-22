import unittest
import unittest.mock

import extract_support as support
from catalog_seed import efsa_extract, safety, tppt_extract
from catalog_seed.safety import (efsa_concern, efsa_effect_group, ema_interaction_class, load_safety_map, tppt_categories,
                                 tppt_level)

MAP = None


def safety_map():
    global MAP
    if MAP is None:
        MAP = load_safety_map()
    return MAP


class TpptLevelTests(unittest.TestCase):
    def level(self, value):
        return tppt_level(safety_map(), value)["level"]

    def test_design_mandates(self):
        self.assertEqual(self.level("strong toxic"), "alto")
        self.assertEqual(self.level("very strong toxic"), "alto")
        self.assertEqual(self.level("carcinogenic"), "medio")
        self.assertEqual(self.level("phototoxic"), "medio")
        self.assertEqual(self.level("allergenic"), "bajo")

    def test_approved_levels(self):
        for value, expected in (("toxic", "medio"), ("weak toxic", "bajo"), ("toxic (unknown strength)", "medio"), ("skin-irritating", "bajo"),
                                ("liver toxic", "medio"), ("cytotoxic", "medio"), ("estrogenic", "medio")):
            self.assertEqual(self.level(value), expected, value)

    def test_every_approved_tppt_category(self):
        approved = {"toxic": "medio", "toxic (unknown strength)": "medio", "liver toxic": "medio", "cytotoxic": "medio", "estrogenic": "medio",
                    "weak toxic": "bajo", "skin-irritating": "bajo", "nontoxic": None, "unknown": None, "infested plants only": None, "stimulating": None}
        for value, expected in approved.items():
            self.assertEqual(self.level(value), expected, value)
        for value in ("very strong toxic", "strong toxic", "very strong toxic (cat)"):
            self.assertIsNone(tppt_level(safety_map(), value, "animal_toxicity")["level"], value)

    def test_explicitly_without_level(self):
        for value in ("nontoxic", "unknown", "infested plants only", "stimulating"):
            result = tppt_level(safety_map(), value)
            self.assertIsNone(result["level"], value)
            self.assertEqual(result["uncovered"], [], value)    # cubierta, con level null

    def test_combined_values_split_and_take_the_highest(self):
        self.assertEqual(tppt_categories("allergenic, skin-irritating"), ["allergenic", "skin-irritating"])
        self.assertEqual(self.level("allergenic, phototoxic"), "medio")
        self.assertEqual(self.level("estrogenic, skin-irritating"), "medio")

    def test_prefix_before_parenthesis(self):
        self.assertEqual(tppt_categories("strong toxic (only wild growing plants)"), ["strong toxic"])
        self.assertEqual(self.level("very strong toxic (only wild growing plants)"), "alto")
        self.assertEqual(self.level("toxic (only wild growing plants)"), "medio")
        self.assertEqual(tppt_categories("strong toxic (cow, pig)"), ["strong toxic"])   # coma dentro del paréntesis

    def test_unknown_category_is_reported_not_guessed(self):
        result = tppt_level(safety_map(), "mystery toxic")
        self.assertEqual(result["uncovered"], ["mystery toxic"])
        self.assertIsNone(result["level"])

    def test_animal_toxicity_never_sets_a_level(self):
        for value in ("very strong toxic (cat)", "toxic (horse)", "strong toxic (cow, pig)"):
            self.assertIsNone(tppt_level(safety_map(), value, "animal_toxicity")["level"])

    def test_real_data_every_value_is_covered(self):
        path = support.require_real(self, "tppt", "tppt-db.zip")
        rows, _ = tppt_extract.extract(path)
        human = {r.content["human_toxicity"] for r in rows}
        animal = {r.content["animal_toxicity"] for r in rows if r.content["animal_toxicity"]}
        self.assertEqual(len(human), 22)
        for value in human:
            self.assertEqual(tppt_level(safety_map(), value)["uncovered"], [], value)
            self.assertTrue(tppt_level(safety_map(), value)["categories"], value)
        for value in animal:
            self.assertEqual(tppt_level(safety_map(), value, "animal_toxicity")["uncovered"], [], value)
        hemlock = [r for r in rows if r.raw_name_cell.startswith("Conium maculatum")][0]
        self.assertEqual(tppt_level(safety_map(), hemlock.content["human_toxicity"])["level"], "alto")


class EfsaConcernTests(unittest.TestCase):
    def test_substance_of_concern_fixes_medium(self):
        rows = [{"substance_name": "coniine", "result_type": "Numerical Value"}]
        result = efsa_concern(safety_map(), rows)
        self.assertEqual((result["level"], result["substances"]), ("medio", ["coniine"]))

    def test_not_detected_rows_and_blank_substances_do_not_count(self):
        rows = [{"substance_name": "thujone", "result_type": "Non Detected Value (<LOD)"}, {"substance_name": None}]
        result = efsa_concern(safety_map(), rows)
        self.assertIsNone(result["level"])
        self.assertEqual(result["rows_excluded"], 2)

    def test_loq_and_unquantified_rows_count(self):
        rows = [{"substance_name": "estragole", "result_type": "Non Quantified Value (<LOQ)"}, {"substance_name": "alpha-thujone"}]
        result = efsa_concern(safety_map(), rows)
        self.assertEqual(result["concern_substances"], ["alpha-thujone", "estragole"])
        self.assertEqual(result["level"], "medio")

    def test_plant_with_only_cineole_has_no_efsa_level(self):
        rows = [{"substance_name": "1,8-cineole", "result_type": "Numerical Value"}, {"substance_name": "Camphor", "result_type": "Numerical Value"}]
        result = efsa_concern(safety_map(), rows)
        self.assertIsNone(result["level"])
        self.assertEqual(result["concern_substances"], [])
        self.assertEqual(result["evidence_substances"], ["1,8-cineole", "Camphor"])

    def test_estragole_fixes_medium_and_reports_the_trigger(self):
        rows = [{"substance_name": "1,8-cineole", "result_type": "Numerical Value"}, {"substance_name": "estragole", "result_type": "Numerical Value"}]
        result = efsa_concern(safety_map(), rows)
        self.assertEqual(result["level"], "medio")
        self.assertEqual(result["concern_substances"], ["estragole"])
        self.assertEqual(result["concern_groups"], ["genotoxico-carcinogeno"])
        self.assertEqual(result["evidence_substances"], ["1,8-cineole"])

    def test_thujone_fixes_medium_and_names_are_compared_loosely(self):
        for name in ("alpha-thujone", "beta-thujone", "ALPHA-THUJONE", " alpha-thujone "):
            self.assertEqual(efsa_concern(safety_map(), [{"substance_name": name, "result_type": "Numerical Value"}])["level"], "medio", name)
        self.assertIsNone(efsa_concern(safety_map(), [{"substance_name": "thujone", "result_type": "Numerical Value"}])["level"])   # nombre que el compendio no usa

    def test_excluded_and_candidate_substances_do_not_fix_a_level(self):
        for name in ("anethole", "carvacrol", "Tannins", "Oxalates", "Lectins", "Saponins", "caffeine", "Emodin", "elemicin", "myristicin", "Cyanogenic glycosides"):
            self.assertIsNone(efsa_concern(safety_map(), [{"substance_name": name, "result_type": "Numerical Value"}])["level"], name)

    def test_concern_list_and_exclusions_do_not_overlap(self):
        listed = {safety.substance_key(e["substance"]) for e in safety_map()["efsa"]["concern_list"]["substances"]}
        for group in safety_map()["efsa"]["evidence_only"]:
            for name in group["substances"]:
                self.assertNotIn(safety.substance_key(name), listed, name)

    def test_efsa_never_sets_high_on_its_own(self):
        self.assertNotIn("alto", [e["level"] for e in safety_map()["efsa"]["classes"].values()])

    def test_effect_group_is_the_part_before_the_colon(self):
        self.assertEqual(efsa_effect_group("digestive: Liver"), "digestive")
        self.assertEqual(efsa_effect_group(None), "")

    def test_real_data_every_category_is_covered_or_without_level(self):
        support.require_module(self, "xlrd")
        botanic = support.require_real(self, "efsa", "BOTANIC.xls")
        endpoint = support.require_real(self, "efsa", "ENDPOINTSTUDY.xls")
        rows, _ = efsa_extract.extract(botanic, endpoint)
        config = safety_map()["efsa"]
        for row in rows:
            content = row.content
            if row.record_type == "efsa_botanic":
                self.assertIn(content.get("result_type", ""), config["result_types"])
                self.assertTrue(content.get("substance_name"))
            else:
                self.assertIn(content["study_category"], config["study_categories"])
                self.assertIn(efsa_effect_group(content.get("toxicity_summary")), config["endpoint_effects"])
        hemlock = [r.content for r in rows if r.record_type == "efsa_botanic" and r.raw_name_cell.startswith("Conium maculatum")]
        self.assertEqual(efsa_concern(safety_map(), hemlock)["level"], "medio")

    def test_real_data_list_uses_exact_compendium_names(self):
        support.require_module(self, "xlrd")
        botanic = support.require_real(self, "efsa", "BOTANIC.xls")
        endpoint = support.require_real(self, "efsa", "ENDPOINTSTUDY.xls")
        rows, _ = efsa_extract.extract(botanic, endpoint)
        config = safety_map()["efsa"]
        present = {r.content["substance_name"] for r in rows if r.record_type == "efsa_botanic"}
        keys = {safety.substance_key(n) for n in present}
        exact = {e["substance"] for e in config["concern_list"]["substances"]}
        self.assertEqual(exact - present, set(), "nombres de la lista que el compendio no usa")
        for group in config["evidence_only"]:
            for name in group["substances"]:
                self.assertIn(safety.substance_key(name), keys, name)
        # Cada sustancia del compendio queda en la lista o fuera de ella (evidencia): ninguna clave ambigua entre variantes de nombre.
        listed = {safety.substance_key(n) for n in exact}
        for name in present:
            result = efsa_concern(safety_map(), [{"substance_name": name, "result_type": "Numerical Value"}])
            self.assertEqual(bool(result["concern_substances"]), safety.substance_key(name) in listed, name)


def section(**columns):
    return {"columns": columns, "text": " ".join("[%s] %s" % item for item in columns.items())}


class EmaInteractionTests(unittest.TestCase):
    def classify(self, **columns):
        return ema_interaction_class(safety_map(), section(**columns))

    def test_contraindicated_is_severe(self):
        result = self.classify(well_established_use="Concomitant use with cyclosporine is contraindicated (see section 4.3).")
        self.assertEqual((result["class"], result["level"]), ("severe", "alto"))
        self.assertIn("contraindicated", result["matched"])

    def test_each_severe_pattern(self):
        cases = {
            "not-to-be-used-together": "Not to be used concomitantly with diuretics.",
            "serotonin-syndrome": "Very rarely serotonin syndrome can occur.",
            "bleeding-risk": "Willow bark may increase the effects of anticoagulants such as coumarin derivatives.",
            "life-threatening": "A life-threatening reaction has been reported.",
        }
        for pattern_id, text in cases.items():
            result = self.classify(traditional_use=text)
            self.assertEqual(result["class"], "severe", pattern_id)
            self.assertIn(pattern_id, result["matched"])

    def test_timing_advice_is_not_severe(self):
        result = self.classify(well_established_use="Absorption of concomitantly administered medicines may be delayed. The product should not be taken 1 hour before or after other medicinal products.")
        self.assertEqual((result["class"], result["level"]), ("interactions", None))

    def test_none_reported_variants(self):
        for text in ("None reported.", "None reported", "None known.", "Not known", "No clinically relevant interactions have been observed."):
            self.assertEqual(self.classify(traditional_use=text)["class"], "none-reported", text)

    def test_indication_labels_do_not_hide_none_reported(self):
        self.assertEqual(self.classify(traditional_use="Indication 1) None reported. Indication 2) None reported.")["class"], "none-reported")
        self.assertEqual(self.classify(traditional_use="Indication 1) Absorption may be delayed. Indication 2) None reported.")["class"], "interactions")

    def test_no_studies(self):
        for text in ("No interaction studies have been performed.", "No data available."):
            self.assertEqual(self.classify(traditional_use=text)["class"], "no-studies", text)

    def test_most_severe_column_wins(self):
        result = self.classify(well_established_use="Contraindicated with anticoagulants.", traditional_use="None reported.")
        self.assertEqual(result["class"], "severe")
        self.assertEqual(result["columns"], {"well_established_use": "severe", "traditional_use": "none-reported"})

    def test_missing_section(self):
        self.assertEqual(ema_interaction_class(safety_map(), None)["class"], "no-section")
        self.assertEqual(ema_interaction_class(safety_map(), {"columns": {}, "text": ""})["class"], "no-section")

    def test_rotulated_text_is_split_back_into_columns(self):
        result = ema_interaction_class(safety_map(), {"text": "[well_established_use] None reported. [traditional_use] Contraindicated with X."})
        self.assertEqual(result["class"], "severe")

    def test_every_class_in_the_map_has_a_level_or_a_reason_for_none(self):
        for name, entry in safety_map()["ema"]["classes"].items():
            self.assertTrue(entry["why"], name)
        self.assertEqual({n: e["level"] for n, e in safety_map()["ema"]["classes"].items() if e["level"]},
                         {"severe": "alto", "statement-with-safety": "medio"})

    def test_public_statement_with_safety_data_is_medium(self):
        classes = safety_map()["ema"]["classes"]
        self.assertEqual(classes["statement-with-safety"]["level"], "medio")
        self.assertIsNone(classes["statement-no-safety"]["level"])

    def test_report_gives_medium_to_statements_with_safety_data(self):
        from catalog_seed import safety_report, workdb
        conn = unittest.mock.MagicMock()
        rows = {("ema_pdf", "ema_pdf_doc"): [{"row_key": "kava", "content": {"status": "declaracion-publica"}},
                                              {"row_key": "otra", "content": {"status": "declaracion-publica"}}],
                ("ema_pdf", "ema_pdf"): []}

        def fetch(connection, source, record_type, row_key=None):
            if row_key:
                return [{"content": {"safety_data": True}}] if row_key.startswith("kava") else []
            return rows[(source, record_type)]
        with unittest.mock.patch.object(workdb, "fetch_rows", fetch):
            result = safety_report.ema_classification(conn, safety_map())
        self.assertEqual((result["kava"]["class"], result["kava"]["level"]), ("statement-with-safety", "medio"))
        self.assertEqual((result["otra"]["class"], result["otra"]["level"]), ("statement-no-safety", None))

    def test_real_pdfs_every_monograph_class_is_covered(self):
        support.require_module(self, "pdfminer", "pdfminer.six")
        import glob
        import os
        from catalog_seed import pdf_sections
        paths = sorted(glob.glob(os.path.join(support.CACHE, "ema_pdf", "*.pdf")))
        if not paths:
            self.skipTest("faltan los PDF de la EMA en data/.cache/ema_pdf")
        classes = safety_map()["ema"]["classes"]
        seen = {}
        for path in paths:
            extraction = pdf_sections.extract_pdf(path)
            result = ema_interaction_class(safety_map(), extraction["sections"].get("4.5"))
            self.assertIn(result["class"], classes, path)
            seen.setdefault(result["class"], []).append(os.path.basename(path).split("__")[0])
        self.assertIn("none-reported", seen)
        for slug in ("hyperici-herba",):
            if any(os.path.basename(p).startswith(slug + "__") for p in paths):
                self.assertIn(slug, seen.get("severe", []))


class MapValidityTests(unittest.TestCase):
    def test_levels_are_valid_and_every_entry_is_justified(self):
        data = safety_map()
        self.assertEqual(data["version"], 2)
        self.assertEqual(tuple(data["levels"]), safety.LEVELS)

    def test_invalid_level_is_rejected(self):
        import json
        import os
        import tempfile
        data = json.loads(json.dumps(safety_map()))
        data["tppt"]["human_toxicity"]["toxic"]["level"] = "critico"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            with open(path, "w") as handle:
                json.dump(data, handle)
            with self.assertRaises(safety.SafetyMapError):
                load_safety_map(path)

    def load_modified(self, change):
        import json
        import os
        import tempfile
        data = json.loads(json.dumps(safety_map()))
        change(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            with open(path, "w") as handle:
                json.dump(data, handle)
            return load_safety_map(path)

    def test_malformed_concern_list_entries_are_rejected(self):
        def entries(data):
            return data["efsa"]["concern_list"]["substances"]
        bad = {
            "sin sustancia": lambda d: entries(d).append({"group": "veneno-potente"}),
            "grupo inexistente": lambda d: entries(d).append({"substance": "nueva", "group": "no-existe"}),
            "sin grupo": lambda d: entries(d).append({"substance": "nueva"}),
            "repetida": lambda d: entries(d).append({"substance": "ESTRAGOLE", "group": "genotoxico-carcinogeno"}),
            "why vacío": lambda d: entries(d).append({"substance": "nueva", "group": "veneno-potente", "why": " "}),
            "no es objeto": lambda d: entries(d).append("estragole"),
            "grupo sin why": lambda d: d["efsa"]["concern_list"]["groups"].update({"x": {}}),
            "lista vacía": lambda d: d["efsa"]["concern_list"].update({"substances": []}),
            "sin lista": lambda d: d["efsa"].pop("concern_list"),
        }
        for name, change in bad.items():
            with self.assertRaises(safety.SafetyMapError, msg=name):
                self.load_modified(change)

    def test_every_concern_entry_has_group_and_reason(self):
        concern = safety_map()["efsa"]["concern_list"]
        self.assertEqual(set(concern["groups"]), {"genotoxico-carcinogeno", "toxico-con-limite", "furocumarina-fototoxica", "veneno-potente"})
        for entry in concern["substances"]:
            self.assertIn(entry["group"], concern["groups"])


if __name__ == "__main__":
    unittest.main()
