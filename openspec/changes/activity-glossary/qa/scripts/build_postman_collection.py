#!/usr/bin/env python3
"""Genera la colección de Postman de la QA de activity-glossary (sin secretos: el token va en {{token}})."""
import json
import sys

COMMON = r'''
const j = pm.response.json();
const grp = (a) => j.useGroups.find(g => g.activity === a);
const cred = (n) => (j.credits || []).filter(c => c.name === n);
const WIKT = "Wikcionario en español", WIKI = "Wikipedia en español";
const KEYS = ["adapted","sourceName","term","text","url"];
'''

T_ALL = r'''
pm.test("estado 200 y JSON", () => { pm.response.to.have.status(200); pm.expect(pm.response.headers.get("Content-Type")||"").to.include("application/json"); });
pm.test("glossary siempre presente en cada grupo: objeto con 5 campos o null", () => {
  pm.expect(j.useGroups).to.be.an("array");
  j.useGroups.forEach(g => { pm.expect(g, g.activity).to.have.property("glossary");
    if (g.glossary !== null) { pm.expect(Object.keys(g.glossary).sort(), g.activity).to.eql(KEYS); pm.expect(g.glossary.url).to.match(/^https:\/\//); pm.expect(g.glossary.adapted).to.be.a("boolean"); } });
});
pm.test("el contrato anterior del grupo no cambia (campos y orden)", () => {
  j.useGroups.forEach(g => pm.expect(Object.keys(g)).to.eql(["activity","activitySource","count","countries","references","glossary"]));
});
pm.test("credits sin repeticiones", () => { const n = j.credits.map(c => c.name); pm.expect(new Set(n).size).to.eql(n.length); });
pm.test("Wikcionario en credits si y solo si algún grupo servido trae glossary de Wikcionario", () => {
  const has = j.useGroups.some(g => g.glossary && g.glossary.sourceName === "Wikcionario");
  pm.expect(cred(WIKT).length).to.eql(has ? 1 : 0);
});
pm.test("si algún glossary es de Wikipedia, Wikipedia está en credits una sola vez", () => {
  const has = j.useGroups.some(g => g.glossary && g.glossary.sourceName === "Wikipedia");
  if (has) pm.expect(cred(WIKI).length).to.eql(1);
  pm.expect(cred(WIKI).length).to.be.at.most(1);
});
pm.test("credits de glosario: CC BY-SA 4.0 con licenseUrl", () => {
  [WIKT, WIKI].forEach(n => cred(n).forEach(c => { pm.expect(c.license).to.eql("CC BY-SA 4.0"); pm.expect(c.licenseUrl).to.eql("https://creativecommons.org/licenses/by-sa/4.0/"); pm.expect(c.attribution).to.be.a("string").and.not.empty; pm.expect(c.url).to.match(/^https:\/\//); }));
});
'''

def term_test(activity, term, text, source, adapted, host):
    return (f'pm.test("{activity}: glossary {source}, adapted={str(adapted).lower()}", () => {{ const g = grp({json.dumps(activity)}); pm.expect(g, "grupo").to.exist; '
            f'pm.expect(g.glossary).to.not.be.null; pm.expect(g.glossary.term).to.eql({json.dumps(term, ensure_ascii=False)}); '
            f'pm.expect(g.glossary.text).to.eql({json.dumps(text, ensure_ascii=False)}); pm.expect(g.glossary.sourceName).to.eql("{source}"); '
            f'pm.expect(g.glossary.adapted).to.be.{"true" if adapted else "false"}; pm.expect(g.glossary.url).to.include("{host}").and.include("oldid="); }});')

def null_test(activity_pred, label):
    return (f'pm.test("{label}: glossary es null", () => {{ const gs = j.useGroups.filter({activity_pred}); pm.expect(gs.length, "grupos").to.be.above(0); gs.forEach(g => pm.expect(g.glossary, g.activity).to.be.null); }});')

