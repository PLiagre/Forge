"""La garde des commandes d'un agent : ni la suite entière, ni une simulation longue.

Claude Code appelle ce script avant chaque commande de shell d'un agent ou de
son sous-agent (`agents.reglages`). Il lit sur son entrée standard ce que
l'agent veut lancer, et sort 2 avec la raison quand il le refuse : l'agent la
lit et choisit une autre commande.

Deux refus, et rien d'autre :

- la suite de tests entière du jeu : elle prend près d'une heure sur le VPS,
  plus que le délai d'un appel. Un lot joue les tests de ce qu'il touche ; la
  CI joue la suite ;
- une simulation de plus de `jours_max` jours : les longues preuves (un an,
  dix ans) tournent la nuit.

    python3 garde_commandes.py <jours_max>   # la commande arrive en JSON sur l'entrée standard
"""

from __future__ import annotations

import json
import re
import sys

# pytest lancé : `python3 -m pytest`, ou `pytest` en tête d'une commande. Le
# mot cité ailleurs (un `grep`, un nom de fichier) n'est pas un lancement.
_PYTEST = re.compile(r"-m\s+pytest\b|(?:^|[;&|(])\s*pytest\b")
# Ce qui borne un lancement de pytest : un fichier de test, un nom (`-k`),
# un test précis (`::`), ou la suite courte de la chaîne.
_BORNE = re.compile(r"[\w/\\.-]*test\w*\.py\b|(?:^|\s)-k[\s=]|::|atelier[/\\]tests")
_JOURS = re.compile(r"--(?:ticks|jours|days)[\s=]+(\d+)")


def refus(commande: str, jours_max: int) -> str:
    """Pourquoi cette commande est refusée ; vide si elle passe."""
    if _PYTEST.search(commande) and not _BORNE.search(commande):
        return ("la suite entière ne se joue pas pendant un lot : elle dépasse ton délai, et la CI la joue après la "
                "poussée. Joue les tests de ce que tu touches : un fichier de test, ou un nom avec -k.")
    longues = [int(n) for n in _JOURS.findall(commande) if int(n) > jours_max]
    if longues:
        return (f"une simulation de {max(longues)} jours ne se joue pas pendant un lot ({jours_max} au plus) : les "
                "longues preuves tournent la nuit. Prouve sur une durée courte, ou sur un monde d'épreuve.")
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    jours_max = int(argv[0]) if argv and argv[0].isdigit() else 400
    try:
        lu = json.load(sys.stdin)
    except ValueError:
        return 0
    entree = lu.get("tool_input") if isinstance(lu, dict) else None
    commande = entree.get("command") if isinstance(entree, dict) else ""
    raison = refus(commande or "", jours_max)
    if raison:
        print(f"Commande refusée par la chaîne : {raison}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
