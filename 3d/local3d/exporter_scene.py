"""Réexporte une scène déjà construite avec des maillages FBX indépendants."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'local3d/v1'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Forge_Village_V1.blend'))
bpy.ops.object.select_all(action='DESELECT')
objects = [o for c in bpy.context.scene.collection.children if not c.name.startswith('04')
    for o in c.objects if o.type=='MESH']
for obj in objects:
    obj.data=obj.data.copy()
    obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'exports/Forge_Village_V1.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_scale_options='FBX_SCALE_ALL',
    bake_space_transform=True,add_leaf_bones=False,mesh_smooth_type='FACE',path_mode='RELATIVE')
print('EXPORT_SCENE_OK',flush=True)
