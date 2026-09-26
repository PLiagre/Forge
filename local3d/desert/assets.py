"""Modules du ksar. Mètres, origine au sol, façade vers -Y.

Même contrat que la citadelle : trois niveaux de détail explicites. Les
ornements de niveau 0 disparaissent d'abord, puis ceux de niveau 1 ; la
silhouette reste dans les trois niveaux.
"""
import math
import random
import bpy
import numpy as np
from mathutils import Vector, Quaternion
from local3d.atelier_v2.geometrie import Mesh, material
from local3d.citadelle.assets import transform_into, relief_noise

TEX = None
ALPHA = ('palme', 'palme_seche', 'feuillage_acacia')


def mat(n):
    m = material(n, TEX, alpha=n in ALPHA)
    if m.get('desert_surface') != 1:
        configure_material(m, n)
    return m


def configure_material(m, n):
    """Cartes partagées, découpe des palmes, teinte d'enduit par objet, feux et métaux."""
    nodes = m.node_tree.nodes; links = m.node_tree.links; bs = nodes.get('Principled BSDF')
    if not bs:
        return
    for node in nodes:
        if node.type == 'NORMAL_MAP':
            node.inputs['Strength'].default_value = .5
    tex = next((q for q in nodes if q.type == 'TEX_IMAGE' and q.image and '_BaseColor' in q.image.name), None)
    if n in ALPHA and tex:
        cutoff = nodes.new('ShaderNodeMath'); cutoff.operation = 'GREATER_THAN'; cutoff.inputs[1].default_value = .35
        links.new(tex.outputs['Alpha'], cutoff.inputs[0]); links.new(cutoff.outputs[0], bs.inputs['Alpha'])
    if n == 'enduit_pise' and tex:
        info = nodes.new('ShaderNodeObjectInfo'); mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1
        links.new(tex.outputs['Color'], mix.inputs[1]); links.new(info.outputs['Color'], mix.inputs[2]); links.new(mix.outputs[0], bs.inputs['Base Color'])
    if n == 'lumiere' and tex:
        links.new(tex.outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 1.8
    gloss = TEX / (n + '_MetallicGloss.png')
    if gloss.exists():
        t = nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(gloss), check_existing=True); t.image.colorspace_settings.name = 'Non-Color'
        invert = nodes.new('ShaderNodeMath'); invert.operation = 'SUBTRACT'; invert.inputs[0].default_value = 1
        links.new(t.outputs['Alpha'], invert.inputs[1]); links.new(invert.outputs[0], bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value = .82 if n == 'fer_noir' else .7 if n == 'cuivre' else 0
    m['desert_surface'] = 1


# ---------------------------------------------------------------- primitives

def frustum(m, x, y, z, bottom, top, h, name, cap=True):
    (w0, d0), (w1, d1) = bottom, top
    vs = [(x-w0/2,y-d0/2,z),(x+w0/2,y-d0/2,z),(x+w0/2,y+d0/2,z),(x-w0/2,y+d0/2,z),
          (x-w1/2,y-d1/2,z+h),(x+w1/2,y-d1/2,z+h),(x+w1/2,y+d1/2,z+h),(x-w1/2,y+d1/2,z+h)]
    faces = [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)] + ([(4,5,6,7)] if cap else [])
    m.surface(vs, faces, mat(name))


def pyramid(m, x, y, z, w, d, h, name):
    vs = [(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z),(x,y,z+h)]
    m.surface(vs, [(0,1,4),(1,2,4),(2,3,4),(3,0,4)], mat(name))


def stepped(m, x, y, z, size, name, steps=3):
    """Merlon à redans : trois gradins et une pointe, comme sur les kasbahs du Drâa."""
    for k in range(steps):
        s = size * (1 - k * .26); m.box((x, y, z + k * size * .34 + size * .17), (s, s, size * .34), mat(name))
    pyramid(m, x, y, z + steps * size * .34, size * .22, size * .22, size * .35, name)


def horseshoe(w, h, over=22, n=14):
    """Arc outrepassé : le cintre dépasse le demi-cercle et resserre sa base."""
    r = w / 2 / math.cos(math.radians(over)); rise = r * math.sin(math.radians(over))
    c = h - r; spring = c - rise
    pts = [(-w/2, 0), (-w/2, spring)]
    for i in range(1, n):
        a = math.radians(180 + over - (180 + 2 * over) * i / n)
        pts.append((r * math.cos(a), c + r * math.sin(a)))
    return pts + [(w/2, spring), (w/2, 0)]


def outline(m, pts, x, y, z, width, name, depth=None, closed=False):
    pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    for a, b in pairs:
        m.beam((x+a[0], y, z+a[1]), (x+b[0], y, z+b[1]), width, mat(name), depth)


def opening(m, x, z, w, h, panel, arch=False, frame='chaux', frame_width=.22, grille=False, studs=False, y0=0):
    """Porte ou fenêtre sur un plan qui regarde -Y, en y=y0 : panneau, encadrement, linteau.

    L'encadrement va du panneau jusqu'au mur (y=0) : une porte avancée devant
    le soubassement reste raccordée à la façade.
    """
    pts = horseshoe(w, h) if arch else [(-w/2, 0), (-w/2, h), (w/2, h), (w/2, 0)]
    m.surface([(x+a, y0-.02, z+b) for a, b in pts], [tuple(range(len(pts)))], mat(panel))
    border = [(a * (1 + frame_width / w), b + (frame_width * .5 if b > 0 else 0)) for a, b in pts]
    depth = abs(y0) + .3
    outline(m, border[:-1] if not arch else border, x, y0 / 2 - .05, z, frame_width, frame, depth)
    if not arch:
        m.detail = 1
        m.box((x, y0 - .14, z + h + .16), (w + .7, .28, .2), mat('bois_palmier'))
        m.detail = 2
    m.detail = 0
    if grille:
        for k in range(1, 4):
            m.beam((x - w/2 + k * w/4, y0 - .06, z + .05), (x - w/2 + k * w/4, y0 - .06, z + h * (.93 if not arch else .72)), .035, mat('fer_noir'))
        m.beam((x - w/2, y0 - .06, z + h * .45), (x + w/2, y0 - .06, z + h * .45), .035, mat('fer_noir'))
    if studs:
        for i in range(3):
            for j in range(5):
                m.ico((x - w * .3 + i * w * .3, y0 - .07, z + .35 + j * (h * .7 - .35) / 4), (.035, .03, .035), mat('cuivre'))
        m.cylinder((x + w * .18, y0 - .06, z + h * .45), (x + w * .18, y0 - .1, z + h * .45), .09, .09, mat('fer_noir'), 8)
    m.detail = 2
    return pts


def place_on(m, face_mesh, side, offset):
    """Pose un plan construit face à -Y sur l'un des quatre côtés d'un volume centré."""
    angle = (0, math.pi/2, math.pi, -math.pi/2)[side]
    c, s = math.cos(angle), math.sin(angle)
    transform_into(m, face_mesh, (offset * s, -offset * c, 0), angle)


def jar(m, x, y, z, k, name='poterie'):
    profile = [(0, .16), (.08, .30), (.32, .40), (.55, .36), (.76, .21), (.86, .13), (.93, .16)]
    for (za, ra), (zb, rb) in zip(profile, profile[1:]):
        m.cylinder((x, y, z + za * k), (x, y, z + zb * k), ra * k, rb * k, mat(name), 10)


def gable(m, x, y, z, w, d, rise, name):
    for side in (-1, 1):
        order = (0, 1, 2, 3) if side == 1 else (3, 2, 1, 0)
        m.surface([(x, y - d/2, z + rise), (x + side * w/2, y - d/2, z), (x + side * w/2, y + d/2, z), (x, y + d/2, z + rise)], [order], mat(name))
    m.cylinder((x, y - d/2 - .1, z + rise + .05), (x, y + d/2 + .1, z + rise + .05), .14, .14, mat(name), 6)


def warp(m, amount, seed, top):
    """Irrégularité d'une construction de terre : les pieds et le pivot restent en place."""
    m.verts = [(x + amount * math.sin(z * .61 + seed) * min(z, 1) * .8 + amount * .4 * math.sin(y * .72 + seed) * min(z, 1),
                y + amount * math.sin(z * .47 + x * .58 + seed) * min(z, 1),
                z + amount * .6 * math.sin(x * .91 + y * .68 + seed) * min(z, 1) * min(1, z / max(top, .1))) for x, y, z in m.verts]


