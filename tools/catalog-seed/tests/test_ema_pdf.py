import json
import os

import extract_support as support
from catalog_seed import ema_pdf
from catalog_seed.ema_pdf import EmaPdfStep, pdf_filename, parse_pdf_filename, pin_ema_pdfs, select_documents, slug_of
from catalog_seed.wiki import RateLimited

BASE = "https://www.ema.europa.eu"


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def page(*hrefs):
    links = "".join('<a href="%s">doc</a>' % h for h in hrefs)
    return "<html><body>%s</body></html>" % links


def doc(group, name):
    return "/en/documents/%s/%s" % (group, name)


class SelectDocumentsTests(support.TempDirTestCase):
    def test_final_monograph_wins_over_drafts_and_superseded(self):
        html = page(doc("herbal-monograph", "draft-community-herbal-monograph-x-first-version_en.pdf"),
                    doc("herbal-monograph", "final-european-union-herbal-monograph-x-revision-1_en.pdf"),
                    doc("herbal-monograph", "superseded-community-herbal-monograph-x_en.pdf"),
                    doc("herbal-assessment", "final-assessment-report-x_en.pdf"),
                    doc("herbal-references", "final-list-references-x_en.pdf"))
        chosen = select_documents(html)
        self.assertEqual([(d["kind"], d["name"]) for d in chosen], [("monograph-final", "final-european-union-herbal-monograph-x-revision-1_en.pdf")])
        self.assertEqual(chosen[0]["url"], BASE + doc("herbal-monograph", "final-european-union-herbal-monograph-x-revision-1_en.pdf"))

    def test_monograph_without_prefix_is_final_and_highest_revision_wins(self):
        html = page(doc("herbal-monograph", "european-union-herbal-monograph-x-revision-1_en.pdf"),
                    doc("herbal-monograph", "final-community-herbal-monograph-x-first-version_en.pdf"))
        self.assertEqual([d["name"] for d in select_documents(html)], ["european-union-herbal-monograph-x-revision-1_en.pdf"])

    def test_two_finals_of_the_same_revision_are_both_kept(self):
        html = page(doc("herbal-monograph", "final-community-herbal-monograph-x-well-established-use_en.pdf"),
                    doc("herbal-monograph", "final-community-herbal-monograph-x-traditional-use_en.pdf"))
        self.assertEqual(len(select_documents(html)), 2)

    def test_draft_is_used_when_there_is_no_final(self):
        html = page(doc("herbal-monograph", "draft-community-herbal-monograph-x-first-version_en.pdf"),
                    doc("herbal-monograph", "draft-european-union-herbal-monograph-x-revision-1_en.pdf"),
                    doc("herbal-monograph", "superseded-community-herbal-monograph-x_en.pdf"))
        chosen = select_documents(html)
        self.assertEqual([(d["kind"], d["name"]) for d in chosen], [("monograph-draft", "draft-european-union-herbal-monograph-x-revision-1_en.pdf")])

    def test_second_draft_beats_draft_of_the_same_revision(self):
        html = page(doc("herbal-monograph", "draft-european-union-herbal-monograph-x-revision-1_en.pdf"),
                    doc("herbal-monograph", "second-draft-european-union-herbal-monograph-x-revision-1_en.pdf"))
        self.assertTrue(select_documents(html)[0]["name"].startswith("second-draft-"))

    def test_public_statement_is_added_and_alone_when_no_monograph(self):
        html = page(doc("public-statement", "final-public-statement-x_en.pdf"), doc("public-statement", "draft-public-statement-x_en.pdf"),
                    doc("public-statement", "superseded-public-statement-x_en.pdf"))
        self.assertEqual([(d["kind"], d["name"]) for d in select_documents(html)], [("public-statement", "final-public-statement-x_en.pdf")])
        both = page(doc("herbal-monograph", "final-monograph_en.pdf"), doc("public-statement", "final-public-statement_en.pdf"))
        self.assertEqual([d["kind"] for d in select_documents(both)], ["monograph-final", "public-statement"])

    def test_calls_for_data_and_other_documents_are_ignored(self):
        html = page(doc("herbal-monograph", "call-scientific-data-periodic-review-monograph-x_en.pdf"),
                    doc("herbal-monograph", "final-european-union-herbal-monograph-x_en.pdf"))
        self.assertEqual([d["name"] for d in select_documents(html)], ["final-european-union-herbal-monograph-x_en.pdf"])

    def test_draft_public_statement_under_monograph_path_is_used_only_alone(self):
        alone = page(doc("herbal-monograph", "draft-public-statement-x-first-version_en.pdf"))
        self.assertEqual([(d["kind"], d["name"][:5]) for d in select_documents(alone)], [("public-statement", "draft")])
        with_monograph = page(doc("herbal-monograph", "draft-public-statement-x_en.pdf"), doc("herbal-monograph", "final-herbal-monograph-x_en.pdf"))
        self.assertEqual([d["kind"] for d in select_documents(with_monograph)], ["monograph-final"])

    def test_page_without_documents_and_escaped_hrefs(self):
        self.assertEqual(select_documents(page()), [])
        html = page(doc("herbal-monograph", "final-monograph-a&amp;b_en.pdf"))
        self.assertIn("final-monograph-a&b_en.pdf", select_documents(html)[0]["url"])

    def test_filenames_round_trip_and_are_bounded(self):
        name = pdf_filename("slug", "monograph-final", "final-x_en.pdf")
        self.assertEqual(parse_pdf_filename(name), ("slug", "monograph-final", "final-x_en.pdf"))
        long = pdf_filename("slug", "public-statement", "final-" + "y" * 400 + "_en.pdf")
        self.assertLessEqual(len(long), 200)
        self.assertEqual(parse_pdf_filename(long)[:2], ("slug", "public-statement"))
        self.assertEqual(pdf_filename("slug", "public-statement", "final-" + "y" * 400 + "_en.pdf"), long)   # estable
        self.assertIsNone(parse_pdf_filename("x.pdf"))
        self.assertEqual(slug_of("https://x/en/medicines/herbal/hyperici-herba-0"), "hyperici-herba-0")


