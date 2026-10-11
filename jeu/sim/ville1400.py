"""Ville de 1400 dérivée des foyers du bourg, sans effet sur le tick.

Vue pure : une place, une rue principale vers chaque voisine par terre,
des ruelles, des maisons individuelles ou des îlots. Le monde ne la stocke pas.
"""

import math
from types import SimpleNamespace

import sim.constants as _constantes
from sim.foyers import ranger_en_foyers


class BaseAbsente(LookupError):
    """L'amorçage ou un centroïde manque : la base ne se devine pas."""


class _Forme:
    """Polygone convexe préparé pour les axes séparateurs."""

    __slots__ = ("points", "axes", "min_x", "max_x", "min_y", "max_y", "marque")

    def __init__(self, points):
        self.points = points
        self.axes = tuple(_axes(points))
        self.marque = 0
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        self.min_x = min(xs)
        self.max_x = max(xs)
        self.min_y = min(ys)
        self.max_y = max(ys)


class _Voie:
    """Segment publié et repère local pour y poser des maisons."""

    __slots__ = (
        "points", "largeur", "sorte", "vers",
        "ox", "oy", "ux", "uy", "vx", "vy", "longueur", "index",
    )

    def __init__(self, points, largeur, sorte, vers, origine, direction, perpendiculaire, longueur, index):
        self.points = points
        self.largeur = largeur
        self.sorte = sorte
        self.vers = vers
        self.ox, self.oy = origine
        self.ux, self.uy = direction
        self.vx, self.vy = perpendiculaire
        self.longueur = longueur
        self.index = index


class _Grille:
    """Cases qui retrouvent les emprises proches, sans toutes les paires."""

    def __init__(self, pas):
        self.pas = pas
        self.cases = {}
        self.tour = 0

    def ajouter(self, forme):
        for cle in self._cles(forme):
            self.cases.setdefault(cle, []).append(forme)

    def proches(self, forme):
        self.tour += 1
        tour = self.tour
        vues = []
        cases = self.cases
        for cle in self._cles(forme):
            for autre in cases.get(cle, ()):
                if autre.marque != tour:
                    autre.marque = tour
                    vues.append(autre)
        return vues

    def _cles(self, forme):
        pas = self.pas
        ix = math.floor(forme.min_x / pas)
        ix_fin = math.floor(forme.max_x / pas)
        iy_debut = math.floor(forme.min_y / pas)
        iy_fin = math.floor(forme.max_y / pas)
        while ix <= ix_fin:
            iy = iy_debut
            while iy <= iy_fin:
                yield ix, iy
                iy += 1
            ix += 1


def _parametres():
    """Relit les constantes du plan de base, une fois par appel public."""
    facade = _constantes.FACADE_MAISON_1400_M
    demi = _constantes.DEMI_LARGEUR_PAR_LARGEUR
    surface = _constantes.SURFACE_M2_PAR_FOYER_LOGE
    profondeur = surface / facade
    return SimpleNamespace(
        demi_cote=_constantes.DEMI_COTE_PLACE_1400_M,
        largeur_rue=_constantes.LARGEUR_RUE_1400_M,
        espacement=_constantes.ESPACEMENT_RUELLES_1400_M,
        longueur_ruelle=_constantes.LONGUEUR_RUELLE_1400_M,
        largeur_ruelle=_constantes.LARGEUR_RUELLE_1400_M,
        facade=facade,
        recul=_constantes.RECUL_MAISON_1400_M,
        demi=demi,
        decimales=_constantes.SNAPSHOT_FLOAT_DECIMALS,
        tolerance=_constantes.TOLERANCE_CHEVAUCHEMENT_M,
        pas=_constantes.PAS_GRILLE_VILLE_1400_M,
        longueur_min=_constantes.LONGUEUR_MIN_RUE_1400_M,
        demi_facade=facade * demi,
        demi_profondeur=profondeur * demi,
    )


def _axes(points):
    axes = []
    precedent = points[-1]
    for point in points:
        dx = point[0] - precedent[0]
        dy = point[1] - precedent[1]
        norme = math.hypot(dx, dy)
        if norme != 0:
            axes.append((-dy / norme, dx / norme))
        precedent = point
    return axes


