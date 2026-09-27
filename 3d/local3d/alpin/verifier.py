"""Réouverture Blender et invariants de réutilisation et de placement."""
import argparse,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.alpin.paysage import RECIPE,make_plan
from local3d.atelier_v2.geometrie import tri_count
from local3d.atelier_v2.plan import fingerprint
from local3d.atelier_v2.verifier import check_positions
p=argparse.ArgumentParser();p.add_argument('--nom');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder=ROOT/'local3d/alpin/sorties/villages'/a.nom
report=json.loads((folder/'scene.json').read_text(encoding='utf-8'))
if fingerprint(make_plan(report['seed']))!=report['plan_sha256']:raise ValueError('Graine non reproductible')
bpy.ops.wm.open_mainfile(filepath=str(folder/(a.nom+'.blend')))
scene=bpy.context.scene;scene.frame_set(1)
actual={o.name:tuple(o.location) for o in scene.objects if 'asset_id' in o}
corrupt=dict(actual);first=report['instances'][0]['id'];v=corrupt[first];corrupt[first]=(v[0]+1,v[1],v[2])
try:check_positions(report['instances'],corrupt)
except ValueError:pass
else:raise ValueError('Le contrôle accepte un déplacement')
check_positions(report['instances'],actual)
meshes=[o for c in scene.collection.children if not c.name.startswith('05') for o in c.objects if o.type=='MESH']
triangles=sum(tri_count(o) for o in meshes)
if not 0<triangles==report['triangles_lod0']<=RECIPE['budget_triangles']:raise ValueError('Budget divergent')
images={n.image for o in meshes for s in o.material_slots if s.material for n in s.material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
if not images or any(not i.packed_file for i in images):raise ValueError('Textures externes dans la scène')
wheel=bpy.data.objects[report['wheels'][0]];scene.frame_set(1);before=wheel.rotation_euler.x;scene.frame_set(61);after=wheel.rotation_euler.x
if abs(after-before)<.5:raise ValueError('La roue ne tourne pas')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(folder/'paysage.fbx'))
if sum(tri_count(o) for o in bpy.context.scene.objects if o.type=='MESH')!=report['static_triangles']:raise ValueError('Paysage FBX divergent')
result={'status':'valide','instances':len(actual),'triangles':triangles,'textures_embarquees':len(images),'animation_roue':'mesurée à deux instants','graine_deterministe':True,'contre_epreuve':'déplacement refusé'}
(folder/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('ALPIN_VERIFIE',result,flush=True)
