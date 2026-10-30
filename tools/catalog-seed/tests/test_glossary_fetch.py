import contextlib
import io
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

import support  # noqa: F401
from test_wiki import Clock
from test_wikipedia_glossary_fetch import article
from test_wiktionary_fetch import MISSING, meta_reply, parse_reply

from catalog_seed import cli, glossary_fetch
from catalog_seed.wiki import WikipediaArticleStep, WiktionaryStep

DOC = {"version": 1, "description": "x",
       "terms": [{"activity": "Diurético", "wiktionaryTitle": "diurético"},
                 {"activity": "Estimulante", "wiktionaryTitle": "estimulante", "wikipediaTitle": "Estimulante"},
                 {"activity": "Vermífugo", "wiktionaryTitle": "vermífugo", "wikipediaTitle": "Vermífugo"}],
       "excluded": [], "approvedPatterns": {}}


class Network:
    """Sustituye a `http_request`: responde a Wikcionario y a Wikipedia y recuerda lo pedido."""

    def __init__(self):
        self.urls = []

    def __call__(self, url, data=None, headers=None, timeout=60):
        self.urls.append(url)
        query = parse_qs(urlparse(url).query)
        if "wiktionary" in url:
            if query["action"] == ["parse"]:
                status, _, body = MISSING if query["page"] == ["vermífugo"] else parse_reply(query["page"][0])
            else:
                status, _, body = meta_reply()
        else:
            status, _, body = article(query["titles"][0])
        return status, json.dumps(body).encode("utf-8"), {}


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.network = Network()
        self.logs = []

    def steps(self):
        return glossary_fetch.make_steps(self.tmp.name, 0, request=self.network, now=Clock(), sleep=lambda s: None)

    def fetch(self, **kwargs):
        return glossary_fetch.fetch(DOC, self.tmp.name, 0, steps=self.steps(), log=self.logs.append, **kwargs)

    def test_wikipedia_is_fetched_only_for_terms_that_declare_a_title(self):
        doc = json.loads(json.dumps(DOC))
        del doc["terms"][1]["wikipediaTitle"]
        del doc["terms"][2]["wikipediaTitle"]
        status, summary = glossary_fetch.fetch(doc, self.tmp.name, 0, steps=self.steps(), log=self.logs.append)
        self.assertEqual(status, "complete")
        self.assertEqual(summary["wikipedia_es"]["titles"], 0)
        self.assertEqual([u for u in self.network.urls if "wikipedia" in u], [])

    def test_plan_counts_requests_and_does_not_open_the_network(self):
        status, summary = self.fetch(plan_only=True)
        self.assertEqual(status, "plan")
        self.assertEqual(summary["wiktionary_es"], {"titles": 3, "pending": 3, "requests": 6})
        self.assertEqual(summary["wikipedia_es"], {"titles": 2, "pending": 2, "requests": 2})
        self.assertEqual(self.network.urls, [])

    def test_full_download_then_second_run_makes_no_requests(self):
        status, _ = self.fetch()
        self.assertEqual(status, "complete")
        wiktionary_files = [n for n in os.listdir(os.path.join(self.tmp.name, "wiktionary_es")) if n.endswith(".json")]
        wikipedia_files = [n for n in os.listdir(os.path.join(self.tmp.name, "wikipedia_es", "glossary")) if n.endswith(".json")]
        self.assertEqual((len(wiktionary_files), len(wikipedia_files)), (3, 2))
        made = len(self.network.urls)
        self.assertEqual(made, 5 + 2)  # 2 entradas halladas con 2 peticiones, 1 ausencia con 1, 2 artículos
        status, summary = self.fetch()
        self.assertEqual(status, "complete")
        self.assertEqual(len(self.network.urls), made)
        self.assertEqual(summary["wiktionary_es"]["pending"], 0)

    def test_source_filter(self):
        self.fetch(sources=["wikipedia_es"])
        self.assertTrue(all("wikipedia" in u for u in self.network.urls))

    def test_refresh_requests_that_title_again(self):
        self.fetch()
        before = len(self.network.urls)
        self.fetch(refresh=["diurético"])
        self.assertEqual(len(self.network.urls) - before, 2)
        pages = [parse_qs(urlparse(u).query).get("page") for u in self.network.urls[before:] if "page=" in u]
        self.assertEqual(pages, [["diurético"]])

    def test_refresh_in_plan_mode_keeps_the_cache(self):
        self.fetch()
        status, _ = self.fetch(refresh=["diurético"], plan_only=True)
        self.assertEqual(status, "plan")
        step = WiktionaryStep(cache_dir=self.tmp.name)
        self.assertTrue(step.is_cached("diurético"))

    def test_disabled_source_is_skipped(self):
        status, summary = self.fetch(enabled={"wiktionary_es": False, "wikipedia_es": True})
        self.assertNotIn("wiktionary_es", summary)
        self.assertTrue(all("wikipedia" in u for u in self.network.urls))

    def test_rate_limit_leaves_resumable_state(self):
        calls = []

        def limited(url, data=None, headers=None, timeout=60):
            calls.append(url)
            return 429, b"", {"Retry-After": "40"}

        steps = glossary_fetch.make_steps(self.tmp.name, 0, request=limited, now=Clock(), sleep=lambda s: None)
        status, _ = glossary_fetch.fetch(DOC, self.tmp.name, 0, steps=steps, log=self.logs.append)
        self.assertEqual(status, "incomplete")
        self.assertEqual(len(calls), 1)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, "wiktionary_es", "_resume.json")))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def terms_file(self, tmp):
        path = os.path.join(tmp, "terms.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(DOC, handle)
        return path

    def test_plan_through_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_cli("--cache-dir", os.path.join(tmp, "cache"), "glossary-fetch", "--plan", "--terms", self.terms_file(tmp))
        self.assertEqual(code, 0)
        self.assertIn("wiktionary_es: 3 títulos, 3 sin respuesta en la caché, hasta 6 peticiones", out)
        self.assertIn("wikipedia_es: 2 títulos", out)

    def test_pause_shorter_than_one_second_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_cli("--cache-dir", os.path.join(tmp, "cache"), "glossary-fetch", "--delay", "0.2", "--terms", self.terms_file(tmp))
        self.assertEqual(code, 1)
        self.assertIn("al menos 1 segundo", err)

    def test_invalid_terms_file_fails_with_a_readable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "terms.json")
            with open(path, "w") as handle:
                json.dump({"version": 1, "terms": [{"activity": "Cancer", "wiktionaryTitle": "cancer"}]}, handle)
            code, _, err = self.run_cli("glossary-fetch", "--plan", "--terms", path)
        self.assertEqual(code, 1)
        self.assertIn("Cancer", err)


if __name__ == "__main__":
    unittest.main()
