import json
import os
import tempfile
import unittest

import support  # noqa: F401
from test_glossary_extract import load

from catalog_seed import cli
from catalog_seed.glossary_build import build_glossary, build_row
from catalog_seed.glossary_terms import base_key
from catalog_seed.sources import SourceError
from catalog_seed.wiki import WikipediaArticleStep, WiktionaryStep

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "glossary")
APPROVED = {"by": "usuario", "date": "2026-10-29"}


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = os.path.join(self.tmp.name, "cache")
        wiktionary, wikipedia = WiktionaryStep(cache_dir=self.cache), WikipediaArticleStep(cache_dir=self.cache)
        for title in ("diurético", "anodino", "astringente", "vermífugo"):
            wiktionary.store(title, load("wiktionary-%s.json" % title))
        wikipedia.store("Estimulante", load("wikipedia-Estimulante.json"))
        wikipedia.store("Hipnótico", load("wikipedia-Hipnótico.json"))

    def wiktionary_term(self, activity, title, sense, **extra):
        return dict({"activity": activity, "wiktionaryTitle": title, "source": "wiktionary_es", "sense": sense, "reason": "r", "approved": APPROVED}, **extra)

    def document(self, *terms):
        return {"version": 1, "description": "x", "terms": list(terms), "excluded": [], "approvedPatterns": {}}


class BuildRowTests(BuildTestCase):
    def test_wiktionary_literal_row(self):
        row = build_row(self.wiktionary_term("Diurético", "diurético", 1), self.cache)
        self.assertEqual(row["text"], "Que aumenta o facilita la producción y excreción de orina.")
        self.assertEqual((row["key"], row["sourceId"], row["sourceName"], row["adapted"], row["sense"]),
                         ("diurético", "wiktionary_es", "Wikcionario", False, 1))
        self.assertEqual(row["entryUrl"], "https://es.wiktionary.org/w/index.php?title=diur%C3%A9tico&oldid=" + str(row["revisionId"]))
        self.assertRegex(row["retrievedAt"], r"^\d{4}-\d{2}-\d{2}$")

    def test_astringente_is_trimmed_to_the_first_sentence(self):
        row = build_row(self.wiktionary_term("Astringente", "astringente", 1), self.cache)
        self.assertTrue(row["text"].endswith("y otras secreciones."))

    def test_abbreviation_does_not_cut_the_sentence(self):
        wiktionary = WiktionaryStep(cache_dir=self.cache)
        record = dict(load("wiktionary-diurético.json"))
        record["html"] = record["html"].replace("Que ", "Que, p. ej. ", 1)
        wiktionary.store("raro", record)
        row = build_row(self.wiktionary_term("Raro", "raro", 1), self.cache)
        self.assertIn("p. ej.", row["text"])

    def test_wikipedia_literal_and_adapted(self):
        literal = build_row({"activity": "Estimulante", "wiktionaryTitle": "estimulante", "wikipediaTitle": "Estimulante", "source": "wikipedia_es",
                             "mode": "literal", "reason": "r", "approved": APPROVED}, self.cache)
        self.assertTrue(literal["text"].startswith("Un estimulante (del verbo latino stimulāre)"))
        self.assertEqual((literal["sourceName"], literal["adapted"], literal["sense"]), ("Wikipedia", False, None))
        self.assertIn("es.wikipedia.org/w/index.php?title=Estimulante&oldid=", literal["entryUrl"])
        adapted = build_row({"activity": "Hipnótico", "wiktionaryTitle": "hipnótico", "wikipediaTitle": "Hipnótico", "source": "wikipedia_es", "mode": "adapted",
                             "text": "Clase de fármacos que inducen el sueño.", "evidence": "x", "reason": "r", "approved": APPROVED}, self.cache)
        self.assertEqual((adapted["text"], adapted["adapted"]), ("Clase de fármacos que inducen el sueño.", True))

    def test_unapproved_term_is_refused(self):
        term = self.wiktionary_term("Diurético", "diurético", 1)
        del term["approved"]
        with self.assertRaises(SourceError) as ctx:
            build_row(term, self.cache)
        self.assertIn("aprobación", str(ctx.exception))

    def test_missing_cache_sense_or_article(self):
        with self.assertRaises(SourceError):
            build_row(self.wiktionary_term("Tónico", "tónico", 3), self.cache)
        with self.assertRaises(SourceError):
            build_row(self.wiktionary_term("Diurético", "diurético", 9), self.cache)
        with self.assertRaises(SourceError):
            build_row(self.wiktionary_term("Vermífugo", "vermífugo", 1), self.cache)  # la entrada no existe

    def test_text_without_a_final_period_or_too_short_fails(self):
        wiktionary = WiktionaryStep(cache_dir=self.cache)
        record = dict(load("wiktionary-diurético.json"))
        record["html"] = record["html"].replace("orina</a>.", "orina</a>", 1)
        wiktionary.store("sinpunto", record)
        with self.assertRaises(SourceError) as ctx:
            build_row(self.wiktionary_term("Sinpunto", "sinpunto", 1), self.cache)
        self.assertIn("punto", str(ctx.exception))


