"""Extracción de las secciones de seguridad de los PDF de la EMA (4.3, 4.4 y 4.5) con pdfminer.six y coordenadas.

Implementa el modo «pdfminer-cols» del spike 3.1 (spikes/ema-pdf/README.md): cada línea se asigna a la columna izquierda
(uso bien establecido), a la derecha (uso tradicional), a ambas o a ninguna (documentos de una columna), se descartan las
cabeceras, los pies y las notas al pie (fuente menor que el 90 % de la mediana de la página), y las secciones se cortan por
sus encabezados numerados. La declaración pública no tiene secciones numeradas: se toma CONCLUSIONS y se marca
«declaración pública sin datos de seguridad» cuando no menciona ninguna de las categorías de seguridad.

La parte que lee el PDF (lines_from_pdf) necesita pdfminer.six (requirements.txt); el resto trabaja sobre líneas ya
extraídas y se prueba sin la dependencia. Los PDF son datos no confiables: solo se leen, nunca se ejecuta nada de ellos.
"""
import hashlib
import re
from pathlib import Path

from .sources import SourceError

NEEDS_PDFMINER = ("leer los PDF de la EMA necesita pdfminer.six; use el entorno virtual: "
                  "tools/catalog-seed/.venv/bin/python3 -I tools/catalog-seed/cli.py ... (véase requirements.txt)")
TOOL = "pdfminer.six pdfminer-cols"
NO_SAFETY_NOTE = "declaración pública sin datos de seguridad"

# Título canónico de cada sección; tolera el título partido en dos líneas y un dígito de nota al pie pegado.
HEADINGS = {
    "4.3": r"Contraindications\d*",
    "4.4": r"Special warnings and precautions? for use\d*",
    "4.5": r"Interactions with other medicinal products and other forms of(\s+interaction\d*)?",
}
# Versión sin espacios de cada título: algunos PDF parten las líneas dentro de las palabras y pdfminer pierde el espacio.
COMPACT_HEADINGS = {number: re.sub(r"\\s\+|\s", "", pattern).replace("(\\s+", "(") for number, pattern in HEADINGS.items()}
SECTION_TITLES = {"4.3": "Contraindications", "4.4": "Special warnings and precautions for use",
                  "4.5": "Interactions with other medicinal products and other forms of interaction"}
# Las referencias cruzadas llevan comillas tras el número (4.4 ‘Special…’); algunas monografías escriben el encabezado sin punto («4.3 Contraindications»). Las monografías de 2009 ponen el número solo en una línea («4.5.») y el título en la siguiente.
NUMBERED = re.compile(r"^(4\.\d{1,2})\.?(\s+[A-Z]|$)")
NOISE = [
    re.compile(r"^(European Union|Community) herbal monograph on .*$", re.IGNORECASE),
    re.compile(r"^EMA/HMPC/\d+/\d+\s*(Page \d+/\d+)?\s*$"),
    re.compile(r"^Page \d+/\d+\s*$"),
    re.compile(r"^Public statement on .*Page \d+/\d+$"),
]
COLUMN_HEADER = re.compile(r"^Well-established use\s+Traditional use$")
COLUMN_LABELS = {"left": "well_established_use", "right": "traditional_use", "both": "both_columns", "single": "single_column"}
# Una declaración pública «tiene datos de seguridad» si sus conclusiones hablan de alguna de estas categorías.
SAFETY_WORDS = re.compile(
    r"contraindicat|interaction|adverse|warning|precaution|genotox|carcinogen|hepatotox|toxicity|toxic\b|"
    r"safety|undesirable|should not be used|not recommended", re.IGNORECASE)


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def is_noise(line):
    return any(rx.match(line) for rx in NOISE)


SAME_BASELINE = 1.5   # puntos
MAX_JOIN_GAP = 3.0    # menos que la separación entre las dos columnas
GLUED_GAP = 1.2       # fragmentos pegados: partes de una misma palabra


def merge_fragments(items):
    """Une los fragmentos de una misma línea visual que pdfminer reparte en varias líneas de texto.

    Algunos PDF de la EMA (por ejemplo quercus-cortex) parten una línea en trozos, incluso dentro de una palabra
    («4.5. Interactions with other m» + «edicinal products...»), y eso rompe los encabezados. Se unen los trozos de la
    misma línea base cuya separación es menor que la de las columnas: sin espacio si están pegados, con un espacio si no.
    items: tuplas (x0, x1, y1, texto, tamaño).
    """
    merged = []
    for item in sorted(items, key=lambda r: (-round(r[2], 1), r[0])):
        if merged:
            x0, x1, y1, text, size = merged[-1]
            gap = item[0] - x1
            if abs(item[2] - y1) <= SAME_BASELINE and 0 <= gap <= MAX_JOIN_GAP:
                joined = text + ("" if gap < GLUED_GAP else " ") + item[3]
                merged[-1] = (x0, max(x1, item[1]), y1, joined, size)
                continue
        merged.append(tuple(item))
    return [r[:4] for r in merged]


