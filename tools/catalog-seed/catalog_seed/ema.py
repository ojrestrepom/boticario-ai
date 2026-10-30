"""Lectura de la EMA (herbal medicines JSON): snapshot y deduplicación por herbal_medicine_url."""
import json
from datetime import date

EXPECTED_RECORDS = 204


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def snapshot_timestamp(document):
    return document.get("meta", {}).get("timestamp")


def dedupe_records(document):
    """Una ficha por herbal_medicine_url, en el orden de primera aparición.

    Las filas idénticas se descartan. Las filas distintas con la misma URL (por ejemplo el
    combinado hyperici-herba, con Hypericum y Cimicifuga) se fusionan: los campos que
    difieren se unen con ';' sin repetir valores y 'rows' conserva las filas originales.
    """
    grouped = {}
    for row in document["data"]:
        rows = grouped.setdefault(row["herbal_medicine_url"], [])
        if row not in rows:
            rows.append(row)
    records = []
    for rows in grouped.values():
        record = dict(rows[0])
        for key in record:
            values = []
            for row in rows:
                if row.get(key) not in values:
                    values.append(row.get(key))
            if len(values) > 1:
                record[key] = ";".join(v for v in values if v)
        record["rows"] = rows
        records.append(record)
    return records


def describe_snapshot(source, paths):
    document = load_json(paths[0])
    return "Snapshot fijado el %s, meta.timestamp %s" % (date.today().isoformat(), snapshot_timestamp(document))
