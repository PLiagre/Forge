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
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.citadelle import assets
from local3d.atelier_v2.geometrie import Mesh,MATS,material,export_fbx,tri_count
from local3d.alpin.fabriquer import reset,coll,move,matters,write
OUT=ROOT/'local3d/citadelle/sorties';LIB=OUT/'bibliotheque';TEX=OUT/'textures'
RECIPE=json.loads((Path(__file__).parent/'recette.json').read_text(encoding='utf-8'))

def clean_mesh(o):
    # Les pointes de cônes ont des faces d'aire nulle que Unity supprime à l'import.
    # Les retirer à la source garde le catalogue et le FBX strictement comparables.
    bm=bmesh.new();bm.from_mesh(o.data)
    if o.name.startswith('montagne_'):bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
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
                    else:slot.material.name=key;MATS[key]=slot.material
        else:
            mesh=builder();lods=[mesh.object(name+'_LOD'+str(i),i) for i in range(3)]
        for o in lods:
            clean_mesh(o)
            o.asset_mark();o.asset_data.description='Citadelle alpine • module en mètres • '+name
            if name.startswith('montagne_'):
                for p in o.data.polygons:p.use_smooth=True
        counts=[tri_count(o) for o in lods]
        if not counts[0]>=counts[1]>=counts[2]>0:raise ValueError('LOD invalides : '+name)
        vs=np.array([v.co for v in lods[0].data.vertices]);records.append({'id':name,'kind':kind,'triangles':counts,'bounds_min':vs.min(axis=0).tolist(),'bounds_max':vs.max(axis=0).tolist()})
        export_fbx(LIB/(name+'.fbx'),lods);objects.extend(lods)
    bpy.data.libraries.write(str(LIB/'Kit_Citadelle.blend'),set(objects),path_remap='RELATIVE',fake_user=True,compress=True)
    write(LIB/'catalogue.json',{'schema':3,'assets':records,'materials':matters(objects)})
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
    # Socle et vallée purement visuels ; aucune donnée du monde n'est modifiée.
    phase=(seed%37)/19
    v=-10+2.4*np.sin(x*.032+phase)*np.cos(y*.028)+1.2*np.sin(x*.13+y*.061)
    hill=34*np.exp(-((x+100)/95)**2-((y+100)/70)**2)+20*np.exp(-((x-145)/70)**2-((y-25)/100)**2)
    road=46*np.exp(-(x/22)**2-((y+110)/65)**2)
    return v+hill+road

