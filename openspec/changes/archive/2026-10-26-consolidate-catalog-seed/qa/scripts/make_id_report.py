#!/usr/bin/env python3 -I
"""10.1: genera informe-ids.md (tabla completa ID anterior -> destino) desde evidence/ids/id-map.tsv.
Uso: make_id_report.py <id-map.tsv> <id-map-summary.json> <salida.md>
"""
import csv, json, sys, collections
rows = list(csv.DictReader(open(sys.argv[1]), delimiter="\t"))
S = json.load(open(sys.argv[2]))
def nrm(t): return t.lower().replace("×", "x")
def motivo(r):
    k, rel, fl = r["estado"], r["relacion_usda"].split(" (")[0], r["flags"]
    old, new = nrm(r["nombre_anterior"]), nrm(r["nombre_nuevo"])
    if k == "AUSENTE": return "Sin datos en ninguna fuente y sin resolución en WCVP/WFO; fuera de la semilla (tools/catalog-seed/README.md, estado final)"
    if k == "MISMO":
        if r["clase"] == "igual-absorbe": return "conserva el ID y absorbe: " + r["otros_ids_que_llegan"]
        return ""
    if rel.startswith("synonym/homot"): m = "sinónimo homotípico del aceptado de WCVP"
    elif rel.startswith("synonym/hetero"): m = "sinónimo heterotípico resuelto al aceptado de WCVP"
    elif old.startswith(new + " "): m = "infraespecífico o autónimo absorbido por la especie aceptada"
    elif "variante-ortografica" in fl: m = "variante ortográfica del nombre de WCVP"
    else: m = "nombre de USDA que WCVP trata con otro nombre aceptado"
    if r["clase"] == "fusionado": m += "; se fusiona con otros: " + r["otros_ids_que_llegan"]
    if "fusion-heterotipica" in fl: m += " (reviewFlag fusion-heterotipica)"
    return m
def esc(s): return s.replace("|", "\\|")
chg = [r for r in rows if r["estado"] != "MISMO"]
abs_ = [r for r in rows if r["clase"] == "igual-absorbe"]
same = [r for r in rows if r["estado"] == "MISMO"]
c = collections.Counter(r["clase"] for r in rows)
L = []
L.append("# Informe 10.1: IDs de la base anterior frente a la nueva")
L.append("")
L.append("Generado por `scripts/compare_bases.py` y `scripts/make_id_report.py` desde `evidence/ids/id-map.tsv`. La base anterior es la que construye `catalog-ingest download` y `build` en `main` (2.376 plantas, hash de contenido `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, ZIP de USDA de la caché); la nueva es `data/build/catalog.db` (2.354 plantas, hash `4be91c438ced8f41a07bc4873cc7562c869b5c16af44570d934f851bb7d5a639`).")
L.append("")
L.append("## Resumen")
L.append("")
L.append("| Medida | Anterior | Nueva |")
L.append("| --- | --- | --- |")
L.append(f"| Plantas | {S['plantas_anterior']} | {S['plantas_nueva']} |")
L.append(f"| Plantas sin ningún uso | {S['sin_usos_anterior']} ({S['sin_usos_anterior']*100/S['plantas_anterior']:.1f} %) | {S['sin_usos_nueva']} ({S['sin_usos_nueva']*100/S['plantas_nueva']:.1f} %) |")
L.append(f"| Usos servidos por la API | {S['usos_anterior']} | {S['usos_nueva']} |")
L.append(f"| Alias en `plant_alias` | 0 (no existía) | {S['alias']} |")
L.append("")
L.append("| Destino de los 2.376 IDs anteriores | IDs |")
L.append("| --- | --- |")
L.append(f"| Mismo ID (sin cambio) | {c['igual']} |")
L.append(f"| Mismo ID y absorbe a otros IDs anteriores | {c['igual-absorbe']} |")
L.append(f"| Pasan a alias de otro ID (renombrados, 1 a 1) | {c['renombrado']} |")
L.append(f"| Pasan a alias de un ID que absorbe a varios (fusionados) | {c['fusionado']} |")
L.append(f"| Ausentes (justificado) | {c['ausente']} |")
L.append(f"| IDs que cambian (alias más ausentes) | {S['ids_que_cambian']} |")
L.append("")
L.append(f"- Los 2.376 IDs anteriores tienen destino: {S['plantas_anterior']-1} son el mismo ID o un alias y 1 es ausencia justificada (`malachra-alaceaefolia`). Los IDs que cambian son {S['ids_que_cambian']}, algo más que el «unos 500 a 600» estimado.")
L.append(f"- {S['nuevos_con_varios_ids_anteriores']} plantas nuevas reciben más de un ID anterior (fusiones por sinonimia). Todas las absorbidas quedan como alias de la planta que las absorbe; ningún alias coincide con el ID de otra planta.")
L.append(f"- {S['ids_nuevos_sin_origen_anterior']} plantas nuevas no vienen de ningún ID anterior (especies de la EMA fuera de USDA y miembros separados por la regla de colisiones); están en `evidence/ids/new-only.txt`. Hay además {S['alias_extra_no_anteriores']} alias que no corresponden a un ID anterior (`evidence/ids/extra-alias.txt`).")
L.append(f"- Plantas que tenían usos y ya no los tienen: {S['con_usos_antes_y_sin_usos_ahora']} (véase DEF-03 del informe de resultados y `evidence/ids/lost-uses-reasons.tsv`). Plantas que no tenían usos y ahora sí: {S['sin_usos_antes_y_con_usos_ahora']}.")
L.append("")
L.append("## Tabla A: IDs que cambian (alias o ausencia)")
L.append("")
L.append("| ID anterior | Nombre anterior | Destino | Nombre nuevo | Usos antes → ahora | Motivo |")
L.append("| --- | --- | --- | --- | --- | --- |")
for r in chg:
    d = f"alias de `{r['id_nuevo']}`" if r["estado"] == "ALIAS" else "ausente"
    L.append(f"| `{r['id_anterior']}` | {esc(r['nombre_anterior'])} | {d} | {esc(r['nombre_nuevo'])} | {r['usos_anteriores']} → {r['usos_nuevos'] or 0} | {esc(motivo(r))} |")
L.append("")
L.append("## Tabla B: IDs que se conservan y absorben a otros")
L.append("")
L.append("| ID | Nombre | Usos antes → ahora | IDs anteriores que absorbe |")
L.append("| --- | --- | --- | --- |")
for r in abs_:
    L.append(f"| `{r['id_anterior']}` | {esc(r['nombre_nuevo'])} | {r['usos_anteriores']} → {r['usos_nuevos']} | {r['otros_ids_que_llegan'].replace(',', ', ')} |")
L.append("")
L.append("## Tabla C: IDs que se conservan sin cambio")
L.append("")
L.append("El destino es el mismo ID. El nombre científico es el mismo salvo el signo híbrido (`x` pasa a `×`).")
L.append("")
L.append("| ID | Nombre nuevo | Usos antes → ahora |")
L.append("| --- | --- | --- |")
for r in same:
    if r["clase"] == "igual-absorbe": continue
    L.append(f"| `{r['id_anterior']}` | {esc(r['nombre_nuevo'])} | {r['usos_anteriores']} → {r['usos_nuevos']} |")
open(sys.argv[3], "w").write("\n".join(L) + "\n")
print(len(chg), len(abs_), len(same) - len(abs_))
