"""Petites textures PBR procédurales, partageables entre Blender et Unity."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .plan import CONFIG, make_plan, field, sample, path_distance, water_distance

def srgb(a):
    a=np.clip(a,0,1)
    return np.where(a<=.0031308,a*12.92,1.055*a**(1/2.4)-.055)

def noise(rng,n):
    out=np.zeros((n,n),dtype=np.float32)
    for resolution,weight in [(8,.45),(32,.3),(128,.18),(n,.07)]:
        layer=Image.fromarray(rng.integers(0,256,(resolution,resolution),dtype=np.uint8))
        out+=np.asarray(layer.resize((n,n),Image.Resampling.BICUBIC))/255*weight
    return out

def save_material(folder,name,color,kind='plaster',seed=1,roughness=.83):
    rng=np.random.default_rng(seed);n=512
    yy,xx=np.mgrid[:n,:n];grain=noise(rng,n);height=grain*.12
    col=np.ones((n,n,3),dtype=np.float32)*np.array(color)
    col*=.85+grain[...,None]*.3
    if kind=='wood':
        streak=np.sin(xx*.17+np.sin(yy*.013)*2+grain*4)
        height+=streak*.10
        seams=(xx%64<3)
        col*=np.where(seams,.47,1)[...,None]
        col*= (.9+.1*streak)[...,None]
    elif kind in ('stone','tiles'):
        row=yy//64; shifted=(xx+(row%2)*64)%128
        seams=(yy%64<3)|(shifted<3)
        cells=np.sin(row*2.4+(xx+(row%2)*64)//128*7.3)
        col*=np.where(seams,.48,.96+cells*.13)[...,None]
        height+=np.where(seams,-.22,.08)
    elif kind=='adobe':
        cracks=(abs(np.sin(xx*.018+yy*.012+grain*1.5))<.025)&(grain<.38)
        col*=np.where(cracks,.65,1)[...,None]
    elif kind=='rock':
        strata=np.sin(yy*.052+grain*8+np.sin(xx*.013)*2)
        veins=np.abs(np.sin(xx*.014+yy*.035+grain*5))<.045
        col*=np.where(veins,.62,.87+strata*.11+grain*.28)[...,None]
        height+=strata*.08+grain*.2
    elif kind=='leaf':
        height+=np.cos(xx*.04+yy*.07)*.025
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*4,-dy*4,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    folder.mkdir(parents=True,exist_ok=True)
    Image.fromarray((srgb(col)*255).astype(np.uint8)).save(folder/(name+'_BaseColor.png'))
    Image.fromarray(((normal*.5+.5)*255).astype(np.uint8)).save(folder/(name+'_Normal.png'))
    smooth=np.clip(1-roughness+(grain-.5)*.14,0,1)
    pack=np.zeros((n,n,4),dtype=np.uint8);pack[:,:,3]=(smooth*255).astype(np.uint8)
    Image.fromarray(pack).save(folder/(name+'_MetallicGloss.png'))

def foliage(folder,name,color,seed):
    rng=np.random.default_rng(seed); n=512
    image=Image.new('RGBA',(n,n),(0,0,0,0));d=ImageDraw.Draw(image)
    # Branches fines et feuilles séparées : le vide appartient à la silhouette.
    d.line([(245,502),(248,254),(266,36)],fill=(80,65,36,255),width=5)
    for i in range(115):
        x,y=rng.uniform(30,482),rng.uniform(24,482)
        if ((x-256)/250)**2+((y-256)/260)**2>1:continue
        width,height=rng.uniform(7,17),rng.uniform(12,27)
        c=tuple((srgb(np.asarray(color)*rng.uniform(.7,1.35))*255).astype(int))+(255,)
        d.polygon([(x-width,y),(x-3,y-height),(x+width,y-4),(x+3,y+height)],fill=c)
        d.line([(x-2,y-height*.65),(x+1,y+height*.65)],fill=(c[0]//2,c[1]//2,c[2]//2,255),width=1)
    image.save(folder/(name+'_BaseColor.png'))

def prepare(folder):
    for i,(style,c) in enumerate(CONFIG['styles'].items()):
        for kind,key in [('plaster','wall'),('tiles','roof'),('wood','timber'),('stone','stone')]:
            actual='wood' if style=='chalet' and key=='wall' else 'adobe' if style=='terre' and key=='wall' else 'stone' if style=='pierre' and key=='wall' else kind
            save_material(folder,style+'_'+key,c[key],actual,31+i*17+len(key))
    save_material(folder,'colombage_roof_terre',[.46,.23,.12],'tiles',58)
    for i,(name,col,kind) in enumerate([
        ('bois',[.30,.17,.075],'wood'),('bois_clair',[.48,.31,.15],'wood'),
        ('pierre_grise',[.38,.40,.34],'stone'),('pierre_ocre',[.56,.36,.19],'stone'),
        ('fer',[.055,.06,.06],'plaster'),('toile_creme',[.75,.65,.42],'plaster'),
        ('toile_rouge',[.42,.10,.06],'plaster'),('toile_indigo',[.08,.17,.21],'plaster'),
        ('paille',[.49,.36,.12],'plaster'),('terre_culture',[.16,.10,.045],'plaster'),
        ('feuilles',[.14,.25,.045],'leaf'),('herbe',[.22,.32,.075],'leaf'),
        ('herbe_seche',[.45,.35,.16],'leaf'),('roche',[.38,.39,.34],'rock'),
        ('roche_ocre',[.56,.32,.16],'rock'),
        ('neige',[.85,.87,.85],'plaster'),('eau',[.06,.28,.26],'plaster'),
        ('fenetre',[.12,.16,.17],'plaster')]):
        save_material(folder,name,col,kind,200+i)
    for i,(name,col) in enumerate([('feuille_chene',[.17,.28,.065]),('feuille_bouleau',[.32,.40,.105]),
        ('aiguilles',[.075,.15,.075]),('feuille_olivier',[.24,.30,.16])]):
        foliage(folder,name,col,400+i)

def terrain_texture(plan,h,path):
    n=1024;ext=CONFIG['extent_m'];v=plan['variant']
    axis=np.linspace(-ext/2,ext/2,n);x,y=np.meshgrid(axis,axis)
    rng=np.random.default_rng(v['seed']);grain=noise(rng,n)
    elev=sample(h,x,y)
    dy,dx=np.gradient(elev,ext/(n-1));slope=np.hypot(dx,dy)
    col=np.ones((n,n,3))*np.asarray(v['ground'])
    col*= (.73+grain*.5)[...,None]
    stone=np.clip((slope-.32)*1.6+(elev-15)/70,0,1)
    col=col*(1-stone[...,None])+np.asarray(v['rock'])*(.78+grain*.35)[...,None]*stone[...,None]
    wd=water_distance(x,y,v)
    shore=np.clip(1-np.maximum(wd,0)/5,0,1)
    col=col*(1-shore[...,None])+np.array([.44,.37,.24])*shore[...,None]
    distance=path_distance(x,y,plan['roads'])
    square=np.hypot(x-20,y+12)-10.6
    distance=np.minimum(distance,square)
    road=np.clip(.65-distance+(.5-grain)*1.3,0,1)
    road*=np.clip(wd/2,0,1)
    roadcolor=np.array([.40,.33,.23]) if v['biome']!='aride' else np.array([.57,.36,.19])
    col=col*(1-road[...,None])+roadcolor*(.9+grain*.18)[...,None]*road[...,None]
    if v['biome']=='alpin':
        snow=np.clip((elev-38)/12,0,1)*np.clip(1-slope*.5,0,1)
        col=col*(1-snow[...,None])+np.array([.88,.9,.91])*snow[...,None]
    # Les UV terrain montent avec y ; les lignes PNG descendent.
    Image.fromarray((srgb(col[::-1])*255).astype(np.uint8)).save(path)
