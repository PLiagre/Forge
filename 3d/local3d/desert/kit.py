"""Les modules ajoutés au kit du désert sans le reconstruire, leur budget et leur jugement.

Python pur : Blender (`fabriquer.py kit`) l'importe pour refuser un module trop lourd,
Python (`atelier_desert.py kit`) pour juger ce qu'Unity a mesuré. Les plafonds ne vivent
qu'ici ; personne ne les recopie.

Unity mesure, Python juge. Chaque défaut porte une étiquette ; chaque contre-épreuve
rejoue `juger` sur une copie déréglée de ses entrées et doit rougir avec l'étiquette
attendue.
"""
import copy

# Lot 269 : les bâtiments finis qui ont leurs étapes de chantier, dans l'ordre du catalogue.
CHANTIERS = ['maison_pise_0', 'scierie', 'four_pain_pise']
ETAPES = ('piquets', 'murs')


def suite(fini):
    """Les étapes d'un chantier dans l'ordre où elles se suivent, puis le bâtiment fini."""
    return ['chantier_{}_{}'.format(fini, e) for e in ETAPES] + [fini]


# Dans l'ordre où ils s'ajoutent à la fin du catalogue.
NOUVEAUX = ['scierie', 'four_pain_pise'] + [s for fini in CHANTIERS for s in suite(fini)[:-1]]
# Les bâtiments finis des chantiers qu'Unity mesure sans les refaire (leur prefab existe déjà).
REFERENCES = [fini for fini in CHANTIERS if fini not in NOUVEAUX]
# Plafonds de triangles par LOD (0, 1, 2).
PLAFONDS = {'scierie': (2400, 1200, 400), 'four_pain_pise': (1600, 800, 300)}
for _fini in CHANTIERS:
    PLAFONDS['chantier_{}_piquets'.format(_fini)] = (400, 200, 80)
    PLAFONDS['chantier_{}_murs'.format(_fini)] = (1200, 600, 240)
TOLERANCE_ORIGINE = 0.01       # m : le point le plus bas du LOD0 est au sol à 1 cm près
TOLERANCE_EMPRISE = 0.3        # m : chaque bord horizontal d'une étape, au bord du bâtiment fini
HAUTEUR_PIQUETS_MAX = 1.2      # m
RAPPORT_MURS = (0.5, 0.8)      # hauteur de l'étape des murs, perches comprises, sur celle du fini
BORDS = ('x_min', 'x_max', 'z_min', 'z_max')
NIVEAUX = 3
ETIQUETTES = ('budget', 'origine', 'lod', 'materiau', 'echantillon', 'catalogue', 'empreinte',
              'emprise', 'hauteur', 'suite')


def defaut(etiquette, message):
    assert etiquette in ETIQUETTES, etiquette
    return {'etiquette': etiquette, 'message': message}


def ecart_pixels(pixels):
    """Variation spatiale d'une image (hauteur × largeur × canaux) : le plus grand des
    écarts-types de chaque canal pris sur les pixels. Une image uniforme, de quelque couleur
    qu'elle soit, donne 0 ; une image vide, -1."""
    import numpy as np
    p = np.asarray(pixels, dtype=float)
    if not p.size:
        return -1.0
    p = p.reshape(-1, p.shape[-1]) if p.ndim == 3 else p.reshape(-1, 1)
    return float(p.std(axis=0).max())


def controler(nom, triangles, materiaux, connus, plafonds=None):
    """Le refus de Blender : budget et matériaux, avant tout export."""
    plafonds = PLAFONDS if plafonds is None else plafonds
    fautes = []
    if nom not in plafonds:
        return [defaut('budget', nom + ' : aucun plafond dans kit.py')]
    for i, (n, p) in enumerate(zip(triangles, plafonds[nom])):
        if n > p:
            fautes.append(defaut('budget', '{} : LOD{} a {} triangles pour un plafond de {}'.format(nom, i, n, p)))
    for m in sorted(set(materiaux) - set(connus)):
        fautes.append(defaut('materiau', '{} : matériau absent du catalogue : {}'.format(nom, m)))
    return fautes


