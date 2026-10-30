"""Extracción del glosario desde la caché: acepciones de Wikcionario y primera oración de Wikipedia (sin red).

De la respuesta `action=parse` de Wikcionario toma la sección «Español» y separa las acepciones: cada una es un par
`<dt>` (número y marca semántica) y `<dd>` (texto, seguido de listas de uso, sinónimos, antónimos o ejemplos que no
forman parte de la definición). Del extracto de Wikipedia normaliza los espacios. En ambos casos `first_sentence`
recorta a la primera oración (D5).
"""
import re
import unicodedata
from html.parser import HTMLParser

VOID = {"br", "hr", "img", "meta", "link", "input", "wbr"}
SKIP_IN_SENSE = {"ul", "ol", "dl", "style", "table", "blockquote", "sup", "script", "div", "small"}
# Encabezados de sección que no son una categoría gramatical.
NON_GRAMMAR = ("etimolog", "traducc", "pronunc", "locucion", "referencia", "véase", "ver también", "información", "conjugaci",
               "términos relacionados", "derivad", "proverbio", "refrán", "descendientes", "anagrama", "cita", "forma", "notas")
ABBREVIATIONS = {"etc", "p. ej", "p.ej", "ej", "dr", "dra", "sr", "sra", "pl", "fam", "aprox", "ca", "vs", "a. c", "d. c", "a. m",
                 "p. m", "n.º", "núm", "pág", "pp", "ud", "uds", "art", "cf", "esp", "gen", "sing", "ant", "adj", "sust"}
MULTIWORD_ABBREVIATION = re.compile(r"\b(?:p\. ?ej|a\. ?C|d\. ?C|a\. ?m|p\. ?m)\.|\bn\.º")
MIN_LENGTH, MAX_LENGTH = 12, 300


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def has_class(self, name):
        """True si el nodo o algún descendiente tiene la clase CSS `name`."""
        if name in self.classes:
            return True
        return any(not isinstance(c, str) and c.has_class(name) for c in self.children)

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def text(self, skip=()):
        """Texto visible del nodo, sin las etiquetas de `skip`."""
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in skip:
                parts.append(child.text(skip))
        return "".join(parts)


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [], None)
        self.cursor = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cursor)
        self.cursor.children.append(node)
        if tag not in VOID:
            self.cursor = node

    def handle_startendtag(self, tag, attrs):
        self.cursor.children.append(Node(tag, attrs, self.cursor))

    def handle_endtag(self, tag):
        node = self.cursor
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.cursor = node.parent

    def handle_data(self, data):
        self.cursor.children.append(data)


def parse_html(html):
    tree = _Tree()
    tree.feed(html)
    tree.close()
    return tree.root


def normalize_space(text):
    """Colapsa espacios (incluidos los no separables y los de ancho especial) y quita los de los extremos."""
    text = unicodedata.normalize("NFC", text)
    return " ".join(re.sub(r"[    ​]", " ", text).split())


def strip_notes(text):
    """Quita las notas al pie «[1]» y «[nota 2]» del texto."""
    return re.sub(r"\[\s*(?:nota\s*)?\d+\s*\]", "", text)


def first_sentence(text):
    """Primera oración de `text` (hasta el primer punto que no sea de una abreviatura, una inicial o un decimal)."""
    text = normalize_space(strip_notes(text))
    masked = MULTIWORD_ABBREVIATION.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    for match in re.finditer(r"\.", masked):
        end = match.end()
        if end >= len(text):
            return text
        if not text[end].isspace():
            continue  # decimal, sigla o URL: el punto no cierra la oración
        tokens = text[:match.start()].split()
        last = tokens[-1].lower() if tokens else ""
        pair = " ".join(tokens[-2:]).lower()
        if len(last) == 1 and last.isalpha() and tokens[-1].isupper():
            continue  # inicial: «J. Duke»
        if last in ABBREVIATIONS or pair in ABBREVIATIONS:
            next_word = text[end:].lstrip()[:1]
            if last == "etc" and next_word.isupper():
                return text[:end]  # «etc.» que cierra la oración
            continue
        return text[:end]
    return text


