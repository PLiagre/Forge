"""Relief artistique, rues raccordées et clairières de construction.

Les profils des chemins sculptent le terrain qui les porte. Blender et Unity
reçoivent les mêmes points : aucune route n'est seulement un trait sur l'image.
"""
from functools import lru_cache
import math
import numpy as np
from local3d.citadelle import urbanisme


def smoothstep(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)


def sample_curve(points, spacing=1.2):
    points=np.array(points,dtype=float);out=[]
    for i in range(len(points)-1):
        p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
        count=max(2,math.ceil(np.linalg.norm(p2[:2]-p1[:2])/spacing))
        for t in np.linspace(0,1,count,endpoint=False):
            p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
            out.append(p.tolist())
    out.append(points[-1].tolist())
    return out


@lru_cache(maxsize=4)
def plan(seed):
    routes=[]
    def road(name,width,points,ground=True):
        routes.append({'id':name,'width':width,'ground':ground,'points':sample_curve(points)})
    road('citadelle_pont',5,[(0,-18,42),(0,-40,42),(0,-63,42),(0,-84.4,42)],False)
    road('descente_village',6,[(0,-84.4,42),(-6,-102,39),(-24,-118,34),(-48,-122,28),
                             (-65,-112,24),(-77,-92,20),(-96,-77,17),(-98,-60,15),(-97,-51.5,14),(-96,-43,13),(-94,-26,11.5),(-97,-7,10)])
    road('rue_basse',3,[(-123,-77,16.1),(-124,-60,16.1),(-125,-51.5,14.6),(-132,-43,13.8),(-134,-28,11.7),(-128,-7,10)])
    road('traverse_village',4,[(-97,-51.5,14),(-125,-51.5,14.6)])
    road('place_marche',3,[(-96,-41,12.8),(-101,-41,14.25),(-120,-41,14.25)])
    road('entree_marche',2,[(-112.5,-51.5,14.332),(-112.5,-41,14.25)])
    road('lisiere_bois',4.5,[(-65,-112,24),(-96,-119,20),(-124,-105,16),(-154,-82,12),(-160,-56,9),(-169,-32,7)])
    houses=urbanisme.hameau(seed)
    for group in dict.fromkeys(h['group'] for h in houses):
        members=[h for h in houses if h['group']==group];lane=[h['lane'] for h in members]
        road('ruelle_'+group,2.6,lane)
        midpoint=lane[len(lane)//2]
        public=next(r for r in routes if r['id']==('rue_basse' if group=='hameau_3' else 'descente_village'))
        start=min(public['points'],key=lambda p:math.dist(p[:2],midpoint[:2]))
        road('liaison_'+group,3,[start,midpoint])
    for i,h in enumerate(houses):road('seuil_'+str(i),2.1,[h['lane'],h['door']])
    plots=[]
    for i,(x,y,z,ax,ay,az) in enumerate([(-100,-143,23,-96,-119,20),(-126,-129,20,-124,-105,16),
                                       (-153,-109,15,-154,-82,12),(-173,-78,11,-160,-56,9)]):
        plots.append({'id':'terrain_'+str(i+1),'position':[x,y,z],'size':[13,12]})
        road('acces_terrain_'+str(i+1),3,[(ax,ay,az),(x,y+8,z),(x,y,z)])
    return {'routes':routes,'houses':houses,'plots':plots,'clearings':[{'position':[-169,-32,7],'size':[12,12]}, {'position':[-110,-41,14.25],'size':[22,16],'market':True}],
            'forest':[-169,-32,7], 'spawn':[0,-24,42.35]}


def raw_height(x,y,seed):
    phase=(seed%37)/19
    base=-10+2.4*np.sin(x*.032+phase)*np.cos(y*.028)+1.2*np.sin(x*.13+y*.061)
    hills=26*np.exp(-((x+100)/110)**2-((y+85)/105)**2)+20*np.exp(-((x-145)/70)**2-((y-25)/100)**2)
    return base+hills+.24*np.sin(x*.6+y*.3)*np.sin(y*.44)


def nearest(x,y,points):
    """Distance et altitude du segment le plus proche, sur scalaires ou grilles."""
    x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
    distance=np.full(x.shape,np.inf);height=np.zeros(x.shape)
    for a,b in zip(points,points[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=dx*dx+dy*dy
        if length<1e-8:continue
        t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/length,0,1)
        d=np.hypot(x-a[0]-t*dx,y-a[1]-t*dy);closer=d<distance
        height=np.where(closer,a[2]+t*(b[2]-a[2]),height);distance=np.minimum(distance,d)
    return distance,height


def field(x,y,seed):
    if np.ndim(x)==0 and np.ndim(y)==0:
        a,b,width=segments(seed,True)
        delta=b-a;t=np.clip(((float(x)-a[:,0])*delta[:,0]+(float(y)-a[:,1])*delta[:,1])/np.maximum(1e-8,np.sum(delta[:,:2]**2,axis=1)),0,1)
        distances=np.hypot(float(x)-a[:,0]-t*delta[:,0],float(y)-a[:,1]-t*delta[:,1])-width/2
        k=np.argmin(distances);influence=1-smoothstep(distances[k]/17)
        height=float(raw_height(x,y,seed))*(1-influence)+(a[k,2]+t[k]*delta[k,2])*influence
        for pad in plan(seed)['clearings']+plan(seed)['houses']+plan(seed)['plots']:
            px,py,pz=pad.get('pad_position',pad['position']);w,d=pad['size'];blend=1-smoothstep(max(abs(x-px)-w*.5,abs(y-py)-d*.5)/5)
            if pad.get('market'):blend*=smoothstep(distances[k]/2)
            height=height*(1-blend)+pz*blend
        return float(height)
    x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
    height=raw_height(x,y,seed);near=np.full(x.shape,np.inf);profile=np.zeros(x.shape);width=np.zeros(x.shape)
    for route in plan(seed)['routes']:
        if not route['ground']:continue
        d,h=nearest(x,y,route['points'][::3]+[route['points'][-1]])
        effective=d-route['width']/2;closer=effective<near
        profile=np.where(closer,h,profile);width=np.where(closer,route['width'],width);near=np.minimum(near,effective)
    influence=1-smoothstep(near/17)
    height=height*(1-influence)+profile*influence
    for pad in plan(seed)['clearings']+plan(seed)['houses']+plan(seed)['plots']:
        px,py,pz=pad.get('pad_position',pad['position']);w,d=pad['size']
        dist=np.maximum(abs(x-px)-w*.5,abs(y-py)-d*.5)
        blend=1-smoothstep(dist/5)
        if pad.get('market'):blend*=smoothstep(near/2)
        height=height*(1-blend)+pz*blend
    return height


@lru_cache(maxsize=8)
def segments(seed,ground_only=False):
    first=[];last=[];width=[]
    for route in plan(seed)['routes']:
        if ground_only and not route['ground']:continue
        pts=route['points'][::3]+[route['points'][-1]]
        for a,b in zip(pts,pts[1:]):first.append(a);last.append(b);width.append(route['width'])
    return np.array(first),np.array(last),np.array(width)


def distance_to_routes(x,y,seed):
    a,b,width=segments(seed);d=b-a
    t=np.clip(((x-a[:,0])*d[:,0]+(y-a[:,1])*d[:,1])/np.maximum(1e-8,np.sum(d[:,:2]**2,axis=1)),0,1)
    return float(np.min(np.hypot(x-a[:,0]-t*d[:,0],y-a[:,1]-t*d[:,1])-width/2))


def blocked_by_use(x,y,seed):
    if distance_to_routes(x,y,seed)<3:return True
    return any(abs(x-p.get('pad_position',p['position'])[0])<p['size'][0]/2+3 and abs(y-p.get('pad_position',p['position'])[1])<p['size'][1]/2+3
               for p in plan(seed)['clearings']+plan(seed)['houses']+plan(seed)['plots'])