# ---------------------------------------------------------------- architecture

def house(index):
    """Maison de terre sur une empreinte de 6 × 6 m, terrasse et acrotère."""
    rng = random.Random(4100 + index); m = Mesh()
    storeys = (1, 2, 2, 3, 2, 3)[index]; h = 3.1 * storeys + .45; t = .14
    def half(z): return 3 - t * max(0, z - .5) / (h - .5)
    frustum(m, 0, 0, 0, (6.34, 6.34), (6.18, 6.18), .5, 'pise')
    frustum(m, 0, 0, .5, (6, 6), (2 * half(h), 2 * half(h)), h - .5, 'enduit_pise')
    s = half(h); par = .95 if index % 2 else .75
    for sign in (-1, 1):
        m.box((0, sign * (s - .13), h + par / 2), (2 * s, .26, par), mat('enduit_pise'))
        m.box((sign * (s - .13), 0, h + par / 2), (.26, 2 * s - .52, par), mat('enduit_pise'))
    m.detail = 1
    for sign in (-1, 1):
        m.box((0, sign * (s - .13), h + par + .04), (2 * s + .06, .34, .08), mat('pise_clair'))
        m.box((sign * (s - .13), 0, h + par + .04), (.34, 2 * s - .6, .08), mat('pise_clair'))
    m.detail = 2
    top = h + par + .08
    if index in (1, 3, 5):
        for cx in (-1, 1):
            for cy in (-1, 1):
                stepped(m, cx * (s - .25), cy * (s - .25), top, .62, 'enduit_pise')
        m.detail = 1
        for k in (-1, 1):
            stepped(m, k * s * .35, -(s - .13), top, .38, 'enduit_pise', 2)
        m.detail = 2
    else:
        m.detail = 1
        for k in range(6):
            x = -s + .5 + k * (2 * s - 1) / 5
            pyramid(m, x, -(s - .13), top, .3, .28, .34, 'enduit_pise')
            pyramid(m, x, s - .13, top, .3, .28, .34, 'enduit_pise')
        m.detail = 2
    # Gargouilles en demi-troncs de palmier : l'eau des rares orages quitte la terrasse.
    m.detail = 1
    for x in (-1.7, 1.6):
        m.cylinder((x, -s + .1, h + .12), (x, -s - .62, h + .02), .075, .07, mat('bois_palmier'), 6)
    m.cylinder((s - .1, .8, h + .12), (s + .6, .8, h + .02), .075, .07, mat('bois_palmier'), 6)
    m.detail = 2
    # Façade : porte, petites baies, parfois un décor d'évents triangulaires.
    door_x = (-1.2, 0, 1.25, -.9, .8, -.1)[index]
    front = Mesh(); opening(front, door_x, 0, 1.2, 2.35, 'bois_peint_bleu' if index % 3 else 'bois_peint_vert', arch=index % 2 == 1, studs=True, y0=-.2)
    front.detail = 1; front.box((door_x, -.3, .07), (1.8, .6, .14), mat('pierre_taille')); front.detail = 2
    for k in range(storeys):
        z = 1.95 if k == 0 else 3.1 * k + 1.1
        xs = [(-door_x * .9 or 1.6)] if k == 0 else [-1.55, 1.55] if storeys < 3 or k < storeys - 1 else [-1.3, 0, 1.3]
        for x in xs:
            glass = 'lumiere' if rng.random() < .33 else 'baie_sombre'
            opening(front, x, z, .55 if k == 0 else .66, .7 if k == 0 else .95, glass, arch=index in (3, 5) and k > 0, grille=True, frame_width=.17)
    if index in (2, 4):
        front.detail = 1
        for k in range(7):
            x = -2.1 + k * .7
            front.surface([(x - .16, -.015, h - .75), (x + .16, -.015, h - .75), (x, -.015, h - .45)], [(0, 1, 2)], mat('baie_sombre'))
        front.box((0, -.02, h - .22), (2 * s, .04, .2), mat('chaux'))
        front.detail = 2
    if index in (0, 3):
        front.detail = 1
        for k in range(7):
            x = -2.55 + k * .85
            front.cylinder((x, .1, h - .38), (x, -.36, h - .4), .07, .065, mat('bois_palmier'), 6)
        front.detail = 2
    transform_into(m, front, (0, -half(1.5) - .01, 0))
    for side in (1, 3):
        n = Mesh()
        for k in range(1, storeys):
            glass = 'lumiere' if rng.random() < .3 else 'baie_sombre'
            opening(n, (-1.1, 1.0)[k % 2], 3.1 * k + 1.2, .6, .85, glass, grille=True, frame_width=.16)
        if storeys == 1:
            opening(n, .8, 1.9, .5, .6, 'baie_sombre', grille=True, frame_width=.15)
        place_on(m, n, side, half(3.5) + .01)
    back = Mesh(); opening(back, .4, 1.9 if storeys == 1 else 4.3, .55, .75, 'baie_sombre', grille=True, frame_width=.15)
    place_on(m, back, 2, half(3) + .01)
    # Pièce haute sur la terrasse, auvent de toile ou tête d'escalier.
    if index in (3, 4, 5):
        frustum(m, .6, s - 1.55, h, (3.2, 2.7), (3.05, 2.55), 2.5, 'enduit_pise')
        m.box((.6, s - 1.55, h + 2.55), (3.3, 2.8, .1), mat('pise_clair'))
        up = Mesh(); opening(up, 0, .15, .9, 1.9, 'bois_sombre', frame_width=.16)
        transform_into(m, up, (.6, s - 2.9, h))
        m.detail = 1
        for cx in (-1, 1):
            pyramid(m, .6 + cx * 1.4, s - 2.8, h + 2.6, .3, .3, .35, 'enduit_pise')
        m.detail = 2
    if index in (2, 5):
        cloth = 'tissu_garance' if index == 2 else 'tissu_ecru'
        for cx in (-1, 1):
            m.cylinder((cx * 1.3 - .6, -s + .7, h), (cx * 1.3 - .6, -s + .7, h + 2.1), .05, .05, mat('bois_palmier'), 6)
        m.surface([(-2.1, -s + .5, h + 2.1), (.9, -s + .5, h + 2.1), (.9, -s + 2.8, h + 2.45), (-2.1, -s + 2.8, h + 2.45)], [(0, 1, 2, 3)], mat(cloth))
    warp(m, .045, index, h)
    return m


def tower(index):
    """Tour de terre à fruit prononcé, frise d'arcatures aveugles et merlons à redans."""
    m = Mesh(); h = 14 + index * 3; b = 6.6; tp = 5.2
    def half(z): return b / 2 - (b - tp) / 2 * z / h
    frustum(m, 0, 0, 0, (b + .6, b + .6), (b + .2, b + .2), 1.4, 'gres_ocre')
    frustum(m, 0, 0, 1.4, (2 * half(1.4), 2 * half(1.4)), (tp, tp), h - 1.4, 'pise')
    ref = half(h * .75)
    def fy(z): return ref - half(z) - .03
    for side in range(4):
        n = Mesh(); band = h * .64
        for x in (-1.45, 0, 1.45):
            n.detail = 1
            outline(n, horseshoe(1.05, 2.1)[1:-1], x, fy(band + 1) - .02, band, .15, 'pise_clair')
            n.detail = 2
        z = h * .80; y = fy(z + .5)
        n.surface([(-.14, y, z), (.14, y, z), (.14, y, z + 1.1), (-.14, y, z + 1.1)], [(0, 1, 2, 3)], mat('lumiere' if side % 2 == 0 else 'baie_sombre'))
        n.detail = 0
        for k in range(6):
            x = -1.9 + k * .76; zc = h * .64 + 2.75
            outline(n, [(0, -.3), (.3, 0), (0, .3), (-.3, 0)], x, fy(zc) - .02, zc, .09, 'pise_clair', closed=True)
        n.detail = 2
        for z in (h * .30, h * .47):
            y = fy(z + .4)
            n.surface([(-.12, y, z), (.12, y, z), (.12, y, z + .8), (-.12, y, z + .8)], [(0, 1, 2, 3)], mat('baie_sombre'))
        n.detail = 1
        for k in range(6):
            x = -tp / 2 + .45 + k * (tp - .9) / 5; y = fy(h - .55)
            n.cylinder((x, y + .18, h - .55), (x, y - .42, h - .58), .075, .07, mat('bois_palmier'), 6)
        n.detail = 2
        place_on(m, n, side, ref)
    s = tp / 2
    for sign in (-1, 1):
        m.box((0, sign * (s - .22), h + .6), (tp, .44, 1.2), mat('pise'))
        m.box((sign * (s - .22), 0, h + .6), (.44, tp - .88, 1.2), mat('pise'))
    for cx in (-1, 1):
        for cy in (-1, 1):
            stepped(m, cx * (s - .35), cy * (s - .35), h + 1.2, 1.0, 'pise')
    m.detail = 1
    for k in (-1, 0, 1):
        for sign in (-1, 1):
            pyramid(m, k * 1.1, sign * (s - .22), h + 1.2, .55, .44, .7, 'pise')
            pyramid(m, sign * (s - .22), k * 1.1, h + 1.2, .44, .55, .7, 'pise')
    m.detail = 2
    if index == 1:
        frustum(m, 0, .6, h, (2.2, 2.2), (2.0, 2.0), 2.6, 'pise_clair')
        for cx in (-1, 1):
            for cy in (-1, 1):
                pyramid(m, cx * .8, .6 + cy * .8, h + 2.6, .4, .4, .5, 'pise_clair')
    warp(m, .05, index + 11, h)
    return m


