"""Filas de la EMA para el formato intermedio: áreas terapéuticas y resultado (JSON) y secciones de seguridad (PDF).

- ema_herbal (fuente ema_json): una fila por ficha deduplicada (row_key = último segmento de herbal_medicine_url), con las áreas
  y el resultado separados por «;» y, en las fichas fusionadas (hyperici-herba), las filas originales con sus propias áreas.
- ema_pdf_doc (fuente ema_pdf): una fila por ficha con los documentos usados y el estado de la extracción.
- ema_pdf (fuente ema_pdf): una fila por sección (row_key = <slug>:4.3, <slug>:4.4, <slug>:4.5 o <slug>:CONCLUSIONS), con el
  texto por columna (uso bien establecido o tradicional). Si dos documentos de una ficha traen la misma sección, el segundo
  usa el sufijo #2.
"""
from .ema_pdf import KIND_MONOGRAPH_DRAFT, KIND_MONOGRAPH_FINAL, KIND_PUBLIC_STATEMENT, parse_pdf_filename, slug_of
from .pdf_sections import NO_SAFETY_NOTE
from .workdb import Row

SEPARATOR = ";"
STATUS_OK = "ok"
STATUS_STATEMENT_ONLY = "declaracion-publica"
STATUS_NO_DOCUMENT = "sin-documento"
STATUS_NOT_DOWNLOADED = "no-descargada"
STATUS_FAILED = "extraccion-fallida"
STATUS_NO_SECTIONS = "sin-secciones"


def split_values(value):
    """Valores de un campo de la EMA separados por «;», sin vacíos ni espacios sobrantes."""
    return [part.strip() for part in (value or "").split(SEPARATOR) if part.strip()]


def herbal_rows(records):
    rows = []
    for record in records:
        slug = slug_of(record["herbal_medicine_url"])
        content = {
            "slug": slug, "url": record["herbal_medicine_url"], "latin_name": record.get("latin_name"),
            "english_common_name": record.get("english_common_name"), "botanical_name": record.get("botanical_name"),
            "combination": record.get("combination"), "status": record.get("status"),
            "therapeutic_areas": split_values(record.get("therapeutic_area")),
            "outcomes": split_values(record.get("outcome_of_european_assessment")),
            "additional_information": record.get("additional_information") or None,
            "last_updated_date": record.get("last_updated_date"), "first_published_date": record.get("first_published_date"),
            "rows": [{"latin_name": r.get("latin_name"), "botanical_name": r.get("botanical_name"), "combination": r.get("combination"),
                      "therapeutic_areas": split_values(r.get("therapeutic_area")),
                      "outcomes": split_values(r.get("outcome_of_european_assessment")), "status": r.get("status")}
                     for r in record.get("rows", [])],
        }
        rows.append(Row("ema_herbal", slug, content, raw_name_cell=record.get("botanical_name")))
    return rows


def pdf_rows(records, pdf_files, read_pdf, pages_cached=None):
    """Filas ema_pdf_doc y ema_pdf. pdf_files: [(ruta, nombre de archivo, url)] ya verificados; read_pdf(ruta) → extracción.

    pages_cached: conjunto de slugs con página descargada (distingue «sin documento» de «no descargada»); None = no distingue.
    """
    by_slug = {}
    for path, filename, url in pdf_files:
        parsed = parse_pdf_filename(filename)
        if parsed:
            by_slug.setdefault(parsed[0], []).append((parsed[1], filename, url, path))
    order = {KIND_MONOGRAPH_FINAL: 0, KIND_MONOGRAPH_DRAFT: 0, KIND_PUBLIC_STATEMENT: 1}
    rows, stats = [], {"fiches": 0, STATUS_OK: 0, STATUS_STATEMENT_ONLY: 0, STATUS_NO_DOCUMENT: 0, STATUS_NOT_DOWNLOADED: 0,
                       STATUS_FAILED: 0, STATUS_NO_SECTIONS: 0, "sections": 0, "statements_without_safety": 0}
    for record in records:
        slug = slug_of(record["herbal_medicine_url"])
        stats["fiches"] += 1
        raw = record.get("botanical_name")
        documents, section_rows, seen = [], [], {}
        failed = False
        for kind, filename, url, path in sorted(by_slug.get(slug, []), key=lambda item: (order[item[0]], item[1])):
            document = {"kind": kind, "filename": filename, "url": url}
            try:
                extraction = read_pdf(path)
            except Exception as error:  # un PDF que no se puede leer no detiene la extracción de los demás
                document["error"] = "%s: %s" % (type(error).__name__, error)
                failed = True
                documents.append(document)
                continue
            document["sha256"] = extraction.get("sha256")
            document["tool"] = extraction.get("tool")
            document["draft"] = kind == KIND_MONOGRAPH_DRAFT
            document["sections"] = sorted(extraction["sections"])
            for number, section in extraction["sections"].items():
                key = "%s:%s" % (slug, number)
                seen[key] = seen.get(key, 0) + 1
                if seen[key] > 1:
                    key += "#%d" % seen[key]
                content = dict(section, section=number, slug=slug, document=filename, kind=kind, draft=kind == KIND_MONOGRAPH_DRAFT)
                section_rows.append(Row("ema_pdf", key, content, raw_name_cell=raw))
            statement = extraction.get("statement")
            if statement:
                key = "%s:CONCLUSIONS" % slug
                seen[key] = seen.get(key, 0) + 1
                if seen[key] > 1:
                    key += "#%d" % seen[key]
                content = dict(statement, section="CONCLUSIONS", slug=slug, document=filename, kind=kind)
                if not statement["safety_data"]:
                    content["note"] = NO_SAFETY_NOTE
                    stats["statements_without_safety"] += 1
                section_rows.append(Row("ema_pdf", key, content, raw_name_cell=raw))
            documents.append(document)
        if failed:
            status = STATUS_FAILED
        elif any(d["kind"] != KIND_PUBLIC_STATEMENT for d in documents):
            status = STATUS_OK if any(d["sections"] for d in documents if d["kind"] != KIND_PUBLIC_STATEMENT) else STATUS_NO_SECTIONS
        elif documents:
            status = STATUS_STATEMENT_ONLY
        elif pages_cached is not None and slug not in pages_cached:
            status = STATUS_NOT_DOWNLOADED
        else:
            status = STATUS_NO_DOCUMENT
        stats[status] += 1
        stats["sections"] += len(section_rows)
        rows.append(Row("ema_pdf_doc", slug, {"slug": slug, "url": record["herbal_medicine_url"], "status": status,
                                              "documents": documents}, raw_name_cell=raw))
        rows.extend(section_rows)
    return rows, stats
