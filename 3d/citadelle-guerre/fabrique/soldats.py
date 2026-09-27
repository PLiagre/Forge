# Soldats de Citadelle-Guerre, fabriqués dans Blender.
#   blender -b --python-exit-code 1 --python fabrique/soldats.py -- SORTIE
#
# Chaque variante (piquier, hallebardier, arbalétrier) est un corps modulaire
# low poly posé sur un vrai squelette. Le script pose ce squelette image par
# image pour la marche et le repos, puis cuit chaque sommet de chaque image
# dans un fichier .vat que Unity transforme en texture d'animation (VAT).
#
# Format .vat (petit-boutiste) :
#   "VAT1", int coins, int clips
#   par clip : nom (16 octets), int images, float durée (s)
#   par coin : position repos (3 × half), normale (3 × half), couleur (4 × half)
#   par clip, par image, par coin : position (3 × half), normale (3 × half)
# Les coordonnées sont déjà en repère Unity : (x, z, y) de Blender.

import bpy, bmesh, math, os, struct, sys, json
from mathutils import Vector, Matrix

SORTIE = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(os.path.dirname(__file__), 'sorties')
os.makedirs(SORTIE, exist_ok=True)

# Zones de couleur. Alpha 1 : la teinte du camp s'y applique.
PALETTE = {
    'peau':     (0.78, 0.60, 0.48, 0),
    'tunique':  (0.90, 0.90, 0.90, 1),
    'chausses': (0.24, 0.21, 0.19, 0),
    'acier':    (0.56, 0.58, 0.62, 0),
    'cuir':     (0.34, 0.23, 0.14, 0),
    'bois':     (0.46, 0.34, 0.21, 0),
    'gambison': (0.64, 0.59, 0.49, 0),
    'robe':     (0.38, 0.25, 0.16, 0),   # un cheval bai
    'crins':    (0.10, 0.08, 0.07, 0),
}
ZONES = list(PALETTE)

# Le squelette, en mètres, soldat face à +Y, droite en +X.
OS = {
    'hanches':    ((0, 0, 0.92), (0, 0, 1.04), None),
    'torse':      ((0, 0, 1.04), (0, 0, 1.44), 'hanches'),
    'tete':       ((0, 0, 1.48), (0, 0, 1.76), 'torse'),
    'bras.D':     ((0.22, 0, 1.40), (0.25, 0, 1.13), 'torse'),
    'avantbras.D':((0.25, 0, 1.13), (0.27, 0.03, 0.90), 'bras.D'),
    # L'arme a son propre os, tenu par la main droite : on peut l'orienter pour le combat.
    'arme':       ((0.27, 0.03, 0.88), (0.27, 0.03, 1.20), 'avantbras.D'),
    'bras.G':     ((-0.22, 0, 1.40), (-0.25, 0, 1.13), 'torse'),
    'avantbras.G':((-0.25, 0, 1.13), (-0.27, 0.03, 0.90), 'bras.G'),
    'cuisse.D':   ((0.10, 0, 0.93), (0.10, 0, 0.51), 'hanches'),
    'jambe.D':    ((0.10, 0, 0.51), (0.10, 0, 0.09), 'cuisse.D'),
    'cuisse.G':   ((-0.10, 0, 0.93), (-0.10, 0, 0.51), 'hanches'),
    'jambe.G':    ((-0.10, 0, 0.51), (-0.10, 0, 0.09), 'cuisse.G'),
}


# Le cheval et son cavalier, face à +Y : un destrier de 1,55 m au garrot, 2,3 m de long.
# Le cavalier est assis en selle à 1,6 m ; ses jambes suivent le corps du cheval.
OS_CAVALIER = {
    'corps':       ((0, -0.2, 1.2), (0, 0.2, 1.2), None),
    'encolure':    ((0, 0.72, 1.36), (0, 1.02, 1.78), 'corps'),
    'tetecheval':  ((0, 1.02, 1.80), (0, 1.38, 1.42), 'encolure'),
    'queue':       ((0, -1.0, 1.32), (0, -1.2, 0.84), 'corps'),
    'epaule.D':    ((0.19, 0.60, 1.08), (0.19, 0.62, 0.58), 'corps'),
    'canon.AD':    ((0.19, 0.62, 0.58), (0.19, 0.62, 0.06), 'epaule.D'),
    'epaule.G':    ((-0.19, 0.60, 1.08), (-0.19, 0.62, 0.58), 'corps'),
    'canon.AG':    ((-0.19, 0.62, 0.58), (-0.19, 0.62, 0.06), 'epaule.G'),
    'cuisse.PD':   ((0.2, -0.72, 1.12), (0.2, -0.84, 0.58), 'corps'),
    'canon.PD':    ((0.2, -0.84, 0.58), (0.2, -0.80, 0.06), 'cuisse.PD'),
    'cuisse.PG':   ((-0.2, -0.72, 1.12), (-0.2, -0.84, 0.58), 'corps'),
    'canon.PG':    ((-0.2, -0.84, 0.58), (-0.2, -0.80, 0.06), 'cuisse.PG'),
    'torse':       ((0, -0.12, 1.62), (0, -0.12, 2.02), 'corps'),
    'tete':        ((0, -0.12, 2.06), (0, -0.12, 2.34), 'torse'),
    'bras.D':      ((0.22, -0.12, 1.98), (0.25, -0.12, 1.71), 'torse'),
    'avantbras.D': ((0.25, -0.12, 1.71), (0.27, -0.09, 1.48), 'bras.D'),
    'arme':        ((0.27, -0.09, 1.46), (0.27, -0.09, 1.78), 'avantbras.D'),
    'bras.G':      ((-0.22, -0.12, 1.98), (-0.25, -0.12, 1.71), 'torse'),
    'avantbras.G': ((-0.25, -0.12, 1.71), (-0.27, -0.09, 1.48), 'bras.G'),
}


