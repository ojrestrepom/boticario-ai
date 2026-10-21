"""Spike 3.1: extract the EMA safety sections (4.3, 4.4, 4.5) from herbal monograph PDFs.

Usage (the PDFs are untrusted: run it isolated and pass paths as arguments):
    python3 -I extract_sections.py --tool pypdf|pdfminer|pdfminer-cols [--out DIR] file.pdf [...]

Tools:
  pypdf          plain reading-order text (pypdf.extract_text), one text per page.
  pdfminer       plain text of pdfminer.six (extract_text), one text per page.
  pdfminer-cols  pdfminer.six with coordinates: every line is assigned to the left column
                 ("Well-established use"), the right column ("Traditional use") or "both"
                 (a line that spans the two columns), and each section keeps the columns apart.

Needs `pypdf` or `pdfminer.six`, installed in a temporary venv (not in the repo).
Writes <out>/<stem>.<tool>.json and prints one summary line per PDF.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

# Section number -> regex for the title. Tolerates a title wrapped onto a second line and a trailing footnote digit.
HEADINGS = {
    "4.3": r"Contraindications\d*",
    "4.4": r"Special warnings and precautions? for use\d*",
    "4.5": r"Interactions with other medicinal products and other forms of(\s+interaction\d*)?",
}
NUMBERED = re.compile(r"^(4\.\d{1,2})\.\s+[A-Z]")  # "4.6.  Fertility..." (cross references have no dot after the number)

# Running headers and footers of EMA documents, removed per page.
NOISE = [
    re.compile(r"^(European Union|Community) herbal monograph on .*$"),
    re.compile(r"^EMA/HMPC/\d+/\d+\s*(Page \d+/\d+)?\s*$"),
    re.compile(r"^Page \d+/\d+\s*$"),
    re.compile(r"^Public statement on .*Page \d+/\d+$"),
]
COLUMN_HEADER = re.compile(r"^Well-established use\s+Traditional use$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def is_noise(line: str) -> bool:
    return any(rx.match(line) for rx in NOISE)


def lines_flat(pdf: Path, tool: str) -> list[dict]:
    """Lines in the order the tool returns them, without blanks or running headers."""
    if tool == "pypdf":
        from pypdf import PdfReader
        pages = [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]
    else:
        from pdfminer.high_level import extract_text
        pages = extract_text(str(pdf)).split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
    out = []
    for n, text in enumerate(pages, 1):
        for raw in text.splitlines():
            line = norm(raw)
            if line and not is_noise(line):
                out.append({"page": n, "text": line, "col": "single"})
    return out


def lines_cols(pdf: Path) -> list[dict]:
    """Lines with column assignment, in reading order (page, then top to bottom)."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextContainer, LTTextLine
    from statistics import median
    out, split = [], None
    for n, page in enumerate(extract_pages(str(pdf)), 1):
        raw = []
        for el in page:
            if isinstance(el, LTTextContainer):
                for ln in el:
                    if isinstance(ln, LTTextLine) and norm(ln.get_text()):
                        sizes = [c.size for c in ln if isinstance(c, LTChar)]
                        raw.append((ln.x0, ln.x1, ln.y1, norm(ln.get_text()), median(sizes) if sizes else 0))
        # Footnotes and running headers use a smaller font than the body of the page: drop them.
        body_size = median([r[4] for r in raw]) if raw else 0
        raw = [r[:4] for r in raw if r[4] >= 0.9 * body_size]
        # Column boundary: left edge of the "Traditional use" header, minus a margin.
        for x0, _, _, t in raw:
            if t == "Traditional use" and x0 > 150:
                split = x0 - 15
        raw.sort(key=lambda r: (-round(r[2]), r[0]))
        for x0, x1, y, t in raw:
            if is_noise(t):
                continue
            if split is None or NUMBERED.match(t) or t.startswith("Well-established use"):
                col = "single"
            elif x0 >= split:
                col = "right"
            elif x1 > split + 20:
                col = "both"
            else:
                col = "left"
            out.append({"page": n, "text": t, "col": col})
    return out


def find_starts(lines: list[dict]) -> dict:
    starts = {}
    for i, ln in enumerate(lines):
        m = NUMBERED.match(ln["text"])
        if not m or m.group(1) not in HEADINGS or m.group(1) in starts:
            continue
        joined = ln["text"] + " " + (lines[i + 1]["text"] if i + 1 < len(lines) else "")
        if re.match(r"^" + re.escape(m.group(1)) + r"\.\s+" + HEADINGS[m.group(1)] + r"\s*$|^" + re.escape(m.group(1)) + r"\.\s+" + HEADINGS[m.group(1)], joined):
            starts[m.group(1)] = i
    return starts


def section_lines(lines: list[dict], i: int, num: int) -> tuple[list[dict], int]:
    """Lines of the section whose heading is at index i, and the index of the line after the heading."""
    body_from = i + 1
    if num == "4.5" and not re.search(r"interaction\d*$", lines[i]["text"]):
        body_from = i + 2  # the title wraps onto a second line
    end = len(lines)
    for j in range(body_from, len(lines)):
        if NUMBERED.match(lines[j]["text"]):
            end = j
            break
    return lines[body_from:end], body_from


def build_text(body: list[dict]) -> str:
    # The column header ("Well-established use" / "Traditional use") is repeated at the top of every page.
    return " ".join(ln["text"] for ln in body
                    if not COLUMN_HEADER.match(ln["text"]) and ln["text"] not in ("Well-established use", "Traditional use"))


def extract(pdf: Path, tool: str) -> dict:
    lines = lines_cols(pdf) if tool == "pdfminer-cols" else lines_flat(pdf, tool)
    res = {"file": pdf.name, "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "tool": tool,
           "sections": {}, "notes": []}
    starts = find_starts(lines)
    for num, i in starts.items():
        body, _ = section_lines(lines, i, num)
        sec = {"heading": re.sub(r"\d+$", "", lines[i]["text"]), "page_from": lines[i]["page"],
               "page_to": body[-1]["page"] if body else lines[i]["page"]}
        if tool == "pdfminer-cols":
            for col in ("left", "right", "both"):
                part = [l for l in body if l["col"] == col]
                if part:
                    sec[col] = build_text(part)
        else:
            sec["text"] = build_text(body)
        res["sections"][num] = sec
    if not starts:
        # Public statement: no numbered sections; the equivalent of the safety part is CONCLUSIONS.
        for i, ln in enumerate(lines):
            if ln["text"] == "CONCLUSIONS":
                res["sections"]["CONCLUSIONS"] = {"heading": "CONCLUSIONS", "page_from": ln["page"],
                                                  "page_to": lines[-1]["page"],
                                                  "text": " ".join(l["text"] for l in lines[i + 1:])}
                break
        res["notes"].append("no numbered 4.x sections (public statement)")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="pypdf", choices=["pypdf", "pdfminer", "pdfminer-cols"])
    ap.add_argument("--out", default=".")
    ap.add_argument("pdfs", nargs="+")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for p in a.pdfs:
        r = extract(Path(p), a.tool)
        (out / f"{Path(p).stem}.{a.tool}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        summary = {k: {c: len(v[c]) for c in ("text", "left", "right", "both", "single") if c in v}
                   for k, v in r["sections"].items()}
        print(Path(p).name, a.tool, summary)


if __name__ == "__main__":
    main()
