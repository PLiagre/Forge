"""Modules de citadelle. Mètres, origine au sol, façade vers -Y.

Les détails de niveau 0 disparaissent en premier, puis ceux de niveau 1.
La silhouette et la neige restent présentes dans les trois niveaux.
"""
import math
import random
import bpy
import numpy as np
from mathutils import Vector
from local3d.atelier_v2.geometrie import Mesh,material

TEX=None
def mat(n):
    m=material(n,TEX,alpha=n in ('aiguilles_sombres','neige_rameaux'))
    if m.get('citadelle_surface') != 2:
        configure_material(m,n)
    return m


def configure_material(m,n):
    """Actualise les cartes partagées sans modifier les maillages des sources."""
    nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
    if not bs:return
    for node in nodes:
        if node.type=='TEX_IMAGE' and node.image:
            path=TEX / node.image.name.split('.')[0]
            # Les sources embarquent parfois l'ancienne version de la même carte.
            filename=node.image.filepath.replace('\\','/').rsplit('/',1)[-1]
            path=TEX/filename
            if path.is_file():
                node.image=bpy.data.images.load(str(path),check_existing=True)
                node.image.reload()
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.48
    tex=next((q for q in nodes if q.type=='TEX_IMAGE' and q.image and '_BaseColor' in q.image.name),None)
    if n in ('aiguilles_sombres','neige_rameaux') and tex:
        cutoff=nodes.new('ShaderNodeMath');cutoff.operation='GREATER_THAN';cutoff.inputs[1].default_value=.35
        links.new(tex.outputs['Alpha'],cutoff.inputs[0]);links.new(cutoff.outputs[0],bs.inputs['Alpha'])
    if n=='enduit' and tex:
        info=nodes.new('ShaderNodeObjectInfo');mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
        links.new(tex.outputs['Color'],mix.inputs[1]);links.new(info.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],bs.inputs['Base Color'])
    if n in ('lumiere','vitrail_ambre','vitrail_bleu') and tex:
        links.new(tex.outputs['Color'],bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value=1.6 if n=='lumiere' else .65
    gloss=TEX/(n+'_MetallicGloss.png')
    if gloss.exists():
        t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(gloss),check_existing=True);t.image.colorspace_settings.name='Non-Color'
        invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1
        links.new(t.outputs['Alpha'],invert.inputs[1]);links.new(invert.outputs[0],bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value=.82 if n=='fer_noir' else .65 if n=='cuivre' else 0
    m['citadelle_surface']=2

def arch_points(w,h,n=12):
    # Deux arcs rejoignent une pointe ; base verticale puis ogive.
    r=w*.5;spring=h-r*1.25
    return [(-r,0),(-r,spring)]+[(-r+2*r*t/n,spring+1.25*r*math.sin(math.pi*t/n)**.72) for t in range(1,n)]+[(r,spring),(r,0)]

def window(m,x,y,z,w,h,stone='calcaire',glass='vitrail_ambre'):
    pts=arch_points(w,h);m.surface([(x+a,y,z+b) for a,b in pts],[tuple(range(len(pts)))],mat(glass))
    for a,b in zip(pts,pts[1:]+pts[:1]):m.beam((x+a[0],y-.055,z+a[1]),(x+b[0],y-.055,z+b[1]),.16,mat(stone))
    m.detail=1
    for dx in (-w/6,w/6):m.beam((x+dx,y-.09,z+.1),(x+dx,y-.09,z+h-.28),.075,mat('fer_noir'))
    m.beam((x-w*.45,y-.1,z+h*.40),(x+w*.45,y-.1,z+h*.4),.085,mat('fer_noir'))
    # Ébrasement en pierre, appui saillant et remplage devant le verre.
    for a,b in zip(pts,pts[1:]):
        m.surface([(x+a[0],y,z+a[1]),(x+b[0],y,z+b[1]),
                   (x+b[0]*1.1,y-.21,z+b[1]*1.02),(x+a[0]*1.1,y-.21,z+a[1]*1.02)],[(0,1,2,3)],mat(stone))
    m.box((x,y-.15,z-.08),(w+.32,.38,.16),mat(stone))
    if w>2:
        for dx in (-w*.22,w*.22):
            sub=arch_points(w*.43,h*.79,12)
            for a,b in zip(sub[1:],sub[2:]):m.beam((x+dx+a[0],y-.18,z+a[1]),(x+dx+b[0],y-.18,z+b[1]),.09,mat(stone))
        ring(m,(x,y-.20,z+h*.79),w*.16,.07,stone,20)
    m.detail=2

def ring(m,center,r,width,material,n=40,plane='XZ'):
    x,y,z=center
    def p(a,rr):return (x+rr*math.cos(a),y,z+rr*math.sin(a)) if plane=='XZ' else (x+rr*math.cos(a),y+rr*math.sin(a),z)
    for j in range(n):
        a=j*math.tau/n;b=(j+1)*math.tau/n
        m.surface([p(a,r-width/2),p(a,r+width/2),p(b,r+width/2),p(b,r-width/2)],[(0,1,2,3)],mat(material))

def masonry(m,x,y,z,w,d,h,seed=0):
    m.box((x,y,z+h/2),(w,d,h),mat('basalte'))
    m.detail=0;rng=random.Random(seed)
    for row in range(int(h/.7)):
        for col in range(int(w/1.3)+1):
            xx=x-w/2+col*1.3+(row%2)*.65;ww=min(1.24,x+w/2-xx)
            if ww<.15:continue
            m.box((xx+ww/2,y-d/2-.045,z+.37+row*.7),(ww,.10,.63),mat('pierre_taille' if rng.random()<.22 else 'basalte'))
    m.detail=2

def roof_snow(m,w,d,z,rise,side,seed):
    # Dépôt mince près du faîtage ; les deux extrémités partagent la même rive.
    segments=max(24,int(d*6))
    def limit(y):
        return .075+.035*math.sin(y*1.6+seed)+.018*math.sin(y*3.7+seed*.5)+(side==1)*.04
    for i in range(segments):
        ya=-d/2+i*d/segments;yb=-d/2+(i+1)*d/segments
        points=[]
        for f,y in ((0,ya),(limit(ya),ya),(limit(yb),yb),(0,yb)):
            points.append((side*w*.5*f,y,z+rise*(1-f)+.042*(1-f/max(limit(y),.001))+.012))
        m.surface(points,[(0,1,2,3)],mat('neige_givre'))


def roof(m,w,d,z,rise,seed=0):
    rng=random.Random(seed)
    for side in (-1,1):
        order=(0,1,2,3) if side==1 else (3,2,1,0)
        m.surface([(0,-d/2,z+rise),(side*w/2,-d/2,z),(side*w/2,d/2,z),(0,d/2,z+rise)],[order],mat('ardoise'))
        rows=max(4,int(rise/.42));cols=max(4,int(d/.62))
        for j in range(rows):
            f=j/rows;f2=min(1,(j+1.03)/rows)
            for i in range(cols):
                yy=-d/2+i*d/cols;yy2=yy+d/cols*.985
                depth=.055+rng.random()*.025
                # Congères continues, déchirées par le vent ; les ardoises restent lisibles.
                cover=math.sin(i*.51+seed)*.34+math.cos(j*.39+i*.24)*.36+rng.uniform(-.1,.1)
                snowy=cover>-.38 and not (side==1 and i>cols*.75 and j>rows*.4)
                # Ardoises physiques au premier niveau, sans damier neige/tuile.
                m.detail=0
                m.surface([(side*w*.5*f,yy,z+rise*(1-f)+depth),
                           (side*w*.5*f2,yy,z+rise*(1-f2)+depth),
                           (side*w*.5*f2,yy2,z+rise*(1-f2)+depth),
                           (side*w*.5*f,yy2,z+rise*(1-f)+depth)],[order],mat('ardoise'))
        m.detail=2
        roof_snow(m,w,d,z,rise,side,seed)
        m.detail=1
        for yy in (-d/2,d/2):m.beam((0,yy,z+rise+.08),(side*w/2,yy,z+.08),.21,mat('bois_noir'))
        # Des chevrons sous le débord donnent de l'épaisseur à la couverture.
        for yy in np.linspace(-d/2,d/2,max(3,int(d))):
            m.beam((side*(w/2-.55),yy,z+.2),(side*w/2,yy,z-.1),.13,mat('bois_noir'))
        m.detail=2
    m.beam((0,-d/2-.15,z+rise+.14),(0,d/2+.15,z+rise+.14),.16,mat('ardoise'))

def house(index):
    m=Mesh();w=6.2+index*.36;d=7+index%3;h=5.6+(index%3)*1.2;rise=5.5+index*.18
    masonry(m,0,0,0,w,d,1.4,index)
    m.box((0,0,1.4+(h-1.4)/2),(w,d,h-1.4),mat('enduit'))
    for y in (-d/2,d/2):
        m.surface([(-w/2,y,h),(w/2,y,h),(0,y,h+rise-.25)],[(0,1,2)],mat('enduit'))
        for x in (-w/2,-w/4,0,w/4,w/2):m.box((x,y-.045,h/2),(.19,.22,h),mat('bois_noir'))
        for z in (1.4,3.8,h):m.box((0,y,z),(w+.1,.24,.25),mat('bois_noir'))
        for x in (-w*.36,w*.36):m.beam((x,y-.08,4),(0,y-.08,h-.1),.17,mat('bois_noir'))
        m.beam((-w/2,y,h),(0,y,h+rise-.2),.23,mat('bois_noir'));m.beam((w/2,y,h),(0,y,h+rise-.2),.23,mat('bois_noir'))
        for z in (2,4.6):
            for x in (-w*.27,w*.27):window(m,x,y-.16,z,.85,1.25,'bois_vieux','lumiere')
        window(m,0,y-.19,h+.7,1.1,1.75,'bois_vieux','lumiere')
    for sx in (-1,1):
        for yy in (-d/2,0,d/2):m.box((sx*w/2,yy,h/2),(.22,.20,h),mat('bois_noir'))
        for z in (1.4,3.8,h):m.box((sx*w/2,0,z),(.23,d,.24),mat('bois_noir'))
        # Fenêtres latérales orientées dans un module temporaire.
        n=Mesh()
        for yy in (-d*.26,d*.24):window(n,yy,0,4.6,.8,1.4,'bois_vieux','lumiere')
        transform_into(m,n,(sx*w/2+sx*.13,0,0),math.pi/2 if sx==1 else -math.pi/2)
    window(m,0,-d/2-.24,.15,1.45,2.5,'pierre_taille','bois_noir')
    roof(m,w+1.1,d+1.2,h,rise,index)
    m.box((w*.28,d*.24,h+rise*.65),(1.05,1.12,3.5),mat('basalte'));m.box((w*.28,d*.24,h+rise*.65+1.8),(1.3,1.38,.22),mat('neige_givre'))
    m.detail=0
    # Menuiseries secondaires : pans de bois, volets et console de balcon.
    for y in (-d/2-.19,d/2+.19):
        for sx in (-1,1):
            m.beam((sx*w*.44,y,1.65),(sx*w*.08,y,3.55),.13,mat('bois_vieux'))
            m.beam((sx*w*.42,y,h+.3),(sx*w*.08,y,h+rise*.70),.11,mat('bois_vieux'))
            for dx in (-.67,.67):
                m.box((sx*w*.27+dx,y,2.58),(.29,.10,1.27),mat('bois_vieux'))
        for j in range(7):
            xx=(j-3)*w/7
            m.beam((xx,y,h+.12),(xx,y-.12,h-.30),.12,mat('bois_noir'))
    if index%2:
        m.box((0,-d/2-.65,3.88),(w*.65,1.3,.20),mat('bois_vieux'))
        m.beam((-w*.32,-d/2-1.22,4.9),(w*.32,-d/2-1.22,4.9),.12,mat('bois_noir'))
        for j in range(9):m.beam(((j-4)*w*.075,-d/2-1.22,3.92),((j-4)*w*.075,-d/2-1.22,4.9),.075,mat('bois_noir'))
        for sx in (-1,1):m.beam((sx*w*.25,-d/2,2.9),(sx*w*.25,-d/2-1.0,3.85),.16,mat('bois_noir'))
    for j in range(9):
        x=-w/2+j*w/8
        m.cylinder((x,-d/2-.6,h),(x+.03,-d/2-.6,h-.25-.15*(j%3)),.045,0,mat('neige_givre'),5)
    m.detail=2
    # Une aile basse au dos du bâtiment reste une partie de la même maison.
    aw=w*(.53 if index%2 else .72);ad=1.7+index%3*.55;az=2.6+index*.16;ax=(-.14 if index%2 else .1)*w
    m.box((ax,d/2+ad/2-.10,az/2),(aw,ad,az),mat('enduit'))
    for xx in (ax-aw/2,ax,ax+aw/2):m.box((xx,d/2+ad-.06,az/2),(.14,.17,az),mat('bois_vieux'))
    roof_points=[(ax-aw/2-.25,d/2-.28,az+1.6),(ax+aw/2+.25,d/2-.28,az+1.6),
                 (ax+aw/2+.25,d/2+ad+.22,az+.15),(ax-aw/2-.25,d/2+ad+.22,az+.15)]
    m.surface(roof_points,[(0,3,2,1)],mat('ardoise'))
    m.surface([(x,y,z+.07) for x,y,z in roof_points],[(0,3,2,1)],mat('neige_ombre'))
    # Usure cohérente des pièces jointives ; l'origine et les pieds restent au sol.
    m.verts=[(x+.055*math.sin(z*.61+index)*min(z,1)+.023*math.sin(y*.72+index)*min(z,1),
              y+.048*math.sin(z*.47+x*.58+index)*min(z,1),
              z+.035*math.sin(x*.91+y*.68+index)*min(z,1)+.10*math.sin(y*.72+index)*max(0,min(1,(z-h)/rise))) for x,y,z in m.verts]
    m.detail=2
    return m

def transform_into(dest,src,loc,angle=0):
    c,s=math.cos(angle),math.sin(angle)
    verts=[(loc[0]+x*c-y*s,loc[1]+x*s+y*c,loc[2]+z) for x,y,z in src.verts]
    for i,f in enumerate(src.faces):
        dest.detail=src.levels[i];dest.surface([verts[j] for j in f],[tuple(range(len(f)))],src.materials[src.indices[i]],src.uv[i])
    dest.detail=2

def spire(m,x,y,z,r,h):
    m.cylinder((x,y,z),(x,y,z+h),r,.06,mat('ardoise'),8)
    for i in range(8):
        a=i*math.tau/8
        m.beam((x+r*math.cos(a),y+r*math.sin(a),z),(x,y,z+h),.075 if r<1 else .12,mat('pierre_taille'))
        m.detail=0
        if r>.8:
            for t in (.22,.4,.58,.76):
                rr=r*(1-t);xx=x+rr*math.cos(a);yy=y+rr*math.sin(a)
                m.beam((xx,yy,z+h*t),(xx+.23*math.cos(a),yy+.23*math.sin(a),z+h*t+.25),.095,mat('calcaire'))
        m.detail=2
    m.cylinder((x,y,z+h-.1),(x,y,z+h+2),.10,.035,mat('fer_noir'),6)
    m.beam((x-.46,y,z+h+1.35),(x+.46,y,z+h+1.35),.075,mat('fer_noir'))

def tower(index=0):
    m=Mesh();r=3.6;h=16+index*2
    m.cylinder((0,0,0),(0,0,h),r,r,mat('basalte'),12)
    for z in (1.2,h*.5,h-2,h):m.cylinder((0,0,z),(0,0,z+.35),r+.22,r+.22,mat('pierre_taille'),12)
    for j in range(12):
        a=j*math.tau/12;xx=(r-.05)*math.sin(a);yy=-(r-.05)*math.cos(a)
        n=Mesh();window(n,0,-r-.03,h-5,.5,1.6,'pierre_taille','lumiere');transform_into(m,n,(0,0,0),a)
        m.box((xx,yy,h+.6),(1.1,1.1,1.2),mat('pierre_taille'),a)
        m.box((xx,yy,h+1.22),(1.17,1.17,.15),mat('neige_givre'),a)
    if index!=2:
        m.cylinder((0,0,h+.5),(0,0,h+3),r+1,r+.8,mat('bois_noir'),12)
        for j in range(12):
            a=j*math.tau/12
            n=Mesh();window(n,0,-r-.88,h+1,.45,.9,'bois_vieux','bois_noir')
            transform_into(m,n,(0,0,0),a)
            m.beam(((r-.2)*math.sin(a),-(r-.2)*math.cos(a),h-1.2),((r+.7)*math.sin(a),-(r+.7)*math.cos(a),h+.6),.28,mat('pierre_taille'))
        spire(m,0,0,h+3,r+1.3,8.5)
    return m

def wall():
    m=Mesh();masonry(m,0,0,0,10,2.7,12)
    m.box((0,0,11.85),(10,3.1,.45),mat('pierre_taille'))
    for x in (-4,-2,0,2,4):
        m.box((x,-.95,12.65),(1.15,1.25,1.6),mat('pierre_taille'))
        m.box((x,-.95,13.49),(1.22,1.32,.15),mat('neige_givre'))
    for x in (-3.3,3.3):
        m.box((x,-1.9,4.8),(1.0,1.25,9.6),mat('basalte'))
        m.surface([(x-.5,-2.52,9.6),(x+.5,-2.52,9.6),(x+.5,-1.35,11.3),(x-.5,-1.35,11.3)],[(0,1,2,3)],mat('neige_givre'))
    m.box((0,.0,12.12),(10,2.2,.1),mat('neige_givre'))
    return m

def gate():
    m=Mesh();w=5;h=8;pts=arch_points(w,h,20)
    for x in (-4.2,4.2):masonry(m,x,0,0,3.3,4.8,15,int(x+10))
    # Au-dessus de l'ogive : ouverture réelle traversante, sans cube derrière.
    for (a,b),(c,d) in zip(pts[1:-1],pts[2:]):
        for y in (-2.4,2.4):m.surface([(a,y,b),(c,y,d),(c,y,15),(a,y,15)],[(0,1,2,3)],mat('basalte'))
        m.surface([(a,-2.4,b),(a,2.4,b),(c,2.4,d),(c,-2.4,d)],[(0,1,2,3)],mat('pierre_taille'))
    for a,b in zip(pts,pts[1:]):m.beam((a[0],-2.48,a[1]),(b[0],-2.48,b[1]),.48,mat('calcaire'))
    for x in range(-5,6,2):
        m.box((x,-1.5,15.6),(1.05,1.6,1.4),mat('pierre_taille'));m.box((x,-1.5,16.35),(1.2,1.75,.15),mat('neige_givre'))
    # Herse relevée, espace libre en dessous.
    for j in range(-5,6):m.cylinder((j*.4,-1.2,5.5),(j*.4,-1.2,8.5),.035,.035,mat('fer_noir'),6)
    m.box((0,-1.2,7.7),(4.5,.12,.10),mat('fer_noir'))
    return m

def bridge():
    m=Mesh();width=7;span=14;radius=6
    # Arche plein cintre en voussoirs extrudés. Le tablier est à Z=0.
    for j in range(24):
        a=j*math.pi/24;b=(j+1)*math.pi/24
        y1=radius*math.cos(a);y2=radius*math.cos(b);z1=-8+radius*math.sin(a);z2=-8+radius*math.sin(b)
        for sx in (-1,1):
            x=sx*width/2;m.surface([(x,y1,z1),(x,y2,z2),(x,y2,0),(x,y1,0)],[(0,1,2,3)],mat('basalte'))
        m.surface([(-width/2,y1,z1),(width/2,y1,z1),(width/2,y2,z2),(-width/2,y2,z2)],[(0,1,2,3)],mat('pierre_taille'))
        m.detail=1
        for sx in (-1,1):m.beam((sx*(width/2+.05),y1,z1),(sx*(width/2+.05),y2,z2),.48,mat('calcaire'))
        m.detail=2
    for yy in (-6.5,6.5):m.box((0,yy,-10),(width+1,1.1,20),mat('basalte'))
    m.box((0,0,-.16),(width,span,.32),mat('sol_pave'))
    for sx in (-1,1):
        m.box((sx*3.2,0,.65),(.55,span,1.3),mat('pierre_taille'));m.box((sx*3.2,0,1.35),(.66,span,.15),mat('neige_givre'))
        for yy in (-6,0,6):m.box((sx*3.2,yy,1.05),(.9,.9,2.1),mat('pierre_taille'));m.box((sx*3.2,yy,2.16),(1,1,.15),mat('neige_givre'))
        m.box((sx*2.6,0,.035),(.7,span,.08),mat('neige_givre'))
    return m

def nave():
    m=Mesh();d=12
    # Nef haute et bas-côtés : une silhouette étagée, au lieu d'un bloc unique.
    m.box((0,0,12),(13.2,d,24),mat('basalte'))
    roof(m,14.1,d+.12,24,8.5,55)
    for side in (-1,1):
        m.box((side*8.6,0,5.3),(4,d,10.6),mat('basalte'))
        m.surface([(side*6.55,-6.06,15.1),(side*10.85,-6.06,10.75),
                   (side*10.85,6.06,10.75),(side*6.55,6.06,15.1)],[(0,1,2,3)],mat('ardoise'))
        for yy in (-4,0,4):
            n=Mesh();window(n,0,0,3.1,2.25,6.1,'calcaire','vitrail_bleu')
            transform_into(m,n,(side*10.64,yy,0),side*math.pi/2)
            n=Mesh();window(n,0,0,15.6,2.8,6.6,'calcaire','vitrail_bleu')
            transform_into(m,n,(side*6.66,yy,0),side*math.pi/2)
            m.box((side*6.7,yy,12.1),(.45,.46,24.2),mat('calcaire'))
            pinnacle(m,side*6.7,yy,24.2,.34,3)
        for zz in (.6,10.5):m.box((side*10.65,0,zz),(.32,d,.23),mat('calcaire'))
        for zz in (15,23.6):m.box((side*6.68,0,zz),(.4,d,.28),mat('calcaire'))
    return m


def pinnacle(m,x,y,z,r,h):
    # Flèche de pierre ajourée : noyau étroit, nervures et petites ouvertures.
    m.cylinder((x,y,z),(x,y,z+h),r*.74,.025,mat('pierre_taille'),8)
    for j in range(8):
        a=j*math.tau/8
        m.beam((x+r*math.cos(a),y+r*math.sin(a),z),(x,y,z+h),.055 if r<1 else .12,mat('calcaire'))
    m.detail=1
    for level in range(1,5):
        t=level/6;rr=r*(1-t)
        for j in range(4):
            a=j*math.pi/2;n=Mesh()
            window(n,0,-rr*.76,z+t*h,max(.10,rr*.48),h*.12,'calcaire','habitat_verre')
            transform_into(m,n,(x,y,0),a)
    m.detail=2


def facade():
    m=Mesh();masonry(m,0,0,0,20,2.6,30,47)
    m.surface([(-10,-1.3,30),(10,-1.3,30),(0,-1.3,40)],[(0,1,2)],mat('basalte'))
    for x in (-6.6,0,6.6):
        window(m,x,-1.42,.1,4.1 if x==0 else 3.4,9,'calcaire','vitrail_bleu')
        width=3.65 if x==0 else 2.95
        m.box((x,-1.62,3),(width,.18,5.8),mat('bois_noir'))
        m.detail=1
        for z in (1.1,3.0,4.9):
            m.box((x,-1.76,z),(width,.09,.16),mat('fer_noir'))
            for dx in (-width*.38,-width*.18,width*.18,width*.38):m.ico((x+dx,-1.82,z),(.055,.04,.055),mat('cuivre'))
        m.detail=2
        for k in range(3):
            pts=arch_points((4.1 if x==0 else 3.4)+.65*k,9+.5*k)
            for a,b in zip(pts,pts[1:]):m.beam((x+a[0],-1.6-k*.13,a[1]),(x+b[0],-1.6-k*.13,b[1]),.15,mat('calcaire'))
    # Rosace : verre, anneaux, rayons et douze petits lobes.
    m.cylinder((0,-1.34,21),(0,-1.44,21),4.4,4.4,mat('vitrail_bleu'),64)
    for r in (4.55,4.22,3.3,1.15):ring(m,(0,-1.55,21),r,.20,'calcaire',64)
    for j in range(12):
        a=j*math.tau/12;m.beam((math.cos(a)*1.1,-1.57,21+math.sin(a)*1.1),(math.cos(a)*4.25,-1.57,21+math.sin(a)*4.25),.13,mat('pierre_taille'))
        ring(m,(math.cos(a)*2.8,-1.59,21+math.sin(a)*2.8),.56,.085,'calcaire',16)
        if j%3==0:m.cylinder((math.cos(a)*2.8,-1.48,21+math.sin(a)*2.8),(math.cos(a)*2.8,-1.53,21+math.sin(a)*2.8),.48,.48,mat('vitrail_bleu'),16)
    window(m,0,-1.45,31,2.4,5,'calcaire','vitrail_bleu')
    for x in (-10,-8.8,-3.4,3.4,8.8,10):
        m.box((x,-1.75,15),(.65,1,30),mat('calcaire'))
        spire(m,x,-1.75,30,.55,5.8)
    for z in (10.2,11,27.5,30):m.box((0,-1.65,z),(20,.75,.26),mat('calcaire'))
    for j in range(11):
        x=-8.8+j*1.76;window(m,x,-1.62,11.55,1.24,3.25,'pierre_taille','bois_noir')
        m.detail=0
        m.ico((x,-1.95,12.45),(.22,.20,.72),mat('calcaire'),2);m.ico((x,-1.95,13.2),(.19,.19,.21),mat('calcaire'),2)
        m.detail=2
    for sx in (-1,1):
        for j in range(8):
            x=sx*(9-j*1.12);z=31+j*1.02
            m.ico((x,-1.65,z),(.19,.3,.32),mat('calcaire'),1)
    for sx in (-1,1):m.beam((sx*10,-1.62,30),(0,-1.62,40),.4,mat('calcaire'))
    # Gâbles et fleurons découpent les portails au lieu d'une grande dalle plane.
    for x in (-6.6,0,6.6):
        for sx in (-1,1):
            m.beam((x+sx*2.45,-2.13,8.4),(x,-2.13,13.6),.22,mat('calcaire'))
            m.beam((x+sx*2.7,-2.12,0),(x+sx*2.7,-2.12,9.0),.22,mat('pierre_taille'))
            spire(m,x+sx*2.7,-2.12,9,.30,3)
        ring(m,(x,-2.17,10.15),.57,.095,'calcaire',24)
        m.cylinder((x,-2.13,13.4),(x,-2.13,14.4),.10,.045,mat('calcaire'),6)
    for z in (16.4,28.5):
        for j in range(21):
            x=-9+j*.9
            m.box((x,-1.93,z),(.24,.45,.6),mat('pierre_taille'))
            m.box((x,-1.95,z+.34),(.32,.50,.12),mat('neige_givre'))
    for j in range(9):
        x=(j-4)*1.6
        window(m,x,-1.55,28.4,.65,1.35,'calcaire','bois_noir')
    spire(m,0,0,40,.45,3)
    m.verts=[(x*.80,y,z*.82) for x,y,z in m.verts]
    return m

def belfry():
    m=Mesh();m.box((0,0,16),(5.5,5.5,32),mat('basalte'))
    for a in (0,math.pi/2,math.pi,3*math.pi/2):
        n=Mesh()
        for x in (-1.15,1.15):window(n,x,-2.82,23.2,1.55,7,'calcaire','habitat_verre')
        window(n,0,-2.85,11.5,1.6,7.3,'calcaire','vitrail_bleu')
        transform_into(m,n,(0,0,0),a)
    for x in (-2.65,2.65):
        for y in (-2.65,2.65):
            m.box((x,y,16),(.38,.38,32),mat('calcaire'));pinnacle(m,x,y,32,.43,5)
    for z in (.6,9.3,22.4,31.8):m.box((0,0,z),(5.9,5.9,.34),mat('calcaire'))
    m.cylinder((0,0,32),(0,0,35.5),2.75,2.2,mat('basalte'),8)
    for a in (0,math.pi/2,math.pi,3*math.pi/2):
        n=Mesh();window(n,0,-2.37,32.3,1.45,2.7,'calcaire','habitat_verre');transform_into(m,n,(0,0,0),a)
    pinnacle(m,0,0,35.5,2.25,15.5)
    return m


def buttress():
    m=Mesh();m.box((0,0,10),(1.3,1.6,20),mat('basalte'))
    # Arc-boutant vers le mur, +X : deux nervures inclinées et leur remplissage.
    m.beam((0,0,16),(8.7,0,22),.7,mat('calcaire'));m.beam((0,0,19),(8.7,0,24),.55,mat('calcaire'))
    m.surface([(0,-.3,16),(8.7,-.3,22),(8.7,-.3,24),(0,-.3,19)],[(0,1,2,3)],mat('pierre_taille'))
    pinnacle(m,0,0,20,.58,5)
    for z in (2,8,14,19):m.box((0,0,z),(1.6,1.85,.28),mat('pierre_taille'))
    m.beam((0,0,19.35),(8.7,0,24.35),.19,mat('neige_givre'))
    m.detail=0
    for y in (-.85,.85):window(m,0,y,8,.64,7,'calcaire','basalte')
    m.detail=2
    return m

def pine(index):
    rng=random.Random(300+index);m=Mesh();h=11+index*2
    m.cylinder((0,0,0),(0,0,h),.28,.055,mat('bois_vieux'),8)
    # Rameaux irréguliers et tombants : une couronne poreuse, sans disques empilés.
    for j in range(10):
        z=1.3+j*(h-1.5)/10;r=(1-z/h)*3.8
        for k in range(6):
            a=k*math.tau/6+j*2.399+rng.uniform(-.25,.25)
            rr=r*rng.uniform(.65,1.17);zz=z+rng.uniform(-.42,.42)
            forward=Vector((math.cos(a),math.sin(a),0));across=Vector((-math.sin(a),math.cos(a),0))
            root=Vector((0,0,zz+.22));tip=forward*rr+Vector((0,0,zz-.75))
            left=forward*rr*.52+across*rr*.24+Vector((0,0,zz-.12))
            right=forward*rr*.64-across*rr*.23+Vector((0,0,zz-.28))
            crest=forward*rr*.45+Vector((0,0,zz+.28))
            under=forward*rr*.53+Vector((0,0,zz-.43))
            vs=[tuple(p) for p in (root,left,tip,right,crest,under)]
            def branch_uv(points):return [((Vector(p)-root).dot(forward)/rr,(Vector(p)-root).dot(across)/(rr*.56)+.5) for p in points]
            m.surface(vs,[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,5,1),(1,5,2),(2,5,3),(3,5,0)],mat('aiguilles_sombres'),branch_uv(vs))
            if rng.random()>.18:
                # La neige occupe le dessus ; les aiguilles restent visibles sous les pointes.
                pts=[root*.9+crest*.1,left*.84+crest*.16,tip*.8+crest*.2,right*.86+crest*.14,crest]
                pts=[tuple(p+Vector((0,0,.055))) for p in pts]
                m.surface(pts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mat('neige_rameaux'),branch_uv(pts))
            m.detail=0
            if j<6:
                for side in (-1,1):
                    start=forward*rr*.55+Vector((0,0,zz-.13))
                    end=forward*rr*.88+across*rr*.33*side+Vector((0,0,zz-.68))
                    pts=[tuple(start),tuple(end),tuple(tip)]
                    m.surface(pts,[(0,1,2)],mat('aiguilles_sombres'),branch_uv(pts))
            m.detail=2
    return m

