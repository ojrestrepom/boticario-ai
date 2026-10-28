#!/usr/bin/env python3 -I
"""Genera postman/serve-consolidated-plants.collection.json desde backend/openapi.json (esquemas resueltos en linea).
Uso: make_postman_collection.py <repo> <salida.json>. El token NO va en la coleccion: se pasa como variable de entorno
secreta `token` (por ejemplo `--env-var token=<token-app>` de Newman o el environment de Postman marcado como secreto).
"""
import copy, json, sys
repo, out = sys.argv[1:3]
spec = json.load(open(f"{repo}/backend/openapi.json"))
S = spec["components"]["schemas"]
def inline(x):
    if isinstance(x, dict):
        if "$ref" in x:
            base = inline(copy.deepcopy(S[x["$ref"].split("/")[-1]]))
            return base | {k: inline(v) for k, v in x.items() if k not in ("$ref", "description")}
        return {k: inline(v) for k, v in x.items() if k not in ("description", "format")}
    if isinstance(x, list): return [inline(v) for v in x]
    return x
def sch(path, status):
    c = spec["paths"][path]["get"]["responses"][str(status)]["content"]
    return inline(next(iter(c.values()))["schema"])
LIST, DETAIL, PROB = sch("/v1/plants", 200), sch("/v1/plants/{id}", 200), sch("/v1/plants/{id}", 404)

def item(name, path, status, ctype, schema=None, auth=True, tests="", token=None):
    js = f"const schema = {json.dumps(schema)};\n" if schema else ""
    ev = [f'pm.test("estado {status}", () => pm.response.to.have.status({status}));',
          f'pm.test("content-type {ctype}", () => pm.expect(pm.response.headers.get("Content-Type")).to.include("{ctype}"));']
    if schema: ev.append('pm.test("cumple el esquema de backend/openapi.json", () => pm.response.to.have.jsonSchema(schema));')
    header = [{"key": "Authorization", "value": "Bearer {{token}}"}] if auth else ([{"key": "Authorization", "value": "Bearer " + token}] if token else [])
    q = path.split("?", 1)
    return {"name": name,
            "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": (js + "\n".join(ev) + "\n" + tests).split("\n")}}],
            "request": {"method": "GET", "header": header,
                        "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": q[0].strip("/").split("/"),
                                "query": [{"key": k, "value": v} for k, v in (p.split("=", 1) for p in q[1].split("&"))] if len(q) > 1 else []}}}

def ids(js="pm.response.json()"): return f"{js}.items.map(i => i.id)"
J = "const j = pm.response.json();\n"
ALWAYS = ('pm.test("campos siempre presentes", () => { ["displayName","synonyms","description","origin","oil","useGroups","goals","safety","image","credits","names","parts","uses"].forEach(k => pm.expect(j).to.have.property(k)); });\n'
          'pm.test("sin reviewFlags ni campos de procedencia", () => { const t = JSON.stringify(j); pm.expect(t).to.not.include("reviewFlags"); pm.expect(t).to.not.include("pending"); pm.expect(j).to.not.have.property("sources"); });\n'
          'pm.test("tiempo < 500 ms", () => pm.expect(pm.response.responseTime).to.be.below(500));\n')
