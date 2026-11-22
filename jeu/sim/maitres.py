"""Maîtres des lieux dérivés, sans stockage ni tirage au sort."""
from itertools import zip_longest

import sim.constants as _constantes
from sim.frontieres import maison_du_bourg, puissances_des_lieux
from sim.lieux import lieux_depuis_monde
from sim.maisons import charger_maisons
from sim.puissances import puissances_depuis_monde
from sim.registre_maisons import MaisonDuMonde


class AttributionInvalide(ValueError):
    """Une attribution ne respecte pas les lieux ou la règle des maîtres."""


def _tete(puissance, maisons):
    """La racine du registre qui règne sur une puissance, ou `None` pour un lieu sans pays."""
    if puissance is None:
        return None
    racine = maisons.par_puissance[puissance]
    return f"grande-{racine}" if racine is not None else f"institution-{puissance}"


def attribuer_maitres(monde, vue=None, maisons=None, puissances_lieux=None):
    """Rend un dictionnaire neuf et les fiches plausibles dans l'ordre spatial.

    Dans une cellule partagée (`puissances_lieux`, celle de `frontieres.puissances_des_lieux`), une
    grande maison ou une institution ne prend que les lieux du pays sur lequel elle règne, et les
    seigneurs plausibles se groupent par pays, chacun relevant de la racine de son pays."""
    depart = _constantes.LIEUX_DE_LA_SEIGNEURIE
    groupe = _constantes.LIEUX_PAR_SEIGNEUR_PLAUSIBLE
    for nom, valeur in (("LIEUX_DE_LA_SEIGNEURIE", depart),
                        ("LIEUX_PAR_SEIGNEUR_PLAUSIBLE", groupe)):
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
            raise AttributionInvalide(f"{nom} : entier positif exigé")
    lieux = lieux_depuis_monde(monde)
    vue = puissances_depuis_monde(monde) if vue is None else vue
    maisons = charger_maisons() if maisons is None else maisons
    puissances_lieux = puissances_des_lieux(monde) if puissances_lieux is None else puissances_lieux
    maitres = {(cid, lieu.rang): None for cid, cellule in lieux.items() for lieu in cellule}
    registre = sorted(monde.maisons, key=lambda m: m.id)
    for sortes in (("seigneurie",), ("grande maison", "institution")):
        for maison in registre:
            if maison.sorte not in sortes or maison.cell_id is None:
                continue
            for lieu in lieux[maison.cell_id]:
                couple = (maison.cell_id, lieu.rang)
                if maitres[couple] is not None:
                    continue
                if maison.sorte == "seigneurie":
                    prend = lieu.rang < depart
                else:
                    prend = (couple not in puissances_lieux
                             or _tete(puissances_lieux[couple], maisons) == maison.id)
                if prend:
                    maitres[couple] = maison.id
    for cid, rang in sorted(puissances_lieux):
        attendue = maison_du_bourg(monde, cid) if rang == 0 and cid in lieux else None
        if attendue is not None and maitres[cid, rang] != attendue:
            raise AttributionInvalide(f"{(cid, rang)} : bourg partagé placé au siège de {attendue}, "
                                      f"mais d'un pays où elle ne règne pas")
    plausibles = []
    for cid, cellule in lieux.items():
        par_pays = {}
        for lieu in cellule:
            if maitres[cid, lieu.rang] is None:
                par_pays.setdefault(puissances_lieux.get((cid, lieu.rang), vue[cid]), []).append(lieu.rang)
        for puissance, libres in par_pays.items():
            suzerain = _tete(puissance, maisons)
            for debut in range(0, len(libres), groupe):
                rangs = libres[debut:debut + groupe]
                identifiant = f"plausible-{cid}-{rangs[0]}"
                plausibles.append(MaisonDuMonde(identifiant, identifiant, "plausible", suzerain,
                                               identifiant, cid, rangs[0], None))
                for rang in rangs:
                    maitres[cid, rang] = identifiant
    return maitres, tuple(plausibles)


def valider_attribution(monde, maitres, plausibles, vue=None, maisons=None, puissances_lieux=None):
    """Nomme le premier couple fautif ; les suzerains se valident dans le registre."""
    couples = [(cid, lieu.rang) for cid, cellule in lieux_depuis_monde(monde).items()
               for lieu in cellule]
    if not couples or not maitres:
        raise AttributionInvalide(f"échantillon vide : {couples[0] if couples else (None, None)}")
    for couple in couples:
        if couple not in maitres:
            raise AttributionInvalide(f"{couple} : lieu sans maître")
    derives = set(couples)
    for couple in maitres:
        if couple not in derives:
            raise AttributionInvalide(f"{couple} : lieu en trop")
    registre = monde.maisons + plausibles
    connus = {m.id for m in registre}
    for couple in couples:
        if maitres[couple] not in connus:
            raise AttributionInvalide(f"{couple} : maître inconnu {maitres[couple]}")
    vus = set()
    for maison in registre:
        if maison.id in vus:
            raise AttributionInvalide(f"{(maison.cell_id, maison.rang)} : identifiant dupliqué {maison.id}")
        vus.add(maison.id)
    attendus, fiches = attribuer_maitres(monde, vue, maisons, puissances_lieux)
    for couple in couples:
        if maitres[couple] != attendus[couple]:
            raise AttributionInvalide(f"{couple} : maître différent de la règle")
    for actuelle, attendue in zip_longest(plausibles, fiches):
        if actuelle != attendue:
            maison = actuelle if actuelle is not None else attendue
            raise AttributionInvalide(f"{(maison.cell_id, maison.rang)} : fiche plausible différente de la règle")