def crag(index):
    rng=random.Random(index+918);m=Mesh();n=32;rings=18;vs=[]
    for j in range(rings):
        z=j/(rings-1)*20
        for i in range(n):
            a=i*math.tau/n;t=j/(rings-1)
            # Pied large, bancs inclinés et décrochements : aucune colonne cylindrique.
            r=(1.65-t*.98)*(1+.25*math.sin(i*2.1+index)+rng.uniform(-.12,.12))
            r+=.19*math.sin(j*2.5+index)+.10*math.sin(i*1.3+j*.8)
            vs.append((math.cos(a)*5*r+t*1.9+math.sin(j*.7+index)*.8,
                       math.sin(a)*4*r+math.cos(j*.8+index)*.7,z+rng.uniform(-.75,.75)+math.sin(i*.8+index)*.7))
    for j in range(rings-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            material=('roche_noire','roche_claire','roche_granite','roche_ocre')[(j//3+index)%4]
            m.surface([vs[a],vs[b],vs[c],vs[d]],[(0,1,2),(0,2,3)],mat(material))
    top=vs[-n:];center=tuple(sum(p[k] for p in top)/n for k in range(3))
    for i in range(n):m.surface([center,top[i],top[(i+1)%n]],[(0,1,2)],mat('neige_givre' if i%5<3 else 'roche_granite'))
    for j in (3,6,9):
        for i in range(index%3,n,3):
            a=vs[j*n+i];b=vs[j*n+(i+1)%n];c=((a[0]+b[0])*.46,(a[1]+b[1])*.46,a[2]+1.1)
            m.surface([a,b,c],[(0,1,2)],mat('neige_givre'))
    return m

def relief_noise(x,y,seed):
    """Bruit continu déterministe, identique pour les sommets et pour la texture."""
    ix=np.floor(x);iy=np.floor(y);fx=x-ix;fy=y-iy
    fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    def h(a,b):
        q=np.sin(a*127.1+b*311.7+seed*91.17)*43758.5453
        return q-np.floor(q)
    return (h(ix,iy)*(1-fx)+h(ix+1,iy)*fx)*(1-fy)+(h(ix,iy+1)*(1-fx)+h(ix+1,iy+1)*fx)*fy


def mountain_field(x,y,index):
    # Plusieurs arêtes asymétriques, puis ravinement à plusieurs échelles.
    # La neige est calculée sur ce même relief, sans coordonnées radiales.
    angle=index*.42;c=math.cos(angle);s=math.sin(angle)
    u=x*c-y*s;v=x*s+y*c
    warp=(relief_noise(x*3,y*3,index)-.5)*.14
    peaks=[]
    for px,py,h,ax,ay in [(-.13,.12,194,.74,.87),(.29,-.08,146,.61,.70),(-.39,-.24,112,.52,.69),(.24,.49,120,.58,.55)]:
        dist=abs((u-px+warp)/ax)+abs((v-py-warp)/ay)
        peaks.append(h*np.maximum(0,1-dist)**1.04)
    height=np.maximum.reduce(peaks)
    # Ravines rayonnantes irrégulières : les flancs se creusent entre les arêtes.
    du=u+.13;dv=v-.12;a=np.arctan2(dv,du);r=np.hypot(du,dv)
    channels=(.5+.5*np.sin(a*9+relief_noise(u*7,v*7,index)*2.2+np.sin(r*11)*.5))**1.7
    height*=1-.30*channels*np.clip(r*6,0,1)
    erosion=np.zeros_like(np.asarray(x,dtype=float))
    for frequency,amount in ((4,21),(10,12),(25,5),(61,2.1)):
        ridge=1-abs(relief_noise(u*frequency,v*frequency,index)*2-1)
        erosion+=(ridge-.55)*amount
    mask=np.clip(height/35,0,1)*np.clip((1-np.maximum(abs(x),abs(y)))*12,0,1)
    return np.maximum(0,height+erosion*mask)

def mountain(index):
    m=Mesh();n=144;vs=[]
    for j in range(n+1):
        for i in range(n+1):
            x=-1+2*i/n;y=-1+2*j/n;vs.append((x*110,y*100,float(mountain_field(x,y,index))))
    # Masque neige/roche continu : évite un damier de couleurs par triangle.
    size=1536;axis=np.linspace(-1,1,size);xx,yy=np.meshgrid(axis,axis)
    heights=mountain_field(xx,yy,index)
    dy,dx=np.gradient(heights,200/size,220/size);slope=np.hypot(dx,dy)
    grain=relief_noise(xx*95,yy*95,index)-.5
    drift=relief_noise(xx*8,yy*13,index+12)-.5
    cover=np.clip((3.2-slope)*1.3+drift*.75+grain*.20+dy*.35,0,1)
    cover=np.maximum(cover,np.clip((35-heights)/25,0,1))
    cold=np.array((.78,.84,.88))
    strata=.5+.5*np.sin(heights*.32+xx*21+relief_noise(xx*6,yy*7,index)*8)
    oxidised=np.clip((relief_noise(xx*9,yy*12,index+17)-.48)*3,0,1)
    granite=np.array((.29,.30,.28));schist=np.array((.11,.14,.17));ochre=np.array((.29,.205,.125))
    stone=schist[None,None,:]*(1-strata[...,None])+granite[None,None,:]*strata[...,None]
    stone=stone*(1-oxidised[...,None]*.65)+ochre*oxidised[...,None]*.65
    fractures=np.clip((abs(np.sin(xx*150+yy*87+grain*9))-.84)*7,0,1)
    stone*=np.clip(.77+grain[...,None]*.6-fractures[...,None]*.32,.32,1.25)
    rgb=stone*(1-cover[...,None])+cold[None,None,:]*cover[...,None]
    # Image.save écrit ces pixels directement : encoder explicitement la couleur sRGB.
    rgb=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    image=bpy.data.images.new('montagne_'+str(index),width=size,height=size,alpha=True);image.pixels.foreach_set(np.concatenate((rgb,np.ones((size,size,1))),axis=2).astype(np.float32).ravel())
    image.filepath_raw=str(TEX/('montagne_'+str(index)+'_BaseColor.png'));image.file_format='PNG';image.save();bpy.data.images.remove(image)
    fine=(relief_noise(xx*180,yy*220,index)*.34+relief_noise(xx*470,yy*390,index+9)*.11)*(1-cover)
    gy,gx=np.gradient(fine,200/size,220/size)
    normals=np.stack((-gx,-gy,np.ones_like(gx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
    image=bpy.data.images.new('montagne_'+str(index)+'_Normal',width=size,height=size,alpha=True)
    image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(np.concatenate((normals*.5+.5,np.ones((size,size,1))),axis=2).astype(np.float32).ravel())
    image.filepath_raw=str(TEX/('montagne_'+str(index)+'_Normal.png'));image.file_format='PNG';image.save();bpy.data.images.remove(image)
    rock=mat('montagne_'+str(index))
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i
            for ids in ((a,a+1,a+n+2),(a,a+n+2,a+n+1)):
                v=[Vector(vs[k]) for k in ids];normal=(v[1]-v[0]).cross(v[2]-v[0]).normalized();z=sum(p.z for p in v)/3
                m.surface([tuple(p) for p in v],[(0,1,2)],rock,[(p.x/220+.5,p.y/200+.5) for p in v])
    return m

def accessory(kind):
    m=Mesh()
    if kind=='torche':
        m.cylinder((0,0,0),(0,0,2.7),.08,.065,mat('bois_noir'),8)
        m.cylinder((0,0,2.35),(0,0,2.85),.12,.25,mat('fer_noir'),8)
        m.ico((0,0,3.1),(.18,.18,.48),mat('lumiere'),2)
    elif kind=='banniere':
        m.cylinder((0,0,0),(0,0,7.5),.075,.055,mat('fer_noir'),8)
        m.beam((-.1,0,7),(2.4,0,7),.065,mat('fer_noir'))
        for j in range(16):
            for i in range(8):
                def p(ii,jj):
                    x=ii*2.2/8;z=7-jj*3.8/16;y=.20*math.sin(x*3+z*2)*(7-z)/3.8
                    return x,y,z
                m.surface([p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1)],[(0,1,2,3)],mat('tissu_bordeaux'))
        m.box((1.1,-.27,5.3),(.11,.04,2),mat('cuivre'));m.box((1.1,-.27,5.55),(1,.04,.11),mat('cuivre'))
    elif kind=='garde':
        # Silhouette de faction : manteau, casque, bras et hampe distincts.
        for x in (-.2,.2):m.cylinder((x,0,.15),(x,0,1.0),.14,.14,mat('fer_noir'),8)
        m.ico((0,0,1.35),(.43,.24,.60),mat('fer_noir'),2)
        m.cylinder((0,.07,.25),(0,.05,1.85),.60,.30,mat('tissu_bordeaux'),10)
        m.ico((0,0,2.02),(.25,.24,.29),mat('pierre_taille'),2)
        m.box((0,-.225,2.01),(.32,.05,.065),mat('fer_noir'))
        m.beam((.3,0,1.6),(.65,-.2,1.1),.19,mat('fer_noir'))
        m.cylinder((.7,-.2,0),(.7,-.2,3.3),.038,.038,mat('bois_vieux'),6)
        m.cylinder((.7,-.2,3.3),(.7,-.2,3.7),.13,0,mat('pierre_taille'),6)
    elif kind=='escalier':
        for j in range(20):
            height=(j+1)*.3
            m.box((0,j*.46,height/2),(14,.48,height),mat('pierre_taille'))
            m.box((0,j*.46-.18,height+.025),(14,.11,.05),mat('calcaire'))
            for sx in (-1,1):m.box((sx*6.5,j*.46,height+.04),(.7,.47,.08),mat('neige_givre'))
        for sx in (-1,1):m.beam((sx*7,0,1),(sx*7,9.2,7),.35,mat('calcaire'))
    elif kind=='paves':
        for j in range(12):
            for i in range(6):m.box(((i-2.5)*.8+(j%2)*.25,(j-5.5)*.66,0),(.75,.61,.14),mat('sol_pave'))
    return m


def dormer():
    m=Mesh()
    m.box((0,.2,.65),(1.8,1.4,1.3),mat('bois_noir'))
    m.surface([(-.9,-.51,1.3),(.9,-.51,1.3),(0,-.51,2.65)],[(0,1,2)],mat('enduit'))
    window(m,0,-.55,.15,1.05,1.3,'bois_vieux','lumiere')
    roof(m,2.15,1.8,1.3,1.5,78)
    return m


def street_life():
    """Petit ensemble de stockage : bois fendu, tonneaux cerclés et caisse."""
    m=Mesh()
    for j in range(3):
        for i in range(4-j):
            x=i*.29+j*.14-.6;z=.15+j*.25
            m.cylinder((x,-.45,z),(x,.55,z),.145,.13,mat('bois_vieux'),8)
    for x,y in ((1.2,0),(1.8,.65)):
        for k in range(6):
            z=k*.21;r=.37+.09*math.sin(k*math.pi/5)
            m.cylinder((x,y,z),(x,y,z+.21),r,r,mat('bois_vieux'),12)
        for z in (.12,.38,.96,1.15):m.cylinder((x,y,z),(x,y,z+.055),.445,.445,mat('fer_noir'),12)
    m.box((-.6,1,.46),(.95,.9,.92),mat('bois_vieux'))
    for z in (.10,.8):m.box((-.6,.53,z),(.98,.08,.12),mat('bois_noir'))
    return m

def jobs(tex):
    global TEX;TEX=tex
    result=[(f'maison_gothique_{i}',lambda j=i:house(j),'batiment') for i in range(6)]
    result += [(f'tour_{i}',lambda j=i:tower(j),'repere') for i in range(3)]
    result += [('rempart_10m',wall,'module'),('porte_ogive',gate,'module'),('pont_arche_14m',bridge,'module'),('cathedrale_nef_12m',nave,'module'),('cathedrale_facade',facade,'module'),('cathedrale_clocher',belfry,'module'),('arc_boutant',buttress,'module')]
    result += [(f'sapin_neige_{i}',lambda j=i:pine(j),'arbre') for i in range(3)]
    result += [(f'falaise_{i}',lambda j=i:crag(j),'roche') for i in range(4)]
    result += [(f'montagne_{i}',lambda j=i:mountain(j),'relief') for i in range(3)]
    result += [(k,lambda j=k:accessory(j),'accessoire') for k in ('torche','banniere','garde','escalier','paves')]
    result += [('lucarne_gothique',dormer,'module'),('reserve_bois_tonneaux',street_life,'accessoire')]
    from local3d.citadelle import habitat
    result += habitat.jobs()
    return result
