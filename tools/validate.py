import os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.environ['CFO_SRC']
OUT=os.path.join(ROOT,'tools','out'); os.makedirs(OUT,exist_ok=True)
import json,re
d=json.load(open(os.path.join(ROOT,'data','funds.json'))); F=d['funds']
T=open(SRC,encoding='utf-8').read()
parts=re.split(r'^## Slide (\d+)\s*$',T,flags=re.M)
S={int(parts[i]):parts[i+1] for i in range(1,len(parts),2)}
def n(s): return re.sub(r'\s+',' ',s.replace('.',',')).strip()
err=[]
mapisins=re.findall(r'^([A-Z]{2}[A-Z0-9]{9}\d)$',S[4]+'\n'+S[5]+'\n'+S[6],flags=re.M)
if len(F)!=41: err.append('count')
if sorted(mapisins)!=sorted(f['isin'] for f in F): err.append('isin set')
if len(set(f['isin'] for f in F))!=41: err.append('dup isin')
for f in F:
    sl=S[f['slide']]; sln=n(sl); maptxt=n(S[f['mapSlide']])
    if f['sheetIsin'] not in sl: err.append(('sheet isin',f['isin']))
    if f['intro'] not in sl: err.append(('intro',f['isin']))
    if f['objective'] not in sl: err.append(('objective',f['isin']))
    def chk(val,where=sln):
        if n(val) not in where: err.append(('value',f['isin'],val))
    chk(f['aum'])
    for k,r in f['returns'].items():
        if r: chk(f"{r['v']:.{r['d']}f}%")
    for x in f['extraReturns']+f['keyMetrics']: chk(x['value'])
    for s in f['sections']:
        for it in s['items']: chk(it['label']); chk(it['value'])
    for r in (f['ter'],f['trailer']): chk(f"{r['v']:.{r['d']}f}%",maptxt)
    if f['asset']=='rf' and (f['ytm'] is None or f['duration'] is None): err.append(('rf ytm/dur',f['isin']))
    if f['balanz'] and not (f['platforms']['StoneX'] and f['platforms']['Pershing']): err.append(('balanz platforms',f['isin']))
exp={'XS2621330369':'Money Market','XS3281861446':'Renta Fija Corta Duración','XS2707193509':'Renta Fija Mercados Emergentes','XS2707193418':'Renta Mixta (Balanceado)','XS3067937642':'Renta Variable Global','XS3146740496':'Renta Variable Alternativos'}
for i,c in exp.items():
    if next(f for f in F if f['isin']==i)['category']!=c: err.append(('cat',i))
# returns 'missing' only where PPT shows — or label absent
for f in F:
    sl=S[f['slide']]
    for k,lab in (('m1','1M'),('m3','3M'),('y1','1Y'),('y3','3Y ANUAL.'),('y5','5Y ANUAL.')):
        if f['returns'][k] is None:
            m=re.search(r'^'+re.escape(lab)+r'\s*\n\s*\n?(.*)$',sl,flags=re.M)
            if m and m.group(1).strip()!='—': err.append(('null but value',f['isin'],lab))
html=open(os.path.join(ROOT,'index.html')).read()
if 'Nota sobre los datos' in html: err.append('nota')
print('ERRORES:',err if err else 'ninguno')
print('Fondos:',len(F),'| propios:',sum(f['balanz'] for f in F))
if err: sys.exit(1)
print('Nulls:',[(f['name'],[k for k,r in f['returns'].items() if r is None]) for f in F if any(r is None for r in f['returns'].values())])
