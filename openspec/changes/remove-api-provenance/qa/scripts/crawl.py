import json, urllib.request, urllib.parse, sys
from concurrent.futures import ThreadPoolExecutor
NEW="http://localhost:18095"; OLD="http://localhost:18097"
def get(base,p):
    try:
        r=urllib.request.urlopen(base+p); return r.status, r.headers.get("content-type"), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type"), json.loads(e.read())
def listing(base):
    items=[];off=0
    while True:
        s,_,b=get(base,f"/v1/plants?limit=100&offset={off}")
        assert s==200
        items+=b["items"]; off+=100
        if off>=b["total"]: return items,b["total"]
def keys(o,path="$"):
    if isinstance(o,dict):
        for k,v in o.items():
            yield path+"."+k
            yield from keys(v,path+"."+k)
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from keys(v,path+"[]")
ln,tn=listing(NEW); lo,to=listing(OLD)
print("listado nuevo",len(ln),tn,"viejo",len(lo),to,"igual:",ln==lo)
ids=[i["id"] for i in ln]
def f(i): return i,get(NEW,"/v1/plants/"+urllib.parse.quote(i)),get(OLD,"/v1/plants/"+urllib.parse.quote(i))
def strip_old(o):
    d=dict(o)
    fam=d["family"]; d["family"]=None if fam is None else fam["value"]
    for k in("names","parts","uses"):
        d[k]=[{kk:vv for kk,vv in x.items() if kk!="sources"} for x in d[k]]
    return d
bad=[];nosrc=0;fam_null=[];fam_txt=0;no_uses=[];multi=0;statuses=set();ctypes=set()
allkeys=set();oldsrc_multi=0
with ThreadPoolExecutor(8) as ex:
    for i,(sn,cn,bn),(so,co,bo) in ex.map(f,ids):
        statuses.add((sn,so)); ctypes.add(cn)
        ks=set(keys(bn)); allkeys|=ks
        if any(k.split(".")[-1]=="sources" for k in ks): bad.append((i,"sources en nuevo"))
        if not (bn["family"] is None or isinstance(bn["family"],str)): bad.append((i,"family tipo "+type(bn["family"]).__name__))
        if bn["family"] is None: fam_null.append(i)
        else: fam_txt+=1
        if not bn["uses"]: no_uses.append(i)
        if strip_old(bo)!=bn: bad.append((i,"difiere del viejo sin sources"))
        if list(bn.keys())!=[k for k in bo.keys()]: bad.append((i,"orden de claves top-level difiere"))
print("detalles",len(ids),"estados (nuevo,viejo)",statuses,"content-types",ctypes)
print("family texto",fam_txt,"null",len(fam_null),fam_null[:5],"sin usos",len(no_uses),no_uses[:5])
print("defectos/diferencias",bad[:10],len(bad))
print("claves vistas",sorted(allkeys))
json.dump({"fam_null":fam_null,"no_uses":no_uses},open(sys.argv[1],"w"))
