"""Comprobaciones automáticas de la revisión de contenido (tarea 10.5): compara cada registro con su paquete."""
import json,re,glob,sys,collections,unicodedata
from pathlib import Path
ROOT=str(Path(__file__).resolve().parents[5])+'/'
sa=json.load(open(ROOT+'tools/catalog-seed/sensitive-activities.json'))['categories']
GRAVE={t.lower() for t in sa['enfermedad-grave']['terms']}
RISK={t.lower():v for t,v in sa['senal-de-riesgo']['terms'].items()}
PREFIX=sa['enfermedad-grave']['formulaPrefix']
def base(a): return a.split('(')[0].strip().lower()
def norm(s): return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().strip()
LEX=re.compile(r"\b(dosis|posolog\w*|mg|ml|gramos?|kg|\d+\s*%|veces al d[ií]a|cada \d+|cucharad\w*|gotas?|infusi[oó]n|decocci[oó]n|tintura|t[eé]\b|prepar\w+|tomar|tome|toma|ingerir|consum\w+|debe\w*|evit\w+|evite|consulte|consultar|recomend\w+|se recomienda|no use|no utilice|use\b|utilice|cura\w*|curar|trata\w*|tratamientos?|previen\w*|prevenir|elimina\w*|alivia\w*|aliviar|eficaz\w*|eficacia|efectiv\w*|ayuda\w*|beneficio\w*|beneficios\w*|propiedades|remedio\w*|terap[eé]utic\w*|calma\w*|mejora\w*|reduc\w+|combat\w+|sana\w*|sanar|fortalece\w*|refuerza\w*|estimula\w*|útil|util|ideal|seguro|segura|inocu\w+|sin riesgo|medicinal(?:es)?)\b",re.I)
def texts(r):
    out=[]
    def add(path,t):
        if isinstance(t,str): out.append((path,t))
    add('description',(r.get('description') or {}).get('value'))
    add('origin',(r.get('origin') or {}).get('value'))
    add('safety',(r.get('safety') or {}).get('text'))
    for i,g in enumerate(r['goals']): add(f'goals[{i}].area',g['area']); add(f'goals[{i}].evidence',g['evidence'])
    for i,u in enumerate(r['traditionalUses']):
        add(f'tu[{i}].activity',u['activity'])
        for c in u['citations']: add(f'tu[{i}].cit',c['text'])
    for i,f in enumerate(r['reviewFlags']): add(f'flag[{i}]',f['message'])
    for i,p in enumerate(r['partsUsed']): add(f'parts[{i}]',p['value'])
    return out