class Corps:
    """Accumule les pièces d'un soldat dans un bmesh, avec zone et os par pièce."""

    def __init__(self, os_=None):
        self.bm = bmesh.new()
        self.zone = self.bm.faces.layers.int.new('zone')
        self.deform = self.bm.verts.layers.deform.verify()
        self.os = list(os_ or OS)

    def _finir(self, verts, faces, zone, os_):
        g = self.os.index(os_)
        for v in verts:
            v[self.deform][g] = 1.0
        for f in faces:
            f[self.zone] = ZONES.index(zone)
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)

    def tronc(self, p0, p1, r0, r1, zone, os_, n=6, aplati=1.0):
        """Tronc de cône fermé de p0 à p1, section à n côtés, aplatie d'avant en arrière."""
        p0, p1 = Vector(p0), Vector(p1)
        axe = (p1 - p0).normalized()
        u = Vector((1, 0, 0)) if abs(axe.x) < 0.9 else Vector((0, 1, 0))
        u = (u - axe * u.dot(axe)).normalized()
        v = axe.cross(u)
        anneaux = []
        for p, r in ((p0, r0), (p1, r1)):
            anneau = []
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                d = u * math.cos(a) * r + v * math.sin(a) * r
                if abs(v.y) > abs(u.y):
                    d = u * math.cos(a) * r + v * math.sin(a) * r * aplati
                else:
                    d = u * math.cos(a) * r * aplati + v * math.sin(a) * r
                anneau.append(self.bm.verts.new(p + d))
            anneaux.append(anneau)
        faces = [self.bm.faces.new((anneaux[0][i], anneaux[0][(i + 1) % n], anneaux[1][(i + 1) % n], anneaux[1][i])) for i in range(n)]
        faces.append(self.bm.faces.new(list(reversed(anneaux[0]))))
        faces.append(self.bm.faces.new(anneaux[1]))
        self._finir([v for a in anneaux for v in a], faces, zone, os_)

    def boite(self, centre, taille, zone, os_, rot=None):
        c, (sx, sy, sz) = Vector(centre), taille
        m = rot or Matrix.Identity(3)
        coins = [c + m @ Vector((x * sx / 2, y * sy / 2, z * sz / 2)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        vs = [self.bm.verts.new(p) for p in coins]
        idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        faces = [self.bm.faces.new([vs[i] for i in q]) for q in idx]
        self._finir(vs, faces, zone, os_)

    def dome(self, centre, rx, ry, rz, zone, os_, n=6, anneaux=3, bas=0.0):
        """Calotte ellipsoïdale, du sommet jusqu'à la latitude 'bas' (0 : équateur, -1 : sphère complète)."""
        c = Vector(centre)
        lat = [math.pi / 2 - (math.pi / 2 - math.asin(bas)) * k / anneaux for k in range(1, anneaux + 1)]
        sommet = self.bm.verts.new(c + Vector((0, 0, rz)))
        rings = []
        for phi in lat:
            rings.append([self.bm.verts.new(c + Vector((math.cos(2 * math.pi * (i + 0.5) / n) * rx * math.cos(phi),
                                                        math.sin(2 * math.pi * (i + 0.5) / n) * ry * math.cos(phi),
                                                        math.sin(phi) * rz))) for i in range(n)])
        faces = [self.bm.faces.new((sommet, rings[0][i], rings[0][(i + 1) % n])) for i in range(n)]
        for a, b in zip(rings, rings[1:]):
            faces += [self.bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n])) for i in range(n)]
        faces.append(self.bm.faces.new(list(reversed(rings[-1]))))
        self._finir([sommet] + [v for r in rings for v in r], faces, zone, os_)


