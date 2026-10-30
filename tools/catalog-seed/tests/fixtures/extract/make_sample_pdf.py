"""Genera sample_monograph.pdf y sample_statement.pdf, PDF mínimos que imitan la maquetación de las monografías de la EMA.

La monografía tiene dos columnas («Well-established use» y «Traditional use»), cabecera y pie repetidos, una referencia cruzada
al inicio de línea, una nota al pie en letra pequeña dentro de la 4.5 y una sección que sigue en una segunda página. La
declaración pública no tiene secciones numeradas. El contenido es inventado (no es de la EMA). Uso: python3 make_sample_pdf.py <salida>.
"""
import sys


def page_stream(items):
    parts = []
    for x, y, size, text in items:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        parts.append("BT /F1 %d Tf %d %d Td (%s) Tj ET" % (size, x, y, escaped))
    return "\n".join(parts)


def build(pages):
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    add("<< /Type /Catalog /Pages 2 0 R >>")
    add(None)  # Pages, completado después
    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    for items in pages:
        stream = page_stream(items)
        content = add("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        page_ids.append(add("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>" % (content, font)))
    objects[1] = "<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % p for p in page_ids), len(page_ids))
    out = "%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out.encode("latin-1")))
        out += "%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out.encode("latin-1"))
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += "%010d 00000 n \n" % offset
    out += "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return out.encode("latin-1")


HEADER = [(50, 760, 9, "European Union herbal monograph on Sampleus officinalis L., herba")]
FOOTER = lambda n: [(50, 30, 9, "EMA/HMPC/123/2020 Page %d/2" % n)]
COLUMNS = [(50, 720, 10, "Well-established use"), (320, 720, 10, "Traditional use")]

MONOGRAPH = [
    HEADER + COLUMNS + FOOTER(1) + [
        (50, 690, 10, "4.2. Posology and method of administration"),
        (50, 676, 10, "See section 4.4. 'Special warnings' for the duration of use."),
        (50, 650, 10, "4.3. Contraindications"),
        (50, 636, 10, "Hypersensitivity to the active substance."),
        (320, 636, 10, "Hypersensitivity to plants of the Asteraceae."),
        (320, 622, 10, "Children under 12 years."),
        (50, 596, 10, "4.4. Special warnings and precautions for use"),
        (50, 582, 10, "If symptoms worsen consult a doctor."),
        (320, 582, 10, "The use in children under 12 has not been"),
    ],
    HEADER + COLUMNS + FOOTER(2) + [
        (320, 690, 10, "established."),
        (50, 664, 10, "4.5. Interactions with other medicinal products and"),
        (50, 650, 10, "other forms of interaction"),
        (50, 636, 10, "Concomitant use with anticoagulants is contraindicated."),
        (320, 636, 10, "None reported."),
        (50, 612, 7, "6 Footnote that must be dropped."),
        (50, 580, 10, "4.6. Fertility, pregnancy and lactation"),
        (50, 566, 10, "Not recommended."),
    ],
]

STATEMENT = [
    [(50, 760, 9, "Public statement on Sampleus officinalis L., herba Page 1/2"),
     (50, 720, 10, "Assessment of the available information"),
     (50, 700, 10, "No data on safety were assessed in the document."),
     (50, 660, 10, "CONCLUSIONS"),
     (50, 640, 10, "A monograph cannot be established unless new data are provided."),
     (50, 626, 10, "See http://www.example.org/more for the assessment.")],
]

if __name__ == "__main__":
    out = sys.argv[1]
    open(out + "/sample_monograph.pdf", "wb").write(build(MONOGRAPH))
    open(out + "/sample_statement.pdf", "wb").write(build(STATEMENT))