def wall():
    """Rempart de pisé sur assise de grès ; merlons en dents de scie côté extérieur."""
    m = Mesh(); h = 9
    frustum(m, 0, 0, 0, (10, 3.3), (10, 3.0), 1.1, 'gres_ocre')
    frustum(m, 0, 0, 1.1, (10, 3.0), (10, 2.0), h - 1.1, 'pise')
    m.box((0, -.78, h + .6), (10, .45, 1.2), mat('pise'))
    m.box((0, .82, h + .3), (10, .36, .6), mat('pise'))
    for k in range(8):
        x = -4.375 + k * 1.25
        pyramid(m, x, -.78, h + 1.2, .8, .45, .75, 'pise')
    m.detail = 0
    for z in (3.2, 6.1):
        for k in range(8):
            x = -4.4 + k * 1.25 + (z > 5) * .6
            yy = -(1.5 - .5 * (z - 1.1) / (h - 1.1))
            m.cylinder((x, yy + .15, z), (x, yy - .28, z - .02), .065, .06, mat('bois_palmier'), 6)
    m.detail = 2
    warp(m, .04, 3, h)
    return m


def gate():
    """Porte monumentale à arc outrepassé, encadrée d'un alfiz, entre deux tours."""
    m = Mesh(); w = 4.4; ah = 7.2; top = 12.5; depth = 6
    for sx in (-1, 1):
        frustum(m, sx * 5.0, 0, 0, (5.4, 7.2), (4.5, 6.4), top + 2, 'pise')
        frustum(m, sx * 5.0, 0, 0, (5.9, 7.7), (5.5, 7.3), 1.2, 'gres_ocre')
        for cx in (-1, 1):
            for cy in (-1, 1):
                stepped(m, sx * 5.0 + cx * 1.8, cy * 2.8, top + 2, .95, 'pise')
        m.box((sx * 5.0, 0, top + 2.08), (4.6, 6.5, .16), mat('pise_clair'))
    pts = horseshoe(w, ah, 20, 18); spring = pts[1][1]
    r = max(abs(p[0]) for p in pts)
    for sx in (-1, 1):
        m.box((sx * (w / 2 + .35), 0, spring / 2), (.7, depth, spring), mat('pierre_taille'))
        m.box((sx * (r + .5), 0, spring + (top - spring) / 2), (1.0, depth, top - spring), mat('pise'))
    arc = pts[1:-1]
    for (a, b), (c, d) in zip(arc, arc[1:]):
        for y in (-depth / 2, depth / 2):
            m.surface([(a, y, b), (c, y, d), (c, y, top), (a, y, top)], [(0, 1, 2, 3)], mat('pise'))
        m.surface([(a, -depth / 2, b), (a, depth / 2, b), (c, depth / 2, d), (c, -depth / 2, d)], [(0, 1, 2, 3)], mat('pise_clair'))
    m.box((0, 0, top + .5), (2 * r + 2, depth, 1.0), mat('pise'))
    for k in range(5):
        pyramid(m, -2.4 + k * 1.2, -depth / 2 + .3, top + 1.0, .8, .5, .8, 'pise')
    # Claveaux de brique, alfiz de pierre et frise d'arcatures au-dessus.
    for a, b in zip(arc, arc[1:]):
        m.beam((a[0], -depth / 2 - .06, a[1]), (b[0], -depth / 2 - .06, b[1]), .5, mat('brique_crue'), .14)
    frame = [(-r - .55, spring - .4), (-r - .55, ah + .7), (r + .55, ah + .7), (r + .55, spring - .4)]
    outline(m, frame, 0, -depth / 2 - .1, 0, .3, 'pierre_taille', .2)
    m.detail = 1
    for k in range(5):
        outline(m, horseshoe(.62, 1.15)[1:-1], -2.0 + k, -depth / 2 - .08, ah + 1.15, .1, 'pise_clair')
    m.detail = 0
    for sx in (-1, 1):
        m.surface([(sx * r * .55, -depth / 2 - .12, spring + 1.4), (sx * (r + .25), -depth / 2 - .12, spring + 1.4),
                   (sx * (r + .25), -depth / 2 - .12, ah + .45)], [(0, 1, 2) if sx < 0 else (2, 1, 0)], mat('zellige'))
    m.detail = 2
    # Vantaux ouverts contre les piédroits : le passage reste libre à hauteur d'homme.
    for sx in (-1, 1):
        m.box((sx * (w / 2 - .09), 1.3, 2.7), (.14, 2.1, 5.2), mat('bois_peint_vert'))
    m.box((0, 0, .05), (w, depth, .1), mat('sol_dalle'))
    for sx in (-1, 1):
        m.detail = 1
        m.cylinder((sx * 2.2, -depth / 2 - .5, top - .8), (sx * 2.2, -depth / 2 - .5, top - .2), .12, .18, mat('cuivre'), 8)
        m.detail = 2
    warp(m, .03, 7, top)
    return m


def bridge():
    """Pont de grès à arches outrepassées ; le tablier est à Z=0."""
    m = Mesh(); width = 7; span = 14; radius = 6.1
    over = math.radians(12); c = -8
    for j in range(24):
        a = -over + j * (math.pi + 2 * over) / 24; b = -over + (j + 1) * (math.pi + 2 * over) / 24
        y1 = radius * math.cos(a); y2 = radius * math.cos(b); z1 = c + radius * math.sin(a); z2 = c + radius * math.sin(b)
        for sx in (-1, 1):
            x = sx * width / 2; m.surface([(x, y1, z1), (x, y2, z2), (x, y2, 0), (x, y1, 0)], [(0, 1, 2, 3)], mat('gres_ocre'))
        m.surface([(-width / 2, y1, z1), (width / 2, y1, z1), (width / 2, y2, z2), (-width / 2, y2, z2)], [(0, 1, 2, 3)], mat('pierre_taille'))
        m.detail = 1
        for sx in (-1, 1):
            m.beam((sx * (width / 2 + .05), y1, z1), (sx * (width / 2 + .05), y2, z2), .5, mat('brique_crue' if j % 2 else 'pierre_taille'))
        m.detail = 2
    low = c - radius * math.sin(over)
    for yy in (-6.6, 6.6):
        m.box((0, yy, (low - 44) / 2), (width + 1, 1.2, 44 + low), mat('gres_ocre'))
        for sx in (-1, 1):
            m.box((sx * (width / 2 + .7), yy, (low - 44) / 2 + 2), (1.4, 1.8, 40 + low), mat('gres_rouge'))
    m.box((0, 0, -.16), (width, span, .32), mat('sol_dalle'))
    for sx in (-1, 1):
        m.box((sx * 3.2, 0, .6), (.55, span, 1.2), mat('pise'))
        for yy in (-5.25, -1.75, 1.75, 5.25):
            stepped(m, sx * 3.2, yy, 1.2, .55, 'pise', 2)
        m.detail = 1
        m.box((sx * 2.75, 0, .04), (.5, span, .06), mat('sable_dune'))
        m.detail = 2
    return m


