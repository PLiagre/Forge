"""Kit d'habitat : travée de 6 m, étage de 3 m, accessoires sur trame de 1,5 m.

Les compositions exportées sont aussi celles assemblées par Unity. Les anciennes
sources retouchées restent disponibles ; aucune pièce manuelle n'est écrasée.
"""
import math
from local3d.atelier_v2.geometrie import Mesh
from local3d.citadelle import assets, marche


MODULES = [
    ('socle_pierre', 'Rez-de-chaussée · pierre', (6,6,3), 'base'),
    ('etage_enduit', 'Étage · colombages crème', (6,6,3), 'etage'),
    ('etage_brique', 'Étage · colombages brique', (6,6,3), 'etage'),
    ('etage_galerie', 'Étage avec accès galerie · crème', (6,6,3), 'etage'),
    ('etage_galerie_brique', 'Étage avec accès galerie · brique', (6,6,3), 'etage'),
    ('toit_ardoise', 'Toit · ardoise bleue', (6,6,4.2), 'toit'),
    ('toit_tuile', 'Toit · tuile rouge', (6,6,4.2), 'toit'),
    ('galerie', 'Galerie sur poteaux', (3,1.5,3), 'base'),
    ('escalier', 'Escalier extérieur', (1.5,3,3), 'base'),
    ('passerelle', 'Passerelle avec garde-corps', (3,1.5,.18), 'pont'),
    ('cheminee', 'Cheminée de brique', (1.5,1.5,3), 'ornement'),
    ('lucarne', 'Lucarne à pignon', (1.5,1.5,1.8), 'ornement'),
] + marche.MODULES


def box(m, p, size, name):
    m.box(p, size, assets.mat(name))


def beam(m, a, b, width=.16):
    m.beam(a, b, width, assets.mat('bois_noir'))


def window(m,x,y,z,w=1.05,h=1.35):
    # Vitrage sombre en retrait, petit bois et volets lisibles à hauteur humaine.
    box(m,(x,y,z+h/2),(w,.06,h),'habitat_verre')
    for dx in (-w/2,w/2):box(m,(x+dx,y-.04,z+h/2),(.11,.13,h+.15),'bois_noir')
    for zz in (z,z+h):box(m,(x,y-.06,zz),(w+.17,.17,.11),'bois_noir')
    m.detail=1
    box(m,(x,y-.11,z+h/2),(.065,.07,h),'bois_vieux')
    box(m,(x,y-.11,z+h*.55),(w,.07,.075),'bois_vieux')
    m.detail=0
    for dx in (-w*.73,w*.73):box(m,(x+dx,y,z+h/2),(.30,.1,h),'bois_vieux')
    m.detail=2


def storey(stone=False,brick=False,gallery_door=False):
    m=Mesh();infill='pierre_taille' if stone else 'habitat_brique' if brick else 'habitat_enduit'
    box(m,(0,0,.10),(6,6,.20),'pierre_taille' if stone else 'bois_vieux')
    # Quatre parois fines ; les deux portes du haut s'ouvrent sur la galerie.
    for side in range(4):
        n=Mesh();front=side==0
        if stone:
            if front:
                for x in (-1.93,1.93):box(n,(x,0,1.5),(2.14,.30,3),infill)
                box(n,(0,0,2.77),(1.72,.30,.46),infill)
                assets.window(n,0,-.20,.08,1.60,2.55,'pierre_taille','bois_vieux')
                for x in (-2.08,2.08):window(n,x,-.20,1.2,.58,1.0)
            else:
                box(n,(0,0,1.5),(6,.30,3),infill)
                for x in (-1.5,1.5):window(n,x,-.20,1.15,.75,1.12)
            box(n,(0,-.03,2.93),(6.08,.42,.14),'calcaire')
        else:
            # Une ouverture réelle dessert la coursive, sans percer les étages sans balcon.
            if gallery_door and front:
                box(n,(-1.0,0,1.5),(4,.22,3),infill)
                box(n,(2.8,0,1.5),(.4,.22,3),infill)
                box(n,(1.8,0,2.75),(1.6,.22,.5),infill)
                window(n,-1.5,-.17,1.0)
                for x in (1.0,2.6):box(n,(x,-.12,1.3),(.16,.26,2.6),'bois_noir')
                box(n,(1.8,-.12,2.5),(1.75,.26,.18),'bois_noir')
            else:
                box(n,(0,0,1.5),(6,.22,3),infill)
                for x in (-1.5,1.5):window(n,x,-.17,1.0)
            for x in (-2.92,0,2.92):box(n,(x,-.09,1.5),(.21,.30,3),'bois_noir')
            for z in (.20,.85,2.87):box(n,(0,-.10,z),(6.15,.31,.19),'bois_noir')
            m.detail=1;n.detail=1
            for sign in (-1,1):
                beam(n,(sign*2.80,-.16,.96),(sign*2.28,-.16,2.65),.12)
            for x in (-2.65,-1.15,.3,1.8):
                if not (gallery_door and front and x>0):beam(n,(x,-.16,.32),(x+.65,-.16,.74),.10)
            n.detail=0
            for x in (-2.4,-.8,.8,2.4):beam(n,(x,-.35,.05),(x,-.12,.60),.14)
        assets.transform_into(m,n,(3*math.sin(side*math.pi/2),-3*math.cos(side*math.pi/2),0),side*math.pi/2)
    m.detail=2
    return m


