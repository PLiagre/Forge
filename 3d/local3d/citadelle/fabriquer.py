"""Fabrique un kit partagé et deux compositions de citadelle dans Blender."""
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
from local3d.citadelle import assets
from local3d.citadelle.cameras import CAMERAS
from local3d.citadelle import paysage,urbanisme
from local3d.atelier_v2.geometrie import Mesh,MATS,material,export_fbx,tri_count
from local3d.alpin.fabriquer import reset,coll,move,matters,write
OUT=ROOT/'local3d/citadelle/sorties';LIB=OUT/'bibliotheque';TEX=OUT/'textures'
RECIPE=json.loads((Path(__file__).parent/'recette.json').read_text(encoding='utf-8'))

def clean_mesh(o):
    # Les pointes de cônes ont des faces d'aire nulle que Unity supprime à l'import.
    # Les retirer à la source garde le catalogue et le FBX strictement comparables.
    bm=bmesh.new();bm.from_mesh(o.data)
    if o.name.startswith(('montagne_','Terrain_')):bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
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
            # Un petit chanfrein capte la lumière sur les angles des modules proches.
            # La source manuelle reste intacte, y compris sa géométrie exportée.
            if not source.exists() and o.name.endswith('_LOD0') and kind in ('batiment','repere','module'):
                bpy.context.view_layer.objects.active=o
                # Réserver les chanfreins aux arêtes structurantes, pas aux milliers
                # de minuscules carreaux, aiguilles et moulures déjà détaillés.
                bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update();weight=bm.edges.layers.float.new('bevel_weight_edge')
                for edge in bm.edges:
                    faces=list(edge.link_faces)
                    edge[weight]=1 if len(faces)==2 and edge.calc_length()>.3 and min(f.calc_area() for f in faces)>.08 and faces[0].normal.dot(faces[1].normal)<.86 else 0
                bm.to_mesh(o.data);bm.free()
                bevel=o.modifiers.new('Arêtes usées de la pierre et du bois','BEVEL')
                bevel.width=.028;bevel.segments=1;bevel.limit_method='WEIGHT'
                bpy.ops.object.modifier_apply(modifier=bevel.name)
            clean_mesh(o)
            o.asset_mark();o.asset_data.description='Citadelle alpine • module en mètres • '+name
            if name.startswith('montagne_'):
                for p in o.data.polygons:p.use_smooth=False
        counts=[tri_count(o) for o in lods]
        if not counts[0]>=counts[1]>=counts[2]>0:raise ValueError('LOD invalides : '+name)
        vs=np.array([v.co for v in lods[0].data.vertices]);records.append({'id':name,'kind':kind,'triangles':counts,'bounds_min':vs.min(axis=0).tolist(),'bounds_max':vs.max(axis=0).tolist()})
        export_fbx(LIB/(name+'.fbx'),lods);objects.extend(lods)
    bpy.data.libraries.write(str(LIB/'Kit_Citadelle.blend'),set(objects),path_remap='RELATIVE',fake_user=True,compress=True)
    write(LIB/'catalogue.json',{'schema':3,'assets':records,'materials':matters(objects)})
    from local3d.citadelle import habitat
    write(LIB/'habitat.json',habitat.catalogue())
    print('KIT_CITADELLE_OK',len(records),flush=True)

def edition(name):
    reset();path=Path(__file__).parent/'sources'/(name+'.blend')
    if path.exists():raise ValueError('Source déjà présente ; aucune retouche écrasée : '+str(path))
    wanted=[name+'_LOD'+str(i) for i in range(3)]
    with bpy.data.libraries.load(str(LIB/'Kit_Citadelle.blend'),link=False) as (src,dst):
        if not set(wanted)<=set(src.objects):raise ValueError('Module inconnu : '+name)
        dst.objects=wanted
    for i,o in enumerate(dst.objects):
        coll('LOD '+str(i)).objects.link(o);o.hide_render=i>0;o.hide_set(i>0)
    o=dst.objects[0];o.select_set(True);bpy.context.view_layer.objects.active=o
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_location=(0,0,6);ar.spaces.active.region_3d.view_distance=25;ar.spaces.active.shading.type='MATERIAL'
    bpy.ops.file.pack_all();path.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)

