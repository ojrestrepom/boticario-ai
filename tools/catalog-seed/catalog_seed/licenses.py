"""Clasificación de la licencia de una imagen de Commons (extmetadata de imageinfo): admitida o descartada, con el motivo.

Se admiten CC0, dominio público, CC BY y CC BY-SA (cualquier versión y portado de jurisdicción). Se descartan, entre otras,
GFDL sola, las licencias NC y ND, las que no son de la lista y las que no se pueden reconocer. Una imagen que exige
atribución y no trae autor ni crédito también se descarta, porque no se podría atribuir.
"""
import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LICENSE_URLS = {
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by": "https://creativecommons.org/licenses/by/%s/",
    "cc-by-sa": "https://creativecommons.org/licenses/by-sa/%s/",
}

# Motivos de descarte.
NON_COMMERCIAL = "no-comercial"
NO_DERIVATIVES = "sin-derivadas"
GFDL = "gfdl"
OTHER = "otra-licencia"
UNKNOWN = "licencia-desconocida"
NO_AUTHOR = "sin-autor"
MISSING = "archivo-no-encontrado"
NOT_DISPLAYABLE = "formato-no-mostrable"
DISCARD_REASONS = (NON_COMMERCIAL, NO_DERIVATIVES, GFDL, OTHER, UNKNOWN, NO_AUTHOR, MISSING, NOT_DISPLAYABLE)

# Tipos MIME que la app puede mostrar; las láminas de herbario en PDF o TIFF y similares se descartan.
DISPLAYABLE_MIMES = ("image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml")

_CC_BY = re.compile(r"^cc[- ]by(?P<sa>[- ]sa)?[- ](?P<version>\d(?:\.\d)?)(?:[- ][a-z]+)*$")
_CC_RESTRICTED = re.compile(r"^cc[- ]by\b.*[- ](?P<kind>nc|nd)\b")
_SPLIT = re.compile(r"\s*(?:,|;|\+|/| and | or )\s*")
_TAG = re.compile(r"<[^>]*>")


def clean_file_url(url):
    """La URL del archivo sin los parámetros de seguimiento `utm_*` que Commons añade a imageinfo."""
    if not isinstance(url, str) or "utm_" not in url:
        return url
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def meta(extmetadata, name):
    value = (extmetadata or {}).get(name)
    return value.get("value", "") if isinstance(value, dict) else ""


def strip_html(text):
    """Texto plano de un fragmento HTML de Commons (Artist, Credit)."""
    text = _TAG.sub(" ", text or "")
    return " ".join(html.unescape(text).split())


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"https?://\S+")
_ASSUMED = re.compile(r"^No machine-readable author provided\.\s*(?P<name>.+?)\s+assumed\b.*$", re.I)
_LICENSE_SENTENCE = re.compile(r"^This (?:file|work|image) is (?:licensed|made available)\b", re.I)
_ATTRIBUTION = re.compile(r"\bAttribution:\s*(?P<name>.+?)(?:\s+You are free\b.*)?$", re.I)
_RIGHTS_TAIL = re.compile(r"\s*,?\s*(?:some rights reserved|all rights reserved|licensed as noted)\b.*$", re.I)
_RIGHTS_HEAD = re.compile(r"^\s*(?:\(c\)|©|copyright(?:\s*\(c\))?(?:\s+by)?)\s+", re.I)
_LICENSE_TOKEN = re.compile(r"\(?\bCC[- ]?(?:BY|0)(?:[- ](?:SA|NC|ND))*(?:[- ]\d(?:\.\d)?)?\b\)?", re.I)


def clean_author(text):
    """Autor de Commons sin correos, texto de licencia ni avisos de «sin autor legible». Vacío si no queda un autor."""
    text = " ".join((text or "").split())
    if not text:
        return ""
    match = _ASSUMED.match(text)
    if match:
        text = re.sub(r"~commonswiki$", "", match.group("name")).strip()
    elif text.lower().startswith("no machine-readable author"):
        return ""
    elif _LICENSE_SENTENCE.match(text):
        match = _ATTRIBUTION.search(text)
        text = match.group("name") if match else ""
    text = _EMAIL.sub("", text)
    text = re.sub(r"^\s*(?:at|on)\s+(?:the\s+)?\w+\s+(?:Wikipedia|Wikimedia Commons)\s*$", "", text, flags=re.I)
    text = _LICENSE_TOKEN.sub("", text)
    text = _RIGHTS_TAIL.sub("", text)
    text = _RIGHTS_HEAD.sub("", text)
    text = re.sub(r"\(\s*[,;]?\s*\)", "", text)
    text = re.sub(r"\s*[,;]\s*(?=\)|$)", "", text)
    text = " ".join(text.split()).strip(" ,;-")
    if not re.search(r"[^\W\d_]", _URL.sub("", text)):
        return ""
    return text