def corps_commun(c, torse='tunique', manches='gambison'):
    # Jambes : chausses, bottes de cuir.
    for s in (1, -1):
        x = 0.10 * s
        c.tronc((x, 0, 0.92), (x, 0, 0.52), 0.085, 0.065, 'chausses', 'cuisse.' + ('D' if s > 0 else 'G'))
        c.tronc((x, 0, 0.52), (x, 0, 0.14), 0.062, 0.05, 'chausses', 'jambe.' + ('D' if s > 0 else 'G'))
        c.tronc((x, 0, 0.26), (x, 0, 0.05), 0.058, 0.055, 'cuir', 'jambe.' + ('D' if s > 0 else 'G'))
        c.boite((x, 0.05, 0.035), (0.09, 0.24, 0.07), 'cuir', 'jambe.' + ('D' if s > 0 else 'G'))
    # Tunique : jupe évasée sur les hanches, buste, ceinture.
    c.tronc((0, 0, 1.06), (0, 0, 0.70), 0.17, 0.23, 'tunique', 'hanches', n=8, aplati=0.75)
    c.tronc((0, 0, 1.03), (0, 0, 1.08), 0.175, 0.175, 'cuir', 'hanches', n=8, aplati=0.72)
    c.tronc((0, 0, 1.06), (0, 0, 1.44), 0.165, 0.215, torse, 'torse', n=8, aplati=0.62)
    c.tronc((0, 0, 1.43), (0, 0, 1.49), 0.20, 0.07, torse, 'torse', n=8, aplati=0.65)
    # Bras : manches de gambison, mains nues.
    for s, cote in ((1, 'D'), (-1, 'G')):
        c.tronc((0.22 * s, 0, 1.41), (0.25 * s, 0, 1.13), 0.065, 0.055, manches, 'bras.' + cote)
        c.tronc((0.25 * s, 0, 1.13), (0.27 * s, 0.03, 0.93), 0.053, 0.045, manches, 'avantbras.' + cote)
        c.boite((0.27 * s, 0.035, 0.88), (0.06, 0.08, 0.10), 'peau', 'avantbras.' + cote)
    # Tête.
    c.tronc((0, 0, 1.47), (0, 0, 1.55), 0.05, 0.05, 'peau', 'tete', n=5)
    c.dome((0, 0.01, 1.63), 0.095, 0.11, 0.12, 'peau', 'tete', n=6, anneaux=3, bas=-0.9)


def chapel_de_fer(c):
    c.dome((0, 0, 1.69), 0.115, 0.125, 0.10, 'acier', 'tete', n=7, anneaux=2)
    c.tronc((0, 0, 1.685), (0, 0, 1.70), 0.20, 0.20, 'acier', 'tete', n=8)


def bassinet(c):
    c.dome((0, -0.01, 1.66), 0.115, 0.13, 0.19, 'acier', 'tete', n=7, anneaux=3, bas=-0.35)


def calotte_de_cuir(c):
    c.dome((0, 0, 1.68), 0.11, 0.12, 0.09, 'cuir', 'tete', n=7, anneaux=2, bas=-0.2)


def piquier():
    c = Corps()
    corps_commun(c)
    chapel_de_fer(c)
    # La pique, portée droite à côté du corps : 4,6 m de frêne, un fer étroit.
    c.tronc((0.30, 0.04, 0.12), (0.30, 0.04, 4.55), 0.018, 0.016, 'bois', 'arme', n=4)
    c.tronc((0.30, 0.04, 4.55), (0.30, 0.04, 4.78), 0.024, 0.002, 'acier', 'arme', n=4)
    return c


def hallebardier():
    c = Corps()
    corps_commun(c, torse='acier')  # plastron d'acier sur le buste
    bassinet(c)
    # Hallebarde de 2,1 m : hampe, fer de hache, pointe et croc.
    c.tronc((0.30, 0.04, 0.12), (0.30, 0.04, 2.10), 0.02, 0.018, 'bois', 'arme', n=4)
    c.boite((0.30, 0.14, 1.92), (0.015, 0.19, 0.25), 'acier', 'arme')
    c.boite((0.30, -0.05, 1.95), (0.012, 0.07, 0.04), 'acier', 'arme')
    c.tronc((0.30, 0.04, 2.10), (0.30, 0.04, 2.34), 0.02, 0.002, 'acier', 'arme', n=4)
    return c


def arbaletrier():
    c = Corps()
    corps_commun(c)
    calotte_de_cuir(c)
    # Arbalète tenue à la main droite, arc en haut ; carquois de carreaux à la hanche gauche.
    c.boite((0.30, 0.05, 1.05), (0.05, 0.06, 0.62), 'bois', 'arme')
    c.boite((0.30, 0.05, 1.33), (0.04, 0.60, 0.04), 'acier', 'arme')
    c.boite((-0.21, -0.06, 0.92), (0.07, 0.10, 0.30), 'cuir', 'hanches', rot=Matrix.Rotation(0.25, 3, 'Y'))
    return c


