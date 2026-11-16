# Procedural fictional billboard art for the blockout (no real brands).
import sys, math
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]; font_path = sys.argv[2]
def F(sz): return ImageFont.truetype(font_path, sz)
def fit(d, text, w, maxsz):
    sz = maxsz
    while sz > 10:
        f = F(sz); bb = d.textbbox((0,0), text, font=f)
        if bb[2]-bb[0] <= w: return f
        sz -= 4
    return F(10)
def center(d, text, cx, y, w, maxsz, fill):
    f = fit(d, text, w, maxsz); bb = d.textbbox((0,0), text, font=f)
    d.text((cx-(bb[2]-bb[0])/2-bb[0], y-bb[1]), text, font=f, fill=fill); return bb[3]-bb[1]

def coffee():
    im = Image.new('RGB',(1024,512),(238,108,32)); d=ImageDraw.Draw(im)
    d.ellipse((60,96,380,416),fill=(255,244,225)); d.ellipse((130,166,310,346),fill=(92,48,22))
    d.arc((300,190,440,330),-70,70,fill=(255,244,225),width=34)
    center(d,'MORNING',700,110,560,170,(255,244,225)); center(d,'RUSH',700,270,560,200,(60,26,10)); return im
def soda():
    im = Image.new('RGB',(1024,512),(232,32,120)); d=ImageDraw.Draw(im)
    for i in range(-6,14): d.polygon([(i*120,0),(i*120+60,0),(i*120+60+512,512),(i*120+512,512)],fill=(250,70,150))
    d.rounded_rectangle((90,60,300,452),40,fill=(40,210,220)); d.rectangle((90,170,300,300),fill=(255,255,255))
    center(d,'SODA',650,90,600,210,(255,255,255)); center(d,'POP!',650,280,600,210,(255,230,40)); return im
def jazz():
    im = Image.new('RGB',(768,1024),(14,20,52)); d=ImageDraw.Draw(im)
    for r,c in ((420,(30,40,90)),(320,(44,58,120)),(220,(212,160,40)),(120,(246,206,90))): d.ellipse((384-r,380-r,384+r,380+r),fill=c)
    d.polygon([(330,250),(450,250),(520,560),(380,600),(300,470)],fill=(14,20,52))
    center(d,'JAZZ',384,700,680,250,(246,206,90)); center(d,'TONIGHT',384,900,680,120,(255,255,255)); return im
def pizza():
    im = Image.new('RGB',(1024,512),(200,30,28)); d=ImageDraw.Draw(im)
    d.polygon([(70,70),(450,256),(70,442)],fill=(250,196,60)); d.polygon([(70,70),(120,94),(120,418),(70,442)],fill=(170,96,40))
    for x,y in ((190,200),(260,290),(180,330),(330,250)): d.ellipse((x-34,y-34,x+34,y+34),fill=(200,30,28))
    center(d,'FRESH',730,90,520,190,(255,240,210)); center(d,'SLICE',730,280,520,190,(250,196,60)); return im
def minute():
    im = Image.new('RGB',(768,1024),(18,18,18)); d=ImageDraw.Draw(im)
    for i in range(-8,16): d.polygon([(i*110,0),(i*110+55,0),(i*110+55-300,300),(i*110-300,300)],fill=(248,204,20))
    d.rectangle((0,300,768,1024),fill=(18,18,18)); d.ellipse((184,360,584,760),fill=(248,204,20)); d.pieslice((204,380,564,740),-90,20,fill=(18,18,18))
    center(d,'ONE MORE',384,800,700,110,(255,255,255)); center(d,'MINUTE',384,910,700,130,(248,204,20)); return im
def open24():
    im = Image.new('RGB',(1024,512),(8,10,8)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((30,30,994,482),60,outline=(60,255,120),width=18)
    center(d,'OPEN',512,80,860,210,(60,255,120)); center(d,'24 HOURS',512,290,860,160,(255,60,150)); return im
def sunny():
    im = Image.new('RGB',(1024,512),(30,110,220)); d=ImageDraw.Draw(im)
    for a in range(0,360,20):
        x=250+math.cos(math.radians(a))*330; y=256+math.sin(math.radians(a))*330
        d.line((250,256,x,y),fill=(255,214,40),width=26)
    d.ellipse((90,96,410,416),fill=(255,214,40))
    center(d,'SUNNY',720,100,540,190,(255,255,255)); center(d,'SIDE',720,290,540,190,(255,214,40)); return im
def shapes():
    im = Image.new('RGB',(1024,512),(22,62,200)); d=ImageDraw.Draw(im)
    d.polygon([(0,512),(360,0),(560,0),(200,512)],fill=(250,214,30)); d.polygon([(420,512),(780,0),(980,0),(620,512)],fill=(250,214,30))
    d.ellipse((700,280,900,480),fill=(255,255,255)); return im
def deli():
    im = Image.new('RGB',(512,1024),(196,24,30)); d=ImageDraw.Draw(im)
    d.rectangle((24,24,488,1000),outline=(255,244,225),width=14)
    y=90
    for ch in 'DELI': center(d,ch,256,y,400,230,(255,244,225)); y+=220
    return im
def taxi():
    im = Image.new('RGB',(1024,512),(246,196,20)); d=ImageDraw.Draw(im)
    for i in range(16):
        for j in range(2):
            if (i+j)%2==0: d.rectangle((i*64,400+j*56,i*64+64,456+j*56),fill=(16,16,16))
    center(d,'NEED A LIFT?',512,90,900,170,(16,16,16)); center(d,'HAIL HERE',512,270,900,110,(16,16,16)); return im
for name,fn in dict(coffee=coffee,soda=soda,jazz=jazz,pizza=pizza,minute=minute,open24=open24,sunny=sunny,shapes=shapes,deli=deli,taxi=taxi).items():
    fn().save(f'{out}/{name}.png')
print('textures ok')
