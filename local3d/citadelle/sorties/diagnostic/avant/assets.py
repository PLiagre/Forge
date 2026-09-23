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
    m=material(n,TEX)
    if n in ('lumiere','vitrail_ambre','vitrail_bleu'):
        bs=m.node_tree.nodes['Principled BSDF']
        bs.inputs['Emission Color'].default_value=(1,.32,.045,1) if n!='vitrail_bleu' else (.05,.21,.35,1)
        bs.inputs['Emission Strength'].default_value=2.8 if n=='lumiere' else 1.35
    return m

def arch_points(w,h,n=12):
    # Deux arcs rejoignent une pointe ; base verticale puis ogive.
    r=w*.5;spring=h-r*1.25
    return [(-r,0),(-r,spring)]+[(-r+2*r*t/n,spring+1.25*r*math.sin(math.pi*t/n)**.72) for t in range(1,n)]+[(r,spring),(r,0)]

def window(m,x,y,z,w,h,stone='calcaire',glass='vitrail_ambre'):
    pts=arch_points(w,h);m.surface([(x+a,y,z+b) for a,b in pts],[tuple(range(len(pts)))],mat(glass))
    for a,b in zip(pts,pts[1:]+pts[:1]):m.beam((x+a[0],y-.055,z+a[1]),(x+b[0],y-.055,z+b[1]),.16,mat(stone))
    m.detail=1
    for dx in (-w/6,w/6):m.beam((x+dx,y-.09,z+.1),(x+dx,y-.09,z+h-.22),.075,mat('fer_noir'))
    m.beam((x-w*.45,y-.1,z+h*.40),(x+w*.45,y-.1,z+h*.4),.085,mat('fer_noir'))
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

def roof(m,w,d,z,rise,seed=0):
    rng=random.Random(seed)
    for side in (-1,1):
        m.surface([(0,-d/2,z+rise),(side*w/2,-d/2,z),(side*w/2,d/2,z),(0,d/2,z+rise)],[(0,1,2,3)],mat('ardoise'))
        rows=max(4,int(rise/.44));cols=max(4,int(d/.85))
        for j in range(rows):
            f=j/rows;f2=(j+.83)/rows
            for i in range(cols):
                yy=-d/2+(i+.01)*d/cols;yy2=yy+d/cols*.98
                # Bande neigeuse irrégulière sur les rangées d'ardoise.
                if rng.random()<.96:
                    m.surface([(side*w*.5*f,yy,z+rise*(1-f)+.055),(side*w*.5*f2,yy,z+rise*(1-f2)+.055),(side*w*.5*f2,yy2,z+rise*(1-f2)+.055),(side*w*.5*f,yy2,z+rise*(1-f)+.055)],[(0,1,2,3)],mat('neige_givre'))
        m.detail=1
        for yy in (-d/2,d/2):m.beam((0,yy,z+rise+.08),(side*w/2,yy,z+.08),.21,mat('bois_noir'))
        m.detail=2
    m.beam((0,-d/2-.15,z+rise+.14),(0,d/2+.15,z+rise+.14),.24,mat('neige_givre'))

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
    for j in range(9):
        x=-w/2+j*w/8
        m.cylinder((x,-d/2-.6,h),(x+.03,-d/2-.6,h-.25-.15*(j%3)),.045,0,mat('neige_givre'),5)
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
    for i in (0,1,3,4,6):
        a=i*math.tau/8;b=(i+1)*math.tau/8
        m.surface([(x+r*math.cos(a),y+r*math.sin(a),z+.07),(x+r*math.cos(b),y+r*math.sin(b),z+.07),(x,y,z+h+.04)],[(0,1,2)],mat('neige_ombre'))
    for j in range(10):
        zz=z+j*h/11;rr=r*(1-j/11)
        m.cylinder((x,y,zz),(x,y,zz+.14),rr+.08,rr+.055,mat('neige_givre'),8)
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
    m=Mesh();w=20;d=12;h=25
    m.box((0,0,h/2),(w,d,h),mat('basalte'))
    roof(m,w+1,d+.15,h,13,55)
    for side in (-1,1):
        for yy in (-4,4):
            n=Mesh();window(n,0,0,7,3.1,13);transform_into(m,n,(side*10.12,yy,0),side*math.pi/2)
            m.box((side*10.25,yy,14),(.6,.5,28),mat('pierre_taille'))
            spire(m,side*10.25,yy,28,.6,4.5)
        for zz in (1,6,24):m.box((side*10.1,0,zz),(.55,d,.3),mat('calcaire'))
    return m

