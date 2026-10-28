#!/usr/bin/env python3 -I
"""Genera las tablas de trazabilidad (escenario -> casos) y de resultados a partir de los deltas de specs y del mapeo MAPPING,
y falla si algun escenario no tiene caso. Uso:
  traceability.py <repo> plan                  imprime la tabla de trazabilidad del plan
  traceability.py <repo> results <json>        imprime la tabla de resultados por criterio (json: {"CASO": ["PASA|FALLA|NO EJECUTADO|OBS", "evidencia"]})
"""
import json, pathlib, re, sys
REPO = pathlib.Path(sys.argv[1]); MODE = sys.argv[2]
SPECS = REPO / "openspec/changes/enable-goal-search/specs"
M = {}
def m(cap, req, cases, scenarios=None): M[(cap, req)] = (cases, scenarios or {})

# ---------------- catalog-api ----------------
m("catalog-api", "Catálogo de objetivos", "API-01 API-02", {
  "Objetivo con subáreas": "API-02 API-05", "Subárea sin plantas": "API-24 UI-14", "Objetivo sin plantas": "API-24 UI-14",
  "Coherencia con los resultados": "API-11", "Sin token": "API-17"})
m("catalog-api", "Plantas por objetivo", "API-03 API-04", {
  "Plantas de un objetivo": "API-03 API-14", "Subárea": "API-04", "Unión sin subárea": "API-05", "Subárea ajena": "API-06", "Objetivo desconocido": "API-07",
  "Objetivo sin plantas": "API-24 UI-14", "Datos ausentes": "API-14 API-24", "Precauciones sin nivel": "API-15 UI-04", "Token y método": "API-17 API-18"})
m("catalog-api", "Orden y paginación de plantas por objetivo", "API-08 API-09 API-10", {
  "Orden por nombre para mostrar": "API-10", "Orden sin distinguir acentos ni mayúsculas": "API-10 API-24", "Páginas sin repetición": "API-09",
  "Límite fuera de rango": "API-08", "Desplazamiento más allá del total": "API-08"})
m("catalog-api", "Qué plantas aparecen por objetivo", "API-12 API-13", {
  "Planta sin objetivos": "API-13 CON-02", "Planta condicionada por revisión": "API-12 API-24", "Flag sin marca de revisión del objetivo": "API-12",
  "Planta en dos objetivos": "API-13 API-16"})
m("catalog-api", "Contrato aditivo de objetivos", "API-19", {
  "OpenAPI actualizado": "API-19", "Rutas existentes intactas": "API-19 API-20", "Ninguna ruta pública nueva": "API-21 API-17"})
# ---------------- goal-results-screen ----------------
m("goal-results-screen", "Composición de P07", "UI-02", {"Contenido": "UI-02", "Subárea": "UI-03", "Barra inferior": "UI-02 UI-09"})
m("goal-results-screen", "Tarjetas derivadas del registro", "UI-02 CON-01", {
  "Tarjeta con un área": "UI-02 CON-01", "Más de dos áreas": "UI-02 CON-01 (los datos reales traen como mucho tres; el caso de cuatro áreas solo con la prueba del producto REG-01)",
  "Sin lenguaje de eficacia": "CON-01 API-16 UI-02", "Planta sin nombre común": "UI-02 CON-03 UI-14",
  "Área con dos valores unidos": "UI-03 CON-01 API-16", "Miniatura ausente o fallida": "UI-05 UI-14"})
m("goal-results-screen", "Miniatura con atribución en la tarjeta", "UI-05 CON-04", {
  "Imagen con licencia": "UI-05 CON-04", "Imagen de dominio público": "UI-05 CON-04", "Autor desconocido": "UI-05 CON-04",
  "Miniatura de 500 px": "UI-16 CON-04", "Sin miniatura derivable": "REG-01 (no hay imagenes sin miniatura derivable en la base real: 0 de 1.860)",
  "Descarga en curso o fallida": "UI-05 UI-14", "Atribución accesible": "UI-13"})
