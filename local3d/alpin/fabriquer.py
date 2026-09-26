"""Bibliothèque alpine et scènes animées fabriquées dans Blender."""
import argparse
import json
import math
import random
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.alpin.paysage import RECIPE,make_plan,field,sample,river_x
from local3d.alpin import assets
from local3d.atelier_v2 import assets as base
from local3d.atelier_v2.geometrie import Mesh,material,MATS,tri_count,export_fbx
from local3d.atelier_v2.plan import path_distance,fingerprint

OUT=ROOT/'local3d/alpin/sorties';LIB=OUT/'bibliotheque';TEX=OUT/'textures'
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;MATS.clear()
def coll(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)
def matters(objects):
    mats={s.material for o in objects if o.type=='MESH' for s in o.material_slots if s.material}
    return [{'name':m.name,'texture':m.get('texture_id',m.name),'alpha':bool(m.get('alpha_clip',False)),
             'color':list(m.diffuse_color),'roughness':m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value} for m in sorted(mats,key=lambda m:m.name)]
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def library():
    reset();LIB.mkdir(parents=True,exist_ok=True);jobs=[];records=[];objects=[]
    for role in ('maison','atelier','auberge'):
        for i in range(6):jobs.append((f'alpin_{role}_{i}',lambda r=role,k=i:assets.building(r,k,TEX),'batiment'))
    jobs.append(('alpin_tour_0',lambda:assets.building('tour',0,TEX),'repere'))
    for kind in ('sapin','meleze'):
        for i in range(3):jobs.append((f'{kind}_{i}',lambda k=kind,j=i:base.tree(k,j,TEX),'arbre'))
    for kind in ('rocher','herbe','roseaux','buisson','cloture','tonneau','caisse','charrette','etal','puits','ble'):
        for i in range(3):jobs.append((f'{kind}_{i}',lambda k=kind,j=i:base.prop(k,j,TEX),'accessoire'))
    for kind in ('roue_moulin','buches','banc','abreuvoir','lanterne','fleurs','foin','linge','muret'):
        jobs.append((kind,lambda k=kind:assets.extra(k,TEX),'module'))
    for name,builder,kind in jobs:
        override=ROOT/'local3d/alpin/sources'/(name+'.blend')
        if override.exists():
            wanted=[name+'_LOD'+str(i) for i in range(3)]
            with bpy.data.libraries.load(str(override),link=False) as (src,dst):
                if any(n not in src.objects for n in wanted):raise ValueError('Retouche sans ses trois LOD : '+name)
                dst.objects=wanted
            lods=dst.objects
            for o in lods:
                bpy.context.collection.objects.link(o);o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
                if any(abs(v)>.00001 for v in o.location) or any(abs(v)>.00001 for v in o.rotation_euler) or any(abs(v-1)>.00001 for v in o.scale):raise ValueError('Transformations non appliquées : '+name)
                for slot in o.material_slots:
                    if not slot.material:raise ValueError('Matériau absent : '+name)
                    m=slot.material;key=m.name.rsplit('.',1)[0] if m.name[-3:].isdigit() else m.name
                    if key in MATS:slot.material=MATS[key]
                    else:m.name=key;MATS[key]=m
            print('SOURCE_REPRISE',name,flush=True)
        else:
            mesh=builder()
            if name.startswith('meleze'):
                mesh.materials=[material('aiguilles_meleze',TEX,alpha=True) if m.name=='aiguilles' else m for m in mesh.materials]
            lods=[mesh.object(name+'_LOD'+str(i),i) for i in range(3)]
        for o in lods:o.asset_mark();o.asset_data.description='Kit alpin réutilisable • '+name
        counts=[tri_count(o) for o in lods]
        if not counts[0]>=counts[1]>=counts[2]>0:raise ValueError('LOD invalides : '+name)
        vs=np.array([v.co for v in lods[0].data.vertices])
        records.append({'id':name,'kind':kind,'triangles':counts,'bounds_min':vs.min(axis=0).tolist(),'bounds_max':vs.max(axis=0).tolist()})
        export_fbx(LIB/(name+'.fbx'),lods);objects.extend(lods)
    bpy.data.libraries.write(str(LIB/'Kit_Alpin.blend'),set(objects),path_remap='RELATIVE',fake_user=True,compress=True)
    write(LIB/'catalogue.json',{'schema':3,'assets':records,'materials':matters(objects)})
    print('KIT_ALPIN_OK',len(records),flush=True)

