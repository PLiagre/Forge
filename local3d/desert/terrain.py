"""Terrain Unity du ksar : hauteurs, couches de sol et touffes tirées de paysage.py.

Le relief ne change pas de source : chaque hauteur est `paysage.field`, la fonction
qui sculptait déjà le maillage Blender. Ce module l'échantillonne sur une grille
régulière pour un Unity Terrain, que la ville creusera et peindra à l'exécution.

Repère : Unity reçoit (-x, z, -y) du repère Blender. Le terrain Unity a son coin
en (-TAILLE/2, base, -TAILLE/2) ; l'échantillon (i, j) de la grille est donc au
point Blender (TAILLE/2 - i*pas, TAILLE/2 - j*pas). Les fichiers sont écrits
ligne j par ligne j, colonne i dans la ligne, en petit-boutiste.

Fichiers écrits dans `sorties/ville/<implantation>/` :
  hauteurs.f32         altitudes en mètres, float32, RESOLUTION² valeurs
  horizon.f32          altitudes de l'horizon de dunes, même repère, pas de HORIZON_PAS
  couches.u8           poids des quatre couches, 4 octets par pixel, COUCHES² pixels
  details_<nom>.u8     nombre de touffes par cellule de 1 m, un octet par cellule
  terrain.json         dimensions, empreintes, couverture et échantillon de contrôle
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local3d.desert import paysage  # noqa: E402
from local3d.citadelle.paysage import smoothstep  # noqa: E402

TAILLE = 1024.0      # m : le côté du terrain ; le cordon de dunes commence à 175 m du centre
RESOLUTION = 2049    # échantillons de hauteur par côté : un pas de 0,5 m, sous la trame de 0,75 m
COUCHES = 1024       # pixels de la carte des couches par côté : 1 m
DETAILS = 1024       # cellules des cartes de touffes par côté : 1 m
MARGE_BAS = 6.0      # m sous le point le plus bas : de quoi creuser un puits ou une cave
MARGE_HAUT = 12.0    # m au-dessus du point le plus haut : de quoi remblayer une terrasse
NOMS_COUCHES = ['sable', 'reg', 'gres', 'terre']
TOUFFES = ['GrassDry_A', 'GrassDry_B', 'GrassDry_C', 'BushDry_B', 'Bush_Twig']
HORIZON = 3072.0     # m : le cordon de dunes continue jusqu'au brouillard (fin à 1 500 m du centre)
HORIZON_PAS = 16.0   # m : le côté du terrain (1 024 m) en est un multiple, les bords tombent sur la grille
MARCHABLE = 0.05     # m : écart toléré sur un sol où l'on marche, le sixième d'une marche de 0,32 m
SORTIES = Path(__file__).resolve().parent / 'sorties' / 'ville'


def pas():
    return TAILLE / (RESOLUTION - 1)


def grille_hauteurs(seed):
    """paysage.field sur la grille ; calculée par bandes pour tenir en mémoire."""
    axe = TAILLE / 2 - np.arange(RESOLUTION) * pas()
    h = np.empty((RESOLUTION, RESOLUTION))
    bande = 128
    for j0 in range(0, RESOLUTION, bande):
        xx, yy = np.meshgrid(axe, axe[j0:j0 + bande])
        h[j0:j0 + bande] = paysage.field(xx, yy, seed)
    return h


def centres(n):
    """Coordonnées Blender des centres de pixels d'une carte n×n posée sur le terrain."""
    axe = TAILLE / 2 - (np.arange(n) + .5) * TAILLE / n
    return np.meshgrid(axe, axe)