def check(id,verbose=True):
    r=json.load(open(ROOT+f'data/seed/plants/{id}.json'))
    b=json.load(open(ROOT+f'data/work/bundles/{id}.json'))
    s=b['sections']; res=[]
    # lexical
    for p,t in texts(r):
        t2=t.replace('Uso tradicional, sin eficacia demostrada','')
        for m in LEX.finditer(t2):
            res.append(('LEX',p,m.group(0),t[:160]))
    # names
    pool=set()
    for n in s['names']: pool.add(norm(n['text']))
    for it in s['wikidata'].get('items',[]):
        if it.get('labelEs'): pool.add(norm(it['labelEs']))
        for x in it.get('p1843Es') or []: pool.add(norm(x))
        for x in it.get('aliasesEs') or []: pool.add(norm(x))
    desc=' '.join(norm(d['text']) for d in s['descriptions'])
    dn=r['displayName']
    if dn['language']!='la' and norm(dn['value']) not in pool and norm(dn['value']) not in desc:
        res.append(('NAME','displayName',dn['value'],'no esta en names/wikidata/desc'))
    for c in r['commonNames']:
        if norm(c['text']) not in pool and norm(c['text']) not in desc:
            res.append(('NAME','commonNames',c['text']+'/'+c['language'],'no esta en names/wikidata/desc'))
    # language check vs bundle
    bl={}
    for n in s['names']: bl.setdefault(norm(n['text']),set()).add(n['language'])
    for c in r['commonNames']:
        k=norm(c['text'])
        if k in bl and c['language'] not in bl[k] and not (c['language']=='es' and 'und' in bl[k]):
            res.append(('LANG','commonNames',c['text'],f"registro {c['language']} paquete {bl[k]}"))
    # uses
    ub={}
    for u in s['uses']: ub.setdefault(u['activity'],[]).append(u)
    sens_b={u['activity'] for u in s['uses'] if base(u['activity']) in GRAVE|set(RISK)}
    for i,u in enumerate(r['traditionalUses']):
        src=u['activitySource']
        if src not in ub: res.append(('USE','tu[%d]'%i,src,'activitySource no esta en el paquete')); continue
        bu=ub[src][0]
        if bu['n']!=u['n']: res.append(('USE','tu[%d]'%i,src,f"n {u['n']} vs {bu['n']}"))
        if base(src) in GRAVE and not u['activity'].startswith(PREFIX): res.append(('SENS','tu[%d]'%i,src,'sin formula: '+u['activity']))
        if base(src) in RISK: res.append(('SENS','tu[%d]'%i,src,'senal de riesgo en usos'))
        if base(src) not in GRAVE and u['activity'].startswith(PREFIX): res.append(('SENS','tu[%d]'%i,src,'formula en actividad no grave'))
        if not set(u['refs'])<=set(bu['refs'])|{c['ref'] for c in u['citations'] if c['ref']}: res.append(('USE','tu[%d]'%i,src,'refs fuera del grupo'))
        if set(bu['refs'])-set(u['refs']) and 'refsTotal' not in bu: res.append(('USE','tu[%d]'%i,src,'faltan refs usda_use'))
        if [c['key'] for c in u['citations']]!=bu['citations']: res.append(('CITE','tu[%d]'%i,src,f"claves {[c['key'] for c in u['citations']]} vs {bu['citations']}"))
        cand=bu.get('candidates',{})
        for c in u['citations']:
            if c['ref'] is None:
                if c['text']!=c['key']+' (sin resolver)': res.append(('CITE','tu[%d]'%i,c['key'],'texto sin resolver raro: '+c['text']))
                if c['key'] in cand: res.append(('CITE','tu[%d]'%i,c['key'],'sin resolver pero hay candidatas: '+json.dumps([x['ref'] for x in cand[c['key']]])))
            else:
                if c['key'] not in cand or c['ref'] not in [x['ref'] for x in cand[c['key']]]: res.append(('CITE','tu[%d]'%i,c['key'],'ref no es candidata '+c['ref']))
        if u['pendingReview'] != all(c['ref'] is None for c in u['citations']): res.append(('CITE','tu[%d]'%i,src,'pendingReview incoherente'))
    # activities missing from record
    tus={u['activitySource'] for u in r['traditionalUses']}
    grouped=len(ub)
    omitted=[a for a in ub if a not in tus and base(a) not in RISK]
    if len(r['traditionalUses'])<min(20,len([a for a in ub if base(a) not in RISK])): res.append(('USE','all','', 'faltan actividades %d vs %d'%(len(r['traditionalUses']),len([a for a in ub if base(a) not in RISK]))))
    # risk signals in safety
    risk_b=[u for u in s['uses'] if base(u['activity']) in RISK]
    if risk_b:
        st=(r['safety'] or {}).get('text','')
        for u in risk_b:
            phrase=RISK[base(u['activity'])]
            if phrase not in st: res.append(('SENS','safety',u['activity'],'falta frase '+phrase))
            miss=[x for x in u['refs'] if x not in (r['safety'] or {}).get('refs',[])]
            if miss: res.append(('SENS','safety',u['activity'],'faltan refs '+str(miss[:3])))
    # image
    im=r.get('image')
    if im:
        bi=[i for i in s['images'] if i['url']==im['url']]
        if not bi: res.append(('IMG','image','','url no esta en paquete'))
        else:
            bi=bi[0]
            if bi['mime'] not in ('image/jpeg','image/png','image/webp','image/gif','image/svg+xml'): res.append(('IMG','image',bi['mime'],'mime no mostrable'))
            if bi['author'] is not None and bi['author']!=im['author']: res.append(('IMGAUTH','image',im['author'],'paquete: '+str(bi['author'])))
        a=im['author'] or ''
        if re.search(r'@|\blicen[cs]e|\bcc[- ]by|assumed|own work|\bunknown\b|<|>|http|&\w+;',a,re.I): res.append(('IMGAUTH','image',a,'autor sospechoso'))
        if im['license'] and 'CC BY' in im['license'].upper() and not im['attributionRequired']: res.append(('IMG','image',im['license'],'attributionRequired falso'))
    # level coherence
    levels=[e.get('level') for e in s['safety'] if e.get('level')]
    order={'bajo':1,'medio':2,'alto':3}
    exp=max(levels,key=lambda x:order[x]) if levels else None
    sf=r['safety']
    if sf and sf['level']!=exp: res.append(('SAFE','safety',str(sf['level']),f'esperado {exp}'))
    if not sf and (s['safety'] or risk_b): res.append(('SAFE','safety','null','hay entradas en el paquete'))
    # goals vs tox
    tppt=[e for e in s['safety'] if e['source']=='tppt']
    for g in r['goals']:
        if not set(g['refs'])<=set(r['refs']): res.append(('REF','goals',g['goal'],'ref'))
    for k in r['refs']:
        if k not in b['refs']: res.append(('REF','refs',k,'no en paquete'))
    return r,res
if __name__=='__main__':
    for a in sys.argv[1:]:
        r,res=check(a)
        print('##',a)
        for x in res: print('  ',x)
