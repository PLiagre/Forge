"""Noms historiques et plausibles, projection pure hors du tick."""
import json
from pathlib import Path
from sim.puissances import charger_table, puissances_depuis_monde
from sim.villes import attribuer_villes, charger_villes

CHEMIN_NOMS = Path(__file__).resolve().parent.parent / 'data/noms-1400.json'
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
def noms_depuis_monde(monde, noms=None, table=None, vue=None, attribution=None):
    """Un bloc neuf par cellule ; les maisons suivent leur fiche et leur rang initial."""
    noms = charger_noms() if noms is None else noms
    table = charger_table() if table is None else table; vue = puissances_depuis_monde(monde, table=table) if vue is None else vue
    attribution = (monde.attribution_villes if monde.attribution_villes is not None else attribuer_villes({**monde.carte_meta, 'cellules': list(monde.carte.values())}, charger_villes())) if attribution is None else attribution
    registre = {m.id: m for m in monde.maisons}; resultat = {}
    for cid, cellule in sorted(monde.cells.items()):
        aire = aire_de_cellule(cid, monde.carte[cid], vue[cid], table, noms); listes = noms['aires'][aire]
        sieges = sorted((m for m in registre.values() if m.cell_id == cid and m.sorte == 'seigneurie'), key=lambda m: m.id)
        villes = sorted((v for v in attribution.entrees if attribution.placees.get(v.nom) == cid), key=lambda v: (-v.population, v.nom))
        historique = sieges[0].siege if sieges else villes[0].nom if villes else None
        candidats = _parcours(listes['lieux'], cid, (historique,)); lieux = sorted(cellule.lieux, key=lambda l: l.rang)
        if len(candidats) < len(lieux) - bool(historique): raise ValueError(f'{aire} : lieux insuffisants, cellule {cid}')
        fiches = {}
        for identifiant in sorted({l.maitre for l in lieux if l.maitre is not None}):
            m = registre[identifiant]
            if m.sorte != 'plausible': fiches[identifiant] = {'nom': m.nom, 'prenom_chef': None}; continue
            a = aire_de_cellule(m.cell_id, monde.carte[m.cell_id], vue[m.cell_id], table, noms); source = noms['aires'][a]
            if m.rang >= len(source['maisons']): raise ValueError(f'{a} : maisons insuffisantes, cellule {m.cell_id}')
            fiches[identifiant] = {'nom': source['maisons'][(m.cell_id + m.rang) % len(source['maisons'])],
                                  'prenom_chef': source['prenoms'][(m.cell_id + m.rang) % len(source['prenoms'])]}
        noms_lieux = ([historique] if historique else []) + candidats
        resultat[cid] = {'lieux': [{'rang': l.rang, 'nom': n} for l, n in zip(lieux, noms_lieux)], 'maisons': fiches}
    return resultat
