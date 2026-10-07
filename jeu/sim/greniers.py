"""Conservation des greniers : chaque maison perd une part de sa nourriture."""

import sim.constants as constantes


def part_perte_par_tick() -> float:
    """Part alimentaire retirée une fois par tick. Relit le taux et la base de temps."""
    return (
        constantes.PERTE_GRENIER_PAR_AN
        * constantes.TICK_DURATION_DAYS
        / constantes.CALENDAR_DAYS_PER_YEAR
    )


def appliquer_pertes_greniers(monde) -> None:
    """Retire S × p sur la nourriture. Sans grenier, n'en ajoute pas."""
    greniers = getattr(monde, "greniers", None)
    if not greniers:
        return
    nourriture = constantes.MARCHANDISE_NOURRITURE
    part = part_perte_par_tick()
    for identifiant in sorted(greniers):
        panier = greniers[identifiant]
        if nourriture not in panier:
            continue
        stock = panier[nourriture]
        retrait = stock * part
        if retrait == 0.0:
            continue
        panier[nourriture] = stock - retrait
        monde.pertes_kg += retrait
