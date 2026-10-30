import os
import unittest
from urllib.parse import parse_qs, urlparse

import support  # noqa: F401
from test_wiki import WikiTestCase

from catalog_seed.sources import SourceError
from catalog_seed.wiki import USER_AGENT, WikipediaArticleStep


def article(title, extract="Un sedante es una sustancia.", revid=175049934, disambiguation=False, redirect=None):
    page = {"pageid": 5, "ns": 0, "title": title, "extract": extract,
            "revisions": [{"revid": revid, "parentid": 1, "timestamp": "2026-10-01T10:00:00Z"}]}
    if disambiguation:
        page["pageprops"] = {"disambiguation": ""}
    query = {"pages": [page]}
    if redirect:
        query["redirects"] = [{"from": redirect, "to": title}]
    return (200, {}, {"batchcomplete": True, "query": query})


MISSING = (200, {}, {"batchcomplete": True, "query": {"pages": [{"title": "Alterativo", "missing": True}]}})


class WikipediaArticleStepTests(WikiTestCase):
    def test_downloads_extract_revision_and_flags(self):
        fake = self.server([article("Sedante", redirect="Calmante")])
        step = self.step(WikipediaArticleStep, fake)
        self.assertEqual(step.run(["Calmante"])["status"], "complete")
        query = parse_qs(urlparse(fake.requests[0]["path"]).query)
        self.assertEqual((query["action"], query["prop"], query["exintro"], query["explaintext"], query["redirects"], query["titles"]),
                         (["query"], ["extracts|revisions|pageprops"], ["1"], ["1"], ["1"], ["Calmante"]))
        self.assertEqual(fake.requests[0]["agent"], USER_AGENT)
        record = step.load("Calmante")
        self.assertEqual((record["title"], record["revid"], record["timestamp"], record["disambiguation"], record["redirectedFrom"]),
                         ("Sedante", 175049934, "2026-10-01T10:00:00Z", False, "Calmante"))
        self.assertEqual(record["extract"], "Un sedante es una sustancia.")

    def test_cache_lives_apart_from_the_summary_cache(self):
        fake = self.server([article("Sedante")])
        self.step(WikipediaArticleStep, fake).run(["Sedante"])
        self.assertTrue(os.path.isdir(os.path.join(self.cache, "wikipedia_es", "glossary")))
        self.assertEqual([n for n in os.listdir(os.path.join(self.cache, "wikipedia_es")) if n.endswith(".json")], [])

    def test_second_run_makes_no_requests(self):
        fake = self.server([article("Sedante")])
        self.step(WikipediaArticleStep, fake).run(["Sedante"])
        result = self.step(WikipediaArticleStep, fake).run(["Sedante"])
        self.assertEqual((result["status"], len(fake.requests)), ("complete", 1))

    def test_disambiguation_page_is_flagged(self):
        fake = self.server([article("Refrigerante (desambiguación)", disambiguation=True)])
        step = self.step(WikipediaArticleStep, fake)
        step.run(["Refrigerante"])
        self.assertTrue(step.load("Refrigerante")["disambiguation"])

    def test_missing_article_is_stored_as_absence(self):
        fake = self.server([MISSING])
        step = self.step(WikipediaArticleStep, fake)
        step.run(["Alterativo"])
        self.assertEqual(step.load("Alterativo"), {"requested": "Alterativo", "missing": True})

    def test_429_with_retry_after_stops_and_resumes(self):
        fake = self.server([article("Uno"), (429, {"Retry-After": "30"}, b"")])
        names = ["Uno", "Dos", "Tres"]
        result = self.step(WikipediaArticleStep, fake).run(names)
        self.assertEqual((result["status"], result["pending"]), ("rate_limited", 2))
        self.assertEqual(self.step(WikipediaArticleStep, fake).run(names)["status"], "waiting")
        self.clock.t += 31
        fake.script = [article("Dos"), article("Tres")]
        self.assertEqual(self.step(WikipediaArticleStep, fake).run(names)["status"], "complete")
        titles = [parse_qs(urlparse(r["path"]).query)["titles"][0] for r in fake.requests]
        self.assertEqual(titles, ["Uno", "Dos", "Dos", "Tres"])

    def test_http_error_stores_nothing(self):
        fake = self.server([(500, {}, {})])
        step = self.step(WikipediaArticleStep, fake)
        with self.assertRaises(SourceError):
            step.run(["Uno"])
        self.assertFalse(step.is_cached("Uno"))


if __name__ == "__main__":
    unittest.main()
