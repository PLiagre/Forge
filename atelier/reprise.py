"""Ce qui se retente, et ce qui demande une personne.

`echec/` était un cul-de-sac : seule `atelier reprendre`, tapée par un
humain, en sortait. Chaque panne passagère — un délai dépassé, un agent
qui plante — coûtait donc une intervention, alors que la reprise aurait
donné un autre résultat sans que personne ne décide quoi que ce soit.

Le partage n'est pas « grave / pas grave », c'est : **est-ce que
refaire le même geste peut donner un autre résultat ?**

- Un délai dépassé, un agent qui rend un code non nul : oui. L'entrée
  n'a pas changé, mais le tirage, si. On reprend, et on borne.
- Un brief absent, un périmètre vide, une branche sans ancêtre commun,
  un numéro de PR que l'agent n'a pas écrit : non. Refaire à
  l'identique brûle un quota pour arriver au même endroit. Il faut
  qu'une personne écrive le brief, corrige le périmètre, inspecte la
  branche ou lise la PR. C'est une décision, pas une réparation.

Le plafond n'est pas un ornement : sans lui, une cause retentable
devient une boucle de dépense. Il se compte en essais, pas en heures —
le réveil du rôle fournit déjà le délai (deux heures entre deux tours
du coder), et une horloge de plus serait une horloge de plus à lire.
"""

from __future__ import annotations


# La cause tient en un mot, écrit par `crons/tour.sh` : c'est elle qu'on
# lit, jamais la phrase de la note. Une note se réécrit ; une cause se
# compare.
TIMEOUT = "timeout"
AGENT = "agent"
BRIEF_ABSENT = "brief-absent"
PERIMETRE = "perimetre"
BRANCHE = "branche"
PR = "pr"
VERROU = "verrou"
WORKTREE = "worktree"
AVANCER = "avancer"
INCONNUE = "inconnue"

CAUSES = (
    TIMEOUT, AGENT, BRIEF_ABSENT, PERIMETRE, BRANCHE,
    PR, VERROU, WORKTREE, AVANCER, INCONNUE,
)

# Combien de fois l'atelier remet une carte en circulation tout seul.
# 0 = jamais : la carte attend une personne.
#
# `agent` a un plafond de 1 et non de 2 : un agent qui plante deux fois
# de suite ne plante pas par hasard, et chaque reprise coûte un quota.
# `timeout` en a 2 : il ne dit rien du travail, seulement de sa durée,
# et un lot qui déborde une fois tient souvent la seconde.
PLAFONDS: dict[str, int] = {
    TIMEOUT: 2,
    AGENT: 1,
    # Ce qui suit ne se retente pas : la même entrée rendra la même
    # réponse, et c'est une personne qu'il faut, pas un second essai.
    BRIEF_ABSENT: 0,
    PERIMETRE: 0,
    BRANCHE: 0,
    PR: 0,
    VERROU: 0,
    WORKTREE: 0,
    AVANCER: 0,
    # Une cause qu'on n'a pas nommée n'est pas une cause qu'on connaît :
    # on ne parie pas un quota dessus.
    INCONNUE: 0,
}


def plafond(cause: str) -> int:
    """Combien de reprises automatiques cette cause autorise."""
    return PLAFONDS.get(cause or INCONNUE, 0)


def retentable(cause: str, essais: int) -> bool:
    """Cette carte revient-elle seule ? `essais` compte les échecs déjà subis."""
    return essais <= plafond(cause)


def raison_du_refus(cause: str, essais: int) -> str:
    """Pourquoi cette carte reste dans echec/. Une phrase, pour le journal."""
    maximum = plafond(cause)
    if maximum == 0:
        return (
            f"cause « {cause or INCONNUE} » : refaire le même geste rendrait la "
            "même réponse — c'est une décision, pas une réparation"
        )
    return f"cause « {cause} » : {essais} essai(s) pour un plafond de {maximum}"
