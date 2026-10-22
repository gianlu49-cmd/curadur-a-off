import os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.environ.get('CFO_SRC','')
OUT=os.path.join(ROOT,'tools','out'); os.makedirs(OUT,exist_ok=True)
import json
d=json.load(open(os.path.join(ROOT,'data','funds.json')))
js=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
html=open(os.path.join(ROOT,'tools','template.html')).read().replace('/*__DATA__*/',js)
open(os.path.join(ROOT,'index.html'),'w').write(html)
print(len(html)//1024,'KB')