def cavalier():
    """Un homme d'armes monté : destrier sous une housse aux couleurs du camp, harnois, bassinet, lance."""
    c = Corps(OS_CAVALIER)
    # Le cheval : tronc, poitrail et croupe, encolure, tête, quatre jambes, queue.
    c.tronc((0, -0.95, 1.20), (0, 0.72, 1.24), 0.31, 0.34, 'robe', 'corps', n=8, aplati=0.82)
    c.tronc((0, 0.72, 1.24), (0, 0.90, 1.32), 0.34, 0.17, 'robe', 'corps', n=8, aplati=0.82)
    c.tronc((0, -0.95, 1.20), (0, -1.08, 1.26), 0.31, 0.13, 'robe', 'corps', n=8, aplati=0.82)
    c.tronc((0, 0.72, 1.30), (0, 1.04, 1.80), 0.19, 0.12, 'robe', 'encolure', n=6)
    c.boite((0, 0.84, 1.62), (0.05, 0.10, 0.52), 'crins', 'encolure', rot=Matrix.Rotation(-0.58, 3, 'X'))
    c.tronc((0, 1.02, 1.82), (0, 1.40, 1.42), 0.11, 0.065, 'robe', 'tetecheval', n=6)
    for s in (1, -1):
        c.boite((0.05 * s, 1.03, 1.93), (0.03, 0.04, 0.10), 'robe', 'tetecheval')
    for s, cote in ((1, 'D'), (-1, 'G')):
        x = 0.19 * s
        c.tronc((x, 0.60, 1.10), (x, 0.62, 0.58), 0.09, 0.055, 'robe', 'epaule.' + cote)
        c.tronc((x, 0.62, 0.58), (x, 0.62, 0.10), 0.045, 0.04, 'robe', 'canon.A' + cote)
        c.tronc((x, 0.62, 0.10), (x, 0.63, 0.0), 0.05, 0.062, 'crins', 'canon.A' + cote, n=5)
        x = 0.2 * s
        c.tronc((x, -0.70, 1.14), (x, -0.84, 0.58), 0.13, 0.06, 'robe', 'cuisse.P' + cote)
        c.tronc((x, -0.84, 0.58), (x, -0.80, 0.10), 0.045, 0.04, 'robe', 'canon.P' + cote)
        c.tronc((x, -0.80, 0.10), (x, -0.79, 0.0), 0.05, 0.062, 'crins', 'canon.P' + cote, n=5)
    c.tronc((0, -1.02, 1.30), (0, -1.22, 0.80), 0.07, 0.035, 'crins', 'queue', n=5)
    # La housse aux couleurs du camp, qui tombe sous le ventre : on reconnaît son camp de loin.
    c.tronc((0, -1.04, 1.10), (0, 0.84, 1.14), 0.40, 0.42, 'tunique', 'corps', n=8, aplati=0.9)
    c.boite((0, -0.12, 1.50), (0.40, 0.55, 0.10), 'cuir', 'corps')   # la selle
    # Le cavalier : harnois sous la cotte d'armes, bassinet, jambes d'acier le long des flancs.
    c.tronc((0, -0.12, 1.56), (0, -0.12, 1.84), 0.19, 0.20, 'tunique', 'torse', n=8, aplati=0.7)
    c.tronc((0, -0.12, 1.80), (0, -0.12, 2.02), 0.20, 0.21, 'acier', 'torse', n=8, aplati=0.62)
    c.tronc((0, -0.12, 2.01), (0, -0.12, 2.07), 0.21, 0.07, 'acier', 'torse', n=8, aplati=0.65)
    c.tronc((0, -0.12, 2.05), (0, -0.12, 2.13), 0.05, 0.05, 'peau', 'tete', n=5)
    c.dome((0, -0.11, 2.21), 0.095, 0.11, 0.12, 'peau', 'tete', n=6, anneaux=3, bas=-0.9)
    c.dome((0, -0.13, 2.24), 0.115, 0.13, 0.19, 'acier', 'tete', n=7, anneaux=3, bas=-0.35)
    for s, cote in ((1, 'D'), (-1, 'G')):
        c.tronc((0.22 * s, -0.12, 1.99), (0.25 * s, -0.12, 1.71), 0.068, 0.058, 'acier', 'bras.' + cote)
        c.tronc((0.25 * s, -0.12, 1.71), (0.27 * s, -0.09, 1.51), 0.055, 0.047, 'acier', 'avantbras.' + cote)
        c.boite((0.27 * s, -0.085, 1.46), (0.07, 0.09, 0.10), 'acier', 'avantbras.' + cote)
        c.tronc((0.17 * s, -0.12, 1.60), (0.40 * s, 0.20, 1.32), 0.085, 0.07, 'acier', 'corps')
        c.tronc((0.40 * s, 0.20, 1.32), (0.42 * s, 0.08, 0.92), 0.062, 0.05, 'acier', 'corps')
        c.boite((0.42 * s, 0.14, 0.89), (0.09, 0.24, 0.07), 'acier', 'corps')
    # La lance de guerre : 4,2 m de frêne, tenue au quart, un fer étroit.
    c.tronc((0.30, -0.08, 0.70), (0.30, -0.08, 4.72), 0.026, 0.018, 'bois', 'arme', n=5)
    c.tronc((0.30, -0.08, 1.55), (0.30, -0.08, 1.65), 0.05, 0.03, 'acier', 'arme', n=5)   # la rondelle qui garde la main
    c.tronc((0.30, -0.08, 4.72), (0.30, -0.08, 4.92), 0.028, 0.002, 'acier', 'arme', n=4)
    return c


VARIANTES = {'piquier': piquier, 'hallebardier': hallebardier, 'arbaletrier': arbaletrier}


def vider_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures):
        for d in list(coll):
            coll.remove(d)


