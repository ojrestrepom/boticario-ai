import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import support  # noqa: F401

from catalog_seed import cli
from catalog_seed.wiki import (
    USER_AGENT, CommonsStep, RateLimited, WikidataStep, WikipediaStep, commons_title, make_step,
    normalize_name, parse_retry_after, read_entries,
)

SPARQL = {"head": {}, "results": {"bindings": [
    {"req": {"value": "Mentha ×piperita"}, "item": {"value": "http://www.wikidata.org/entity/Q26309"},
     "taxon": {"value": "Mentha ×piperita"}, "esNames": {"value": "menta|hierbabuena inglesa"},
     "images": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/Mentha%20piperita.jpg"},
     "eswiki": {"value": "Mentha × piperita"}, "gbif": {"value": "3034025"}, "powo": {"value": "429467-1"},
     "authors": {"value": "L."}, "label": {"value": "Mentha × piperita"}, "aliases": {"value": "Mentha piperita|Menta"},
     "ipni": {"value": "450969-1"}},
    {"req": {"value": "Arnica montana"}, "item": {"value": "http://www.wikidata.org/entity/Q147709"},
     "taxon": {"value": "Arnica montana"}, "esNames": {"value": ""}, "images": {"value": ""},
     "eswiki": {"value": "Arnica montana"}, "gbif": {"value": ""}, "powo": {"value": ""}},
]}}


class FakeServer:
    """Servidor local: responde según un guion; guarda las peticiones recibidas."""

    def __init__(self, script):
        self.script = list(script)  # elementos (estado, cabeceras, cuerpo) o una función(petición)
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8") if length else ""
                request = {"method": self.command, "path": self.path, "body": body,
                           "agent": self.headers.get("User-Agent")}
                outer.requests.append(request)
                step = outer.script.pop(0) if outer.script else outer.script_default
                if callable(step):
                    step = step(request)
                status, headers, payload = step
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = handle_any

        self.script_default = (500, {}, {})
        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/" % self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def open_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Clock:
    def __init__(self, start=1_000_000.0):
        self.t = start

    def __call__(self):
        return self.t


class WikiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = self.tmp.name
        self.clock = Clock()

    def server(self, script):
        fake = FakeServer(script)
        self.addCleanup(fake.close)
        return fake

    def step(self, cls, fake, **kwargs):
        return cls(cache_dir=self.cache, endpoint=fake.url, delay=0, now=self.clock, sleep=lambda s: None, **kwargs)


class HelperTests(unittest.TestCase):
    def test_retry_after_parsing(self):
        self.assertEqual(parse_retry_after("1000", 0), 1000)
        self.assertEqual(parse_retry_after("Thu, 01 Jan 1970 00:10:00 GMT", 0), 600)
        self.assertIsNone(parse_retry_after("pronto", 0))
        self.assertIsNone(parse_retry_after(None, 0))

    def test_hybrid_sign_has_no_space(self):
        self.assertEqual(normalize_name("Mentha × piperita"), "Mentha ×piperita")
        self.assertEqual(normalize_name("Mentha ×piperita"), "Mentha ×piperita")

    def test_commons_title_from_wikidata_url(self):
        self.assertEqual(commons_title("http://commons.wikimedia.org/wiki/Special:FilePath/Mentha%20piperita.jpg"),
                         "File:Mentha piperita.jpg")
        self.assertEqual(commons_title("Foo_bar.jpg"), "File:Foo bar.jpg")

    def test_read_entries_skips_comments_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "in.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# nombres\nArnica montana\n\nArnica montana\nQ147709\n")
            self.assertEqual(read_entries(path), ["Arnica montana", "Q147709"])

    def test_user_agent_has_no_email(self):
        self.assertNotIn("@", USER_AGENT)
        self.assertIn("BoticarioAI", USER_AGENT)


