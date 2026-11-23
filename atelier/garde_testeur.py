"""La garde du testeur : il joue par l'écran, et ne sait rien d'autre.

Le testeur juge ce qu'un joueur trouve seul. S'il lisait le code, le service
du monde ou un journal, il saurait où cliquer et son verdict ne dirait plus
rien. Claude Code appelle ce script avant chacun de ses appels d'outil
(`agents.reglages`), et il sort 2 avec la raison quand il refuse : le testeur
la lit, et note ce qui lui manquait comme un défaut de l'écran.

Deux gestes passent, et rien d'autre :

- son outil de jeu, appelé tel que sa consigne l'écrit (lancer, jouer des
  gestes, fermer, regarder qui est au premier plan) : aucune autre commande,
  aucun chemin, aucun enchaînement ;
- lire un fichier de son dossier de passage : ses photos, et les deux textes
  qu'un joueur averti connaît (la vision du jeu, les repères de 1400).

    python3 garde_testeur.py <outil.ps1> <dossier du passage>   # l'appel arrive en JSON sur l'entrée standard
"""

from __future__ import annotations

import json
import ntpath
import re
import sys

# Les outils que le harnais pourrait lui proposer et qu'il n'a pas.
REFUSES = ("Bash", "Glob", "Grep", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Agent", "Task")
# Ceux que la garde juge : `agents.reglages` l'appelle pour eux.
JUGES = ("PowerShell", "Read", *REFUSES)
ACTIONS = ("lancer", "gestes", "fermer", "sonde")
# L'appel de l'outil : `& "<outil>"`, puis ses seules options.
_APPEL = re.compile(r"""^\s*&\s*(["'])(?P<outil>[^"']+)\1(?P<options>(?:\s+-(?:Action\s+\w+|Attente\s+\d+|"""
                    r"""Gestes\s+(?:"[^"]*"|'[^']*')))+)\s*$""")
_ACTION = re.compile(r"-Action\s+(\w+)")
_GESTES = re.compile(r"""-Gestes\s+(?:"([^"]*)"|'([^']*)')""")
# Une liste de gestes : des mots, des nombres, des « ; » ; rien que PowerShell interprète.
_LISTE = re.compile(r"^[A-Za-z0-9 ;._-]*$")


def _norme(chemin: str) -> str:
    """Un chemin de Windows, tel que Windows le compare : le testeur ne joue que sur le PC."""
    return ntpath.normcase(ntpath.normpath(chemin))


def _meme(a: str, b: str) -> bool:
    return _norme(a) == _norme(b)


def _dedans(chemin: str, dossier: str) -> bool:
    return ntpath.isabs(chemin) and _norme(chemin).startswith(_norme(dossier).rstrip("\\") + "\\")


def refus(outil_appele: str, entree: dict, outil: str, dossier: str) -> str:
    """Pourquoi cet appel est refusé ; vide s'il passe."""
    if outil_appele == "PowerShell":
        commande = str(entree.get("command") or "")
        m = _APPEL.match(commande)
        if not m or not _meme(m.group("outil"), outil):
            return ("ta seule commande est ton outil de jeu, tel que ta consigne l'écrit : "
                    f'& "{outil}" -Action gestes -Gestes "clic 960 540; photo p01". Rien avant, rien après.')
        actions = _ACTION.findall(m.group("options"))
        if len(actions) != 1 or actions[0] not in ACTIONS:
            return "l'outil de jeu ne connaît que -Action " + ", ".join(ACTIONS) + ", une seule fois."
        listes = _GESTES.findall(m.group("options"))
        if any(not _LISTE.match(a or b) for a, b in listes):
            return ("une liste de gestes ne porte que des mots, des nombres et des « ; » : "
                    '"clic 960 540; attendre 2; photo p01".')
        return ""
    if outil_appele == "Read":
        chemin = str(entree.get("file_path") or "")
        if not chemin or not _dedans(chemin, dossier):
            return (f"tu ne lis que ton dossier de passage ({dossier}) : tes photos, la vision et les repères. Ce que "
                    "l'écran ne dit pas est un défaut à noter, pas une raison d'aller le chercher ailleurs.")
        return ""
    if outil_appele in REFUSES:
        return "tu joues par l'écran : ton outil de jeu, et la lecture de tes photos. Rien d'autre."
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print("Garde du testeur mal appelée : l'outil et le dossier du passage manquent.", file=sys.stderr)
        return 2
    try:
        lu = json.load(sys.stdin)
    except ValueError:
        lu = None
    if not isinstance(lu, dict):
        # Un appel illisible ne passe pas : la garde ne laisse rien au doute.
        print("Appel refusé par la chaîne : il est illisible.", file=sys.stderr)
        return 2
    entree = lu.get("tool_input") if isinstance(lu.get("tool_input"), dict) else {}
    raison = refus(str(lu.get("tool_name") or ""), entree, argv[0], argv[1])
    if raison:
        print(f"Appel refusé par la chaîne : {raison}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
