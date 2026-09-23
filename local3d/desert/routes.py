"""Routes du joueur (lot 263) : jeu de gestes, référence et jugement du contrôle Unity.

Unity pose les routes ; il ne se juge pas. Ce module :

1. écrit, par implantation, `sorties/ville/<implantation>/routes/gestes.json` : les
   paramètres du profil (seule source : Unity les y lit) et cinq familles de gestes,
   chacune vérifiée sur la grille d'origine au moment où elle est tirée ;
2. rejoue, depuis `hauteurs.f32`, chaque route dans l'ordre sur l'axe qu'Unity a
   échantillonné : profil lissé, refus, terrain aplani et talus. C'est la référence ;
3. juge le rapport d'Unity (`unity-routes.json`) et ses grilles exportées, puis
   joue chaque contre-épreuve du jugement : chacune doit le faire échouer.

Repère : celui de `paysage.py` (Blender). Le sommet (i, j) de la grille est en
(TAILLE/2 - i*pas, TAILLE/2 - j*pas) ; les tableaux sont indexés [j, i].
"""
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local3d.desert import paysage, terrain  # noqa: E402

# Les paramètres du profil ; Unity les lit dans gestes.json, il ne les recopie pas.
PARAMETRES = {
    'pas': terrain.pas(),      # m : l'axe est échantillonné au pas du terrain
    'fenetre': 10.0,           # m : moyenne glissante du profil en long (ordre de grandeur plausible)
    'pente_max': 0.12,         # au-delà, la route est refusée
    'talus': 0.5,              # pente du talus : 1:2
    'talus_max': 15.0,         # m au-delà du bord : un talus qui ne s'est pas refermé là est refusé
    'bruit_bord': 0.6,         # m : amplitude du bruit qui rend le bord peint irrégulier
    'fondu_bord': 0.75,        # m : largeur du fondu de la peinture au bord
    'arrondi': 0.01,           # m : les points du joueur sont arrondis au centimètre
}
TOLERANCE_PROFIL = 0.03        # m : écart toléré entre le terrain sous l'axe et le profil (brief, SC2)
ECART_POINTS = 0.02           # m : l'axe passe par les points du joueur (corde de 0,5 m sur une courbe douce : quelques mm)
ECART_CAPTURE = 6              # écart moyen des pixels sous lequel une capture est uniforme (comme la V0)
FAMILLES = ['ancienne', 'plaine', 'flanc', 'raide_long', 'raide_travers']
ATTENDU = {'plaine': 'acceptee', 'flanc': 'acceptee', 'raide_long': 'pente', 'raide_travers': 'talus'}
COUCHES_ROUTES = ['Ville_sable', 'Ville_reg', 'Ville_gres', 'Ville_terre', 'Ville_terre_battue', 'Ville_paves']
REVETEMENTS = {'terre': 4, 'paves': 5}
LARGEUR_NEUVE = 4.0


def dossier(ident):
    return terrain.SORTIES / ident / 'routes'


def grille(ident):
    n = terrain.RESOLUTION
    chemin = terrain.SORTIES / ident / 'hauteurs.f32'
    if not chemin.exists():
        raise RuntimeError(ident + ' : ' + str(chemin) + ' absent — lancer d’abord py local3d/atelier_desert.py terrain')
    return np.fromfile(chemin, dtype='<f4').reshape(n, n).astype(float)


def hauteur(h, x, y):
    return terrain.interpolee(h, x, y)


def gradient(h, x, y):
    e = terrain.pas()
    gx = (hauteur(h, x + e, y) - hauteur(h, x - e, y)) / (2 * e)
    gy = (hauteur(h, x, y + e) - hauteur(h, x, y - e)) / (2 * e)
    return gx, gy


# ---------- La référence : profil, refus, terrain taillé ----------

def longueurs(axe):
    d = np.diff(axe, axis=0)
    return np.concatenate([[0.0], np.cumsum(np.sqrt(d[:, 0] * d[:, 0] + d[:, 1] * d[:, 1]))])


def demi_fenetre(P):
    """Échantillons de part et d'autre dans la moyenne glissante."""
    return max(1, round(P['fenetre'] / (2 * P['pas'])))


def profil(h, axe, P):
    """Hauteur d'origine sous chaque échantillon, puis moyenne glissante centrée.

    La fenêtre compte des échantillons, pas des mètres : bornée en distance, elle gagnait ou
    perdait un échantillon d'un pas à l'autre (égalités à la virgule près) et la moyenne
    sautait — 38 % mesurés sur la descente de l'oasis, dont le terrain n'en a que 22.
    Aux bouts, elle rétrécit des deux côtés à la fois : la route rejoint le terrain à ses
    extrémités.
    """
    s = longueurs(axe)
    h0 = hauteur(h, axe[:, 0], axe[:, 1])
    n = len(h0); i = np.arange(n)
    k = np.minimum(demi_fenetre(P), np.minimum(i, n - 1 - i))
    c = np.concatenate([[0.0], np.cumsum(h0)])
    return s, h0, (c[i + k + 1] - c[i - k]) / (2 * k + 1)


def pente(p, s):
    ds = np.diff(s)
    g = np.abs(np.diff(p)) / np.maximum(ds, 1e-9)
    k = int(np.argmax(g))
    return float(g[k]), float((s[k] + s[k + 1]) / 2)


