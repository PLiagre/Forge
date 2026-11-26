"""Noms historiques et plausibles, projection pure hors du tick."""
import dataclasses
import functools
import json
import math
import re
import types
import unicodedata
from pathlib import Path
from sim.frontieres import maison_du_bourg
from sim.projection import projeter_epsg3035
from sim.puissances import charger_table, puissances_depuis_monde
from sim.villes import LATITUDE_MAX, LONGITUDE_MAX, attribuer_villes, charger_villes, point_dans_geometrie

CHEMIN_NOMS = Path(__file__).resolve().parent.parent / 'data/noms-1400.json'
CHEMIN_CHEFS_LIEUX = Path(__file__).resolve().parent.parent / 'data/chefs-lieux-1400.json'
_CLES_CHEFS_LIEUX = frozenset({'date', 'reference', 'unite', 'description', 'fidelite', 'chefs_lieux', 'sans_ville'})
_DATE_CHEFS_LIEUX, _REFERENCE_CHEFS_LIEUX = '1400-01-01', 'EPSG:4326'
_URL = re.compile(r'https?://\S+')
_ARTICLES_DE_REGION = ("le ", "la ", "les ", "l'")

@dataclasses.dataclass(frozen=True)
class ChefLieu:
    nom: str
    lat: float
    lon: float
    source: str

@dataclasses.dataclass(frozen=True)
class ChefsLieux:
    """cell_id → chef-lieu sourcé ; cell_id → raison d'une terre où l'histoire ne nomme aucune ville ;
    cell_id → nom de cette terre, avec son article (« le Souf »), pour les mêmes cellules."""
    lignes: types.MappingProxyType
    sans_ville: types.MappingProxyType
    regions: types.MappingProxyType

def charger_noms(chemin=None):
    """Valide toutes les listes, y compris celles que la carte ne consulte pas."""
    document = json.loads(Path(chemin or CHEMIN_NOMS).read_text(encoding='utf-8'))
    for regle in document['regles']:
        if regle['aire'] not in document['aires']:
            raise ValueError(f"{regle['aire']} : listes absentes")
        if not all(c in regle for c in ('puissances', 'religions', 'lat', 'lon')):
            raise ValueError(f"{regle['aire']} : critères absents")
    for aire, listes in document['aires'].items():
        for champ in ('lieux', 'maisons', 'prenoms'):
            valeurs = listes.get(champ) if isinstance(listes, dict) else None
            if not isinstance(valeurs, list) or not valeurs or any(not isinstance(v, str) or not v.strip() for v in valeurs):
                raise ValueError(f'{aire} : {champ} absent ou vide')
            if len({v.strip().casefold() for v in valeurs}) != len(valeurs):
                raise ValueError(f'{aire} : {champ} doublon')
    return document
def _texte_chef_lieu(valeur, ou):
    if not isinstance(valeur, str) or not valeur.strip(): raise ValueError(f'chefs-lieux, {ou} : texte absent ou vide')
    return valeur
def _cellule_chef_lieu(ligne, vues):
    cid = ligne.get('cell_id') if isinstance(ligne, dict) else None
    if isinstance(cid, bool) or not isinstance(cid, int): raise ValueError(f'chefs-lieux, ligne {ligne!r} : cell_id entier attendu')
    if cid in vues: raise ValueError(f'chefs-lieux, cellule {cid} : décidée deux fois')
    vues.add(cid); return cid
def _degres(valeur, borne, ou):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur) or not -borne <= valeur <= borne:
        raise ValueError(f'chefs-lieux, {ou} : nombre fini entre {-borne} et {borne} attendu')
    return valeur