m("goal-results-screen", "Marca de precaución en la tarjeta", "UI-04", {
  "Nivel alto o medio": "UI-04", "Sin datos": "UI-14 (con base modificada; en la real ninguna planta con objetivo lo cumple)", "Nivel bajo": "UI-04",
  "Precauciones sin nivel": "UI-04", "Lectura accesible": "UI-13 UI-04"})
m("goal-results-screen", "Orden y paginación de los resultados", "UI-02", {
  "Primera página": "UI-02", "Fin de lista": "UI-02", "Error al cargar más": "UI-10", "Sin sugerir relevancia": "UI-02 CON-01"})
m("goal-results-screen", "Estados de P07", "UI-10", {
  "Carga": "UI-10 REG-01 (el estado dura milisegundos con el backend local: se verifica con la prueba del producto y con el backend pausado)", "Error con reintento": "UI-10",
  "Vacío": "UI-14", "Objetivo desconocido": "REG-01 (la app no ofrece un objetivo desconocido: solo la prueba del producto y la API, API-07)", "Sin autorización": "UI-11"})
m("goal-results-screen", "Destino de las tarjetas", "UI-07", {
  "Abrir el pasaporte": "UI-07", "Volver conservando la posición": "UI-07", "Atrás desde el pasaporte hasta Inicio": "UI-08"})
m("goal-results-screen", "Ver más detalles", "UI-06", {"Abrir la hoja": "UI-06", "Cerrar la hoja": "UI-06", "Sin peticiones ni registro": "UI-06 UI-17"})
m("goal-results-screen", "Adaptación accesible de P07", "UI-12 UI-13", {"Texto aumentado": "UI-12 UI-18", "Controles accesibles": "UI-13"})
# ---------------- goal-search-screen ----------------
m("goal-search-screen", "Presentación de Buscar por objetivo", "UI-01", {
  "Contenido y orden de las seis filas": "UI-01", "Nombres y orden de la API": "REG-01 (con otro nombre solo la prueba del producto; la API real lo entrega de la base, API-01)",
  "Objetivo sin icono conocido": "REG-01 (la app solo conoce los seis ids reales)", "Presentación local sin collage": "UI-01 REG-01"})
m("goal-search-screen", "Adaptación accesible de P06", "UI-12 UI-13", {
  "Texto normal y aumentado": "UI-12 UI-01", "Zonas seguras y controles funcionales accesibles": "UI-13 (zonas seguras: el emulador no tiene notch; solo insets de la barra de gestos)"})
m("goal-search-screen", "Filas de objetivos con acción", "UI-01 UI-02", {
  "Activación de una fila sin subáreas": "UI-02", "Activación de una fila con subáreas": "UI-03", "Semántica de botón": "UI-13 UI-01", "Sin selección persistente": "UI-01 UI-08"})
m("goal-search-screen", "Catálogo de objetivos desde la API", "UI-01 UI-10", {
  "Carga": "UI-10 REG-01", "Error con reintento": "UI-10", "Sin autorización": "UI-11", "Sin conteos": "UI-01"})
m("goal-search-screen", "Pantalla de Otros objetivos", "UI-03", {
  "Lista de subáreas": "UI-03", "Abrir una subárea": "UI-03", "Subárea vacía": "UI-14", "Retorno": "UI-08", "Estados de carga y error": "UI-10"})
m("goal-search-screen", "Navegación a resultados", "UI-08", {
  "Pila completa": "UI-08", "Pestaña Inicio": "UI-09", "Sin datos de usuario": "UI-17", "Otras pestañas sin acción": "UI-09"})
