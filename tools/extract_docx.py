"""Lee el Word de la Curaduría de Fondos Offshore y escribe data/funds.json.

Uso:  python tools/extract_docx.py ruta/al/documento.docx
No inventa datos: todo valor proviene del documento. Si la estructura cambia, aborta.
"""
import os, re, sys, json, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get('CFO_SRC') or (sys.argv[1] if len(sys.argv) > 1 else '')
if not SRC:
    sys.exit(__doc__)

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

# ---------------------------------------------------------------- utilidades
def body_items(doc):
    for ch in doc.element.body.iterchildren():
        if ch.tag.endswith('}p'):
            yield Paragraph(ch, doc)
        elif ch.tag.endswith('}tbl'):
            yield Table(ch, doc)

def rows_of(t):
    return [[c.text.strip() for c in r.cells] for r in t.rows]

ISIN_RE = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}\d$')

def isin_ok(s):
    d = ''.join(str(int(c, 36)) for c in s[:-1])
    tot = 0
    for i, ch in enumerate(reversed(d)):
        v = int(ch) * (2 if i % 2 == 0 else 1)
        tot += v // 10 + v % 10
    return (10 - tot % 10) % 10 == int(s[-1])

def num(s):
    """'1,73%' -> {'v':1.73,'d':2}; '—' -> None. Conserva los decimales de la fuente."""
    s = (s or '').strip()
    if s in ('—', '-', ''):
        return None
    m = re.match(r'^(-?\d+(?:[.,]\d+)?)\s*%?\s*(años|x)?$', s)
    if not m:
        return None
    n = m.group(1).replace(',', '.')
    return {'v': float(n), 'd': len(n.split('.')[1]) if '.' in n else 0}

def dec_comma(s):
    """Normaliza el separador decimal a coma (solo formato, no cambia el valor)."""
    return re.sub(r'(?<=\d)\.(?=\d)', ',', (s or '').strip())

def upper_first(s):
    s = (s or '').strip()
    return s[0].upper() + s[1:] if s and s[0].islower() else s

