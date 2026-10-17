"""Les ateliers achevés prennent leurs artisans parmi les paysans de leur cellule."""

from sim import constants as _constantes
from sim.model import ecrire_habitants_par_metier, lire_habitants_par_metier
from sim.plan import aire_du_contour

def affecter_artisans(world):
    """Retour aux champs puis emploi par identifiant, sans changer le plan."""
    affectations = {}
    for cell_id in sorted(world.cells):
        cell = world.cells[cell_id]
        avant = lire_habitants_par_metier(cell)
        paysans, artisans = _constantes.METIER_PAYSANS, _constantes.METIER_ARTISANS
        disponibles = avant.get(paysans, 0) + avant.get(artisans, 0) if avant != -1 else 0
        employes = 0
        for batiment in sorted(world.plans[cell_id].batiments, key=lambda b: b.identifiant):
            if batiment.en_chantier or batiment.nature not in ("scierie", "four"):
                continue
            places = max(1, int(aire_du_contour(batiment.emprise) // _constantes.SURFACE_M2_PAR_FOYER_ARTISAN)) * _constantes.TAILLE_FOYER
            personnes = min(disponibles, places)
            affectations[(cell_id, batiment.identifiant)] = personnes
            disponibles -= personnes
            employes += personnes
        if avant != -1:
            # La lecture fournit déjà une copie ; ne reconstruire les métiers
            # que si l'emploi change, ou s'il reste des comptes nuls à retirer.
            if employes == avant.get(artisans, 0) and all(avant.values()):
                continue
            metiers = avant.copy()
            metiers[paysans], metiers[artisans] = disponibles, employes
            metiers = {m: n for m, n in metiers.items() if n}
            if metiers != avant:
                ecrire_habitants_par_metier(cell, metiers)
    return affectations