def lines_from_pdf(path):
    """Líneas del PDF en orden de lectura: [{page, text, col}] con col left, right, both o single."""
    try:
        from pdfminer.high_level import extract_pages  # dependencia opcional
        from pdfminer.layout import LTChar, LTTextContainer, LTTextLine
    except ImportError:
        raise SourceError(NEEDS_PDFMINER)
    from statistics import median
    out, split = [], None
    for number, page in enumerate(extract_pages(str(path)), 1):
        raw = []
        for element in page:
            if isinstance(element, LTTextContainer):
                for line in element:
                    if isinstance(line, LTTextLine) and norm(line.get_text()):
                        sizes = [c.size for c in line if isinstance(c, LTChar)]
                        raw.append((line.x0, line.x1, line.y1, norm(line.get_text()), median(sizes) if sizes else 0))
        body_size = median([r[4] for r in raw]) if raw else 0
        raw = merge_fragments([r for r in raw if r[4] >= 0.9 * body_size])
        for x0, _, _, text in raw:
            if text == "Traditional use" and x0 > 150:
                split = x0 - 15
        raw.sort(key=lambda r: (-round(r[2]), r[0]))
        for x0, x1, _, text in raw:
            if is_noise(text):
                continue
            if split is None or NUMBERED.match(text) or text.startswith("Well-established use"):
                column = "single"
            elif x0 >= split:
                column = "right"
            elif x1 > split + 20:
                column = "both"
            else:
                column = "left"
            out.append({"page": number, "text": text, "col": column})
    return out


def heading_length(lines, index, number):
    """Líneas que ocupa el encabezado completo de la sección que empieza en index (0 si no es el encabezado canónico).

    El título puede ir en la misma línea que el número, partido en dos líneas o, en las monografías antiguas, en las líneas
    siguientes al número solo. Se prueba con 3, 2 y 1 líneas y gana la más larga que encaja entera.
    """
    for count in (4, 3, 2, 1):
        joined = " ".join(l["text"] for l in lines[index:index + count])
        if re.fullmatch(re.escape(number) + r"\.?\s+" + HEADINGS[number], joined):
            return count
        compact = re.sub(r"\s+", "", joined)
        if re.fullmatch(re.escape(number) + r"\.?" + COMPACT_HEADINGS[number], compact):
            return count
    return 0


def find_starts(lines):
    starts = {}
    for index, line in enumerate(lines):
        match = NUMBERED.match(line["text"])
        if not match or match.group(1) not in HEADINGS or match.group(1) in starts:
            continue
        if heading_length(lines, index, match.group(1)):
            starts[match.group(1)] = index
    return starts


def section_body(lines, index, number):
    body_from = index + heading_length(lines, index, number)
    end = len(lines)
    for j in range(body_from, len(lines)):
        if NUMBERED.match(lines[j]["text"]):
            end = j
            break
    return lines[body_from:end]


def build_text(body):
    return " ".join(l["text"] for l in body
                    if not COLUMN_HEADER.match(l["text"]) and l["text"] not in ("Well-established use", "Traditional use"))


def labelled_text(parts):
    """Texto único de una sección con las columnas rotuladas; si solo hay una columna sin rótulo, el texto a secas."""
    if list(parts) == ["single_column"]:
        return parts["single_column"]
    return " ".join("[%s] %s" % (label, text) for label, text in parts.items())


def sections_from_lines(lines):
    """Secciones 4.3, 4.4 y 4.5 por columna, o CONCLUSIONS si no hay secciones numeradas.

    Devuelve {"sections": {num: {heading, page_from, page_to, columns: {etiqueta: texto}, text}}, "statement": ...}.
    """
    sections = {}
    starts = find_starts(lines)
    for number, index in starts.items():
        body = section_body(lines, index, number)
        columns = {}
        for column in ("left", "right", "both", "single"):
            part = [l for l in body if l["col"] == column]
            text = build_text(part) if part else ""
            if text:
                columns[COLUMN_LABELS[column]] = text
        sections[number] = {"heading": SECTION_TITLES[number], "page_from": lines[index]["page"],
                            "page_to": body[-1]["page"] if body else lines[index]["page"],
                            "columns": columns, "text": labelled_text(columns)}
    statement = None
    if not starts:
        for index, line in enumerate(lines):
            if re.fullmatch(r"conclusions?:?", line["text"], re.IGNORECASE):   # «CONCLUSIONS» o «Conclusions»
                text = " ".join(l["text"] for l in lines[index + 1:])
                statement = {"heading": "CONCLUSIONS", "page_from": line["page"], "page_to": lines[-1]["page"], "text": text,
                             "safety_data": bool(SAFETY_WORDS.search(text))}
                break
    return {"sections": sections, "statement": statement}


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_pdf(path):
    """Extrae un PDF de la EMA: {sha256, tool, sections, statement}."""
    result = sections_from_lines(lines_from_pdf(path))
    result["sha256"] = sha256_of(path)
    result["tool"] = TOOL
    return result
