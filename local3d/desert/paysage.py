"""Relief du désert : table de grès, reg, oued sec, dunes et oasis.

Le tracé des rues reprend celui de la citadelle, dont il a déjà prouvé la
continuité ; seules les altitudes changent (fonction `Z`). Les profils des
chemins sculptent le terrain qui les porte, et Blender comme Unity reçoivent
les mêmes points.
"""
from functools import lru_cache
import math
import numpy as np
from local3d.citadelle.paysage import smoothstep, sample_curve, nearest
from local3d.desert import urbanisme

PLATEAU = 30.0


def Z(z):
    """Altitude de la citadelle ramenée au désert : plateau à 30 m, bourg bas vers 4 m."""
    return 4 + (z - 10) * (PLATEAU - 4) / 32


# Oued sec : lit de galets, quelques mètres sous la plaine, bordé de palmiers.
OUED = [(360,80),(230,40),(140,-10),(115,-90),(60,-160),(-30,-195),(-140,-215),(-260,-200),(-390,-230)]


@lru_cache(maxsize=4)
def plan(seed):
    routes = []
    def road(name, width, points, ground=True):
        routes.append({'id':name,'width':width,'ground':ground,'points':sample_curve(points)})
    # La lisière de la palmeraie reste au niveau du sol naturel, au-dessus de la guelta :
    # ses deux derniers points ne suivent pas la conversion d'altitude.
    edge = {(-160,-56):5.2,(-169,-32):5.4}
    def z(points):
        return [(x,y,edge.get((x,y),Z(h))) for x,y,h in points]
    road('ksar_pont',5,[(0,-18,PLATEAU),(0,-40,PLATEAU),(0,-63,PLATEAU),(0,-84.4,PLATEAU)],False)
    road('descente_oasis',6,z([(0,-84.4,42),(-6,-102,39),(-24,-118,34),(-48,-122,28),
                               (-65,-112,24),(-77,-92,20),(-96,-77,17),(-98,-60,15),(-97,-51.5,14),(-96,-43,13),(-94,-26,11.5),(-97,-7,10)]))
    road('rue_basse',3,z([(-123,-77,16.1),(-124,-60,16.1),(-125,-51.5,14.6),(-132,-43,13.8),(-134,-28,11.7),(-128,-7,10)]))
    road('traverse_bourg',4,z([(-97,-51.5,14),(-125,-51.5,14.6)]))
    road('place_souk',3,z([(-96,-41,12.8),(-101,-41,14.25),(-120,-41,14.25)]))
    road('entree_souk',2,z([(-112.5,-51.5,14.332),(-112.5,-41,14.25)]))
    road('lisiere_palmeraie',4.5,z([(-65,-112,24),(-96,-119,20),(-124,-105,16),(-154,-82,12),(-160,-56,9),(-169,-32,7)]))
    houses = urbanisme.hameau(seed,[Z(17.3),Z(16.1),Z(11.7),Z(13.8)])
    for group in dict.fromkeys(h['group'] for h in houses):
        members = [h for h in houses if h['group']==group]; lane = [h['lane'] for h in members]
        road('ruelle_'+group,2.6,lane)
        midpoint = lane[len(lane)//2]
        public = next(r for r in routes if r['id']==('rue_basse' if group=='hameau_3' else 'descente_oasis'))
        start = min(public['points'],key=lambda p:math.dist(p[:2],midpoint[:2]))
        road('liaison_'+group,3,[start,midpoint])
    for i,h in enumerate(houses):road('seuil_'+str(i),2.1,[h['lane'],h['door']])
    plots = []
    for i,(x,y,h,ax,ay,ah) in enumerate([(-100,-143,23,-96,-119,20),(-126,-129,20,-124,-105,16),
                                        (-153,-109,15,-154,-82,12),(-173,-78,11,-160,-56,9)]):
        plots.append({'id':'jardin_'+str(i+1),'position':[x,y,Z(h)],'size':[13,12]})
        road('acces_jardin_'+str(i+1),3,z([(ax,ay,ah),(x,y+8,h),(x,y,h)]))
    pool = {'position':[-201,-58,Z(7)-2.2],'size':[30,20],'water':True}
    return {'routes':routes,'houses':houses,'plots':plots,'pool':pool,
            'clearings':[{'position':[-169,-32,edge[(-169,-32)]],'size':[12,12]},{'position':[-110,-41,Z(14.25)],'size':[22,16],'market':True}],
            'forest':[-169,-32,edge[(-169,-32)]],'spawn':[0,-24,PLATEAU+.35]}


@lru_cache(maxsize=1)
def oued_points():
    return [tuple(p) for p in sample_curve([(a,b,0) for a,b in OUED],6)]


def oued_distance(x, y):
    distance,_ = nearest(x,y,oued_points())
    return distance


def dunes(x, y, seed):
    """Cordons de dunes au-delà de la plaine : crêtes vives, versants sous le vent plus raides."""
    phase = (seed % 41) / 7
    r = np.hypot(x, y)
    angle = .55 + .08 * math.sin(phase)
    u = x * math.cos(angle) + y * math.sin(angle); v = -x * math.sin(angle) + y * math.cos(angle)
    warp = 22 * np.sin(v * .009 + phase) + 9 * np.sin(v * .023 + u * .006) + 40 * (value_noise(u * .008, v * .008, seed + 3) - .5)
    wave = (u + warp) * .026
    t = wave - np.floor(wave)
    # Crête arrondie sur 1,5 m environ (minimum doux des deux versants) : un pli vif se
    # crénelle en dents de scie une fois échantillonné sur la grille du terrain.
    up = t / .72; down = (1 - t) / .28; k = .2
    mix = np.clip(.5 + .5 * (down - up) / k, 0, 1)
    crest = np.clip(down * (1 - mix) + up * mix - k * mix * (1 - mix), 0, None) ** 1.6
    along = .25 + .75 * value_noise(u * .007 + np.floor(wave) * 1.7, v * .013, seed + 5)
    amplitude = 18 * smoothstep((r - 175) / 140) * along
    return amplitude * crest


def value_noise(x, y, seed):
    """Bruit de valeur continu, sans dépendance à Blender."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    ix = np.floor(x); iy = np.floor(y); fx = x - ix; fy = y - iy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    def h(a, b):
        q = np.sin(a * 127.1 + b * 311.7 + seed * 91.17) * 43758.5453
        return q - np.floor(q)
    return (h(ix, iy) * (1 - fx) + h(ix + 1, iy) * fx) * (1 - fy) + (h(ix, iy + 1) * (1 - fx) + h(ix + 1, iy + 1) * fx) * fy


def raw_height(x, y, seed):
    phase = (seed % 37) / 19
    base = 1.2 * np.sin(x * .021 + phase) * np.cos(y * .018) + .6 * np.sin(x * .07 + y * .05)
    base = base + 3 * (value_noise(x * .012, y * .012, seed) - .5)
    # L'éperon de grès qui porte la descente, et un second relief à l'est.
    spur = 22 * np.exp(-((x + 100) / 110) ** 2 - ((y + 85) / 105) ** 2) + 12 * np.exp(-((x - 145) / 70) ** 2 - ((y - 25) / 100) ** 2)
    bed = 3.2 * (1 - smoothstep(oued_distance(x, y) / 12))
    height = base + spur + dunes(x, y, seed) - bed
    px, py, pz = plan(seed)['pool']['position']; w, d = plan(seed)['pool']['size']
    bowl = np.hypot((x - px) / (w * .5 + 9), (y - py) / (d * .5 + 9))
    height = height * smoothstep(bowl - .6) + (pz - .9) * (1 - smoothstep(bowl - .6))
    # Bosselures irrégulières : un produit de sinus dessinait une boîte à œufs régulière,
    # visible en lumière rasante sur le terrain Unity au pas de 0,5 m.
    return height + .36 * (value_noise(x * .11, y * .11, seed + 29) - .5)


def pads(seed):
    return plan(seed)['clearings'] + plan(seed)['houses'] + plan(seed)['plots']


BLEND = 1.0  # mètres : deux rues qui se chevauchent mêlent leurs profils sur cette distance


def blend_profiles(effective, heights):
    """Profil continu là où plusieurs rues se recouvrent : moyenne pondérée par la proximité.

    Un simple « rue la plus proche » fait sauter le sol d'un profil à l'autre à la
    bascule ; le contrôle Blender l'a mesuré sur la place du souk (60 cm).
    """
    near = np.min(effective, axis=0)
    weights = np.exp(-(effective - near) / BLEND)
    return near, np.sum(weights * heights, axis=0) / np.sum(weights, axis=0)


@lru_cache(maxsize=8)
def route_segments(seed):
    """Segments au sol, groupés par rue : départs, arrivées, largeurs et bornes des groupes."""
    first = []; last = []; width = []; bounds = []
    for route in plan(seed)['routes']:
        if not route['ground']:continue
        pts = route['points'][::3] + [route['points'][-1]]
        start = len(first)
        for a, b in zip(pts, pts[1:]):
            first.append(a); last.append(b); width.append(route['width'])
        bounds.append((start, len(first)))
    return np.array(first), np.array(last), np.array(width), bounds


def pad_blend(x, y, seed, height, near):
    for pad in pads(seed):
        px,py,pz = pad.get('pad_position',pad['position']); w,d = pad['size']
        dist = np.maximum(abs(x-px)-w*.5,abs(y-py)-d*.5)
        blend = 1-smoothstep(dist/5)
        if pad.get('market'):blend = blend*smoothstep(near/2)
        height = height*(1-blend)+pz*blend
    return height


def field(x, y, seed):
    if np.ndim(x)==0 and np.ndim(y)==0:
        a,b,width,bounds = route_segments(seed)
        delta = b-a; t = np.clip(((float(x)-a[:,0])*delta[:,0]+(float(y)-a[:,1])*delta[:,1])/np.maximum(1e-8,np.sum(delta[:,:2]**2,axis=1)),0,1)
        distance = np.hypot(float(x)-a[:,0]-t*delta[:,0],float(y)-a[:,1]-t*delta[:,1])
        effective = []; heights = []
        for start, stop in bounds:
            k = start + int(np.argmin(distance[start:stop]))
            effective.append(distance[k]-width[k]/2); heights.append(a[k,2]+t[k]*delta[k,2])
        near, profile = blend_profiles(np.array(effective), np.array(heights))
        influence = 1-smoothstep(near/17)
        height = float(raw_height(x,y,seed))*(1-influence)+profile*influence
        return float(pad_blend(float(x),float(y),seed,height,near))
    x,y = np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
    effective = []; heights = []
    for route in plan(seed)['routes']:
        if not route['ground']:continue
        d,h = nearest(x,y,route['points'][::3]+[route['points'][-1]])
        effective.append(d-route['width']/2); heights.append(h)
    near, profile = blend_profiles(np.array(effective), np.array(heights))
    influence = 1-smoothstep(near/17)
    height = raw_height(x,y,seed)*(1-influence)+profile*influence
    return pad_blend(x,y,seed,height,near)


@lru_cache(maxsize=8)
def segments(seed, ground_only=False):
    first=[];last=[];width=[]
    for route in plan(seed)['routes']:
        if ground_only and not route['ground']:continue
        pts = route['points'][::3]+[route['points'][-1]]
        for a,b in zip(pts,pts[1:]):first.append(a);last.append(b);width.append(route['width'])
    return np.array(first),np.array(last),np.array(width)


def distance_to_routes(x, y, seed):
    a,b,width = segments(seed); d = b-a
    t = np.clip(((x-a[:,0])*d[:,0]+(y-a[:,1])*d[:,1])/np.maximum(1e-8,np.sum(d[:,:2]**2,axis=1)),0,1)
    return float(np.min(np.hypot(x-a[:,0]-t*d[:,0],y-a[:,1]-t*d[:,1])-width/2))


def in_pool(x, y, seed, margin=0):
    px,py,_ = plan(seed)['pool']['position']; w,d = plan(seed)['pool']['size']
    return ((x-px)/(w*.5+margin))**2+((y-py)/(d*.5+margin))**2<1


def blocked_by_use(x, y, seed):
    if distance_to_routes(x,y,seed)<3:return True
    if in_pool(x,y,seed,2.5):return True
    return any(abs(x-p.get('pad_position',p['position'])[0])<p['size'][0]/2+3 and abs(y-p.get('pad_position',p['position'])[1])<p['size'][1]/2+3
               for p in pads(seed))
