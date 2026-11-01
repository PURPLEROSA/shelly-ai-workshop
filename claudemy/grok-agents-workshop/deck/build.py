import base64
s=open('deck-src.html',encoding='utf-8').read()
for k,f in [('LOGO_IVORY','disco-logo-ivory.png'),('LOGO_BLUE','disco-logo.png')]:
    s=s.replace(k,'data:image/png;base64,'+base64.b64encode(open(f,'rb').read()).decode())
open('index.html','w',encoding='utf-8').write(s)