def _projection(points, axe):
    ax, ay = axe
    valeur = points[0][0] * ax + points[0][1] * ay
    mini = maxi = valeur
    for x, y in points[1:]:
        valeur = x * ax + y * ay
        if valeur < mini:
            mini = valeur
        elif valeur > maxi:
            maxi = valeur
    return mini, maxi


def _profondeur(points, autres, axe):
    min_a, max_a = _projection(points, axe)
    min_b, max_b = _projection(autres, axe)
    return min(max_a, max_b) - max(min_a, min_b)


def _bbox_separe(gauche, droite, tolerance):
    recouvrement_x = min(gauche.max_x, droite.max_x) - max(gauche.min_x, droite.min_x)
    if recouvrement_x <= tolerance:
        return True
    recouvrement_y = min(gauche.max_y, droite.max_y) - max(gauche.min_y, droite.min_y)
    return recouvrement_y <= tolerance


def _recouvrent(gauche, droite, tolerance):
    if _bbox_separe(gauche, droite, tolerance):
        return False
    for points, autres, axes in (
        (gauche.points, droite.points, gauche.axes),
        (droite.points, gauche.points, droite.axes),
    ):
        for axe in axes:
            if _profondeur(points, autres, axe) <= tolerance:
                return False
    return True


def se_chevauchent(a, b):
    """Vrai si les intérieurs de deux polygones convexes se recouvrent.

    Le recouvrement doit dépasser ``TOLERANCE_CHEVAUCHEMENT_M``. Un côté
    partagé, ou un recouvrement plus petit, ne compte pas. Le contrat vaut
    pour des polygones convexes.
    """
    return _recouvrent(_Forme(a), _Forme(b), _constantes.TOLERANCE_CHEVAUCHEMENT_M)


def emprise_de_rue(points, largeur_m):
    """Rectangle du segment, coins arrondis, polygone convexe."""
    debut, fin = points[0], points[1]
    dx = fin[0] - debut[0]
    dy = fin[1] - debut[1]
    norme = math.hypot(dx, dy)
    if norme == 0:
        raise ValueError("segment de rue de longueur nulle")
    ux, uy = dx / norme, dy / norme
    vx, vy = -uy, ux
    demi = largeur_m * _constantes.DEMI_LARGEUR_PAR_LARGEUR
    decimales = _constantes.SNAPSHOT_FLOAT_DECIMALS
    ox, oy = vx * demi, vy * demi
    coins = (
        (debut[0] + ox, debut[1] + oy),
        (fin[0] + ox, fin[1] + oy),
        (fin[0] - ox, fin[1] - oy),
        (debut[0] - ox, debut[1] - oy),
    )
    return [[round(x, decimales), round(y, decimales)] for x, y in coins]


def _angle_positif(angle):
    tour = math.tau
    ramene = angle % tour
    if ramene < 0:
        ramene += tour
    return ramene


def _arrondir(x, y, decimales):
    return [round(x, decimales), round(y, decimales)]


def _trier_directions(directions):
    if not directions:
        return ((None, 0.0),)
    triees = []
    for identifiant, angle in directions:
        triees.append((identifiant, _angle_positif(angle)))
    triees.sort(key=lambda direction: (
        direction[1],
        direction[0] is None,
        0 if direction[0] is None else direction[0],
    ))
    return tuple(triees)


