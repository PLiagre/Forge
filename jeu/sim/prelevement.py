"""La récolte du maître voyage vers son grenier ; aucun aléa supplémentaire."""

import sim.constants as constantes
from sim.model import ecrire_stock_marchandise, lire_stock_marchandise


class GroupeArrivee:
    """Une charge dense par maison et un facteur de perte commun au groupe."""
    __slots__ = ("facteur", "total", "charges")

    def __init__(self, nombre):
        self.facteur = 1.0
        self.total = 0.0
        self.charges = [0.0] * nombre

    def __eq__(self, autre):
        """Deux groupes sont égaux si leurs charges et pertes sont identiques."""
        if not isinstance(autre, GroupeArrivee):
            return NotImplemented
        return (self.facteur == autre.facteur
                and self.total == autre.total
                and self.charges == autre.charges)


def charges_en_route(monde):
    """Charges courantes, triées par arrivée puis maison, sans arrondi."""
    noms = monde.routes_des_lieux.noms
    return [[nom, arrivee, kg * groupe.facteur]
            for arrivee, groupe in sorted(monde.convois.items())
            for nom, kg in sorted(zip(noms, groupe.charges)) if kg]


def _livrer_secours(monde, charges):
    """Le grain rejoint le lieu destinataire et sa cellule, quel que soit son maître."""
    nourriture = constantes.MARCHANDISE_NOURRITURE
    for (cid, rang), kg in charges.items():
        cellule = monde.cells[cid]
        lieu = cellule.lieux[rang]
        ecrire_stock_marchandise(lieu, nourriture,
                                lire_stock_marchandise(lieu, nourriture) + kg)
        ecrire_stock_marchandise(cellule, nourriture,
                                lire_stock_marchandise(cellule, nourriture) + kg)


def prelever(monde, recoltes) -> None:
    """Perd en route, livre les arrivées, puis retire la part de la récolte."""
    routes = getattr(monde, "routes_des_lieux", None)
    if not routes:
        return
    nourriture = constantes.MARCHANDISE_NOURRITURE
    garde = 1.0 - constantes.PERTE_CONVOI_PAR_JOUR
    tick = monde.ticks_ecoules
    if monde.secours:
        for charges in monde.secours.values():
            for cle, kg in charges.items():
                reste = kg * garde
                monde.mange_convois_kg += kg - reste
                charges[cle] = reste
        arrives_secours = monde.secours.pop(tick, None)
        if arrives_secours:
            _livrer_secours(monde, arrives_secours)
    convois = monde.convois
    # Groupe d'arrivée : facteur commun, total courant, charges nominales par maître.
    for groupe in convois.values():
        total = groupe.total
        reste = total * garde
        monde.mange_convois_kg += total - reste
        groupe.facteur *= garde
        groupe.total = reste
    arrives = convois.pop(tick, None)
    if arrives:
        facteur = arrives.facteur
        dus = monde.dus_des_vassaux.par_indice
        part_due = constantes.PART_DUE_AU_SUZERAIN
        for i, (nom, kg) in enumerate(zip(routes.noms, arrives.charges)):
            if kg:
                panier = monde.greniers[nom]
                entree = kg * facteur
                route_due = dus[i] if dus else None
                if route_due is not None and part_due:
                    indice, jours = route_due
                    du = entree * part_due
                    entree -= du
                    arrivee = tick + jours
                    groupe = convois.get(arrivee)
                    if groupe is None:
                        groupe = convois[arrivee] = GroupeArrivee(len(routes.noms))
                    groupe.charges[indice] += du / groupe.facteur
                    groupe.total += du
                panier[nourriture] = panier.get(nourriture, 0.0) + entree
    taux = [monde.parts[nom] for nom in routes.noms]
    groupes = [None] * (routes.jours_max + 1)
    charges = [None] * len(groupes)
    facteurs = [1.0] * len(groupes)
    ajouts = [0.0] * len(groupes)
    for cid, (indices, durees) in routes.par_cellule.items():
        recolte = recoltes.get(cid)
        if recolte is None:
            continue
        cellule = monde.cells[cid]
        lieux = cellule.lieux
        retire = 0.0
        for rang, indice in enumerate(indices):
            if indice < 0:
                continue
            kg = taux[indice] * recolte[rang]
            if not kg:
                continue
            lieu = lieux[rang]
            ecrire_stock_marchandise(lieu, nourriture,
                                    lire_stock_marchandise(lieu, nourriture) - kg)
            retire += kg
            jours = durees[rang]
            groupe = groupes[jours]
            if groupe is None:
                arrivee = tick + jours
                groupe = convois.get(arrivee)
                if groupe is None:
                    groupe = convois[arrivee] = GroupeArrivee(len(taux))
                groupes[jours] = groupe
                charges[jours] = groupe.charges
                facteurs[jours] = groupe.facteur
            ajouts[jours] += kg
            # Une arrivée reçoit des départs d'âges différents : défaire son facteur.
            charges[jours][indice] += kg / facteurs[jours]
        if retire:
            ecrire_stock_marchandise(cellule, nourriture,
                                    lire_stock_marchandise(cellule, nourriture) - retire)
    # Un seul ajout au total de chaque groupe, plutôt qu'une écriture par lieu.
    for jours, groupe in enumerate(groupes):
        if groupe is not None:
            groupe.total += ajouts[jours]