def fenetre(axe, rayon, n, pas, decalage):
    """Indices (i0, i1, j0, j1) des points de grille à moins de `rayon` de l'axe, bornés à la grille."""
    moitie = terrain.TAILLE / 2
    i0 = max(0, math.floor((moitie - (axe[:, 0].max() + rayon)) / pas - decalage) - 1)
    i1 = min(n - 1, math.ceil((moitie - (axe[:, 0].min() - rayon)) / pas - decalage) + 1)
    j0 = max(0, math.floor((moitie - (axe[:, 1].max() + rayon)) / pas - decalage) - 1)
    j1 = min(n - 1, math.ceil((moitie - (axe[:, 1].min() - rayon)) / pas - decalage) + 1)
    return i0, i1, j0, j1


def plus_proche(axe, valeurs, rayon, n, pas, decalage=0.0):
    """Pour chaque point de grille de la fenêtre : distance à l'axe, et valeurs interpolées au projeté.

    Même calcul, dans le même ordre, que DesertRoads.PlusProche : les segments sont parcourus
    dans l'ordre et seul un écart strictement plus petit remplace le précédent.
    """
    moitie = terrain.TAILLE / 2
    i0, i1, j0, j1 = fenetre(axe, rayon, n, pas, decalage)
    X = moitie - (np.arange(i0, i1 + 1) + decalage) * pas
    Y = moitie - (np.arange(j0, j1 + 1) + decalage) * pas
    D = np.full((len(Y), len(X)), np.inf); V = [np.zeros(D.shape) for _ in valeurs]
    for k in range(len(axe) - 1):
        ax, ay = axe[k]; bx, by = axe[k + 1]; sx = bx - ax; sy = by - ay; l2 = sx * sx + sy * sy
        a = max(0, math.floor((moitie - (max(ax, bx) + rayon)) / pas - decalage) - 1 - i0)
        b = min(len(X) - 1, math.ceil((moitie - (min(ax, bx) - rayon)) / pas - decalage) + 1 - i0)
        c = max(0, math.floor((moitie - (max(ay, by) + rayon)) / pas - decalage) - 1 - j0)
        e = min(len(Y) - 1, math.ceil((moitie - (min(ay, by) - rayon)) / pas - decalage) + 1 - j0)
        if a > b or c > e:
            continue
        dx = X[None, a:b + 1] - ax; dy = Y[c:e + 1, None] - ay
        t = np.clip((dx * sx + dy * sy) / l2, 0, 1) if l2 > 0 else np.zeros(np.broadcast(dx, dy).shape)
        ex = dx - t * sx; ey = dy - t * sy
        d = np.sqrt(ex * ex + ey * ey)
        zone = D[c:e + 1, a:b + 1]; mieux = d < zone
        zone[mieux] = d[mieux]
        for v, w in zip(V, valeurs):
            vz = v[c:e + 1, a:b + 1]; vz[mieux] = (w[k] + t * (w[k + 1] - w[k]))[mieux]
    return (i0, j0), D, V


def tailler(h, axe, largeur, P, pente_max=None, forcer=False):
    """Rejoue une route sur la grille h (en mètres). Renvoie la décision ; h est modifiée si acceptée.

    Décision : 'acceptee', 'pente' ou 'talus', avec la valeur mesurée, sa position le long de
    l'axe et deux marges signées (positives du côté accepté) : à la pente maximale, et au
    talus qui se referme. Elles disent quand une décision ne tient qu'à la quantification.
    `forcer` pose la route sans refus : la référence suit alors une décision d'Unity ambiguë.
    """
    pente_max = P['pente_max'] if pente_max is None else pente_max
    s, h0, p = profil(h, axe, P)
    g, ou = pente(p, s)
    r = {'profil': p, 's': s, 'marge_pente': pente_max - g, 'marge_talus': None}
    if g > pente_max and not forcer:
        return dict(r, decision='pente', valeur=g, position=ou)
    demi = largeur / 2; R = demi + P['talus_max']; pas = terrain.pas()
    if np.abs(axe).max() > terrain.TAILLE / 2 - R - pas:
        return dict(r, decision='hors_terrain', valeur=-1, position=-1, marge_pente=np.inf, marge_talus=np.inf)
    (i0, j0), D, (Pp, S) = plus_proche(axe, [p, s], R, terrain.RESOLUTION, pas)
    zone = h[j0:j0 + D.shape[0], i0:i0 + D.shape[1]]
    lim = (D - demi) * P['talus']
    exces = np.abs(zone - Pp) - lim
    chaussee = D <= demi
    talus = connexe(chaussee, (D > demi) & (D <= R) & (exces > 0))
    bande = (D > R - pas) & (D <= R)
    atteint = talus & bande
    if atteint.any():
        k = np.unravel_index(int(np.argmax(np.where(atteint, exces, -np.inf))), exces.shape)
        r['marge_talus'] = -float(exces[k])
        if not forcer:
            return dict(r, decision='talus', valeur=float(exces[k]), position=float(S[k]))
    else:
        # Le sommet du bord le plus près de rejoindre le talus dit la marge de la décision.
        voisin = bande & dilate(talus | chaussee, 8)
        r['marge_talus'] = float(np.abs(exces[voisin]).min()) if voisin.any() else np.inf
    nouveau = np.where(chaussee, Pp, np.minimum(np.maximum(zone, Pp - lim), Pp + lim))
    dedans = chaussee | talus
    change = dedans & (nouveau != zone)
    zone[dedans] = nouveau[dedans]
    return dict(r, decision='acceptee', valeur=g, position=ou, change=(i0, j0, change))


