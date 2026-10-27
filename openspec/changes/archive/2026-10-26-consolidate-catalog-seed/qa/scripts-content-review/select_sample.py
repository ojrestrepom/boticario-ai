"""Elige la muestra de 30 plantas de la tarea 10.5 y la imprime en JSON.

Los grupos fijos salen de la tarea; las 8 de la fase 2 salen de una semilla fija (105), con Python 3.9:
- Fase 2 = plantas cuyo paquete no trae fichas de la EMA (sections.regulatory vacío), con los IDs ordenados.
- 6 con random.Random(105).sample(fase2, 6).
- 2 con random.Random(105).sample(sorted(fase2 con alguna actividad sensible y fuera de las 6), 2).
Uso: python3 select_sample.py > sample.json
"""
import json, glob, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cr_lib import ROOT, GRAVE, RISK, base

FIXED = {
    "piloto": ["lavandula-angustifolia", "matricaria-chamomilla", "mentha-x-piperita", "hypericum-perforatum", "citrus-x-bergamia", "prunus-amygdalus"],
    "toxicas-tppt": ["conium-maculatum", "ricinus-communis", "datura-stramonium", "aconitum-napellus", "abrus-precatorius"],
    "solo-genero": ["aloe-spp", "crataegus-sp", "ephedra-spp"],
    "separadas-por-colision": ["citrus-x-paradisi", "brassica-oleracea-var-italica", "foeniculum-vulgare-var-dulce"],
    "fusionadas-por-colision": ["cinnamomum-verum", "ocimum-tenuiflorum"],
    "ema-fuera-de-usda": ["pelargonium-sidoides", "rhodiola-rosea", "tilia-cordata"],
}

def main():
    ids = [Path(f).stem for f in sorted(glob.glob(ROOT + "data/seed/plants/*.json"))]
    phase2, sensitive = [], set()
    for i in ids:
        b = json.load(open(ROOT + f"data/work/bundles/{i}.json"))
        if not b["sections"]["regulatory"]:
            phase2.append(i)
        acts = [u["activity"] for u in b["sections"]["uses"]]
        if any(base(a) in GRAVE or base(a) in RISK for a in acts):
            sensitive.add(i)
    phase2.sort()
    six = random.Random(105).sample(phase2, 6)
    pool = sorted(i for i in phase2 if i in sensitive and i not in six)
    two = random.Random(105).sample(pool, 2)
    out = dict(FIXED)
    out["fase-2-al-azar"] = six
    out["fase-2-con-actividad-sensible"] = two
    out["_notas"] = {"fase2": len(phase2), "pool-sensibles": len(pool), "python": sys.version.split()[0]}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
