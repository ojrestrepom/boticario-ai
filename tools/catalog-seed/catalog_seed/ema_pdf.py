"""Descarga de los PDF de la EMA (monografías y declaraciones públicas) con espera, reanudación y pin.

Para cada ficha de la EMA (deduplicada por URL) se descarga su página, se eligen los documentos
(monografía final de la UE o, si no hay, el borrador, y la declaración pública final si existe) y se
descargan sus PDF a data/.cache/ema_pdf/. La EMA limita las peticiones: este paso espera unos 15 s
entre peticiones, respeta Retry-After, rechaza lo que no empiece por %PDF- (a veces entrega una
página HTML de error) y deja un estado de reanudación en data/.cache/ema_pdf/_state.json.

La lista de PDF y el checksum de cada uno se registran en sources.json (fuente ema_pdf, varios
archivos) con pin_ema_pdfs: es el mecanismo de pin de esta fuente, porque la lista de archivos
solo se conoce tras leer las páginas.
"""
import hashlib
import html as html_lib
import json
import re
import time
from pathlib import Path

from . import download as download_lib
from .sources import DEFAULT_CACHE_DIR, SourceError
from .wiki import DEFAULT_WAIT, RateLimited, http_request, iso, parse_retry_after

SOURCE_ID = "ema_pdf"
DEFAULT_DELAY = 15.0
MAX_ATTEMPTS = 3
MAX_FILENAME = 200
SOFT_LIMIT_WAIT = 60
STATE_FILE = "_state.json"
PDF_MAGIC = b"%PDF-"
BASE_URL = "https://www.ema.europa.eu"

KIND_MONOGRAPH_FINAL = "monograph-final"
KIND_MONOGRAPH_DRAFT = "monograph-draft"
KIND_PUBLIC_STATEMENT = "public-statement"
KINDS = (KIND_MONOGRAPH_FINAL, KIND_MONOGRAPH_DRAFT, KIND_PUBLIC_STATEMENT)

HREF = re.compile(r'href="([^"]*/documents/(herbal-monograph|public-statement)/([^"/?#]+\.pdf))"', re.IGNORECASE)
REVISION = re.compile(r"revision-(\d+)")


