"""Dépôt des intentions du joueur, appliquées seulement au tick suivant."""

from dataclasses import dataclass
import math

import sim.constants as _constantes
from sim import flux as _flux
import sim.ville1400 as _ville1400
from sim.chantiers import travail_requis_de_batiment, travail_requis_de_enceinte, travail_requis_de_parcelle, travail_requis_de_route
from sim.plan import Batiment, Enceinte, Parcelle, Plan, PlanInvalide, Rue, _points
from sim.puissances import PuissanceInvalide
from sim.lieux import partager
from sim.seigneuries import cellule_du_siege, charger_seigneuries, identifiant_de_seigneurie

TYPE_CHOISIR_DEPART = "choisir_depart"
TYPE_FIXER_PART = "fixer_part"
TYPE_OUVRIR_GRENIER = "ouvrir_grenier"
TYPE_TRACER_ROUTE = "tracer_route"
TYPE_DECOUPER_PARCELLE = "decouper_parcelle"
TYPE_POSER_BATIMENT = "poser_batiment"
TYPE_TRACER_ENCEINTE = "tracer_enceinte"
NATURES_BATIMENT = ("maison", "scierie", "four")

CHAMPS_OBLIGATOIRES = {
    TYPE_OUVRIR_GRENIER: ("type", "maison", "kg"),
    TYPE_FIXER_PART: ("type", "maison", "part"),
    TYPE_TRACER_ROUTE: ("type", "cell", "points", "largeur_m", "maison"),
    TYPE_DECOUPER_PARCELLE: ("type", "cell", "rue", "segment", "debut_m", "facade_m", "profondeur_m", "cote", "maison"),
    TYPE_POSER_BATIMENT: ("type", "cell", "parcelle", "nature", "maison"),
    TYPE_TRACER_ENCEINTE: ("type", "cell", "points", "maison"),
}


class IntentionRefusee(ValueError):
    """Intention impossible à jouer, refusée avant toute mise en attente."""


@dataclass(frozen=True)
class ChoixDepart:
    identifiant: int

    def appliquer(self, monde):
        monde.maison_du_joueur = identifiant_de_seigneurie(self.identifiant)


@dataclass(frozen=True)
class FixerPart:
    maison: str
    part: int | float

    def appliquer(self, monde):
        monde.parts[self.maison] = self.part


def _lieux_de_la_maison(monde, maison, indice=None):
    """Relit l'index des routes, dans l'ordre de la table, sans registre."""
    routes = monde.routes_des_lieux
    if indice is None:
        indice = routes.noms.index(maison)
    return [(cid, rang, jours) for cid, rang, maitre_idx, jours in
            zip(routes.cids, routes.rangs, routes.maitre_idx, routes.jours)
            if maitre_idx == indice]


def _poids_des_lieux(monde, entrees):
    lieux = [monde.cells[cid].lieux[rang] for cid, rang, _ in entrees]
    dettes = [lieu.dette_alimentaire_kg for lieu in lieux]
    return dettes if any(dettes) else [lieu.population for lieu in lieux]


@dataclass(frozen=True)
class OuvrirGrenier:
    maison: str
    kg: int | float

    def appliquer(self, monde):
        nourriture = _constantes.MARCHANDISE_NOURRITURE
        panier = monde.greniers[self.maison]
        panier[nourriture] = panier.get(nourriture, 0.0) - self.kg
        indice = monde.routes_des_lieux.noms.index(self.maison)
        entrees = _lieux_de_la_maison(monde, self.maison, indice)
        parts = partager(self.kg, _poids_des_lieux(monde, entrees))
        jour = _flux.jour_courant(monde)
        if jour is not None:
            jour.rendu[indice] += self.kg
        for (cid, rang, jours), part in zip(entrees, parts):
            if part:
                arrivee = monde.ticks_ecoules + jours - 1
                charges = monde.secours.setdefault(arrivee, {})
                cle = (cid, rang)
                charges[cle] = charges.get(cle, 0.0) + part


