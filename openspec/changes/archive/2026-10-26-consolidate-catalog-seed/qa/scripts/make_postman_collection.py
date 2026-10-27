#!/usr/bin/env python3 -I
"""Genera postman/consolidate-catalog-seed.collection.json desde backend/openapi.json (esquemas resueltos en linea).
Uso: make_postman_collection.py <repo> <salida.json>. El token NO va en la coleccion: se pasa con --env-var token=...
"""
import json, sys, copy
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
def item(name, path, status, ctype, schema=None, auth=True, extra="", header_checks=""):
    js = f"const schema = {json.dumps(schema)};\n" if schema else ""
    ev = [f'pm.test("estado {status}", () => pm.response.to.have.status({status}));',
          f'pm.test("content-type {ctype}", () => pm.expect(pm.response.headers.get("Content-Type")).to.include("{ctype}"));']
    if schema: ev.append('pm.test("cumple el esquema de backend/openapi.json", () => pm.response.to.have.jsonSchema(schema));')
    return {"name": name, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": (js + "\n".join(ev) + "\n" + extra + header_checks).split("\n")}}],
            "request": {"method": "GET", "header": ([{"key": "Authorization", "value": "Bearer {{token}}"}] if auth else []),
                        "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": path.split("?")[0].strip("/").split("/"),
                                "query": [{"key": k, "value": v} for k, v in (p.split("=", 1) for p in path.split("?")[1].split("&"))] if "?" in path else []}}}
A401 = 'pm.test("WWW-Authenticate: Bearer", () => pm.expect(pm.response.headers.get("WWW-Authenticate")).to.eql("Bearer"));'
items = [
    item("listado por defecto", "/v1/plants", 200, "application/json", sch("/v1/plants", 200),
         extra='const j = pm.response.json();\npm.test("total 2354, limit 20, offset 0", () => { pm.expect(j.total).to.eql(2354); pm.expect(j.limit).to.eql(20); pm.expect(j.offset).to.eql(0); pm.expect(j.items.length).to.eql(20); });'),
    item("pagina 2 de 5", "/v1/plants?limit=5&offset=5", 200, "application/json", sch("/v1/plants", 200)),
    item("busqueda cientifica sinonimo: rosmarinus officinalis", "/v1/plants?q=rosmarinus%20officinalis", 200, "application/json", sch("/v1/plants", 200),
         extra='pm.test("encuentra salvia-rosmarinus", () => pm.expect(pm.response.json().items.map(i => i.id)).to.include("salvia-rosmarinus"));'),
    item("busqueda comun es: manzanilla", "/v1/plants?q=manzanilla", 200, "application/json", sch("/v1/plants", 200),
         extra='pm.test("encuentra matricaria-chamomilla", () => pm.expect(pm.response.json().items.map(i => i.id)).to.include("matricaria-chamomilla"));'),
    item("busqueda comun es: menta", "/v1/plants?q=menta&limit=100", 200, "application/json", sch("/v1/plants", 200),
         extra='pm.test("encuentra mentha-x-piperita", () => pm.expect(pm.response.json().items.map(i => i.id)).to.include("mentha-x-piperita"));'),
]
for pid, n in [("matricaria-chamomilla", "manzanilla"), ("mentha-x-piperita", "menta"), ("lavandula-angustifolia", "lavanda"), ("hypericum-perforatum", "hiperico"), ("lavandula-sp", "solo genero")]:
    extra = ""
    if n in ("manzanilla", "menta", "lavanda", "hiperico"):
        extra = f'pm.test("{n} tiene usos", () => pm.expect(pm.response.json().uses.length).to.be.above(0));\npm.test("usos en es con referencia", () => pm.response.json().uses.forEach(u => {{ pm.expect(u.language).to.eql("es"); pm.expect(u.reference.id).to.be.a("string").and.not.empty; pm.expect(u.reference.citation).to.be.a("string").and.not.empty; }}));'
    items.append(item(f"detalle {n}", f"/v1/plants/{pid}", 200, "application/json", sch("/v1/plants/{id}", 200), extra=extra))
items += [
    item("404 planta inexistente", "/v1/plants/no-existe", 404, "application/problem+json", sch("/v1/plants/{id}", 404)),
    item("404 ID anterior (alias aun no resuelto por la API)", "/v1/plants/rosmarinus-officinalis", 404, "application/problem+json", sch("/v1/plants/{id}", 404)),
    item("400 limit=0", "/v1/plants?limit=0", 400, "application/problem+json", sch("/v1/plants", 400)),
    item("400 limit=101", "/v1/plants?limit=101", 400, "application/problem+json", sch("/v1/plants", 400)),
    item("401 sin token (listado)", "/v1/plants", 401, "application/problem+json", sch("/v1/plants", 401), auth=False, header_checks=A401),
    item("401 sin token (detalle)", "/v1/plants/lavandula-angustifolia", 401, "application/problem+json", sch("/v1/plants/{id}", 401), auth=False, header_checks=A401),
    item("health publico", "/health", 200, "application/json", sch("/health", 200), auth=False),
]
col = {"info": {"name": "consolidate-catalog-seed API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
       "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8080"}], "item": items}
json.dump(col, open(out, "w"), ensure_ascii=False, indent=1)
print(len(items), "peticiones")
