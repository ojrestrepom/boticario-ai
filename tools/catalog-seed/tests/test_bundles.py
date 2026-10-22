import contextlib
import copy
import io
import json
import os
import tempfile
import unittest

import bundles_support as bs
import extract_support
import fixtures_support as fx
import support  # noqa: F401

from catalog_seed import bundles, cli, goals, workdb
from catalog_seed.schema import DEFAULT_RECORD_SCHEMA, load_schema, validate
from catalog_seed.seed import canonical_json, compute_plan
from catalog_seed.sources import TOOL_DIR
from catalog_seed.validate import ema_goal_support, has_severe_interactions, is_toxic_by_tppt, validate_record

BUNDLE_SCHEMA = TOOL_DIR / "schema" / "bundle.schema.json"
WIKIPEDIA_PLANTS = {"lavandula-angustifolia", "passiflora-incarnata", "hypericum-perforatum"}


def cited_refs(bundle):
    """Todo ref que menciona el paquete fuera de su diccionario `refs`."""
    found = set()

    def visit(node):
        if isinstance(node, dict):
            if isinstance(node.get("ref"), str):
                found.add(node["ref"])
            if isinstance(node.get("refs"), list):
                found.update(r for r in node["refs"] if isinstance(r, str))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit({k: v for k, v in bundle.items() if k != "refs"})
    return found


class BundleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = bs.World()
        cls.schema = load_schema(BUNDLE_SCHEMA)
        cls.built = cls.world.build()

    def ids(self, bundle):
        return {i["qid"] for i in bundle["sections"]["wikidata"]["items"]}