def req(name, path, tests, desc, auth=True, extra=""):
    item = {
        "name": name,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": (COMMON + extra + tests).split("\n")}}],
        "request": {"method": "GET", "header": [], "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": [p for p in path.split("?")[0].split("/") if p]}, "description": desc},
    }
    if "?" in path:
        item["request"]["url"]["query"] = [{"key": k.split("=")[0], "value": k.split("=")[1]} for k in path.split("?")[1].split("&")]
    return item

DIUR = "Que aumenta o facilita la producción y excreción de orina."
CARM = "Se dice de las sustancias que propician la expulsión de los gases intestinales."
ESTI = "Sustancia que aumenta los niveles de actividad motriz y cognitiva y refuerza la vigilia, el estado de alerta y la atención."
SEDA = "Sustancia que induce una sedación gradual y reduce la irritabilidad o la excitación."
EXPE = "Un expectorante es un fármaco que tiene propiedades de provocar o promover la expulsión de las secreciones bronquiales acumuladas."
ANTI = "Un antídoto, antitóxico o contraveneno es una sustancia química cuya función es contrarrestar los efectos de un veneno, toxina o químico."

TONI = "Que provoca o favorece el tono de un músculo, de un órgano, o del metabolismo en general."
W = "es.wiktionary.org"; P = "es.wikipedia.org"
items = []
items.append(req("G1 Lavanda: Wikcionario literal (Diurético, Carminativo) y adaptado (Estimulante)", "/v1/plants/lavandula-angustifolia",
    T_ALL + term_test("Diurético","Diurético",DIUR,"Wikcionario",False,W) + term_test("Carminativo","Carminativo",CARM,"Wikcionario",False,W) + term_test("Estimulante","Estimulante",ESTI,"Wikipedia",True,P) +
    'pm.test("credits: Wikcionario y Wikipedia una vez cada uno", () => { pm.expect(cred(WIKT).length).to.eql(1); pm.expect(cred(WIKI).length).to.eql(1); });',
    "Planta con varias explicaciones de las dos fuentes."))
items.append(req("G2 Sedante adaptado de Wikipedia", "/v1/plants/aconitum-napellus",
    T_ALL + term_test("Sedante","Sedante",SEDA,"Wikipedia",True,P), "Sedante: texto adaptado de Wikipedia."))
items.append(req("G3 Expectorante: Wikipedia literal", "/v1/plants/abies-alba",
    T_ALL + term_test("Expectorante","Expectorante",EXPE,"Wikipedia",False,P), "Expectorante: primera oración literal de Wikipedia."))
items.append(req("G4 Solo explicaciones de Wikipedia: sin crédito de Wikcionario", "/v1/plants/actaea-dahurica",
    T_ALL + 'pm.test("ningun glossary de Wikcionario y credits sin Wikcionario", () => { pm.expect(j.useGroups.some(g => g.glossary && g.glossary.sourceName==="Wikcionario")).to.be.false; pm.expect(cred(WIKT).length).to.eql(0); pm.expect(cred(WIKI).length).to.eql(1); });',
    "Planta cuyas explicaciones son todas de Wikipedia."))
items.append(req("G5 Fórmula de enfermedad grave sin glossary", "/v1/plants/abelmoschus-manihot",
    T_ALL + null_test('g => g.activity.startsWith("Uso tradicional, sin eficacia demostrada: ")', "fórmula «Uso tradicional, sin eficacia demostrada: …»") +
    'pm.test("la fórmula conserva su texto completo en activity", () => { pm.expect(j.useGroups.some(g => g.activity === "Uso tradicional, sin eficacia demostrada: cáncer")).to.be.true; });',
    "Fórmula de enfermedad grave: nunca lleva glosario."))
items.append(req("G6 Término excluido (Hemostático, Depurativo) sin glossary", "/v1/plants/achillea-millefolium",
    T_ALL + null_test('g => g.activity === "Hemostático" || g.activity === "Depurativo"', "Hemostático y Depurativo (excluidos)") +
    'pm.test("existen ambos grupos", () => { pm.expect(grp("Hemostático")).to.exist; pm.expect(grp("Depurativo")).to.exist; });',
    "Términos excluidos de la lista aprobada."))
