"""Extracción de Wikidata, Wikipedia en español y Commons desde la caché de respuestas a `data/work/sources.db`.

Solo lee la caché (nunca la red). Filas, con el ref `<record_type>:<row_key>`:

- `wikidata`: `wikidata:<QID>`, un ítem por QID con su nombre P225 en `raw_name_cell`.
- `wikipedia_es`: `wikipedia_es:<título>`, el resumen del artículo enlazado por algún ítem (título canónico de la respuesta).
- `commons`: `commons:<File:...>`, solo las imágenes P18 con licencia admitida; las descartadas se cuentan en las estadísticas y
  salen en el informe de asignación.

La extracción no filtra homónimos: guarda lo que hay en la caché, que la descarga solo llena para los ítems que pasan el filtro
(Wikipedia y Commons). La asignación a plantas (`wiki_assign.build_assignment`) dice qué ítem va a qué planta.
"""
from .licenses import MISSING, classify, strip_html
from .wiki import CommonsStep, WikidataStep, WikipediaStep, commons_title
from .wiki_assign import IPNI_PREFIX, _wikidata_items
from .workdb import Row


def _ids(values):
    return sorted({v[len(IPNI_PREFIX):] if v.startswith(IPNI_PREFIX) else v for v in values})


def wikidata_rows(cache_dir):
    rows = []
    for qid, item in sorted(_wikidata_items(WikidataStep(cache_dir=cache_dir)).items()):
        content = {
            "qid": qid, "taxon": item["taxon"], "authors": item.get("authors", []), "labelEs": item.get("labelEs", ""),
            "aliasesEs": item.get("aliasesEs", []), "spanishNames": item.get("spanishNames", []),
            "images": sorted({commons_title(i) for i in item.get("images", [])}), "eswiki": item.get("eswiki", ""),
            "gbif": item.get("gbif", []), "ipni": _ids(item.get("ipni", [])), "powo": _ids(item.get("powo", [])),
            "queried": sorted(item["queried"]),
        }
        rows.append(Row("wikidata", qid, content, raw_name_cell=item["taxon"], qid=qid))
    return rows, {"wikidata": len(rows)}


def wikipedia_rows(cache_dir):
    items = _wikidata_items(WikidataStep(cache_dir=cache_dir))
    step = WikipediaStep(cache_dir=cache_dir)
    rows, seen, stats = [], set(), {"wikipedia_es": 0, "missing": 0, "not_standard": 0, "not_cached": 0}
    for title in sorted({step.key_of(i["eswiki"]) for i in items.values() if i.get("eswiki")}):
        if not step.is_cached(title):
            stats["not_cached"] += 1
            continue
        response = step.load(title)
        if response.get("missing"):
            stats["missing"] += 1
            continue
        if response.get("type") != "standard":
            stats["not_standard"] += 1
            continue
        canonical = response["title"]
        if canonical in seen:
            continue
        seen.add(canonical)
        content = {
            "title": canonical, "displayTitle": strip_html(response.get("displaytitle") or canonical),
            "description": response.get("description", ""), "extract": response.get("extract", ""),
            "url": response.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "revision": str(response.get("revision", "")), "timestamp": response.get("timestamp", ""),
            "lang": response.get("lang", "es"), "wikibaseItem": response.get("wikibase_item", ""),
        }
        rows.append(Row("wikipedia_es", canonical, content, raw_name_cell=canonical))
        stats["wikipedia_es"] += 1
    return rows, stats


def commons_rows(cache_dir):
    items = _wikidata_items(WikidataStep(cache_dir=cache_dir))
    step = CommonsStep(cache_dir=cache_dir)
    rows, stats = [], {"commons": 0, "not_cached": 0, "discarded": 0}
    for title in sorted({commons_title(i) for item in items.values() for i in item.get("images", [])}):
        if not step.is_cached(title):
            stats["not_cached"] += 1
            continue
        response = step.load(title)
        if response.get("missing"):
            stats["discarded"] += 1
            stats["discarded_" + MISSING] = stats.get("discarded_" + MISSING, 0) + 1
            continue
        info = response["imageinfo"]
        result = classify(info.get("extmetadata"))
        if not result["admitted"]:
            stats["discarded"] += 1
            key = "discarded_" + result["reason"]
            stats[key] = stats.get(key, 0) + 1
            continue
        content = {
            "title": response["title"], "pageUrl": info.get("descriptionurl", ""), "fileUrl": info.get("url", ""),
            "author": result["author"] or result["credit"], "license": result["license"], "licenseCode": result["licenseCode"],
            "licenseUrl": result["licenseUrl"], "attributionRequired": result["attributionRequired"],
            "mime": info.get("mime", ""), "width": info.get("width"), "height": info.get("height"),
        }
        rows.append(Row("commons", response["title"], content, raw_name_cell=response["title"]))
        stats["commons"] += 1
    return rows, stats


EXTRACTORS = {"wikidata": wikidata_rows, "wikipedia_es": wikipedia_rows, "commons": commons_rows}