def _ouvrir_grenier(monde, intention):
    maison, kg = intention["maison"], intention["kg"]
    if not isinstance(maison, str) or not any(m.id == maison for m in monde.maisons):
        raise IntentionRefusee(f"maison inconnue ou mal formée : {maison!r}")
    if maison not in getattr(monde.routes_des_lieux, "noms", ()):
        raise IntentionRefusee(f"maison sans lieu : {maison}")
    if (isinstance(kg, bool) or not isinstance(kg, (int, float))
            or (isinstance(kg, float) and not math.isfinite(kg)) or kg <= 0):
        raise IntentionRefusee(f"kg invalide : {kg!r}")
    reste = monde.greniers[maison].get(_constantes.MARCHANDISE_NOURRITURE, 0.0)
    for precedent in monde.intentions_en_attente:
        if isinstance(precedent, OuvrirGrenier) and precedent.maison == maison:
            reste -= precedent.kg
    if kg > reste:
        raise IntentionRefusee(f"grenier insuffisant : {kg} kg demandés, {reste} kg disponibles")
    if not any(_poids_des_lieux(monde, _lieux_de_la_maison(monde, maison))):
        raise IntentionRefusee(f"lieux sans dette ni habitants : {maison}")
    geste = OuvrirGrenier(maison, kg)
    monde.intentions_en_attente.append(geste)
    return geste


def _fixer_part(monde, intention):
    maison, part = intention["maison"], intention["part"]
    if not isinstance(maison, str) or not any(m.id == maison for m in monde.maisons):
        raise IntentionRefusee(f"maison inconnue ou mal formée : {maison!r}")
    if (isinstance(part, bool) or not isinstance(part, (int, float))
            or (isinstance(part, float) and not math.isfinite(part))
            or not 0 <= part <= _constantes.PART_MAXIMALE):
        raise IntentionRefusee(f"part invalide : attendu un nombre fini entre 0 et {_constantes.PART_MAXIMALE}")
    geste = FixerPart(maison, part)
    for rang, precedent in enumerate(monde.intentions_en_attente):
        if isinstance(precedent, FixerPart) and precedent.maison == maison:
            monde.intentions_en_attente[rang] = geste
            return geste
    monde.intentions_en_attente.append(geste)
    return geste


@dataclass(frozen=True)
class TraceRoute:
    cell_id: int
    points: tuple[tuple[float, float], ...]
    largeur_m: float
    foyers: int = 1
    porte_cell_id: int | None = None

    def appliquer(self, monde):
        """Ajoute la rue en chantier en reconstruisant et revalidant le plan."""
        plan = monde.plans[self.cell_id]
        identifiant = max((rue.identifiant for rue in plan.rues), default=-1) + 1
        rue = Rue(identifiant, self.points, self.largeur_m, en_chantier=True,
                  foyers=self.foyers,
                  travail_requis=travail_requis_de_route(self.points, self.largeur_m),
                  porte_cell_id=self.porte_cell_id)
        monde.plans[self.cell_id] = Plan(
            rues=[*plan.rues, rue], parcelles=plan.parcelles, batiments=plan.batiments,
            enceinte=plan.enceinte,
        )


@dataclass(frozen=True)
class DecoupeParcelle:
    cell_id: int
    contour: tuple[tuple[float, float], ...]
    facade_m: float
    profondeur_m: float
    foyers: int = 1

    def appliquer(self, monde):
        """Ajoute une parcelle en chantier, en relisant son coût à l’application."""
        plan = monde.plans[self.cell_id]
        identifiant = max((p.identifiant for p in plan.parcelles), default=-1) + 1
        parcelle = Parcelle(identifiant, self.contour, en_chantier=True,
                            foyers=self.foyers,
                            travail_requis=travail_requis_de_parcelle(self.facade_m, self.profondeur_m))
        monde.plans[self.cell_id] = Plan(
            rues=plan.rues, parcelles=[*plan.parcelles, parcelle], batiments=plan.batiments,
            enceinte=plan.enceinte,
        )


@dataclass(frozen=True)
class PoseBatiment:
    cell_id: int
    parcelle: int
    nature: str
    foyers: int = 1

    def appliquer(self, monde):
        """Relit l’emprise et le coût puis ajoute un bâtiment en chantier."""
        plan = monde.plans[self.cell_id]
        parcelle = next(p for p in plan.parcelles if p.identifiant == self.parcelle)
        emprise = tuple(tuple(point) for point in parcelle.contour)
        identifiant = max((b.identifiant for b in plan.batiments), default=-1) + 1
        batiment = Batiment(identifiant, self.parcelle, self.nature, emprise,
                            en_chantier=True, foyers=self.foyers,
                            travail_requis=travail_requis_de_batiment(emprise))
        monde.plans[self.cell_id] = Plan(
            rues=plan.rues, parcelles=plan.parcelles, batiments=[*plan.batiments, batiment],
            enceinte=plan.enceinte,
        )


@dataclass(frozen=True)
class TracerEnceinte:
    cell_id: int
    points: tuple[tuple[float, float], ...]
    foyers: int = 1
    def appliquer(self, monde):
        plan = monde.plans[self.cell_id]
        monde.plans[self.cell_id] = Plan(rues=plan.rues, parcelles=plan.parcelles, batiments=plan.batiments,
            enceinte=Enceinte(self.points, True, self.foyers, travail_requis_de_enceinte(self.points), 0))