def dilate(m, voisins=4):
    d = m.copy()
    d[1:] |= m[:-1]; d[:-1] |= m[1:]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
    if voisins == 8:
        d[1:, 1:] |= m[:-1, :-1]; d[:-1, :-1] |= m[1:, 1:]; d[1:, :-1] |= m[:-1, 1:]; d[:-1, 1:] |= m[1:, :-1]
    return d


def connexe(depart, masque):
    """Sommets du masque reliés au départ de proche en proche (quatre voisins).

    Le talus est ce qui touche la chaussée : une butte voisine que la route ne touche pas
    n'est ni rabotée, ni une raison de refuser la route.
    """
    pris = dilate(depart) & masque
    while True:
        suite = dilate(pris) & masque
        if (suite == pris).all():
            return pris
        pris = suite


def marge(r):
    """Distance de la décision à son seuil, positive quand elle est nette."""
    if r['decision'] == 'pente':
        return -r['marge_pente']
    if r['decision'] == 'talus':
        return -r['marge_talus']
    return min(r['marge_pente'], r['marge_talus'])


# ---------- Le jeu de gestes ----------

def arrondi(v, P):
    k = round(1 / P['arrondi'])
    return [round(float(a) * k) / k for a in v]


def axe_polyligne(points, P):
    """Axe approché d'un geste (polyligne rééchantillonnée) : sert seulement à tirer les gestes.

    Le vrai axe est la spline d'Unity ; le jugement la rejoue telle qu'Unity l'a exportée.
    """
    pts = np.asarray(points, dtype=float)
    s = longueurs(pts); n = max(1, round(s[-1] / P['pas']))
    t = np.linspace(0, s[-1], n + 1)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], axis=1)


def travers(h, axe):
    """Pente en travers en chaque échantillon : gradient projeté sur la normale à l'axe."""
    d = np.gradient(axe, axis=0); d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
    gx, gy = gradient(h, axe[:, 0], axe[:, 1])
    return np.abs(-d[:, 1] * gx + d[:, 0] * gy)


def suivre(h, x, y, longueur, mode, pas=1.0):
    """Trace un chemin depuis (x, y) : le long d'une courbe de niveau, ou dans la plus grande pente."""
    pts = [(x, y)]; z0 = float(hauteur(h, x, y)); avant = None
    limite = terrain.TAILLE / 2 - 30
    for _ in range(int(longueur / pas)):
        gx, gy = (float(v) for v in gradient(h, x, y)); g = math.hypot(gx, gy)
        if g < 1e-4:
            return None
        tx, ty = (-gy / g, gx / g) if mode == 'niveau' else (gx / g, gy / g)
        if avant and tx * avant[0] + ty * avant[1] < 0:
            tx, ty = -tx, -ty
        x += tx * pas; y += ty * pas
        if mode == 'niveau':
            for _ in range(3):
                gx, gy = (float(v) for v in gradient(h, x, y)); g2 = gx * gx + gy * gy
                if g2 < 1e-8:
                    return None
                dz = float(hauteur(h, x, y)) - z0; x -= dz * gx / g2; y -= dz * gy / g2
        if abs(x) > limite or abs(y) > limite:
            return None
        avant = (tx, ty); pts.append((x, y))
    return pts


def noeuds(chemin, ecart=10.0):
    """Points posés par le joueur : un tous les `ecart` mètres le long du chemin, et le dernier."""
    pts = np.asarray(chemin, dtype=float); s = longueurs(pts)
    garde = [0]
    for k in range(1, len(pts)):
        if s[k] - s[garde[-1]] >= ecart:
            garde.append(k)
    if garde[-1] != len(pts) - 1:
        if s[-1] - s[garde[-1]] < ecart / 2 and len(garde) > 1:
            garde[-1] = len(pts) - 1
        else:
            garde.append(len(pts) - 1)
    return pts[garde]


def geste(ident, famille, points, largeur, revetement, P, mesures):
    x = arrondi(points[:, 0], P); y = arrondi(points[:, 1], P)
    return {'id': ident, 'famille': famille, 'revetement': revetement, 'largeur': largeur, 'x': x, 'y': y, 'mesures': mesures}


def essai(h, points, largeur, P, pente_max=None):
    """Décision de la référence pour un geste, sur une copie de la grille."""
    return tailler(h.copy(), axe_polyligne(np.column_stack(points) if isinstance(points, tuple) else points, P), largeur, P, pente_max)


def anciennes(h, seed, P):
    sortie = []
    for route in paysage.plan(seed)['routes']:
        if not route['ground'] or route['id'].startswith(('seuil_', 'ruelle_', 'liaison_')):
            continue
        pts = noeuds([p[:2] for p in route['points']])
        largeur = max(3.0, float(route['width']))
        revetement = 'paves' if largeur >= 4 else 'terre'
        r = essai(h, pts, largeur, P)
        sortie.append(geste('ancienne_' + route['id'], 'ancienne', pts, largeur, revetement, P,
                            {'decision_prevue': r['decision'], 'pente_profil': r['valeur'] if r['decision'] != 'talus' else -1}))
    return sortie


def candidats(seed, rayon_min, rayon_max, graine):
    """Points de départ sur un treillis de 8 m, dans un anneau, en ordre tiré par la graine."""
    axe = np.arange(-terrain.TAILLE / 2 + 40, terrain.TAILLE / 2 - 40, 8.0)
    xx, yy = np.meshgrid(axe, axe); r = np.hypot(xx, yy)
    garde = (r >= rayon_min) & (r <= rayon_max)
    pts = np.column_stack([xx[garde], yy[garde]])
    rng = np.random.default_rng(seed + graine)
    return pts[rng.permutation(len(pts))]