class FormatTests(BundleTestCase):
    def test_every_plant_has_a_bundle_that_meets_the_schema(self):
        self.assertEqual(sorted(self.built), ["cinnamomum-verum", "hypericum-perforatum", "lavandula-angustifolia", "lavandula-latifolia",
                                              "mentha-spicata", "passiflora-incarnata"])
        for plant_id, bundle in self.built.items():
            self.assertEqual(validate(bundle, self.schema), [], plant_id)
            self.assertEqual(bundle["plantKey"], plant_id)
            self.assertEqual(bundle["identity"]["proposedId"], plant_id)
            self.assertEqual(bundle["bundleVersion"], "1")

    def test_every_cited_ref_is_in_the_dictionary_and_none_is_orphan(self):
        for plant_id, bundle in self.built.items():
            self.assertEqual(cited_refs(bundle), set(bundle["refs"]), plant_id)

    def test_refs_have_dataset_label_license_and_the_dataset_is_a_source(self):
        for bundle in self.built.values():
            for ref, entry in bundle["refs"].items():
                self.assertIn(entry["dataset"], bs.LICENSES, ref)
                self.assertTrue(entry["label"] and entry["license"], ref)

    def test_row_refs_follow_record_type_colon_row_key(self):
        refs = self.built["lavandula-angustifolia"]["refs"]
        for expected in ("wcvp:1", "wfo:wfo-0000224116", "usda_common_name:1-1", "usda_part:1-FL", "usda_use:101", "usda_reference:WOI",
                         "ema_herbal:lavandulae-flos", "ema_pdf:lavandulae-flos:4.5", "efsa_botanic:1", "efsa_endpoint:7", "wikidata:Q42081",
                         "wikipedia_es:Lavandula angustifolia"):
            self.assertIn(expected, refs)
        self.assertIn("tppt_plant:P291", self.built["hypericum-perforatum"]["refs"])
        self.assertIn("commons:File:Hiperico.jpg", self.built["hypericum-perforatum"]["refs"])

    def test_hash_is_the_sha256_of_the_canonical_json_without_the_hash(self):
        bundle = self.built["lavandula-angustifolia"]
        body = {k: v for k, v in bundle.items() if k != "bundleHash"}
        import hashlib
        self.assertEqual(bundle["bundleHash"], "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest())
        self.assertEqual(bundle["bundleHash"], bundles.bundle_hash(bundle))

    def test_all_sections_are_present_even_when_empty(self):
        for bundle in self.built.values():
            self.assertEqual(sorted(bundle["sections"]), sorted(bundles.SECTIONS))

    def test_validator_fixtures_meet_the_bundle_schema(self):
        for name in ("matricaria", "hiperico"):
            self.assertEqual(validate(fx.bundle(name), self.schema), [], name)

    def test_schema_rejects_a_malformed_bundle(self):
        bundle = copy.deepcopy(self.built["lavandula-angustifolia"])
        bundle["sections"].pop("uses")
        bundle["identity"]["extra"] = 1
        bundle["refs"]["wcvp:1"]["dataset"] = "otra-fuente"
        errors = validate(bundle, self.schema)
        self.assertTrue(any("uses" in e for e in errors) and any("extra" in e for e in errors) and any("dataset" in e for e in errors), errors)


class DeterminismTests(BundleTestCase):
    def test_two_builds_are_identical(self):
        again = self.world.build()
        self.assertEqual({k: canonical_json(v) for k, v in again.items()}, {k: canonical_json(v) for k, v in self.built.items()})

    def test_an_input_change_changes_only_that_plants_hash(self):
        world = bs.World()
        for row in world.rows["ema_pdf"]:
            if row.row_key == "hyperici-herba-0:4.3":
                row.content["text"] = "Otro texto de contraindicaciones."
        changed = world.build()
        differing = {k for k in changed if changed[k]["bundleHash"] != self.built[k]["bundleHash"]}
        self.assertEqual(differing, {"hypericum-perforatum"})

    def test_a_wikidata_change_of_one_plant_changes_only_its_hash(self):
        world = bs.World()
        world.rows["wikidata"][4].content["spanishNames"] = ["hierba de San Juan", "hipérico"]
        changed = world.build()
        self.assertEqual({k for k in changed if changed[k]["bundleHash"] != self.built[k]["bundleHash"]}, {"hypericum-perforatum"})

    def test_a_subset_gives_the_same_bundles(self):
        subset = self.world.build(plant_ids=["mentha-spicata"])
        self.assertEqual(list(subset), ["mentha-spicata"])
        self.assertEqual(subset["mentha-spicata"]["bundleHash"], self.built["mentha-spicata"]["bundleHash"])


class HomonymFilterTests(BundleTestCase):
    def test_lavender_has_nothing_from_lavandula_latifolia(self):
        lavender = self.built["lavandula-angustifolia"]
        text = canonical_json(lavender)
        self.assertEqual(self.ids(lavender), {"Q42081"})
        for leak in ("Q905916", "alhucema", "Spike lavender", "usda_use:201", "efsa_botanic:4", "usda_common_name:2-1", "Lavandula latifolia"):
            self.assertNotIn(leak, text)
        latifolia = self.built["lavandula-latifolia"]
        self.assertEqual(self.ids(latifolia), {"Q905916"})
        self.assertIn("usda_use:201", latifolia["refs"])
        self.assertIn("efsa_botanic:4", latifolia["refs"])

    def test_passionflower_has_nothing_from_passiflora_edulis(self):
        passionflower = self.built["passiflora-incarnata"]
        text = canonical_json(passionflower)
        self.assertEqual(self.ids(passionflower), {"Q128939"})
        for leak in ("Q156790", "maracuyá", "Passiflora edulis", "wikipedia_es:Passiflora edulis"):
            self.assertNotIn(leak, text)


class WikipediaTests(BundleTestCase):
    def test_wikipedia_refs_carry_the_article_url_and_the_share_alike_license(self):
        for bundle in self.built.values():
            for ref, entry in bundle["refs"].items():
                if entry["dataset"] == "wikipedia_es":
                    self.assertTrue(entry.get("url", "").startswith("https://es.wikipedia.org/wiki/"), ref)
                    self.assertEqual(entry["license"], "CC BY-SA 4.0")
        description = self.built["lavandula-angustifolia"]["sections"]["descriptions"][0]
        self.assertEqual(description["url"], "https://es.wikipedia.org/wiki/Lavandula_angustifolia")
        self.assertEqual(description["license"], "CC BY-SA 4.0")

    def test_wikimedia_refs_have_their_license_and_url(self):
        refs = self.built["hypericum-perforatum"]["refs"]
        self.assertEqual(refs["commons:File:Hiperico.jpg"]["license"], "Public domain")
        self.assertEqual(refs["commons:File:Hiperico.jpg"]["url"], "https://commons.wikimedia.org/wiki/File:Hiperico.jpg")
        self.assertEqual(refs["wikidata:Q158289"]["url"], "https://www.wikidata.org/wiki/Q158289")
        image = self.built["hypericum-perforatum"]["sections"]["images"][0]
        self.assertIsNone(image["author"])
        self.assertFalse(image["attributionRequired"])


class UsesTests(BundleTestCase):
    def groups(self, plant_id="lavandula-angustifolia"):
        return {g["activity"]: g for g in self.built[plant_id]["sections"]["uses"]}

    def test_candidates_come_with_their_usda_reference_ref_and_citation(self):
        sedative = self.groups()["Sedative"]
        self.assertEqual(sedative["n"], 2)
        self.assertEqual(sedative["countries"], ["France", "Spain"])
        self.assertEqual(sedative["refs"], ["usda_use:101", "usda_use:102"])
        self.assertEqual(sorted(sedative["citations"]), ["Burkill,1966", "Woi.10"])
        self.assertEqual(sedative["candidates"]["Woi.10"], [{"ref": "usda_reference:WOI", "citation": "The Wealth of India"}])
        self.assertEqual(sedative["candidates"]["Burkill,1966"][0]["ref"], "usda_reference:Burkill, 1966")
        refs = self.built["lavandula-angustifolia"]["refs"]
        self.assertIn("usda_reference:WOI", refs)
        self.assertEqual(refs["usda_reference:WOI"]["dataset"], "usda")

    def test_a_key_without_candidates_keeps_the_key_and_has_no_entry(self):
        carminative = self.groups()["Carminative"]
        self.assertEqual(carminative["citations"], ["Woi.Syria"])
        self.assertNotIn("Woi.Syria", carminative["candidates"])

    def test_the_use_cap_keeps_the_groups_with_more_rows_and_says_so(self):
        capped = self.world.build(limits={"useGroups": 1}, plant_ids=["lavandula-angustifolia"])["lavandula-angustifolia"]
        self.assertEqual([g["activity"] for g in capped["sections"]["uses"]], ["Sedative"])
        self.assertTrue(any("se omitieron 1 grupos con 1 filas" in n for n in capped["identity"]["notes"]))
        self.assertNotIn("usda_use:103", capped["refs"])
        self.assertEqual(validate(capped, self.schema), [])
        self.assertNotEqual(capped["bundleHash"], self.built["lavandula-angustifolia"]["bundleHash"])

    def test_ref_and_key_caps_are_reported(self):
        capped = self.world.build(limits={"useRefs": 1, "useKeys": 1}, plant_ids=["lavandula-angustifolia"])["lavandula-angustifolia"]
        sedative = {g["activity"]: g for g in capped["sections"]["uses"]}["Sedative"]
        self.assertEqual((len(sedative["refs"]), sedative["refsTotal"], len(sedative["citations"]), sedative["citationsTotal"]), (1, 2, 1, 2))
        self.assertEqual(validate(capped, self.schema), [])


class SafetyTests(BundleTestCase):
    def entries(self, plant_id, source):
        return [e for e in self.built[plant_id]["sections"]["safety"] if e["source"] == source]

    def test_hypericum_has_tppt_medium_and_severe_ema_interactions(self):
        bundle = self.built["hypericum-perforatum"]
        tppt = self.entries("hypericum-perforatum", "tppt")[0]
        self.assertEqual((tppt["level"], tppt["humanToxicity"]), ("medio", "phototoxic"))
        self.assertEqual(tppt["categories"], [{"category": "phototoxic", "level": "medio"}])
        self.assertTrue(tppt["levelReason"])
        self.assertEqual([t["name"] for t in tppt["toxins"]], ["Hypericin"])
        self.assertNotIn("dose", canonical_json(tppt))      # las dosis de TPPT no van al paquete
        sections = {e["section"]: e for e in self.entries("hypericum-perforatum", "ema_pdf")}
        self.assertEqual(sorted(sections), ["4.3", "4.4", "4.5"])
        self.assertTrue(sections["4.5"]["severeInteractions"])
        self.assertEqual((sections["4.5"]["interactionClass"], sections["4.5"]["level"]), ("severe", "alto"))
        self.assertIn("contraindicated", sections["4.5"]["matchedPatterns"])
        self.assertFalse(sections["4.3"]["severeInteractions"])
        self.assertTrue(has_severe_interactions(bundle))
        self.assertFalse(is_toxic_by_tppt(bundle))

    def test_ema_text_that_reports_nothing_is_not_severe(self):
        entry = [e for e in self.entries("lavandula-angustifolia", "ema_pdf") if e["section"] == "4.5"][0]
        self.assertEqual((entry["interactionClass"], entry["level"], entry["severeInteractions"]), ("none-reported", None, False))
        self.assertFalse(has_severe_interactions(self.built["lavandula-angustifolia"]))

    def test_public_statement_with_safety_data_is_medium(self):
        entry = self.entries("passiflora-incarnata", "ema_pdf")[0]
        self.assertEqual((entry["section"], entry["interactionClass"], entry["level"], entry["safetyData"]), ("CONCLUSIONS", "statement-with-safety", "medio", True))
        self.assertFalse(entry["severeInteractions"])

    def test_nontoxic_tppt_sets_no_level(self):
        entry = self.entries("passiflora-incarnata", "tppt")[0]
        self.assertEqual((entry["level"], entry["levelReason"]), (None, None))
        self.assertEqual(entry["humanToxicity"], "nontoxic")

    def test_efsa_lists_the_substances_that_set_the_level_and_the_evidence(self):
        entry = self.entries("lavandula-angustifolia", "efsa")[0]
        self.assertEqual(entry["level"], "medio")
        self.assertEqual([s["substance"] for s in entry["concernSubstances"]], ["alpha-thujone"])
        self.assertEqual(entry["concernSubstances"][0]["group"], "toxico-con-limite")
        self.assertEqual([s["substance"] for s in entry["evidenceSubstances"]], ["1,8-cineole"])
        self.assertEqual(entry["concernGroups"], ["toxico-con-limite"])
        self.assertEqual(entry["rowsCounted"], 2)             # la fila «Non Detected Value (<LOD)» no cuenta
        self.assertNotIn("beta-thujone", canonical_json(entry))
        self.assertEqual(len(entry["studies"]), 1)
        self.assertEqual(self.entries("lavandula-angustifolia", "efsa")[0]["ref"], "efsa_botanic:1")

    def test_efsa_evidence_only_sets_no_level(self):
        entry = self.entries("lavandula-latifolia", "efsa")[0]
        self.assertEqual((entry["level"], entry["concernSubstances"], entry["levelReason"]), (None, [], None))
        self.assertEqual([s["substance"] for s in entry["evidenceSubstances"]], ["Camphor"])

    def test_failed_or_incomplete_extraction_is_declared(self):
        mint = self.built["mentha-spicata"]
        failure = [e for e in mint["sections"]["safety"] if e.get("status") == "extraccion-fallida"]
        self.assertEqual(len(failure), 1)
        self.assertIn("4.4", failure[0]["reason"])
        flags = {f["code"]: f for f in mint["identity"]["flags"]}
        self.assertEqual(flags["extraccion-seguridad-fallida"]["target"], "safety")
        cinnamon = [e for e in self.built["cinnamomum-verum"]["sections"]["safety"] if e["source"] == "ema_pdf"]
        self.assertEqual([(e["slug"], e["status"]) for e in cinnamon], [("cinnamomi-cortex", "extraccion-fallida")])

    def test_a_plant_without_ema_or_tppt_rows_only_has_what_efsa_gives(self):
        self.assertEqual([e["source"] for e in self.built["lavandula-latifolia"]["sections"]["safety"]], ["efsa"])


class GoalCandidatesTests(BundleTestCase):
    def candidates(self, plant_id):
        out = {}
        for row in self.built[plant_id]["sections"]["regulatory"]:
            out[row["slug"]] = [(c["goal"], c["subarea"]) for c in row["goalCandidates"]]
        return out

    def test_combined_outcome_is_split_by_semicolon_and_counts(self):
        row = self.built["mentha-spicata"]["sections"]["regulatory"][0]
        self.assertEqual(row["outcome"], "European Union herbal monograph;European Union list entry")
        self.assertEqual(self.candidates("mentha-spicata")["menthae-spicatae-folium"], [("otros-objetivos", "digestion"), ("alivio-respiratorio", None)])
        self.assertEqual(row["goalCandidates"][1]["areaEs"], goals.load_goals_map()["areas"]["Cough and cold"]["es"])

    def test_hypericum_candidate_for_stress_and_the_combination_does_not_count(self):
        candidates = self.candidates("hypericum-perforatum")
        self.assertEqual(candidates["hyperici-herba-0"], [("relajacion-estres", None), ("otros-objetivos", "digestion")])
        self.assertEqual(candidates["hyperici-herba"], [])
        merged = {r["slug"]: r for r in self.built["hypericum-perforatum"]["sections"]["regulatory"]}["hyperici-herba"]
        self.assertEqual(merged["therapeuticAreas"], ["Urinary tract and genital disorders"])   # solo las áreas de su fila, no las de Cimicifuga
        self.assertEqual(merged["combination"], "Yes")

    def test_public_statement_gives_no_candidates(self):
        self.assertEqual(self.candidates("passiflora-incarnata"), {"passiflorae-herba": []})

    def test_candidates_agree_with_what_the_validator_accepts(self):
        goals_map = goals.load_goals_map()
        for plant_id, bundle in self.built.items():
            support, _ = ema_goal_support(bundle, goals_map)
            expected = {(c["goal"], c["subarea"]) for row in bundle["sections"]["regulatory"] for c in row["goalCandidates"]}
            self.assertEqual(expected, set(support), plant_id)


class IdentityTests(BundleTestCase):
    def test_fused_heterotypic_brings_its_rows_and_the_review_flag(self):
        bundle = self.built["cinnamomum-verum"]
        identity = bundle["identity"]
        self.assertEqual(identity["aliases"], ["cinnamomum-zeylanicum"])
        self.assertEqual(identity["collision"]["role"], "aceptado")
        self.assertEqual([f["name"] for f in identity["collision"]["fused"]], ["Cinnamomum zeylanicum"])
        self.assertIn("fusion-heterotipica", [f["code"] for f in identity["flags"]])
        self.assertIn(("Cinnamomum zeylanicum", "heterotipico-fusionado"), [(n["name"], n["reason"]) for n in identity["nameSet"]])
        self.assertIn(("wcvp:9", "heterotipico-fusionado"), [(t["ref"], t["role"]) for t in bundle["sections"]["taxonomy"]])
        self.assertIn("usda_use:901", bundle["refs"])
        self.assertIn("usda_common_name:9-1", bundle["refs"])
        self.assertTrue(any("Cinnamomum zeylanicum" in n for n in identity["notes"]))

    def test_accepted_names_and_name_set(self):
        identity = self.built["lavandula-angustifolia"]["identity"]
        self.assertEqual(identity["primaryBackbone"], "wcvp")
        self.assertEqual(identity["accepted"]["wcvp"]["name"], "Lavandula angustifolia")
        self.assertEqual(identity["accepted"]["wfo"]["id"], "wfo-0000224116")
        self.assertEqual(identity["nameSet"][0]["reason"], "universe")
        self.assertIn(("Lavandula officinalis", "sinonimo-homotipico", "wcvp"), [(n["name"], n["reason"], n["backbone"]) for n in identity["nameSet"]])
        self.assertIsNone(identity["collision"])
        self.assertEqual(identity["family"], "Lamiaceae")

    def test_distribution_has_native_regions_and_area_counts(self):
        distribution = self.built["lavandula-angustifolia"]["sections"]["distribution"]
        self.assertEqual(distribution["native"], ["Southwestern Europe"])
        self.assertEqual(distribution["nativeAreas"], ["France", "Spain"])
        self.assertEqual((distribution["nativeAreaCount"], distribution["introducedAreaCount"], distribution["introduced"]), (2, 1, ["Middle Europe"]))
        self.assertIsNone(self.built["mentha-spicata"]["sections"]["distribution"])

    def test_wikidata_status_is_declared_in_the_section_and_in_the_flags(self):
        self.assertEqual(self.built["lavandula-angustifolia"]["sections"]["wikidata"]["status"], "con-item")
        cinnamon = self.built["cinnamomum-verum"]
        self.assertEqual(cinnamon["sections"]["wikidata"], {"status": "sin-item", "items": []})
        self.assertIn(("wikidata-sin-item", "wikidata"), [(f["code"], f["target"]) for f in cinnamon["identity"]["flags"]])
        without = self.world.build(with_wikidata=False)
        self.assertEqual(without["lavandula-angustifolia"]["sections"]["wikidata"]["status"], "sin-respuesta")
        self.assertIn("wikidata-sin-respuesta", [f["code"] for f in without["lavandula-angustifolia"]["identity"]["flags"]])
        self.assertEqual(without["lavandula-angustifolia"]["sections"]["images"], [])
        for bundle in without.values():
            self.assertEqual(validate(bundle, self.schema), [])

    def test_names_come_from_their_sources_with_refs(self):
        names = [(n["source"], n["text"], n["language"]) for n in self.built["lavandula-angustifolia"]["sections"]["names"]]
        self.assertIn(("usda", "English Lavender", "en"), names)
        self.assertIn(("wikidata", "espliego", "es"), names)
        self.assertIn(("wikidata", "lavanda", "es"), names)


class DisabledSourcesTests(BundleTestCase):
    def datasets(self, bundle):
        return {e["dataset"] for e in bundle["refs"].values()}

    def test_disabled_wikipedia_drops_its_rows_and_refs_and_changes_only_the_plants_that_had_it(self):
        built = self.world.build(disabled=("wikipedia_es",))
        for bundle in built.values():
            self.assertNotIn("wikipedia_es", self.datasets(bundle))
            self.assertEqual(bundle["sections"]["descriptions"], [])
            self.assertEqual(validate(bundle, self.schema), [])
        changed = {k for k in built if built[k]["bundleHash"] != self.built[k]["bundleHash"]}
        self.assertEqual(changed, WIKIPEDIA_PLANTS)
        self.assertTrue(all(self.built[k]["sections"]["descriptions"] for k in WIKIPEDIA_PLANTS))

    def test_plan_detects_only_the_plants_that_had_wikipedia(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed, directory = os.path.join(tmp, "seed"), os.path.join(tmp, "bundles")
            os.makedirs(os.path.join(seed, "plants"))
            for plant_id, bundle in self.built.items():
                with open(os.path.join(seed, "plants", plant_id + ".json"), "w", encoding="utf-8") as handle:
                    json.dump({"id": plant_id, "bundleHash": bundle["bundleHash"], "promptVersion": 2, "recordVersion": 1}, handle)
            self.assertEqual(compute_plan_ids(self.built, directory, seed), [])
            built = self.world.build(disabled=("wikipedia_es",))
            plan = compute_plan_ids(built, directory, seed)
            self.assertEqual(set(plan), WIKIPEDIA_PLANTS)

    def test_a_regenerated_record_without_wikipedia_passes_the_validator(self):
        built = self.world.build(disabled=("wikipedia_es",))["hypericum-perforatum"]
        schema, goals_map, catalog = load_schema(DEFAULT_RECORD_SCHEMA), goals.load_goals_map(), goals.load_goals_catalog()
        for description in (None, {"value": "La EMA tiene una monografía para la hierba del hipérico.", "refs": ["ema_herbal:hyperici-herba-0"]}):
            record = example_record(built, description)
            errors, _ = validate_record(record, built, schema, goals_map, catalog)
            self.assertEqual(errors, [], description)
        # Con Wikipedia activa, el mismo registro con la descripción de Wikipedia exige el url del artículo en sus refs.
        with_wikipedia = self.built["hypericum-perforatum"]
        record = example_record(with_wikipedia, {"value": "Resumen del artículo.", "refs": ["wikipedia_es:Hypericum perforatum"]})
        errors, _ = validate_record(record, with_wikipedia, schema, goals_map, catalog)
        self.assertEqual(errors, [])
        del record["refs"]["wikipedia_es:Hypericum perforatum"]["url"]
        errors, _ = validate_record(record, with_wikipedia, schema, goals_map, catalog)
        self.assertTrue(errors)

    def test_each_source_can_be_turned_off_without_touching_the_others(self):
        expectations = {"usda": ({"usda"}, lambda b: not b["sections"]["uses"] and not b["sections"]["parts"]),
                        "tppt": ({"tppt"}, lambda b: all(e["source"] != "tppt" for e in b["sections"]["safety"])),
                        "efsa": ({"efsa"}, lambda b: all(e["source"] != "efsa" for e in b["sections"]["safety"])),
                        "ema_json": ({"ema_json"}, lambda b: not b["sections"]["regulatory"]),
                        "ema_pdf": ({"ema_pdf"}, lambda b: all(e["source"] != "ema_pdf" for e in b["sections"]["safety"])),
                        "commons": ({"commons"}, lambda b: not b["sections"]["images"])}
        for source, (gone, empty) in expectations.items():
            built = self.world.build(disabled=(source,))
            for plant_id, bundle in built.items():
                self.assertFalse(self.datasets(bundle) & gone, (source, plant_id))
                self.assertTrue(empty(bundle), (source, plant_id))
                self.assertEqual(validate(bundle, self.schema), [], (source, plant_id))

    def test_without_wikidata_there_is_no_wikipedia_or_commons_either(self):
        built = self.world.build(disabled=("wikidata",))
        for bundle in built.values():
            self.assertFalse(self.datasets(bundle) & {"wikidata", "wikipedia_es", "commons"})
            self.assertEqual((bundle["sections"]["descriptions"], bundle["sections"]["images"], bundle["sections"]["wikidata"]["items"]), ([], [], []))

    def test_disabling_the_main_taxonomy_fails(self):
        from catalog_seed.sources import SourceError
        with self.assertRaises(SourceError):
            self.world.build(disabled=("wcvp",))

    def test_validator_and_prompt_have_no_per_source_conditionals(self):
        validator = (TOOL_DIR / "catalog_seed" / "validate.py").read_text(encoding="utf-8")
        prompt = (TOOL_DIR / "prompt" / "consolidate.md").read_text(encoding="utf-8")
        self.assertNotIn("enabled", validator)
        self.assertNotIn("enabled", prompt)
        self.assertNotIn("sources.json", prompt)


def compute_plan_ids(built, directory, seed):
    bundles.write_bundles(built, directory, prune=True)
    return [p["id"] for p in compute_plan(directory, seed, 2, 1)]


def example_record(bundle, description):
    """Registro de ejemplo del hipérico (el del fixture del validador) adaptado a un paquete."""
    record = fx.record("hiperico")
    record["bundleHash"] = bundle["bundleHash"]
    record["description"] = description
    wcvp = "wcvp:7"
    record["scientificName"]["refs"] = [wcvp]
    record["family"]["refs"] = [wcvp]
    record["goals"][0]["refs"] = ["ema_herbal:hyperici-herba-0"]
    record["safety"]["refs"] = ["ema_pdf:hyperici-herba-0:4.5"]
    used = {wcvp, "ema_herbal:hyperici-herba-0", "ema_pdf:hyperici-herba-0:4.5"} | set(description["refs"] if description else [])
    record["refs"] = {ref: bundle["refs"][ref] for ref in sorted(used)}
    record["sources"] = sorted(({"dataset": e["dataset"], "license": e["license"]} for e in record["refs"].values()), key=lambda s: s["dataset"])
    return record


class WriteAndSizeTests(BundleTestCase):
    def test_write_prune_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundles.write_bundles(self.built, tmp)
            with open(os.path.join(tmp, "mentha-spicata.json"), encoding="utf-8") as handle:
                text = handle.read()
            self.assertEqual(text, canonical_json(self.built["mentha-spicata"]) + "\n")
            self.assertEqual(len(bundles.read_bundles(tmp)), len(self.built))
            some = {k: v for k, v in self.built.items() if k != "mentha-spicata"}
            self.assertEqual(bundles.write_bundles(some, tmp, prune=False), [])
            self.assertEqual(bundles.write_bundles(some, tmp, prune=True), ["mentha-spicata"])
            self.assertEqual(len(bundles.read_bundles(tmp)), len(self.built) - 1)

    def test_plant_id_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ids.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# plantas\nmentha-spicata\n\n  lavandula-angustifolia  \n")
            self.assertEqual(bundles.read_plant_ids(path), ["mentha-spicata", "lavandula-angustifolia"])

    def test_unknown_plant_is_an_error(self):
        from catalog_seed.sources import SourceError
        with self.assertRaises(SourceError):
            self.world.build(plant_ids=["no-existe"])

    def test_size_report_estimates_tokens_from_characters_over_three_and_a_half(self):
        report = bundles.size_report(list(self.built.values()), top=3)
        sizes = sorted(int(round(len(canonical_json(b)) / 3.5)) for b in self.built.values())
        self.assertEqual(report["max"], sizes[-1])
        self.assertEqual(report["total"], sum(sizes))
        self.assertEqual(report["p50"], sizes[int(round(0.5 * (len(sizes) - 1)))])
        self.assertEqual(report["plants"], len(sizes))
        self.assertEqual(len(report["top"]), 3)
        self.assertEqual(report["top"][0]["tokens"], sizes[-1])
        self.assertEqual(list(report["top"][0]["sections"]), sorted(report["top"][0]["sections"], key=lambda k: -report["top"][0]["sections"][k]))
        text = bundles.format_sizes(report)
        self.assertIn("p50", text)
        self.assertIn("máximo", text)

    def test_coverage_counts_plants_with_and_without_each_section(self):
        coverage = bundles.coverage(list(self.built.values()))
        self.assertEqual(coverage["plants"], 6)
        self.assertEqual(coverage["withSection"]["regulatory"], 5)
        self.assertEqual(coverage["withoutSection"]["regulatory"], 1)
        self.assertEqual(coverage["wikidataStatus"], {"con-item": 4, "sin-item": 2})


class BundlesCommandTests(unittest.TestCase):
    """El comando `bundles` sobre un `sources.db` y un índice taxonómico de fixtures, sin red."""

    def test_command_writes_bundles_and_prints_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "sources.db")
            connection = workdb.open_db(db)
            world = bs.World()
            workdb.replace_source(connection, "usda", [r for r in world.rows["usda"] if r.record_type == "usda_taxon"] + [
                workdb.Row("usda_taxon", e.key.split(":")[1], {"taxon": e.name, "taxauthor": e.author}, raw_name_cell=e.name, fnfnum=e.key.split(":")[1])
                for e in bs.ENTRIES if e.source == "usda" and e.key != "usda:1"] + [r for r in world.rows["usda"] if r.record_type != "usda_taxon"],
                "prueba", {})
            workdb.replace_source(connection, "ema_json", world.rows["ema_json"], "prueba", {})
            connection.close()
            out, report = os.path.join(tmp, "bundles"), os.path.join(tmp, "report.json")
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = cli.main(["--cache-dir", os.path.join(tmp, "cache"), "bundles", "--db", db, "--taxonomy-db", bs.index_path(), "--out", out,
                                 "--report", report])
            self.assertEqual(code, 0)
            self.assertIn("paquetes escritos", stdout.getvalue())
            self.assertIn("p50", stdout.getvalue())
            written = bundles.read_bundles(out)
            self.assertIn("lavandula-angustifolia", {b["plantKey"] for b in written})
            schema = load_schema(BUNDLE_SCHEMA)
            for bundle in written:
                self.assertEqual(validate(bundle, schema), [])
                # Caché vacía: no se pide nada a la red. Las plantas sin aceptado (Cimicifuga, que el fixture no tiene) no se consultan.
                expected = "no-consultada" if bundle["identity"]["kind"] not in ("resolved", "heterotypic") else "sin-respuesta"
                self.assertEqual(bundle["sections"]["wikidata"]["status"], expected, bundle["plantKey"])
            with open(report, encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["stats"]["bundles"], len(written))
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cli.main(["bundle-sizes", "--bundles", out, "--top", "2"]), 0)
            self.assertIn("las plantas más grandes", stdout.getvalue())
            # Un subconjunto no retira los demás paquetes.
            ids = os.path.join(tmp, "ids.txt")
            with open(ids, "w", encoding="utf-8") as handle:
                handle.write("lavandula-angustifolia\n")
            with contextlib.redirect_stdout(io.StringIO()):
                cli.main(["--cache-dir", os.path.join(tmp, "cache"), "bundles", "--db", db, "--taxonomy-db", bs.index_path(), "--out", out, "--plants", ids])
            self.assertEqual(len(bundles.read_bundles(out)), len(written))


