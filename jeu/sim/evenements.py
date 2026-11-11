"""Les événements du monde qui posent un modificateur : la famine, la première.

Un événement ne décide ni un kilo ni une mort : il lit un état que le tick a
déjà calculé (ici, la faim d'un lieu) et pose, dans le registre des
modificateurs (`sim/modificateurs.py`), une pose datée que `expirer` ôtera
seule. La faim, elle, tue toujours par la dette (`engine._apply_mortality`).
"""
import dataclasses

import sim.constants as _constantes
import sim.modificateurs as _modificateurs

IDENTIFIANT_FAMINE = "famine"
SOURCE_FAMINE = "evenement:famine"


def _lieu(monde, cid, rang):
    return next(lieu for lieu in monde.cells[cid].lieux if lieu.rang == rang)


def _famine_du_lieu(monde, cible):
    """L'indice de la pose `famine` d'un lieu dans `monde.modificateurs`, ou None."""
    return next((i for i, pose in enumerate(getattr(monde, "modificateurs", ()))
                 if pose.identifiant == IDENTIFIANT_FAMINE and pose.cible == cible), None)


def _fin(definition, tick):
    """La fin d'une pose, comme `modificateurs.poser` la compte ; aucune sans durée."""
    if not definition.duree_jours:
        return None
    return tick + definition.duree_jours // _constantes.TICK_DURATION_DAYS


def poser_les_famines(monde, affames, donnees=None) -> list:
    """Au tick courant : pose la famine au lieu dont la faim dépasse le seuil du secours, la prolonge sinon.

    `affames` : les lieux `(cell_id, rang)` dont la population est positive, la
    pénurie aussi et la faim déjà comptée. Un lieu qui porte la famine voit sa
    fin repoussée de sa durée entière, son début restant celui du premier jour ;
    un lieu qui n'en porte pas la reçoit quand sa faim dépasse
    `FAIM_AVANT_SECOURS_JOURS` ; un lieu qui a faim depuis moins longtemps n'a
    rien. Rend les lieux où une famine commence. Les données ne se lisent que
    si une pose se fait ou se prolonge.
    """
    if not affames:
        return []
    t = monde.ticks_ecoules
    seuil = _constantes.FAIM_AVANT_SECOURS_JOURS
    jour = _constantes.TICK_DURATION_DAYS
    commencent = []
    for cid, rang in sorted(affames):
        i = _famine_du_lieu(monde, ("lieu", cid, rang))
        if i is None and _lieu(monde, cid, rang).duree_faim_ticks * jour <= seuil:
            continue
        donnees = _modificateurs.charger_donnees() if donnees is None else donnees
        if i is not None:
            poses = list(monde.modificateurs)
            poses[i] = dataclasses.replace(poses[i], fin=_fin(donnees.definitions[IDENTIFIANT_FAMINE], t))
            monde.modificateurs = poses
        else:
            _modificateurs.poser(monde, IDENTIFIANT_FAMINE, SOURCE_FAMINE, {"lieu": [cid, rang]}, donnees)
            commencent.append((cid, rang))
    return commencent
