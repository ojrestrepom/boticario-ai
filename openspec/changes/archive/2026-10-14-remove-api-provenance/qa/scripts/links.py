import re,sys,os,urllib.parse,glob
root="/Users/jsrc1115/Code/boticario-ai"
def slug(h):
    h=re.sub(r'[`*_]','',h.strip().lower()) if False else h.strip().lower()
    h=re.sub(r'`','',h); h=re.sub(r'[*]','',h)
    h=re.sub(r'\[([^\]]*)\]\([^)]*\)',r'\1',h)
    h=re.sub(r'[^\w\- ]','',h,flags=re.UNICODE)
    return h.replace(' ','-')
def anchors(path):
    out=set();cnt={};infence=False
    for l in open(path,encoding='utf8'):
        if l.lstrip().startswith('```'): infence=not infence; continue
        if infence: continue
        m=re.match(r'^(#{1,6})\s+(.*?)\s*#*\s*$',l)
        if m:
            s=slug(m.group(2)); n=cnt.get(s,0); cnt[s]=n+1
            out.add(s if n==0 else f"{s}-{n}")
    return out
def check(files):
    total=0;bad=[]
    for f in files:
        txt=open(f,encoding='utf8').read()
        txt=re.sub(r'```.*?```','',txt,flags=re.S)
        txt=re.sub(r'`[^`\n]*`',lambda m:'`'+'x'*(len(m.group(0))-2)+'`',txt)  # ignore inline code
        for m in re.finditer(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)|!\[[^\]]*\]\(([^)\s]+)\)',txt):
            t=m.group(1) or m.group(2)
            if re.match(r'^[a-z][a-z0-9+.-]*:',t): continue
            total+=1
            p,_,a=t.partition('#'); p=urllib.parse.unquote(p); a=urllib.parse.unquote(a)
            dest=f if p=='' else os.path.normpath(os.path.join(os.path.dirname(f),p))
            if not os.path.exists(dest): bad.append((f,t,'no existe')); continue
            if a and dest.endswith('.md') and a.lower() not in anchors(dest): bad.append((f,t,'anclaje'))
    return total,bad
files=[root+"/README.md",root+"/backend/README.md"]+sorted(glob.glob(root+"/docs/**/*.md",recursive=True))
t,b=check(files); print("archivos",len(files),"enlaces",t,"rotos",len(b)); [print(" ",x) for x in b]
# control negativo
import tempfile
d=tempfile.mkdtemp(dir=sys.argv[1]); open(d+"/a.md","w").write("# Titulo Uno\n[ok](#titulo-uno) [mal](#nada) [mal2](no%20existe.md) [mal3](a.md#otro) [ok2](a.md#titulo-uno)\n")
t,b=check([d+"/a.md"]); print("control negativo: enlaces",t,"rotos detectados",len(b),"(esperado 3)")
