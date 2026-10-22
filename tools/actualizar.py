"""Regenera index.html y data/funds.json desde el documento de la curaduría.

Uso:  python tools/actualizar.py fuente/<archivo>
      Acepta el Word (.docx) y el texto plano de la PPT (.txt) del formato anterior.

Luego subir a GitHub: index.html, data/funds.json y el archivo de fuente.
"""
import os, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
    sys.exit(__doc__)
src = os.path.abspath(sys.argv[1])
if not os.path.exists(src):
    sys.exit(f'No existe el archivo: {src}')
ext = os.path.splitext(src)[1].lower()
if ext == '.docx':
    steps = ['extract_docx.py', 'build_html.py', 'validate_docx.py']
elif ext in ('.txt', '.md'):
    steps = ['extract.py', 'build_data.py', 'build_html.py', 'validate.py']
else:
    sys.exit(f'Formato no soportado: {ext}. Usar .docx o .txt')

env = dict(os.environ, CFO_SRC=src)
data = os.path.join(ROOT, 'data', 'funds.json')
prev = {f['isin']: f['name'] for f in json.load(open(data))['funds']} if os.path.exists(data) else {}

for step in steps:
    if subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', step)], env=env).returncode:
        sys.exit(f'\nFalló {step}. No se publica nada hasta revisarlo.')

new = {f['isin']: f['name'] for f in json.load(open(data))['funds']}
print('\nAltas:', [f'{i} {new[i]}' for i in new if i not in prev] or 'ninguna')
print('Bajas:', [f'{i} {prev[i]}' for i in prev if i not in new] or 'ninguna')
