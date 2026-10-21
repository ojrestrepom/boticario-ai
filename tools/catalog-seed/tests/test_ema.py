import support  # noqa: F401

from catalog_seed.ema import dedupe_records


def row(url, **extra):
    base = {"latin_name": "X", "english_common_name": "X", "botanical_name": "Xus", "herbal_medicine_url": url}
    base.update(extra)
    return base


class EmaTests(__import__("unittest").TestCase):
    def test_exact_duplicates_collapse(self):
        records = dedupe_records({"data": [row("u1"), row("u1"), row("u2")]})
        self.assertEqual([r["herbal_medicine_url"] for r in records], ["u1", "u2"])
        self.assertEqual(len(records[0]["rows"]), 1)

    def test_distinct_rows_with_same_url_are_merged(self):
        a = row("h", english_common_name="St. John's Wort", botanical_name="Hypericum perforatumL.")
        b = row("h", english_common_name="Black Cohosh", botanical_name="Cimicifuga racemosa (L.) Nutt.")
        (record,) = dedupe_records({"data": [a, b, a]})
        self.assertEqual(record["english_common_name"], "St. John's Wort;Black Cohosh")
        self.assertEqual(record["botanical_name"], "Hypericum perforatumL.;Cimicifuga racemosa (L.) Nutt.")
        self.assertEqual(record["rows"], [a, b])


if __name__ == "__main__":
    __import__("unittest").main()
