import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import fixtures_support as fx
import support

from catalog_seed import goals, seed
from catalog_seed.cli import main
from catalog_seed.schema import DEFAULT_RECORD_SCHEMA, load_schema
from catalog_seed.seed import DEFAULT_PROMPT, compute_plan, read_prompt_version
from catalog_seed.sources import SourceError


def dump(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


class SeedCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.bundles = os.path.join(self.root, "bundles")
        self.seed_dir = os.path.join(self.root, "seed")
        os.makedirs(self.bundles)
        os.makedirs(os.path.join(self.seed_dir, "plants"))
        self.prompt = os.path.join(self.root, "consolidate.md")
        self.set_prompt_version(1)
        self.sources = os.path.join(self.root, "sources.json")
        self.write_sources()
        dump(os.path.join(self.bundles, "matricaria-recutita.json"), fx.bundle())
        dump(os.path.join(self.bundles, "hypericum-perforatum.json"), fx.bundle("hiperico"))
        dump(os.path.join(self.seed_dir, "plants", "matricaria-chamomilla.json"), fx.record())
        dump(os.path.join(self.seed_dir, "plants", "hypericum-perforatum.json"), fx.record("hiperico"))
        shutil.copy(goals.DEFAULT_GOALS_CATALOG, os.path.join(self.seed_dir, "goals.json"))

    def set_prompt_version(self, version):
        with open(self.prompt, "w", encoding="utf-8") as handle:
            handle.write("# Prompt\n\nprompt-version: %d\n\nTexto.\n" % version)

    def write_sources(self, **overrides):
        usda = support.make_source(**overrides)
        off = support.make_source(id="wikipedia_es", enabled=False, license="CC BY-SA 4.0")
        dump(self.sources, {"sources": [usda.data, off.data]})

    def plan(self, record_version=1):
        return compute_plan(self.bundles, self.seed_dir, read_prompt_version(self.prompt), record_version)

    def seal(self):
        return seed.seal(self.seed_dir, self.sources, prompt_path=self.prompt)

    def read_manifest(self):
        with open(os.path.join(self.seed_dir, "manifest.json"), encoding="utf-8") as handle:
            return json.load(handle)


class PromptTests(unittest.TestCase):
    def test_real_prompt_declares_its_version(self):
        self.assertEqual(read_prompt_version(DEFAULT_PROMPT), 1)
        with open(DEFAULT_PROMPT, encoding="utf-8") as handle:
            self.assertRegex(handle.read(), r"(?m)^prompt-version: 1$")

    def test_prompt_without_version_fails(self):
        path = os.path.join(tempfile.mkdtemp(), "p.md")
        with open(path, "w") as handle:
            handle.write("sin versión\n")
        self.addCleanup(shutil.rmtree, os.path.dirname(path))
        with self.assertRaises(SourceError):
            read_prompt_version(path)

    def test_prompt_mentions_the_pilot_corrections(self):
        with open(DEFAULT_PROMPT, encoding="utf-8") as handle:
            text = handle.read()
        for needle in ("(sin resolver)", "cita-sin-resolver", "traditionalUses[<índice>]", "Woi.10", "Eb24: 441", "Citrus × bergamia",
                       "`EO`", "ricino", "very strong toxic", "interacciones-graves-estres", "`und`", "`;`"):
            self.assertIn(needle, text)


class PlanTests(SeedCase):
    def test_sin_cambios_el_plan_esta_vacio(self):
        self.assertEqual(self.plan(), [])

    def test_cambia_el_prompt_todas_pendientes(self):
        self.set_prompt_version(2)
        plan = self.plan()
        self.assertEqual([p["id"] for p in plan], ["hypericum-perforatum", "matricaria-chamomilla"])
        self.assertTrue(all(p["reasons"] == ["promptVersion"] for p in plan))

    def test_cambia_una_fuente_solo_esa_planta(self):
        path = os.path.join(self.bundles, "hypericum-perforatum.json")
        bundle = fx.bundle("hiperico")
        bundle["bundleHash"] = "sha256:" + "c3" * 32
        dump(path, bundle)
        plan = self.plan()
        self.assertEqual(plan, [{"id": "hypericum-perforatum", "plantKey": "hypericum-perforatum", "reasons": ["bundleHash"]}])

    def test_planta_sin_registro(self):
        os.remove(os.path.join(self.seed_dir, "plants", "matricaria-chamomilla.json"))
        self.assertEqual([(p["id"], p["reasons"]) for p in self.plan()], [("matricaria-chamomilla", ["sin-registro"])])

    def test_cambia_el_esquema(self):
        self.assertEqual(len(self.plan(record_version=2)), 2)
        self.assertEqual(self.plan(record_version=2)[0]["reasons"], ["recordVersion"])

    def test_motivos_se_acumulan(self):
        self.set_prompt_version(3)
        bundle = fx.bundle()
        bundle["bundleHash"] = "sha256:" + "d4" * 32
        dump(os.path.join(self.bundles, "matricaria-recutita.json"), bundle)
        by_id = {p["id"]: p["reasons"] for p in self.plan()}
        self.assertEqual(by_id["matricaria-chamomilla"], ["bundleHash", "promptVersion"])

    def test_cli_plan(self):
        args = ["plan", "--bundles", self.bundles, "--seed", self.seed_dir, "--prompt", self.prompt]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(args), 0)
        self.assertIn("0 plantas a regenerar", out.getvalue())
        self.set_prompt_version(2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(args + ["--json"])
        self.assertEqual(len(json.loads(out.getvalue())), 2)


class SealTests(SeedCase):
    def test_manifest_contents(self):
        manifest, changed = self.seal()
        self.assertTrue(changed)
        self.assertEqual(self.read_manifest(), manifest)
        self.assertEqual(manifest["formatVersion"], 1)
        self.assertEqual(manifest["plantCount"], 2)
        self.assertEqual(manifest["promptVersion"], 1)
        self.assertEqual(manifest["recordVersion"], 1)
        self.assertEqual(manifest["models"], ["modelo-de-prueba"])
        self.assertEqual(manifest["reviewFlags"], {"cita-sin-resolver": 1, "interacciones-graves-estres": 1, "sin-datos-de-seguridad": 1})
        self.assertRegex(manifest["seedHash"], r"^sha256:[0-9a-f]{64}$")
        (source,) = manifest["sources"]  # la desactivada no figura
        self.assertEqual(source["id"], "usda")
        self.assertEqual(source["files"][0]["checksum"]["algorithm"], "md5")
        self.assertTrue(source["version"] and source["license"] and source["attribution"])

    def test_determinista_y_sin_cambios(self):
        self.seal()
        with open(os.path.join(self.seed_dir, "manifest.json"), "rb") as handle:
            first = handle.read()
        _, changed = self.seal()
        self.assertFalse(changed)
        with open(os.path.join(self.seed_dir, "manifest.json"), "rb") as handle:
            self.assertEqual(handle.read(), first)
        self.assertTrue(first.endswith(b"\n"))

    def test_seed_hash_no_depende_del_formato_de_los_archivos(self):
        before, _ = self.seal()
        path = os.path.join(self.seed_dir, "plants", "hypericum-perforatum.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)  # sin sangría ni orden
        after, _ = self.seal()
        self.assertEqual(before["seedHash"], after["seedHash"])

    def test_seed_hash_cambia_con_un_registro_o_con_goals(self):
        base, _ = self.seal()
        path = os.path.join(self.seed_dir, "plants", "hypericum-perforatum.json")
        record = fx.record("hiperico")
        record["origin"] = {"value": "Europa", "refs": ["wcvp:2"]}
        dump(path, record)
        changed, _ = self.seal()
        self.assertNotEqual(base["seedHash"], changed["seedHash"])
        dump(path, fx.record("hiperico"))
        self.assertEqual(self.seal()[0]["seedHash"], base["seedHash"])
        catalog_path = os.path.join(self.seed_dir, "goals.json")
        catalog = goals.load_goals_catalog(catalog_path)
        catalog["goals"][0]["label"] = "Otra etiqueta"
        dump(catalog_path, catalog)
        self.assertNotEqual(self.seal()[0]["seedHash"], base["seedHash"])

    def test_cambia_el_prompt_el_sellado_exige_regenerar(self):
        self.set_prompt_version(2)
        with self.assertRaises(SourceError) as caught:
            self.seal()
        self.assertIn("promptVersion", str(caught.exception))

    def test_cambia_una_fuente_el_manifiesto_refleja_la_nueva_version(self):
        before, _ = self.seal()
        self.write_sources(version="v2", size=10, checksum={"algorithm": "sha256", "value": "ab" * 32})
        after, changed = self.seal()
        self.assertTrue(changed)
        self.assertEqual(after["sources"][0]["version"], "v2")
        self.assertEqual(after["sources"][0]["files"][0]["checksum"]["value"], "ab" * 32)
        self.assertEqual(before["seedHash"], after["seedHash"])  # los registros no cambiaron

    def test_fuente_desactivada_deja_de_listarse(self):
        dump(self.sources, {"sources": [support.make_source(enabled=False).data]})
        manifest, _ = self.seal()
        self.assertEqual(manifest["sources"], [])

    def test_fuente_activa_sin_fijar_falla(self):
        self.write_sources(size=None, checksum=None)
        with self.assertRaises(SourceError):
            self.seal()

    def test_archivo_con_otro_id_falla(self):
        os.rename(os.path.join(self.seed_dir, "plants", "hypericum-perforatum.json"), os.path.join(self.seed_dir, "plants", "otro.json"))
        with self.assertRaises(SourceError) as caught:
            self.seal()
        self.assertIn("otro.json", str(caught.exception))

    def test_registro_invalido_falla(self):
        record = fx.record()
        record["reviewFlags"] = ["suelto"]
        dump(os.path.join(self.seed_dir, "plants", "matricaria-chamomilla.json"), record)
        with self.assertRaises(SourceError):
            self.seal()

    def test_cli_seal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--sources", self.sources, "seal", "--seed", self.seed_dir, "--prompt", self.prompt]), 0)
        self.assertIn("actualizado: 2 plantas", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["--sources", self.sources, "seal", "--seed", self.seed_dir, "--prompt", self.prompt])
        self.assertIn("sin cambios", out.getvalue())

    def test_cli_seal_error_returns_1(self):
        self.set_prompt_version(9)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main(["--sources", self.sources, "seal", "--seed", self.seed_dir, "--prompt", self.prompt]), 1)
        self.assertIn("promptVersion", err.getvalue())

    def test_schema_version_is_declared(self):
        self.assertEqual(seed.schema_version(load_schema(DEFAULT_RECORD_SCHEMA)), 1)


if __name__ == "__main__":
    unittest.main()
