"""Rangement réversible en foyers et répartition des habitants par métier."""

from dataclasses import dataclass

import sim.constants as _constantes


class FoyersInvalides(ValueError):
    """Un compte, une taille ou une déclaration de métiers est incohérent."""


def _entier(valeur, nom, minimum=0):
    if type(valeur) is not int or valeur < minimum:
        raise FoyersInvalides(f"{nom} doit être un entier ≥ {minimum}, reçu : {valeur!r}")


def valider_metiers(habitants_par_metier):
    """Refuse les métiers sans nom ou sans personne entière positive."""
    for metier, personnes in habitants_par_metier.items():
        if not isinstance(metier, str) or not metier.strip():
            raise FoyersInvalides("Le nom du métier manque ou est vide")
        _entier(personnes, f"Compte du métier {metier!r}", minimum=1)


@dataclass(frozen=True)
class Foyers:
    taille: int
    complets: int
    dernier: int

    def __post_init__(self):
        _entier(self.taille, "taille du foyer", minimum=1)
        _entier(self.complets, "Nombre de foyers complets")
        _entier(self.dernier, "Personnes du dernier foyer")
        if self.dernier >= self.taille:
            raise FoyersInvalides("Le dernier foyer doit être plus petit que la taille")

    @property
    def nombre(self):
        return self.complets + (1 if self.dernier > 0 else 0)


def ranger_en_foyers(personnes):
    """Relit la taille constante et conserve l'éventuel foyer incomplet."""
    _entier(personnes, "Nombre de personnes")
    taille = _constantes.TAILLE_FOYER
    _entier(taille, "taille du foyer", minimum=1)
    complets, dernier = divmod(personnes, taille)
    return Foyers(taille, complets, dernier)


def rendre_les_personnes(foyers):
    """Désagrège sans perdre les personnes du dernier foyer."""
    return foyers.complets * foyers.taille + foyers.dernier


def repartir(habitants_par_metier, population):
    """Répartit en entiers ; le métier majoritaire reçoit tout le reste."""
    _entier(population, "Population")
    valider_metiers(habitants_par_metier)
    somme = sum(habitants_par_metier.values())
    if population == somme:
        return dict(habitants_par_metier)
    if not habitants_par_metier:
        return {_constantes.METIER_PAYSANS: population} if population else {}
    parts = {metier: population * n // somme
             for metier, n in habitants_par_metier.items()}
    majoritaire = min(habitants_par_metier,
                      key=lambda metier: (-habitants_par_metier[metier], metier))
    parts[majoritaire] += population - sum(parts.values())
    return {metier: n for metier, n in parts.items() if n > 0}
