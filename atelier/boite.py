"""Boîte aux lettres : chaque rôle prend une carte et s'arrête.

Personne n'attend personne. Si la boîte d'un rôle est vide, le cron
sort 0 avec `RIEN`. Un échec va dans `echec/`, il ne bloque pas
l'autre rôle.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys

from . import reprise, verrou


ROLES = ("briefer", "planifier", "coder", "relire")

# Ce que chaque rôle *lit*. Le planificateur est facultatif :
# le coder lit `a-coder`, pas la sortie du planificateur.
BOITE_DU_ROLE = {
    "briefer": "a-briefer",
    "planifier": "a-planifier",
    "coder": "a-coder",
    "relire": "a-relire",
}

# Le briefer écrit dans son propre worktree et ouvre une PR : le brief
# n'est sur master qu'une fois fusionné par le propriétaire. Sa carte
# ne va donc ni à a-planifier ni à a-coder — le coder ne trouverait pas
# le brief. Elle attend la fusion ; le pilote dépose ensuite la carte
# du coder d'après la feuille de route (`atelier piloter`).
SUIVANT = {
    "briefer": "brief-a-fusionner",
    "planifier": "a-coder",     # s'il passe, il enrichit la même file
    "coder": "a-relire",
    "relire": "faite",
}

# Ce qu'un rôle a le droit de changer en passant la carte au suivant.
# `lot` et `brief` n'y sont pas : le brief est la seule source
# d'instruction d'un lot, et une carte qui change de brief en fait une
# seconde.
CHAMPS_MODIFIABLES = ("pr", "note", "fichiers")

# Le seul rôle qui écrit du code. Les autres relisent ou rédigent : un
# verrou de fichiers ne les suspend pas.
ROLE_QUI_ECRIT = "coder"


class BoiteErreur(ValueError):
    pass


class CarteIllisible(BoiteErreur):
    """Le fichier n'est pas du JSON. Ce n'est pas une carte qui dit faux.

    La distinction porte : une carte vide ou incomplète *dit* quelque
    chose de faux, et un échantillon vide échoue — la file s'arrête et
    on répare. Un fichier tronqué ou corrompu ne dit rien du tout ; le
    garder en tête de file prendrait les cartes saines en otage.
    """


@dataclass(frozen=True)
class Carte:
    lot: str
    brief: str
    fichiers: list[str]
    pr: int | None = None
    note: str = ""
    # Ce que la mécanique sait de la carte, et qui n'est pas une
    # instruction : d'où elle vient de tomber, pourquoi, et combien de
    # fois. `note` reste la phrase pour l'œil ; `cause` est le mot que
    # la machine compare.
    cause: str = ""
    essais: int = 0
    role: str = ""

    def __post_init__(self) -> None:
        if not self.lot.strip():
            raise BoiteErreur("une carte sans lot n'en est pas une")
        if not self.brief.strip():
            # Un échantillon vide qui traverse la boîte ferait dépenser
            # un quota sur une instruction qui n'existe pas : lot 035.
            raise BoiteErreur(
                f"la carte {self.lot} ne nomme aucun brief — "
                "le brief est la seule source d'instruction"
            )

    def vers_dict(self) -> dict:
        return {
            "lot": self.lot,
            "brief": self.brief,
            "fichiers": list(self.fichiers),
            "pr": self.pr,
            "note": self.note,
            "cause": self.cause,
            "essais": self.essais,
            "role": self.role,
        }


def racine_boite(projet: Path) -> Path:
    return Path(projet) / ".atelier" / "boite"


def _dossier(projet: Path, nom: str) -> Path:
    """Où regarder. Regarder ne crée rien : sans écriture, rien n'est écrit."""
    return racine_boite(projet) / nom


def _ouvrir(projet: Path, nom: str) -> Path:
    """Où déposer. Seul un dépôt crée le dossier."""
    cible = _dossier(projet, nom)
    cible.mkdir(parents=True, exist_ok=True)
    return cible


def _chemin(projet: Path, etat: str, lot: str) -> Path:
    return _dossier(projet, etat) / f"{lot}.json"