def mesuree(m):
    """Une mesure d'Unity est prise quand ni son enveloppe ni sa hauteur ne valent -1."""
    return all(isinstance(m.get(k), (int, float)) and m.get(k) != -1 for k in BORDS + ('y_max',))


def juger_chantiers(entrees):
    """Lot 269 : emprise, hauteurs et suite des étapes de chantier."""
    u = entrees['unity'] or {}; apres = entrees['catalogue_apres']
    fautes = []
    modules = {m.get('id'): m for m in u.get('modules') or []}
    references = {m.get('id'): m for m in u.get('references') or []}

    # SC7 : exactement les bâtiments de référence, au moins un.
    mesures = [m.get('id') for m in u.get('references') or []]
    if not REFERENCES or mesures != REFERENCES:
        fautes.append(defaut('echantillon', 'Unity a mesuré les références {} ; attendu {}'.format(mesures, REFERENCES)))

    for fini in CHANTIERS:
        f = modules.get(fini) or references.get(fini)
        piquets, murs = suite(fini)[:2]
        etapes = [(e, modules.get(e)) for e in (piquets, murs)]
        # SC2 : chaque étape posée sur l'emprise du bâtiment fini, mesurée par Unity des deux côtés.
        if not f or not mesuree(f):
            fautes.append(defaut('emprise', fini + ' : bâtiment fini non mesuré par Unity'))
        for e, m in etapes:
            if not m or not mesuree(m):
                fautes.append(defaut('emprise', e + ' : enveloppe non mesurée par Unity'))
            elif f and mesuree(f):
                for bord in BORDS:
                    if abs(m[bord] - f[bord]) > TOLERANCE_EMPRISE:
                        fautes.append(defaut('emprise', '{} : {} à {:.3f} m, {} à {:.3f} m (tolérance {} m)'.format(
                            e, bord, m[bord], fini, f[bord], TOLERANCE_EMPRISE)))
        # SC3 : les hauteurs montent avec le chantier.
        hp = modules[piquets]['y_max'] if piquets in modules and mesuree(modules[piquets]) else None
        hm = modules[murs]['y_max'] if murs in modules and mesuree(modules[murs]) else None
        hf = f['y_max'] if f and mesuree(f) else None
        if hp is None or hm is None or hf is None:
            fautes.append(defaut('hauteur', '{} : hauteurs non mesurées (piquets {}, murs {}, fini {})'.format(fini, hp, hm, hf)))
            continue
        if not hp <= HAUTEUR_PIQUETS_MAX:
            fautes.append(defaut('hauteur', '{} : {:.3f} m, au-dessus de {} m'.format(piquets, hp, HAUTEUR_PIQUETS_MAX)))
        if not hp < hm:
            fautes.append(defaut('hauteur', '{} : {:.3f} m, pas sous les murs ({:.3f} m)'.format(piquets, hp, hm)))
        if not RAPPORT_MURS[0] * hf <= hm <= RAPPORT_MURS[1] * hf:
            fautes.append(defaut('hauteur', '{} : {:.3f} m, soit {:.2f} fois {} ({:.3f} m) ; attendu entre {} et {}'.format(
                murs, hm, hm / hf if hf else -1, fini, hf, *RAPPORT_MURS)))

    # SC4 : la suite est déclarée, et complète.
    if 'chantiers' not in apres:
        fautes.append(defaut('suite', 'le catalogue après n\'a pas de clé chantiers'))
    else:
        declares = apres['chantiers'] or {}
        if sorted(declares) != sorted(CHANTIERS):
            fautes.append(defaut('suite', 'chantiers déclarés {} ; attendu {}'.format(sorted(declares), CHANTIERS)))
        fiches = {a['id'] for a in apres['assets']}
        for fini in CHANTIERS:
            s = declares.get(fini)
            if s != suite(fini):
                fautes.append(defaut('suite', '{} : suite {} ; attendu {}'.format(fini, s, suite(fini))))
            for i in s or []:
                if i not in fiches:
                    fautes.append(defaut('suite', '{} : {} n\'est pas une fiche du catalogue'.format(fini, i)))
        for fini in CHANTIERS:
            for e in suite(fini)[:-1]:
                if e not in modules:
                    fautes.append(defaut('suite', e + ' : étape non mesurée par Unity'))
    return fautes