items.append(req("G7 Calificador: Antídoto (…) hereda Antídoto", "/v1/plants/alocasia-macrorrhizos",
    T_ALL + 'pm.test("Antídoto (Laportea) conserva su activity y trae term Antídoto", () => { const g = grp("Antídoto (Laportea)"); pm.expect(g).to.exist; pm.expect(g.glossary.term).to.eql("Antídoto"); pm.expect(g.glossary.text).to.eql(' + json.dumps(ANTI, ensure_ascii=False) + '); pm.expect(g.glossary.sourceName).to.eql("Wikipedia"); pm.expect(g.glossary.adapted).to.be.false; });',
    "Actividad con calificador."))
items.append(req("G8 Solo grupos pendientes de revisión: sin glossary ni crédito de Wikcionario", "/v1/plants/cedrus-deodara",
    T_ALL + 'pm.test("sin ningún glossary y sin créditos del glosario (los grupos Carminativo, Diaforético y Diurético están pendientes y no se sirven)", () => { pm.expect(j.useGroups.filter(g => g.glossary).length).to.eql(0); pm.expect(j.useGroups.some(g => ["Carminativo","Diaforético","Diurético"].includes(g.activity))).to.be.false; pm.expect(cred(WIKT).length).to.eql(0); });',
    "Todos sus grupos enlazados a términos están pendientes."))
items.append(req("G9 Pendiente de Wikipedia: no se sirve (maclura)", "/v1/plants/maclura-pomifera",
    T_ALL + 'pm.test("el grupo pendiente Estimulante no se sirve", () => { pm.expect(grp("Estimulante")).to.be.undefined; pm.expect(j.useGroups.filter(g => g.glossary).length).to.eql(0); });',
    "Grupo pendiente enlazado a un término de Wikipedia."))
items.append(req("G10 Planta sin ningún término del glosario", "/v1/plants/acacia-confusa",
    T_ALL + 'pm.test("ningún glossary y credits sin Wikcionario", () => { pm.expect(j.useGroups.filter(g => g.glossary).length).to.eql(0); pm.expect(cred(WIKT).length).to.eql(0); });',
    "Sin explicaciones."))
items.append(req("G11 Detalle por alias conserva glossary", "/v1/plants/rosmarinus-officinalis",
    T_ALL, "El alias resuelve a salvia-rosmarinus y trae glossary."))
