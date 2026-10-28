#!/usr/bin/env python3 -I
"""Genera la tabla de trazabilidad (escenario -> casos) a partir de los deltas de specs y de MAPPING, y falla si algun escenario no tiene caso.
Con un segundo argumento (JSON de estados) genera la tabla de resultados por criterio.
Uso: traceability.py <repo> plan            -> imprime la tabla del plan
     traceability.py <repo> results <json>  -> imprime la tabla de resultados (json: {"API-01": ["PASA", "evidencia"], ...})
"""
import json, pathlib, re, sys
REPO = pathlib.Path(sys.argv[1]); MODE = sys.argv[2]
SPECS = REPO / "openspec/changes/serve-consolidated-plants/specs"
M = {}
def m(cap, req, cases, scenarios=None):
    M[(cap, req)] = (cases, scenarios or {})
# capability, requisito, casos por defecto, excepciones por escenario
m("catalog-api", "Listado y búsqueda de plantas", "API-01 API-12 API-13 API-16", {
  "Orden estable en empate": "API-01 (la base no tiene nombres cientificos repetidos: el empate solo se cubre con la prueba del producto, API-18)",
  "Búsqueda por nombre científico": "API-12 API-16", "Búsqueda por identificador anterior": "API-12 API-16", "Alias con puntuación en la consulta": "API-12 API-16",
  "Caracteres de patrón literales": "API-12 API-16 API-17", "Consulta sin letras ni dígitos": "API-12", "Consulta vacía": "API-12", "Sin coincidencias": "API-12 API-17",
  "Listado sin búsqueda": "API-01 API-16 APP-02", "Contenido de cada elemento": "API-01 API-16", "Nombre para mostrar en el listado": "API-01 API-03 API-16", "Planta sin nombre común": "API-01 API-03 API-13"})
m("catalog-api", "Detalle de planta", "API-02 API-13 API-16", {
  "Sin información de procedencia": "API-02 API-11", "Cita de `uses` sin cambios": "API-05 API-13 API-16", "Planta sin usos": "API-02 API-13 API-16",
  "Familia presente": "API-02 API-04", "Familia ausente": "API-02 API-04 API-13", "Identificador inexistente": "API-10 API-16 API-17"})
m("catalog-api", "Independencia de la fuente de datos", "IND-01", {
  "Base construida con otra fuente": "IND-01 API-18 (solo pruebas del producto)",
  "Atribución en las respuestas": "API-09 API-13", "Contrato sin nombres de dataset": "API-11 IND-01"})
m("catalog-api", "Nombre para mostrar y orden de los nombres comunes", "API-03 API-13", {"Sin nombre común": "API-01 API-03 API-13"})
m("catalog-api", "Contenido consolidado del detalle", "API-04 API-05 API-06 API-07 API-13", {
  "Planta con todos los campos": "API-13 API-16", "Planta con campos vacíos": "API-13 API-16", "Grupos de uso": "API-05 API-13", "Seguridad sin datos": "API-07 API-13",
  "Seguridad sin nivel": "API-07 API-13 API-16 APP-05", "Cita completa en los grupos de uso": "API-05 API-13 API-16", "Grupo de uso con una cita sin resolver": "API-05 APP-08",
  "Objetivo de la EMA": "API-06 API-13 APP-03", "Subárea de otros objetivos": "API-06 APP-05"})
m("catalog-api", "Imagen con atribución en el detalle", "API-08 API-13", {"Sin acceso a la red": "API-15"})
m("catalog-api", "Créditos neutrales a nivel de planta", "API-09 API-13", {
  "Planta sin créditos": "API-09 (0 plantas sin creditos en la base real: solo la prueba del producto, API-18)"})
m("catalog-api", "Identificadores anteriores", "API-10 API-16", {"Alias sin autorización": "API-10 API-11 API-16"})
m("catalog-api", "Contenido pendiente de revisión no se sirve", "API-02 API-05 API-06 API-13", {
  "Objetivo condicionado": "API-06 API-13 API-16 APP-09", "Grupo sin ninguna cita resuelta": "API-05", "Grupo con una cita resuelta y otra sin resolver": "API-05 APP-08",
  "Planta con otros flags": "API-02 API-13 REV-01", "Sin flags en las respuestas": "API-02 API-11"})
m("catalog-client", "Consumo de la API v1 del catálogo", "APP-16", {
  "Sin otros endpoints, hosts ni datos de usuario": "APP-16 APP-14", "Imagen de un host permitido": "APP-14 APP-16", "Imagen de un host no permitido": "APP-16",
  "Detalle por identificador": "APP-03 APP-16", "Token en cada petición": "APP-02 APP-03 APP-16", "Listado con parámetros": "APP-02 APP-16"})
m("catalog-client", "Parseo estricto de las respuestas", "APP-16", {
  "Precauciones sin nivel": "APP-05 APP-16", "Cita sin resolver": "APP-08 APP-16", "Detalle válido": "APP-03 APP-16", "Listado válido": "APP-02 APP-16",
  "Backend anterior sin los campos nuevos": "APP-12 APP-16", "Familia nula": "APP-06 APP-16"})
m("catalog-client", "Nombre para mostrar", "APP-16", {
  "Planta con nombre común": "APP-02 APP-03", "Planta sin nombre común": "APP-02 APP-06 APP-07", "Backend sin nombre para mostrar": "APP-12 APP-16", "Idioma del nombre común": "APP-16 APP-07"})
