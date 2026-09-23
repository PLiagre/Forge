"""Rouvre les scènes existantes et photographie les cadrages à hauteur humaine.

À lancer avec Blender en arrière-plan. Ne sauvegarde jamais les scènes sources.
"""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local3d.citadelle.cameras import CAMERAS

OUT = Path(__file__).parent / 'sorties'
recipe = json.loads((Path(__file__).parent / 'recette.json').read_text(encoding='utf-8'))
for entry in recipe['dispositions']:
    name = entry['id']
    # Les comparaisons relisent toujours la sauvegarde initiale, jamais la scène retouchée.
    source=OUT/'diagnostic/avant'/(name+'.blend')
    if not source.exists():raise FileNotFoundError('Sauvegarde initiale absente : '+str(source))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    sc = bpy.context.scene
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    sc.cycles.device = 'GPU'
    folder = OUT / 'diagnostic' / 'avant' / name
    folder.mkdir(parents=True, exist_ok=True)
    inspection = {'objets': len(sc.objects), 'maillages': sum(o.type == 'MESH' for o in sc.objects),
                  'cameras': [{'nom': o.name, 'position': list(o.location),
                               'rotation': list(o.rotation_euler), 'focale': o.data.lens}
                              for o in sc.objects if o.type == 'CAMERA'],
                  'textures': [i.name for i in bpy.data.images if i.source == 'FILE']}
    if not (folder/'inspection.json').exists():
        (folder / 'inspection.json').write_text(json.dumps(inspection, indent=2), encoding='utf-8')
    complementary=[]
    for label, position, target, lens in CAMERAS[3:]:
        complementary.append({'name':label,'position':list(position),'target':list(target),'lens':lens})
        if (folder/('blender_'+label.lower()+'.png')).exists():continue
        c = bpy.data.cameras.new(label)
        o = bpy.data.objects.new(label, c)
        sc.collection.objects.link(o)
        o.location = position
        o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
        c.lens = lens
        c.clip_end = 2200
        sc.camera = o
        sc.render.filepath = str(folder / ('blender_' + label.lower() + '.png'))
        bpy.ops.render.render(write_still=True)
    (folder/'cameras-complementaires.json').write_text(json.dumps(complementary,indent=2),encoding='utf-8')
    print('SCENE_EXISTANTE_EXAMINEE', name, inspection['objets'], flush=True)
