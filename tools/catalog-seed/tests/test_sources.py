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

    def test_shipped_sources_declare_all_phase_one_sources(self):
        sources = {s.id: s for s in load_sources(DEFAULT_SOURCES_FILE)}
        self.assertTrue({"usda", "wcvp", "wfo", "ema_json", "tppt", "efsa"} <= set(sources))
        for source in sources.values():
            self.assertTrue(source.pinned, source.id)
        self.assertEqual(sources["wcvp"].size, 88179649)
        self.assertEqual(sources["wfo"].checksum, "0e4486945cd9f7af548ca87eb9a870ed")
        self.assertEqual([f.filename for f in sources["efsa"].files], ["BOTANIC.xls", "ENDPOINTSTUDY.xls"])
        self.assertIn("meta.timestamp", sources["ema_json"].version)

    def test_license_url_is_optional_and_must_be_https_or_null(self):
        self.assertFalse(make_source().has_license_url)
        self.assertIsNone(make_source().license_url)
        url = "https://creativecommons.org/licenses/by/4.0/"
        with_url = make_source(licenseUrl=url)
        self.assertTrue(with_url.has_license_url)
        self.assertEqual(with_url.license_url, url)
        explicit_null = make_source(licenseUrl=None)
        self.assertTrue(explicit_null.has_license_url)
        self.assertIsNone(explicit_null.license_url)
        for bad in ("", "   ", "http://creativecommons.org/licenses/by/4.0/", "creativecommons.org", "https://", "https://a b/", 3, True, ["https://x/"]):
            data = copy.deepcopy(make_source().data)
            data["licenseUrl"] = bad
            with self.assertRaises(SourceError, msg=repr(bad)) as ctx:
                validate_source(data)
            self.assertIn("licenseUrl", str(ctx.exception))

    def test_shipped_sources_declare_the_license_url(self):
        sources = {s.id: s for s in load_sources(DEFAULT_SOURCES_FILE)}
        cc = "https://creativecommons.org/"
        expected = {
            "wikipedia_es": (cc + "licenses/by-sa/4.0/", "CC BY-SA 4.0"),
            "efsa": (cc + "licenses/by/4.0/", "CC BY 4.0"),
            "wcvp": (cc + "licenses/by/3.0/", "CC BY 3.0"),
            "usda": (cc + "publicdomain/zero/1.0/", "CC0"),
            "wfo": (cc + "publicdomain/zero/1.0/", "CC0"),
            "wikidata": (cc + "publicdomain/zero/1.0/", "CC0 1.0"),
            "commons": (None, None),
            "ema_json": (None, None),
            "ema_pdf": (None, None),
            "tppt": (None, None),
        }
        self.assertEqual(set(expected), set(sources))
        for source_id, (url, license_text) in expected.items():
            source = sources[source_id]
            self.assertTrue(source.has_license_url, source_id)
            self.assertEqual(source.license_url, url, source_id)
            if license_text:
                self.assertEqual(source.license, license_text, source_id)

    def test_multi_file_source_is_valid_and_single_file_stays_compatible(self):
        single = copy.deepcopy(make_source().data)
        multi = {k: v for k, v in single.items() if k not in ("url", "filename", "size", "checksum")}
        multi["files"] = [
            {k: single[k] for k in ("url", "filename", "size", "checksum")},
            dict({k: single[k] for k in ("url", "size", "checksum")}, filename="otro.zip")]
        source = validate_source(multi)
        self.assertEqual(len(source.files), 2)
        self.assertEqual(validate_source(single).filename, "insumo.zip")

    def test_files_and_single_file_fields_are_exclusive(self):
        data = copy.deepcopy(make_source().data)
        data["files"] = [{k: data[k] for k in ("url", "filename", "size", "checksum")}]
        with self.assertRaises(SourceError):
            validate_source(data)

    def test_duplicate_filenames_in_files_are_rejected(self):
        data = copy.deepcopy(make_source().data)
        entry = {k: data.pop(k) for k in ("url", "filename", "size", "checksum")}
        data["files"] = [entry, dict(entry)]
        with self.assertRaises(SourceError):
            validate_source(data)

    def test_size_and_checksum_must_be_both_null_or_both_set(self):
        data = copy.deepcopy(make_source().data)
        data["checksum"] = None
        with self.assertRaises(SourceError):
            validate_source(data)
        data["size"] = None
        self.assertFalse(validate_source(data).pinned)


class ReadableFieldsTests(unittest.TestCase):
    """`name` y `pageUrl` son obligatorios en todas las fuentes: la semilla los entrega para los créditos."""

    def test_name_and_page_url_are_required(self):
        for field in ("name", "pageUrl"):
            data = dict(make_source().data)
            del data[field]
            with self.assertRaises(SourceError, msg=field):
                validate_source(data)
            data[field] = "  "
            with self.assertRaises(SourceError, msg=field):
                validate_source(data)

    def test_page_url_must_be_http(self):
        with self.assertRaises(SourceError):
            validate_source(dict(make_source().data, pageUrl="www.example.org"))

    def test_shipped_sources_have_a_name_and_a_page_url(self):
        for source in load_sources(DEFAULT_SOURCES_FILE):
            self.assertTrue(source.name.strip(), source.id)
            self.assertTrue(source.page_url.startswith("https://"), source.id)


class ServiceSourceTests(unittest.TestCase):
    """Wikidata, Wikipedia en español y Commons son servicios en línea: sin archivo, tamaño ni checksum."""

    def data(self, source_id="wikidata", **overrides):
        data = {"id": source_id, "name": "Fixture", "pageUrl": "https://example.invalid/", "version": "consulta dirigida", "url": "https://query.example/sparql", "license": "CC0 1.0",
                "attribution": "Colaboradores de Wikidata", "enabled": True}
        data.update(overrides)
        return data

    def test_service_source_is_valid_without_file_fields(self):
        for name in ("wikidata", "wikipedia_es", "commons"):
            source = validate_source(self.data(name))
            self.assertTrue(source.is_service)
            self.assertEqual(source.files, [])
            self.assertTrue(source.pinned)
            self.assertEqual(source.url, "https://query.example/sparql")
            self.assertIsNone(source.checksum)
            self.assertEqual(source.cache_path("/cache").name, name)

    def test_service_source_keeps_the_common_fields_and_enabled(self):
        self.assertFalse(validate_source(self.data(enabled=False)).enabled)
        for field in ("version", "license", "attribution", "enabled", "url"):
            data = self.data()
            del data[field]
            with self.assertRaises(SourceError, msg=field):
                validate_source(data)
        with self.assertRaises(SourceError):
            validate_source(self.data(enabled="si"))

    def test_service_source_rejects_file_fields(self):
        for field, value in (("filename", "x.json"), ("size", 3), ("checksum", None), ("files", [])):
            with self.assertRaises(SourceError, msg=field) as ctx:
                validate_source(self.data(**{field: value}))
            self.assertIn("servicio en línea", str(ctx.exception))

    def test_file_sources_are_not_services(self):
        self.assertFalse(make_source().is_service)

    def test_shipped_services_have_license_attribution_and_enabled(self):
        sources = {s.id: s for s in load_sources(DEFAULT_SOURCES_FILE)}
        self.assertEqual(sources["wikipedia_es"].license, "CC BY-SA 4.0")
        self.assertIn("CC0", sources["commons"].license)
        for name in ("wikidata", "wikipedia_es", "commons"):
            self.assertIsInstance(sources[name].enabled, bool)
            self.assertTrue(sources[name].attribution)


if __name__ == "__main__":
    unittest.main()
