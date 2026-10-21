"""Índice SQLite de WCVP y WFO: carga por lotes y acceso de solo lectura (`Backbone`)."""
import csv
import io
import os
import sqlite3
import time
import zipfile

from .names import make_keys, rank_from_column, valid_epithet

INDEX_VERSION = 1

# Rangos de WFO que no son nombres de especie o inferiores: no entran al índice.
_WFO_HIGHER_RANKS = frozenset((
    "genus", "family", "order", "class", "phylum", "kingdom", "subgenus", "section", "subsection", "series", "subseries",
    "tribe", "subtribe", "supertribe", "subfamily", "suborder", "subclass", "superorder", "subkingdom",
))

_SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE wcvp_name(plant_name_id INTEGER PRIMARY KEY, ipni_id TEXT, taxon_rank TEXT, taxon_status TEXT, family TEXT,
  genus TEXT, species TEXT, infra_rank TEXT, infra_epithet TEXT, taxon_name TEXT, taxon_authors TEXT, accepted_id INTEGER,
  basionym_id INTEGER, homotypic TEXT, parent_id INTEGER, powo_id TEXT, is_hybrid INTEGER, key_full TEXT, key_binomial TEXT);
CREATE TABLE wcvp_distribution(plant_name_id INTEGER, continent TEXT, region TEXT, area_code_l3 TEXT, area TEXT,
  introduced INTEGER, extinct INTEGER, location_doubtful INTEGER);
CREATE TABLE wfo_name(taxon_id TEXT PRIMARY KEY, scientific_name_id TEXT, scientific_name TEXT, taxon_rank TEXT,
  authorship TEXT, family TEXT, genus TEXT, species TEXT, infra_rank TEXT, infra_epithet TEXT, nomenclatural_status TEXT,
  taxon_status TEXT, accepted_id TEXT, original_id TEXT, is_hybrid INTEGER, key_full TEXT, key_binomial TEXT);
