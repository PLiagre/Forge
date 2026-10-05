"""Journées de route : des paysans deviennent ouvriers pour un seul tick."""

from dataclasses import replace
import math

import sim.constants as _constantes
from sim.model import ecrire_habitants_par_metier, lire_habitants_par_metier
from sim.plan import Plan


def travail_requis_de_route(points, largeur_m):
    """Somme des segments en mètres, puis surface convertie en journées."""
    longueur = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    return max(1, math.ceil(longueur * largeur_m * _constantes.TRAVAIL_ROUTE_JOURNEES_PAR_M2))


def avancer_chantiers(world):
    """Retour aux champs puis envoi aux rues les plus anciennes, sans aléa."""
    envois = {}
    for cell_id in sorted(world.cells):
        cell, plan = world.cells[cell_id], world.plans[cell_id]
        avant = lire_habitants_par_metier(cell)
        metiers = dict(avant) if avant != -1 else None
        paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
        if metiers is not None and ouvriers in metiers:
            metiers[paysans] = metiers.get(paysans, 0) + metiers.pop(ouvriers)
        rues, travail_apporte = [], False
        for rue in sorted(plan.rues, key=lambda rue: rue.identifiant):
            if rue.en_chantier:
                personnes = 0 if metiers is None else min(
                    rue.foyers * _constantes.TAILLE_FOYER,
                    rue.travail_requis - rue.travail_fourni, metiers.get(paysans, 0))
                envois[cell_id, rue.identifiant] = personnes
                if personnes:
                    metiers[paysans] -= personnes
                    if metiers[paysans] == 0:
                        del metiers[paysans]
                    metiers[ouvriers] = metiers.get(ouvriers, 0) + personnes
                    fourni = rue.travail_fourni + personnes
                    rue = replace(rue, travail_fourni=fourni, en_chantier=fourni < rue.travail_requis)
                    travail_apporte = True
            rues.append(rue)
        if metiers is not None and metiers != avant:
            ecrire_habitants_par_metier(cell, metiers)
        if travail_apporte:
            world.plans[cell_id] = Plan(rues=rues, parcelles=plan.parcelles, batiments=plan.batiments)
    return envois
