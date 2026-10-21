import copy
import json
import os
import tempfile
import unittest

import support  # noqa: F401
from support import make_source

from catalog_seed.sources import (
    ADMITTED_SOURCES, DEFAULT_SOURCES_FILE, DISCARDED_SOURCES, SourceError,
    check_source_id, load_sources, validate_source,
)


class SourceListTests(unittest.TestCase):
    def test_lists_match_the_spec(self):
        self.assertEqual(set(ADMITTED_SOURCES), {
            "usda", "wcvp", "wfo", "ema_json", "ema_pdf", "tppt", "efsa",
            "wikidata", "wikipedia_es", "commons"})
        self.assertEqual(len(DISCARDED_SOURCES), 10)
        self.assertFalse(set(ADMITTED_SOURCES) & set(DISCARDED_SOURCES))

    def test_admitted_sources_pass(self):
        for name in ADMITTED_SOURCES:
            check_source_id(name)

    def test_source_outside_admitted_list_fails(self):
        with self.assertRaises(SourceError):
            check_source_id("fuente_inventada")
        with self.assertRaises(SourceError):
            validate_source(copy.deepcopy(make_source(id="fuente_inventada").data))

    def test_discarded_sources_fail(self):
        for name in ("DrugBank", "iNaturalist", "AromaDb", "NHPID", "who"):
            with self.assertRaises(SourceError) as ctx:
                check_source_id(name)
            self.assertIn("descartada", str(ctx.exception))

    def test_manifest_with_discarded_source_is_rejected(self):
        data = copy.deepcopy(make_source().data)
        data["id"] = "drugbank"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sources.json")
            with open(path, "w") as handle:
                json.dump({"sources": [data]}, handle)
            with self.assertRaises(SourceError):
                load_sources(path)

    def test_missing_field_is_rejected(self):
        data = copy.deepcopy(make_source().data)
        del data["license"]
        with self.assertRaises(SourceError):
            validate_source(data)

    def test_shipped_sources_json_is_valid_and_has_usda(self):
        sources = {s.id: s for s in load_sources(DEFAULT_SOURCES_FILE)}
        usda = sources["usda"]
        self.assertEqual(usda.size, 6033990)
        self.assertEqual(usda.checksum, "45ae44a0544586b8ac22a232beaac344")
        self.assertTrue(usda.enabled)


if __name__ == "__main__":
    unittest.main()
