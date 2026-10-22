import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.parse

import support  # noqa: F401
import wiki_support as ws

from catalog_seed import cli, wiki_fetch, workdb
from catalog_seed.sources import load_sources
from catalog_seed.wiki import USER_AGENT

FILE_URL = "http://commons.wikimedia.org/wiki/Special:FilePath/"
ITEMS = {
    # nombre pedido -> filas devueltas: (nombre P225, QID, autor, eswiki, imágenes)
    "Lavandula angustifolia": [("Lavandula angustifolia", "Q42081", "Mill.", "Lavandula angustifolia", ["Ok.jpg", "Nc.jpg"]),
                               ("Lavandula latifolia", "Q905916", "Medik.", "Lavandula latifolia", ["Spike.jpg"])],
    "Passiflora incarnata": [("Passiflora incarnata", "Q128939", "L.", "Passiflora incarnata", []),
                             ("Passiflora edulis", "Q156790", "Sims", "Passiflora edulis", ["Edulis.jpg"])],
    "Passiflora edulis": [("Passiflora edulis", "Q156790", "Sims", "Passiflora edulis", ["Edulis.jpg"])],
}


def sparql_row(requested, taxon, qid, author, eswiki, images):
    def v(value):
        return {"value": value}
    return {"req": v(requested), "item": v("http://www.wikidata.org/entity/" + qid), "taxon": v(taxon), "authors": v(author),
            "label": v(taxon), "aliases": v(""), "esNames": v("espliego" if qid == "Q42081" else ""),
            "images": v("|".join(FILE_URL + i for i in images)), "eswiki": v(eswiki), "gbif": v(""), "powo": v(""),
            "ipni": v("")}


