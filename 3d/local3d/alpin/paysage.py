"""Une recette alpine, plusieurs implantations ; aucune seconde simulation."""
import json
import math
import random
from pathlib import Path
import numpy as np

RECIPE=json.loads((Path(__file__).parent/'recette.json').read_text(encoding='utf-8'))

def river_x(y,seed):
    phase=(seed%113)/113*math.tau
    return -29+9*np.sin(np.asarray(y)*.031+phase)+4*np.sin(np.asarray(y)*.069+phase*.4)

def raw_height(x,y,seed):
    x,y=np.asarray(x),np.asarray(y);phase=(seed%113)/113*math.tau
    hills=(65*np.exp(-((x-85-math.sin(phase)*12)/43)**2-((y-92)/39)**2)
           +78*np.exp(-((x+99)/33)**2-((y-69-math.cos(phase)*16)/46)**2)
           +24*np.exp(-((x-120)/33)**2-((y+28)/50)**2))
    h=2.6+.65*np.sin(x*.05+y*.032)+.45*np.cos(y*.09)+hills*(.86+.1*np.sin(x*.12-y*.074))
    d=abs(x-river_x(y,seed))-5.8
    valley=np.exp(-(np.maximum(d,0)/18)**2)*.94
    h=h*(1-valley)+1.8*valley
    t=np.clip((d+2.7)/5.3,0,1);t=t*t*(3-2*t)
    return -1.3*(1-t)+h*t

def make_plan(seed):
    rng=random.Random(seed)
    center=np.array([15+rng.uniform(-7,10),-12+rng.uniform(-7,9)])
    spine=[[center[0]+8*math.sin(y*.055+seed),y] for y in np.linspace(-94,64,12)]
    roads=[{'width':3.6,'points':spine,'kind':'voie'}]
    bridge_y=-32+rng.uniform(-13,8);bridge_x=float(river_x(bridge_y,seed))
    mill_y=bridge_y+18;mill_x=float(river_x(mill_y,seed))+10.4
    roads.append({'width':3.3,'kind':'voie','points':[[-115,bridge_y-10],[bridge_x-11,bridge_y],[bridge_x+11,bridge_y],center.tolist(),[92,-47]]})
    buildings=[]
    for attempt in range(5000):
        if len(buildings)>=RECIPE['buildings']-1:break
        # Deux rives et un chemin principal : les maisons font face à leur accès.
        if attempt%4==0:
            y=rng.uniform(bridge_y-25,bridge_y+26);roadx=float(river_x(y,seed))-23
            x=roadx+rng.choice([-1,1])*rng.uniform(8,12)
            target=np.array([roadx,y])
        else:
            y=rng.uniform(-88,60);roadx=center[0]+8*math.sin(y*.055+seed)
            x=roadx+rng.choice([-1,1])*rng.uniform(11,29);target=np.array([roadx,y])
        if abs(x-river_x(y,seed))<17 or raw_height(x,y,seed)>12 or np.linalg.norm(np.array([x,y])-center)<14:continue
        if math.hypot(x-mill_x,y-mill_y)<17:continue
        if any(math.hypot(x-b['x'],y-b['y'])<13 for b in buildings):continue
        index=rng.randrange(6);role='auberge' if len(buildings)%9==0 else 'atelier' if len(buildings)%5==0 else 'maison'
        angle=math.degrees(math.atan2(target[0]-x,-(target[1]-y)))
        scale=[rng.uniform(.91,1.13),rng.uniform(.9,1.10),1]
        b={'id':f'maison_{len(buildings):03d}','asset':f'alpin_{role}_{index}','x':x,'y':y,'height':float(raw_height(x,y,seed)),
           'rotation':angle,'scale':scale,'width':7.2*scale[0],'depth':6.2*scale[1],'radius':6.5,'role':role,'index':index}
        buildings.append(b)
        roads.append({'width':1.5,'kind':'acces','points':[[x,y],target.tolist()]})
    if len(buildings)!=RECIPE['buildings']-1:raise ValueError('Disposition incomplète : '+str(len(buildings)))
    mill_y=bridge_y+18;mill_x=float(river_x(mill_y,seed))+10.4
    buildings.append({'id':'moulin','asset':'alpin_atelier_2','x':mill_x,'y':mill_y,'height':1.8,'rotation':90,
                      'scale':[1.1,1.1,1],'width':7.92,'depth':6.82,'radius':6.7,'role':'moulin','index':2})
    roads.append({'width':2.3,'kind':'acces','points':[[mill_x,mill_y],[mill_x+13,mill_y],center.tolist()]})
    roads.append({'width':2.8,'kind':'voie','points':[[float(river_x(y,seed))-23,y] for y in np.linspace(bridge_y-38,bridge_y+36,8)]})
    return {'schema':3,'seed':seed,'biome':RECIPE['biome'],'typologie':RECIPE['typologie'],'annee':RECIPE['annee'],'culture':RECIPE['culture'],
            'center':center.tolist(),'bridge':[bridge_x,bridge_y],'buildings':buildings,'roads':roads}

def field(plan):
    n=RECIPE['terrain_cells'];ext=RECIPE['extent_m'];axis=np.linspace(-ext/2,ext/2,n+1)
    x,y=np.meshgrid(axis,axis);h=raw_height(x,y,plan['seed'])
    for b in plan['buildings']:
        a=math.radians(b['rotation']);dx=x-b['x'];dy=y-b['y']
        lx=np.cos(a)*dx+np.sin(a)*dy;ly=-np.sin(a)*dx+np.cos(a)*dy
        d=np.maximum(abs(lx)-b['width']/2-1.3,abs(ly)-b['depth']/2-1.5)
        w=1-np.clip(d/3,0,1);w=w*w*(3-2*w)
        h=h*(1-w)+b['height']*w
    cx,cy=plan['center'];d=np.hypot(x-cx,y-cy);w=1-np.clip((d-9)/4,0,1)
    return np.round(h*(1-w)+float(raw_height(cx,cy,plan['seed']))*w,5)

def sample(h,x,y):
    n=h.shape[0]-1;ext=RECIPE['extent_m']
    u=np.clip((np.asarray(x)/ext+.5)*n,0,n-1e-7);v=np.clip((np.asarray(y)/ext+.5)*n,0,n-1e-7)
    i=u.astype(int);j=v.astype(int);a=u-i;b=v-j
    return (1-a)*(1-b)*h[j,i]+a*(1-b)*h[j,i+1]+(1-a)*b*h[j+1,i]+a*b*h[j+1,i+1]
