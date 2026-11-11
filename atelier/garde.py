"""La garde d'une réparation de la chaîne par elle-même.

Quand le dépanneur dit que la chaîne est en cause, le mécanicien peut la
réparer (`pilote._reparer_la_chaine`) : jusqu'au 10 novembre 2026, seul le
propriétaire le pouvait, en mode direct, et 21 lots l'ont attendu pour cela en
six semaines. Ce fichier dit ce qu'une telle réparation a le droit de
toucher. Il est fait de fonctions pures, que le pilote applique avant
d'enregistrer : un changement hors de portée est retiré, jamais poussé.

Ce n'est pas un bac à sable : les agents tournent déjà sur le VPS et sur le
PC. C'est une garde contre la dérive : une réparation ne sort pas de la
chaîne, ne touche pas à ce qui garde la chaîne, et ne change ni les droits,
ni les secrets, ni la machine d'un workflow. Ce fichier et ses tests sont
eux-mêmes hors de portée (`[projet].sensibles`) : seul le mode direct y écrit.
"""
from __future__ import annotations

import re

# Dans un workflow, les lignes qu'une réparation n'ajoute ni ne retire : ses
# droits, ses secrets, sa machine, ses déclencheurs et les actions qu'il
# appelle. Le reste (une commande, une option, une reprise) lui est ouvert.
_LIGNE_SENSIBLE = re.compile(
    r"permissions\s*:|secrets\.|GITHUB_TOKEN|runs-on\s*:|self-hosted|"
    r"pull_request|workflow_run|workflow_dispatch|^\s*on\s*:|^\s*-?\s*uses\s*:|"
    r"^\s*(push|schedule|branches|paths)\s*:", re.IGNORECASE)
WORKFLOWS = ".github/"


def _sous(chemin: str, regles: tuple[str, ...]) -> bool:
    chemin = chemin.replace("\\", "/")
    return any(chemin == regle or (regle.endswith("/") and chemin.startswith(regle)) for regle in regles)


def reparable(chemin: str, reparables: tuple[str, ...], sensibles: tuple[str, ...]) -> bool:
    """Une réparation de la chaîne a-t-elle le droit d'écrire ce chemin ? Il
    est nommé par `reparables`, et pas par `sensibles`, qui l'emporte."""
    return _sous(chemin, reparables) and not _sous(chemin, sensibles)


def lignes_sensibles(chemin: str, lignes: list[str]) -> list[str]:
    """Parmi les lignes qu'une réparation ajoute ou retire dans un workflow,
    celles qu'elle n'a pas le droit de toucher. Hors de `.github/`, aucune."""
    if not chemin.replace("\\", "/").startswith(WORKFLOWS):
        return []
    return [l.strip() for l in lignes if _LIGNE_SENSIBLE.search(l)]


def hors_reparation(chemin: str, lignes: list[str], reparables: tuple[str, ...],
                    sensibles: tuple[str, ...]) -> str:
    """Pourquoi ce changement est retiré d'une réparation de la chaîne, ou « ».

    `lignes` : celles que la réparation ajoute ou retire dans ce fichier
    (`depot.lignes_changees`)."""
    if not reparable(chemin, reparables, sensibles):
        return "hors de portée d'une réparation"
    touchees = lignes_sensibles(chemin, lignes)
    if touchees:
        return f"touche aux droits, aux secrets, à la machine ou aux déclencheurs d'un workflow (« {touchees[0][:80]} »)"
    return ""