def strip_ac(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def letters(s):
    return re.sub(r'[^a-z0-9]', '', strip_ac(s).lower())

# ------------------------------------------------- nombre, clase y gestora
KEEP = {'PIMCO', 'JPM', 'FTGF', 'BGF', 'BSF', 'MFS', 'ISF', 'GIS', 'US', 'U.S.', 'UK', 'EM', 'ETF',
        'ETP', 'IG', 'HY', 'MBS', 'ABS', 'CLO', 'TIPS', 'LATAM', 'OIS', 'WAM', 'WAL', 'NB', 'ESG',
        'USD', 'EUR', 'GBP', 'CHF', 'JPY', 'USDHDG', 'EE.', 'UU.', 'REIT', 'ADR'}
MINOR = {'and', 'y', 'de', 'del', 'la', 'el', 'los', 'las', 'of', 'the', 'en'}
MANAGERS = [('BALANZ', 'Balanz'), ('FEDERATED', 'Federated Hermes'), ('PIMCO', 'PIMCO'),
            ('LORD ABBETT', 'Lord Abbett'), ('FTGF', 'Franklin Templeton'), ('FRANKLIN', 'Franklin Templeton'),
            ('TEMPLETON', 'Franklin Templeton'), ('MUZINICH', 'Muzinich'), ('MFS', 'MFS'),
            ('BGF', 'BlackRock'), ('BSF', 'BlackRock'), ('NEUBERGER', 'Neuberger Berman'),
            ('SCHRODER', 'Schroders'), ('WELLINGTON', 'Wellington'), ('BARINGS', 'Barings'),
            ('JANUS HENDERSON', 'Janus Henderson'), ('JUPITER', 'Jupiter'), ('JPM', 'J.P. Morgan'),
            ('CALAMOS', 'Calamos')]

def manager_of(raw):
    for k, v in MANAGERS:
        if raw.startswith(k):
            return v
    raise SystemExit(f'Gestora no reconocida para: {raw}. Agregarla a MANAGERS en tools/extract_docx.py')

def title_case(s):
    out = []
    for i, w in enumerate(s.split()):
        if w in KEEP or (len(w) > 1 and not w.isalpha() and w.upper() == w and '&' not in w):
            out.append(w)
        elif w.lower() in MINOR and i > 0:
            out.append(w.lower())
        elif w == '&':
            out.append('&')
        else:
            out.append(w[0] + w[1:].lower())
    return ' '.join(out)

def split_name(raw):
    """Separa nombre y clase del nombre completo en mayúsculas del documento."""
    base, cls = raw, None
    m = re.match(r'^(?P<b>.*?)\s*"(?P<c>[^"]+)"\s*(?P<r>.*)$', raw)
    if m:
        base = m.group('b').strip()
        cls = (m.group('c') + ' ' + m.group('r')).strip()
    else:
        m = re.match(r'^(?P<b>.*?)\s+(?P<c>[A-Z]\d?\s+(?:USD|EUR)(?:\s+HDG)?\s+ACC)$', raw)
        if m:
            base, cls = m.group('b').strip(), m.group('c').strip()
    if cls:
        cls = re.sub(r'\bACC\b', 'Acc', cls)
        cls = re.sub(r'\bINC\b', 'Inc', cls)
        cls = re.sub(r'\s+', ' ', cls).strip()
    base = re.sub(r'\s+(FUND|FONDO)$', '', base).strip()
    return base, cls

# ---------------------------------------------------------------- categorías
ASSET_OF = {'RENTA FIJA': 'rf', 'RENTA MIXTA': 'rm', 'RENTA VARIABLE': 'rv'}

def canon_cat(raw):
    """'RENTA VARIABLE RENTA VARIABLE US' -> 'Renta Variable US';
       'Renta Fija Liquidez / Money Market' -> 'Renta Fija Liquidez'."""
    s = re.sub(r'\s+', ' ', raw.strip())
    s = re.sub(r'\s*/\s*Money Market$', '', s, flags=re.I)
    u = s.upper()
    for pref in ('RENTA VARIABLE', 'RENTA FIJA', 'RENTA MIXTA'):
        if u.startswith(pref + ' ' + pref):
            u = pref + u[len(pref) * 2 + 1:]
            break
    asset = next((a for p, a in ASSET_OF.items() if u.startswith(p)), None)
    if not asset:
        raise SystemExit(f'Categoría sin clase de activo reconocible: {raw}')
    pref = next(p for p in ASSET_OF if u.startswith(p))
    rest = u[len(pref):].strip()
    name = title_case(pref) + (' ' + title_case(rest) if rest else '')
    return re.sub(r'\s+', ' ', name).strip(), asset

# ---------------------------------------------------------------- documento
doc = docx.Document(SRC)
seq = list(body_items(doc))

def is_fund_head(n):
    it = seq[n]
    return (isinstance(it, Paragraph) and it.style.name == 'Heading 1'
            and any(isinstance(seq[m], Paragraph) and seq[m].text.strip().startswith('ISIN ')
                    for m in range(n + 1, min(n + 4, len(seq)))))

heads = [n for n in range(len(seq)) if is_fund_head(n)]
if not heads:
    sys.exit('No se encontraron fichas de fondos en el documento.')

# ---- portada
cover = [p.text.strip() for p in seq[:heads[0]] if isinstance(p, Paragraph) and p.text.strip()]
perf_line = next(x for x in cover if x.lower().startswith('performance al'))
comp_line = next(x for x in cover if x.lower().startswith('composición'))
src_line = next(x for x in cover if x.lower().startswith('fuente'))
scope_line = next((x for x in cover if x.lower().startswith('el documento reúne')), '')

# ---- metodología (encabezados Heading 2 antes de la primera ficha)
metodologia = {'titulo': '', 'intro': '', 'bloques': []}
for n in range(heads[0]):
    it = seq[n]
    if not isinstance(it, Paragraph) or not it.text.strip():
        continue
    if it.style.name == 'Heading 1':
        if metodologia['titulo'] or it.text.strip().lower().startswith('mapa de fondos'):
            continue          # los mapas también son Heading 1
        metodologia['titulo'] = it.text.strip()
        metodologia['intro'] = next((seq[m].text.strip() for m in range(n + 1, heads[0])
                                     if isinstance(seq[m], Paragraph) and seq[m].text.strip()
                                     and seq[m].style.name == 'Normal'), '')
    elif it.style.name == 'Heading 2':
        txt = []
        for m in range(n + 1, heads[0]):
            o = seq[m]
            if not isinstance(o, Paragraph):
                break
            if o.style.name.startswith('Heading'):
                break
            if o.text.strip():
                txt.append(o.text.strip())
        metodologia['bloques'].append({'titulo': it.text.strip(), 'parrafos': txt})

# ---- mapas de fondos (tablas con encabezado ISIN)
maprows = {}
mapcats = []          # categorías en el orden del documento, tablas de terceros primero
PLAT_CANON = {'bcv': 'BCV', 'bci': 'BCI', 'stonex': 'StoneX', 'pershing': 'Pershing'}
maptables = []
for n in range(heads[0]):
    it = seq[n]
    if isinstance(it, Table):
        rows = rows_of(it)
        if rows[0][0] != 'ISIN':
            continue
        title = next((seq[m].text.strip() for m in range(n - 1, max(n - 3, -1), -1)
                      if isinstance(seq[m], Paragraph) and seq[m].text.strip()), '')
        maptables.append((('BALANZ' in title.upper()), rows))
for es_balanz, rows in sorted(maptables, key=lambda x: x[0]):
    hdr = rows[0]
    for r in rows[1:]:
        rec = dict(zip(hdr, r))
        if not ISIN_RE.match(rec['ISIN']):
            sys.exit(f'ISIN inválido en el mapa: {rec["ISIN"]}')
        maprows[rec['ISIN']] = rec
        c = canon_cat(rec['Categoría'])[0]
        if c not in mapcats:
            mapcats.append(c)
if not maprows:
    sys.exit('No se encontraron las tablas "Mapa de fondos".')

# ---- fichas
PERF_HDR = ['AUM USD mill.', 'YTD', '1M', '3M', '6M', '1Y', '3Y anual.', '5Y anual.']
MET_HDR = ['YTM bruta', 'Duración', 'Trailer fee', 'TER', 'Plataformas', 'Categoría']
RET_KEY = {'YTD': 'ytd', '1M': 'm1', '3M': 'm3', '6M': 'm6', '1Y': 'y1', '3Y anual.': 'y3', '5Y anual.': 'y5'}

funds = []
warnings = []
ASSET_RANK = {'rf': 0, 'rm': 1, 'rv': 2}
for k, n in enumerate(heads):
    end = heads[k + 1] - 1 if k + 1 < len(heads) else len(seq)
    blk = seq[n:end]
    raw_name = seq[n].text.strip()
    paras = [x for x in blk if isinstance(x, Paragraph)]
    tabs = [x for x in blk if isinstance(x, Table)]
    if len(tabs) != 3:
        sys.exit(f'{raw_name}: se esperaban 3 tablas y hay {len(tabs)}.')

    isin_line = next(p.text.strip() for p in paras if p.text.strip().startswith('ISIN '))
    isin = isin_line.split()[1]
    if not ISIN_RE.match(isin) or not isin_ok(isin):
        warnings.append(f'{raw_name}: ISIN {isin} no supera el dígito verificador.')
    if isin not in maprows:
        sys.exit(f'{raw_name}: el ISIN {isin} no figura en las tablas "Mapa de fondos".')

    # tagline anterior al título (PRODUCTOS BALANZ · ...) o categoría del mapa
    tag_prev = next((seq[m].text.strip() for m in range(n - 1, max(n - 3, -1), -1)
                     if isinstance(seq[m], Paragraph) and seq[m].text.strip()), '')
    balanz = tag_prev.startswith('PRODUCTOS BALANZ')

    # objetivo: párrafos entre el Heading 3 "Objetivo..." y el siguiente Heading
    obj = []
    grab = False
    for p in paras:
        if p.style.name.startswith('Heading'):
            if p.text.strip().lower().startswith('objetivo'):
                grab = True
                continue
            grab = False
        elif grab and p.text.strip():
            obj.append(p.text.strip())
    if not obj:
        sys.exit(f'{raw_name}: no se encontró "Objetivo y política de inversión".')
    objective = upper_first(' '.join(obj))

    perf, met = rows_of(tabs[0]), rows_of(tabs[1])
    if perf[0] != PERF_HDR or met[0] != MET_HDR:
        sys.exit(f'{raw_name}: cambió el encabezado de las tablas de performance o métricas.')
    pv, mv = dict(zip(perf[0], perf[1])), dict(zip(met[0], met[1]))

    returns = {RET_KEY[k2]: num(pv[k2]) for k2 in RET_KEY}
    ytm = num(mv['YTM bruta'])
    dur_raw = mv['Duración']
    duration = num(dur_raw)
    if '%' in dur_raw and duration is not None:
        warnings.append(f'{raw_name}: la duración figura como "{dur_raw}" (con % en el documento); '
                        f'se interpreta como {dec_comma(str(duration["v"]))} años.')
    ter, trailer = num(mv['TER']), num(mv['Trailer fee'])
    plats_raw = [x.strip() for x in mv['Plataformas'].split(',') if x.strip()]
    unknown = [p for p in plats_raw if p.lower() not in PLAT_CANON]
    if unknown:
        sys.exit(f'{raw_name}: plataforma desconocida {unknown}.')
    plat_set = {PLAT_CANON[p.lower()] for p in plats_raw}
    platforms = {p: (p in plat_set) for p in ('BCV', 'BCI', 'StoneX', 'Pershing')}

    mapcat = maprows[isin]['Categoría']
    category, asset = canon_cat(mapcat)
    clasif_raw = mv['Categoría']      # taxonomía técnica del documento (FI/EQ/MM/MA)
    clasif = clasif_raw if re.match(r'^[A-Z]{2}\s*-\s*', clasif_raw) else None

    # composición: tabla de maquetación con tablas anidadas por sección
    sections = []
    for row in tabs[2].rows:
        for cell in row.cells:
            title = cell.paragraphs[0].text.strip()
            for nt in cell.tables:
                nr = rows_of(nt)
                head = nr[0]
                items = []
                for r in nr[1:]:
                    if len(head) == 1:
                        items.append({'label': upper_first(r[0]), 'value': None, 'pct': None})
                    else:
                        val = dec_comma(r[1])
                        p = num(val)
                        items.append({'label': upper_first(r[0]), 'value': val,
                                      'pct': (p['v'] if (val.endswith('%') and p) else None)})
                if items:
                    sections.append({'title': upper_first(title) or 'Composición', 'items': items})

    notes = [p.text.strip() for p in paras
             if p.text.strip().startswith(('Nota de fuente:', 'Datos adicionales:'))]
    comp_line_f = next((p.text.strip() for p in paras if p.text.strip().startswith('Fuente Factsheet')), '')
    m = re.search(r'Composición al\s+([\d/]+)', comp_line_f)
    comp_date = m.group(1) if m else ''

    base, cls = split_name(raw_name)
    name = title_case(base)
    funds.append({
        'isin': isin, 'sheetIsin': isin, 'name': name, 'mapName': raw_name,
        'manager': manager_of(raw_name), 'balanz': balanz, 'cls': cls,
        'currency': 'USD' if (cls and 'USD' in cls.upper()) or balanz else None,
        'category': category, 'pptCategory': mapcat, 'asset': asset,
        'tag': category,
        'strategy': clasif or '', 'intro': '', 'objective': objective,
        'aum': pv['AUM USD mill.'].strip(), 'returns': returns, 'extraReturns': [],
        'ytm': ytm, 'duration': duration, 'rfPortion': False,
        'keyMetrics': ([{'label': 'YTM bruta', 'value': mv['YTM bruta']}] if ytm else [])
                      + ([{'label': 'Duración',
                           'value': f"{duration['v']:.{duration['d']}f}".replace('.', ',') + ' años'}]
                         if duration else [])
                      + ([{'label': 'Clasificación', 'value': clasif}] if clasif else []),
        'ter': ter, 'trailer': trailer, 'platforms': platforms,
        'perfHeader': 'Performance', 'sections': sections, 'notes': notes,
        'compDate': comp_date, 'slide': k + 1, 'mapSlide': 0,
    })

# ---- nombres: reutilizar la grafía del mes anterior cuando el fondo es el mismo
prev_path = os.path.join(ROOT, 'data', 'funds.json')
if os.path.exists(prev_path):
    prev = {f['isin']: f for f in json.load(open(prev_path))['funds']}
    for f in funds:
        p = prev.get(f['isin'])
        if not p:
            continue
        a, b = letters(f['name']), letters(p['name'])
        if a == b or b in (a, a + 'fund') or a in (b, b + 'fund'):
            f['name'] = p['name']
        if not f['currency'] and p.get('currency'):
            f['currency'] = p['currency']   # la clase del mes anterior informaba la moneda

# ---- orden: por clase de activo y categoría (orden del documento), Balanz primero
cat_asset = {f['category']: f['asset'] for f in funds}
cat_order = sorted(mapcats, key=lambda c: (ASSET_RANK[cat_asset[c]], mapcats.index(c)))
funds.sort(key=lambda f: (cat_order.index(f['category']), 0 if f['balanz'] else 1))

# ---- metadatos y contenido institucional
inst = json.load(open(os.path.join(ROOT, 'data', 'institucional.json')))['institutional']
inst['metodologia'] = metodologia
inst['alcance'] = scope_line

PERF_SHORT_RE = re.compile(r'(Performance al \d{1,2}/\d{1,2}/\d{4})')
perf_short = next((PERF_SHORT_RE.match(p.text.strip()).group(1)
                   for p in seq[:heads[0]] if isinstance(p, Paragraph)
                   and PERF_SHORT_RE.match(p.text.strip())), perf_line)
short_comp = 'Composición: Balanz {} · terceros {}'.format(
    next((f['compDate'] for f in funds if f['balanz']), ''),
    next((f['compDate'] for f in funds if not f['balanz']), ''))
meta = {
    'title': 'Curaduría de Fondos Offshore',
    'cutoff': perf_line, 'performance': perf_line, 'performanceShort': perf_short,
    'composition': short_comp,
    'compositionLong': comp_line, 'legend': 'USO INTERNO · INDIVIDUOS',
    'feeNote': 'TER y trailer fee expresados como porcentajes anuales. '
               'Plataformas habilitadas según el documento.',
    'feeSource': 'Fuente: documento de la Curaduría de Fondos Offshore',
    'sheetSource': src_line,
    'disclaimer': 'Material de uso interno para asesores. No constituye una recomendación '
                  'personalizada de inversión. Los fondos no garantizan rendimientos y están '
                  'sujetos a riesgos de mercado, crédito, liquidez y moneda.',
    'aumUnit': 'AUM (USD mill.)',
}
cats = [{'name': c, 'asset': next(f['asset'] for f in funds if f['category'] == c)} for c in cat_order]
out = {'meta': meta, 'institutional': inst, 'categories': cats, 'funds': funds}
json.dump(out, open(prev_path, 'w'), ensure_ascii=False, indent=1)

print(f'funds.json: {len(funds)} fondos ({sum(f["balanz"] for f in funds)} propios) '
      f'en {len(cats)} categorías')
for w in warnings:
    print('  AVISO:', w)
