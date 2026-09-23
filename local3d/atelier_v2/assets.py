"""Bibliothèque modulaire : quatre architectures, arbres ramifiés et accessoires."""
import math
import random
from mathutils import Euler, Vector
from .geometrie import Mesh, material
from .plan import CONFIG

def building(style,role,index,textures):
    rng=random.Random(index+sum(ord(c) for c in style)*31)
    c=CONFIG['styles'][style];b=Mesh()
    wall=material(style+'_wall',textures);roof=material('colombage_roof_terre' if style=='colombage' and index in (2,5) else style+'_roof',textures)
    timber=material(style+'_timber',textures);stone=material(style+'_stone',textures)
    dark=material('fenetre',textures);iron=material('fer',textures)
    light=material('bois_clair',textures)
    if role=='tour':
        return landmark(style,textures)
    floors=1 if index in (0,3) and role=='maison' else 2
    height=c['floor_height']*floors*(.93+.028*index)+.62
    if role=='tour':height=12 if style!='terre' else 11
    w=7.2;d=6.2
    b.box((0,0,.28),(w+.35,d+.35,.56),stone)
    b.box((0,0,(height+.56)/2),(w,d,height-.56),wall)
    b.detail=1
    # Assises de pierre et angles avec joints visibles.
    for y in (-d/2,d/2):
        for i in range(10):
            b.box((-w/2+(i+.5)*w/10,y,.34),(w/10-.025,.12,.45),stone)
    for x in (-w/2,w/2):
        for y in (-d/2,d/2):
            if style=='colombage':b.box((x,y,height/2),(.19,.19,height),timber)
            elif style=='pierre':
                for z in range(int(height/.45)):
                    b.box((x,y,.7+z*.45),(.4 if z%2 else .6,.3,.39),stone)
    if style in ('colombage','chalet'):
        for z in (.72,3.3,height-.15):
            if z>height:continue
            b.box((0,-d/2-.06,z),(w+.12,.17,.17),timber)
            b.box((0,d/2+.06,z),(w+.12,.17,.17),timber)
        if style=='colombage':
            for x in (-2.35,0,2.35):
                for y in (-d/2-.08,d/2+.08):
                    b.box((x,y,height/2),(.14,.16,height-.7),timber)
                    for z in (1,3.55):
                        if z+1.6<height:
                            b.beam((x+.1,y,z),(x+1.05,y,z+1.5),.13,timber)
        else:
            for z in range(int((height-.6)/.25)):
                zz=.7+z*.25
                b.box((0,-d/2-.045,zz),(w+.12,.11,.065),timber)
                b.box((0,d/2+.045,zz),(w+.12,.11,.065),timber)
    # Baies profondes, appuis, meneaux et volets en volume.
    for side in (-1,1):
        for floor in range(floors if role!='tour' else 3):
            z=1.95+floor*c['floor_height']
            for x in (-2.2,0,2.2):
                if floor==0 and x==0 and side==-1:continue
                y=side*(d/2+.018)
                b.detail=2;b.box((x,y,z),(.96,.035,1.15),dark)
                b.detail=1
                for dx in (-.56,.56):b.box((x+dx,y+side*.1,z),(.13,.21,1.38),stone if style in ('pierre','terre') else timber)
                for zz in (-.63,.63):b.box((x,y+side*.1,z+zz),(1.22,.26,.13),stone if style in ('pierre','terre') else timber)
                b.detail=0
                b.box((x,y+side*.15,z),(.055,.055,1.1),timber)
                b.box((x,y+side*.15,z+.10),(1,.055,.055),timber)
                if style!='terre':
                    for dx in (-.85,.85):
                        b.box((x+dx,y+side*.13,z),(.45,.09,1.14),timber,angle=side*.1)
                        for j in range(3):b.box((x+dx,y+side*.19,z-.35+j*.35),(.45,.025,.065),light)
                else:
                    for j in range(4):b.box((x-.36+j*.24,y+side*.17,z),(.035,.05,1.1),timber)
    # Les façades latérales participent à la lecture à hauteur de rue.
    for side in (-1,1):
        x=side*(w/2+.025)
        for floor in range(floors):
            z=1.95+floor*c['floor_height']
            for y in (-1.55,1.55):
                b.detail=2;b.box((x,y,z),(.04,.92,1.10),dark)
                b.detail=1
                for yy in (-.53,.53):b.box((x+side*.10,y+yy,z),(.18,.12,1.34),timber if style in ('chalet','colombage') else stone)
                for zz in (-.61,.61):b.box((x+side*.10,y,z+zz),(.20,1.18,.12),timber if style in ('chalet','colombage') else stone)
                b.detail=0;b.box((x+side*.15,y,z),(.045,.04,1.1),timber)
                if style!='terre':
                    for yy in (-.8,.8):b.box((x+side*.13,y+yy,z),(.09,.42,1.12),timber)
        b.detail=1
        if style in ('colombage','chalet'):
            for z in (.72,3.3,height-.15):
                if z<=height:b.box((x,0,z),(.17,d,.16),timber)
        if style=='colombage':
            for y in (-d/2,0,d/2):b.box((x,y,height/2),(.16,.16,height-.5),timber)
    b.detail=2
    door_y=-d/2-.03
    b.box((0,door_y,1.45),(1.22,.10,2.15),timber)
    b.detail=1
    for x in (-.7,.7):b.box((x,door_y-.1,1.47),(.16,.23,2.45),stone)
    b.box((0,door_y-.10,2.65),(1.6,.24,.22),stone)
    if style in ('pierre','terre'):
        for i in range(11):
            a=i*math.pi/10
            b.box((math.cos(a)*.8,door_y-.13,2.55+math.sin(a)*.8),(.24,.24,.25),stone,angle=0)
    b.detail=0
    for x in (-.36,-.12,.12,.36):b.box((x,door_y-.062,1.45),(.025,.022,2.0),light)
    b.box((.4,door_y-.11,1.35),(.13,.04,.09),iron)
    for i in range(3):b.box((0,-d/2-.28-i*.27,.5-i*.15),(1.8,.34,.16),stone)
    b.detail=2
    if style=='terre':
        b.box((0,0,height),(w+.28,d+.28,.27),roof)
        for x in (-w/2,w/2):b.box((x,0,height+.37),(.3,d,.65),wall)
        for y in (-d/2,d/2):b.box((0,y,height+.37),(w,.3,.65),wall)
        if role=='tour':
            for x in (-3,-1.5,0,1.5,3):
                for y in (-d/2,d/2):b.box((x,y,height+.88),(.58,.45,.7),wall)
        b.detail=1
        for x in (-2.3,0,2.3):b.cylinder((x,-d/2+.3,height-.15),(x,-d/2-.55,height-.15),.11,.09,timber,8)
        # Pergola ombragée sur la terrasse.
        for x in (-2.3,2.3):
            for y in (-1.8,1.8):b.box((x,y,height+1.1),(.13,.13,2),timber)
        for i in range(12):b.box((-2.5+i*.46,0,height+2.1),(.13,4.1,.13),timber)
    else:
        pitch=math.radians(c['pitch']);span=w/2+c['overhang'];run=d/2+c['overhang']
        ridge=height+math.tan(pitch)*span
        for s in (-1,1):
            b.surface([(0,-run,ridge),(s*span,-run,height),(s*span,run,height),(0,run,ridge)],[(0,1,2,3)],roof)
            b.surface([(0,-d/2,height),(s*w/2,-d/2,height),(0,-d/2,ridge-.15)],[(0,1,2)],wall)
            b.surface([(0,d/2,height),(s*w/2,d/2,height),(0,d/2,ridge-.15)],[(0,2,1)],wall)
            b.detail=1
            for y in (-run,run):b.beam((0,y,ridge),(s*span,y,height),.16,timber)
            b.beam((s*span,-run,height),(s*span,run,height),.17,timber)
            b.detail=0
            # Rangées de couverture en relief : lisibles de près, retirées aux LOD suivants.
            for i in range(1,int(span/.32)):
                x=s*i*.32;z=ridge-abs(x)*math.tan(pitch)+.028
                b.beam((x,-run,z),(x,run,z),.035,roof)
            b.detail=2
        b.beam((0,-run-.10,ridge+.04),(0,run+.10,ridge+.04),.19,roof)
        b.box((2,1,height+1.2),(.62,.72,3),stone)
        b.detail=1;b.box((2,1,height+2.76),(.85,.95,.18),stone)
        if style=='colombage' and floors>1:
            # Lucarne charpentée, véritable volume sur la pente.
            b.box((1.85,0,height+1),(.9,1.1,1.15),wall)
            b.box((2.32,0,height+1.12),(.06,.62,.6),dark)
            b.beam((1.3,-.68,height+1.6),(2.5,0,height+1.6),.14,roof)
            b.beam((1.3,.68,height+1.6),(2.5,0,height+1.6),.14,roof)
        b.detail=1
        if style=='colombage':
            for y in (-d/2-.055,d/2+.055):
                b.beam((-w/2,y,height),(0,y,ridge-.18),.14,timber)
                b.beam((w/2,y,height),(0,y,ridge-.18),.14,timber)
                b.beam((0,y,height),(0,y,ridge-.18),.14,timber)
        # Appentis bas : une seconde masse distingue les variantes.
        if index in (1,4) and role!='tour':
            leanheight=2.65
            b.box((0,d/2+.55,1.42),(w*.62,1.2,2.5),wall)
            b.surface([(-w*.35,d/2,leanheight+.5),(w*.35,d/2,leanheight+.5),
                (w*.35,d/2+1.45,leanheight),(-w*.35,d/2+1.45,leanheight)],[(0,1,2,3)],roof)
    if (style=='chalet' and floors>1) or role=='auberge':
        z=3.2;b.detail=1
        b.box((0,-d/2-.72,z),(w,1.5,.18),timber)
        for x in (-3.3,0,3.3):b.box((x,-d/2-1.2,1.85),(.18,.18,3.6),timber)
        for i in range(19):b.box((-3.4+i*.38,-d/2-1.4,z+.51),(.09,.10,.94),timber)
        b.box((0,-d/2-1.4,z+1),(w,.14,.13),timber)
    if role in ('atelier','auberge'):
        b.detail=1
        cloth=material('toile_indigo' if style=='terre' else 'toile_creme',textures)
        b.surface([(-3,-d/2,2.8),(3,-d/2,2.8),(3,-d/2-1.65,2.3),(-3,-d/2-1.65,2.3)],[(0,3,2,1)],cloth)
        for x in (-2.8,2.8):b.box((x,-d/2-1.55,1.2),(.12,.12,2.4),timber)
        b.detail=0;b.box((2.8,-d/2-.45,2.85),(.55,.15,.68),light)
    return b

