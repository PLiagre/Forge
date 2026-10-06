"""Logement des artisans, dérivé du plan sans effet sur le monde."""

from sim import constants as _constantes
from sim.foyers import ranger_en_foyers
from sim.model import lire_habitants_par_metier
from sim.plan import aire_du_contour


def logement_de(cellule, plan):
    """Compte les places achevées et les foyers, sans conserver de donnée."""
    if not plan.batiments:
        return None
    capacite = sum(
        max(1, int(aire_du_contour(b.emprise) // _constantes.SURFACE_M2_PAR_FOYER_LOGE))
        for b in sorted(plan.batiments, key=lambda b: b.identifiant)
        if b.nature == "maison" and not b.en_chantier
    )
    metiers = lire_habitants_par_metier(cellule)
    if metiers == -1:
        return {"capacite": capacite, "loges": -1, "sans_logis": -1}
    foyers = ranger_en_foyers(metiers.get(_constantes.METIER_ARTISANS, 0)).nombre
    loges = min(foyers, capacite)
    return {"capacite": capacite, "loges": loges, "sans_logis": foyers - loges}
