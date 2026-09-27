"""Échoppes ouvertes et marchandises, sur la même trame que l'habitat.

Les petits fruits disparaissent au loin ; les caisses colorées restent lisibles.
Une échoppe est un seul maillage par niveau de détail, sans lumière ajoutée.
"""
import math
from local3d.atelier_v2.geometrie import Mesh
from local3d.citadelle import assets

MODULES = [
    ('marche_fruits', 'Marché · fruits, toile rouge', (4.5,3,3.5), 'base'),
    ('marche_legumes', 'Marché · légumes, toile verte', (4.5,3,3.5), 'base'),
    ('marche_pain', 'Marché · pains, toile bleue', (4.5,3,3.5), 'base'),
    ('marche_poterie', 'Marché · poteries, toile safran', (4.5,3,3.5), 'base'),
    ('marche_paniers', 'Marché · paniers de récolte', (1.5,1.5,.9), 'base'),
    ('marche_tonneaux', 'Marché · tonneaux et réserve', (1.5,1.5,1.35), 'base'),
    ('marche_fanions', 'Marché · guirlande sur poteaux', (6,1.5,4.5), 'base'),
]

def box(m,p,s,mat='bois_vieux'):m.box(p,s,assets.mat(mat))
def beam(m,a,b,w=.10):m.beam(a,b,w,assets.mat('bois_noir'))

def basket(m,x,y,z,produce=0,r=.32):
    m.cylinder((x,y,z),(x,y,z+.42),r*.72,r,assets.mat('bois_vieux'),12)
    m.cylinder((x,y,z+.421),(x,y,z+.432),r*.85,r*.85,assets.mat('bois_noir'),12)
    for zz in (.06,.22,.40):assets.ring(m,(x,y,z+zz),r*(.72+.28*zz/.42),.035,'bois_vieux',16,'XY')
    goods(m,x,y,z+.42,.45,.45,produce)

def goods(m,x,y,z,w,d,kind):
    color=('marche_rouge','marche_vert','marche_dore','cuivre')[kind%4]
    # La masse colorée garde le rayon identifiable au troisième niveau.
    box(m,(x,y,z+.035),(w*.90,d*.9,.07),color)
    m.detail=1
    for row in range(3):
        for col in range(5):
            xx=x+(col-2)*w/5;yy=y+(row-1)*d/3
            radius=min(w/11,d/6)
            scale=(radius,radius,radius*.9)
            if kind==1:scale=(radius*.65,radius*1.2,radius*1.45)
            if kind==2:scale=(radius*1.15,radius*.85,radius*.7)
            m.ico((xx,yy,z+.1),scale,assets.mat(color))
            if kind==1 and col%2==0:
                m.detail=0;beam(m,(xx,yy,z+.2),(xx+.035,yy,z+.32),.018);m.detail=1
    m.detail=2

def crate(m,x,y,z,kind):
    box(m,(x,y,z+.035),(.83,.84,.07))
    for dx in (-.43,.43):box(m,(x+dx,y,z+.17),(.07,.91,.29))
    for dy in (-.43,.43):box(m,(x,y+dy,z+.12),(.83,.055,.19))
    goods(m,x,y,z+.19,.78,.74,kind)

def stall(kind):
    m=Mesh();fabric=('marche_rouge','marche_vert','marche_bleu','marche_dore')[kind]
    for x in (-2,2):
        for y in (-1.3,1.3):
            beam(m,(x,y,0),(x,y,3.1),.13)
            beam(m,(x,y,2.2),(x*.68,y,2.85),.09)
        beam(m,(x,-1.38,2.85),(x,0,3.35),.1);beam(m,(x,0,3.35),(x,1.38,2.85),.1)
    beam(m,(-2.12,0,3.35),(2.12,0,3.35),.12)
    # Toile tendue, légèrement creusée entre les barres, bord festonné.
    for j in range(12):
        x=-2.2+j*4.4/12;end=x+4.4/12;mat=assets.mat(fabric if j%3<2 else 'marche_creme')
        for k in range(10):
            y=-1.45+k*2.9/10;y2=y+2.9/10
            def h(v):return 3.35-.34*abs(v)-.14*math.sin(math.pi*abs(v)/1.45)
            m.surface([(x,y,h(y)),(end,y,h(y)),(end,y2,h(y2)),(x,y2,h(y2))],[(0,1,2,3)],mat)
        for y in (-1.45,1.45):
            m.surface([(x,y,2.86),(end,y,2.86),(end,y,2.68),((x+end)/2,y,2.61),(x,y,2.68)],[(0,1,2,3,4)],mat)
    # Comptoir ouvert : on voit les caisses, la réserve et les pieds du marchand.
    box(m,(0,-.35,.94),(3.7,1.35,.14))
    for x in (-1.65,1.65):
        for y in (-.85,.15):beam(m,(x,y,0),(x,y,.95),.14)
    box(m,(0,.86,.38),(3.6,.55,.14))
    for j,x in enumerate((-1.35,-.45,.45,1.35)):
        if kind<3:crate(m,x,-.4,1.02,(kind+(j%2 if kind==0 else 0))%3)
        else:
            for yy in (-.65,-.12):
                m.cylinder((x,yy,1.03),(x,yy,1.42),.16,.23,assets.mat('marche_terre'),12)
                assets.ring(m,(x,yy,1.43),.22,.045,'marche_creme',16,'XY')
        box(m,(x,.85,.62),(.7,.49,.35))
    for x in (-1.75,1.75):basket(m,x,-1.05,0,kind%3,r=.28)
    # Enseigne de bois et petit pavillon coloré.
    box(m,(1.45,-1.43,2.15),(.63,.08,.43))
    m.surface([(-1.9,-1.44,2.68),(-1.45,-1.44,2.68),(-1.45,-1.44,1.92),(-1.67,-1.44,2.09),(-1.9,-1.44,1.92)],[(0,1,2,3,4)],assets.mat(fabric))
    return m

def barrels():
    m=Mesh()
    for x,y,h,r in ((-.35,.26,1.18,.34),(.38,-.28,.88,.30)):
        levels=[(0,r*.86),(.18*h,r),(.65*h,r*1.07),(h,r*.88)]
        for (z,a),(zz,b) in zip(levels,levels[1:]):m.cylinder((x,y,z),(x,y,zz),a,b,assets.mat('bois_vieux'),12)
        for z in (.12*h,.75*h,.94*h):assets.ring(m,(x,y,z),r*(1.04 if z<h*.8 else .94),.055,'fer_noir',16,'XY')
    return m

def baskets():
    m=Mesh()
    for x,y,k in ((-.34,-.30,0),(.33,-.28,1),(0,.34,2)):basket(m,x,y,0,k)
    return m

def bunting():
    m=Mesh()
    for x in (-2.92,2.92):beam(m,(x,0,0),(x,0,4.45),.11)
    def height(x):return 4.4-.48*(1-(x/3)**2)
    for i in range(18):
        a=-3+i/3;b=a+1/3;beam(m,(a,0,height(a)),(b,0,height(b)),.023)
    for j in range(11):
        x=-2.65+j*.53;z=height(x)
        m.surface([(x-.19,0,z),(x+.19,0,z),(x,.02,z-.58)],[(0,1,2)],assets.mat(('marche_rouge','marche_dore','marche_bleu','marche_vert','marche_creme')[j%5]))
    return m

def module(name):
    kinds=['fruits','legumes','pain','poterie']
    name=name.removeprefix('marche_')
    if name in kinds:return stall(kinds.index(name))
    return {'paniers':baskets,'tonneaux':barrels,'fanions':bunting}[name]()
