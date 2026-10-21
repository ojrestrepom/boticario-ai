"""Normalización de nombres científicos, separación de celdas y comparación de autores.

Solo biblioteca estándar, Python 3.9. Las reglas están en `specs/catalog-seed/spec.md` del cambio
`consolidate-catalog-seed` (requisito «Normalización de nombres científicos»).
"""
import html
import re
import unicodedata

# --- Rangos --------------------------------------------------------------------------------------------------------
# Clave: marcador en minúsculas y sin punto final. Valor: rango canónico de la clave.
_RANKS_DOT_OPTIONAL = {
    "subsp": "subsp.", "ssp": "subsp.", "subspecies": "subsp.", "nothosubsp": "subsp.",
    "var": "var.", "variety": "var.", "nothovar": "var.",
    "forma": "f.", "subvar": "subvar.", "convar": "convar.", "unranked": "unranked",
}
# Marcadores que solo se reconocen con punto final (sin él serían ambiguos con iniciales o epítetos).
_RANKS_DOT_REQUIRED = {
    "f": "f.", "fo": "f.", "nothof": "f.", "subf": "subf.", "prol": "prol.", "proles": "prol.", "lus": "lus.", "lusus": "lus.",
}
# Rangos raros de WCVP: se conservan tal cual para que la clave del índice y la del texto coincidan.
_RANKS_EXTRA = ("monstr", "grex", "stirps", "provar", "modif", "psp", "mut", "sublusus", "subap", "subspecioid",
                "subsubsp", "positio", "micromorphe", "agamosp", "nid", "ecas", "group", "microf", "microgène",
                "subproles")
_RANKS_DOT_REQUIRED.update({r: r + "." for r in _RANKS_EXTRA})

# Rangos de la columna `infraspecific_rank` de WCVP y de `taxonRank` de WFO (palabras completas).
_RANK_COLUMN = {"subspecies": "subsp.", "variety": "var.", "form": "f.", "subvariety": "subvar.", "subform": "subf.",
                "prole": "prol.", "lusus": "lus.", "convar": "convar.", "convariety": "convar.", "unranked": "unranked"}

_GLUE_MARKERS = ("nothosubsp", "nothovar", "subsp", "ssp", "subvar", "convar", "subf", "nothof", "forma", "prol",
                 "var", "lus", "f")

# Partículas de autor en minúscula: no son epítetos infraespecíficos implícitos.
AUTHOR_PARTICLES = frozenset((
    "ex", "de", "del", "della", "des", "di", "da", "dos", "das", "du", "van", "von", "der", "den", "ten", "ter", "la",
    "le", "el", "al", "af", "zu", "et", "in", "and", "y", "e", "sensu", "auct", "non", "nec", "hort", "fide", "ined",
    "nom", "orth", "pro", "emend", "mscr", "cf", "aff",
))

_QUALIFIER_RE = re.compile(
    r"(?:(?<=\s)|^)(?:aggr\.?|agg\.?|s\.\s?str\.?|s\.\s?l\.?|sensu\s+lato|sensu\s+stricto)(?=\s|$|\)|,)")
_CULTIVAR_QUOTED_RE = re.compile(r"(?:(?<=\s)|^)['‘`][^'’`]+['’`]")
_CULTIVAR_CV_RE = re.compile(r"(?:(?<=\s)|^)cv\.?\s+(?:[A-Z][\w\-]*\s?)+")
_TRAILING_PAREN_RE = re.compile(r"\s*\(([^()]*)\)\s*$")
_GENUS_RE = re.compile(r"^[^\W\d_][\w\-]*$", re.UNICODE)
_ROMAN_RE = re.compile(r"^[ivx]+$")


