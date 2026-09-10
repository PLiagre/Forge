"""La relecture : une donnée, pas une prose.

La règle de rôle du dépôt est une phrase : celui qui a écrit le code ne
dit pas s'il est recevable. Tant que la relecture est un commentaire,
cette phrase est une politesse — rien ne la tient. Ici elle devient un
contrôle : une approbation existe, elle porte sur la **révision
courante** de la PR, et son auteur n'est pas de ceux qui ont écrit les
commits.

Quatre refus, et aucun feu vert par défaut :

- **absente** — personne n'a approuvé ;
- **périmée** — l'approbation porte sur une révision antérieure ; le
  code a bougé depuis, l'approbation ne dit plus rien de lui ;
- **de l'auteur** — seul un auteur des commits a approuvé ;
- **refus** — une demande de changements est posée sur la révision
  courante.

Ce module ne parle pas à GitHub : il reçoit les revues déjà lues.
"""

from __future__ import annotations

from dataclasses import dataclass

APPROUVE = "APPROVED"
REFUSE = "CHANGES_REQUESTED"


@dataclass(frozen=True)
class Revue:
    auteur: str
    etat: str
    # La révision relue. GitHub peut la rendre vide ; une revue sans
    # révision ne porte sur rien, et elle est écartée comme périmée.
    revision: str


@dataclass(frozen=True)
class Verdict:
    passe: bool
    raison: str


def juger(revision: str, auteurs_du_code, revues) -> Verdict:
    """Le verdict de relecture d'une révision, et pourquoi.

    `auteurs_du_code` : les connexions GitHub qui ont écrit ou porté les
    commits de la PR — l'auteur de la PR en fait partie. C'est d'elles
    qu'on se méfie, pas d'un nom déclaré dans la PR.
    """
    if not revision:
        return Verdict(False, "révision inconnue : rien à relire")
    auteurs = {a.lower() for a in auteurs_du_code if a}
    if not auteurs:
        # Rule 10 : une donnée manquante ne se devine pas. Sans auteur
        # connu, on ne peut pas dire que le relecteur n'en est pas un.
        return Verdict(False, "aucun auteur de commit connu : la règle de rôle ne peut pas être tenue")

    # Une revue par relecteur : la dernière qu'il a posée sur cette
    # révision. Un « changements demandés » suivi d'une approbation est
    # une approbation.
    derniere: dict[str, Revue] = {}
    for revue in revues:
        if not revue.auteur:
            # GitHub rend `user: null` pour un compte supprimé. Une
            # approbation que personne ne signe ne prouve pas qu'un
            # tiers a relu : elle ne compte pas.
            continue
        if revue.revision != revision:
            continue  # périmée : elle parle d'un autre code
        if revue.etat not in (APPROUVE, REFUSE):
            continue  # un commentaire ne verdit ni ne bloque
        derniere[revue.auteur.lower()] = revue

    refus = sorted(a for a, r in derniere.items() if r.etat == REFUSE)
    if refus:
        return Verdict(False, f"changements demandés sur {revision[:7]} par {', '.join(refus)}")

    approbations = sorted(a for a, r in derniere.items() if r.etat == APPROUVE)
    if not approbations:
        return Verdict(
            False,
            f"aucune approbation sur {revision[:7]} : relecture absente ou périmée",
        )
    tiers = [a for a in approbations if a not in auteurs]
    if not tiers:
        return Verdict(
            False,
            f"seuls les auteurs du code ont approuvé ({', '.join(approbations)}) : "
            "celui qui a écrit le code ne dit pas s'il est recevable",
        )
    return Verdict(True, f"approuvée sur {revision[:7]} par {', '.join(tiers)}")


def revues_depuis_github(bruts) -> list[Revue]:
    """Les revues, telles que l'API les rend. Un champ absent vaut vide,
    et une revue vide ne verdit rien — jamais l'inverse."""
    return [
        Revue(
            auteur=(brut.get("user") or {}).get("login", ""),
            etat=brut.get("state", ""),
            revision=brut.get("commit_id") or "",
        )
        for brut in bruts
    ]
