import unittest

import taxonomy_support
from catalog_seed import workdb
from catalog_seed.citations import MAX_CANDIDATES, ReferenceIndex, alpha_prefix, normalize_key
from catalog_seed.taxonomy import Entry, build_universe
from catalog_seed.usda_assign import assign_usda
from catalog_seed.workdb import Row


def refs(*keys):
    return ReferenceIndex([{"reference": k, "longref": "Larga de " + k} for k in keys])


def names(candidates):
    return [c["reference"] for c in candidates]


class CitationCandidatesTest(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_key("Burkill, 1966"), "burkill1966")
        self.assertEqual(alpha_prefix("Eb24: 441"), "eb")
        self.assertEqual(alpha_prefix("15"), "")

    def test_exact_key_brings_only_its_entry(self):
        index = refs("Burkill, 1966", "Burkill, 1935", "EB", "EB35:24")
        found = index.candidates("EB35:24")
        self.assertEqual(names(found), ["EB35:24", "EB"])
        self.assertEqual(found[0]["match"], "exacta")
        self.assertEqual(found[0]["ref"], "usda_reference:EB35:24")
        self.assertEqual(found[0]["longref"], "Larga de EB35:24")

    def test_exact_key_without_prefix_candidates_is_alone(self):
        self.assertEqual(names(refs("15", "16").candidates("15")), ["15"])

    def test_normalized_equal_key(self):
        index = refs("Burkill, 1966", "Burkill, 1935", "EB")
        found = index.candidates("Burkill,1966")
        self.assertEqual(names(found), ["Burkill, 1966", "Burkill, 1935"])
        self.assertEqual([c["match"] for c in found], ["normalizada", "prefijo"])

    def test_woi_number_finds_woi(self):
        index = refs("WOI", "Burkill, 1966", "WOIT")
        self.assertEqual(names(index.candidates("Woi.10"))[0], "WOI")
        self.assertNotIn("Burkill, 1966", names(index.candidates("Woi.10")))

    def test_eb_with_volume_gives_eb_then_volumes_up_to_the_cap(self):
        keys = ["EB"] + ["EB%d:%d" % (v, v) for v in range(40, 50)] + ["Burkill, 1966"]
        found = refs(*keys).candidates("Eb24: 441")
        self.assertEqual(len(found), MAX_CANDIDATES)
        self.assertEqual(names(found)[0], "EB")
        self.assertTrue(all(n.startswith("EB") for n in names(found)))

    def test_cap_and_no_candidates(self):
        index = refs(*["Abc%d" % i for i in range(9)])
        self.assertEqual(len(index.candidates("Abc")), 5)
        self.assertEqual(len(index.candidates("Abc", limit=2)), 2)
        self.assertEqual(index.candidates("Zzz.1"), [])
        self.assertEqual(index.candidates("12"), [])

    def test_longer_common_prefix_goes_first(self):
        found = refs("EB48:111", "EB24:1", "EB").candidates("Eb24:441")
        self.assertEqual(names(found), ["EB24:1", "EB", "EB48:111"])


def taxon(fnfnum, name, author=""):
    return Row("usda_taxon", fnfnum, {"taxon": name, "taxauthor": author}, raw_name_cell=name, fnfnum=fnfnum)


def use(ethno, name, activity, country, reference, author=""):
    content = {"activity": activity, "taxon": name, "reference": reference}
    if country:
        content["country"] = country
    if author:
        content["taxauthor"] = author
    return Row("usda_use", ethno, content, raw_name_cell=name)


class AssignUsdaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wcvp, cls.wfo = taxonomy_support.backbones()

    def setUp(self):
        self.uni = build_universe([Entry("usda", "usda:10", "Matricaria chamomilla", "L."), Entry("usda", "usda:11", "Mentha piperita", "L."),
                                   Entry("usda", "usda:12", "Gossypium sp")], self.wcvp, self.wfo)
        self.db = workdb.open_db(":memory:")
        rows = [
            taxon("10", "Matricaria chamomilla", "L."), taxon("11", "Mentha piperita", "L."), taxon("99", "Planta fantasma"),
            Row("usda_common_name", "10-1", {"name": "Chamomile", "language": "en"}, raw_name_cell="Chamomile", fnfnum="10"),
            Row("usda_common_name", "10-2", {"name": "Manzanilla (es)", "language": "und"}, raw_name_cell="Manzanilla (es)", fnfnum="10"),
            Row("usda_common_name", "99-1", {"name": "Fantasma", "language": "en"}, raw_name_cell="Fantasma", fnfnum="99"),
            Row("usda_part", "10-FL", {"ppco": "FL", "ppna": "Flower", "rows": 3, "has_eo": True, "eo_compounds": ["BISABOLOL"],
                                       "top_amount": [], "top_eo": []}, raw_name_cell="Matricaria chamomilla", fnfnum="10"),
            use("1", "Matricaria chamomilla", "Fever", "Egypt", "Burkill,1966", "L."),
            use("2", "Matricaria recutita", "Fever", "Spain", "Woi.10", "L."),
            use("3", "Matricaria recutita", "Fever", "Egypt", "Woi.10", "L."),
            use("4", "Matricaria recutita", "Colic", "", "Eb24: 441", "L."),
            use("20", "Mentha piperita", "Colic", "Italy", "EB35:24", "L."),
            use("30", "Quercus nonexistens", "Cough", "Peru", "Woi.10"),
            use("31", "Quercus nonexistens", "Cough", "Peru", "Woi.10"),
            Row("usda_reference", "Burkill, 1966", {"reference": "Burkill, 1966", "longref": "Burkill 1966 Dictionary"}, raw_name_cell="Burkill, 1966"),
            Row("usda_reference", "WOI", {"reference": "WOI", "longref": "The Wealth of India"}, raw_name_cell="WOI"),
            Row("usda_reference", "EB", {"reference": "EB", "longref": "Economic Botany"}, raw_name_cell="EB"),
            Row("usda_reference", "EB35:24", {"reference": "EB35:24", "longref": "Econ Bot 35: 24"}, raw_name_cell="EB35:24"),
        ]
        workdb.replace_source(self.db, "usda", rows, "test", {})

    def run_assign(self):
        return assign_usda(self.uni, self.db)

    def test_rows_under_a_synonym_reach_the_plant(self):
        result = self.run_assign()
        groups = {g["activity"]: g for g in result.by_plant["matricaria-chamomilla"]["useGroups"]}
        self.assertEqual(sorted(groups), ["Colic", "Fever"])
        self.assertEqual(groups["Fever"]["n"], 3)
        self.assertEqual(groups["Fever"]["refs"], ["usda_use:1", "usda_use:2", "usda_use:3"])
        self.assertEqual(groups["Fever"]["countries"], ["Egypt", "Spain"])
        self.assertEqual(groups["Colic"]["countries"], [])

    def test_keys_stay_as_they_come_with_candidates(self):
        fever = result_group(self.run_assign(), "matricaria-chamomilla", "Fever")
        self.assertEqual([(k["key"], k["n"]) for k in fever["keys"]], [("Woi.10", 2), ("Burkill,1966", 1)])
        woi, burkill = fever["keys"]
        self.assertEqual(names(woi["candidates"]), ["WOI"])
        self.assertEqual(woi["candidates"][0]["longref"], "The Wealth of India")
        self.assertEqual(woi["candidates"][0]["ref"], "usda_reference:WOI")
        self.assertEqual(names(burkill["candidates"]), ["Burkill, 1966"])

    def test_eb_volume_key_gets_eb_and_volumes(self):
        colic = result_group(self.run_assign(), "matricaria-chamomilla", "Colic")
        self.assertEqual(names(colic["keys"][0]["candidates"]), ["EB", "EB35:24"])

    def test_names_and_parts_are_assigned_by_fnfnum(self):
        plant = self.run_assign().by_plant["matricaria-chamomilla"]
        self.assertEqual([(c["name"], c["language"], c["ref"]) for c in plant["commonNames"]],
                         [("Chamomile", "en", "usda_common_name:10-1"), ("Manzanilla (es)", "und", "usda_common_name:10-2")])
        part = plant["parts"][0]
        self.assertEqual((part["ppco"], part["hasEo"], part["eoCompounds"], part["ref"]), ("FL", True, ["BISABOLOL"], "usda_part:10-FL"))

    def test_unassigned_rows_report_the_reason(self):
        result = self.run_assign()
        by_kind = {(u["kind"], u["name"]): u for u in result.unassigned}
        quercus = by_kind[("usda_use", "Quercus nonexistens")]
        self.assertEqual((quercus["reason"], quercus["rows"], quercus["examples"]), ("sin-resolver", 2, ["30", "31"]))
        ghost = by_kind[("usda_common_name", "Fantasma")]
        self.assertEqual((ghost["reason"], ghost["rows"]), ("fnfnum-sin-planta", 1))
        self.assertEqual(result.stats["use_rows_assigned"], 5)
        self.assertEqual(result.stats["use_rows_unassigned"], 2)
        self.assertEqual(result.stats["use_rows_unassigned_by_reason"], {"sin-resolver": 2})
        self.assertEqual(result.stats["short_keys_without_candidates"], 0)

    def test_result_is_deterministic(self):
        first = self.run_assign().canonical()
        second = self.run_assign().canonical()
        self.assertEqual(first, second)