def landmark(style,textures):
    """Une silhouette de repère, distincte des maisons agrandies."""
    b=Mesh();wall=material(style+'_wall',textures);stone=material(style+'_stone',textures)
    roof=material(style+'_roof',textures);timber=material(style+'_timber',textures);dark=material('fenetre',textures)
    b.box((0,0,.32),(6.8,8.8,.64),stone)
    b.box((0,-1.5,2.8),(6,5,5),wall)
    b.box((0,2,5.5),(3.7,3.7,10.4),wall)
    for z in (.8,5.2,8.6,10.6):b.box((0,2,z),(4,4,.24),stone)
    for side in (-1,1):
        for x in (-.55,.55):b.box((x,2+side*1.87,9.6),(.65,.04,1.5),dark)
        for y in (1.45,2.55):b.box((side*1.87,y,9.6),(.04,.65,1.5),dark)
        for y in (-2.8,-.3):
            b.box((side*3.02,y,3),(.04,.7,1.8),dark)
            b.detail=1;b.box((side*3.18,y,1.9),(.35,.9,.2),stone);b.detail=2
    b.box((0,-4.03,1.7),(1.45,.08,2.8),timber)
    if style=='terre':
        b.box((0,-1.5,5.38),(6.3,5.3,.3),roof)
        for x in (-2.9,2.9):b.box((x,-1.5,5.7),(.25,5,.7),wall)
        for x in (-1.6,0,1.6):
            for y in (.3,3.7):b.box((x,y,11.0),(.6,.45,.85),wall)
        for x in (-1.7,1.7):
            for y in (1.25,2.75):b.box((x,y,11.0),(.45,.6,.85),wall)
    else:
        b.surface([(-3.4,-4.3,5.1),(0,-4.3,7.2),(3.4,-4.3,5.1),(-3.4,1.3,5.1),(0,1.3,7.2),(3.4,1.3,5.1)],[(0,3,4,1),(1,4,5,2)],roof)
        top=14.8 if style in ('colombage','chalet') else 12.5
        b.surface([(-2.3,-.3,10.8),(2.3,-.3,10.8),(2.3,4.3,10.8),(-2.3,4.3,10.8),(0,2,top)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],roof)
        b.detail=1;b.beam((0,2,top),(0,2,top+.9),.075,timber)
    return b