# ---------------- catalog-client ----------------
m("catalog-client", "Consumo de la API v1 del catálogo", "REG-01", {
  "Listado con parámetros": "REG-01", "Consulta con caracteres especiales": "REG-01", "Consulta vacía": "REG-01", "Consulta larga": "REG-01",
  "Detalle por identificador": "REG-01 UI-07", "Catálogo de objetivos": "REG-01 UI-01", "Plantas de un objetivo": "REG-01 UI-02 UI-03",
  "Plantas de un objetivo sin subárea": "REG-01 UI-02", "Token en cada petición": "REG-01 UI-11 UI-15", "Imagen de un host permitido": "UI-05 UI-16 REG-01",
  "Imagen de un host no permitido": "REG-01 (la base real solo trae upload.wikimedia.org: el host no permitido solo con la prueba del producto)",
  "Sin otros endpoints, hosts ni datos de usuario": "UI-17 REG-01"})
m("catalog-client", "Parseo estricto de objetivos", "REG-01", {
  "Catálogo válido": "UI-01 UI-03 REG-01", "Plantas por objetivo válidas": "UI-02 REG-01", "Datos nulos": "UI-14 UI-04 REG-01",
  "Campo ausente o nivel desconocido": "REG-01 (la API real no devuelve contratos rotos: solo la prueba del producto)", "Campos desconocidos": "REG-01"})
m("catalog-client", "Errores de objetivos", "UI-10 UI-11 REG-01", {
  "Sin conexión o 5xx": "UI-10 REG-01", "No autorizado": "UI-11", "Objetivo no encontrado": "REG-01 API-07", "Reintento": "UI-10"})

req_re = re.compile(r"^### Requirement: (.+)$"); sc_re = re.compile(r"^#### Scenario: (.+)$")
rows = []; missing = []; removed = []
for cap_dir in sorted(SPECS.iterdir()):
    cap = cap_dir.name; req = None; section = None
    for line in (cap_dir / "spec.md").read_text().splitlines():
        if line.startswith("## "): section = line[3:].strip()
        r = req_re.match(line)
        if r: req = r.group(1).strip(); continue
        s = sc_re.match(line)
        if s and section != "REMOVED Requirements":
            sc = s.group(1).strip()
            ent = M.get((cap, req))
            if ent is None: missing.append((cap, req, sc)); continue
            cases = ent[1].get(sc, ent[0])
            rows.append((cap, req, sc, cases))
if missing:
    print("ESCENARIOS SIN CASO:", missing, file=sys.stderr); sys.exit(1)
unused = [(k, s) for k, (c, scs) in M.items() for s in scs if (k[0], k[1], s) not in {(a, b, c2) for a, b, c2, _ in rows}]
if unused:
    print("MAPEOS SIN ESCENARIO:", unused, file=sys.stderr); sys.exit(1)

if MODE == "plan":
    print("| Capability | Requisito | Escenario | Casos |\n|---|---|---|---|")
    for cap, req, sc, cases in rows: print(f"| `{cap}` | {req} | {sc} | {cases} |")
    print(f"\nTotal: {len(rows)} escenarios, todos con caso.", file=sys.stderr)
else:
    st = json.load(open(sys.argv[3]))
    print("| Capability | Requisito | Escenario | Casos | Estado | Evidencia |\n|---|---|---|---|---|---|")
    counts = {}
    for cap, req, sc, cases in rows:
        ids = re.findall(r"\b(?:API|UI|CON|REG|EXP)-\d+\b", cases)
        sts = [st[i][0] for i in ids if i in st]
        if not ids: res = "SIN CASO"
        elif any(s == "FALLA" for s in sts): res = "FALLA"
        elif sts and all(s == "PASA" for s in sts): res = "PASA"
        elif any(s == "PASA" for s in sts): res = "PASA con limitaciones"
        else: res = "NO EJECUTADO"
        ev = "; ".join(dict.fromkeys(st[i][1] for i in ids if i in st))
        counts[res] = counts.get(res, 0) + 1
        print(f"| `{cap}` | {req} | {sc} | {cases} | {res} | {ev} |")
    print("\n" + ", ".join(f"{k}: {v}" for k, v in counts.items()), file=sys.stderr)