def prayer_hall():
    """Salle de prière de douze mètres : murs chaulés, toits de tuiles vertes, arcs aveugles."""
    m = Mesh(); w = 22; d = 12; h = 8.5
    m.box((0, 0, .4), (w + .4, d, .8), mat('pierre_taille'))
    m.box((0, 0, .8 + (h - .8) / 2), (w, d, h - .8), mat('chaux'))
    for k in range(3):
        x = -w / 2 + w / 3 * (k + .5)
        gable(m, x, 0, h + .15, w / 3 + .12, d + .1, 2.1, 'tuile_verte')
    m.box((0, 0, h + .07), (w + .2, d, .14), mat('pierre_taille'))
    for sign in (-1, 1):
        m.box((sign * (w / 2 - .15), 0, h + .55), (.3, d, 1.1), mat('chaux'))
        for k in range(8):
            stepped(m, sign * (w / 2 - .15), -d / 2 + .75 + k * (d - 1.5) / 7, h + 1.1, .5, 'chaux', 2)
    for side in (1, 3):
        n = Mesh()
        for x in (-3, 3):
            opening(n, x, 3.4, 1.1, 2.4, 'lumiere' if x > 0 else 'baie_sombre', arch=True, grille=True, frame='pierre_taille', frame_width=.2)
        n.detail = 1
        for k in range(5):
            outline(n, horseshoe(1.3, 2.2)[1:-1], -4.8 + k * 2.4, -.04, .9, .12, 'pise_clair')
        n.detail = 2
        place_on(m, n, side, w / 2 + .01)
    return m


def portal():
    """Façade de la mosquée : avant-corps, portail outrepassé, zellige et frise d'arcatures."""
    m = Mesh(); w = 22; h = 10
    m.box((0, 0, .4), (w + .4, 2.6, .8), mat('pierre_taille'))
    m.box((0, 0, .8 + (h - .8) / 2), (w, 2.5, h - .8), mat('chaux'))
    m.box((0, -.45, 6.25), (8, 3.4, 12.5), mat('chaux'))
    y = -2.15
    m.box((0, y + .02, 4.6), (5.9, .06, 8.2), mat('zellige'))
    pts = opening(Mesh(), 0, 0, 3.6, 6.4, 'bois_sombre', arch=True)
    m.surface([(a, y - .04, .5 + b) for a, b in pts], [tuple(range(len(pts)))], mat('bois_peint_vert'))
    arc = pts[1:-1]
    for a, b in zip(arc, arc[1:]):
        m.beam((a[0] * 1.08, y - .1, .5 + a[1] * 1.02), (b[0] * 1.08, y - .1, .5 + b[1] * 1.02), .42, mat('pierre_taille'), .18)
    outline(m, [(-2.95, .5), (-2.95, 8.7), (2.95, 8.7), (2.95, .5)], 0, y - .08, 0, .3, 'pierre_taille', .16)
    m.detail = 1
    for k in range(7):
        outline(m, horseshoe(.62, 1.2)[1:-1], -2.7 + k * .9, y - .05, 9.3, .1, 'pise_clair')
    m.box((0, y - .03, 11.3), (7.4, .08, .55), mat('zellige'))
    m.detail = 0
    for x in (-.5, .5):
        m.cylinder((x, y - .12, 3.0), (x, y - .18, 3.0), .1, .1, mat('cuivre'), 8)
    m.cylinder((0, y - .6, 7.2), (0, y - .6, 7.9), .02, .02, mat('fer_noir'), 4)
    m.cylinder((0, y - .6, 6.7), (0, y - .6, 7.2), .22, .12, mat('cuivre'), 8)
    m.ico((0, y - .6, 6.85), (.16, .16, .2), mat('lumiere'), 1)
    m.detail = 2
    for k in range(6):
        stepped(m, -3.3 + k * 1.32, -.45 - 1.4, 12.5, .7, 'chaux', 2)
    for sign in (-1, 1):
        for k in range(6):
            stepped(m, sign * (5 + k * 1.2), -1.0, h, .55, 'chaux', 2)
        n = Mesh(); opening(n, sign * 7.3, 3.2, 1.3, 2.7, 'lumiere', arch=True, grille=True, frame='pierre_taille', frame_width=.2)
        transform_into(m, n, (0, -1.26, 0))
    return m


def lattice(m, x0, x1, z0, z1, y, step, width, name):
    """Réseau de losanges (sebka) découpé dans un panneau rectangulaire."""
    def clip(a, b):
        (ax, az), (bx, bz) = a, b; t0, t1 = 0, 1
        for p, q in ((-(bx - ax), ax - x0), (bx - ax, x1 - ax), (-(bz - az), az - z0), (bz - az, z1 - az)):
            if abs(p) < 1e-9:
                if q < 0: return None
                continue
            r = q / p
            if p < 0: t0 = max(t0, r)
            else: t1 = min(t1, r)
        if t0 >= t1: return None
        return (ax + (bx - ax) * t0, az + (bz - az) * t0), (ax + (bx - ax) * t1, az + (bz - az) * t1)
    span = (x1 - x0) + (z1 - z0)
    for k in range(int(span / step) + 2):
        o = x0 - (z1 - z0) + k * step
        for a, b in (((o, z0), (o + span, z0 + span)), ((o + (z1 - z0), z0), (o + (z1 - z0) - span, z0 + span))):
            seg = clip(a, b)
            if seg:
                (ax, az), (bx, bz) = seg
                m.beam((ax, y, az), (bx, y, bz), width, mat(name))


def minaret():
    """Minaret carré : fût de brique crue, réseau de losanges, lanterne et jamour de cuivre."""
    m = Mesh(); b = 5.4; h = 24
    m.box((0, 0, 2), (b + .3, b + .3, 4), mat('pierre_taille'))
    m.box((0, 0, 4 + (h - 4) / 2), (b, b, h - 4), mat('brique_crue'))
    for side in range(4):
        n = Mesh()
        for k, z in enumerate((6.2, 11.2)):
            opening(n, (-.9, .9)[(k + side) % 2], z, .7, 1.5, 'baie_sombre' if k else 'lumiere', arch=True, frame='pise_clair', frame_width=.16)
        n.detail = 1
        outline(n, [(-2.0, 15.6), (-2.0, 21.8), (2.0, 21.8), (2.0, 15.6)], 0, -.05, 0, .18, 'pise_clair', closed=True)
        n.detail = 0
        lattice(n, -1.9, 1.9, 15.7, 21.7, -.05, 1.1, .11, 'pise_clair')
        n.detail = 2
        place_on(m, n, side, b / 2 + .01)
    m.box((0, 0, h - .5), (b + .1, b + .1, .9), mat('zellige'))
    m.box((0, 0, h + .05), (b + .5, b + .5, .2), mat('pierre_taille'))
    for sign in (-1, 1):
        m.box((0, sign * (b / 2 + .05), h + .6), (b + .5, .3, 1.0), mat('brique_crue'))
        m.box((sign * (b / 2 + .05), 0, h + .6), (.3, b - .1, 1.0), mat('brique_crue'))
        for k in range(4):
            stepped(m, -1.95 + k * 1.3, sign * (b / 2 + .05), h + 1.1, .55, 'brique_crue', 2)
            stepped(m, sign * (b / 2 + .05), -1.95 + k * 1.3, h + 1.1, .55, 'brique_crue', 2)
    lb = 2.6; lh = 4.8
    m.box((0, 0, h + lh / 2), (lb, lb, lh), mat('brique_crue'))
    for side in range(4):
        n = Mesh(); opening(n, 0, h + 1.0, .8, 1.9, 'lumiere' if side == 0 else 'baie_sombre', arch=True, frame='pise_clair', frame_width=.14)
        place_on(m, n, side, lb / 2 + .01)
    m.box((0, 0, h + lh - .3), (lb + .08, lb + .08, .5), mat('zellige'))
    for cx in (-1, 1):
        for cy in (-1, 1):
            stepped(m, cx * (lb / 2 - .2), cy * (lb / 2 - .2), h + lh, .45, 'brique_crue', 2)
    m.ico((0, 0, h + lh), (1.05, 1.05, .95), mat('tuile_verte'), 2)
    m.cylinder((0, 0, h + lh + .8), (0, 0, h + lh + 3.1), .04, .03, mat('cuivre'), 6)
    for k, r in enumerate((.26, .21, .15)):
        m.ico((0, 0, h + lh + 1.35 + k * .55), (r, r, r), mat('cuivre'), 2)
    return m