def tree(kind,index,textures):
    b=Mesh();rng=random.Random(802+index*117+sum(map(ord,kind)))
    wood=material('bois',textures)
    leaves=material('feuilles',textures)
    h=rng.uniform(10,15) if kind!='cypres' else rng.uniform(12,18)
    b.cylinder((0,0,0),(.15,.2,h*(.74 if kind=='palmier' else .65)),.38,.09,wood,10)
    if kind=='palmier':
        for j in range(12):
            a=j*math.tau/12;tip=(math.cos(a)*4.7,math.sin(a)*4.7,h-.8)
            b.detail=2
            curve=[]
            for k in range(19):
                t=k/18;curve.append((math.cos(a)*4.7*t,math.sin(a)*4.7*t,h*.72+math.sin(t*2.7)*2.5-t*1.0))
            for k,(p,q) in enumerate(zip(curve,curve[1:])):
                b.beam(p,q,.075,wood)
                for side in (-1,1):
                    pp=Vector(p);qq=Vector(q);t=(k+.5)/18
                    spread=math.sin(math.pi*(t*.84+.08))*.95
                    tip=(pp+qq)/2+Vector((-math.sin(a),math.cos(a),-.5))*side*spread
                    tip.z=min(pp.z,qq.z)-.25-spread*.2
                    tip+=Vector((math.cos(a),math.sin(a),0))*.38
                    mid=(pp+qq)/2
                    offset=(qq-pp).normalized()*.065
                    b.surface([tuple(mid-offset),tuple(mid+offset),tuple(tip)],[(0,1,2)],leaves)
        b.detail=0
        for z in range(int(h*.65/.26)):
            b.cylinder((0,0,z*.26),(0,0,z*.26+.07),.38-z*.005,.39-z*.005,wood,10)
    elif kind=='cypres':
        for i in range(7):
            b.ico((.2*math.sin(i),0,h*.27+i*h*.09),(1.35-i*.12,1.3-i*.11,2.2),leaves,2)
    elif kind in ('sapin','meleze'):
        needles=material('aiguilles',textures,alpha=True)
        for layer in range(9):
            z=h*.25+layer*h*.078;radius=(1-layer/10)*3.6
            for j in range(7):
                a=j*math.tau/7+layer*.7
                end=(math.cos(a)*radius,math.sin(a)*radius,z+.12)
                b.detail=1 if layer%2 else 2
                b.cylinder((0,0,z+.25),end,.07,.018,wood,6)
                for t in (.5,.9):
                    center=(end[0]*t,end[1]*t,z+.3)
                    for tilt in (0,.9):
                        q=Euler((tilt,.15,a),'XYZ').to_quaternion()
                        b.foliage_card(center,(radius*1.15,2),q,needles)
    else:
        texture='feuille_bouleau' if kind=='bouleau' else 'feuille_olivier' if kind=='olivier' else 'feuille_chene'
        foliage=material(texture,textures,alpha=True)
        if kind=='olivier':h*=.67
        for j in range(13):
            a=j*2.399;rad=rng.uniform(1.7,3.8);z=h*.49+rng.uniform(0,h*.32)
            tip=Vector((math.cos(a)*rad,math.sin(a)*rad,z))
            b.detail=2;b.cylinder((.1,0,h*.35),tip,.13,.022,wood,7)
            for k in range(8):
                offset=Vector((rng.uniform(-1.5,1.5),rng.uniform(-1.5,1.5),rng.uniform(-1.4,1.4)))
                center=tip+offset
                b.detail=2 if k%3==0 else 1 if k%2 else 0
                q=Euler((rng.uniform(-1.3,1.3),rng.uniform(-1.1,1.1),rng.uniform(0,6.28)),'XYZ').to_quaternion()
                b.foliage_card(center,(3.2,3.2),q,foliage)
    b.detail=2
    return b

