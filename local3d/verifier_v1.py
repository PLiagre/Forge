"""Vérifie le fichier Blender sauvegardé et la géométrie réellement réimportée."""
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'local3d/v1'
report=json.loads((OUT/'rapport.json').read_text(encoding='utf-8'))
pilot=json.loads((ROOT/report['source_plan']).read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Forge_Village_V1.blend'))
def triangles(objects):
    count=0
    for o in objects:
        if o.type=='MESH':
            o.data.calc_loop_triangles()
            count+=len(o.data.loop_triangles)
    return count

buildings=next(c for c in bpy.context.scene.collection.children if c.name.startswith('01'))
assert len(buildings.objects)==len(pilot['buildings'])>0, 'Nombre de bâtiments différent du plan'
for item in pilot['buildings']:
    obj=buildings.objects[item['id']]
    expected=(item['x'],-item['z'],item['ground_y'])
    assert max(abs(a-b) for a,b in zip(obj.location,expected))<.0001, item['id']
images=[i for i in bpy.data.images if i.source=='FILE']
assert images and all(i.packed_file for i in images), 'Texture non embarquée'
meshes=[o for c in bpy.context.scene.collection.children if not c.name.startswith('04') for o in c.objects if o.type=='MESH']
expected=triangles(meshes)
assert 0<expected==report['triangles']<=report['budget'], 'Budget incohérent'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'exports/Forge_Village_V1.fbx'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
actual=triangles(imported)
assert actual==expected, f'Perte géométrique FBX : {actual} / {expected}'
missing=[o.name for o in imported if not o.material_slots or any(s.material is None for s in o.material_slots)]
assert not missing, 'Matériaux absents : '+str(missing)
result={'blender_reopened':True,'packed_textures':len(images),'buildings_from_plan':len(pilot['buildings']),
    'fbx_reimported':True,'fbx_meshes':len(imported),'triangles':actual,'missing_materials':missing}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('VERIFICATION_V1_OK '+json.dumps(result),flush=True)
