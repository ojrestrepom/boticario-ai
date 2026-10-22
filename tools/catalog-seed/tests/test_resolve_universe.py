import contextlib
import hashlib
import io
import json
import os
import sqlite3
import zipfile

import extract_support as support
import taxonomy_support
from catalog_seed import cli, workdb
from catalog_seed.workdb import Row

FIXTURES = taxonomy_support.FIXTURES


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def usda_row(fnfnum, taxon, author=""):
    return Row("usda_taxon", fnfnum, {"taxon": taxon, "taxauthor": author}, raw_name_cell=taxon, fnfnum=fnfnum)


def ema_row(slug, cell, combination="No"):
    return Row("ema_herbal", slug, {"slug": slug, "combination": combination}, raw_name_cell=cell)


class ResolveCommandTests(support.TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(os.path.join(self.cache, "wcvp"))
        os.makedirs(os.path.join(self.cache, "wfo"))
        self.wcvp_zip = os.path.join(self.cache, "wcvp", "wcvp.zip")
        self.wfo_zip = os.path.join(self.cache, "wfo", "wfo.zip")
        with zipfile.ZipFile(self.wcvp_zip, "w") as archive:
            archive.write(os.path.join(FIXTURES, "wcvp_names.csv"), "wcvp_names.csv")
            archive.write(os.path.join(FIXTURES, "wcvp_distribution.csv"), "wcvp_distribution.csv")
        with zipfile.ZipFile(self.wfo_zip, "w") as archive:
            archive.write(os.path.join(FIXTURES, "wfo_classification.csv"), "classification.csv")
        self.sources = os.path.join(self.tmp, "sources.json")
        self.write_sources()
        self.db = os.path.join(self.tmp, "work", "sources.db")
        self.taxonomy = os.path.join(self.tmp, "work", "taxonomy.db")
        self.out = os.path.join(self.tmp, "work", "universe")
        self.catalog = os.path.join(self.tmp, "catalog.db")
        self.store([usda_row("1", "Matricaria recutita", "L."), usda_row("2", "Citrus limon", "(L.) BURMAN f.")],
                   [ema_row("matricariae-flos", "Matricaria recutita L."), ema_row("valerianae-radix", "Valeriana officinalisL."),
                    ema_row("citri-bergamiae-aetheroleum", "Citrus bergamia Risso &amp; Poiteau."),
                    ema_row("valerianae-radix-passiflorae-herba", "Combination: Valeriana officinalis L. and Passiflora incarnata L.", "Yes")])
        connection = sqlite3.connect(self.catalog)
        connection.execute("CREATE TABLE plant (id TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO plant VALUES (?)", [("matricaria-recutita",), ("citrus-limon",), ("lavandula-angustifolia",)])
        connection.commit()
        connection.close()

    def write_sources(self, wcvp_value=None):
        def source(source_id, path, name, algorithm="sha256", value=None):
            return {"id": source_id, "version": "v", "license": "l", "attribution": "a", "enabled": True,
                    "url": "https://example.invalid/" + name, "filename": name, "size": os.path.getsize(path),
                    "checksum": {"algorithm": algorithm, "value": value or digest(path)}}
        with open(self.sources, "w") as handle:
            json.dump({"sources": [source("wcvp", self.wcvp_zip, "wcvp.zip", value=wcvp_value),
                                   source("wfo", self.wfo_zip, "wfo.zip")]}, handle)

    def store(self, usda_rows, ema_rows):
        connection = workdb.open_db(self.db)
        try:
            workdb.replace_source(connection, "usda", usda_rows, "usda test", [])
            workdb.replace_source(connection, "ema_json", ema_rows, "ema test", [])
        finally:
            connection.close()

    def run_cli(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        files = ["--decisions", os.path.join(self.tmp, "decisions.json"), "--exceptions", os.path.join(self.tmp, "exceptions.json")]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["--sources", self.sources, "--cache-dir", self.cache, "resolve", "--db", self.db,
                             "--taxonomy-db", self.taxonomy, "--out-dir", self.out, "--catalog-db", self.catalog] + files + list(extra))
        return code, out.getvalue(), err.getvalue()

    def universe(self):
        with open(os.path.join(self.out, "universe.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def report(self):
        with open(os.path.join(self.out, "report.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def test_entries_from_usda_and_ema_species_not_in_usda(self):
        code, _, err = self.run_cli()
        self.assertEqual(code, 1, err)  # lavandula-angustifolia no está en este universo mínimo
        report = self.report()
        entries = report["entries"]
        self.assertEqual((entries["usda_entries"], entries["ema_entries"]), (2, 3))
        self.assertEqual(entries["ema_fiches_without_species"], ["valerianae-radix-passiflorae-herba"])
        plants = {p["id"]: p for p in self.universe()["plants"]}
        self.assertEqual(sorted(plants), ["citrus-x-bergamia", "citrus-x-limon", "matricaria-chamomilla", "valeriana-officinalis"])
        # La especie de la EMA que ya está en USDA se une a la planta; la que no está, crea la suya.
        self.assertEqual([e["key"] for e in plants["matricaria-chamomilla"]["entries"]], ["usda:1", "ema:matricariae-flos#1"])
        self.assertEqual([e["source"] for e in plants["valeriana-officinalis"]["entries"]], ["ema"])
        self.assertEqual(report["plants"]["ema_only"], 2)  # valeriana y bergamota
        self.assertEqual(report["plants"]["usda_and_ema"], 1)

    def test_universe_json_format(self):
        self.run_cli()
        document = self.universe()
        self.assertEqual(document["format"], "catalog-universe/1")
        self.assertEqual(set(document), {"format", "inputs", "checks", "plantCount", "plants"})
        self.assertEqual(document["plantCount"], len(document["plants"]))
        self.assertEqual(set(document["inputs"]), {"wcvp", "wfo", "usda", "ema_json", "indexVersion", "collisionDecisions",
                                                 "collisionExceptions"})
        plant = {p["id"]: p for p in document["plants"]}["citrus-x-limon"]
        self.assertEqual(set(plant), {"id", "name", "author", "kind", "backbone", "acceptedId", "matchedId", "family", "entries",
                                      "aliases", "flags", "reviewFlags", "collision"})
        self.assertEqual((plant["name"], plant["kind"], plant["backbone"]), ("Citrus × limon", "resolved", "wcvp"))
        self.assertEqual(plant["aliases"], ["citrus-limon"])
        self.assertEqual(set(plant["entries"][0]), {"source", "key", "name", "author", "outcome", "matchedName", "relation"})
        self.assertEqual(plant["collision"]["members"], ["citrus-x-bergamia", "citrus-x-limon"])
        bergamot = {p["id"]: p for p in document["plants"]}["citrus-x-bergamia"]
        self.assertEqual(bergamot["kind"], "heterotypic")
        self.assertEqual(bergamot["entries"][0]["relation"], "heterotípico")
        self.assertIn("grupo-partido", [f["code"] for f in bergamot["reviewFlags"]])
        self.assertEqual(self.universe()["plants"], sorted(self.universe()["plants"], key=lambda p: p["id"]))

    def write_decisions(self, decision, reason):
        document = {"format": "catalog-collision-decisions/1", "groups": {"citrus limon": {"accepted": "Citrus × limon", "members": {
            "citrus bergamia": {"name": "Citrus × bergamia", "decision": decision, "reason": reason}}}}}
        with open(os.path.join(self.tmp, "decisions.json"), "w", encoding="utf-8") as handle:
            json.dump(document, handle)

    def test_without_decisions_the_report_lists_the_member_as_undecided(self):
        self.run_cli()
        decisions = self.report()["collisions"]["decisions"]
        self.assertEqual((decisions["members"], decisions["undecided"], decisions["fused"], decisions["separated"]), (1, 1, 0, 0))
        self.assertEqual(decisions["groupsByState"], {"decidido": 0, "parcial": 0, "sin-decision": 1})
        self.assertEqual(decisions["undecidedMembers"][0]["plant"], "citrus-x-bergamia")
        with open(os.path.join(self.out, "report.md"), encoding="utf-8") as handle:
            self.assertIn("### Heterotípicos sin decisión registrada (1)", handle.read())
        self.assertIsNone(self.universe()["inputs"]["collisionDecisions"])

    def test_recorded_fusion_merges_the_member_and_is_reported(self):
        self.write_decisions("fuse", "redireccion")
        self.run_cli()
        plants = {p["id"]: p for p in self.universe()["plants"]}
        self.assertNotIn("citrus-x-bergamia", plants)
        lemon = plants["citrus-x-limon"]
        self.assertEqual(lemon["aliases"], ["citrus-bergamia", "citrus-limon"])
        self.assertIn("fusion-heterotipica", [f["code"] for f in lemon["reviewFlags"]])
        self.assertEqual(lemon["fusedHeterotypic"], [{"name": "Citrus × bergamia", "reason": "redireccion", "entries": ["ema:citri-bergamiae-aetheroleum#1"]}])
        self.assertEqual(len(lemon["fusedMatchedIds"]), 1)
        self.assertIsNone(lemon["collision"])
        report = self.report()
        decisions = report["collisions"]["decisions"]
        self.assertEqual((decisions["fused"], decisions["fusedByReason"], decisions["undecided"]), (1, {"redireccion": 1}, 0))
        self.assertEqual(report["collisions"]["split_groups"], 0)
        self.assertEqual(report["collisions"]["groups_with_heterotypic_fused"], 1)
        self.assertEqual(report["comparison_with_current"]["current_ids_lost"], ["lavandula-angustifolia"])
        self.assertEqual(len(self.universe()["inputs"]["collisionDecisions"]), 64)

    def test_recorded_separation_keeps_the_member_as_its_own_plant(self):
        self.write_decisions("separate", "articulo-propio")
        self.run_cli()
        bergamot = {p["id"]: p for p in self.universe()["plants"]}["citrus-x-bergamia"]
        self.assertEqual(bergamot["collisionDecision"], {"state": "decidido", "decision": "separate", "reason": "articulo-propio"})
        self.assertEqual(self.report()["collisions"]["decisions"]["separatedByReason"], {"articulo-propio": 1})

    def test_report_and_comparison_with_current_ids(self):
        self.run_cli()
        report = self.report()
        comparison = report["comparison_with_current"]
        self.assertEqual(comparison["current_ids"], 3)
        self.assertEqual(comparison["current_ids_kept_as_alias"], 2)  # citrus-limon y matricaria-recutita
        self.assertEqual(comparison["current_ids_lost"], ["lavandula-angustifolia"])
        self.assertEqual(report["collisions"]["groups_with_heterotypic_split"], 1)
        with open(os.path.join(self.out, "report.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## Grupos de colisión", text)
        self.assertIn("citrus-x-bergamia", text)
        self.assertIn("heterotípico; planta propia `citrus-x-bergamia`", text)

    def test_report_lists_modified_ema_cells_and_fuzzy_matches(self):
        self.store([usda_row("1", "Zizyphus jujuba", "MILL."), usda_row("2", "Taraxacum officinale", "WEBER EX F. H. WIGG.")],
                   [ema_row("verbenae", "Aloysia citrodora Paláu (syn. Aloysia triphylla (L’Hér.) Kuntze;Verbena triphylla L’Hér.;Lippia citriodora Kunth"),
                    ema_row("salicis", "Salix [various species including S. purpurea L.; S. daphnoides Vill.]"),
                    ema_row("viola", "Viola arvensis Murray (Gaud)"),
                    ema_row("eschscholziae", "Eschscholzia california Cham.")])
        self.run_cli()
        report = self.report()
        cells = {c["fiche"]: c for c in report["ema_modified_cells"]}
        self.assertEqual(sorted(cells), ["salicis", "verbenae", "viola"])
        self.assertEqual([e["name"] for e in cells["verbenae"]["entries"]], ["Aloysia citrodora"])
        self.assertEqual([(e["name"], e["author"]) for e in cells["salicis"]["entries"]],
                         [("Salix purpurea", "L."), ("Salix daphnoides", "Vill.")])
        self.assertEqual(cells["viola"]["entries"][0]["author"], "Murray")
        fuzzy = {i["key"]: i for i in report["review"]["fuzzy_match"]}
        self.assertEqual(sorted(fuzzy), ["ema:eschscholziae#1", "usda:1"])
        self.assertEqual((fuzzy["usda:1"]["matched"], fuzzy["usda:1"]["distance"], fuzzy["usda:1"]["accepted"]),
                         ("Ziziphus jujuba", 1, "Ziziphus jujuba"))
        self.assertEqual([i["key"] for i in report["review"]["accepted_above_species"]], ["usda:2"])
        ids = {p["id"] for p in self.universe()["plants"]}
        self.assertTrue({"ziziphus-jujuba", "eschscholzia-californica", "taraxacum-officinale", "salix-purpurea"} <= ids)
        self.assertFalse({"lippia-citriodora", "eschscholzia-california"} & ids)
        with open(os.path.join(self.out, "report.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## Coincidencia aproximada (fuzzy_match) (2)", text)
        self.assertIn("## Celdas de la EMA modificadas (3)", text)

    def test_exit_code_is_zero_when_the_pilot_plant_is_present(self):
        self.store([usda_row("1", "Lavandula angustifolia", "Mill.")], [ema_row("lavandulae-flos", "Lavandula angustifolia Mill.")])
        code, _, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertTrue(self.report()["checks"]["lavandula-angustifolia"])

    def test_duplicate_ids_fail_and_write_nothing(self):
        self.store([usda_row("1", "Foo ba r"), usda_row("2", "Foo ba-r")], [ema_row("x", "Matricaria recutita L.")])
        code, _, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("IDs repetidos", err)
        self.assertIn("foo-ba-r", err)
        self.assertFalse(os.path.exists(os.path.join(self.out, "universe.json")))

    def test_index_is_reused_and_rebuilt_when_a_checksum_changes(self):
        _, out, _ = self.run_cli()
        self.assertIn("construyendo el índice", out)
        stamp = os.stat(self.taxonomy).st_mtime_ns
        _, out, _ = self.run_cli()
        self.assertIn("índice taxonómico vigente", out)
        self.assertEqual(os.stat(self.taxonomy).st_mtime_ns, stamp)
        # Un checksum distinto en sources.json con el insumo íntegro de la caché: el índice se recrea (y falla la verificación).
        self.write_sources(wcvp_value="0" * 64)
        code, out, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("alterado", err)

    def test_missing_sources_db_names_the_extract_step(self):
        os.remove(self.db)
        code, _, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("extract", err)
