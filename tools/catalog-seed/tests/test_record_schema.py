import copy
import json
import unittest

import fixtures_support as fx
import support  # noqa: F401

from catalog_seed import schema as schema_lib
from catalog_seed.sources import SourceError


class MiniValidatorTests(unittest.TestCase):
    def check(self, schema, value):
        return schema_lib.validate(value, schema)

    def test_types_and_bool_is_not_integer(self):
        self.assertEqual(self.check({"type": "integer"}, 3), [])
        self.assertTrue(self.check({"type": "integer"}, True))
        self.assertEqual(self.check({"type": ["string", "null"]}, None), [])
        self.assertTrue(self.check({"type": "string"}, 4))

    def test_object_keywords(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
        self.assertEqual(self.check(schema, {"a": "x"}), [])
        self.assertTrue(any("falta" in e for e in self.check(schema, {})))
        self.assertTrue(any("desconocido" in e for e in self.check(schema, {"a": "x", "b": 1})))

    def test_array_and_string_limits(self):
        self.assertTrue(self.check({"type": "array", "maxItems": 1}, [1, 2]))
        self.assertTrue(self.check({"type": "array", "minItems": 1}, []))
        self.assertTrue(self.check({"type": "string", "maxLength": 2}, "abc"))
        self.assertTrue(self.check({"type": "string", "minLength": 1}, ""))
        self.assertTrue(self.check({"type": "string", "pattern": "^a"}, "b"))
        self.assertTrue(self.check({"type": "integer", "minimum": 1}, 0))

    def test_enum_const_ref_and_property_names(self):
        self.assertTrue(self.check({"enum": ["a", None]}, "b"))
        self.assertEqual(self.check({"enum": ["a", None]}, None), [])
        self.assertTrue(self.check({"const": 1}, 2))
        schema = {"$defs": {"s": {"type": "string"}}, "type": "object", "propertyNames": {"pattern": "^k"}, "additionalProperties": {"$ref": "#/$defs/s"}}
        self.assertEqual(self.check(schema, {"k1": "x"}), [])
        self.assertTrue(self.check(schema, {"k1": 1}))
        self.assertTrue(self.check(schema, {"z": "x"}))

    def test_unsupported_keyword_is_rejected(self):
        with self.assertRaises(SourceError):
            schema_lib.check_supported({"type": "object", "oneOf": []})

    def test_annotations_and_extension_keys_are_allowed(self):
        schema_lib.check_supported({"title": "t", "description": "d", "x-recordVersion": 1, "type": "string"})


class RecordSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema_lib.load_schema()

    def errors(self, record):
        return schema_lib.validate(record, self.schema)

    def test_schema_uses_only_the_supported_subset(self):
        schema_lib.check_supported(self.schema)

    def test_valid_records_pass(self):
        self.assertEqual(self.errors(fx.record("matricaria")), [])
        self.assertEqual(self.errors(fx.record("hiperico")), [])

    def test_every_missing_field_fails(self):
        base = fx.record()
        for field in self.schema["required"]:
            record = copy.deepcopy(base)
            del record[field]
            self.assertTrue(any("'%s'" % field in e for e in self.errors(record)), field)

    def test_every_unknown_field_fails_at_each_level(self):
        for path in ([], ["scientificName"], ["goals", 0], ["traditionalUses", 0], ["traditionalUses", 0, "citations", 0],
                     ["image"], ["safety"], ["family"], ["reviewFlags", 0], ["sources", 0], ["refs", "wcvp:1"]):
            record = fx.record()
            if path == ["safety"]:
                record = fx.record("hiperico")
            node = record
            for step in path:
                node = node[step]
            node["campoDesconocido"] = 1
            self.assertTrue(any("campo desconocido" in e for e in self.errors(record)), path)

    def test_limits(self):
        name = {"name": "Mentha", "authors": None, "refs": ["wcvp:1"]}
        record = fx.record()
        record["synonyms"] = [name] * 10
        self.assertEqual(self.errors(record), [])
        record["synonyms"] = [name] * 11
        self.assertTrue(any("synonyms" in e for e in self.errors(record)))

        record = fx.record()
        record["partsUsed"] = [{"value": "Flor", "refs": ["wcvp:1"]}] * 6
        self.assertTrue(any("partsUsed" in e for e in self.errors(record)))

        record = fx.record()
        record["traditionalUses"] = [record["traditionalUses"][0]] * 21
        self.assertTrue(any("traditionalUses" in e for e in self.errors(record)))
        record["traditionalUses"] = record["traditionalUses"][:20]
        self.assertEqual(self.errors(record), [])

        record = fx.record()
        record["description"] = {"value": "x" * 400, "refs": ["wcvp:1"]}
        self.assertEqual(self.errors(record), [])
        record["description"]["value"] = "x" * 401
        self.assertTrue(any("description.value" in e for e in self.errors(record)))

    def test_review_flag_as_string_fails(self):
        record = fx.record()
        record["reviewFlags"] = ["grupo-partido"]
        self.assertTrue(any("reviewFlags[0]" in e for e in self.errors(record)))

    def test_review_flag_missing_parts_fail(self):
        for field in ("code", "target", "message"):
            record = fx.record()
            del record["reviewFlags"][0][field]
            self.assertTrue(any("'%s'" % field in e for e in self.errors(record)), field)

    def test_goal_and_subarea_ids_are_closed_sets(self):
        record = fx.record()
        record["goals"][0]["goal"] = "concentracion"
        self.assertTrue(any("goals[0].goal" in e for e in self.errors(record)))
        record = fx.record()
        record["goals"][0]["subarea"] = "inventada"
        self.assertTrue(any("goals[0].subarea" in e for e in self.errors(record)))

    def test_goal_requires_subarea_and_pending_review_fields(self):
        for field in ("subarea", "pendingReview"):
            record = fx.record()
            del record["goals"][0][field]
            self.assertTrue(any("'%s'" % field in e for e in self.errors(record)), field)

    def test_traditional_use_requires_pending_review(self):
        record = fx.record()
        del record["traditionalUses"][0]["pendingReview"]
        self.assertTrue(any("'pendingReview'" in e for e in self.errors(record)))

    def test_safety_level_and_oil_type_are_closed(self):
        record = fx.record("hiperico")
        record["safety"]["level"] = "critico"
        self.assertTrue(any("safety.level" in e for e in self.errors(record)))
        record = fx.record()
        record["oil"] = {"type": "Fijo", "refs": ["wcvp:1"]}
        self.assertTrue(any("oil.type" in e for e in self.errors(record)))

    def test_refs_must_have_the_ref_format_and_entries_dataset_label_license(self):
        record = fx.record()
        record["scientificName"]["refs"] = ["sinformato"]
        self.assertTrue(any("scientificName.refs" in e for e in self.errors(record)))
        record = fx.record()
        del record["refs"]["wcvp:1"]["license"]
        self.assertTrue(any("'license'" in e for e in self.errors(record)))

    def test_schema_goal_ids_match_the_seed_catalog(self):
        from catalog_seed import goals
        catalog = goals.load_goals_catalog()
        props = self.schema["properties"]["goals"]["items"]["properties"]
        self.assertEqual(props["goal"]["enum"], goals.goal_ids(catalog))
        self.assertEqual(props["subarea"]["enum"], goals.subarea_ids(catalog) + [None])


if __name__ == "__main__":
    unittest.main()