def is_displayable(mime):
    return (mime or "").strip().lower() in DISPLAYABLE_MIMES


def _labels(extmetadata):
    return [" ".join(str(meta(extmetadata, name)).lower().split()) for name in ("License", "LicenseShortName", "UsageTerms")]


_WORDS = (("attribution-noncommercial", "by-nc"), ("attribution-non-commercial", "by-nc"),
          ("noderivatives", "nd"), ("no derivative works", "nd"), ("attribution-share alike", "by-sa"),
          ("attribution-sharealike", "by-sa"), ("share alike", "sa"), ("attribution", "by"))


def _normalize(label):
    label = label.replace("_", "-").replace("creative commons ", "cc ")
    for old, new in _WORDS:
        label = label.replace(old, new)
    return label


def _pieces(extmetadata):
    out = []
    for label in _labels(extmetadata):
        for piece in _SPLIT.split(label):
            piece = _normalize(piece.strip())
            if piece:
                out.append(piece)
    return out


def license_family(extmetadata):
    """Devuelve (código, versión) con código en cc0, public-domain, cc-by, cc-by-sa o un motivo de descarte."""
    labels = _pieces(extmetadata)
    joined = " ".join(labels)
    # Una restricción manda sobre la familia: «CC BY-NC-SA» no es CC BY-SA. Si hay otra licencia admitida en la lista, esa gana.
    admitted_elsewhere = any(_CC_BY.match(l) and not _CC_RESTRICTED.match(l) or l.startswith("cc0") for l in labels)
    for label in labels:
        match = _CC_RESTRICTED.match(label)
        if match and not admitted_elsewhere:
            nc = re.search(r"[- ]nc\b", label)
            return (NON_COMMERCIAL if nc else NO_DERIVATIVES), None
    for label in labels:
        if label.startswith("cc0") or label.startswith("cc zero") or label.startswith("cc-zero"):
            return "cc0", "1.0"
    for label in labels:
        match = _CC_BY.match(label)
        if match:
            return ("cc-by-sa" if match.group("sa") else "cc-by"), match.group("version")
    for label in labels:
        if label.startswith("pd") or "public domain" in label or "dominio público" in label or label in ("cc-pd", "cc pd"):
            return "public-domain", None
    if "gfdl" in joined or "gnu free documentation" in joined:
        return GFDL, None
    if joined.strip():
        return OTHER, None
    return UNKNOWN, None


def classify(extmetadata, mime=None):
    """Clasifica los extmetadata de una imagen (y su `mime`, si se da). Devuelve un dict con `admitted`, `reason` (si se descarta) y los datos de la licencia."""
    code, version = license_family(extmetadata)
    short = meta(extmetadata, "LicenseShortName") or meta(extmetadata, "UsageTerms") or meta(extmetadata, "License")
    author = clean_author(strip_html(meta(extmetadata, "Artist")))
    credit = clean_author(strip_html(meta(extmetadata, "Credit")))
    result = {"admitted": False, "reason": None, "license": short or None, "licenseCode": code, "licenseUrl": None,
              "attributionRequired": None, "author": author or None, "credit": credit or None}
    if code in DISCARD_REASONS:
        result["reason"] = code
        result["licenseCode"] = None
        return result
    if mime is not None and not is_displayable(mime):
        result["reason"] = NOT_DISPLAYABLE
        return result
    url = meta(extmetadata, "LicenseUrl").strip()
    if not url and code in ("cc-by", "cc-by-sa"):
        url = LICENSE_URLS[code] % version
    if not url and code == "cc0":
        url = LICENSE_URLS["cc0"]
    result["licenseUrl"] = url or None
    result["attributionRequired"] = code in ("cc-by", "cc-by-sa")
    if result["attributionRequired"] and not (author or credit):
        result["reason"] = NO_AUTHOR
        return result
    result["admitted"] = True
    return result
