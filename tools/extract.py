import os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.environ['CFO_SRC']
OUT=os.path.join(ROOT,'tools','out'); os.makedirs(OUT,exist_ok=True)
import re, json

t=open(SRC,encoding='utf-8').read()
parts=re.split(r'^## Slide (\d+)\s*$',t,flags=re.M)
slides={int(parts[i]):parts[i+1] for i in range(1,len(parts),2)}
def toks(n): return [x.strip() for x in slides[n].split('\n') if x.strip()]
ISIN_RE=re.compile(r'^[A-Z]{2}[A-Z0-9]{9}\d$')

def isin_ok(s):
    d=''.join(str(int(c,36)) for c in s[:-1])
    tot=0
    for i,ch in enumerate(reversed(d)):
        v=int(ch)
        if i%2==0: v*=2
        tot+=v//10+v%10
    return (10-tot%10)%10==int(s[-1])

def pnum(s):
    """'1,73%' -> (1.73, decimals) ; '—' -> None"""
    s=s.strip()
    if s in ('—','-',''): return None
    m=re.match(r'^(-?\d+(?:[.,]\d+)?)\s*(%|años|x)?$',s)
    if not m: raise ValueError(s)
    num=m.group(1).replace(',','.')
    dec=len(num.split('.')[1]) if '.' in num else 0
    return {'v':float(num),'d':dec}

def normtxt(s):
    # decimal dot -> comma only in numeric tokens like 58.2% / 6.4bn
    return re.sub(r'(?<=\d)\.(?=\d+(%|bn|m)\b)', ',', s)

# ---------- map rows (slides 4-6)
maprows=[]
for n in (4,5,6):
    tk=toks(n)
    i=0
    while i<len(tk):
        if ISIN_RE.match(tk[i]):
            r=tk[i:i+9]
            maprows.append(dict(isin=r[0],mapName=r[1],pptCategory=r[2],trailer=pnum(r[3]),ter=pnum(r[4]),
                platforms={'BCV':r[5]=='Sí','BCI':r[6]=='Sí','StoneX':r[7]=='Sí','Pershing':r[8]=='Sí'},
                platformsRaw=r[5:9],mapSlide=n))
            assert all(x in('Sí','No') for x in r[5:9]),r
            i+=9
        else: i+=1

# ---------- fund sheets (slides 7-47)
CHROME={'USO INTERNO INDIVIDUOS','◎  @balanz.international','PRODUCTOS PROPIOS','BALANZ','I N T E R N A T I O N A L','INTERNATIONAL','NEUBERGER BERMAN','Fuentes Factsheet y Reuters'}
TAGS={'RENTA FIJA','RENTA MIXTA','RENTA VARIABLE'}
METRIC_LABELS=['AUM','YTD','1M','3M','6M','1Y','3Y ANUAL.','5Y ANUAL.','3Y ACUM.','5Y ACUM.','2025','2024','YTM BRUTA','DURACIÓN',
 'YIELD RENTA FIJA','DURACIÓN RENTA FIJA','RENTA VARIABLE','RENTA FIJA','CASH','ACCIONES EE.UU.','RENTA FIJA EE.UU.','RENTA FIJA EX-US',
 'ESTILO / UNIVERSO','MAYOR EXPOSICIÓN','ESTILO','CARTERA','PRICE / BOOK','VOL. 5Y']
SECTIONS={'ASIGNACIÓN POR ACTIVO','ASIGNACIÓN POR SUBSECTORES','ASIGNACIÓN SECTORIAL','CALIDAD CREDITICIA','CAPITALIZACIÓN BURSÁTIL',
 'CARACTERÍSTICAS','CARACTERÍSTICAS DE CARTERA','COMPOSICIÓN DE CARTERA','COMPOSICIÓN SECTORIAL','CONTRIBUCIÓN A DURACIÓN','DATOS DE CARTERA',
 'DATOS DEL PRODUCTO','DESGLOSE GEOGRÁFICO','DISTRIBUCIÓN DE INGRESOS','DISTRIBUCIÓN POR ACTIVO','DISTRIBUCIÓN POR DURACIÓN','DISTRIBUCIÓN POR PAÍS',
 'DISTRIBUCIÓN POR SECTOR','DISTRIBUCIÓN POR SECTORES','DISTRIBUCIÓN POR VENCIMIENTO','DISTRIBUCIÓN REGIONAL','DISTRIBUCIÓN SECTORIAL',
 'DURACIÓN POR SECTOR RF','ESTRUCTURA DE CARTERA','EXPOSICIÓN GEOGRÁFICA','EXPOSICIÓN POR PAÍSES','EXPOSICIÓN REGIONAL','POSICIONAMIENTO NETO',
 'PRINCIPALES EMISORES','PRINCIPALES INDUSTRIAS','PRINCIPALES PAÍSES','PRINCIPALES PAÍSES RV','PRINCIPALES POSICIONES','PRINCIPALES SECTORES EX-TREASURY',
 'PRINCIPALES TENENCIAS','VENCIMIENTO EFECTIVO','VENCIMIENTOS','VENCIMIENTOS RENTA FIJA','RENTA FIJA'}
