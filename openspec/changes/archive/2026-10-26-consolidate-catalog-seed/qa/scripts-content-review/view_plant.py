"""Vista compacta de un registro y de lo que dice su paquete: python3 view_plant.py <id> [<id> ...]"""
import json,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from cr_lib import check,GRAVE,RISK,base
ROOT=str(__import__('pathlib').Path(__file__).resolve().parents[5])+'/'
def J(o): return json.dumps(o,ensure_ascii=False)
def view(id,full_safety=False):
    r,res=check(id)
    b=json.load(open(ROOT+f'data/work/bundles/{id}.json')); s=b['sections']; I=b['identity']
    print('='*8,id,'| nuse',len(s['uses']),'| flags',sorted(set(f['code'] for f in r['reviewFlags'])))
    print('IDENT',I['name'],'role=',(I.get('collision') or {}).get('role'),'kind=',I['kind'],'aliases=',I['aliases'],'notes=',I['notes'])
    if I.get('collision'): print('COLL',J({k:I['collision'][k] for k in I['collision'] if k!='decision'}))
    print('B.names',J([(n['language'],n['text'],n['ref'].split(':')[0]) for n in s['names']]))
    print('B.wd',J([(i.get('qid'),i.get('labelEs'),i.get('p1843Es'),i.get('aliasesEs'),i.get('p225')) for i in s['wikidata'].get('items',[])]),s['wikidata'].get('status'))
    print('B.desc',J([(d['ref'],d['text']) for d in s['descriptions']]))
    d=s['distribution'] or {}; print('B.dist',d.get('of'),d.get('native'),d.get('nativeAreas'),d.get('nativeAreaCount'))
    print('B.parts',J([(p['ref'],p['ppna'],p['hasEo']) for p in s['parts']]))
    print('B.reg',J([(x['ref'],x['outcome'],x['combination'],x['therapeuticAreas'],[g['goal'] for g in x['goalCandidates']]) for x in s['regulatory']]))
    for e in s['safety']:
        if e['source']=='tppt': print('B.tppt',e['humanToxicity'],e['categories'],e['level'],'part=',e['toxicPart'],'animal=',e['animalToxicity'],'remarks=',e['remarks'],'major=',[t['name'] for t in e['toxins'] if t.get('major')][:5],'ntox',e['toxinCount'])
        elif e['source']=='efsa': print('B.efsa',e['level'],J(e['concernSubstances']),J([x['substance'] for x in e['evidenceSubstances']]),e['studies'][:3] if e['studies'] else [])
        else: print('B.ema',e['ref'],e.get('status'),e.get('interactionClass'),e.get('severeInteractions'),'level=',e.get('level'),'|',(e.get('text') or '')[:int(900 if full_safety else 450)].replace('\n',' '))
    print('B.uses sens:',[(u['activity'],u['n']) for u in s['uses'] if base(u['activity']) in GRAVE|set(RISK)])
    print('B.images',J([(i['ref'][:60],i['license'],i['mime'],i['author']) for i in s['images']]))
    print('--- RECORD')
    for k in ['aliases','scientificName','family','synonyms','displayName','commonNames','origin','description','partsUsed','oil','goals','safety','image','reviewFlags']:
        v=r.get(k)
        if k=='commonNames': v=[(c['language'],c['text'],[x.split(':')[0] for x in c['refs']]) for c in v]
        if k=='image' and v: v={a:v[a] for a in ('author','license','url','attributionRequired')}
        if k=='reviewFlags': v=[(f['code'],f['target'],f['message'][:110]) for f in v if f['code']!='cita-sin-resolver']+[('cita-sin-resolver x%d'%sum(f['code']=='cita-sin-resolver' for f in v),)]
        if k=='goals': v=[(g['goal'],g['subarea'],g['area'],g['evidence'],g['pendingReview']) for g in v]
        print(k,':',J(v))
    print('traditionalUses (%d):'%len(r['traditionalUses']))
    for i,u in enumerate(r['traditionalUses']):
        print('  [%d] %s <= %s | n=%d | %s | pend=%s | cit=%s'%(i,u['activity'],u['activitySource'],u['n'],', '.join(u['countries']),u['pendingReview'],[(c['key'],(c['text'][:40]) if c['ref'] else 'SR') for c in u['citations']]))
    print('AUTO:')
    for x in res:
        if x[0]=='LEX' and x[2].lower() in ('estimulante','estimulantes','medicinal','medicinales') and x[1].endswith(('cit','activity')): continue
        print('  ',x)
if __name__=='__main__':
    for a in sys.argv[1:]: view(a); print()
