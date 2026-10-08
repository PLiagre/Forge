"""Maîtres des lieux dérivés, sans stockage ni tirage au sort."""
from itertools import zip_longest

import sim.constants as _constantes
from sim.lieux import lieux_depuis_monde
from sim.maisons import charger_maisons
from sim.puissances import puissances_depuis_monde
from sim.registre_maisons import MaisonDuMonde


class AttributionInvalide(ValueError):
    """Une attribution ne respecte pas les lieux ou la règle des maîtres."""


def attribuer_maitres(monde, vue=None, maisons=None):
    """Rend un dictionnaire neuf et les fiches plausibles dans l'ordre spatial."""
    depart = _constantes.LIEUX_DE_LA_SEIGNEURIE
    groupe = _constantes.LIEUX_PAR_SEIGNEUR_PLAUSIBLE
    for nom, valeur in (("LIEUX_DE_LA_SEIGNEURIE", depart),
                        ("LIEUX_PAR_SEIGNEUR_PLAUSIBLE", groupe)):
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
            raise AttributionInvalide(f"{nom} : entier positif exigé")
    lieux = lieux_depuis_monde(monde)
    vue = puissances_depuis_monde(monde) if vue is None else vue
    maisons = charger_maisons() if maisons is None else maisons
    maitres = {(cid, lieu.rang): None for cid, cellule in lieux.items() for lieu in cellule}
    registre = sorted(monde.maisons, key=lambda m: m.id)
    for sortes in (("seigneurie",), ("grande maison", "institution")):
        for maison in registre:
            if maison.sorte not in sortes or maison.cell_id is None:
                continue
            for lieu in lieux[maison.cell_id]:
                couple = (maison.cell_id, lieu.rang)
                if maitres[couple] is None and (maison.sorte != "seigneurie" or lieu.rang < depart):
                    maitres[couple] = maison.id
    plausibles = []
    for cid, cellule in lieux.items():
        libres = [lieu.rang for lieu in cellule if maitres[cid, lieu.rang] is None]
        puissance = vue[cid]
        racine = maisons.par_puissance[puissance] if puissance is not None else None
        suzerain = (f"grande-{racine}" if racine is not None else
                    f"institution-{puissance}" if puissance is not None else None)
        for debut in range(0, len(libres), groupe):
            rangs = libres[debut:debut + groupe]
            identifiant = f"plausible-{cid}-{rangs[0]}"
            plausibles.append(MaisonDuMonde(identifiant, identifiant, "plausible", suzerain,
                                           identifiant, cid, rangs[0], None))
            for rang in rangs:
                maitres[cid, rang] = identifiant
    return maitres, tuple(plausibles)


def valider_attribution(monde, maitres, plausibles, vue=None, maisons=None):
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
    attendus, fiches = attribuer_maitres(monde, vue, maisons)
    for couple in couples:
        if maitres[couple] != attendus[couple]:
            raise AttributionInvalide(f"{couple} : maître différent de la règle")
    for actuelle, attendue in zip_longest(plausibles, fiches):
        if actuelle != attendue:
            maison = actuelle if actuelle is not None else attendue
            raise AttributionInvalide(f"{(maison.cell_id, maison.rang)} : fiche plausible différente de la règle")
