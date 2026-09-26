"""Implantation graphique déterministe. Ne lit ni n'écrit la simulation."""
import hashlib
import json
import math
import random
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((Path(__file__).parent/'recettes.json').read_text(encoding='utf-8'))
def variant(name):
    return next(v for v in CONFIG['variants'] if v['id']==name)

def river_x(y):
    return -45+11*np.sin(np.asarray(y)*.033)+5*np.sin(np.asarray(y)*.071+1)

def water_distance(x,y,v):
    if v['water']=='oasis':
        return (np.sqrt(((np.asarray(x)+39)/18)**2+((np.asarray(y)+22)/29)**2)-1)*18
    return np.abs(np.asarray(x)-river_x(y))-v['water_width']

def raw_height(x,y,v):
    x,y=np.asarray(x),np.asarray(y)
    waves=.65*np.sin(x*.037+y*.023)+.42*np.cos(y*.06-x*.032)
    peaks=(.82*np.exp(-((x-62)/47)**2-((y-86)/34)**2)
        +np.exp(-((x+85)/39)**2-((y-62)/34)**2)
        +.33*np.exp(-((x-103)/32)**2-((y+24)/38)**2))
    ridges=.72+.18*np.sin(x*.10-y*.06)+.1*np.cos(y*.17+x*.08)
    h=2.2+waves+v['mountain_height']*peaks*ridges
    if v['biome']=='aride':
        h+=1.25*(np.sin(x*.052+y*.06)+1)*(.3+peaks)
    dist=water_distance(x,y,v)
    # La vallée accompagne le cours d'eau avant l'incision du lit.
    valley=np.exp(-(np.maximum(dist,0)/22)**2)*.90
    h=h*(1-valley)+2.0*valley
    blend=np.clip((dist+3)/6,0,1)
    blend=blend*blend*(3-2*blend)
    bed=-1.4+.08*np.cos(y*.11)
    return bed*(1-blend)+h*blend

def road_ring(radius,count=100):
    pts=[]
    for i in range(count+1):
        a=i/count*math.tau
        r=radius+1.6*math.sin(a*3)+.8*math.cos(a*5)
        x=20+r*math.cos(a)
        y=-12+r*.88*math.sin(a)
        pts.append([x,y])
    return pts

def make_plan(v):
    rng=random.Random(v['seed'])
    buildings=[]
    # Les chemins des quatre couronnes sont des données exportées avec le plan.
    roads=[]
    for radius,slots in [(23,11),(44,19),(65,27),(85,32)]:
        for i in range(slots):
            a=i/slots*math.tau+rng.uniform(-.045,.045)
            r=radius+rng.uniform(-1.3,1.3)
            x=20+r*math.cos(a)
            y=-12+r*.88*math.sin(a)
            w=rng.uniform(6.2,8.4)
            d=rng.uniform(5.3,7.1)
            if math.hypot(x,y)>109 or y>58 or water_distance(x,y,v)<max(w,d)*.8+4:
                continue
            if raw_height(x,y,v)>11:
                continue
            radius_collision=math.hypot(w,d)/2+1.35
            if any(math.hypot(x-b['x'],y-b['y'])<radius_collision+b['radius'] for b in buildings):
                continue
            role='maison' if len(buildings)%5 else ('atelier' if len(buildings)%10 else 'auberge')
            k=len(buildings)%6
            buildings.append({'id':f'batiment_{len(buildings):03d}','asset':f'{v["style"]}_{role}_{k}',
                'role':role,'x':round(x,4),'y':round(y,4),'rotation':round(math.degrees(a-math.pi/2),4),
                'width':w,'depth':d,'radius':radius_collision,'scale':[w/7.2,d/6.2,1],
                'height':float(raw_height(x,y,v)), 'ring':radius})
            if len(buildings)==v['buildings']: break
        if any(b['ring']==radius for b in buildings):
            pts=road_ring(radius-7.3)
            # La route reste sur la rive habitée. Un unique pont porte la traversée.
            for p in pts:
                p[0]=max(p[0],float(river_x(p[1]))+v['water_width']+5)
            roads.append({'kind':'ruelle','width':2.3,'points':pts})
        if len(buildings)==v['buildings']: break
    if len(buildings)!=v['buildings']:
        raise ValueError(f'Implantation incomplète : {len(buildings)} / {v["buildings"]}')
    roads.extend([
        {'kind':'voie','width':3.6,'points':[[20,-12],[35,-28],[63,-49],[93,-72],[121,-83]]},
        {'kind':'voie','width':3.3,'points':[[20,-12],[25,8],[32,31],[40,65]]},
        {'kind':'voie','width':3.4,'points':[[20,-12],[1,-17],[-17,-23],[float(river_x(-28))+v['water_width']+3,-28]]}
    ])
    if v['water']!='oasis':
        roads.append({'kind':'voie','width':3.2,'points':[[float(river_x(-28))-v['water_width']-5,-28],[-94,-38],[-120,-62]]})
    # Les chemins vers les portes sont conservés pour le contrôle des accès.
    for b in buildings:
        a=math.radians(b['rotation'])
        forward=np.array([math.sin(a),-math.cos(a)])
        door=np.array([b['x'],b['y']])+forward*(b['depth']/2)
        target=np.array([b['x'],b['y']])+forward*8
        roads.append({'kind':'acces','width':1.15,'points':[door.tolist(),target.tolist()]})
    return {'schema':2,'variant':v,'buildings':buildings,'roads':roads,
        'source':'Implantation artistique locale, fidélité 2 ; aucune donnée de simulation',
        'square':[20,-12,11]}

def field(plan):
    v=plan['variant']; n=CONFIG['terrain_cells']; ext=CONFIG['extent_m']
    axis=np.linspace(-ext/2,ext/2,n+1)
    x,y=np.meshgrid(axis,axis)
    h=raw_height(x,y,v)
    for b in plan['buildings']:
        a=math.radians(b['rotation']); dx=x-b['x'];dy=y-b['y']
        lx=np.cos(a)*dx+np.sin(a)*dy;ly=-np.sin(a)*dx+np.cos(a)*dy
        distance=np.maximum(abs(lx)-b['width']/2-1,abs(ly)-b['depth']/2-1)
        weight=1-np.clip(distance/3,0,1)
        weight=weight*weight*(3-2*weight)
        h=h*(1-weight)+b['height']*weight
    sq=np.sqrt((x-20)**2+(y+12)**2)
    weight=1-np.clip((sq-10)/5,0,1)
    h=h*(1-weight)+float(raw_height(20,-12,v))*weight
    return np.round(h,5)

def sample(h,x,y):
    n=h.shape[0]-1;ext=CONFIG['extent_m']
    u=np.clip((np.asarray(x)/ext+.5)*n,0,n-1e-7)
    v=np.clip((np.asarray(y)/ext+.5)*n,0,n-1e-7)
    i=u.astype(int);j=v.astype(int);a=u-i;b=v-j
    return (1-a)*(1-b)*h[j,i]+a*(1-b)*h[j,i+1]+(1-a)*b*h[j+1,i]+a*b*h[j+1,i+1]

def path_distance(x,y,roads):
    dist=np.full(np.broadcast(x,y).shape,1e6)
    for road in roads:
        pts=road['points']
        for a,b in zip(pts,pts[1:]):
            dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
            t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/max(den,.001),0,1)
            d=np.sqrt((x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2)-road['width']/2
            dist=np.minimum(dist,d)
    return dist

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
