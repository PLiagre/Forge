"""Noms historiques et plausibles, projection pure hors du tick."""
import dataclasses
import functools
import json
import math
import re
import types
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

@dataclasses.dataclass(frozen=True)
class ChefLieu:
    nom: str
    lat: float
    lon: float
    source: str

@dataclasses.dataclass(frozen=True)
class ChefsLieux:
    """cell_id → chef-lieu sourcé, et cell_id → raison d'une terre où l'histoire ne nomme aucune ville."""
    lignes: types.MappingProxyType
    sans_ville: types.MappingProxyType

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
    vues, noms, lignes, sans_ville = set(), set(), {}, {}
    for ligne in document['chefs_lieux']:
        cid = _cellule_chef_lieu(ligne, vues)
        if set(ligne) != {'cell_id', 'nom', 'lat', 'lon', 'source'}: raise ValueError(f'chefs-lieux, cellule {cid} : champs cell_id, nom, lat, lon, source attendus')
        nom, source = _texte_chef_lieu(ligne['nom'], f'cellule {cid} nom'), _texte_chef_lieu(ligne['source'], f'cellule {cid} source')
        if not _URL.search(source): raise ValueError(f'chefs-lieux, cellule {cid} : source sans URL publique')
        if nom.strip().casefold() in noms: raise ValueError(f'chefs-lieux, cellule {cid} : nom {nom} deux fois')
        noms.add(nom.strip().casefold())
        lignes[cid] = ChefLieu(nom, _degres(ligne['lat'], LATITUDE_MAX, f'cellule {cid} lat'), _degres(ligne['lon'], LONGITUDE_MAX, f'cellule {cid} lon'), source)
    for ligne in document['sans_ville']:
        cid = _cellule_chef_lieu(ligne, vues)
        if set(ligne) != {'cell_id', 'raison'}: raise ValueError(f'chefs-lieux, cellule {cid} : champs cell_id, raison attendus')
        sans_ville[cid] = _texte_chef_lieu(ligne['raison'], f'cellule {cid} raison')
    return ChefsLieux(types.MappingProxyType(dict(sorted(lignes.items()))), types.MappingProxyType(dict(sorted(sans_ville.items()))))
def charger_chefs_lieux(chemin=None):
    """Lit et valide le fichier une fois par chemin ; le résultat est immuable."""
    return _chefs_lieux(str(Path(chemin or CHEMIN_CHEFS_LIEUX).resolve()))
def aire_de_cellule(cid, cellule, puissance, table, noms):
    """La première règle applicable lit la religion dans la table des puissances."""
    religion = None if puissance is None else next(p.religion for p in table.puissances if p.id == puissance); position = cellule['centroid']
    for r in noms['regles']:
        if (puissance in r['puissances'] and religion in r['religions']
                and all(r[c][0] <= position[c] <= r[c][-1] for c in ('lat', 'lon'))):
            return r['aire']
    raise ValueError(f'cellule {cid} : aucune règle de noms (puissance={puissance}, religion={religion})')
def _parcours(valeurs, cid, reserves=()):
    return [n for n in valeurs[cid % len(valeurs):] + valeurs[:cid % len(valeurs)] if n not in reserves]
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
    chef-lieu de la cellule. Refuse, en nommant la cellule, un chef-lieu hors du polygone de sa cellule,
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
def noms_depuis_monde(monde, noms=None, table=None, vue=None, attribution=None):
    """Un bloc neuf par cellule ; le bourg porte le nom sourcé de sa terre, ou un nom plausible que nulle
    autre terre ne porte ; les maisons suivent leur fiche et leur rang initial."""
    noms = charger_noms() if noms is None else noms
    table = charger_table() if table is None else table; vue = puissances_depuis_monde(monde, table=table) if vue is None else vue
    attribution = (monde.attribution_villes if monde.attribution_villes is not None else attribuer_villes({**monde.carte_meta, 'cellules': list(monde.carte.values())}, charger_villes())) if attribution is None else attribution
    registre = {m.id: m for m in monde.maisons}; resultat = {}
    aires = {cid: aire_de_cellule(cid, monde.carte[cid], vue[cid], table, noms) for cid in sorted(monde.cells)}
    bourgs = bourgs_historiques(monde, attribution); portes = {nom.casefold() for nom in bourgs.values()}
    for cid in sorted(monde.cells):
        if cid in bourgs: continue
        libre = next((n for n in _parcours(noms['aires'][aires[cid]]['lieux'], cid) if n.casefold() not in portes), None)
        if libre is None: raise ValueError(f'{aires[cid]} : lieux insuffisants pour un bourg sans ville, cellule {cid}')
        bourgs[cid] = libre; portes.add(libre.casefold())
    for cid, cellule in sorted(monde.cells.items()):
        aire = aires[cid]; listes = noms['aires'][aire]; bourg = bourgs[cid]
        candidats = [n for n in _parcours(listes['lieux'], cid)[1:] if n.casefold() != bourg.casefold()]; lieux = sorted(cellule.lieux, key=lambda l: l.rang)
        if len(candidats) < len(lieux) - 1: raise ValueError(f'{aire} : lieux insuffisants, cellule {cid}')
        fiches = {}
        for identifiant in sorted({l.maitre for l in lieux if l.maitre is not None}):
            m = registre[identifiant]
            if m.sorte != 'plausible': fiches[identifiant] = {'nom': m.nom, 'prenom_chef': None}; continue
            a = aires[m.cell_id] if m.cell_id in aires else aire_de_cellule(m.cell_id, monde.carte[m.cell_id], vue[m.cell_id], table, noms); source = noms['aires'][a]
            if m.rang >= len(source['maisons']): raise ValueError(f'{a} : maisons insuffisantes, cellule {m.cell_id}')
            fiches[identifiant] = {'nom': source['maisons'][(m.cell_id + m.rang) % len(source['maisons'])],
                                  'prenom_chef': source['prenoms'][(m.cell_id + m.rang) % len(source['prenoms'])]}
        resultat[cid] = {'lieux': [{'rang': l.rang, 'nom': n} for l, n in zip(lieux, [bourg] + candidats)], 'maisons': fiches}
    return resultat