def terrain_height(x,y,seed):
    return paysage.field(x,y,seed)

def scene(name,seed,quick=False,no_render=False):
    reset();assets.TEX=TEX;rng=random.Random(seed);alt=seed!=RECIPE['dispositions'][0]['seed']
    layout=paysage.plan(seed)
    path=OUT/'villages'/name;path.mkdir(parents=True,exist_ok=True);(path/'renders').mkdir(exist_ok=True)
    catalogue=json.loads((LIB/'catalogue.json').read_text(encoding='utf-8'));records={a['id']:a for a in catalogue['assets']}
    with bpy.data.libraries.load(str(LIB/'Kit_Citadelle.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.endswith('_LOD0')]
    prototypes={o.name[:-5]:o for o in dst.objects}
    for o in prototypes.values():
        for slot in o.material_slots:
            if slot.material:MATS[slot.material.name]=slot.material
    arch=coll('01 • Citadelle et bourg');nature=coll('02 • Rochers et forêt');props=coll('03 • Faction et lumières');land=coll('04 • Relief et chemins');studio=coll('05 • Atmosphère')
    instances=[];torches=[];banners=[];smokes=[];static=[]
    def place(asset,x,y,z,rotation=0,scale=(1,1,1),category=arch):
        o=prototypes[asset].copy();category.objects.link(o);o.name=asset+'__'+str(len(instances));o.location=(x,y,z);o.rotation_euler.z=math.radians(rotation);o.scale=scale;o['asset_id']=asset
        instances.append({'id':o.name,'asset':asset,'position':[float(x),float(y),float(z)],'rotation':float(rotation),'scale':list(scale),'category':category.name[:2]})
        return o
    def torch(x,y,z):
        o=place('torche',x,y,z,category=props);torches.append({'position':[x,y,z+3.1],'id':o.name})
        light=bpy.data.lights.new('Feu de torche','POINT');light.energy=240;light.color=(1,.36,.075);light.shadow_soft_size=.34
        l=bpy.data.objects.new('Lueur '+o.name,light);studio.objects.link(l);l.location=(x,y,z+3.1)
        light.driver_add('energy').driver.expression='240+26*sin(frame*.63+'+str(len(torches))+')+15*sin(frame*1.3)'
    def maison(kind,plan):
        x,y,z=plan['position'];scale=urbanisme.echelle(plan,kind)
        o=place('maison_modulaire_'+str(kind),x,y,z,plan['rotation'],scale)
        o.color=(*plan['color'],1);instances[-1]['color']=list(plan['color']);instances[-1]['urban_group']=plan['group']
        return o
    def banner(x,y,z,rotation=0):
        o=place('banniere',x,y,z,rotation,category=props);banners.append(o.name)
        # Déplacement géométrique du tissu, attaché en haut et à la hampe.
        o.data=o.data.copy();o.shape_key_add(name='Repos');key=o.shape_key_add(name='Rafale')
        for v in key.data:
            p=v.co
            if p.x>.08 and 3.15<p.z<7.05:p.y+=.42*math.sin(p.x*2.7+p.z*1.8)*min(1,p.x)*max(0,(7-p.z)/3.8)
        key.driver_add('value').driver.expression='.5+.5*sin(frame*.14+'+str(len(banners))+')'
    # Socle : plateau fermé, falaise instanciée sur son pourtour.
    m=Mesh();n=96;top=[];rings=[]
    for level,(z,radius) in enumerate(((42,1),(37,1.06),(29,1.18),(20,1.13),(9,1.4),(-8,1.62))):
        ring=[]
        for i in range(n):
            a=i*math.tau/n;r=radius*(1+.045*math.sin(a*5+seed)+.055*math.sin(a*11+level*.8))
            ring.append((math.cos(a)*53*r+level*math.sin(a*3),math.sin(a)*44*r,z+(0 if level==0 else 1.8*math.sin(a*7+level))))
        rings.append(ring)
    top=rings[0]
    m.surface(top,[tuple(range(n))],assets.mat('neige_ombre'))
    for level in range(len(rings)-1):
        for i in range(n):
            j=(i+1)%n
            material=('roche_noire','roche_granite','roche_claire','roche_claire')[(level+i//11)%4]
            m.surface([rings[level+1][i],rings[level+1][j],rings[level][j],rings[level][i]],[(0,1,2),(0,2,3)],assets.mat(material))
    for j in range(42):
        a=j*math.tau/42;rr=1+rng.uniform(-.025,.025)
        x=math.cos(a)*51*rr;y=math.sin(a)*43*rr;sz=2.35+rng.uniform(-.12,.08)
        if abs(x)<11 and y<-30:sz*=.91
        place('falaise_'+str(j%4),x,y,-7,math.degrees(a),scale=(1.6,1.4,sz),category=nature)
    # Terrasse haute et escalier la reliant à la place.
    m.box((0,20,44.5),(34,39,5),assets.mat('basalte'));m.box((0,20,47.05),(34,39,.12),assets.mat('neige_ombre'))
    place('escalier',0,-8,42,scale=(1,1,.83))
    # Cathédrale assemblée : trois travées, façade, deux clochers, arcs-boutants.
    church_x=-5 if alt else 0;church_y=7 if alt else 8;cz=47.2
    for yy in (church_y+6,church_y+18):place('cathedrale_nef_12m',church_x,yy,cz)
    place('cathedrale_facade',church_x,church_y,cz)
    for sx in (-1,1):
        place('cathedrale_clocher',church_x+sx*9.6,church_y+1,cz,scale=(.82,.82,1))
        for yy in (church_y+7,church_y+18):place('arc_boutant',church_x+sx*15.5,yy,cz,rotation=180 if sx==1 else 0,scale=(1,1,.96))
    # Enceinte polygonale ouverte sur le pont.
    polygon=[(-7,-40),(-44,-31),(-51,5),(-35,37),(32,38),(50,8),(44,-31),(7,-40)]
    for a,b in zip(polygon,polygon[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);count=math.ceil(length/10)
        for i in range(count):
            t=(i+.5)/count;place('rempart_10m',a[0]+dx*t,a[1]+dy*t,42,180+math.degrees(math.atan2(dy,dx)),scale=(length/count/10,1,1))
    for j,(x,y) in enumerate(polygon[1:-1]):place('tour_'+str(j%3),x,y,41.7,scale=(1.1,1.1,1));banner(x,y,68 if j%3!=2 else 62,rotation=j*40)
    for sx in (-1,1):place('tour_0',sx*8,-40,42,scale=(.82,.82,.94))
    place('porte_ogive',0,-40,42)
    for yy in (-49.4,-63.4,-77.4):place('pont_arche_14m',0,yy,42)
    for sx in (-1,1):
        torch(sx*5,-43,43);torch(sx*7,-5,47);torch(sx*8,church_y-3,47)
        banner(sx*12,-40,56,rotation=0)
    # Rues serrées : tirage de modèles ET placements, au même contexte artistique.
    sites=[(-31,-22),(-19,-25),(17,-25),(30,-21),(-35,-8),(-24,-10),(23,-10),(35,-7),(-34,8),(32,12),(-29,24),(28,27),(-13,-18),(10,-14)]
    if alt:sites=[(-32,-23),(-20,-28),(-9,-29),(13,-30),(27,-24),(36,-12),(-36,-6),(-25,-15),(-13,-15),(13,-14),(23,-5),(34,4),(30,19),(-34,15),(-29,29)]
    city_houses=urbanisme.cite(seed,len(sites)+10)
    for i,(x,y) in enumerate(sites):
        k=rng.randrange(6);rotation=rng.choice((-8,0,7))+(90 if x<-28 else -90 if x>28 else 0);s=rng.uniform(.85,1.04)
        plan=city_houses[i];maison(k,plan);x,y,z=plan['position'];sx,sy,sz=urbanisme.echelle(plan,k);h=3*(2+int(k in (1,3,5)));rise=0
        aa=math.radians(plan['rotation']);xx=-1.5*sx;yy=1.5*sy
        smokes.append({'position':[x+xx*math.cos(aa)-yy*math.sin(aa),y+xx*math.sin(aa)+yy*math.cos(aa),z+(h+4.5)*sz]})
        if i%3==0:torch(plan['lane'][0],plan['lane'][1],42.2)
    for yy in range(-35,2,7):place('paves',0,yy,42.16,scale=(1.3,1,1),category=props)
    for x in (-34,-20,20,34):place('garde',x,-32,54.2,180,category=props)
    # Petit hameau en contrebas et forêt continue, séparés de la ville haute.
    for i,plan in enumerate(layout['houses']):
        rng.uniform(-125,-70);rng.uniform(-68,-12);kind=rng.randrange(6);rng.uniform(-30,25)
        maison(kind,plan)
    # Un marché ouvert borde deux vraies allées, sans les encombrer.
    for row,y in enumerate((-46.5,-35.5)):
        for j,x in enumerate((-116,-109,-102)):
            kind=('fruits','legumes','pain','poterie')[(j+row*2)%4]
            place('habitat_marche_'+kind,x,y,14.25,rotation=180 if row==0 else 0)
    for x,y in ((-119,-46.5),(-112.8,-35.5),(-105.5,-35.5),(-118,-35.5)):
        place('habitat_marche_paniers',x,y,14.25,category=props)
    for x,y in ((-119,-35.8),(-118.5,-45.5),(-105.5,-46.5)):
        place('habitat_marche_tonneaux',x,y,14.25,category=props)
    for x,y in ((-112.5,-43.3),(-105.5,-38.5)):
        place('habitat_marche_fanions',x,y,14.25,category=props)
    # Pavés épousant l'assise réelle, raccordés aux rues sans marche rapportée.
    market=Mesh();mx=np.linspace(-121,-98.8,46);my=np.linspace(-49.1,-32.8,34)
    for j in range(len(my)-1):
        for i in range(len(mx)-1):
            points=[(x,y,float(terrain_height(x,y,seed))+.045) for x,y in
                    ((mx[i],my[j]),(mx[i+1],my[j]),(mx[i+1],my[j+1]),(mx[i],my[j+1]))]
            market.surface(points,[(0,1,2,3)],assets.mat('marche_paves'))
    plaza=market.object('Place_du_marche');move(plaza,land);static.append(plaza);clean_mesh(plaza)
    # Terrain large : aucune tranche circulaire visible dans la composition.
    n=320;extent=800;axis=np.linspace(-extent/2,extent/2,n+1);xx,yy=np.meshgrid(axis,axis);hh=terrain_height(xx,yy,seed)
    corridor=np.full(xx.shape,np.inf)
    for route in layout['routes']:
        if route['ground']:
            dd,_=paysage.nearest(xx,yy,route['points'][::3]+[route['points'][-1]])
            corridor=np.minimum(corridor,dd-route['width']/2)
    # Une assise creusée évite que la neige traverse les pavés. La grille reste
    # continue : aucun bord partagé entre une cellule fine et une cellule grossière.
    hh-=.16*(1-paysage.smoothstep((corridor-1)/3))
    verts=np.stack((xx,yy,hh),axis=-1).reshape(-1,3).tolist();terrain=Mesh()
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;ids=(a,a+1,a+n+2,a+n+1)
            slope=abs(hh[j+1,i]-hh[j,i])+abs(hh[j,i+1]-hh[j,i])
            rock=slope>3.4 and assets.relief_noise(i*.17,j*.17,seed)>.5
            terrain.surface([verts[k] for k in ids],[(0,1,2,3)],assets.mat('roche_claire' if rock else 'neige_ombre'))
    terr=terrain.object('Terrain_vallee');move(terr,land);static.append(terr)
    clean_mesh(terr)
    terrain_surface=BVHTree.FromPolygons([v.co for v in terr.data.vertices],[tuple(p.vertices) for p in terr.data.polygons],all_triangles=True)
    for p in terr.data.polygons:p.use_smooth=True
    # Même budget d'arbres, concentré en cinq bois : les lisières laissent lire le village.
    woods=[(-203,-13,25,36),(157,-10,30,45),(100,135,45,26),(-93,144,38,30),(-223,155,28,38)]
    forest_rng=random.Random(seed+830);feet=[];attempts=0
    while len(feet)<1600 and attempts<40000:
        attempts+=1;cx,cy,rx,ry=woods[forest_rng.randrange(len(woods))]
        u=forest_rng.gauss(0,1);v=forest_rng.gauss(0,1)
        if u*u+v*v>4:continue
        x=cx+u*rx;y=cy+v*ry
        if not (-290<x<290 and -175<y<260):continue
        if (x/82)**2+(y/70)**2<1.25 or abs(x)<13 and y<-40 or -142<x<-58 and -88<y<4:continue
        if any((x-a)**2+(y-b)**2<3.2**2 for a,b in feet):continue
        if paysage.blocked_by_use(x,y,seed):continue
        i=len(feet);feet.append((x,y));z=float(terrain_height(x,y,seed))
        scale=forest_rng.uniform(.9,1.55);angle=forest_rng.uniform(0,360)
        o=place('sapin_neige_'+str(i%3),x,y,z,angle,(scale,scale,scale),nature)
        if i%7==0:o.driver_add('rotation_euler',0).driver.expression='.009*sin(frame*.08+'+str(i)+')'
    if len(feet)<1600:raise ValueError('Massifs forestiers trop exigus pour le budget prévu')
    # Montagnes éloignées, asset partagé et échelles indépendantes.
    for i,(x,y,sx,sz) in enumerate([(-235,230,1.1,.82),(-405,315,1.8,.97),(200,260,1.3,.89),(385,340,1.7,1.05),(-80,440,1.4,.80),(80,480,1.6,.92),(-290,10,.85,.60)]):
        place('montagne_'+str(i%3),x+(20 if alt else 0),y,-22,i*53+(17 if alt else 0),(sx,sx,sz),nature)
    # Des rubans de terrain praticables relient les ouvrages et tous les seuils.
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
                # Le bord rejoint la neige creusée ; la bande centrale garde
                # sa hauteur et sa largeur de circulation contrôlées.
                edge=float(paysage.smoothstep((abs(sign)-.78)/.22))
                center_height=float(terrain_height(x,y,seed))+.14
                hit=terrain_surface.ray_cast(Vector((x,y,500)),Vector((0,0,-1)))[0]
                if hit is None:raise ValueError('Accotement hors du terrain')
                # Lire la surface triangulée réelle, dont la hauteur diffère
                # légèrement du champ continu entre les sommets de la grille.
                row.append((x,y,center_height*(1-edge)+(hit.z+.012)*edge))
            sections.append(row)
            if k:distance+=math.hypot(p[0]-route['points'][k-1][0],p[1]-route['points'][k-1][1])
            distances.append(distance/6)
        for k,(a,b) in enumerate(zip(sections,sections[1:])):
            for j in range(len(across)-1):
                u=(1-across[j])/2;v=(1-across[j+1])/2
                roads.surface([a[j],a[j+1],b[j+1],b[j]],[(0,1,2,3)],assets.mat('chemin_pave' if route['id'] in ('descente_village','rue_basse','traverse_village') else 'chemin_terre'),
                              [(u,distances[k]),(v,distances[k]),(v,distances[k+1]),(u,distances[k+1])])
    roads_obj=roads.object('Chemins_praticables');move(roads_obj,land);static.append(roads_obj)
    plots_mesh=Mesh()
    for plot in layout['plots']:
        x,y,z=plot['position'];w,d=plot['size']
        plots_mesh.box((x,y,z-.04),(w,d,.10),assets.mat('terre_gelee'))
        for sx in (-1,1):
            for sy in (-1,1):
                plots_mesh.cylinder((x+sx*w/2,y+sy*d/2,z),(x+sx*w/2,y+sy*d/2,z+.85),.085,.07,assets.mat('bois_vieux'),6)
                plots_mesh.box((x+sx*w/2,y+sy*d/2,z+.77),(.19,.19,.08),assets.mat('neige_givre'))
    oo=plots_mesh.object('Clairières de construction');move(oo,land);static.append(oo)
    ground=m.object('Socle_terrasses_chemin');move(ground,land);static.append(ground)
    # L'ancien piton voisin et ses remparts isolés sont supprimés : seule la citadelle domine.
    # Ajouts après les placements existants : leurs identifiants restent stables.
    for i,(x,y) in enumerate([(-20,5),(23,7),(-22,28),(20,30),(-38,20),(38,22)]):
        maison(1+i%5,city_houses[len(sites)+i])
    # Les lucarnes font désormais partie de chaque composition modulaire.
    for i,(x,y) in enumerate([(-12,-29),(11,-26),(-10,-12),(17,-8),(-26,1),(27,20)]):
        place('reserve_bois_tonneaux',x,y,42.2,i*47,category=props)
    for sx in (-1,1):
        for yy in (-68,-54,-29):torch(sx*2.7,yy,42.1)
    # Cailloux d'éboulis et congères raccordent les falaises au sol.
    detail=Mesh();decor_rng=random.Random(seed+502)
    for j in range(110):
        a=decor_rng.uniform(0,math.tau);rad=decor_rng.uniform(1.06,1.40)
        x=math.cos(a)*61*rad;y=math.sin(a)*52*rad
        if abs(x)<9 and y<0:continue
        if paysage.blocked_by_use(x,y,seed):continue
        z=float(terrain_height(x,y,seed));r=decor_rng.uniform(.35,2.0)
        detail.ico((x,y,z+r*.25),(r,r*.75,r*.7),assets.mat('roche_claire'),1)
        if j%3:detail.ico((x,y,z+r*.65),(r*.82,r*.65,r*.12),assets.mat('neige_givre'),1)
    oo=detail.object('Éboulis et neige au pied des falaises');move(oo,land);static.append(oo)
    # Densifier les abords de la place après les identifiants déjà présents.
    for i,plan in enumerate(city_houses[-4:]):maison((i+2)%6,plan)
    for o in static:clean_mesh(o)
    static_triangles=sum(tri_count(o) for o in static);export_fbx(path/(name+'.fbx'),static)
    # Ciel procédural à couches de nuages : fait partie du .blend, pas une image collée.
    world=bpy.data.worlds.new('Ciel de tempête');bpy.context.scene.world=world;world.use_nodes=True
    nodes=world.node_tree.nodes;links=world.node_tree.links;bg=nodes.get('Background');bg.inputs['Strength'].default_value=.48
    coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.8;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.72
    mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,1,3.2);links.new(coord.outputs['Normal'],mapping.inputs[0]);links.new(mapping.outputs[0],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[0].color=(.025,.04,.06,1);ramp.color_ramp.elements[1].position=.73;ramp.color_ramp.elements[1].color=(.42,.51,.57,1)
    links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bg.inputs['Color'])
    sun=bpy.data.lights.new('Trouée froide','SUN');sun.energy=2.0;sun.color=(.86,.90,1);sun.angle=.10
    so=bpy.data.objects.new('Lumière froide',sun);studio.objects.link(so);so.rotation_euler=tuple(math.radians(a) for a in (32,-25,-35))
    area=bpy.data.lights.new('Ciel diffus','AREA');area.energy=65000;area.shape='DISK';area.size=150;area.color=(.71,.79,.90)
    ao=bpy.data.objects.new('Remplissage du ciel',area);studio.objects.link(ao);ao.location=(30,-110,160);ao.rotation_euler=(Vector((0,0,40))-ao.location).to_track_quat('-Z','Y').to_euler()
    # Brume volumétrique, plus épaisse au fond de la vallée.
    fog=bpy.data.materials.new('Brume volumétrique');fog.use_nodes=True;nn=fog.node_tree.nodes;nn.clear();vo=nn.new('ShaderNodeVolumePrincipled');vo.inputs['Density'].default_value=.00065;vo.inputs['Color'].default_value=(.51,.64,.72,1);vo.inputs['Anisotropy'].default_value=.1
    output=nn.new('ShaderNodeOutputMaterial');fog.node_tree.links.new(vo.outputs['Volume'],output.inputs['Volume'])
    fogmesh=Mesh();fogmesh.box((0,130,300),(1800,1600,1000),fog);fo=fogmesh.object('Brume de vallée');move(fo,studio);fo.display_type='WIRE'
    # La brume se concentre en contrebas et laisse les façades proches lisibles.
    coord=nn.new('ShaderNodeTexCoord');separate=nn.new('ShaderNodeSeparateXYZ');height=nn.new('ShaderNodeMapRange')
    height.inputs['From Min'].default_value=-8;height.inputs['From Max'].default_value=60
    height.inputs['To Min'].default_value=.0035;height.inputs['To Max'].default_value=.00028
    fog.node_tree.links.new(coord.outputs['Object'],separate.inputs[0])
    fog.node_tree.links.new(separate.outputs['Z'],height.inputs['Value']);fog.node_tree.links.new(height.outputs['Result'],vo.inputs['Density'])
    for i,p in enumerate(smokes[::4]):
        for j in range(4):
            smoke=Mesh();q=p['position'];smoke.ico((q[0]+j*.35,q[1],q[2]+j*.85),( .25+j*.18,.3+j*.18,.5),fog,2)
            oo=smoke.object('Fumée '+str(i)+' '+str(j));move(oo,studio)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32 if quick else 64;sc.cycles.use_denoising=True
    sc.cycles.adaptive_threshold=.035;sc.cycles.adaptive_min_samples=16
    sc.cycles.max_bounces=6;sc.cycles.diffuse_bounces=3;sc.cycles.glossy_bounces=3;sc.cycles.transparent_max_bounces=4
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        sc.cycles.device='GPU'
    except Exception:pass
    sc.render.resolution_x=1600;sc.render.resolution_y=900;sc.render.resolution_percentage=65 if quick else 100
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.25
    sc.render.image_settings.file_format='PNG';sc.render.fps=24;sc.frame_start=1;sc.frame_end=240
    tree=bpy.data.node_groups.new('Halo des feux','CompositorNodeTree');sc.compositing_node_group=tree
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    rl=tree.nodes.new('CompositorNodeRLayers');glare=tree.nodes.new('CompositorNodeGlare');glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High';glare.inputs['Strength'].default_value=.18;out=tree.nodes.new('NodeGroupOutput');tree.links.new(rl.outputs['Image'],glare.inputs['Image']);tree.links.new(glare.outputs['Image'],out.inputs['Image'])
    cameras={}
    for label,position,target,lens in CAMERAS:
        c=bpy.data.cameras.new(label);o=bpy.data.objects.new(label,c);studio.objects.link(o);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.lens=lens;c.clip_end=2200;cameras[label]=o
    sc.camera=cameras['Citadelle'];sc.frame_set(1)
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.clip_end=2200
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path/(name+'.blend')),compress=True)
    triangles=static_triangles+sum(records[i['asset']]['triangles'][0] for i in instances)
    label=next((s['label'] for s in RECIPE['dispositions'] if s['id']==name),name)
    report={**{k:RECIPE[k] for k in ('biome','culture','typologie','annee')},'id':name,'label':label,'description':RECIPE['description'],'schema':4,'seed':seed,'instances':instances,'materials':matters(static),'config':{'sun':[.67,.79,1]},'building_count':sum(i['asset'].startswith('maison_') for i in instances),'tree_count':sum(i['asset'].startswith('sapin_') for i in instances),'triangles_lod0':triangles,'static_triangles':static_triangles,'anchors':[{'position':verts[i]} for i in (0,70,500,2600,13000,20000)],'smokes':smokes,'wheels':[],'torches':torches,'banners':banners,'center':[0,0],'camera_position':[148,-228,120],'camera_target':[0,7,67],'catalogue_sha256':hashlib.sha256((LIB/'catalogue.json').read_bytes()).hexdigest(),'simulation_connected':False}
    report['cameras']=[{'name':n,'position':list(p),'target':list(t),'lens':f} for n,p,t,f in CAMERAS]
    report['routes']=[{'id':r['id'],'width':r['width'],'points':[{'position':[p[0],p[1],float(terrain_height(p[0],p[1],seed))+.085 if r['ground'] else p[2]]} for p in r['points']]} for r in layout['routes']]
    report['plots']=layout['plots'];report['spawn']=layout['spawn'];report['forest']=layout['forest']
    write(path/(name+'.json'),report)
    for label in ([] if no_render else ['Citadelle'] if quick else cameras):
        sc.camera=cameras[label];sc.render.filepath=str(path/'renders'/('blender_'+label.lower()+'.png'));bpy.ops.render.render(write_still=True)
    print('CITADELLE_OK',name,len(instances),triangles,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['assets','scene','edition']);p.add_argument('--nom',default='eperon_des_veilleurs');p.add_argument('--graine',type=int,default=1407);p.add_argument('--rapide',action='store_true');p.add_argument('--sans-rendus',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.phase=='assets':library()
    elif a.phase=='edition':edition(a.nom)
    else:scene(a.nom,a.graine,a.rapide,a.sans_rendus)
