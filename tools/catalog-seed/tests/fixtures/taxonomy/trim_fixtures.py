"""Regenera los fixtures de `tests/fixtures/taxonomy/` recortando WCVP y WFO a unos pocos taxones reales.

Uso (desde la raíz del repositorio, con las fuentes ya descargadas y verificadas en la caché):

    python3 -I tools/catalog-seed/tests/fixtures/taxonomy/trim_fixtures.py

Copia las filas reales sin modificarlas: los taxones de KEYS (clave sin signo híbrido) más sus aceptados y sus basiónimos.
No forma parte de las pruebas: solo documenta de dónde salen los fixtures.
"""
import csv
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, TOOL_DIR)

from catalog_seed.taxonomy.names import make_keys, rank_from_column  # noqa: E402

CACHE = os.path.abspath(os.path.join(TOOL_DIR, "..", "..", "data", ".cache"))

KEYS = set("""
matricaria recutita|matricaria chamomilla|mentha piperita|mentha piperita subsp. piperita|prunus dulcis|prunus amygdalus
prunus avium|lavandula angustifolia|lavandula latifolia|rosmarinus officinalis|salvia rosmarinus|rosmarinus lavandulaceus
cistus ladanifer|cistus ladaniferus|cistus creticus|citrus limon|citrus limetta|citrus bergamia|citrus aurantium subsp. bergamia
citrus limettioides|citrus meyeri|citrus meyerii|citrus sinensis|citrus paradisi|citrus aurantium f. aurantium
citrus medica var. limon|brassica oleracea|brassica oleracea var. italica|brassica oleracea var. capitata
brassica oleracea var. acephala|valeriana officinalis|valeriana officinalis subsp. officinalis|veratrum album
veratrum album virescens|veratrum lobelianum|poa annua|poa annua var. reptans|crataegus azarolus|crataegus monogyna
aquilegia vulgaris|aquilegia vulgaris inversa|mentha arvensis|mentha arvensis var. piperascens|acorus calamus
acorus calamus subsp. gramineus|gossypium hirsutum
eschscholzia californica|salvia fruticosa|salvia triloba|aloysia citrodora|aloysia triphylla|lippia citriodora|ziziphus jujuba
curcuma zanthorrhiza|taraxacum officinale|croton macrostachyus|croton microstachys|croton tenuicaulis
""".replace("\n", "|").split("|")) - {""}


def lines(zip_path, member):
    return io.TextIOWrapper(zipfile.ZipFile(zip_path).open(member), encoding="utf-8", errors="replace", newline="")


def trim_wcvp():
    path = os.path.join(CACHE, "wcvp", "wcvp.zip")
    with lines(path, "wcvp_names.csv") as handle:
        header = handle.readline()
        names = header.rstrip("\n").split("|")
        ix = {n: i for i, n in enumerate(names)}
        rows = {}
        for line in handle:
            f = line.rstrip("\n").split("|")
            infra = f[ix["infraspecies"]]
            rank = rank_from_column(f[ix["infraspecific_rank"]]) if infra else ""
            if f[ix["genus"]] and f[ix["species"]]:
                key = make_keys(f[ix["genus"]], f[ix["species"]], rank, infra)[0]
                if key in KEYS:
                    rows[f[0]] = line
            if len(rows) < 0:
                break
    # cierre: aceptados y basiónimos (una pasada más)
    wanted = set()
    for line in rows.values():
        f = line.rstrip("\n").split("|")
        wanted.update(x for x in (f[ix["accepted_plant_name_id"]], f[ix["basionym_plant_name_id"]]) if x)
    with lines(path, "wcvp_names.csv") as handle:
        handle.readline()
        for line in handle:
            pid = line.split("|", 1)[0]
            if pid in wanted and pid not in rows:
                rows[pid] = line
    out = os.path.join(HERE, "wcvp_names.csv")
    with open(out, "w", encoding="utf-8", newline="") as w:
        w.write(header)
        for pid in sorted(rows, key=int):
            w.write(rows[pid])
    accepted = set(rows)
    with lines(path, "wcvp_distribution.csv") as handle, open(os.path.join(HERE, "wcvp_distribution.csv"), "w", encoding="utf-8", newline="") as w:
        w.write(handle.readline())
        for line in handle:
            if line.split("|")[1] in accepted:
                w.write(line)
    return len(rows)


def trim_wfo():
    path = os.path.join(CACHE, "wfo", "_DwC_backbone_R.zip")
    with lines(path, "classification.csv") as handle:
        header = handle.readline()
        cols = header.rstrip("\n").split("\t")
        ix = {n: i for i, n in enumerate(cols)}
        rows = {}
        by_id = {}
        for line in handle:
            f = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")]
            if len(f) != len(cols):
                continue
            g, s, i = f[ix["genus"]], f[ix["specificEpithet"]], f[ix["infraspecificEpithet"]]
            if not g or not s:
                continue
            rank = rank_from_column(f[ix["taxonRank"]]) if i else ""
            if make_keys(g, s, rank, i)[0] in KEYS:
                rows[f[ix["taxonID"]]] = line
    wanted = set()
    for line in rows.values():
        f = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")]
        wanted.update(x for x in (f[ix["acceptedNameUsageID"]], f[ix["originalNameUsageID"]]) if x)
    with lines(path, "classification.csv") as handle:
        handle.readline()
        for line in handle:
            tid = line.split("\t", 1)[0].strip('"')
            if tid in wanted and tid not in rows:
                rows[tid] = line
    with open(os.path.join(HERE, "wfo_classification.csv"), "w", encoding="utf-8", newline="") as w:
        w.write(header)
        for tid in sorted(rows):
            w.write(rows[tid])
    return len(rows)


if __name__ == "__main__":
    print("wcvp filas:", trim_wcvp())
    print("wfo filas:", trim_wfo())