def juger(entrees):
    """Les défauts, sans les contre-épreuves.

    `entrees` : plafonds, catalogue_avant, catalogue_apres, unity (le rapport de
    DesertKit), empreintes_avant, empreintes_apres, ecart_image (`ecart_pixels` de la
    planche des ateliers, -1 si elle manque), ecart_chantiers (de même pour la planche des
    chantiers), ecart_minimal, verification (le vérificateur des scènes rejoué par la
    commande : status, message, et le status de chaque disposition).
    """
    plafonds = entrees['plafonds']; u = entrees['unity'] or {}
    avant = entrees['catalogue_avant']; apres = entrees['catalogue_apres']
    fautes = []

    # SC4 : un échantillon vide échoue.
    modules = u.get('modules') or []
    mesures = [m.get('id') for m in modules]
    if not NOUVEAUX or mesures != NOUVEAUX:
        fautes.append(defaut('echantillon', 'Unity a mesuré {} ; attendu {}'.format(mesures, NOUVEAUX)))
    nouveaux_apres = [a['id'] for a in apres['assets'] if a['id'] in NOUVEAUX]
    if not NOUVEAUX or nouveaux_apres != NOUVEAUX:
        fautes.append(defaut('echantillon', 'le catalogue après porte {} ; attendu {}'.format(nouveaux_apres, NOUVEAUX)))
    if not entrees['empreintes_avant']:
        fautes.append(defaut('echantillon', 'aucune empreinte relevée avant'))
    for e in u.get('erreurs') or []:
        fautes.append(defaut('echantillon', 'Unity : ' + e))

    # SC6 : les anciens enregistrements, à l'identique et dans le même ordre.
    anciens_avant = [a for a in avant['assets'] if a['id'] not in NOUVEAUX]
    anciens_apres = [a for a in apres['assets'] if a['id'] not in NOUVEAUX]
    if anciens_avant != anciens_apres:
        change = [a['id'] for a, b in zip(anciens_avant, anciens_apres) if a != b]
        fautes.append(defaut('catalogue', '{} anciens modules avant, {} après ; différents : {}'.format(
            len(anciens_avant), len(anciens_apres), change or 'ordre ou nombre')))
    if [a['id'] for a in apres['assets']] != [a['id'] for a in anciens_apres] + nouveaux_apres:
        fautes.append(defaut('catalogue', 'les nouveaux modules ne sont pas à la fin du catalogue'))
    # Lot 269 : toute fiche d'avant, nouveaux modules compris, se retrouve à l'identique ; hors
    # `chantiers`, aucune clé du catalogue n'apparaît, ne disparaît ni ne change.
    fiches_apres = {a['id']: a for a in apres['assets']}
    changees = [a['id'] for a in avant['assets'] if fiches_apres.get(a['id']) != a]
    if changees:
        fautes.append(defaut('catalogue', 'fiches d\'avant absentes ou changées : {}'.format(changees)))
    cles = sorted((set(avant) | set(apres)) - {'assets', 'chantiers'})
    for cle in cles:
        if avant.get(cle, -1) != apres.get(cle, -1):
            fautes.append(defaut('catalogue', 'la clé {} du catalogue a changé'.format(cle)))

    # SC5 : seulement les matériaux du catalogue.
    connus = [m['name'] for m in avant['materials']]
    if [m for m in apres['materials']] != [m for m in avant['materials']]:
        fautes.append(defaut('materiau', 'la liste des matériaux du catalogue a changé'))
    for m in u.get('materiaux_manquants') or []:
        fautes.append(defaut('materiau', 'Unity ne trouve pas le matériau ' + m))

    # SC7 : rien d'autre ne bouge.
    ea = entrees['empreintes_avant']; ep = entrees['empreintes_apres']
    for chemin in sorted(set(ea) | set(ep)):
        if ea.get(chemin) != ep.get(chemin):
            fautes.append(defaut('empreinte', 'fichier ' + ('apparu' if chemin not in ea else 'disparu' if chemin not in ep else 'modifié') + ' : ' + chemin))

    # SC8 : les planches existent et ne sont pas uniformes.
    for cle, planche in (('ecart_image', 'ateliers'), ('ecart_chantiers', 'chantiers')):
        ecart = entrees.get(cle, -1.0)
        if not ecart >= entrees['ecart_minimal']:
            fautes.append(defaut('echantillon', 'planche des {} absente ou uniforme (écart-type {:.1f}, {} au moins)'.format(
                planche, ecart, entrees['ecart_minimal'])))

    # SC9 : le vérificateur existant reste vert, sur chaque disposition. Il n'a pas d'étiquette
    # à lui : aucune disposition vérifiée est un échantillon vide ; un vérificateur rouge dit
    # que les scènes du ksar, que gardent aussi les empreintes (SC7), ne sont plus intactes.
    v = entrees.get('verification') or {}
    rapports = v.get('dispositions') or {}
    if not rapports:
        fautes.append(defaut('echantillon', 'verifier : aucune disposition vérifiée'))
    if v.get('status') != 'valide' or any(s != 'valide' for s in rapports.values()):
        fautes.append(defaut('empreinte', 'verifier : {} ({}) ; dispositions {}'.format(
            v.get('status'), v.get('message') or 'aucun message', rapports or 'aucune')))

    catalogue = {a['id']: a for a in apres['assets']}
    for m in modules:
        nom = m.get('id', '?'); tri = m.get('triangles') or []
        # SC3 : trois LOD, égaux au catalogue, strictement décroissants.
        if m.get('niveaux') != NIVEAUX or len(tri) != NIVEAUX:
            fautes.append(defaut('lod', '{} : {} niveaux dans le LODGroup, {} mesures de triangles'.format(nom, m.get('niveaux'), len(tri))))
            continue
        if nom in catalogue and tri != catalogue[nom]['triangles']:
            fautes.append(defaut('lod', '{} : Unity mesure {}, le catalogue dit {}'.format(nom, tri, catalogue[nom]['triangles'])))
        if not tri[0] > tri[1] > tri[2] > 0:
            fautes.append(defaut('lod', '{} : triangles non strictement décroissants {}'.format(nom, tri)))
        # SC1 : sous le plafond.
        for i, (n, p) in enumerate(zip(tri, plafonds.get(nom, (-1,) * NIVEAUX))):
            if not 0 <= n <= p:
                fautes.append(defaut('budget', '{} : LOD{} mesuré à {} triangles pour un plafond de {}'.format(nom, i, n, p)))
        # SC2 : l'origine au sol.
        y = m.get('y_min')
        if y is None or abs(y) > TOLERANCE_ORIGINE:
            fautes.append(defaut('origine', '{} : le LOD0 descend à y = {} (tolérance {} m)'.format(nom, y, TOLERANCE_ORIGINE)))
        # SC5 : chaque matériau mesuré est au catalogue.
        for mat in sorted(set(m.get('materiaux') or []) - set(connus)):
            fautes.append(defaut('materiau', '{} : matériau hors catalogue : {}'.format(nom, mat)))
        if not m.get('materiaux'):
            fautes.append(defaut('materiau', nom + ' : aucun matériau mesuré'))
    return fautes + juger_chantiers(entrees)