def plaine(h, seed, P):
    """Une route neuve sur la plaine : loin de toute ancienne rue, hors des dunes, acceptée avec marge."""
    for x, y in candidats(seed, 40, 150, 263):
        if paysage.distance_to_routes(x, y, seed) <= 40:
            continue
        for angle in range(0, 360, 30):
            a = math.radians(angle); pts = [(x, y)]
            for k in range(10):
                a += math.radians(3)
                pts.append((pts[-1][0] + 10 * math.cos(a), pts[-1][1] + 10 * math.sin(a)))
            pts = np.asarray(pts); axe = axe_polyligne(pts, P)
            loin = min(paysage.distance_to_routes(px, py, seed) for px, py in axe[::4])
            if loin <= 20 or np.hypot(axe[:, 0], axe[:, 1]).max() > 170:
                continue
            r = tailler(h.copy(), axe, LARGEUR_NEUVE, P)
            if r['decision'] == 'acceptee' and marge(r) > .02:
                return geste('plaine_neuve', 'plaine', pts, LARGEUR_NEUVE, 'paves', P,
                             {'distance_min_aux_rues': float(loin), 'pente_profil': r['valeur']})
    raise RuntimeError('aucune route de plaine neuve ne se trace loin des anciennes rues')


def flanc(h, seed, P):
    """Une route à flanc de dune : de niveau en long, pente en travers de 20 à 40 % sur un tiers au moins."""
    for x, y in candidats(seed, 190, 400, 264):
        gx, gy = gradient(h, x, y)
        if not .25 <= math.hypot(gx, gy) <= .35:
            continue
        chemin = suivre(h, x, y, 60, 'niveau')
        if not chemin:
            continue
        pts = noeuds(chemin); axe = axe_polyligne(pts, P)
        cote = travers(h, axe); part = float(np.mean((cote >= .2) & (cote <= .4)))
        if part < 1 / 3:
            continue
        r = tailler(h.copy(), axe, LARGEUR_NEUVE, P)
        if r['decision'] == 'acceptee' and marge(r) > .02 and r['valeur'] < P['pente_max'] - .03:
            return geste('flanc_de_dune', 'flanc', pts, LARGEUR_NEUVE, 'terre', P,
                         {'part_travers_20_40': part, 'pente_profil': r['valeur']})
    raise RuntimeError('aucune route à flanc de dune ne tient la pente en travers de 20 à 40 %')


def plus_raide(h, axe, longueur):
    """Plus forte pente moyenne, sur la grille, le long de `longueur` mètres d'axe."""
    s = longueurs(axe); z = hauteur(h, axe[:, 0], axe[:, 1]); best = 0.0
    for k in range(len(s)):
        m = int(np.searchsorted(s, s[k] + longueur))
        if m >= len(s):
            break
        best = max(best, abs(z[m] - z[k]) / (s[m] - s[k]))
    return best


def raide_long(h, seed, P):
    """Une montée droite : plus de 30 % sur 10 m. Refusée pour la pente, acceptée si la pente
    maximale passait à 40 % (c'est la contre-épreuve de SC4)."""
    for x, y in candidats(seed, 30, 420, 265):
        gx, gy = gradient(h, x, y)
        if not .32 <= math.hypot(gx, gy) <= .45:
            continue
        chemin = suivre(h, x, y, 30, 'pente')
        if not chemin:
            continue
        pts = noeuds(chemin); axe = axe_polyligne(pts, P)
        raide = plus_raide(h, axe, 10)
        if raide <= .30:
            continue
        r = tailler(h.copy(), axe, LARGEUR_NEUVE, P)
        r40 = tailler(h.copy(), axe, LARGEUR_NEUVE, P, pente_max=.40)
        if r['decision'] == 'pente' and marge(r) > .02 and r40['decision'] == 'acceptee' and marge(r40) > .02:
            return geste('trop_raide_en_long', 'raide_long', pts, LARGEUR_NEUVE, 'terre', P,
                         {'pente_10m': raide, 'pente_profil': r['valeur']})
    raise RuntimeError('aucune montée à plus de 30 % sur 10 m ne se trace')


def raide_travers(h, seed, P):
    """Une route de niveau sur une face d'avalanche : plus de 60 % en travers sur 10 m, talus impossible."""
    for x, y in candidats(seed, 190, 420, 266):
        gx, gy = gradient(h, x, y)
        if math.hypot(gx, gy) < .75:
            continue
        chemin = suivre(h, x, y, 40, 'niveau')
        if not chemin:
            continue
        pts = noeuds(chemin); axe = axe_polyligne(pts, P)
        cote = travers(h, axe) > .6
        # 10 m d'affilée au-dessus de 60 %
        suite = 0; plus_longue = 0
        for v in cote:
            suite = suite + 1 if v else 0; plus_longue = max(plus_longue, suite)
        if plus_longue * P['pas'] < 10:
            continue
        r = tailler(h.copy(), axe, LARGEUR_NEUVE, P)
        s, _, p = profil(h, axe, P)
        if r['decision'] == 'talus' and marge(r) > .05 and pente(p, s)[0] < P['pente_max'] - .03:
            return geste('trop_raide_en_travers', 'raide_travers', pts, LARGEUR_NEUVE, 'terre', P,
                         {'travers_60_m': plus_longue * P['pas'], 'pente_profil': pente(p, s)[0]})
    raise RuntimeError('aucune face à plus de 60 % en travers ne porte une route de niveau')


