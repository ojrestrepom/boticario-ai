"""Regla de colisiones («criterio de Wikipedia») aplicada con datos: escenarios de la spec, sin red."""
import json
import os
import unittest

import collision_support as cs
import extract_support as support
import taxonomy_support
from catalog_seed.taxonomy import CollisionFileError, Entry, build_universe, load_rules
from catalog_seed.taxonomy.collisions import (DECISIONS_FORMAT, CollisionRules, dump_decisions, load_decisions, load_exceptions,
                                              name_key)


def usda(key, name, author=""):
    return Entry("usda", "usda:" + key, name, author)


class CollisionRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wcvp, cls.wfo = cs.backbones()
        cls.main_wcvp, cls.main_wfo = taxonomy_support.backbones()

    def build(self, entries, rules=None, main=False):
        wcvp, wfo = (self.main_wcvp, self.main_wfo) if main else (self.wcvp, self.wfo)
        return build_universe(entries, wcvp, wfo, rules=rules)

    def ids(self, uni):
        return sorted(p.id for p in uni.plants)

    def codes(self, plant):
        return [f["code"] for f in plant.review_flags]

    def test_cinnamon_fused_by_redirect(self):
        entries = [usda("1", "Cinnamomum verum"), usda("2", "Cinnamomum zeylanicum")]
        rules = cs.rules_for(self.build(entries), {"Cinnamomum zeylanicum": ("fuse", "redireccion")})
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["cinnamomum-verum"])
        plant = uni.plants[0]
        self.assertEqual((plant.name, plant.kind, plant.split), ("Cinnamomum verum", "resolved", False))
        self.assertEqual([e.key for e in plant.entries], ["usda:1", "usda:2"])
        self.assertEqual(plant.aliases, ["cinnamomum-zeylanicum"])
        self.assertIn("fusion-heterotipica", self.codes(plant))
        self.assertNotIn("grupo-partido", self.codes(plant))
        flag = [f for f in plant.review_flags if f["code"] == "fusion-heterotipica"][0]
        self.assertIn("Cinnamomum zeylanicum", flag["message"])
        self.assertEqual(set(flag), {"code", "target", "message"})
        self.assertEqual([m["state"] for m in uni.collisions], ["decidido"])
        self.assertEqual(uni.stats()["collision_members_fused"], 1)

    def test_bergamot_separated_by_own_article(self):
        entries = [usda("279", "Citrus limon"), Entry.from_text("ema", "ema:bergamot", "Citrus bergamia Risso & Poiteau.")]
        rules = cs.rules_for(self.build(entries, main=True), {"Citrus × bergamia": ("separate", "articulo-propio")})
        uni = self.build(entries, rules, main=True)
        self.assertEqual(self.ids(uni), ["citrus-x-bergamia", "citrus-x-limon"])
        bergamot = uni.plant("citrus-x-bergamia")
        self.assertEqual((bergamot.name, bergamot.kind), ("Citrus × bergamia", "heterotypic"))
        self.assertIn("grupo-partido", self.codes(bergamot))
        self.assertNotIn("fusion-heterotipica", self.codes(uni.plant("citrus-x-limon")))
        self.assertTrue(uni.plant("citrus-x-limon").split)

    def test_fennel_sweet_variety_separated_by_exception(self):
        entries = [usda("1", "Foeniculum vulgare"), usda("2", "Foeniculum vulgare var. dulce")]
        rules = cs.rules_for(self.build(entries), {"Foeniculum vulgare var. dulce": ("separate", "excepcion")},
                             exceptions=["Foeniculum vulgare var. dulce"])
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["foeniculum-vulgare", "foeniculum-vulgare-var-dulce"])
        sweet = uni.plant("foeniculum-vulgare-var-dulce")
        self.assertEqual(sweet.kind, "heterotypic")
        self.assertIn("grupo-partido", self.codes(sweet))
        self.assertEqual(uni.collisions[0]["exception"], "prueba")

    def test_thevetia_fused_with_cascabela_by_shared_article(self):
        entries = [usda("1", "Cascabela thevetia"), usda("2", "Thevetia peruviana")]
        rules = cs.rules_for(self.build(entries), {"Thevetia peruviana": ("fuse", "articulo-compartido")})
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["cascabela-thevetia"])
        plant = uni.plants[0]
        self.assertIn("fusion-heterotipica", self.codes(plant))
        self.assertEqual(plant.aliases, ["thevetia-peruviana"])
        self.assertEqual(uni.collisions[0]["reason"], "articulo-compartido")

    def test_new_group_without_decision_stays_split_with_flag(self):
        entries = [usda("1", "Cinnamomum verum"), usda("2", "Cinnamomum zeylanicum")]
        uni = self.build(entries, CollisionRules())
        self.assertEqual(self.ids(uni), ["cinnamomum-verum", "cinnamomum-zeylanicum"])
        for plant in uni.plants:
            self.assertIn("grupo-partido", self.codes(plant))
            self.assertNotIn("fusion-heterotipica", self.codes(plant))
        self.assertEqual([(m["state"], m["decision"]) for m in uni.collisions], [("sin-decision", "separate")])
        self.assertEqual(uni.stats()["collision_members_undecided"], 1)
        # build_universe sin reglas es lo mismo.
        self.assertEqual(self.ids(self.build(entries)), self.ids(uni))

    def test_homotypic_names_of_one_member_share_one_decision(self):
        entries = [usda("1", "Cascabela thevetia"), usda("2", "Thevetia peruviana"), usda("3", "Cerbera peruviana")]
        # Thevetia peruviana y Cerbera peruviana son homotípicos entre sí: un solo miembro (el basiónimo).
        uni = self.build(entries)
        self.assertEqual([m["name"] for m in uni.collisions], ["Cerbera peruviana"])
        self.assertEqual(sorted(uni.collisions[0]["entries"]), ["usda:2", "usda:3"])

    def test_partially_decided_group_separates_the_undecided_member(self):
        entries = [usda("1", "Cinnamomum verum"), usda("2", "Cinnamomum zeylanicum"), usda("3", "Cinnamomum aromaticum")]
        rules = cs.rules_for(self.build(entries), {"Cinnamomum zeylanicum": ("fuse", "redireccion")})
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["cinnamomum-aromaticum", "cinnamomum-verum"])
        self.assertEqual(sorted((m["name"], m["state"]) for m in uni.collisions),
                         [("Cinnamomum aromaticum", "sin-decision"), ("Cinnamomum zeylanicum", "decidido")])
        self.assertIn("fusion-heterotipica", self.codes(uni.plant("cinnamomum-verum")))
        self.assertIn("grupo-partido", self.codes(uni.plant("cinnamomum-verum")))

    def test_group_without_core_fuses_into_a_plant_named_after_the_accepted(self):
        entries = [usda("1", "Cinnamomum zeylanicum"), usda("2", "Cinnamomum aromaticum")]
        rules = cs.rules_for(self.build(entries), {"Cinnamomum zeylanicum": ("fuse", "redireccion"),
                                                    "Cinnamomum aromaticum": ("separate", "articulo-propio")})
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["cinnamomum-aromaticum", "cinnamomum-verum"])
        accepted = uni.plant("cinnamomum-verum")
        self.assertEqual((accepted.kind, accepted.is_core, accepted.aliases), ("resolved", False, ["cinnamomum-zeylanicum"]))

    def test_registered_decision_does_not_depend_on_wikipedia_being_enabled(self):
        entries = [usda("1", "Cinnamomum verum"), usda("2", "Cinnamomum zeylanicum")]
        rules = cs.rules_for(self.build(entries), {"Cinnamomum zeylanicum": ("fuse", "redireccion")})
        first, second = self.build(entries, rules), self.build(entries, rules)
        self.assertEqual(self.ids(first), self.ids(second))
        self.assertEqual([p.to_dict() for p in first.plants], [p.to_dict() for p in second.plants])

    def test_rows_of_a_fused_member_go_to_the_fused_plant(self):
        entries = [usda("1", "Cascabela thevetia"), usda("2", "Thevetia peruviana"), usda("3", "Foeniculum vulgare"),
                   usda("4", "Foeniculum vulgare var. dulce")]
        rules = cs.rules_for(self.build(entries), {"Thevetia peruviana": ("fuse", "articulo-compartido"),
                                                    "Foeniculum vulgare var. dulce": ("separate", "excepcion")})
        uni = self.build(entries, rules)
        plant, reason = uni.assign("Thevetia peruviana", author="(Pers.) K.Schum.")
        self.assertEqual((plant.id, reason), ("cascabela-thevetia", "grupo-unico"))
        # El basiónimo del fusionado (homotípico suyo) llega a la misma planta.
        plant, _ = uni.assign("Cerbera peruviana")
        self.assertEqual(plant.id, "cascabela-thevetia")
        # En el grupo partido, la variedad separada conserva sus filas y el nombre del aceptado va al aceptado.
        self.assertEqual(uni.assign("Foeniculum vulgare var. dulce")[0].id, "foeniculum-vulgare-var-dulce")
        self.assertEqual(uni.assign("Foeniculum vulgare")[0].id, "foeniculum-vulgare")
        self.assertEqual(uni.unassigned, [])

    def test_rows_of_a_fused_member_in_a_split_group_follow_the_fusion(self):
        entries = [usda("1", "Foeniculum vulgare"), usda("2", "Foeniculum vulgare var. dulce"), usda("3", "Foeniculum dulce")]
        # var. dulce y Foeniculum dulce (su basiónimo) son un solo miembro; se funde con el aceptado.
        rules = cs.rules_for(self.build(entries), {"Foeniculum dulce": ("fuse", "sin-articulo")})
        uni = self.build(entries, rules)
        self.assertEqual(self.ids(uni), ["foeniculum-vulgare"])
        self.assertEqual(uni.assign("Foeniculum dulce")[0].id, "foeniculum-vulgare")

    def test_rules_files_are_validated_and_missing_files_mean_no_rules(self):
        self.assertEqual(load_decisions(None)["groups"], {})
        self.assertEqual(load_exceptions("/no/existe.json")["exceptions"], [])
        self.assertEqual(name_key("Citrus × bergamia"), name_key("Citrus bergamia"))

    def test_initial_exceptions_file_matches_the_approved_list(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collision-exceptions.json")
        names = [e["name"] for e in load_exceptions(path)["exceptions"]]
        self.assertEqual(names, ["Brassica napus var. napobrassica", "Brassica oleracea var. acephala", "Brassica chinensis",
                                 "Brassica pekinensis", "Citrus meyeri", "Foeniculum vulgare var. dulce", "Grindelia humilis",
                                 "Lactuca sativa var. capitata", "Origanum creticum", "Origanum vulgare var. hirtum"])
        self.assertTrue(all(e["reason"] for e in load_exceptions(path)["exceptions"]))
        rules = load_rules(None, path)
        self.assertTrue(rules.exception_reason({name_key("Citrus meyeri")}))
        self.assertIsNone(rules.exception_reason({name_key("Citrus bergamia")}))


class RulesFileTest(support.TempDirTestCase):
    def write(self, name, document):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return path

    def test_invalid_reason_for_the_decision_fails(self):
        bad = {"format": DECISIONS_FORMAT, "groups": {"a b": {"members": {"c d": {"decision": "fuse", "reason": "excepcion"}}}}}
        with self.assertRaises(CollisionFileError):
            load_decisions(self.write("bad.json", bad))

    def test_wrong_format_fails_and_dump_round_trips_sorted(self):
        with self.assertRaises(CollisionFileError):
            load_decisions(self.write("bad.json", {"format": "otro", "groups": {}}))
        good = {"format": DECISIONS_FORMAT, "groups": {"b b": {"members": {"x y": {"decision": "separate", "reason": "excepcion"}}},
                                                       "a a": {"members": {"x y": {"decision": "fuse", "reason": "sin-articulo"}}}}}
        path = os.path.join(self.tmp, "good.json")
        dump_decisions(path, good)
        self.assertEqual(list(load_decisions(path)["groups"]), ["a a", "b b"])
        with open(path, encoding="utf-8") as handle:
            self.assertTrue(handle.read().endswith("}\n"))


if __name__ == "__main__":
    unittest.main()