@functools.lru_cache(maxsize=None)
def _chefs_lieux(chemin):
    document = json.loads(Path(chemin).read_text(encoding='utf-8'))
    if not isinstance(document, dict) or set(document) != _CLES_CHEFS_LIEUX: raise ValueError(f'chefs-lieux : clés {sorted(_CLES_CHEFS_LIEUX)} attendues')
    if document['date'] != _DATE_CHEFS_LIEUX or document['reference'] != _REFERENCE_CHEFS_LIEUX: raise ValueError('chefs-lieux : date ou référence inattendue')
    for cle in ('unite', 'description', 'fidelite'): _texte_chef_lieu(document[cle], cle)
    if not isinstance(document['chefs_lieux'], list) or not isinstance(document['sans_ville'], list): raise ValueError('chefs-lieux : listes attendues')
    vues, noms, lignes, sans_ville, regions = set(), set(), {}, {}, {}
    for ligne in document['chefs_lieux']:
        cid = _cellule_chef_lieu(ligne, vues)
        if set(ligne) != {'cell_id', 'nom', 'lat', 'lon', 'source'}: raise ValueError(f'chefs-lieux, cellule {cid} : champs cell_id, nom, lat, lon, source attendus')
        nom, source = _texte_chef_lieu(ligne['nom'], f'cellule {cid} nom'), _texte_chef_lieu(ligne['source'], f'cellule {cid} source')
        if not _URL.search(source): raise ValueError(f'chefs-lieux, cellule {cid} : source sans URL publique')
        if nom.strip().casefold() in noms: raise ValueError(f'chefs-lieux, cellule {cid} : nom {nom} deux fois')
        noms.add(nom.strip().casefold())
        lignes[cid] = ChefLieu(nom, _degres(ligne['lat'], LATITUDE_MAX, f'cellule {cid} lat'), _degres(ligne['lon'], LONGITUDE_MAX, f'cellule {cid} lon'), source)
    pris = set()
    for ligne in document['sans_ville']:
        cid = _cellule_chef_lieu(ligne, vues)
        if set(ligne) != {'cell_id', 'region', 'raison'}: raise ValueError(f'chefs-lieux, cellule {cid} : champs cell_id, region, raison attendus')
        region = _texte_chef_lieu(ligne['region'], f'cellule {cid} region')
        droite = region.replace("\u2019", "'")
        article = next((a for a in _ARTICLES_DE_REGION if droite.startswith(a) and droite[len(a):].strip()), None)
        if article is None: raise ValueError(f'chefs-lieux, cellule {cid} : région {region} sans article ({", ".join(a.strip() for a in _ARTICLES_DE_REGION)})')
        sans_article = droite[len(article):].strip().casefold()
        if droite.strip().casefold() in noms or sans_article in noms: raise ValueError(f'chefs-lieux, cellule {cid} : région {region} est le nom d\'un chef-lieu')
        if droite.strip().casefold() in pris: raise ValueError(f'chefs-lieux, cellule {cid} : région {region} deux fois')
        pris.add(droite.strip().casefold())
        regions[cid] = region
        sans_ville[cid] = _texte_chef_lieu(ligne['raison'], f'cellule {cid} raison')
    return ChefsLieux(types.MappingProxyType(dict(sorted(lignes.items()))), types.MappingProxyType(dict(sorted(sans_ville.items()))),
                      types.MappingProxyType(dict(sorted(regions.items()))))
def charger_chefs_lieux(chemin=None):
    """Lit et valide le fichier une fois par chemin ; le résultat est immuable."""
    return _chefs_lieux(str(Path(chemin or CHEMIN_CHEFS_LIEUX).resolve()))
@functools.lru_cache(maxsize=None)
def _villes_livrees():
    return charger_villes()
_DERNIERE_ATTRIBUTION_LIVREE = {}
def attribution_livree(monde):
    """Les villes de `villes-1400.json` placées sur la carte du monde, quel que soit le jeu de villes qui a
    amorcé ses populations. L'attribution du monde sert telle quelle quand elle porte exactement ces villes
    (le monde livré) ; sinon, ou sans attribution, celle du fichier est refaite sur sa carte, gardée pour la
    dernière carte, jugée par identité comme `_chefs_lieux_dans_leur_cellule`."""
    villes, propre = _villes_livrees(), monde.attribution_villes
    if propre is not None and (propre.entrees is villes or propre.entrees == villes): return propre
    garde = _DERNIERE_ATTRIBUTION_LIVREE.get('carte')
    if garde is None or garde[0] is not monde.carte or garde[1] is not monde.carte_meta:
        attribution = attribuer_villes({**monde.carte_meta, 'cellules': list(monde.carte.values())}, villes)
        garde = _DERNIERE_ATTRIBUTION_LIVREE['carte'] = (monde.carte, monde.carte_meta, attribution)
    _, _, attribution = garde
    return attribution
