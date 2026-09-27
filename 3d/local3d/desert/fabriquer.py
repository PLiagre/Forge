"""Fabrique un kit partagé et deux compositions de ksar dans Blender.

Même chaîne que la citadelle : bibliothèque de modules à trois niveaux de
détail, puis scène par disposition, manifeste en coordonnées Blender, paysage
FBX, cadrages et rendus Cycles.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.desert import assets, paysage, urbanisme
from local3d.desert.cameras import CAMERAS
from local3d.desert.paysage import PLATEAU, Z
from local3d.atelier_v2.geometrie import Mesh,MATS,export_fbx,tri_count
from local3d.alpin.fabriquer import reset,coll,move,matters,write
OUT=ROOT/'local3d/desert/sorties';LIB=OUT/'bibliotheque';TEX=OUT/'textures'
RECIPE=json.loads((Path(__file__).parent/'recette.json').read_text(encoding='utf-8'))


def clean_mesh(o):
    # Les faces d'aire nulle disparaissent à l'import Unity : les retirer ici garde
    # le catalogue et le FBX strictement comparables.
    bm=bmesh.new();bm.from_mesh(o.data)
    if o.name.startswith(('dune_','butte_','Terrain_')):bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    dead=[f for f in bm.faces if f.calc_area()<1e-9]
    if dead:bmesh.ops.delete(bm,geom=dead,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(o.data);bm.free();o.data.update()


def library():
    reset();LIB.mkdir(parents=True,exist_ok=True);records=[];objects=[]
    for name,builder,kind in assets.jobs(TEX):
        source=Path(__file__).parent/'sources'/(name+'.blend');wanted=[name+'_LOD'+str(i) for i in range(3)]
        if source.exists():
            with bpy.data.libraries.load(str(source),link=False) as (src,dst):
                if not set(wanted)<=set(src.objects):raise ValueError('Source sans ses trois LOD : '+name)
                dst.objects=wanted
            lods=dst.objects
            for o in lods:
                bpy.context.collection.objects.link(o);o.hide_render=False;o.hide_set(False)
                if o.location.length>.0001 or any(abs(s-1)>.0001 for s in o.scale) or any(abs(a)>.0001 for a in o.rotation_euler):raise ValueError('Transformations non appliquées : '+name)
                for slot in o.material_slots:
                    if not slot.material:raise ValueError('Matériau absent : '+name)
                    key=slot.material.name.split('.')[0]
                    if key in MATS:slot.material=MATS[key]
                    else:
                        slot.material.name=key;MATS[key]=slot.material
                        assets.configure_material(slot.material,key)
        else:
            mesh=builder();lods=[mesh.object(name+'_LOD'+str(i),i) for i in range(3)]
        for o in lods:
            # Un petit chanfrein capte la lumière rasante sur les arêtes des volumes de terre.
            if not source.exists() and o.name.endswith('_LOD0') and kind in ('batiment','repere','module'):
                bpy.context.view_layer.objects.active=o
                bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update();weight=bm.edges.layers.float.new('bevel_weight_edge')
                for edge in bm.edges:
                    faces=list(edge.link_faces)
                    edge[weight]=1 if len(faces)==2 and edge.calc_length()>.3 and min(f.calc_area() for f in faces)>.08 and faces[0].normal.dot(faces[1].normal)<.86 else 0
                bm.to_mesh(o.data);bm.free()
                bevel=o.modifiers.new('Arêtes adoucies de la terre crue','BEVEL')
                bevel.width=.04;bevel.segments=1;bevel.limit_method='WEIGHT'
                bpy.ops.object.modifier_apply(modifier=bevel.name)
            clean_mesh(o)
            o.asset_mark();o.asset_data.description='Ksar du désert • module en mètres • '+name
            if name.startswith(('dune_','butte_')):
                for p in o.data.polygons:p.use_smooth=True
        counts=[tri_count(o) for o in lods]
        if not counts[0]>=counts[1]>=counts[2]>0:raise ValueError('LOD invalides : '+name)
        vs=np.array([v.co for v in lods[0].data.vertices]);records.append({'id':name,'kind':kind,'triangles':counts,'bounds_min':vs.min(axis=0).tolist(),'bounds_max':vs.max(axis=0).tolist()})
        export_fbx(LIB/(name+'.fbx'),lods);objects.extend(lods)
    bpy.data.libraries.write(str(LIB/'Kit_Desert.blend'),set(objects),path_remap='RELATIVE',fake_user=True,compress=True)
    write(LIB/'catalogue.json',{'schema':3,'assets':records,'materials':matters(objects)})
    print('KIT_DESERT_OK',len(records),flush=True)


def edition(name):
    reset();path=Path(__file__).parent/'sources'/(name+'.blend')
    if path.exists():raise ValueError('Source déjà présente ; aucune retouche écrasée : '+str(path))
    wanted=[name+'_LOD'+str(i) for i in range(3)]
    with bpy.data.libraries.load(str(LIB/'Kit_Desert.blend'),link=False) as (src,dst):
        if not set(wanted)<=set(src.objects):raise ValueError('Module inconnu : '+name)
        dst.objects=wanted
    for i,o in enumerate(dst.objects):
        coll('LOD '+str(i)).objects.link(o);o.hide_render=i>0;o.hide_set(i>0)
    o=dst.objects[0];o.select_set(True);bpy.context.view_layer.objects.active=o
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_location=(0,0,5);ar.spaces.active.region_3d.view_distance=25;ar.spaces.active.shading.type='MATERIAL'
    bpy.ops.file.pack_all();path.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)


def terrain_height(x,y,seed):
    return paysage.field(x,y,seed)


def free_spot(rng,center,radius,seed,clearance,tries=400):
    """Premier emplacement libre autour d'un point : hors des rues, seuils, jardins et de l'eau."""
    for _ in range(tries):
        a=rng.uniform(0,math.tau);r=radius*math.sqrt(rng.random())
        x=center[0]+math.cos(a)*r;y=center[1]+math.sin(a)*r
        if paysage.distance_to_routes(x,y,seed)<clearance or paysage.in_pool(x,y,seed,clearance):continue
        if paysage.blocked_by_use(x,y,seed):continue
        return x,y
    raise ValueError('Aucun emplacement libre près de '+str(center))


def scene(name,seed,quick=False,no_render=False,views=None):
    reset();assets.TEX=TEX;rng=random.Random(seed);alt=seed!=RECIPE['dispositions'][0]['seed']
    layout=paysage.plan(seed)
    path=OUT/'villages'/name;path.mkdir(parents=True,exist_ok=True);(path/'renders').mkdir(exist_ok=True)
    catalogue=json.loads((LIB/'catalogue.json').read_text(encoding='utf-8'));records={a['id']:a for a in catalogue['assets']}
    with bpy.data.libraries.load(str(LIB/'Kit_Desert.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.endswith('_LOD0')]
    prototypes={o.name[:-5]:o for o in dst.objects}
    for o in prototypes.values():
        for slot in o.material_slots:
            if slot.material:MATS[slot.material.name]=slot.material
    arch=coll('01 • Ksar et bourg');nature=coll('02 • Grès et palmeraie');props=coll('03 • Vie et lumières');land=coll('04 • Relief et chemins');studio=coll('05 • Atmosphère')
    instances=[];torches=[];banners=[];smokes=[];static=[]
    def place(asset,x,y,z,rotation=0,scale=(1,1,1),category=arch):
        o=prototypes[asset].copy();category.objects.link(o);o.name=asset+'__'+str(len(instances));o.location=(x,y,z);o.rotation_euler.z=math.radians(rotation);o.scale=scale;o['asset_id']=asset
        instances.append({'id':o.name,'asset':asset,'position':[float(x),float(y),float(z)],'rotation':float(rotation),'scale':list(scale),'category':category.name[:2]})
        return o
    def lantern(x,y,z):
        o=place('lanterne',x,y,z,category=props);torches.append({'position':[x,y,z+3.1],'id':o.name})
        light=bpy.data.lights.new('Feu de lanterne','POINT');light.energy=180;light.color=(1,.52,.18);light.shadow_soft_size=.25
        l=bpy.data.objects.new('Lueur '+o.name,light);studio.objects.link(l);l.location=(x,y,z+3.1)
        light.driver_add('energy').driver.expression='180+18*sin(frame*.63+'+str(len(torches))+')+10*sin(frame*1.3)'
    def maison(kind,plan):
        x,y,z=plan['position'];scale=urbanisme.echelle(plan,kind)
        o=place('maison_pise_'+str(kind),x,y,z,plan['rotation'],scale)
        o.color=(*plan['color'],1);instances[-1]['color']=list(plan['color']);instances[-1]['urban_group']=plan['group']
        return o
    def banner(x,y,z,rotation=0):
        o=place('etendard',x,y,z,rotation,category=props);banners.append(o.name)
        # Déplacement géométrique de la toile, attachée en haut et à la hampe.
        o.data=o.data.copy();o.shape_key_add(name='Repos');key=o.shape_key_add(name='Rafale')
        for v in key.data:
            p=v.co
            if p.x>.08 and 3.15<p.z<7.05:p.y+=.42*math.sin(p.x*2.7+p.z*1.8)*min(1,p.x)*max(0,(7-p.z)/3.8)
        key.driver_add('value').driver.expression='.5+.5*sin(frame*.14+'+str(len(banners))+')'
    def ground(x,y,footprint=0):
        # Le point le plus bas sous l'emprise : un bâtiment ne flotte jamais au-dessus du sol.
        return min(terrain_height(x+dx,y+dy,seed) for dx in (-footprint,0,footprint) for dy in (-footprint,0,footprint))
    # Table de grès : plateau fermé, bancs horizontaux sur son pourtour.
    m=Mesh();n=96;rings=[]
    levels=((PLATEAU,1),(26.5,1.05),(21,1.1),(14.5,1.1),(6,1.33),(-6,1.62))
    for level,(z,radius) in enumerate(levels):
        ring=[]
        for i in range(n):
            a=i*math.tau/n;r=radius*(1+.045*math.sin(a*5+seed)+.05*math.sin(a*11+level*.8))
            ring.append((math.cos(a)*53*r+level*math.sin(a*3),math.sin(a)*44*r,z+(0 if level==0 else 1.2*math.sin(a*7+level))))
        rings.append(ring)
    m.surface(rings[0],[tuple(range(n))],assets.mat('sable_ombre'))
    strata=('gres_clair','gres_ocre','gres_rouge','gres_ocre','gres_sombre')
    for level in range(len(rings)-1):
        for i in range(n):
            j=(i+1)%n
            m.surface([rings[level+1][i],rings[level+1][j],rings[level][j],rings[level][i]],[(0,1,2),(0,2,3)],assets.mat(strata[level]))
    for j in range(42):
        a=j*math.tau/42;rr=1+rng.uniform(-.025,.025)
        x=math.cos(a)*51*rr;y=math.sin(a)*43*rr;sz=1.72+rng.uniform(-.1,.05)
        if abs(x)<11 and y<-30:sz*=.9
        place('falaise_gres_'+str(j%4),x,y,-6,math.degrees(a)+90,scale=(2.3,1.5,sz),category=nature)
    # Terrasse de la mosquée, escalier et deux fontaines au pied du parvis.
    m.box((0,20,PLATEAU+2.5),(34,39,5),assets.mat('gres_ocre'));m.box((0,20,PLATEAU+5.05),(34,39,.12),assets.mat('sol_dalle'))
    place('escalier',0,-8,PLATEAU,scale=(1,1,.83))
    for sx in (-1,1):place('fontaine_zellige',sx*10.5,-.35,PLATEAU)
    # Grande mosquée : façade, deux travées de salle, minaret carré.
    mx=-5 if alt else 0;my=7 if alt else 8;mz=PLATEAU+5.2
    place('mosquee_portail',mx,my,mz)
    for yy in (my+7.25,my+19.25):place('mosquee_salle_12m',mx,yy,mz)
    place('minaret',mx+13.5,my+3.2,mz)
    # Enceinte polygonale ouverte sur le pont.
    polygon=[(-7,-40),(-44,-31),(-51,5),(-35,37),(32,38),(50,8),(44,-31),(7,-40)]
    for a,b in zip(polygon,polygon[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);count=math.ceil(length/10)
        for i in range(count):
            t=(i+.5)/count;place('rempart_pise_10m',a[0]+dx*t,a[1]+dy*t,PLATEAU,180+math.degrees(math.atan2(dy,dx)),scale=(length/count/10,1,1))
    for j,(x,y) in enumerate(polygon[1:-1]):
        place('tour_ksar_'+str(j%3),x,y,PLATEAU-.3,scale=(1.1,1.1,1));banner(x,y,PLATEAU-.3+14+3*(j%3),rotation=j*40)
    place('porte_ksar',0,-40,PLATEAU)
    for yy in (-49.4,-63.4,-77.4):place('pont_arcades_14m',0,yy,PLATEAU)
    for sx in (-1,1):
        lantern(sx*3.2,-44.2,PLATEAU+1.2);lantern(sx*9.5,-6,PLATEAU);lantern(sx*8,my-3.6,mz)
        banner(sx*10.2,-43.7,PLATEAU+14.5,rotation=0)
    # Rues serrées de la ville haute : mêmes sites que la citadelle, maisons de terre.
    sites=[(-31,-22),(-19,-25),(17,-25),(30,-21),(-35,-8),(-24,-10),(23,-10),(35,-7),(-34,8),(32,12),(-29,24),(28,27),(-13,-18),(10,-14)]
    if alt:sites=[(-32,-23),(-20,-28),(-9,-29),(13,-30),(27,-24),(36,-12),(-36,-6),(-25,-15),(-13,-15),(13,-14),(23,-5),(34,4),(30,19),(-34,15),(-29,29)]
    city_houses=urbanisme.cite(seed,len(sites)+10,PLATEAU+.15)
    for i,(x,y) in enumerate(sites):
        k=rng.randrange(6);rng.choice((-8,0,7));rng.uniform(.85,1.04)
        plan=city_houses[i];maison(k,plan);x,y,z=plan['position'];sx,sy,sz=urbanisme.echelle(plan,k)
        h=3.1*(1,2,2,3,2,3)[k]+.45
        aa=math.radians(plan['rotation']);xx=-1.5*sx;yy=1.5*sy
        smokes.append({'position':[x+xx*math.cos(aa)-yy*math.sin(aa),y+xx*math.sin(aa)+yy*math.cos(aa),z+(h+1.2)*sz]})
        if i%3==0:lantern(plan['lane'][0],plan['lane'][1],PLATEAU+.2)
    for yy in range(-35,2,7):place('dalles',0,yy,PLATEAU+.16,scale=(1.3,1,1),category=props)
    for x in (-34,-20,20,34):place('garde',x,-32.6,PLATEAU+9.05,180,category=props)
    # Bourg bas au bord des jardins, séparé de la ville haute.
    for i,plan in enumerate(layout['houses']):
        rng.uniform(-125,-70);rng.uniform(-68,-12);kind=rng.randrange(6);rng.uniform(-30,25)
        maison(kind,plan)
    # Souk : quatre échoppes par rang, de part et d'autre de l'allée.
    souk=Z(14.25)
    for row,y in enumerate((-46.5,-35.5)):
        for j,x in enumerate((-116,-109,-102)):
            kind=('epices','tissus','poteries','dattes')[(j+row*2)%4]
            place('souk_'+kind,x,y,souk,rotation=180 if row==0 else 0)
    for x,y in ((-119,-46.5),(-112.8,-35.5),(-105.5,-35.5),(-118,-35.5)):
        place('souk_jarres',x,y,souk,category=props)
    for x,y in ((-119,-35.8),(-118.5,-45.5),(-105.5,-46.5)):
        place('souk_tapis',x,y,souk,rotation=90,category=props)
    for x,y in ((-112.5,-43.3),(-105.5,-38.5)):
        place('souk_velum',x,y,souk,category=props)
    market=Mesh();mx_=np.linspace(-121,-98.8,46);my_=np.linspace(-49.1,-32.8,34)
    for j in range(len(my_)-1):
        for i in range(len(mx_)-1):
            points=[(x,y,float(terrain_height(x,y,seed))+.045) for x,y in
                    ((mx_[i],my_[j]),(mx_[i+1],my_[j]),(mx_[i+1],my_[j+1]),(mx_[i],my_[j+1]))]
            market.surface(points,[(0,1,2,3)],assets.mat('souk_dalles'))
    plaza=market.object('Place_du_souk');move(plaza,land);static.append(plaza);clean_mesh(plaza)
    # Terrain large : plaine de reg, lit de l'oued, dunes et cuvette de l'oasis.
    n=320;extent=800;axis=np.linspace(-extent/2,extent/2,n+1);xx,yy=np.meshgrid(axis,axis);hh=terrain_height(xx,yy,seed)
    corridor=np.full(xx.shape,np.inf)
    for route in layout['routes']:
        if route['ground']:
            dd,_=paysage.nearest(xx,yy,route['points'][::3]+[route['points'][-1]])
            corridor=np.minimum(corridor,dd-route['width']/2)
    hh-=.12*(1-paysage.smoothstep((corridor-1)/3))
    oued=paysage.oued_distance(xx,yy);dunes=paysage.dunes(xx,yy,seed)
    px,py,pz=layout['pool']['position'];pw,pd=layout['pool']['size']
    damp=np.hypot((xx-px)/(pw*.5+30),(yy-py)/(pd*.5+30))
    verts=np.stack((xx,yy,hh),axis=-1).reshape(-1,3).tolist();terrain=Mesh()
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;ids=(a,a+1,a+n+2,a+n+1)
            slope=abs(hh[j+1,i]-hh[j,i])+abs(hh[j,i+1]-hh[j,i])
            # De grandes plaques plutôt qu'un damier : chaque matière couvre des dizaines de mètres.
            noise=assets.relief_noise(i*.035,j*.035,seed);rock=assets.relief_noise(i*.13,j*.13,seed)
            if slope>3.0 and rock>.35:name_='gres_ocre'
            elif oued[j,i]<9+3*noise:name_='reg_gravier'
            elif damp[j,i]<1:name_='sable_ombre'
            elif dunes[j,i]>1.5 or noise>.5:name_='sable_dune'
            else:name_='reg_gravier' if noise<.3 else 'sable_ombre'
            terrain.surface([verts[k] for k in ids],[(0,1,2,3)],assets.mat(name_))
    terr=terrain.object('Terrain_desert');move(terr,land);static.append(terr)
    clean_mesh(terr)
    terrain_surface=BVHTree.FromPolygons([v.co for v in terr.data.vertices],[tuple(p.vertices) for p in terr.data.polygons],all_triangles=True)
    for p in terr.data.polygons:p.use_smooth=True
    # Eau de la guelta : le terrain la borde lui-même en remontant.
    water=Mesh();ring=[(px+math.cos(a)*(pw*.5+8),py+math.sin(a)*(pd*.5+8),pz) for a in np.linspace(0,math.tau,49)[:-1]]
    water.surface(ring,[tuple(range(len(ring)))],assets.mat('eau_oasis'))
    pool=water.object('Eau_de_la_guelta');move(pool,land);static.append(pool)
    # Palmeraie : même budget que la forêt de la citadelle, rassemblé autour de l'eau et de l'oued.
    groves=[(-205,-40,24,38),(-230,-95,26,18),(-170,40,40,16),(130,-40,18,40),(-40,-205,45,12)]
    if alt:groves=[(-210,-30,30,34),(-190,-100,30,14),(-150,45,34,18),(95,-125,22,30),(-95,-215,50,12)]
    forest_rng=random.Random(seed+830);feet=[];attempts=0
    while len(feet)<1200 and attempts<60000:
        attempts+=1;cx,cy,rx,ry=groves[forest_rng.randrange(len(groves))]
        u=forest_rng.gauss(0,1);v=forest_rng.gauss(0,1)
        if u*u+v*v>4:continue
        x=cx+u*rx;y=cy+v*ry
        if not (-290<x<290 and -260<y<260):continue
        if (x/82)**2+(y/70)**2<1.25 or abs(x)<13 and y<-40 or -142<x<-58 and -88<y<4:continue
        if any((x-a)**2+(y-b)**2<3.4**2 for a,b in feet):continue
        if paysage.blocked_by_use(x,y,seed):continue
        i=len(feet);feet.append((x,y));z=float(terrain_height(x,y,seed))
        scale=forest_rng.uniform(.85,1.25);angle=forest_rng.uniform(0,360)
        o=place('palmier_'+str(i%3),x,y,z-.1,angle,(scale,scale,scale),nature)
        if i%6==0:o.driver_add('rotation_euler',0).driver.expression='.012*sin(frame*.09+'+str(i)+')'
    if len(feet)<1200:raise ValueError('Palmeraie trop exiguë pour le budget prévu')
    acacia_rng=random.Random(seed+417);count=0;attempts=0
    while count<70 and attempts<5000:
        attempts+=1;a=acacia_rng.uniform(0,math.tau);r=acacia_rng.uniform(110,300);x=math.cos(a)*r;y=math.sin(a)*r
        if (x/82)**2+(y/70)**2<1.5 or paysage.blocked_by_use(x,y,seed) or paysage.dunes(x,y,seed)>2:continue
        if any((x-a_)**2+(y-b_)**2<6**2 for a_,b_ in feet):continue
        place('acacia_'+str(count%2),x,y,float(terrain_height(x,y,seed))-.05,acacia_rng.uniform(0,360),(1,1,acacia_rng.uniform(.85,1.15)),nature);count+=1
    # Dunes et buttes lointaines, modules partagés et échelles indépendantes.
    for i,(x,y,sx,sz) in enumerate([(-235,245,1.3,.8),(-405,315,1.8,1.0),(215,265,1.4,.9),(385,340,1.7,1.05),(-80,440,1.6,.85),(90,470,1.7,.95),(-330,20,1.0,.7)]):
        place('dune_'+str(i%3),x+(20 if alt else 0),y,-3,i*53+(17 if alt else 0),(sx,sx,sz),nature)
    for i,(x,y,s) in enumerate([(430,-190,1.0),(-460,-260,1.2)]):
        place('butte_'+str(i),x,y+(30 if alt else 0),-6,i*70+20,(s,s,1),nature)
    # Rubans praticables : ils relient les ouvrages et tous les seuils.
    roads=Mesh()
    for route in layout['routes']:
        if not route['ground']:continue
        sections=[];distances=[];distance=0
        across=(1,.78,.42,0,-.42,-.78,-1)
        for k,p in enumerate(route['points']):
            a=route['points'][max(0,k-1)];b=route['points'][min(len(route['points'])-1,k+1)]
            tangent=Vector((b[0]-a[0],b[1]-a[1],0)).normalized()
            side=Vector((-tangent.y,tangent.x,0))*(route['width']/2+.5)
            row=[]
            for sign in across:
                jitter=1+.08*math.sin(k*.51+seed)+.035*math.sin(k*1.7) if sign else 1
                x=p[0]+side.x*sign*jitter;y=p[1]+side.y*sign*jitter
                edge=float(paysage.smoothstep((abs(sign)-.78)/.22))
                center_height=float(terrain_height(x,y,seed))+.14
                hit=terrain_surface.ray_cast(Vector((x,y,500)),Vector((0,0,-1)))[0]
                if hit is None:raise ValueError('Accotement hors du terrain')
                row.append((x,y,center_height*(1-edge)+(hit.z+.012)*edge))
            sections.append(row)
            if k:distance+=math.hypot(p[0]-route['points'][k-1][0],p[1]-route['points'][k-1][1])
            distances.append(distance/6)
        for k,(a,b) in enumerate(zip(sections,sections[1:])):
            for j in range(len(across)-1):
                u=(1-across[j])/2;v=(1-across[j+1])/2
                roads.surface([a[j],a[j+1],b[j+1],b[j]],[(0,1,2,3)],assets.mat('chemin_dalle' if route['id'] in ('descente_oasis','rue_basse','traverse_bourg') else 'chemin_sable'),
                              [(u,distances[k]),(v,distances[k]),(v,distances[k+1]),(u,distances[k+1])])
    roads_obj=roads.object('Chemins_praticables');move(roads_obj,land);static.append(roads_obj)
    # Jardins irrigués : terre sombre et murets de pisé, ouverts côté accès.
    gardens=Mesh()
    for plot in layout['plots']:
        x,y,z=plot['position'];w,d=plot['size']
        gardens.box((x,y,z-.04),(w,d,.10),assets.mat('terre_jardin'))
        # L'accès arrive par +Y : ce côté garde une porte de 3,6 m au milieu.
        gate=3.6;piece=(w-gate)/2
        gardens.box((x,y-d/2,z+.3),(w+.4,.4,.7),assets.mat('pise'))
        for sx in (-1,1):
            gardens.box((x+sx*(gate/2+piece/2),y+d/2,z+.3),(piece+.4,.4,.7),assets.mat('pise'))
            gardens.box((x+sx*w/2,y,z+.3),(.4,d,.7),assets.mat('pise'))
    oo=gardens.object('Jardins_irrigues');move(oo,land);static.append(oo)
    ground_mesh=m.object('Socle_terrasses_chemin');move(ground_mesh,land);static.append(ground_mesh)
    # Réserves de jarres et de bois de palmier dans les rues du ksar.
    for i,(x,y) in enumerate([(-12,-29),(11,-26),(-10,-12),(17,-8),(-26,1),(27,20)]):
        place('jarres_reserve',x,y,PLATEAU+.2,i*47,category=props)
    for sx in (-1,1):
        for yy in (-68,-54,-29):lantern(sx*2.7,yy,PLATEAU+.1)
    # Blocs de grès et congères de sable au pied de la table.
    detail=Mesh();decor_rng=random.Random(seed+502)
    for j in range(110):
        a=decor_rng.uniform(0,math.tau);rad=decor_rng.uniform(1.06,1.40)
        x=math.cos(a)*61*rad;y=math.sin(a)*52*rad
        if abs(x)<9 and y<0:continue
        if paysage.blocked_by_use(x,y,seed):continue
        z=float(terrain_height(x,y,seed));r=decor_rng.uniform(.35,2.0)
        detail.ico((x,y,z+r*.25),(r,r*.75,r*.7),assets.mat('gres_ocre' if j%3 else 'gres_rouge'),1)
        if j%2:detail.ico((x+r*.6,y,z),(r*1.4,r*.9,r*.28),assets.mat('sable_dune'),1)
    oo=detail.object('Éboulis et sable au pied de la table');move(oo,land);static.append(oo)
    # Caravane au repos près de la guelta, tentes et coupoles dans la palmeraie.
    life=random.Random(seed+61)
    for k in range(5):
        x,y=free_spot(life,(px+18,py-24),14,seed,3.5)
        place('chameau_'+('2' if k<3 else '1'),x,y,float(terrain_height(x,y,seed)),life.uniform(0,360),category=props)
    for k,center in enumerate(((-245,-25),(-120,-170))):
        x,y=free_spot(life,center,18,seed,6)
        place('tente_nomade',x,y,ground(x,y,3)-.05,life.uniform(0,360),category=props)
        x2,y2=free_spot(life,(x,y),9,seed,4)
        place('chameau_0',x2,y2,float(terrain_height(x2,y2,seed)),life.uniform(0,360),category=props)
    for center in ((-150,5),(150,60)):
        x,y=free_spot(life,center,25,seed,8)
        place('coupole_marabout',x,y,ground(x,y,3.5)-.1,life.choice((0,90,180,270)))
    for center in ((-135,-118),(-195,-75)):
        x,y=free_spot(life,center,10,seed,3)
        place('puits',x,y,ground(x,y,1.2)-.05,life.uniform(0,360),category=props)
    # Densifier les abords de la place après les identifiants déjà présents.
    for i,plan in enumerate(city_houses[len(sites):len(sites)+6]):maison(1+i%5,plan)
    for i,plan in enumerate(city_houses[-4:]):maison((i+2)%6,plan)
    for o in static:clean_mesh(o)
    static_triangles=sum(tri_count(o) for o in static);export_fbx(path/(name+'.fbx'),static)
    # Ciel chaud, bleu profond au zénith et voile de poussière à l'horizon.
    world=bpy.data.worlds.new('Ciel du désert');bpy.context.scene.world=world;world.use_nodes=True
    nodes=world.node_tree.nodes;links=world.node_tree.links;bg=nodes.get('Background');bg.inputs['Strength'].default_value=1.0
    coord=nodes.new('ShaderNodeTexCoord');separate=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Generated'],separate.inputs[0])
    # La composante verticale de la direction regardée : 0 à l'horizon, 1 au zénith.
    gradient=nodes.new('ShaderNodeValToRGB');ramp=gradient.color_ramp
    ramp.elements[0].position=0;ramp.elements[0].color=(.80,.62,.44,1);ramp.elements[1].position=.55;ramp.elements[1].color=(.10,.25,.55,1)
    mid=ramp.elements.new(.12);mid.color=(.55,.60,.68,1)
    links.new(separate.outputs['Z'],gradient.inputs[0])
    clouds=nodes.new('ShaderNodeTexNoise');clouds.inputs['Scale'].default_value=2.6;clouds.inputs['Detail'].default_value=6;clouds.inputs['Roughness'].default_value=.6
    stretch=nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(1,4,6);links.new(coord.outputs['Normal'],stretch.inputs[0]);links.new(stretch.outputs[0],clouds.inputs['Vector'])
    wisps=nodes.new('ShaderNodeValToRGB');wisps.color_ramp.elements[0].position=.55;wisps.color_ramp.elements[0].color=(0,0,0,1);wisps.color_ramp.elements[1].position=.8;wisps.color_ramp.elements[1].color=(.45,.45,.45,1)
    links.new(clouds.outputs['Fac'],wisps.inputs[0])
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='SCREEN';links.new(wisps.outputs['Color'],mix.inputs[0]);links.new(gradient.outputs['Color'],mix.inputs[1]);mix.inputs[2].default_value=(1,.92,.84,1)
    links.new(mix.outputs['Color'],bg.inputs['Color'])
    sun=bpy.data.lights.new('Soleil bas','SUN');sun.energy=5.0;sun.color=(1,.82,.60);sun.angle=.012
    so=bpy.data.objects.new('Soleil de fin de journée',sun);studio.objects.link(so);so.rotation_euler=tuple(math.radians(a) for a in (62,0,-45))
    area=bpy.data.lights.new('Ciel diffus','AREA');area.energy=15000;area.shape='DISK';area.size=150;area.color=(.62,.74,.95)
    ao=bpy.data.objects.new('Remplissage du ciel',area);studio.objects.link(ao);ao.location=(60,-120,170);ao.rotation_euler=(Vector((0,0,20))-ao.location).to_track_quat('-Z','Y').to_euler()
    # Brume de poussière, plus dense au ras du sol.
    fog=bpy.data.materials.new('Poussière en suspension');fog.use_nodes=True;nn=fog.node_tree.nodes;nn.clear();vo=nn.new('ShaderNodeVolumePrincipled');vo.inputs['Color'].default_value=(.86,.70,.52,1);vo.inputs['Anisotropy'].default_value=.35
    output=nn.new('ShaderNodeOutputMaterial');fog.node_tree.links.new(vo.outputs['Volume'],output.inputs['Volume'])
    fogmesh=Mesh();fogmesh.box((0,130,60),(1800,1600,200),fog);fo=fogmesh.object('Poussière de la vallée');move(fo,studio);fo.display_type='WIRE'
    coord=nn.new('ShaderNodeTexCoord');separate=nn.new('ShaderNodeSeparateXYZ');height=nn.new('ShaderNodeMapRange')
    height.inputs['From Min'].default_value=-4;height.inputs['From Max'].default_value=70
    height.inputs['To Min'].default_value=.00055;height.inputs['To Max'].default_value=.00006
    fog.node_tree.links.new(coord.outputs['Object'],separate.inputs[0])
    fog.node_tree.links.new(separate.outputs['Z'],height.inputs['Value']);fog.node_tree.links.new(height.outputs['Result'],vo.inputs['Density'])
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32 if quick else 64;sc.cycles.use_denoising=True
    sc.cycles.adaptive_threshold=.035;sc.cycles.adaptive_min_samples=16
    sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=3;sc.cycles.glossy_bounces=3;sc.cycles.transparent_max_bounces=6
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        sc.cycles.device='GPU'
    except Exception:pass
    sc.render.resolution_x=1600;sc.render.resolution_y=900;sc.render.resolution_percentage=65 if quick else 100
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.4
    sc.render.image_settings.file_format='PNG';sc.render.fps=24;sc.frame_start=1;sc.frame_end=240
    tree=bpy.data.node_groups.new('Halo des lanternes','CompositorNodeTree');sc.compositing_node_group=tree
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    rl=tree.nodes.new('CompositorNodeRLayers');glare=tree.nodes.new('CompositorNodeGlare');glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High';glare.inputs['Strength'].default_value=.12;out=tree.nodes.new('NodeGroupOutput');tree.links.new(rl.outputs['Image'],glare.inputs['Image']);tree.links.new(glare.outputs['Image'],out.inputs['Image'])
    cameras={}
    for label,position,target,lens in CAMERAS:
        c=bpy.data.cameras.new(label);o=bpy.data.objects.new(label,c);studio.objects.link(o);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.lens=lens;c.clip_end=2200;cameras[label]=o
    sc.camera=cameras['Ksar'];sc.frame_set(1)
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.clip_end=2200
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path/(name+'.blend')),compress=True)
    triangles=static_triangles+sum(records[i['asset']]['triangles'][0] for i in instances)
    label=next((s['label'] for s in RECIPE['dispositions'] if s['id']==name),name)
    report={**{k:RECIPE[k] for k in ('biome','culture','typologie','annee')},'id':name,'label':label,'description':RECIPE['description'],'schema':4,'seed':seed,'instances':instances,'materials':matters(static),'config':{'sun':[1,.86,.66]},
            'building_count':sum(i['asset'].startswith('maison_') for i in instances),'tree_count':sum(i['asset'].startswith(('palmier_','acacia_')) for i in instances),
            'triangles_lod0':triangles,'static_triangles':static_triangles,'anchors':[{'position':verts[i]} for i in (0,70,500,2600,13000,20000)],'smokes':smokes,'wheels':[],'torches':torches,'banners':banners,
            'center':[0,0],'camera_position':list(CAMERAS[0][1]),'camera_target':list(CAMERAS[0][2]),'catalogue_sha256':hashlib.sha256((LIB/'catalogue.json').read_bytes()).hexdigest(),'simulation_connected':False}
    report['cameras']=[{'name':n,'position':list(p),'target':list(t),'lens':f} for n,p,t,f in CAMERAS]
    report['routes']=[{'id':r['id'],'width':r['width'],'points':[{'position':[p[0],p[1],float(terrain_height(p[0],p[1],seed))+.085 if r['ground'] else p[2]]} for p in r['points']]} for r in layout['routes']]
    report['plots']=layout['plots'];report['spawn']=layout['spawn'];report['forest']=layout['forest'];report['pool']=layout['pool']
    write(path/(name+'.json'),report)
    for label in ([] if no_render else views or (['Ksar'] if quick else cameras)):
        sc.camera=cameras[label];sc.render.filepath=str(path/'renders'/('blender_'+label.lower()+'.png'));bpy.ops.render.render(write_still=True)
    print('DESERT_OK',name,len(instances),triangles,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['assets','scene','edition']);p.add_argument('--nom',default='ksar_des_sept_puits');p.add_argument('--graine',type=int,default=1433);p.add_argument('--rapide',action='store_true');p.add_argument('--sans-rendus',action='store_true');p.add_argument('--vues',default='');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.phase=='assets':library()
    elif a.phase=='edition':edition(a.nom)
    else:scene(a.nom,a.graine,a.rapide,a.sans_rendus,[v for v in a.vues.split(',') if v])
