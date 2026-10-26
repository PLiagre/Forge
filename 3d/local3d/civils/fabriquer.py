# Un civil de Biskra vers 1400, fabriqué dans Blender et cuit en VAT1 (lot #785).
#   blender -b --python-exit-code 1 --python 3d/local3d/civils/fabriquer.py -- --sortie DOSSIER [--apercu PNG]
# Technique reprise, sans l'importer, des soldats archivés (citadelle-guerre/fabrique/soldats.py) : maillage
# simple sur un squelette, posé image par image, cuit par coin de triangle. Contrat et contrôle : verifier.py.
import argparse, math, os, pathlib, struct, sys
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verifier import CLIPS, controler, decoder

# Zones de couleur. Alpha 1 : la tunique, que le rendu pourra reteindre.
PALETTE = {'peau': (0.62, 0.45, 0.33, 0), 'tunique': (0.86, 0.82, 0.72, 1), 'serouel': (0.52, 0.45, 0.35, 0),
           'cuir': (0.36, 0.24, 0.15, 0), 'turban': (0.94, 0.92, 0.86, 0)}
ZONES = list(PALETTE)
# Le squelette, en mètres, civil face à +Y, droite en +X : os -> (tête, queue, parent).
OS = {'hanches': ((0, 0, 0.92), (0, 0, 1.04), None), 'torse': ((0, 0, 1.04), (0, 0, 1.44), 'hanches'),
      'tete': ((0, 0, 1.48), (0, 0, 1.74), 'torse')}
for s, k in ((1, 'D'), (-1, 'G')):
    OS.update({'bras.' + k: ((0.22 * s, 0, 1.40), (0.25 * s, 0, 1.13), 'torse'),
               'avantbras.' + k: ((0.25 * s, 0, 1.13), (0.27 * s, 0.03, 0.90), 'bras.' + k),
               'cuisse.' + k: ((0.10 * s, 0, 0.93), (0.10 * s, 0, 0.51), 'hanches'),
               'jambe.' + k: ((0.10 * s, 0, 0.51), (0.10 * s, 0, 0.09), 'cuisse.' + k)})