def interpolee(h, bx, by):
    """Hauteur entre les échantillons, comme la surface d'un Unity Terrain.

    Unity ne fait pas une interpolation bilinéaire : chaque carreau est coupé en deux
    triangles le long de la diagonale (i, j)–(i+1, j+1). Mesuré sur l'échantillon avec
    TerrainData.GetInterpolatedHeight : 0,01 mm d'écart avec ce découpage, 13 cm avec
    la bilinéaire.
    """
    u = (TAILLE / 2 - np.asarray(bx)) / pas(); v = (TAILLE / 2 - np.asarray(by)) / pas()
    i = np.clip(np.floor(u).astype(int), 0, RESOLUTION - 2); j = np.clip(np.floor(v).astype(int), 0, RESOLUTION - 2)
    fu = u - i; fv = v - j
    a = h[j, i]; b = h[j, i + 1]; c = h[j + 1, i]; e = h[j + 1, i + 1]
    return np.where(fu > fv, a + (b - a) * fu + (e - b) * fv, a + (c - a) * fv + (e - c) * fu)


def pente(h, n):
    """Pente (tangente) de la grille, ramenée aux centres d'une carte n×n."""
    gy, gx = np.gradient(h, pas())
    g = np.hypot(gx, gy)
    xx, yy = centres(n)
    return interpolee(g, xx, yy)


def usages(xx, yy, seed):
    """Distance aux rues du plan, et masque des lieux déjà pris (rues, guelta, seuils, jardins)."""
    near = np.full(xx.shape, np.inf)
    for route in paysage.plan(seed)['routes']:
        if not route['ground']:
            continue
        d, _ = paysage.nearest(xx, yy, route['points'][::3] + [route['points'][-1]])
        near = np.minimum(near, d - route['width'] / 2)
    pris = near < 3
    px, py, _ = paysage.plan(seed)['pool']['position']; w, d = paysage.plan(seed)['pool']['size']
    pris |= ((xx - px) / (w * .5 + 2.5)) ** 2 + ((yy - py) / (d * .5 + 2.5)) ** 2 < 1
    for pad in paysage.pads(seed):
        cx, cy, _ = pad.get('pad_position', pad['position']); sw, sd = pad['size']
        pris |= (abs(xx - cx) < sw / 2 + 3) & (abs(yy - cy) < sd / 2 + 3)
    return near, pris


def couches(h, seed):
    """Poids sable, reg, grès, terre ; leur somme vaut 1 en chaque pixel.

    Le grès affleure sur les pentes fortes hors des dunes (le versant d'avalanche d'une
    dune reste du sable) ; la terre de jardin borde la guelta et les jardins ; le reste
    se partage entre reg et sable par grandes plaques, le lit de l'oued restant en galets.
    Un bruit fin rend chaque bord irrégulier.
    """
    xx, yy = centres(COUCHES)
    g = pente(h, COUCHES)
    dune = paysage.dunes(xx, yy, seed)
    oued = paysage.oued_distance(xx, yy)
    plaque = paysage.value_noise(xx * .018, yy * .018, seed + 11)
    fin = paysage.value_noise(xx * .21, yy * .21, seed + 13) - .5
    grain = paysage.value_noise(xx * .9, yy * .9, seed + 17) - .5
    bord = .6 * fin + .25 * grain
    gres = smoothstep((g - .55 + .35 * bord) / .25) * (1 - smoothstep((dune - .4) / 1.2))
    px, py, _ = paysage.plan(seed)['pool']['position']; w, d = paysage.plan(seed)['pool']['size']
    guelta = np.hypot((xx - px) / (w * .5 + 24), (yy - py) / (d * .5 + 18))
    terre = 1 - smoothstep((guelta - .75 + .5 * bord) / .3)
    for plot in paysage.plan(seed)['plots']:
        cx, cy, _ = plot['position']; sw, sd = plot['size']
        dist = np.maximum(abs(xx - cx) - sw / 2, abs(yy - cy) - sd / 2)
        terre = np.maximum(terre, 1 - smoothstep((dist - 1.5 + 4 * bord) / 2.5))
    terre = np.clip(terre, 0, 1)
    gres = gres * (1 - terre)
    reste = 1 - terre - gres
    sable = smoothstep((dune - .6 + 1.5 * bord) / 1.4)
    sable = np.maximum(sable, smoothstep((plaque - .58 + .25 * bord) / .12))
    sable = sable * smoothstep((oued - 6 + 8 * bord) / 6)
    w = np.stack([reste * sable, reste * (1 - sable), gres, terre], axis=-1)
    return w / w.sum(axis=-1, keepdims=True)


