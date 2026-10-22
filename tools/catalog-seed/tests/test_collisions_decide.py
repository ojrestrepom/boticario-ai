"""Comando `collisions-decide` y paso de consulta de títulos: Wikipedia simulada, sin red."""
import json
import os
import unittest
import urllib.parse

import collision_support as cs
import extract_support as support
from support import make_service_source
from catalog_seed import cli, collisions_decide as cd, workdb
from catalog_seed.taxonomy import load_rules
from catalog_seed.taxonomy.collisions import load_decisions
from catalog_seed.wiki import WikipediaTitlesStep
from catalog_seed.workdb import Row


class FakeWikipedia(object):
    """Simula `es.wikipedia.org/w/api.php`: `pages` da por título 'page', 'missing', 'disambiguation' o ('redirect', destino)."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.status = 200
        self.headers = {}

    def __call__(self, url, data=None, headers=None):
        self.calls.append(url)
        if self.status != 200:
            return self.status, b"", self.headers
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert query["action"] == ["query"] and query["redirects"] == ["1"] and query["format"] == ["json"]
        titles = query["titles"][0].split("|")
        assert len(titles) <= 50
        out_pages, redirects = {}, []
        for title in titles:
            state = self.pages.get(title, "missing")
            final = title
            if isinstance(state, tuple):
                redirects.append({"from": title, "to": state[1]})
                final, state = state[1], self.pages.get(state[1], "missing")
            if state == "missing":
                out_pages[final] = {"title": final, "missing": True}
            else:
                page = {"pageid": 1, "ns": 0, "title": final}
                if state == "disambiguation":
                    page["pageprops"] = {"disambiguation": ""}
                out_pages[final] = page
        body = {"batchcomplete": True, "query": {"redirects": redirects, "pages": list(out_pages.values())}}
        return 200, json.dumps(body).encode("utf-8"), {}


def record(title, exists=True, redirect=False, target=None, disambiguation=False):
    return {"title": title, "exists": exists, "redirect": redirect, "target": target if exists else None,
            "disambiguation": disambiguation, "date": "2026-10-21"}


class JudgeTest(unittest.TestCase):
    ACCEPTED = [record("Cinnamomum verum", target="Cinnamomum verum")]

    def test_criterion_table(self):
        own = [record("Citrus × bergamia", target="Citrus × bergamia")]
        cases = [
            ("redirect to the accepted", [record("Cinnamomum zeylanicum", redirect=True, target="Cinnamomum verum")], ("fuse", "redireccion")),
            ("redirect elsewhere", [record("X y", redirect=True, target="Otro artículo")], ("fuse", "redireccion")),
            ("missing", [record("X y", exists=False)], ("fuse", "sin-articulo")),
            ("disambiguation", [record("X y", target="X y", disambiguation=True)], ("fuse", "sin-articulo")),
            ("own article", own, ("separate", "articulo-propio")),
        ]
        for label, member, expected in cases:
            self.assertEqual(cd.judge(member, self.ACCEPTED), expected, label)

    def test_shared_article_when_the_accepted_redirects_to_the_member(self):
        accepted = [record("Cascabela thevetia", redirect=True, target="Thevetia peruviana")]
        member = [record("Thevetia peruviana", target="Thevetia peruviana")]
        self.assertEqual(cd.judge(member, accepted), ("fuse", "articulo-compartido"))

    def test_own_article_when_the_accepted_has_no_article_or_another_one(self):
        member = [record("Foeniculum vulgare var. dulce", target="Foeniculum vulgare var. dulce")]
        self.assertEqual(cd.judge(member, [record("Foeniculum vulgare", exists=False)]), ("separate", "articulo-propio"))
        self.assertEqual(cd.judge(member, [record("Foeniculum vulgare", target="Foeniculum vulgare")]), ("separate", "articulo-propio"))

    def test_exception_wins_over_everything(self):
        member = [record("X y", redirect=True, target="Cinnamomum verum")]
        self.assertEqual(cd.judge(member, self.ACCEPTED, "motivo"), ("separate", "excepcion"))

    def test_hybrid_variants_try_both_spellings_of_the_sign(self):
        self.assertEqual(cd.title_variants("Citrus × bergamia"), ["Citrus × bergamia", "Citrus ×bergamia", "Citrus bergamia"])
        self.assertEqual(cd.title_variants("Citrus ×bergamia"), ["Citrus ×bergamia", "Citrus × bergamia", "Citrus bergamia"])
        self.assertEqual(cd.title_variants("Aloe vera"), ["Aloe vera"])
        # Con el signo pegado en Wikipedia, la variante lo encuentra.
        member = [record("Citrus × bergamia", exists=False), record("Citrus ×bergamia", target="Citrus ×bergamia")]
        self.assertEqual(cd.judge(member, self.ACCEPTED), ("separate", "articulo-propio"))


class DecideVariantsTest(unittest.TestCase):
    def group(self, name, names, accepted="Citrus × junos", accepted_names=()):
        return {"citrus junos": [{"accepted_key": "citrus junos", "accepted": accepted, "accepted_names": list(accepted_names),
                                  "member": "m", "name": name, "names": list(names), "exception": None}]}

    def run_decide(self, groups, pages):
        asked = []

        def records_of(title):
            asked.append(title)
            state = pages.get(title)
            if state is None:
                return record(title, exists=False)
            return record(title, redirect=isinstance(state, tuple), target=state[1] if isinstance(state, tuple) else title)
        out = cd.decide(groups, records_of)
        return out["citrus junos"]["members"]["m"], asked

    def test_hybrid_with_article_only_without_the_sign_is_separated(self):
        member, asked = self.run_decide(self.group("Citrus × sudachi", ["Citrus sudachi"]),
                                        {"Citrus sudachi": "page"})
        self.assertIn("Citrus sudachi", asked)
        self.assertEqual((member["decision"], member["reason"]), ("separate", "articulo-propio"))

    def test_origin_name_with_article_when_the_wcvp_name_has_none(self):
        member, asked = self.run_decide(self.group("Aaa bbb", ["Aaa bbb", "Ccc ddd"], accepted="Eee fff"), {"Ccc ddd": "page", "Eee fff": "page"})
        self.assertIn("Ccc ddd", asked)
        self.assertEqual((member["decision"], member["reason"]), ("separate", "articulo-propio"))

    def test_origin_name_of_the_accepted_that_redirects_to_the_member_article_is_shared(self):
        member, _ = self.run_decide(self.group("Aaa bbb", ["Aaa bbb"], accepted="Eee fff", accepted_names=["Ggg hhh"]),
                                    {"Aaa bbb": "page", "Ggg hhh": ("redirect", "Aaa bbb")})
        self.assertEqual((member["decision"], member["reason"]), ("fuse", "articulo-compartido"))

    def test_only_redirect_variants_fuse(self):
        member, _ = self.run_decide(self.group("Citrus × sudachi", ["Citrus sudachi"]), {"Citrus sudachi": ("redirect", "Citrus × junos"),
                                                                                         "Citrus × junos": "page"})
        self.assertEqual((member["decision"], member["reason"]), ("fuse", "redireccion"))


class TitlesStepTest(support.TempDirTestCase):
    def step(self, fake, **kwargs):
        return WikipediaTitlesStep(cache_dir=self.tmp, delay=0, request=fake, **kwargs)

    def test_batches_titles_follows_redirects_and_caches(self):
        fake = FakeWikipedia({"A b": "page", "C d": ("redirect", "A b")})
        step = self.step(fake)
        titles = ["A b", "C d", "E f"] + ["T%d x" % i for i in range(60)]
        result = step.run(titles)
        self.assertEqual((result["status"], len(fake.calls)), ("complete", 2))  # 63 títulos: 50 + 13
        self.assertEqual(step.load("C d"), {"title": "C d", "exists": True, "redirect": True, "target": "A b",
                                            "disambiguation": False, "date": step.load("C d")["date"]})
        self.assertEqual((step.load("A b")["redirect"], step.load("A b")["target"]), (False, "A b"))
        self.assertEqual((step.load("E f")["exists"], step.load("E f")["target"]), (False, None))
        # Una segunda ejecución no consulta lo que ya está en la caché.
        again = self.step(fake)
        again.run(titles)
        self.assertEqual(len(fake.calls), 2)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "wikipedia_es", "titulos")))

    def test_429_with_retry_after_stops_with_resume_state(self):
        fake = FakeWikipedia({})
        fake.status, fake.headers = 429, {"Retry-After": "120"}
        step = self.step(fake, now=lambda: 1000.0)
        result = step.run(["A b"])
        self.assertEqual((result["status"], result["pending"]), ("rate_limited", 1))
        self.assertEqual(step.read_resume()["retry_not_before_epoch"], 1120.0)
        fake.status = 200
        waiting = self.step(fake, now=lambda: 1050.0).run(["A b"])
        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(len(fake.calls), 1)


def usda_row(fnfnum, taxon):
    return Row("usda_taxon", fnfnum, {"taxon": taxon, "taxauthor": ""}, raw_name_cell=taxon, fnfnum=fnfnum)


class CollisionsDecideCommandTest(support.TempDirTestCase):
    PAGES = {"Cinnamomum verum": "page", "Cinnamomum zeylanicum": ("redirect", "Cinnamomum verum"),
             "Cascabela thevetia": ("redirect", "Thevetia peruviana"), "Thevetia peruviana": "page",
             "Foeniculum vulgare": "page"}

    def setUp(self):
        super().setUp()
        self.db = os.path.join(self.tmp, "sources.db")
        os.makedirs(os.path.join(self.tmp, "idx"))
        self.taxonomy = os.path.join(self.tmp, "idx", "taxonomy.db")
        cs.build_collision_index(self.taxonomy)
        connection = workdb.open_db(self.db)
        names = ["Cinnamomum verum", "Cinnamomum zeylanicum", "Cascabela thevetia", "Thevetia peruviana", "Foeniculum vulgare",
                 "Foeniculum vulgare var. dulce"]
        workdb.replace_source(connection, "usda", [usda_row(str(i), n) for i, n in enumerate(names, 1)], "usda test", [])
        workdb.replace_source(connection, "ema_json", [Row("ema_herbal", "x", {"slug": "x", "combination": "No"},
                                                           raw_name_cell="Cinnamomum verum J.Presl")], "ema test", [])
        connection.close()
        self.decisions = os.path.join(self.tmp, "collision-decisions.json")
        self.exceptions = os.path.join(self.tmp, "collision-exceptions.json")
        with open(self.exceptions, "w", encoding="utf-8") as handle:
            json.dump({"format": "catalog-collision-exceptions/1",
                       "exceptions": [{"name": "Foeniculum vulgare var. dulce", "reason": "prueba"}]}, handle)
        self.cache = os.path.join(self.tmp, "cache")
        self.logs = []

    def run_decide(self, fake, enabled=True):
        sources = [make_service_source("wikipedia_es", enabled=enabled)]
        return cd.run_collisions_decide(sources, self.cache, self.db, self.taxonomy, self.decisions, self.exceptions,
                                        delay=0, request=fake, log=self.logs.append)

    def file_bytes(self):
        with open(self.decisions, "rb") as handle:
            return handle.read()

    def members(self):
        decisions = load_decisions(self.decisions)["groups"]
        return {m["name"]: (m["decision"], m["reason"]) for g in decisions.values() for m in g["members"].values()}

    def test_decides_the_spec_scenarios_with_evidence(self):
        fake = FakeWikipedia(self.PAGES)
        result = self.run_decide(fake)
        self.assertEqual((result["status"], result["added"]), ("complete", 2 + 1))
        self.assertEqual(self.members(), {"Cinnamomum zeylanicum": ("fuse", "redireccion"),
                                          "Thevetia peruviana": ("fuse", "articulo-compartido"),
                                          "Foeniculum vulgare var. dulce": ("separate", "excepcion")})
        group = load_decisions(self.decisions)["groups"]["cinnamomum verum"]
        evidence = group["members"]["cinnamomum zeylanicum"]["evidence"][0]
        self.assertEqual((evidence["title"], evidence["exists"], evidence["redirect"], evidence["target"]),
                         ("Cinnamomum zeylanicum", True, True, "Cinnamomum verum"))
        self.assertEqual(group["acceptedEvidence"][0]["title"], "Cinnamomum verum")
        self.assertRegex(evidence["date"], r"^\d{4}-\d{2}-\d{2}$")
        # Pocas peticiones: todos los títulos caben en un lote.
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn("Special:", fake.calls[0])

    def test_a_second_run_asks_for_nothing_and_leaves_the_file_unchanged(self):
        self.run_decide(FakeWikipedia(self.PAGES))
        before = self.file_bytes()
        fake = FakeWikipedia({})
        result = self.run_decide(fake)
        self.assertEqual((result["status"], fake.calls), ("nothing", []))
        self.assertEqual(self.file_bytes(), before)

    def test_a_registered_decision_is_never_overwritten(self):
        self.run_decide(FakeWikipedia(self.PAGES))
        document = load_decisions(self.decisions)
        member = document["groups"]["cinnamomum verum"]["members"]["cinnamomum zeylanicum"]
        member.update(decision="separate", reason="articulo-propio", name="Cinnamomum zeylanicum (editada a mano)")
        with open(self.decisions, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        # La decisión editada queda como está y no se consulta nada.
        fake = FakeWikipedia(self.PAGES)
        self.run_decide(fake)
        edited = load_decisions(self.decisions)["groups"]["cinnamomum verum"]["members"]["cinnamomum zeylanicum"]
        self.assertEqual((edited["name"], edited["decision"], edited["reason"]),
                         ("Cinnamomum zeylanicum (editada a mano)", "separate", "articulo-propio"))
        self.assertEqual(fake.calls, [])

    def test_new_member_in_a_decided_group_is_added_without_touching_the_rest(self):
        self.run_decide(FakeWikipedia(self.PAGES))
        document = load_decisions(self.decisions)
        document["groups"]["cinnamomum verum"]["members"]["cinnamomum zeylanicum"]["reason"] = "sin-articulo"
        with open(self.decisions, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        connection = workdb.open_db(self.db)
        rows = workdb.fetch_rows(connection, "usda", "usda_taxon")
        workdb.replace_source(connection, "usda", [usda_row(r["row_key"], r["raw_name_cell"]) for r in rows] +
                              [usda_row("90", "Cinnamomum aromaticum")], "usda test", [])
        connection.close()
        fake = FakeWikipedia(dict(self.PAGES, **{"Cinnamomum aromaticum": "page"}))
        result = self.run_decide(fake)
        self.assertEqual(result["added"], 1)
        members = load_decisions(self.decisions)["groups"]["cinnamomum verum"]["members"]
        self.assertEqual(members["cinnamomum zeylanicum"]["reason"], "sin-articulo")
        self.assertEqual((members["cinnamomum aromaticum"]["decision"], members["cinnamomum aromaticum"]["reason"]),
                         ("separate", "articulo-propio"))

    def test_wikipedia_disabled_queries_nothing_and_keeps_the_decisions(self):
        self.run_decide(FakeWikipedia(self.PAGES))
        before = self.file_bytes()
        fake = FakeWikipedia({})
        result = self.run_decide(fake, enabled=False)
        self.assertEqual((result["status"], fake.calls), ("disabled", []))
        self.assertTrue(any("desactivada" in line for line in self.logs))
        self.assertEqual(self.file_bytes(), before)
        # Y tampoco se crea el archivo si no existía.
        os.remove(self.decisions)
        self.run_decide(fake, enabled=False)
        self.assertFalse(os.path.exists(self.decisions))

    def test_rate_limit_stops_without_writing_decisions(self):
        fake = FakeWikipedia(self.PAGES)
        fake.status, fake.headers = 429, {"Retry-After": "60"}
        result = self.run_decide(fake)
        self.assertEqual(result["status"], "rate_limited")
        self.assertFalse(os.path.exists(self.decisions))
        # Sin esperar, la siguiente ejecución no abre la red.
        fake.status = 200
        again = self.run_decide(fake)
        self.assertEqual(again["status"], "waiting")
        self.assertEqual(len(fake.calls), 1)

    def test_resolve_uses_the_recorded_decisions_without_network(self):
        self.run_decide(FakeWikipedia(self.PAGES))
        rules = load_rules(self.decisions, self.exceptions)
        with cd.build_universe_from_work(self.db, self.taxonomy, rules=rules, log=lambda *_: None) as (uni, _):
            ids = sorted(p.id for p in uni.plants)
            self.assertEqual(ids, ["cascabela-thevetia", "cinnamomum-verum", "foeniculum-vulgare", "foeniculum-vulgare-var-dulce"])
            self.assertEqual(uni.assign("Cinnamomum zeylanicum")[0].id, "cinnamomum-verum")
        # Con el archivo vacío (sin decisión) todo heterotípico es planta propia.
        with cd.build_universe_from_work(self.db, self.taxonomy, rules=load_rules(None, self.exceptions), log=lambda *_: None) as (uni, _):
            self.assertEqual(len(uni.plants), 6)
            self.assertIn("cinnamomum-zeylanicum", [p.id for p in uni.plants])

    def test_cli_command_is_registered_with_default_files(self):
        args = cli.build_parser().parse_args(["collisions-decide"])
        self.assertEqual(args.command, "collisions-decide")
        self.assertTrue(args.decisions.endswith("collision-decisions.json"))
        self.assertTrue(args.exceptions.endswith("collision-exceptions.json"))


if __name__ == "__main__":
    unittest.main()
