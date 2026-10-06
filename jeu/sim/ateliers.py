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
        metiers = dict(avant) if avant != -1 else None
        paysans, artisans = _constantes.METIER_PAYSANS, _constantes.METIER_ARTISANS
        if metiers is not None and artisans in metiers:
            metiers[paysans] = metiers.get(paysans, 0) + metiers.pop(artisans)
        for batiment in sorted(world.plans[cell_id].batiments, key=lambda b: b.identifiant):
            if batiment.en_chantier or batiment.nature not in ("scierie", "four"):
                continue
            places = max(1, int(aire_du_contour(batiment.emprise) // _constantes.SURFACE_M2_PAR_FOYER_ARTISAN)) * _constantes.TAILLE_FOYER
            personnes = min(metiers.get(paysans, 0), places) if metiers is not None else 0
            affectations[(cell_id, batiment.identifiant)] = personnes
            if personnes:
                metiers[paysans] -= personnes
                metiers[artisans] = metiers.get(artisans, 0) + personnes
        if metiers is not None:
            metiers = {m: n for m, n in metiers.items() if n}
            if metiers != avant:
                ecrire_habitants_par_metier(cell, metiers)
    return affectations
