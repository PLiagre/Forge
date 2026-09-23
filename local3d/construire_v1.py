"""Assemble le village pilote existant avec les recettes Blender du dépôt.

Commande : blender --background --python local3d/construire_v1.py
Les modèles tiers absents sont remplacés par des créations locales déclarées.
Cette scène est une étude graphique du plan pilote, sans simulation ajoutée.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'local3d/v1'
sys.path[:0] = [str(ROOT / 'fabrique/Blender'), str(ROOT / 'fabrique')]
import building_kit as kit
import generate_building_family as gen
import style as grammar

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

PILOT = read('fabrique/donnees/Manifests/village_pilot.json')
SPEC = read('fabrique/donnees/Catalogs/village_pilot.json')
CATALOG = read('fabrique/donnees/Catalogs/building_pilot.json')
STYLE = read('fabrique/donnees/Styles/frontier.json')
STYLE['trim']['published_root'] = 'local3d/v1/textures'
for folder in ('assets', 'renders', 'exports'):
    (OUT / folder).mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
RNG = random.Random(PILOT['seed'])
asset_stats = []

def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

BUILDINGS = collection('01 • Bourg — 40 bâtiments du plan pilote')
LAND = collection('02 • Relief et voies')
DECOR = collection('03 • Décors créés dans Blender')
STUDIO = collection('04 • Caméras et éclairage')

def move(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

def mat(name, color, rough=0.8, metal=0):
    return kit.principled_material(name, (*color, 1), rough, metal)

WOOD = mat('Décor • chêne', (0.19, 0.095, 0.037))
EDGE = mat('Décor • bois de coupe', (0.46, 0.29, 0.13))
IRON = mat('Décor • fer', (0.065, 0.08, 0.083), .43, .75)
STONE = mat('Décor • calcaire', (.32, .34, .28))
LEAF = [mat('Feuillage • ' + str(i), c) for i,c in enumerate([
    (.16,.26,.065),(.23,.33,.08),(.31,.38,.11),(.105,.19,.06),(.34,.31,.075)])]
CLOTH = [mat('Toile • ' + str(i), c) for i,c in enumerate([(.61,.26,.11),(.77,.65,.39),(.2,.34,.32)])]

def export_fbx(path, objects):
    # Blender 5.2 : l'export FBX peut confondre les slots des instances liées.
    # Des copies temporaires de maillage isolent les slots pendant cet export.
    originals = {obj:obj.data for obj in objects}
    for obj in objects:
        obj.data = obj.data.copy()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
        add_leaf_bones=False, mesh_smooth_type='FACE', path_mode='RELATIVE')
    for obj, original in originals.items():
        temporary = obj.data
        obj.data = original
        bpy.data.meshes.remove(temporary)

def build_asset(family, variant):
    plan = grammar.plan_building(STYLE, family, CATALOG['variants'], variant['id'])
    print('CONSTRUCTION ' + plan.asset_id, flush=True)
    kit.set_bevel_policy(STYLE['budget']['max_bevel_segments'], STYLE['trim']['world_uv_scale_m'])
    materials = kit.build_materials(ROOT, STYLE, plan.palette, plan.asset_id,
        plan.wall_system, plan.roof_system, plan.upper_band, plan.lower_band)
    gen.alias_materials(materials)
    kit.set_stages(CATALOG['construction_stages'],
        {name:i+1 for i,name in enumerate(gen.STAGE_VOCABULARY)}, 'S')
    kit.set_phase('groundworks', 'foundation')
    gen.foundation(plan, materials)
    gen.shell(plan, materials)
    kit.set_phase('carpentry', 'roof_frame')
    gen.roof_carpentry(plan, materials, plan.roof_frame)
    if plan.roof_frame_high:
        gen.roof_carpentry(plan, materials, plan.roof_frame_high)
    kit.set_phase('roofing', 'roof_plane')
    gen.roof(plan, materials)
    kit.set_category('edge_trim')
    gen.edge_trim(plan, materials)
    for annex in plan.annexes:
        gen.build_annex(plan, annex, materials)
    kit.set_phase('joinery', 'opening_plane')
    gen.opening_leaves(plan, materials)
    kit.set_phase('finishes', 'appendage')
    gen.appendages(plan, materials)
    markers = gen.function_details(plan, variant, materials, random.Random(plan.seed))
    kit.uv_assets(STYLE['trim']['world_uv_scale_m'])
    sources = kit.asset_objects()
    lods = []
    for level in range(3):
        selected = kit.lod_selection(sources, level, STYLE['lod'])
        obj = kit.joined_copy(plan.asset_id + '_LOD' + str(level), selected)
        obj['origine'] = 'Recette du dépôt Forge, sans import Vendor'
        obj['famille'] = plan.function
        obj['variante'] = variant['id']
        obj['graine'] = plan.seed
        lods.append(obj)
    for src in sources:
        bpy.data.objects.remove(src, do_unlink=True)
    counts = [kit.triangle_count(o) for o in lods]
    if any(n > maximum for n,maximum in zip(counts,plan.budget_lod)):
        raise RuntimeError(f'Budget asset dépassé : {plan.asset_id} {counts} / {plan.budget_lod}')
    export_fbx(OUT / 'assets' / (plan.asset_id + '.fbx'), lods)
    bpy.data.libraries.write(str(OUT / 'assets' / (plan.asset_id + '.blend')), set(lods),
        path_remap='RELATIVE', fake_user=True, compress=True)
    asset_stats.append({'id':plan.asset_id, 'fonction':plan.function,
        'triangles_lod':counts, 'budget_lod':list(plan.budget_lod),
        'marqueurs':markers, 'geometrie_sha256':kit.canonical_hash(lods[0])})
    master = lods[0]
    for placement in [b for b in PILOT['buildings'] if b['asset'] == plan.asset_id]:
        instance = master.copy()
        instance.name = placement['id']
        BUILDINGS.objects.link(instance)
        instance.location = (placement['x'], -placement['z'], placement['ground_y'])
        instance.rotation_euler.z = math.radians(placement['rotation_y'])
    for obj in lods:
        bpy.data.objects.remove(obj, do_unlink=True)

for family in CATALOG['families']:
    for variant in CATALOG['variants']:
        build_asset(family, variant)

# La grille originale reste la seule source des hauteurs.
N = PILOT['terrain']['cells']
EXTENT = PILOT['extent_m']
HEIGHTS = PILOT['terrain']['heights_row_major']
def ground(x,y):
    u = min(N-1e-6, max(0, (x/EXTENT+.5)*N))
    v = min(N-1e-6, max(0, (-y/EXTENT+.5)*N))
    i,j = int(u),int(v)
    a,b = u-i,v-j
    h = lambda dx,dy: HEIGHTS[(j+dy)*(N+1)+i+dx]
    return (1-a)*(1-b)*h(0,0)+a*(1-b)*h(1,0)+(1-a)*b*h(0,1)+a*b*h(1,1)

grasses = [mat('Sol • prairie '+str(i),c) for i,c in enumerate([
    (.205,.255,.115),(.218,.267,.12),(.195,.246,.10),(.228,.274,.125)])]
road = mat('Sol • terre battue',(.34,.27,.165))
square = mat('Sol • place en gravier',(.38,.335,.245))
steps = int(EXTENT)
verts = [(x-EXTENT/2,y-EXTENT/2,ground(x-EXTENT/2,y-EXTENT/2))
    for y in range(steps+1) for x in range(steps+1)]
faces = [(j*(steps+1)+i,j*(steps+1)+i+1,(j+1)*(steps+1)+i+1,(j+1)*(steps+1)+i)
    for j in range(steps) for i in range(steps)]
mesh = bpy.data.meshes.new('Relief lu dans village_pilot.json')
mesh.from_pydata(verts, [], faces)
terrain = bpy.data.objects.new('Terrain • 140 × 140 m',mesh)
LAND.objects.link(terrain)
for m in grasses + [road,square]:
    mesh.materials.append(m)
for face in mesh.polygons:
    p = sum((mesh.vertices[i].co for i in face.vertices),Vector())/4
    if p.x*p.x+p.y*p.y < SPEC['streets']['square_radius_m']**2:
        face.material_index=5
    elif min(min(abs(p.x-a),abs(p.y-a)) for a in SPEC['streets']['axes_m']) < SPEC['streets']['half_width_m']:
        face.material_index=4
    else:
        face.material_index=RNG.choices(range(4),[6,1,1,1])[0]
    face.use_smooth=True

# Un soubassement descend jusqu'au relief sous chaque bâtiment.
for obj in list(BUILDINGS.objects):
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    x0,x1 = min(v.x for v in corners),max(v.x for v in corners)
    y0,y1 = min(v.y for v in corners),max(v.y for v in corners)
    base = obj.location.z
    low = min(ground(x,y) for x in (x0,x1) for y in (y0,y1))-.12
    if base-low > .08:
        pad=kit.box('Assise • '+obj.name, ((x0+x1)/2,(y0+y1)/2,(base+low)/2),
            (x1-x0,y1-y0,base-low),STONE,bevel=0)
        pad[kit.ASSET_TAG]=False
        move(pad,LAND)

def box(name,loc,size,material):
    return kit.box(name,loc,size,material,bevel=0)

def cyl(name,loc,radius,depth,material,vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    o=bpy.context.object
    o.name=name
    o.data.materials.append(material)
    return o

def ico(name,loc,scale,material,sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc)
    o=bpy.context.object
    o.name=name
    o.scale=scale
    o.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return o

def build_prop(kind):
    before=set(bpy.data.objects)
    if kind in ('arbre','arbre_second'):
        h = 9.4 if kind=='arbre' else 12
        cyl('Tronc', (0,0,h*.31),.26,h*.62,WOOD)
        for i in range(7):
            a=i*2.4
            p=(math.cos(a)*1.35,math.sin(a)*1.35,h*.58+(i%3)*.95)
            kit.beam_between('Branche',(0,0,h*.3),p,.15,WOOD)
            ico('Houppier',p,(2.25,1.8,2.1),LEAF[i%len(LEAF)],2)
    elif kind=='buisson':
        for i in range(3):
            ico('Buisson',(i*.55-.55,0,.5),(.85,.65,.7),LEAF[i],1)
    elif kind=='rocher':
        ico('Rocher',(0,0,.5),(1.1,.8,.95),STONE,1)
    elif kind=='herbe':
        for i in range(7):
            x,y=RNG.uniform(-.4,.4),RNG.uniform(-.4,.4)
            kit.surface_mesh('Brin',[(x-.05,y,0),(x+.05,y,0),(x+.12,y+.05,RNG.uniform(.3,.65))],[(0,1,2)],LEAF[1])
    elif kind=='cloture':
        for x in (-1.1,1.1): box('Poteau',(x,0,.65),(.14,.15,1.3),WOOD)
        for z in (.45,.95): box('Traverse',(0,0,z),(2.35,.10,.12),EDGE)
    elif kind=='tonneau':
        cyl('Tonneau',(0,0,.52),.42,1.04,WOOD,12)
        for z in (.13,.85): cyl('Cercle',(0,0,z),.434,.07,IRON,12)
        cyl('Couvercle',(0,0,1.05),.40,.04,EDGE,12)
    elif kind=='caisse':
        box('Caisse',(0,0,.42),(.85,.85,.84),EDGE)
        for x in (-.37,.37): box('Montant',(x,-.44,.42),(.09,.05,.84),WOOD)
        for z in (.08,.76): box('Renfort',(0,-.45,z),(.86,.05,.10),WOOD)
    elif kind=='etal':
        box('Comptoir',(0,0,.8),(2.2,.85,.12),EDGE)
        for x in (-1,1):
            for y in (-.45,.45): box('Pied',(x,y,.4),(.1,.1,.8),WOOD)
            box('Auvent',(x,.4,1.45),(.1,.1,2.9),WOOD)
        for i in range(8):
            x0=-1.2+i*.3
            kit.surface_mesh('Toile',[(x0,-.9,2.45),(x0+.3,-.9,2.45),(x0+.3,.65,2.85),(x0,.65,2.85)],[(0,1,2,3)],CLOTH[i%2])
        for i in range(4): box('Marchandise',(i*.42-.65,0,.98),(.34,.5,.25),CLOTH[2])
    elif kind=='puits':
        for layer in range(3):
            for i in range(12):
                a=(i+layer*.5)*math.tau/12
                o=box('Margelle',(math.cos(a)*.87,math.sin(a)*.87,.17+layer*.3),(.46,.32,.28),STONE)
                o.rotation_euler.z=a+math.pi/2
        for x in (-1.15,1.15): box('Support',(x,0,1.35),(.16,.16,2.7),WOOD)
        box('Poutre',(0,0,2.65),(2.6,.18,.18),WOOD)
        for s in (-1,1):
            kit.surface_mesh('Couverture',[(-1.4,0,3.2),(1.4,0,3.2),(1.4,s*.85,2.65),(-1.4,s*.85,2.65)],[(0,1,2,3)],EDGE)
        cyl('Corde',(0,0,1.8),.025,1.8,EDGE,6)
    else:
        raise ValueError('Décor sans recette : '+kind)
    objects=sorted(set(bpy.data.objects)-before, key=lambda o:o.name)
    joined=kit.joined_copy('forge_decor_'+kind,objects)
    for o in objects: bpy.data.objects.remove(o,do_unlink=True)
    joined[kit.ASSET_TAG]=False
    joined['origine']='Création Blender locale ; remplace le Vendor absent'
    export_fbx(OUT/'assets'/('forge_decor_'+kind+'.fbx'),[joined])
    bpy.data.libraries.write(str(OUT/'assets'/('forge_decor_'+kind+'.blend')),{joined},path_remap='RELATIVE',compress=True)
    return joined

for kind in sorted({d['kind'] for d in PILOT['decor']}):
    master=build_prop(kind)
    for d in [d for d in PILOT['decor'] if d['kind']==kind]:
        obj=master.copy()
        obj.name=d['id']
        DECOR.objects.link(obj)
        obj.location=(d['x'],-d['z'],d['ground_y'])
        obj.rotation_euler.z=math.radians(d['rotation_y'])
    bpy.data.objects.remove(master,do_unlink=True)

visible=list(BUILDINGS.objects)+list(LAND.objects)+list(DECOR.objects)
total=sum(kit.triangle_count(o) for o in visible)
if total > SPEC['budget']['scene_triangles_max']:
    raise RuntimeError(f'Scène hors budget : {total}')
export_fbx(OUT/'exports/Forge_Village_V1.fbx',visible)

# Studio de présentation, hors géométrie exportée.
backdrop=box('Fond de présentation',(0,0,-5.5),(2000,2000,1),mat('Fond • sauge',(.16,.195,.15)))
move(backdrop,STUDIO)
world=bpy.data.worlds.new('Ciel doux')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.68,.82,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
bpy.context.scene.world=world
bpy.ops.object.light_add(type='SUN',location=(40,-70,100))
sun=bpy.context.object
sun.name='Soleil • fin d’après-midi'
sun.rotation_euler=(math.radians(28),math.radians(-25),math.radians(-35))
sun.data.energy=2.5
sun.data.angle=.12
sun.data.color=(1,.82,.61)
move(sun,STUDIO)
bpy.ops.object.light_add(type='AREA',location=(-55,-20,80))
fill=bpy.context.object
fill.data.energy=15000
fill.data.shape='DISK'
fill.data.size=90
fill.rotation_euler=(Vector((0,0,0))-fill.location).to_track_quat('-Z','Y').to_euler()
move(fill,STUDIO)

def camera(name,loc,target,ortho):
    bpy.ops.object.camera_add(location=loc)
    cam=bpy.context.object
    cam.name=name
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'
    cam.data.ortho_scale=ortho
    cam.data.clip_end=2000
    move(cam,STUDIO)
    return cam

hero=camera('Vue 01 • Le bourg',(150,-175,155),(0,0,1),205)
detail=camera('Vue 02 • Place et métiers',(62,-75,60),(0,0,2),88)
scene=bpy.context.scene
scene.camera=hero
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
try:
    cp=bpy.context.preferences.addons['cycles'].preferences
    cp.compute_device_type='OPTIX'
    cp.get_devices()
    for device in cp.devices: device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
except Exception as e:
    print('Rendu CPU : '+str(e),flush=True)
scene.render.resolution_x=1920
scene.render.resolution_y=1440
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False
scene.unit_settings.system='METRIC'
scene['description']='Forge — village pilote V1. Étude graphique locale, sans simulation.'
scene['source_plan']='fabrique/donnees/Manifests/village_pilot.json'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.clip_end=2000
            area.spaces.active.shading.color_type='MATERIAL'
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
materials=[]
for m in sorted({s.material for obj in visible for s in obj.material_slots if s.material}, key=lambda m:m.name):
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    base=next((n.image for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and 'BaseColor' in n.image.name),None)
    materials.append({'name':m.name,'color':list(m.diffuse_color),
        'textured':base is not None,'metallic':float(bsdf.inputs['Metallic'].default_value),
        'roughness':float(bsdf.inputs['Roughness'].default_value)})
report={'schema':1,'description':scene['description'], 'blender':bpy.app.version_string,
    'source_plan':scene['source_plan'],'seed':PILOT['seed'],'extent_m':EXTENT,
    'buildings':len(BUILDINGS.objects),'decor':len(DECOR.objects),'triangles':total,
    'budget':SPEC['budget']['scene_triangles_max'],'assets':asset_stats,
    'materials':materials,'vendor_imported':False,'artistic_approval':'à examiner',
    'render_engine':'Cycles','simulation_connected':False}
(OUT/'rapport.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Forge_Village_V1.blend'),compress=True)
for cam,filename in ((hero,'01_vue_ensemble.png'),(detail,'02_place_et_metiers.png')):
    scene.camera=cam
    scene.render.filepath=str(OUT/'renders'/filename)
    bpy.ops.render.render(write_still=True)
print(f'FORGE_V1_OK bâtiments={len(BUILDINGS.objects)} décors={len(DECOR.objects)} triangles={total}',flush=True)
