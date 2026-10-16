"""Journées de route, parcelle puis bâtiment : des paysans deviennent ouvriers."""

from dataclasses import replace
import math

import sim.constants as _constantes
from sim.flux import jour_courant
from sim.model import (ecrire_habitants_par_metier, lire_habitants_par_metier,
                       ecrire_stock_marchandise, contenus_des_paniers)
from sim.plan import Plan, aire_du_contour


def travail_requis_de_route(points, largeur_m):
    """Somme des segments en mètres, puis surface convertie en journées."""
    longueur = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    return max(1, math.ceil(longueur * largeur_m * _constantes.TRAVAIL_ROUTE_JOURNEES_PAR_M2))


def travail_requis_de_parcelle(facade_m, profondeur_m):
    """Surface exacte du rectangle convertie en journées de préparation du lot."""
    return max(1, math.ceil(facade_m * profondeur_m * _constantes.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))


def travail_requis_de_batiment(emprise):
    """Surface de l’emprise convertie en journées de construction."""
    return max(1, math.ceil(aire_du_contour(emprise) * _constantes.TRAVAIL_BATIMENT_JOURNEES_PAR_M2))


def _servir(element, metiers, payables):
    """Prend les bras restants et compte une journée par personne envoyée."""
    paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
    personnes = 0 if metiers is None else min(
        payables, element.foyers * _constantes.TAILLE_FOYER,
        element.travail_requis - element.travail_fourni, metiers.get(paysans, 0))
    if personnes:
        metiers[paysans] -= personnes
        if metiers[paysans] == 0:
            del metiers[paysans]
        metiers[ouvriers] = metiers.get(ouvriers, 0) + personnes
        fourni = element.travail_fourni + personnes
        element = replace(element, travail_fourni=fourni, en_chantier=fourni < element.travail_requis)
    return element, personnes


def avancer_chantiers(world):
    """Retour aux champs, rues, parcelles puis bâtiments prêts, par identifiant."""
    envois = {}
    world.chantiers_du_jour = {}
    for cell_id in sorted(world.cells):
        cell, plan = world.cells[cell_id], world.plans[cell_id]
        avant = lire_habitants_par_metier(cell)
        metiers = dict(avant) if avant != -1 else None
        paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
        if metiers is not None and ouvriers in metiers:
            metiers[paysans] = metiers.get(paysans, 0) + metiers.pop(ouvriers)
        actifs = any(e.en_chantier for nom in ("rues", "parcelles", "batiments") for e in getattr(plan, nom))
        bourg = next((lieu for lieu in cell.lieux if lieu.rang == 0), None) if actifs else None
        grenier = world.greniers.get(bourg.maitre) if bourg is not None and bourg.maitre is not None else None
        nourriture, salaire = _constantes.MARCHANDISE_NOURRITURE, _constantes.SALAIRE_JOURNEE_KG
        payables = math.floor(grenier.get(nourriture, 0) / salaire) if grenier is not None else 0
        listes, journees = {}, 0
        parcelles_en_chantier = {p.identifiant for p in plan.parcelles if p.en_chantier}
        for nom, cle in (("rues", ()), ("parcelles", ("parcelle",)), ("batiments", ("batiment",))):
            listes[nom] = []
            for element in sorted(getattr(plan, nom), key=lambda element: element.identifiant):
                if element.en_chantier:
                    attend = nom == "batiments" and element.parcelle in parcelles_en_chantier
                    motif = ("parcelle_en_chantier" if attend else
                             "metiers_non_calcules" if metiers is None else
                             "sans_bras" if not metiers.get(paysans, 0) else
                             "payeur_absent" if grenier is None else "sans_grain")
                    if attend:
                        personnes = 0
                    else:
                        element, personnes = _servir(element, metiers, payables - journees)
                    envois[(cell_id, *cle, element.identifiant)] = personnes
                    world.chantiers_du_jour[(cell_id, *cle, element.identifiant)] = {
                        "bras": personnes, "grain_paye_kg": personnes * salaire,
                        "motif_arret": None if personnes else motif,
                    }
                    journees += personnes
                listes[nom].append(element)
        if metiers is not None and metiers != avant:
            ecrire_habitants_par_metier(cell, metiers)
        if journees:
            montant = journees * salaire
            grenier[nourriture] -= montant
            jour = jour_courant(world)
            if jour is not None:
                jour.salaires[bourg.maitre] = jour.salaires.get(bourg.maitre, 0) + montant
            for entite in (bourg, cell):
                stock = contenus_des_paniers((entite,), nourriture)[0]
                ecrire_stock_marchandise(entite, nourriture, stock + montant)
            world.plans[cell_id] = Plan(rues=listes["rues"], parcelles=listes["parcelles"],
                                       batiments=listes["batiments"])
    return envois