def slug_of(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def pdf_filename(slug, kind, name):
    """Nombre en la caché y en sources.json: <slug>__<tipo>__<nombre del PDF>."""
    filename = "%s__%s__%s" % (slug, kind, name)
    if len(filename) > MAX_FILENAME:
        # Algunos nombres de la EMA superan los 255 caracteres del sistema de archivos: se acortan con un hash estable.
        stem = name[:-4] if name.endswith(".pdf") else name
        keep = MAX_FILENAME - len(slug) - len(kind) - 4 - 11 - 4
        filename = "%s__%s__%s-%s.pdf" % (slug, kind, stem[:keep], hashlib.sha1(name.encode("utf-8")).hexdigest()[:10])
    return filename


def parse_pdf_filename(filename):
    """Inversa de pdf_filename: (slug, tipo, nombre) o None si no tiene la forma esperada."""
    parts = filename.split("__", 2)
    if len(parts) != 3 or parts[1] not in KINDS:
        return None
    return tuple(parts)


def _revision(name):
    match = REVISION.search(name)
    return int(match.group(1)) if match else 0


def _draft_rank(name):
    return 1 if name.startswith("second-draft-") else 0


def select_documents(page_html):
    """Elige los documentos de una página de la EMA.

    - Monografía final: ruta herbal-monograph/ cuyo nombre no empieza por draft-, second-draft- ni
      superseded-; si hay varias (por ejemplo una de uso bien establecido y otra de uso tradicional)
      se quedan las de la revisión más alta.
    - Si no hay final, el borrador más avanzado (second-draft sobre draft, revisión más alta).
    - Declaración pública: ruta public-statement/ (o, en borrador, herbal-monograph/) con el mismo criterio; un borrador solo
      se usa si la ficha no tiene monografía ni declaración final.
    - Se ignoran superseded-, call- (convocatorias de datos) y los documentos que no son monografías.
    Devuelve una lista de {kind, name, url} en orden estable (monografías primero).
    """
    found = []
    for href, group, name in HREF.findall(page_html):
        href = html_lib.unescape(href)
        url = href if href.startswith("http") else BASE_URL + href
        found.append((group.lower(), name, url))
    seen, unique = set(), []
    for item in found:
        if item[2] not in seen:
            seen.add(item[2])
            unique.append(item)

    def usable(name):
        return not name.startswith("superseded-") and not name.startswith("call-")

    def is_draft(name):
        return name.startswith("draft-") or name.startswith("second-draft-")

    chosen = []
    usable_items = [i for i in unique if usable(i[1])]
    # Algunas declaraciones públicas (en borrador) están publicadas bajo herbal-monograph/.
    monographs = [i for i in usable_items if i[0] == "herbal-monograph" and "public-statement" not in i[1] and "monograph" in i[1]]
    finals = [i for i in monographs if not is_draft(i[1])]
    if finals:
        top = max(_revision(i[1]) for i in finals)
        chosen += [(KIND_MONOGRAPH_FINAL, i[1], i[2]) for i in finals if _revision(i[1]) == top]
    else:
        drafts = [i for i in monographs if is_draft(i[1])]
        if drafts:
            best = max(drafts, key=lambda i: (_revision(i[1]), _draft_rank(i[1])))
            chosen.append((KIND_MONOGRAPH_DRAFT, best[1], best[2]))
    statements = [i for i in usable_items if "public-statement" in i[1] and i[0] in ("public-statement", "herbal-monograph")]
    final_statements = [i for i in statements if not is_draft(i[1])]
    if final_statements:
        top = max(_revision(i[1]) for i in final_statements)
        chosen += [(KIND_PUBLIC_STATEMENT, i[1], i[2]) for i in final_statements if _revision(i[1]) == top]
    elif statements and not chosen:
        best = max(statements, key=lambda i: (_revision(i[1]), _draft_rank(i[1])))
        chosen.append((KIND_PUBLIC_STATEMENT, best[1], best[2]))
    return [{"kind": kind, "name": name, "url": url} for kind, name, url in chosen]


def is_pdf(body):
    return body[:len(PDF_MAGIC)] == PDF_MAGIC


class EmaPdfStep:
    """Descarga páginas y PDF de las fichas con espera entre peticiones y estado de reanudación."""

    def __init__(self, cache_dir=DEFAULT_CACHE_DIR, delay=DEFAULT_DELAY, request=http_request,
                 now=time.time, sleep=time.sleep, monotonic=time.monotonic):
        self.dir = Path(cache_dir) / SOURCE_ID
        self.pages_dir = self.dir / "pages"
        self.delay = delay
        self.request = request
        self.now = now
        self.sleep = sleep
        self.monotonic = monotonic
        self.requests_made = 0
        self._last = None

    # --- rutas y estado ---
    def page_path(self, slug):
        return self.pages_dir / (slug + ".html")

    def pdf_path(self, slug, document):
        return self.dir / pdf_filename(slug, document["kind"], document["name"])

    def state_path(self):
        return self.dir / STATE_FILE

    def read_state(self):
        try:
            return json.loads(self.state_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}

    def write_state(self, state):
        self.dir.mkdir(parents=True, exist_ok=True)
        state["updated"] = iso(self.now())
        self.state_path().write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")

    # --- peticiones ---
    def _pace(self):
        if self._last is not None and self.delay:
            wait = self.delay - (self.monotonic() - self._last)
            if wait > 0:
                self.sleep(wait)

    def _get(self, url):
        """Una petición con espera previa. Un 429 o 503 lanza RateLimited."""
        self._pace()
        self.requests_made += 1
        try:
            status, body, headers = self.request(url, None, None)
        finally:
            self._last = self.monotonic()
        if status in (429, 503):
            wait = parse_retry_after(headers.get("Retry-After") if headers else None, self.now())
            if wait is None:
                wait = DEFAULT_WAIT
            raise RateLimited(self.now() + wait, "HTTP %d%s" % (
                status, "" if headers and headers.get("Retry-After") else " sin Retry-After"))
        return status, body

    @staticmethod
    def _write(path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".part")
        partial.write_bytes(body)
        partial.replace(path)

    def _fetch_page(self, slug, url, state):
        status, body = self._get(url)
        if status == 200 and b"<html" in body[:4096].lower():
            self._write(self.page_path(slug), body)
            return True
        self._failed(state, "page:" + slug, "HTTP %d" % status)
        return self._soft_limit(status)

    def _fetch_pdf(self, slug, document, state):
        key = "pdf:" + self.pdf_path(slug, document).name
        status, body = self._get(document["url"])
        if status == 200 and is_pdf(body):
            self._write(self.pdf_path(slug, document), body)
            return True
        self._failed(state, key, "HTTP %d%s" % (status, "" if status != 200 else ", la respuesta no empieza por %PDF-"))
        return self._soft_limit(status)

    def _soft_limit(self, status):
        """Un 200 sin PDF (página HTML de error) suele ser un límite de peticiones disfrazado: se detiene el paso."""
        if status == 200:
            raise RateLimited(self.now() + SOFT_LIMIT_WAIT, "respuesta 200 que no es un PDF ni una página válida")
        return False

    @staticmethod
    def _failed(state, key, reason):
        failures = state.setdefault("failures", {})
        entry = failures.setdefault(key, {"count": 0, "reason": reason})
        entry["count"] += 1
        entry["reason"] = reason
        return False

    # --- ejecución ---
    def run(self, records, limit=None):
        """Descarga lo pendiente de las fichas. Devuelve un dict con el estado y los conteos.

        status: complete, rate_limited (se detuvo por límite de peticiones; reanudable) o waiting
        (el plazo de un 429 anterior no ha pasado: no abre la red). limit corta tras ese número
        de peticiones (para pruebas manuales).
        """
        state = self.read_state()
        if state.get("retry_not_before_epoch", 0) > self.now():
            return self.report("waiting", records, state, state["retry_not_before_epoch"], state.get("reason"))
        state.pop("retry_not_before_epoch", None)
        state.pop("retry_not_before", None)
        state.pop("reason", None)
        try:
            for record in records:
                url = record["herbal_medicine_url"]
                slug = slug_of(url)
                if not self.page_path(slug).is_file():
                    if self._exhausted(state, "page:" + slug):
                        continue
                    if limit is not None and self.requests_made >= limit:
                        break
                    if not self._fetch_page(slug, url, state):
                        self.write_state(state)
                        continue
                documents = select_documents(self.page_path(slug).read_text(encoding="utf-8", errors="replace"))
                for document in documents:
                    path = self.pdf_path(slug, document)
                    if path.is_file():
                        continue
                    if self._exhausted(state, "pdf:" + path.name):
                        continue
                    if limit is not None and self.requests_made >= limit:
                        break
                    self._fetch_pdf(slug, document, state)
                    self.write_state(state)
                if limit is not None and self.requests_made >= limit:
                    break
        except RateLimited as stop:
            state["retry_not_before_epoch"] = stop.retry_at
            state["retry_not_before"] = iso(stop.retry_at)
            state["reason"] = stop.reason
            self.write_state(state)
            return self.report("rate_limited", records, state, stop.retry_at, stop.reason)
        self.write_state(state)
        return self.report("complete", records, state, None, None)

    @staticmethod
    def _exhausted(state, key):
        return state.get("failures", {}).get(key, {}).get("count", 0) >= MAX_ATTEMPTS

    def inventory(self, records):
        """Cuenta fichas, páginas y PDF descargados y pendientes (sin abrir la red)."""
        pages = pdfs_done = pdfs_pending = no_document = 0
        for record in records:
            slug = slug_of(record["herbal_medicine_url"])
            if not self.page_path(slug).is_file():
                continue
            pages += 1
            documents = select_documents(self.page_path(slug).read_text(encoding="utf-8", errors="replace"))
            if not documents:
                no_document += 1
            for document in documents:
                if self.pdf_path(slug, document).is_file():
                    pdfs_done += 1
                else:
                    pdfs_pending += 1
        return {"fiches": len(records), "pages_cached": pages, "pages_pending": len(records) - pages,
                "pdfs_downloaded": pdfs_done, "pdfs_pending_known": pdfs_pending, "fiches_without_document": no_document}

    def report(self, status, records, state, retry_at, reason):
        failed = sorted(k for k, v in state.get("failures", {}).items() if v["count"] >= MAX_ATTEMPTS)
        out = {"status": status, "requests": self.requests_made, "retry_at": iso(retry_at) if retry_at else None,
               "reason": reason, "failed": failed}
        out.update(self.inventory(records))
        return out


def pin_ema_pdfs(sources_path, records, cache_dir=DEFAULT_CACHE_DIR, version=None):
    """Registra en sources.json (fuente ema_pdf) los PDF descargados con su tamaño y sha256.

    Una entrada ya registrada se verifica contra la caché y no se cambia (si no coincide falla). El
    orden sigue el de las fichas. Las entradas que la selección vigente ya no elige (por ejemplo documentos descartados
    después) se retiran de la lista. Devuelve (agregados, total).
    """
    step = EmaPdfStep(cache_dir)
    with open(sources_path, encoding="utf-8") as handle:
        document = json.load(handle)
    entry = next((e for e in document["sources"] if e["id"] == SOURCE_ID), None)
    if entry is None:
        raise SourceError("la fuente '%s' no está declarada en %s" % (SOURCE_ID, sources_path))
    known = {f["filename"]: f for f in entry.get("files", [])}
    files, added = [], 0
    for record in records:
        slug = slug_of(record["herbal_medicine_url"])
        if not step.page_path(slug).is_file():
            continue
        for item in select_documents(step.page_path(slug).read_text(encoding="utf-8", errors="replace")):
            path = step.pdf_path(slug, item)
            if not path.is_file():
                continue
            filename = path.name
            digest = download_lib.file_digest(str(path), "sha256")
            size = path.stat().st_size
            if filename in known:
                old = known[filename]
                if old["size"] != size or old["checksum"]["value"] != digest:
                    raise SourceError("el PDF %s de la caché no coincide con el checksum fijado en %s; "
                                      "bórrelo de la caché y vuelva a descargarlo" % (filename, sources_path))
                files.append(old)
            else:
                files.append({"url": item["url"], "filename": filename, "size": size,
                              "checksum": {"algorithm": "sha256", "value": digest}})
                added += 1
    entry["files"] = files
    if version:
        entry["version"] = version
    download_lib._write_sources_file(sources_path, document)
    return added, len(files)