class ParsedName(object):
    """Resultado de `parse_name`. `key_full` es la clave de búsqueda principal y `key_alt` la de reserva (autónimos)."""

    def __init__(self, raw):
        self.raw = raw
        self.genus = ""
        self.species = ""
        self.infra_rank = ""
        self.infra_epithet = ""
        self.hybrid = False
        self.chimera = False
        self.author = ""
        self.species_author = ""
        self.author_removed = []     # notas quitadas del autor por `clean_author`
        self.flags = []
        self.genus_only = False
        self.autonym = False
        self.implicit_infra = False
        self.key_full = None
        self.key_alt = None
        self.key_binomial = None
        self.ok = False

    @property
    def infraspecific(self):
        return bool(self.infra_epithet)

    @property
    def display(self):
        """Nombre canónico legible: `Genus [×] species [rango epíteto]`."""
        if not self.genus:
            return ""
        sign = "+" if self.chimera else "×"
        genus = self.genus[:1].upper() + self.genus[1:]
        parts = [genus]
        if self.species:
            parts.append(sign if self.hybrid else "")
            parts.append(self.species)
            if self.infra_epithet:
                if self.infra_rank:
                    parts.append(self.infra_rank)
                parts.append(self.infra_epithet)
        return " ".join(p for p in parts if p)

    def to_dict(self):
        keys = ("raw", "genus", "species", "infra_rank", "infra_epithet", "hybrid", "chimera", "author", "species_author",
                "flags", "genus_only", "autonym", "implicit_infra", "key_full", "key_alt", "key_binomial", "ok")
        return {k: getattr(self, k) for k in keys}

    def __repr__(self):
        return "ParsedName(%r -> %r, flags=%r)" % (self.raw, self.key_full, self.flags)


# --- Texto ---------------------------------------------------------------------------------------------------------

def clean_text(text):
    """NFC, entidades HTML decodificadas, sin comillas dobles y con los espacios colapsados."""
    s = html.unescape(text or "")
    s = unicodedata.normalize("NFC", s)
    for ch in (" ", " ", " ", "\t", "\n", "\r"):
        s = s.replace(ch, " ")
    for ch in ('"', "“", "”", "„"):
        s = s.replace(ch, "")
    return re.sub(r"\s+", " ", s).strip()


def canonical_rank(raw):
    """Rango canónico de un marcador de texto (`ssp.`, `var`, `forma`...) o None. Respeta la regla del punto."""
    if not raw:
        return None
    tok = raw.strip()
    base = tok.lower().rstrip(".")
    has_dot = tok.endswith(".")
    if base in _RANKS_DOT_OPTIONAL:
        return _RANKS_DOT_OPTIONAL[base]
    if has_dot and base in _RANKS_DOT_REQUIRED:
        return _RANKS_DOT_REQUIRED[base]
    return None


def rank_from_column(raw):
    """Rango canónico desde la columna de un backbone (`infraspecific_rank` de WCVP o `taxonRank` de WFO)."""
    if not raw:
        return ""
    base = raw.strip().lower()
    if base in _RANK_COLUMN:
        return _RANK_COLUMN[base]
    c = canonical_rank(base if base.endswith(".") else base + ".") or canonical_rank(base)
    return c or ""


def valid_epithet(epithet):
    """Un epíteto interpretable: minúsculas, sin espacios, sin numerales romanos sueltos."""
    if not epithet or not epithet[0].islower():
        return False
    if any(ch.isspace() for ch in epithet):
        return False
    if _ROMAN_RE.match(epithet.lower()) and len(epithet) <= 5:
        return False
    return True


def make_keys(genus, species, infra_rank="", infra_epithet=""):
    """(key_full, key_binomial) a partir de las partes ya normalizadas."""
    binomial = "%s %s" % (genus.lower(), species.lower())
    if infra_epithet:
        parts = [binomial] + ([infra_rank] if infra_rank else []) + [infra_epithet.lower()]
        return " ".join(parts), binomial
    return binomial, binomial


def _split_epithet(token):
    """Separa `roseaL.` en (`rosea`, `L.`). Devuelve (epíteto, resto) o (None, token)."""
    i = 0
    while i < len(token) and (token[i].islower() or (token[i] == "-" and i > 0)):
        i += 1
    if i == 0:
        return None, token
    epithet, rest = token[:i].rstrip("-"), token[i:]
    if rest.startswith(".") and len(rest) == 1:
        rest = ""
    return epithet, rest