def deposer(projet: Path, etat: str, carte: Carte, *, ecraser: bool = False) -> Path:
    cible = _ouvrir(projet, etat) / f"{carte.lot}.json"
    if cible.exists() and not ecraser:
        raise BoiteErreur(f"carte déjà là : {cible}")
    cible.write_text(json.dumps(carte.vers_dict(), indent=2, ensure_ascii=False) + "\n")
    return cible


def _depuis_brut(brut: dict, fichier: Path) -> Carte:
    if not brut:
        raise BoiteErreur(f"carte vide : {fichier}")
    try:
        return Carte(
            lot=brut["lot"],
            brief=brut["brief"],
            fichiers=list(brut.get("fichiers") or []),
            pr=brut.get("pr"),
            note=brut.get("note") or "",
            cause=brut.get("cause") or "",
            essais=int(brut.get("essais") or 0),
            role=brut.get("role") or "",
        )
    except KeyError as exc:
        raise BoiteErreur(f"carte incomplète {fichier} : {exc.args[0]}") from exc


def _depuis_json(fichier: Path) -> Carte:
    try:
        brut = json.loads(fichier.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        # Un traceback Python dans le journal du cron ne dit rien à
        # personne, et la pile n'ajoute rien à « ce fichier n'est pas du
        # JSON ». On nomme le fichier : c'est lui qu'on répare.
        raise CarteIllisible(f"carte illisible {fichier} : {exc}") from exc
    return _depuis_brut(brut, fichier)


# Le suffixe que porte une carte qu'on a écartée pour ne pas bloquer sa
# file. Elle n'est pas effacée : elle est mise de côté, à côté.
SUFFIXE_ILLISIBLE = ".illisible"


def lister(projet: Path, etat: str) -> list[Carte]:
    """Les cartes lisibles. Une carte illisible ne prend pas la file en otage.

    Avant, un seul JSON corrompu faisait remonter un `JSONDecodeError`
    jusqu'au cron : le rôle plantait à chaque réveil, et les autres
    cartes de la même file attendaient une réparation à la main. Le
    fichier fautif est maintenant mis de côté — jamais effacé — et la
    file repart.
    """
    dossier = _dossier(projet, etat)
    if not dossier.is_dir():
        return []
    cartes: list[Carte] = []
    for fichier in sorted(dossier.glob("*.json")):
        try:
            cartes.append(_depuis_json(fichier))
        except CarteIllisible as exc:
            ecarte = fichier.with_suffix(fichier.suffix + SUFFIXE_ILLISIBLE)
            fichier.rename(ecarte)
            print(
                f"carte écartée : {exc} — mise de côté dans {ecarte.name}",
                file=sys.stderr,
            )
    return cartes


def lire(projet: Path, etat: str, lot: str) -> Carte:
    source = _chemin(projet, etat, lot)
    if not source.is_file():
        raise BoiteErreur(f"pas de carte {lot} dans {etat}")
    return _depuis_json(source)


def _fichiers_tenus(projet: Path) -> dict[str, str]:
    """Quel lot tient quel fichier, d'après le tableau des verrous."""
    tenus: dict[str, str] = {}
    for pose in verrou.charger(Path(projet)).poses:
        for fichier in pose.fichiers:
            tenus[fichier] = pose.lot
    return tenus


def prochain(projet: Path, role: str) -> Carte | None:
    if role not in BOITE_DU_ROLE:
        raise BoiteErreur(f"rôle inconnu : {role} (connus : {', '.join(ROLES)})")
    cartes = lister(projet, BOITE_DU_ROLE[role])
    if role != ROLE_QUI_ECRIT:
        return cartes[0] if cartes else None
    # « 044 occupe engine.py ? 046 attend dans a-coder. Le cron prend
    # 047 s'il est disjoint, ou sort RIEN. » Un fichier n'est pas dans
    # deux lots actifs.
    tenus = _fichiers_tenus(projet)
    for carte in cartes:
        pris = [
            f for f in carte.fichiers
            if tenus.get(Path(f).as_posix(), carte.lot) != carte.lot
        ]
        if not pris:
            return carte
    return None


def avancer(projet: Path, role: str, lot: str, **champs: object) -> Path:
    inconnus = sorted(k for k in champs if k not in CHAMPS_MODIFIABLES)
    if inconnus:
        raise BoiteErreur(
            f"une carte ne change pas de {', '.join(inconnus)} : "
            "le brief est la seule source d'instruction"
        )
    etat = BOITE_DU_ROLE[role]
    source = _chemin(projet, etat, lot)
    if not source.is_file():
        raise BoiteErreur(f"pas de carte {lot} dans {etat}")
    brut = json.loads(source.read_text(encoding="utf-8"))
    fichiers = champs.get("fichiers")
    if fichiers and brut.get("fichiers"):
        raise BoiteErreur(
            f"le périmètre de la carte {lot} est déjà posé : il ne se réécrit pas"
        )
    brut.update({k: v for k, v in champs.items() if v is not None})
    carte = Carte(
        lot=brut["lot"],
        brief=brut["brief"],
        fichiers=list(brut.get("fichiers") or []),
        pr=brut.get("pr"),
        note=brut.get("note") or "",
    )
    destination = deposer(projet, SUIVANT[role], carte)
    source.unlink()
    return destination


def echouer(projet: Path, role: str, lot: str, raison: str, cause: str = "") -> Path:
    """Range la carte dans `echec/`, avec ce qu'il faut pour l'en sortir.

    Le dépôt écrase : une carte qui échoue une seconde fois trouvait sa
    place prise, `echouer` levait, et `crons/tour.sh` sortait avant de
    lever le verrou — la carte restait alors dans la file du rôle, qui
    la reprenait au réveil suivant et la repayait. Une boucle de
    dépense, mesurée. Un second échec écrase donc le premier et compte
    un essai de plus.
    """
    etat = BOITE_DU_ROLE[role]
    source = _chemin(projet, etat, lot)
    if not source.is_file():
        raise BoiteErreur(f"pas de carte {lot} dans {etat}")
    ancienne = _depuis_json(source)
    deja = _chemin(projet, "echec", lot)
    essais = ancienne.essais
    if deja.is_file():
        essais = max(essais, _depuis_json(deja).essais)
    carte = Carte(
        lot=ancienne.lot,
        brief=ancienne.brief,
        fichiers=list(ancienne.fichiers),
        pr=ancienne.pr,
        note=raison,
        cause=cause or reprise.INCONNUE,
        essais=essais + 1,
        role=role,
    )
    destination = deposer(projet, "echec", carte, ecraser=True)
    source.unlink()
    return destination


def retirer(projet: Path, etat: str, lot: str) -> Carte:
    """Sort une carte de sa boîte et la rend. `faite` et `a-relire` comprises."""
    source = _chemin(projet, etat, lot)
    if not source.is_file():
        raise BoiteErreur(f"pas de carte {lot} dans {etat}")
    carte = _depuis_json(source)
    source.unlink()
    return carte


def ou_est(projet: Path, lot: str) -> str | None:
    """Dans quelle boîte dort cette carte. None si aucune."""
    racine = racine_boite(projet)
    if not racine.is_dir():
        return None
    for dossier in sorted(racine.iterdir()):
        if dossier.is_dir() and (dossier / f"{lot}.json").is_file():
            return dossier.name
    return None


def rappelables(projet: Path, role: str) -> list[Carte]:
    """Les cartes de `echec/` que ce rôle a le droit de reprendre seul."""
    return [
        carte for carte in lister(projet, "echec")
        if carte.role == role and reprise.retentable(carte.cause, carte.essais)
    ]


def rappeler(projet: Path, role: str) -> list[Carte]:
    """Remet en circulation les cartes retentables de ce rôle.

    La carte retourne dans la boîte du rôle qui l'a laissée tomber, pas
    dans celle que la feuille recalculerait : un lot qui a échoué en
    relecture n'est pas un lot à recoder.
    """
    rappelees: list[Carte] = []
    for carte in rappelables(projet, role):
        if _chemin(projet, BOITE_DU_ROLE[role], carte.lot).exists():
            # La file la porte déjà : rien à rappeler, et surtout pas
            # de doublon. On laisse la trace dans echec/ pour l'œil.
            continue
        deposer(projet, BOITE_DU_ROLE[role], carte)
        retirer(projet, "echec", carte.lot)
        rappelees.append(carte)
    return rappelees
