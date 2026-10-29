#!/usr/bin/env python3 -I
"""Genera postman/enable-goal-search.collection.json desde backend/openapi.json (esquemas resueltos en linea).
Uso: make_postman_collection.py <repo> <salida.json>. El token NO va en la coleccion: se pasa como variable secreta `token`
(environment local con la variable de tipo secret, o `--env-var token=$QA_TOKEN` en la linea de comandos).
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
def sch(path, status, method="get"):
    c = spec["paths"][path][method]["responses"][str(status)]["content"]
    return inline(next(iter(c.values()))["schema"])
GOALS, PAGE = sch("/v1/goals", 200), sch("/v1/goals/{goalId}/plants", 200)
PROB = sch("/v1/goals/{goalId}/plants", 404)

def item(name, path, status, ctype, schema=None, auth=True, tests="", token=None, method="GET"):
    js = f"const schema = {json.dumps(schema)};\n" if schema else ""
    ev = [f'pm.test("estado {status}", () => pm.response.to.have.status({status}));',
          f'pm.test("content-type {ctype}", () => pm.expect(pm.response.headers.get("Content-Type")).to.include("{ctype}"));']
    if schema: ev.append('pm.test("cumple el esquema de backend/openapi.json", () => pm.response.to.have.jsonSchema(schema));')
    header = [{"key": "Authorization", "value": "Bearer {{token}}"}] if auth else ([{"key": "Authorization", "value": "Bearer " + token}] if token else [])
    q = path.split("?", 1)
    return {"name": name,
            "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": (js + "\n".join(ev) + "\n" + tests).split("\n")}}],
            "request": {"method": method, "header": header,
                        "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": q[0].strip("/").split("/"),
                                "query": [{"key": k, "value": v} for k, v in (p.split("=", 1) for p in q[1].split("&"))] if len(q) > 1 else []}}}

J = "const j = pm.response.json();\n"
NORM = 'const norm = s => s.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/\\s+/g, " ").trim();\n'
ORDER = (NORM + 'pm.test("orden por displayName normalizado, cientifico normalizado e id", () => { const k = i => [norm(i.displayName), norm(i.scientificName), i.id]; const cmp = (a, b) => { for (let n = 0; n < 3; n++) { if (a[n] < b[n]) return -1; if (a[n] > b[n]) return 1; } return 0; }; const ks = j.items.map(k); for (let n = 1; n < ks.length; n++) pm.expect(cmp(ks[n-1], ks[n]), `${ks[n-1]} vs ${ks[n]}`).to.be.below(1); });\n')
FIELDS = 'pm.test("campos de cada planta y nada de dosis ni descripcion", () => j.items.forEach(i => pm.expect(Object.keys(i).sort()).to.eql(["areas","commonNames","displayName","family","hasSafety","id","image","safetyLevel","scientificName"])));\n'
NOEFF = 'pm.test("areas sin lenguaje de dosis o eficacia", () => j.items.forEach(i => i.areas.forEach(a => pm.expect(a).to.not.match(/dosis|\\bmg\\b|eficaz|eficacia|efecto|calma|ayuda a|promueve|reduce/i))));\n'
PROBLEM = 'pm.test("problem+json con status, title y detail", () => { const p = pm.response.json(); pm.expect(p.status).to.eql(pm.response.code); pm.expect(p.title).to.be.a("string"); pm.expect(p.detail).to.be.a("string"); });\n'
PARAM = lambda n: f'pm.test("param = {n}", () => pm.expect(pm.response.json().param).to.eql("{n}"));\n'
WWW = 'pm.test("WWW-Authenticate: Bearer", () => pm.expect(pm.response.headers.get("WWW-Authenticate")).to.eql("Bearer"));\n'
NOTOK = 'pm.test("el cuerpo no contiene el token", () => pm.expect(pm.response.text()).to.not.include(pm.environment.get("token") || "__sin_token__"));\n'

items = [
    {"name": "Objetivos", "item": [
        item("OBJ-01 catalogo de objetivos", "/v1/goals", 200, "application/json", GOALS,
             tests=J + 'pm.test("array en la raiz con los seis objetivos en orden", () => { pm.expect(j).to.be.an("array"); pm.expect(j.map(g => g.id)).to.eql(["relajacion-estres","mejorar-el-sueno","cuidado-de-la-piel","alivio-respiratorio","cansancio-y-fatiga","otros-objetivos"]); });\n'
             'pm.test("nombres en espanol", () => pm.expect(j.map(g => g.name)).to.eql(["Relajación / Estrés","Mejorar el sueño","Cuidado de la piel","Alivio respiratorio","Cansancio y fatiga","Otros objetivos"]));\n'
             'pm.test("conteos reales 17, 8, 32, 52, 8, 135", () => pm.expect(j.map(g => g.plantCount)).to.eql([17,8,32,52,8,135]));\n'
             'pm.test("solo otros-objetivos trae subareas, las demas []", () => j.forEach(g => pm.expect(g.subareas.length > 0).to.eql(g.id === "otros-objetivos")));\n'
             'pm.test("subareas en orden con conteos 68, 42, 22, 20, 17, 1", () => { const s = j[5].subareas; pm.expect(s.map(x => x.id)).to.eql(["digestion","vias-urinarias-y-genitales","dolor-e-inflamacion","boca-y-garganta","circulacion","molestias-oculares"]); pm.expect(s.map(x => x.plantCount)).to.eql([68,42,22,20,17,1]); });\n'),
    ]},
    {"name": "Plantas por objetivo", "item": [
        item("PLA-01 mejorar-el-sueno, primera pagina", "/v1/goals/mejorar-el-sueno/plants", 200, "application/json", PAGE,
             tests=J + 'pm.test("goal, subarea null, total 8, limit 20, offset 0", () => { pm.expect(j.goal).to.eql({id: "mejorar-el-sueno", name: "Mejorar el sueño"}); pm.expect(j.subarea).to.eql(null); pm.expect(j.total).to.eql(8); pm.expect(j.limit).to.eql(20); pm.expect(j.offset).to.eql(0); pm.expect(j.items.length).to.eql(8); });\n' + FIELDS + ORDER + NOEFF),
        item("PLA-02 relajacion-estres sin el hiperico", "/v1/goals/relajacion-estres/plants?limit=100", 200, "application/json", PAGE,
             tests=J + 'pm.test("total 17 y el hiperico ausente", () => { pm.expect(j.total).to.eql(17); pm.expect(j.items.map(i => i.id)).to.not.include("hypericum-perforatum"); });\n' + ORDER),
        item("PLA-03 subarea digestion", "/v1/goals/otros-objetivos/plants?subarea=digestion&limit=100", 200, "application/json", PAGE,
             tests=J + 'pm.test("subarea digestion, total 68", () => { pm.expect(j.subarea).to.eql({id: "digestion", name: "Digestión"}); pm.expect(j.total).to.eql(68); pm.expect(j.items.length).to.eql(68); });\n'
             'pm.test("areas de digestion solamente", () => { const ok = new Set(["Trastornos gastrointestinales","Estreñimiento","Pérdida de apetito","Pérdida de apetito; Trastornos gastrointestinales","Estreñimiento; Trastornos gastrointestinales","Trastornos gastrointestinales; Trastornos digestivos"]); j.items.forEach(i => i.areas.forEach(a => pm.expect(ok.has(a), a).to.eql(true))); });\n' + ORDER + NOEFF),
        item("PLA-04 union de otros-objetivos sin repetir", "/v1/goals/otros-objetivos/plants?limit=100", 200, "application/json", PAGE,
             tests=J + 'pm.test("subarea null, total 135, sin repetidas", () => { pm.expect(j.subarea).to.eql(null); pm.expect(j.total).to.eql(135); pm.expect(new Set(j.items.map(i => i.id)).size).to.eql(j.items.length); pm.expect(j.items.length).to.eql(100); });\n' + ORDER),
        item("PLA-05 paginacion limit 5 offset 5", "/v1/goals/alivio-respiratorio/plants?limit=5&offset=5", 200, "application/json", PAGE,
             tests=J + 'pm.test("cinco elementos, limit 5, offset 5, total 52", () => { pm.expect(j.items.length).to.eql(5); pm.expect(j.limit).to.eql(5); pm.expect(j.offset).to.eql(5); pm.expect(j.total).to.eql(52); });\n'),
        item("PLA-06 offset mas alla del total", "/v1/goals/alivio-respiratorio/plants?offset=1000", 200, "application/json", PAGE,
             tests=J + 'pm.test("lista vacia y total conservado", () => { pm.expect(j.items).to.eql([]); pm.expect(j.total).to.eql(52); });\n'),
        item("PLA-07 eucalipto: precauciones sin nivel", "/v1/goals/alivio-respiratorio/plants?limit=100", 200, "application/json", PAGE,
             tests=J + 'pm.test("eucalyptus-globulus con safetyLevel null y hasSafety true", () => { const e = j.items.find(i => i.id === "eucalyptus-globulus"); pm.expect(e.safetyLevel).to.eql(null); pm.expect(e.hasSafety).to.eql(true); });\n'
             'pm.test("niveles validos y hasSafety verdadero en todas", () => j.items.forEach(i => { pm.expect([null,"alto","medio","bajo"]).to.include(i.safetyLevel); pm.expect(i.hasSafety).to.eql(true); }));\n'),
        item("PLA-08 la lavanda en el sueno con su area", "/v1/goals/mejorar-el-sueno/plants", 200, "application/json", PAGE,
             tests=J + 'pm.test("lavandula-angustifolia con el area de sueno", () => { const l = j.items.find(i => i.id === "lavandula-angustifolia"); pm.expect(l.areas).to.eql(["Trastornos del sueño e insomnio pasajero"]); pm.expect(l.image.license).to.be.a("string"); });\n'),
        item("PLA-09 plantas toxicas ausentes", "/v1/goals/otros-objetivos/plants?limit=100", 200, "application/json", PAGE,
             tests=J + 'pm.test("aconitum-napellus, ricinus-communis y abrus-precatorius no estan", () => { const ids = j.items.map(i => i.id); ["aconitum-napellus","ricinus-communis","abrus-precatorius"].forEach(x => pm.expect(ids).to.not.include(x)); });\n'),
        item("PLA-10 el hiperico sigue en el detalle", "/v1/plants/hypericum-perforatum", 200, "application/json",
             tests=J + 'pm.test("detalle con id hypericum-perforatum", () => pm.expect(j.id).to.eql("hypericum-perforatum"));\n'),
    ]},
    {"name": "Errores", "item": [
        item("ERR-01 objetivo desconocido", "/v1/goals/no-existe/plants", 404, "application/problem+json", PROB, tests=PROBLEM),
        item("ERR-02 subarea ajena", "/v1/goals/relajacion-estres/plants?subarea=digestion", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("subarea")),
        item("ERR-03 subarea inexistente en otros-objetivos", "/v1/goals/otros-objetivos/plants?subarea=no-existe", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("subarea")),
        item("ERR-04 subarea sobre un objetivo sin subareas", "/v1/goals/mejorar-el-sueno/plants?subarea=x", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("subarea")),
        item("ERR-05 limit 0", "/v1/goals/mejorar-el-sueno/plants?limit=0", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("limit")),
        item("ERR-06 limit 101", "/v1/goals/mejorar-el-sueno/plants?limit=101", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("limit")),
        item("ERR-07 limit no numerico", "/v1/goals/mejorar-el-sueno/plants?limit=abc", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("limit")),
        item("ERR-08 offset negativo", "/v1/goals/mejorar-el-sueno/plants?offset=-1", 400, "application/problem+json", PROB, tests=PROBLEM + PARAM("offset")),
    ]},
    {"name": "Autenticacion y metodos", "item": [
        item("AUT-01 catalogo sin token", "/v1/goals", 401, "application/problem+json", PROB, auth=False, tests=PROBLEM + WWW),
        item("AUT-02 plantas sin token", "/v1/goals/mejorar-el-sueno/plants", 401, "application/problem+json", PROB, auth=False, tests=PROBLEM + WWW),
        item("AUT-03 objetivo desconocido sin token: 401 y no 404", "/v1/goals/no-existe/plants", 401, "application/problem+json", PROB, auth=False, tests=WWW),
        item("AUT-04 catalogo con token incorrecto", "/v1/goals", 401, "application/problem+json", PROB, auth=False, token="token-incorrecto-de-prueba-0123456789abcdef", tests=WWW),
        item("AUT-05 plantas con token incorrecto", "/v1/goals/mejorar-el-sueno/plants", 401, "application/problem+json", PROB, auth=False, token="token-incorrecto-de-prueba-0123456789abcdef", tests=WWW),
        item("MET-01 POST al catalogo", "/v1/goals", 405, "application/problem+json", PROB, method="POST", tests='pm.test("Allow: GET", () => pm.expect(pm.response.headers.get("Allow")).to.include("GET"));\n' + PROBLEM),
        item("MET-02 DELETE a las plantas", "/v1/goals/mejorar-el-sueno/plants", 405, "application/problem+json", PROB, method="DELETE", tests='pm.test("Allow: GET", () => pm.expect(pm.response.headers.get("Allow")).to.include("GET"));\n'),
        item("MET-03 POST sin token: 401 antes que 405", "/v1/goals", 401, "application/problem+json", PROB, auth=False, method="POST", tests=WWW),
    ]},
    {"name": "Rutas existentes", "item": [
        item("REG-01 listado de plantas sigue igual", "/v1/plants?limit=3", 200, "application/json", sch("/v1/plants", 200),
             tests=J + 'pm.test("total 2354 y limit 3", () => { pm.expect(j.total).to.eql(2354); pm.expect(j.limit).to.eql(3); });\n'),
        item("REG-02 detalle de la lavanda sigue igual", "/v1/plants/lavandula-angustifolia", 200, "application/json", sch("/v1/plants/{id}", 200),
             tests=J + 'pm.test("displayName Lavanda y objetivos", () => { pm.expect(j.displayName).to.eql("Lavanda"); pm.expect(j.goals.map(g => g.name)).to.include.members(["Mejorar el sueño","Relajación / Estrés"]); });\n'),
    ]},
]
json.dump({"info": {"name": "enable-goal-search API", "description": "Pruebas de GET /v1/goals y GET /v1/goals/{goalId}/plants contra el servicio local de docker compose. Variables: baseUrl y token (secreta).",
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
           "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8080"}], "item": items}, open(out, "w"), indent=1, ensure_ascii=False)
print(sum(len(f["item"]) for f in items), "peticiones")