def _foyers(intention):
    foyers = intention.get("foyers", 1)
    if isinstance(foyers, bool) or not isinstance(foyers, int) or foyers < 1:
        raise IntentionRefusee(f"foyers invalide : attendu un entier ≥ 1, reçu {foyers!r}")
    return foyers


def _cellule(monde, intention):
    cell_id = intention["cell"]
    if isinstance(cell_id, bool) or not isinstance(cell_id, int) or cell_id not in monde.plans:
        raise IntentionRefusee(f"cell inconnu : {cell_id!r}")
    return cell_id


def maitre_du_bourg(monde, cell_id):
    """Relit le maître actuel, sans déduire un droit de la puissance."""
    cellule = monde.cells.get(cell_id)
    if cellule is None:
        raise IntentionRefusee(f"cellule absente : {cell_id}")
    bourg = next((lieu for lieu in cellule.lieux if lieu.rang == 0), None)
    if bourg is None:
        raise IntentionRefusee(f"bourg absent : {cell_id}")
    maitre = bourg.maitre
    if not isinstance(maitre, str) or not any(m.id == maitre for m in monde.maisons):
        raise IntentionRefusee(f"maître absent ou inconnu : {maitre!r}")
    return maitre


def _verifier_terres(monde, intention):
    maison = intention["maison"]
    if not isinstance(maison, str) or not any(m.id == maison for m in monde.maisons):
        raise IntentionRefusee(f"maison inconnue ou mal formée : {maison!r}")
    maitre = maitre_du_bourg(monde, intention["cell"])
    if maison != maitre:
        raise IntentionRefusee(f"ce lieu n'est pas à toi : {maitre}")


def _decoupe_parcelle(monde, intention):
    cell_id = _cellule(monde, intention)
    identifiant = intention["rue"]
    rue = next((r for r in monde.plans[cell_id].rues if r.identifiant == identifiant), None)
    if isinstance(identifiant, bool) or not isinstance(identifiant, int) or rue is None:
        raise IntentionRefusee(f"rue absente du plan : {identifiant!r}")
    segment = intention["segment"]
    if (isinstance(segment, bool) or not isinstance(segment, int)
            or not 0 <= segment < len(rue.points) - 1):
        raise IntentionRefusee(f"segment hors de la rue : {segment!r}")
    for champ in ("debut_m", "facade_m", "profondeur_m"):
        valeur = intention[champ]
        if (isinstance(valeur, bool) or not isinstance(valeur, (int, float))
                or (isinstance(valeur, float) and not math.isfinite(valeur))
                or valeur < 0 or (champ != "debut_m" and valeur == 0)):
            raise IntentionRefusee(f"{champ} invalide : {valeur!r}")
    debut, facade, profondeur = (intention[c] for c in ("debut_m", "facade_m", "profondeur_m"))
    a, b = rue.points[segment], rue.points[segment + 1]
    longueur = math.dist(a, b)
    if debut + facade > longueur:
        raise IntentionRefusee(f"façade dépasse le segment : {debut} + {facade} > {longueur}")
    cote = intention["cote"]
    if cote not in ("gauche", "droite"):
        raise IntentionRefusee(f"cote invalide : {cote!r}")
    ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
    nx, ny = (-uy, ux) if cote == "gauche" else (uy, -ux)
    d = rue.largeur_m * _constantes.DEMI_LARGEUR_PAR_LARGEUR
    c0 = (a[0] + ux * debut + nx * d, a[1] + uy * debut + ny * d)
    c1 = (a[0] + ux * (debut + facade) + nx * d, a[1] + uy * (debut + facade) + ny * d)
    contour = (c0, c1, (c1[0] + nx * profondeur, c1[1] + ny * profondeur),
               (c0[0] + nx * profondeur, c0[1] + ny * profondeur))
    try:
        Parcelle(0, contour)
    except PlanInvalide as exc:
        raise IntentionRefusee(f"parcelle invalide : {exc}") from exc
    return DecoupeParcelle(cell_id, contour, facade, profondeur, _foyers(intention))


