"""Ayudas de las pruebas de extracción: rutas de fixtures, ZIP de USDA y SQLite de TPPT en memoria, y dependencias opcionales."""
import importlib.util
import io
import os
import sqlite3
import tempfile
import unittest
import zipfile

import support  # noqa: F401

EXTRACT_FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "extract")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE = os.path.join(REPO_ROOT, "data", ".cache")


def fixture(name):
    return os.path.join(EXTRACT_FIXTURES, name)


def has_module(name):
    return importlib.util.find_spec(name) is not None


def require_module(testcase, name, package=None):
    if not has_module(name):
        testcase.skipTest("falta %s: use tools/catalog-seed/.venv (véase requirements.txt)" % (package or name))


def require_real(testcase, *relative):
    path = os.path.join(CACHE, *relative)
    if not os.path.isfile(path):
        testcase.skipTest("falta %s en la caché: ejecute los pasos de descarga" % os.path.join("data/.cache", *relative))
    return path


def csv_text(header, rows):
    def cell(value):
        value = str(value)
        return '"%s"' % value.replace('"', '""') if any(c in value for c in ',"\n') else value
    lines = [",".join(header)] + [",".join(cell(v) for v in row) for row in rows]
    return "\r\n".join(lines) + "\r\n"


def make_usda_zip(path, tables):
    """tables: {nombre: (cabecera, filas)}; los CSV se escriben en Windows-1252."""
    with zipfile.ZipFile(path, "w") as archive:
        for name, (header, rows) in tables.items():
            archive.writestr(name + ".csv", csv_text(header, rows).encode("cp1252"))


def make_tppt_zip(path, statements):
    """Crea un SQLite con las sentencias dadas y lo guarda como tppt-db.db dentro de un ZIP."""
    with tempfile.TemporaryDirectory() as directory:
        db_path = os.path.join(directory, "tppt-db.db")
        connection = sqlite3.connect(db_path)
        for statement, args in statements:
            connection.execute(statement, args)
        connection.commit()
        connection.close()
        with zipfile.ZipFile(path, "w") as archive:
            archive.write(db_path, "tppt-db.db")


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name