def _glued_splits(token):
    """Posibles separaciones de `arvensisvar.piperascens` en (prefijo, marcador, resto)."""
    out = []
    for pos in range(2, len(token)):
        for marker in _GLUE_MARKERS:
            end = pos + len(marker)
            if token.startswith(marker, pos) and end < len(token) - 1 and token[end] == "." and token[end + 1].islower():
                if token[:pos].isalpha() or token[:pos].replace("-", "").isalpha():
                    out.append((token[:pos], marker + ".", token[end + 1:]))
    return out


def _expand_glued(tokens, index, hint_species):
    """Si tokens[index] lleva un marcador pegado, lo separa en tres. Devuelve la lista (posiblemente la misma)."""
    token = tokens[index]
    if not token or not token[0].islower():
        return tokens, False
    splits = _glued_splits(token)
    if not splits:
        return tokens, False
    choice = splits[0]
    if hint_species:
        for cand in splits:
            if cand[0].lower() == hint_species:
                choice = cand
                break
    return tokens[:index] + [choice[0], choice[1], choice[2]] + tokens[index + 1:], True


def _looks_like_name(text):
    """Un calificador en paréntesis que parece un nombre común: dos o más palabras capitalizadas sin punto."""
    words = text.split()
    return len(words) >= 2 and all(re.match(r"^[A-Z][a-zà-ÿ]{2,}$", w) for w in words)


def _is_epithet_candidate(token, allow_capital):
    """Token que puede ser el epíteto tras un marcador: minúscula, o capitalizado sin punto (solo antes de todo autor)."""
    if not token or token.lower() in AUTHOR_PARTICLES or token.startswith("("):
        return False
    if token[0].islower():
        return True
    return allow_capital and token[0].isupper() and token.isalpha() and len(token) >= 3


def _split_leading_marker(token):
    """`var.piperascens` -> (`var.`, `piperascens`); None si el token no empieza por un marcador pegado."""
    low = token.lower()
    for marker in sorted(_GLUE_MARKERS + tuple(_RANKS_EXTRA) + ("lusus", "proles"), key=len, reverse=True):
        if low.startswith(marker + ".") and len(token) > len(marker) + 1 and token[len(marker) + 1].islower():
            return token[:len(marker) + 1], token[len(marker) + 1:]
    return None


def _hint_species(hint):
    if not hint:
        return ""
    if isinstance(hint, (tuple, list)):
        return str(hint[-1]).lower()
    parts = str(hint).split()
    return parts[-1].lower() if parts else ""


