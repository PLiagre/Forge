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


def metiers_d_amorcage(population, gisements):
    """Amorçage A : les mineurs suivent les gisements, les autres sont paysans."""
    _entier(population, "Population")
    mineurs = int(population * _constantes.part_miniere_de(
        gisements, _constantes.facteurs_richesse_extraction()
    ))
    return {metier: n for metier, n in (
        (_constantes.METIER_MINEURS, mineurs),
        (_constantes.METIER_PAYSANS, population - mineurs),
    ) if n > 0}


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


def au_prorata(n, habitants_par_metier):
    """Parts entières, puis une personne aux plus forts restes. Somme exacte `n`."""
    _entier(n, "Nombre de personnes")
    if n == 0:
        return {}
    if not habitants_par_metier or sum(habitants_par_metier.values()) <= 0:
        raise FoyersInvalides("Aucun métier pour répartir des personnes")
    somme = sum(habitants_par_metier.values())
    parts = {}
    for metier, compte in habitants_par_metier.items():
        quotient = n * compte // somme
        if quotient > 0:
            parts[metier] = quotient
    restant = n - sum(parts.values())
    ordre = sorted(
        habitants_par_metier,
        key=lambda metier: (-(n * habitants_par_metier[metier] % somme), metier),
    )
    for metier in ordre[:restant]:
        parts[metier] = parts.get(metier, 0) + 1
    return parts


def retirer(habitants_par_metier, n):
    """Retire `n` personnes au prorata. Un métier tombé à zéro disparaît."""
    _entier(n, "Retrait")
    if n == 0:
        return dict(habitants_par_metier)
    somme = sum(habitants_par_metier.values())
    if n > somme:
        raise FoyersInvalides(f"Retrait de {n} supérieur à la somme {somme}")
    parts = au_prorata(n, habitants_par_metier)
    return {
        metier: compte - parts.get(metier, 0)
        for metier, compte in habitants_par_metier.items()
        if compte > parts.get(metier, 0)
    }


def ajouter(habitants_par_metier, n):
    """Ajoute `n` personnes au prorata. Sans métier, ce sont des paysans."""
    _entier(n, "Ajout")
    if n == 0:
        return dict(habitants_par_metier)
    if not habitants_par_metier:
        return {_constantes.METIER_PAYSANS: n}
    resultat = dict(habitants_par_metier)
    for metier, part in au_prorata(n, habitants_par_metier).items():
        resultat[metier] = resultat[metier] + part
    return resultat
