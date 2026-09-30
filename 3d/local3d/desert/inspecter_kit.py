"""Planche de contrôle du kit : chaque module au LOD0, rangé par famille, rendu EEVEE.

`blender -b --python 3d/local3d/desert/inspecter_kit.py -- [filtre]` écrit
`sorties/diagnostic/kit_<famille>.png`, sans toucher à la bibliothèque.
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(__file__).parent / 'sorties'
wanted = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
bpy.ops.wm.read_factory_settings(use_empty=True)
objects = []
# Les modules ajoutés par `fabriquer.py kit` n'entrent dans Kit_Desert.blend qu'à la
# prochaine reconstruction complète : d'ici là, ils se lisent dans le cache du kit.
# Pour un module présent dans les deux, la bibliothèque écrite en dernier l'emporte :
# la planche montre la géométrie que vient d'exporter `kit` ou `assets`, jamais une ancienne.
libraries = [p for p in (OUT / 'bibliotheque/Kit_Desert.blend', OUT / 'cache/kit_nouveaux.blend') if p.exists()]
for library in sorted(libraries, key=lambda p: p.stat().st_mtime, reverse=True):
    known = {o.name for o in objects}
    with bpy.data.libraries.load(str(library), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith('_LOD0') and n not in known and (not wanted or any(w in n for w in wanted))]
    objects += dst.objects
families = {}
for o in objects:
    families.setdefault(o.name.split('_')[0], []).append(o)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 1600; sc.render.resolution_y = 900
sc.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Studio'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .62, .72, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .9
sun = bpy.data.objects.new('Soleil', bpy.data.lights.new('Soleil', 'SUN')); sun.data.energy = 4; sun.data.color = (1, .85, .66)
sun.rotation_euler = (math.radians(55), 0, math.radians(-40)); sc.collection.objects.link(sun)
camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera')); sc.collection.objects.link(camera); sc.camera = camera
(OUT / 'diagnostic').mkdir(parents=True, exist_ok=True)
groups = [('maison', ['maison']), ('ksar', ['tour', 'rempart', 'porte', 'pont']), ('mosquee', ['mosquee', 'minaret', 'coupole', 'fontaine', 'escalier']),
          ('vegetation', ['palmier', 'acacia']), ('relief', ['falaise', 'dune', 'butte']), ('vie', ['chameau', 'tente', 'lanterne', 'etendard', 'garde', 'dalles', 'jarres', 'puits']),
          ('souk', ['souk']), ('ateliers', ['scierie', 'four'])]
for label, prefixes in groups:
    items = [o for p in prefixes for o in families.get(p, [])]
    if not items:
        continue
    for o in sc.collection.objects[:]:
        if o.type == 'MESH': sc.collection.objects.unlink(o)
    x = 0; top = 0
    for o in items:
        sc.collection.objects.link(o)
        size = Vector(o.dimensions)
        o.location = (x + size.x / 2, 0, 0); x += size.x + max(2, size.x * .15); top = max(top, size.z)
    width = x
    distance = max(width * .75, top * 2.2)
    camera.location = (width / 2 + distance * .15, -distance, distance * .45 + top * .3)
    camera.data.lens = 35
    camera.rotation_euler = (Vector((width / 2, 0, top * .35)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.clip_end = distance * 6
    sc.render.filepath = str(OUT / 'diagnostic' / ('kit_' + label + '.png'))
    bpy.ops.render.render(write_still=True)