"""
_INDEXES = """
CREATE INDEX ix_wcvp_key_full ON wcvp_name(key_full);
CREATE INDEX ix_wcvp_key_bin ON wcvp_name(key_binomial);
CREATE INDEX ix_wcvp_acc ON wcvp_name(accepted_id);
CREATE INDEX ix_wcvp_dist ON wcvp_distribution(plant_name_id);
CREATE INDEX ix_wfo_key_full ON wfo_name(key_full);
CREATE INDEX ix_wfo_key_bin ON wfo_name(key_binomial);
CREATE INDEX ix_wfo_acc ON wfo_name(accepted_id);
"""

# status -> clase: 1 aceptado, 2 sinónimo, 3 ilegítimo/inválido/ortográfico, 4 mal aplicado, 5 sin aceptado utilizable.
STATUS_CLASS = {
    "wcvp": {"Accepted": 1, "Artificial Hybrid": 1, "Synonym": 2, "Illegitimate": 3, "Invalid": 3, "Orthographic": 3,
             "Misapplied": 4, "Unplaced": 5, "Local Biotype": 5},
    "wfo": {"Accepted": 1, "Synonym": 2, "Unchecked": 5},
}


def _open_text(spec):
    """Abre un CSV como texto UTF-8 tolerante. `spec` es una ruta o una tupla (zip, miembro)."""
    if isinstance(spec, (tuple, list)):
        archive = zipfile.ZipFile(spec[0])
        return io.TextIOWrapper(archive.open(spec[1]), encoding="utf-8", errors="replace", newline="")
    return open(spec, encoding="utf-8", errors="replace", newline="")


def _toint(value):
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def _flush(db, table, rows, width):
    if rows:
        db.executemany("INSERT OR REPLACE INTO %s VALUES (%s)" % (table, ",".join("?" * width)), rows)


def _load_wcvp(db, spec, stats):
    started = time.time()
    read = skipped = 0
    reasons = {}
    batch = []
    with _open_text(spec) as handle:
        for row in csv.DictReader(handle, delimiter="|", quoting=csv.QUOTE_NONE):
            read += 1
            genus, species = row["genus"].strip(), row["species"].strip()
            infra = row["infraspecies"].strip()
            reason = None
            if row["taxon_rank"] == "Genus" or not genus or not species:
                reason = "genus_or_incomplete"
            elif not species[0].islower() or any(ch.isspace() for ch in species):
                reason = "invalid_species_epithet"
            elif infra and not valid_epithet(infra):
                reason = "invalid_infraspecific_epithet"
            if reason:
                skipped += 1
                reasons[reason] = reasons.get(reason, 0) + 1
                continue
            rank = rank_from_column(row["infraspecific_rank"]) if infra else ""
            if infra and not rank and row["infraspecific_rank"]:
                rank = row["infraspecific_rank"].strip().lower()
            key_full, key_bin = make_keys(genus, species, rank, infra)
            hybrid = 1 if (row["genus_hybrid"] or row["species_hybrid"]) else 0
            accepted = _toint(row["accepted_plant_name_id"])
            if accepted is None and row["taxon_status"] in ("Accepted", "Artificial Hybrid"):
                accepted = int(row["plant_name_id"])
            batch.append((int(row["plant_name_id"]), row["ipni_id"], row["taxon_rank"], row["taxon_status"], row["family"],
                          genus, species, rank, infra, row["taxon_name"], row["taxon_authors"], accepted,
                          _toint(row["basionym_plant_name_id"]), row["homotypic_synonym"].strip(),
                          _toint(row["parent_plant_name_id"]), row["powo_id"], hybrid, key_full, key_bin))
            if len(batch) >= 50000:
                _flush(db, "wcvp_name", batch, 19)
                batch = []
    _flush(db, "wcvp_name", batch, 19)
    db.commit()
    stats["wcvp_names"] = {"rows_read": read, "rows_skipped": skipped, "skipped_by_reason": reasons,
                           "seconds": round(time.time() - started, 1)}


def _load_distribution(db, spec, stats):
    started = time.time()
    count = 0
    batch = []
    with _open_text(spec) as handle:
        for row in csv.DictReader(handle, delimiter="|", quoting=csv.QUOTE_NONE):
            count += 1
            batch.append((_toint(row["plant_name_id"]), row["continent"], row["region"], row["area_code_l3"], row["area"],
                          _toint(row["introduced"]), _toint(row["extinct"]), _toint(row["location_doubtful"])))
            if len(batch) >= 100000:
                _flush(db, "wcvp_distribution", batch, 8)
                batch = []
    _flush(db, "wcvp_distribution", batch, 8)
    db.commit()
    stats["wcvp_distribution"] = {"rows": count, "seconds": round(time.time() - started, 1)}


def _load_wfo(db, spec, stats):
    started = time.time()
    read = skipped = bad = 0
    reasons = {}
    batch = []
    with _open_text(spec) as handle:
        reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader)
        ix = {name: i for i, name in enumerate(header)}
        width = len(header)
        for row in reader:
            read += 1
            if len(row) != width:
                bad += 1
                continue

            def g(name):
                return row[ix[name]].strip().strip('"').strip()

            rank_raw = g("taxonRank").lower()
            genus, species, infra = g("genus"), g("specificEpithet"), g("infraspecificEpithet")
            reason = None
            if rank_raw in _WFO_HIGHER_RANKS or not genus or not species:
                reason = "higher_rank_or_incomplete"
            elif not species[0].islower():
                reason = "invalid_species_epithet"
            elif infra and not valid_epithet(infra):
                reason = "invalid_infraspecific_epithet"
            if reason:
                skipped += 1
                reasons[reason] = reasons.get(reason, 0) + 1
                continue
            rank = rank_from_column(rank_raw) if infra else ""
            key_full, key_bin = make_keys(genus, species, rank, infra)
            taxon_id, status, accepted = g("taxonID"), g("taxonomicStatus"), g("acceptedNameUsageID")
            if status == "Accepted" and not accepted:
                accepted = taxon_id
            name = g("scientificName")
            batch.append((taxon_id, g("scientificNameID"), name, rank_raw, g("scientificNameAuthorship"), g("family"),
                          genus, species, rank, infra, g("nomenclaturalStatus"), status, accepted, g("originalNameUsageID"),
                          1 if ("×" in name or name.startswith("+")) else 0, key_full, key_bin))
            if len(batch) >= 50000:
                _flush(db, "wfo_name", batch, 17)
                batch = []
    _flush(db, "wfo_name", batch, 17)
    db.commit()
    stats["wfo_names"] = {"rows_read": read, "rows_skipped": skipped, "rows_bad_field_count": bad,
                          "skipped_by_reason": reasons, "seconds": round(time.time() - started, 1)}


def build_index(out_path, wcvp_names, wcvp_distribution, wfo_classification, wcvp_label="", wfo_label=""):
    """Carga WCVP (nombres y distribución) y WFO en un SQLite nuevo. Devuelve las estadísticas de la carga.

    Cada entrada es una ruta a un CSV o una tupla `(ruta_zip, miembro)`. Si `out_path` existe, se reemplaza.
    """
    if os.path.exists(out_path):
        os.remove(out_path)
    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    csv.field_size_limit(10 ** 9)
    db = sqlite3.connect(out_path)
    try:
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.executescript(_SCHEMA)
        stats = {}
        _load_wcvp(db, wcvp_names, stats)
        _load_distribution(db, wcvp_distribution, stats)
        _load_wfo(db, wfo_classification, stats)
        started = time.time()
        db.executescript(_INDEXES)
        stats["indexes_seconds"] = round(time.time() - started, 1)
        db.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("index_version", str(INDEX_VERSION)), ("wcvp", wcvp_label), ("wfo", wfo_label)])
        db.commit()
        stats["table_rows"] = {t: db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                               for t in ("wcvp_name", "wcvp_distribution", "wfo_name")}
    finally:
        db.close()
    stats["db_bytes"] = os.path.getsize(out_path)
    return stats


_WCVP_SQL = ("SELECT plant_name_id, taxon_name, taxon_authors, taxon_status, accepted_id, taxon_rank, family, key_full, "
             "homotypic, basionym_id, is_hybrid, ipni_id, genus, species, infra_rank, infra_epithet FROM wcvp_name ")
_WFO_SQL = ("SELECT taxon_id, scientific_name, authorship, taxon_status, accepted_id, taxon_rank, family, key_full, "
            "'', original_id, is_hybrid, scientific_name_id, genus, species, infra_rank, infra_epithet FROM wfo_name ")


class Backbone(object):
    """Acceso de solo lectura a un backbone (`wcvp` o `wfo`) dentro del índice.

    Cada fila es un dict: `id`, `name`, `author`, `status`, `accepted_id` ('' si no tiene), `rank`, `family`, `key_full`,
    `homotypic` ('T' si WCVP lo marca; '' si no o si se desconoce; siempre '' en WFO), `basionym_id` (basionym_plant_name_id
    en WCVP; originalNameUsageID en WFO), `is_hybrid`, `source_id` (IPNI o scientificNameID), `genus`, `species`,
    `infra_rank` e `infra_epithet`.
    """

    def __init__(self, path, kind):
        if kind not in STATUS_CLASS:
            raise ValueError("kind debe ser 'wcvp' o 'wfo'")
        self.kind = kind
        self.path = path
        self.db = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        self.sql = _WCVP_SQL if kind == "wcvp" else _WFO_SQL
        self.idcol = "plant_name_id" if kind == "wcvp" else "taxon_id"
        self.table = "wcvp_name" if kind == "wcvp" else "wfo_name"
        self._lookup_cache = {}
        self._get_cache = {}
        self._species_cache = {}
        self._genera = None

    def close(self):
        self.db.close()

    @staticmethod
    def _row(r):
        return {"id": str(r[0]), "name": r[1], "author": r[2] or "", "status": r[3],
                "accepted_id": "" if r[4] in (None, "") else str(r[4]), "rank": r[5], "family": r[6] or "",
                "key_full": r[7], "homotypic": r[8] or "", "basionym_id": "" if r[9] in (None, "") else str(r[9]),
                "is_hybrid": bool(r[10]), "source_id": r[11], "genus": r[12], "species": r[13],
                "infra_rank": r[14] or "", "infra_epithet": r[15] or ""}

    def lookup(self, key_full):
        """Filas con esa clave completa."""
        if key_full not in self._lookup_cache:
            cur = self.db.execute(self.sql + "WHERE key_full = ? ORDER BY 1", (key_full,))
            self._lookup_cache[key_full] = [self._row(r) for r in cur.fetchall()]
        return self._lookup_cache[key_full]

    def get(self, id_):
        id_ = str(id_)
        if id_ not in self._get_cache:
            value = int(id_) if (self.kind == "wcvp" and id_.isdigit()) else id_
            r = self.db.execute(self.sql + "WHERE %s = ?" % self.idcol, (value,)).fetchone()
            self._get_cache[id_] = self._row(r) if r else None
        return self._get_cache[id_]

    def species_of_genus(self, genus):
        """Epítetos de especie (en minúscula) de las filas del género, para la coincidencia aproximada. Con caché."""
        genus = genus.lower()
        if genus not in self._species_cache:
            cur = self.db.execute("SELECT DISTINCT key_binomial FROM %s WHERE key_binomial >= ? AND key_binomial < ?"
                                  % self.table, (genus + " ", genus + "!"))
            self._species_cache[genus] = sorted(r[0][len(genus) + 1:] for r in cur.fetchall())
        return self._species_cache[genus]

    def genera(self):
        """Géneros (en minúscula) con al menos una fila en el índice. Se lee una vez por conexión."""
        if self._genera is None:
            cur = self.db.execute("SELECT DISTINCT genus FROM %s" % self.table)
            self._genera = sorted(set(r[0].lower() for r in cur.fetchall() if r[0]))
        return self._genera

    def status_class(self, status):
        return STATUS_CLASS[self.kind].get(status, 5)

    def synonyms(self, accepted_id, include_self=False):
        """Todos los nombres cuyo aceptado es `accepted_id`, con estado, autor, homotipia y basiónimo."""
        aid = str(accepted_id)
        value = int(aid) if (self.kind == "wcvp" and aid.isdigit()) else aid
        rows = []
        for r in self.db.execute(self.sql + "WHERE accepted_id = ? ORDER BY 1", (value,)).fetchall():
            d = self._row(r)
            if d["id"] == aid and not include_self:
                continue
            rows.append(d)
        return rows

    def distribution(self, plant_name_id):
        """Distribución de WCVP de un nombre (lista de dicts); vacía en WFO."""
        if self.kind != "wcvp":
            return []
        cur = self.db.execute(
            "SELECT continent, region, area_code_l3, area, introduced, extinct, location_doubtful "
            "FROM wcvp_distribution WHERE plant_name_id = ? ORDER BY 3", (int(plant_name_id),))
        return [{"continent": r[0], "region": r[1], "area_code_l3": r[2], "area": r[3], "introduced": bool(r[4]),
                 "extinct": bool(r[5]), "location_doubtful": bool(r[6])} for r in cur.fetchall()]

    def meta(self):
        return dict(self.db.execute("SELECT key, value FROM meta").fetchall())


def open_backbone(path, kind):
    return Backbone(path, kind)