def prop(kind,index,textures):
    b=Mesh();rng=random.Random(990+index)
    wood=material('bois',textures);light=material('bois_clair',textures)
    iron=material('fer',textures);stone=material('pierre_grise',textures)
    grass=material('herbe',textures);hay=material('paille',textures)
    if kind=='rocher':
        mat=material('roche_ocre' if index%3==2 else 'roche',textures)
        for i in range(2):
            start=len(b.verts)
            b.ico((rng.uniform(-.5,.5),rng.uniform(-.4,.4),.35+i*.3),
                (rng.uniform(.9,1.6),rng.uniform(.7,1.2),rng.uniform(.7,1.4)),mat,2)
            for j in range(start,len(b.verts)):
                x,y,z=b.verts[j]
                f=.88+.18*math.sin(x*5.7+y*3.1+index)+.12*math.cos(z*6.3-x*4)
                b.verts[j]=(x*f+z*.19,y*f,z*f-.35)
    elif kind in ('herbe','roseaux','buisson','sec'):
        mat=material('herbe_seche' if kind=='sec' else 'herbe',textures)
        for j in range(18 if kind!='buisson' else 35):
            a=rng.uniform(0,6.28);r=rng.uniform(0,.65);h=rng.uniform(.3,1.1)
            if kind=='roseaux':h*=2.3
            x,y=math.cos(a)*r,math.sin(a)*r
            b.detail=2 if j%3==0 else 1 if j%2 else 0
            b.surface([(x-.04,y,0),(x+.04,y,0),(x+.14,y+.12,h)],[(0,1,2)],mat)
            if kind=='roseaux':b.cylinder((x+.14,y+.12,h*.8),(x+.14,y+.12,h),.045,.035,wood,5)
        if kind=='buisson':
            fol=material('feuille_chene',textures,alpha=True)
            for j in range(8):b.foliage_card((rng.uniform(-.5,.5),rng.uniform(-.5,.5),.65),(1.3,1.3),Euler((j*.6,.2,j*2.4)).to_quaternion(),fol)
    elif kind=='cloture':
        for x in (-1.5,1.5):b.box((x,0,.65),(.14,.16,1.3),wood)
        for z in (.4,.95):b.box((0,0,z),(3.15,.10,.13),light)
        b.detail=0;b.beam((-1.4,0,.3),(1.4,0,1),.08,wood)
    elif kind=='tonneau':
        b.cylinder((0,0,.1),(0,0,.62),.42,.51,wood,12)
        b.cylinder((0,0,.62),(0,0,1.14),.51,.42,wood,12)
        for z,r in ((.2,.45),(.57,.52),(1.04,.45)):
            b.cylinder((0,0,z),(0,0,z+.07),r,r,iron,12)
        b.detail=0;b.cylinder((0,0,1.15),(0,0,1.18),.4,.4,light,12)
    elif kind=='caisse':
        b.box((0,0,.45),(.9,.9,.9),light)
        b.detail=1
        for x in (-.39,.39):b.box((x,-.48,.45),(.1,.08,.9),wood)
        b.beam((-.4,-.5,.05),(.4,-.5,.85),.09,wood)
    elif kind=='charrette':
        b.box((0,0,.85),(1.7,2.4,.17),wood)
        for x in (-.8,.8):b.box((x,0,1.25),(.12,2.4,.65),light)
        for y in (-1.15,1.15):b.box((0,y,1.25),(1.6,.12,.65),light)
        for x in (-1.08,1.08):
            for j in range(12):
                a=j*math.tau/12;c=(x,math.cos(a)*.64,.65+math.sin(a)*.64)
                q=(x,math.cos(a+.53)*.64,.65+math.sin(a+.53)*.64)
                b.beam(c,q,.10,iron)
                b.detail=1;b.beam((x,0,.65),c,.055,wood);b.detail=2
        for x in (-.65,.65):b.beam((x,-.7,.8),(x,-3.4,.9),.13,wood)
    elif kind=='etal':
        b.box((0,0,.9),(2.5,1,.18),wood)
        for x in (-1.1,1.1):
            for y in (-.5,.5):b.box((x,y,1.3),(.1,.1,2.6),wood)
        for i in range(10):
            mat=material('toile_rouge' if i%2 else 'toile_creme',textures)
            x=-1.4+i*.28
            b.surface([(x,-.85,2.6),(x+.28,-.85,2.6),(x+.28,0,3),(x,0,3)],[(0,1,2,3)],mat)
            b.surface([(x,0,3),(x+.28,0,3),(x+.28,.85,2.6),(x,.85,2.6)],[(0,1,2,3)],mat)
        b.detail=0
        for j in range(15):b.ico((rng.uniform(-1,1),rng.uniform(-.35,.35),1.05),(.13,.13,.15),hay,1)
    elif kind=='puits':
        for layer in range(4):
            for i in range(14):
                a=(i+layer*.5)*math.tau/14
                b.box((math.cos(a),math.sin(a),.14+layer*.27),(.46,.3,.25),stone,angle=a+math.pi/2)
        for x in (-1.3,1.3):b.box((x,0,1.45),(.17,.17,2.9),wood)
        b.beam((-1.4,0,2.8),(1.4,0,2.8),.18,wood)
        b.cylinder((0,0,.6),(0,0,2.8),.025,.025,light,6)
    elif kind=='barque':
        vs=[(-.75,-1.8,.15),(.75,-1.8,.15),(.95,1.2,.15),(0,2.3,.3),(-.95,1.2,.15),
            (-.95,-1.9,.7),(.95,-1.9,.7),(1.2,1.2,.7),(0,2.5,.85),(-1.2,1.2,.7)]
        b.surface(vs,[(0,4,3,2,1)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)],wood)
        for y in (-1,0,1):b.box((0,y,.55),(1.7,.3,.09),light)
        b.detail=1;b.beam((-.7,-1.4,.8),(1.7,1.4,.8),.055,light)
    elif kind=='ble':
        for i in range(20):
            x,y=rng.uniform(-.7,.7),rng.uniform(-.7,.7);h=rng.uniform(.65,1.1)
            b.detail=2 if i%4==0 else 0
            b.beam((x,y,0),(x+.08,y,h),.012,hay)
            b.ico((x+.08,y,h),(.055,.055,.15),hay,1)
    else:raise ValueError('Accessoire inconnu : '+kind)
    return b