def contre_epreuves(entrees):
    """Chaque contre-épreuve : (étiquette attendue, entrées déréglées sur une copie)."""
    ce = {}
    modules = (entrees['unity'] or {}).get('modules') or []
    mesure = {m.get('id'): m for m in modules}

    e = copy.deepcopy(entrees)
    if 'scierie' in mesure and mesure['scierie'].get('triangles'):
        p = list(e['plafonds']['scierie']); p[0] = mesure['scierie']['triangles'][0] - 1; e['plafonds']['scierie'] = tuple(p)
    ce['piece_trop_lourde'] = ('budget', e)

    e = copy.deepcopy(entrees)
    for m in (e['unity'] or {}).get('modules') or []:
        if m.get('id') == 'four_pain_pise' and m.get('y_min') is not None:
            m['y_min'] += .05
    ce['origine_relevee'] = ('origine', e)

    e = copy.deepcopy(entrees)
    for m in (e['unity'] or {}).get('modules') or []:
        if m.get('id') == 'scierie' and len(m.get('triangles') or []) > 1:
            m['triangles'][1] += 1
    ce['triangles_divergents'] = ('lod', e)

    e = copy.deepcopy(entrees); e['unity'] = dict(e['unity'] or {}, modules=[])
    ce['echantillon_vide'] = ('echantillon', e)

    e = copy.deepcopy(entrees)
    for m in ((e['unity'] or {}).get('modules') or [])[:1]:
        m['materiaux'] = list(m.get('materiaux') or []) + ['inconnu']
    ce['materiau_neuf'] = ('materiau', e)

    e = copy.deepcopy(entrees)
    for a in e['catalogue_apres']['assets']:
        if a['id'] == 'maison_pise_0':
            a['bounds_max'][2] += 1
    ce['ancien_module_change'] = ('catalogue', e)

    e = copy.deepcopy(entrees)
    for chemin in e['empreintes_apres']:
        if chemin.endswith('Forge_Desert_ksar_des_sept_puits.unity'):
            e['empreintes_apres'][chemin] = 'touchee'
    ce['scene_touchee'] = ('empreinte', e)

    # La mesure elle-même est rejouée : une planche toute rouge doit être jugée uniforme.
    e = copy.deepcopy(entrees); e['ecart_image'] = ecart_pixels([[[255, 0, 0]] * 16] * 9)
    ce['planche_uniforme'] = ('echantillon', e)

    e = copy.deepcopy(entrees)
    e['verification'] = dict(e.get('verification') or {}, status='echec', message='contre-épreuve')
    ce['verification_rouge'] = ('empreinte', e)

    # Lot 269.
    e = copy.deepcopy(entrees)
    for m in (e['unity'] or {}).get('modules') or []:
        if m.get('id') == 'chantier_scierie_piquets':
            for bord in ('x_min', 'x_max'):
                if isinstance(m.get(bord), (int, float)):
                    m[bord] += 2
    ce['etape_decalee'] = ('emprise', e)

    e = copy.deepcopy(entrees)
    fini = next((m for m in (e['unity'] or {}).get('references') or [] if m.get('id') == 'maison_pise_0'), None)
    for m in (e['unity'] or {}).get('modules') or []:
        if m.get('id') == 'chantier_maison_pise_0_murs' and fini and isinstance(fini.get('y_max'), (int, float)):
            m['y_max'] = fini['y_max'] + .5
    ce['murs_trop_hauts'] = ('hauteur', e)

    e = copy.deepcopy(entrees)
    s = (e['catalogue_apres'].get('chantiers') or {}).get('four_pain_pise')
    if isinstance(s, list) and 'chantier_four_pain_pise_murs' in s:
        s.remove('chantier_four_pain_pise_murs')
    ce['etape_manquante'] = ('suite', e)

    e = copy.deepcopy(entrees); e['ecart_chantiers'] = ecart_pixels([[[255, 0, 0]] * 16] * 9)
    ce['planche_chantiers_uniforme'] = ('echantillon', e)
    return ce