PERF_HEADERS={'PERFORMANCE Y MÉTRICAS CLAVE','PERFORMANCE DE LA CLASE','PERFORMANCE Y ASIGNACIÓN ACTUAL'}

sheets=[]
for n in range(7,48):
    tk=toks(n)
    # remove chrome; drop asset-class tag directly before 'USO INTERNO INDIVIDUOS'
    clean=[]
    for j,x in enumerate(tk):
        if x in CHROME: continue
        if x in TAGS and j+1<len(tk) and tk[j+1]=='USO INTERNO INDIVIDUOS': continue
        clean.append(x)
    tk=clean
    k=next(i for i,x in enumerate(tk) if '·' in x and ISIN_RE.match(x.split('·')[-1].strip()))
    cls,isin=[s.strip() for s in tk[k].split('·')]
    name=tk[k-1]; tag=tk[k-2]; assert '|' in tag,(n,tag)
    o=tk.index('OBJETIVO Y POLÍTICA DE INVERSIÓN')
    intro=' '.join(tk[k+1:o]); objective=tk[o+1]; assert tk[o+2] in PERF_HEADERS,(n,tk[o+2])
    perfHeader=tk[o+2]
    i=o+3; metrics=[]
    special = (n==13)
    while i<len(tk) and tk[i] in METRIC_LABELS and tk[i] not in (SECTIONS-{'RENTA FIJA'}):
        metrics.append((tk[i],tk[i+1])); i+=2
    sections=[]
    if special:
        rest=tk[i:]
        sections=[{'title':'COMPOSICIÓN DE CARTERA','items':[['Repo Treasury EE. UU.','58.2%'],['Repo agencias EE. UU.','24,4%']]},
                  {'title':'VENCIMIENTO EFECTIVO','items':[['1 día','83.3%']]},
                  {'title':'CARACTERÍSTICAS','items':[['WAM','18 días']]}]
        # verify every token of the manual override exists in the slide
        joined=set(rest)
        for s in sections:
            assert s['title'] in joined
            for a,b in s['items']: assert a in joined and b in joined,(a,b)
        leftovers=joined-{s['title'] for s in sections}-{x for s in sections for it in s['items'] for x in it}-{'1','2','RENTA FIJA'}
        assert not leftovers,leftovers
    else:
        cur=None
        while i<len(tk):
            x=tk[i]
            if x in SECTIONS:
                cur={'title':x,'items':[]}; sections.append(cur); i+=1; continue
            assert cur is not None,(n,x)
            cur['items'].append([x,tk[i+1]]); i+=2
    sheets.append(dict(slide=n,tag=tag,name=name,cls=cls,isin=isin,intro=intro,objective=objective,perfHeader=perfHeader,metrics=metrics,sections=sections))

json.dump({'maprows':maprows,'sheets':sheets},open(os.path.join(OUT,'raw.json'),'w'),ensure_ascii=False,indent=1)
print(len(maprows),'map rows;',len(sheets),'sheets')
for r in maprows:
    if not isin_ok(r['isin']): print('BAD CHECK DIGIT map',r['isin'])
for s in sheets:
    if not isin_ok(s['isin']): print('BAD CHECK DIGIT sheet',s['slide'],s['isin'],s['name'])
ms={r['isin'] for r in maprows}; ss={s['isin'] for s in sheets}
print('in map not sheets',ms-ss); print('in sheets not map',ss-ms)
from collections import Counter
print(Counter(m[0] for s in sheets for m in s['metrics']))