def facade():
    m=Mesh();masonry(m,0,0,0,20,2.6,30,47)
    m.surface([(-10,-1.3,30),(10,-1.3,30),(0,-1.3,40)],[(0,1,2)],mat('basalte'))
    for x in (-6.6,0,6.6):
        window(m,x,-1.42,.1,4.1 if x==0 else 3.4,9)
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
    m.cylinder((0,-1.34,21),(0,-1.44,21),4.4,4.4,mat('vitrail_ambre'),64)
    for r in (4.55,4.22,3.3,1.15):ring(m,(0,-1.55,21),r,.20,'calcaire',64)
    for j in range(12):
        a=j*math.tau/12;m.beam((math.cos(a)*1.1,-1.57,21+math.sin(a)*1.1),(math.cos(a)*4.25,-1.57,21+math.sin(a)*4.25),.13,mat('pierre_taille'))
        ring(m,(math.cos(a)*2.8,-1.59,21+math.sin(a)*2.8),.56,.085,'calcaire',16)
        if j%3==0:m.cylinder((math.cos(a)*2.8,-1.48,21+math.sin(a)*2.8),(math.cos(a)*2.8,-1.53,21+math.sin(a)*2.8),.48,.48,mat('vitrail_bleu'),16)
    window(m,0,-1.45,31,2.4,5)
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
    spire(m,0,0,40,.45,3)
    return m

def belfry():
    m=Mesh();m.box((0,0,19),(5.5,5.5,38),mat('basalte'))
    for a in (0,math.pi/2,math.pi,3*math.pi/2):
        n=Mesh()
        for x in (-1.2,1.2):window(n,x,-2.82,25,1.6,9,'calcaire','bois_noir')
        window(n,0,-2.85,10,1.4,7)
        transform_into(m,n,(0,0,0),a)
    for x in (-2.7,2.7):
        for y in (-2.7,2.7):
            m.box((x,y,19),(.45,.45,38),mat('calcaire'));spire(m,x,y,38,.53,8)
    for z in (1,9,23,37.5):m.box((0,0,z),(5.95,5.95,.5),mat('calcaire'))
    spire(m,0,0,38,3.1,20)
    return m

def buttress():
    m=Mesh();m.box((0,0,10),(1.3,1.6,20),mat('basalte'))
    # Arc-boutant vers le mur, +X : deux nervures inclinées et leur remplissage.
    m.beam((0,0,16),(5.5,0,22),.7,mat('calcaire'));m.beam((0,0,19),(5.5,0,24),.55,mat('calcaire'))
    m.surface([(0,-.3,16),(5.5,-.3,22),(5.5,-.3,24),(0,-.3,19)],[(0,1,2,3)],mat('pierre_taille'))
    spire(m,0,0,20,.85,7)
    return m

def pine(index):
    rng=random.Random(300+index);m=Mesh();h=11+index*2
    m.cylinder((0,0,0),(0,0,h),.28,.055,mat('bois_vieux'),8)
    # Branches radiales distinctes, et neige déposée sur leur face supérieure.
    for j in range(12):
        z=1.5+j*(h-2)/12;r=(1-z/h)*3.6
        for k in range(7):
            a=k*math.tau/7+j*.62;rr=r*rng.uniform(.8,1.1);end=(math.cos(a)*rr,math.sin(a)*rr,z-.7)
            side=Vector((-math.sin(a),math.cos(a),0))*.42*rr
            v=[(0,0,z+.35),tuple(Vector(end)+side*.15),(end[0],end[1],z-.8),tuple(Vector(end)-side*.15)]
            mid=Vector(end)*.66;mid.z=z-.25
            v=[(0,0,z+.42),tuple(mid+side),end,tuple(mid-side)]
            m.surface(v,[(0,1,2,3)],mat('aiguilles_sombres'))
            m.surface([(x*.92,y*.92,zz+.09) for x,y,zz in v],[(0,1,2,3)],mat('neige_givre' if j%3 else 'neige_ombre'))
            m.detail=0;m.beam((0,0,z),end,.055,mat('bois_vieux'));m.detail=2
    return m

