import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import support  # noqa: F401  (prepara sys.path)
from support import PAYLOAD, make_source

from catalog_seed import cli
from catalog_seed.download import download_source, require_verified
from catalog_seed.sources import SourceError


def no_network(*args, **kwargs):
    raise AssertionError("se intentó abrir la red")


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = self.tmp.name

    def place(self, source, payload):
        path = source.cache_path(self.cache)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def block_network(self):
        for target in ("urllib.request.urlopen", "socket.socket.connect", "socket.create_connection"):
            patcher = mock.patch(target, side_effect=no_network)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_intact_input_is_used_without_network(self):
        source = make_source()
        path = self.place(source, PAYLOAD)
        self.block_network()
        self.assertEqual(require_verified(source, self.cache), path)
        self.assertEqual(download_source(source, self.cache), ("cached", path))

    def test_altered_input_fails_naming_source_and_download_step(self):
        source = make_source()
        self.place(source, PAYLOAD.replace(b"prueba", b"PRUEBA"))
        self.block_network()
        with self.assertRaises(SourceError) as ctx:
            require_verified(source, self.cache)
        message = str(ctx.exception)
        self.assertIn("usda", message)
        self.assertIn("alterado", message)
        self.assertIn("download", message)
        with self.assertRaises(SourceError):
            download_source(source, self.cache)

    def test_missing_input_fails_indicating_download_without_network(self):
        source = make_source()
        self.block_network()
        with self.assertRaises(SourceError) as ctx:
            require_verified(source, self.cache)
        self.assertIn("usda", str(ctx.exception))
        self.assertIn("download --source usda", str(ctx.exception))

    def test_cli_offline_missing_fails_without_network(self):
        self.block_network()
        sources_file = os.path.join(self.tmp.name, "sources.json")
        source = make_source()
        with open(sources_file, "w") as handle:
            json.dump({"sources": [source.data]}, handle)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = cli.main(["--sources", sources_file, "--cache-dir", self.cache, "download", "--offline"])
        self.assertEqual(code, 1)
        self.assertIn("download", err.getvalue())

    def test_download_stores_verified_file(self):
        source = make_source()
        calls = []

        def fake_fetch(url, destination):
            calls.append(url)
            with open(destination, "wb") as handle:
                handle.write(PAYLOAD)

        status, path = download_source(source, self.cache, fetch=fake_fetch)
        self.assertEqual(status, "downloaded")
        self.assertEqual(path.read_bytes(), PAYLOAD)
        status, _ = download_source(source, self.cache, fetch=fake_fetch)
        self.assertEqual(status, "cached")
        self.assertEqual(len(calls), 1)

    def test_bad_download_is_not_kept(self):
        source = make_source()

        def bad_fetch(url, destination):
            with open(destination, "wb") as handle:
                handle.write(b"otra cosa")

        with self.assertRaises(SourceError):
            download_source(source, self.cache, fetch=bad_fetch)
        self.assertFalse(source.cache_path(self.cache).exists())
        self.assertEqual(os.listdir(source.cache_path(self.cache).parent), [])

    def test_disabled_source_is_not_downloaded(self):
        source = make_source(enabled=False)
        self.block_network()
        self.assertEqual(download_source(source, self.cache), ("disabled", None))
        self.assertFalse(source.cache_path(self.cache).exists())


if __name__ == "__main__":
    unittest.main()