def dome_shell(m, x, y, z, radius, height, name, n=16, rings=7):
    rings_pts = []
    for j in range(rings + 1):
        a = j / rings * math.pi / 2; r = radius * math.cos(a) * (1 + .06 * math.sin(a * 2)); zz = z + height * math.sin(a)
        rings_pts.append([(x + r * math.cos(i * math.tau / n), y + r * math.sin(i * math.tau / n), zz) for i in range(n)])
    for j in range(rings):
        for i in range(n):
            k = (i + 1) % n
            m.surface([rings_pts[j][i], rings_pts[j][k], rings_pts[j + 1][k], rings_pts[j + 1][i]], [(0, 1, 2, 3)], mat(name))
    return rings_pts


def marabout():
    """Coupole de saint : cube chaulé, tambour octogonal, dôme nervuré."""
    m = Mesh(); b = 6; h = 4.8
    m.box((0, 0, .25), (b + .3, b + .3, .5), mat('pierre_taille'))
    m.box((0, 0, .5 + (h - .5) / 2), (b, b, h - .5), mat('chaux'))
    for cx in (-1, 1):
        for cy in (-1, 1):
            stepped(m, cx * (b / 2 - .3), cy * (b / 2 - .3), h, .65, 'chaux')
    m.cylinder((0, 0, h), (0, 0, h + 1.2), 2.5, 2.4, mat('chaux'), 8)
    rings = dome_shell(m, 0, 0, h + 1.2, 2.35, 2.5, 'chaux')
    m.detail = 1
    for i in range(0, 16, 2):
        for j in range(len(rings) - 1):
            m.beam(rings[j][i], rings[j + 1][i], .09, mat('pise_clair'))
    m.detail = 2
    m.cylinder((0, 0, h + 3.65), (0, 0, h + 4.6), .035, .03, mat('cuivre'), 6)
    m.ico((0, 0, h + 3.95), (.16, .16, .16), mat('cuivre'), 1)
    n = Mesh(); opening(n, 0, .5, 1.3, 2.6, 'bois_peint_vert', arch=True, frame='pierre_taille', studs=True)
    transform_into(m, n, (0, -b / 2 - .01, 0))
    for side in (1, 3):
        n = Mesh(); opening(n, 0, 2.2, .5, .9, 'baie_sombre', arch=True, grille=True, frame_width=.14)
        place_on(m, n, side, b / 2 + .01)
    return m


def fountain():
    """Fontaine murale : niche de zellige, bassin et petit auvent de tuiles vertes."""
    m = Mesh()
    m.box((0, .4, 1.9), (3.2, .8, 3.8), mat('chaux'))
    m.box((0, 0, 1.8), (2.4, .06, 2.8), mat('zellige'))
    outline(m, horseshoe(1.4, 2.2)[1:-1], 0, -.06, .9, .16, 'pierre_taille')
    m.box((0, -.4, .35), (2.6, .8, .7), mat('zellige'))
    m.box((0, -.4, .69), (2.3, .6, .04), mat('eau_oasis'))
    m.cylinder((0, -.02, 1.6), (0, -.3, 1.52), .04, .03, mat('cuivre'), 6)
    for sx in (-1, 1):
        m.beam((sx * 1.4, 0, 3.4), (sx * 1.4, -.55, 3.4), .14, mat('bois_sombre'))
    gable(m, 0, -.15, 3.5, 3.4, 1.0, .45, 'tuile_verte')
    return m


def stairs():
    m = Mesh()
    for j in range(20):
        height = (j + 1) * .3
        m.box((0, j * .46, height / 2), (14, .48, height), mat('pierre_taille'))
        m.box((0, j * .46 - .18, height + .025), (14, .11, .05), mat('gres_clair'))
        m.detail = 1
        for sx in (-1, 1): m.box((sx * 6.5, j * .46, height + .04), (.7, .47, .08), mat('sable_dune'))
        m.detail = 2
    for sx in (-1, 1): m.beam((sx * 7, 0, 1), (sx * 7, 9.2, 7), .35, mat('gres_ocre'))
    return m


# ---------------------------------------------------------------- végétation

def palm(index):
    """Palmier-dattier : stipe écaillé et arqué, couronne de palmes pliées en V."""
    rng = random.Random(900 + index); m = Mesh(); h = 9 + index * 2.2; lean = 1.1 + index * .45
    def axis(t): return Vector((lean * t * t, .15 * math.sin(t * 3 + index), h * t))
    n = 9; rings = 14; prev = None
    for j in range(rings + 1):
        t = j / rings; c = axis(t); r = .30 - .09 * t + .03 * math.sin(j * 1.7)
        ring = [(c.x + r * math.cos(i * math.tau / n), c.y + r * math.sin(i * math.tau / n), c.z) for i in range(n)]
        if prev:
            for i in range(n):
                k = (i + 1) % n
                m.surface([prev[i], prev[k], ring[k], ring[i]], [(0, 1, 2, 3)], mat('stipe_palmier'),
                          [(i / n, (j - 1) * h / rings / 2), ((i + 1) / n, (j - 1) * h / rings / 2), ((i + 1) / n, j * h / rings / 2), (i / n, j * h / rings / 2)])
        prev = ring
    crown = axis(1) + Vector((0, 0, .15))
    def frond(azimuth, elevation, length, name, segments=6, droop=.55):
        d = Vector((math.cos(azimuth), math.sin(azimuth), 0)); side = Vector((-d.y, d.x, 0))
        pts = []
        for k in range(segments + 1):
            s = k / segments
            p = crown + d * (length * s * math.cos(elevation)) + Vector((0, 0, length * s * math.sin(elevation) - droop * length * s * s))
            pts.append(p)
        for k in range(segments):
            s0 = k / segments; s1 = (k + 1) / segments
            w0 = .62 * length / 4.2; w1 = w0
            for sign, v in ((-1, 0), (1, 1)):
                a = pts[k] + side * sign * w0 + Vector((0, 0, .18 * w0)); b = pts[k + 1] + side * sign * w1 + Vector((0, 0, .18 * w1))
                quad = [tuple(pts[k]), tuple(pts[k + 1]), tuple(b), tuple(a)]
                uv = [(s0, .5), (s1, .5), (s1, v), (s0, v)]
                m.surface(quad, [(0, 1, 2, 3)], mat(name), uv)
    golden = 2.39996
    for k in range(20):
        el = math.radians(62 - k * 3.9 + rng.uniform(-6, 6)); length = rng.uniform(3.6, 4.6)
        frond(k * golden + rng.uniform(-.2, .2), el, length, 'palme', 6, .5 + k * .02)
    m.detail = 1
    for k in range(9):
        a = k * golden * 1.3 + .4
        frond(a, math.radians(-58 + rng.uniform(-8, 8)), rng.uniform(1.8, 2.4), 'palme_seche', 3, .15)
    m.detail = 0
    if index != 1:
        for k in range(3):
            a = k * math.tau / 3 + .5; p = crown + Vector((math.cos(a) * .45, math.sin(a) * .45, -.6))
            m.ico(tuple(p), (.26, .26, .42), mat('dattes'), 1)
    m.detail = 2
    return m


def acacia(index):
    """Acacia en parasol : tronc fourchu et plateaux de feuillage aplatis."""
    rng = random.Random(1300 + index); m = Mesh(); h = 4.4 + index * 1.1
    m.cylinder((0, 0, 0), (.3, .1, h * .45), .22, .15, mat('bois_sombre'), 7)
    tops = []
    for k in range(3 + index):
        a = k * math.tau / (3 + index) + rng.uniform(-.3, .3); r = rng.uniform(1.3, 2.4)
        tip = (math.cos(a) * r, math.sin(a) * r, h + rng.uniform(-.4, .3))
        m.beam((.3, .1, h * .45), tip, .14, mat('bois_sombre')); tops.append(tip)
    for tip in tops + [(0, 0, h + .3)]:
        for k in range(9):
            a = k * math.tau / 9 + rng.uniform(0, .6); rr = rng.uniform(.6, 1.9)
            c = (tip[0] + math.cos(a) * rr, tip[1] + math.sin(a) * rr, tip[2] + .3 + rng.uniform(-.15, .2))
            q = Quaternion((0, 0, 1), rng.uniform(0, math.tau)) @ Quaternion((1, 0, 0), rng.uniform(-.25, .25))
            m.foliage_card(c, (rng.uniform(1.8, 2.6), rng.uniform(1.5, 2.2)), q, mat('feuillage_acacia'))
    return m


