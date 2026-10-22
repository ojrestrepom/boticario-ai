"""Descarga con límite de peticiones y reanudación: Wikidata, Wikipedia en español y Commons.

Cada respuesta se guarda en un archivo de la caché (data/.cache/<servicio>/). Un 429 o 503 con
Retry-After detiene el paso y deja un estado de reanudación (_resume.json) con la hora mínima
de reintento; mientras no pase esa hora no se abre la red. Una segunda ejecución solo consulta
lo que no tiene archivo en la caché.
"""
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from .sources import DEFAULT_CACHE_DIR, SourceError

USER_AGENT = "BoticarioAI-catalog-seed/0.1 (academic project)"
DEFAULT_WAIT = 300  # segundos cuando un 429 o 503 llega sin Retry-After
RESUME_FILE = "_resume.json"

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIPEDIA_ES_ENDPOINT = "https://es.wikipedia.org/api/rest_v1/page/summary/"
COMMONS_ENDPOINT = "https://commons.wikimedia.org/w/api.php"

SERVICES = ("wikidata", "wikipedia_es", "commons")
DEFAULT_BATCH = {"wikidata": 20, "wikipedia_es": 1, "commons": 20}
MAX_BATCH = {"wikidata": 100, "wikipedia_es": 1, "commons": 50}


class RateLimited(Exception):
    def __init__(self, retry_at, reason):
        super().__init__(reason)
        self.retry_at = retry_at  # segundos desde la época (UTC)
        self.reason = reason


def parse_retry_after(value, now):
    """Segundos de espera de una cabecera Retry-After (entero o fecha HTTP); None si no es válida."""
    if value is None:
        return None
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return int(value)
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0, int(moment.timestamp() - now))


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_request(url, data=None, headers=None, timeout=60):
    """Devuelve (estado, cuerpo, cabeceras). No lanza para códigos HTTP de error."""
    request = urllib.request.Request(url, data=data, headers=dict(headers or {}, **{"User-Agent": USER_AGENT}))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def cache_name(key):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", key)[:60]
    return "%s-%s.json" % (safe, hashlib.sha1(key.encode("utf-8")).hexdigest()[:10])


def read_entries(path):
    """Lee la lista de entradas (una por línea; se ignoran vacías y comentarios con #)."""
    entries = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and line not in entries:
                entries.append(line)
    return entries


