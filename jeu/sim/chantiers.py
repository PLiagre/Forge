"""Journées de route, parcelle puis bâtiment : des paysans deviennent ouvriers."""

from dataclasses import replace
import math

import sim.constants as _constantes
from sim.flux import jour_courant
from sim.foyers import ranger_en_foyers
from sim.model import (ecrire_habitants_par_metier, lire_habitants_par_metier,
                       ecrire_stock_marchandise, contenus_des_paniers,
                       ecrire_ouvriers_du_jour, lire_ouvriers_du_jour)
from sim.plan import Batiment, Plan, aire_du_contour


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


def travail_requis_de_enceinte(contour):
    """Périmètre bouclé, dernier point relié au premier, converti en journées."""
    longueur = sum(math.dist(a, b) for a, b in zip(contour, (*contour[1:], contour[0])))
    return max(1, math.ceil(longueur * _constantes.TRAVAIL_ENCEINTE_JOURNEES_PAR_M))


def _ouvrir_maisons(plan, metiers, bourg):
    """Réserve les places avant l'affectation, parcelles prêtes seulement."""
    if metiers is None or bourg is None or bourg.maitre is None or not metiers.get(_constantes.METIER_ARTISANS, 0):
        return plan
    occupees = {b.parcelle for b in plan.batiments}
    libres = [p for p in plan.parcelles if not p.en_chantier and p.identifiant not in occupees]
    if not libres or _constantes.MAISONS_OUVERTES_PAR_JOUR <= 0:
        return plan
    besoin = ranger_en_foyers(metiers.get(_constantes.METIER_ARTISANS, 0)).nombre - sum(
        max(1, int(aire_du_contour(b.emprise) // _constantes.SURFACE_M2_PAR_FOYER_LOGE))
        for b in plan.batiments if b.nature == "maison")
    maisons = list(plan.batiments)
    identifiant = max((b.identifiant for b in maisons), default=-1) + 1
    restantes = _constantes.MAISONS_OUVERTES_PAR_JOUR
    for parcelle in sorted(libres, key=lambda p: p.identifiant):
        if besoin <= 0 or restantes <= 0:
            break
        maisons.append(Batiment(identifiant, parcelle.identifiant, "maison", parcelle.contour,
                                True, 1, travail_requis_de_batiment(parcelle.contour), autoconstruction=True))
        besoin -= max(1, int(aire_du_contour(parcelle.contour) // _constantes.SURFACE_M2_PAR_FOYER_LOGE))
        identifiant += 1
        restantes -= 1
    return Plan(rues=plan.rues, parcelles=plan.parcelles, batiments=maisons,
                enceinte=plan.enceinte) if maisons != plan.batiments else plan


def _servir(element, metiers, payables, autonome=False):
    """Prend les bras restants et compte une journée par personne envoyée."""
    paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
    if autonome:
        paysans, ouvriers = _constantes.METIER_ARTISANS, _constantes.METIER_AUTOCONSTRUCTEURS
    personnes = 0 if metiers is None else min(
        payables, (1 if autonome else element.foyers * _constantes.TAILLE_FOYER),
        element.travail_requis - element.travail_fourni, metiers.get(paysans, 0))
    if personnes:
        metiers[paysans] -= personnes
        if metiers[paysans] == 0:
            del metiers[paysans]
        metiers[ouvriers] = metiers.get(ouvriers, 0) + personnes
        fourni = element.travail_fourni + personnes
        element = replace(element, travail_fourni=fourni, en_chantier=fourni < element.travail_requis)
    return element, personnes


def _reserves(cell, bourg):
    """Bourg, puis les autres lieux du même maître, par rang croissant."""
    if bourg is None or bourg.maitre is None:
        return []
    return [bourg, *sorted(
        (lieu for lieu in cell.lieux if lieu.rang != 0 and lieu.maitre == bourg.maitre),
        key=lambda lieu: lieu.rang)]


def _disponible(lieu, cell, metiers):
    """Paysans encore prenables : au bourg, hors des métiers non agricoles."""
    if lieu.rang != 0:
        return max(0, lieu.population - lire_ouvriers_du_jour(lieu))
    ailleurs = sum(lire_ouvriers_du_jour(autre) for autre in cell.lieux if autre.rang != 0)
    ici = metiers.get(_constantes.METIER_OUVRIERS, 0) - ailleurs
    if ici < 0:
        ici = 0
    autres = sum(nombre for nom, nombre in metiers.items()
                 if nom != _constantes.METIER_PAYSANS and nom != _constantes.METIER_OUVRIERS)
    # Un montage direct peut laisser des paysans cellulaires hors des lieux :
    # ils restent au bourg, comme les métiers non agricoles.
    hors_lieux = cell.population - sum(autre.population for autre in cell.lieux)
    if hors_lieux < 0:
        hors_lieux = 0
    return max(0, lieu.population + hors_lieux - autres - ici)


def _puiser(element, metiers, payables, cell, reserves):
    """Prend au bourg puis aux lieux admissibles, et note chaque origine."""
    paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
    quota = min(payables, element.foyers * _constantes.TAILLE_FOYER,
                element.travail_requis - element.travail_fourni, metiers.get(paysans, 0))
    prises, reste = [], quota
    for lieu in reserves:
        if reste <= 0:
            break
        peut = min(reste, _disponible(lieu, cell, metiers))
        if peut:
            prises.append((lieu, peut))
            reste -= peut
    personnes = quota - reste
    if personnes:
        for lieu, peut in prises:
            ecrire_ouvriers_du_jour(lieu, lire_ouvriers_du_jour(lieu) + peut)
        metiers[paysans] -= personnes
        if metiers[paysans] == 0:
            del metiers[paysans]
        metiers[ouvriers] = metiers.get(ouvriers, 0) + personnes
        fourni = element.travail_fourni + personnes
        element = replace(element, travail_fourni=fourni, en_chantier=fourni < element.travail_requis)
    return element, personnes, {lieu.rang: peut for lieu, peut in prises}


def _bras_admissibles(metiers, origine, autonome, cell, reserves):
    if metiers is None:
        return 0
    stock = metiers.get(origine, 0)
    if autonome or not reserves:
        return stock
    return min(stock, sum(_disponible(lieu, cell, metiers) for lieu in reserves))


def avancer_chantiers(world):
    """Retour aux champs, rues, parcelles puis bâtiments prêts, par identifiant."""
    envois = {}
    world.chantiers_du_jour = {}
    world.origines_des_chantiers = {}
    world.recolte_perdue_par_chantier = {}
    for cell_id in sorted(world.cells):
        cell, plan = world.cells[cell_id], world.plans[cell_id]
        # Le compte de la veille s'efface avant toute sortie, métiers calculés ou non.
        for lieu in cell.lieux:
            ecrire_ouvriers_du_jour(lieu, 0)
        avant = lire_habitants_par_metier(cell)
        paysans, ouvriers = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
        actifs = any(e.en_chantier for nom in ("rues", "parcelles", "batiments") for e in getattr(plan, nom))
        familiaux = _constantes.METIER_AUTOCONSTRUCTEURS
        ouvre_maisons = (
            avant != -1
            and avant.get(_constantes.METIER_ARTISANS, 0)
            and _constantes.MAISONS_OUVERTES_PAR_JOUR > 0
        )
        # Un plan achevé ne demande que le retour des derniers ouvriers, sauf autoconstruction ou maisons.
        if not actifs and (
            avant == -1
            or (
                ouvriers not in avant
                and not avant.get(familiaux, 0)
                and not ouvre_maisons
            )
        ):
            continue
        metiers = avant.copy() if avant != -1 else None
        if metiers is not None and ouvriers in metiers:
            metiers[paysans] = metiers.get(paysans, 0) + metiers.pop(ouvriers)
        if metiers is not None and familiaux in metiers:
            artisans = _constantes.METIER_ARTISANS
            metiers[artisans] = metiers.get(artisans, 0) + metiers.pop(familiaux)
        besoin_bourg = actifs or ouvre_maisons
        bourg = next((lieu for lieu in cell.lieux if lieu.rang == 0), None) if besoin_bourg else None
        plan = _ouvrir_maisons(plan, metiers, bourg)
        # Les bras reviennent même si le dernier chantier est achevé.
        if not any(e.en_chantier for nom in ("rues", "parcelles", "batiments") for e in getattr(plan, nom)):
            if metiers is not None and metiers != avant:
                ecrire_habitants_par_metier(cell, metiers)
            continue
        grenier = world.greniers.get(bourg.maitre) if bourg is not None and bourg.maitre is not None else None
        nourriture, salaire = _constantes.MARCHANDISE_NOURRITURE, _constantes.SALAIRE_JOURNEE_KG
        payables = math.floor(grenier.get(nourriture, 0) / salaire) if grenier is not None else 0
        reserves = _reserves(cell, bourg) if metiers is not None else []
        listes, journees = {}, 0
        parcelles_en_chantier = {p.identifiant for p in plan.parcelles if p.en_chantier}
        for nom, cle in (("rues", ()), ("parcelles", ("parcelle",)), ("batiments", ("batiment",))):
            listes[nom] = []
            for element in sorted(getattr(plan, nom), key=lambda element: element.identifiant):
                if element.en_chantier:
                    autonome = nom == "batiments" and element.autoconstruction
                    origine = _constantes.METIER_ARTISANS if autonome else paysans
                    attend = nom == "batiments" and element.parcelle in parcelles_en_chantier
                    admissibles = _bras_admissibles(metiers, origine, autonome, cell, reserves)
                    motif = ("parcelle_en_chantier" if attend else
                             "metiers_non_calcules" if metiers is None else
                             "sans_bras" if not admissibles or autonome else
                             "payeur_absent" if grenier is None else "sans_grain")
                    origines = {}
                    if attend:
                        personnes = 0
                    elif autonome or metiers is None or not reserves:
                        element, personnes = _servir(element, metiers, 1 if autonome else payables - journees, autonome)
                    else:
                        element, personnes, origines = _puiser(
                            element, metiers, payables - journees, cell, reserves)
                    cle_chantier = (cell_id, *cle, element.identifiant)
                    envois[cle_chantier] = personnes
                    world.chantiers_du_jour[cle_chantier] = {
                        "bras": personnes, "grain_paye_kg": 0 if autonome else personnes * salaire,
                        "motif_arret": None if personnes else motif,
                    }
                    if origines and not autonome:
                        world.origines_des_chantiers[cle_chantier] = origines
                    journees += 0 if autonome else personnes
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
        if plan is not world.plans[cell_id] or any(listes[nom] != getattr(plan, nom) for nom in listes):
            world.plans[cell_id] = Plan(rues=listes["rues"], parcelles=listes["parcelles"],
                                       batiments=listes["batiments"], enceinte=plan.enceinte)
    return envois