class FakeEma:
    """Servidor falso: páginas y PDF por URL; registra las peticiones y simula límites."""

    def __init__(self, pages, pdfs):
        self.pages, self.pdfs, self.calls, self.script = pages, pdfs, [], {}

    def __call__(self, url, data=None, headers=None):
        self.calls.append(url)
        if url in self.script and self.script[url]:
            return self.script[url].pop(0)
        if url in self.pages:
            return 200, self.pages[url].encode("utf-8"), {}
        if url in self.pdfs:
            return 200, self.pdfs[url], {}
        return 404, b"no", {}


class StepTests(support.TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.records = [{"herbal_medicine_url": BASE + "/en/medicines/herbal/a"}, {"herbal_medicine_url": BASE + "/en/medicines/herbal/b"}]
        mono = doc("herbal-monograph", "final-herbal-monograph-a_en.pdf")
        ps = doc("public-statement", "final-public-statement-b_en.pdf")
        self.fake = FakeEma(
            {BASE + "/en/medicines/herbal/a": page(mono), BASE + "/en/medicines/herbal/b": page(ps)},
            {BASE + mono: b"%PDF-1.4 mono", BASE + ps: b"%PDF-1.4 ps"})
        self.clock = [1000.0]
        self.sleeps = []

    def step(self, delay=15):
        def sleep(seconds):
            self.sleeps.append(seconds)
            self.clock[0] += seconds
        return EmaPdfStep(self.tmp, delay=delay, request=self.fake, now=lambda: self.clock[0], sleep=sleep, monotonic=lambda: self.clock[0])

    def test_downloads_pages_and_pdfs_with_delay_between_requests(self):
        result = self.step().run(self.records)
        self.assertEqual(result["status"], "complete")
        self.assertEqual((result["pdfs_downloaded"], result["pdfs_pending_known"], result["pages_cached"]), (2, 0, 2))
        self.assertEqual(len(self.fake.calls), 4)
        self.assertEqual(self.sleeps, [15, 15, 15])           # entre peticiones, no antes de la primera
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "ema_pdf", "a__monograph-final__final-herbal-monograph-a_en.pdf")))

    def test_second_run_does_not_repeat_requests(self):
        self.step().run(self.records)
        before = len(self.fake.calls)
        result = self.step().run(self.records)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.fake.calls), before)

    def test_429_with_retry_after_stops_and_resumes_only_what_is_pending(self):
        mono_url = BASE + doc("herbal-monograph", "final-herbal-monograph-a_en.pdf")
        self.fake.script[mono_url] = [(429, b"slow down", {"Retry-After": "40"})]
        first = self.step().run(self.records)
        self.assertEqual(first["status"], "rate_limited")
        self.assertEqual(first["pdfs_downloaded"], 0)
        state = read_json(os.path.join(self.tmp, "ema_pdf", "_state.json"))
        self.assertEqual(state["retry_not_before_epoch"], self.clock[0] + 40)
        calls = len(self.fake.calls)
        waiting = self.step().run(self.records)             # antes del plazo: no abre la red
        self.assertEqual(waiting["status"], "waiting")
        self.assertEqual(len(self.fake.calls), calls)
        self.clock[0] += 41
        done = self.step().run(self.records)
        self.assertEqual(done["status"], "complete")
        self.assertEqual(done["pdfs_downloaded"], 2)
        self.assertEqual(self.fake.calls.count(BASE + "/en/medicines/herbal/a"), 1)   # la página ya estaba en la caché

    def test_html_instead_of_pdf_is_rejected_and_not_cached(self):
        mono_url = BASE + doc("herbal-monograph", "final-herbal-monograph-a_en.pdf")
        self.fake.script[mono_url] = [(200, b"<html>error</html>", {})]
        result = self.step().run(self.records)
        self.assertEqual(result["status"], "rate_limited")      # un 200 sin PDF se trata como límite disfrazado
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "ema_pdf", "a__monograph-final__final-herbal-monograph-a_en.pdf")))
        self.clock[0] += 61
        again = self.step().run(self.records)
        self.assertEqual(again["pdfs_downloaded"], 2)

    def test_a_permanently_failing_pdf_is_skipped_after_three_attempts(self):
        mono_url = BASE + doc("herbal-monograph", "final-herbal-monograph-a_en.pdf")
        del self.fake.pdfs[mono_url]                            # 404 siempre
        for _ in range(ema_pdf.MAX_ATTEMPTS):
            self.step().run(self.records)
        calls = len(self.fake.calls)
        result = self.step().run(self.records)
        self.assertEqual(len(self.fake.calls), calls)           # ya no insiste
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(result["pdfs_downloaded"], 1)

    def test_pin_registers_checksums_and_detects_alterations(self):
        self.step().run(self.records)
        sources = os.path.join(self.tmp, "sources.json")
        write_json(sources, {"sources": [{"id": "ema_pdf", "name": "Fixture", "pageUrl": "https://example.invalid/", "version": "x", "license": "l", "attribution": "a", "enabled": True, "files": []}]})
        added, total = pin_ema_pdfs(sources, self.records, self.tmp, version="fijado")
        self.assertEqual((added, total), (2, 2))
        entry = read_json(sources)["sources"][0]
        self.assertEqual(entry["version"], "fijado")
        file = entry["files"][0]
        self.assertEqual(file["filename"], "a__monograph-final__final-herbal-monograph-a_en.pdf")
        self.assertEqual(file["checksum"]["algorithm"], "sha256")
        self.assertEqual(file["size"], len(b"%PDF-1.4 mono"))
        self.assertEqual(pin_ema_pdfs(sources, self.records, self.tmp), (0, 2))     # idempotente
        with open(os.path.join(self.tmp, "ema_pdf", file["filename"]), "wb") as handle:
            handle.write(b"%PDF-1.4 alterado")
        with self.assertRaises(ema_pdf.SourceError):
            pin_ema_pdfs(sources, self.records, self.tmp)


class DeclaredSourceTests(support.TempDirTestCase):
    def test_ema_pdf_is_declared_with_generated_file_list(self):
        from catalog_seed.sources import load_sources
        sources = {s.id: s for s in load_sources()}
        self.assertIn("ema_pdf", sources)
        self.assertTrue(sources["ema_pdf"].enabled)
        for f in sources["ema_pdf"].files:
            self.assertIsNotNone(ema_pdf.parse_pdf_filename(f.filename))
            self.assertEqual(f.algorithm, "sha256")


if __name__ == "__main__":
    import unittest
    unittest.main()
