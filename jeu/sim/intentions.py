"""Dépôt des intentions du joueur, appliquées seulement au tick suivant."""

from dataclasses import dataclass

from sim.chantiers import travail_requis_de_route
from sim.plan import Plan, PlanInvalide, Rue
from sim.puissances import PuissanceInvalide
from sim.seigneuries import cellule_du_siege, charger_seigneuries

TYPE_CHOISIR_DEPART = "choisir_depart"
TYPE_TRACER_ROUTE = "tracer_route"


class IntentionRefusee(ValueError):
    """Intention impossible à jouer, refusée avant toute mise en attente."""


@dataclass(frozen=True)
class ChoixDepart:
    identifiant: int

    def appliquer(self, monde):
        monde.maison_du_joueur = self.identifiant


@dataclass(frozen=True)
class TraceRoute:
    cell_id: int
    points: tuple[tuple[float, float], ...]
    largeur_m: float
    foyers: int = 1

    def appliquer(self, monde):
        """Ajoute la rue en chantier en reconstruisant et revalidant le plan."""
        plan = monde.plans[self.cell_id]
        identifiant = max((rue.identifiant for rue in plan.rues), default=-1) + 1
        rue = Rue(identifiant, self.points, self.largeur_m, en_chantier=True,
                  foyers=self.foyers,
                  travail_requis=travail_requis_de_route(self.points, self.largeur_m))
        monde.plans[self.cell_id] = Plan(
            rues=[*plan.rues, rue], parcelles=plan.parcelles, batiments=plan.batiments,
        )


def recevoir_intention(monde, intention):
    """Point d'entrée commun : seuls les types connus peuvent être déposés."""
    type_intention = intention.get("type") if isinstance(intention, dict) else None
    if type_intention == TYPE_CHOISIR_DEPART:
        return deposer_intention(monde, intention)
    if type_intention != TYPE_TRACER_ROUTE:
        raise IntentionRefusee(f"type d'intention inconnu : {type_intention!r}")
    champs = ("type", "cell", "points", "largeur_m")
    for champ in champs:
        if champ not in intention:
            raise IntentionRefusee(f"champ manquant : {champ}")
    for champ in intention:
        if champ not in champs and champ != "foyers":
            raise IntentionRefusee(f"champ inconnu : {champ}")
    foyers = intention.get("foyers", 1)
    if isinstance(foyers, bool) or not isinstance(foyers, int) or foyers < 1:
        raise IntentionRefusee(f"foyers invalide : attendu un entier ≥ 1, reçu {foyers!r}")
    cell_id = intention["cell"]
    if isinstance(cell_id, bool) or not isinstance(cell_id, int) or cell_id not in monde.plans:
        raise IntentionRefusee(f"cell inconnu : {cell_id!r}")
    try:
        rue = Rue(0, intention["points"], intention["largeur_m"])
    except PlanInvalide as exc:
        raise IntentionRefusee(f"route invalide : {exc}") from exc
    route = TraceRoute(cell_id, tuple(tuple(point) for point in rue.points), rue.largeur_m, foyers)
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
    retenu = monde.maison_du_joueur
    if retenu is None:
        retenu = next((choix.identifiant for choix in monde.intentions_en_attente
                       if isinstance(choix, ChoixDepart)), None)
    if retenu is not None:
        raise IntentionRefusee(f"départ déjà choisi : {retenu}")
    choix = ChoixDepart(identifiant)
    monde.intentions_en_attente.append(choix)
    return choix