def crag(index):
    rng=random.Random(index+918);m=Mesh();n=12;rings=7;vs=[]
    for j in range(rings):
        z=j/(rings-1)*20
        for i in range(n):
            a=i*math.tau/n;r=(1.1-abs(j/(rings-1)-.48)*.62)*(1+.18*math.sin(i*2.7+index)+rng.uniform(-.12,.12))
            vs.append((math.cos(a)*5*r+math.sin(z*.16+index)*1.2,math.sin(a)*4*r,z+rng.uniform(-1.3,1.3)))
    for j in range(rings-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            m.surface([vs[a],vs[b],vs[c],vs[d]],[(0,1,2),(0,2,3)],mat('roche_noire' if i%3 else 'roche_claire'))
    top=vs[-n:];m.surface(top,[tuple(range(n))],mat('neige_givre'))
    for j in (2,4):
        for i in range(0,n,3):
            a=vs[j*n+i];b=vs[j*n+(i+1)%n];c=((a[0]+b[0])*.46,(a[1]+b[1])*.46,a[2]+1.1)
            m.surface([a,b,c],[(0,1,2)],mat('neige_givre'))
    return m

def mountain_field(x,y,index):
    r=np.hypot(x*.9,y);a=np.arctan2(y,x)
    peak=np.maximum(0,1-r)**1.3
    ridges=1-.34*(.5+.5*np.sin(a*7+index+np.sin(r*8)))*np.minimum(1,r*5)
    fine=.007*np.sin(x*87+y*68+index)+.011*np.sin(x*41-y*29)*np.sin(y*37)
    return np.maximum(0,peak*ridges+fine*np.maximum(0,1-r))*205

def mountain(index):
    m=Mesh();n=92;vs=[]
    for j in range(n+1):
        for i in range(n+1):
            x=-1+2*i/n;y=-1+2*j/n;vs.append((x*110,y*100,float(mountain_field(x,y,index))))
    # Masque neige/roche continu : évite un damier de couleurs par triangle.
    size=512;axis=np.linspace(-1,1,size);xx,yy=np.meshgrid(axis,axis)
    rr=np.hypot(xx*.9,yy);aa=np.arctan2(yy,xx)
    heights=mountain_field(xx,yy,index)
    dy,dx=np.gradient(heights,200/size,220/size);slope=np.hypot(dx,dy)
    grain=(np.sin(xx*93+yy*21)*np.sin(yy*117)+np.sin(xx*29-yy*41))*.07
    cover=np.clip((3.7-slope)*.62+grain,0,1)
    couloirs=np.clip((np.sin(aa*7+index+np.sin(rr*8))+.2)*.85,0,1)*np.clip(heights/25,0,1)
    cover=np.maximum(cover,couloirs)
    cover=np.maximum(cover,np.clip((heights-145)/55,0,.88))
    cold=np.array((.67,.76,.81));stone=np.array((.18,.22,.25));rgb=stone[None,None,:]*(1-cover[...,None])+cold[None,None,:]*cover[...,None]
    rgb*=np.clip(.88+grain[...,None],.65,1.2)
    # Blender écrit les pixels linéaires dans un PNG sRGB ; Unity lit la même texture.
    image=bpy.data.images.new('montagne_'+str(index),width=size,height=size,alpha=True);image.pixels.foreach_set(np.concatenate((rgb,np.ones((size,size,1))),axis=2).astype(np.float32).ravel())
    image.filepath_raw=str(TEX/('montagne_'+str(index)+'_BaseColor.png'));image.file_format='PNG';image.save();bpy.data.images.remove(image)
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
        for j in range(20):m.box((0,j*.46,.15+j*.3),(14,.48,.3+j*.6),mat('pierre_taille'))
        for sx in (-1,1):m.beam((sx*7,0,1),(sx*7,9.2,7),.35,mat('calcaire'))
    elif kind=='paves':
        for j in range(12):
            for i in range(6):m.box(((i-2.5)*.8+(j%2)*.25,(j-5.5)*.66,0),(.75,.61,.14),mat('sol_pave'))
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
    return result