def parse_name(text, hint=None):
    """Interpreta un nombre científico. `hint` («Genus species» o tupla) desambigua marcadores pegados."""
    p = ParsedName(text)
    flags = p.flags
    s = clean_text(text)
    if not s:
        flags.append("empty")
        return p

    # Cultivares y calificadores (se quitan con marca).
    if _CULTIVAR_QUOTED_RE.search(s) or _CULTIVAR_CV_RE.search(s):
        s = _CULTIVAR_CV_RE.sub(" ", _CULTIVAR_QUOTED_RE.sub(" ", s))
        flags.append("cultivar_removed")
    if _QUALIFIER_RE.search(s):
        s = _QUALIFIER_RE.sub(" ", s)
        flags.append("qualifier_removed")
    s = re.sub(r"\s+", " ", s).strip()
    m = _TRAILING_PAREN_RE.search(s)
    if m and len(s[:m.start()].split()) >= 2:
        inner = m.group(1).strip()
        if inner and (inner[0].islower() or _looks_like_name(inner)):
            s = s[:m.start()].strip()
            flags.append("qualifier_removed")

    # Signos híbridos como tokens aparte.
    s = s.replace("×", " × ")
    s = re.sub(r"(?:(?<=\s)|^)\+(?=[^\W\d_])", "+ ", s)
    tokens = s.split()
    if not tokens:
        flags.append("empty")
        return p

    i = 0
    if tokens[0] in ("×", "+") or (tokens[0] in ("x", "X") and len(tokens) > 1 and tokens[1][:1].isupper()):
        p.hybrid = True
        p.chimera = tokens[0] == "+"
        i = 1
    if i >= len(tokens) or not _GENUS_RE.match(tokens[i]):
        flags.append("unparsed")
        return p
    p.genus = tokens[i].lower()
    i += 1
    rest = tokens[i:]

    # Solo género: nada más, `sp`/`spp`, o el género seguido de un autor.
    if not rest or rest[0].lower() in ("sp", "sp.", "spp", "spp."):
        p.genus_only = True
        flags.append("genus_only")
        _finish_hybrid_flags(p)
        return p
    if rest[0] in ("×", "+") or (rest[0] in ("x", "X") and len(rest) > 1 and rest[1][:1].islower()):
        p.hybrid = True
        p.chimera = p.chimera or rest[0] == "+"
        rest = rest[1:]
    if not rest or not rest[0][:1].islower():
        p.genus_only = True
        p.author = " ".join(rest)
        flags.append("genus_only")
        _finish_hybrid_flags(p)
        return p

    hint_species = _hint_species(hint)
    rest, _ = _expand_glued(rest, 0, hint_species)
    species, glued = _split_epithet(rest[0])
    if not species or not valid_epithet(species):
        flags.append("unparsed")
        return p
    p.species = species
    tokens_after = ([glued] if glued else []) + rest[1:]

    stage = "pre"
    author_tokens = []
    infra_author_tokens = []
    species_author = ""
    j = 0
    pending = None
    while j < len(tokens_after):
        t = tokens_after[j]
        if stage != "author" and t[0].islower() and not canonical_rank(t):
            lead = _split_leading_marker(t)
            if lead:
                tokens_after = tokens_after[:j] + [lead[0], lead[1]] + tokens_after[j + 1:]
                t = tokens_after[j]
            elif stage == "pre":
                tokens_after, did = _expand_glued(tokens_after, j, "")
                t = tokens_after[j]
        marker = canonical_rank(t)
        nxt = tokens_after[j + 1] if j + 1 < len(tokens_after) else None
        if marker and nxt is not None and canonical_rank(nxt):
            pending = marker  # varios marcadores seguidos: cuenta el último
            j += 1
            continue
        if marker and nxt is not None and _is_epithet_candidate(nxt, stage == "pre"):
            if stage == "author":
                species_author = " ".join(author_tokens)
                author_tokens = []
            elif stage == "infra":
                flags.append("multiple_infra")
                infra_author_tokens = []
            epi, glue_author = _split_epithet(nxt) if nxt[0].islower() else (nxt.lower(), "")
            if nxt[0].isupper():
                flags.append("capitalized_epithet")
            if not epi:
                flags.append("unparsed")
                return p
            p.infra_rank = marker
            p.infra_epithet = epi
            stage = "infra"
            infra_author_tokens = [glue_author] if glue_author else []
            pending = None
            j += 2
            continue
        if stage == "pre":
            if t in ("×", "x", "X", "+") and (j + 1 < len(tokens_after)):
                flags.append("hybrid_formula")
                return p
            lowered = t.lower().rstrip(".")
            if t[0].islower() and not t.endswith(".") and lowered not in AUTHOR_PARTICLES and not t.startswith("("):
                epi, glue_author = _split_epithet(t)
                if epi and valid_epithet(epi):
                    p.infra_epithet = epi
                    p.implicit_infra = True
                    flags.append("implicit_infra")
                    stage = "infra"
                    infra_author_tokens = [glue_author] if glue_author else []
                    j += 1
                    continue
            stage = "author"
            author_tokens.append(t)
        elif stage == "author":
            author_tokens.append(t)
        else:
            infra_author_tokens.append(t)
        j += 1
    if pending and not p.infra_epithet:
        pending = None

    if stage == "infra":
        p.author = " ".join(infra_author_tokens).strip()
        p.species_author = species_author
    else:
        p.author = " ".join(author_tokens).strip()
        p.species_author = p.author
    p.author, removed_a = clean_author(p.author)
    p.species_author, removed_s = clean_author(p.species_author)
    if removed_a or removed_s:
        p.author_removed = removed_a or removed_s
        flags.append("author_note_removed")

    if p.infra_epithet and not valid_epithet(p.infra_epithet):
        flags.append("invalid_epithet")
        return p
    if p.infra_epithet and p.infra_epithet == p.species:
        p.autonym = True
        flags.append("autonym")

    p.key_full, p.key_binomial = make_keys(p.genus, p.species, p.infra_rank, p.infra_epithet)
    if p.autonym:
        p.key_alt = p.key_full
        p.key_full = p.key_binomial
    p.ok = True
    _finish_hybrid_flags(p)
    p.flags = sorted(set(p.flags))
    return p