def ecrire_gestes(ident, seed):
    h = grille(ident); P = dict(PARAMETRES)
    routes = anciennes(h, seed, P) + [plaine(h, seed, P), flanc(h, seed, P), raide_long(h, seed, P), raide_travers(h, seed, P)]
    donnees = {'implantation': ident, 'graine': seed, 'parametres': P, 'routes': routes}
    fautes = juger_gestes(donnees)
    if fautes:
        raise RuntimeError(ident + ' : ' + ' ; '.join(fautes))
    dossier(ident).mkdir(parents=True, exist_ok=True)
    (dossier(ident) / 'gestes.json').write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding='utf-8')
    return donnees


def juger_gestes(donnees):
    fautes = []
    routes = donnees.get('routes') or []
    if not routes:
        return ['jeu de gestes vide']
    for f in FAMILLES:
        if not any(r['famille'] == f for r in routes):
            fautes.append('famille absente du jeu de gestes : ' + f)
    for r in routes:
        if len(r['x']) < 2 or len(r['x']) != len(r['y']):
            fautes.append('geste sans deux points : ' + r['id'])
    return fautes


# ---------- Le jugement ----------

def lire_rapport(ident):
    chemin = dossier(ident) / 'unity-routes.json'
    if not chemin.exists():
        raise RuntimeError(ident + ' : Unity n’a pas écrit ' + str(chemin))
    return json.loads(chemin.read_text(encoding='utf-8-sig'))


def lire_grilles(ident, u):
    base = terrain.SORTIES / ident
    n = u['resolution']; m = u['couches_resolution']; k = len(u['couches']); dn = u['details_resolution']
    lire = lambda nom, t, c: np.fromfile(base / nom, dtype=t).reshape(c)
    return {
        'avant': lire('routes_avant.f32', '<f4', (n, n)).astype(float),
        'apres': lire('routes_apres.f32', '<f4', (n, n)).astype(float),
        'couches': lire('routes_couches.u8', np.uint8, (m, m, k)).astype(int),
        'touffes': {t: lire('routes_details_' + t + '.u8', np.uint8, (dn, dn)).astype(int) for t in u['touffes']},
        'couches_origine': lire('couches.u8', np.uint8, (m, m, 4)).astype(int),
        'touffes_origine': {t: lire('details_' + t + '.u8', np.uint8, (dn, dn)).astype(int) for t in u['touffes']},
    }


def axe_de(r):
    return np.column_stack([np.asarray(r['ax'], dtype=float), np.asarray(r['ay'], dtype=float)])


def rejouer(h0, gestes, u, P):
    """La référence : chaque route, dans l'ordre, sur l'axe qu'Unity a échantillonné."""
    h = h0.copy(); n = h.shape[0]
    dernier = np.full(h.shape, -1, dtype=int)
    tol_pente = 2 * u['quantification'] / P['pas']; tol_talus = 2 * u['quantification'] + 1e-3
    sortie = []
    for k, (g, r) in enumerate(zip(gestes, u['routes'])):
        axe = axe_de(r)
        essai_h = h.copy()
        prevu = tailler(essai_h, axe, g['largeur'], P)
        ambigu = abs(prevu['marge_pente']) <= tol_pente or (prevu['marge_talus'] is not None and abs(prevu['marge_talus']) <= tol_talus)
        obtenu = 'acceptee' if r['acceptee'] else r['motif']
        if ambigu and obtenu != prevu['decision']:
            # Décision à la quantification près : la référence suit Unity.
            essai_h = h.copy()
            prevu = tailler(essai_h, axe, g['largeur'], P, forcer=True) if r['acceptee'] else dict(prevu, decision=obtenu)
        if prevu['decision'] == 'acceptee':
            h[:] = essai_h
        if 'change' in prevu:
            i0, j0, change = prevu['change']
            dernier[j0:j0 + change.shape[0], i0:i0 + change.shape[1]][change] = k
        sortie.append({'prevu': prevu['decision'], 'ambigu': bool(ambigu), 'profil': prevu['profil'], 's': prevu['s']})
    return h, dernier, sortie


def cellule(n, x, y, pas, decalage=0.0):
    moitie = terrain.TAILLE / 2
    u = (moitie - np.asarray(x)) / pas - decalage; v = (moitie - np.asarray(y)) / pas - decalage
    return np.clip(np.floor(u).astype(int), 0, n - 2), np.clip(np.floor(v).astype(int), 0, n - 2)


