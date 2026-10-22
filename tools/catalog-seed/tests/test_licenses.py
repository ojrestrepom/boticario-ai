import unittest

import support  # noqa: F401
from wiki_support import commons_response

from catalog_seed import licenses


def meta(**fields):
    return {k: {"value": v} for k, v in fields.items()}


class LicenseTests(unittest.TestCase):
    def test_admitted_licenses(self):
        cases = {
            "cc-by-sa-4.0": ("CC BY-SA 4.0", "cc-by-sa", True), "cc-by-3.0": ("CC BY 3.0", "cc-by", True),
            "cc-by-2.0": ("CC BY 2.0", "cc-by", True), "cc-by-sa-2.5-es": ("CC BY-SA 2.5 es", "cc-by-sa", True),
            "cc0": ("CC0", "cc0", False), "pd": ("Public domain", "public-domain", False),
        }
        for code, (short, family, attribution) in cases.items():
            result = licenses.classify(meta(License=code, LicenseShortName=short, Artist="<a href='x'>Ana &amp; Luis</a>"))
            self.assertTrue(result["admitted"], code)
            self.assertEqual(result["licenseCode"], family, code)
            self.assertEqual(result["attributionRequired"], attribution, code)
            self.assertEqual(result["author"], "Ana & Luis")

    def test_license_url_is_built_when_commons_does_not_give_it(self):
        result = licenses.classify(meta(License="cc-by-sa-4.0", LicenseShortName="CC BY-SA 4.0", Artist="A"))
        self.assertEqual(result["licenseUrl"], "https://creativecommons.org/licenses/by-sa/4.0/")
        given = licenses.classify(meta(License="cc-by-3.0", LicenseUrl="https://creativecommons.org/licenses/by/3.0", Artist="A"))
        self.assertEqual(given["licenseUrl"], "https://creativecommons.org/licenses/by/3.0")

    def test_public_domain_variants(self):
        for short in ("PD-old-70", "Public domain", "PD-US-expired"):
            self.assertTrue(licenses.classify(meta(LicenseShortName=short))["admitted"], short)

    def test_discarded_licenses_with_reason(self):
        cases = [
            (dict(License="cc-by-nc-2.0", LicenseShortName="CC BY-NC 2.0"), licenses.NON_COMMERCIAL),
            (dict(License="cc-by-nc-sa-3.0", LicenseShortName="CC BY-NC-SA 3.0"), licenses.NON_COMMERCIAL),
            (dict(License="cc-by-nd-2.0", LicenseShortName="CC BY-ND 2.0"), licenses.NO_DERIVATIVES),
            (dict(License="gfdl", LicenseShortName="GFDL"), licenses.GFDL),
            (dict(LicenseShortName="FAL"), licenses.OTHER),
            (dict(), licenses.UNKNOWN),
        ]
        for fields, reason in cases:
            result = licenses.classify(meta(Artist="Alguien", **fields))
            self.assertFalse(result["admitted"], fields)
            self.assertEqual(result["reason"], reason, fields)

    def test_gfdl_dual_licensed_with_cc_by_sa_is_admitted(self):
        result = licenses.classify(meta(License="cc-by-sa-3.0", LicenseShortName="CC BY-SA 3.0, GFDL", Artist="A"))
        self.assertTrue(result["admitted"])

    def test_attribution_required_without_author_is_discarded(self):
        result = licenses.classify(meta(License="cc-by-3.0", LicenseShortName="CC BY 3.0"))
        self.assertFalse(result["admitted"])
        self.assertEqual(result["reason"], licenses.NO_AUTHOR)
        self.assertTrue(licenses.classify(meta(License="cc-by-3.0", Credit="<span>Own work</span>"))["admitted"])
        self.assertTrue(licenses.classify(meta(License="cc0", LicenseShortName="CC0"))["admitted"])

    def test_record_from_the_cache_shape(self):
        record = commons_response("File:A.jpg", License="cc-by-sa-4.0", LicenseShortName="CC BY-SA 4.0", Artist="Ana")
        self.assertTrue(licenses.classify(record["imageinfo"]["extmetadata"])["admitted"])

    def test_clean_file_url_drops_utm_parameters_only(self):
        base = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Lavanda.jpg"
        self.assertEqual(licenses.clean_file_url(base + "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original"), base)
        self.assertEqual(licenses.clean_file_url(base + "?x=1&utm_source=a"), base + "?x=1")
        self.assertEqual(licenses.clean_file_url(base), base)
        self.assertIsNone(licenses.clean_file_url(None))


if __name__ == "__main__":
    unittest.main()