def roof(tile=False):
    m=Mesh();material='habitat_tuile' if tile else 'habitat_ardoise';height=3.9
    for y in (-3,3):
        m.surface([(-3,y,0),(3,y,0),(0,y,height)],[(0,1,2)],assets.mat('habitat_enduit'))
        beam(m,(-3,y,0),(3,y,0),.24)
        for x in (-2,-1,0,1,2):beam(m,(x,y,0),(x,y,height*(1-abs(x)/3)),.15)
        for side in (-1,1):beam(m,(side*3,y,0),(0,y,height),.22)
        window(m,0,y-.16,.5,.75,1.25)
    for side in (-1,1):
        points=[(0,-3.4,height+.12),(side*3.38,-3.4,-.10),(side*3.38,3.4,-.10),(0,3.4,height+.12)]
        m.surface(points,[(0,1,2,3)],assets.mat(material))
        for y in (-3.4,3.4):beam(m,(0,y,height+.16),(side*3.38,y,-.07),.16)
        # Une rive continue, fine et asymétrique, sans marches entre les segments.
        assets.roof_snow(m,6.76,6.8,-.10,4.22,side,9 if tile else 2)
    beam(m,(0,-3.5,height+.15),(0,3.5,height+.15),.15)
    return m


def gallery(bridge=False):
    m=Mesh();z=.10 if bridge else 3
    box(m,(0,0,z-.10),(3,1.5,.20),'bois_vieux')
    for y in (-.67,.67):
        if not bridge:
            # Les poteaux extérieurs dégagent le passage vers la porte basse.
            for x in (1.35,):
                beam(m,(x,y,0),(x,y,z),.18)
                beam(m,(x,y,z-1),(x*.52,y,z-.2),.14)
        if y>0 and not bridge:continue
        beam(m,(-1.45,y,z+1.06),(1.45,y,z+1.06),.12)
        for x in (-1.4,-.7,0,.7,1.4):beam(m,(x,y,z),(x,y,z+1.1),.075)
    m.detail=0
    for i in range(12):box(m,(-1.375+i*.25,0,z+.012),(.23,1.46,.035),'bois_vieux')
    m.detail=2
    return m


def stairs():
    m=Mesh()
    for j in range(15):
        y=-1.5+(j+.5)*.2;z=(j+1)*.2
        box(m,(0,y,z-.06),(1.5,.22,.12),'bois_vieux')
        box(m,(0,y-.10,z-.14),(1.5,.07,.22),'bois_vieux')
    for x in (-.70,.70):
        beam(m,(x,-1.55,0),(x,1.55,3),.16)
        beam(m,(x,-1.55,1.05),(x,1.55,4.05),.12)
        for j in range(6):
            y=-1.5+j*.6;z=.2+j*.6
            beam(m,(x,y,z),(x,y,z+1),.09)
    return m


def chimney():
    m=Mesh();box(m,(0,0,1.35),(.82,.90,2.7),'habitat_brique')
    box(m,(0,0,2.76),(1.05,1.12,.22),'pierre_taille')
    box(m,(0,0,2.90),(.64,.7,.09),'habitat_verre')
    return m


def dormer():
    m=Mesh();box(m,(0,0,.48),(1.42,1.35,.96),'habitat_enduit')
    window(m,0,-.72,.05,.90,.88)
    for side in (-1,1):
        m.surface([(0,-.85,1.8),(side*.86,-.85,.93),(side*.86,.8,.93),(0,.8,1.8)],[(0,1,2,3)],assets.mat('habitat_ardoise'))
        beam(m,(0,-.85,1.8),(side*.86,-.85,.93),.10)
    return m


def module(name):
    if name.startswith('marche_'):return marche.module(name)
    return {'socle_pierre':lambda:storey(True), 'etage_enduit':storey,
            'etage_brique':lambda:storey(brick=True),
            'etage_galerie':lambda:storey(gallery_door=True),
            'etage_galerie_brique':lambda:storey(brick=True,gallery_door=True),'toit_ardoise':roof,
            'toit_tuile':lambda:roof(True),'galerie':gallery,'escalier':stairs,
            'passerelle':lambda:gallery(True),'cheminee':chimney,'lucarne':dormer}[name]()


def composition(index):
    floors=2+int(index in (1,3,5));pieces=[]
    def add(n,p,rotation=0):pieces.append({'asset':'habitat_'+n,'position':list(p),'rotation':rotation})
    add('socle_pierre',(0,0,0))
    for level in range(1,floors):
        name='etage_brique' if index in (2,3) and level==1 else 'etage_enduit'
        if level==1 and index in (1,2,4,5):name='etage_galerie_brique' if index==2 else 'etage_galerie'
        add(name,(0,0,level*3))
    add('toit_tuile' if index in (2,4) else 'toit_ardoise',(0,0,floors*3))
    add('cheminee',(-1.5,1.5,floors*3+1.5))
    if index%2==0:add('lucarne',(1.5,0,floors*3+1.5),90)
    if index in (1,2,4,5):
        add('galerie',(1.5,-3.75,0),0)
        add('escalier',(-1.5,-3.75,0),-90)
    return pieces


def house(index):
    m=Mesh()
    for p in composition(index):assets.transform_into(m,module(p['asset'][8:]),p['position'],math.radians(p['rotation']))
    return m


def jobs():
    return [('habitat_'+n,lambda key=n:module(key),'module') for n,*_ in MODULES]+[(f'maison_modulaire_{i}',lambda j=i:house(j),'batiment') for i in range(6)]


def catalogue():
    return {'schema':1,'grille':.75,'etage':3,
            'modules':[{'id':'habitat_'+n,'label':label,'size':list(size),'kind':kind} for n,label,size,kind in MODULES],
            'maisons':[{'id':f'maison_modulaire_{i}','pieces':composition(i)} for i in range(6)]}