def squelette(nom, os_=OS):
    arm = bpy.data.armatures.new(nom + '_squelette')
    obj = bpy.data.objects.new(nom + '_squelette', arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n, (tete, queue, parent) in os_.items():
        b = arm.edit_bones.new(n)
        b.head, b.tail = tete, queue
        b.roll = 0
        if parent:
            b.parent = arm.edit_bones[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in obj.pose.bones:
        pb.rotation_mode = 'XYZ'
    return obj


def maillage(nom, c, arm, os_=OS):
    me = bpy.data.meshes.new(nom)
    obj = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(obj)
    for n in os_:
        obj.vertex_groups.new(name=n)
    c.bm.to_mesh(me)
    c.bm.free()
    obj.parent = arm
    mod = obj.modifiers.new('Squelette', 'ARMATURE')
    mod.object = arm
    return obj


def lire(obj):
    """Positions et normales par coin de triangle, dans le repère Unity."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    zone = me.attributes['zone'].data
    pos, nor, zones = [], [], []
    for t in me.loop_triangles:
        n = t.normal
        # Le passage de Blender (droitier) à Unity (gaucher) inverse le sens des triangles : on
        # écrit leurs coins à rebours pour que Unity voie la face extérieure.
        for vi in reversed(t.vertices):
            p = me.vertices[vi].co
            pos.append((p.x, p.z, p.y))
            nor.append((n.x, n.z, n.y))
            zones.append(zone[t.polygon_index].value)
    ev.to_mesh_clear()
    return pos, nor, zones


def sens(arm, os_, extremite, axe_monde):
    """Signe d'une rotation positive autour de X local qui porte l'extrémité de l'os vers axe_monde."""
    pb = arm.pose.bones[os_]
    pb.rotation_euler = (0.3, 0, 0)
    bpy.context.view_layer.update()
    p = arm.matrix_world @ (pb.tail if extremite == 'queue' else pb.head)
    pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    q = arm.matrix_world @ (pb.tail if extremite == 'queue' else pb.head)
    return 1 if (p - q).dot(Vector(axe_monde)) > 0 else -1


def orienter_arme(arm, direction):
    """Tourne l'os de l'arme pour que la hampe (son axe Y) pointe vers direction, poignée dans la main."""
    bpy.context.view_layer.update()
    main = arm.pose.bones['avantbras.D'].tail.copy()
    y = Vector(direction).normalized()
    x = Vector((1, 0, 0)) - y * y.x
    x.normalize()
    z = x.cross(y)
    rot = Matrix((x, y, z)).transposed().to_4x4()  # colonnes : axes X, Y, Z de l'os
    arm.pose.bones['arme'].matrix = Matrix.Translation(main) @ rot
    bpy.context.view_layer.update()


def sens_translation(arm, os_, axe_monde):
    """Signe d'un déplacement positif selon Z local de l'os, mesuré dans le monde."""
    pb = arm.pose.bones[os_]
    pb.location = (0, 0, 0.1)
    bpy.context.view_layer.update()
    p = arm.matrix_world @ pb.head
    pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    q = arm.matrix_world @ pb.head
    return 1 if (p - q).dot(Vector(axe_monde)) > 0 else -1


def poser(arm, clip, phase, signes, arme='piquier'):
    """Pose du squelette à une phase (0..1) d'un cycle. La marche est un cycle de deux pas."""
    w = 2 * math.pi * phase
    P = arm.pose.bones
    for pb in P:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    d = math.radians
    if clip == 'marche':
        balance = math.sin(w)
        P['cuisse.D'].rotation_euler.x = signes['cuisse'] * d(24) * balance
        P['cuisse.G'].rotation_euler.x = -signes['cuisse'] * d(24) * balance
        # Le genou plie pendant que la jambe revient vers l'avant.
        P['jambe.D'].rotation_euler.x = signes['jambe'] * d(8 + 38 * max(0.0, math.sin(w + 1.9)))
        P['jambe.G'].rotation_euler.x = signes['jambe'] * d(8 + 38 * max(0.0, math.sin(w + 1.9 + math.pi)))
        # Le bras gauche balance à l'opposé de la jambe gauche ; le droit tient l'arme.
        P['bras.G'].rotation_euler.x = signes['bras'] * d(18) * balance
        P['avantbras.G'].rotation_euler.x = signes['bras'] * d(12 + 8 * balance)
        P['bras.D'].rotation_euler.x = signes['bras'] * d(3) * balance
        # Le bassin descend à chaque appui et tourne un peu avec le pas.
        P['hanches'].location = (0, -0.025 * math.cos(2 * w), 0)
        P['torse'].rotation_euler.y = d(5) * balance
        P['tete'].rotation_euler.y = -d(4) * balance
    elif clip == 'repos':  # on respire, on porte le poids d'une jambe sur l'autre, on regarde autour.
        P['torse'].rotation_euler.x = signes['torse'] * d(2.5) * math.sin(w * 2)
        P['hanches'].location = (0.012 * math.sin(w), 0, 0)
        P['tete'].rotation_euler.z = d(9) * math.sin(w + 0.6)
        P['bras.G'].rotation_euler.x = signes['bras'] * d(4) * math.sin(w * 2 + 1)
        P['avantbras.G'].rotation_euler.x = signes['bras'] * d(10)
    elif clip == 'abri':  # à genou derrière son pavois, genou droit à terre, l'arme serrée contre soi.
        P['hanches'].location = (0, -0.45, 0)
        P['cuisse.D'].rotation_euler.x = signes['cuisse'] * d(-5)
        P['jambe.D'].rotation_euler.x = signes['jambe'] * d(88)
        P['cuisse.G'].rotation_euler.x = signes['cuisse'] * d(82)
        P['jambe.G'].rotation_euler.x = signes['jambe'] * d(84)
        P['torse'].rotation_euler.x = signes['torse'] * d(14 + 1.5 * math.sin(w * 2))
        P['tete'].rotation_euler.x = signes['torse'] * d(10)
        P['bras.D'].rotation_euler.x = signes['bras'] * d(25)
        P['avantbras.D'].rotation_euler.x = signes['bras'] * d(35)
        P['bras.G'].rotation_euler.x = signes['bras'] * d(20)
        P['avantbras.G'].rotation_euler.x = signes['bras'] * d(40)
    else:  # combat : en garde, pied gauche devant ; le coup part dans la première moitié du cycle.
        coup = math.sin(math.pi * min(1.0, max(0.0, (phase - 0.05) / 0.45)))
        P['cuisse.G'].rotation_euler.x = signes['cuisse'] * d(20)
        P['cuisse.D'].rotation_euler.x = -signes['cuisse'] * d(14)
        P['jambe.G'].rotation_euler.x = signes['jambe'] * d(22)
        P['jambe.D'].rotation_euler.x = signes['jambe'] * d(14)
        # Le corps s'abaisse et se porte en avant avec le coup.
        P['hanches'].location = (0, -0.05, signes['fente'] * 0.12 * coup)
        P['torse'].rotation_euler.x = signes['torse'] * d(10 + 8 * coup)
        P['bras.D'].rotation_euler.x = signes['bras'] * d(45 + 25 * coup)
        P['avantbras.D'].rotation_euler.x = signes['bras'] * d(35 - 20 * coup)
        P['bras.G'].rotation_euler.x = signes['bras'] * d(50 + 25 * coup)
        P['avantbras.G'].rotation_euler.x = signes['bras'] * d(45 - 20 * coup)
        bpy.context.view_layer.update()
        if arme == 'piquier':
            # La pique abaissée à hauteur d'épaule, la pointe légèrement vers le bas.
            orienter_arme(arm, (0, 1, -0.06 - 0.05 * coup))
        elif arme == 'hallebardier':
            # La hallebarde levée à 60°, puis abattue jusque sous l'horizontale.
            e = d(60 - 72 * coup)
            orienter_arme(arm, (0, math.cos(e), math.sin(e)))
        else:
            # L'arbalète tenue devant soi, pour parer et frapper de la crosse.
            orienter_arme(arm, (0, 1, 0.35 - 0.3 * coup))
    bpy.context.view_layer.update()


def signes_soldat(arm):
    return {
        'cuisse': sens(arm, 'cuisse.D', 'queue', (0, 1, 0)),     # la cuisse part vers l'avant
        'jambe': sens(arm, 'jambe.D', 'queue', (0, -1, 0)),      # le genou plie : le pied part en arrière
        'bras': sens(arm, 'bras.G', 'queue', (0, 1, 0)),
        'torse': sens(arm, 'torse', 'queue', (0, 1, 0)),
        'fente': sens_translation(arm, 'hanches', (0, 1, 0)),    # le bassin se porte en avant
    }


def signes_cavalier(arm):
    return {
        'avant': sens(arm, 'epaule.D', 'queue', (0, 1, 0)),      # l'antérieur part vers l'avant
        'genou': sens(arm, 'canon.AD', 'queue', (0, -1, 0)),     # le genou plie : le sabot part en arrière
        'arriere': sens(arm, 'cuisse.PD', 'queue', (0, 1, 0)),   # le postérieur part vers l'avant
        'jarret': sens(arm, 'canon.PD', 'queue', (0, 1, 0)),     # le jarret plie : le sabot passe sous le ventre
        'encolure': sens(arm, 'encolure', 'queue', (0, 0, -1)),  # l'encolure s'abaisse
        'tangage': sens(arm, 'corps', 'queue', (0, 0, 1)),       # l'avant-main se lève
        'queue': sens(arm, 'queue', 'queue', (0, -1, 0)),        # la queue se relève
        'bras': sens(arm, 'bras.G', 'queue', (0, 1, 0)),
        'torse': sens(arm, 'torse', 'queue', (0, 1, 0)),
        'haut': sens_translation(arm, 'corps', (0, 0, 1)),
    }


def membre(q, appui, amplitude, flexion):
    """Angle et flexion d'une jambe à la phase q de son propre pas : balayée d'avant en arrière
    pendant l'appui, repliée et ramenée vers l'avant pendant le soutien."""
    if q < appui:
        return amplitude * (1 - 2 * q / appui), flexion * 0.08
    s = (q - appui) / (1 - appui)
    return -amplitude + 2 * amplitude * (0.5 - 0.5 * math.cos(math.pi * s)), flexion * math.sin(math.pi * s)


def poser_cavalier(arm, clip, phase, signes, arme='cavalier'):
    """Le cheval au trot (marche), au repos, au combat arrêté, et au galop de charge, lance couchée."""
    w = 2 * math.pi * phase
    P = arm.pose.bones
    for pb in P:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    d = math.radians
    S = signes

    def jambes(decalages, appui, a_av, a_ar, f_av, f_ar):
        for os_, flex, dec, avant in (('epaule.D', 'canon.AD', decalages[0], True), ('epaule.G', 'canon.AG', decalages[1], True),
                                      ('cuisse.PD', 'canon.PD', decalages[2], False), ('cuisse.PG', 'canon.PG', decalages[3], False)):
            a, f = membre((phase - dec) % 1.0, appui, d(a_av if avant else a_ar), d(f_av if avant else f_ar))
            P[os_].rotation_euler.x = (S['avant'] if avant else S['arriere']) * a
            P[flex].rotation_euler.x = (S['genou'] if avant else S['jarret']) * f

    if clip == 'marche':      # le trot : les diagonales battent ensemble
        jambes((0.0, 0.5, 0.5, 0.0), 0.45, 20, 18, 65, 40)
        P['corps'].location = (0, 0, S['haut'] * 0.03 * math.cos(4 * math.pi * phase))
        P['encolure'].rotation_euler.x = S['encolure'] * d(3) * math.sin(4 * math.pi * phase)
        P['queue'].rotation_euler.x = S['queue'] * d(12)
    elif clip == 'repos':     # il respire, baisse et relève la tête, chasse les mouches de la queue
        P['encolure'].rotation_euler.x = S['encolure'] * d(8 + 6 * math.sin(w))
        P['queue'].rotation_euler.z = d(12) * math.sin(w * 2)
        P['corps'].location = (0, 0, S['haut'] * 0.008 * math.sin(w * 2))
        P['epaule.G'].rotation_euler.x = S['avant'] * d(4)
        P['cuisse.PD'].rotation_euler.x = S['arriere'] * d(-4)
    elif clip == 'combat':    # arrêté dans la presse, le cheval piaffe ; le cavalier frappe de haut
        coup = math.sin(math.pi * min(1.0, max(0.0, (phase - 0.05) / 0.45)))
        P['epaule.D'].rotation_euler.x = S['avant'] * d(10 * math.sin(w))
        P['canon.AD'].rotation_euler.x = S['genou'] * d(25 * max(0.0, math.sin(w)))
        P['encolure'].rotation_euler.x = S['encolure'] * d(-6 + 4 * math.sin(w))
        P['queue'].rotation_euler.x = S['queue'] * d(18)
        P['torse'].rotation_euler.x = S['torse'] * d(8 + 12 * coup)
    else:                     # le galop de charge : quatre temps désunis, suspension ; lance couchée
        jambes((0.54, 0.42, 0.12, 0.0), 0.32, 34, 30, 80, 55)
        P['corps'].rotation_euler.x = S['tangage'] * d(5) * math.sin(w - 1.2)
        P['corps'].location = (0, 0, S['haut'] * 0.07 * math.sin(w + 0.6))
        P['encolure'].rotation_euler.x = S['encolure'] * d(-4 + 9 * math.sin(w + 0.4))
        P['queue'].rotation_euler.x = S['queue'] * d(35)
        P['torse'].rotation_euler.x = S['torse'] * d(14)
    # Le cavalier : la main gauche aux rênes, la droite à la lance.
    P['bras.G'].rotation_euler.x = S['bras'] * d(18)
    P['avantbras.G'].rotation_euler.x = S['bras'] * d(62)
    bpy.context.view_layer.update()
    if clip in ('marche', 'repos'):
        P['bras.D'].rotation_euler.x = S['bras'] * d(12)
        P['avantbras.D'].rotation_euler.x = S['bras'] * d(55)
        bpy.context.view_layer.update()
        orienter_arme(arm, (0, 0.22, 1))                    # la lance droite, appuyée sur l'étrier
    elif clip == 'combat':
        coup = math.sin(math.pi * min(1.0, max(0.0, (phase - 0.05) / 0.45)))
        P['bras.D'].rotation_euler.x = S['bras'] * d(20 + 40 * coup)
        P['avantbras.D'].rotation_euler.x = S['bras'] * d(60 - 30 * coup)
        bpy.context.view_layer.update()
        orienter_arme(arm, (0.05, 1, -0.10 - 0.12 * coup))  # la lance portée en avant, à la volée
    else:
        P['bras.D'].rotation_euler.x = S['bras'] * d(-8)
        P['avantbras.D'].rotation_euler.x = S['bras'] * d(78)
        bpy.context.view_layer.update()
        orienter_arme(arm, (-0.06, 1, -0.04))               # couchée sous le bras, par-dessus l'encolure
    bpy.context.view_layer.update()


CLIPS = [('marche', 24, 1.15), ('repos', 24, 4.0), ('combat', 24, 1.0), ('abri', 12, 3.0)]
# Pour le cavalier, la quatrième place est le galop de charge : le shader le joue au pas de la marche.
CLIPS_CAVALIER = [('trot', 24, 1.0), ('repos', 24, 5.0), ('combat', 24, 1.0), ('galop', 24, 1.0)]
half = lambda vals: struct.pack('<%de' % len(vals), *vals)


def fabriquer(nom, construire, os_=OS, poseur=poser, mesurer=signes_soldat, clips_=CLIPS):
    arm = squelette(nom, os_)
    obj = maillage(nom, construire(), arm, os_)
    signes = mesurer(arm)
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    pos0, nor0, zones = lire(obj)
    n = len(pos0)
    clips = []
    for clip, images, duree in clips_:
        cadres = []
        for i in range(images):
            poseur(arm, clip, i / images, signes, nom)
            p, nn, _ = lire(obj)
            assert len(p) == n, 'la topologie a changé pendant l\'animation'
            cadres.append((p, nn))
        clips.append((clip, images, duree, cadres))
    with open(os.path.join(SORTIE, nom + '.vat'), 'wb') as f:
        f.write(b'VAT1' + struct.pack('<ii', n, len(clips)))
        for clip, images, duree, _ in clips:
            f.write(clip.encode('ascii').ljust(16, b'\0') + struct.pack('<if', images, duree))
        for i in range(n):
            f.write(half(pos0[i] + nor0[i] + PALETTE[ZONES[zones[i]]]))
        for _, _, _, cadres in clips:
            for p, nn in cadres:
                f.write(half([c for i in range(n) for c in p[i] + nn[i]]))
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    return obj, arm, n // 3, signes


def apercu(objets):
    """Planche de contrôle : les trois variantes au repos et en pleine foulée, rendues par Workbench."""
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'VERTEX'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (6.5, -7.5, 2.6)
    cam.rotation_euler = (math.radians(82), 0, math.radians(38))
    cam.data.lens = 38


if __name__ == '__main__':
    vider_scene()
    rapport = {}
    objets = []
    for k, (nom, f) in enumerate(VARIANTES.items()):
        obj, arm, tris, signes = fabriquer(nom, f)
        arm.location.x = (k - 1) * 1.6
        rapport[nom] = {'triangles': tris, 'coins': tris * 3, 'signes': signes}
        objets.append((obj, arm))
    cav, cav_arm, tris, signes_cav = fabriquer('cavalier', cavalier, OS_CAVALIER, poser_cavalier, signes_cavalier, CLIPS_CAVALIER)
    rapport['cavalier'] = {'triangles': tris, 'coins': tris * 3, 'signes': signes_cav}
    cav_arm.location.x = 40
    # Couleurs visibles dans Blender : un attribut de coin tiré des zones.
    for obj, _ in objets + [(cav, cav_arm)]:
        me = obj.data
        col = me.color_attributes.new('Couleur', 'FLOAT_COLOR', 'CORNER')
        zone = me.attributes['zone'].data
        for poly in me.polygons:
            r, g, b, a = PALETTE[ZONES[zone[poly.index].value]]
            teinte = (0.2, 0.3, 0.7) if a else (r, g, b)
            for li in poly.loop_indices:
                col.data[li].color = (*teinte, 1)
        me.color_attributes.active_color = col
    apercu(objets)
    bpy.context.scene.render.filepath = os.path.join(SORTIE, 'apercu_repos.png')
    bpy.ops.render.render(write_still=True)
    signes = rapport['piquier']['signes']
    for obj, arm in objets:
        poser(arm, 'marche', 0.25, signes)
    bpy.context.scene.render.filepath = os.path.join(SORTIE, 'apercu_marche.png')
    bpy.ops.render.render(write_still=True)
    # Le coup, vu de profil : la pique abaissée, la hallebarde qui s'abat.
    for (obj, arm), nom in zip(objets, VARIANTES):
        poser(arm, 'combat', 0.3, signes, nom)
    cam = bpy.context.scene.camera
    cam.location, cam.rotation_euler = (9.0, 1.2, 1.5), (math.radians(88), 0, math.radians(90))
    bpy.context.scene.render.filepath = os.path.join(SORTIE, 'apercu_combat.png')
    bpy.ops.render.render(write_still=True)
    for (obj, arm), nom in zip(objets, VARIANTES):
        poser(arm, 'abri', 0.0, signes, nom)
    bpy.context.scene.render.filepath = os.path.join(SORTIE, 'apercu_abri.png')
    bpy.ops.render.render(write_still=True)
    for obj, arm in objets:
        for pb in arm.pose.bones:
            pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    # Le cavalier, de profil puis de trois quarts, dans chacune de ses allures.
    for clip, phase, nom_image in (('marche', 0.2, 'trot'), ('combat', 0.3, 'combat'), ('galop', 0.1, 'galop')):
        poser_cavalier(cav_arm, clip, phase, signes_cav)
        for vue, (loc, rot) in (('profil', ((49.0, 0.2, 1.6), (88, 0, 90))), ('face', ((45.5, 6.5, 2.4), (80, 0, 140)))):
            cam.location, cam.rotation_euler = loc, tuple(math.radians(a) for a in rot)
            bpy.context.scene.render.filepath = os.path.join(SORTIE, 'apercu_cavalier_%s_%s.png' % (nom_image, vue))
            bpy.ops.render.render(write_still=True)
    for pb in cav_arm.pose.bones:
        pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SORTIE, 'soldats.blend'))
    with open(os.path.join(SORTIE, 'soldats.json'), 'w', encoding='utf-8') as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print('[Soldats]', json.dumps(rapport, ensure_ascii=False))
