import contextlib
import hashlib
import io
import json
import os
import sqlite3

import extract_support as support
from catalog_seed import cli, workdb
from test_tppt_extract import statements
from test_usda_extract import tables


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class ExtractCommandTests(support.TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(os.path.join(self.cache, "usda"))
        os.makedirs(os.path.join(self.cache, "tppt"))
        usda = os.path.join(self.cache, "usda", "u.zip")
        tppt = os.path.join(self.cache, "tppt", "t.zip")
        support.make_usda_zip(usda, tables())
        support.make_tppt_zip(tppt, statements())

        def source(source_id, path, name):
            return {"id": source_id, "version": "v", "license": "l", "attribution": "a", "enabled": True, "url": "https://example.invalid/" + name,
                    "filename": name, "size": os.path.getsize(path), "checksum": {"algorithm": "sha256", "value": digest(path)}}
        self.sources = os.path.join(self.tmp, "sources.json")
        with open(self.sources, "w") as handle:
            json.dump({"sources": [source("usda", usda, "u.zip"), source("tppt", tppt, "t.zip")]}, handle)
        self.db = os.path.join(self.tmp, "work", "sources.db")

    def run_cli(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cli.main(["--sources", self.sources, "--cache-dir", self.cache, "extract", "--db", self.db] + list(extra))

    def counts(self):
        connection = sqlite3.connect(self.db)
        try:
            return workdb.counts(connection)
        finally:
            connection.close()

    def test_extract_writes_rows_and_is_repeatable(self):
        self.assertEqual(self.run_cli(), 0)
        first = self.counts()
        self.assertEqual(first["usda/usda_use"], 3)
        self.assertEqual(first["tppt/tppt_plant"], 3)
        self.assertEqual(self.run_cli("--source", "tppt"), 0)
        self.assertEqual(self.counts(), first)

    def test_row_columns_hold_provenance(self):
        self.run_cli("--source", "usda")
        connection = sqlite3.connect(self.db)
        try:
            row = connection.execute("SELECT source, record_type, row_key, raw_name_cell, fnfnum, qid, content_json FROM source_row "
                                     "WHERE record_type = 'usda_use' AND row_key = '12'").fetchone()
            meta = connection.execute("SELECT version, rows FROM extraction WHERE source = 'usda'").fetchone()
        finally:
            connection.close()
        self.assertEqual(row[:6], ("usda", "usda_use", "12", "Mentha × piperita", None, None))
        self.assertEqual(json.loads(row[6])["reference"], "Burkill,1966")
        self.assertEqual(meta, ("v", sum(n for k, n in self.counts().items() if k.startswith("usda/"))))

    def test_missing_input_fails_with_download_step(self):
        os.remove(os.path.join(self.cache, "tppt", "t.zip"))
        self.assertEqual(self.run_cli("--source", "tppt"), 1)

    def test_disabled_source_is_skipped(self):
        with open(self.sources) as handle:
            document = json.load(handle)
        document["sources"][0]["enabled"] = False
        with open(self.sources, "w") as handle:
            json.dump(document, handle)
        self.run_cli()
        self.assertNotIn("usda/usda_use", self.counts())


if __name__ == "__main__":
    import unittest
    unittest.main()