class FakeNetwork:
    """Sustituye a `http_request`: responde a Wikidata, Wikipedia y Commons y recuerda lo pedido."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, data=None, headers=None, timeout=60):
        self.calls.append((url, data))
        if "query.wikidata.org" in url:
            query = urllib.parse.parse_qs(data.decode("utf-8"))["query"][0]
            rows = [sparql_row(name, *row) for name, found in ITEMS.items() if json.dumps(name) in query for row in found]
            return 200, json.dumps({"results": {"bindings": rows}}).encode("utf-8"), {}
        if "es.wikipedia.org" in url:
            title = urllib.parse.unquote(url.rsplit("/", 1)[1]).replace("_", " ")
            body = {"type": "standard", "title": title, "extract": "Resumen de %s." % title, "revision": "7",
                    "timestamp": "2026-01-01T00:00:00Z", "lang": "es", "displaytitle": "<i>%s</i>" % title,
                    "content_urls": {"desktop": {"page": "https://es.wikipedia.org/wiki/" + title.replace(" ", "_")}}}
            return 200, json.dumps(body).encode("utf-8"), {}
        if "commons.wikimedia.org" in url:
            titles = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["titles"][0].split("|")
            licenses = {"File:Ok.jpg": ("cc-by-sa-4.0", "CC BY-SA 4.0"), "File:Nc.jpg": ("cc-by-nc-2.0", "CC BY-NC 2.0"),
                        "File:Spike.jpg": ("cc-by-3.0", "CC BY 3.0"), "File:Edulis.jpg": ("cc0", "CC0")}
            pages = [{"title": t, "imageinfo": [ws.commons_response(t, License=licenses[t][0], LicenseShortName=licenses[t][1],
                                                                     Artist="Ana")["imageinfo"]]} for t in titles]
            return 200, json.dumps({"query": {"pages": pages}}).encode("utf-8"), {}
        return 404, b"", {}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = os.path.join(self.tmp.name, "cache")
        self.universe = os.path.join(self.tmp.name, "universe.json")
        with open(self.universe, "w", encoding="utf-8") as handle:
            json.dump(ws.universe(), handle)
        self.network = FakeNetwork()
        self.enabled = {"wikidata": True, "wikipedia_es": True, "commons": True}
        self.logs = []

    def steps(self):
        return wiki_fetch.make_steps(self.cache, 0, request=self.network, sleep=lambda s: None)

    def fetch(self, enabled=None, **kwargs):
        return wiki_fetch.fetch(self.universe, ws.index_path(), self.cache, enabled or self.enabled, 0, 0, log=self.logs.append,
                                steps=self.steps(), **kwargs)

    def test_fetch_downloads_articles_and_images_only_for_items_that_pass_the_filter(self):
        status, _ = self.fetch()
        self.assertEqual(status, "complete")
        asked = [url for url, _ in self.network.calls]
        # El ítem de L. latifolia (entra por la lavanda) se asigna a su propia planta; el de P. edulis no tiene planta.
        self.assertTrue(any("Lavandula_angustifolia" in u for u in asked))
        self.assertTrue(any("Lavandula_latifolia" in u for u in asked))
        self.assertFalse(any("Passiflora_edulis" in u for u in asked if "es.wikipedia.org" in u))
        commons = [u for u in asked if "commons.wikimedia.org" in u]
        self.assertEqual(len(commons), 1)
        self.assertNotIn("Edulis", urllib.parse.unquote(commons[0]))
        # La segunda ejecución no abre la red.
        before = len(self.network.calls)
        self.assertEqual(self.fetch()[0], "complete")
        self.assertEqual(len(self.network.calls), before)

    def test_assign_writes_assignment_and_report_without_network(self):
        self.fetch()
        before = len(self.network.calls)
        out = os.path.join(self.tmp.name, "wiki")
        document, report = wiki_fetch.assign(self.universe, ws.index_path(), self.cache, self.enabled, out,
                                             steps=self.steps(), log=self.logs.append)
        self.assertEqual(len(self.network.calls), before)
        for name in ("assignment.json", "report.json", "report.md"):
            self.assertTrue(os.path.isfile(os.path.join(out, name)))
        lavender = document["plants"]["lavandula-angustifolia"]
        self.assertEqual(lavender["wikidata"]["items"], ["Q42081"])
        self.assertEqual([i["title"] for i in lavender["commons"]["admitted"]], ["File:Ok.jpg"])
        self.assertEqual([i["reason"] for i in lavender["commons"]["discarded"]], ["no-comercial"])
        self.assertEqual(document["plants"]["lavandula-latifolia"]["wikidata"]["items"], ["Q905916"])
        self.assertTrue(report["controls"]["lavandula-angustifolia"]["ok"])
        # L. latifolia (pedido por la lavanda) pasa a su propia planta; P. edulis (pedido por la pasiflora) no tiene planta.
        self.assertEqual((report["homonyms"]["movedTotal"], report["homonyms"]["discardedTotal"]), (1, 1))
        self.assertEqual(report["homonyms"]["discarded"][0]["taxon"], "Passiflora edulis")
        with open(os.path.join(out, "report.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("Filtro de homónimos", text)
        self.assertIn("Passiflora edulis", text)

    def test_plan_only_does_not_open_the_network(self):
        status, summary = self.fetch(plan_only=True)
        self.assertEqual(status, "plan")
        self.assertEqual(self.network.calls, [])
        self.assertGreater(summary["names"], 5)
        self.assertGreaterEqual(summary["wikidataRequests"], 1)

    def test_disabled_wikidata_fetches_nothing(self):
        status, _ = self.fetch(dict(self.enabled, wikidata=False))
        self.assertEqual(status, "disabled")
        self.assertEqual(self.network.calls, [])

    def test_disabled_wikipedia_and_commons_are_not_downloaded(self):
        status, _ = self.fetch(dict(self.enabled, wikipedia_es=False, commons=False))
        self.assertEqual(status, "complete")
        self.assertTrue(all("query.wikidata.org" in url for url, _ in self.network.calls))

    def test_rate_limit_stops_with_resume_state(self):
        def limited(url, data=None, headers=None, timeout=60):
            return 429, b"", {"Retry-After": "1000"}
        steps = wiki_fetch.make_steps(self.cache, 0, request=limited, sleep=lambda s: None)
        status, _ = wiki_fetch.fetch(self.universe, ws.index_path(), self.cache, self.enabled, 0, 0, log=self.logs.append,
                                     steps=steps)
        self.assertEqual(status, "incomplete")
        self.assertTrue(os.path.isfile(os.path.join(self.cache, "wikidata", "_resume.json")))
        self.assertTrue(any("No reintentar antes de" in line for line in self.logs))

    def test_user_agent_is_generic(self):
        self.assertNotIn("@", USER_AGENT)


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = os.path.join(self.tmp.name, "cache")
        self.universe = os.path.join(self.tmp.name, "universe.json")
        with open(self.universe, "w", encoding="utf-8") as handle:
            json.dump(ws.universe(), handle)
        network = FakeNetwork()
        steps = wiki_fetch.make_steps(self.cache, 0, request=network, sleep=lambda s: None)
        wiki_fetch.fetch(self.universe, ws.index_path(), self.cache, {"wikidata": True, "wikipedia_es": True, "commons": True},
                         0, 0, log=lambda m: None, steps=steps)
        self.db = os.path.join(self.tmp.name, "work", "sources.db")

    def sources(self, **enabled):
        base = {"version": "v", "license": "l", "attribution": "a", "url": "https://example.invalid/"}
        path = os.path.join(self.tmp.name, "sources.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"sources": [dict(base, id=i, enabled=enabled.get(i, True)) for i in ("wikidata", "wikipedia_es", "commons")]},
                      handle)
        return path

    def run_extract(self, sources, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["--sources", sources, "--cache-dir", self.cache, "extract", "--db", self.db] + list(extra))
        return code, out.getvalue()

    def counts(self):
        if not os.path.exists(self.db):
            return {}
        connection = sqlite3.connect(self.db)
        try:
            return workdb.counts(connection)
        finally:
            connection.close()

    def test_extract_writes_stable_refs(self):
        code, _ = self.run_extract(self.sources())
        self.assertEqual(code, 0)
        counts = self.counts()
        self.assertEqual(counts["wikidata/wikidata"], 4)
        self.assertEqual(counts["wikipedia_es/wikipedia_es"], 3)
        self.assertEqual(counts["commons/commons"], 2)   # Ok y Spike; Nc se descarta y Edulis no se pide (su ítem no pasa el filtro)
        connection = sqlite3.connect(self.db)
        try:
            item = workdb.fetch_rows(connection, "wikidata", "wikidata", "Q42081")[0]
            article = workdb.fetch_rows(connection, "wikipedia_es", "wikipedia_es", "Lavandula angustifolia")[0]
            image = workdb.fetch_rows(connection, "commons", "commons", "File:Ok.jpg")[0]
            stats = dict(connection.execute("SELECT source, rows FROM extraction").fetchall())
        finally:
            connection.close()
        self.assertEqual(item["qid"], "Q42081")
        self.assertEqual(item["raw_name_cell"], "Lavandula angustifolia")
        self.assertEqual(item["content"]["spanishNames"], ["espliego"])
        self.assertEqual(item["content"]["images"], ["File:Nc.jpg", "File:Ok.jpg"])
        self.assertEqual(article["content"]["revision"], "7")
        self.assertEqual(article["content"]["url"], "https://es.wikipedia.org/wiki/Lavandula_angustifolia")
        self.assertEqual(article["content"]["displayTitle"], "Lavandula angustifolia")
        self.assertEqual(image["content"]["license"], "CC BY-SA 4.0")
        self.assertTrue(image["content"]["attributionRequired"])
        self.assertEqual(image["content"]["author"], "Ana")
        self.assertTrue(image["content"]["pageUrl"].startswith("https://commons.wikimedia.org/wiki/File:Ok"))
        self.assertEqual(stats, {"wikidata": 4, "wikipedia_es": 3, "commons": 2})

    def test_extract_is_repeatable(self):
        self.run_extract(self.sources())
        first = self.counts()
        self.run_extract(self.sources())
        self.assertEqual(self.counts(), first)

    def test_disabled_source_is_not_extracted(self):
        code, out = self.run_extract(self.sources(wikipedia_es=False))
        self.assertEqual(code, 0)
        self.assertIn("wikipedia_es: desactivada, omitida", out)
        self.assertNotIn("wikipedia_es/wikipedia_es", self.counts())
        self.assertIn("commons/commons", self.counts())

    def test_disabled_wikidata_skips_the_sources_that_depend_on_it(self):
        code, out = self.run_extract(self.sources(wikidata=False))
        self.assertEqual(code, 0)
        self.assertEqual(self.counts(), {})
        self.assertIn("wikidata: desactivada, omitida", out)
        self.assertIn("depende de wikidata", out)

    def test_fetch_command_skips_a_disabled_service(self):
        names = os.path.join(self.tmp.name, "names.txt")
        with open(names, "w") as handle:
            handle.write("Arnica montana\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--sources", self.sources(wikidata=False), "--cache-dir", os.path.join(self.tmp.name, "otra"),
                             "fetch", "--service", "wikidata", "--input", names, "--endpoint", "http://127.0.0.1:1/"])
        self.assertEqual(code, 0)
        self.assertIn("desactivada", out.getvalue())
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "otra")))

    def test_download_and_pin_leave_services_to_wiki_fetch(self):
        for argv, expected in ((["download"], "wiki-fetch"), (["download", "--offline"], "wiki-fetch"),
                               (["pin", "--source", "wikidata"], "no hay snapshot que fijar")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["--sources", self.sources(), "--cache-dir", os.path.join(self.tmp.name, "nada")] + argv)
            self.assertEqual(code, 0, argv)
            self.assertIn(expected, out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["--sources", self.sources(commons=False), "--cache-dir", self.cache, "download"])
        self.assertIn("commons: desactivada, omitida", out.getvalue())

    def test_shipped_sources_json_declares_the_three_services(self):
        shipped = {s.id: s for s in load_sources(cli.DEFAULT_SOURCES_FILE)}
        for name in ("wikidata", "wikipedia_es", "commons"):
            self.assertTrue(shipped[name].is_service)
            self.assertTrue(shipped[name].enabled)
            self.assertTrue(shipped[name].license and shipped[name].attribution)


if __name__ == "__main__":
    unittest.main()