def scene(name,seed,quick=False):
    reset();assets.TEX=TEX;rng=random.Random(seed);alt=seed!=RECIPE['dispositions'][0]['seed']
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
        light=bpy.data.lights.new('Feu de torche','POINT');light.energy=125;light.color=(1,.30,.045);light.shadow_soft_size=.45
        l=bpy.data.objects.new('Lueur '+o.name,light);studio.objects.link(l);l.location=(x,y,z+3.1)
        light.driver_add('energy').driver.expression='125+16*sin(frame*.63+'+str(len(torches))+')+10*sin(frame*1.3)'
    def banner(x,y,z,rotation=0):
        o=place('banniere',x,y,z,rotation,category=props);banners.append(o.name)
        # Déplacement géométrique du tissu, attaché en haut et à la hampe.
        o.data=o.data.copy();o.shape_key_add(name='Repos');key=o.shape_key_add(name='Rafale')
        for v in key.data:
            p=v.co
            if p.x>.08 and 3.15<p.z<7.05:p.y+=.42*math.sin(p.x*2.7+p.z*1.8)*min(1,p.x)*max(0,(7-p.z)/3.8)
        key.driver_add('value').driver.expression='.5+.5*sin(frame*.14+'+str(len(banners))+')'
    # Socle : plateau fermé, falaise instanciée sur son pourtour.
    m=Mesh();n=72;top=[];bottom=[]
    for i in range(n):
        a=i*math.tau/n;r=1+.025*math.sin(a*9+seed);top.append((math.cos(a)*53*r,math.sin(a)*44*r,42));bottom.append((math.cos(a)*62*r,math.sin(a)*54*r,-8))
    m.surface(top,[tuple(range(n))],assets.mat('neige_ombre'))
    for i in range(n):j=(i+1)%n;m.surface([bottom[i],bottom[j],top[j],top[i]],[(0,1,2,3)],assets.mat('roche_noire'))
    for j in range(42):
        a=j*math.tau/42;rr=1+rng.uniform(-.025,.025)
        place('falaise_'+str(j%4),math.cos(a)*51*rr,math.sin(a)*43*rr,-7,math.degrees(a),scale=(1.6,1.4,2.35+rng.uniform(-.12,.08)),category=nature)
    # Terrasse haute et escalier la reliant à la place.
    m.box((0,20,44.5),(34,39,5),assets.mat('basalte'));m.box((0,20,47.05),(34,39,.12),assets.mat('neige_ombre'))
    place('escalier',0,-8,42,scale=(1,1,.83))
    # Cathédrale assemblée : trois travées, façade, deux clochers, arcs-boutants.
    church_x=-5 if alt else 0;church_y=7 if alt else 8;cz=47.2
    for yy in (church_y+6,church_y+18):place('cathedrale_nef_12m',church_x,yy,cz)
    place('cathedrale_facade',church_x,church_y,cz)
    for sx in (-1,1):
        place('cathedrale_clocher',church_x+sx*11,church_y+1,cz,scale=(.82,.82,1))
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
    for i,(x,y) in enumerate(sites):
        k=rng.randrange(6);rotation=rng.choice((-8,0,7))+(90 if x<-28 else -90 if x>28 else 0);s=rng.uniform(.85,1.04)
        place('maison_gothique_'+str(k),x,y,42.15,rotation,(s,s,s));h=5.6+(k%3)*1.2;rise=5.5+k*.18
        aa=math.radians(rotation);xx=(6.2+k*.36)*.28*s;yy=(7+k%3)*.24*s
        smokes.append({'position':[x+xx*math.cos(aa)-yy*math.sin(aa),y+xx*math.sin(aa)+yy*math.cos(aa),42.15+(h+rise*.65+1.85)*s]})
        if i%3==0:torch(x,y-4.2,42.2)
    for yy in range(-35,2,7):place('paves',0,yy,42.16,scale=(1.3,1,1),category=props)
    for x in (-34,-20,20,34):place('garde',x,-32,54.2,180,category=props)
    # Petit hameau en contrebas et forêt continue, séparés de la ville haute.
    for i in range(15):
        x=rng.uniform(-125,-70);y=rng.uniform(-68,-12);z=float(terrain_height(x,y,seed))
        place('maison_gothique_'+str(rng.randrange(6)),x,y,z,rng.uniform(-30,25),(.75,.75,.78))
    # Terrain large : aucune tranche circulaire visible dans la composition.
    n=160;extent=800;axis=np.linspace(-extent/2,extent/2,n+1);xx,yy=np.meshgrid(axis,axis);hh=terrain_height(xx,yy,seed)
    verts=np.stack((xx,yy,hh),axis=-1).reshape(-1,3).tolist();terrain=Mesh()
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;ids=(a,a+1,a+n+2,a+n+1);terrain.surface([verts[k] for k in ids],[(0,1,2,3)],assets.mat('neige_ombre'))
    terr=terrain.object('Terrain_vallee');move(terr,land);static.append(terr)
    for i in range(1800):
        x=rng.uniform(-290,290);y=rng.uniform(-175,260)
        if (x/66)**2+(y/57)**2<1.15 or abs(x)<10 and y<-40 or -136<x<-61 and -80<y<2:continue
        z=float(terrain_height(x,y,seed));s=rng.uniform(.7,1.7)
        o=place('sapin_neige_'+str(i%3),x,y,z,rng.uniform(0,360),(s,s,s),nature)
        if i%7==0:o.driver_add('rotation_euler',0).driver.expression='.009*sin(frame*.08+'+str(i)+')'
    # Montagnes éloignées, asset partagé et échelles indépendantes.
    for i,(x,y,sx,sz) in enumerate([(-235,230,1.1,.82),(-405,315,1.8,.97),(200,260,1.3,.89),(385,340,1.7,1.05),(-80,440,1.4,.80),(80,480,1.6,.92),(-290,10,.85,.60)]):
        place('montagne_'+str(i%3),x+(20 if alt else 0),y,-22,i*53+(17 if alt else 0),(sx,sx,sz),nature)
    # Chemin d'accès au pont : hauteur raccordée au tablier.
    for j in range(70):
        y=-85-j*1.5;y2=y-1.5;x=math.sin((y+85)*.037)*12;x2=math.sin((y2+85)*.037)*12
        def roadz(xx,yy):return max(float(terrain_height(xx,yy,seed))+.12,42-(max(0,-yy-85))*.34)
        z=roadz(x,y);z2=roadz(x2,y2)
        m.surface([(x-3,y,z),(x+3,y,z),(x2+3,y2,z2),(x2-3,y2,z2)],[(0,1,2,3)],assets.mat('sol_pave'))
        for side in (-1,1):m.beam((x+side*3.3,y,z+.4),(x2+side*3.3,y2,z2+.4),.65,assets.mat('neige_givre'))
    ground=m.object('Socle_terrasses_chemin');move(ground,land);static.append(ground)
    # Deux sentinelles au premier plan donnent l'échelle humaine.
    for i in range(3):place('rempart_10m',39+i*9,-82,49,0,scale=(.9,1,.5))
    for i in range(3):place('garde',42+i*7,-82,55.2,20,category=props)
    torch(40,-83,55);torch(58,-83,55);banner(60,-81,56,rotation=15)
    for i in range(6):place('falaise_'+str(i%4),40+i*4,-80,5,25,(1.3,1.8,2.5),nature)
    for o in static:clean_mesh(o)
    static_triangles=sum(tri_count(o) for o in static);export_fbx(path/(name+'.fbx'),static)
    # Ciel procédural à couches de nuages : fait partie du .blend, pas une image collée.
    world=bpy.data.worlds.new('Ciel de tempête');bpy.context.scene.world=world;world.use_nodes=True
    nodes=world.node_tree.nodes;links=world.node_tree.links;bg=nodes.get('Background');bg.inputs['Strength'].default_value=.48
    coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.8;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.72
    mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,1,3.2);links.new(coord.outputs['Normal'],mapping.inputs[0]);links.new(mapping.outputs[0],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[0].color=(.025,.04,.06,1);ramp.color_ramp.elements[1].position=.73;ramp.color_ramp.elements[1].color=(.42,.51,.57,1)
    links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bg.inputs['Color'])
    sun=bpy.data.lights.new('Trouée froide','SUN');sun.energy=1.4;sun.color=(.67,.79,1);sun.angle=.15
    so=bpy.data.objects.new('Lumière froide',sun);studio.objects.link(so);so.rotation_euler=tuple(math.radians(a) for a in (32,-25,-35))
    area=bpy.data.lights.new('Ciel diffus','AREA');area.energy=90000;area.shape='DISK';area.size=150;area.color=(.66,.77,.86)
    ao=bpy.data.objects.new('Remplissage du ciel',area);studio.objects.link(ao);ao.location=(30,-110,160);ao.rotation_euler=(Vector((0,0,40))-ao.location).to_track_quat('-Z','Y').to_euler()
    # Brume volumétrique, plus épaisse au fond de la vallée.
    fog=bpy.data.materials.new('Brume volumétrique');fog.use_nodes=True;nn=fog.node_tree.nodes;nn.clear();vo=nn.new('ShaderNodeVolumePrincipled');vo.inputs['Density'].default_value=.00065;vo.inputs['Color'].default_value=(.51,.64,.72,1);vo.inputs['Anisotropy'].default_value=.1
    output=nn.new('ShaderNodeOutputMaterial');fog.node_tree.links.new(vo.outputs['Volume'],output.inputs['Volume'])
    fogmesh=Mesh();fogmesh.box((0,130,300),(1800,1600,1000),fog);fo=fogmesh.object('Brume de vallée');move(fo,studio);fo.display_type='WIRE'
    for i,p in enumerate(smokes[::4]):
        for j in range(4):
            smoke=Mesh();q=p['position'];smoke.ico((q[0]+j*.35,q[1],q[2]+j*.85),( .25+j*.18,.3+j*.18,.5),fog,2)
            oo=smoke.object('Fumée '+str(i)+' '+str(j));move(oo,studio)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32 if quick else 72;sc.cycles.use_denoising=True
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
    for label,position,target,lens in [('Citadelle',(148,-228,120),(0,7,67),43),('Porte',(44,-109,69),(0,-21,62),39),('Cathedrale',(63,-81,84),(0,12,68),43)]:
        c=bpy.data.cameras.new(label);o=bpy.data.objects.new(label,c);studio.objects.link(o);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.lens=lens;c.clip_end=2200;cameras[label]=o
    sc.camera=cameras['Citadelle'];sc.frame_set(1)
    for screen in bpy.data.screens:
        for ar in screen.areas:
            if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.clip_end=2200
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path/(name+'.blend')),compress=True)
    triangles=static_triangles+sum(records[i['asset']]['triangles'][0] for i in instances)
    label=next((s['label'] for s in RECIPE['dispositions'] if s['id']==name),name)
    report={**{k:RECIPE[k] for k in ('biome','culture','typologie','annee')},'id':name,'label':label,'description':RECIPE['description'],'schema':4,'seed':seed,'instances':instances,'materials':matters(static),'config':{'sun':[.67,.79,1]},'building_count':sum(i['asset'].startswith('maison_') for i in instances),'tree_count':sum(i['asset'].startswith('sapin_') for i in instances),'triangles_lod0':triangles,'static_triangles':static_triangles,'anchors':[{'position':verts[i]} for i in (0,70,500,2600,13000,20000)],'smokes':smokes,'wheels':[],'torches':torches,'banners':banners,'center':[0,0],'camera_position':[148,-228,120],'camera_target':[0,7,67],'catalogue_sha256':hashlib.sha256((LIB/'catalogue.json').read_bytes()).hexdigest(),'simulation_connected':False}
    write(path/(name+'.json'),report)
    for label in (['Citadelle'] if quick else cameras):
        sc.camera=cameras[label];sc.render.filepath=str(path/'renders'/('blender_'+label.lower()+'.png'));bpy.ops.render.render(write_still=True)
    print('CITADELLE_OK',name,len(instances),triangles,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['assets','scene','edition']);p.add_argument('--nom',default='eperon_des_veilleurs');p.add_argument('--graine',type=int,default=1407);p.add_argument('--rapide',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.phase=='assets':library()
    elif a.phase=='edition':edition(a.nom)
    else:scene(a.nom,a.graine,a.rapide)