def aire_de_cellule(cid, cellule, puissance, table, noms):
    """La première règle applicable lit la religion dans la table des puissances."""
    religion = None if puissance is None else next(p.religion for p in table.puissances if p.id == puissance); position = cellule['centroid']
    for r in noms['regles']:
        if (puissance in r['puissances'] and religion in r['religions']
                and all(r[c][0] <= position[c] <= r[c][-1] for c in ('lat', 'lon'))):
            return r['aire']
    raise ValueError(f'cellule {cid} : aucune règle de noms (puissance={puissance}, religion={religion})')
_DERNIERE_PLACE_DES_CHEFS_LIEUX = {}
def _chefs_lieux_dans_leur_cellule(chefs, carte):
    """Les cellules de la carte dont le chef-lieu tombe dans le polygone. Le fichier et la carte figée ne
    changent pas pendant une partie : le calcul est gardé pour le dernier couple (fichier, carte), jugé par
    identité, et refait pour tout autre."""
    garde = _DERNIERE_PLACE_DES_CHEFS_LIEUX.get('couple')
    if garde is None or garde[0] is not chefs or garde[1] is not carte:
        dedans = frozenset(cid for cid, ligne in chefs.lignes.items() if cid in carte
                           and point_dans_geometrie(*projeter_epsg3035(ligne.lat, ligne.lon), carte[cid]['geometry']))
        garde = _DERNIERE_PLACE_DES_CHEFS_LIEUX['couple'] = (chefs, carte, dedans)
    _, _, dedans = garde
    return dedans
def bourgs_historiques(monde, attribution, chefs=None):
    """cell_id → nom sourcé du bourg ; une terre déclarée sans ville n'y est pas.

    Le siège de la maison qui prend le bourg (`maison_du_bourg`), sinon la ville placée de plus forte
    population historique (puis nom croissant) dont aucun siège ne nomme déjà une autre terre, sinon le
    chef-lieu de la cellule. `attribution` porte les villes de `villes-1400.json` (`attribution_livree`) :
    le fichier des chefs-lieux se juge contre elles. Refuse, en nommant la cellule, un chef-lieu hors du polygone de sa cellule,
    une ligne pour une cellule déjà nommée et une cellule ni nommée ni déclarée ; les lignes des cellules
    hors du monde sont laissées de côté."""
    chefs = charger_chefs_lieux() if chefs is None else chefs
    # maison_du_bourg ne choisit jamais une maison plausible : elle ne parcourt que les autres.
    historiques = types.SimpleNamespace(maisons=tuple(m for m in monde.maisons if m.sorte != 'plausible'))
    registre = {m.id: m for m in historiques.maisons}; cellules = {m.cell_id for m in historiques.maisons}
    par_siege = {cid: registre[i].siege for cid in sorted(monde.cells) if cid in cellules and (i := maison_du_bourg(historiques, cid)) is not None}
    pris = {nom.casefold() for nom in par_siege.values()}
    villes = {}
    for v in sorted(attribution.entrees, key=lambda v: (-v.population, v.nom)):
        cid = attribution.placees.get(v.nom)
        if cid is not None and cid not in par_siege and cid not in villes and v.nom.casefold() not in pris: villes[cid] = v.nom
    resultat = {}; dedans = _chefs_lieux_dans_leur_cellule(chefs, monde.carte)
    for cid in sorted(monde.cells):
        nom = par_siege.get(cid) or villes.get(cid); ligne = chefs.lignes.get(cid)
        if nom is not None and (ligne is not None or cid in chefs.sans_ville):
            raise ValueError(f'chefs-lieux, cellule {cid} : déjà nommée {nom} par un siège ou une ville, sa ligne est inutile')
        if nom is None and ligne is not None:
            if cid not in dedans:
                raise ValueError(f'chefs-lieux, cellule {cid} : {ligne.nom} hors du polygone de sa cellule')
            nom = ligne.nom
        if nom is None and cid not in chefs.sans_ville: raise ValueError(f'chefs-lieux, cellule {cid} : ni nommée ni déclarée sans ville')
        if nom is not None: resultat[cid] = nom
    return resultat