def _strip_trailing_group(text):
    """Quita un grupo final entre paréntesis (balanceado) si queda texto antes de él; None si no hay tal grupo."""
    t = text.rstrip()
    if t.endswith(")."):
        t = t[:-1]
    if not t.endswith(")"):
        return None
    depth = 0
    for idx in range(len(t) - 1, -1, -1):
        if t[idx] == ")":
            depth += 1
        elif t[idx] == "(":
            depth -= 1
            if depth == 0:
                prefix = t[:idx].rstrip()
                return prefix if prefix else None
    return None


_AUTHOR_TAIL_WORDS_RE = re.compile(r"^(.*?\.),\s+[a-z]+(?:\s+[a-z]+)*$")
_DOUBLED_AUTHOR_RE = re.compile(r"^([A-Z][A-Za-z\-]*\.)\1$")


def clean_author(author):
    """Autor sin notas: quita grupos finales entre paréntesis tras un autor (sinónimos), colas en minúscula tras coma y
    autores duplicados (`L.L.`). Conserva el autor del basiónimo, que va al principio (`(L.) Moench`).

    Devuelve (autor limpio, lista de notas quitadas).
    """
    a = (author or "").strip().strip(",;").strip()
    removed = []
    while True:
        prefix = _strip_trailing_group(a)
        if prefix is None:
            break
        removed.append(a[len(prefix):].strip())
        a = prefix.strip().strip(",;").strip()
    m = _AUTHOR_TAIL_WORDS_RE.match(a)
    if m:
        removed.append(a[len(m.group(1)):].strip(", "))
        a = m.group(1)
    m = _DOUBLED_AUTHOR_RE.match(a)
    if m:
        removed.append(m.group(1))
        a = m.group(1)
    return a, removed


def _tidy_author(a):
    return clean_author(a)[0]


def _finish_hybrid_flags(p):
    if p.hybrid:
        p.flags.append("chimera" if p.chimera else "hybrid")
    p.flags = sorted(set(p.flags))


# --- Separación de celdas de las fuentes -------------------------------------------------------------------------

_ABBREV_RE = re.compile(r"^([A-Z])\.\s*([a-z×].*)$")
_FULL_NAME_RE = re.compile(r"^(?:[×+]\s*)?[A-Z][a-zà-ÿ\-]+\s+(?:[×x]\s*)?[a-z]")
_ABBREV_NAME_RE = re.compile(r"^[A-Z]\.\s*(?:[×x]\s*)?[a-z]")
_SYN_RE = re.compile(r"^(?:syn|synonyms?)\.?:?\s+", re.IGNORECASE)


def _looks_like_another_name(text):
    t = text.strip()
    return bool(_FULL_NAME_RE.match(t) or _ABBREV_NAME_RE.match(t))


def _split_commas(fragment):
    """Separa por coma solo donde lo siguiente parece otro nombre (`Género especie` o `G. especie`)."""
    pieces = [x for x in fragment.split(",")]
    out = [pieces[0]]
    for piece in pieces[1:]:
        if _looks_like_another_name(piece):
            out.append(piece)
        else:
            out[-1] = out[-1] + "," + piece
    return out


def _first_word(fragment):
    m = re.match(r"^(?:[×+]\s*)?([A-Z][a-zà-ÿ\-]+)\b", fragment.strip())
    return m.group(1) if m else None