def touffes(poids, seed):
    """Nombre de touffes par cellule de 1 m : herbes sèches sur le reg, broussailles le long de l'oued.

    Les touffes vont par groupes (bruit) et jamais sur une rue, un seuil, un jardin ou la
    guelta : la ville posera ses propres rues par-dessus, et le contrôle le vérifie.
    """
    xx, yy = centres(DETAILS)
    _, pris = usages(xx, yy, seed)
    rng = np.random.default_rng(seed + 4051)
    if poids.shape[:2] != xx.shape:
        raise ValueError('Cartes de couches et de touffes de tailles différentes')
    groupe = paysage.value_noise(xx * .06, yy * .06, seed + 23)
    herbe = .09 * poids[..., 1] * smoothstep((groupe - .45) / .25) * (1 - poids[..., 2])
    oued = paysage.oued_distance(xx, yy)
    px, py, _ = paysage.plan(seed)['pool']['position']
    humide = np.maximum(1 - smoothstep((oued - 4) / 18), 1 - smoothstep((np.hypot(xx - px, yy - py) - 25) / 35))
    buisson = .035 * humide * (1 - poids[..., 2]) * (1 - poids[..., 0])
    cartes = {}
    tire = rng.random(xx.shape)
    herbe_ici = (tire < herbe) & ~pris
    espece = rng.integers(0, 3, xx.shape)
    for k in range(3):
        cartes[TOUFFES[k]] = (herbe_ici & (espece == k)).astype(np.uint8) * (1 + (rng.random(xx.shape) < .25))
    buisson_ici = (rng.random(xx.shape) < buisson) & ~pris
    brindille = rng.random(xx.shape) < .4
    cartes[TOUFFES[3]] = (buisson_ici & ~brindille).astype(np.uint8)
    cartes[TOUFFES[4]] = (buisson_ici & brindille).astype(np.uint8)
    return cartes


