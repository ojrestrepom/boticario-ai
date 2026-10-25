import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import fixtures_support as fx
import support  # noqa: F401

from catalog_seed import goals
from catalog_seed.cli import main
from catalog_seed.schema import load_schema
from catalog_seed.validate import image_license_kind, load_flag_codes, toxic_categories, validate_directory, validate_record


class ValidatorCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls.goals_map = goals.load_goals_map()
        cls.catalog = goals.load_goals_catalog()

    def run_validator(self, record, bundle=None):
        return validate_record(record, bundle if bundle is not None else fx.bundle(), self.schema, self.goals_map, self.catalog)

    def assertError(self, record, text, bundle=None):
        errors, _ = self.run_validator(record, bundle)
        self.assertTrue(any(text in e for e in errors), "no hay error con %r en %s" % (text, errors))

    def assertNoErrors(self, record, bundle=None):
        errors, _ = self.run_validator(record, bundle)
        self.assertEqual(errors, [])


class ScenarioTests(ValidatorCase):
    def test_valid_records_pass(self):
        self.assertNoErrors(fx.record())
        self.assertNoErrors(fx.record("hiperico"), fx.bundle("hiperico"))

    def test_schema_error_stops_the_other_checks(self):
        record = fx.record()
        record["reviewFlags"] = ["texto suelto"]
        errors, _ = self.run_validator(record)
        self.assertTrue(errors and all(e.startswith("esquema:") for e in errors))

    # Escenarios de «Validador automático».
    def test_ref_inexistente(self):
        record = fx.record()
        record["scientificName"]["refs"] = ["wcvp:999"]
        self.assertError(record, "wcvp:999")
        errors, _ = self.run_validator(record)
        self.assertTrue(any("matricaria-chamomilla" in e for e in errors))  # nombra la planta

    def test_ref_de_cita_inexistente(self):
        record = fx.record()
        record["traditionalUses"][0]["citations"][0]["ref"] = "usda_reference:NOEXISTE"
        self.assertError(record, "usda_reference:NOEXISTE")

    def test_ref_fuera_del_subconjunto_refs_del_registro(self):
        record = fx.record()
        del record["refs"]["wcvp:1"]
        self.assertError(record, "no está en refs del registro")

    def test_ref_del_registro_distinto_del_paquete(self):
        record = fx.record()
        record["refs"]["wcvp:1"]["license"] = "otra"
        self.assertError(record, "distintos de los del paquete")

    def test_objetivo_sin_respaldo(self):
        record = fx.record()
        record["goals"].append({"goal": "mejorar-el-sueno", "subarea": None, "area": "Trastornos del sueño e insomnio pasajero",
                                "evidence": "x", "pendingReview": False, "refs": ["ema_herbal:matricariae-flos"]})
        self.assertError(record, "sin respaldo de la EMA")

    def test_objetivo_con_subarea_equivocada_no_tiene_respaldo(self):
        record = fx.record()
        record["goals"][0]["subarea"] = "circulacion"
        self.assertError(record, "sin respaldo de la EMA")

    def test_declaracion_publica_no_respalda_objetivos(self):
        bundle = fx.bundle()
        bundle["sections"]["regulatory"][0]["outcome"] = "Public statement"
        self.assertError(fx.record(), "sin respaldo de la EMA", bundle)

    def test_producto_combinado_no_respalda_objetivos(self):
        bundle = fx.bundle()
        bundle["sections"]["regulatory"][0]["combination"] = "Yes"
        self.assertError(fx.record(), "sin respaldo de la EMA", bundle)

    def test_resultado_combinado_o_entrada_de_lista_si_respalda(self):
        for outcome in ("European Union list entry", "European Union herbal monograph;European Union list entry"):
            bundle = fx.bundle()
            bundle["sections"]["regulatory"][0]["outcome"] = outcome
            self.assertNoErrors(fx.record(), bundle)

    def test_objetivo_respaldado_por_un_ref_que_no_es_de_la_ema_falla(self):
        record = fx.record()
        record["goals"][0]["refs"] = ["wcvp:1"]
        self.assertError(record, "sin respaldo de la EMA")

    def test_objetivo_pendiente_sin_flag(self):
        record = fx.record("hiperico")
        record["reviewFlags"] = []
        self.assertError(record, "pendingReview sin un reviewFlag", fx.bundle("hiperico"))

    def test_flag_con_otro_target_no_cuenta(self):
        record = fx.record("hiperico")
        record["reviewFlags"][0]["target"] = "goals.mejorar-el-sueno"
        self.assertError(record, "pendingReview sin un reviewFlag", fx.bundle("hiperico"))

    def test_palabra_de_dosis_es_advertencia(self):
        record = fx.record()
        record["goals"][0]["evidence"] = "Cura la gastritis con una dosis de 3 mg."
        errors, warnings = self.run_validator(record)
        self.assertEqual(errors, [])
        found = " | ".join(warnings)
        self.assertIn("goals[0].evidence", found)
        for word in ("Cura", "dosis", "mg"):
            self.assertIn("'%s'" % word, found)

    def test_texto_sin_dosis_no_da_advertencias(self):
        _, warnings = self.run_validator(fx.record())
        self.assertEqual(warnings, [])

    def test_codigo_de_flag_fuera_del_catalogo_es_advertencia(self):
        record = fx.record()
        record["reviewFlags"].append({"code": "nombre-comun-ausente", "target": "displayName", "message": "Sin nombre."})
        errors, warnings = self.run_validator(record)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("'nombre-comun-ausente' no está en el catálogo", warnings[0])

    def test_catalogo_de_codigos_y_prompt_coinciden(self):
        codes = load_flag_codes()
        self.assertIn("sin-nombre-comun-es", codes)
        prompt = (Path(__file__).resolve().parent.parent / "prompt" / "consolidate.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"^\| `([a-z-]+)` \|", prompt, re.MULTILINE))
        self.assertEqual(listed, codes)

    def test_grupo_pendiente_sin_flag(self):
        record = fx.record()
        record["reviewFlags"] = [f for f in record["reviewFlags"] if f["target"] != "traditionalUses[1]"]
        self.assertError(record, "pendingReview sin un reviewFlag cuyo target sea 'traditionalUses[1]'")

    def test_cita_sin_resolver_sin_grupo_pendiente(self):
        record = fx.record()
        record["traditionalUses"][1]["pendingReview"] = False
        self.assertError(record, "pendingReview falso")

    def test_grupo_con_una_cita_resuelta_y_otra_sin_resolver_se_muestra_con_su_flag(self):
        record = fx.record()
        group = record["traditionalUses"][0]
        group["citations"].append({"key": "Woi.Syria", "ref": None, "text": "Woi.Syria (sin resolver)"})
        record["reviewFlags"].append({"code": "cita-sin-resolver", "target": "traditionalUses[0]",
                                      "message": "La clave Woi.Syria no tiene una candidata correspondiente en el paquete."})
        self.assertFalse(group["pendingReview"])
        self.assertNoErrors(record)
        # Sin su flag, el grupo visible con una clave sin resolver no es válido.
        record["reviewFlags"].pop()
        self.assertError(record, "falta el reviewFlag 'cita-sin-resolver' con target 'traditionalUses[0]'")

    def test_grupo_con_una_cita_resuelta_no_puede_estar_pendiente(self):
        record = fx.record()
        record["traditionalUses"][0]["pendingReview"] = True
        record["reviewFlags"].append({"code": "cita-sin-resolver", "target": "traditionalUses[0]", "message": "x"})
        self.assertError(record, "al menos una cita resuelta y pendingReview verdadero")

    def test_grupo_sin_ninguna_cita_resuelta_queda_pendiente(self):
        record = fx.record()
        group = record["traditionalUses"][1]
        self.assertTrue(group["pendingReview"])
        self.assertTrue(all(c["ref"] is None for c in group["citations"]))
        self.assertNoErrors(record)
        group["pendingReview"] = False
        self.assertError(record, "ninguna cita está resuelta")

    def test_safety_con_nivel_nulo_y_texto_es_valido(self):
        record = fx.record()
        record["safety"] = {"level": None, "text": "La EMA registra contraindicaciones y advertencias en niños.",
                            "refs": ["ema_herbal:matricariae-flos"]}
        record["reviewFlags"] = [f for f in record["reviewFlags"] if f["code"] != "sin-datos-de-seguridad"]
        self.assertNoErrors(record)

    def test_safety_con_nivel_nulo_y_sin_texto_es_invalido(self):
        record = fx.record()
        record["safety"] = {"level": None, "text": "", "refs": ["ema_herbal:matricariae-flos"]}
        record["reviewFlags"] = [f for f in record["reviewFlags"] if f["code"] != "sin-datos-de-seguridad"]
        self.assertError(record, "safety.text")
        del record["safety"]["text"]
        self.assertError(record, "'text'")

    def test_safety_nula_exige_el_flag_y_el_nivel_nulo_no_contradice_al_paquete(self):
        record = fx.record()
        record["reviewFlags"] = [f for f in record["reviewFlags"] if f["code"] != "sin-datos-de-seguridad"]
        self.assertError(record, "falta el reviewFlag 'sin-datos-de-seguridad'")
        record = fx.record("hiperico")
        record["safety"]["level"] = None
        self.assertError(record, "safety.level: es nulo pero el paquete fija nivel", fx.bundle("hiperico"))

    def test_cita_sin_resolver_exige_flag_cita_sin_resolver(self):
        record = fx.record()
        record["reviewFlags"][0]["code"] = "otro-motivo"
        self.assertError(record, "falta el reviewFlag 'cita-sin-resolver'")

    def test_cita_sin_ref_requiere_la_marca(self):
        record = fx.record()
        record["traditionalUses"][1]["citations"][0]["text"] = "Woi.Syria"
        self.assertError(record, "sin la marca")

    def test_cita_inventada(self):
        record = fx.record()
        record["traditionalUses"][0]["citations"][0]["ref"] = "usda_reference:INVENTADA"
        record["refs"]["usda_reference:INVENTADA"] = {"dataset": "usda", "label": "x", "license": "CC0"}
        self.assertError(record, "usda_reference:INVENTADA")

    def test_cita_que_no_es_candidata_del_paquete(self):
        # El ref existe en el paquete (otra obra de USDA) pero no es candidata de esa clave.
        bundle = fx.bundle()
        record = fx.record()
        record["traditionalUses"][0]["citations"][0]["ref"] = "usda_reference:OTRA"
        record["refs"]["usda_reference:OTRA"] = bundle["refs"]["usda_reference:OTRA"]
        self.assertError(record, "no es una candidata del paquete", bundle)

    def test_cita_con_ref_que_no_es_usda_reference(self):
        record = fx.record()
        record["traditionalUses"][0]["citations"][0]["ref"] = "wcvp:1"
        self.assertError(record, "no es un usda_reference")

    def test_actividad_alterada(self):
        record = fx.record()
        record["traditionalUses"][0]["activitySource"] = "Sedative agent"
        self.assertError(record, "no es una actividad del paquete")

    # Otros controles del contrato.
    def test_id_y_bundle_hash_deben_coincidir(self):
        record = fx.record()
        record["id"] = "otra-planta"
        self.assertError(record, "distinto de identity.proposedId")
        record = fx.record()
        record["bundleHash"] = "sha256:" + "0" * 64
        self.assertError(record, "bundleHash")

    def test_hiperico_en_relajacion_estres_sin_pending_review(self):
        record = fx.record("hiperico")
        record["goals"][0]["pendingReview"] = False
        record["reviewFlags"] = []
        self.assertError(record, "interacciones graves", fx.bundle("hiperico"))

    def test_hiperico_con_pending_review_pero_sin_flag(self):
        record = fx.record("hiperico")
        record["reviewFlags"] = []
        errors, _ = self.run_validator(record, fx.bundle("hiperico"))
        self.assertEqual(len(errors), 1)
        self.assertIn("sin un reviewFlag", errors[0])

    def test_sin_interacciones_graves_el_objetivo_puede_no_estar_pendiente(self):
        bundle = fx.bundle("hiperico")
        bundle["sections"]["safety"] = []
        record = fx.record("hiperico")
        record["goals"][0]["pendingReview"] = False
        record["reviewFlags"] = []
        self.assertNoErrors(record, bundle)

    def test_planta_toxica_segun_tppt_sin_objetivos(self):
        for value in ("strong toxic", "very strong toxic", "weak toxic, strong toxic (horses)"):
            bundle = fx.bundle()
            bundle["sections"]["safety"] = [{"ref": "wcvp:1", "source": "tppt", "humanToxicity": value}]
            self.assertError(fx.record(), "planta tóxica según TPPT", bundle)
        bundle = fx.bundle()
        bundle["sections"]["safety"] = [{"ref": "wcvp:1", "source": "tppt", "humanToxicity": "weak toxic, toxic (horse)"}]
        self.assertNoErrors(fx.record(), bundle)

    def test_toxic_categories_split_by_comma_and_prefix_before_parenthesis(self):
        self.assertEqual(toxic_categories("very strong toxic (cat), weak toxic"), ["very strong toxic", "weak toxic"])
        self.assertEqual(toxic_categories(None), [])

    def test_planta_toxica_sin_objetivos_pasa(self):
        bundle = fx.bundle()
        bundle["sections"]["safety"] = [{"ref": "wcvp:1", "source": "tppt", "humanToxicity": "very strong toxic"}]
        record = fx.record()
        record["goals"] = []
        self.assertNoErrors(record, bundle)

    def test_imagen_con_licencia_aceptada(self):
        for license_text in ("CC0", "CC0 1.0", "Public domain", "CC BY 4.0", "CC BY-SA 4.0", "CC BY-SA 3.0"):
            self.assertIsNotNone(image_license_kind(license_text), license_text)

    def test_imagen_con_licencia_no_aceptada(self):
        for license_text in ("CC BY-NC 4.0", "CC BY-ND 4.0", "CC BY-NC-SA 4.0", "All rights reserved", "GFDL", ""):
            self.assertIsNone(image_license_kind(license_text), license_text)
        record = fx.record()
        record["image"]["license"] = "CC BY-NC 4.0"
        self.assertError(record, "licencia 'CC BY-NC 4.0' no aceptada")

    def test_imagen_cc_by_exige_atribucion(self):
        record = fx.record()
        record["image"]["attributionRequired"] = False
        self.assertError(record, "attributionRequired")

    def test_imagen_debe_ser_del_paquete(self):
        record = fx.record()
        record["image"]["refs"] = ["wcvp:1"]
        self.assertError(record, "ningún ref corresponde a una imagen del paquete")

    def test_ref_de_wikipedia_cc_by_sa_exige_url(self):
        bundle = fx.bundle()
        bundle["refs"]["wikipedia_es:Matricaria"] = {"dataset": "wikipedia_es", "label": "Wikipedia: Matricaria", "license": "CC BY-SA 4.0"}
        record = fx.record()
        record["description"] = {"value": "Planta herbácea.", "refs": ["wikipedia_es:Matricaria"]}
        record["refs"]["wikipedia_es:Matricaria"] = dict(bundle["refs"]["wikipedia_es:Matricaria"])
        self.assertError(record, "exige 'url'", bundle)
        url = "https://es.wikipedia.org/wiki/Matricaria"
        bundle["refs"]["wikipedia_es:Matricaria"]["url"] = url
        record["refs"]["wikipedia_es:Matricaria"]["url"] = url
        self.assertNoErrors(record, bundle)

    def test_subarea_solo_en_otros_objetivos(self):
        record = fx.record()
        record["goals"][1]["subarea"] = "digestion"
        self.assertError(record, "solo 'otros-objetivos' lleva subárea")
        record = fx.record()
        record["goals"][0]["subarea"] = None
        self.assertError(record, "exige subárea")


class DirectoryTests(ValidatorCase):
    def write(self, directory, name, data):
        with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)

    def make_dirs(self):
        root = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, root)
        records, bundles = os.path.join(root, "plants"), os.path.join(root, "bundles")
        os.makedirs(records)
        os.makedirs(bundles)
        self.write(bundles, "matricaria-recutita.json", fx.bundle())
        self.write(bundles, "hypericum-perforatum.json", fx.bundle("hiperico"))
        self.write(records, "matricaria-chamomilla.json", fx.record())
        self.write(records, "hypericum-perforatum.json", fx.record("hiperico"))
        return records, bundles

    def test_report_has_per_record_results_and_summary(self):
        records, bundles = self.make_dirs()
        report = validate_directory(records, bundles)
        self.assertEqual(report["summary"], {"records": 2, "recordsWithErrors": 0, "errors": 0, "warnings": 0})
        self.assertEqual(sorted(report["plants"]), ["hypericum-perforatum", "matricaria-chamomilla"])

    def test_file_name_must_match_id_and_missing_bundle_is_an_error(self):
        records, bundles = self.make_dirs()
        os.rename(os.path.join(records, "hypericum-perforatum.json"), os.path.join(records, "otro.json"))
        os.remove(os.path.join(bundles, "matricaria-recutita.json"))
        report = validate_directory(records, bundles)
        self.assertTrue(any("no se llama como el id" in e for e in report["plants"]["otro"]["errors"]))
        self.assertTrue(any("no hay paquete" in e for e in report["plants"]["matricaria-chamomilla"]["errors"]))
        self.assertEqual(report["summary"]["recordsWithErrors"], 2)

    def test_cli_exit_code_and_output(self):
        records, bundles = self.make_dirs()
        out = os.path.join(os.path.dirname(records), "report.json")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["validate", "--records", records, "--bundles", bundles, "--out", out]), 0)
        self.assertIn("2 registros, 0 con errores", stdout.getvalue())
        with open(out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["summary"]["errors"], 0)
        broken = fx.record()
        broken["scientificName"]["refs"] = ["wcvp:999"]
        self.write(records, "matricaria-chamomilla.json", broken)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["validate", "--records", records, "--bundles", bundles]), 1)
        self.assertIn("wcvp:999", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