def juger_axe(r, prevu, dernier, k, u, P):
    """SC2 : le terrain sous l'axe (rendu et collision) suit le profil de référence ; pente ≤ 12 %."""
    fautes = []
    rendu = np.asarray(r['rendu'], dtype=float); coll = np.asarray(r['collision'], dtype=float)
    axe = axe_de(r); p = prevu['profil']; s = prevu['s']
    if len(rendu) != len(p) or len(coll) != len(p):
        return ['{} : {} hauteurs mesurées pour {} échantillons'.format(r['id'], len(rendu), len(p))], {}
    # Un échantillon qu'une route posée plus tard a retaillé ne juge plus celle-ci.
    garde = np.ones(len(p), bool)
    if dernier is not None:
        i, j = cellule(dernier.shape[0], axe[:, 0], axe[:, 1], terrain.pas())
        garde = (dernier[j, i] == k) & (dernier[j, i + 1] == k) & (dernier[j + 1, i] == k) & (dernier[j + 1, i + 1] == k)
    if not garde.any():
        return [r['id'] + ' : aucun échantillon de l’axe à juger'], {}
    e_rendu = np.abs(rendu - p)[garde]; e_coll = np.abs(coll - p)[garde]
    if np.isnan(e_coll).any():
        fautes.append(r['id'] + ' : collision absente sous {} échantillons'.format(int(np.isnan(e_coll).sum())))
    e = np.nan_to_num(np.maximum(e_rendu, e_coll), nan=np.inf)
    if e.max() > TOLERANCE_PROFIL:
        fautes.append('{} : terrain à {:.3f} m du profil de référence (tolérance {} m)'.format(r['id'], e.max(), TOLERANCE_PROFIL))
    suite = garde[:-1] & garde[1:]
    g = np.abs(np.diff(rendu)) / np.diff(s)
    tol = P['pente_max'] + 2 * u['quantification'] / P['pas']
    if suite.any() and g[suite].max() > tol:
        fautes.append('{} : pente de {:.1%} mesurée sur le terrain'.format(r['id'], g[suite].max()))
    return fautes, {'echantillons': int(len(p)), 'juges': int(garde.sum()),
                    'mediane': float(np.median(e_rendu)), 'p95': float(np.percentile(e_rendu, 95)), 'max': float(e.max()),
                    'pente_max': float(g[suite].max()) if suite.any() else -1}


def juger_grille(gr, h_ref, dernier, gestes, u, P):
    """SC3 : talus ≤ 1:2 sur des coupes en travers ; hors de l'emprise, rien n'a bougé ; la
    grille d'Unity vaut la référence rejouée sur toute l'emprise."""
    fautes = []; n = u['resolution']; pas = terrain.pas()
    emprise = np.zeros((n, n), bool)
    coupes = 0; pire = 0.0; tol = P['talus'] + 2 * u['quantification'] / pas
    for k, (g, r) in enumerate(zip(gestes, u['routes'])):
        if not r['acceptee']:
            continue
        axe = axe_de(r); demi = g['largeur'] / 2; R = demi + P['talus_max']
        (i0, j0), D, _ = plus_proche(axe, [], R, n, pas)
        emprise[j0:j0 + D.shape[0], i0:i0 + D.shape[1]] |= D <= R
        d = np.gradient(axe, axis=0); d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
        for q in range(0, len(axe), int(round(5 / P['pas']))):
            nx, ny = -d[q, 1], d[q, 0]
            for signe in (-1, 1):
                off = np.arange(demi + pas, R + 1e-9, pas)
                x = axe[q, 0] + signe * off * nx; y = axe[q, 1] + signe * off * ny
                i, j = cellule(n, x, y, pas)
                # Là où la surface est entièrement le talus de cette route : les quatre sommets du carreau.
                tout = (dernier[j, i] == k) & (dernier[j, i + 1] == k) & (dernier[j + 1, i] == k) & (dernier[j + 1, i + 1] == k)
                z = terrain.interpolee(gr['apres'], x, y)
                ok = tout[:-1] & tout[1:]
                if ok.any():
                    coupes += int(ok.sum())
                    pire = max(pire, float((np.abs(np.diff(z)) / pas)[ok].max()))
    if coupes == 0:
        fautes.append('aucune coupe de talus à mesurer')
    elif pire > tol:
        fautes.append('talus à {:.1%} (1:2 au plus)'.format(pire))
    change = gr['apres'] != gr['avant']
    dehors = int((change & ~emprise).sum())
    if dehors:
        fautes.append('{} sommets modifiés hors de l’emprise des routes'.format(dehors))
    ecart = float(np.abs(gr['apres'] - h_ref)[emprise].max()) if emprise.any() else -1
    if ecart < 0 or ecart > TOLERANCE_PROFIL:
        fautes.append('grille d’Unity à {:.3f} m de la référence rejouée sur l’emprise'.format(ecart))
    return fautes, {'coupes': coupes, 'talus_max': pire, 'sommets_hors_emprise': dehors, 'ecart_reference_max': ecart,
                    'sommets_emprise': int(emprise.sum())}


