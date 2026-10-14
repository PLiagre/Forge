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

# Le rouge des pertes ne doit jamais se confondre avec celui du choix historique.
COULEUR_PERTE = (210, 55, 65, 255)
COULEUR_CONTOUR = (95, 109, 119, 255)
COULEUR_SANS_MAITRE = '#b0b0b0'
COULEUR_FLUX = (110, 194, 225)


def dessiner_encart(document, *, largeur):
    """Dessine la photographie vérifiée ; les fractions portent leur couverture."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from vues.relief.raster import index_des_cellules, _vers_pixel
    from vues.relief.carte1400 import _lignes_ajustees, MARGE_FICHE, HAUTEUR_LIGNE, COULEUR_FOND, COULEUR_TEXTE

    try:
        e = lire_encart(document); verifier_legende(document, e)
        if largeur < 8: raise EncartErreur('largeur de l’encart trop petite')
        legende = list(e['legende']); hauteur = dessinees = coupees = cercles = 0
        plan = np.empty((0, largeur, 4), dtype=np.uint8)
        if e['cellules']:
            index, bornes, _ = index_des_cellules({'cells': e['cellules']}, largeur=largeur)
            hauteur = len(index); plan = np.full((hauteur, largeur, 4), (24, 30, 34, 255), dtype=np.uint8)
            bord = np.zeros(index.shape, bool)
            for a, b in ((np.s_[:, :-1], np.s_[:, 1:]), (np.s_[:-1, :], np.s_[1:, :])): bord[a] |= index[a] != index[b]
            # Fermer aussi les contours qui touchent le rectangle.
            bord[0] |= index[0] > 0; bord[-1] |= index[-1] > 0
            bord[:, 0] |= index[:, 0] > 0; bord[:, -1] |= index[:, -1] > 0
            plan[bord] = COULEUR_CONTOUR; yy, xx = np.indices(index.shape)
            def position(l):
                p = l['point']; return np.array(_vers_pixel(p['x_m'], p['y_m'], bornes, largeur, hauteur), dtype=float)
            for f in e['fleches']:
                source, cible = f['source']['point'], f['destination']['point']
                a, destination = position(f['source']), position(f['destination']); v = destination-a
                longueur = np.linalg.norm(v)
                minx, miny, maxx, maxy = bornes
                dehors = not (minx <= cible['x_m'] <= maxx and miny <= cible['y_m'] <= maxy)
                if dehors:
                    legende.append(f"{f['destination']['nom']} : siège hors encart ; dû = {f['kg']} kg")
                if f['kg'] <= 0 or longueur == 0: continue
                t = 1.0
                # Couper le segment en mètres : jamais un rabattement des deux axes.
                for axe, minimum, maximum in (('x_m', minx, maxx), ('y_m', miny, maxy)):
                    delta = cible[axe]-source[axe]
                    if delta: t = min(t, (maximum-source[axe])/delta if delta > 0 else (minimum-source[axe])/delta)
                bout = np.array(_vers_pixel(source['x_m']+t*(cible['x_m']-source['x_m']), source['y_m']+t*(cible['y_m']-source['y_m']), bornes, largeur, hauteur))
                u = v/longueur; n = np.array([-u[1], u[0]]); w = f['epaisseur_px']
                segment = bout-a; l2 = np.dot(segment, segment)
                if l2 == 0: continue
                projection = np.clip(((xx-a[0])*segment[0]+(yy-a[1])*segment[1])/l2, 0, 1)
                distance = np.hypot(xx-a[0]-projection*segment[0], yy-a[1]-projection*segment[1])
                couverture = np.clip(w/2+.5-distance, 0, min(1, w))
                pointe = Image.new('L', (largeur, hauteur)); crayon = ImageDraw.Draw(pointe)
                base = bout-u*max(6, 2*w); rayon = max(3, w)
                crayon.polygon([tuple(bout), tuple(base+n*rayon), tuple(base-n*rayon)], fill=255)
                couverture = np.maximum(couverture, np.array(pointe)/255*min(1, w))
                # Arrondir la couverture positive vers le haut garde même un kilo visible.
                alpha = np.ceil(couverture*255)/255
                plan[..., :3] = np.ceil(plan[..., :3]*(1-alpha[..., None])+np.array(COULEUR_FLUX)*alpha[..., None]).astype(np.uint8)
                dessinees += int(np.any(alpha)); coupees += int(dehors and np.any(alpha))
            vignette = Image.fromarray(plan); dessin = ImageDraw.Draw(vignette)
            for lieu in e['lieux']:
                x, y = position(lieu); dessin.ellipse((x-3, y-3, x+3, y+3), fill=lieu['couleur'] or COULEUR_SANS_MAITRE)
            for cercle in e['cercles']:
                x, y = position(cercle); dessin.ellipse((x-8, y-8, x+8, y+8), outline=COULEUR_PERTE, width=2); cercles += 1
            plan = np.array(vignette)
            legende += ['points : couleur du maître ; gris : sans maître', 'flèches : lieu vers siège, siège vers suzerain ; épaisseur absolue en kilos', 'cercles rouges : perte nette positive ; couleur du lieu conservée au centre']
        police = ImageFont.load_default(); dessin = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        lignes = _lignes_ajustees(legende, dessin, police, largeur)
        bande = Image.new('RGBA', (largeur, 2*MARGE_FICHE+HAUTEUR_LIGNE*len(lignes)), COULEUR_FOND)
        dessin = ImageDraw.Draw(bande)
        for i, ligne in enumerate(lignes): dessin.text((MARGE_FICHE, MARGE_FICHE+i*HAUTEUR_LIGNE), ligne, font=police, fill=COULEUR_TEXTE)
        image = np.concatenate((plan, np.array(bande)))
        return image, dict(tick=document['tick'], seed=document['seed'], largeur=largeur, hauteur_plan=hauteur, hauteur_totale=len(image), compteurs=e['compteurs'], fleches_dessinees=dessinees, fleches_coupees=coupees, cercles_dessines=cercles, legende=legende)
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as exc:
        raise EncartErreur(f'encart : {exc}') from exc