# contrato anterior
LISTT = r'''
pm.test("200", () => pm.response.to.have.status(200));
const l = pm.response.json();
pm.test("listado: sin glossary ni useGroups y misma forma", () => { pm.expect(Object.keys(l)).to.eql(["items","total","limit","offset"]); pm.expect(l.items).to.be.an("array").and.not.empty; l.items.forEach(p => { pm.expect(p).to.not.have.property("glossary"); pm.expect(p).to.not.have.property("useGroups"); pm.expect(Object.keys(p)).to.eql(["id","scientificName","displayName","commonNames","family"]); }); });
'''
it = req("C1 Listado de plantas sin cambios", "/v1/plants?limit=3", "", "Forma del listado.")
it["event"][0]["script"]["exec"] = LISTT.split("\n")
items.append(it)
UT = r'''
pm.test("200", () => pm.response.to.have.status(200));
const d = pm.response.json();
pm.test("detalle: uses con sus campos de siempre y orden de claves de la raíz", () => { pm.expect(d.uses).to.be.an("array").and.not.empty; d.uses.forEach(u => pm.expect(u).to.not.have.property("glossary")); pm.expect(Object.keys(d.uses[0])).to.eql(["activity","language","reference"]); pm.expect(Object.keys(d)).to.eql(["id","scientificName","displayName","family","names","parts","uses","synonyms","description","origin","oil","useGroups","goals","safety","image","credits"]); });
pm.test("los campos del detalle siguen presentes", () => { ["id","scientificName","displayName","names","parts","uses","synonyms","description","origin","oil","useGroups","goals","safety","image","credits"].forEach(k => pm.expect(d).to.have.property(k)); });
'''
it = req("C2 Detalle: uses y campos raíz", "/v1/plants/lavandula-angustifolia", "", "uses sin glossary.")
it["event"][0]["script"]["exec"] = UT.split("\n")
items.append(it)
OA = r'''
pm.test("200", () => pm.response.to.have.status(200));
const o = pm.response.json();
const s = o.components.schemas;
pm.test("UseGroupDto declara glossary y es obligatorio", () => { pm.expect(s.UseGroupDto.properties).to.have.property("glossary"); pm.expect(s.UseGroupDto.required).to.include("glossary"); });
pm.test("glossary es objeto UseGlossaryDto o null", () => { const p = JSON.stringify(s.UseGroupDto.properties.glossary); pm.expect(p).to.include("UseGlossaryDto"); pm.expect(p).to.include("null"); });
pm.test("UseGlossaryDto describe term, text, sourceName, url y adapted, todos obligatorios", () => { const u = s.UseGlossaryDto; pm.expect(Object.keys(u.properties).sort()).to.eql(["adapted","sourceName","term","text","url"]); pm.expect(u.required.slice().sort()).to.eql(["adapted","sourceName","term","text","url"]); pm.expect(u.properties.adapted.type).to.eql("boolean"); });
pm.test("las propiedades previas de UseGroupDto siguen y glossary es la única nueva (el documento las ordena alfabéticamente)", () => { pm.expect(Object.keys(s.UseGroupDto.properties).sort()).to.eql(["activity","activitySource","count","countries","glossary","references"]); pm.expect(s.UseGroupDto.required.slice().sort()).to.eql(["activity","activitySource","count","countries","glossary","references"]); });
'''
it = req("C3 OpenAPI describe glossary", "/openapi.json", "", "Documento OpenAPI.")
it["request"]["auth"] = {"type": "noauth"}
it["event"][0]["script"]["exec"] = OA.split("\n")
items.append(it)
ERR = r'''
pm.test("401", () => pm.response.to.have.status(401));
pm.test("problem+json y WWW-Authenticate Bearer", () => { pm.expect(pm.response.headers.get("Content-Type")).to.include("application/problem+json"); pm.expect(pm.response.headers.get("WWW-Authenticate")).to.include("Bearer"); });
pm.test("el cuerpo no trae glossary ni datos de la planta", () => { pm.expect(pm.response.text()).to.not.include("glossary"); });
'''
it = req("C4 401 sin token en el detalle", "/v1/plants/lavandula-angustifolia", "", "Sin token.")
it["request"]["auth"] = {"type": "noauth"}
it["event"][0]["script"]["exec"] = ERR.split("\n")
items.append(it)
GOALS = r'''
pm.test("200", () => pm.response.to.have.status(200));
const g = pm.response.json();
pm.test("objetivos: forma sin cambios", () => { const arr = Array.isArray(g) ? g : (g.items || g.goals); pm.expect(arr).to.be.an("array").and.not.empty; pm.expect(JSON.stringify(g)).to.not.include("glossary"); });
'''
it = req("C5 /v1/goals sin cambios", "/v1/goals", "", "Objetivos.")
it["event"][0]["script"]["exec"] = GOALS.split("\n")
items.append(it)
GP = r'''
pm.test("200", () => pm.response.to.have.status(200));
const g = pm.response.json();
pm.test("plantas de un objetivo: elementos como los del listado, sin glossary", () => { pm.expect(g.items).to.be.an("array").and.not.empty; g.items.forEach(p => { pm.expect(p).to.not.have.property("glossary"); pm.expect(p).to.not.have.property("useGroups"); }); });
'''
it = req("C6 /v1/goals/{id}/plants sin cambios", "/v1/goals/relajacion-estres/plants?limit=3", "", "Plantas de un objetivo.")
it["event"][0]["script"]["exec"] = GP.split("\n")
items.append(it)