def jugement(entrees):
    """Le jugement complet : défauts, contre-épreuves, et le défaut d'une contre-épreuve sans effet."""
    fautes = juger(entrees)
    resultats = {}
    for nom, (attendue, e) in contre_epreuves(entrees).items():
        etiquettes = sorted({f['etiquette'] for f in juger(e)})
        rougit = attendue in etiquettes
        resultats[nom] = {'attendue': attendue, 'obtenues': etiquettes, 'rougit': rougit}
        if not rougit:
            fautes.append(defaut(attendue, 'contre-épreuve sans effet : ' + nom))
    anciens = sum(a['id'] not in NOUVEAUX for a in entrees['catalogue_avant']['assets'])
    u = entrees['unity'] or {}
    return {'status': 'valide' if not fautes else 'echec', 'nouveaux': NOUVEAUX, 'anciens_modules': anciens,
            'empreintes': len(entrees['empreintes_avant']), 'plafonds': {k: list(v) for k, v in entrees['plafonds'].items()},
            'modules': u.get('modules') or [], 'references': u.get('references') or [],
            'chantiers': {fini: suite(fini) for fini in CHANTIERS}, 'ecart_image': entrees['ecart_image'],
            'ecart_chantiers': entrees.get('ecart_chantiers', -1.0),
            'verification': entrees.get('verification'), 'defauts': fautes, 'contre_epreuves': resultats}