# ---------------------------------------------------------------- relief

def sandstone_crag(index):
    """Chicot de grès tabulaire : bancs durs en saillie, bancs tendres en retrait."""
    rng = random.Random(index + 1918); m = Mesh(); n = 32; rings = 20; vs = []
    for j in range(rings):
        t = j / (rings - 1); band = j // 3
        hard = band % 2 == 0
        for i in range(n):
            a = i * math.tau / n
            r = (1.55 - t * .55) * (1 + .18 * math.sin(i * 2.1 + index) + rng.uniform(-.05, .05))
            r *= 1.13 if hard else .88
            r += (.08 if band % 3 == 1 else -.04)
            r += .06 * math.sin(i * 1.3 + j * .8)
            vs.append((math.cos(a) * 5 * r + t * 1.2, math.sin(a) * 4 * r, t * 20 + rng.uniform(-.2, .2)))
    for j in range(rings - 1):
        for i in range(n):
            a = j * n + i; b = j * n + (i + 1) % n; c = (j + 1) * n + (i + 1) % n; d = (j + 1) * n + i
            name = ('gres_rouge', 'gres_ocre', 'gres_clair', 'gres_ocre', 'gres_sombre', 'gres_rouge', 'gres_ocre')[(j // 3 + index) % 7]
            m.surface([vs[a], vs[b], vs[c], vs[d]], [(0, 1, 2), (0, 2, 3)], mat(name))
    top = vs[-n:]; center = tuple(sum(p[k] for p in top) / n for k in range(3))
    for i in range(n):
        m.surface([center, top[i], top[(i + 1) % n]], [(0, 1, 2)], mat('gres_ocre'))
    return m


def dune_field(x, y, index):
    """Cordons de dunes : crêtes vives et sinueuses, versant au vent doux, face d'avalanche raide.

    Deux familles de crêtes se croisent pour former des dunes en étoile ;
    le relief s'annule sur le pourtour du module pour se poser sur la plaine.
    """
    phase = index * 1.7
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    height = np.zeros_like(x)
    for k, (angle, frequency, amplitude) in enumerate(((.35 + index * .2, 1.25, 42), (1.35 + index * .2, 1.05, 24))):
        u = x * math.cos(angle) + y * math.sin(angle); v = -x * math.sin(angle) + y * math.cos(angle)
        u = u + .16 * np.sin(v * 3.1 + phase + k) + .06 * np.sin(v * 7.3 - phase)
        t = (u * frequency + .3 * k + index * .21) % 1
        profile = np.where(t < .74, t / .74, (1 - t) / .26) ** 1.25
        along = .55 + .45 * np.sin(v * 2.4 + phase * (k + 1))
        height = np.maximum(height, amplitude * profile * along)
    envelope = np.clip(1 - np.hypot(x * .9, y) ** 2, 0, 1)
    rip = (relief_noise(x * 14, y * 14, index + 4) - .5) * 1.2
    mask = np.clip((1 - np.maximum(abs(x), abs(y))) * 9, 0, 1)
    return np.maximum(0, height * envelope + rip * np.clip(height / 8, 0, 1)) * mask


def baked_ground(name, heights, size, colours):
    """Écrit la couleur et les normales fines calculées depuis un relief de module."""
    rgb = np.where(colours <= .0031308, colours * 12.92, 1.055 * np.maximum(colours, 0) ** (1 / 2.4) - .055)
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    image.pixels.foreach_set(np.concatenate((np.clip(rgb, 0, 1), np.ones((size, size, 1))), axis=2).astype(np.float32).ravel())
    image.filepath_raw = str(TEX / (name + '_BaseColor.png')); image.file_format = 'PNG'; image.save(); bpy.data.images.remove(image)
    gy, gx = np.gradient(heights)
    normals = np.stack((-gx, -gy, np.ones_like(gx)), axis=-1); normals /= np.linalg.norm(normals, axis=-1)[..., None]
    image = bpy.data.images.new(name + '_Normal', width=size, height=size, alpha=True); image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(np.concatenate((normals * .5 + .5, np.ones((size, size, 1))), axis=2).astype(np.float32).ravel())
    image.filepath_raw = str(TEX / (name + '_Normal.png')); image.file_format = 'PNG'; image.save(); bpy.data.images.remove(image)


def grid_module(field, name, sx, sy, n, material_name):
    m = Mesh(); vs = []
    for j in range(n + 1):
        for i in range(n + 1):
            x = -1 + 2 * i / n; y = -1 + 2 * j / n; vs.append((x * sx, y * sy, float(field(x, y))))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            for ids in ((a, a + 1, a + n + 2), (a, a + n + 2, a + n + 1)):
                v = [vs[k] for k in ids]
                m.surface(v, [(0, 1, 2)], mat(material_name), [(p[0] / (2 * sx) + .5, p[1] / (2 * sy) + .5) for p in v])
    return m


def dune(index):
    size = 1536; axis = np.linspace(-1, 1, size); xx, yy = np.meshgrid(axis, axis)
    heights = dune_field(xx, yy, index)
    dy, dx = np.gradient(heights, 200 / size, 220 / size); slope = np.hypot(dx, dy)
    shade = relief_noise(xx * 7, yy * 9, index + 3) - .5
    base = np.array((.80, .56, .33)); slip = np.array((.70, .44, .25)); crest = np.array((.88, .66, .42))
    lee = np.clip((dx - .15) * 1.8, 0, 1)
    col = base[None, None, :] * (1 + shade[..., None] * .10)
    col = col * (1 - lee[..., None] * .6) + slip * lee[..., None] * .6
    col = col * (1 - np.clip(slope - 1.1, 0, 1)[..., None] * .4) + crest * np.clip(slope - 1.1, 0, 1)[..., None] * .4
    phase = (xx * 160 + yy * 45 + shade * 9) % 1
    ripples = np.where(phase < .75, phase / .75, (1 - phase) / .25) * (1 - np.clip(slope * .6, 0, 1))
    col *= (.96 + ripples[..., None] * .06)
    baked_ground('dune_' + str(index), ripples * .45, size, col)
    return grid_module(lambda x, y: dune_field(x, y, index), 'dune_' + str(index), 110, 100, 120, 'dune_' + str(index))


def butte_field(x, y, index):
    a = np.arctan2(y, x); r = np.hypot(x, y)
    rim = .48 + .08 * np.sin(a * 3 + index) + .05 * np.sin(a * 7 + index * 2) + (relief_noise(x * 5, y * 5, index + 20) - .5) * .08
    cliff = np.clip((rim - r) / .05, 0, 1)
    talus = np.clip((rim + .32 - r) / .32, 0, 1) ** 1.6
    h = 62 + index * 10
    terraces = np.floor(cliff * 5) / 5 * .15 + cliff * .85
    height = h * np.maximum(terraces, talus * .38)
    mask = np.clip((1 - np.maximum(abs(x), abs(y))) * 9, 0, 1)
    return height * mask


def butte(index):
    size = 1024; axis = np.linspace(-1, 1, size); xx, yy = np.meshgrid(axis, axis)
    heights = butte_field(xx, yy, index); top = 62 + index * 10
    strata = np.floor(heights / top * 11 + (relief_noise(xx * 6, yy * 6, index) - .5) * .8)
    palette = np.array([(.52, .27, .15), (.66, .43, .24), (.74, .58, .41), (.46, .24, .14), (.62, .38, .20), (.33, .19, .12)])
    col = palette[(strata.astype(int) + index) % len(palette)]
    dy, dx = np.gradient(heights, 2 / size, 2 / size); slope = np.hypot(dx, dy)
    sand = np.clip((60 - slope) / 60, 0, 1) * np.clip(1 - heights / (top * .5), 0, 1)
    col = col * (1 - sand[..., None]) + np.array((.78, .55, .33)) * sand[..., None]
    varnish = np.clip(heights / top - .92, 0, 1) * 8
    col *= (1 - np.clip(varnish, 0, .4))[..., None]
    col *= (.9 + (relief_noise(xx * 40, yy * 40, index) - .5) * .25)[..., None]
    baked_ground('butte_' + str(index), heights * .02 + strata * .3, size, col)
    return grid_module(lambda x, y: butte_field(x, y, index), 'butte_' + str(index), 90, 90, 110, 'butte_' + str(index))


# ---------------------------------------------------------------- vie du ksar

def camel(index):
    """Dromadaire : debout, bâté pour la caravane, ou couché."""
    m = Mesh(); hide = 'cuir_chameau'
    lying = index == 2; lift = -1.05 if lying else 0
    m.ico((0, 0, 1.75 + lift), (1.2, .46, .5), mat(hide), 2)
    m.ico((-.1, 0, 2.2 + lift), (.55, .36, .48), mat(hide), 2)
    m.beam((.95, 0, 1.95 + lift), (1.45, 0, 2.55 + lift), .30, mat(hide))
    m.beam((1.45, 0, 2.55 + lift), (1.62, 0, 2.95 + lift), .22, mat(hide))
    m.ico((1.82, 0, 2.95 + lift), (.36, .15, .17), mat(hide), 1)
    m.ico((1.6, 0, 3.08 + lift), (.12, .13, .12), mat(hide), 1)
    m.beam((-1.15, 0, 1.9 + lift), (-1.35, 0, 1.2 + lift), .07, mat(hide))
    for sx in (-1, 1):
        for sy in (-1, 1):
            hip = (sx * .72, sy * .24, 1.45 + lift)
            if lying:
                m.beam(hip, (sx * .72 + .55, sy * .34, .18), .17, mat(hide))
            else:
                knee = (sx * .76 + (.05 if sx > 0 else -.08), sy * .25, .78)
                m.beam(hip, knee, .18, mat(hide)); m.beam(knee, (sx * .74, sy * .25, .08), .12, mat(hide))
                m.ico((sx * .74 + .05, sy * .25, .05), (.14, .1, .05), mat(hide), 1)
    if index >= 1:
        m.box((-.1, 0, 2.62 + lift), (1.1, 1.05, .08), mat('tapis'))
        for sy in (-1, 1):
            m.ico((-.1, sy * .62, 2.15 + lift), (.5, .22, .38), mat('tissu_ecru' if sy < 0 else 'tissu_indigo'), 1)
        m.beam((-.55, 0, 2.75 + lift), (.35, 0, 2.75 + lift), .1, mat('bois_sombre'))
    return m


def nomad_tent():
    """Tente de poil de chèvre ouverte au levant, tapis et cordes."""
    m = Mesh(); w = 8; d = 5; nx = 10; ny = 6
    def z(x, y):
        return 2.1 - .75 * abs(y + .4) / (d / 2) - .25 * (abs(x) / (w / 2)) ** 2 + (.35 if y < -d / 2 + .1 else 0)
    pts = [[(-w / 2 + w * i / nx, -d / 2 + d * j / ny, z(-w / 2 + w * i / nx, -d / 2 + d * j / ny)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            m.surface([pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]], [(0, 1, 2, 3)], mat('tissu_poil'))
    for i in range(nx):
        m.surface([pts[ny][i], pts[ny][i + 1], (pts[ny][i + 1][0], d / 2 + .3, 0), (pts[ny][i][0], d / 2 + .3, 0)], [(0, 1, 2, 3)], mat('tissu_poil'))
    for x in (-2.4, 0, 2.4):
        m.cylinder((x, -.4, 0), (x, -.4, 2.15), .05, .05, mat('bois_palmier'), 6)
        m.cylinder((x, -d / 2, 0), (x, -d / 2, z(x, -d / 2)), .045, .045, mat('bois_palmier'), 6)
    m.box((0, -.2, .02), (6.4, 3.4, .04), mat('tapis'))
    m.detail = 0
    for x in (-w / 2, w / 2):
        for y in (-d / 2, 0):
            m.beam((x, y, z(x, y)), (x * 1.35, y - .8, 0), .02, mat('bois_sombre'))
    m.detail = 2
    return m


def lantern():
    m = Mesh()
    m.cylinder((0, 0, 0), (0, 0, 2.75), .08, .065, mat('bois_sombre'), 8)
    m.cylinder((0, 0, 2.75), (0, 0, 2.9), .17, .19, mat('cuivre'), 8)
    m.cylinder((0, 0, 2.9), (0, 0, 3.32), .15, .15, mat('lumiere'), 8)
    m.cylinder((0, 0, 3.32), (0, 0, 3.55), .2, .02, mat('cuivre'), 8)
    m.detail = 0
    for k in range(8):
        a = k * math.tau / 8
        m.beam((.16 * math.cos(a), .16 * math.sin(a), 2.9), (.16 * math.cos(a), .16 * math.sin(a), 3.32), .02, mat('cuivre'))
    m.detail = 2
    return m


def standard():
    """Étendard : même géométrie de toile que la bannière de la citadelle, animée pareil."""
    m = Mesh()
    m.cylinder((0, 0, 0), (0, 0, 7.5), .075, .055, mat('bois_sombre'), 8)
    m.beam((-.1, 0, 7), (2.4, 0, 7), .065, mat('bois_sombre'))
    for j in range(16):
        for i in range(8):
            def p(ii, jj):
                x = ii * 2.2 / 8; z = 7 - jj * 3.8 / 16; y = .20 * math.sin(x * 3 + z * 2) * (7 - z) / 3.8
                return x, y, z
            m.surface([p(i, j), p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)], [(0, 1, 2, 3)], mat('tissu_etendard'))
    m.ico((0, 0, 7.65), (.13, .13, .13), mat('cuivre'), 1)
    for k in range(8):
        a = k * math.pi / 4
        m.beam((1.1, -.26, 5.3), (1.1 + .42 * math.cos(a), -.26, 5.3 + .42 * math.sin(a)), .09, mat('cuivre'), .04)
    return m


def guard():
    m = Mesh()
    m.cylinder((0, 0, .05), (0, 0, 1.5), .46, .28, mat('tissu_ecru'), 10)
    m.cylinder((0, 0, 1.5), (0, 0, 1.85), .3, .22, mat('tissu_ecru'), 10)
    m.ico((0, 0, 2.02), (.17, .17, .2), mat('cuir_chameau'), 2)
    m.ico((0, .02, 2.14), (.23, .23, .17), mat('tissu_indigo'), 2)
    m.beam((0, -.14, 1.97), (0, -.2, 2.0), .22, mat('tissu_indigo'), .05)
    m.beam((.28, 0, 1.7), (.6, -.2, 1.1), .16, mat('tissu_ecru'))
    m.cylinder((.65, -.2, 0), (.65, -.2, 3.2), .035, .035, mat('bois_sombre'), 6)
    m.cylinder((.65, -.2, 3.2), (.65, -.2, 3.6), .08, 0, mat('fer_noir'), 6)
    m.cylinder((-.38, -.12, 1.2), (-.44, -.16, 1.2), .36, .36, mat('cuir_chameau'), 12)
    return m


def paving():
    m = Mesh()
    for j in range(12):
        for i in range(6):
            m.box(((i - 2.5) * .8 + (j % 2) * .25, (j - 5.5) * .66, 0), (.75, .61, .14), mat('sol_dalle'))
    return m


def storage():
    m = Mesh()
    for k, (x, y, s) in enumerate(((0, 0, 1.3), (.8, .35, 1.05), (-.75, .45, 1.15), (.2, .95, .9))):
        jar(m, x, y, 0, s)
    for j in range(3):
        for i in range(3 - j):
            x = 1.6 + i * .3 + j * .15; z = .15 + j * .27
            m.cylinder((x, -.6, z), (x, .6, z), .15, .14, mat('bois_palmier'), 8)
    for k in range(3):
        m.ico((-1.5 + k * .45, -.5, .25), (.28, .22, .26), mat('tissu_ecru'), 1)
    return m


def well():
    m = Mesh()
    m.cylinder((0, 0, 0), (0, 0, .85), 1.0, .95, mat('gres_ocre'), 16)
    m.cylinder((0, 0, .86), (0, 0, .87), .78, .78, mat('baie_sombre'), 16)
    for sx in (-1, 1):
        m.beam((sx * 1.1, 0, 0), (sx * .95, 0, 2.6), .18, mat('bois_palmier'))
    m.beam((-1.2, 0, 2.55), (1.2, 0, 2.55), .16, mat('bois_palmier'))
    m.cylinder((0, -.12, 2.3), (0, .12, 2.3), .2, .2, mat('bois_sombre'), 10)
    m.beam((0, 0, 2.1), (0, 0, 1.25), .02, mat('bois_sombre'))
    m.cylinder((0, 0, .95), (0, 0, 1.25), .14, .18, mat('cuir_chameau'), 8)
    m.box((1.9, .2, .3), (1.8, .7, .6), mat('pierre_taille'))
    m.box((1.9, .2, .59), (1.55, .45, .03), mat('eau_oasis'))
    return m


def stall(kind):
    """Échoppe du souk : cadre de palmier, toile inclinée, comptoir et marchandises."""
    m = Mesh(); w = 4.5; d = 3
    cloth = {'epices': 'tissu_garance', 'tissus': 'tissu_indigo', 'poteries': 'tissu_safran', 'dattes': 'tissu_ecru'}[kind]
    for sx in (-1, 1):
        m.cylinder((sx * w / 2, -d / 2, 0), (sx * w / 2, -d / 2, 2.5), .07, .06, mat('bois_palmier'), 6)
        m.cylinder((sx * w / 2, d / 2, 0), (sx * w / 2, d / 2, 3.1), .07, .06, mat('bois_palmier'), 6)
    m.surface([(-w / 2 - .2, -d / 2 - .7, 2.4), (w / 2 + .2, -d / 2 - .7, 2.4), (w / 2 + .2, d / 2 + .1, 3.15), (-w / 2 - .2, d / 2 + .1, 3.15)], [(0, 1, 2, 3)], mat(cloth))
    m.detail = 1
    for k in range(9):
        x = -w / 2 - .2 + (k + .5) * (w + .4) / 9
        m.surface([(x - .25, -d / 2 - .7, 2.4), (x + .25, -d / 2 - .7, 2.4), (x, -d / 2 - .72, 2.12)], [(0, 1, 2)], mat(cloth))
    m.detail = 2
    m.box((0, d / 2 - .05, 1.5), (w, .1, 3.0), mat('bois_palmier'))
    m.box((0, -d / 2 + .6, .42), (w - .3, .9, .84), mat('bois_palmier'))
    m.box((0, -d / 2 + .6, .86), (w - .1, 1.0, .05), mat('tapis'))
    if kind == 'epices':
        colors = ('epices_rouge', 'epices_jaune', 'epices_vert')
        for i in range(6):
            for j in range(2):
                x = -1.75 + i * .7; y = -d / 2 + .35 + j * .5
                m.cylinder((x, y, .88), (x, y, .98), .19, .24, mat('poterie'), 10)
                m.detail = 1 if j else 2
                m.cylinder((x, y, .98), (x, y, 1.28), .22, .02, mat(colors[(i + j) % 3]), 10)
                m.detail = 2
        for k in range(5):
            m.box((-1.8 + k * .9, d / 2 - .35, 1.1), (.6, .4, 1.1 + (k % 2) * .3), mat('tissu_ecru'))
    elif kind == 'tissus':
        for k in range(7):
            m.box((-1.9 + k * .62, -d / 2 + .55, .98), (.55, .8, .22 + (k % 3) * .1), mat(('tissu_garance', 'tissu_indigo', 'tissu_safran', 'tissu_ecru')[k % 4]))
        m.beam((-w / 2, d / 2 - .4, 2.6), (w / 2, d / 2 - .4, 2.6), .06, mat('bois_sombre'))
        for k in range(6):
            m.box((-1.9 + k * .76, d / 2 - .4, 1.7), (.62, .03, 1.8), mat(('tapis', 'tissu_indigo', 'tissu_garance', 'tissu_safran')[k % 4]))
    elif kind == 'poteries':
        for k in range(6):
            jar(m, -1.8 + k * .72, -d / 2 + .6, .88, .45 + (k % 2) * .15)
        for k in range(5):
            x = -1.7 + k * .85
            m.cylinder((x, d / 2 - .6, 0), (x, d / 2 - .6, .12), .32, .34, mat('poterie'), 12)
            m.cylinder((x, d / 2 - .6, .12), (x, d / 2 - .6, .55), .3, .03, mat('poterie'), 12)
        for k in range(4):
            jar(m, -1.6 + k * 1.1, d / 2 - 1.3, 0, .9)
    else:
        for k in range(5):
            x = -1.8 + k * .9
            m.cylinder((x, -d / 2 + .6, .88), (x, -d / 2 + .6, 1.15), .3, .36, mat('bois_palmier'), 10)
            m.detail = 1
            m.ico((x, -d / 2 + .6, 1.16), (.33, .33, .12), mat('dattes'), 1)
            m.detail = 2
        for k in range(4):
            m.ico((-1.5 + k, d / 2 - .45, 2.2), (.18, .18, .45), mat('dattes'), 1)
            m.beam((-1.5 + k, d / 2 - .45, 2.65), (-1.5 + k, d / 2 - .45, 2.95), .02, mat('bois_sombre'))
    return m


def rug_rack():
    m = Mesh()
    for x in (-2.2, 2.2):
        m.cylinder((x, 0, 0), (x, 0, 2.9), .07, .06, mat('bois_palmier'), 6)
    m.beam((-2.3, 0, 2.8), (2.3, 0, 2.8), .08, mat('bois_palmier'))
    for k, x in enumerate((-1.4, 0, 1.4)):
        m.box((x, 0, 1.6 + .1 * (k % 2)), (1.25, .03, 2.3 - .2 * (k % 2)), mat('tapis' if k != 1 else 'tissu_indigo'))
    for k in range(3):
        m.cylinder((-1.2 + k * .3, .9, .13 + k * .02), (1.2 - k * .2, .9, .13 + k * .02), .13, .13, mat('tapis'), 8)
    return m


def jars():
    m = Mesh()
    for k, (x, y, s) in enumerate(((0, 0, 1.5), (1.0, .2, 1.2), (-1.0, .3, 1.3), (.5, -.9, 1.0), (-.6, -.8, .9), (1.6, -.7, .8), (-1.7, -.5, 1.1))):
        jar(m, x, y, 0, s, 'poterie' if k % 3 else 'pise_clair')
    return m


def velum():
    m = Mesh(); nx = 8; ny = 6; w = 6; d = 4
    pts = [[(-w / 2 + w * i / nx, -d / 2 + d * j / ny, 4.1 - .45 * math.sin(math.pi * i / nx) * math.sin(math.pi * j / ny)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            m.surface([pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]], [(0, 1, 2, 3)], mat('tissu_ecru' if (i // 2) % 2 else 'tissu_safran'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.cylinder((sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, 4.2), .07, .06, mat('bois_palmier'), 6)
    return m


def jobs(tex):
    global TEX; TEX = tex
    result = [(f'maison_pise_{i}', lambda j=i: house(j), 'batiment') for i in range(6)]
    result += [(f'tour_ksar_{i}', lambda j=i: tower(j), 'repere') for i in range(3)]
    result += [('rempart_pise_10m', wall, 'module'), ('porte_ksar', gate, 'module'), ('pont_arcades_14m', bridge, 'module'),
               ('mosquee_salle_12m', prayer_hall, 'module'), ('mosquee_portail', portal, 'module'), ('minaret', minaret, 'module'),
               ('coupole_marabout', marabout, 'module'), ('fontaine_zellige', fountain, 'module')]
    result += [(f'palmier_{i}', lambda j=i: palm(j), 'arbre') for i in range(3)]
    result += [(f'acacia_{i}', lambda j=i: acacia(j), 'arbre') for i in range(2)]
    result += [(f'falaise_gres_{i}', lambda j=i: sandstone_crag(j), 'roche') for i in range(4)]
    result += [(f'dune_{i}', lambda j=i: dune(j), 'relief') for i in range(3)]
    result += [(f'butte_{i}', lambda j=i: butte(j), 'relief') for i in range(2)]
    result += [('lanterne', lantern, 'accessoire'), ('etendard', standard, 'accessoire'), ('garde', guard, 'accessoire'),
               ('escalier', stairs, 'accessoire'), ('dalles', paving, 'accessoire'), ('jarres_reserve', storage, 'accessoire'),
               ('puits', well, 'accessoire'), ('tente_nomade', nomad_tent, 'accessoire')]
    result += [(f'chameau_{i}', lambda j=i: camel(j), 'accessoire') for i in range(3)]
    result += [(f'souk_{k}', lambda j=k: stall(j), 'module') for k in ('epices', 'tissus', 'poteries', 'dattes')]
    result += [('souk_tapis', rug_rack, 'module'), ('souk_jarres', jars, 'module'), ('souk_velum', velum, 'module')]
    return result