def echantillon(seed):
    """Points de contrôle dérivés du plan : chaque point de rue au sol, les coins et centres
    des seuils et des jardins, et une grille jitterée d'un point par carré de 16 m."""
    points = []
    for route in paysage.plan(seed)['routes']:
        if route['ground']:
            points += [('rue', p[0], p[1]) for p in route['points']]
    for pad in paysage.pads(seed):
        cx, cy, _ = pad.get('pad_position', pad['position']); sw, sd = pad['size']
        points += [('seuil', cx + a * sw / 2, cy + b * sd / 2) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    rng = np.random.default_rng(seed + 977)
    cote = 16.0; n = int(TAILLE // cote)
    bord = 2 * pas()  # le dernier carreau de la grille n'a pas de voisin pour l'interpolation
    for j in range(n):
        for i in range(n):
            x = -TAILLE / 2 + (i + rng.random()) * cote; y = -TAILLE / 2 + (j + rng.random()) * cote
            if abs(x) < TAILLE / 2 - bord and abs(y) < TAILLE / 2 - bord:
                points.append(('libre', x, y))
    return points


def empreinte(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exporter(ident, seed, dossier=None):
    dossier = Path(dossier or SORTIES / ident); dossier.mkdir(parents=True, exist_ok=True)
    t = time.monotonic()
    h = grille_hauteurs(seed)
    base = math.floor(float(h.min()) - MARGE_BAS); haut = math.ceil(float(h.max()) + MARGE_HAUT)
    h.astype('<f4').tofile(dossier / 'hauteurs.f32')
    n = int(round(HORIZON / HORIZON_PAS)) + 1
    axe = HORIZON / 2 - np.arange(n) * HORIZON_PAS
    xx, yy = np.meshgrid(axe, axe)
    paysage.field(xx, yy, seed).astype('<f4').tofile(dossier / 'horizon.f32')
    poids = couches(h, seed)
    q = np.round(poids * 255).astype(np.int16)
    # Les poids arrondis doivent encore sommer à 255 : l'écart va à la couche dominante.
    ecart = 255 - q.sum(axis=-1)
    dominante = np.argmax(poids, axis=-1)
    np.put_along_axis(q, dominante[..., None], np.take_along_axis(q, dominante[..., None], -1) + ecart[..., None], -1)
    if q.min() < 0 or np.any(q.sum(axis=-1) != 255):
        raise ValueError('Poids des couches mal arrondis')
    q.astype(np.uint8).tofile(dossier / 'couches.u8')
    cartes = touffes(poids, seed)
    for nom, carte in cartes.items():
        carte.astype(np.uint8).tofile(dossier / ('details_' + nom + '.u8'))
    points = echantillon(seed)
    bx = np.array([p[1] for p in points]); by = np.array([p[2] for p in points])
    reference = paysage.field(bx, by, seed)
    ideal = interpolee(h.astype('<f4').astype(float), bx, by)
    rues = np.array([p[:2] for r in paysage.plan(seed)['routes'] if r['ground'] for p in r['points']])
    gx, gy, gz = paysage.plan(seed)['pool']['position']; gw, gd = paysage.plan(seed)['pool']['size']
    # Écrit pour JsonUtility : des listes alignées plutôt que des dictionnaires.
    rapport = {
        'implantation': ident, 'graine': seed,
        'source': 'local3d.desert.paysage.field',
        'repere': 'Unity = (-x_blender, z_blender, -y_blender) ; coin du terrain en (-taille/2, base, -taille/2)',
        'taille': TAILLE, 'resolution': RESOLUTION, 'pas': pas(), 'base': base, 'hauteur': haut - base,
        'couches_resolution': COUCHES, 'details_resolution': DETAILS,
        'couches': NOMS_COUCHES,
        'couverture': [float(q[..., k].sum() / 255 / q[..., k].size) for k in range(len(NOMS_COUCHES))],
        'touffes': TOUFFES,
        'nombre_touffes': [int(cartes[n].sum()) for n in TOUFFES],
        'tolerance_marchable': MARCHABLE,
        'fichiers': [{'nom': name, 'sha256': empreinte(dossier / name)} for name in
                     ['hauteurs.f32', 'horizon.f32', 'couches.u8'] + ['details_' + n + '.u8' for n in TOUFFES]],
        'horizon_taille': HORIZON, 'horizon_resolution': n,
        'echantillon': [{'nature': p[0], 'x': float(p[1]), 'y': float(p[2]), 'field': float(r), 'grille': float(g)}
                        for p, r, g in zip(points, reference, ideal)],
        'guelta': {'x': gx, 'y': gy, 'z': gz, 'largeur': gw, 'profondeur': gd},
        'oued': [{'x': float(x), 'y': float(y)} for x, y, _ in paysage.oued_points()],
        'centre': {'x': float(rues[:, 0].mean()), 'y': float(rues[:, 1].mean())},
        'duree_s': round(time.monotonic() - t, 1),
    }
    ecarts = np.abs(ideal - reference)
    rapport['ecart_grille'] = {'mediane': float(np.median(ecarts)), 'p95': float(np.percentile(ecarts, 95)), 'max': float(ecarts.max())}
    (dossier / 'terrain.json').write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding='utf-8')
    return rapport


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--nom', required=True); p.add_argument('--graine', type=int, required=True)
    a = p.parse_args()
    r = exporter(a.nom, a.graine)
    print(a.nom, 'base', r['base'], 'hauteur', r['hauteur'], 'couverture', r['couverture'],
          'touffes', r['nombre_touffes'], 'écart grille', r['ecart_grille'], r['duree_s'], 's')
