"""Le registre des lots, et le branchement de l'intégration.

Le registre a **un** lecteur : celui de ForgeAtelier. Ce fichier ne le
réécrit pas, il l'appelle — deux analyseurs du même format finiraient
par ne pas dire la même chose du même fichier, et c'est le genre de
désaccord qu'on découvre le jour où il coûte cher.

S'il est hors de portée, on le dit et on s'arrête. On ne devine pas.
"""

from __future__ import annotations

from pathlib import Path
import tomllib

# Ce que `[integration]` doit nommer. Rien n'a de valeur par défaut :
# une liste de contrôles devinée serait une porte qu'on ne se souvient
# pas d'avoir ouverte.
CLES = ("controles", "branches")

# Ce que `[tableau]` doit nommer. Mêmes règles : rien n'a de valeur par
# défaut. Un seuil écrit dans le code est un réglage que personne ne
# relit, et celui-ci décide de ce que le propriétaire voit en premier.
CLES_TABLEAU = (
    "tours_sans_fusion",
    "brouillon_jours",
    "journal",
    "semaines",
    "executions",
    "historique",
)


class AtelierAbsent(RuntimeError):
    pass


class BranchementIncomplet(ValueError):
    pass


def atelier():
    """Le module `feuille` de l'atelier, ou un refus qui dit quoi faire."""
    try:
        from atelier import feuille
    except ModuleNotFoundError as exc:
        raise AtelierAbsent(
            "ForgeAtelier n'est pas sur le PYTHONPATH : le registre des lots ne se "
            "lit que par lui. Voir docs/WORKFLOW.md § « L'atelier »."
        ) from exc
    return feuille


def feuille(racine: Path):
    """Le registre du produit, tel que l'atelier le lit."""
    projet = branchement(racine)
    if not projet["feuille"]:
        raise BranchementIncomplet(
            "atelier.toml ne nomme pas [projet].feuille : le registre des lots "
            "ne se cherche pas au hasard"
        )
    return atelier().lire(Path(racine) / projet["feuille"])


def _brut(racine: Path) -> dict:
    fichier = Path(racine) / "atelier.toml"
    if not fichier.is_file():
        raise BranchementIncomplet(f"atelier.toml introuvable : {fichier}")
    with fichier.open("rb") as fh:
        return tomllib.load(fh)


def branchement(racine: Path) -> dict:
    """`[projet]` du branchement : où vit le registre, où arrivent les PR."""
    projet = _brut(racine).get("projet", {})
    return {
        "feuille": projet.get("feuille"),
        "base": projet.get("branche_base", "master"),
        "briefs": projet.get("briefs", "briefs"),
    }


def integration(racine: Path) -> dict:
    """`[integration]` : ce qui gouverne l'entrée dans la branche de base.

    C'est un réglage du **produit**, pas du workflow : la liste des
    contrôles requis se lit dans le dépôt, en clair, dans le même fichier
    que le reste du branchement — pas dans une case d'options que personne
    ne relit jamais.
    """
    bloc = _brut(racine).get("integration")
    if bloc is None:
        raise BranchementIncomplet(
            "atelier.toml ne porte pas de section [integration] : "
            "l'intégration ne devine ni les contrôles requis ni les branches "
            f"qu'elle fusionne (attendu : {', '.join(CLES)})"
        )
    manquants = [cle for cle in CLES if not bloc.get(cle)]
    if manquants:
        raise BranchementIncomplet(
            f"[integration] incomplet, champs vides : {', '.join(manquants)}"
        )
    return {
        "controles": tuple(str(c) for c in bloc["controles"]),
        "branches": tuple(str(b) for b in bloc["branches"]),
    }


def tableau(racine: Path) -> dict:
    """`[tableau]` : les seuils et les fenêtres de la page de pilotage.

    Ils vivent dans le branchement, en clair, pour la même raison que la
    liste des contrôles : un réglage qui ne vit que dans le code ne se
    change pas — il se recommit. Et un seuil qu'on ne change pas est un
    seuil qui finit par ne plus rien vouloir dire.
    """
    bloc = _brut(racine).get("tableau")
    if bloc is None:
        raise BranchementIncomplet(
            "atelier.toml ne porte pas de section [tableau] : la page de pilotage "
            "ne devine ni ses seuils ni ses fenêtres "
            f"(attendu : {', '.join(CLES_TABLEAU)})"
        )
    manquants = [cle for cle in CLES_TABLEAU if bloc.get(cle) is None]
    if manquants:
        raise BranchementIncomplet(
            f"[tableau] incomplet, champs absents : {', '.join(manquants)}"
        )
    negatifs = [cle for cle in CLES_TABLEAU if int(bloc[cle]) <= 0]
    if negatifs:
        raise BranchementIncomplet(
            f"[tableau] : {', '.join(negatifs)} doit être un nombre positif — "
            "un seuil nul alerterait toujours, une fenêtre nulle ne mesurerait rien"
        )
    return {cle: int(bloc[cle]) for cle in CLES_TABLEAU}
