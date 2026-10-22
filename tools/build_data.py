import os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.environ['CFO_SRC']
OUT=os.path.join(ROOT,'tools','out'); os.makedirs(OUT,exist_ok=True)
import json, re
raw=json.load(open(os.path.join(OUT,'raw.json')))
TXT=open(SRC,encoding='utf-8').read()
parts=re.split(r'^## Slide (\d+)\s*$',TXT,flags=re.M)
slides={int(parts[i]):parts[i+1] for i in range(1,len(parts),2)}
def toks(n): return [x.strip() for x in slides[n].split('\n') if x.strip()]

def num(s):
    s=s.strip()
    if s in ('—',''): return None
    m=re.match(r'^(-?\d+(?:[.,]\d+)?)\s*(%|años|x)?$',s)
    if not m: return None
    n=m.group(1).replace(',','.')
    return {'v':float(n),'d':len(n.split('.')[1]) if '.' in n else 0}
def dispnum(s):  # normalize decimal point to comma for display (formatting only)
    return re.sub(r'(?<=\d)\.(?=\d)',',',s) if re.match(r'^-?\d+\.\d+(%|bn|m)?$',s.strip()) else s

# Assign ISIN from the fees/platform table (slide 6) where sheet ISIN has a transposition
ISIN_ALIAS={'IE00B1D7PY71':'IE00B1D7YP71'}

MANAGER=[('Balanz','Balanz'),('Federated Hermes','Federated Hermes'),('PIMCO','PIMCO'),('Lord Abbett','Lord Abbett'),
 ('FTGF','Franklin Templeton'),('Franklin','Franklin Templeton'),('Templeton','Franklin Templeton'),('Muzinich','Muzinich'),
 ('MFS','MFS'),('BGF','BlackRock'),('BSF','BlackRock'),('NB ','Neuberger Berman'),('Neuberger','Neuberger Berman'),
 ('Schroder','Schroders'),('Wellington','Wellington'),('Barings','Barings'),('Janus Henderson','Janus Henderson'),
 ('Jupiter','Jupiter'),('JPM','J.P. Morgan')]
def manager(mapname):
    for k,v in MANAGER:
        if mapname.startswith(k): return v
    raise ValueError(mapname)

CAT_OVERRIDE={  # productos propios integrados en categorías de la curaduría (instrucción del usuario)
 'XS2621330369':'Money Market','XS3281861446':'Renta Fija Corta Duración','XS2707193509':'Renta Fija Mercados Emergentes',
 'XS2707193418':'Renta Mixta (Balanceado)','XS3067937642':'Renta Variable Global','XS3146740496':'Renta Variable Alternativos'}
CATEGORIES=[('Money Market','rf'),('Renta Fija Ultra Corta Duración','rf'),('Renta Fija Corta Duración','rf'),
 ('Renta Fija Income (Flexible)','rf'),('Renta Fija High Yield','rf'),('Renta Fija Mercados Emergentes','rf'),
 ('Renta Mixta (Balanceado)','rm'),('Renta Variable Global','rv'),('Renta Variable US','rv'),('Renta Variable Growth','rv'),
 ('Renta Variable Mercados Emergentes','rv'),('Renta Variable Commodities','rv'),('Renta Variable Alternativos','rv')]
CATIDX={c:i for i,(c,_) in enumerate(CATEGORIES)}
STRAT={'LIQUIDEZ':'Liquidez','ULTRA CORTA DURACIÓN':'Ultra corta duración','CORTA DURACIÓN':'Corta duración','INCOME':'Income',
 'EM / HIGH YIELD':'EM / High Yield','CORPORATIVOS LATAM':'Corporativos Latam','BALANCEADO':'Balanceado','GLOBAL':'Global',
 'EE. UU.':'Estados Unidos','ESTADOS UNIDOS':'Estados Unidos','TECNOLOGÍA':'Tecnología','LATAM':'Latam',
 'METALES PRECIOSOS':'Metales preciosos','CRIPTOACTIVOS':'Criptoactivos'}
TAGCLASS={'RENTA FIJA':'Renta fija','MULTI-ASSET':'Multi-asset','RENTA MIXTA':'Renta mixta','RENTA VARIABLE':'Renta variable','ALTERNATIVOS':'Alternativos'}
LABEL={'YTM BRUTA':'YTM bruta','DURACIÓN':'Duración','YIELD RENTA FIJA':'Yield renta fija','DURACIÓN RENTA FIJA':'Duración renta fija',
 'RENTA VARIABLE':'Renta variable','RENTA FIJA':'Renta fija','CASH':'Cash','ACCIONES EE.UU.':'Acciones EE. UU.',
 'RENTA FIJA EE.UU.':'Renta fija EE. UU.','RENTA FIJA EX-US':'Renta fija ex-US','ESTILO / UNIVERSO':'Estilo / universo',
 'MAYOR EXPOSICIÓN':'Mayor exposición','ESTILO':'Estilo','CARTERA':'Cartera','PRICE / BOOK':'Price / book','VOL. 5Y':'Vol. 5Y',
 '3Y ACUM.':'3Y acumulado','5Y ACUM.':'5Y acumulado','2025':'Año 2025','2024':'Año 2024'}