class Step:
    """Un servicio con caché por archivo, estado de reanudación y límite de peticiones."""

    def __init__(self, service, cache_dir=DEFAULT_CACHE_DIR, endpoint=None, batch_size=None,
                 delay=1.0, request=http_request, now=time.time, sleep=time.sleep):
        if service not in SERVICES:
            raise SourceError("servicio desconocido '%s' (%s)" % (service, ", ".join(SERVICES)))
        self.service = service
        self.dir = Path(cache_dir) / service
        self.endpoint = endpoint or {"wikidata": WIKIDATA_ENDPOINT, "wikipedia_es": WIKIPEDIA_ES_ENDPOINT,
                                     "commons": COMMONS_ENDPOINT}[service]
        size = batch_size or DEFAULT_BATCH[service]
        if size < 1 or size > MAX_BATCH[service]:
            raise SourceError("el tamaño de lote de %s debe estar entre 1 y %d" % (service, MAX_BATCH[service]))
        self.batch_size = size
        self.delay = delay
        self.request = request
        self.now = now
        self.sleep = sleep
        self.requests_made = 0

    # --- caché y estado ---
    def cache_path(self, key):
        return self.dir / cache_name(key)

    def is_cached(self, key):
        return self.cache_path(key).is_file()

    def store(self, key, payload):
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_path(key)
        partial = path.with_name(path.name + ".part")
        record = {"key": key, "service": self.service, "fetched_at": iso(self.now()), "response": payload}
        partial.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        partial.replace(path)

    def load(self, key):
        return json.loads(self.cache_path(key).read_text(encoding="utf-8"))["response"]

    def iter_cached(self):
        """(clave, respuesta) de cada archivo de la caché del servicio, en orden de nombre de archivo."""
        if not self.dir.is_dir():
            return
        for path in sorted(self.dir.glob("*.json")):
            if path.name == RESUME_FILE:
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            yield record["key"], record["response"]

    def resume_path(self):
        return self.dir / RESUME_FILE

    def read_resume(self):
        try:
            return json.loads(self.resume_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return None

    def write_resume(self, retry_at, reason, pending):
        self.dir.mkdir(parents=True, exist_ok=True)
        state = {"service": self.service, "retry_not_before": iso(retry_at), "retry_not_before_epoch": retry_at,
                 "reason": reason, "pending": len(pending), "updated": iso(self.now())}
        self.resume_path().write_text(json.dumps(state, indent=1), encoding="utf-8")

    def clear_resume(self):
        if self.resume_path().exists():
            self.resume_path().unlink()

    # --- ejecución ---
    def call(self, url, data=None, headers=None):
        """Una petición. Devuelve (estado, cuerpo). Un 429/503 lanza RateLimited."""
        self.requests_made += 1
        status, body, response_headers = self.request(url, data, headers)
        if status in (429, 503):
            wait = parse_retry_after(response_headers.get("Retry-After") if response_headers else None, self.now())
            if wait is None:
                wait = DEFAULT_WAIT
            raise RateLimited(self.now() + wait, "HTTP %d%s" % (
                status, "" if response_headers and response_headers.get("Retry-After") else " sin Retry-After"))
        return status, body

    def run(self, entries):
        """Consulta lo pendiente. Devuelve un dict con status (complete, waiting o rate_limited)."""
        pending = [e for e in entries if not self.is_cached(self.key_of(e))]
        state = self.read_resume()
        if state and state["retry_not_before_epoch"] > self.now():
            return self.result("waiting", entries, pending, state["retry_not_before_epoch"], state["reason"])
        if state:
            self.clear_resume()
        first = True
        try:
            for start in range(0, len(pending), self.batch_size):
                if not first and self.delay:
                    self.sleep(self.delay)
                first = False
                self.fetch_batch(pending[start:start + self.batch_size])
        except RateLimited as stop:
            pending = [e for e in entries if not self.is_cached(self.key_of(e))]
            self.write_resume(stop.retry_at, stop.reason, pending)
            return self.result("rate_limited", entries, pending, stop.retry_at, stop.reason)
        return self.result("complete", entries, [], None, None)

    def result(self, status, entries, pending, retry_at, reason):
        out = {"status": status, "service": self.service, "total": len(entries), "pending": len(pending),
               "fetched_requests": self.requests_made, "retry_at": iso(retry_at) if retry_at else None, "reason": reason}
        return out

    def key_of(self, entry):
        return entry

    def fetch_batch(self, batch):
        raise NotImplementedError


def normalize_name(name):
    """Forma P225 de un nombre: el signo híbrido pegado al epíteto (Mentha ×piperita)."""
    return re.sub(r"×\s+", "×", " ".join(name.split()))


QID = re.compile(r"Q[0-9]+")


def split_values(text):
    return [v for v in text.split("|") if v]


class WikidataStep(Step):
    """SPARQL por lotes y por POST. Entradas: nombres (P225) o QIDs; un archivo por entrada."""

    def __init__(self, *args, **kwargs):
        super().__init__("wikidata", *args, **kwargs)

    def key_of(self, entry):
        return entry if QID.fullmatch(entry) else normalize_name(entry)

    @staticmethod
    def build_query(batch):
        qids = [e for e in batch if QID.fullmatch(e)]
        names = [e for e in batch if not QID.fullmatch(e)]
        values = []
        if qids:
            values.append("{ VALUES ?item { %s } BIND(\"\" AS ?req) }" % " ".join("wd:" + q for q in qids))
        if names:
            quoted = " ".join(json.dumps(normalize_name(n), ensure_ascii=False) for n in names)
            values.append("{ VALUES ?req { %s } ?item wdt:P225 ?req }" % quoted)
        return (
            "SELECT ?req ?item ?taxon "
            "(GROUP_CONCAT(DISTINCT ?auth; separator=\"|\") AS ?authors) "
            "(SAMPLE(?labelEs) AS ?label) "
            "(GROUP_CONCAT(DISTINCT ?alias; separator=\"|\") AS ?aliases) "
            "(GROUP_CONCAT(DISTINCT ?es; separator=\"|\") AS ?esNames) "
            "(GROUP_CONCAT(DISTINCT ?img; separator=\"|\") AS ?images) "
            "(SAMPLE(?eswikiTitle) AS ?eswiki) "
            "(GROUP_CONCAT(DISTINCT ?gbifId; separator=\"|\") AS ?gbif) "
            "(GROUP_CONCAT(DISTINCT ?powoId; separator=\"|\") AS ?powo) "
            "(GROUP_CONCAT(DISTINCT ?ipniId; separator=\"|\") AS ?ipni) "
            "WHERE { " + " UNION ".join(values) + " "
            "OPTIONAL { ?item p:P225 ?st . ?st ps:P225 ?taxon . OPTIONAL { ?st pq:P405 ?authItem . ?authItem wdt:P428 ?auth } } "
            "OPTIONAL { ?item rdfs:label ?labelEs . FILTER(LANG(?labelEs) = \"es\") } "
            "OPTIONAL { ?item skos:altLabel ?alias . FILTER(LANG(?alias) = \"es\") } "
            "OPTIONAL { ?item wdt:P1843 ?es . FILTER(LANG(?es) = \"es\") } "
            "OPTIONAL { ?item wdt:P18 ?img } "
            "OPTIONAL { ?sl schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> ; schema:name ?eswikiTitle } "
            "OPTIONAL { ?item wdt:P846 ?gbifId } "
            "OPTIONAL { ?item wdt:P5037 ?powoId } "
            "OPTIONAL { ?item wdt:P961 ?ipniId } "
            "} GROUP BY ?req ?item ?taxon"
        )

    def fetch_batch(self, batch):
        keys = [self.key_of(e) for e in batch]
        body = urllib.parse.urlencode({"query": self.build_query(batch), "format": "json"}).encode("utf-8")
        status, payload = self.call(self.endpoint, body, {
            "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"})
        if status != 200:
            raise SourceError("wikidata respondió HTTP %d; no se guarda nada de este lote" % status)
        try:
            bindings = json.loads(payload.decode("utf-8"))["results"]["bindings"]
        except (ValueError, KeyError):
            raise SourceError("wikidata devolvió una respuesta que no es SPARQL JSON")
        items = {key: [] for key in keys}
        for row in bindings:
            def val(name):
                return row.get(name, {}).get("value", "")

            item = {
                "qid": val("item").rsplit("/", 1)[-1],
                "taxon": val("taxon"),
                "authors": split_values(val("authors")),
                "labelEs": val("label"),
                "aliasesEs": split_values(val("aliases")),
                "spanishNames": [v for v in val("esNames").split("|") if v],
                "images": [v for v in val("images").split("|") if v],
                "eswiki": val("eswiki"),
                "gbif": [v for v in val("gbif").split("|") if v],
                "powo": [v for v in val("powo").split("|") if v],
                "ipni": split_values(val("ipni")),
            }
            request_key = val("req") or item["qid"]
            if request_key in items:
                items[request_key].append(item)
        for key in keys:
            self.store(key, {"items": items[key]})


class WikipediaStep(Step):
    """API REST de resúmenes de es.wikipedia.org. Entradas: títulos de artículo."""

    def __init__(self, *args, **kwargs):
        super().__init__("wikipedia_es", *args, **kwargs)

    def key_of(self, entry):
        return entry.replace("_", " ").strip()

    def fetch_batch(self, batch):
        for entry in batch:
            title = self.key_of(entry)
            url = self.endpoint + urllib.parse.quote(title.replace(" ", "_"), safe="")
            status, payload = self.call(url, None, {"Accept": "application/json"})
            if status == 404:
                self.store(title, {"missing": True})
            elif status == 200:
                self.store(title, json.loads(payload.decode("utf-8")))
            else:
                raise SourceError("wikipedia_es respondió HTTP %d para '%s'" % (status, title))


class CommonsStep(Step):
    """Metadatos de imagen de Commons (imageinfo con extmetadata). Entradas: nombres de archivo."""

    def __init__(self, *args, **kwargs):
        super().__init__("commons", *args, **kwargs)

    def key_of(self, entry):
        return commons_title(entry)

    def fetch_batch(self, batch):
        titles = [self.key_of(e) for e in batch]
        query = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2", "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata", "titles": "|".join(titles)})
        status, payload = self.call(self.endpoint + "?" + query, None, {"Accept": "application/json"})
        if status != 200:
            raise SourceError("commons respondió HTTP %d; no se guarda nada de este lote" % status)
        try:
            data = json.loads(payload.decode("utf-8"))["query"]
        except (ValueError, KeyError):
            raise SourceError("commons devolvió una respuesta inesperada")
        renamed = {n["from"]: n["to"] for n in data.get("normalized", [])}
        pages = {p.get("title"): p for p in data.get("pages", [])}
        for title in titles:
            page = pages.get(renamed.get(title, title))
            if page is None or page.get("missing") or not page.get("imageinfo"):
                self.store(title, {"missing": True})
            else:
                self.store(title, {"title": page["title"], "imageinfo": page["imageinfo"][0]})


def commons_title(entry):
    """'File:X.jpg' a partir de un nombre, 'File:...' o una URL Special:FilePath de Wikidata."""
    entry = entry.strip()
    if "Special:FilePath/" in entry:
        entry = urllib.parse.unquote(entry.split("Special:FilePath/", 1)[1])
    if not entry.lower().startswith("file:"):
        entry = "File:" + entry
    return "File:" + entry[5:].replace("_", " ").strip()


STEPS = {"wikidata": WikidataStep, "wikipedia_es": WikipediaStep, "commons": CommonsStep}


def make_step(service, **kwargs):
    if service not in STEPS:
        raise SourceError("servicio desconocido '%s' (%s)" % (service, ", ".join(SERVICES)))
    return STEPS[service](**kwargs)
