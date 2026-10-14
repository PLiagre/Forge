"""Données de l'encart, exclusivement lues dans la photographie du monde."""
from copy import deepcopy

KG_PAR_PIXEL = 50000
EPAISSEUR_MAX = 8
COULEUR_JOUEUR = '#e6ab02'
PALETTE = ('#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#a6761d', '#666666')
FLUX_LIEU = ('preleve_kg', 'partis_personnes', 'arrives_personnes')
FLUX_MAISON = ('preleve_kg', 'recu_kg', 'du_envoye_kg', 'mange_en_route_kg', 'rendu_kg', 'partis_personnes', 'arrives_personnes')

class EncartErreur(ValueError):
    """Une mesure nécessaire manque ou la lecture contredit sa source."""


def _champ(objet, champ, contexte, nullable=False):
    if not isinstance(objet, dict) or champ not in objet or (objet[champ] is None and not nullable):
        raise EncartErreur(f'{contexte} : champ {champ} absent ou nul')
    return objet[champ]


def _siege(maison):
    contexte = f"maison {maison['id']}, siège"
    siege = _champ(maison, 'siege', contexte)
    for champ in ('cell_id', 'rang', 'nom', 'point'): _champ(siege, champ, contexte)
    return deepcopy(siege)


def lire_encart(document):
    """Rend des primitives et une légende détachées, sans charger ni dessiner."""
    resultat = dict(cellules=[], lieux=[], couleurs={}, fleches=[], cercles=[], compteurs={}, legende=[])
    terre = _champ(document, 'terre_choisie', 'photographie', nullable=True)
    if terre is None:
        resultat['legende'] = ['aucune terre choisie']
        return resultat
    bloc = _champ(document, 'maisons_du_joueur', 'photographie')
    maison = deepcopy(_champ(bloc, 'maison', 'maisons_du_joueur'))
    joueur = _champ(maison, 'id', 'maison du joueur'); contexte = f'maison {joueur}'
    for champ in ('nom', 'part', 'grenier'): _champ(maison, champ, contexte)
    flux = _champ(maison, 'flux_30j', contexte)
    for champ in FLUX_MAISON: _champ(flux, champ, f'{contexte}, flux_30j')
    suzerain_id = _champ(maison, 'suzerain', contexte, nullable=True)
    suzerain = deepcopy(_champ(bloc, 'suzerain', contexte, nullable=suzerain_id is None))
    siege = _siege(maison); destination = None if suzerain_id is None else _siege(suzerain)
    if suzerain_id is not None and _champ(suzerain, 'id', 'maison suzerain') != suzerain_id:
        raise EncartErreur(f'{contexte} : suzerain incohérent')
    ids = {terre['cell_id']} | {v['cell_id'] for v in terre['voisins']}
    cellules = {c['cell_id']: c for c in _champ(document, 'cells', 'photographie')}
    for cid in sorted(ids):
        if cid not in cellules: raise EncartErreur(f'cell_id {cid} : cellule de la zone absente')
        cellule = deepcopy(cellules[cid]); cellule['lieux'].sort(key=lambda l: l['rang'])
        resultat['cellules'].append(cellule)
        for lieu in cellule['lieux']:
            contexte = f"lieu ({cid}, {lieu['rang']})"
            for champ in ('nom', 'point', 'flux_30j'): _champ(lieu, champ, contexte)
            _champ(lieu, 'maitre', contexte, nullable=True)
            for champ in FLUX_LIEU: _champ(lieu['flux_30j'], champ, f'{contexte}, flux_30j')
            resultat['lieux'].append(dict(deepcopy(lieu), cell_id=cid))
    lieux = resultat['lieux']; autres = sorted({l['maitre'] for l in lieux if l['maitre'] not in (None, joueur)})
    couleurs = resultat['couleurs']; couleurs[joueur] = COULEUR_JOUEUR
    groupes = [{l['maitre'] for l in c['lieux']} for c in resultat['cellules']]
    for maitre in autres:
        interdites = {couleurs[m] for g in groupes if maitre in g for m in g if m in couleurs}
        couleur = next((c for c in PALETTE if c not in interdites), None)
        if couleur is None: raise EncartErreur(f'maître {maitre} : palette épuisée')
        couleurs[maitre] = couleur
    def fleche(sorte, source, cible, kg):
        extremite = lambda l: {k: deepcopy(l[k]) for k in ('cell_id', 'rang', 'nom', 'point')}
        return dict(sorte=sorte, source=extremite(source), destination=extremite(cible), kg=kg, epaisseur_px=min(EPAISSEUR_MAX, kg / KG_PAR_PIXEL))
    for lieu in lieux:
        lieu['couleur'] = couleurs.get(lieu['maitre'])
        f = lieu['flux_30j']; perte = f['partis_personnes'] - f['arrives_personnes']
        lieu['perte_nette_personnes'] = perte
        if lieu['maitre'] == joueur and (lieu['cell_id'], lieu['rang']) != (siege['cell_id'], siege['rang']):
            resultat['fleches'].append(fleche('prelevement', lieu, siege, f['preleve_kg']))
        if perte > 0:
            resultat['cercles'].append({k: deepcopy(lieu[k]) for k in ('cell_id', 'rang', 'point', 'maitre', 'perte_nette_personnes')} | {k: f[k] for k in FLUX_LIEU[1:]})
    if destination is not None: resultat['fleches'].append(fleche('du', siege, destination, flux['du_envoye_kg']))
    compteurs = dict(
        cellules=len(ids), lieux=len(lieux), maitres=len({l['maitre'] for l in lieux if l['maitre'] is not None}),
        autres_maitres=len(autres), lieux_joueur=sum(l['maitre'] == joueur for l in lieux),
        autres_lieux=sum(l['maitre'] not in (None, joueur) for l in lieux),
        lieux_sans_maitre=sum(l['maitre'] is None for l in lieux),
        cercles_joueur=sum(c['maitre'] == joueur for c in resultat['cercles']),
        cercles_autres=sum(c['maitre'] != joueur for c in resultat['cercles']))
    legende = [f"tick {document['tick']} ; fenêtre de 30 jours", f'échelle : KG_PAR_PIXEL = {KG_PAR_PIXEL} kg/pixel ; EPAISSEUR_MAX = {EPAISSEUR_MAX} pixels ; plafond, épaisseur = min(EPAISSEUR_MAX, kg / KG_PAR_PIXEL)', f'compteurs : {compteurs}']
    legende += [f'maître {m} : couleur {c}' for m, c in sorted(couleurs.items())]
    legende += [f"joueur {maison['nom']} ({joueur}) ; part = {maison['part']} ; grenier = {maison['grenier']}", f"siège {siege['nom']} ({siege['cell_id']}, {siege['rang']}) ; siège, sans flèche", 'sans suzerain' if destination is None else f"suzerain {suzerain['nom']} ({suzerain_id}), siège {destination['nom']} ({destination['cell_id']}, {destination['rang']})", 'autres maîtres : sans flèche de prélèvement, fiches de siège absentes de la photographie']
    legende += [f"maison du joueur, {k} = {flux[k]} {'kg' if k.endswith('_kg') else 'personnes'}" for k in FLUX_MAISON]
    for l in lieux:
        f = l['flux_30j']; est_siege = (l['cell_id'], l['rang']) == (siege['cell_id'], siege['rang']) and l['maitre'] == joueur
        statut = 'siège, sans flèche' if est_siege else 'lieu du joueur' if l['maitre'] == joueur else 'sans maître, sans flèche' if l['maitre'] is None else 'autre maître, sans flèche'
        legende.append(f"{l['nom']} ({l['cell_id']}, {l['rang']}), maître {l['maitre']}, {statut} : prélevé = {f['preleve_kg']} kg ; sorties = {f['partis_personnes']} personnes ; entrées = {f['arrives_personnes']} personnes ; perte nette = {l['perte_nette_personnes']} personnes")
    legende += [f"{f['sorte']} : {f['source']['nom']} ({f['source']['cell_id']}, {f['source']['rang']}) → {f['destination']['nom']} ({f['destination']['cell_id']}, {f['destination']['rang']}) : {f['kg']} kg ; {f['epaisseur_px']} pixels" for f in resultat['fleches']]
    resultat.update(joueur=maison, suzerain=suzerain, compteurs=compteurs, legende=legende)
    return resultat


def verifier_legende(document, encart):
    """Confronte toute la lecture, ses destinations et sa légende aux champs sources."""
    reference = lire_encart(document)
    for champ in reference:
        if champ not in encart or encart[champ] != reference[champ]:
            raise EncartErreur(f'{champ} : encart différent de la photographie')