def juger_sol(gr, gestes, u, P):
    """SC5 : sous l'axe, la couche du revêtement domine ; hors de l'emprise peinte, les poids
    sont ceux d'origine ; aucune touffe sur l'emprise peinte ; les couches gardent leur ordre."""
    fautes = []; m = u['couches_resolution']; dn = u['details_resolution']
    if u['couches'] != COUCHES_ROUTES:
        fautes.append('couches du terrain : ' + ', '.join(u['couches']))
    peint = np.zeros((m, m), bool); sans_touffe = np.zeros((dn, dn), bool)
    acceptees = [(k, g, r) for k, (g, r) in enumerate(zip(gestes, u['routes'])) if r['acceptee']]
    zones = []
    for k, g, r in acceptees:
        axe = axe_de(r); bord = g['largeur'] / 2 + P['bruit_bord'] + P['fondu_bord'] / 2
        (i0, j0), D, _ = plus_proche(axe, [], bord, m, terrain.TAILLE / m, .5)
        peint[j0:j0 + D.shape[0], i0:i0 + D.shape[1]] |= D <= bord
        (a0, b0), E, _ = plus_proche(axe, [], bord, dn, terrain.TAILLE / dn, .5)
        sans_touffe[b0:b0 + E.shape[0], a0:a0 + E.shape[1]] |= E <= bord
        zones.append((k, g, r, axe, bord))
    c = gr['couches']; o = gr['couches_origine']
    ecart = np.abs(c[..., :4] - o)[~peint].max() if (~peint).any() else 0
    neuves = c[..., 4:][~peint].max() if (~peint).any() else 0
    if ecart > 1 or neuves > 1:
        fautes.append('poids des couches changés hors des routes ({}/255, couches neuves {}/255)'.format(ecart, neuves))
    domine = 0; juges = 0
    for idx, (k, g, r, axe, bord) in enumerate(zones):
        couche = COUCHES_ROUTES.index('Ville_terre_battue' if g['revetement'] == 'terre' else 'Ville_paves')
        i, j = cellule(m + 1, axe[:, 0], axe[:, 1], terrain.TAILLE / m, 0)
        i = np.clip(i, 0, m - 1); j = np.clip(j, 0, m - 1)
        libre = np.ones(len(axe), bool)
        for k2, g2, r2, axe2, bord2 in zones[idx + 1:]:
            # Un pixel qu'une route posée plus tard a repeint ne juge plus celle-ci.
            (i0, j0), D, _ = plus_proche(axe2, [], bord2, m, terrain.TAILLE / m, .5)
            ii = i - i0; jj = j - j0; dans = (ii >= 0) & (jj >= 0) & (ii < D.shape[1]) & (jj < D.shape[0])
            libre[dans] &= ~(D[jj[dans], ii[dans]] <= bord2)
        w = c[j, i]
        ok = np.all(np.delete(w, couche, axis=1) < w[:, couche:couche + 1], axis=1)
        juges += int(libre.sum()); domine += int((ok & libre).sum())
    if juges == 0:
        fautes.append('aucun pixel sous un axe à juger')
    elif domine < juges:
        fautes.append('{} pixels sous l’axe où le revêtement ne domine pas'.format(juges - domine))
    sur_route = sum(int(t[sans_touffe].sum()) for t in gr['touffes'].values())
    if sur_route:
        fautes.append('{} touffes sur l’emprise d’une route'.format(sur_route))
    touchees = sum(int((gr['touffes'][t] != gr['touffes_origine'][t])[~sans_touffe].sum()) for t in u['touffes'])
    if touchees:
        fautes.append('{} cellules de touffes changées hors des routes'.format(touchees))
    return fautes, {'pixels_axe': juges, 'pixels_domines': domine, 'touffes_sur_route': sur_route}


def juger_marche(r, nom):
    m = r.get('marche') or {}
    if not m.get('faite'):
        return [nom + ' : marcheur non lancé']
    fautes = []
    if m['distance_fin'] < 0 or m['distance_fin'] > 1:
        fautes.append('{} : marcheur arrêté à {:.2f} m du bout'.format(nom, m['distance_fin']))
    if m['pas_max'] > m['pas_permis'] * 1.001:
        fautes.append('{} : un pas de {:.3f} m pour {:.3f} m permis'.format(nom, m['pas_max'], m['pas_permis']))
    return fautes


def juger_refus(gestes, u):
    """SC4 : les deux familles trop raides sont refusées pour leur motif, sans rien changer."""
    fautes = []
    for g, r in zip(gestes, u['routes']):
        if g['famille'] not in ('raide_long', 'raide_travers'):
            continue
        if r['acceptee']:
            fautes.append(r['id'] + ' : posée alors qu’elle est trop raide')
            continue
        if r['motif'] != ATTENDU[g['famille']]:
            fautes.append('{} : refusée pour « {} » au lieu de « {} »'.format(r['id'], r['motif'], ATTENDU[g['famille']]))
        if not r.get('message') or r.get('valeur', -1) < 0 or r.get('position', -1) < 0:
            fautes.append(r['id'] + ' : le refus ne dit ni la valeur ni l’endroit')
        if not r.get('avant') or r.get('avant') != r.get('apres'):
            fautes.append(r['id'] + ' : le terrain a changé pendant le refus')
    return fautes


def distance_axe(axe, x, y):
    """Distance d'un point à la polyligne de l'axe."""
    a = axe[:-1]; b = axe[1:]; s = b - a; l2 = np.maximum((s * s).sum(1), 1e-12)
    t = np.clip(((x - a[:, 0]) * s[:, 0] + (y - a[:, 1]) * s[:, 1]) / l2, 0, 1)
    return float(np.min(np.hypot(x - a[:, 0] - t * s[:, 0], y - a[:, 1] - t * s[:, 1])))


