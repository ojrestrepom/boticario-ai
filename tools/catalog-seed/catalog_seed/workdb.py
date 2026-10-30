"""Formato intermedio de las extracciones: un SQLite (data/work/sources.db) con una tabla de filas con procedencia.

source_row(source, record_type, row_key, raw_name_cell, fnfnum, qid, content_json):
- source: la fuente de sources.json (usda, ema_json, ema_pdf, tppt, efsa, y más adelante wikidata...).
- record_type y row_key identifican la fila dentro de la fuente; el ref de un dato es <record_type>:<row_key>.
- raw_name_cell: la celda del nombre científico tal cual viene de la fuente, sin normalizar (el resolvedor la normaliza).
- fnfnum: identificador de planta de USDA cuando la fila ya lo trae; qid: reservado para Wikidata. Pueden ser nulos.
- content_json: JSON canónico (claves ordenadas, sin escapar) con el contenido normalizado de la fila.
extraction(source, version, rows, inputs_json): qué insumos produjeron las filas de cada fuente.
Extraer una fuente reemplaza todas sus filas, así que repetir el comando da el mismo resultado.
"""
import json
import sqlite3
from pathlib import Path

from .sources import REPO_ROOT

DEFAULT_WORK_DIR = REPO_ROOT / "data" / "work"
DEFAULT_DB = DEFAULT_WORK_DIR / "sources.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_row (
  source TEXT NOT NULL,
  record_type TEXT NOT NULL,
  row_key TEXT NOT NULL,
  raw_name_cell TEXT,
  fnfnum TEXT,
  qid TEXT,
  content_json TEXT NOT NULL,
  PRIMARY KEY (source, record_type, row_key)
);
CREATE INDEX IF NOT EXISTS source_row_fnfnum ON source_row (fnfnum);
CREATE INDEX IF NOT EXISTS source_row_name ON source_row (source, record_type, raw_name_cell);
CREATE TABLE IF NOT EXISTS extraction (
  source TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  rows INTEGER NOT NULL,
  inputs_json TEXT NOT NULL
);
"""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class Row:
    """Una fila normalizada con procedencia."""

    __slots__ = ("record_type", "row_key", "raw_name_cell", "fnfnum", "qid", "content")

    def __init__(self, record_type, row_key, content, raw_name_cell=None, fnfnum=None, qid=None):
        self.record_type = record_type
        self.row_key = str(row_key)
        self.raw_name_cell = raw_name_cell
        self.fnfnum = fnfnum
        self.qid = qid
        self.content = content


def open_db(path=DEFAULT_DB):
    path = Path(path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.executescript(SCHEMA)
    return connection


def replace_source(connection, source, rows, version, inputs):
    """Reemplaza en una transacción todas las filas de la fuente. Devuelve el número de filas."""
    with connection:
        connection.execute("DELETE FROM source_row WHERE source = ?", (source,))
        count = 0
        for row in rows:
            connection.execute(
                "INSERT INTO source_row (source, record_type, row_key, raw_name_cell, fnfnum, qid, content_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source, row.record_type, row.row_key, row.raw_name_cell, row.fnfnum, row.qid, canonical(row.content)))
            count += 1
        connection.execute("INSERT OR REPLACE INTO extraction (source, version, rows, inputs_json) VALUES (?, ?, ?, ?)",
                           (source, version, count, canonical(inputs)))
    return count


def counts(connection, source=None):
    """{record_type: filas} de una fuente (o de todas, con la clave 'fuente/tipo')."""
    if source:
        query = connection.execute("SELECT record_type, COUNT(*) FROM source_row WHERE source = ? GROUP BY record_type ORDER BY record_type", (source,))
        return dict(query.fetchall())
    query = connection.execute("SELECT source || '/' || record_type, COUNT(*) FROM source_row GROUP BY 1 ORDER BY 1")
    return dict(query.fetchall())


def fetch_rows(connection, source, record_type, row_key=None, name_like=None):
    """Filas como dicts (row_key, raw_name_cell, fnfnum, content) de un tipo, por clave o por texto del nombre."""
    sql = "SELECT row_key, raw_name_cell, fnfnum, qid, content_json FROM source_row WHERE source = ? AND record_type = ?"
    args = [source, record_type]
    if row_key is not None:
        sql += " AND row_key = ?"
        args.append(row_key)
    if name_like is not None:
        sql += " AND raw_name_cell LIKE ?"
        args.append(name_like)
    sql += " ORDER BY rowid"
    return [{"row_key": k, "raw_name_cell": n, "fnfnum": f, "qid": q, "content": json.loads(c)}
            for k, n, f, q, c in connection.execute(sql, args)]