def _pose_batiment(monde, intention):
    cell_id = _cellule(monde, intention)
    identifiant = intention["parcelle"]
    plan = monde.plans[cell_id]
    if (isinstance(identifiant, bool) or not isinstance(identifiant, int)
            or not any(p.identifiant == identifiant for p in plan.parcelles)):
        raise IntentionRefusee(f"parcelle absente du plan : {identifiant!r}")
    if any(b.parcelle == identifiant for b in plan.batiments):
        raise IntentionRefusee(f"parcelle déjà bâtie : {identifiant}")
    if any(isinstance(p, PoseBatiment) and p.cell_id == cell_id and p.parcelle == identifiant
           for p in monde.intentions_en_attente):
        raise IntentionRefusee(f"parcelle déjà promise : {identifiant}")
    nature = intention["nature"]
    if nature not in NATURES_BATIMENT:
        raise IntentionRefusee(f"nature inconnue : {nature!r}")
    return PoseBatiment(cell_id, identifiant, nature, _foyers(intention))


def _cotes(points): return tuple((points[i], points[(i + 1) % len(points)]) for i in range(len(points)))
def _produit(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
def _sur(a, b, p): return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
def _touche(a, b, c, d):
    o1, o2, o3, o4 = _produit(a, b, c), _produit(a, b, d), _produit(c, d, a), _produit(c, d, b)
    return any(o == 0 and _sur(p, q, r) for o, p, q, r in ((o1, a, b, c), (o2, a, b, d), (o3, c, d, a), (o4, c, d, b))) or o1 * o2 < 0 and o3 * o4 < 0
def _se_croise(points):
    cotes, n = _cotes(points), len(points)
    return any(_touche(*cotes[i], *cotes[j]) for i in range(n) for j in range(i + 1, n) if min((i - j) % n, (j - i) % n) > 1)
def _dans(point, polygone, strict):
    if any(_produit(a, b, point) == 0 and _sur(a, b, point) for a, b in _cotes(polygone)):
        return not strict
    x, y, dedans = point[0], point[1], False
    for a, b in _cotes(polygone):
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            dedans = not dedans
    return dedans
def _emprises(points, largeur): return [_ville1400.emprise_de_rue((a, b), largeur) for a, b in _cotes(points) if a != b]
def _tracer_enceinte(monde, intention):
    foyers, cell_id, points = _foyers(intention), _cellule(monde, intention), intention["points"]
    try:
        _points(points, _constantes.POINTS_MIN_CONTOUR, "enceinte.contour")
    except PlanInvalide as exc:
        raise IntentionRefusee(str(exc)) from exc
    if _se_croise(points):
        raise IntentionRefusee("enceinte : contour qui se croise")
    try:
        base = _ville1400.base_de_cellule(monde, cell_id)
    except _ville1400.BaseAbsente as exc:
        raise IntentionRefusee(str(exc)) from exc
    place, cotes = base["place"], _cotes(points)
    if (any(_dans(p, place, False) or _dans(q, place, False) or any(_touche(p, q, a, b) for a, b in _cotes(place))
            for p, q in cotes) or not all(_dans(sommet, points, True) for sommet in place)):
        raise IntentionRefusee("enceinte : place de 1400 non entourée")
    rang = _ville1400.maison_touchee(base, _emprises(points, _constantes.ASSISE_ENCEINTE_M))
    if rang is not None:
        raise IntentionRefusee(f"cellule {cell_id} : maison de 1400 {rang} ({base['maisons'][rang]['foyers']} foyers) touchée")
    _verifier_terres(monde, intention)
    if monde.plans[cell_id].enceinte is not None:
        raise IntentionRefusee("enceinte déjà tracée")
    if any(isinstance(geste, TracerEnceinte) and geste.cell_id == cell_id for geste in monde.intentions_en_attente):
        raise IntentionRefusee("enceinte déjà promise")
    geste = TracerEnceinte(cell_id, tuple(tuple(point) for point in points), foyers)
    monde.intentions_en_attente.append(geste)
    return geste


def verifier_base(monde, cell_id, points=None, largeur_m=None, contour=None):
    """Garde commune du dépôt et de l'IA, sans cache ni écriture au monde."""
    if monde.populations_bourg_amorcage is None:
        return
    try:
        base = _ville1400.base_de_cellule(monde, cell_id)
    except _ville1400.BaseAbsente as exc:
        raise IntentionRefusee(str(exc)) from exc
    emprises = [contour] if contour is not None else [
        _ville1400.emprise_de_rue((a, b), largeur_m)
        for a, b in zip(points, points[1:]) if a != b]
    rang = _ville1400.maison_touchee(base, emprises)
    if rang is not None:
        foyers = base["maisons"][rang]["foyers"]
        raise IntentionRefusee(f"cellule {cell_id} : maison de 1400 {rang} ({foyers} foyers) touchée")


def recevoir_intention(monde, intention):
    """Point d'entrée commun : seuls les types connus peuvent être déposés."""
    type_intention = intention.get("type") if isinstance(intention, dict) else None
    if type_intention == TYPE_CHOISIR_DEPART:
        return deposer_intention(monde, intention)
    if isinstance(intention, dict) and "type" not in intention and "rue" in intention:
        raise IntentionRefusee("champ manquant : type")
    if type_intention not in tuple(CHAMPS_OBLIGATOIRES):
        raise IntentionRefusee(f"type d'intention inconnu : {type_intention!r}")
    champs = CHAMPS_OBLIGATOIRES[type_intention]
    for champ in champs:
        if champ not in intention:
            raise IntentionRefusee(f"champ manquant : {champ}")
    for champ in intention:
        if (champ not in champs and not (type_intention in (
                TYPE_TRACER_ROUTE, TYPE_DECOUPER_PARCELLE, TYPE_POSER_BATIMENT,
                TYPE_TRACER_ENCEINTE) and champ == "foyers")
                and not (type_intention == TYPE_TRACER_ROUTE and champ == "porte_cell_id")):
            raise IntentionRefusee(f"champ inconnu : {champ}")
    if type_intention == TYPE_FIXER_PART:
        return _fixer_part(monde, intention)
    if type_intention == TYPE_OUVRIR_GRENIER:
        return _ouvrir_grenier(monde, intention)
    if type_intention == TYPE_POSER_BATIMENT:
        pose = _pose_batiment(monde, intention)
        contour = next(p.contour for p in monde.plans[pose.cell_id].parcelles if p.identifiant == pose.parcelle)
        verifier_base(monde, pose.cell_id, contour=contour)
        _verifier_terres(monde, intention)
        monde.intentions_en_attente.append(pose)
        return pose
    if type_intention == TYPE_DECOUPER_PARCELLE:
        decoupe = _decoupe_parcelle(monde, intention)
        verifier_base(monde, decoupe.cell_id, contour=decoupe.contour)
        _verifier_terres(monde, intention)
        monde.intentions_en_attente.append(decoupe)
        return decoupe
    if type_intention == TYPE_TRACER_ENCEINTE:
        return _tracer_enceinte(monde, intention)
    foyers = _foyers(intention)
    cell_id = _cellule(monde, intention)
    try:
        rue = Rue(0, intention["points"], intention["largeur_m"],
                  porte_cell_id=intention.get("porte_cell_id"))
    except PlanInvalide as exc:
        raise IntentionRefusee(f"route invalide : {exc}") from exc
    porte = rue.porte_cell_id
    if porte is not None and (cell_id not in monde.cells or porte not in monde.cells
            or porte == cell_id or not any(
                (edge["a"] == cell_id and edge["b"] == porte)
                or (edge["b"] == cell_id and edge["a"] == porte) for edge in monde.adjacency)):
        raise IntentionRefusee(f"porte_cell_id : voisine terrestre attendue, reçu {porte!r}")
    route = TraceRoute(cell_id, tuple(tuple(point) for point in rue.points), rue.largeur_m, foyers, porte)
    verifier_base(monde, cell_id, points=route.points, largeur_m=route.largeur_m)
    _verifier_terres(monde, intention)
    monde.intentions_en_attente.append(route)
    return route


def deposer_intention(monde, intention, seigneuries=None) -> ChoixDepart:
    """Valide la terre et l'unicité du choix sans modifier le monde visible."""
    identifiant = intention.get("seigneurie")
    if isinstance(identifiant, bool) or not isinstance(identifiant, int):
        raise IntentionRefusee(f"seigneurie inconnue : {identifiant!r}")
    if seigneuries is None:
        seigneuries = charger_seigneuries()
    terre = next((s for s in seigneuries if s.id == identifiant), None)
    if terre is None:
        raise IntentionRefusee(f"seigneurie inconnue : {identifiant!r}")
    try:
        cellule_du_siege(terre, monde.carte)
    except PuissanceInvalide as exc:
        raise IntentionRefusee(str(exc)) from exc
    if not any(m.id == identifiant_de_seigneurie(identifiant) and m.sorte == "seigneurie"
               for m in monde.maisons):
        raise IntentionRefusee(f"seigneurie inconnue : {identifiant!r}")
    retenu = monde.maison_du_joueur
    if retenu is None:
        retenu = next((identifiant_de_seigneurie(choix.identifiant) for choix in monde.intentions_en_attente
                       if isinstance(choix, ChoixDepart)), None)
    if retenu is not None:
        raise IntentionRefusee(f"départ déjà choisi : {retenu}")
    choix = ChoixDepart(identifiant)
    monde.intentions_en_attente.append(choix)
    return choix
