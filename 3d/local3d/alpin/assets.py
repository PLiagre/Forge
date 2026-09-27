"""Kit alpin : bâtiments enrichis et petits modules partagés entre dispositions."""
import math
import random
from local3d.atelier_v2.geometrie import Mesh,material
from local3d.atelier_v2 import assets as base

def building(role,index,textures):
    b=base.building('chalet',role,index,textures)
    if role=='tour':return b
    floors=1 if index in (0,3) and role=='maison' else 2
    timber=material('chalet_timber',textures);stone=material('chalet_stone',textures)
    colored=material('volet_'+str(index%3),textures)
    flower=material('fleur_'+str(index%3),textures);leaf=material('herbe',textures)
    for side in (-1,1):
        for floor in range(floors):
            z=1.95+floor*2.7
            for x in (-2.2,0,2.2):
                if floor==0 and x==0 and side==-1:continue
                b.detail=1
                for dx in (-.85,.85):b.box((x+dx,side*3.33,z),(.44,.045,1.1),colored)
                if floor==1 or (index%2==0 and side==-1):
                    b.box((x,side*3.45,z-.77),(1.45,.48,.26),timber)
                    b.detail=0
                    for i in range(7):
                        xx=x-.6+i*.2
                        b.ico((xx,side*3.45,z-.54),(.15,.16,.15),leaf,1)
                        b.ico((xx+.04,side*3.48,z-.37),(.085,.085,.075),flower,1)
    b.detail=0
    # Consoles charpentées et enseigne, fabriquées dans le même repère métrique.
    height=2.7*floors*(.93+.028*index)+.62
    for x in (-3.45,0,3.45):b.beam((x,-3.12,height-.75),(x,-3.95,height),.13,timber)
    if role in ('atelier','auberge'):
        b.beam((2.5,-3.2,3),(2.5,-4.45,3),.12,timber)
        b.box((2.5,-4.15,2.55),(.12,.7,.65),colored)
    return b

def extra(kind,textures):
    b=Mesh();wood=material('bois',textures);light=material('bois_clair',textures)
    stone=material('chalet_stone',textures);iron=material('fer',textures)
    if kind=='roue_moulin':
        # Origine au centre de l'axe : le même asset tourne dans Blender et Unity.
        for x in (-.65,.65):
            for j in range(32):
                a=j*math.tau/32;aa=(j+1)*math.tau/32
                b.beam((x,math.sin(a)*2.4,math.cos(a)*2.4),(x,math.sin(aa)*2.4,math.cos(aa)*2.4),.16,wood)
                if j%4==0:b.beam((x,0,0),(x,math.sin(a)*2.3,math.cos(a)*2.3),.15,light)
        for j in range(20):
            a=j*math.tau/20
            b.beam((-.8,math.sin(a)*2.4,math.cos(a)*2.4),(.8,math.sin(a)*2.4,math.cos(a)*2.4),.38,light,depth=.14)
        b.cylinder((-1.5,0,0),(1.5,0,0),.24,.24,iron,12)
    elif kind=='buches':
        for layer in range(4):
            for i in range(6-layer):
                x=(i-(5-layer)/2)*.4
                b.cylinder((x,-.5,.22+layer*.37),(x,.5,.22+layer*.37),.22,.18,wood,9)
                b.detail=1;b.cylinder((x,-.515,.22+layer*.37),(x,-.53,.22+layer*.37),.16,.16,light,9);b.detail=2
    elif kind=='banc':
        b.box((0,0,.6),(2.6,.5,.16),light)
        for x in (-1,1):b.box((x,0,.3),(.18,.4,.6),wood)
        for z in (.94,1.2):b.box((0,.2,z),(2.6,.09,.18),wood)
        for x in (-1,1):b.box((x,.2,.9),(.12,.12,.7),wood)
    elif kind=='abreuvoir':
        b.box((0,0,.16),(3.8,1.2,.3),stone)
        for y in (-.6,.6):b.box((0,y,.55),(3.8,.18,.9),stone)
        for x in (-1.85,1.85):b.box((x,0,.55),(.2,1.2,.9),stone)
        b.box((0,0,.58),(3.5,1,.04),material('eau_alpine',textures))
        b.box((-2,0,1),(.35,.35,2),wood);b.beam((-2,0,1.6),(-1.2,0,1.6),.15,wood)
    elif kind=='lanterne':
        glow=material('lumiere',textures)
        b.box((0,0,.35),(.3,.3,.45),glow)
        for x in (-.18,.18):
            for y in (-.18,.18):b.box((x,y,.35),(.04,.04,.6),iron)
        b.box((0,0,.05),(.4,.4,.07),iron)
        b.surface([(-.23,-.23,.64),(.23,-.23,.64),(.23,.23,.64),(-.23,.23,.64),(0,0,.89)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],iron)
    elif kind=='fleurs':
        rng=random.Random(73)
        for i in range(25):
            x,y=rng.uniform(-.65,.65),rng.uniform(-.65,.65);z=rng.uniform(.22,.55)
            b.detail=2 if i%3==0 else 0
            b.beam((x,y,0),(x,y,z),.012,material('herbe',textures))
            mat=material('fleur_'+str(i%3),textures)
            for j in range(5):
                a=j*math.tau/5;b.ico((x+math.cos(a)*.05,y+math.sin(a)*.05,z),(.05,.04,.02),mat,1)
    elif kind=='foin':
        mat=material('paille',textures)
        b.ico((0,0,.8),(1.5,1.5,1.4),mat,2)
        for x in (-1.7,1.7):b.box((x,0,1.3),(.15,.15,2.6),wood)
        b.beam((-1.9,0,2.4),(1.9,0,2.4),.12,wood)
    elif kind=='linge':
        for x in (-2,2):b.box((x,0,1.3),(.1,.1,2.6),wood)
        b.beam((-2,0,2.45),(2,0,2.45),.02,wood)
        for i in range(4):
            x=-1.8+i*.92
            b.surface([(x,0,2.4),(x+.75,0,2.4),(x+.73,.15,1.1),(x,.12,1.15)],[(0,1,2,3)],material('linge_'+str(i%2),textures))
    elif kind=='muret':
        for z in range(3):
            for i in range(7):b.box((-1.5+i*.48+(z%2)*.12,0,.2+z*.33),(.44,.52,.3),stone)
    else:raise ValueError(kind)
    b.detail=2
    return b