def length_problem(sentence):
    """Motivo por el que una oración recortada necesita revisión a mano, o None."""
    if not sentence.endswith("."):
        return "no termina en punto"
    if len(sentence) < MIN_LENGTH:
        return "demasiado corta (%d caracteres)" % len(sentence)
    if len(sentence) > MAX_LENGTH:
        return "demasiado larga (%d caracteres)" % len(sentence)
    return None


# --- Wikcionario ---------------------------------------------------------------------------------------------------

def _heading_text(node):
    for child in node.children:
        if not isinstance(child, str) and child.tag in ("h2", "h3", "h4", "h5"):
            return child.tag, normalize_space(child.text({"span"}) or child.text())
    return None, None


def _sense_header(dt):
    """(número, marca) de un `<dt>`: «4 Medicina» da (4, «Medicina»); «1» da (1, «»)."""
    text = normalize_space(dt.text())
    match = re.match(r"(\d+)\s*(.*)$", text)
    if not match:
        return None, text
    return int(match.group(1)), match.group(2)


def parse_wiktionary(html):
    """Acepciones de la sección «Español» de una entrada.

    Devuelve `{"languages": [...], "spanish": bool, "senses": [{"n", "mark", "text", "pos", "improper"}], "flexed": bool}`
    (`improper`: Wikcionario marca la definición como impropia):
    `flexed` es verdadero si todas las acepciones están bajo encabezados de forma («Forma adjetiva», «Forma sustantiva»)
    o empiezan con «Femenino de», «Plural de» o «Forma … de».
    """
    root = parse_html(html)
    container = root.children[0] if root.children and not isinstance(root.children[0], str) else root
    languages, senses = [], []
    language, pos = None, None
    for node in container.children:
        if isinstance(node, str):
            continue
        if "mw-heading" in node.classes:
            level, text = _heading_text(node)
            if level == "h2":
                language, pos = text, None
                languages.append(text)
            elif language == "Español":
                pos = text
            continue
        if language != "Español" or node.tag != "dl":
            continue
        current = None
        for child in node.children:
            if isinstance(child, str):
                continue
            if child.tag == "dt":
                current = _sense_header(child)
            elif child.tag == "dd" and current is not None:
                number, mark = current
                current = None
                if number is not None:
                    senses.append({"n": number, "mark": mark, "text": normalize_space(strip_notes(child.text(SKIP_IN_SENSE))),
                                   "pos": pos or "", "improper": child.has_class("definicion-impropia")})
    flexed = bool(senses) and all(
        s["pos"].lower().startswith("forma") or re.match(r"(?:femenino|masculino|plural|forma)\b.*\bde\b", s["text"], re.IGNORECASE)
        for s in senses)
    return {"languages": languages, "spanish": "Español" in languages, "senses": senses, "flexed": flexed}


def entry_status(record):
    """Estado de una entrada de Wikcionario en la caché: sin-entrada, sin-español, forma-flexionada o con-acepciones."""
    if record.get("missing"):
        return "sin-entrada"
    parsed = parse_wiktionary(record["html"])
    if not parsed["spanish"] or not parsed["senses"]:
        return "sin-español"
    if parsed["flexed"]:
        return "forma-flexionada"
    return "con-acepciones"


def sense_text(record, number):
    """Texto literal de la acepción `number` (recortado a la primera oración) o None si no existe."""
    for sense in parse_wiktionary(record["html"])["senses"]:
        if sense["n"] == number:
            return first_sentence(sense["text"])
    return None


# --- Wikipedia -------------------------------------------------------------------------------------------------------

def article_intro(record):
    """Párrafos de la introducción de un artículo cacheado, con los espacios normalizados."""
    return [normalize_space(strip_notes(p)) for p in record.get("extract", "").split("\n") if p.strip()]


def article_first_sentence(record):
    paragraphs = article_intro(record)
    return first_sentence(paragraphs[0]) if paragraphs else None