def _expand_abbreviations(fragments):
    """Expande `C. azarolus` con el género completo más cercano de la misma celda (el anterior gana en empates)."""
    genera = [_first_word(f) if not _ABBREV_NAME_RE.match(f.strip()) else None for f in fragments]
    out = []
    for idx, frag in enumerate(fragments):
        m = _ABBREV_RE.match(frag.strip())
        if not m:
            out.append(frag)
            continue
        initial = m.group(1)
        best = None
        for dist in range(1, len(fragments)):
            for cand in (idx - dist, idx + dist):
                if 0 <= cand < len(fragments) and genera[cand] and genera[cand].startswith(initial):
                    best = genera[cand]
                    break
            if best:
                break
        out.append("%s %s" % (best, m.group(2)) if best else frag)
    return out


_SYN_GROUP_RE = re.compile(r"\(\s*(?:syn|synonyms?)\b\.?:?", re.IGNORECASE)
_GENUS_BRACKET_RE = re.compile(r"^([A-Z][a-zà-ÿ\-]+)\s*\[([^\]]*)\]\s*\.?$")
_BRACKET_INTRO_RE = re.compile(r"^(?:various\s+)?species\s+(?:including|such\s+as)\s+", re.IGNORECASE)
_VARIOUS_TAIL_RE = re.compile(r"\s+(?:and|&)\s+[A-Z][a-zà-ÿ\-]+\s*\(\s*various\s+species\s*\)", re.IGNORECASE)
_VARIOUS_RE = re.compile(r"\s*\(\s*various\s+species\s*\)", re.IGNORECASE)


def _group_end(text, start):
    """Índice del paréntesis que cierra el que abre en `start`, o -1 si queda sin cerrar."""
    depth = 0
    for idx in range(start, len(text)):
        if text[idx] == "(":
            depth += 1
        elif text[idx] == ")":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def _drop_synonym_groups(text, changes):
    """Quita los grupos `(syn. ...)` (con sus paréntesis anidados). Si el grupo no cierra, descarta hasta el final de la celda."""
    while True:
        m = _SYN_GROUP_RE.search(text)
        if not m:
            return text
        end = _group_end(text, m.start())
        if end < 0:
            changes.append("sinónimos descartados (grupo sin cerrar): %s" % text[m.start():].strip())
            return text[:m.start()].rstrip()
        changes.append("sinónimos descartados: %s" % text[m.start():end + 1])
        text = (text[:m.start()].rstrip() + " " + text[end + 1:].lstrip()).strip()


def _expand_bracket_list(text, changes):
    """`Genus [various species including G. a L.; G. b L.]` -> `Genus a L.; Genus b L.` (solo las especies que nombra)."""
    m = _GENUS_BRACKET_RE.match(text)
    if not m:
        return text
    genus, body = m.group(1), _BRACKET_INTRO_RE.sub("", m.group(2).strip())
    items = []
    for item in body.split(";"):
        item = item.strip()
        am = _ABBREV_RE.match(item)
        if am and genus.startswith(am.group(1)):
            item = "%s %s" % (genus, am.group(2))
        if item:
            items.append(item)
    changes.append("lista entre corchetes expandida: %s" % "; ".join(items))
    return "; ".join(items)


def split_source_cell(source, cell):
    """Como `split_source_names`, pero devuelve también las notas de los cambios hechos a la celda: (nombres, [nota])."""
    src = (source or "").lower()
    changes = []
    if src in ("ema", "ema_json", "ema_pdf", "efsa"):
        text = unicodedata.normalize("NFC", html.unescape(cell or ""))
        text = re.sub(r"\s+", " ", text).strip()
        if src != "efsa":
            if text.lower().startswith("combination"):
                return [], ["ficha de combinación: la celda no aporta especies"]
            text = _expand_bracket_list(text, changes)
            before = text
            text = _VARIOUS_RE.sub("", _VARIOUS_TAIL_RE.sub("", text)).strip()
            if text != before:
                changes.append("«(various species)» descartado; solo salen las especies nombradas")
            text = _drop_synonym_groups(text, changes)
        fragments = []
        for chunk in re.split(r"[;$]" if src == "efsa" else r";", text):
            chunk = chunk.strip()
            if not chunk or chunk.lower().startswith("combination"):
                continue
            if src != "efsa" and _SYN_RE.match(chunk):
                changes.append("sinónimo descartado: %s" % chunk)
                continue
            fragments.extend(_split_commas(chunk) if src != "efsa" else [chunk])
        cleaned = []
        for frag in fragments:
            frag = _SYN_RE.sub("", frag.strip()).strip().rstrip(",;")
            if len(frag) >= 4 and not frag.lower().startswith("combination"):
                cleaned.append(frag)
        return _expand_abbreviations(cleaned), changes
    one = clean_text(cell)
    return ([one] if one else []), changes