def sources_des_noms(monde):
    """Ce que `noms_depuis_monde` reçoit en arguments, lu des données et de la carte, jamais des maîtres :
    les listes de noms, la table des puissances et la puissance de chaque cellule, dans l'ordre de ses
    arguments. Qui refait les noms d'un même monde les lit une fois et les lui repasse. Les chefs-lieux
    (`data/chefs-lieux-1400.json`) ne passent pas par là : `charger_chefs_lieux` les lit une fois par
    processus."""
    table = charger_table()
    return charger_noms(), table, puissances_depuis_monde(monde, table=table)
# Les mots d'une désignation : elle décrit un lieu que l'histoire ne nomme pas, sans lui prêter de nom.
_CAMPAGNE = 'campagne'
_DIRECTIONS_8 = ('nord', 'nord-est', 'est', 'sud-est', 'sud', 'sud-ouest', 'ouest', 'nord-ouest')
_DIRECTIONS_16 = ('nord', 'nord-nord-est', 'nord-est', 'est-nord-est', 'est', 'est-sud-est', 'sud-est', 'sud-sud-est',
                  'sud', 'sud-sud-ouest', 'sud-ouest', 'ouest-sud-ouest', 'ouest', 'ouest-nord-ouest', 'nord-ouest',
                  'nord-nord-ouest')
# Les tangentes des bornes des secteurs dans un quart de tour, depuis le nord : 22,5° et 67,5° pour huit
# directions ; 11,25°, 33,75°, 56,25° et 78,75° pour seize. Racines carrées et quatre opérations seules, sans
# trigonométrie : les mêmes bits sous Windows et sous Linux.
_TAN_22 = math.sqrt(2) - 1
_TAN_11 = (math.sqrt(1 + _TAN_22 * _TAN_22) - 1) / _TAN_22
_BORNES = {8: (_TAN_22, 1 / _TAN_22), 16: (_TAN_11, (1 - _TAN_11) / (1 + _TAN_11), (1 + _TAN_11) / (1 - _TAN_11), 1 / _TAN_11)}
_DIRECTIONS = {len(_DIRECTIONS_8): _DIRECTIONS_8, len(_DIRECTIONS_16): _DIRECTIONS_16}
_QUARTS_DE_TOUR = 4
_METRES_PAR_KM = 1000
_DIXIEMES_PAR_KM = 10
# Les degrés d'une désignation et le nombre de directions de chacun : la direction ; puis la distance en
# kilomètres ; puis la direction en seize ; puis la distance au dixième de kilomètre.
_SECTEURS_PAR_DEGRE = {1: 8, 2: 8, 3: 16, 4: 16}
_DEGRE_SANS_DISTANCE, _DEGRE_MAX = min(_SECTEURS_PAR_DEGRE), max(_SECTEURS_PAR_DEGRE)
def _de_la_province(nom):
    """« de » devant le nom d'une terre, élidé ou contracté : d'Orléans, du Mans, des Baux, du Souf, de La Rochelle."""
    for article, contraction in (('le ', 'du '), ('les ', 'des ')):
        if nom[:len(article)].casefold() == article: return contraction + nom[len(article):]
    return ("d'" if unicodedata.normalize('NFD', nom[0])[0].casefold() in 'aeiouy' else 'de ') + nom
# Le nom d'un petit seigneur : une désignation de sa fonction et de son siège, jamais un nom de maison inventé.
SEIGNEUR = 'Seigneur'
def nom_de_seigneur(nom_du_lieu, region=None):
    """« Seigneur de <lieu de son siège> » : une ville passe par `_de_la_province` (Seigneur de Saint-Dizier,
    d'Orléans, du Mans), une désignation (« campagne de … ») prend « de la », et le bourg d'une terre déclarée sans
    ville prend sa `region` telle qu'écrite dans les données, article en minuscule (Seigneur du Souf, de l'île de Jura)."""
    if region is not None: return f'{SEIGNEUR} {_de_la_province(region)}'
    if nom_du_lieu.startswith(_CAMPAGNE + ' '): return f'{SEIGNEUR} de {avec_son_article(nom_du_lieu)}'
    return f'{SEIGNEUR} {_de_la_province(nom_du_lieu)}'
