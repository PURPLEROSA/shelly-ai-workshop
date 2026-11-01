import base64,re,sys
L='assets/lucide/'
s=open('deck2-src.html',encoding='utf-8').read()
b64=lambda p:base64.b64encode(open(p,'rb').read()).decode()
s=re.sub(r'\{\{FONT:([^}]+)\}\}',lambda m:'data:font/ttf;base64,'+b64('assets/'+m.group(1)),s)
s=re.sub(r'\{\{IMG:([^}]+)\}\}',lambda m:'data:image/jpeg;base64,'+b64('assets/'+m.group(1)+'.jpg'),s)
s=re.sub(r'\{\{AI:([^}]+)\}\}',lambda m:'data:image/png;base64,'+b64('assets/'+m.group(1)+'.png'),s)
missing=set()
def lucide(m):
    n=m.group(1)
    try: svg=open(L+n+'.svg',encoding='utf-8').read()
    except FileNotFoundError: missing.add(n); return ''
    svg=re.sub(r'<!--.*?-->','',svg,flags=re.S).strip()
    head,rest=svg.split('>',1)
    head=re.sub(r'\s(width|height|class|stroke-width)="[^"]*"','',head)
    return head.replace('<svg','<svg class="i"',1)+'>'+rest
def mini(m):
    svg=open('assets/mini-'+m.group(1)+'.svg',encoding='utf-8').read()
    head,rest=svg.split('>',1)
    head=re.sub(r'\s(width|height)="[^"]*"','',head)
    return head.replace('<svg','<svg class="i"',1)+'>'+rest
s=re.sub(r'\{\{i:([a-z0-9-]+)\}\}',lucide,s)
s=re.sub(r'\{\{m:([A-Za-z-]+)\}\}',mini,s)
assert '{{' not in s, re.findall(r'\{\{[^}]+\}\}',s)[:5]
open('index.html','w',encoding='utf-8').write(s)
print('missing:',sorted(missing),'size KB',len(s)//1024)
