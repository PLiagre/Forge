"""Branchement d'un dépôt produit. L'atelier ne devine rien."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ProjetIncomplet(ValueError):
    """Un champ obligatoire manque : on refuse, on n'invente pas."""


@dataclass(frozen=True)
class Roles:
    ecriture: str
    execution: str
    controle: str

    def __post_init__(self) -> None:
        # La règle est : « celui qui a écrit le CODE ne dit pas s'il est
        # recevable ». Écrire un brief n'est pas écrire du code — un
        # même agent peut donc briefer le matin et relire le diff le
        # soir. Interdire `ecriture == controle` serait plus strict que
        # la règle, et forcerait le branchement à nommer un quatrième
        # abonnement que le propriétaire n'a pas.
        if self.execution == self.controle:
            raise ProjetIncomplet(
                "l'exécution et le contrôle ne peuvent pas être le même agent : "
                "celui qui a écrit le code ne dit pas s'il est recevable"
            )

    def vers_dict(self) -> dict[str, str]:
        return {
            "ecriture": self.ecriture,
            "execution": self.execution,
            "controle": self.controle,
        }


@dataclass(frozen=True)
class Projet:
    racine: Path
    nom: str
    briefs: Path
    tests: str
    fumee: str
    branche_base: str
    prefixe_branche: str
    roles: Roles
    # La feuille de route du produit, où vit le registre des lots. `None`
    # si le branchement ne la nomme pas : le pilote refuse alors de
    # décider, il ne cherche pas un ROADMAP.md au hasard.
    feuille: Path | None = None

    @property
    def etat_dir(self) -> Path:
        return self.racine / ".atelier"

    def feuille_ou_refus(self) -> Path:
        if self.feuille is None:
            raise ProjetIncomplet(
                "le branchement ne nomme pas [projet].feuille : l'atelier ne devine "
                "pas où vit le registre des lots (chez ForgeHistory : ROADMAP.md)"
            )
        return self.feuille

    def branche_du_lot(self, lot: str) -> str:
        """La branche du lot, dérivée de `[projet].prefixe_branche`. Jamais recopiée."""
        if not lot.strip():
            raise ProjetIncomplet("un lot vide n'a pas de branche : l'atelier ne la devine pas")
        return f"{self.prefixe_branche}{lot}"


def charger(racine: Path) -> Projet:
    racine = Path(racine).resolve()
    fichier = racine / "atelier.toml"
    if not fichier.is_file():
        raise ProjetIncomplet(f"atelier.toml introuvable : {fichier}")

    with fichier.open("rb") as fh:
        brut = tomllib.load(fh)

    try:
        bloc = brut["projet"]
        roles_brut = brut["roles"]
    except KeyError as exc:
        raise ProjetIncomplet(f"section manquante dans atelier.toml : {exc.args[0]}") from exc

    obligatoires = ("nom", "briefs", "tests", "fumee", "branche_base", "prefixe_branche")
    manquants = [cle for cle in obligatoires if not bloc.get(cle)]
    if manquants:
        raise ProjetIncomplet(f"projet incomplet, champs vides : {', '.join(manquants)}")

    roles_cles = ("ecriture", "execution", "controle")
    manquants_roles = [cle for cle in roles_cles if not roles_brut.get(cle)]
    if manquants_roles:
        raise ProjetIncomplet(
            f"rôles incomplets, champs vides : {', '.join(manquants_roles)}"
        )

    briefs = racine / str(bloc["briefs"])
    return Projet(
        racine=racine,
        nom=str(bloc["nom"]),
        briefs=briefs,
        tests=str(bloc["tests"]),
        fumee=str(bloc["fumee"]),
        branche_base=str(bloc["branche_base"]),
        prefixe_branche=str(bloc["prefixe_branche"]),
        roles=Roles(
            ecriture=str(roles_brut["ecriture"]),
            execution=str(roles_brut["execution"]),
            controle=str(roles_brut["controle"]),
        ),
        feuille=racine / str(bloc["feuille"]) if bloc.get("feuille") else None,
    )