def avec_son_article(nom_du_lieu):
    """Le nom d'un lieu tel qu'une phrase l'écrit après « de » : une désignation prend son article (« la campagne de
    Bar-le-Duc, au nord-est »), un nom de ville reste tel quel."""
    return f'la {nom_du_lieu}' if nom_du_lieu.startswith(_CAMPAGNE + ' ') else nom_du_lieu
def _vers(direction):
    """« au nord », « à l'est-sud-est »."""
    return ("à l'" if direction.startswith(('est', 'ouest')) else 'au ') + direction
def _direction(dx, dy, secteurs):
    """La direction du vecteur (dx vers l'est, dy vers le nord), parmi `secteurs` (8 ou 16), par comparaison de pentes."""
    # Un quart de tour à la fois, le vecteur revient dans le quart nord-est ; le vecteur nul n'a pas de direction.
    quart, x, y = 0, dx, dy
    while not (x >= 0 and y > 0): quart, x, y = quart + 1, -y, x
    secteur = quart * secteurs // _QUARTS_DE_TOUR + sum(x > y * borne for borne in _BORNES[secteurs])
    return _DIRECTIONS[secteurs][secteur % secteurs]
def _position(bourg, place, degre):
    dx, dy = place.x_m - bourg.x_m, place.y_m - bourg.y_m
    direction = _vers(_direction(dx, dy, _SECTEURS_PAR_DEGRE[degre]))
    if degre == _DEGRE_SANS_DISTANCE: return direction
    distance = math.sqrt(dx * dx + dy * dy)
    if degre < _DEGRE_MAX: km = str(round(distance / _METRES_PAR_KM))
    else: dixiemes = round(distance * _DIXIEMES_PAR_KM / _METRES_PAR_KM); km = f'{dixiemes // _DIXIEMES_PAR_KM},{dixiemes % _DIXIEMES_PAR_KM}'
    return f'à {km} km {direction}'
def _designations(cid, places, rangs, province):
    """rang → « campagne de <province>, <position> » des `rangs` ; la position, vue depuis la place du bourg,
    monte d'un degré pour les lieux qu'elle ne distingue pas encore. Refuse deux lieux qu'aucun degré ne distingue."""
    degres = {r: _DEGRE_SANS_DISTANCE for r in rangs}
    while True:
        positions = {r: _position(places[0], places[r], degres[r]) for r in rangs}
        groupes = {}
        for r in rangs: groupes.setdefault(positions[r], []).append(r)
        doubles = [g for g in groupes.values() if len(g) > 1]
        if not doubles: break
        for groupe in doubles:
            montent = [r for r in groupe if degres[r] < _DEGRE_MAX]
            if not montent: raise ValueError(f'cellule {cid} : les lieux {groupe} ne se distinguent pas ({positions[groupe[0]]})')
            for r in montent: degres[r] += 1
    return {r: f'{_CAMPAGNE} {_de_la_province(province)}, {positions[r]}' for r in rangs}
@functools.lru_cache(maxsize=None)
def _sieges_sources():
    from sim.places import sieges_des_maisons
    return sieges_des_maisons()
@functools.lru_cache(maxsize=None)
def _villes_des_frontieres(chemin):
    """Les villes de partage (nom, x, y, cellule déclarée), par cellule puis dans l'ordre déclaré, et les villes
    témoins placées sur la carte (nom, x, y), par nom, de la table des frontières lue à `chemin`."""
    from sim.frontieres import charger_frontieres
    table = charger_frontieres(chemin)
    partages = tuple((v.nom, *projeter_epsg3035(v.lat, v.lon), cid) for cid, villes in table.partages.items() for v in villes)
    return partages, tuple((t.nom, *projeter_epsg3035(t.lat, t.lon)) for t in table.temoins if t.hors_carte is None)
