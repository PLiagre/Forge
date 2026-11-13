"""Les pays que le joueur peut prendre : une vue pure du registre et des maîtres de lieux.

Une maison est jouable si elle n'est pas une institution (république, Église,
ordre : elles élisent leur chef, #441) et si au moins un lieu du monde l'a pour
maître actuel. Rien ne s'écrit ici, rien ne se tire au hasard.
"""
import re

from sim.puissances import charger_table
from sim.seigneuries import numero_de_seigneurie

_RAISONS_DES_INSTITUTIONS = {
    "république": "une république élit ses magistrats",
    "Église": "l'Église élit ses prélats",
    "ordre": "un ordre élit son maître",
}


def _lieux_tenus(monde) -> dict:
    """Nombre de lieux dont chaque maison est maître actuel, relu sur les cellules."""
    tenus = {}
    for cellule in monde.cells.values():
        for lieu in cellule.lieux:
            if lieu.maitre is not None:
                tenus[lieu.maitre] = tenus.get(lieu.maitre, 0) + 1
    return tenus


def _raison_d_institution(maison, table):
    """La raison d'une institution (nature relue dans la table des puissances), sinon None."""
    if maison.sorte != "institution":
        return None
    trouve = re.fullmatch(r"institution-(\d+)", maison.id)
    nature = None
    if trouve is not None:
        nature = next((p.nature for p in table.puissances if p.id == int(trouve.group(1))), None)
    explication = _RAISONS_DES_INSTITUTIONS.get(nature)
    if explication is None:
        raise ValueError(f"institution {maison.id} ({maison.nom}) : nature inconnue : {nature!r}")
    return f"maison non jouable : {maison.id} ({maison.nom}), {explication}"


def raison_de_refus(monde, identifiant):
    """`None` si la maison est jouable, sinon la raison de son refus."""
    maison = None
    if isinstance(identifiant, str):
        maison = next((m for m in monde.maisons if m.id == identifiant), None)
    if maison is None:
        return f"maison inconnue ou mal formée : {identifiant!r}"
    raison = _raison_d_institution(maison, charger_table())
    if raison is not None:
        return raison
    if _lieux_tenus(monde).get(identifiant, 0) == 0:
        return f"maison sans lieu : {identifiant}"
    return None


_ORDRE_DES_SORTES = ("seigneurie", "grande maison")  # puis les petits seigneurs (`plausible`)


def _rang(maison):
    """Les six seigneuries de départ par numéro, puis les grandes maisons, puis les petits seigneurs."""
    rang = (_ORDRE_DES_SORTES.index(maison.sorte) if maison.sorte in _ORDRE_DES_SORTES
            else len(_ORDRE_DES_SORTES))
    if maison.sorte == "seigneurie":
        return (rang, numero_de_seigneurie(maison.id), "")
    return (rang, 0, maison.id)


def maisons_jouables(monde) -> list:
    """Les maisons jouables, dans l'ordre où le choix les propose."""
    tenus = _lieux_tenus(monde)
    table = charger_table()
    jouables = [m for m in monde.maisons
                if _raison_d_institution(m, table) is None and tenus.get(m.id, 0) > 0]
    return [{"id": m.id, "nom": m.nom, "sorte": m.sorte, "lieux": tenus[m.id]}
            for m in sorted(jouables, key=_rang)]