class RealBundlesTests(unittest.TestCase):
    """Con los paquetes reales de `data/work/bundles/` (se omiten si no existen: ejecute el comando `bundles`)."""

    @classmethod
    def setUpClass(cls):
        cls.directory = os.path.join(extract_support.REPO_ROOT, "data", "work", "bundles")
        if not os.path.isfile(os.path.join(cls.directory, "lavandula-angustifolia.json")):
            raise unittest.SkipTest("faltan los paquetes reales en data/work/bundles: ejecute el comando bundles")

    def bundle(self, plant_id):
        with open(os.path.join(self.directory, plant_id + ".json"), encoding="utf-8") as handle:
            return json.load(handle)

    def candidates(self, plant_id):
        return {(c["goal"], c["subarea"]) for r in self.bundle(plant_id)["sections"]["regulatory"] for c in r["goalCandidates"]}

    def test_lavender_and_passionflower_have_no_homonym_data(self):
        lavender = canonical_json(self.bundle("lavandula-angustifolia"))
        self.assertNotIn("Lavandula latifolia", lavender)
        self.assertNotIn("Q905916", lavender)
        passionflower = canonical_json(self.bundle("passiflora-incarnata"))
        self.assertNotIn("Passiflora edulis", passionflower)
        self.assertNotIn("Q156790", passionflower)

    def test_hypericum_has_severe_interactions_and_the_stress_goal_candidate(self):
        bundle = self.bundle("hypericum-perforatum")
        self.assertTrue(has_severe_interactions(bundle))
        self.assertIn(("relajacion-estres", None), self.candidates("hypericum-perforatum"))

    def test_mint_tea_tree_and_calendula_goal_candidates_from_the_split_outcome(self):
        self.assertIn(("otros-objetivos", "digestion"), self.candidates("mentha-x-piperita"))
        self.assertIn(("alivio-respiratorio", None), self.candidates("mentha-x-piperita"))
        self.assertEqual(self.candidates("melaleuca-alternifolia"), {("otros-objetivos", "boca-y-garganta"), ("cuidado-de-la-piel", None)})
        self.assertEqual(self.candidates("calendula-officinalis"), {("otros-objetivos", "boca-y-garganta"), ("cuidado-de-la-piel", None)})

    def test_bergamot_is_its_own_plant_and_cinnamon_brings_zeylanicum(self):
        bergamot = self.bundle("citrus-x-bergamia")
        self.assertEqual(bergamot["identity"]["name"], "Citrus × bergamia")
        self.assertEqual(bergamot["identity"]["collision"]["role"], "separada")
        cinnamon = self.bundle("cinnamomum-verum")
        self.assertEqual([f["name"] for f in cinnamon["identity"]["collision"]["fused"]], ["Cinnamomum zeylanicum"])
        self.assertIn("fusion-heterotipica", [f["code"] for f in cinnamon["identity"]["flags"]])

    def test_every_real_bundle_meets_the_schema(self):
        schema = load_schema(BUNDLE_SCHEMA)
        for name in sorted(os.listdir(self.directory)):
            if name.endswith(".json"):
                bundle = self.bundle(name[:-5])
                self.assertEqual(validate(bundle, schema), [], name)
                self.assertEqual(bundle["bundleHash"], bundles.bundle_hash(bundle), name)


if __name__ == "__main__":
    unittest.main()