class BuildDocumentTests(BuildTestCase):
    def test_rows_are_sorted_by_key_and_the_build_is_deterministic(self):
        document = self.document(self.wiktionary_term("Diurético", "diurético", 1), self.wiktionary_term("Anodino", "anodino", 4))
        first = build_glossary(document, self.cache)
        second = build_glossary(json.loads(json.dumps(document)), self.cache)
        self.assertEqual(first, second)
        self.assertEqual([r["key"] for r in first["rows"]], ["anodino", "diurético"])
        self.assertEqual((first["format"], first["license"]), ("catalog-glossary/1", "CC BY-SA 4.0"))
        self.assertIn("primera oración", first["changes"])

    def test_cli_build_writes_a_valid_file_without_network(self):
        terms = os.path.join(self.tmp.name, "terms.json")
        with open(terms, "w", encoding="utf-8") as handle:
            json.dump(self.document(self.wiktionary_term("Diurético", "diurético", 1)), handle)
        out = os.path.join(self.tmp.name, "seed", "glossary.json")
        self.assertEqual(cli.main(["--cache-dir", self.cache, "glossary-build", "--terms", terms, "--out", out]), 0)
        with open(out, encoding="utf-8") as handle:
            first = handle.read()
        self.assertEqual(cli.main(["--cache-dir", self.cache, "glossary-build", "--terms", terms, "--out", out]), 0)
        with open(out, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), first)
        self.assertEqual(json.loads(first)["rows"][0]["key"], "diurético")

    def test_cli_build_refuses_to_write_an_invalid_glossary(self):
        wiktionary = WiktionaryStep(cache_dir=self.cache)
        record = dict(load("wiktionary-diurético.json"))
        record["html"] = record["html"].replace("Que ", "Que cura y ", 1)
        wiktionary.store("curativo", record)
        terms = os.path.join(self.tmp.name, "terms.json")
        with open(terms, "w", encoding="utf-8") as handle:
            json.dump(self.document(self.wiktionary_term("Curativo", "curativo", 1)), handle)
        out = os.path.join(self.tmp.name, "glossary.json")
        self.assertEqual(cli.main(["--cache-dir", self.cache, "glossary-build", "--terms", terms, "--out", out]), 1)
        self.assertFalse(os.path.exists(out))


class KeyCasesTests(unittest.TestCase):
    def test_shared_key_cases(self):
        with open(os.path.join(FIXTURES, "..", "glossary-key-cases.json"), encoding="utf-8") as handle:
            cases = json.load(handle)["cases"]
        for case in cases:
            self.assertEqual(base_key(case["activity"]), case["key"], case["activity"])


if __name__ == "__main__":
    unittest.main()
