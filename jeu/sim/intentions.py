"""Dépôt des intentions du joueur, appliquées seulement au tick suivant."""

from dataclasses import dataclass

from sim.puissances import PuissanceInvalide
from sim.seigneuries import cellule_du_siege, charger_seigneuries

TYPE_CHOISIR_DEPART = "choisir_depart"


class IntentionRefusee(ValueError):
    """Intention impossible à jouer, refusée avant toute mise en attente."""


@dataclass(frozen=True)
class ChoixDepart:
    identifiant: int


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
