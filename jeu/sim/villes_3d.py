"""Les capitales dont la ville est bâtie en 3D : un fait de la vue, déclaré en données."""

import dataclasses
import json
import pathlib

from sim.model import _NoBadSpatialField

_RACINE_DEPOT = pathlib.Path(__file__).parent.parent
_CHEMIN_VILLES = _RACINE_DEPOT / "data" / "villes-3d.json"
_CLE_VILLES = "villes"
_CLE_MAISON = "maison"
_CLE_SCENE = "scene"
_CLE_RAISON = "raison_sans_ville"
_CLE_SIEGE = "siege"
_CLE_BATIES = "baties"
_MARQUE_SIEGE = "{" + _CLE_SIEGE + "}"


class VilleEn3DInvalide(ValueError):
    """Levée quand la donnée des villes bâties en 3D est incomplète ou incohérente."""


@dataclasses.dataclass(frozen=True)
class VilleEn3D(_NoBadSpatialField):
    maison: str
    scene: str


@dataclasses.dataclass(frozen=True)
class VillesEn3D(_NoBadSpatialField):
    villes: tuple
    raison_sans_ville: str


def _texte(brute: dict, nom_entree: str, champ: str) -> str:
    valeur = brute.get(champ)
    if not isinstance(valeur, str) or not valeur.strip():
        raise VilleEn3DInvalide(f"ville {nom_entree}, champ {champ} : texte absent ou vide")
    return valeur


def _valider_raison(modele) -> str:
    if not isinstance(modele, str) or not modele.strip():
        raise VilleEn3DInvalide(f"champ {_CLE_RAISON} : texte absent ou vide")
    if _MARQUE_SIEGE not in modele:
        raise VilleEn3DInvalide(f"champ {_CLE_RAISON} : {_MARQUE_SIEGE} absent du modèle")
    try:
        modele.format(**{_CLE_SIEGE: _CLE_SIEGE, _CLE_BATIES: _CLE_BATIES})
    except (KeyError, IndexError, ValueError) as erreur:
        raise VilleEn3DInvalide(
            f"champ {_CLE_RAISON} : le modèle ne se formate qu'avec "
            f"{_CLE_SIEGE} et {_CLE_BATIES} ({erreur!r})"
        ) from erreur
    return modele


def charger_villes_3d(path=None) -> VillesEn3D:
    """Lit la donnée, la valide entièrement et rend les villes triées par maison.

    Le moteur ne vérifie pas que les scènes existent : il tourne sans le dossier 3d/.
    """
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_VILLES
    document = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise VilleEn3DInvalide("document : objet attendu")
    brutes = document.get(_CLE_VILLES)
    if not isinstance(brutes, list) or not brutes:
        raise VilleEn3DInvalide(f"champ {_CLE_VILLES} : liste absente ou vide")

    villes, vues = [], set()
    for rang, brute in enumerate(brutes, start=1):
        if not isinstance(brute, dict):
            raise VilleEn3DInvalide(f"ville de rang {rang} : objet attendu")
        maison_brute = brute.get(_CLE_MAISON)
        nom_entree = maison_brute if isinstance(maison_brute, str) and maison_brute.strip() else f"de rang {rang}"
        maison = _texte(brute, nom_entree, _CLE_MAISON)
        if maison in vues:
            raise VilleEn3DInvalide(f"ville {maison}, champ {_CLE_MAISON} : maison dupliquée")
        vues.add(maison)
        villes.append(VilleEn3D(maison, _texte(brute, nom_entree, _CLE_SCENE)))

    raison = _valider_raison(document.get(_CLE_RAISON))
    return VillesEn3D(tuple(sorted(villes, key=lambda v: v.maison)), raison)


def raison_sans_ville(villes: VillesEn3D, siege: str, baties: str) -> str:
    """Dit pourquoi la capitale de `siege` n'a pas de ville en 3D ; `baties` nomme les sièges bâtis."""
    return villes.raison_sans_ville.format(**{_CLE_SIEGE: siege, _CLE_BATIES: baties})