def juger(ident):
    """Le jugement d'une implantation : les défauts, puis les contre-épreuves du jugement lui-même."""
    donnees = json.loads((dossier(ident) / 'gestes.json').read_text(encoding='utf-8'))
    P = donnees['parametres']; gestes = donnees['routes']
    u = lire_rapport(ident); gr = lire_grilles(ident, u)
    fautes = list(juger_gestes(donnees)) + ['Unity : ' + d for d in u.get('defauts', [])]
    rapport = {'implantation': ident, 'graine': donnees['graine'], 'routes': []}
    if [r['id'] for r in u['routes']] != [g['id'] for g in gestes]:
        fautes.append('le rapport Unity ne suit pas le jeu de gestes')
        return fin(ident, rapport, fautes)
    h0 = grille(ident)
    if np.abs(gr['avant'] - h0).max() > u['quantification']:
        fautes.append('la copie de départ n’est pas la grille d’origine')
    h_ref, dernier, prevus = rejouer(h0, gestes, u, P)
    for k, (g, r, pr) in enumerate(zip(gestes, u['routes'], prevus)):
        ligne = {'id': g['id'], 'famille': g['famille'], 'decision': 'acceptee' if r['acceptee'] else r['motif'],
                 'reference': pr['prevu'], 'ambigu': pr['ambigu']}
        axe = axe_de(r)
        # L'axe passe par les points du joueur.
        pts = np.column_stack([g['x'], g['y']])
        d = [distance_axe(axe, x, y) for x, y in pts]
        ligne['ecart_points'] = max(d)
        if max(d) > ECART_POINTS:
            fautes.append('{} : l’axe passe à {:.2f} m d’un point du joueur'.format(g['id'], max(d)))
        if ligne['decision'] != pr['prevu']:
            fautes.append('{} : Unity dit « {} », la référence « {} »'.format(g['id'], ligne['decision'], pr['prevu']))
        if g['famille'] in ('plaine', 'flanc') and not r['acceptee']:
            fautes.append(g['id'] + ' : refusée alors que sa famille doit passer')
        if r['acceptee']:
            f, stats = juger_axe(r, pr, dernier, k, u, P); fautes += f; ligne['axe'] = stats
            fm = juger_marche(r, g['id']); fautes += fm
            ligne['marche'] = r.get('marche')
        rapport['routes'].append(ligne)
    fautes += juger_refus(gestes, u)
    f, rapport['grille'] = juger_grille(gr, h_ref, dernier, gestes, u, P); fautes += f
    f, rapport['sol'] = juger_sol(gr, gestes, u, P); fautes += f

    # SC7 : déterminisme et asset intact.
    e = u['empreintes']
    if not e['a']['hauteurs'] or e['a'] != e['b']:
        fautes.append('mêmes gestes, même graine : empreintes différentes')
    if e['autre_graine']['couches'] == e['a']['couches']:
        fautes.append('une autre graine donne les mêmes couches : le bruit de bord ne dépend pas de la graine')
    if not u['asset_avant'] or u['asset_avant'] != u['asset_apres']:
        fautes.append('l’asset du terrain a changé')

    # SC8 : le clic passe par la même entrée.
    c = u['clic']
    if not c['voulus_x'] or len(c['voulus_x']) != len(c['obtenus_x']):
        fautes.append('clic : points manquants')
    else:
        e_clic = np.hypot(np.subtract(c['voulus_x'], c['obtenus_x']), np.subtract(c['voulus_y'], c['obtenus_y'])).max()
        if e_clic > .5:
            fautes.append('clic : point obtenu à {:.2f} m du point voulu'.format(e_clic))
        rapport['clic_ecart_max'] = float(e_clic)
    if not c['empreinte_clic'] or c['empreinte_clic'] != c['empreinte_gestes']:
        fautes.append('clic : le terrain diffère de la même route posée par le jeu de gestes')

    # SC9 : captures non uniformes, quatre au plus.
    caps = u.get('captures', [])
    if not caps or len(caps) > 4:
        fautes.append('{} captures (une à quatre attendues)'.format(len(caps)))
    for cap in caps:
        if cap['ecart'] < ECART_CAPTURE:
            fautes.append('capture uniforme : ' + cap['nom'])

    # Contre-épreuves du jugement : chacune doit le faire échouer.
    ce = {}
    ce['gestes_vides'] = bool(juger_gestes({'routes': []}))
    ce['famille_retiree'] = bool(juger_gestes({'routes': [g for g in gestes if g['famille'] != 'flanc']}))
    rel = u['profil_releve']; g_rel = next(g for g in gestes if g['id'] == rel['id'])
    s, _, p = profil(h0, axe_de(rel), P)
    ce['profil_releve'] = bool(juger_axe(rel, {'profil': p, 's': s}, None, 0, u, P)[0]) if rel.get('acceptee') else False
    faux = dict(gr); faux['apres'] = gr['apres'].copy()
    loin = np.argwhere(~(gr['apres'] != gr['avant']))
    j, i = loin[len(loin) // 2]
    faux['apres'][j, i] += .1
    ce['sommet_hors_emprise'] = bool(juger_grille(faux, h_ref, dernier, gestes, u, P)[0])
    ce['pente_40'] = bool(juger_refus(gestes, {'routes': [dict(r, acceptee=True) if r['id'] == u['pente_40']['id'] and u['pente_40']['acceptee'] else r for r in u['routes']]}))
    faux = dict(gr); faux['couches'] = gr['couches'][..., [0, 1, 2, 3, 5, 4]]
    ce['couches_echangees'] = bool(juger_sol(faux, gestes, u, P)[0])
    if u['touffes']:
        faux = dict(gr); faux['touffes'] = {t: v.copy() for t, v in gr['touffes'].items()}
        premiere = next(r for r in u['routes'] if r['acceptee'])
        a, b = cellule(u['details_resolution'] + 1, premiere['ax'][len(premiere['ax']) // 2], premiere['ay'][len(premiere['ay']) // 2], terrain.TAILLE / u['details_resolution'])
        faux['touffes'][u['touffes'][0]][b, a] += 1
        ce['touffe_sur_route'] = bool(juger_sol(faux, gestes, u, P)[0])
    else:
        rapport['touffes'] = 'pack Terrain Sample absent : aucune touffe, contre-épreuve sans objet'
    ce['mur'] = bool(juger_marche(u['mur'], 'mur'))
    for nom, rougit in ce.items():
        if not rougit:
            fautes.append('contre-épreuve sans effet : ' + nom)
    rapport['contre_epreuves'] = ce
    rapport['captures'] = caps
    return fin(ident, rapport, fautes)


def fin(ident, rapport, fautes):
    rapport['defauts'] = fautes; rapport['status'] = 'valide' if not fautes else 'echec'
    (dossier(ident) / 'jugement.json').write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding='utf-8')
    return rapport