items = [
    item("LIS-01 listado por defecto con displayName", "/v1/plants", 200, "application/json", LIST,
         tests=J + 'pm.test("total 2354, limit 20, offset 0", () => { pm.expect(j.total).to.eql(2354); pm.expect(j.limit).to.eql(20); pm.expect(j.items.length).to.eql(20); });\n'
         'pm.test("cada elemento lleva displayName", () => j.items.forEach(i => pm.expect(i.displayName).to.be.a("string").and.not.empty));\n'),
    item("LIS-02 busqueda por nombre comun: lavanda", "/v1/plants?q=lavanda", 200, "application/json", LIST,
         tests=J + 'pm.test("lavandula-angustifolia con displayName Lavanda y Lavanda primero", () => { const p = j.items.find(i => i.id === "lavandula-angustifolia"); pm.expect(p.displayName).to.eql("Lavanda"); pm.expect(p.commonNames[0].text).to.eql("Lavanda"); });\n'),
    item("BUS-01 sinonimo: rosmarinus officinalis", "/v1/plants?q=rosmarinus%20officinalis", 200, "application/json", LIST,
         tests=J + f'pm.test("salvia-rosmarinus una sola vez", () => pm.expect({ids()}.filter(x => x === "salvia-rosmarinus").length).to.eql(1));\n'
         'pm.test("total = numero de elementos", () => pm.expect(j.total).to.eql(j.items.length));\n'),
    item("BUS-02 nombre anterior: matricaria recutita", "/v1/plants?q=matricaria%20recutita", 200, "application/json", LIST,
         tests=J + f'pm.test("encuentra matricaria-chamomilla una sola vez", () => {{ pm.expect({ids()}).to.eql(["matricaria-chamomilla"]); pm.expect(j.total).to.eql(1); }});\n'
         'pm.test("el alias no aparece como nombre", () => { const t = JSON.stringify(j).toLowerCase(); pm.expect(t).to.not.include("matricaria-recutita"); pm.expect(t).to.not.include("matricaria recutita"); });\n'),
    item("BUS-03 alias con puntuacion en la consulta", "/v1/plants?q=Mentha%20x%20piperita%20subsp.%20nothosubsp.%20piperita", 200, "application/json", LIST,
         tests=J + f'pm.test("encuentra mentha-x-piperita", () => pm.expect({ids()}).to.include("mentha-x-piperita"));\n'),
    item("BUS-04 limite conocido: mentha piperita sin la x da 0", "/v1/plants?q=mentha%20piperita", 200, "application/json", LIST,
         tests=J + 'pm.test("0 resultados (limite documentado)", () => { pm.expect(j.total).to.eql(0); pm.expect(j.items).to.eql([]); });\n'),
    item("BUS-05 caracteres de patron literales", "/v1/plants?q=%25", 200, "application/json", LIST,
         tests=J + 'pm.test("% no es comodin: no lista todo el catalogo", () => pm.expect(j.total).to.be.below(2354));\n'),
    item("DET-01 lavanda: cita completa en useGroups y etiqueta en uses", "/v1/plants/lavandula-angustifolia", 200, "application/json", DETAIL,
         tests=J + ALWAYS +
         'pm.test("displayName Lavanda; Lavanda primer nombre comun", () => { pm.expect(j.displayName).to.eql("Lavanda"); pm.expect(j.names.filter(n => n.kind === "common")[0].text).to.eql("Lavanda"); });\n'
         'pm.test("useGroups: cita completa de Steinmetz", () => { const r = j.useGroups.flatMap(g => g.references).find(r => r.id === "usda_reference:Steinmetz"); pm.expect(r.citation).to.eql("Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam."); pm.expect(r.resolved).to.eql(true); });\n'
         'pm.test("uses: etiqueta corta sin cambios", () => { pm.expect(j.uses.length).to.be.above(0); j.uses.forEach(u => pm.expect(u.reference.citation).to.match(/^USDA Dr\\. Duke: referencia /)); });\n'
         'pm.test("useGroups ordenados por count descendente", () => { const c = j.useGroups.map(g => g.count); pm.expect(c).to.eql([...c].sort((a, b) => b - a)); });\n'
         'pm.test("image con licencia y pagina", () => { pm.expect(j.image.license).to.be.a("string"); pm.expect(j.image.pageUrl).to.match(/^https:\\/\\//); });\n'
         'pm.test("credits: Wikipedia CC BY-SA 4.0 con URL de licencia; EMA con licenseUrl null", () => { const w = j.credits.find(c => c.name === "Wikipedia en español"); pm.expect(w.licenseUrl).to.eql("https://creativecommons.org/licenses/by-sa/4.0/"); pm.expect(w.url).to.eql("https://es.wikipedia.org/wiki/Lavandula_angustifolia"); j.credits.filter(c => c.name.startsWith("EMA")).forEach(c => pm.expect(c.licenseUrl).to.eql(null)); });\n'),
    item("DET-02 manzanilla (matricaria-chamomilla)", "/v1/plants/matricaria-chamomilla", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("nombre en espanol y usos", () => { pm.expect(j.displayName).to.not.eql(j.scientificName); pm.expect(j.useGroups.length).to.be.above(0); pm.expect(j.uses.length).to.be.above(0); });\n'),
    item("DET-03 menta (mentha-x-piperita)", "/v1/plants/mentha-x-piperita", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("nombre en espanol y usos", () => { pm.expect(j.displayName).to.not.eql(j.scientificName); pm.expect(j.useGroups.length).to.be.above(0); });\n'),
    item("DET-04 hiperico: sin relajacion-estres", "/v1/plants/hypericum-perforatum", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("goals no incluye relajacion-estres y conserva el resto", () => { pm.expect(j.goals.map(g => g.id)).to.not.include("relajacion-estres"); pm.expect(j.goals.length).to.be.above(0); });\n'),
    item("DET-05 planta toxica de nivel alto (aconitum-napellus)", "/v1/plants/aconitum-napellus", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("safety de nivel alto con texto y citas", () => { pm.expect(j.safety.level).to.eql("alto"); pm.expect(j.safety.text).to.not.be.empty; pm.expect(j.safety.references.length).to.be.above(0); });\n'),
    item("DET-06 eucalipto: safety sin nivel", "/v1/plants/eucalyptus-globulus", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("safety objeto con level null, texto y referencias", () => { pm.expect(j.safety).to.not.eql(null); pm.expect(j.safety.level).to.eql(null); pm.expect(j.safety.text).to.not.be.empty; pm.expect(j.safety.references.length).to.be.above(0); });\n'),
    item("DET-07 planta sin datos (angelica-laxiflora)", "/v1/plants/angelica-laxiflora", 200, "application/json", DETAIL,
         tests=J + ALWAYS + 'pm.test("vacios y null, nunca inventados", () => { pm.expect(j.useGroups).to.eql([]); pm.expect(j.goals).to.eql([]); pm.expect(j.uses).to.eql([]); pm.expect(j.synonyms).to.eql([]); ["safety","image","description","origin","oil"].forEach(k => pm.expect(j[k]).to.eql(null)); });\n'),
    item("DET-08 planta sin nombre en espanol (abutilon-theophrasti)", "/v1/plants/abutilon-theophrasti", 200, "application/json", DETAIL,
         tests=J + 'pm.test("displayName es el nombre cientifico y Velvetleaf sigue entre los comunes", () => { pm.expect(j.displayName).to.eql("Abutilon theophrasti"); pm.expect(j.names.map(n => n.text)).to.include("Velvetleaf"); });\n'),
    item("ALI-01 alias de identificador: rosmarinus-officinalis", "/v1/plants/rosmarinus-officinalis", 200, "application/json", DETAIL,
         tests=J + 'pm.test("id canonico y Content-Location", () => { pm.expect(j.id).to.eql("salvia-rosmarinus"); pm.expect(pm.response.headers.get("Content-Location")).to.eql("/v1/plants/salvia-rosmarinus"); });\n'),
    item("ALI-02 id canonico sin Content-Location", "/v1/plants/salvia-rosmarinus", 200, "application/json", DETAIL,
         tests='pm.test("sin Content-Location", () => pm.expect(pm.response.headers.has("Content-Location")).to.eql(false));\n'),
    item("ERR-01 id inexistente", "/v1/plants/no-existe-xyz", 404, "application/problem+json", PROB),
    item("AUT-01 listado sin token", "/v1/plants", 401, "application/problem+json", PROB, auth=False,
         tests='pm.test("WWW-Authenticate: Bearer", () => pm.expect(pm.response.headers.get("WWW-Authenticate")).to.eql("Bearer"));\n'),
    item("AUT-02 detalle sin token", "/v1/plants/lavandula-angustifolia", 401, "application/problem+json", PROB, auth=False,
         tests='pm.test("WWW-Authenticate: Bearer", () => pm.expect(pm.response.headers.get("WWW-Authenticate")).to.eql("Bearer"));\n'),
    item("AUT-03 alias sin token", "/v1/plants/rosmarinus-officinalis", 401, "application/problem+json", PROB, auth=False,
         tests='pm.test("sin Content-Location", () => pm.expect(pm.response.headers.has("Content-Location")).to.eql(false));\n'),
    item("AUT-04 token incorrecto", "/v1/plants", 401, "application/problem+json", PROB, auth=False, token="token-incorrecto-de-prueba"),
]
json.dump({"info": {"name": "serve-consolidated-plants API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
           "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8080"}], "item": items}, open(out, "w"), indent=1, ensure_ascii=False)
print(len(items), "peticiones")
