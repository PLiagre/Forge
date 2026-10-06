"""Journées de route puis de parcelle : des paysans deviennent ouvriers au tick."""

from dataclasses import replace
import math

import sim.constants as _constantes
from sim.model import ecrire_habitants_par_metier, lire_habitants_par_metier
from sim.plan import Plan


def travail_requis_de_route(points, largeur_m):
    """Somme des segments en mètres, puis surface convertie en journées."""
    longueur = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    return max(1, math.ceil(longueur * largeur_m * _constantes.TRAVAIL_ROUTE_JOURNEES_PAR_M2))


def travail_requis_de_parcelle(facade_m, profondeur_m):
    """Surface exacte du rectangle convertie en journées de préparation du lot."""
    return max(1, math.ceil(facade_m * profondeur_m * _constantes.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))


def _servir(element, metiers):
    """Prend les bras restants et compte une journée par personne envoyée."""
    paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
    personnes = 0 if metiers is None else min(
        element.foyers * _constantes.TAILLE_FOYER,
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
    """Retour aux champs, rues par identifiant, puis parcelles, sans aléa."""
    envois = {}
    for cell_id in sorted(world.cells):
        cell, plan = world.cells[cell_id], world.plans[cell_id]
        avant = lire_habitants_par_metier(cell)
        metiers = dict(avant) if avant != -1 else None
        paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
        if metiers is not None and ouvriers in metiers:
            metiers[paysans] = metiers.get(paysans, 0) + metiers.pop(ouvriers)
        listes, travail_apporte = {}, False
        for nom, cle in (("rues", ()), ("parcelles", ("parcelle",))):
            listes[nom] = []
            for element in sorted(getattr(plan, nom), key=lambda element: element.identifiant):
                if element.en_chantier:
                    element, personnes = _servir(element, metiers)
                    envois[(cell_id, *cle, element.identifiant)] = personnes
                    travail_apporte = travail_apporte or personnes > 0
                listes[nom].append(element)
        if metiers is not None and metiers != avant:
            ecrire_habitants_par_metier(cell, metiers)
        if travail_apporte:
            world.plans[cell_id] = Plan(rues=listes["rues"], parcelles=listes["parcelles"],
                                       batiments=plan.batiments)
    return envois
