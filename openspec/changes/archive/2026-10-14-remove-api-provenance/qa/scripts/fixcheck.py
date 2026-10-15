import json,urllib.request
def g(u): return json.loads(urllib.request.urlopen(u).read())
def keys(o):
    if isinstance(o,dict):
        for k,v in o.items(): yield k; yield from keys(v)
    elif isinstance(o,list):
        for x in o: yield from keys(x)
for pid in ["lavandula-angustifolia","matricaria-chamomilla"]:
    n=g(f"http://localhost:18096/v1/plants/{pid}"); o=g(f"http://localhost:18098/v1/plants/{pid}")
    print(pid,"claves 'sources' en nuevo:", sum(k=="sources" for k in keys(n)), "en viejo:", sum(k=="sources" for k in keys(o)))
    o["family"]=o["family"]["value"] if o["family"] else None
    for k in("names","parts","uses"): o[k]=[{a:b for a,b in x.items() if a!="sources"} for x in o[k]]
    print("  igual al viejo sin sources:", o==n)
    if pid.startswith("lav"):
        print("  nombres viejos (con sources):", [ (x["text"],x["sources"]) for x in g(f"http://localhost:18098/v1/plants/{pid}")["names"]])
n=g("http://localhost:18096/v1/plants"); print("plantas lavanda en listado:", sum(i["id"]=="lavandula-angustifolia" for i in n["items"]), "total", n["total"])