def _place(parametres):
    demi = parametres.demi_cote
    decimales = parametres.decimales
    return [
        _arrondir(signe_x * demi, signe_y * demi, decimales)
        for signe_x, signe_y in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def _sortie(angle, demi):
    ux, uy = math.cos(angle), math.sin(angle)
    portee = max(abs(ux), abs(uy))
    distance = demi / portee
    return (distance * ux, distance * uy), (ux, uy), (-uy, ux)


def _voie(ox, oy, ux, uy, vx, vy, longueur, largeur, sorte, vers, index, decimales):
    points = [
        _arrondir(ox, oy, decimales),
        _arrondir(ox + ux * longueur, oy + uy * longueur, decimales),
    ]
    return _Voie(
        points, largeur, sorte, vers,
        (ox, oy), (ux, uy), (vx, vy), longueur, index,
    )


def _voies(directions, longueur, parametres):
    voies = []
    index = 0
    for identifiant, angle in directions:
        origine, direction, perpendiculaire = _sortie(angle, parametres.demi_cote)
        ox, oy = origine
        ux, uy = direction
        vx, vy = perpendiculaire
        voies.append(_voie(
            ox, oy, ux, uy, vx, vy, longueur,
            parametres.largeur_rue, "principale", identifiant, index, parametres.decimales,
        ))
        index += 1
        station = parametres.espacement
        while station <= longueur:
            px = ox + ux * station
            py = oy + uy * station
            demi_chaussee = parametres.largeur_rue * parametres.demi
            for signe in (1, -1):
                debut_x = px + vx * signe * demi_chaussee
                debut_y = py + vy * signe * demi_chaussee
                ux_rue, uy_rue = vx * signe, vy * signe
                voies.append(_voie(
                    debut_x, debut_y, ux_rue, uy_rue, -uy_rue, ux_rue,
                    parametres.longueur_ruelle, parametres.largeur_ruelle,
                    "ruelle", None, index, parametres.decimales,
                ))
                index += 1
            station += parametres.espacement
    return voies


def _emprise_maison(cx, cy, ux, uy, vx, vy, parametres):
    demi_f = parametres.demi_facade
    demi_p = parametres.demi_profondeur
    decimales = parametres.decimales
    coins = []
    for signe_longueur, signe_profondeur in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        x = cx + signe_longueur * demi_f * ux + signe_profondeur * demi_p * vx
        y = cy + signe_longueur * demi_f * uy + signe_profondeur * demi_p * vy
        coins.append(_arrondir(x, y, decimales))
    return coins


def _cle_candidat(candidat):
    distance, rue, rang, signe, *_reste = candidat
    return distance, rue, rang, signe


def _candidats(voies, parametres):
    candidats = []
    facade = parametres.facade
    for voie in voies:
        demi_chaussee = voie.largeur * parametres.demi
        lateral = demi_chaussee + parametres.recul + parametres.demi_profondeur
        direction = (voie.ux, voie.uy, voie.vx, voie.vy)
        rang = 0
        while (rang + 1) * facade <= voie.longueur:
            centre = rang * facade + parametres.demi_facade
            for signe in (1, -1):
                cx = voie.ox + voie.ux * centre + voie.vx * signe * lateral
                cy = voie.oy + voie.uy * centre + voie.vy * signe * lateral
                candidats.append((cx * cx + cy * cy, voie.index, rang, signe, cx, cy, direction))
            rang += 1
    return candidats


def _publier(voie):
    rue = {
        "points": voie.points,
        "largeur_m": voie.largeur,
        "sorte": voie.sorte,
    }
    if voie.sorte == "principale":
        rue["vers_cell_id"] = voie.vers
    return rue


def _poser(voies, nombre, foyers, parametres, grille):
    """Pose les objets d'une même forme, du centre vers l'extérieur."""
    candidats = _candidats(voies, parametres)
    maisons = []
    if nombre > 0 and candidats:
        candidats.sort(key=_cle_candidat)
        tolerance = parametres.tolerance
        for candidat in candidats:
            if len(maisons) == nombre:
                break
            _distance, _rue, _rang, _signe, cx, cy, direction = candidat
            ux, uy, vx, vy = direction
            emprise = _emprise_maison(cx, cy, ux, uy, vx, vy, parametres)
            forme = _Forme(emprise)
            if any(_recouvrent(forme, autre, tolerance) for autre in grille.proches(forme)):
                continue
            grille.ajouter(forme)
            maisons.append({"emprise": emprise, "foyers": foyers})
    return maisons


def _assembler(directions, longueur, groupes, parametres):
    place = _place(parametres)
    voies = _voies(directions, longueur, parametres)
    grille = _Grille(parametres.pas)
    grille.ajouter(_Forme(place))
    for voie in voies:
        grille.ajouter(_Forme(emprise_de_rue(voie.points, voie.largeur)))
    maisons = []
    for nombre, foyers, forme in groupes:
        maisons.extend(_poser(voies, nombre, foyers, forme, grille))
    return {
        "place": place,
        "rues": [_publier(voie) for voie in voies],
        "maisons": maisons,
    }


def _forme_ilots(foyers, parametres):
    forme = SimpleNamespace(**vars(parametres))
    forme.facade = parametres.facade * min(foyers, _constantes.MAISONS_EN_FACADE_ILOT)
    forme.demi_facade = forme.facade * parametres.demi
    forme.demi_profondeur = foyers * _constantes.SURFACE_M2_PAR_FOYER_LOGE / forme.facade * parametres.demi
    return forme


def _groupes(n_foyers, parametres):
    """Maisons individuelles sous le seuil, sinon îlots pleins puis reste."""
    if n_foyers <= _constantes.FOYERS_SANS_ILOTS:
        return ((n_foyers, 1, parametres),)
    maximum = _constantes.MAISONS_PAR_ILOT_MAX
    pleins, reste = divmod(n_foyers, maximum)
    groupes = []
    if pleins:
        groupes.append((pleins, maximum, _forme_ilots(maximum, parametres)))
    if reste:
        groupes.append((1, reste, _forme_ilots(reste, parametres)))
    return groupes


def _quotient_haut(numerateur, diviseur):
    return (numerateur + diviseur - 1) // diviseur


def _longueur_initiale(n_objets, n_rues, parametres):
    if n_objets == 0 or n_rues == 0:
        return parametres.longueur_min
    cotes = (1, -1)
    pas = _quotient_haut(n_objets, n_rues * len(cotes))
    return max(parametres.longueur_min, pas * parametres.facade)


def _etendre(longueur, n_objets, obtenus, parametres):
    if obtenus <= 0:
        return longueur + parametres.espacement
    suivante = longueur * n_objets / obtenus + parametres.facade
    if suivante <= longueur:
        return longueur + parametres.espacement
    return suivante


def base_d_une_population(population, directions):
    """Place, rues, maisons ou îlots d'une population, sans lire le monde."""
    parametres = _parametres()
    n_foyers = ranger_en_foyers(population).nombre
    groupes = _groupes(n_foyers, parametres)
    n_objets = sum(nombre for nombre, _foyers, _forme in groupes)
    forme = groupes[0][-1]
    dirs = _trier_directions(directions)
    if n_foyers == 0:
        return _assembler(dirs, parametres.longueur_min, groupes, parametres)
    longueur = _longueur_initiale(n_objets, len(dirs), forme)
    while True:
        base = _assembler(dirs, longueur, groupes, parametres)
        obtenus = len(base["maisons"])
        if obtenus == n_objets:
            return base
        longueur = _etendre(longueur, n_objets, obtenus, forme)


def _centroide(monde, cell_id):
    enregistrement = monde.carte.get(cell_id) if monde.carte else None
    centroide = enregistrement.get("centroid") if isinstance(enregistrement, dict) else None
    if not isinstance(centroide, dict) or "x_m" not in centroide or "y_m" not in centroide:
        raise BaseAbsente(f"cellule {cell_id} : centroïde absent, angle non deviné")
    return centroide["x_m"], centroide["y_m"]


def _directions_terre(monde, cell_id):
    centre_x, centre_y = _centroide(monde, cell_id)
    voisines = {}
    for arete in monde.adjacency:
        if arete.get("kind") != "land-land":
            continue
        if arete.get("a") == cell_id:
            autre = arete.get("b")
        elif arete.get("b") == cell_id:
            autre = arete.get("a")
        else:
            continue
        if autre in voisines:
            continue
        voisin_x, voisin_y = _centroide(monde, autre)
        voisines[autre] = math.atan2(voisin_y - centre_y, voisin_x - centre_x)
    if not voisines:
        return ((None, 0.0),)
    return tuple(voisines.items())


def base_de_cellule(monde, cell_id):
    """Ville de 1400 de la cellule, lue sur l'amorçage et l'adjacence."""
    populations = monde.populations_bourg_amorcage
    if populations is None:
        raise BaseAbsente(
            f"cellule {cell_id} : populations_bourg_amorcage absentes "
            "(monde sans amorçage)"
        )
    if cell_id not in populations:
        raise BaseAbsente(f"cellule {cell_id} : inconnue du monde amorcé")
    base = base_d_une_population(populations[cell_id], _directions_terre(monde, cell_id))
    base["cell_id"] = cell_id
    return base