def split_source_names(source, cell):
    """Nombres científicos contenidos en una celda de una fuente.

    - `ema`, `ema_json`, `ema_pdf`: decodifica entidades HTML. Una celda que empieza por «Combination» no aporta
      nombres. Quita los grupos `(syn. ...)` y los fragmentos `syn. ...` (los sinónimos que la celda marca no son
      entradas), quita `(various species)` y `and Género (various species)` (solo salen las especies nombradas),
      expande `Género [various species including G. a L.; G. b L.]` a las especies listadas, separa por `;` y por coma
      cuando lo siguiente parece otro nombre, expande géneros abreviados y descarta fragmentos de menos de 4 caracteres.
    - `efsa`: separa por `;` y `$`, con las mismas reglas de abreviatura, sin separar por coma.
    - Las demás fuentes traen un nombre por celda.
    """
    return split_source_cell(source, cell)[0]


# --- Autores -------------------------------------------------------------------------------------------------------

_NOISE_TOKENS = frozenset(("ex", "in", "et", "and", "al", "fil", "f", "ined", "de", "del", "van", "von", "der", "den",
                           "da", "di", "du", "la", "le", "ter", "ten", "dos", "das", "des", "af", "zu"))
_AUTHOR_SPLIT_RE = re.compile(r"\s*&\s*|\s+et\s+|\s+ex\s+|\s+in\s+|\s*,\s*", re.IGNORECASE)


def _ascii_lower(text):
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower()


def _split_parenthetical(author):
    a = (author or "").strip()
    if a.startswith("("):
        depth = 0
        for idx, ch in enumerate(a):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return a[1:idx], a[idx + 1:]
        return a[1:], ""
    return "", a


def _surnames(part):
    """Apellidos de un grupo de autores: sin iniciales, `ex`, `&`, `et`, `in`; `L.`, `Linn.` y `Linnaeus` iguales."""
    names = []
    for unit in _AUTHOR_SPLIT_RE.split(part or ""):
        unit = unit.strip()
        if not unit:
            continue
        compact = re.sub(r"[\s.]", "", unit).lower()
        if compact in ("l", "lf", "linn", "linnf", "linne", "linnaeus", "linnaei", "linnfil"):
            names.append("linnaeus")
            continue
        pieces = [x for x in re.split(r"[.\s]+", unit) if x]
        merged = []
        for piece in pieces:
            if piece.startswith("-") and merged:
                merged[-1] = merged[-1] + piece
            else:
                merged.append(piece)
        for piece in merged:
            norm = re.sub(r"[^a-z\-]", "", _ascii_lower(piece))
            if len(norm) <= 1 or norm in _NOISE_TOKENS:
                continue
            names.append("linnaeus" if norm in ("linn", "linne", "linnaeus", "linnaei") else norm)
    return names


def _surname_match(a, b):
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 3 and long_.startswith(short)


def _match_count(xs, ys):
    pool = list(ys)
    count = 0
    for x in xs:
        for k, y in enumerate(pool):
            if _surname_match(x, y):
                count += 1
                del pool[k]
                break
    return count


def author_score(query, candidate):
    """Puntaje 0..1: apellidos coincidentes (basiónimo con basiónimo, combinación con combinación) sobre el máximo."""
    qb, qc = _split_parenthetical(query)
    cb, cc = _split_parenthetical(candidate)
    qb, qc, cb, cc = _surnames(qb), _surnames(qc), _surnames(cb), _surnames(cc)
    total = max(len(qb) + len(qc), len(cb) + len(cc))
    if total == 0:
        return 0.0
    return (_match_count(qb, cb) + _match_count(qc, cc)) / float(total)


def authors_match(query, candidate, threshold=0.5):
    return author_score(query, candidate) >= threshold
