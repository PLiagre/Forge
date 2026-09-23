"""Point d'entrée Blender : bibliothèque partagée ou assemblage d'une variante."""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from local3d.atelier_v2 import assets
from local3d.atelier_v2.geometrie import Mesh, material, tri_count, export_fbx, MATS
from local3d.atelier_v2.plan import CONFIG, variant, make_plan, field, sample, river_x, water_distance, path_distance, fingerprint

OUT=ROOT/'local3d/v2'
TEXTURES=OUT/'textures'
LIBRARY=OUT/'bibliotheque'

def emit(message):print(message,flush=True)
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    MATS.clear()
def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
def move(obj,c):
    for old in list(obj.users_collection):old.objects.unlink(obj)
    c.objects.link(obj)

def build_library():
    reset();LIBRARY.mkdir(parents=True,exist_ok=True)
    records=[];objects=[]
    jobs=[]
    for style in CONFIG['styles']:
        for role in ('maison','atelier','auberge'):
            for i in range(6):jobs.append((f'{style}_{role}_{i}',lambda s=style,r=role,k=i:assets.building(s,r,k,TEXTURES),'batiment'))
        jobs.append((style+'_tour_0',lambda s=style:assets.building(s,'tour',0,TEXTURES),'repere'))
    kinds=sorted({k for v in CONFIG['variants'] for k in v['foliage']})
    for kind in kinds:
        for i in range(3):jobs.append((f'{kind}_{i}',lambda k=kind,j=i:assets.tree(k,j,TEXTURES),'arbre'))
    for kind in ('rocher','herbe','roseaux','buisson','sec','cloture','tonneau','caisse','charrette','etal','puits','barque','ble'):
        for i in range(3):jobs.append((f'{kind}_{i}',lambda k=kind,j=i:assets.prop(k,j,TEXTURES),'accessoire'))
    for name,builder,kind in jobs:
        emit('ASSET '+name)
        override=ROOT/'local3d/sources_v2'/(name+'.blend')
        if override.exists():
            wanted=[name+'_LOD'+str(i) for i in range(3)]
            with bpy.data.libraries.load(str(override),link=False) as (src,dst):
                if any(n not in src.objects for n in wanted):raise ValueError('Retouche sans ses trois LOD : '+str(override))
                dst.objects=wanted
            lods=dst.objects
            for o in lods:
                bpy.context.collection.objects.link(o)
                o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
                if any(abs(c)>.00001 for c in o.location) or any(abs(c)>.00001 for c in o.rotation_euler) or any(abs(c-1)>.00001 for c in o.scale):
                    raise ValueError('Appliquer les transformations de la retouche : '+o.name)
                for slot in o.material_slots:
                    if not slot.material:raise ValueError('Retouche sans matériau : '+name)
                    m=slot.material;base=m.name.rsplit('.',1)[0] if m.name[-3:].isdigit() else m.name
                    if base in MATS:slot.material=MATS[base]
                    else:m.name=base;MATS[base]=m
            emit('RETOUCHE '+name)
        else:
            mesh=builder();lods=[mesh.object(name+'_LOD'+str(i),i) for i in range(3)]
        for obj in lods:
            obj.asset_mark();obj.asset_data.description='Forge V2 • '+kind+' • '+name
        counts=[tri_count(o) for o in lods]
        if not counts[0] or not counts[0]>=counts[1]>=counts[2]>0:raise ValueError('LOD invalides : '+name)
        coordinates=np.array([v.co for v in lods[0].data.vertices])
        lo=coordinates.min(axis=0).tolist();hi=coordinates.max(axis=0).tolist()
        records.append({'id':name,'kind':kind,'triangles':counts,'bounds_min':lo,'bounds_max':hi})
        export_fbx(LIBRARY/(name+'.fbx'),lods)
        objects.extend(lods)
    bpy.data.libraries.write(str(LIBRARY/'Forge_Assets_V2.blend'),set(objects),path_remap='RELATIVE',fake_user=True,compress=True)
    mats=[]
    for m in sorted({s.material for o in objects for s in o.material_slots if s.material},key=lambda m:m.name):
        mats.append({'name':m.name,'texture':m.get('texture_id',m.name),'alpha':bool(m.get('alpha_clip',False)),
            'color':list(m.diffuse_color),'roughness':m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value})
    (LIBRARY/'catalogue.json').write_text(json.dumps({'schema':2,'assets':records,'materials':mats},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    emit(f'BIBLIOTHEQUE_OK assets={len(records)}')

def prepare_edit(name):
    reset();destination=ROOT/'local3d/sources_v2'/(name+'.blend')
    if destination.exists():raise ValueError('La retouche existe déjà : '+str(destination))
    wanted=[name+'_LOD'+str(i) for i in range(3)]
    with bpy.data.libraries.load(str(LIBRARY/'Forge_Assets_V2.blend'),link=False) as (src,dst):
        if any(n not in src.objects for n in wanted):raise ValueError('Asset inconnu : '+name)
        dst.objects=wanted
    for i,o in enumerate(dst.objects):
        c=collection('LOD '+str(i));c.objects.link(o)
        o.hide_render=i>0;o.hide_set(i>0)
    primary=dst.objects[0];primary.select_set(True);bpy.context.view_layer.objects.active=primary
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=(0,0,4)
                area.spaces.active.region_3d.view_distance=22
                area.spaces.active.shading.type='MATERIAL'
    bpy.context.scene.unit_settings.system='METRIC';bpy.ops.file.pack_all()
    destination.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
    emit('EDITION_PRETE '+str(destination))

def build_scene(name,quality):
    reset();v=variant(name);plan=make_plan(v);h=field(plan)
    path=OUT/'villages'/name;path.mkdir(parents=True,exist_ok=True)
    (path/'renders').mkdir(exist_ok=True)
    catalog=json.loads((LIBRARY/'catalogue.json').read_text(encoding='utf-8'))
    records={a['id']:a for a in catalog['assets']}
    with bpy.data.libraries.load(str(LIBRARY/'Forge_Assets_V2.blend'),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n.endswith('_LOD0')]
    prototypes={o.name[:-5]:o for o in dst.objects}
    for o in prototypes.values():
        for slot in o.material_slots:
            if slot.material:MATS[slot.material.name]=slot.material
    buildings=collection('01 • Architecture et métiers')
    nature=collection('02 • Végétation et rochers')
    props=collection('03 • Vie du village')
    landscape=collection('04 • Terrain, berges et ouvrages')
    studio=collection('05 • Caméras et lumière')
    rng=random.Random(v['seed']);instances=[]
    def place(asset,x,y,z=None,rotation=0,scale=(1,1,1),coll=props,label=None):
        if asset not in prototypes:raise ValueError('Asset absent : '+asset)
        o=prototypes[asset].copy();coll.objects.link(o)
        o.name=label or asset+'__'+str(len(instances))
        z=float(sample(h,x,y)) if z is None else z
        o.location=(x,y,z);o.rotation_euler.z=math.radians(rotation);o.scale=scale
        o['asset_id']=asset
        instances.append({'id':o.name,'asset':asset,'position':[float(x),float(y),float(z)],
            'rotation':float(rotation),'scale':list(scale),'category':coll.name[:2]})
        return o
    for b in plan['buildings']:
        place(b['asset'],b['x'],b['y'],b['height'],b['rotation'],b['scale'],buildings,b['id'])
    center_height=float(sample(h,20,-12))
    place(v['style']+'_tour_0',20,-12,center_height,scale=(.85,.85,1.15),coll=buildings,label='Repère central')
    # Relief avec UV continus et bord naturel, sans grille de couleurs par face.
    n=CONFIG['terrain_cells'];ext=CONFIG['extent_m'];axis=np.linspace(-ext/2,ext/2,n+1)
    x,y=np.meshgrid(axis,axis);points=np.stack((x,y,h),axis=-1).reshape(-1,3)
    faces=[]
    for j in range(n):
        for i in range(n):
            cx=(axis[i]+axis[i+1])/2;cy=(axis[j]+axis[j+1])/2
            limit=126+2.7*math.sin(math.atan2(cy,cx)*5)
            if math.hypot(cx,cy)<limit:
                a=j*(n+1)+i;faces.append((a,a+1,a+n+2,a+n+1))
    edge_count={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            edge=tuple(sorted((a,b)));edge_count[edge]=edge_count.get(edge,0)+1
    border=sorted({i for edge,count in edge_count.items() if count==1 for i in edge},key=lambda i:math.atan2(points[i,1],points[i,0]))
    # Projeter le contour de grille sur une courbe continue évite une tranche
    # en accordéon. La hauteur reste lue dans le même champ de relief.
    for i in border:
        a=math.atan2(points[i,1],points[i,0]);r=126+2.7*math.sin(a*5)
        px,py=r*math.cos(a),r*math.sin(a)
        points[i]=(px,py,float(sample(h,px,py)))
    mesh=bpy.data.meshes.new('Relief continu');mesh.from_pydata(points.tolist(),[],faces);mesh.update()
    terrain=bpy.data.objects.new('Terrain_'+name,mesh);landscape.objects.link(terrain)
    terrain_mat=material('terrain_'+name,TEXTURES)
    if not (TEXTURES/('terrain_'+name+'_BaseColor.png')).is_file():raise ValueError('Texture terrain absente')
    mesh.materials.append(terrain_mat);uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        p.use_smooth=True
        for li in p.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co.x/ext+.5,co.y/ext+.5)
    static=Mesh();stone=material('pierre_ocre' if v['biome']=='aride' else 'pierre_grise',TEXTURES)
    wood=material('bois',TEXTURES);light=material('bois_clair',TEXTURES)
    # La tranche du terrain descend sans trou jusqu'au socle.
    skirt=Mesh();skirtmat=material('roche_ocre' if v['biome']=='aride' else 'roche',TEXTURES)
    for a,b in zip(border,border[1:]+border[:1]):
        aa=points[a];bb=points[b]
        aa2=aa[:2]*(1+5/max(1,np.linalg.norm(aa[:2])))
        bb2=bb[:2]*(1+5/max(1,np.linalg.norm(bb[:2])))
        skirt.surface([tuple(aa),tuple(bb),(bb2[0],bb2[1],-6),(aa2[0],aa2[1],-6)],[(0,3,2,1)],skirtmat)
    skirtobj=skirt.object('Tranche du paysage');move(skirtobj,landscape)
    # Pont et accès : une traversée lisible, avec tablier, garde-corps et piles.
    if v['water']!='oasis':
        cy=-28;cx=float(river_x(cy));half=v['water_width']+4.4
        deck=max(float(sample(h,cx-half,cy)),float(sample(h,cx+half,cy)))+.40
        for i in range(int(half*2/.4)):
            xx=cx-half+(i+.5)*.4
            static.box((xx,cy,deck),(.385,4.5,.22),stone if v['style']=='pierre' else light)
        for side in (-1,1):
            static.beam((cx-half,cy+side*2.2,deck+1.0),(cx+half,cy+side*2.2,deck+1.0),.14,wood)
            for i in range(int(half*2/2)+1):
                xx=cx-half+i*2
                static.box((xx,cy+side*2.2,deck+.5),(.16,.16,1.1),wood)
        for xx in np.linspace(cx-half+2,cx+half-2,4):
            for yy in (cy-1.6,cy+1.6):static.box((float(xx),yy,(deck-1.4)/2),(.55,.7,deck+1.4),stone)
        for side in (-1,1):
            x0=cx+side*half;x1=x0+side*4
            static.surface([(x0,cy-2.2,deck),(x0,cy+2.2,deck),(x1,cy+2.2,float(sample(h,x1,cy))),
                (x1,cy-2.2,float(sample(h,x1,cy)))],[(0,1,2,3)],stone if v['style']=='pierre' else light)
        # Ponton et barques à l'abri du pont.
        dx=float(river_x(10))+v['water_width']-1
        dz=1.25
        for i in range(18):static.box((dx-2,4+i*.32,dz),(5,.3,.15),wood)
        for xx in (dx-4,dx):
            for yy in (4,9):static.box((xx,yy,.8),(.2,.2,2.7),wood)
        place('barque_0',dx-5.5,7,.05,rotation=8,coll=props)
        if v['water']=='fleuve':place('barque_1',dx-9,14,.06,rotation=-14,scale=(1.5,1.5,1.3),coll=props)
    # Eau présente dans chaque variante, avec lit et berges dérivés du même relief.
    water=Mesh();watermat=material('eau',TEXTURES,rough=.19)
    bs=watermat.node_tree.nodes['Principled BSDF'];bs.inputs['IOR'].default_value=1.333
    bs.inputs['Transmission Weight'].default_value=.23
    if v['water']=='oasis':
        vs=[(-39,-22,.12)]+[(-39+18*math.cos(i*math.tau/100),-22+29*math.sin(i*math.tau/100),.12) for i in range(100)]
        water.surface(vs,[(0,i+1,(i+1)%100+1) for i in range(100)],watermat)
    else:
        for yy in np.arange(-130,130,1.0):
            xx=float(river_x(yy));xx2=float(river_x(yy+1));ww=v['water_width']
            quad=[(xx-ww,yy,.12),(xx+ww,yy,.12),(xx2+ww,yy+1,.12),(xx2-ww,yy+1,.12)]
            # L'eau s'arrête sur la même découpe que la terre.
            if not all(math.hypot(q[0],q[1])<126+2.7*math.sin(math.atan2(q[1],q[0])*5) for q in quad):continue
            water.surface(quad,[(0,1,2,3)],watermat)
    waterobj=water.object('Eau_'+name);move(waterobj,landscape)
    # Aménagements de place, marché et objets aux portes, posés sur le sol réel.
    for i in range(7):
        a=i*math.tau/7;xx=20+math.cos(a)*9;yy=-12+math.sin(a)*9
        place('etal_'+str(i%3),xx,yy,rotation=math.degrees(a)+90,scale=(.85,.85,.85))
    place('puits_0',13,-10,scale=(.75,.75,.75))
    for i,b in enumerate(plan['buildings']):
        a=math.radians(b['rotation']);front=np.array([math.sin(a),-math.cos(a)]);side=np.array([math.cos(a),math.sin(a)])
        p=np.array([b['x'],b['y']])+front*(b['depth']/2+1)+side*(b['width']/2-.6)
        place('tonneau_'+str(i%3),*p,rotation=b['rotation'])
        if i%2==0:place('caisse_'+str(i%3),*(p+side*1.1),rotation=b['rotation'])
        if i%7==0:place('charrette_'+str(i%3),*(p+front*2.3),rotation=b['rotation']+18,scale=(.85,.85,.85))
        if i%2==0:
            # Cour arrière et petit potager : les espaces entre maisons ont un usage.
            rear=np.array([b['x'],b['y']])-front*(b['depth']/2+3)
            for t in (-1,0,1):
                point=rear+side*t*2.1-front*1.7
                place('cloture_'+str(i%3),*point,rotation=b['rotation'],scale=(.7,.7,.85))
            for t in (-1,0,1):
                point=rear+side*t*1.15
                coords=[point+side*dx+front*dy for dx,dy in [(-.42,-1.25),(.42,-1.25),(.42,1.25),(-.42,1.25)]]
                static.surface([(float(q[0]),float(q[1]),float(sample(h,*q))+.03) for q in coords],[(0,1,2,3)],material('terre_culture',TEXTURES))
                for dy in (-.7,.2,.9):place('herbe_'+str(t%3),*(point+front*dy),scale=(.7,.7,.8),coll=nature)
    # Les recherches utilisent un champ de distance, au lieu de recalculer
    # toutes les routes pour chaque brindille ou arbre.
    distances=path_distance(x,y,plan['roads'])
    def free(xx,yy,margin=1,trees=False):
        if math.hypot(xx,yy)>120 or water_distance(xx,yy,v)<margin:return False
        if sample(distances,xx,yy)<margin:return False
        if math.hypot(xx-20,yy+12)<13+margin:return False
        if any(math.hypot(xx-b['x'],yy-b['y'])<b['radius']+margin for b in plan['buildings']):return False
        return True
    # Parcelles cultivées et vergers bordés de clôtures.
    plots=[]
    for xx,yy in [(77,-75),(47,-86),(3,-89),(86,-38),(88,2),(62,49),(-12,30),(-16,-67)]:
        if not all(free(xx+dx,yy+dy,.3) for dx in (-5,5) for dy in (-7,7)):continue
        heights=[float(sample(h,xx+dx,yy+dy)) for dx in (-5,5) for dy in (-7,7)]
        if max(heights)-min(heights)>2.5:continue
        plots.append((xx,yy))
        for i in range(12):
            y0=yy-7+i*1.25
            mat=material('terre_culture' if i%2 else 'paille',TEXTURES)
            coords=[(xx-5,y0),(xx+5,y0),(xx+5,y0+.8),(xx-5,y0+.8)]
            static.surface([(a,b,float(sample(h,a,b))+.035) for a,b in coords],[(0,1,2,3)],mat)
            for j in range(3):place('ble_'+str(j),xx-3+j*3,y0+.4,scale=(1,1,.7 if v['biome']=='aride' else 1),coll=nature)
        for side in (-1,1):
            for i in range(5):place('cloture_'+str(i%3),xx+side*5.4,yy-6+i*3,rotation=90)
    clusters=[(-88,45),(-87,-45),(87,58),(94,-37),(7,86),(49,-104)]
    tree_positions=[];attempts=0
    while len(tree_positions)<v['trees'] and attempts<v['trees']*150:
        attempts+=1
        if rng.random()<.84:
            cx,cy=rng.choice(clusters);xx=rng.gauss(cx,20);yy=rng.gauss(cy,20)
        else:xx=rng.uniform(-117,117);yy=rng.uniform(-117,117)
        if v['biome']=='aride' and rng.random()<.75:
            a=rng.uniform(0,6.28);r=rng.uniform(1.12,2.4);xx=-39+math.cos(a)*18*r;yy=-22+math.sin(a)*29*r
        if not free(xx,yy,3.2,True):continue
        if any(math.hypot(xx-a,yy-b)<4.3 for a,b in tree_positions):continue
        if any(abs(xx-a)<8 and abs(yy-b)<10 for a,b in plots):continue
        zz=float(sample(h,xx,yy))
        if v['biome']=='alpin' and zz>35:continue
        k=rng.choice(v['foliage']);j=rng.randrange(3);scale=rng.uniform(.7,1.2)
        place(k+'_'+str(j),xx,yy,zz,rng.uniform(0,360),(scale,scale,scale),nature)
        tree_positions.append((xx,yy))
    if len(tree_positions)!=v['trees']:raise ValueError('Peuplement forestier incomplet')
    for kind,count,margin in [('rocher',v['rocks'],.5),('sec' if v['biome']=='aride' else 'herbe',v['groundcover'],.3),('buisson',100,.6)]:
        made=0
        for attempt in range(count*40):
            if made>=count:break
            xx=rng.uniform(-120,120);yy=rng.uniform(-120,120)
            if not free(xx,yy,margin):continue
            if any(abs(xx-a)<6 and abs(yy-b)<8 for a,b in plots):continue
            scale=rng.uniform(.65,1.35)
            if kind=='rocher':
                zz=float(sample(h,xx,yy));scale*=1+max(0,zz-9)*.16
            j=2 if kind=='rocher' and v['biome']=='aride' else rng.randrange(3)
            place(kind+'_'+str(j),xx,yy,rotation=rng.uniform(0,360),scale=(scale,scale,scale),coll=nature)
            made+=1
        if made!=count:raise ValueError('Décor incomplet : '+kind)
    # Rideaux de roseaux sur les berges, pas dans le chenal.
    for i in range(170):
        yy=rng.uniform(-115,115)
        if v['water']=='oasis':
            a=rng.uniform(0,6.28);xx=-39+math.cos(a)*19.8;yy=-22+math.sin(a)*31.5
        else:xx=float(river_x(yy))+rng.choice((-1,1))*(v['water_width']+rng.uniform(.8,2.1))
        if math.hypot(xx,yy)>119 or sample(distances,xx,yy)<1.0:continue
        place('roseaux_'+str(i%3),xx,yy,rotation=rng.uniform(0,360),scale=(.7,.7,.7),coll=nature)
    built=static.object('Ouvrages_'+name);move(built,landscape)
    static_objects=[terrain,waterobj,built,skirtobj]
    export_fbx(path/'paysage.fbx',static_objects)
    static_triangles=sum(tri_count(o) for o in static_objects)
    count=sum(records[i['asset']]['triangles'][0] for i in instances)+static_triangles
    if count>CONFIG['budget_triangles']:raise ValueError(f'Budget dépassé {count}')
    for o in prototypes.values():bpy.data.objects.remove(o,do_unlink=True)
    # Éclairage et deux cadrages : territoire entier, puis lecture des détails.
    world=bpy.data.worlds.new('Ciel');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.62,.74,.91,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.45
    scene=bpy.context.scene;scene.world=world
    bg=Mesh();bg.box((0,0,-6.5),(2000,2000,.2),material('fond_'+name,TEXTURES,color=(.20,.23,.18) if v['biome']!='aride' else (.36,.25,.15)))
    back=bg.object('Fond de présentation');move(back,studio)
    bpy.ops.object.light_add(type='SUN',location=(50,-80,160));sun=bpy.context.object
    sun.data.energy=2.2;sun.data.angle=.10;sun.data.color=v['sun'];sun.rotation_euler=(.48,-.45,-.5);move(sun,studio)
    bpy.ops.object.light_add(type='AREA',location=(-80,-30,130));fill=bpy.context.object
    fill.data.energy=28000;fill.data.shape='DISK';fill.data.size=110
    fill.rotation_euler=(Vector((0,0,0))-fill.location).to_track_quat('-Z','Y').to_euler();move(fill,studio)
    cameras=[]
    for title,location,target,size in [('Territoire',(180,-230,215),(0,8,7),315),('Village',(112,-151,110),(15,-6,7),150)]:
        bpy.ops.object.camera_add(location=location);cam=bpy.context.object;cam.name=title
        cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size;cam.data.clip_end=2000
        move(cam,studio);cameras.append(cam)
    scene.camera=cameras[1];scene.render.engine='CYCLES';scene.cycles.samples=20 if quality=='apercu' else 64
    scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
    cp=bpy.context.preferences.addons['cycles'].preferences
    try:
        cp.compute_device_type='OPTIX';cp.get_devices()
        for device in cp.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    except Exception as exc:emit('Rendu CPU : '+str(exc))
    scene.render.resolution_x=1280 if quality=='apercu' else 1920
    scene.render.resolution_y=840 if quality=='apercu' else 1260
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.unit_settings.system='METRIC'
    scene['description']=v['label']+' • '+v['subtitle']+' • revue graphique V2'
    scene['simulation_connected']=False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=2000
                area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False
    bpy.ops.object.select_all(action='DESELECT')
    # Les sorties portent leurs mesures, leur recette et leurs dépendances.
    used_materials=sorted({s.material for c in (buildings,nature,props,landscape) for o in c.objects if o.type=='MESH' for s in o.material_slots if s.material},key=lambda m:m.name)
    scene_materials=[{'name':m.name,'texture':m.get('texture_id',m.name),'alpha':bool(m.get('alpha_clip',False)),
        'color':list(m.diffuse_color),'roughness':m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value} for m in used_materials]
    manifest={'schema':2,'id':name,'label':v['label'],'biome':v['biome'],'style':v['style'],'description':v['subtitle'],
        'config':v,'plan_sha256':fingerprint(plan),'instances':instances,'building_count':len(buildings.objects),
        'tree_count':len(tree_positions),'fields':len(plots),'static_triangles':static_triangles,'triangles_lod0':count,
        'budget_triangles':CONFIG['budget_triangles'],'materials':scene_materials,
        'water_mode':v['water'],'terrain_extent_m':ext,'simulation_connected':False,'artistic_approval':'à examiner',
        'cameras':[{'position':list(c.location),'rotation':list(c.rotation_euler),'ortho':c.data.ortho_scale} for c in cameras]}
    (path/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (path/'scene.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    np.save(path/'hauteurs.npy',h)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path/(name+'.blend')),compress=True)
    for i,cam in enumerate(cameras):
        scene.camera=cam;scene.render.filepath=str(path/'renders'/('territoire.png' if i==0 else 'village.png'))
        bpy.ops.render.render(write_still=True)
    emit(f'SCENE_OK {name} triangles={count} instances={len(instances)}')

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['assets','scene','edition']);parser.add_argument('--variante');parser.add_argument('--asset');parser.add_argument('--qualite',default='final',choices=['apercu','final'])
    a=parser.parse_args(args)
    if a.phase=='assets':build_library()
    elif a.phase=='edition':prepare_edit(a.asset)
    else:build_scene(a.variante,a.qualite)
