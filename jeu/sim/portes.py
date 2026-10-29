"""Portes de l'enceinte : ses croisements avec les rues, calculés à la lecture, jamais stockés."""

from fractions import Fraction
import math

import sim.constants as _constantes


class PorteSansRue(ValueError):
    """Une porte ne repose pas sur une rue connue, ou sort du mur ou de son axe."""


def _croisement(a, b, p, q):
    """Fraction t du côté [a, b] au point commun avec [p, q], ou None s'il n'y en a pas un seul."""
    dx, dy, ex, ey = b[0] - a[0], b[1] - a[1], q[0] - p[0], q[1] - p[1]
    denominateur = dx * ey - dy * ex
    if denominateur == 0:
        return None
    t = ((p[0] - a[0]) * ey - (p[1] - a[1]) * ex) / denominateur
    u = ((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / denominateur
    return t if 0 <= t <= 1 and 0 <= u <= 1 else None


def _segments(points):
    exacts = [(Fraction(x), Fraction(y)) for x, y in points]
    return [(a, b) for a, b in zip(exacts, exacts[1:]) if a != b]


def portes_de_l_enceinte(contour, rues_du_plan, rues_de_base):
    """Portes triées : un point par croisement du contour bouclé avec l'axe d'une rue."""
    sommets = [(Fraction(x), Fraction(y)) for x, y in contour]
    axes = [("plan", rue.identifiant, rue.largeur_m, _segments(rue.points)) for rue in rues_du_plan]
    axes += [("base", rang, rue["largeur_m"], _segments(rue["points"])) for rang, rue in enumerate(rues_de_base)]
    trouvees = {}
    for rang_cote, (a, b) in enumerate(zip(sommets, (*sommets[1:], sommets[0]))):
        for source, identifiant, largeur, segments in axes:
            for p, q in segments:
                t = _croisement(a, b, p, q)
                if t is None:
                    continue
                x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
                point = [round(float(x), _constantes.SNAPSHOT_FLOAT_DECIMALS),
                         round(float(y), _constantes.SNAPSHOT_FLOAT_DECIMALS)]
                cle = (source, identifiant, tuple(point))
                ordre = (rang_cote, t, source, identifiant)
                if cle not in trouvees or ordre < trouvees[cle][0]:
                    trouvees[cle] = (ordre, {"point": point, "rue": source,
                                             "identifiant": identifiant, "largeur_m": largeur})
    return [porte for _ordre, porte in sorted(trouvees.values(), key=lambda e: e[0])]


def _distance_a_la_ligne(point, sommets):
    mesures = []
    for a, b in zip(sommets, sommets[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        carre = dx * dx + dy * dy
        t = 0.0 if carre == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / carre))
        mesures.append(math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy))
    return min(mesures)


def controler_portes(contour, portes, rues_du_plan, rues_de_base):
    """Lève PorteSansRue, en nommant la porte, si l'une d'elles ne repose pas sur sa rue et le mur."""
    boucle = [*contour, contour[0]]
    for porte in portes:
        def refuser(raison):
            raise PorteSansRue(f"porte {porte!r} : {raison}")
        point, source, identifiant = (porte.get(cle) if isinstance(porte, dict) else None
                                      for cle in ("point", "rue", "identifiant"))
        if source == "plan":
            axes = [rue.points for rue in rues_du_plan if rue.identifiant == identifiant]
            if not axes:
                refuser("identifiant absent du plan")
        elif source == "base":
            if isinstance(identifiant, bool) or not isinstance(identifiant, int) or not 0 <= identifiant < len(rues_de_base):
                refuser("rang hors de la base")
            axes = [rues_de_base[identifiant]["points"]]
        else:
            refuser("source de rue inconnue")
        if (not isinstance(point, (list, tuple)) or len(point) != _constantes.COORDONNEES_PAR_POINT
                or not all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in point)):
            refuser("point (x, y) attendu")
        if _distance_a_la_ligne(point, axes[0]) > _constantes.TOLERANCE_CHEVAUCHEMENT_M:
            refuser("point loin de l'axe de sa rue")
        if _distance_a_la_ligne(point, boucle) > _constantes.TOLERANCE_CHEVAUCHEMENT_M:
            refuser("point hors du contour")