class WikidataTests(WikiTestCase):
    def test_success_posts_batch_and_stores_one_file_per_entry(self):
        fake = self.server([(200, {}, SPARQL)])
        step = self.step(WikidataStep, fake)
        result = step.run(["Mentha × piperita", "Arnica montana", "Nada inventada"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(fake.requests), 1)
        request = fake.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["agent"], USER_AGENT)
        query = parse_qs(request["body"])["query"][0]
        self.assertIn('"Mentha ×piperita"', query)
        for prop in ("P225", "P405", "P428", "P1843", "P18", "P846", "P5037", "P961", "rdfs:label", "skos:altLabel",
                     "es.wikipedia.org"):
            self.assertIn(prop, query)
        mint = step.load("Mentha ×piperita")["items"][0]
        self.assertEqual(mint["qid"], "Q26309")
        self.assertEqual(mint["spanishNames"], ["menta", "hierbabuena inglesa"])
        self.assertEqual(mint["eswiki"], "Mentha × piperita")
        self.assertEqual(mint["gbif"], ["3034025"])
        self.assertEqual(mint["powo"], ["429467-1"])
        self.assertEqual(mint["ipni"], ["450969-1"])
        self.assertEqual(mint["authors"], ["L."])
        self.assertEqual(mint["labelEs"], "Mentha × piperita")
        self.assertEqual(mint["aliasesEs"], ["Mentha piperita", "Menta"])
        # Una respuesta sin los campos nuevos da listas vacías.
        arnica = step.load("Arnica montana")["items"][0]
        self.assertEqual((arnica["ipni"], arnica["aliasesEs"], arnica["authors"], arnica["labelEs"]), ([], [], [], ""))
        self.assertEqual(step.load("Nada inventada"), {"items": []})
        files = [f for f in os.listdir(os.path.join(self.cache, "wikidata")) if f.endswith(".json")]
        self.assertEqual(len(files), 3)

    def test_qid_input(self):
        row = {"req": {"value": ""}, "item": {"value": "http://www.wikidata.org/entity/Q147709"},
               "taxon": {"value": "Arnica montana"}}
        fake = self.server([(200, {}, {"results": {"bindings": [row]}})])
        step = self.step(WikidataStep, fake)
        step.run(["Q147709"])
        self.assertIn("wd:Q147709", parse_qs(fake.requests[0]["body"])["query"][0])
        self.assertEqual(step.load("Q147709")["items"][0]["taxon"], "Arnica montana")

    def test_429_with_retry_after_stops_and_does_not_retry_before_deadline(self):
        fake = self.server([(200, {}, {"results": {"bindings": []}}), (429, {"Retry-After": "1000"}, b"")])
        step = self.step(WikidataStep, fake, batch_size=1)
        names = ["Arnica montana", "Mentha ×piperita", "Salvia officinalis"]
        result = step.run(names)
        self.assertEqual(result["status"], "rate_limited")
        self.assertEqual(result["pending"], 2)
        self.assertEqual(len(fake.requests), 2)
        state = json.loads(step.resume_path().read_text())
        self.assertEqual(state["retry_not_before_epoch"], 1_000_000.0 + 1000)
        self.assertEqual(state["pending"], 2)
        self.assertTrue(step.is_cached("Arnica montana"))
        # Antes del plazo: no se abre la red.
        self.clock.t += 999
        again = self.step(WikidataStep, fake, batch_size=1).run(names)
        self.assertEqual(again["status"], "waiting")
        self.assertEqual(len(fake.requests), 2)
        # Pasado el plazo: solo lo pendiente.
        self.clock.t += 2
        fake.script = [(200, {}, {"results": {"bindings": []}}), (200, {}, {"results": {"bindings": []}})]
        done = self.step(WikidataStep, fake, batch_size=1).run(names)
        self.assertEqual(done["status"], "complete")
        self.assertEqual(len(fake.requests), 4)
        self.assertFalse(os.path.exists(step.resume_path()))
        sent = [parse_qs(r["body"])["query"][0] for r in fake.requests[2:]]
        self.assertTrue(any("Mentha ×piperita" in q for q in sent))
        self.assertTrue(any("Salvia officinalis" in q for q in sent))
        self.assertFalse(any("Arnica montana" in q for q in sent))

    def test_503_without_retry_after_uses_default_wait(self):
        fake = self.server([(503, {}, b"")])
        result = self.step(WikidataStep, fake).run(["Arnica montana"])
        self.assertEqual(result["status"], "rate_limited")
        self.assertIn("sin Retry-After", result["reason"])
        self.assertEqual(json.loads(open_text(os.path.join(self.cache, "wikidata", "_resume.json")))["retry_not_before_epoch"],
                         1_000_000.0 + 300)

    def test_second_run_only_queries_pending(self):
        fake = self.server([(200, {}, SPARQL)])
        self.step(WikidataStep, fake).run(["Mentha ×piperita", "Arnica montana"])
        self.assertEqual(len(fake.requests), 1)
        fake.script = [(200, {}, {"results": {"bindings": []}})]
        step = self.step(WikidataStep, fake)
        step.run(["Mentha ×piperita", "Arnica montana", "Salvia officinalis"])
        self.assertEqual(len(fake.requests), 2)
        body = parse_qs(fake.requests[1]["body"])["query"][0]
        self.assertIn("Salvia officinalis", body)
        self.assertNotIn("Arnica montana", body)
        step.run(["Mentha ×piperita", "Arnica montana", "Salvia officinalis"])
        self.assertEqual(len(fake.requests), 2)

    def test_http_error_stores_nothing(self):
        fake = self.server([(500, {}, b"boom")])
        from catalog_seed.sources import SourceError
        step = self.step(WikidataStep, fake)
        with self.assertRaises(SourceError):
            step.run(["Arnica montana"])
        self.assertFalse(step.is_cached("Arnica montana"))

    def test_batches_are_small_and_configurable(self):
        fake = self.server([])
        fake.script_default = (200, {}, {"results": {"bindings": []}})
        self.step(WikidataStep, fake, batch_size=2).run(["A a", "B b", "C c", "D d", "E e"])
        self.assertEqual(len(fake.requests), 3)


