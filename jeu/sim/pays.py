"""Le pays d'un seul tenant : une maison, ses lieux, ses vassaux, son suzerain et ses totaux.

Une vue dérivée (CAP.md, jalon 6, « Le pays se lit d'un seul tenant ») : rien
ne se stocke. Les lieux viennent de leur maître (porté par chaque lieu), les
vassaux du registre des maisons (`suzerain`), les récoltes de la fenêtre des
flux, les greniers de `World.greniers`, les chantiers des plans des bourgs.
Un lieu n'appartient qu'au pays de son maître et, au-dessus, à ceux de ses
suzerains : les pays sans suzerain se partagent tous les lieux tenus du monde,
chacun une fois.
"""
from sim import constants as _constantes
from sim.flux import _jours_de_fenetre


class PaysInconnu(KeyError):
    """Une maison absente du registre."""


def index_des_pays(monde):
    """Les lieux tenus par chaque maître, et les vassaux directs de chaque maison, triés."""
    tenus = {}
    for cid in sorted(monde.cells):
        for lieu in monde.cells[cid].lieux:
            if lieu.maitre is not None:
                tenus.setdefault(lieu.maitre, []).append((cid, lieu.rang))
    vassaux = {}
    for maison in sorted(monde.maisons, key=lambda m: m.id):
        if maison.suzerain is not None:
            vassaux.setdefault(maison.suzerain, []).append(maison.id)
    return tenus, vassaux


def _descendants(maison_id, vassaux):
    """Les vassaux à tous les degrés, en largeur, dans l'ordre des identifiants."""
    vus, file = [], list(vassaux.get(maison_id, ()))
    while file:
        suivant = file.pop(0)
        if suivant in vus:
            continue
        vus.append(suivant)
        file.extend(vassaux.get(suivant, ()))
    return vus


def _recoltes_30j(monde, lieux):
    """Le grain récolté sur ces lieux pendant la fenêtre des flux (trente jours)."""
    total = 0.0
    voulus = {}
    for cid, rang in lieux:
        voulus.setdefault(cid, []).append(rang)
    for jour in _jours_de_fenetre(monde):
        recoltes = jour.recoltes or {}
        for cid, rangs in voulus.items():
            parts = recoltes.get(cid)
            if parts:
                total += sum(parts[rang] for rang in rangs if rang < len(parts))
    return total


def _chantiers(monde, lieux):
    """Les ouvrages en chantier dans les bourgs que le pays tient."""
    bourgs = sorted({cid for cid, rang in lieux if rang == 0})
    compte = 0
    for cid in bourgs:
        plan = monde.plans.get(cid)
        if plan is None:
            continue
        compte += sum(o.en_chantier for o in (*plan.rues, *plan.parcelles, *plan.batiments))
        compte += int(plan.enceinte is not None and plan.enceinte.en_chantier)
    return compte


def pays(monde, maison_id, index=None) -> dict:
    """Le document du pays de `maison_id` au tick courant."""
    registre = {m.id: m for m in monde.maisons}
    maison = registre.get(maison_id)
    if maison is None:
        raise PaysInconnu(maison_id)
    tenus, vassaux = index_des_pays(monde) if index is None else index
    propres = list(tenus.get(maison_id, ()))
    descendants = _descendants(maison_id, vassaux)
    des_vassaux = sorted(cle for v in descendants for cle in tenus.get(v, ()))
    tous = sorted(propres + des_vassaux)
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    habitants = sum(monde.cells[cid].lieux[rang].population for cid, rang in tous)
    propres_habitants = sum(monde.cells[cid].lieux[rang].population for cid, rang in propres)
    grenier = monde.greniers.get(maison_id)
    return {
        "maison": {"id": maison.id, "nom": maison.nom, "sorte": maison.sorte},
        "suzerain": maison.suzerain,
        "vassaux": list(vassaux.get(maison_id, ())),
        "vassaux_tous": descendants,
        "lieux": [{"cell_id": cid, "rang": rang} for cid, rang in propres],
        "lieux_des_vassaux": [{"cell_id": cid, "rang": rang} for cid, rang in des_vassaux],
        "totaux": {
            "lieux": len(tous),
            "habitants": habitants,
            "habitants_propres": propres_habitants,
            "recolte_30j_kg": _recoltes_30j(monde, tous),
            "grenier_nourriture_kg": None if grenier is None else grenier.get(nourriture, 0.0),
            "greniers_des_vassaux_kg": sum(monde.greniers.get(v, {}).get(nourriture, 0.0) for v in descendants),
            "chantiers": _chantiers(monde, tous),
        },
        "absents": {} if grenier is not None else {"grenier": f"grenier absent pour la maison {maison_id}"},
        "tick": monde.ticks_ecoules,
    }


def pays_sans_suzerain(monde, index=None) -> list:
    """Les identifiants des maisons racines, triés."""
    return sorted(m.id for m in monde.maisons if m.suzerain is None)