_DERNIERS_TEMOINS = {}
def _temoins_dans_leur_cellule(temoins, carte):
    """(nom, x, y, cellule) des témoins, la cellule étant celle dont le polygone contient le point (la plus
    petite sur un bord). Gardé pour le dernier couple (témoins, carte), jugé par identité."""
    garde = _DERNIERS_TEMOINS.get('couple')
    if garde is None or garde[0] is not temoins or garde[1] is not carte:
        boites = {}
        for cid in sorted(carte):
            geometrie = carte[cid]['geometry']; polygones = [geometrie['coordinates']] if geometrie['type'] == 'Polygon' else geometrie['coordinates']
            xs, ys = [p[0] for poly in polygones for p in poly[0]], [p[1] for poly in polygones for p in poly[0]]
            boites[cid] = (min(xs), min(ys), max(xs), max(ys))
        places = tuple((nom, x, y, next((c for c, (x0, y0, x1, y1) in boites.items() if x0 <= x <= x1 and y0 <= y <= y1
                                         and point_dans_geometrie(x, y, carte[c]['geometry'])), None)) for nom, x, y in temoins)
        garde = _DERNIERS_TEMOINS['couple'] = (temoins, carte, places)
    _, _, places = garde
    return places
def villes_a_nommer(monde, attribution):
    """(nom, x, y, cell_id) des villes sourcées, dans l'ordre où elles nomment les lieux : les sièges du registre
    (par identifiant), les villes de `villes-1400.json` (population décroissante, puis nom), les villes de partage
    (par cellule, dans l'ordre déclaré), puis les villes témoins (par nom). Une ville hors du monde n'y est pas."""
    from sim import frontieres
    sieges = _sieges_sources()
    villes = [(m.siege, *sieges[m.id], m.cell_id) for m in sorted(monde.maisons, key=lambda m: m.id)
              if m.sorte != 'plausible' and m.cell_id is not None and m.id in sieges]
    villes += [(v.nom, v.x_m, v.y_m, attribution.placees[v.nom]) for v in sorted(attribution.entrees, key=lambda v: (-v.population, v.nom))
               if v.nom in attribution.placees]
    partages, temoins = _villes_des_frontieres(str(frontieres._CHEMIN))
    villes += list(partages) + list(_temoins_dans_leur_cellule(temoins, monde.carte))
    return [(nom, x, y, cid) for nom, x, y, cid in villes if cid in monde.cells]
def noms_des_lieux(monde, bourgs, provinces, places, villes):
    """cell_id → noms des lieux par rang. Le bourg porte le nom de sa terre (`bourgs`). Chaque ville de `villes`,
    dans leur ordre, va au lieu de sa cellule dont la place est la plus proche (à égalité, le plus petit rang) ;
    ce lieu prend son nom s'il n'est pas le bourg, s'il n'a pas déjà sa ville et si aucun lieu du monde ne porte
    ce nom, à la casse près. Les autres lieux se désignent d'après leur province (`provinces`) et leur position.
    Refuse un nom porté deux fois."""
    portes = {nom.casefold() for nom in bourgs.values()}
    noms = {cid: {0: bourgs[cid]} for cid in sorted(monde.cells)}
    for nom, x, y, cid in villes:
        lieux = places[cid]
        rang = min(range(len(lieux)), key=lambda r: ((lieux[r].x_m - x) * (lieux[r].x_m - x) + (lieux[r].y_m - y) * (lieux[r].y_m - y), r))
        if rang in noms[cid] or nom.casefold() in portes: continue
        noms[cid][rang] = nom; portes.add(nom.casefold())
    for cid, cellule in sorted(monde.cells.items()):
        restes = [l.rang for l in sorted(cellule.lieux, key=lambda l: l.rang) if l.rang not in noms[cid]]
        for rang, designation in _designations(cid, places[cid], restes, provinces[cid]).items():
            if designation.casefold() in portes: raise ValueError(f'cellule {cid} : « {designation} » nomme déjà un autre lieu')
            noms[cid][rang] = designation; portes.add(designation.casefold())
    return noms