m("catalog-ingest", "Procedencia de cada dato", "ING-03", {
  "Trazabilidad de un uso": "API-05 ING-03", "Trazabilidad de un objetivo": "API-06 API-09 ING-03", "Dato sin fuente": "ING-03 (solo pruebas del producto)",
  "URL de licencia de una fuente": "SED-01 ING-01", "URL de licencia inválida en el manifiesto": "ING-02"})
m("catalog-seed", "Fuentes con versión fija, checksum y licencia", "SED-03", {
  "URL de licencia de una fuente": "SED-01 ING-01", "Fuente sin URL de licencia": "SED-01 SED-02", "URL de licencia inválida": "SED-02"})
m("explore-screen", "Composición y contenido de Explorar", "APP-02", {"Vista inicial": "APP-02", "Arte local": "APP-02", "Planta sin nombre común": "APP-02", "Nombre en español": "APP-02 API-12"})
m("plant-passport", "Identidad y composición del pasaporte", "APP-03", {
  "Campo de aceite no aplicable": "APP-06 APP-16", "Planta sin nombre común": "APP-06 APP-07", "Carga del pasaporte": "APP-16 (solo pruebas del producto)", "Atribución sin procedencia por campo": "APP-03 APP-04 REV-02"})
m("plant-passport", "General con vacíos explícitos", "APP-03 APP-06", {
  "Campos de P05 presentes": "APP-03", "Datos generales ausentes": "APP-06", "Parte registrada": "APP-03", "Familia y nombres comunes": "APP-03 APP-05", "Sin partes ni nombres comunes": "APP-06",
  "Planta sin nombre en español": "APP-07", "Aviso de nivel alto": "APP-04", "Sin aviso para otros niveles": "APP-03 APP-05", "Sin lista de referencias en General": "APP-03"})
m("plant-passport", "Propiedades sin inferencia de eficacia", "APP-03 APP-05", {
  "Plantas sin evaluación respaldada": "APP-04 APP-06", "Sin lenguaje de eficacia": "APP-03 APP-16 REV-02", "Objetivo de otros objetivos": "APP-05"})
m("plant-passport", "Usos como registros tradicionales trazables", "APP-03", {
  "Aviso fijo de usos tradicionales": "APP-03 APP-06", "Cita sin resolver visible": "APP-08", "Actividades sensibles tal como llegan": "APP-04 REV-01 REV-02",
  "Grupo sin países": "APP-16 (solo pruebas del producto)", "Sin registro elegible": "APP-06", "Muchos usos": "APP-03 APP-13"})
m("plant-passport", "Accesibilidad del pasaporte", "APP-13", {"Imagen descrita": "APP-03", "Nivel de precauciones sin depender del color": "APP-04 APP-05"})
m("plant-passport", "Imagen de cabecera con atribución", "APP-03 APP-11", {
  "Imagen con licencia CC BY-SA": "APP-03 APP-14", "Imagen sin atribución obligatoria": "APP-03", "Sin imagen": "APP-06", "Falla la descarga de la imagen": "APP-11", "Abrir la página del archivo": "APP-10"})
m("plant-passport", "Precauciones con nivel opcional y citas", "APP-04 APP-05", {
  "Precauciones de nivel alto": "APP-04", "Precauciones sin nivel": "APP-05", "Precauciones sin datos": "APP-06", "Ninguna planta se presenta como segura": "APP-04 APP-05 APP-06 REV-01 REV-02"})
m("plant-passport", "Sección Fuentes con licencias y atribución", "APP-03 APP-06", {
  "Fuentes de una planta": "APP-03", "Fuentes visibles en cada pestaña": "APP-03 APP-04", "Entrada de la imagen": "APP-03", "Sin créditos": "APP-16 (solo pruebas del producto)", "Sin procedencia por campo": "APP-03 REV-02"})

rows = []; missing = []
for cap in ("catalog-api", "catalog-client", "explore-screen", "plant-passport", "catalog-seed", "catalog-ingest"):
    req = None
    for line in (SPECS / cap / "spec.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### Requirement:"): req = line.split(":", 1)[1].strip()
        elif line.startswith("#### Scenario:"):
            sc = line.split(":", 1)[1].strip()
            if (cap, req) not in M: missing.append((cap, req, sc)); continue
            default, exc = M[(cap, req)]
            rows.append((cap, req, sc, exc.get(sc, default)))
if missing: print("SIN CASO:", missing, file=sys.stderr); sys.exit(1)
if MODE == "plan":
    print("| Capability | Requisito | Escenario | Casos |"); print("|---|---|---|---|")
    for cap, req, sc, cases in rows: print(f"| `{cap}` | {req} | {sc} | {cases} |")
else:
    st = json.load(open(sys.argv[3]))
    print("| Capability | Escenario | Casos | Resultado | Evidencia | Estado |"); print("|---|---|---|---|---|---|")
    for cap, req, sc, cases in rows:
        ids = re.findall(r"[A-Z]{3}-\d{2}", cases)
        res = [st.get(i, ["NO EJECUTADO", ""])[0] for i in ids]
        est = "FALLA" if "FALLA" in res else ("NO EJECUTADO" if "NO EJECUTADO" in res else ("PARCIAL" if "PARCIAL" in res else "PASA"))
        ev = ", ".join(sorted({"`" + st.get(i, ["", "-"])[1].replace("evidence/", "") + "`" for i in ids}))
        print(f"| `{cap}` | {sc} | {cases} | " + ", ".join(f"{i}: {r}" for i, r in zip(ids, res)) + f" | {ev} | {est} |")
print(len(rows), "escenarios", file=sys.stderr)