# --- Cloud Run (2026-10-31): casos añadidos ---
items.append(req("G12 Senna occidentalis: Sucedáneo del café (USDA Coffee) sin glossary y sin Café", "/v1/plants/senna-occidentalis",
    T_ALL + 'pm.test("el uso Coffee de USDA se traduce Sucedáneo del café, sin glossary, y no hay grupo Café", () => { const g = grp("Sucedáneo del café"); pm.expect(g, "grupo").to.exist; pm.expect(g.activitySource).to.eql("Coffee"); pm.expect(g.glossary).to.be.null; pm.expect(grp("Café")).to.be.undefined; pm.expect(j.uses.filter(u => u.activity === "Café").length).to.eql(0); pm.expect(j.uses.filter(u => u.activity === "Sucedáneo del café").length).to.be.above(0); });' +
    'pm.test("Fiebre sin glossary y Purgante adaptado de Wikipedia", () => { pm.expect(grp("Fiebre").glossary).to.be.null; pm.expect(grp("Purgante").glossary.adapted).to.be.true; pm.expect(grp("Purgante").glossary.sourceName).to.eql("Wikipedia"); });' +
    'pm.test("fórmula de enfermedad grave (malaria, lepra) sin glossary", () => { const gs = j.useGroups.filter(g => g.activity.startsWith("Uso tradicional, sin eficacia demostrada: ")); pm.expect(gs.length).to.be.above(0); gs.forEach(g => pm.expect(g.glossary, g.activity).to.be.null); });',
    "Sucedáneo del café (ajuste de revisión), Fiebre y fórmula de enfermedad grave sin glosario."))
items.append(req("G13 Planta con una sola explicación (Cardo: Diurético)", "/v1/plants/cynara-cardunculus",
    T_ALL + 'pm.test("exactamente un grupo con glossary: Diurético de Wikcionario", () => { const gs = j.useGroups.filter(g => g.glossary); pm.expect(gs.length).to.eql(1); pm.expect(gs[0].activity).to.eql("Diurético"); pm.expect(gs[0].glossary.sourceName).to.eql("Wikcionario"); pm.expect(cred(WIKT).length).to.eql(1); });',
    "Una sola explicación."))
items.append(req("G14 Romero: varias explicaciones, Emenagogo y Tónico literales", "/v1/plants/salvia-rosmarinus",
    T_ALL + term_test("Tónico","Tónico",TONI,"Wikcionario",False,W) + 'pm.test("Romero trae 10 explicaciones y los dos créditos una vez", () => { pm.expect(j.useGroups.filter(g => g.glossary).length).to.eql(10); pm.expect(cred(WIKT).length).to.eql(1); pm.expect(cred(WIKI).length).to.eql(1); });',
    "Planta con varias explicaciones."))
items.append(req("G15 Atribución de Wikcionario y de Wikipedia en credits", "/v1/plants/lavandula-angustifolia",
    T_ALL + 'pm.test("atribución de Wikcionario: definiciones tomadas, sin marcado ni notas, primera oración, historial de autores", () => { const a = cred(WIKT)[0].attribution; pm.expect(a).to.include("Wikcionario").and.include("primera oración").and.include("historial"); pm.expect(cred(WIKT)[0].url).to.eql("https://es.wiktionary.org"); });' +
    'pm.test("Wikipedia en credits con licencia y licenseUrl, y menciona el glosario", () => { const c = cred(WIKI)[0]; pm.expect(c.license).to.eql("CC BY-SA 4.0"); pm.expect(c.attribution.toLowerCase()).to.include("glosario"); });',
    "Textos de atribución."))
BADTOK = r"""
pm.test("401 con token inválido", () => pm.response.to.have.status(401));
pm.test("problem+json y sin datos", () => { pm.expect(pm.response.headers.get("Content-Type")).to.include("application/problem+json"); pm.expect(pm.response.text()).to.not.include("glossary"); });
"""
it = req("C7 401 con token inválido en el detalle", "/v1/plants/lavandula-angustifolia", "", "Token incorrecto.")
it["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "token-invalido", "type": "string"}]}
it["event"][0]["script"]["exec"] = BADTOK.split("\n")
items.append(it)

coll = {
    "info": {"name": "Boticario API: QA activity-glossary", "description": "Colección de la QA del cambio activity-glossary. Variables: baseUrl y token (sin valor en el archivo).", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
    "item": items,
}
json.dump(coll, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
print(len(items), "peticiones")