class WikipediaTests(WikiTestCase):
    def test_success_and_missing_page(self):
        summary = {"title": "Arnica montana", "extract": "Planta medicinal.", "content_urls": {}}
        fake = self.server([(200, {}, summary), (404, {}, {"title": "Not found."})])
        step = self.step(WikipediaStep, fake)
        result = step.run(["Arnica montana", "Pagina inexistente"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(fake.requests[0]["path"], "/Arnica_montana")
        self.assertEqual(fake.requests[0]["method"], "GET")
        self.assertEqual(fake.requests[0]["agent"], USER_AGENT)
        self.assertEqual(step.load("Arnica montana")["extract"], "Planta medicinal.")
        self.assertEqual(step.load("Pagina inexistente"), {"missing": True})

    def test_429_stops_and_resumes_only_pending(self):
        summary = {"title": "x", "extract": "y"}
        fake = self.server([(200, {}, summary), (429, {"Retry-After": "30"}, b"")])
        names = ["Uno", "Dos", "Tres"]
        result = self.step(WikipediaStep, fake).run(names)
        self.assertEqual((result["status"], result["pending"]), ("rate_limited", 2))
        self.clock.t += 31
        fake.script = [(200, {}, summary), (200, {}, summary)]
        self.step(WikipediaStep, fake).run(names)
        self.assertEqual([r["path"] for r in fake.requests], ["/Uno", "/Dos", "/Dos", "/Tres"])


class CommonsTests(WikiTestCase):
    def test_success_with_extmetadata_and_missing(self):
        reply = {"query": {
            "normalized": [{"from": "File:Mentha_piperita.jpg", "to": "File:Mentha piperita.jpg"}],
            "pages": [
                {"title": "File:Mentha piperita.jpg", "imageinfo": [{
                    "url": "https://upload.example/x.jpg", "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}}}]},
                {"title": "File:Falta.jpg", "missing": True}]}}
        fake = self.server([(200, {}, reply)])
        step = self.step(CommonsStep, fake)
        result = step.run(["http://commons.wikimedia.org/wiki/Special:FilePath/Mentha%20piperita.jpg", "Falta.jpg"])
        self.assertEqual(result["status"], "complete")
        path = fake.requests[0]["path"]
        query = parse_qs(urlparse(path).query)
        self.assertEqual(query["prop"], ["imageinfo"])
        self.assertIn("extmetadata", query["iiprop"][0])
        self.assertEqual(query["titles"], ["File:Mentha piperita.jpg|File:Falta.jpg"])
        info = step.load("File:Mentha piperita.jpg")["imageinfo"]
        self.assertEqual(info["extmetadata"]["LicenseShortName"]["value"], "CC BY-SA 4.0")
        self.assertEqual(step.load("File:Falta.jpg"), {"missing": True})

    def test_429_stops_with_resume_state(self):
        fake = self.server([(429, {"Retry-After": "60"}, b"")])
        result = self.step(CommonsStep, fake).run(["A.jpg"])
        self.assertEqual(result["status"], "rate_limited")
        self.assertTrue(os.path.exists(os.path.join(self.cache, "commons", "_resume.json")))


class FetchCliTests(WikiTestCase):
    def test_cli_exit_codes(self):
        fake = self.server([(429, {"Retry-After": "60"}, b"")])
        input_file = os.path.join(self.cache, "names.txt")
        with open(input_file, "w") as handle:
            handle.write("Arnica montana\n")
        args = ["--cache-dir", self.cache, "fetch", "--service", "wikidata", "--input", input_file,
                "--endpoint", fake.url, "--delay", "0"]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(args), 2)
            self.assertEqual(cli.main(args), 2)
        self.assertIn("No reintentar antes de", out.getvalue())
        self.assertEqual(len(fake.requests), 1)

    def test_make_step_rejects_unknown_service(self):
        from catalog_seed.sources import SourceError
        with self.assertRaises(SourceError):
            make_step("otro")


if __name__ == "__main__":
    unittest.main()