RET={'YTD':'ytd','1M':'m1','3M':'m3','6M':'m6','1Y':'y1','3Y ANUAL.':'y3','5Y ANUAL.':'y5'}
def sec_title(t):
    s=t.capitalize()
    for a,b in ((' rf',' RF'),(' rv',' RV'),('ex-treasury','ex-Treasury')): s=s.replace(a,b)
    return s

maprows={r['isin']:r for r in raw['maprows']}
funds=[]
for sh in raw['sheets']:
    isin=ISIN_ALIAS.get(sh['isin'],sh['isin'])
    mr=maprows[isin]
    tag=re.sub(r'\s*\|\s*',' | ',sh['tag'].strip())
    tc,ts=tag.split(' | ')
    isb=mr['mapSlide']==4
    cat=CAT_OVERRIDE.get(isin,mr['pptCategory'])
    assert cat in CATIDX,(isin,cat)
    m=dict(sh['metrics'])
    returns={k:num(m[lab]) if lab in m else None for lab,k in RET.items()}
    extra=[{'label':LABEL[l],'value':dispnum(m[l]),'n':num(m[l])} for l in ('3Y ACUM.','5Y ACUM.','2025','2024') if l in m]
    ytm=dur=None; rfPortion=False
    if 'YTM BRUTA' in m: ytm=num(m['YTM BRUTA']); dur=num(m['DURACIÓN'])
    elif 'YIELD RENTA FIJA' in m: ytm=num(m['YIELD RENTA FIJA']); dur=num(m['DURACIÓN RENTA FIJA']); rfPortion=True
    key=[{'label':LABEL[l],'value':dispnum(v)} for l,v in sh['metrics'] if l not in RET and l!='AUM' and l not in ('3Y ACUM.','5Y ACUM.','2025','2024')]
    sections=[]
    for s in sh['sections']:
        items=[{'label':a,'value':dispnum(b),'pct':(num(b)['v'] if (b.strip().endswith('%') and num(b)) else None)} for a,b in s['items']]
        sections.append({'title':sec_title(s['title']),'items':items})
    funds.append(dict(
        isin=isin, sheetIsin=sh['isin'], name=sh['name'], mapName=mr['mapName'], manager=manager(mr['mapName']), balanz=isb,
        cls=sh['cls'], currency='USD' if 'USD' in sh['cls'] else None,
        category=cat, pptCategory=mr['pptCategory'], asset=dict(CATEGORIES)[cat],
        tag=TAGCLASS[tc]+' | '+STRAT[ts], strategy=STRAT[ts],
        intro=sh['intro'], objective=sh['objective'],
        aum=dispnum(m['AUM']), returns=returns, extraReturns=extra, ytm=ytm, duration=dur, rfPortion=rfPortion,
        keyMetrics=key, ter=mr['ter'], trailer=mr['trailer'], platforms=mr['platforms'],
        perfHeader=sh['perfHeader'], sections=sections, compDate='31/08' if isb else '31/07', slide=sh['slide'], mapSlide=mr['mapSlide']))
funds.sort(key=lambda f:(CATIDX[f['category']], 0 if f['balanz'] else 1, f['mapSlide'], [r['isin'] for r in raw['maprows']].index(f['isin'])))

# ---- institutional content (slides 1-3), literal
s2=toks(2); s3=toks(3)
def after(tk,label): return tk[tk.index(label)+1]
inst={
 'kicker2':s2[0], 'headline':s2[1], 'intro':s2[2], 'universeFigure':s2[3], 'universeLabel':s2[4], 'challenge':s2[5],
 'steps':[{'n':s2[i],'title':s2[i+1],'text':s2[i+2]} for i in (6,9,12,15)],
 'diversification':s2[18], 'profiles':[p.strip() for p in s2[19].split('•')],
 'kicker3':s3[0], 'headline3':s3[1]+' '+s3[2], 'intro3':s3[3],
 'pillars':[{'n':s3[i],'title':s3[i+1],'text':s3[i+2]} for i in (4,7,10)],
 'nextTitle':s3[13], 'nextText':s3[14], 'disclaimer':s3[15]}
s1=toks(1); s4=toks(4); s5=toks(5)
cut=next(x for x in s1 if x.startswith('Performance'))
perf,comp=[x.strip() for x in cut.split('|')]
meta={'title':'Curaduría de Fondos Offshore','cutoff':cut,'performance':perf,'composition':comp,'legend':'USO INTERNO · INDIVIDUOS',
 'feeNote':s5[-7] if False else next(x for x in s5 if x.startswith('Trailer fee y TER')),
 'feeSource':next(x for x in s5 if x.startswith('Fuente:')), 'sheetSource':'Fuentes: Factsheet y Reuters',
 'disclaimer':inst['disclaimer']}
data={'meta':meta,'institutional':inst,'categories':[{'name':c,'asset':a} for c,a in CATEGORIES],'funds':funds}
json.dump(data,open(os.path.join(ROOT,'data','funds.json'),'w'),ensure_ascii=False,indent=1)
print('funds.json:',len(funds),'fondos')
