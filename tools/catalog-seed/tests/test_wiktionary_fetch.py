import json
import os
import unittest
from urllib.parse import parse_qs, urlparse

import support  # noqa: F401
from test_wiki import Clock, FakeServer, WikiTestCase

from catalog_seed.sources import SourceError
from catalog_seed.wiki import USER_AGENT, WiktionaryStep

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "glossary")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return json.load(handle)


def parse_reply(title, revid=6324321):
    record = fixture("wiktionary-diurético.json")
    return (200, {}, {"parse": {"title": title, "pageid": 1, "revid": revid, "text": record["html"]}})


def meta_reply(revid=6324321, timestamp="2026-08-16T17:41:41Z"):
    return (200, {}, {"query": {"pages": [{"pageid": 1, "revisions": [{"revid": revid, "parentid": 1, "timestamp": timestamp}]}]}})


MISSING = (200, {}, {"error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}})


class WiktionaryStepTests(WikiTestCase):
    def test_downloads_html_revision_and_timestamp(self):
        fake = self.server([parse_reply("diurético"), meta_reply()])
        step = self.step(WiktionaryStep, fake)
        result = step.run(["diurético"])
        self.assertEqual(result["status"], "complete")
        first, second = (parse_qs(urlparse(r["path"]).query) for r in fake.requests)
        self.assertEqual((first["action"], first["page"], first["prop"], first["redirects"]),
                         (["parse"], ["diurético"], ["text|revid"], ["1"]))
        self.assertEqual((second["action"], second["revids"], second["rvprop"]), (["query"], ["6324321"], ["ids|timestamp"]))
        self.assertEqual({r["method"] for r in fake.requests}, {"GET"})
        self.assertEqual({r["agent"] for r in fake.requests}, {USER_AGENT})
        record = step.load("diurético")
        self.assertEqual((record["title"], record["revid"], record["timestamp"]), ("diurético", 6324321, "2026-08-16T17:41:41Z"))
        self.assertIn("facilita", record["html"])
        self.assertTrue(os.path.isdir(os.path.join(self.cache, "wiktionary_es")))

    def test_second_run_makes_no_requests(self):
        fake = self.server([parse_reply("diurético"), meta_reply()])
        self.step(WiktionaryStep, fake).run(["diurético"])
        before = len(fake.requests)
        result = self.step(WiktionaryStep, fake).run(["diurético"])
        self.assertEqual((result["status"], result["fetched_requests"]), ("complete", 0))
        self.assertEqual(len(fake.requests), before)

    def test_titles_are_case_sensitive_and_one_per_request(self):
        fake = self.server([parse_reply("diurético"), meta_reply(), parse_reply("tónico", 2), meta_reply(2)])
        self.step(WiktionaryStep, fake).run(["diurético", "tónico"])
        pages = [parse_qs(urlparse(r["path"]).query).get("page") for r in fake.requests if "page=" in r["path"]]
        self.assertEqual(pages, [["diurético"], ["tónico"]])

    def test_missing_entry_is_stored_as_absence(self):
        fake = self.server([MISSING])
        step = self.step(WiktionaryStep, fake)
        step.run(["vermífugo"])
        self.assertEqual(step.load("vermífugo"), {"requested": "vermífugo", "missing": True})
        self.step(WiktionaryStep, fake).run(["vermífugo"])
        self.assertEqual(len(fake.requests), 1)

    def test_429_with_retry_after_stops_and_resumes(self):
        fake = self.server([parse_reply("a"), meta_reply(), (429, {"Retry-After": "30"}, b"")])
        names = ["a", "b", "c"]
        result = self.step(WiktionaryStep, fake).run(names)
        self.assertEqual((result["status"], result["pending"]), ("rate_limited", 2))
        waiting = self.step(WiktionaryStep, fake).run(names)
        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(len(fake.requests), 3)
        self.clock.t += 31
        fake.script = [parse_reply("b", 3), meta_reply(3), parse_reply("c", 4), meta_reply(4)]
        done = self.step(WiktionaryStep, fake).run(names)
        self.assertEqual(done["status"], "complete")
        self.assertEqual(len(fake.requests), 7)

    def test_429_in_the_metadata_request_stores_nothing_for_that_entry(self):
        fake = self.server([parse_reply("a"), (429, {"Retry-After": "10"}, b"")])
        step = self.step(WiktionaryStep, fake)
        result = step.run(["a"])
        self.assertEqual(result["status"], "rate_limited")
        self.assertFalse(step.is_cached("a"))

    def test_http_error_stores_nothing(self):
        fake = self.server([(500, {}, {})])
        step = self.step(WiktionaryStep, fake)
        with self.assertRaises(SourceError):
            step.run(["a"])
        self.assertFalse(step.is_cached("a"))

    def test_pause_between_requests(self):
        sleeps = []
        fake = self.server([parse_reply("a"), meta_reply(), parse_reply("b", 2), meta_reply(2)])
        step = WiktionaryStep(cache_dir=self.cache, endpoint=fake.url, delay=1.0, now=Clock(), sleep=sleeps.append)
        step.run(["a", "b"])
        self.assertEqual(sleeps, [1.0, 1.0, 1.0])  # entre parse y metadatos, y entre las dos entradas


if __name__ == "__main__":
    unittest.main()