def edition(name):
    reset();destination=ROOT/'local3d/alpin/sources'/(name+'.blend')
    if destination.exists():raise ValueError('La source existe déjà : '+str(destination))
    wanted=[name+'_LOD'+str(i) for i in range(3)]
    with bpy.data.libraries.load(str(LIB/'Kit_Alpin.blend'),link=False) as (src,dst):
        if any(n not in src.objects for n in wanted):raise ValueError('Asset inconnu : '+name)
        dst.objects=wanted
    for i,o in enumerate(dst.objects):
        coll('LOD '+str(i)).objects.link(o);o.hide_render=i>0;o.hide_set(i>0)
    o=dst.objects[0];o.select_set(True);bpy.context.view_layer.objects.active=o
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_location=(0,0,4);area.spaces.active.region_3d.view_distance=24;area.spaces.active.shading.type='MATERIAL'
    bpy.ops.file.pack_all();destination.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)

def scene(name,seed):
    reset();plan=make_plan(seed);h=field(plan);rng=random.Random(seed)
    path=OUT/'villages'/name;path.mkdir(parents=True,exist_ok=True);(path/'renders').mkdir(exist_ok=True)
    catalog=json.loads((LIB/'catalogue.json').read_text(encoding='utf-8'));records={a['id']:a for a in catalog['assets']}
    with bpy.data.libraries.load(str(LIB/'Kit_Alpin.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.endswith('_LOD0')]
    prototypes={o.name[:-5]:o for o in dst.objects}
    for o in prototypes.values():
        for s in o.material_slots:
            if s.material:MATS[s.material.name]=s.material
    architecture=coll('01 • Architecture');nature=coll('02 • Nature');props=coll('03 • Vie du village')
    landscape=coll('04 • Paysage');studio=coll('05 • Atmosphère et caméras')
    instances=[];smokes=[];wheels=[]
    def place(asset,x,y,z=None,rotation=0,scale=(1,1,1),category=props,label=None):
        o=prototypes[asset].copy();category.objects.link(o);o.name=label or asset+'_'+str(len(instances))
        z=float(sample(h,x,y)) if z is None else z
        o.location=(x,y,z);o.rotation_euler.z=math.radians(rotation);o.scale=scale;o['asset_id']=asset
        instances.append({'id':o.name,'asset':asset,'position':[float(x),float(y),float(z)],'rotation':float(rotation),'scale':list(scale),'category':category.name[:2]})
        return o
    for b in plan['buildings']:
        o=place(b['asset'],b['x'],b['y'],b['height'],b['rotation'],b['scale'],architecture,b['id'])
        a=math.radians(b['rotation']);front=np.array([math.sin(a),-math.cos(a)]);side=np.array([math.cos(a),math.sin(a)])
        point=np.array([b['x'],b['y']])+front*(b['depth']/2+1.6)
        place('buches',*(point+side*3),rotation=b['rotation'],scale=(.8,.8,.8))
        place('banc',*(point-side*2.8),rotation=b['rotation'])
        place('lanterne',*(point+side*.95),b['height']+2.1,rotation=b['rotation'])
        place('tonneau_'+str(b['index']%3),*(point+side*4.5),rotation=b['rotation'])
        if len(smokes)%3==0:place('linge',*(np.array([b['x'],b['y']])-front*7),rotation=b['rotation'])
        for dy in (-2,0,2):place('fleurs',*(point+side*5+front*dy),scale=(1.5,1.5,1.1),category=nature)
        floor=1 if b['index'] in (0,3) and b['role']=='maison' else 2
        chimney_z=2.7*floor*(.93+.028*b['index'])+.62+2.95
        chimney=np.array([b['x'],b['y']])+side*2*b['scale'][0]-front*b['scale'][1]
        smokes.append([float(chimney[0]),float(chimney[1]),b['height']+chimney_z])
    cx,cy=plan['center'];place('alpin_tour_0',cx,cy,scale=(.8,.8,.85),category=architecture,label='Chapelle')
    for i in range(5):
        a=i*math.tau/5;place('etal_'+str(i%3),cx+math.cos(a)*8,cy+math.sin(a)*8,rotation=math.degrees(a)+90)
    place('abreuvoir',cx-7,cy+2);place('charrette_0',cx+8,cy+10,rotation=20)
    mill=plan['buildings'][-1];wx=float(river_x(mill['y'],seed))+3.4;wy=mill['y']
    wheel=place('roue_moulin',wx,wy,2.65,label='Roue du moulin')
    wheel.rotation_euler.x=0;wheel.keyframe_insert('rotation_euler',frame=1,index=0)
    wheel.rotation_euler.x=-math.tau;wheel.keyframe_insert('rotation_euler',frame=241,index=0)
    if wheel.animation_data:
        for f in wheel.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for k in f.keyframe_points:k.interpolation='LINEAR'
            f.modifiers.new('CYCLES')
    wheels.append(wheel.name)
    n=RECIPE['terrain_cells'];ext=RECIPE['extent_m'];axis=np.linspace(-ext/2,ext/2,n+1)
    x,y=np.meshgrid(axis,axis);points=np.stack((x,y,h),axis=-1).reshape(-1,3);faces=[];edge_count={}
    for j in range(n):
        for i in range(n):
            xx=(axis[i]+axis[i+1])/2;yy=(axis[j]+axis[j+1])/2
            if math.hypot(xx,yy)>145:continue
            a=j*(n+1)+i;face=(a,a+1,a+n+2,a+n+1);faces.append(face)
            for aa,bb in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((aa,bb)));edge_count[edge]=edge_count.get(edge,0)+1
    border=sorted({i for e,c in edge_count.items() if c==1 for i in e},key=lambda i:math.atan2(points[i,1],points[i,0]))
    for i in border:
        a=math.atan2(points[i,1],points[i,0]);xx=145*math.cos(a);yy=145*math.sin(a);points[i]=(xx,yy,float(sample(h,xx,yy)))
    mesh=bpy.data.meshes.new('Terrain');mesh.from_pydata(points.tolist(),[],faces);mesh.update()
    terrain=bpy.data.objects.new('Terrain_'+name,mesh);landscape.objects.link(terrain)
    terrainmat=material('terrain_'+name,TEX);mesh.materials.append(terrainmat);uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        p.use_smooth=True
        for li in p.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co.x/ext+.5,co.y/ext+.5)
    static=Mesh();stone=material('roche',TEX);wood=material('bois',TEX);light=material('bois_clair',TEX)
    for a,b in zip(border,border[1:]+border[:1]):
        aa=points[a];bb=points[b];aa2=aa[:2]*1.025;bb2=bb[:2]*1.025
        static.surface([tuple(aa),tuple(bb),(bb2[0],bb2[1],-7),(aa2[0],aa2[1],-7)],[(0,3,2,1)],stone)
    bx,by=plan['bridge'];deck=max(float(sample(h,bx-10,by)),float(sample(h,bx+10,by)))+.4
    for i in range(55):static.box((bx-11+i*.4,by,deck),(.39,4,.22),light)
    for sy in (-1,1):
        static.beam((bx-11,by+sy*1.95,deck+1),(bx+11,by+sy*1.95,deck+1),.16,wood)
        for xx in np.linspace(bx-11,bx+11,12):static.box((float(xx),by+sy*1.95,deck+.5),(.13,.13,1.1),wood)
    for dx in (-7,0,7):
        for dy in (-1.5,1.5):static.box((bx+dx,by+dy,(deck-1.3)/2),(.7,.8,deck+1.3),stone)
    # Bief et passerelle vers le moulin, modules statiques en dehors de sa roue animée.
    static.beam((wx-1,wy,2.65),(mill['x'],wy,2.65),.3,wood)
    water=Mesh();watermat=material('eau_alpine',TEX,rough=.2)
    for yy in np.arange(-145,145,1.0):
        xx=float(river_x(yy,seed));xx2=float(river_x(yy+1,seed))
        if math.hypot(xx,yy)>143:continue
        water.surface([(xx-5.8,yy,.15),(xx+5.8,yy,.15),(xx2+5.8,yy+1,.15),(xx2-5.8,yy+1,.15)],[(0,1,2,3)],watermat,[(0,yy/10),(1,yy/10),(1,(yy+1)/10),(0,(yy+1)/10)])
    waterobj=water.object('Torrent');move(waterobj,landscape)
    nodes=watermat.node_tree.nodes;wave=nodes.new('ShaderNodeTexWave');wave.inputs['Scale'].default_value=2.4;wave.inputs['Distortion'].default_value=7
    wave.inputs['Phase Offset'].default_value=0;wave.inputs['Phase Offset'].keyframe_insert('default_value',frame=1)
    wave.inputs['Phase Offset'].default_value=18;wave.inputs['Phase Offset'].keyframe_insert('default_value',frame=241)
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.12
    watermat.node_tree.links.new(wave.outputs['Color'],bump.inputs['Height']);watermat.node_tree.links.new(bump.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    distances=path_distance(x,y,plan['roads'])
    def free(xx,yy,margin):
        return math.hypot(xx,yy)<140 and abs(xx-river_x(yy,seed))>6.8+margin and sample(distances,xx,yy)>margin and math.hypot(xx-cx,yy-cy)>12+margin and all(math.hypot(xx-b['x'],yy-b['y'])>b['radius']+margin for b in plan['buildings'])
    trees=[]
    for attempt in range(50000):
        if len(trees)>=RECIPE['trees']:break
        xx=rng.uniform(-138,138);yy=rng.uniform(-138,138)
        if not free(xx,yy,3) or float(sample(h,xx,yy))>48 or any(math.hypot(xx-a,yy-b)<4 for a,b in trees):continue
        if abs(xx-cx)<39 and -88<yy<57 and rng.random()<.85:continue
        scale=rng.uniform(.8,1.35);kind='meleze' if rng.random()<.38 else 'sapin'
        o=place(kind+'_'+str(rng.randrange(3)),xx,yy,rotation=rng.uniform(0,360),scale=(scale,scale,scale),category=nature)
        driver=o.driver_add('rotation_euler',0).driver;driver.expression=f'0.007*sin(frame/19+{len(trees)*.3})'
        trees.append((xx,yy))
    if len(trees)!=RECIPE['trees']:raise ValueError('Forêt incomplète')
    for kind,count,margin in [('rocher',150,.6),('herbe',RECIPE['groundcover'],.3),('buisson',120,.8),('fleurs',110,.3)]:
        made=0
        for attempt in range(count*100):
            if made==count:break
            xx=rng.uniform(-140,140);yy=rng.uniform(-140,140)
            if not free(xx,yy,margin):continue
            z=float(sample(h,xx,yy));scale=rng.uniform(.65,1.3)
            if kind=='rocher':scale*=1+max(z-17,0)*.06
            if kind in ('fleurs','herbe') and z>35:continue
            asset=kind if kind=='fleurs' else kind+'_'+str(rng.randrange(2 if kind=='rocher' else 3))
            place(asset,xx,yy,rotation=rng.uniform(0,360),scale=(scale,scale,scale),category=nature);made+=1
        if made!=count:raise ValueError('Peuplement incomplet : '+kind)
    for i in range(160):
        yy=rng.uniform(-133,133);xx=float(river_x(yy,seed))+rng.choice([-1,1])*rng.uniform(6,8.5)
        if math.hypot(xx,yy)>140 or sample(distances,xx,yy)<2:continue
        place('rocher_'+str(i%2),xx,yy,rotation=rng.uniform(0,360),scale=(.32,.32,.23),category=nature)
        if i%3==0:place('roseaux_'+str(i%3),xx,yy,scale=(.5,.5,.5),category=nature)
    for i,b in enumerate(plan['buildings']):
        if i%3:continue
        a=math.radians(b['rotation']);side=np.array([math.cos(a),math.sin(a)]);rear=np.array([-math.sin(a),math.cos(a)])
        for k in range(4):
            p=np.array([b['x'],b['y']])+rear*7+side*(k-1.5)*3
            place('cloture_'+str(k%3),*p,rotation=b['rotation'])
        if i%2==0:place('foin',b['x']+8,b['y']+6)
    built=static.object('Ouvrages');move(built,landscape);static_objects=[terrain,waterobj,built]
    export_fbx(path/'paysage.fbx',static_objects)
    total=sum(records[i['asset']]['triangles'][0] for i in instances)+sum(tri_count(o) for o in static_objects)
    if total>RECIPE['budget_triangles']:raise ValueError('Budget graphique dépassé')
    scene=bpy.context.scene;scene.frame_end=240;scene.render.fps=30;scene.frame_set(1)
    world=bpy.data.worlds.new('Ciel alpin');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.64,.83,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4;scene.world=world
    bg=Mesh();bg.box((0,0,-7.6),(2000,2000,.15),material('fond_alpin',TEX,color=(.16,.20,.19)));move(bg.object('Fond'),studio)
    bpy.ops.object.light_add(type='SUN');sun=bpy.context.object;sun.name='Soleil de fin d’après-midi';sun.data.energy=2;sun.data.angle=.12;sun.data.color=(1,.83,.58);sun.rotation_euler=(.75,-.5,-.55);move(sun,studio)
    bpy.ops.object.light_add(type='AREA',location=(-65,-25,95));fill=bpy.context.object;fill.data.energy=50000;fill.data.size=110;fill.rotation_euler=(Vector((0,0,0))-fill.location).to_track_quat('-Z','Y').to_euler();move(fill,studio)
    for i,loc in enumerate(smokes[::4]):
        m=bpy.data.materials.get('Fumée')
        if not m:
            m=bpy.data.materials.new('Fumée');m.use_nodes=True;ns=m.node_tree.nodes;ns.clear();out=ns.new('ShaderNodeOutputMaterial');vol=ns.new('ShaderNodeVolumePrincipled');vol.inputs['Density'].default_value=.065;vol.inputs['Color'].default_value=(.7,.73,.77,1);m.node_tree.links.new(vol.outputs['Volume'],out.inputs['Volume'])
        for k in range(4):
            puff=Mesh();puff.ico((0,0,0),(.4+k*.16,.4+k*.13,.65+k*.2),m,2);o=puff.object(f'Fumée_{i}_{k}');move(o,studio)
            o.location=(loc[0]+k*.28,loc[1],loc[2]+k*1.1)
            o.driver_add('location',0).driver.expression=f'{loc[0]+k*.28}+.3*sin(frame/22+{k})'
    for o in prototypes.values():bpy.data.objects.remove(o,do_unlink=True)
    cameras=[]
    for label,location,target,size in [('Territoire',(190,-245,215),(0,4,12),335),('Village',(99,-145,100),(cx-2,cy,5),170),('Moulin',(wx-38,wy-40,26),(wx+5,wy,5),58)]:
        bpy.ops.object.camera_add(location=location);cam=bpy.context.object;cam.name=label;cam.data.type='ORTHO';cam.data.ortho_scale=size;cam.data.clip_end=2200;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();move(cam,studio);cameras.append(cam)
    scene.camera=cameras[1];scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    except Exception:pass
    scene.render.resolution_x=1920;scene.render.resolution_y=1260;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.unit_settings.system='METRIC'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False;area.spaces.active.clip_end=2200
    bpy.ops.object.select_all(action='DESELECT')
    anchors=[points[j*(n+1)+i].tolist() for j,i in [(88,90),(90,110),(70,85),(130,80),(145,126),(114,142)]]
    description=next((d['label'] for d in RECIPE['dispositions'] if d['id']==name),name)
    report={'schema':3,'id':name,'label':description,'seed':seed,'biome':RECIPE['biome'],'typologie':RECIPE['typologie'],'annee':RECIPE['annee'],'culture':RECIPE['culture'],
            'instances':instances,'materials':matters([o for c in (architecture,nature,props,landscape) for o in c.objects]),
            'building_count':len(architecture.objects),'tree_count':len(trees),'triangles_lod0':total,'static_triangles':sum(tri_count(o) for o in static_objects),
            'plan_sha256':fingerprint(plan),'catalogue_sha256':fingerprint(catalog),'anchors':[{'position':p} for p in anchors],'smokes':[{'position':p} for p in smokes],'wheels':wheels,'center':[float(cx),float(cy)],'simulation_connected':False}
    write(path/'scene.json',report);write(path/'plan.json',plan);np.save(path/'hauteurs.npy',h)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path/(name+'.blend')),compress=True)
    for cam in cameras:
        scene.camera=cam;scene.render.filepath=str(path/'renders'/(cam.name.lower()+'.png'));bpy.ops.render.render(write_still=True)
    print('ALPIN_SCENE_OK',name,total,len(instances),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['assets','scene','edition']);p.add_argument('--nom');p.add_argument('--seed',type=int)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.phase=='assets':library()
    elif a.phase=='edition':edition(a.nom)
    else:scene(a.nom,a.seed)