_DERNIERS_NOMS_DES_LIEUX = {}
def _lieux_nommes(monde, attribution, places):
    """cell_id → noms des lieux par rang (`noms_des_lieux`). Ils ne lisent ni un maître ni le tick : ils se
    gardent pour le dernier monde nommé, jugé par identité de la carte, des villes, des places et des chefs-lieux,
    et par valeur des cellules et des sièges du registre ; une prise de lieu ne les refait pas."""
    from sim import frontieres
    chefs = charger_chefs_lieux()
    identites = (monde.carte, attribution, places, chefs)
    valeurs = (str(frontieres._CHEMIN), tuple((cid, len(c.lieux)) for cid, c in sorted(monde.cells.items())),
               tuple((m.id, m.sorte, m.cell_id, m.siege) for m in monde.maisons if m.sorte != 'plausible'))
    garde = _DERNIERS_NOMS_DES_LIEUX.get('monde')
    if garde is None or any(a is not b for a, b in zip(garde[0], identites)) or garde[1] != valeurs:
        bourgs = bourgs_historiques(monde, attribution, chefs); provinces = dict(bourgs)
        portes = {nom.casefold() for nom in bourgs.values()}
        for cid in sorted(monde.cells):
            if cid in bourgs: continue
            region = chefs.regions[cid]; bourgs[cid] = region[0].upper() + region[1:]; provinces[cid] = region
            if bourgs[cid].casefold() in portes: raise ValueError(f'chefs-lieux, cellule {cid} : la région {region} nomme déjà une autre terre')
            portes.add(bourgs[cid].casefold())
        garde = _DERNIERS_NOMS_DES_LIEUX['monde'] = (identites, valeurs, noms_des_lieux(monde, bourgs, provinces, places, villes_a_nommer(monde, attribution)))
    _, _, lieux = garde
    return lieux
def noms_depuis_monde(monde, noms=None, table=None, vue=None, attribution=None, places=None):
    """Un bloc neuf par cellule. Le bourg porte le nom sourcé de sa terre, ou la région d'une terre déclarée sans
    ville ; les autres lieux, une ville sourcée qui tombe chez eux, sinon une désignation (`noms_des_lieux`) ;
    chaque maison suit sa fiche : son nom et sa sorte, et pour une plausible « Seigneur de <lieu de son siège> »
    (`nom_de_seigneur`) et un prénom de chef tiré de l'aire de sa terre. Sans `attribution`, les villes qui
    nomment les terres sont celles de `villes-1400.json` (`attribution_livree`) ; sans `places`, celles de `places_du_monde`."""
    from sim.places import places_du_monde
    noms = charger_noms() if noms is None else noms
    table = charger_table() if table is None else table; vue = puissances_depuis_monde(monde, table=table) if vue is None else vue
    attribution = attribution_livree(monde) if attribution is None else attribution
    places = places_du_monde(monde) if places is None else places
    registre = {m.id: m for m in monde.maisons}; resultat = {}
    lieux = _lieux_nommes(monde, attribution, places)
    aires = {}
    def aire(cid):
        if cid not in aires: aires[cid] = aire_de_cellule(cid, monde.carte[cid], vue[cid], table, noms)
        return aires[cid]
    regions = charger_chefs_lieux().regions
    for cid, cellule in sorted(monde.cells.items()):
        fiches = {}
        for identifiant in sorted({l.maitre for l in cellule.lieux if l.maitre is not None}):
            m = registre[identifiant]
            if m.sorte != 'plausible': fiches[identifiant] = {'nom': m.nom, 'prenom_chef': None, 'sorte': m.sorte}; continue
            prenoms = noms['aires'][aire(m.cell_id)]['prenoms']
            region = regions.get(m.cell_id) if m.rang == 0 else None
            fiches[identifiant] = {'nom': nom_de_seigneur(lieux[m.cell_id][m.rang], region),
                                  'prenom_chef': prenoms[(m.cell_id + m.rang) % len(prenoms)], 'sorte': m.sorte}
        resultat[cid] = {'lieux': [{'rang': rang, 'nom': nom} for rang, nom in sorted(lieux[cid].items())], 'maisons': fiches}
    return resultat