def result_group(result, plant_id, activity):
    return next(g for g in result.by_plant[plant_id]["useGroups"] if g["activity"] == activity)


if __name__ == "__main__":
    unittest.main()


class FusedHeterotypicUsdaTest(unittest.TestCase):
    """Un heterotípico fusionado por la regla de colisiones comparte la planta del aceptado en todas las asignaciones."""

    @classmethod
    def setUpClass(cls):
        import collision_support as cs
        cls.wcvp, cls.wfo = cs.backbones()
        entries = [Entry("usda", "usda:1", "Cinnamomum verum"), Entry("usda", "usda:2", "Cinnamomum zeylanicum"),
                   Entry("usda", "usda:3", "Cinnamomum aromaticum")]
        cls.uni = build_universe(entries, cls.wcvp, cls.wfo,
                                 rules=cs.rules_for(build_universe(entries, cls.wcvp, cls.wfo), {
                                     "Cinnamomum zeylanicum": ("fuse", "redireccion"), "Cinnamomum aromaticum": ("separate", "articulo-propio")}))

    def test_names_parts_and_use_rows_of_the_fused_name_reach_the_accepted_plant(self):
        db = workdb.open_db(":memory:")
        workdb.replace_source(db, "usda", [
            taxon("1", "Cinnamomum verum"), taxon("2", "Cinnamomum zeylanicum"), taxon("3", "Cinnamomum aromaticum"),
            Row("usda_common_name", "2-1", {"name": "Ceylon cinnamon", "language": "en"}, raw_name_cell="Ceylon cinnamon", fnfnum="2"),
            Row("usda_part", "2-BK", {"ppco": "BK", "ppna": "Bark", "rows": 2, "has_eo": False}, raw_name_cell="Cinnamomum zeylanicum", fnfnum="2"),
            Row("usda_common_name", "3-1", {"name": "Cassia", "language": "en"}, raw_name_cell="Cassia", fnfnum="3"),
            use("1", "Cinnamomum verum", "Colic", "India", "Woi.1"),
            use("2", "Cinnamomum zeylanicum", "Colic", "Sri Lanka", "Woi.1"),
            use("3", "Cinnamomum aromaticum", "Cough", "China", "Woi.1"),
        ], "test", {})
        result = assign_usda(self.uni, db)
        verum = result.by_plant["cinnamomum-verum"]
        self.assertEqual([c["ref"] for c in verum["commonNames"]], ["usda_common_name:2-1"])
        self.assertEqual([p["ref"] for p in verum["parts"]], ["usda_part:2-BK"])
        self.assertEqual([(g["activity"], g["n"], g["countries"]) for g in verum["useGroups"]], [("Colic", 2, ["India", "Sri Lanka"])])
        self.assertEqual([c["ref"] for c in result.by_plant["cinnamomum-aromaticum"]["commonNames"]], ["usda_common_name:3-1"])
        self.assertEqual(result.unassigned, [])
        self.assertEqual(result.stats["use_rows_assigned"], 3)
