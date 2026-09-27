# Engins de siège de Citadelle-Guerre, fabriqués dans Blender.
#   blender -b --python-exit-code 1 --python fabrique/engins.py -- SORTIE
#
# Une bombarde sur son affût et un trébuchet à contrepoids, low poly, exportés en FBX.
# Les matériaux portent les noms de ceux du kit de la Citadelle de Forge (bois_vieux,
# fer_noir, pierre_taille) : Unity leur substitue les matériaux du kit. Le bras du
# trébuchet est un objet à part, pour qu'il puisse basculer quand l'engin tire.

import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix

SORTIE = os.path.abspath(sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(os.path.dirname(__file__), 'sorties', 'engins'))
os.makedirs(SORTIE, exist_ok=True)


def vider():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials):
        for d in list(coll):
            coll.remove(d)


def materiau(nom, couleur):
    m = bpy.data.materials.get(nom) or bpy.data.materials.new(nom)
    m.diffuse_color = couleur
    return m


BOIS = lambda: materiau('bois_vieux', (0.42, 0.30, 0.18, 1))
FER = lambda: materiau('fer_noir', (0.12, 0.12, 0.13, 1))
PIERRE = lambda: materiau('pierre_taille', (0.6, 0.58, 0.54, 1))


class Piece:
    """Accumule des volumes dans un bmesh, chacun avec son matériau."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _m(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def boite(self, centre, taille, mat, rot=None):
        c, (sx, sy, sz) = Vector(centre), taille
        m = rot or Matrix.Identity(3)
        vs = [self.bm.verts.new(c + m @ Vector((x * sx / 2, y * sy / 2, z * sz / 2))) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for q in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
            f = self.bm.faces.new([vs[i] for i in q])
            f.material_index = self._m(mat)

    def cylindre(self, p0, p1, r0, r1, mat, n=10):
        p0, p1 = Vector(p0), Vector(p1)
        axe = (p1 - p0).normalized()
        u = Vector((1, 0, 0)) if abs(axe.x) < 0.9 else Vector((0, 1, 0))
        u = (u - axe * u.dot(axe)).normalized()
        v = axe.cross(u)
        anneaux = [[self.bm.verts.new(p + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * r) for i in range(n)] for p, r in ((p0, r0), (p1, r1))]
        k = self._m(mat)
        for i in range(n):
            self.bm.faces.new((anneaux[0][i], anneaux[0][(i + 1) % n], anneaux[1][(i + 1) % n], anneaux[1][i])).material_index = k
        self.bm.faces.new(list(reversed(anneaux[0]))).material_index = k
        self.bm.faces.new(anneaux[1]).material_index = k

    def objet(self, nom, parent=None):
        me = bpy.data.meshes.new(nom)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(nom, me)
        bpy.context.scene.collection.objects.link(o)
        if parent:
            o.parent = parent
        return o


def bombarde():
    """Une grosse bombarde de fer forgé cerclé, couchée sur un affût de madriers ; la bouche vers +Y."""
    p = Piece()
    # L'affût : deux longerons, des traverses, un butoir de pieux à l'arrière contre le recul.
    for s in (-1, 1):
        p.boite((0.42 * s, 0, 0.25), (0.22, 4.4, 0.5), BOIS())
    for y in (-1.8, -0.6, 0.6, 1.8):
        p.boite((0, y, 0.12), (1.2, 0.25, 0.24), BOIS())
    for x in (-0.5, 0, 0.5):
        p.boite((x, -2.45, 0.6), (0.2, 0.2, 1.4), BOIS(), rot=Matrix.Rotation(0.35, 3, 'X'))
    # La volée (le tube) et la chambre, plus étroite, à l'arrière ; des cercles de fer tout du long.
    p.cylindre((0, -0.2, 0.85), (0, 2.1, 0.85), 0.42, 0.40, FER(), n=12)
    p.cylindre((0, -1.9, 0.85), (0, -0.2, 0.85), 0.30, 0.30, FER(), n=10)
    for y in (-1.6, -1.0, -0.4, 0.3, 0.9, 1.5, 2.0):
        r = 0.34 if y < -0.2 else 0.45
        p.cylindre((0, y - 0.05, 0.85), (0, y + 0.05, 0.85), r, r, FER(), n=12)
    # La bouche : un cercle noir, et un boulet de pierre posé à côté.
    p.cylindre((0, 2.1, 0.85), (0, 2.12, 0.85), 0.25, 0.25, FER(), n=12)
    for k in range(3):
        p.boite((0.95, -0.6 + k * 0.55, 0.22), (0.44, 0.44, 0.44), PIERRE(), rot=Matrix.Rotation(0.4 * k, 3, 'Z'))
    return p.objet('bombarde')


def trebuchet():
    """Un trébuchet à contrepoids : deux chevalets, un axe à 6 m, un bras de 11 m ; le tir part vers +Y."""
    p = Piece()
    # Le châssis au sol et les deux chevalets en A qui portent l'axe.
    for s in (-1, 1):
        p.boite((1.1 * s, 0, 0.2), (0.35, 7.0, 0.4), BOIS())
        for dy in (-1, 1):
            a = math.atan2(2.6, 6.0) * dy
            p.boite((1.1 * s, 1.3 * dy, 3.1), (0.3, 0.3, 6.6), BOIS(), rot=Matrix.Rotation(a, 3, 'X'))
    for y in (-3.2, 0, 3.2):
        p.boite((0, y, 0.2), (2.6, 0.3, 0.3), BOIS())
    p.cylindre((-1.4, 0, 6.0), (1.4, 0, 6.0), 0.14, 0.14, FER(), n=8)
    chassis = p.objet('trebuchet')
    # Le bras, pivot à l'origine de l'objet (sur l'axe) : le petit bout porte le contrepoids, le grand la fronde.
    b = Piece()
    b.boite((0, 2.8, 0), (0.35, 11.0, 0.4), BOIS(), rot=None)
    b.boite((0, -2.2, -1.2), (1.6, 1.4, 1.6), BOIS())               # la caisse du contrepoids
    b.boite((0, -2.2, -0.5), (1.7, 1.5, 0.12), FER())
    b.cylindre((0, 8.2, 0), (0, 8.3, -1.6), 0.02, 0.02, FER(), n=4)   # la fronde, qui pend
    b.boite((0, 8.3, -1.8), (0.5, 0.5, 0.5), PIERRE())
    bras = b.objet('bras', chassis)
    bras.location = (0, 0, 6.0)
    # Bras armé : le grand bout en bas, vers l'arrière, le contrepoids en haut ; il bascule vers l'avant au tir.
    bras.rotation_euler = (math.radians(-142), 0, 0)
    return chassis


def exporter(racine, nom):
    bpy.ops.object.select_all(action='DESELECT')
    racine.select_set(True)
    for c in racine.children_recursive:
        c.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(SORTIE, nom + '.fbx'), use_selection=True, apply_unit_scale=True,
                             axis_forward='-Z', axis_up='Y', bake_space_transform=False, object_types={'MESH'},
                             mesh_smooth_type='FACE', add_leaf_bones=False)


def triangles(o):
    n = 0
    for x in [o] + list(o.children_recursive):
        x.data.calc_loop_triangles()
        n += len(x.data.loop_triangles)
    return n


if __name__ == '__main__':
    vider()
    rapport = {}
    for nom, f in (('bombarde', bombarde), ('trebuchet', trebuchet)):
        o = f()
        exporter(o, nom)
        rapport[nom] = {'triangles': triangles(o)}
        o.location.x = 40 if nom == 'trebuchet' else 0
    # Planche de contrôle.
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 35
    for nom, (loc, rot) in (('bombarde', ((6.5, -6.0, 3.0), (72, 0, 47))), ('trebuchet', ((58, -18, 9.0), (80, 0, 45)))):
        cam.location, cam.rotation_euler = loc, tuple(math.radians(a) for a in rot)
        sc.render.filepath = os.path.join(SORTIE, 'apercu_' + nom + '.png')
        bpy.ops.render.render(write_still=True)
    with open(os.path.join(SORTIE, 'engins.json'), 'w', encoding='utf-8') as f:
        json.dump(rapport, f, indent=2)
    print('[Engins]', json.dumps(rapport))