def tronc(bm, p0, p1, r0, r1, zone, os_, n=6, aplati=1.0):
    """Tronc de cône fermé de p0 à p1, à n côtés, aplati d'avant en arrière, porté par un seul os."""
    p0, p1 = Vector(p0), Vector(p1)
    axe = (p1 - p0).normalized()
    u = Vector((1, 0, 0)) if abs(axe.x) < 0.9 else Vector((0, 1, 0))
    u = (u - axe * u.dot(axe)).normalized()
    ds = [u * math.cos(t) + axe.cross(u) * math.sin(t) for t in (2 * math.pi * (i + 0.5) / n for i in range(n))]
    a, b = [[bm.verts.new(p + Vector((d.x, d.y * aplati, d.z)) * r) for d in ds] for p, r in ((p0, r0), (p1, r1))]
    faces = [bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])) for i in range(n)]
    faces += [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
    for v in a + b: v[bm.verts.layers.deform.active][list(OS).index(os_)] = 1.0
    for f in faces: f.material_index = ZONES.index(zone)
    bmesh.ops.recalc_face_normals(bm, faces=faces)

def civil(bm):
    """Serouel et babouches, tunique aux genoux serrée d'une ceinture, manches longues, turban."""
    for s, k in ((1, 'D'), (-1, 'G')):
        x = 0.10 * s
        tronc(bm, (x, 0, 0.93), (x, 0, 0.50), 0.08, 0.062, 'serouel', 'cuisse.' + k)
        tronc(bm, (x, 0, 0.53), (x, 0, 0.06), 0.06, 0.045, 'serouel', 'jambe.' + k)
        tronc(bm, (x, -0.07, 0.042), (x, 0.17, 0.035), 0.06, 0.05, 'cuir', 'jambe.' + k, n=4)
        tronc(bm, (0.22 * s, 0, 1.41), (0.25 * s, 0, 1.13), 0.065, 0.055, 'tunique', 'bras.' + k)
        tronc(bm, (0.25 * s, 0, 1.13), (0.27 * s, 0.03, 0.93), 0.055, 0.047, 'tunique', 'avantbras.' + k)
        tronc(bm, (0.27 * s, 0.03, 0.95), (0.275 * s, 0.04, 0.82), 0.045, 0.04, 'peau', 'avantbras.' + k, n=4)
    tronc(bm, (0, 0, 1.06), (0, 0, 0.58), 0.17, 0.24, 'tunique', 'hanches', n=8, aplati=0.8)
    tronc(bm, (0, 0, 1.02), (0, 0, 1.08), 0.177, 0.177, 'cuir', 'hanches', n=8, aplati=0.75)
    tronc(bm, (0, 0, 1.06), (0, 0, 1.44), 0.165, 0.21, 'tunique', 'torse', n=8, aplati=0.65)
    tronc(bm, (0, 0, 1.43), (0, 0, 1.49), 0.20, 0.07, 'tunique', 'torse', n=8, aplati=0.65)
    tronc(bm, (0, 0, 1.46), (0, 0, 1.56), 0.05, 0.05, 'peau', 'tete', n=5)
    tronc(bm, (0, 0.01, 1.54), (0, 0.01, 1.68), 0.075, 0.095, 'peau', 'tete', n=6)
    tronc(bm, (0, 0, 1.64), (0, 0, 1.73), 0.112, 0.122, 'turban', 'tete', n=8)
    tronc(bm, (0, 0, 1.73), (0, 0, 1.775), 0.122, 0.06, 'turban', 'tete', n=8)

def monter():
    """Le squelette, puis le maillage du civil lié à lui par un modificateur Armature."""
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    arm = bpy.data.objects.new('civil_squelette', bpy.data.armatures.new('civil_squelette'))
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for n, (tete, queue, parent) in OS.items():
        b = arm.data.edit_bones.new(n)
        b.head, b.tail, b.roll, b.parent = tete, queue, 0, arm.data.edit_bones[parent] if parent else None
    bpy.ops.object.mode_set(mode='OBJECT')
    obj = bpy.data.objects.new('civil', bpy.data.meshes.new('civil'))
    bpy.context.scene.collection.objects.link(obj)
    for n in OS: obj.vertex_groups.new(name=n)
    bm = bmesh.new()
    bm.verts.layers.deform.verify()  # la couche avant les sommets : la créer après les invaliderait
    civil(bm)
    bm.to_mesh(obj.data)
    obj.parent = arm
    obj.modifiers.new('Squelette', 'ARMATURE').object = arm
    return arm, obj

def poser(arm, clip, phase):
    """Pose à une phase (0..1) du cycle ; la marche, sur place, est un cycle de deux pas. Les membres pendent,
    roll nul : X local reste +X monde, et un angle positif porte l'extrémité de l'os vers l'avant (+Y)."""
    w, d, P = 2 * math.pi * phase, math.radians, arm.pose.bones
    for pb in P: pb.rotation_mode, pb.rotation_euler, pb.location = 'XYZ', (0, 0, 0), (0, 0, 0)
    if clip == 'marche':
        b = math.sin(w)
        for k, s in (('D', 1), ('G', -1)):
            P['cuisse.' + k].rotation_euler.x = d(22) * b * s
            # Le genou plie pendant que la jambe revient vers l'avant ; le bras balance à l'opposé.
            P['jambe.' + k].rotation_euler.x = -d(6 + 40 * max(0.0, math.sin(w + 1.9 + (s < 0) * math.pi)))
            P['bras.' + k].rotation_euler.x = -d(17) * b * s
            P['avantbras.' + k].rotation_euler.x = d(12 - 8 * b * s)
        P['hanches'].location = (0, -0.015 * (1 - math.cos(2 * w)), 0)  # le bassin s'abaisse à chaque foulée
        P['torse'].rotation_euler.y = d(4) * b
    elif clip == 'repos':  # il regarde autour de lui
        P['tete'].rotation_euler.z = d(8) * math.sin(w + 0.6)
    bpy.context.view_layer.update()

def lire(obj):
    """Position, normale et (sommet, zone) par coin de triangle, en repère Unity (x, z, y) ; coins à rebours :
    Blender est droitier, Unity gaucher, la face reste extérieure."""
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me, unity = ev.to_mesh(), lambda v: (v.x, v.z, v.y)
    me.calc_loop_triangles()
    coins = [(unity(me.vertices[vi].co), unity(t.normal), (vi, me.polygons[t.polygon_index].material_index))
             for t in me.loop_triangles for vi in reversed(t.vertices)]
    ev.to_mesh_clear()
    return coins

def fabriquer(sortie):
    arm, obj = monter()
    poser(arm, None, 0)
    ref, half = lire(obj), lambda v: struct.pack('<%de' % len(v), *v)
    morceaux = [b'VAT1' + struct.pack('<ii', len(ref), len(CLIPS))]
    morceaux += [nom.encode('ascii').ljust(16, b'\0') + struct.pack('<if', i, d) for nom, i, d in CLIPS]
    morceaux += [half(p + n + PALETTE[ZONES[o[1]]]) for p, n, o in ref]
    for clip, images, _ in CLIPS:
        cadres = []
        for i in range(images + 1):  # la phase 1, en plus, ne sert qu'à vérifier la boucle
            poser(arm, clip, i / images)
            cadres.append(lire(obj))
            if [o for _, _, o in cadres[-1]] != [o for _, _, o in ref]:
                raise RuntimeError('topologie ou ordre des coins changé : %s, image %d' % (clip, i))
        boucle = max(abs(a - b) for x, y in zip(cadres[-1], cadres[0]) for a, b in zip(x[0], y[0]))
        if boucle > 0.001:
            raise RuntimeError('%s : la phase 1 s\'écarte de la phase 0 de %.4f m' % (clip, boucle))
        morceaux += [half([v for p, n, _ in coins for v in p + n]) for coins in cadres[:-1]]
    data = b''.join(morceaux)
    print('\n'.join('[civil] ' + ligne for ligne in controler(data)))
    os.makedirs(sortie, exist_ok=True)
    chemin = os.path.join(sortie, 'civil.vat')
    pathlib.Path(chemin + '.tmp').write_bytes(data)
    os.replace(chemin + '.tmp', chemin)  # un export interrompu ne laisse pas de VAT partiel
    return chemin

def apercu(chemin, png):
    """Planche repos, marche au quart et aux trois quarts, rendue depuis le VAT relu."""
    c, _, ref, poses = decoder(pathlib.Path(chemin).read_bytes())
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc, m = bpy.context.scene, poses['marche']
    for k, pose in enumerate((poses['repos'][0], m[len(m) // 4], m[3 * len(m) // 4])):
        me = bpy.data.meshes.new('pose%d' % k)
        me.from_pydata([(p[0] - k, p[2], p[1]) for p in pose], [], [(i + 2, i + 1, i) for i in range(0, c, 3)])
        col = me.color_attributes.new('Couleur', 'FLOAT_COLOR', 'CORNER')
        for li, l in enumerate(me.loops): col.data[li].color = ref[l.vertex_index][6:9] + (1,)
        sc.collection.objects.link(bpy.data.objects.new('pose%d' % k, me))
    sc.render.engine, sc.render.resolution_x, sc.render.resolution_y = 'BLENDER_WORKBENCH', 1400, 800
    sc.display.shading.light, sc.display.shading.color_type = 'STUDIO', 'VERTEX'
    cam = bpy.data.objects.new('camera', bpy.data.cameras.new('camera'))
    sc.collection.objects.link(cam)
    sc.camera, sc.render.filepath, cam.location, cam.data.lens = cam, png, (1.6, 3.6, 1.5), 40
    cam.rotation_euler = (Vector((-1, 0, 0.88)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    lecteur = argparse.ArgumentParser()
    lecteur.add_argument('--sortie', required=True)
    lecteur.add_argument('--apercu')
    args = lecteur.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    chemin = fabriquer(args.sortie)
    if args.apercu: apercu(chemin, args.apercu)
