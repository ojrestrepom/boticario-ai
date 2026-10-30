import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest

import support  # noqa: F401
from test_glossary_extract import load

from catalog_seed import cli, glossary_review
from catalog_seed.sources import SourceError
from catalog_seed.wiki import WikipediaArticleStep, WiktionaryStep

FORMULA = "Uso tradicional, sin eficacia demostrada: cáncer"
# (planta, actividad, pendiente)
GROUPS = ([("p%d" % i, "Diurético", 0) for i in range(5)] + [("p0", "Diurético (veterinario)", 0)]
          + [("p%d" % i, "Estimulante", 0) for i in range(3)] + [("p1", "Fiebre", 0), ("p2", "Fiebre", 0), ("p3", "Fiebre", 0)]
          + [("p4", "Tónico", 0), ("p4", "Tónico", 1), ("p5", "Anodino", 0), ("p5", "Vermífugo", 0), ("p6", "Vermífugo", 0)]
          + [("p6", FORMULA, 0), ("p7", FORMULA, 0), ("p7", "Antiséptico", 0)])


def make_catalog(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE plant_use_group (id INTEGER PRIMARY KEY, plant_id TEXT, position INTEGER, activity TEXT, "
                 "activity_source TEXT, n INTEGER, countries TEXT, pending_review BOOLEAN)")
    for i, (plant, activity, pending) in enumerate(GROUPS):
        conn.execute("INSERT INTO plant_use_group VALUES (?,?,?,?,?,?,?,?)", (i, plant, i, activity, "x", 1, "[]", pending))
    conn.commit()
    conn.close()


def doc(terms, excluded=(), approved=None):
    return {"version": 1, "description": "x", "terms": terms, "excluded": list(excluded), "approvedPatterns": approved or {}}


class ReviewTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = os.path.join(self.tmp.name, "cache")
        self.db = os.path.join(self.tmp.name, "catalog.db")
        make_catalog(self.db)
        wiktionary = WiktionaryStep(cache_dir=self.cache)
        for title in ("diurético", "anodino", "vermífugo"):
            record = load("wiktionary-%s.json" % title)
            wiktionary.store(title, {k: v for k, v in record.items()})
        antiseptic = {"requested": "antiséptico", "title": "antiséptico", "revid": 11, "timestamp": "2026-07-31T15:02:41Z",
                      "html": '<div class="mw-parser-output"><div class="mw-heading mw-heading2"><h2>Español</h2></div>'
                              '<div class="mw-heading mw-heading4"><h4>Adjetivo</h4></div>'
                              '<dl><dt>1</dt><dd>Relacionado con la antisepsia.</dd><dt>2 Medicina</dt><dd>Capaz de prevenir las infecciones microbianas.</dd></dl></div>'}
        wiktionary.store("antiséptico", antiseptic)
        wikipedia = WikipediaArticleStep(cache_dir=self.cache)
        wikipedia.store("Estimulante", load("wikipedia-Estimulante.json"))
        wikipedia.store("Vermífugo", {"requested": "Vermífugo", "title": "Antihelmíntico", "revid": 168576174, "timestamp": "2026-09-01T00:00:00Z",
                                      "extract": "Un antihelmíntico es un medicamento contra los vermes.", "disambiguation": False,
                                      "redirectedFrom": "Vermífugo"})

    def conn(self):
        return glossary_review.open_catalog(self.db)


class CandidateTests(ReviewTestCase):
    def test_candidates_by_frequency_without_known_or_sensitive_activities(self):
        document = doc([{"activity": "Estimulante", "wiktionaryTitle": "estimulante"}],
                       [{"activity": "Tónico", "code": "vaga", "reason": "r", "date": "2026-10-29"}])
        with self.conn() as conn:
            rows = glossary_review.candidates(conn, document, min_groups=1)
        names = [r[0] for r in rows]
        self.assertEqual(names[0], "Diurético")  # 5 grupos y el calificador sumados: la actividad más frecuente
        self.assertEqual(dict(rows)["Diurético"], 6)
        self.assertNotIn("Estimulante", names)
        self.assertNotIn("Tónico", names)
        self.assertNotIn(FORMULA, names)

    def test_minimum_group_count(self):
        document = doc([{"activity": "Estimulante", "wiktionaryTitle": "estimulante"}])
        with self.conn() as conn:
            rows = glossary_review.candidates(conn, document, min_groups=3)
        self.assertEqual([r[0] for r in rows], ["Diurético", "Fiebre"])

    def test_pending_groups_are_not_counted(self):
        with self.conn() as conn:
            stats, total, plants = glossary_review.activity_stats(conn)
        self.assertEqual(stats["tónico"]["groups"], 1)
        self.assertEqual(total, len(GROUPS) - 1)

    def test_missing_catalog(self):
        with self.assertRaises(SourceError):
            glossary_review.open_catalog(os.path.join(self.tmp.name, "no-existe.db"))

    def test_catalog_is_opened_read_only(self):
        with self.conn() as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM plant_use_group")


class SensesTests(ReviewTestCase):
    def test_senses_output_for_a_wiktionary_term(self):
        document = doc([{"activity": "Anodino", "wiktionaryTitle": "anodino"}])
        text = glossary_review.format_senses(document, self.cache)
        self.assertIn("== Anodino (Wikcionario: anodino)", text)
        self.assertIn("4 (Medicina) [Adjetivo] Dicho de un medicamento: Que mitiga el dolor.", text)
        self.assertIn("1 [Adjetivo] Insignificante, insustancial.", text)

    def test_senses_output_for_missing_and_not_downloaded(self):
        document = doc([{"activity": "Vermífugo", "wiktionaryTitle": "vermífugo", "wikipediaTitle": "Vermífugo"},
                        {"activity": "Tónico", "wiktionaryTitle": "tónico"}])
        text = glossary_review.format_senses(document, self.cache)
        self.assertIn("sin entrada", text)
        self.assertIn("primera oración: Un antihelmíntico es un medicamento contra los vermes.", text)
        self.assertIn("sin descargar", text)

    def test_filter(self):
        document = doc([{"activity": "Anodino", "wiktionaryTitle": "anodino"}, {"activity": "Diurético", "wiktionaryTitle": "diurético"}])
        text = glossary_review.format_senses(document, self.cache, only=["Diurético"])
        self.assertIn("Diurético", text)
        self.assertNotIn("Anodino", text)


class ReviewTableTests(ReviewTestCase):
    def build(self, document):
        with self.conn() as conn:
            return glossary_review.build_review(document, self.cache, conn, "2026-10-29")

    def document(self):
        return doc(
            [{"activity": "Diurético", "wiktionaryTitle": "diurético", "source": "wiktionary_es", "sense": 1, "reason": "Describe la acción."},
             {"activity": "Antiséptico", "wiktionaryTitle": "antiséptico", "source": "wiktionary_es", "sense": 2, "reason": "Medicina."},
             {"activity": "Estimulante", "wiktionaryTitle": "estimulante", "wikipediaTitle": "Estimulante", "source": "wikipedia_es",
              "mode": "literal", "reason": "Define bien."},
             {"activity": "Vermífugo", "wiktionaryTitle": "vermífugo", "wikipediaTitle": "Vermífugo", "source": "wikipedia_es", "mode": "adapted",
              "text": "Medicamento contra los vermes.", "evidence": "es un medicamento contra los vermes", "reason": "Sin entrada."}],
            [{"activity": "Tónico", "code": "vaga", "reason": "No define.", "date": "2026-10-29"}],
            {"Antiséptico": [{"pattern": "prevenir", "reason": "aprobado"}]})

    def test_one_row_per_term_with_exact_text_mode_and_revision_url(self):
        text = self.build(self.document())
        rows = {line.split("|")[1].strip(): [c.strip() for c in line.split("|")] for line in text.split("\n")
                if line.startswith("| ") and line.count("|") == 10}
        self.assertEqual(set(rows) - {"Término", "---"}, {"Diurético", "Antiséptico", "Estimulante", "Vermífugo"})
        diuretic = rows["Diurético"]
        self.assertEqual(diuretic[5], "«Que aumenta o facilita la producción y excreción de orina.»")
        self.assertEqual((diuretic[3], diuretic[6]), ("Wikcionario", "literal"))
        self.assertEqual(diuretic[7], "https://es.wiktionary.org/w/index.php?title=diur%C3%A9tico&oldid=6324321")
        self.assertEqual(diuretic[9], "")  # «Aprobado» vacía
        self.assertEqual(rows["Vermífugo"][5], "«Medicamento contra los vermes.»")
        self.assertEqual((rows["Vermífugo"][3], rows["Vermífugo"][6]), ("Wikipedia", "adaptado"))
        self.assertEqual(rows["Vermífugo"][7], "https://es.wikipedia.org/w/index.php?title=Antihelm%C3%ADntico&oldid=168576174")
        self.assertIn("Un estimulante (del verbo latino stimulāre)", rows["Estimulante"][5])

    def test_coverage_counts_groups_and_plants_by_base_form(self):
        text = self.build(self.document())
        self.assertIn("| Diurético | 6 grupos, 5 plantas (Diurético 5; Diurético (veterinario) 1) |", text)

    def test_alerts_show_approved_and_unapproved_patterns(self):
        document = self.document()
        text = self.build(document)
        self.assertIn("patrón vigilado «prevenir» (aprobado por el usuario el 2026-10-29)", text)
        document["approvedPatterns"] = {}
        self.assertIn("patrón vigilado «prevenir» (SIN APROBAR)", self.build(document))

    def test_evidence_that_is_not_in_the_extract_is_flagged(self):
        document = self.document()
        document["terms"][3]["evidence"] = "es un medicamento que no figura"
        self.assertIn("LA EVIDENCIA NO ES LITERAL", self.build(document))

    def test_excluded_section_and_coverage_summary(self):
        text = self.build(self.document())
        self.assertIn("## Términos excluidos", text)
        self.assertIn("| Tónico | 1 grupos, 1 plantas | No define. | `vaga` | 2026-10-29 |", text)
        self.assertIn("| Términos con explicación | 4 |", text)
        self.assertIn("| Explicación literal de Wikcionario | 2 |", text)
        self.assertIn("| Explicación literal de Wikipedia | 1 |", text)
        self.assertIn("| Explicación adaptada de Wikipedia | 1 |", text)
        self.assertIn("| Términos sin explicación (excluidos) | 1 |", text)
        # Grupos con explicación: Diurético 6 + Antiséptico 1 + Estimulante 3 + Vermífugo 2 = 12 de 19 visibles
        self.assertIn("| Grupos con explicación (de 19 visibles) | 12 (63.2 %) |", text)

    def test_pending_terms_are_listed(self):
        document = self.document()
        document["terms"].append({"activity": "Anodino", "wiktionaryTitle": "anodino"})
        text = self.build(document)
        self.assertIn("## Términos sin propuesta", text)
        self.assertIn("| Términos sin propuesta | 1 |", text)

    def test_missing_sense_fails_clearly(self):
        document = self.document()
        document["terms"][0]["sense"] = 9
        with self.assertRaises(SourceError):
            self.build(document)

    def test_cli_writes_the_file(self):
        terms = os.path.join(self.tmp.name, "terms.json")
        with open(terms, "w", encoding="utf-8") as handle:
            json.dump(self.document(), handle)
        out = os.path.join(self.tmp.name, "review", "glossary-review.md")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = cli.main(["--cache-dir", self.cache, "glossary-review", "--terms", terms, "--catalog", self.db, "--out", out])
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as handle:
            self.assertTrue(handle.read().startswith("# Revisión del glosario de actividades"))

    def test_cli_candidates_and_senses(self):
        terms = os.path.join(self.tmp.name, "terms.json")
        with open(terms, "w", encoding="utf-8") as handle:
            json.dump(doc([{"activity": "Anodino", "wiktionaryTitle": "anodino"}]), handle)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cli.main(["glossary-candidates", "--terms", terms, "--catalog", self.db, "--min-groups", "1", "--limit", "2"])
            cli.main(["--cache-dir", self.cache, "glossary-senses", "--terms", terms])
        lines = buffer.getvalue().split("\n")
        self.assertEqual(lines[0].split(), ["6", "Diurético"])
        self.assertIn("== Anodino (Wikcionario: anodino)", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
