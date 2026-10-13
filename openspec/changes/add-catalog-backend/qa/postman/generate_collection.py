#!/usr/bin/env python3
"""Genera catalog-api.postman_collection.json (Postman v2.1) con los escenarios principales de la spec catalog-api.

Uso: python3 generate_collection.py > catalog-api.postman_collection.json
La URL base viene de la variable de entorno de Postman `baseUrl` (ver catalog-api.postman_environment.json).
"""
import json

def test(lines):
    return {"listen": "test", "script": {"type": "text/javascript", "exec": lines}}

def req(name, method, path, tests, headers=None, body=None):
    r = {"method": method, "header": headers or [], "url": {"raw": "{{baseUrl}}" + path}}
    # Postman recomienda desglosar la URL; el raw basta para Newman, pero se separa path y query.
    p, _, q = path.partition("?")
    r["url"] = {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": [s for s in p.split("/") if s],
                "query": [dict(zip(("key", "value"), kv.split("=", 1) + [""])) for kv in q.split("&")] if q else []}
    if body is not None:
        r["body"] = {"mode": "raw", "raw": body}
    return {"name": name, "event": [test(tests)], "request": r}

def status(code):
    return f'pm.test("estado {code}", () => pm.response.to.have.status({code}));'

def ctype(ct):
    return f'pm.test("content-type {ct}", () => pm.expect(pm.response.headers.get("Content-Type")).to.eql("{ct}"));'

def json_test(name, expr):
    return f'pm.test("{name}", () => {{ const j = pm.response.json(); pm.expect({expr}).to.be.true; }});'

items = []
items.append(req("API-001 GET /healthz", "GET", "/healthz", [status(200), ctype("application/json"), json_test("status ok", 'j.status === "ok"')]))
items.append(req("API-002 GET /v1/sources", "GET", "/v1/sources", [status(200), ctype("application/json"),
    json_test("una fuente usda CC0 con todos los campos", 'j.length === 1 && j[0].id === "usda" && j[0].license === "CC0" && ["id","name","version","license","citation","url"].every(k => typeof j[0][k] === "string" && j[0][k].length > 0)')]))
items.append(req("API-003 GET /v1/plants (por defecto)", "GET", "/v1/plants", [status(200), ctype("application/json"),
    json_test("20 elementos y total 2376", 'j.items.length === 20 && j.total === 2376 && j.limit === 20 && j.offset === 0'),
    json_test("orden por nombre científico", 'j.items.map(i => i.scientificName).join("|") === j.items.map(i => i.scientificName).sort().join("|")'),
    json_test("forma de cada elemento", 'j.items.every(i => "id" in i && "scientificName" in i && Array.isArray(i.commonNames) && "family" in i)')]))
items.append(req("API-006 GET /v1/plants?limit=5&offset=10", "GET", "/v1/plants?limit=5&offset=10", [status(200),
    json_test("5 elementos, offset 10", 'j.items.length === 5 && j.offset === 10 && j.total === 2376')]))
items.append(req("API-007 offset más allá del total", "GET", "/v1/plants?offset=5000", [status(200),
    json_test("lista vacía y total conservado", 'j.items.length === 0 && j.total === 2376')]))
items.append(req("API-012 q=lavandula", "GET", "/v1/plants?q=lavandula", [status(200),
    json_test("incluye lavandula-angustifolia", 'j.total >= 1 && j.items.some(i => i.id === "lavandula-angustifolia")')]))
items.append(req("API-013 q=peppermint (nombre común)", "GET", "/v1/plants?q=peppermint", [status(200),
    json_test("incluye la menta", 'j.items.some(i => i.id === "mentha-x-piperita-subsp-nothosubsp-piperita")')]))
items.append(req("API-014 q=%20%20LAV%C3%81NDULA%20%20", "GET", "/v1/plants?q=%20%20LAV%C3%81NDULA%20%20", [status(200),
    json_test("7 coincidencias como lavandula", 'j.total === 7')]))
items.append(req("API-015 q vacío", "GET", "/v1/plants?q=", [status(200), json_test("total 2376", 'j.total === 2376')]))
items.append(req("API-015 q solo espacios", "GET", "/v1/plants?q=%20%20%20", [status(200), json_test("total 2376", 'j.total === 2376')]))
items.append(req("API-016 q=Tea_tree literal", "GET", "/v1/plants?q=Tea_tree", [status(200),
    json_test("encuentra Paperbark Tea_tree", 'j.total >= 1 && j.items.some(i => i.commonNames.some(n => n.text === "Paperbark Tea_tree"))')]))
items.append(req("API-016 q=Tea%tree no es comodín", "GET", "/v1/plants?q=Tea%25tree", [status(200), json_test("0 coincidencias", 'j.total === 0')]))
items.append(req("API-017 sin coincidencias", "GET", "/v1/plants?q=zzzzqqqq", [status(200), json_test("vacío", 'j.items.length === 0 && j.total === 0')]))
for v in ["0", "-1", "101", "abc"]:
    items.append(req(f"API-009 limit={v}", "GET", f"/v1/plants?limit={v}", [status(400), ctype("application/problem+json"),
        json_test("param limit", 'j.status === 400 && j.param === "limit"')]))
items.append(req("API-010 offset=-1", "GET", "/v1/plants?offset=-1", [status(400), ctype("application/problem+json"), json_test("param offset", 'j.param === "offset"')]))
items.append(req("API-011 q de 201 caracteres", "GET", "/v1/plants?q=" + "a" * 201, [status(400), ctype("application/problem+json"), json_test("param q", 'j.param === "q"')]))
items.append(req("API-019 detalle lavandula-angustifolia", "GET", "/v1/plants/lavandula-angustifolia", [status(200), ctype("application/json"),
    json_test("10 usos, 4 partes, English Lavender", 'j.uses.length === 10 && j.parts.length === 4 && j.names.some(n => n.text === "English Lavender" && n.kind === "common" && n.language === "en")'),
    json_test("fuente en cada dato", '[].concat(j.names, j.parts, j.uses).every(d => d.sources.length > 0) && j.family.sources.length > 0')]))
items.append(req("API-021 planta sin usos", "GET", "/v1/plants/matricaria-recutita", [status(200), json_test("usos vacío", 'Array.isArray(j.uses) && j.uses.length === 0')]))
items.append(req("API-022 planta sin familia", "GET", "/v1/plants/aspidixia-angulata", [status(200), json_test("family null", 'j.family === null')]))
items.append(req("API-023 id inexistente", "GET", "/v1/plants/no-existe", [status(404), ctype("application/problem+json")]))
items.append(req("API-024 ruta desconocida", "GET", "/v1/nada", [status(404), ctype("application/problem+json")]))
for m in ["POST", "PUT", "DELETE", "PATCH"]:
    items.append(req(f"API-025 {m} /v1/plants", m, "/v1/plants", [status(405), ctype("application/problem+json"),
        'pm.test("Allow: GET", () => pm.expect(pm.response.headers.get("Allow")).to.eql("GET"));'],
        headers=[{"key": "Content-Type", "value": "application/json"}], body="{}"))
items.append(req("API-027 GET /openapi.json", "GET", "/openapi.json", [status(200), ctype("application/json"), json_test("OpenAPI 3.1", 'j.openapi.startsWith("3.1")')]))

col = {"info": {"name": "Boticario AI Catalog API - QA add-catalog-backend", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": items}
print(json.dumps(col, indent=2, ensure_ascii=False))
